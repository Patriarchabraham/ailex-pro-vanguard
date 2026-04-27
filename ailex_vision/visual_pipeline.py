"""
AILEX Vision — visual_pipeline.py
Orchestrates: WebCapture + VisualAnalyzer + ClaudeDesign + ImageCraft + VideoCraft.

Main operations:
  analyze_website(url)              → full website visual analysis
  recreate_website(url)             → analyze + generate improved images
  design_website(url)               → analyze + Claude Design HTML redesign
  design_from_prompt(prompt, type)  → direct Claude Design generation
  generate_image(prompt)            → direct image generation
  generate_video(prompt)            → direct video generation
  alter_image(path, instr)          → edit existing image
  improve_image(path)               → upscale + enhance
  animate_image(path, prompt)       → image → video
  website_to_video(url)             → analyze website, generate video version
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .claude_design   import ClaudeDesign, DesignOutput
from .image_craft     import GenerationResult, ImageCraft
from .video_craft     import VideoResult, VideoCraft
from .visual_analyzer import VisualAnalysis, VisualAnalyzer
from .web_capture     import WebCapture, WebSnapshot


@dataclass
class VisualReport:
    url:           Optional[str]
    snapshot:      Optional[WebSnapshot]
    analysis:      Optional[VisualAnalysis]
    generations:   List[GenerationResult] = field(default_factory=list)
    videos:        List[VideoResult]      = field(default_factory=list)
    designs:       List[DesignOutput]     = field(default_factory=list)
    summary:       str = ""
    error:         Optional[str] = None


class VisualPipeline:
    def __init__(
        self,
        replicate_key: Optional[str] = None,
        anthropic_key: Optional[str] = None,
        image_backend: str = "replicate",
        quality_mode:  bool = False,
        save_dir:      str = "/data/data/com.termux/files/home/ailex_vision",
    ):
        self.capture  = WebCapture(save_dir=os.path.join(save_dir, "captures"))
        self.analyzer = VisualAnalyzer(api_key=anthropic_key)
        self.designer = ClaudeDesign(api_key=anthropic_key,
                                     save_dir=os.path.join(save_dir, "designs"))
        self.imager   = ImageCraft(backend=image_backend, api_key=replicate_key,
                                   save_dir=os.path.join(save_dir, "generated"),
                                   quality_mode=quality_mode)
        self.video    = VideoCraft(replicate_key=replicate_key,
                                  save_dir=os.path.join(save_dir, "videos"))

    # ── Website operations ────────────────────────────────────────────────────

    def analyze_website(self, url: str) -> VisualReport:
        """Fetch + analyze any website. Returns full visual breakdown."""
        snap     = self.capture.capture(url)
        analysis = self.analyzer.analyze_website(snap)
        return VisualReport(
            url=url, snapshot=snap, analysis=analysis,
            summary=self._website_summary(snap, analysis),
        )

    def design_website(self, url: str, output_type: str = "html") -> VisualReport:
        """Analyze website + generate improved Claude Design version."""
        report = self.analyze_website(url)
        if report.error or not report.snapshot:
            return report
        design = self.designer.from_website(report.snapshot)
        report.designs.append(design)
        report.summary = f"{report.summary} | Claude Design: {design.saved_path}"
        return report

    def design_from_prompt(self, prompt: str, output_type: str = "html",
                            image_path: Optional[str] = None) -> DesignOutput:
        """Generate any design type directly from a prompt."""
        return self.designer.generate(prompt, output_type, image_path=image_path)

    def recreate_website(self, url: str, n_images: int = 3,
                          improved: bool = True) -> VisualReport:
        """Analyze website + generate improved/recreated images."""
        report = self.analyze_website(url)
        if report.error or not report.analysis:
            return report

        a = report.analysis
        prompts = [
            a.improvement_prompt if improved else a.recreation_prompt,
            a.improvement_prompt + ", hero section, full page layout",
            a.recreation_prompt  + ", mobile version, responsive design",
        ]

        for prompt in prompts[:n_images]:
            w, h = self.imager._parse_aspect(a.aspect_ratio)
            result = self.imager.generate(prompt, width=w, height=h)
            report.generations.append(result)

        report.summary = self._generation_summary(report)
        return report

    def website_to_video(self, url: str) -> VisualReport:
        """Analyze website + generate a video demo/promo for it."""
        report = self.analyze_website(url)
        if report.error or not report.analysis:
            return report

        video_prompt = self.video.generate_video_prompt(report.analysis)
        result       = self.video.generate(video_prompt, duration=5)
        report.videos.append(result)
        return report

    # ── Direct image operations ───────────────────────────────────────────────

    def generate_image(
        self,
        prompt:   str,
        negative: str = "blurry, low quality, distorted",
        width:    int = 1024,
        height:   int = 1024,
        style:    str = "",
    ) -> GenerationResult:
        """Generate a new image from a text prompt."""
        full_prompt = f"{prompt}, {style}" if style else prompt
        return self.imager.generate(full_prompt, negative, width, height)

    def improve_image(self, path: str) -> GenerationResult:
        """Upscale and enhance an existing image."""
        return self.imager.improve(path)

    def alter_image(self, path: str, instructions: str) -> GenerationResult:
        """Modify an image using text instructions."""
        return self.imager.alter(path, instructions)

    def analyze_and_improve(self, path: str) -> tuple:
        """Analyze an image with Claude Vision, then generate an improved version."""
        analysis = self.analyzer.analyze_image_file(path)
        result   = self.imager.recreate_from_analysis(analysis, improved=True)
        return analysis, result

    # ── Video operations ─────────────────────────────────────────────────────

    def generate_video(self, prompt: str, duration: int = 5,
                        model: str = "wan_t2v") -> VideoResult:
        """Generate a video from a text prompt."""
        return self.video.generate(prompt, duration=duration, model=model)

    def animate_image(self, image_path: str, prompt: str = "",
                      duration: int = 5) -> VideoResult:
        """Turn a still image into a video."""
        return self.video.from_image(image_path, prompt, duration)

    def website_frames_to_video(self, url: str) -> VideoResult:
        """Download website images and compile them into a slideshow video."""
        snap = self.capture.capture(url)
        downloaded = [img.local for img in snap.images if img.local][:10]
        if not downloaded:
            return VideoResult(success=False, backend="ffmpeg", model="",
                               prompt="", output_path=None, output_url=None,
                               error="No images downloaded from website")
        # Use the best image to animate
        best = max(downloaded, key=lambda p: os.path.getsize(p))
        return self.animate_image(best, f"website showcase for {snap.title}")

    # ── Formatted output ──────────────────────────────────────────────────────

    def format_report(self, report: VisualReport) -> str:
        lines = []
        sep = "─" * 70

        if report.snapshot:
            s = report.snapshot
            lines += [
                "AILEX VISION — WEBSITE ANALYSIS",
                sep,
                f"URL:         {s.url}",
                f"Title:       {s.title}",
                f"Description: {s.description[:100]}",
                f"Tech stack:  {', '.join(s.tech_stack) or 'unknown'}",
                f"Images:      {len(s.images)} ({sum(1 for i in s.images if i.local)} downloaded)",
                f"Videos:      {len(s.videos)}",
                f"Fonts:       {', '.join(s.fonts[:4]) or 'none'}",
                f"Colors:      {', '.join(s.colors[:6]) or 'none'}",
                f"Layout:      {', '.join(s.layout_hints) or 'unknown'}",
                f"Load time:   {s.fetch_time_s}s",
            ]

        if report.analysis:
            a = report.analysis
            lines += [
                sep,
                "VISUAL ANALYSIS",
                f"  Description:  {a.description[:120]}",
                f"  Style:        {a.style}",
                f"  Mood:         {a.dominant_mood}",
                f"  Colors:       {', '.join(a.colors[:6])}",
                f"  Composition:  {a.composition[:100]}",
                f"  Issues:       {'; '.join(a.issues[:3])}",
                f"  Strengths:    {'; '.join(a.strengths[:3])}",
                f"  Style tags:   {', '.join(a.style_tags[:6])}",
            ]

        if report.designs:
            lines += [sep, "CLAUDE DESIGN OUTPUT"]
            for i, d in enumerate(report.designs, 1):
                lines.append(f"  [{i}] {d.type.upper()} | {d.title[:50]}")
                if d.saved_path: lines.append(f"      Saved: {d.saved_path}")
                if d.error:      lines.append(f"      Error: {d.error}")

        if report.generations:
            lines += [sep, "GENERATED IMAGES"]
            for i, g in enumerate(report.generations, 1):
                lines.append(f"  [{i}] {self.imager.format_result(g)}")

        if report.videos:
            lines += [sep, "GENERATED VIDEOS"]
            for i, v in enumerate(report.videos, 1):
                lines.append(f"  [{i}] {self.video.format_result(v)}")

        if report.error:
            lines += [sep, f"ERROR: {report.error}"]

        lines.append(sep)
        return "\n".join(lines)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _website_summary(self, snap: WebSnapshot, analysis: VisualAnalysis) -> str:
        return (
            f"{snap.title} ({snap.url}) — "
            f"{analysis.style}, {analysis.dominant_mood} mood, "
            f"{len(snap.images)} images, tech: {', '.join(snap.tech_stack) or 'unknown'}"
        )

    def _generation_summary(self, report: VisualReport) -> str:
        base = report.summary
        gens = [g for g in report.generations if g.success]
        paths = [g.output_path for g in gens if g.output_path]
        return f"{base} | Generated {len(gens)} images: {', '.join(paths)}"
