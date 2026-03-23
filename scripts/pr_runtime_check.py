from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from runtime_tools import (
    asdict_result,
    discover_root,
    ensure_runtime_env,
    resolve_git_exe,
    resolve_npm_cmd,
    resolve_python_exe,
    run_command,
    write_report,
)


@dataclass
class CheckResult:
    ok: bool
    detail: str


def _check_repo_rw(root: Path) -> CheckResult:
    probe = root / ".tmp_runtime_write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return CheckResult(True, f"writable:{root}")
    except Exception as exc:
        return CheckResult(False, f"repo write failed: {exc}")


def _check_python(root: Path) -> tuple[CheckResult, dict[str, Any]]:
    try:
        python_exe = resolve_python_exe(root)
        result = run_command(python_exe, ["--version"], timeout=15, check=False)
        ok = result.exit_code == 0
        detail = f"{python_exe} => {(result.stdout or result.stderr).strip()}"
        return CheckResult(ok, detail), asdict_result(result)
    except Exception as exc:
        return CheckResult(False, str(exc)), {}


def _check_npm() -> tuple[CheckResult, dict[str, Any]]:
    try:
        npm_cmd = resolve_npm_cmd()
        result = run_command(npm_cmd, ["--version"], timeout=15, check=False)
        ok = result.exit_code == 0
        detail = f"{npm_cmd} => {(result.stdout or result.stderr).strip()}"
        return CheckResult(ok, detail), asdict_result(result)
    except Exception as exc:
        return CheckResult(False, str(exc)), {}


def _check_git(root: Path) -> tuple[CheckResult, dict[str, Any], dict[str, Any]]:
    try:
        git_exe = resolve_git_exe()
        version = run_command(git_exe, ["--version"], timeout=15, check=False)
        status = run_command(git_exe, ["status", "--short", "--branch"], cwd=root, timeout=20, check=False)
        ok = version.exit_code == 0 and status.exit_code == 0
        detail = f"{git_exe} => {(version.stdout or version.stderr).strip()}"
        return CheckResult(ok, detail), asdict_result(version), asdict_result(status)
    except Exception as exc:
        return CheckResult(False, str(exc)), {}, {}


def main() -> int:
    runtime_snapshot = ensure_runtime_env()
    root = discover_root()
    report_dir = root / "data" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    python_check, python_raw = _check_python(root)
    npm_check, npm_raw = _check_npm()
    git_check, git_version_raw, git_status_raw = _check_git(root)
    repo_rw_check = _check_repo_rw(root)

    checks = {
        "runtime_shell": CheckResult(bool(runtime_snapshot.get("ComSpec")), runtime_snapshot.get("ComSpec", "")),
        "runtime_pathext": CheckResult(".EXE" in runtime_snapshot.get("PATHEXT", "").upper(), runtime_snapshot.get("PATHEXT", "")),
        "python": python_check,
        "npm": npm_check,
        "git": git_check,
        "repo_rw": repo_rw_check,
    }
    failed = [key for key, value in checks.items() if not value.ok]
    status = "pass" if not failed else "fail"

    payload = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "failed_checks": failed,
        "runtime_env": runtime_snapshot,
        "checks": {name: asdict(item) for name, item in checks.items()},
        "raw": {
            "python": python_raw,
            "npm": npm_raw,
            "git_version": git_version_raw,
            "git_status": git_status_raw,
        },
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"pr-runtime-check-{ts}.json"
    latest_path = report_dir / "pr-runtime-check-latest.json"
    write_report(report_path, payload)
    write_report(latest_path, payload)

    print(f"[pr-runtime-check] status={status}")
    print(f"[pr-runtime-check] report={report_path}")
    if failed:
        print(f"[pr-runtime-check] failed: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
