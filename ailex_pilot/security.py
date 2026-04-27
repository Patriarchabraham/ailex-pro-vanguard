"""
AILEX Pilot — security.py
SAST + secret detection + CVE scanner.
Runs on every commit/review without external services.
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# Secret patterns — high-confidence leaked credential signatures
SECRET_PATTERNS: List[Tuple[str, str]] = [
    (r"sk-ant-[a-zA-Z0-9\-_]{20,}", "Anthropic API key"),
    (r"sk-[a-zA-Z0-9]{48}", "OpenAI API key"),
    (r"AIza[0-9A-Za-z\-_]{35}", "Google API key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub personal token"),
    (r"ghr_[a-zA-Z0-9]{36}", "GitHub refresh token"),
    (r"r8_[a-zA-Z0-9]{40}", "Replicate API token"),
    (r"xoxb-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{24}", "Slack bot token"),
    (r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----", "Private key"),
    (r"(?:password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{8,}['\"]", "Hardcoded password"),
    (r"(?:secret|token|api_key)\s*[:=]\s*['\"][a-zA-Z0-9\-_]{16,}['\"]", "Hardcoded secret"),
    (r"mongodb\+srv://[^:]+:[^@]+@", "MongoDB connection string with credentials"),
    (r"postgres://[^:]+:[^@]+@", "PostgreSQL connection string with credentials"),
    (r"mysql://[^:]+:[^@]+@", "MySQL connection string with credentials"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
]

# SAST patterns — common vulnerabilities
SAST_PATTERNS: List[Tuple[str, str, str]] = [
    # (pattern, language, description)
    (r"eval\s*\(", "js,py", "eval() — arbitrary code execution"),
    (r"exec\s*\(", "py", "exec() — arbitrary code execution"),
    (r"os\.system\s*\(", "py", "os.system() — command injection risk"),
    (r"subprocess\.call\s*\(.+shell\s*=\s*True", "py", "subprocess shell=True — injection risk"),
    (r"__import__\s*\(", "py", "Dynamic import — code injection risk"),
    (r"pickle\.loads?\s*\(", "py", "pickle deserialization — RCE risk"),
    (r"yaml\.load\s*\([^,]+\)", "py", "yaml.load without Loader — RCE risk"),
    (r"innerHTML\s*=\s*[^\"']", "js", "innerHTML assignment — XSS risk"),
    (r"dangerouslySetInnerHTML", "js", "dangerouslySetInnerHTML — XSS risk"),
    (r"document\.write\s*\(", "js", "document.write — XSS risk"),
    (r"\.query\s*\(\s*[f\"'`][^)]*\$\{", "js", "SQL injection — string interpolation in query"),
    (r"cursor\.execute\s*\(\s*[f\"'][^,)]+%", "py", "SQL injection — string formatting in query"),
    (r"Math\.random\s*\(\)", "js", "Math.random() — not cryptographically secure"),
    (r"md5\s*\(", "py,js", "MD5 — weak hash for passwords"),
    (r"SHA1\s*\(|sha1\s*\(", "py,js", "SHA1 — weak hash"),
    (r"verify\s*=\s*False", "py", "SSL verification disabled"),
    (r"ssl\.wrap_socket.*verify_mode=ssl\.CERT_NONE", "py", "SSL cert verification disabled"),
]


@dataclass
class SecurityFinding:
    file:        str
    line:        int
    kind:        str     # "secret" | "sast" | "cve"
    severity:    str     # "critical" | "high" | "medium" | "low"
    description: str
    snippet:     str


@dataclass
class SecurityReport:
    files_scanned: int
    findings:      List[SecurityFinding]
    secrets:       List[SecurityFinding]
    sast:          List[SecurityFinding]
    cves:          List[str]
    score:         float   # 0.0 = critical issues, 1.0 = clean
    summary:       str


class SecurityScanner:
    """SAST + secret detection + dependency CVE scanner."""

    IGNORE_DIRS = {".git", "node_modules", "__pycache__", "dist", "build",
                   "venv", ".venv", "test", "tests", "fixtures"}
    IGNORE_FILES = {"package-lock.json", "yarn.lock", "*.min.js"}

    def scan_project(self, root: str) -> SecurityReport:
        findings: List[SecurityFinding] = []
        files_scanned = 0

        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in (".py", ".js", ".ts", ".tsx", ".jsx", ".env",
                               ".yml", ".yaml", ".json", ".sh", ".bash"):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    content = open(fpath, encoding="utf-8", errors="ignore").read()
                    findings.extend(self._scan_secrets(fpath, content))
                    findings.extend(self._scan_sast(fpath, content, ext))
                    files_scanned += 1
                except (OSError, PermissionError):
                    pass

        cves = self._scan_cves(root)
        secrets = [f for f in findings if f.kind == "secret"]
        sast    = [f for f in findings if f.kind == "sast"]
        score   = max(0.0, 1.0 - len(secrets) * 0.3 - len(sast) * 0.1 - len(cves) * 0.05)

        return SecurityReport(
            files_scanned=files_scanned, findings=findings,
            secrets=secrets, sast=sast, cves=cves,
            score=round(score, 2),
            summary=self._summary(files_scanned, secrets, sast, cves),
        )

    def _scan_secrets(self, path: str, content: str) -> List[SecurityFinding]:
        findings: List[SecurityFinding] = []
        # Skip test files and example files
        if any(x in path.lower() for x in (".example", ".sample", "test_", "_test", "spec")):
            return findings
        for pattern, desc in SECRET_PATTERNS:
            for m in re.finditer(pattern, content, re.IGNORECASE):
                line = content[:m.start()].count("\n") + 1
                snippet = m.group(0)[:40] + "..."
                findings.append(SecurityFinding(
                    file=path, line=line, kind="secret",
                    severity="critical", description=desc, snippet=snippet,
                ))
        return findings

    def _scan_sast(self, path: str, content: str, ext: str) -> List[SecurityFinding]:
        findings: List[SecurityFinding] = []
        lang = "py" if ext == ".py" else "js"
        for pattern, langs, desc in SAST_PATTERNS:
            if lang not in langs:
                continue
            for m in re.finditer(pattern, content, re.IGNORECASE):
                line  = content[:m.start()].count("\n") + 1
                sev   = "high" if any(w in desc.lower() for w in ("injection", "rce", "xss")) else "medium"
                findings.append(SecurityFinding(
                    file=path, line=line, kind="sast",
                    severity=sev, description=desc,
                    snippet=content[m.start():m.start()+60].strip(),
                ))
        return findings

    def _scan_cves(self, root: str) -> List[str]:
        """Check dependencies for known CVEs via pip/npm audit."""
        cves: List[str] = []
        # Python
        req_path = os.path.join(root, "requirements.txt")
        if os.path.exists(req_path):
            try:
                r = subprocess.run(["pip-audit", "--requirement", req_path, "-f", "json"],
                                   capture_output=True, text=True, timeout=30)
                if r.returncode == 0:
                    import json
                    data = json.loads(r.stdout)
                    for dep in data.get("dependencies", []):
                        for v in dep.get("vulns", []):
                            cves.append(f"{dep['name']}: {v['id']} — {v.get('description','')[:60]}")
            except Exception:
                pass
        # Node.js
        pkg_path = os.path.join(root, "package.json")
        if os.path.exists(pkg_path):
            try:
                r = subprocess.run(["npm", "audit", "--json"],
                                   capture_output=True, text=True, timeout=30,
                                   cwd=root)
                if r.returncode != 0:
                    import json
                    data = json.loads(r.stdout)
                    vulns = data.get("vulnerabilities", {})
                    for name, info in list(vulns.items())[:10]:
                        sev = info.get("severity", "")
                        if sev in ("critical", "high"):
                            cves.append(f"{name}: {sev}")
            except Exception:
                pass
        return cves[:20]

    def _summary(self, n: int, secrets: List, sast: List, cves: List) -> str:
        if not secrets and not sast and not cves:
            return f"✓ Clean — {n} files scanned, no issues found"
        parts = []
        if secrets: parts.append(f"{len(secrets)} secrets exposed")
        if sast:    parts.append(f"{len(sast)} SAST issues")
        if cves:    parts.append(f"{len(cves)} CVEs in dependencies")
        return f"⚠ {n} files — " + " | ".join(parts)

    def format_report(self, r: SecurityReport) -> str:
        lines = [
            f"Security Scan: {r.files_scanned} files | score={r.score:.0%}",
            r.summary, "",
        ]
        if r.secrets:
            lines.append("SECRETS (fix immediately):")
            for f in r.secrets[:5]:
                lines.append(f"  🔴 {f.file}:{f.line} — {f.description}")
        if r.sast:
            lines.append("\nSAST Issues:")
            for f in r.sast[:8]:
                icon = "🔴" if f.severity == "high" else "🟡"
                lines.append(f"  {icon} {f.file}:{f.line} — {f.description}")
        if r.cves:
            lines.append("\nDependency CVEs:")
            for c in r.cves[:5]:
                lines.append(f"  🟠 {c}")
        return "\n".join(lines)
