# AILEX Pro Vanguard
## Documentação Completa — Instalação, Configuração e Uso

> **119 agentes especializados · Multi-wave orchestration · Zero-bug generation · 2026 LLM knowledge**

---

## Índice

- [O que é o AILEX](#o-que-é-o-ailex)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Activação](#activação)
- [Uso por domínio](#uso-por-domínio)
  - [Wave Orchestration](#wave-orchestration)
  - [MultiWave Performer — 100 agentes](#multiwave-performer)
  - [BMAD 4-Phase Lifecycle](#bmad-4-phase-lifecycle)
  - [Backend Generation](#backend-generation)
  - [Website Generation](#website-generation)
  - [MARY — Pesquisa 2026](#mary--pesquisa-2026)
  - [AIoX Maximizer](#aiox-maximizer)
- [Referência completa](#referência-completa)
- [Exemplos reais](#exemplos-reais)
- [Troubleshooting](#troubleshooting)

---

## O que é o AILEX

AILEX Pro Vanguard é uma plataforma de inteligência artificial para engenharia de software completa. Em vez de um assistente que responde, é um **executor autónomo** que:

1. **Analisa** a tarefa com 119 agentes especializados
2. **Pesquisa** conhecimento académico actual (482+ papers, 8 fontes)
3. **Gera** código, websites, e backends completos e funcionais
4. **Verifica** a qualidade com 27 checks automáticos
5. **Garante** zero-bugs via 10 regras constitucionais
6. **Rastreia** cada decisão com observabilidade total

### Comparação rápida

| Ferramenta | O que faz |
|---|---|
| GitHub Copilot | Autocompletion de código |
| ChatGPT / Claude | Responde perguntas, escreve código |
| bolt.new | Gera frontend web |
| **AILEX Pro** | Gera sistemas completos (frontend + backend + deploy + testes) com qualidade garantida |

---

## Instalação

### Requisitos

- **Python 3.11+** (recomendado: 3.12)
- **pip** ou **pip3**
- **Git**
- Chave API da Anthropic (obrigatória) — obter em [console.anthropic.com](https://console.anthropic.com)

### Passo 1 — Clonar o repositório

```bash
git clone https://github.com/Patriarchabraham/ailex-pro-vanguard.git
cd ailex-pro-vanguard
```

### Passo 2 — Instalar dependências

```bash
# Mínimo (só Anthropic)
pip install anthropic pydantic rich

# Completo (todas as funcionalidades)
pip install -r requirements.txt
```

### Passo 3 — Configurar API key

```bash
# Opção A: variável de ambiente (recomendado)
export ANTHROPIC_API_KEY="sk-ant-..."

# Opção B: ficheiro .env na pasta do projecto
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# Opção C: Termux / Android
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc && source ~/.bashrc
```

### Passo 4 — Verificar instalação

```bash
python ailex_activate.py --health
```

Deve mostrar:
```
⚡ AILEX — Subsystem Health Check
──────────────────────────────────────────────────
  ✅ WebResearcher          Wikipedia OK
  ✅ KnowledgeUpdater       44 entries
  ✅ ContentGuard           pick() OK
  ✅ HTMLQualityAssurance   96.0/100
  ✅ MotionSystem           inject() OK
  ✅ UltraMotionSystem      Three.js present
  ✅ SmartCacheV2           set/get OK
  ✅ AgentQualityGate       score=0.81
  ✅ StructuredOutput       schema OK
  ✅ MultiProvider          1 provider available
  ✅ ContextCompressor      compress() OK
  ✅ GenerationGuard        auto-fixed
  ✅ AILEXLogger            log OK
  ✅ MetricsStore           counter OK
  ✅ ResearchScheduler      interval=6h

  15/15 subsystems healthy
```

---

## Configuração

### Variáveis de ambiente

```bash
# ── OBRIGATÓRIO ─────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...          # Claude (primary LLM)

# ── OPCIONAL — providers adicionais (fallback automático) ────────────────────
OPENAI_API_KEY=sk-...                 # GPT-4o fallback
GEMINI_API_KEY=AIza...                # Gemini 2.5 fallback

# ── OPCIONAL — aumenta rate limits ──────────────────────────────────────────
GITHUB_TOKEN=ghp_...                  # 60 → 5000 req/h no GitHub

# ── OPCIONAL — geração de imagens com FLUX ───────────────────────────────────
REPLICATE_API_TOKEN=r8_...            # FLUX.1-pro image generation
```

### Ficheiro .env

Criar `.env` na raiz do projecto:

```env
ANTHROPIC_API_KEY=sk-ant-api_key_aqui
OPENAI_API_KEY=sk-openai_key_aqui
GEMINI_API_KEY=AIzaGemini_key_aqui
GITHUB_TOKEN=ghp_github_token_aqui
```

### Configuração de modelos

O AILEX usa routing inteligente por agente — sem configuração necessária:

```
DEX, ARIA, BASTIAN, WINSTON, AMELIA  →  Claude Opus 4.7  (melhor qualidade)
NOVA, FELIX, DARA, ORION, MARY, JOHN →  Claude Sonnet 4.6 (equilibrado)
QUINN, UMA, KAI, SALLY, BOB, BARRY  →  Claude Haiku 4.5  (rápido)
```

---

## Activação

### Activação completa (recomendada)

```bash
python ailex_activate.py
```

Inicia em background:
- Research Scheduler (actualiza KB a cada 6h)
- Pipeline v2 com instrumentação
- WebResearcher (Wikipedia, arXiv, OpenAlex...)
- GitHub Research
- Auto-Improvement cycle

### Comandos do script de activação

```bash
# Activação background (não bloqueia)
python ailex_activate.py

# Activação completa blocking (aguarda tudo)
python ailex_activate.py --now

# Dashboard de métricas ao vivo
python ailex_activate.py --dash

# Dashboard com auto-refresh a cada 5 segundos
python ailex_activate.py --watch 5

# Health check de 15 subsistemas
python ailex_activate.py --health

# Pesquisa académica imediata
python ailex_activate.py --search "transformer attention mechanism 2025"

# Pesquisa no GitHub
python ailex_activate.py --github "neural network pytorch training"

# Ver sugestões de melhorias detectadas
python ailex_activate.py --suggest

# Ver eventos recentes do pipeline
python ailex_activate.py --recent
```

### Dashboard ao vivo

```
⚡ AILEX Pipeline — Observability Dashboard   2026-04-27 09:45
──────────────────────────────────────────────────────────────────
PIPELINE ACTIVITY
  Calls today:     47       This hour:     12
  Total all-time:  847      QA blocked:    3

CACHE PERFORMANCE
  Hit rate: ████████████████░░░░  78.5%
  Hits: 124   Misses: 34

QUALITY & COST
  Avg confidence: 0.871   Avg latency: 842ms
  Tokens today:   14,200  Est. cost: $0.0087

KNOWLEDGE BASE
  482 entries · 97 llm_2026 · 12 domains active
──────────────────────────────────────────────────────────────────
```

---

## Uso por domínio

### Wave Orchestration

O sistema mais simples. Escolhe o domínio, executa as ondas.

```python
from ailex_pilot.wave_orchestrator import wave_run, WaveOrchestrator

# Uma linha — executa todas as ondas do domínio
result = wave_run("Build JWT authentication with Redis sessions", "backend")

# Ver resultado completo onda a onda
print(result.wave_by_wave_summary())

# Só a síntese final (ORION)
print(result.final_synthesis)

# Injectar contexto na próxima chamada
ctx = result.to_context()
```

#### Domínios disponíveis

| Domínio | Ondas | Melhor para |
|---|---|---|
| `frontend` | RESEARCH→DESIGN→ARCH→IMPL→QUALITY→SYNTHESIS | UI, React, CSS |
| `backend` | RESEARCH→ARCH→DB→IMPL→SECURITY→DEVOPS→SYNTHESIS | APIs, auth, DB |
| `fullstack` | RESEARCH→ARCH→FRONTEND→BACKEND→INTEG→QUALITY→SYNTHESIS | Apps completas |
| `bug` | TRIAGE→DIAGNOSIS→FIX→REGRESSION→SYNTHESIS | Debugging |
| `architecture` | REQUIREMENTS→DESIGN→DATA→RESILIENCE→TRADEOFFS→SYNTHESIS | System design |
| `security` | THREAT_MODEL→ATTACK_SURFACE→OWASP→DEFENCE→SYNTHESIS | Auditorias |
| `performance` | PROFILING→DATABASE→FRONTEND→INFRA→SYNTHESIS | Optimização |
| `feature` | DISCOVERY→UX→ARCH→IMPL→TESTING→DEPLOY→SYNTHESIS | Novas features |
| `deploy` | PRE_CHECK→RISK→EXECUTION→SYNTHESIS | Deployment |
| `analysis` | DATA_GATHER→PATTERN→INSIGHT→RECOMMENDATION→SYNTHESIS | Data analysis |
| `creative` | VISION→DESIGN_SYSTEM→MOTION→CONTENT→SYNTHESIS | Design |
| `code` | DIAGNOSIS→ANALYSIS→IMPL→VERIFICATION→SYNTHESIS | Código geral |
| `universal` | RESEARCH→ANALYSIS→IMPL→QUALITY→SYNTHESIS | Qualquer coisa |

#### Aliases rápidos

```python
wave_run("...", "back")    # backend
wave_run("...", "front")   # frontend
wave_run("...", "fix")     # bug
wave_run("...", "arch")    # architecture
wave_run("...", "sec")     # security
wave_run("...", "perf")    # performance
wave_run("...", "all")     # universal
```

#### Controlo avançado

```python
from ailex_pilot.wave_orchestrator import WaveOrchestrator

orch = WaveOrchestrator(verbose=True)

# Limitar ondas (mais rápido)
result = orch.run(
    task    = "Optimise PostgreSQL queries",
    domain  = "performance",
    max_waves = 3,    # só as 3 primeiras ondas
    context = "PostgreSQL 16, 10M rows, avg query 2s",
)

print(result.wave_by_wave_summary())
```

---

### MultiWave Performer

100 agentes super-especializados em formação dinâmica.

```python
from ailex_pilot.multiwave_performer import mwp_run, MultiWavePerformer

# Uma linha
result = mwp_run("Build real-time collaborative editor with AI autocomplete")

print(result.executive_summary())
print(result.top_performers())   # quem contribuiu mais
```

#### Selecção inteligente

O AILEX selecciona automaticamente os agentes mais relevantes dos 100:

```
Task: "GLSL particle shaders WebGL"
→ THREE_MASTER (glsl keywords) · GLSL_MASTER · VISUAL_DES

Task: "JWT authentication refresh tokens"
→ AUTH_MASTER (oauth, jwt) · CRYPTO_PRO · REDIS_PRO (session)

Task: "PostgreSQL query optimization"
→ PRISM (postgresql, index) · DB_OPT · PROFILER
```

#### Agentes por especialidade

```python
from ailex_pilot.multiwave_performer import AGENT_REGISTRY

# Ver todos os 100
for agent in AGENT_REGISTRY:
    print(f"[T{agent.tier}] {agent.id:<20} {agent.name}")

# Filtrar por tier
tier3_security = [a for a in AGENT_REGISTRY if a.tier == 3]
# → PENTEST_PRO, CRYPTO_PRO, AUTH_MASTER, DEVSEC, THREAT_ARCH,
#   ZERO_TRUST, BLOCK_SEC, PRIVACY_ENG, NETWORK_SEC, FORENSIC_ENG
```

#### Controlo avançado

```python
mwp = MultiWavePerformer(verbose=True)
result = mwp.run(
    task       = "Design microservices for an e-commerce platform",
    domain     = "architecture",
    max_agents = 25,   # quantos dos 100 usar
    max_waves  = 4,    # máximo de ondas
)
print(result.waves[0].insights)   # Tier 1 Engineering findings
print(result.waves[1].insights)   # Tier 3 Security findings
print(result.final_synthesis)     # ORION synthesis
```

---

### BMAD 4-Phase Lifecycle

BMAD (Breakthrough Method for Agile Development) integrado com toda a stack AILEX.

```python
from ailex_pilot.bmad_integration import bmad_run

# Lifecycle completo
project = bmad_run(
    project_name = "Payment Gateway Service",
    brief        = "Stripe integration with webhooks, idempotency, PCI-DSS compliance"
)

print(project.summary())
```

Output:
```
╔══ BMAD Project: Payment Gateway Service ═══════════════
║  Phase: implementation | Trace: a3f7e2b4c8d1
║  Artifacts: 4 | Stories: 8 | Files: 25
║  📄 [analysis]       research_findings   agent=MARY   q=0.88
║  📄 [planning]       prd                 agent=JOHN   q=0.91
║  📄 [solutioning]    architecture        agent=WINSTON q=0.87
║  📄 [implementation] code                agent=AMELIA  q=0.83
║  📌 [MUST] S001: Payment intent creation [5pts]
║  📌 [MUST] S002: Webhook signature verification [3pts]
║  📌 [SHOULD] S003: Idempotency key handling [3pts]
║  Generated code: ['main.py', 'app/routers/payments.py', ...]
╚══════════════════════════════════════════════════════════
```

#### Fases individuais

```python
from ailex_pilot.bmad_integration import BMADIntegration

bi = BMADIntegration()

# Só análise (Phase 1 — MARY pesquisa + JOHN + ZARA)
analysis = bi.run_phase("analysis", "Build a real-time chat system")

# Só arquitectura (Phase 3 — WINSTON + MultiWave)
arch = bi.run_phase("solutioning", "...", project=project)

print(f"Quality: {arch.quality_score:.2f}")
print(arch.content[:500])
```

#### Artefactos individuais

```python
from ailex_pilot.bmad_integration import bmad_artifact, bmad_stories

# PRD
prd = bmad_artifact("prd", "E-commerce checkout with Stripe and PayPal")
print(prd.content)

# Arquitectura
arch = bmad_artifact("architecture", "Microservices for user management")
print(f"Quality: {arch.quality_score:.2f} | Validated: {arch.validated}")

# Sprint stories
stories = bmad_stories(prd.content, "Checkout Epic", n=5)
for s in stories:
    print(f"[{s.priority.upper()}] {s.id}: {s.title} [{s.story_points}pts]")
    print(f"  As a {s.as_a}, I want to {s.i_want}")
    for c in s.acceptance_criteria:
        print(f"  ✓ {c}")
```

#### Quick Flow (BARRY — ultra-rápido)

```python
bi = BMADIntegration()
answer = bi.quick_flow("Fix the null pointer in AuthMiddleware.validate()")
# BARRY responde em < 1s com resposta directa e sem preâmbulo
```

---

### Backend Generation

BASTIAN gera projectos backend completos e funcionais.

```python
from ailex_pilot.backend_generator import BackendGenerator, bastian_generate

gen = BackendGenerator()

# FastAPI (Python) — 25 ficheiros
project = gen.generate("fastapi", "user-service", "User management with JWT and roles")
project.write_to("~/projects/user-service")

# Express/TypeScript — 17 ficheiros
project = gen.generate("express", "notifications-api", "Push notifications with Redis")
project.write_to("~/projects/notifications-api")

# Django REST Framework — 15 ficheiros
project = gen.generate("django", "blog-api", "Blog with comments, tags, search")
project.write_to("~/projects/blog-api")

# Shortcut directo
bastian_generate("fastapi", "payment-api",
                 brief="Stripe payment processing with webhooks",
                 output="~/projects/payment-api")
```

#### O que cada projecto inclui

**FastAPI:**
```
requirements.txt          main.py               Dockerfile
requirements-dev.txt      app/__init__.py       docker-compose.yml
.env.example              app/config.py         .github/workflows/ci.yml
app/database.py           app/auth.py           alembic.ini
app/models/user.py        app/routers/auth.py   .gitignore
app/schemas/user.py       app/routers/users.py  tests/__init__.py
app/middleware.py         app/exceptions.py     tests/conftest.py
                                                tests/test_auth.py
```

**Cada projecto tem sempre:**
- JWT auth com access + refresh tokens + bcrypt
- PostgreSQL + ORM + migrations (Alembic/Prisma/Django migrations)
- Validação de inputs (Pydantic v2 / Zod / DRF serializers)
- Error handling global com tipos
- Logging estruturado JSON
- Testes (unit + integration + API) com exemplos
- Docker + docker-compose (app + db + redis)
- .env.example com todas as variáveis necessárias
- OpenAPI/Swagger automático
- Rate limiting + CORS configurado
- GitHub Actions CI/CD
- OWASP security headers

#### Comandos do projecto gerado

```bash
cd ~/projects/user-service

# FastAPI
cp .env.example .env
pip install -r requirements.txt
uvicorn main:app --reload          # dev server
pytest tests/ -v                   # testes
docker-compose up                  # stack completa

# Express
npm install && npm run dev         # dev server
npm test                           # testes
npx prisma migrate dev             # migrations

# Django
python manage.py migrate           # migrations
python manage.py runserver         # dev server
pytest                             # testes
```

---

### Website Generation

```python
from ailex_vision.site_factory import SiteFactory, get_factory
from ailex_vision.ultra_motion_system import UltraMotionSystem
from ailex_vision.generation_guard import GenerationGuard
from ailex_vision.html_qa import HTMLQualityAssurance

factory = SiteFactory()
ums     = UltraMotionSystem()
guard   = GenerationGuard()
qa      = HTMLQualityAssurance()

# 1. Escolher tipo de site
spec = factory.get_spec("luxury_dating")
print(f"Required pages: {[p.slug for p in spec.pages]}")

# 2. Gerar HTML (com o seu gerador preferido)
html = your_html_generator(spec)

# 3. Validar e auto-corrigir (zero-bug constitution)
html, report = guard.validate_and_fix(html, verify_images=True)
print(f"Bugs fixed: {report.bugs_fixed}")

# 4. Injectar sistema de motion (20 bibliotecas visuais)
html = ums.inject(html, preset="luxury_dating", loader_logo="ROMA")

# 5. QA final
r = qa.validate(html)
print(f"QA: {r.score}/100 — {'DEPLOYABLE' if r.deployable else 'BLOCKED'}")

# 6. Gerar sitemap + robots + vercel.json
sitemap = factory.generate_sitemap("https://mysite.com", spec)
robots  = factory.generate_robots("https://mysite.com")
vercel  = factory.generate_vercel_json(spec)
```

#### Tipos de site disponíveis

```python
factory = SiteFactory()
print(factory.describe())

# luxury_dating   10 pages  [luxury_dating preset]
# institutional    9 pages  [institutional preset]
# dark_metal_band  8 pages  [cinematic preset]
# luxury_restaurant 9 pages [luxury_restaurant preset]
# corporate       10 pages  [minimal preset]
# portfolio        7 pages  [cinematic preset]
# e_commerce      11 pages  [minimal preset]
# healthcare       9 pages  [minimal preset]
# nonprofit       10 pages  [institutional preset]
# saas_product    11 pages  [minimal preset]
# api_backend     10 pages  [minimal preset]
# fullstack       11 pages  [minimal preset]
```

#### Motion presets

```python
html = ums.inject(html, preset="luxury_dating")
# Activa:
# Three.js WebGL 5000 partículas GLSL + 12 wireframes flutuantes
# Cursor dourado 24 dots trail
# Hero text char-by-char entrance (stagger .024s, rotateX)
# Magnetic CTAs (elastic return)
# 3D card tilt (rotateX/Y 7°)
# Parallax hero BG + stats
# Film grain noise + scanlines
# Page loader + progress bar
# Gallery stagger + chromatic aberration
# Floating KPIs + neon glow

# Outros presets:
html = ums.inject(html, preset="institutional")    # formal + gold
html = ums.inject(html, preset="cinematic")        # maximum effects
html = ums.inject(html, preset="minimal")          # clean + fast
html = ums.inject(html, preset="luxury_restaurant") # warm + elegant
```

#### MaxEffects — 20 bibliotecas visuais

Injectadas automaticamente pelo UltraMotionSystem. Activação por atributo HTML:

```html
<!-- Typewriter effect -->
<h1 data-typed="Welcome|Olá|Bonjour"></h1>

<!-- Text scramble -->
<h2 data-scramble="AILEX PRO VANGUARD">AILEX PRO VANGUARD</h2>

<!-- Neon glow -->
<span data-neon="gold">Texto neon</span>

<!-- Holographic card -->
<div class="holo-card">Card com efeito holográfico</div>

<!-- Scroll reveal -->
<div class="sr-reveal">Aparece ao scroll</div>
<div class="sr-stagger">
  <p>Item 1</p><p>Item 2</p><p>Item 3</p>   <!-- stagger automático -->
</div>

<!-- VANTA 3D background -->
<div data-vanta="NET" style="height:400px"></div>

<!-- D3 bar chart -->
<div data-d3-bar='[{"label":"Jan","value":120},{"label":"Feb","value":180}]'></div>

<!-- Chart.js -->
<canvas data-chart='{"type":"line","data":{...}}'></canvas>

<!-- Animated counter -->
<div data-count="47000" data-suffix="+">47,000+</div>

<!-- SVG draw animation -->
<svg data-vivus class="vivus-svg">...</svg>
```

#### Images — ContentGuard

```python
from ailex_vision.content_guard import ContentGuard, guaranteed_image

cg = ContentGuard()

# Kit completo para um tipo de site
images = cg.get_site_images("dating_luxury_italian")
# → images["hero_bg"], images["manifesto_photo"], images["profile_female_1"]...

# Imagem individual por categoria semântica
url = cg.pick("romantic_couple")       # casal romântico verificado
url = cg.pick("diplomatic_institutional") # edifício governamental
url = cg.pick("luxury_dining")         # restaurante de luxo

# Garantido (nunca None — ContentGuard → FLUX → Unsplash fallback)
url = guaranteed_image("romantic_couple", context="Italian luxury")
```

---

### MARY — Pesquisa 2026

MARY é a agente de pesquisa com conhecimento completo de LLMs e AI de 2026.

```python
from ailex_pilot.mary_2026 import (
    enrich_mary, mary_research, mary_compare_models,
    Mary2026, LLM_LANDSCAPE_2026, AI_TECHNIQUES_2026
)

# Contexto 2026 para injectar em prompts
context = enrich_mary("Build a RAG system for document search")
# → "[2026 LLM Context] Claude 4: tool_use, agents...
#    [2026 AI Techniques] HyDE: Hypothetical Document Embeddings...
#    [KB Research 2026] arXiv: Advanced RAG techniques..."

# Recomendação de modelos
print(mary_compare_models("secure multi-tenant SaaS with AI features"))
# → ✦ Claude 4 Sonnet — balanced quality/cost, tool_use, agents
#   ✦ GPT-4o — if multimodal features needed
#   ✦ Gemini Flash — if cost optimization is priority

# Pesquisa completa
result = mary_research("Best practices for LLM agent tool use 2025", deep=True)
print(result.summary)   # Wikipedia + arXiv + técnicas 2026

# Landscape completo de LLMs
m = Mary2026()
print(m.describe_llm_landscape())
print(m.describe_techniques("RAG & Retrieval"))
print(m.describe_techniques("Training & Alignment"))
```

#### Modelos que MARY conhece (2026)

```
Claude 4 (Anthropic)       — Opus 4.7, Sonnet 4.6, Haiku 4.5
GPT-4o / o3 (OpenAI)       — gpt-4o, gpt-4o-mini, o3, o4-mini
Gemini 2.5 Pro (Google)    — gemini-2.5-pro, gemini-2.0-flash
Llama 3.x (Meta)           — llama-3.3-70b, llama-3.1-405b
Mistral Large 2            — mistral-large-2, codestral
DeepSeek V3/R1             — deepseek-v3, deepseek-r1
Qwen 2.5 (Alibaba)         — qwen-2.5-72b, qwen-2.5-coder
```

#### Técnicas que MARY domina

```
Training:    RLHF, DPO, GRPO, Constitutional AI, LoRA, QLoRA, SFT
Architecture: MoE, Mamba/SSM, FlashAttention 3, Ring Attention
Inference:   vLLM, GGUF/GPTQ, AWQ, speculative decoding
RAG:         HyDE, reranking, ColBERT, hybrid search, GraphRAG, Self-RAG
Agents:      ReAct, CoT, ToT, Reflexion, MCTS, multi-agent, tool use
Evals:       SWE-bench (72.5%), LiveBench, MMLU-Pro, GPQA Diamond
```

---

### AIoX Maximizer

Activa todos os módulos AIOX em simultâneo.

```python
from ailex_pilot.aiox_maximizer import aiox_run, aiox_status, AIoXMaximizer

# Ver módulos disponíveis
print(aiox_status())
# ✅ 🔒 SecurityScanner
# ✅ ↺ RecursiveImprovement
# ✅ 🌊 SwarmIntelligence
# ✅ ⚙️ GSD2Integration
# ...

# Modo standard (rápido)
result = aiox_run("Add rate limiting to FastAPI", "backend", mode="standard")

# Modo enhanced (+ Security + Quality + RecursiveImprovement)
result = aiox_run("Implement JWT auth", "backend", mode="enhanced")

# Modo maximum (tudo activado)
result = aiox_run("Design complete e-commerce system", "fullstack", mode="maximum")

print(result.full_report())
print(result.security_report)    # SecurityScanner findings
print(result.quality_report)     # CodeQualityGate findings
print(result.swarm_synthesis)    # SwarmIntelligence consensus
```

#### Módulos bridgeados

| Módulo | Activa quando | O que faz |
|---|---|---|
| 🔒 SecurityScanner | mode=enhanced+ | Scan SAST, secrets, CVEs no código |
| ↺ RecursiveImprovement | score < 0.75 | Itera até qualidade suficiente |
| 🌊 SwarmIntelligence | mode=maximum | 4 instâncias AILEX em paralelo |
| ⚙️ GSD2Integration | mode=maximum | Scout→Researcher→Worker pipeline |
| ✓ CodeQualityGate | mode=enhanced+ | Estrutura, padrões, coverage |
| 🧪 TDDLoop | quando pedido | QUINN testa → AMELIA implementa |
| 📊 Evaluator | quando pedido | Benchmark do output |
| 🧠 KnowledgeSynthesis | sempre | Padrões da KB de 482 entries |
| 🌳 ASTAnalyzer | code/bug | Análise estrutural AST |
| 🔗 DependencyGraph | architecture | Deps circulares, coupling |
| 🔮 PredictiveIntelligence | planning | Prevê próximas necessidades |
| 📝 PromptLibrary | all agents | Templates de prompt optimizados |

---

## Referência completa

### Pipeline v2

```python
from ailex_pilot.pipeline_v2 import get_pipeline, InstrumentedPipeline

pipe = get_pipeline()

# Chamada individual
result = pipe.call_agent(
    agent      = "BASTIAN",
    task       = "Design a rate limiting middleware for FastAPI",
    domain     = "backend",
    context    = "Current setup: FastAPI 0.115, Redis 7, 10k req/day",
    max_tokens = 500,
    force_fresh = False,  # True = ignorar cache
)
print(result.agent)          # "BASTIAN"
print(result.analysis)       # análise completa
print(result.recommendation) # recomendação concreta
print(result.confidence)     # 0.0-1.0
print(result.cache_hit)      # True se veio do cache
print(result.quality_score)  # 0.0-1.0 (AgentQualityGate)
print(result.trace_id)       # trace para observabilidade
print(result.pipeline_ms)    # duração

# Paralelo (múltiplos agentes em simultâneo)
results = pipe.run_parallel(
    task    = "Build secure payment API",
    domain  = "backend",
    agents  = ["BASTIAN", "AUTH_MASTER", "PENTEST_PRO", "FELIX"],
)

# Síntese ORION
synthesis = pipe.synthesise("Build secure payment API", "backend", results)
print(synthesis.analysis)

# Activar instrumentação (Cache + QA + Logger + Metrics)
from ailex_pilot.pipeline_v2 import activate_instrumentation
pipe = activate_instrumentation(verbose=True)
```

### Observabilidade

```python
from ailex_pilot.observability import metrics, tracer, health

# Métricas
d = metrics.dashboard_data()
print(f"Calls today: {d['calls_today']}")
print(f"Cache rate: {d['cache_rate']}")
print(f"Avg confidence: {d['avg_conf']}")
print(f"Cost estimate: {d['cost_est_usd']}")

# Eventos recentes
events = metrics.recent_events("agent.call", limit=10)
for e in events:
    print(f"{e['age_s']}s ago — {e['data'].get('agent')} conf={e['data'].get('confidence',0):.2f}")

# Health check
results = health.check_all(verbose=True)
ok = sum(1 for r in results if r.ok)
print(f"{ok}/15 subsystems healthy")

# Trace manual
trace = tracer.new_trace()
with tracer.span("my_operation", domain="backend") as span:
    result = pipe.call_agent("BASTIAN", task, "backend")
    span.set("confidence", result.confidence)

# Decorator
from ailex_pilot.observability import observe

@observe("my_function", domain="code")
def my_function(task):
    return pipe.call_agent("DEX", task, "code")
```

### Knowledge Base

```python
from ailex_pilot.knowledge_updater import KnowledgeUpdater

ku = KnowledgeUpdater()

# Ver estatísticas
stats = ku.stats()
print(f"Total: {stats['total']} entries")
print(f"By domain: {stats['by_domain']}")

# Pesquisar
results = ku.query("RAG retrieval", domain="llm_2026", limit=5)
for e in results:
    print(f"• {e['title'][:60]} ({e['source']}, ★{e['citations']})")

# Actualizar um domínio
report = ku.update_domain("backend", verbose=True)
print(f"New entries: {report.new_entries}")

# Síntese de domínio (para injectar em prompts)
context = ku.get_synthesis("backend", limit=5)
print(context)
```

### QA & Generation Guard

```python
from ailex_vision.html_qa import HTMLQualityAssurance, ensure_qa
from ailex_vision.generation_guard import GenerationGuard, guard_html

# QA manual
qa = HTMLQualityAssurance()
report = qa.validate(html)
print(f"Score: {report.score}/100")
print(f"Critical: {report.critical}")
print(f"Deployable: {report.deployable}")
for check in report.checks:
    if not check.passed:
        print(f"  [{check.severity}] [{check.id}] {check.name}: {check.detail}")

# Auto-fix
html, fixes = qa.autofix(html)
print(f"Fixed: {fixes}")

# QA antes de deploy
from ailex_vision.html_qa import qa_before_deploy
ok = qa_before_deploy("path/to/site.html", auto_fix=True)

# Decorator obrigatório em funções geradoras
@ensure_qa(auto_fix=True, block_on_critical=True, min_score=90.0)
def generate_homepage(brief: str) -> str:
    return your_generator(brief)

# GenerationGuard — 10 zero-bug rules
guard = GenerationGuard()
html, report = guard.validate_and_fix(html, verify_images=True)
print(report.summary())
# ✅ [B07] Markdown fences removed
# ✅ [B01] Counter defaults set to real values
# ✅ [B08] Missing </html> appended
```

---

## Exemplos reais

### Exemplo 1 — Backend completo em 3 linhas

```python
from ailex_pilot.backend_generator import bastian_generate

bastian_generate("fastapi", "auth-service",
                 brief="JWT auth with refresh tokens, Redis blacklist, rate limiting",
                 output="./auth-service")
# → 25 ficheiros completos. cd auth-service && pip install -r requirements.txt && uvicorn main:app --reload
```

### Exemplo 2 — Análise de arquitectura com 30 agentes

```python
from ailex_pilot.multiwave_performer import mwp_run

result = mwp_run(
    "Design a scalable event-driven microservices architecture for a fintech platform",
    max_agents=30
)
print(result.executive_summary())
# Wave 1 (Engineering): MICRO_SVC, QUEUE_MSG, GRPC_PRO, API_ARCH
# Wave 2 (Security): PENTEST_PRO, CRYPTO_PRO, AUTH_MASTER, DEVSEC
# Wave 3 (Domain): FINTECH_ENG, BLOCK_ENG
# Wave 4 (Strategy): ENT_ARCH, SCALE_STRAT
# ORION synthesis → final architecture decision
```

### Exemplo 3 — BMAD completo de uma aplicação

```python
from ailex_pilot.bmad_integration import bmad_run

project = bmad_run(
    "Real-time collaborative code editor",
    "VS Code-like editor with WebSocket sync, CRDT conflict resolution, AI autocomplete via Claude"
)

# Salvar artefactos
with open("PRD.md", "w") as f: f.write(project.prd)
with open("ARCHITECTURE.md", "w") as f: f.write(project.architecture)
with open("IMPLEMENTATION.md", "w") as f: f.write(project.implementation_report)

# Sprint backlog
print(f"Stories generated: {len(project.stories)}")
for s in project.stories[:5]:
    print(f"  [{s.story_points}pts] {s.title}")
```

### Exemplo 4 — Website com todos os efeitos

```python
from ailex_vision.ultra_motion_system import UltraMotionSystem
from ailex_vision.generation_guard import GenerationGuard
from ailex_vision.html_qa import qa_before_deploy

html = open("my_site.html").read()

# Validar e corrigir bugs
html, report = GenerationGuard().validate_and_fix(html, verify_images=True)

# Injectar 20 bibliotecas visuais
html = UltraMotionSystem().inject(html, preset="luxury_dating", loader_logo="ROMA")

# Salvar e fazer deploy
with open("site_final.html", "w") as f: f.write(html)
assert qa_before_deploy("site_final.html")  # 27 checks — bloqueia se critical
```

### Exemplo 5 — Pesquisa com MARY 2026

```python
from ailex_pilot.mary_2026 import Mary2026

m = Mary2026()

# Qual modelo usar para RAG?
print(m.compare_models("Build a RAG pipeline for legal documents"))
# → Claude 4 Sonnet (tool_use, structured output)
#   + DeepSeek R1 (para queries complexas de raciocínio)
#   + Gemini Flash (para custo em produção)

# Técnicas actuais de RAG
print(m.describe_techniques("RAG & Retrieval"))
# HyDE, ColBERT, GraphRAG, Self-RAG, FLARE, Hybrid Search...

# Pesquisa com papers reais
result = m.research("GraphRAG knowledge graph retrieval 2025", deep=True)
print(result.summary)
# → arXiv papers + técnicas 2026 + KB context
```

### Exemplo 6 — Observabilidade completa

```python
from ailex_pilot.pipeline_v2 import activate_instrumentation
from ailex_pilot.observability import metrics

# Activar instrumentação
pipe = activate_instrumentation(verbose=True)

# Chamar agentes normalmente — tudo é rastreado automaticamente
results = pipe.run_parallel(
    "Add Redis caching to PostgreSQL queries",
    "performance",
    ["DB_OPT", "REDIS_PRO", "PROFILER"]
)

# Ver o que aconteceu
d = metrics.dashboard_data()
print(f"Calls: {d['calls_today']}")
print(f"Cache: {d['cache_rate']}")
print(f"Cost:  {d['cost_est_usd']}")
events = metrics.recent_events("agent.call", limit=3)
for e in events: print(f"  {e['data']['agent']} conf={e['data']['confidence']:.2f}")
```

---

## Troubleshooting

### Erro: `ANTHROPIC_API_KEY not set`
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# ou adicionar ao .env
```

### Erro: `401 Unauthorized` nas chamadas API
```bash
# Verificar se a chave está correcta
python -c "import os; print(os.environ.get('ANTHROPIC_API_KEY','NOT SET')[:20])"
```

### `conf=0.00` em todos os outputs
Funcionamento normal em modo fallback (sem API key). Com chave real, os valores serão 0.75-0.95.

### `QA blocked — CRITICAL`
```python
from ailex_vision.html_qa import HTMLQualityAssurance
qa = HTMLQualityAssurance()
r  = qa.validate(html)
for c in r.checks:
    if not c.passed and c.severity == "CRITICAL":
        print(f"[{c.id}] {c.name}: {c.detail}")
        print(f"  Fix: {c.autofix}")
```

### Imagens 404 no website
```python
from ailex_vision.generation_guard import GenerationGuard
guard = GenerationGuard()
html, report = guard.validate_and_fix(html, verify_images=True)
print(f"Broken images: {report.broken_images}")
```

### Knowledge Base vazia
```bash
python ailex_activate.py --now
# Aguarda ~60-90 min para popular todos os 16 domínios
```

### Rate limit (429)
O AILEX tem retry automático: 0s → 15s → 45s. Para tasks longas, usar `ANTHROPIC_API_KEY` com tier maior.

---

## Tests

```bash
cd tests

# Todos os testes
python run_all.py

# Com verbose
python run_all.py --verbose

# Módulo específico
python run_all.py --only content_guard
python run_all.py --only pipeline
python run_all.py --only e2e

# Resultado esperado:
# ✅  168/168 tests passed in 30s
```

---

## Estrutura do projecto

```
ailex-pro-vanguard/
│
├── README.md                   ← Este ficheiro
├── ailex_core.py               ← 19 agentes core + MODEL_ROUTING + AGENT_PROMPTS
├── ailex_activate.py           ← Script de activação principal
├── ailex_rdt.py                ← RDT Engine (Recurrent Depth Transformer)
├── ailex_deep.py               ← Deep analysis (16 neural layers)
├── requirements.txt
│
├── ailex_pilot/                ← 81 módulos de orquestração e inteligência
│   ├── __init__.py             ← Exports de todos os módulos
│   ├── pipeline_v2.py          ← Pipeline 9 estágios (principal)
│   ├── wave_orchestrator.py    ← 13 domínios de wave orchestration
│   ├── multiwave_performer.py  ← 100 agentes super-especializados
│   ├── bmad_integration.py     ← BMAD × AILEX v2 (4 fases)
│   ├── mary_2026.py            ← MARY + conhecimento LLM 2026
│   ├── aiox_maximizer.py       ← 14 módulos AIOX bridgeados
│   ├── backend_generator.py    ← FastAPI/Express/Django scaffolding
│   ├── observability.py        ← Traces + Metrics + Health
│   ├── smart_cache_v2.py       ← Cache SHA-256 com TTL
│   ├── agent_quality_gate.py   ← 5 quality checks por output
│   ├── structured_output.py    ← tool_use JSON schema
│   ├── knowledge_updater.py    ← KB SQLite (482 entries)
│   ├── web_researcher.py       ← 8 fontes académicas/web
│   ├── research_scheduler.py   ← Auto-update 6h
│   ├── github_researcher.py    ← GitHub API search
│   ├── auto_improve.py         ← GitHub + Academia → melhorias
│   ├── provider_health.py      ← Multi-provider health check
│   ├── multi_provider.py       ← Anthropic→OpenAI→Gemini fallback
│   ├── context_compressor.py   ← Comprime contexto > 40k tokens
│   ├── ailex_logger.py         ← JSON structured logging
│   ├── metrics_dashboard.py    ← Terminal dashboard
│   └── ... (81 total)
│
├── ailex_vision/               ← 23 módulos de geração visual
│   ├── __init__.py
│   ├── site_factory.py         ← 12 tipos de site com specs completas
│   ├── ultra_motion_system.py  ← 18 motion effects + Three.js
│   ├── max_effects_system.py   ← 20 visual libraries CDN
│   ├── generation_guard.py     ← 10 zero-bug rules
│   ├── html_qa.py              ← 27 QA checks
│   ├── content_guard.py        ← 40 imagens verificadas
│   ├── motion_system.py        ← 5 presets GSAP+Lenis
│   ├── image_generator.py      ← FLUX.1-pro via Replicate
│   └── ... (23 total)
│
└── tests/                      ← 168 testes
    ├── run_all.py
    ├── test_*.py               ← Unit tests
    ├── integration/            ← Integration tests
    └── e2e/                    ← End-to-end tests
```

---

## Licença

MIT — Ver [LICENSE](LICENSE)

---

*AILEX Pro Vanguard v7.2 · Built with Claude Sonnet 4.6 · Anthropic · 2026*
