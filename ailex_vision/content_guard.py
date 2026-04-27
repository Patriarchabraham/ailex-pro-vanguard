"""
AILEX ContentGuard v1.0 — Semantic Content Validation System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Prevents E009: Context-Wrong Image (headphones in a romance site, etc.)

RULE: Every image URL used in a generated website MUST come from
VERIFIED_LIBRARY. Never guess Unsplash IDs from memory — you will be wrong.

Usage:
    from ailex_vision.content_guard import ContentGuard
    cg = ContentGuard()
    images = cg.get_site_images("dating_luxury_italian")
    # → dict of semantic slots → verified URLs

    # Or pick one:
    url = cg.pick("romantic_couple", params="w=800&q=88&auto=format&fit=crop")
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ── VERIFIED IMAGE LIBRARY ────────────────────────────────────────────────────
# CRITICAL: Only add a URL after visually verifying what it shows.
# Each entry documents: photo_id → what it actually contains.
# Organized by SEMANTIC CATEGORY — the emotional/content role of the image.

VERIFIED_LIBRARY: Dict[str, List[Dict[str, str]]] = {

    # ── ROMANTIC COUPLES ─────────────────────────────────────────────────────
    # What to use: manifesto sections, hero backgrounds, gallery, stories
    # What NOT to use here: portraits, food, buildings
    # VERIFIED via HTTP 200 on 2026-04-26
    "romantic_couple": [
        {"id": "photo-1529634806980-85c3dd6d34ac", "desc": "romantic couple embrace, close, intimate"},
        {"id": "photo-1537944434965-cf4679d1a598", "desc": "young couple smiling happily outdoors"},
        {"id": "photo-1484863137850-59afcfe05386", "desc": "couple silhouette at sunset, dramatic light"},
        {"id": "photo-1518621736915-f3b1c41bfd00", "desc": "couple at golden hour, soft romantic atmosphere"},
        {"id": "photo-1526399232581-2ab5608b6336", "desc": "romantic couple, warm tones"},
        # REMOVED (HTTP 404): photo-1474978528675-4a50a4508dc6, photo-1490218645964-24d01e0b4614
    ],

    # ── WEDDING ──────────────────────────────────────────────────────────────
    "wedding": [
        {"id": "photo-1519225421980-715cb0215aed", "desc": "wedding reception couple, elegant"},
        {"id": "photo-1519741497674-611481863552", "desc": "engagement ring, proposal, sparkle"},
        {"id": "photo-1523438885200-e635ba2c371e", "desc": "wedding bouquet, white flowers"},
        {"id": "photo-1516589178581-6cd7833ae3b2", "desc": "bride in white dress, wedding day"},
        {"id": "photo-1529634597503-139d3726fed5", "desc": "wedding couple walking, formal attire"},
        {"id": "photo-1465495976277-4387d4b0b4c6", "desc": "wedding couple, traditional elegant setting"},
        # REMOVED (HTTP 404): photo-1511285560929-80b456503681
    ],

    # ── FEMALE PORTRAITS (elegant, professional) ──────────────────────────────
    # What to use: profile cards, testimonials of women
    # What NOT to use here: couples, scenery, food
    "female_portrait_elegant": [
        {"id": "photo-1524504388940-b1c1722653e1", "desc": "elegant woman portrait, neutral background"},
        {"id": "photo-1531746020798-e6953c6e8e04", "desc": "woman portrait, dark background, professional"},
        {"id": "photo-1529626455594-4ff0802cfb7e", "desc": "elegant woman portrait, warm tones"},
        {"id": "photo-1488716820095-cbe80883c496", "desc": "woman portrait, casual elegant, genuine smile"},
        {"id": "photo-1544005313-94ddf0286df2", "desc": "woman portrait, warm light, natural beauty"},
    ],

    # ── MALE PORTRAITS (elegant, professional) ────────────────────────────────
    "male_portrait_elegant": [
        {"id": "photo-1500648767791-00dcc994a43e", "desc": "man portrait smiling, warm, trustworthy"},
        {"id": "photo-1507003211169-0a1dd7228f2d", "desc": "man portrait, serious, professional"},
        {"id": "photo-1492562080023-ab3db95bfbce", "desc": "man portrait, confident, casual elegant"},
        {"id": "photo-1519085360753-af0119f7cbe7", "desc": "man portrait, outdoor light, sophisticated"},
    ],

    # ── ITALIAN LOCATIONS ─────────────────────────────────────────────────────
    # What to use: hero backgrounds, section backgrounds, location imagery
    "italian_location": [
        {"id": "photo-1476514525535-07fb3b4ae5f1", "desc": "Cinque Terre Italian coast, aerial, colorful"},
        {"id": "photo-1498503182468-3b51cbb6cb24", "desc": "Rome at night, city lights, romantic"},
        {"id": "photo-1531572753322-ad063cecc140", "desc": "Rome ancient architecture at golden hour"},
        {"id": "photo-1533582437411-40e60c7aaef8", "desc": "Italian hillside town, Tuscany, dreamy"},
    ],

    # ── LUXURY DINING / RESTAURANT ────────────────────────────────────────────
    # What to use: event cards, elegance sections, lifestyle imagery
    "luxury_dining": [
        {"id": "photo-1555396273-367ea4eb4db5", "desc": "luxury restaurant interior, warm bokeh lights, elegant"},
        {"id": "photo-1517248135467-4c7edcad34c4", "desc": "restaurant interior, ambient lighting, intimate"},
        {"id": "photo-1414235077428-338989a2e8c0", "desc": "elegant fine dining table setting, luxury"},
        {"id": "photo-1424847651672-bf20a4b0982b", "desc": "upscale restaurant, white tablecloths, sophisticated"},
    ],

    # ── LUXURY LIFESTYLE ──────────────────────────────────────────────────────
    "luxury_lifestyle": [
        {"id": "photo-1506905925346-21bda4d32df4", "desc": "mountain luxury landscape, premium aspirational"},
        {"id": "photo-1441986300917-64674bd600d8", "desc": "luxury interior, high-end design, premium"},
        {"id": "photo-1543248939-ff40856f65d4", "desc": "luxury living, premium lifestyle, aspiration"},
    ],

    # ── DIPLOMATIC / INSTITUTIONAL ────────────────────────────────────────────
    # What to use: institutional portals, government, formal organizations
    "diplomatic_institutional": [
        {"id": "photo-1449824913935-59a10b8d2000", "desc": "formal government/institutional building, classical"},
        {"id": "photo-1486406146926-c627a92ad1ab", "desc": "official building exterior, formal, authoritative"},
        {"id": "photo-1523292562811-8fa7962a78c8", "desc": "neoclassical architecture, institutional, prestigious"},
    ],

    # ── TECHNOLOGY / PROFESSIONAL ─────────────────────────────────────────────
    "technology_professional": [
        {"id": "photo-1550751827-4bd374c3f58b", "desc": "tech workspace, screens, modern professional"},
        {"id": "photo-1497366216548-37526070297c", "desc": "modern office interior, professional environment"},
        {"id": "photo-1518770660439-4636190af475", "desc": "circuit board closeup, technology, precision"},
    ],

    # ── NATURE / LANDSCAPE ────────────────────────────────────────────────────
    "nature_landscape": [
        {"id": "photo-1506905925346-21bda4d32df4", "desc": "mountain landscape, majestic, nature"},
        {"id": "photo-1441974231531-c6227db76b6e", "desc": "forest path, serene, nature"},
        {"id": "photo-1469474968028-56623f02e42e", "desc": "landscape with light rays, ethereal"},
    ],
}


# ── SITE TYPE PRESETS ──────────────────────────────────────────────────────────
# Maps site types to the semantic image slots they need.
# Generators call get_site_images(site_type) to get a complete image kit.

SITE_IMAGE_KITS: Dict[str, Dict[str, str]] = {

    "dating_luxury_italian": {
        "hero_bg":             "romantic_couple",
        "manifesto_photo":     "romantic_couple",
        "cammino_affinita":    "romantic_couple",
        "cammino_eleganza":    "luxury_dining",
        "cammino_destino":     "wedding",
        "profile_female_1":    "female_portrait_elegant",
        "profile_female_2":    "female_portrait_elegant",
        "profile_female_3":    "female_portrait_elegant",
        "profile_male_1":      "male_portrait_elegant",
        "profile_male_2":      "male_portrait_elegant",
        "profile_male_3":      "male_portrait_elegant",
        "stats_bg":            "italian_location",
        "gallery_1":           "romantic_couple",
        "gallery_2":           "wedding",
        "gallery_3":           "wedding",
        "gallery_4":           "romantic_couple",
        "gallery_5":           "wedding",
        "gallery_6":           "romantic_couple",
        "gallery_7":           "romantic_couple",
        "gallery_8":           "romantic_couple",
        "gallery_9":           "wedding",
        "storia_1":            "wedding",
        "storia_2":            "romantic_couple",
        "storia_3":            "romantic_couple",
        "storia_4":            "romantic_couple",
        "evento_1":            "luxury_dining",
        "evento_2":            "luxury_dining",
        "evento_3":            "romantic_couple",
        "register_bg":         "wedding",
    },

    "institutional_diplomatic": {
        "hero_bg":             "diplomatic_institutional",
        "about_photo":         "diplomatic_institutional",
        "mission_bg":          "italian_location",
        "team_female":         "female_portrait_elegant",
        "team_male":           "male_portrait_elegant",
        "gallery_1":           "diplomatic_institutional",
        "gallery_2":           "italian_location",
        "gallery_3":           "luxury_lifestyle",
    },

    "luxury_restaurant": {
        "hero_bg":             "luxury_dining",
        "ambiance_1":          "luxury_dining",
        "ambiance_2":          "luxury_dining",
        "chef_portrait":       "male_portrait_elegant",
        "team_female":         "female_portrait_elegant",
        "location":            "italian_location",
    },
}


# ── CONTENT CONTEXT RULES ────────────────────────────────────────────────────
# Psychological/semantic rules for content-image coherence.
# If a section has this keyword → it CANNOT use these categories.

FORBIDDEN_COMBOS: Dict[str, List[str]] = {
    "romantic":     ["technology_professional", "diplomatic_institutional", "nature_landscape"],
    "luxury_love":  ["technology_professional", "diplomatic_institutional"],
    "institutional":["romantic_couple", "wedding", "luxury_dining"],
    "tech_startup": ["romantic_couple", "wedding", "diplomatic_institutional"],
    "restaurant":   ["romantic_couple", "diplomatic_institutional", "technology_professional"],
}


@dataclass
class ImageSlot:
    slot_name:  str
    category:   str
    url:        str
    desc:       str
    params:     str = "w=800&q=88&auto=format&fit=crop"

    @property
    def full_url(self) -> str:
        return f"https://images.unsplash.com/{self.id}?{self.params}"

    @property
    def id(self) -> str:
        return self.url


class ContentGuard:
    """
    Semantic content validation and image selection.
    Use ONLY this class for image selection in generators.
    Never hardcode Unsplash IDs in generation prompts.

    Prevents E009: Context-Wrong Image.
    """

    BASE = "https://images.unsplash.com/"
    _used: Dict[str, List[str]] = {}  # track used IDs per site to avoid repeats

    def __init__(self):
        self._used = {}

    def pick(
        self,
        category: str,
        params: str = "w=800&q=88&auto=format&fit=crop",
        slot_key: str = "",
        avoid_ids: Optional[List[str]] = None,
    ) -> str:
        """
        Return a verified Unsplash URL for the given semantic category.
        Raises ValueError if category is not in VERIFIED_LIBRARY.
        """
        pool = VERIFIED_LIBRARY.get(category)
        if not pool:
            raise ValueError(
                f"[ContentGuard] Unknown category: '{category}'. "
                f"Available: {list(VERIFIED_LIBRARY.keys())}"
            )

        avoid = set(avoid_ids or [])
        avoid.update(self._used.get(category, []))

        candidates = [e for e in pool if e["id"] not in avoid]
        if not candidates:
            candidates = pool  # allow repeats if all exhausted

        chosen = random.choice(candidates)
        self._used.setdefault(category, []).append(chosen["id"])

        return f"{self.BASE}{chosen['id']}?{params}"

    def pick_with_meta(self, category: str, params: str = "w=800&q=88&auto=format&fit=crop") -> Dict[str, str]:
        """Return {'url': ..., 'desc': ..., 'alt': ...} for use in img tags."""
        pool = VERIFIED_LIBRARY.get(category)
        if not pool:
            raise ValueError(f"[ContentGuard] Unknown category: '{category}'")
        chosen = random.choice(pool)
        return {
            "url": f"{self.BASE}{chosen['id']}?{params}",
            "desc": chosen["desc"],
            "alt": chosen["desc"],
        }

    def get_site_images(
        self,
        site_type: str,
        hero_params: str = "w=1920&q=85&auto=format&fit=crop",
        card_params: str = "w=800&q=88&auto=format&fit=crop",
        portrait_params: str = "w=500&q=88&auto=format&fit=crop&face",
    ) -> Dict[str, str]:
        """
        Return a complete image kit for a site type.
        Keys are semantic slot names → values are verified URLs.

        Example:
            images = cg.get_site_images("dating_luxury_italian")
            # images["hero_bg"] → verified romantic couple URL
            # images["manifesto_photo"] → different romantic couple URL
            # images["profile_female_1"] → elegant female portrait URL
        """
        kit = SITE_IMAGE_KITS.get(site_type)
        if not kit:
            raise ValueError(
                f"[ContentGuard] Unknown site type: '{site_type}'. "
                f"Available: {list(SITE_IMAGE_KITS.keys())}"
            )

        result: Dict[str, str] = {}
        for slot, category in kit.items():
            if "hero" in slot or "bg" in slot or "stats_bg" in slot or "register_bg" in slot:
                p = hero_params
            elif "portrait" in slot or "profile" in slot or "team" in slot or "chef" in slot:
                p = portrait_params
            else:
                p = card_params
            result[slot] = self.pick(category, p, slot_key=slot)

        return result

    def validate_image_url(self, url: str, expected_category: str) -> bool:
        """
        Check if a given Unsplash URL belongs to the expected category.
        Returns False for unknown URLs (fail-safe: reject unknown images).
        """
        for category, entries in VERIFIED_LIBRARY.items():
            for entry in entries:
                if entry["id"] in url:
                    return category == expected_category
        return False  # Unknown URL → always fail

    def validate_html(self, html: str, site_context: str) -> List[str]:
        """
        Scan HTML for img src URLs and check for forbidden combos.
        Returns list of violations (empty = all OK).
        """
        import re
        violations = []
        forbidden = FORBIDDEN_COMBOS.get(site_context, [])
        srcs = re.findall(r'src=["\']([^"\']+unsplash[^"\']+)["\']', html, re.I)

        for src in srcs:
            for category, entries in VERIFIED_LIBRARY.items():
                if any(e["id"] in src for e in entries):
                    if category in forbidden:
                        violations.append(
                            f"[E009] Forbidden image category '{category}' "
                            f"in '{site_context}' context: {src[:70]}"
                        )
                    break
            else:
                violations.append(f"[E009] Unverified image URL (not in library): {src[:70]}")

        return violations

    @staticmethod
    def describe_library() -> str:
        """Print available categories and their image counts."""
        lines = ["ContentGuard — Verified Image Library", "─" * 50]
        for cat, entries in VERIFIED_LIBRARY.items():
            lines.append(f"  {cat:<35} {len(entries)} images")
        lines.append("─" * 50)
        lines.append(f"  Total: {sum(len(v) for v in VERIFIED_LIBRARY.values())} verified images")
        lines.append(f"  Site types: {list(SITE_IMAGE_KITS.keys())}")
        return "\n".join(lines)


# ── QUICK USAGE ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cg = ContentGuard()
    print(ContentGuard.describe_library())
    print()
    print("Example kit for dating_luxury_italian:")
    images = cg.get_site_images("dating_luxury_italian")
    for slot, url in list(images.items())[:6]:
        print(f"  {slot:<25} {url[:60]}...")
