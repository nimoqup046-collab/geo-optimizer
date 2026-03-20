from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


def discover_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in [here.parent.parent, Path.cwd().resolve()]:
        if (candidate / "backend").exists() and (candidate / "frontend").exists():
            return candidate
    return here.parent.parent


ROOT = discover_root()
REPORT_DIR = ROOT / "data" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_GITIGNORE_PATTERNS = [
    "tmp_*",
    "railway_*",
    "_deploy_backend*/",
    "_deploy_frontend*/",
    "backend/.env",
    "backend/.venv/",
    "frontend/dist/",
]

RISKY_PATH_PATTERNS = [
    "tmp_",
    "railway_",
    "_deploy_backend",
    "_deploy_frontend",
    "backend/.env",
]

SECRET_REGEXES = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"\b[A-Za-z0-9]{32}\.[A-Za-z0-9]{8,}\b"),
]

SECRET_MARKERS = [
    "ZHIPU_API_KEY=",
    "OPENROUTER_API_KEY=",
    "DOUBAO_API_KEY=",
    "ANTHROPIC_AUTH_TOKEN=",
    "RAILWAY_TOKEN=",
]

SCAN_EXT = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".env", ".ts", ".tsx", ".js", ".bat", ".ps1"}
SCAN_EXCLUDE_SEGMENTS = {"node_modules", ".venv", "_deploy_backend", "_deploy_frontend", "__pycache__"}


@dataclass
class CheckResult:
    ok: bool
    detail: str


def read_gitignore() -> str:
    path = ROOT / ".gitignore"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def check_gitignore_rules() -> CheckResult:
    content = read_gitignore()
    missing = [rule for rule in REQUIRED_GITIGNORE_PATTERNS if rule not in content]
    if missing:
        return CheckResult(False, f".gitignore missing: {', '.join(missing)}")
    return CheckResult(True, ".gitignore rules present")


def find_git_exe() -> Path | None:
    candidates = [
        Path(r"C:\Program Files\Git\cmd\git.exe"),
        Path(r"C:\Program Files\Git\bin\git.exe"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def check_git_status_for_risky_files() -> CheckResult:
    git_dir = ROOT / ".git"
    if not git_dir.exists():
        return CheckResult(True, "git repo not initialized yet (skip status check)")

    git_exe = find_git_exe()
    if not git_exe:
        return CheckResult(False, "git.exe not found")

    proc = subprocess.run(
        [str(git_exe), "status", "--porcelain"],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=20,
    )
    if proc.returncode != 0:
        return CheckResult(False, f"git status failed: {(proc.stdout or '').strip()}")

    risky: list[str] = []
    for line in (proc.stdout or "").splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        normalized = path.replace("\\", "/")
        if any(marker in normalized for marker in RISKY_PATH_PATTERNS):
            risky.append(normalized)

    if risky:
        return CheckResult(False, f"risky staged/untracked files: {', '.join(risky[:12])}")
    return CheckResult(True, "no risky files in git status")


def should_scan(path: Path) -> bool:
    if path.suffix.lower() not in SCAN_EXT:
        return False
    parts = set(path.parts)
    return parts.isdisjoint(SCAN_EXCLUDE_SEGMENTS)


def check_secret_leak() -> CheckResult:
    hits: list[str] = []
    for f in ROOT.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(ROOT)
        rel_text = str(rel).replace("\\", "/")
        if any(seg in rel_text for seg in ("node_modules/", ".venv/", "_deploy_backend", "_deploy_frontend")):
            continue
        if not should_scan(f):
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        for marker in SECRET_MARKERS:
            if marker in text and "your_" not in text and "<" not in text:
                hits.append(f"{rel_text} contains {marker}")
        for regex in SECRET_REGEXES:
            if regex.search(text):
                hits.append(f"{rel_text} matches {regex.pattern}")

    if hits:
        return CheckResult(False, f"potential secrets: {', '.join(hits[:10])}")
    return CheckResult(True, "no obvious secret pattern found")


def check_env_file_presence() -> CheckResult:
    path = ROOT / "backend" / ".env"
    if path.exists():
        return CheckResult(True, "backend/.env exists locally (must remain ignored)")
    return CheckResult(True, "backend/.env not present")


def main() -> int:
    checks: dict[str, CheckResult] = {
        "gitignore_rules": check_gitignore_rules(),
        "git_status_risky": check_git_status_for_risky_files(),
        "env_file_presence": check_env_file_presence(),
        "secret_scan": check_secret_leak(),
    }

    failed = [name for name, result in checks.items() if not result.ok]
    status = "pass" if not failed else "fail"

    payload: dict[str, Any] = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "failed_checks": failed,
        "checks": {name: asdict(result) for name, result in checks.items()},
    }

    report = REPORT_DIR / f"repo-preflight-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    latest = REPORT_DIR / "repo-preflight-latest.json"
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[repo-preflight] status={status}")
    print(f"[repo-preflight] report={report}")
    if failed:
        print(f"[repo-preflight] failed: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
