# AILEX Pro Vanguard

> **The most advanced AI engineering platform** — 119 specialized agents, multi-wave orchestration, full-stack generation with zero-bug guarantees, and live academic knowledge.

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![Agents](https://img.shields.io/badge/Agents-119-purple)](./ailex_pilot)
[![Tests](https://img.shields.io/badge/Tests-168_passing-green)](./tests)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## What is AILEX Pro Vanguard?

AILEX is an autonomous AI platform for complete software engineering, web generation, and product creation. It combines:

- **119 specialized agents** in dynamic multi-wave orchestration
- **Guaranteed quality** via 27 automated QA checks and a 10-rule zero-bug constitution  
- **Full-stack generation** — websites (12 types, 20 visual libraries) + backends (FastAPI/Express/Django)
- **Live knowledge** — 482+ academic papers across 16 domains, auto-updated every 6h
- **BMAD integration** — 4-phase agile lifecycle (Analysis → Planning → Solutioning → Implementation)
- **Complete observability** — traces, metrics, logs, health checks on 15 subsystems

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   AILEX Pro Vanguard                    │
├─────────────────┬─────────────────┬─────────────────────┤
│   INTELLIGENCE  │  ORCHESTRATION  │    GENERATION       │
│                 │                 │                     │
│  119 agents     │  WaveOrch.      │  12 site types      │
│  19 core        │  13 domains     │  3 backend fw       │
│  100 MultiWave  │  MultiWave      │  20 visual libs     │
│  (8 tiers)      │  100 agents     │  27 QA checks       │
├─────────────────┴─────────────────┴─────────────────────┤
│               PIPELINE v2 (9 stages)                    │
│  Trace → Cache → KB Context → Call → QualityGate       │
│       → Log → Metrics → Store → Return                 │
├─────────────────────────────────────────────────────────┤
│            AIOX MAXIMIZER (14 bridges)                  │
│  SecurityScanner · RecursiveImprovement · Swarm        │
│  GSD2 · TDDLoop · CodeQualityGate · KnowledgeSynth     │
├─────────────────────────────────────────────────────────┤
│              BMAD × AILEX v2 (4 phases)                 │
│  MARY(2026 LLM) · JOHN · WINSTON(MultiWave)            │
│  AMELIA(BackendGen+Security) · BOB · SALLY · BARRY     │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Activate all AILEX systems (background)
python ailex_activate.py

# Or block until complete
python ailex_activate.py --now

# Live dashboard
python ailex_activate.py --dash

# Health check (15 subsystems)
python ailex_activate.py --health
```

---

## Core Usage

### 1. Wave Orchestration
```python
from ailex_pilot.wave_orchestrator import wave_run

# 13 domain-specific wave configs
result = wave_run("Build JWT auth microservice", "backend")
print(result.wave_by_wave_summary())
# Wave 1: RESEARCH → Wave 2: ARCHITECTURE → Wave 3: DATABASE
# → Wave 4: IMPLEMENTATION → Wave 5: SECURITY → ORION synthesis
```

### 2. MultiWave Performer — 100 Specialized Agents
```python
from ailex_pilot.multiwave_performer import mwp_run

result = mwp_run("Design real-time collaborative editor with AI", max_agents=30)
print(result.executive_summary())
# Auto-selects: REALTIME_ENG, RAG_PRO, THREE_MASTER, TDD_MASTER...
# Groups into tier waves, context chains, ORION synthesizes
```

### 3. BMAD 4-Phase Lifecycle
```python
from ailex_pilot.bmad_integration import bmad_run

project = bmad_run("Build payment gateway with Stripe")
print(project.prd)           # Phase 2: JOHN's PRD
print(project.architecture)  # Phase 3: WINSTON + MultiWave analysis
print(project.implementation_report)  # Phase 4: AMELIA's generated code
```

### 4. Backend Generation (BASTIAN agent)
```python
from ailex_pilot.backend_generator import bastian_generate

project = bastian_generate("fastapi", "user-service",
                            output="~/projects/user-service")
# Generates 25 files: JWT auth + PostgreSQL + Redis + Docker + CI/CD + tests
```

### 5. Website Generation
```python
from ailex_vision.ultra_motion_system import UltraMotionSystem
from ailex_vision.site_factory import SiteFactory

factory = SiteFactory()
spec    = factory.get_spec("luxury_dating")  # 10 required pages defined
ums     = UltraMotionSystem()
html    = ums.inject(html, "luxury_dating")
# Injects: Three.js WebGL + GSAP + Lenis + Tailwind + D3 + anime.js
#          + tsParticles + Typed.js + Chart.js + Swiper + VANTA + 8 more
```

### 6. MARY — Research with 2026 LLM Knowledge
```python
from ailex_pilot.mary_2026 import enrich_mary, mary_compare_models

# Inject 2026 context into any MARY call
context = enrich_mary("Build a RAG system for document search")
# → Claude 4 capabilities, RAG techniques, benchmark comparisons

# Model recommendations
mary_compare_models("real-time data pipeline")
# → DeepSeek V3 for math/data, Claude 4 Sonnet for agents...
```

### 7. AIoX Maximizer — All Modules
```python
from ailex_pilot.aiox_maximizer import aiox_run

result = aiox_run("Secure REST API with rate limiting", "backend", mode="maximum")
# Activates: SecurityScanner + RecursiveImprovement + SwarmIntelligence
#          + GSD2 + TDDLoop + CodeQualityGate + KnowledgeSynthesis + more
print(result.full_report())
```

---

## Agent Registry (119 total)

### Core Agents (19) — in MODEL_ROUTING + Pipeline v2
| Agent | Model | Role |
|---|---|---|
| DEX | Opus 4.7 | React/TypeScript |
| ARIA | Opus 4.7 | Software Architect |
| BASTIAN | Opus 4.7 | Backend Engineering |
| ORION | Sonnet 4.6 | Meta-synthesis |
| MARY | Sonnet 4.6 | Research + 2026 LLM knowledge |
| WINSTON | Opus 4.7 | BMAD Architect + MultiWave |
| AMELIA | Opus 4.7 | BMAD Developer + Code Gen |
| ... | ... | ... |

### MultiWave Performer — 100 Specialized Agents
```
Tier 1 Engineering (20): DEXTRA, NEXUM, GRAPHOS, PRISM, REDIS_PRO, DOCKER_K8S...
Tier 2 AI/ML (15):       VECTOR_AI, RAG_PRO, PROMPT_ENG, AGENT_ARCH, FINE_TUNE...
Tier 3 Security (10):    PENTEST_PRO, CRYPTO_PRO, AUTH_MASTER, ZERO_TRUST...
Tier 4 Performance (10): PROFILER, DB_OPT, BUNDLE_OPT, ALGO_OPT, CONCUR_ENG...
Tier 5 Domain (15):      FINTECH_ENG, HEALTH_IT, GAME_DEV, BLOCK_ENG...
Tier 6 Quality (10):     TDD_MASTER, E2E_MASTER, CHAOS_ENG, CODE_REV...
Tier 7 Creative (10):    THREE_MASTER, GLSL_MASTER, D3_MASTER, MOTION_MASTER...
Tier 8 Strategy (10):    ENT_ARCH, SCALE_STRAT, TECH_LEAD, INNOV_STRAT...
```

---

## Module Map

```
ailex_pilot/                    ailex_vision/
├── ailex_core.py              ├── site_factory.py      (12 site types)
├── pipeline_v2.py             ├── ultra_motion_system.py (20 libs)
├── wave_orchestrator.py       ├── max_effects_system.py
├── multiwave_performer.py     ├── generation_guard.py
├── bmad_integration.py        ├── content_guard.py
├── mary_2026.py               ├── html_qa.py           (27 checks)
├── aiox_maximizer.py          ├── motion_system.py
├── backend_generator.py       ├── image_generator.py
├── observability.py           └── ...
├── pipeline_v2.py
├── smart_cache_v2.py
├── agent_quality_gate.py
├── knowledge_updater.py       tests/
├── web_researcher.py          ├── run_all.py
├── github_researcher.py       ├── test_*.py  (unit)
├── research_scheduler.py      ├── integration/
├── auto_improve.py            └── e2e/
└── ...81 total modules
```

---

## Quality System

### 27 HTML QA Checks
```python
from ailex_vision.html_qa import HTMLQualityAssurance, ensure_qa

# Auto-run before any deploy
@ensure_qa(auto_fix=True, block_on_critical=True)
def generate_page(brief): ...

# Score 100/100 = deployable. Any CRITICAL = blocked.
```

### Zero-Bug Constitution (10 rules)
| Rule | Prevents |
|---|---|
| B01 | Counters showing "0" (use real default values) |
| B02 | Hero elements invisible (opacity:0 in CSS → use JS failsafe) |
| B03 | Images 404 (ContentGuard verifies HTTP 200) |
| B04 | Missing sub-pages (all nav links must exist) |
| B05 | Mobile broken (viewport meta = CRITICAL) |
| B06 | Wrong image context (ContentGuard semantic categories) |
| B07 | Markdown fences visible in browser (auto-strip) |
| B08 | HTML truncated (auto-append `</html>`) |
| B09 | Rate limit silent failure (retry 0s/15s/45s) |
| B10 | Dead nav links (cross-page validation) |

---

## Knowledge System

### 482 Academic Entries (auto-updating)

```
llm_2026 (97 entries)   — Claude 4, GPT-5, Gemini, DeepSeek, RAG 2025...
ai (25)                 — Transformers, MoE, RLHF, agents...
academic (24)           — Stanford AI, MIT CSAIL, DeepMind...
web (19)                — Core Web Vitals, CSS GPU, WebAssembly...
backend (?)             — FastAPI, PostgreSQL, Redis, JWT...
security (12)           — Blockchain, smart contracts, zero-knowledge...
```

### Sources (all free)
Wikipedia · arXiv · Semantic Scholar · OpenAlex · CrossRef · PubMed · DuckDuckGo · GitHub

### Auto-update
```python
python ailex_activate.py --now    # populate all 16 domains
python ailex_activate.py --search "transformer attention 2025"
python ailex_activate.py --github "neural network RAG"
```

---

## Tests
```bash
cd tests && python run_all.py
# ✅  168/168 tests passed
#  Unit: structured_output, agent_quality_gate, smart_cache, content_guard...
#  Integration: pipeline, health checks, generation workflow
#  E2E: site generation across all 12 types
```

---

## Environment Setup

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional (providers fallback: Anthropic → OpenAI → Gemini)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...

# Optional (higher GitHub rate limits)
GITHUB_TOKEN=ghp_...

# Optional (FLUX image generation)
REPLICATE_API_TOKEN=r8_...
```

---

## Stats

```
214  Python modules
119  agents (19 core + 100 MultiWave)
 13  wave domains
 12  site types
  3  backend frameworks
 20  visual libraries (CDN)
 27  HTML QA checks
 10  zero-bug rules
482  KB entries (16 domains)
  7  frontier LLMs known by MARY
 14  AIOX modules bridged
168  tests passing
 15  health-monitored subsystems
```

---

## License

MIT — See [LICENSE](LICENSE)

---

*Built with Claude Sonnet 4.6 · Anthropic · 2026*
