"""
AILEX Vision — image_craft.py
Generate, alter, and improve images via multiple AI backends.

Supported backends:
  - Replicate (Flux Schnell, Flux Dev, SDXL, Stable Diffusion 3, img2img)
  - Stability AI (SDXL, SD3)
  - Together AI (Flux)
  - Demo mode (returns prompt without generating)

Usage:
  craft = ImageCraft()
  result = craft.generate("a futuristic city at sunset, cinematic")
  result = craft.improve("/path/to/image.jpg")
  result = craft.alter("/path/to/image.jpg", "make the sky more dramatic")
  result = craft.recreate_from_analysis(analysis)
"""
from __future__ import annotations

import base64
import io
import os
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

Backend = Literal["replicate", "stability", "together", "demo"]


@dataclass
class GenerationResult:
    success:      bool
    backend:      str
    model:        str
    prompt:       str
    output_path:  Optional[str]
    output_url:   Optional[str]
    width:        int = 1024
    height:       int = 1024
    seed:         int = -1
    time_s:       float = 0.0
    error:        Optional[str] = None
    metadata:     Dict[str, Any] = field(default_factory=dict)


class ImageCraft:
    """Multi-backend image generation and editing."""

    # Best models per backend
    MODELS = {
        "replicate": {
            "fast":     "black-forest-labs/flux-schnell",
            "quality":  "black-forest-labs/flux-dev",
            "sdxl":     "stability-ai/sdxl:39ed52f2319f9b5b84c3b8e5a34e7b27073d853f2d87d44b28e",
            "img2img":  "timothybrooks/instruct-pix2pix:30c1d0b916a6f8efce20493f5d61ee27491ab2a60437c13c588",
            "upscale":  "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7",
        },
        "stability": {
            "sdxl":     "stable-diffusion-xl-1024-v1-0",
            "sd3":      "sd3-medium",
        },
        "together": {
            "flux":     "black-forest-labs/FLUX.1-schnell",
            "flux-dev": "black-forest-labs/FLUX.1-dev",
        },
    }

    def __init__(
        self,
        backend:     Backend = "replicate",
        api_key:     Optional[str] = None,
        save_dir:    str = "/data/data/com.termux/files/home/ailex_vision/generated",
        quality_mode: bool = False,
    ):
        self.backend      = backend
        self.quality_mode = quality_mode
        self.save_dir     = save_dir
        os.makedirs(save_dir, exist_ok=True)
        self._client = None
        self._available = False
        self._init_backend(api_key)

    def _init_backend(self, api_key: Optional[str]) -> None:
        if self.backend == "replicate":
            key = api_key or os.getenv("REPLICATE_API_TOKEN", "")
            if key:
                try:
                    import replicate
                    os.environ["REPLICATE_API_TOKEN"] = key
                    self._client    = replicate
                    self._available = True
                except ImportError:
                    pass

        elif self.backend == "stability":
            key = api_key or os.getenv("STABILITY_API_KEY", "")
            if key:
                try:
                    import stability_sdk.client as stability_client
                    self._client    = stability_client.StabilityInference(key=key)
                    self._available = True
                except ImportError:
                    self._available = False

        elif self.backend == "together":
            key = api_key or os.getenv("TOGETHER_API_KEY", "")
            if key:
                try:
                    import together
                    together.api_key = key
                    self._client    = together
                    self._available = True
                except ImportError:
                    pass

        elif self.backend == "demo":
            self._available = True

    # ── Public methods ────────────────────────────────────────────────────────

    def generate(
        self,
        prompt:   str,
        negative: str = "blurry, low quality, distorted, ugly, watermark",
        width:    int = 1024,
        height:   int = 1024,
        steps:    int = 4,
        seed:     int = -1,
    ) -> GenerationResult:
        """Generate a new image from a text prompt."""
        start = time.time()

        if not self._available or self.backend == "demo":
            return self._demo_result(prompt, width, height)

        enhanced = self._enhance_prompt(prompt)

        try:
            if self.backend == "replicate":
                return self._replicate_generate(enhanced, negative, width, height, steps, seed, start)
            elif self.backend == "stability":
                return self._stability_generate(enhanced, negative, width, height, steps, seed, start)
            elif self.backend == "together":
                return self._together_generate(enhanced, width, height, steps, seed, start)
        except Exception as e:
            return GenerationResult(success=False, backend=self.backend, model="",
                                    prompt=prompt, output_path=None, output_url=None,
                                    error=str(e), time_s=round(time.time()-start, 2))

    def improve(self, image_path: str, strength: float = 0.4) -> GenerationResult:
        """Upscale and enhance an existing image."""
        if not os.path.exists(image_path):
            return GenerationResult(success=False, backend=self.backend, model="",
                                    prompt="", output_path=None, output_url=None,
                                    error=f"File not found: {image_path}")
        if not self._available or self.backend == "demo":
            return self._demo_result(f"upscale: {image_path}", 2048, 2048)

        start = time.time()
        try:
            if self.backend == "replicate":
                return self._replicate_upscale(image_path, start)
        except Exception as e:
            return GenerationResult(success=False, backend=self.backend, model="upscale",
                                    prompt="", output_path=None, output_url=None,
                                    error=str(e), time_s=round(time.time()-start, 2))
        return self._demo_result("improve", 2048, 2048)

    def alter(self, image_path: str, instructions: str) -> GenerationResult:
        """Alter an existing image with text instructions (instruct-pix2pix style)."""
        if not os.path.exists(image_path):
            return GenerationResult(success=False, backend=self.backend, model="",
                                    prompt=instructions, output_path=None, output_url=None,
                                    error=f"File not found: {image_path}")
        if not self._available or self.backend == "demo":
            return self._demo_result(f"alter: {instructions}", 1024, 1024)

        start = time.time()
        try:
            if self.backend == "replicate":
                return self._replicate_img2img(image_path, instructions, start)
        except Exception as e:
            return GenerationResult(success=False, backend=self.backend, model="img2img",
                                    prompt=instructions, output_path=None, output_url=None,
                                    error=str(e), time_s=round(time.time()-start, 2))
        return self._demo_result(instructions, 1024, 1024)

    def recreate_from_analysis(self, analysis: Any, improved: bool = True) -> GenerationResult:
        """Generate from a VisualAnalysis — recreate or improve the original."""
        prompt = analysis.improvement_prompt if improved else analysis.recreation_prompt
        ar = analysis.aspect_ratio or "1:1"
        w, h = self._parse_aspect(ar)
        return self.generate(prompt, width=w, height=h)

    # ── Replicate backend ──────────────────────────────────────────────────────

    def _replicate_generate(self, prompt: str, negative: str, w: int, h: int,
                             steps: int, seed: int, start: float) -> GenerationResult:
        model = (self.MODELS["replicate"]["quality"] if self.quality_mode
                 else self.MODELS["replicate"]["fast"])
        inp: Dict = {
            "prompt":           prompt,
            "num_outputs":      1,
            "output_format":    "webp",
            "output_quality":   90,
            "num_inference_steps": steps,
        }
        if "flux" in model:
            inp["width"] = min(w, 1440)
            inp["height"] = min(h, 1440)
        if seed > 0:
            inp["seed"] = seed

        output = self._client.run(model, input=inp)
        url    = str(output[0]) if isinstance(output, (list, tuple)) else str(output)
        path   = self._download_output(url, "gen")
        return GenerationResult(success=True, backend="replicate", model=model,
                                prompt=prompt, output_path=path, output_url=url,
                                width=w, height=h, time_s=round(time.time()-start, 2))

    def _replicate_upscale(self, image_path: str, start: float) -> GenerationResult:
        model = self.MODELS["replicate"]["upscale"]
        with open(image_path, "rb") as f:
            output = self._client.run(model, input={"image": f, "scale": 4})
        url  = str(output[0]) if isinstance(output, (list, tuple)) else str(output)
        path = self._download_output(url, "upscale")
        return GenerationResult(success=True, backend="replicate", model=model,
                                prompt="upscale 4x", output_path=path, output_url=url,
                                time_s=round(time.time()-start, 2))

    def _replicate_img2img(self, image_path: str, instructions: str, start: float) -> GenerationResult:
        model = self.MODELS["replicate"]["img2img"]
        with open(image_path, "rb") as f:
            output = self._client.run(model, input={
                "prompt": instructions,
                "image":  f,
                "num_outputs": 1,
                "image_guidance_scale": 1.5,
                "guidance_scale": 7.5,
            })
        url  = str(output[0]) if isinstance(output, (list, tuple)) else str(output)
        path = self._download_output(url, "alter")
        return GenerationResult(success=True, backend="replicate", model=model,
                                prompt=instructions, output_path=path, output_url=url,
                                time_s=round(time.time()-start, 2))

    # ── Together backend ────────────────────────────────────────────────────────

    def _together_generate(self, prompt: str, w: int, h: int,
                           steps: int, seed: int, start: float) -> GenerationResult:
        model  = self.MODELS["together"]["flux"]
        resp   = self._client.Image.create(
            prompt=prompt, model=model,
            width=min(w, 1024), height=min(h, 1024),
            steps=steps, n=1,
        )
        url  = resp.data[0].url
        path = self._download_output(url, "gen")
        return GenerationResult(success=True, backend="together", model=model,
                                prompt=prompt, output_path=path, output_url=url,
                                width=w, height=h, time_s=round(time.time()-start, 2))

    # ── Utilities ──────────────────────────────────────────────────────────────

    def _enhance_prompt(self, prompt: str) -> str:
        if len(prompt) < 100:
            return prompt + ", highly detailed, professional quality, sharp focus, 4k resolution"
        return prompt

    def _parse_aspect(self, ar: str) -> tuple:
        ratios = {"16:9": (1344, 768), "9:16": (768, 1344), "1:1": (1024, 1024),
                  "4:3": (1152, 864), "3:4": (864, 1152), "21:9": (1536, 640)}
        return ratios.get(ar, (1024, 1024))

    def _download_output(self, url: str, prefix: str) -> Optional[str]:
        try:
            fname = f"{prefix}_{int(time.time())}.webp"
            path  = os.path.join(self.save_dir, fname)
            urllib.request.urlretrieve(url, path)
            return path
        except Exception:
            return None

    def _demo_result(self, prompt: str, w: int, h: int) -> GenerationResult:
        return GenerationResult(
            success=True, backend="demo", model="demo",
            prompt=prompt, output_path=None, output_url=None,
            width=w, height=h, time_s=0.0,
            metadata={"note": "Demo mode — set REPLICATE_API_TOKEN to generate real images"},
        )

    def format_result(self, r: GenerationResult) -> str:
        if not r.success:
            return f"GENERATION FAILED: {r.error}"
        lines = [
            f"Backend:  {r.backend} | Model: {r.model}",
            f"Prompt:   {r.prompt[:80]}...",
            f"Size:     {r.width}×{r.height}",
            f"Time:     {r.time_s}s",
        ]
        if r.output_path: lines.append(f"Saved:    {r.output_path}")
        if r.output_url:  lines.append(f"URL:      {r.output_url}")
        if r.backend == "demo": lines.append("NOTE: Demo mode — no real image generated")
        return "\n".join(lines)
