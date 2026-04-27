"""
AILEX — web_researcher.py
Multi-source academic and web research engine.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Free APIs — no keys required:
  ↳ Wikipedia REST API         en.wikipedia.org/api/rest_v1
  ↳ arXiv API                  export.arxiv.org/api/query
  ↳ Semantic Scholar           api.semanticscholar.org/graph/v1
  ↳ DuckDuckGo Instant Answer  api.duckduckgo.com
  ↳ PubMed E-utilities         eutils.ncbi.nlm.nih.gov/entrez/eutils
  ↳ CrossRef                   api.crossref.org/works
  ↳ CORE (open access papers)  api.core.ac.uk/v3
  ↳ OpenAlex                   api.openalex.org/works

Paid/keyed (optional, set env vars):
  ↳ Google Custom Search       GOOGLE_CSE_KEY + GOOGLE_CSE_ID
  ↳ CORE API                   CORE_API_KEY (higher limits)

Usage:
    from ailex_pilot.web_researcher import WebResearcher
    r = WebResearcher()

    # Quick topic search across all free sources:
    results = r.research("transformer attention mechanisms", max_per_source=3)
    for res in results:
        print(res.title, res.source, res.url)

    # Single source:
    papers = r.arxiv("large language models RLHF", max_results=5)
    wiki   = r.wikipedia("Transformer (machine learning)")
    papers = r.semantic_scholar("GSAP animation performance", limit=5)
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ResearchResult:
    title:      str
    abstract:   str         # summary / abstract / first paragraph
    url:        str
    source:     str         # "arxiv" | "wikipedia" | "semantic_scholar" | etc.
    date:       str         # ISO date or year
    authors:    List[str]   = field(default_factory=list)
    doi:        str         = ""
    citations:  int         = 0
    relevance:  float       = 1.0   # 0–1
    tags:       List[str]   = field(default_factory=list)
    raw:        Dict        = field(default_factory=dict)

    def snippet(self, chars: int = 200) -> str:
        return self.abstract[:chars] + ("…" if len(self.abstract) > chars else "")

    def __str__(self) -> str:
        return (
            f"[{self.source.upper()}] {self.title}\n"
            f"  Authors: {', '.join(self.authors[:3])}\n"
            f"  Date: {self.date} | Citations: {self.citations}\n"
            f"  {self.snippet()}\n"
            f"  {self.url}"
        )


# ── HTTP helper ───────────────────────────────────────────────────────────────

_UA = "AILEX-Research/6.0 (academic bot; contact: ailex@research.int)"

def _get(url: str, timeout: int = 15) -> Optional[bytes]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None

def _get_json(url: str, timeout: int = 15) -> Optional[Dict]:
    data = _get(url, timeout)
    if data:
        try:
            return json.loads(data.decode("utf-8"))
        except Exception:
            pass
    return None


# ── Main researcher ───────────────────────────────────────────────────────────

class WebResearcher:
    """
    Multi-source research engine. All free APIs, no keys required for base usage.
    Combines Wikipedia, arXiv, Semantic Scholar, DuckDuckGo, PubMed, CrossRef, OpenAlex.
    """

    # ── Wikipedia ─────────────────────────────────────────────────────────────

    def wikipedia(self, query: str, lang: str = "en") -> Optional[ResearchResult]:
        """Get Wikipedia summary for a topic."""
        # First: search for the best matching page
        search_url = (
            f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search"
            f"&srsearch={urllib.parse.quote(query)}&srlimit=1&format=json"
        )
        data = _get_json(search_url)
        if not data:
            return None

        hits = data.get("query", {}).get("search", [])
        if not hits:
            return None

        title = hits[0]["title"]
        slug  = urllib.parse.quote(title.replace(" ", "_"))

        # Get summary
        summary_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{slug}"
        summary = _get_json(summary_url)
        if not summary:
            return None

        return ResearchResult(
            title    = summary.get("title", title),
            abstract = summary.get("extract", ""),
            url      = summary.get("content_urls", {}).get("desktop", {}).get("page", f"https://{lang}.wikipedia.org/wiki/{slug}"),
            source   = "wikipedia",
            date     = summary.get("timestamp", "")[:10],
            tags     = ["encyclopedia", "general-knowledge"],
        )

    def wikipedia_search(self, query: str, limit: int = 5, lang: str = "en") -> List[ResearchResult]:
        """Search Wikipedia and return multiple results."""
        search_url = (
            f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search"
            f"&srsearch={urllib.parse.quote(query)}&srlimit={limit}&format=json"
        )
        data = _get_json(search_url)
        if not data:
            return []

        results = []
        for hit in data.get("query", {}).get("search", []):
            title  = hit["title"]
            slug   = urllib.parse.quote(title.replace(" ", "_"))
            # Clean snippet
            snippet = re.sub(r"<[^>]+>", "", hit.get("snippet", ""))
            results.append(ResearchResult(
                title    = title,
                abstract = snippet,
                url      = f"https://{lang}.wikipedia.org/wiki/{slug}",
                source   = "wikipedia",
                date     = "",
                tags     = ["encyclopedia"],
            ))
        return results

    # ── arXiv ─────────────────────────────────────────────────────────────────

    def arxiv(
        self, query: str, max_results: int = 5,
        sort_by: str = "relevance",  # relevance | lastUpdatedDate | submittedDate
        categories: Optional[List[str]] = None,
    ) -> List[ResearchResult]:
        """Search arXiv preprint server."""
        cat_filter = ""
        if categories:
            cat_filter = " AND (" + " OR ".join(f"cat:{c}" for c in categories) + ")"

        q = urllib.parse.quote(f"all:{query}{cat_filter}")
        url = (
            f"http://export.arxiv.org/api/query?"
            f"search_query={q}&max_results={max_results}"
            f"&sortBy={sort_by}&sortOrder=descending"
        )
        data = _get(url)
        if not data:
            return []

        try:
            raw  = data.decode("utf-8")
            root = ET.fromstring(raw)
            # Use Clark notation {ns}tag — more reliable than prefix maps
            A    = "http://www.w3.org/2005/Atom"
            entries = root.findall(f"{{{A}}}entry")
        except Exception:
            return []

        results = []
        for e in entries:
            def _t(tag: str) -> str:
                el = e.find(f"{{{A}}}{tag}")
                return (el.text or "").strip() if el is not None else ""

            title     = _t("title").replace("\n", " ")
            summary   = _t("summary").replace("\n", " ")
            published = _t("published")

            link = next(
                (l.get("href", "") for l in e.findall(f"{{{A}}}link")
                 if l.get("rel") == "alternate"),
                "",
            )
            authors = [
                (a.find(f"{{{A}}}name").text or "").strip()
                for a in e.findall(f"{{{A}}}author")
                if a.find(f"{{{A}}}name") is not None
            ]
            categories_tags = [t.get("term", "") for t in e.findall(f"{{{A}}}category")]

            if title:
                results.append(ResearchResult(
                    title    = title,
                    abstract = summary,
                    url      = link,
                    source   = "arxiv",
                    date     = published[:10],
                    authors  = [a for a in authors if a],
                    tags     = categories_tags[:5],
                ))
        return results

    # ── Semantic Scholar ──────────────────────────────────────────────────────

    def semantic_scholar(
        self, query: str, limit: int = 5,
        fields: str = "title,abstract,authors,year,citationCount,externalIds,openAccessPdf",
        min_citations: int = 0,
    ) -> List[ResearchResult]:
        """Search Semantic Scholar academic database."""
        url = (
            f"https://api.semanticscholar.org/graph/v1/paper/search"
            f"?query={urllib.parse.quote(query)}&limit={limit}&fields={fields}"
        )
        data = _get_json(url)
        if not data:
            return []

        results = []
        for p in data.get("data", []):
            citations = p.get("citationCount", 0) or 0
            if citations < min_citations:
                continue

            doi  = (p.get("externalIds") or {}).get("DOI", "")
            pdf  = (p.get("openAccessPdf") or {}).get("url", "")
            url_ = pdf or (f"https://doi.org/{doi}" if doi else "")
            if not url_:
                pid = p.get("paperId", "")
                url_ = f"https://www.semanticscholar.org/paper/{pid}" if pid else ""

            results.append(ResearchResult(
                title    = p.get("title", ""),
                abstract = p.get("abstract", "") or "",
                url      = url_,
                source   = "semantic_scholar",
                date     = str(p.get("year", "")),
                authors  = [a.get("name", "") for a in (p.get("authors") or [])[:5]],
                doi      = doi,
                citations = citations,
            ))
        return results

    # ── DuckDuckGo Instant Answer ─────────────────────────────────────────────

    def duckduckgo(self, query: str) -> Optional[ResearchResult]:
        """DuckDuckGo Instant Answer API — great for definitions and summaries."""
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        data = _get_json(url)
        if not data:
            return None

        abstract = data.get("AbstractText", "") or data.get("Answer", "")
        if not abstract:
            # Try related topics
            topics = data.get("RelatedTopics", [])
            if topics:
                abstract = topics[0].get("Text", "") if isinstance(topics[0], dict) else ""

        if not abstract:
            return None

        return ResearchResult(
            title    = data.get("Heading", query),
            abstract = abstract,
            url      = data.get("AbstractURL", "") or data.get("AbstractSource", ""),
            source   = "duckduckgo",
            date     = "",
            tags     = ["web", "instant-answer"],
        )

    def duckduckgo_related(self, query: str, limit: int = 5) -> List[ResearchResult]:
        """Get DuckDuckGo related topics."""
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
        data = _get_json(url)
        if not data:
            return []

        results = []
        for topic in data.get("RelatedTopics", [])[:limit]:
            if not isinstance(topic, dict) or not topic.get("Text"):
                continue
            results.append(ResearchResult(
                title    = topic.get("Text", "")[:80],
                abstract = topic.get("Text", ""),
                url      = topic.get("FirstURL", ""),
                source   = "duckduckgo",
                date     = "",
                tags     = ["web", "related"],
            ))
        return results

    # ── PubMed ────────────────────────────────────────────────────────────────

    def pubmed(self, query: str, max_results: int = 5) -> List[ResearchResult]:
        """Search PubMed biomedical literature database."""
        base   = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        search_url = (
            f"{base}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(query)}"
            f"&retmax={max_results}&retmode=json&sort=relevance"
        )
        data = _get_json(search_url)
        if not data:
            return []

        ids = data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        # Fetch summaries
        fetch_url = f"{base}/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json"
        summary   = _get_json(fetch_url)
        if not summary:
            return []

        results = []
        for uid, doc in summary.get("result", {}).items():
            if uid == "uids":
                continue
            authors = [
                a.get("name", "") for a in doc.get("authors", [])[:5]
                if isinstance(a, dict)
            ]
            results.append(ResearchResult(
                title    = doc.get("title", ""),
                abstract = doc.get("source", "") + " " + str(doc.get("pubdate", "")),
                url      = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                source   = "pubmed",
                date     = doc.get("pubdate", "")[:4],
                authors  = [a for a in authors if a],
            ))
        return results

    # ── CrossRef ─────────────────────────────────────────────────────────────

    def crossref(self, query: str, limit: int = 5) -> List[ResearchResult]:
        """Search CrossRef academic metadata database."""
        url = (
            f"https://api.crossref.org/works?query={urllib.parse.quote(query)}"
            f"&rows={limit}&sort=relevance&mailto=ailex@research.int"
        )
        data = _get_json(url)
        if not data:
            return []

        results = []
        for item in data.get("message", {}).get("items", []):
            doi   = item.get("DOI", "")
            title_list = item.get("title", [])
            title = title_list[0] if title_list else ""

            authors = []
            for a in item.get("author", [])[:5]:
                name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                if name:
                    authors.append(name)

            abstract = ""
            if "abstract" in item:
                abstract = re.sub(r"<[^>]+>", "", item["abstract"])

            date = ""
            if "published" in item:
                parts = item["published"].get("date-parts", [[]])
                date  = "-".join(str(p) for p in parts[0]) if parts else ""

            results.append(ResearchResult(
                title    = title,
                abstract = abstract,
                url      = f"https://doi.org/{doi}" if doi else "",
                source   = "crossref",
                date     = date,
                authors  = authors,
                doi      = doi,
                citations = item.get("is-referenced-by-count", 0),
            ))
        return results

    # ── OpenAlex ─────────────────────────────────────────────────────────────

    def openalex(self, query: str, limit: int = 5) -> List[ResearchResult]:
        """Search OpenAlex — largest open scholarly metadata database."""
        url = (
            f"https://api.openalex.org/works?search={urllib.parse.quote(query)}"
            f"&per-page={limit}&sort=cited_by_count:desc"
            f"&mailto=ailex@research.int"
        )
        data = _get_json(url)
        if not data:
            return []

        results = []
        for work in data.get("results", []):
            title = work.get("title", "") or ""
            abstract = ""
            # OpenAlex stores abstract as inverted index — reconstruct it
            if "abstract_inverted_index" in work and work["abstract_inverted_index"]:
                try:
                    inv = work["abstract_inverted_index"]
                    word_pos = [(w, p) for w, positions in inv.items() for p in positions]
                    word_pos.sort(key=lambda x: x[1])
                    abstract = " ".join(w for w, _ in word_pos[:100])
                except Exception:
                    pass

            doi = (work.get("ids") or {}).get("doi", "").replace("https://doi.org/", "")
            url_ = work.get("open_access", {}).get("oa_url") or \
                   (f"https://doi.org/{doi}" if doi else work.get("id", ""))
            authors = [
                a.get("author", {}).get("display_name", "")
                for a in (work.get("authorships") or [])[:5]
            ]
            year = work.get("publication_year", "")

            results.append(ResearchResult(
                title     = title,
                abstract  = abstract,
                url       = url_,
                source    = "openalex",
                date      = str(year),
                authors   = [a for a in authors if a],
                doi       = doi,
                citations = work.get("cited_by_count", 0),
            ))
        return results

    # ── Google Custom Search (optional, requires API key) ────────────────────

    def google_search(
        self, query: str, limit: int = 5,
        site_restrict: str = "",  # e.g., "site:arxiv.org"
    ) -> List[ResearchResult]:
        """Google Custom Search — requires GOOGLE_CSE_KEY + GOOGLE_CSE_ID env vars."""
        key = os.environ.get("GOOGLE_CSE_KEY", "")
        cx  = os.environ.get("GOOGLE_CSE_ID", "")
        if not key or not cx:
            return []  # Not configured

        q = f"{query} {site_restrict}".strip()
        url = (
            f"https://www.googleapis.com/customsearch/v1"
            f"?key={key}&cx={cx}&q={urllib.parse.quote(q)}&num={min(limit,10)}"
        )
        data = _get_json(url)
        if not data:
            return []

        results = []
        for item in data.get("items", []):
            results.append(ResearchResult(
                title    = item.get("title", ""),
                abstract = item.get("snippet", ""),
                url      = item.get("link", ""),
                source   = "google",
                date     = item.get("pagemap", {}).get("metatags", [{}])[0].get("date", ""),
                tags     = ["web"],
            ))
        return results

    # ── Aggregated research ───────────────────────────────────────────────────

    def research(
        self,
        query:          str,
        sources:        List[str] = ["arxiv", "semantic_scholar", "openalex", "wikipedia", "duckduckgo"],
        max_per_source: int       = 3,
        deduplicate:    bool      = True,
        min_abstract:   int       = 30,
    ) -> List[ResearchResult]:
        """
        Comprehensive research across multiple sources.
        Returns deduplicated, relevance-ranked results.

        Args:
            query:          Search query
            sources:        List of sources to use (or ["all"] for everything)
            max_per_source: Max results per source
            deduplicate:    Remove duplicate titles
            min_abstract:   Skip results with abstract shorter than this

        Example:
            results = researcher.research(
                "GSAP animation web performance",
                sources=["arxiv", "semantic_scholar", "openalex"],
                max_per_source=3,
            )
        """
        all_sources = {
            "arxiv":            lambda: self.arxiv(query, max_per_source),
            "semantic_scholar": lambda: self.semantic_scholar(query, max_per_source),
            "openalex":         lambda: self.openalex(query, max_per_source),
            "crossref":         lambda: self.crossref(query, max_per_source),
            "pubmed":           lambda: self.pubmed(query, max_per_source),
            "wikipedia":        lambda: self.wikipedia_search(query, max_per_source),
            "duckduckgo":       lambda: self.duckduckgo_related(query, max_per_source),
            "google":           lambda: self.google_search(query, max_per_source),
        }

        if "all" in sources:
            sources = list(all_sources.keys())

        collected: List[ResearchResult] = []
        for src in sources:
            if src not in all_sources:
                continue
            try:
                results = all_sources[src]()
                collected.extend(results)
                time.sleep(0.3)  # rate limit courtesy
            except Exception:
                pass

        # Filter short abstracts
        if min_abstract > 0:
            collected = [r for r in collected if len(r.abstract) >= min_abstract]

        # Deduplicate by title similarity
        if deduplicate:
            seen: set = set()
            unique: List[ResearchResult] = []
            for r in collected:
                key = re.sub(r"\W+", "", r.title.lower())[:50]
                if key not in seen:
                    seen.add(key)
                    unique.append(r)
            collected = unique

        # Sort: cited papers first, then by source quality
        SOURCE_WEIGHT = {"openalex": 5, "semantic_scholar": 4, "arxiv": 4,
                         "crossref": 3, "pubmed": 3, "wikipedia": 2, "duckduckgo": 1}
        collected.sort(
            key=lambda r: (r.citations * 0.01 + SOURCE_WEIGHT.get(r.source, 1)),
            reverse=True
        )

        return collected

    def format_results(self, results: List[ResearchResult], max_chars: int = 120) -> str:
        """Human-readable summary of research results."""
        if not results:
            return "No results found."
        lines = [f"Research Results ({len(results)} papers/articles)", "─" * 60]
        for i, r in enumerate(results, 1):
            lines.append(
                f"{i}. [{r.source.upper()}] {r.title[:70]}\n"
                f"   {r.date} | {', '.join(r.authors[:2])} | ★ {r.citations}\n"
                f"   {r.abstract[:max_chars]}…\n"
                f"   {r.url[:80]}"
            )
        return "\n\n".join(lines)


# ── Convenience singleton ──────────────────────────────────────────────────────

_researcher: Optional[WebResearcher] = None

def get_researcher() -> WebResearcher:
    global _researcher
    if _researcher is None:
        _researcher = WebResearcher()
    return _researcher


def quick_research(query: str, max_per_source: int = 3) -> List[ResearchResult]:
    """Quick research across all free sources."""
    return get_researcher().research(
        query,
        sources=["arxiv", "semantic_scholar", "openalex", "wikipedia"],
        max_per_source=max_per_source,
    )


if __name__ == "__main__":
    r = WebResearcher()

    print("Testing Wikipedia...")
    wiki = r.wikipedia("Transformer (machine learning)")
    if wiki:
        print(f"  ✅ {wiki.title}: {wiki.snippet(100)}")

    print("\nTesting DuckDuckGo...")
    ddg = r.duckduckgo("GSAP animation library javascript")
    if ddg:
        print(f"  ✅ {ddg.title}: {ddg.snippet(100)}")

    print("\nTesting arXiv...")
    papers = r.arxiv("large language models instruction tuning", max_results=2)
    for p in papers:
        print(f"  ✅ {p.title[:60]}... ({p.date})")

    print("\nTesting Semantic Scholar...")
    ss = r.semantic_scholar("attention is all you need transformer", limit=2)
    for p in ss:
        print(f"  ✅ {p.title[:60]} | ★ {p.citations}")

    print("\nTesting OpenAlex...")
    oa = r.openalex("neural network optimization gradient descent", limit=2)
    for p in oa:
        print(f"  ✅ {p.title[:60]} | ★ {p.citations}")

    print("\n✅ WebResearcher operational — 7 sources available")
