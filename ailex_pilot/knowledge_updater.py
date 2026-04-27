"""
AILEX — knowledge_updater.py
Auto-updates AILEX knowledge base with the latest research on activation.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Runs automatically when AILEX activates. Searches 8+ academic/web sources
for the latest developments relevant to AILEX capabilities.

Research domains updated on every activation:
  D01  AI/ML models & architectures       (arXiv, Semantic Scholar, OpenAlex)
  D02  Claude/LLM best practices          (arXiv, Wikipedia, DuckDuckGo)
  D03  Web development & standards        (OpenAlex, Wikipedia, DuckDuckGo)
  D04  Three.js & WebGL techniques        (arXiv, Semantic Scholar)
  D05  Motion design & animation          (Semantic Scholar, CrossRef)
  D06  Security & cryptography            (arXiv, OpenAlex)
  D07  Legal tech & blockchain            (Semantic Scholar, CrossRef)
  D08  UX/accessibility research          (Semantic Scholar, OpenAlex)
  D09  Software engineering patterns      (arXiv, Semantic Scholar)
  D10  Neuroscience & cognitive science   (PubMed, OpenAlex)  — for MYTHOS
  D11  University research highlights     (OpenAlex, CrossRef)
  D12  Computer graphics & rendering      (arXiv, Semantic Scholar)

Usage:
    from ailex_pilot.knowledge_updater import KnowledgeUpdater
    ku = KnowledgeUpdater()
    report = ku.update_all()         # full update (takes ~60s)
    report = ku.update_domain("ai")  # specific domain
    ku.print_latest(domain="ai", n=5)

    # Auto-update on AILEX activation:
    from ailex_pilot.knowledge_updater import auto_update_on_activation
    auto_update_on_activation()      # non-blocking, runs in background thread
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .web_researcher import WebResearcher, ResearchResult


# ── Config ────────────────────────────────────────────────────────────────────

DB_PATH = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "ailex_knowledge.db"

UPDATE_INTERVAL_HOURS = 6     # re-search same topic after 6h
MAX_RESULTS_PER_QUERY = 4     # papers per search query
MAX_DB_ENTRIES        = 5000  # prune oldest beyond this


# ── Research agenda ───────────────────────────────────────────────────────────

RESEARCH_AGENDA: List[Dict[str, Any]] = [
    # D01 — AI/ML
    {"domain": "ai",       "query": "large language models instruction following 2025",  "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "ai",       "query": "transformer architecture improvements efficiency",   "sources": ["arxiv", "openalex"]},
    {"domain": "ai",       "query": "multimodal AI vision language models",              "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "ai",       "query": "reinforcement learning human feedback RLHF",        "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "ai",       "query": "AI agent autonomous reasoning planning",             "sources": ["arxiv", "openalex"]},

    # D02 — Claude/LLM best practices
    {"domain": "llm",      "query": "prompt engineering chain of thought reasoning",     "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "llm",      "query": "tool use function calling LLM",                     "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "llm",      "query": "context window long document processing LLM",       "sources": ["arxiv", "openalex"]},
    {"domain": "llm",      "query": "structured output JSON schema LLM reliability",     "sources": ["arxiv", "semantic_scholar"]},

    # D03 — Web development
    {"domain": "web",      "query": "web performance optimization Core Web Vitals",      "sources": ["semantic_scholar", "openalex"]},
    {"domain": "web",      "query": "CSS animation GPU performance browser",             "sources": ["semantic_scholar", "wikipedia"]},
    {"domain": "web",      "query": "WebAssembly WASM web applications performance",     "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "web",      "query": "progressive web apps PWA mobile",                  "sources": ["openalex", "wikipedia"]},

    # D04 — Three.js / WebGL
    {"domain": "webgl",    "query": "WebGL GLSL shader optimization performance",        "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "webgl",    "query": "real-time 3D rendering web browser techniques",    "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "webgl",    "query": "particle systems GPU simulation WebGL",             "sources": ["arxiv", "openalex"]},

    # D05 — Motion design
    {"domain": "motion",   "query": "animation easing functions perception psychology", "sources": ["semantic_scholar", "pubmed"]},
    {"domain": "motion",   "query": "UI animation UX user experience engagement",       "sources": ["semantic_scholar", "openalex"]},
    {"domain": "motion",   "query": "scroll-driven animation web interaction design",   "sources": ["semantic_scholar", "openalex"]},

    # D06 — Security/Crypto
    {"domain": "security", "query": "blockchain distributed ledger security immutability", "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "security", "query": "zero knowledge proofs cryptography applications",    "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "security", "query": "smart contract security vulnerability detection",    "sources": ["arxiv", "semantic_scholar"]},

    # D07 — Legal tech
    {"domain": "legaltech","query": "smart contracts legal enforceability international", "sources": ["semantic_scholar", "crossref"]},
    {"domain": "legaltech","query": "digital identity blockchain legal recognition",      "sources": ["semantic_scholar", "openalex"]},

    # D08 — UX/Accessibility
    {"domain": "ux",       "query": "WCAG accessibility web design inclusive",           "sources": ["semantic_scholar", "openalex"]},
    {"domain": "ux",       "query": "dark mode design psychology user preference",       "sources": ["semantic_scholar", "pubmed"]},
    {"domain": "ux",       "query": "micro-interactions feedback UI design patterns",    "sources": ["semantic_scholar", "openalex"]},

    # D09 — Software engineering
    {"domain": "swe",      "query": "code generation AI automated software testing",    "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "swe",      "query": "software architecture patterns microservices",     "sources": ["arxiv", "openalex"]},
    {"domain": "swe",      "query": "type safety static analysis bug detection",        "sources": ["arxiv", "semantic_scholar"]},

    # D10 — Neuroscience (for MYTHOS architecture)
    {"domain": "neuro",    "query": "recurrent neural networks working memory cognition", "sources": ["arxiv", "pubmed"]},
    {"domain": "neuro",    "query": "attention mechanism brain cortex neural correlates", "sources": ["pubmed", "openalex"]},
    {"domain": "neuro",    "query": "brain computer interface BCI neural decoding",      "sources": ["arxiv", "pubmed"]},

    # D11 — University/Academic highlights
    {"domain": "academic", "query": "Stanford AI lab research 2025 highlights",         "sources": ["openalex", "arxiv"]},
    {"domain": "academic", "query": "MIT CSAIL AI research recent",                     "sources": ["openalex", "arxiv"]},
    {"domain": "academic", "query": "DeepMind research advances 2025",                  "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "academic", "query": "OpenAI Anthropic research technical report",       "sources": ["arxiv", "semantic_scholar"]},

    # D12 — Computer graphics
    {"domain": "graphics", "query": "real-time rendering path tracing optimization",    "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "graphics", "query": "generative AI image synthesis diffusion models",   "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "graphics", "query": "neural radiance fields NeRF 3D reconstruction",   "sources": ["arxiv", "semantic_scholar"]},

    # D13 — Backend Engineering (NEW)
    {"domain": "backend",  "query": "REST API design best practices scalability microservices",       "sources": ["arxiv", "semantic_scholar", "openalex"]},
    {"domain": "backend",  "query": "GraphQL vs REST API performance comparison",                    "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "backend",  "query": "PostgreSQL query optimization indexing performance",            "sources": ["arxiv", "openalex"]},
    {"domain": "backend",  "query": "database sharding partitioning distributed systems",           "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "backend",  "query": "JWT OAuth2 authentication authorization security",             "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "backend",  "query": "Redis caching strategies performance scalability",             "sources": ["arxiv", "openalex"]},
    {"domain": "backend",  "query": "message queue Kafka RabbitMQ event-driven architecture",       "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "backend",  "query": "FastAPI Python async performance API framework",               "sources": ["arxiv", "openalex", "wikipedia"]},
    {"domain": "backend",  "query": "Node.js Express NestJS backend architecture patterns",         "sources": ["arxiv", "semantic_scholar", "openalex"]},
    {"domain": "backend",  "query": "Docker Kubernetes container orchestration backend deploy",     "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "backend",  "query": "API rate limiting throttling backend protection",              "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "backend",  "query": "database ORM SQLAlchemy Prisma TypeORM patterns",             "sources": ["arxiv", "openalex"]},
    {"domain": "backend",  "query": "OWASP backend security injection SQL XSS prevention",         "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "backend",  "query": "WebSocket real-time server push notification backend",        "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "backend",  "query": "gRPC protocol buffer microservices communication",            "sources": ["arxiv", "openalex"]},
    {"domain": "backend",  "query": "serverless functions AWS Lambda cloud backend architecture",  "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "backend",  "query": "backend testing pytest integration API test coverage",        "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "backend",  "query": "CI/CD pipeline backend deployment GitHub Actions Railway",   "sources": ["arxiv", "openalex"]},
    {"domain": "backend",  "query": "OpenAPI Swagger documentation backend API specification",    "sources": ["arxiv", "wikipedia", "openalex"]},
    {"domain": "backend",  "query": "backend observability logging tracing metrics OpenTelemetry", "sources": ["arxiv", "semantic_scholar"]},

    # D14 — Databases (NEW)
    {"domain": "database", "query": "SQL NoSQL database comparison use cases performance",         "sources": ["arxiv", "openalex"]},
    {"domain": "database", "query": "MongoDB PostgreSQL MySQL schema design patterns",             "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "database", "query": "database transaction ACID BASE consistency patterns",        "sources": ["arxiv", "openalex"]},
    {"domain": "database", "query": "vector database embedding similarity search pgvector",       "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "database", "query": "database migration schema evolution versioning patterns",    "sources": ["arxiv", "openalex"]},

    # D15 — API Design (NEW)
    {"domain": "api",      "query": "API versioning strategies REST backward compatibility",      "sources": ["arxiv", "openalex"]},
    {"domain": "api",      "query": "API pagination cursor keyset offset performance",            "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "api",      "query": "API error handling response codes status design",            "sources": ["arxiv", "openalex"]},
    {"domain": "api",      "query": "API documentation OpenAPI AsyncAPI specification",           "sources": ["arxiv", "wikipedia"]},
    {"domain": "api",      "query": "API testing contract testing Pact schema validation",        "sources": ["arxiv", "semantic_scholar"]},

    # D16 — DevOps / Infrastructure (extend FELIX)
    {"domain": "devops",   "query": "infrastructure as code Terraform Pulumi best practices",    "sources": ["arxiv", "openalex"]},
    {"domain": "devops",   "query": "monitoring observability Prometheus Grafana backend",        "sources": ["arxiv", "semantic_scholar"]},
    {"domain": "devops",   "query": "zero-downtime deployment blue-green canary strategies",     "sources": ["arxiv", "openalex"]},
    {"domain": "devops",   "query": "secrets management Vault environment variables security",   "sources": ["arxiv", "semantic_scholar"]},
]


# ── Entry ─────────────────────────────────────────────────────────────────────

@dataclass
class KnowledgeEntry:
    id:           int
    domain:       str
    query:        str
    title:        str
    abstract:     str
    url:          str
    source:       str
    date:         str
    authors:      str   # JSON
    citations:    int
    fetched_at:   float
    tags:         str   # JSON


@dataclass
class UpdateReport:
    domains_updated:  List[str]
    new_entries:      int
    total_entries:    int
    queries_run:      int
    duration_s:       float
    errors:           List[str]

    def __str__(self) -> str:
        return (
            f"KnowledgeUpdater Report\n"
            f"  Queries:  {self.queries_run}\n"
            f"  New:      {self.new_entries} entries\n"
            f"  Total DB: {self.total_entries}\n"
            f"  Duration: {self.duration_s:.1f}s\n"
            f"  Domains:  {', '.join(self.domains_updated)}\n"
            f"  Errors:   {len(self.errors)}"
        )


# ── Updater ───────────────────────────────────────────────────────────────────

class KnowledgeUpdater:
    """
    Searches academic and web sources and stores findings in a local SQLite DB.
    Runs on AILEX activation and periodically.

    The knowledge base becomes AILEX's "living memory" of current research —
    always reflecting the latest papers, techniques, and developments.
    """

    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path    = db_path
        self.researcher = WebResearcher()
        self.conn       = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                domain      TEXT NOT NULL,
                query       TEXT NOT NULL,
                title       TEXT NOT NULL,
                abstract    TEXT,
                url         TEXT,
                source      TEXT,
                pub_date    TEXT,
                authors     TEXT,
                citations   INTEGER DEFAULT 0,
                fetched_at  REAL,
                tags        TEXT
            );
            CREATE TABLE IF NOT EXISTS update_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                domain      TEXT,
                query       TEXT,
                n_results   INTEGER,
                duration_ms INTEGER,
                ts          REAL
            );
            CREATE INDEX IF NOT EXISTS idx_domain    ON knowledge(domain);
            CREATE INDEX IF NOT EXISTS idx_source    ON knowledge(source);
            CREATE INDEX IF NOT EXISTS idx_fetched   ON knowledge(fetched_at);
            CREATE INDEX IF NOT EXISTS idx_citations ON knowledge(citations);
        """)
        self.conn.commit()

    # ── Public API ─────────────────────────────────────────────────────────────

    def update_all(
        self,
        domains:        Optional[List[str]] = None,
        max_age_hours:  float               = UPDATE_INTERVAL_HOURS,
        verbose:        bool                = True,
    ) -> UpdateReport:
        """
        Run all research queries and update knowledge base.
        Skips queries that were run less than max_age_hours ago.
        """
        t0    = time.perf_counter()
        new   = 0
        runs  = 0
        errs  = []
        updated_domains: set = set()

        agenda = RESEARCH_AGENDA
        if domains:
            agenda = [a for a in agenda if a["domain"] in domains]

        for item in agenda:
            domain  = item["domain"]
            query   = item["query"]
            sources = item.get("sources", ["arxiv", "semantic_scholar"])

            if not self._needs_update(query, max_age_hours):
                if verbose:
                    print(f"  ⏭  {domain:<10} {query[:50]}  (cached)")
                continue

            if verbose:
                print(f"  🔍 {domain:<10} {query[:50]}…")

            try:
                t_q = time.perf_counter()
                results = self.researcher.research(
                    query,
                    sources=sources,
                    max_per_source=MAX_RESULTS_PER_QUERY,
                )
                dur_ms = int((time.perf_counter() - t_q) * 1000)

                stored = self._store(domain, query, results)
                new   += stored
                runs  += 1
                updated_domains.add(domain)

                self._log(domain, query, len(results), dur_ms)
                time.sleep(0.5)  # polite delay between queries

            except Exception as e:
                errs.append(f"{query[:40]}: {e}")

        total = self._count()
        self._prune()

        report = UpdateReport(
            domains_updated=sorted(updated_domains),
            new_entries=new,
            total_entries=total,
            queries_run=runs,
            duration_s=round(time.perf_counter() - t0, 1),
            errors=errs,
        )
        if verbose:
            print(f"\n{report}")
        return report

    def update_domain(self, domain: str, verbose: bool = True) -> UpdateReport:
        """Update a specific domain only."""
        return self.update_all(domains=[domain], max_age_hours=0, verbose=verbose)

    def query(
        self,
        search:         str,
        domain:         Optional[str] = None,
        source:         Optional[str] = None,
        min_citations:  int           = 0,
        limit:          int           = 20,
        since_hours:    Optional[float] = None,
    ) -> List[Dict]:
        """
        Query the local knowledge base.

        Example:
            ku.query("transformer attention", domain="ai", limit=5)
        """
        filters  = []
        params: List[Any] = []

        if domain:
            filters.append("domain=?"); params.append(domain)
        if source:
            filters.append("source=?"); params.append(source)
        if min_citations > 0:
            filters.append("citations>=?"); params.append(min_citations)
        if since_hours:
            filters.append("fetched_at>=?"); params.append(time.time() - since_hours * 3600)
        if search:
            filters.append("(title LIKE ? OR abstract LIKE ?)")
            params += [f"%{search}%", f"%{search}%"]

        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        params.append(limit)

        rows = self.conn.execute(
            f"SELECT title, abstract, url, source, pub_date, authors, citations, domain, fetched_at "
            f"FROM knowledge {where} ORDER BY citations DESC, fetched_at DESC LIMIT ?",
            params,
        ).fetchall()

        return [
            {
                "title":     r[0],
                "abstract":  (r[1] or "")[:200],
                "url":       r[2],
                "source":    r[3],
                "date":      r[4],
                "authors":   json.loads(r[5]) if r[5] else [],
                "citations": r[6],
                "domain":    r[7],
                "age_h":     round((time.time() - r[8]) / 3600, 1),
            }
            for r in rows
        ]

    def print_latest(self, domain: Optional[str] = None, n: int = 10) -> None:
        """Print latest knowledge base entries."""
        entries = self.query("", domain=domain, since_hours=72, limit=n)
        if not entries:
            print(f"No entries found (domain={domain})")
            return
        print(f"\nLatest Knowledge ({domain or 'all'}) — {len(entries)} entries")
        print("─" * 70)
        for e in entries:
            print(
                f"[{e['source'].upper():<15}] {e['title'][:55]}\n"
                f"  ★ {e['citations']:<5}  {e['date'][:7]}  {e['domain']}\n"
                f"  {(e['abstract'] or '')[:100]}…\n"
            )

    def get_synthesis(self, domain: str, limit: int = 10) -> str:
        """
        Return a synthesized summary of the latest knowledge for a domain.
        Suitable for injecting into an AILEX prompt as context.
        """
        entries = self.query("", domain=domain, limit=limit)
        if not entries:
            return f"No knowledge available for domain: {domain}"

        lines = [f"[AILEX Knowledge Base — {domain.upper()} domain — {len(entries)} papers]\n"]
        for e in entries:
            lines.append(
                f"• {e['title'][:80]}\n"
                f"  ({e['source']}, {e['date']}, ★{e['citations']})\n"
                f"  {(e['abstract'] or '')[:150]}"
            )
        return "\n".join(lines)

    def stats(self) -> Dict[str, Any]:
        """Return knowledge base statistics."""
        total = self._count()
        by_domain = dict(self.conn.execute(
            "SELECT domain, COUNT(*) FROM knowledge GROUP BY domain ORDER BY COUNT(*) DESC"
        ).fetchall())
        by_source = dict(self.conn.execute(
            "SELECT source, COUNT(*) FROM knowledge GROUP BY source ORDER BY COUNT(*) DESC"
        ).fetchall())
        recent_count = self.conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE fetched_at>=?",
            (time.time() - 86400,)
        ).fetchone()[0]

        return {
            "total":       total,
            "recent_24h":  recent_count,
            "by_domain":   by_domain,
            "by_source":   by_source,
            "db_path":     self.db_path,
        }

    def format_stats(self) -> str:
        s = self.stats()
        lines = [
            f"AILEX Knowledge Base",
            f"  Total entries: {s['total']:,}",
            f"  Last 24h:      {s['recent_24h']}",
            f"  DB: {s['db_path']}",
            "",
            f"  By domain:",
        ]
        for d, n in s["by_domain"].items():
            lines.append(f"    {d:<14} {n:>4}")
        return "\n".join(lines)

    # ── Private ────────────────────────────────────────────────────────────────

    def _needs_update(self, query: str, max_age_hours: float) -> bool:
        """True if query hasn't been run recently."""
        if max_age_hours == 0:
            return True
        row = self.conn.execute(
            "SELECT MAX(fetched_at) FROM knowledge WHERE query=?", (query,)
        ).fetchone()[0]
        if not row:
            return True
        return (time.time() - row) > max_age_hours * 3600

    def _store(self, domain: str, query: str, results: List[ResearchResult]) -> int:
        stored = 0
        now    = time.time()
        for r in results:
            if not r.title or not r.abstract:
                continue
            # Check duplicate
            exists = self.conn.execute(
                "SELECT id FROM knowledge WHERE title=? AND source=?",
                (r.title, r.source)
            ).fetchone()
            if exists:
                # Update citation count
                self.conn.execute(
                    "UPDATE knowledge SET citations=?, fetched_at=? WHERE id=?",
                    (r.citations, now, exists[0])
                )
                continue

            self.conn.execute(
                """INSERT INTO knowledge
                   (domain, query, title, abstract, url, source, pub_date,
                    authors, citations, fetched_at, tags)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    domain, query, r.title, r.abstract[:2000], r.url, r.source,
                    r.date, json.dumps(r.authors[:5]), r.citations, now,
                    json.dumps(r.tags[:8]),
                )
            )
            stored += 1
        self.conn.commit()
        return stored

    def _log(self, domain: str, query: str, n: int, dur_ms: int) -> None:
        self.conn.execute(
            "INSERT INTO update_log (domain,query,n_results,duration_ms,ts) VALUES(?,?,?,?,?)",
            (domain, query, n, dur_ms, time.time())
        )
        self.conn.commit()

    def _count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]

    def _prune(self) -> None:
        count = self._count()
        if count > MAX_DB_ENTRIES:
            to_delete = count - MAX_DB_ENTRIES
            self.conn.execute(
                "DELETE FROM knowledge WHERE id IN "
                "(SELECT id FROM knowledge ORDER BY citations ASC, fetched_at ASC LIMIT ?)",
                (to_delete,)
            )
            self.conn.commit()


# ── Background activation ──────────────────────────────────────────────────────

_update_thread: Optional[threading.Thread] = None
_updater: Optional[KnowledgeUpdater] = None

def auto_update_on_activation(
    domains:    Optional[List[str]] = None,
    verbose:    bool                = True,
    max_age_h:  float               = UPDATE_INTERVAL_HOURS,
) -> None:
    """
    Start a background thread to update AILEX knowledge on activation.
    Non-blocking — AILEX continues while research runs.

    Call this at the end of AILEX init:
        from ailex_pilot.knowledge_updater import auto_update_on_activation
        auto_update_on_activation()
    """
    global _updater, _update_thread

    def _run():
        global _updater
        try:
            _updater = KnowledgeUpdater()
            if verbose:
                print("\n[AILEX WebResearcher] 🌐 Auto-update started in background…")
            report = _updater.update_all(
                domains=domains,
                max_age_hours=max_age_h,
                verbose=verbose,
            )
            if verbose:
                print(f"\n[AILEX WebResearcher] ✅ Done: {report.new_entries} new entries")
        except Exception as e:
            if verbose:
                print(f"\n[AILEX WebResearcher] ⚠️ Update error: {e}")

    _update_thread = threading.Thread(target=_run, daemon=True)
    _update_thread.start()


def get_updater() -> Optional[KnowledgeUpdater]:
    """Return the global KnowledgeUpdater instance (may be None if not started)."""
    return _updater


if __name__ == "__main__":
    ku = KnowledgeUpdater()
    print("Testing KnowledgeUpdater with AI domain only…")
    report = ku.update_domain("ai", verbose=True)
    print("\nStats:", ku.format_stats())
    print("\nLatest AI entries:")
    ku.print_latest("ai", n=3)
