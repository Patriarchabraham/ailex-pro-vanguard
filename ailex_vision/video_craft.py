"""
AILEX Vision — video_craft.py
Generate and process videos via Replicate + ffmpeg frame processing.

Supported models (Replicate):
  - Wan 2.1 T2V 480p  — text-to-video, fast
  - LTX Video         — high quality text/image-to-video
  - Stable Video Diffusion — image-to-video
  - MiniMax Video 01  — high quality, longer clips

Video operations:
  - generate(prompt)              → generate from text
  - from_image(path, prompt)      → animate a still image
  - extract_frames(video_path)    → break into frames for analysis
  - describe_video(frames)        → Claude describes video content
  - improve_video(path)           → enhance quality of existing video
"""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class VideoResult:
    success:     bool
    backend:     str
    model:       str
    prompt:      str
    output_path: Optional[str]
    output_url:  Optional[str]
    duration_s:  float = 5.0
    fps:         int   = 24
    resolution:  str   = "720p"
    time_s:      float = 0.0
    frames:      List[str] = field(default_factory=list)
    error:       Optional[str] = None
    metadata:    Dict[str, Any] = field(default_factory=dict)


class VideoCraft:
    """Multi-backend video generation and frame processing."""

    MODELS = {
        "wan_t2v":   "wan-video/wan2.1-t2v-480p",
        "wan_i2v":   "wan-video/wan2.1-i2v-480p",
        "ltx":       "lightricks/ltx-video",
        "svd":       "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
        "minimax":   "minimax/video-01",
    }

    def __init__(self, replicate_key: Optional[str] = None,
                 save_dir: str = "/data/data/com.termux/files/home/ailex_vision/videos"):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        self._client    = None
        self._available = False
        key = replicate_key or os.getenv("REPLICATE_API_TOKEN", "")
        if key:
            try:
                import replicate
                os.environ["REPLICATE_API_TOKEN"] = key
                self._client    = replicate
                self._available = True
            except ImportError:
                pass

    # ── Text-to-video ─────────────────────────────────────────────────────────

    def generate(
        self,
        prompt:   str,
        duration: int = 5,
        model:    str = "wan_t2v",
        resolution: str = "480p",
    ) -> VideoResult:
        """Generate video from text prompt."""
        start = time.time()
        if not self._available:
            return self._demo("generate", prompt, duration)

        model_id = self.MODELS.get(model, self.MODELS["wan_t2v"])
        inp = {
            "prompt":          self._enhance_video_prompt(prompt),
            "num_frames":      duration * 24,
            "fps":             24,
        }
        if "wan" in model_id:
            inp["aspect_ratio"] = "16:9"
        if "ltx" in model_id:
            inp["duration"]  = duration
            inp["frame_rate"] = 24

        try:
            output = self._client.run(model_id, input=inp)
            url    = str(output) if isinstance(output, str) else str(list(output)[0])
            path   = self._download_video(url, "gen")
            return VideoResult(success=True, backend="replicate", model=model_id,
                               prompt=prompt, output_path=path, output_url=url,
                               duration_s=duration, fps=24, resolution=resolution,
                               time_s=round(time.time()-start, 2))
        except Exception as e:
            return VideoResult(success=False, backend="replicate", model=model_id,
                               prompt=prompt, output_path=None, output_url=None,
                               error=str(e), time_s=round(time.time()-start, 2))

    # ── Image-to-video ────────────────────────────────────────────────────────

    def from_image(self, image_path: str, prompt: str = "", duration: int = 5) -> VideoResult:
        """Animate a still image into a video."""
        if not os.path.exists(image_path):
            return VideoResult(success=False, backend="replicate", model="svd",
                               prompt=prompt, output_path=None, output_url=None,
                               error=f"File not found: {image_path}")
        if not self._available:
            return self._demo("image-to-video", prompt or "animate image", duration)

        start    = time.time()
        model_id = self.MODELS["wan_i2v"] if prompt else self.MODELS["svd"]
        try:
            with open(image_path, "rb") as f:
                inp = {"image": f, "num_frames": duration * 24, "fps": 24}
                if prompt:
                    inp["prompt"] = self._enhance_video_prompt(prompt)
                output = self._client.run(model_id, input=inp)
            url  = str(output) if isinstance(output, str) else str(list(output)[0])
            path = self._download_video(url, "i2v")
            return VideoResult(success=True, backend="replicate", model=model_id,
                               prompt=prompt, output_path=path, output_url=url,
                               duration_s=duration, time_s=round(time.time()-start, 2))
        except Exception as e:
            return VideoResult(success=False, backend="replicate", model=model_id,
                               prompt=prompt, output_path=None, output_url=None,
                               error=str(e), time_s=round(time.time()-start, 2))

    # ── Frame extraction ──────────────────────────────────────────────────────

    def extract_frames(
        self, video_path: str, fps: int = 2, max_frames: int = 30
    ) -> List[str]:
        """Extract frames from a video file using ffmpeg."""
        if not os.path.exists(video_path):
            return []
        frames_dir = os.path.join(self.save_dir, "frames", str(int(time.time())))
        os.makedirs(frames_dir, exist_ok=True)
        output_pattern = os.path.join(frames_dir, "frame_%04d.jpg")
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"fps={fps}",
            "-vframes", str(max_frames),
            "-q:v", "2",
            output_pattern, "-y", "-loglevel", "error",
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            frames = sorted([
                os.path.join(frames_dir, f)
                for f in os.listdir(frames_dir)
                if f.endswith(".jpg")
            ])
            return frames
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    def describe_video(self, frames: List[str], analyzer: Any = None) -> str:
        """Use Claude Vision to describe video content from key frames."""
        if not frames or analyzer is None or not analyzer.available:
            return f"[DEMO] Video has {len(frames)} extracted frames"

        key_frames = frames[::max(1, len(frames)//4)][:4]
        descriptions = []
        for i, frame in enumerate(key_frames):
            analysis = analyzer.analyze_image_file(frame)
            descriptions.append(f"Frame {i+1}: {analysis.description}")

        return "\n".join(descriptions)

    def get_video_info(self, video_path: str) -> Dict:
        """Get video metadata using ffprobe."""
        if not os.path.exists(video_path):
            return {"error": "file not found"}
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_streams", "-show_format", video_path],
                capture_output=True, text=True
            )
            import json
            return json.loads(result.stdout)
        except Exception as e:
            return {"error": str(e)}

    def frames_to_video(
        self, frame_dir: str, output_path: str, fps: int = 24
    ) -> VideoResult:
        """Reassemble frames into a video file."""
        start   = time.time()
        pattern = os.path.join(frame_dir, "frame_%04d.jpg")
        cmd = [
            "ffmpeg", "-framerate", str(fps),
            "-i", pattern, "-c:v", "libx264",
            "-pix_fmt", "yuv420p", output_path, "-y", "-loglevel", "error"
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return VideoResult(success=True, backend="ffmpeg", model="libx264",
                               prompt="reassemble frames", output_path=output_path,
                               output_url=None, fps=fps, time_s=round(time.time()-start, 2))
        except Exception as e:
            return VideoResult(success=False, backend="ffmpeg", model="libx264",
                               prompt="", output_path=None, output_url=None,
                               error=str(e))

    # ── Prompt generation for video services ─────────────────────────────────

    def generate_video_prompt(self, analysis: Any) -> str:
        """Generate an optimized video prompt from a VisualAnalysis."""
        base = analysis.recreation_prompt or analysis.description
        additions = [
            "cinematic camera movement",
            "smooth motion",
            "professional cinematography",
            f"mood: {analysis.dominant_mood}",
            "4k quality",
        ]
        if "website" in analysis.estimated_type.lower():
            additions = ["UI/UX demo video", "smooth scrolling animation",
                         "professional screen recording style", "clean transitions"]
        return f"{base}, {', '.join(additions)}"

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _enhance_video_prompt(self, prompt: str) -> str:
        if len(prompt) < 80:
            return prompt + ", cinematic, smooth motion, professional, high quality, 4k"
        return prompt

    def _download_video(self, url: str, prefix: str) -> Optional[str]:
        import urllib.request
        try:
            ext  = "mp4"
            if ".webm" in url: ext = "webm"
            fname = f"{prefix}_{int(time.time())}.{ext}"
            path  = os.path.join(self.save_dir, fname)
            urllib.request.urlretrieve(url, path)
            return path
        except Exception:
            return None

    def _demo(self, op: str, prompt: str, duration: int) -> VideoResult:
        return VideoResult(
            success=True, backend="demo", model="demo",
            prompt=prompt, output_path=None, output_url=None,
            duration_s=duration, time_s=0.0,
            metadata={"note": f"Demo mode ({op}) — set REPLICATE_API_TOKEN to generate real video"},
        )

    def format_result(self, r: VideoResult) -> str:
        if not r.success:
            return f"VIDEO GENERATION FAILED: {r.error}"
        lines = [
            f"Backend:   {r.backend} | Model: {r.model}",
            f"Prompt:    {r.prompt[:80]}",
            f"Duration:  {r.duration_s}s @ {r.fps}fps | {r.resolution}",
            f"Time:      {r.time_s}s",
        ]
        if r.output_path: lines.append(f"Saved:     {r.output_path}")
        if r.output_url:  lines.append(f"URL:       {r.output_url}")
        if r.backend == "demo": lines.append("NOTE: Demo mode — no real video generated")
        return "\n".join(lines)
