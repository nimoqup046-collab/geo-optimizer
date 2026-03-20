from __future__ import annotations

import json
import os
import socket
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


def discover_root() -> Path:
    candidates: list[Path] = []
    here = Path(__file__).resolve()
    candidates.extend(here.parents)
    cwd = Path.cwd().resolve()
    candidates.append(cwd)
    candidates.extend(cwd.parents)

    checked: set[Path] = set()
    for candidate in candidates:
        if candidate in checked:
            continue
        checked.add(candidate)
        if (candidate / "backend" / "main.py").exists() and (
            candidate / "frontend" / "package.json"
        ).exists():
            return candidate

    # Fallback to the original location assumption.
    return here.parents[1]


ROOT = discover_root()
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
REPORT_DIR = ROOT / "data" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class CheckResult:
    ok: bool
    detail: str


def _run_version(cmd: list[str]) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=12,
        )
        output = (proc.stdout or "").strip()
        if proc.returncode == 0:
            return True, output or "ok"
        return False, output or f"exit={proc.returncode}"
    except Exception as exc:
        return False, str(exc)


def _resolve_python() -> tuple[bool, str]:
    ok, out = _run_version(["py", "-3.13", "--version"])
    if ok:
        return True, "py -3.13"

    py313 = Path(r"C:\Python313\python.exe")
    if py313.exists():
        ok2, out2 = _run_version([str(py313), "--version"])
        return ok2, f"{py313} ({out2})"

    ok3, out3 = _run_version(["python", "--version"])
    return ok3, f"python ({out3})"


def _resolve_npm() -> tuple[bool, str]:
    nvm_symlink = os.getenv("NVM_SYMLINK", "")
    if nvm_symlink:
        npm_cmd = Path(nvm_symlink) / "npm.cmd"
        if npm_cmd.exists():
            ok, out = _run_version([str(npm_cmd), "--version"])
            return ok, f"{npm_cmd} ({out})"

    npm_cmd2 = Path(r"C:\nvm4w\nodejs\npm.cmd")
    if npm_cmd2.exists():
        ok2, out2 = _run_version([str(npm_cmd2), "--version"])
        return ok2, f"{npm_cmd2} ({out2})"

    ok3, out3 = _run_version(["npm", "--version"])
    return ok3, f"npm ({out3})"


def _check_port(port: int) -> CheckResult:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        code = sock.connect_ex(("127.0.0.1", port))
        if code == 0:
            return CheckResult(True, f"127.0.0.1:{port} is occupied (service reachable)")
        return CheckResult(True, f"127.0.0.1:{port} is free")
    finally:
        sock.close()


def _check_env_template() -> CheckResult:
    env_example = BACKEND_DIR / ".env.example"
    env_file = BACKEND_DIR / ".env"
    if not env_example.exists():
        return CheckResult(False, ".env.example missing")
    if not env_file.exists():
        return CheckResult(False, ".env missing in backend directory")

    def parse_keys(path: Path) -> set[str]:
        keys: set[str] = set()
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key = stripped.split("=", 1)[0].strip()
            if key:
                keys.add(key)
        return keys

    required = parse_keys(env_example)
    actual = parse_keys(env_file)
    missing = sorted(required - actual)
    if missing:
        return CheckResult(False, f"missing keys: {', '.join(missing[:8])}")
    return CheckResult(True, "backend/.env keys are aligned with .env.example")


def _check_pid_file(name: str) -> CheckResult:
    pid_file = ROOT / "data" / "run" / f"{name}.pid"
    if not pid_file.exists():
        return CheckResult(False, f"{name}.pid not found")
    value = pid_file.read_text(encoding="utf-8", errors="ignore").strip()
    if not value.isdigit():
        return CheckResult(False, f"{name}.pid invalid value")
    return CheckResult(True, f"{name}.pid={value}")


def main() -> int:
    now = datetime.now().strftime("%Y%m%d_%H%M%S")

    py_ok, py_detail = _resolve_python()
    npm_ok, npm_detail = _resolve_npm()

    checks: dict[str, CheckResult] = {
        "python": CheckResult(py_ok, py_detail),
        "npm": CheckResult(npm_ok, npm_detail),
        "backend_main": CheckResult((BACKEND_DIR / "main.py").exists(), "backend/main.py"),
        "frontend_package": CheckResult((FRONTEND_DIR / "package.json").exists(), "frontend/package.json"),
        "backend_venv": CheckResult((BACKEND_DIR / ".venv").exists(), "backend/.venv"),
        "uploads_dir": CheckResult((ROOT / "data" / "uploads").exists(), "data/uploads"),
        "exports_dir": CheckResult((ROOT / "data" / "exports").exists(), "data/exports"),
        "env_file": _check_env_template(),
        "port_8000": _check_port(8000),
        "port_5173": _check_port(5173),
        "backend_pid": _check_pid_file("backend"),
        "frontend_pid": _check_pid_file("frontend"),
    }

    critical_keys = ["python", "npm", "backend_main", "frontend_package", "env_file"]
    failed_critical = [key for key in critical_keys if not checks[key].ok]
    status = "pass" if not failed_critical else "fail"
    report: dict[str, Any] = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "critical_keys": critical_keys,
        "failed_critical": failed_critical,
        "checks": {name: asdict(result) for name, result in checks.items()},
    }

    report_path = REPORT_DIR / f"doctor-report-{now}.json"
    latest_path = REPORT_DIR / "doctor-report-latest.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[体检] 状态={status}")
    print(f"[体检] 报告={report_path}")
    if status != "pass":
        print(f"[体检] 关键项失败: {', '.join(failed_critical)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
