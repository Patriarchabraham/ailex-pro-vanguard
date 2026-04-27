"""
AILEX Prompt Master — CLI entry point.

Usage:
  python -m ailex_pilot.prompt_master_cli craft "fix broken login" --domain software_engineering
  python -m ailex_pilot.prompt_master_cli synthesise "why does consciousness exist" --domain philosophy
  python -m ailex_pilot.prompt_master_cli harness --task reasoning --complexity 0.9
  python -m ailex_pilot.prompt_master_cli ontology --domain mathematics
  python -m ailex_pilot.prompt_master_cli terminology --domain prompt_engineering
"""
from __future__ import annotations

import os
import sys
import argparse

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from ailex_pilot.prompt_master import (
    PromptArchitect, OmniscientSynthesiser, HarnessEngineer,
    ContextEngineer, DOMAIN_ONTOLOGY, DOMAIN_TERMINOLOGY,
)

try:
    from rich.console import Console
    from rich.panel   import Panel
    RICH = True
except ImportError:
    RICH = False


def main() -> int:
    parser = argparse.ArgumentParser(description="AILEX Prompt Master")
    sub    = parser.add_subparsers(dest="command", required=True)

    p_craft = sub.add_parser("craft", help="Craft optimal prompt")
    p_craft.add_argument("request")
    p_craft.add_argument("--domain",     default="software_engineering")
    p_craft.add_argument("--task",       default="analytical")
    p_craft.add_argument("--complexity", type=float, default=0.5)
    p_craft.add_argument("--technique",  default=None)
    p_craft.add_argument("--json",       action="store_true")

    p_synth = sub.add_parser("synthesise", help="Omniscient cross-domain synthesis")
    p_synth.add_argument("request")
    p_synth.add_argument("--domain", default="software_engineering")

    p_harn = sub.add_parser("harness", help="Generate harness config")
    p_harn.add_argument("--task",       default="analytical")
    p_harn.add_argument("--domain",     default="software_engineering")
    p_harn.add_argument("--complexity", type=float, default=0.5)

    p_onto = sub.add_parser("ontology", help="Show domain ontology")
    p_onto.add_argument("--domain", default="software_engineering")

    p_term = sub.add_parser("terminology", help="Show domain terminology")
    p_term.add_argument("--domain", default="prompt_engineering")

    p_list = sub.add_parser("domains", help="List all available domains")

    args = parser.parse_args()

    try:
        import anthropic
        client = anthropic.Anthropic()
    except ImportError:
        client = None

    console = Console() if RICH else None
    def out(text: str, title: str = "") -> None:
        if RICH and console:
            console.print(Panel(text, title=title) if title else text)
        else:
            if title: print(f"\n{'─'*60}\n{title}\n{'─'*60}")
            print(text)

    if args.command == "craft":
        arch   = PromptArchitect(client)
        prompt = arch.craft(
            args.request, args.domain, args.task,
            args.complexity, require_json=args.json,
            technique=args.technique,
        )
        out(arch.format(prompt), f"Prompt | {args.domain} | {prompt.technique}")

    elif args.command == "synthesise":
        synth  = OmniscientSynthesiser(client)
        result = synth.synthesise(args.request, args.domain)
        out(synth.format(result), "Omniscient Synthesis")

    elif args.command == "harness":
        eng    = HarnessEngineer()
        cfg    = eng.configure(args.task, args.domain, args.complexity)
        lines  = [
            f"Model:           {cfg.model}",
            f"Temperature:     {cfg.temperature}",
            f"Max tokens:      {cfg.max_tokens:,}",
            f"Thinking:        {cfg.use_thinking} (budget={cfg.thinking_budget:,})",
            f"Sampling:        {cfg.sampling_strategy}",
            f"Retry attempts:  {cfg.retry_attempts} (min_conf={cfg.retry_on_low_conf:.0%})",
            f"Tool use:        {cfg.use_tool_use}",
            f"Output format:   {cfg.output_format}",
            f"Est. cost:       ${cfg.estimated_cost_usd:.5f}",
            f"Guardrails:      {', '.join(cfg.guardrails)}",
        ]
        out("\n".join(lines), f"Harness Config | {args.task} | {args.domain}")

    elif args.command == "ontology":
        onto  = DOMAIN_ONTOLOGY.get(args.domain, {})
        if not onto:
            out(f"No ontology for domain: {args.domain}")
            out(f"Available: {', '.join(DOMAIN_ONTOLOGY)}")
            return 1
        lines = [f"Ontology: {args.domain}\n"]
        for key, vals in onto.items():
            if isinstance(vals, list):
                lines.append(f"{key.upper()}:")
                for v in vals:
                    lines.append(f"  • {v}")
            lines.append("")
        out("\n".join(lines), f"Ontology: {args.domain}")

    elif args.command == "terminology":
        terms = DOMAIN_TERMINOLOGY.get(args.domain, {})
        if not terms:
            out(f"No terminology for: {args.domain}")
            out(f"Available: {', '.join(DOMAIN_TERMINOLOGY)}")
            return 1
        lines = [f"Terminology: {args.domain}\n"]
        for term, defn in terms.items():
            lines.append(f"  {term:25s} {defn}")
        out("\n".join(lines), f"Terminology: {args.domain}")

    elif args.command == "domains":
        out(
            "Ontology domains: " + ", ".join(DOMAIN_ONTOLOGY) + "\n"
            "Terminology domains: " + ", ".join(DOMAIN_TERMINOLOGY),
            "Available Domains"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
