from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


RUNTIME_DEFAULTS = {
    "SystemRoot": r"C:\Windows",
    "windir": r"C:\Windows",
    "ComSpec": r"C:\Windows\System32\cmd.exe",
    "PATHEXT": ".COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC;.CPL",
}


@dataclass
class CommandResult:
    ok: bool
    command: str
    exit_code: int
    stdout: str
    stderr: str


def discover_root() -> Path:
    here = Path(__file__).resolve()
    candidates = [*here.parents, Path.cwd().resolve(), *Path.cwd().resolve().parents]
    for candidate in candidates:
        if (candidate / "backend" / "main.py").exists() and (candidate / "frontend" / "package.json").exists():
            return candidate
    return here.parents[1]


def ensure_runtime_env() -> dict[str, str]:
    for key, value in RUNTIME_DEFAULTS.items():
        if key == "PATHEXT":
            os.environ[key] = value
            continue
        if not os.environ.get(key):
            os.environ[key] = value

    if not Path(os.environ["ComSpec"]).exists():
        os.environ["ComSpec"] = RUNTIME_DEFAULTS["ComSpec"]

    pathext = os.environ.get("PATHEXT", "")
    if ".EXE" not in pathext.upper().split(";"):
        os.environ["PATHEXT"] = RUNTIME_DEFAULTS["PATHEXT"]

    return {
        "SystemRoot": os.environ.get("SystemRoot", ""),
        "windir": os.environ.get("windir", ""),
        "ComSpec": os.environ.get("ComSpec", ""),
        "PATHEXT": os.environ.get("PATHEXT", ""),
    }


def _find_in_path(file_name: str) -> str | None:
    for entry in os.environ.get("PATH", "").split(";"):
        entry = entry.strip()
        if not entry:
            continue
        candidate = Path(entry) / file_name
        if candidate.exists():
            return str(candidate)
    return None


def _run_for_output(file_path: str, args: list[str], timeout: int = 20) -> CommandResult:
    return run_command(file_path, args, timeout=timeout, check=False)


def _read_python_version_candidates(project_root: Path | None) -> list[str]:
    version_candidates: list[str] = []
    version_files: list[Path] = []
    if project_root:
        version_files.extend(
            [
                project_root / "backend" / ".python-version",
                project_root / ".python-version",
            ]
        )

    for version_file in version_files:
        if not version_file.exists():
            continue
        raw = version_file.read_text(encoding="utf-8").strip()
        if not raw:
            continue
        version = raw.splitlines()[0].strip()
        if not version:
            continue
        version_candidates.append(version)
        major = version.split(".", 1)[0]
        if major and major != version:
            version_candidates.append(major)
        break

    version_candidates.extend(["3.12", "3", "3.13"])

    unique: list[str] = []
    seen: set[str] = set()
    for item in version_candidates:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def resolve_python_exe(project_root: Path | None = None) -> str:
    ensure_runtime_env()
    if project_root:
        venv_python = project_root / "backend" / ".venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            return str(venv_python)

    py_launcher = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "py.exe"
    if py_launcher.exists():
        for selector in _read_python_version_candidates(project_root):
            result = _run_for_output(
                str(py_launcher),
                [f"-{selector}", "-c", "import sys; print(sys.executable)"],
            )
            path = (result.stdout or "").strip()
            if result.exit_code == 0 and path and Path(path).exists():
                return path

    local_python_candidates = [
        Path(r"C:\Python312\python.exe"),
        Path(r"C:\Python313\python.exe"),
    ]
    for local_python in local_python_candidates:
        if local_python.exists():
            return str(local_python)

    from_path = _find_in_path("python.exe")
    if from_path:
        return from_path

    raise RuntimeError("python executable not found")


def resolve_npm_cmd() -> str:
    ensure_runtime_env()
    nvm_symlink = os.environ.get("NVM_SYMLINK", "").strip()
    if nvm_symlink:
        npm_from_nvm = Path(nvm_symlink) / "npm.cmd"
        if npm_from_nvm.exists():
            return str(npm_from_nvm)

    npm_default = Path(r"C:\nvm4w\nodejs\npm.cmd")
    if npm_default.exists():
        return str(npm_default)

    from_path = _find_in_path("npm.cmd")
    if from_path:
        return from_path

    raise RuntimeError("npm.cmd not found")


def resolve_git_exe() -> str:
    ensure_runtime_env()
    candidates = [
        Path(r"C:\Program Files\Git\cmd\git.exe"),
        Path(r"C:\Program Files\Git\bin\git.exe"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    from_path = _find_in_path("git.exe")
    if from_path:
        return from_path

    raise RuntimeError("git.exe not found")


def _render(file_path: str, args: list[str]) -> str:
    chunks = [file_path]
    for arg in args:
        if any(ch.isspace() for ch in arg) or '"' in arg:
            chunks.append(f'"{arg.replace("\"", "\\\"")}"')
        else:
            chunks.append(arg)
    return " ".join(chunks)


def run_command(
    file_path: str,
    args: list[str] | None = None,
    *,
    cwd: str | Path | None = None,
    timeout: int = 1800,
    check: bool = True,
) -> CommandResult:
    ensure_runtime_env()
    args = args or []
    ext = Path(file_path).suffix.lower()
    command = [file_path, *args]
    command_text = _render(file_path, args)

    if ext in {".cmd", ".bat"}:
        comspec = os.environ.get("ComSpec", RUNTIME_DEFAULTS["ComSpec"])
        cmd_line = _render(file_path, args)
        command = [comspec, "/d", "/c", cmd_line]
        command_text = _render(comspec, ["/d", "/c", cmd_line])

    proc = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )
    result = CommandResult(
        ok=(proc.returncode == 0),
        command=command_text,
        exit_code=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )
    if check and not result.ok:
        stderr_tail = " | ".join(line for line in result.stderr.splitlines()[-8:] if line) or " | ".join(
            line for line in result.stdout.splitlines()[-8:] if line
        )
        raise RuntimeError(
            f"command failed exit={result.exit_code} command={result.command} stderr_tail={stderr_tail}"
        )
    return result


def write_report(report_path: Path, payload: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def asdict_result(result: CommandResult) -> dict[str, Any]:
    return asdict(result)


def print_runtime_snapshot() -> None:
    snap = ensure_runtime_env()
    print(f"[runtime] ComSpec={snap['ComSpec']}")
    print(f"[runtime] PATHEXT={snap['PATHEXT']}")


if __name__ == "__main__":
    print_runtime_snapshot()
    root = discover_root()
    print(f"[runtime] root={root}")
    print(f"[runtime] python={resolve_python_exe(root)}")
    print(f"[runtime] npm={resolve_npm_cmd()}")
    print(f"[runtime] git={resolve_git_exe()}")
