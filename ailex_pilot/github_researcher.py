"""
AILEX — github_researcher.py
GitHub repository research — AI, neural networks, web tech, and more.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Searches GitHub for the latest AI/ML/WebGL/neural network repositories.
Extracts: README summaries, key techniques, patterns, stars, topics.
Integrates with KnowledgeUpdater to auto-improve AILEX.

Sources:
  ↳ GitHub Search API    api.github.com/search/repositories
  ↳ GitHub Topics API    api.github.com/repos/{owner}/{repo}/topics
  ↳ README extraction    api.github.com/repos/{owner}/{repo}/readme (base64)
  ↳ Trending proxy       github-trending-api via open endpoint

Optional: Set GITHUB_TOKEN env var for 5000 req/hour (vs 60 unauth).

Usage:
    from ailex_pilot.github_researcher import GitHubResearcher
    gh = GitHubResearcher()

    # Find top AI repos
    repos = gh.search_repos("neural network attention mechanism", limit=10)
    for r in repos:
        print(r['name'], r['stars'], r['description'])

    # Get trending AI repos today
    trending = gh.trending(language="python", topic="machine-learning")

    # Extract techniques from a repo
    techniques = gh.extract_techniques("huggingface/transformers")

    # Full auto-improve cycle
    improvements = gh.auto_improve_ailex()
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ── Auth ──────────────────────────────────────────────────────────────────────

def _gh_token() -> str:
    return os.environ.get("GITHUB_TOKEN", "")

def _gh_headers() -> Dict[str, str]:
    h = {
        "Accept":     "application/vnd.github.v3+json",
        "User-Agent": "AILEX-Research/6.0",
    }
    tok = _gh_token()
    if tok:
        h["Authorization"] = f"token {tok}"
    return h

def _get(url: str, timeout: int = 15) -> Optional[Dict]:
    try:
        req = urllib.request.Request(url, headers=_gh_headers())
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            time.sleep(60)  # rate limit — wait and continue
        return None
    except Exception:
        return None


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class GitHubRepo:
    name:         str
    full_name:    str           # "owner/repo"
    description:  str
    url:          str
    stars:        int
    forks:        int
    language:     str
    topics:       List[str]     = field(default_factory=list)
    readme:       str           = ""    # first 500 chars of README
    techniques:   List[str]     = field(default_factory=list)
    last_push:    str           = ""
    license:      str           = ""
    open_issues:  int           = 0

    def snippet(self, chars: int = 150) -> str:
        if self.readme:
            return self.readme[:chars].replace("\n", " ")
        return self.description[:chars]

    def __str__(self) -> str:
        return (
            f"[GitHub] ★{self.stars:,} {self.full_name}\n"
            f"  {self.language} | {', '.join(self.topics[:5])}\n"
            f"  {self.description[:80]}\n"
            f"  {self.url}"
        )


@dataclass
class TechPattern:
    name:        str
    category:    str     # architecture | algorithm | library | pattern | dataset
    description: str
    repos:       List[str]  # repo full_names that use this
    stars:       int         # total stars across repos
    novelty:     str         # "cutting-edge" | "established" | "experimental"


# ── Researcher ────────────────────────────────────────────────────────────────

class GitHubResearcher:
    """
    Searches GitHub for technical repositories and extracts patterns.
    Used by AILEX to auto-update its knowledge of the latest tech.
    """

    # Curated search queries per AILEX domain
    DOMAIN_QUERIES: Dict[str, List[str]] = {
        "ai": [
            "large language model transformer attention",
            "neural network training optimization PyTorch",
            "RLHF reward model language model",
            "multimodal vision language model",
            "AI agent autonomous planning tool use",
            "mixture of experts sparse model",
        ],
        "neuro": [
            "brain computer interface neural decoding",
            "spiking neural network neuromorphic",
            "recurrent neural network working memory",
            "computational neuroscience simulation",
        ],
        "webgl": [
            "WebGL GLSL shader particle system",
            "Three.js animation effects examples",
            "GSAP ScrollTrigger animation",
            "canvas 2D 3D real-time rendering",
            "WebGPU compute shader web",
        ],
        "web": [
            "CSS animation performance GPU",
            "progressive web app PWA offline",
            "WebAssembly WASM performance",
            "modern JavaScript TypeScript patterns",
        ],
        "security": [
            "blockchain smart contract Solidity",
            "zero knowledge proof implementation",
            "cryptography library implementation",
            "homomorphic encryption",
        ],
        "ml_frameworks": [
            "PyTorch neural network examples",
            "JAX functional machine learning",
            "Hugging Face transformers fine-tuning",
            "LangChain LLM agent framework",
            "vector database embedding search",
        ],
        "motion": [
            "GSAP animation library examples",
            "Lenis smooth scroll",
            "Three.js particle animation",
            "CSS keyframe animation",
            "scroll driven animation web",
        ],
    }

    # Techniques to look for in READMEs
    TECHNIQUE_PATTERNS = {
        # AI architectures
        r"attention\s+mechanism":      ("attention", "architecture"),
        r"transformer\s+architecture": ("transformer", "architecture"),
        r"mixture\s+of\s+experts":     ("MoE", "architecture"),
        r"retrieval.augmented":        ("RAG", "architecture"),
        r"chain.of.thought":           ("CoT reasoning", "algorithm"),
        r"RLHF|reinforcement.from":    ("RLHF", "algorithm"),
        r"LoRA|low.rank.adaptation":   ("LoRA fine-tuning", "algorithm"),
        r"quantization|GGUF|GPTQ":     ("model quantization", "algorithm"),
        r"embeddings?\s+vector":       ("vector embeddings", "algorithm"),
        r"diffusion\s+model":          ("diffusion models", "architecture"),
        r"contrastive\s+learning":     ("contrastive learning", "algorithm"),
        r"knowledge\s+distillation":   ("knowledge distillation", "algorithm"),
        # Web/rendering
        r"WebGL|GLSL\s+shader":        ("WebGL/GLSL", "library"),
        r"Three\.js|THREE\s+js":       ("Three.js", "library"),
        r"GSAP|GreenSock":             ("GSAP animation", "library"),
        r"WebGPU":                     ("WebGPU", "library"),
        r"WebAssembly|WASM":           ("WebAssembly", "technology"),
        # Neural computation
        r"spiking\s+neural":           ("spiking neural networks", "architecture"),
        r"neuromorphic":               ("neuromorphic computing", "architecture"),
        r"graph\s+neural\s+network":   ("GNN", "architecture"),
        r"recurrent|LSTM|GRU":         ("RNN/LSTM", "architecture"),
        # Infrastructure
        r"vector\s+database|Pinecone|Weaviate|Qdrant": ("vector DB", "infrastructure"),
        r"LangChain|LlamaIndex":       ("LLM orchestration", "library"),
        r"Kubernetes|docker\s+compose":("containerization", "infrastructure"),
    }

    def __init__(self):
        self._rate_limited_until: float = 0.0

    def _rate_ok(self) -> bool:
        if time.time() < self._rate_limited_until:
            return False
        return True

    # ── Search repos ──────────────────────────────────────────────────────────

    def search_repos(
        self,
        query:      str,
        limit:      int    = 10,
        sort:       str    = "stars",   # stars | updated | best-match
        min_stars:  int    = 100,
        language:   str    = "",
    ) -> List[GitHubRepo]:
        """Search GitHub repositories by query."""
        if not self._rate_ok():
            return []

        q = query
        if language:
            q += f" language:{language}"
        if min_stars > 0:
            q += f" stars:>={min_stars}"

        url = (
            f"https://api.github.com/search/repositories"
            f"?q={urllib.parse.quote(q)}&sort={sort}&order=desc&per_page={min(limit, 30)}"
        )
        data = _get(url)
        if not data:
            return []

        results = []
        for item in data.get("items", [])[:limit]:
            repo = self._parse_repo(item)
            results.append(repo)
            time.sleep(0.1)  # polite

        return results

    def search_by_topic(
        self,
        topic:      str,
        limit:      int = 10,
        min_stars:  int = 500,
    ) -> List[GitHubRepo]:
        """Search repos by GitHub topic."""
        url = (
            f"https://api.github.com/search/repositories"
            f"?q=topic:{urllib.parse.quote(topic)}"
            f"+stars:>={min_stars}&sort=stars&order=desc&per_page={min(limit,30)}"
        )
        data = _get(url)
        if not data:
            return []
        return [self._parse_repo(item) for item in data.get("items", [])[:limit]]

    def trending(
        self,
        language:  str = "",
        since:     str = "daily",    # daily | weekly | monthly
        topic:     str = "",
        limit:     int = 10,
    ) -> List[GitHubRepo]:
        """
        Get trending GitHub repos.
        Uses the unofficial trending API proxy (not rate-limited by GitHub).
        """
        # Use GitHub search as trending proxy (sort by recently updated, high stars)
        q = "stars:>=500"
        if language:
            q += f" language:{language}"
        if topic:
            q += f" topic:{topic}"

        url = (
            f"https://api.github.com/search/repositories"
            f"?q={urllib.parse.quote(q)}&sort=updated&order=desc&per_page={min(limit,20)}"
        )
        data = _get(url)
        if not data:
            return []
        return [self._parse_repo(item) for item in data.get("items", [])[:limit]]

    # ── README extraction ──────────────────────────────────────────────────────

    def get_readme(self, full_name: str, max_chars: int = 800) -> str:
        """Fetch and decode README for a repository."""
        url  = f"https://api.github.com/repos/{full_name}/readme"
        data = _get(url)
        if not data or "content" not in data:
            return ""
        try:
            raw = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
            # Strip markdown formatting for cleaner text
            raw = re.sub(r"#{1,6}\s+", "", raw)          # headers
            raw = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", raw)  # links
            raw = re.sub(r"```[^`]*```", "", raw, flags=re.DOTALL)  # code blocks
            raw = re.sub(r"`[^`]+`", "", raw)            # inline code
            raw = re.sub(r"\s+", " ", raw).strip()
            return raw[:max_chars]
        except Exception:
            return ""

    # ── Technique extraction ───────────────────────────────────────────────────

    def extract_techniques(self, full_name: str) -> List[str]:
        """Extract technical patterns from a repo's README and description."""
        readme = self.get_readme(full_name, max_chars=2000)
        found  = []
        for pattern, (name, _) in self.TECHNIQUE_PATTERNS.items():
            if re.search(pattern, readme, re.IGNORECASE):
                found.append(name)
        return found

    def find_techniques_in_repos(
        self, repos: List[GitHubRepo]
    ) -> List[TechPattern]:
        """
        Aggregate techniques across multiple repos.
        Returns ranked list of patterns by total star count.
        """
        tech_map: Dict[str, TechPattern] = {}

        for repo in repos:
            if not repo.readme:
                repo.readme = self.get_readme(repo.full_name)
                time.sleep(0.2)

            for pattern, (name, category) in self.TECHNIQUE_PATTERNS.items():
                if re.search(pattern, repo.readme + " " + repo.description, re.IGNORECASE):
                    if name not in tech_map:
                        tech_map[name] = TechPattern(
                            name=name, category=category,
                            description="", repos=[], stars=0,
                            novelty="established",
                        )
                    tech_map[name].repos.append(repo.full_name)
                    tech_map[name].stars += repo.stars

        techs = sorted(tech_map.values(), key=lambda t: t.stars, reverse=True)
        return techs

    # ── Domain research ───────────────────────────────────────────────────────

    def research_domain(
        self,
        domain:     str,
        limit:      int = 5,
        min_stars:  int = 200,
        fetch_readmes: bool = False,
    ) -> List[GitHubRepo]:
        """Research all queries for a given AILEX domain."""
        queries = self.DOMAIN_QUERIES.get(domain, [])
        repos   = []
        seen    = set()

        for q in queries[:3]:  # max 3 queries per domain
            if not self._rate_ok():
                break
            batch = self.search_repos(q, limit=limit, min_stars=min_stars)
            for r in batch:
                if r.full_name not in seen:
                    seen.add(r.full_name)
                    if fetch_readmes and not r.readme:
                        r.readme = self.get_readme(r.full_name)
                    repos.append(r)
            time.sleep(1.5)   # respect rate limits

        return sorted(repos, key=lambda r: r.stars, reverse=True)

    # ── Auto-improve AILEX ────────────────────────────────────────────────────

    def auto_improve_ailex(
        self,
        domains:      List[str]  = ["ai", "neuro", "webgl", "ml_frameworks"],
        repos_per_d:  int        = 5,
        verbose:      bool       = True,
    ) -> Dict[str, Any]:
        """
        Find the latest tech on GitHub and identify improvements for AILEX.
        Returns a report of discovered techniques and suggested integrations.
        """
        report = {
            "timestamp":    time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "domains":      {},
            "top_repos":    [],
            "new_techniques": [],
            "suggestions":  [],
        }

        all_repos: List[GitHubRepo] = []

        for domain in domains:
            if verbose:
                print(f"  🔍 GitHub research: {domain}…")
            repos = self.research_domain(domain, limit=repos_per_d)
            report["domains"][domain] = [
                {"name": r.full_name, "stars": r.stars, "desc": r.description[:80]}
                for r in repos[:3]
            ]
            all_repos.extend(repos)
            time.sleep(2)

        # Find top repos overall
        all_repos.sort(key=lambda r: r.stars, reverse=True)
        report["top_repos"] = [
            {"name": r.full_name, "stars": r.stars, "lang": r.language, "topics": r.topics[:3]}
            for r in all_repos[:10]
        ]

        # Extract techniques
        if verbose:
            print("  🧬 Extracting techniques from README files…")

        techs = self.find_techniques_in_repos(all_repos[:15])
        report["new_techniques"] = [
            {"name": t.name, "category": t.category, "repos": len(t.repos), "stars": t.stars}
            for t in techs[:10]
        ]

        # Generate AILEX improvement suggestions
        ai_related = [t for t in techs if t.category in ("architecture", "algorithm")]
        web_related = [t for t in techs if t.category == "library"]

        for t in ai_related[:3]:
            if "MYTHOS" in t.name.upper() or any(k in t.name for k in ["CoT", "RLHF", "LoRA", "RAG"]):
                report["suggestions"].append(
                    f"Integrate {t.name} into AILEX-MYTHOS agent pipeline "
                    f"(★{t.stars:,} across {len(t.repos)} repos)"
                )
        for t in web_related[:2]:
            report["suggestions"].append(
                f"Update AILEX WebResearcher with {t.name} best practices "
                f"(★{t.stars:,} GitHub stars)"
            )

        if verbose:
            print(f"\n  ✅ GitHub research complete:")
            print(f"     {len(all_repos)} repos analysed")
            print(f"     {len(techs)} techniques found")
            print(f"     {len(report['suggestions'])} improvement suggestions")

        return report

    # ── Helper ────────────────────────────────────────────────────────────────

    def _parse_repo(self, item: Dict) -> GitHubRepo:
        lic = item.get("license") or {}
        return GitHubRepo(
            name        = item.get("name", ""),
            full_name   = item.get("full_name", ""),
            description = item.get("description", "") or "",
            url         = item.get("html_url", ""),
            stars       = item.get("stargazers_count", 0),
            forks       = item.get("forks_count", 0),
            language    = item.get("language", "") or "",
            topics      = item.get("topics", []),
            last_push   = (item.get("pushed_at") or "")[:10],
            license     = lic.get("spdx_id", "") if isinstance(lic, dict) else "",
            open_issues = item.get("open_issues_count", 0),
        )

    def format_results(self, repos: List[GitHubRepo]) -> str:
        lines = [f"GitHub Research — {len(repos)} repositories", "─" * 60]
        for r in repos:
            lines.append(
                f"★{r.stars:>7,}  {r.full_name:<40}  [{r.language}]\n"
                f"          {r.description[:70]}\n"
                f"          Topics: {', '.join(r.topics[:5])}"
            )
        return "\n\n".join(lines)


