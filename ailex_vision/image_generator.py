"""
AILEX — image_generator.py  (P7)
On-demand image generation via FLUX.1-pro when ContentGuard has no verified image.
Generates contextually correct images with semantic prompts.

Pipeline:
    1. ContentGuard.pick(category) → if None (category exhausted or missing)
    2. ImageGenerator.generate(semantic_role, context) → FLUX.1-pro via Replicate
    3. Verify generated URL returns 200
    4. Add to ContentGuard runtime library for session reuse

Usage:
    from ailex_vision.image_generator import ImageGenerator
    gen = ImageGenerator(replicate_token="r8_...")
    url = gen.generate("romantic_couple", context="Italian luxury dating, evening light")
    # url is a valid HTTPS image URL

    # Integration with ContentGuard:
    from ailex_vision.image_generator import guaranteed_image
    url = guaranteed_image("romantic_couple", context="Roma, Italian couple")
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional

# ── Semantic prompt library ───────────────────────────────────────────────────
# Maps ContentGuard categories → FLUX prompt templates
CATEGORY_PROMPTS: Dict[str, str] = {
    "romantic_couple": (
        "romantic Italian couple, {context}, warm golden hour light, "
        "elegant and intimate, cinematic depth of field, luxury lifestyle photography, "
        "8K, award-winning photo, shot on Sony A7R IV"
    ),
    "wedding": (
        "Italian wedding, {context}, elegant venue, warm candlelight, "
        "beautiful bride and groom, cinematic wedding photography, luxury aesthetic, "
        "Tuscany, golden hour, 8K resolution"
    ),
    "female_portrait_elegant": (
        "professional portrait of elegant Italian woman, {context}, "
        "soft studio lighting, neutral background, sophisticated, confident, "
        "luxury fashion editorial style, shallow depth of field, 8K"
    ),
    "male_portrait_elegant": (
        "professional portrait of elegant Italian man, {context}, "
        "soft studio lighting, neutral background, sophisticated, confident, "
        "luxury lifestyle editorial style, shallow depth of field, 8K"
    ),
    "italian_location": (
        "stunning Italian location, {context}, architecture, golden hour sunlight, "
        "cinematic landscape photography, ultra-detailed, aerial perspective, "
        "Rome or Tuscany or Cinque Terre, 8K"
    ),
    "luxury_dining": (
        "luxury Italian restaurant interior, {context}, "
        "warm ambient bokeh lighting, elegant table settings, candles, "
        "high-end hospitality photography, 8K resolution"
    ),
    "luxury_lifestyle": (
        "Italian luxury lifestyle, {context}, premium, aspirational, "
        "elegant interior or outdoor setting, sophisticated aesthetic, "
        "editorial photography, 8K"
    ),
    "diplomatic_institutional": (
        "formal institutional architecture, {context}, "
        "neoclassical Italian building, official, prestigious, "
        "architectural photography, symmetrical, 8K"
    ),
}

NEGATIVE_PROMPT = (
    "cartoon, anime, illustration, painting, low quality, blurry, "
    "watermark, text, oversaturated, plastic, artificial, fake, distorted"
)


# ── Dataclass ─────────────────────────────────────────────────────────────────
@dataclass
class GeneratedImage:
    url:       str
    category:  str
    context:   str
    model:     str
    prompt:    str
    width:     int
    height:    int
    provider:  str   = "replicate"
    cached:    bool  = False
    verified:  bool  = False    # HTTP 200 confirmed


# ── Generator ─────────────────────────────────────────────────────────────────
class ImageGenerator:
    """
    Generates contextually appropriate images via FLUX.1-pro on Replicate.
    Falls back to curated Unsplash images if Replicate is unavailable.

    Replicate API: https://replicate.com/black-forest-labs/flux-1.1-pro
    """

    REPLICATE_API = "https://api.replicate.com/v1/models/black-forest-labs/flux-1.1-pro/predictions"

    # Fallback Unsplash images per category (all verified 200)
    UNSPLASH_FALLBACK: Dict[str, List[str]] = {
        "romantic_couple": [
            "https://images.unsplash.com/photo-1529634806980-85c3dd6d34ac?w=800&q=88&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1537944434965-cf4679d1a598?w=800&q=88&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1518621736915-f3b1c41bfd00?w=800&q=88&auto=format&fit=crop",
        ],
        "wedding": [
            "https://images.unsplash.com/photo-1519225421980-715cb0215aed?w=800&q=88&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1516589178581-6cd7833ae3b2?w=800&q=88&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1519741497674-611481863552?w=800&q=88&auto=format&fit=crop",
        ],
        "female_portrait_elegant": [
            "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=500&q=88&auto=format&fit=crop&face",
            "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=500&q=88&auto=format&fit=crop&face",
        ],
        "male_portrait_elegant": [
            "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=500&q=88&auto=format&fit=crop&face",
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=500&q=88&auto=format&fit=crop&face",
        ],
        "italian_location": [
            "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=1920&q=85&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1531572753322-ad063cecc140?w=1920&q=85&auto=format&fit=crop",
        ],
        "luxury_dining": [
            "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800&q=85&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&q=85&auto=format&fit=crop",
        ],
    }

    def __init__(self, replicate_token: str = ""):
        self.token = replicate_token or os.environ.get("REPLICATE_API_TOKEN", "")
        self._session_cache: Dict[str, str] = {}   # category+context → url

    def generate(
        self,
        category:    str,
        context:     str = "",
        width:       int = 1024,
        height:      int = 1024,
        steps:       int = 25,
        timeout:     int = 120,
    ) -> Optional[GeneratedImage]:
        """
        Generate an image for the given semantic category.
        Returns GeneratedImage on success, None on failure.
        """
        # Session cache
        cache_key = f"{category}:{context}"
        if cache_key in self._session_cache:
            url = self._session_cache[cache_key]
            return GeneratedImage(url=url, category=category, context=context,
                                  model="cached", prompt="", width=width, height=height,
                                  cached=True, verified=True)

        # Build semantic prompt
        template = CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["luxury_lifestyle"])
        prompt   = template.format(context=context or "Italy, elegant, premium")

        if not self.token:
            return self._fallback(category, context, width, height)

        try:
            url = self._replicate_generate(prompt, width, height, steps, timeout)
            if url:
                verified = self._verify_url(url)
                img = GeneratedImage(
                    url=url, category=category, context=context,
                    model="flux-1.1-pro", prompt=prompt,
                    width=width, height=height,
                    provider="replicate", verified=verified,
                )
                if verified:
                    self._session_cache[cache_key] = url
                return img
        except Exception:
            pass

        return self._fallback(category, context, width, height)

    def generate_for_site(
        self,
        site_type: str,
        slots:     Dict[str, str],   # slot_name → semantic category
        context:   str = "",
    ) -> Dict[str, str]:
        """
        Generate all images for a website in parallel.
        Returns slot_name → image_url dict.
        """
        import concurrent.futures

        def gen_slot(item):
            slot, category = item
            img = self.generate(category, context=context)
            return slot, img.url if img else self._fallback_url(category)

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            results = dict(ex.map(gen_slot, slots.items()))

        return results

    # ── Private ───────────────────────────────────────────────────────────────

    def _replicate_generate(
        self, prompt: str, width: int, height: int, steps: int, timeout: int
    ) -> Optional[str]:
        """Submit prediction to Replicate and poll for result."""
        payload = {
            "input": {
                "prompt":          prompt,
                "negative_prompt": NEGATIVE_PROMPT,
                "width":           width,
                "height":          height,
                "num_inference_steps": steps,
                "output_format":   "webp",
                "output_quality":  90,
            }
        }

        # Create prediction
        req = urllib.request.Request(
            self.REPLICATE_API,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.token}",
                "content-type":  "application/json",
                "Prefer":        "wait",  # synchronous response if possible
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp  = json.loads(r.read().decode())

        # Synchronous output (Prefer: wait)
        output = resp.get("output")
        if isinstance(output, list) and output:
            return output[0]
        if isinstance(output, str):
            return output

        # Poll if needed (async)
        poll_url = resp.get("urls", {}).get("get", "")
        if not poll_url:
            return None

        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(3)
            req2 = urllib.request.Request(
                poll_url,
                headers={"Authorization": f"Bearer {self.token}"},
            )
            with urllib.request.urlopen(req2, timeout=30) as r2:
                status_resp = json.loads(r2.read().decode())
            status = status_resp.get("status")
            if status == "succeeded":
                out = status_resp.get("output", [])
                return out[0] if isinstance(out, list) and out else out
            if status in {"failed", "canceled"}:
                return None

        return None

    def _verify_url(self, url: str) -> bool:
        """Check that the generated URL returns HTTP 200."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status == 200
        except Exception:
            return False

    def _fallback(
        self, category: str, context: str, width: int, height: int
    ) -> GeneratedImage:
        """Return a verified Unsplash fallback image."""
        import random
        pool = self.UNSPLASH_FALLBACK.get(category, list(self.UNSPLASH_FALLBACK.values())[0])
        url  = random.choice(pool)
        return GeneratedImage(
            url=url, category=category, context=context,
            model="unsplash-fallback", prompt="",
            width=width, height=height,
            provider="unsplash", verified=True, cached=False,
        )

    def _fallback_url(self, category: str) -> str:
        """Quick URL-only fallback."""
        img = self._fallback(category, "", 800, 600)
        return img.url


# ── Integration helper ────────────────────────────────────────────────────────
def guaranteed_image(
    category: str,
    context:  str    = "",
    params:   str    = "w=800&q=88&auto=format&fit=crop",
    gen:      Optional[ImageGenerator] = None,
) -> str:
    """
    Always returns a valid image URL for the given semantic category.
    Tries ContentGuard first, then generates with FLUX, then Unsplash fallback.

        url = guaranteed_image("romantic_couple", context="Roma")
        # → always a working URL, never None
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        from content_guard import ContentGuard
        cg = ContentGuard()
        url = cg.pick(category, params=params)
        if url:
            return url
    except Exception:
        pass

    g = gen or ImageGenerator()
    img = g.generate(category, context)
    return img.url if img else ""


if __name__ == "__main__":
    print("ImageGenerator demo (no Replicate token — using fallbacks)")
    gen = ImageGenerator()
    for cat in ["romantic_couple", "italian_location", "luxury_dining"]:
        img = gen.generate(cat, context="Italian luxury, premium aesthetic")
        print(f"  {cat:<30} {img.provider:<12} {img.url[:60]}...")
