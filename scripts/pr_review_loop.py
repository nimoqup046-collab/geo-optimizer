from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from runtime_tools import (
    asdict_result,
    discover_root,
    ensure_runtime_env,
    resolve_git_exe,
    resolve_python_exe,
    run_command,
    write_report,
)


RISK_PATTERNS: dict[str, str] = {
    "secret_or_env_change": "backend/.env",
    "runtime_or_deploy": "scripts/",
    "database_or_migration": "backend/database",
    "llm_or_prompt_logic": "backend/services/",
    "api_surface_change": "backend/api/",
    "frontend_core_change": "frontend/src/",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PR review loop helper for local Codex workflow")
    parser.add_argument("--base", default="origin/main", help="Base ref for diff")
    parser.add_argument("--head", default="", help="Head ref for diff; if empty and --pr provided, auto-resolve.")
    parser.add_argument("--pr", type=int, default=0, help="PR number on GitHub (optional)")
    parser.add_argument("--skip-fetch", action="store_true", help="Skip git fetch")
    parser.add_argument("--run-doctor", action="store_true", help="Run scripts/doctor.py")
    parser.add_argument("--run-smoke", action="store_true", help="Run scripts/smoke.py")
    return parser.parse_args()


def run_git(git_exe: str, args: list[str], *, cwd: Path, check: bool = True) -> dict[str, Any]:
    result = run_command(git_exe, args, cwd=cwd, timeout=120, check=check)
    return asdict_result(result)


def fetch_pr_ref(git_exe: str, *, root: Path, pr_number: int) -> tuple[bool, str]:
    local_ref = f"refs/remotes/origin/pr-{pr_number}"
    fetch_ref = f"pull/{pr_number}/head:{local_ref}"
    result = run_command(git_exe, ["fetch", "origin", fetch_ref], cwd=root, timeout=180, check=False)
    if result.exit_code == 0:
        return True, f"origin/pr-{pr_number}"
    detail = (result.stderr or result.stdout).strip()
    return False, detail


def summarize_risks(paths: list[str]) -> list[str]:
    risks: set[str] = set()
    normalized = [p.replace("\\", "/").lower() for p in paths]
    for key, marker in RISK_PATTERNS.items():
        marker_l = marker.lower()
        if any(marker_l in item for item in normalized):
            risks.add(key)
    return sorted(risks)


def run_optional_python_check(python_exe: str, root: Path, script_name: str) -> dict[str, Any]:
    script_path = root / "scripts" / script_name
    result = run_command(python_exe, [str(script_path)], cwd=root, timeout=1800, check=False)
    return asdict_result(result)


def main() -> int:
    args = parse_args()
    runtime_snapshot = ensure_runtime_env()
    root = discover_root()
    report_dir = root / "data" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "status": "fail",
        "timestamp": datetime.now().isoformat(),
        "args": vars(args),
        "runtime_env": runtime_snapshot,
        "steps": {},
        "summary": {},
    }

    try:
        git_exe = resolve_git_exe()
        python_exe = resolve_python_exe(root)
    except Exception as exc:
        payload["summary"]["fatal"] = str(exc)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"pr-review-{ts}.json"
        write_report(report_path, payload)
        write_report(report_dir / "pr-review-latest.json", payload)
        print(f"[pr-review] failed: {exc}")
        print(f"[pr-review] report={report_path}")
        return 1

    payload["steps"]["tooling"] = {
        "git_exe": git_exe,
        "python_exe": python_exe,
    }

    head_ref = args.head.strip()
    if not args.skip_fetch:
        fetch_result = run_command(git_exe, ["fetch", "--all", "--prune"], cwd=root, timeout=300, check=False)
        payload["steps"]["fetch_all"] = asdict_result(fetch_result)

    if args.pr > 0:
        ok, detail = fetch_pr_ref(git_exe, root=root, pr_number=args.pr)
        payload["steps"]["fetch_pr"] = {"ok": ok, "detail": detail}
        if ok and not head_ref:
            head_ref = detail
        elif not ok and not head_ref:
            payload["summary"]["fatal"] = f"fetch PR failed: {detail}"
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = report_dir / f"pr-review-{ts}.json"
            write_report(report_path, payload)
            write_report(report_dir / "pr-review-latest.json", payload)
            print(f"[pr-review] failed: {payload['summary']['fatal']}")
            print(f"[pr-review] report={report_path}")
            return 1

    if not head_ref:
        head_ref = "HEAD"

    diff_result = run_command(
        git_exe,
        ["diff", "--name-status", f"{args.base}...{head_ref}"],
        cwd=root,
        timeout=120,
        check=False,
    )
    payload["steps"]["diff"] = asdict_result(diff_result)
    if diff_result.exit_code != 0:
        payload["summary"]["fatal"] = f"diff failed: {(diff_result.stderr or diff_result.stdout).strip()}"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"pr-review-{ts}.json"
        write_report(report_path, payload)
        write_report(report_dir / "pr-review-latest.json", payload)
        print(f"[pr-review] failed: {payload['summary']['fatal']}")
        print(f"[pr-review] report={report_path}")
        return 1

    changed_rows: list[dict[str, str]] = []
    changed_paths: list[str] = []
    for line in (diff_result.stdout or "").splitlines():
        chunks = line.split("\t")
        if len(chunks) < 2:
            continue
        status, path = chunks[0], chunks[-1]
        changed_rows.append({"status": status, "path": path})
        changed_paths.append(path)

    log_result = run_command(
        git_exe,
        ["log", "--oneline", "--decorate", f"{args.base}..{head_ref}"],
        cwd=root,
        timeout=120,
        check=False,
    )
    payload["steps"]["log"] = asdict_result(log_result)

    optional_checks: dict[str, Any] = {}
    if args.run_doctor:
        optional_checks["doctor"] = run_optional_python_check(python_exe, root, "doctor.py")
    if args.run_smoke:
        optional_checks["smoke"] = run_optional_python_check(python_exe, root, "smoke.py")
    payload["steps"]["optional_checks"] = optional_checks

    failed_optional = [
        name for name, item in optional_checks.items() if isinstance(item, dict) and item.get("exit_code", 1) != 0
    ]
    risks = summarize_risks(changed_paths)

    payload["summary"] = {
        "base": args.base,
        "head": head_ref,
        "changed_files": len(changed_rows),
        "risk_flags": risks,
        "failed_optional_checks": failed_optional,
        "changed": changed_rows,
    }
    payload["status"] = "pass" if not failed_optional else "fail"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"pr-review-{ts}.json"
    write_report(report_path, payload)
    write_report(report_dir / "pr-review-latest.json", payload)

    print(f"[pr-review] status={payload['status']}")
    print(f"[pr-review] changed_files={len(changed_rows)}")
    print(f"[pr-review] risk_flags={','.join(risks) if risks else 'none'}")
    print(f"[pr-review] report={report_path}")
    if failed_optional:
        print(f"[pr-review] optional checks failed: {', '.join(failed_optional)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
