"""
AILEX Vision — cli.py
Rich CLI for all visual operations.

Commands:
  analyze   <url>                   — full website visual analysis
  recreate  <url> [--n N]           — analyze + generate improved images
  design    <url or prompt>         — Claude Design: generate/redesign HTML/CSS/React/SVG
  generate  <prompt>                — generate image from text (Flux)
  video     <prompt>                — generate video from text (Wan 2.1)
  alter     <path> <instructions>   — edit existing image
  improve   <path>                  — upscale + enhance image 4x
  animate   <path> [--prompt TEXT]  — animate still image to video
  web2vid   <url>                   — website → video promo
  critique  <path or url>           — Claude Design critique
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    from rich.console import Console
    from rich.panel   import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH = True
except ImportError:
    RICH = False

from .visual_pipeline import VisualPipeline


def _load_env() -> None:
    for env_path in [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        os.path.expanduser("~/.env"),
    ]:
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    _load_env()

    parser = argparse.ArgumentParser(
        description="AILEX Vision — Visual Intelligence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m ailex_vision.cli analyze  https://apple.com
  python -m ailex_vision.cli site     "Foundation for world peace" --pages 5
  python -m ailex_vision.cli site     https://example.com           # recreate as multipage
  python -m ailex_vision.cli recreate https://stripe.com --n 2
  python -m ailex_vision.cli generate "a futuristic city at sunset"
  python -m ailex_vision.cli video    "ocean waves at sunrise"
  python -m ailex_vision.cli alter    photo.jpg "make the sky dramatic"
  python -m ailex_vision.cli improve  photo.jpg
  python -m ailex_vision.cli animate  design.png --prompt "parallax"
  python -m ailex_vision.cli web2vid  https://vercel.com

API Keys:
  REPLICATE_API_TOKEN  — image/video generation
  ANTHROPIC_API_KEY    — visual analysis + Claude Design + site generation
        """,
    )

    parser.add_argument("command", choices=["analyze","recreate","design","generate",
                                             "video","alter","improve","animate",
                                             "web2vid","critique","site"])
    parser.add_argument("target", help="URL, file path, or text prompt")
    parser.add_argument("extra",  nargs="?", default="",
                        help="Extra argument (instructions for alter, prompt for animate)")
    parser.add_argument("--n",        type=int, default=2,    help="Number of images")
    parser.add_argument("--pages",    type=int, default=0,    help="Number of pages for site generation (0=auto)")
    parser.add_argument("--duration", type=int, default=5,    help="Video duration seconds")
    parser.add_argument("--width",    type=int, default=1024, help="Image width")
    parser.add_argument("--height",   type=int, default=1024, help="Image height")
    parser.add_argument("--quality",  action="store_true",    help="Use quality model (Flux Dev)")
    parser.add_argument("--type",     default="html",
                        choices=["html","react","svg","css","design_system",
                                 "wireframe","slide","pitch_deck"],
                        help="Claude Design output type")
    parser.add_argument("--backend",  default="replicate",
                        choices=["replicate","stability","together","demo"])

    args = parser.parse_args()

    pipeline = VisualPipeline(
        replicate_key = os.getenv("REPLICATE_API_TOKEN"),
        anthropic_key = os.getenv("ANTHROPIC_API_KEY"),
        image_backend = args.backend,
        quality_mode  = args.quality,
    )

    if RICH:
        console = Console()
        mode = "REAL" if (os.getenv("REPLICATE_API_TOKEN") or os.getenv("ANTHROPIC_API_KEY")) else "DEMO"
        console.rule(f"[bold]AILEX VISION[/bold]  [{mode}]  {args.command.upper()}: {args.target[:60]}")

    def run_with_spinner(label: str, fn, *a, **kw):
        if RICH:
            c = Console()
            with Progress(SpinnerColumn(), TextColumn(label), console=c, transient=True) as p:
                p.add_task("", total=None)
                return fn(*a, **kw)
        else:
            print(f"{label}...")
            return fn(*a, **kw)

    # ── Dispatch ──────────────────────────────────────────────────────────────

    if args.command == "site":
        from ailex_vision.site_architect import SiteArchitect
        import anthropic as _anthro
        client = _anthro.Anthropic() if os.getenv("ANTHROPIC_API_KEY") else None
        arch   = SiteArchitect(client=client)

        if args.target.startswith("http") or args.target.startswith("www"):
            # Recreate existing site as multipage
            snap   = run_with_spinner(f"Capturing {args.target}...",
                                       pipeline.capture.capture, args.target)
            img_map = {img.url.split("/")[-1]: img.url
                       for img in snap.images if img.url}
            site   = run_with_spinner(f"Generating multipage site...",
                                       arch.generate_site,
                                       snap.title or args.target,
                                       snap, img_map)
        else:
            site = run_with_spinner(f"Generating site: {args.target[:50]}...",
                                     arch.generate_site, args.target)
        output = arch.format_result(site)

    elif args.command == "design":
        # If target looks like a URL → redesign website; else → generate from prompt
        if args.target.startswith("http") or args.target.startswith("www"):
            report = run_with_spinner(f"Designing {args.target}...",
                                      pipeline.design_website, args.target, args.type)
            output = pipeline.format_report(report)
        else:
            result = run_with_spinner(f"Claude Design: {args.target[:50]}...",
                                      pipeline.design_from_prompt, args.target, args.type)
            output = pipeline.designer.format_output(result)

    elif args.command == "critique":
        if args.target.startswith("http"):
            # Critique from URL — analyze first, then critique
            snap   = run_with_spinner(f"Fetching {args.target}...",
                                       pipeline.capture.capture, args.target)
            imgs   = [i.local for i in snap.images if i.local]
            result = run_with_spinner("Critiquing...",
                                      pipeline.designer.critique,
                                      image_path=imgs[0] if imgs else None,
                                      description=snap.title)
        elif os.path.exists(args.target):
            result = run_with_spinner(f"Critiquing {args.target}...",
                                      pipeline.designer.critique,
                                      image_path=args.target)
        else:
            result = run_with_spinner("Critiquing...",
                                      pipeline.designer.critique,
                                      html=args.target)
        output = pipeline.designer.format_output(result)

    elif args.command == "analyze":
        report = run_with_spinner(f"Analyzing {args.target}...", pipeline.analyze_website, args.target)
        output = pipeline.format_report(report)

    elif args.command == "recreate":
        report = run_with_spinner(f"Recreating {args.target}...",
                                   pipeline.recreate_website, args.target, args.n)
        output = pipeline.format_report(report)

    elif args.command == "generate":
        result = run_with_spinner(f"Generating: {args.target[:50]}...",
                                   pipeline.generate_image, args.target,
                                   width=args.width, height=args.height)
        output = pipeline.imager.format_result(result)

    elif args.command == "video":
        result = run_with_spinner(f"Generating video: {args.target[:50]}...",
                                   pipeline.generate_video, args.target, args.duration)
        output = pipeline.video.format_result(result)

    elif args.command == "alter":
        if not args.extra:
            print("alter requires instructions: ailex_vision alter <path> '<instructions>'")
            return 1
        result = run_with_spinner(f"Altering {args.target}...",
                                   pipeline.alter_image, args.target, args.extra)
        output = pipeline.imager.format_result(result)

    elif args.command == "improve":
        result = run_with_spinner(f"Improving {args.target}...",
                                   pipeline.improve_image, args.target)
        output = pipeline.imager.format_result(result)

    elif args.command == "animate":
        result = run_with_spinner(f"Animating {args.target}...",
                                   pipeline.animate_image, args.target,
                                   args.extra, args.duration)
        output = pipeline.video.format_result(result)

    elif args.command == "web2vid":
        report = run_with_spinner(f"Generating video for {args.target}...",
                                   pipeline.website_to_video, args.target)
        output = pipeline.format_report(report)

    else:
        return 1

    if RICH:
        Console().print(Panel(output, title=f"[bold]{args.command.upper()}[/bold] result",
                              border_style="cyan"))
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