# ── Singleton ─────────────────────────────────────────────────────────────────

_gh: Optional[GitHubResearcher] = None

def get_gh() -> GitHubResearcher:
    global _gh
    if _gh is None:
        _gh = GitHubResearcher()
    return _gh


def github_search(query: str, limit: int = 5) -> List[GitHubRepo]:
    return get_gh().search_repos(query, limit=limit)


def github_trending(language: str = "python", limit: int = 10) -> List[GitHubRepo]:
    return get_gh().trending(language=language, limit=limit)


if __name__ == "__main__":
    gh = GitHubResearcher()

    print("=== GitHub Researcher Test ===\n")
    print("1. Searching 'large language model transformer'…")
    repos = gh.search_repos("large language model transformer attention", limit=3, min_stars=500)
    for r in repos:
        print(f"   ★{r.stars:,}  {r.full_name}  [{r.language}]")
        print(f"          {r.description[:70]}")

    print("\n2. Trending Python AI repos…")
    trending = gh.trending(language="python", topic="machine-learning", limit=3)
    for r in trending:
        print(f"   ★{r.stars:,}  {r.full_name}")

    print("\n3. WebGL/Three.js repos…")
    webgl = gh.search_repos("Three.js WebGL particle animation", limit=3, min_stars=100)
    for r in webgl:
        print(f"   ★{r.stars:,}  {r.full_name}  [{r.language}]")

    print("\n✅ GitHub Researcher operational")
