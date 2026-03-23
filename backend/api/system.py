import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import text

from config import settings
from database import engine


router = APIRouter(prefix="/system", tags=["system"])


def _command_check(candidates: list[list[str]]) -> tuple[bool, str]:
    last_failure = "not found"
    for cmd in candidates:
        exe = cmd[0]
        if shutil.which(exe) is None and not Path(exe).exists():
            continue
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=8,
                check=False,
            )
            output = (proc.stdout or "").strip()
            if proc.returncode == 0:
                return True, output or "ok"
            last_failure = output or f"exit={proc.returncode}"
        except Exception as exc:  # pragma: no cover
            last_failure = str(exc)
    return False, last_failure


@router.get("/readiness")
async def readiness_check():
    checks = {}

    # Database check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = {"ok": True, "detail": "数据库可连接"}
    except Exception as exc:  # pragma: no cover
        checks["database"] = {"ok": False, "detail": str(exc)}

    upload_dir = Path(settings.UPLOAD_DIR)
    export_dir = Path(settings.EXPORT_DIR)
    checks["upload_dir"] = {"ok": upload_dir.exists(), "detail": str(upload_dir.resolve())}
    checks["export_dir"] = {"ok": export_dir.exists(), "detail": str(export_dir.resolve())}

    llm_key_status = settings.llm_key_status
    selected_provider = settings.DEFAULT_LLM_PROVIDER
    selected_key_ok = llm_key_status.get(selected_provider, False)
    checks["llm_provider"] = {
        "ok": bool(selected_provider),
        "detail": selected_provider,
    }
    checks["llm_provider_key"] = {
        "ok": selected_key_ok,
        "detail": f"{selected_provider}:{'已配置' if selected_key_ok else '缺少密钥'}",
    }
    checks["llm_keys"] = {
        "ok": any(llm_key_status.values()),
        "detail": ",".join(
            [
                f"{name}={'已设置' if enabled else '未设置'}"
                for name, enabled in llm_key_status.items()
            ]
        ),
    }
    checks["internal_api_key"] = {
        "ok": True,
        "detail": "已设置" if settings.INTERNAL_API_KEY else "未设置",
    }
    checks["feature_flags"] = {
        "ok": True,
        "detail": (
            f"expert_team={settings.FEATURE_EXPERT_TEAM}, "
            f"prompt_profiles={settings.FEATURE_PROMPT_PROFILES}, "
            f"seo_audit={settings.FEATURE_SEO_AUDIT}"
        ),
    }

    all_ok = all(item["ok"] for item in checks.values())

    feature_flags = {
        "FEATURE_EXPERT_TEAM": settings.FEATURE_EXPERT_TEAM,
        "FEATURE_PROMPT_PROFILES": settings.FEATURE_PROMPT_PROFILES,
        "FEATURE_SEO_AUDIT": settings.FEATURE_SEO_AUDIT,
        "FEATURE_CONTENT_CALENDAR": settings.FEATURE_CONTENT_CALENDAR,
        "FEATURE_AI_CRAWL": settings.FEATURE_AI_CRAWL,
        "FEATURE_SCHEMA_GEN": settings.FEATURE_SCHEMA_GEN,
        "FEATURE_CASE_CORPUS": settings.FEATURE_CASE_CORPUS,
        "FEATURE_ENTITY_AUTHORITY": settings.FEATURE_ENTITY_AUTHORITY,
        "FEATURE_BRAND_CITATION": settings.FEATURE_BRAND_CITATION,
        "FEATURE_WORKFLOW_STEPS": settings.FEATURE_WORKFLOW_STEPS,
        "FEATURE_AGENT_TEAM": settings.FEATURE_AGENT_TEAM,
        "FEATURE_WECHAT_RICH_POST": settings.FEATURE_WECHAT_RICH_POST,
        "FEATURE_DATA_SOURCES": settings.FEATURE_DATA_SOURCES,
        "FEATURE_RANKING_MONITOR": settings.FEATURE_RANKING_MONITOR,
        "FEATURE_COMPETITOR_ANALYSIS": settings.FEATURE_COMPETITOR_ANALYSIS,
    }

    runtime_shell = os.getenv("ComSpec") or ("/bin/sh" if Path("/bin/sh").exists() else "")
    runtime_python_ok, runtime_python_detail = _command_check(
        [
            ["python", "--version"],
            ["py", "-3.12", "--version"],
            ["py", "-3", "--version"],
            ["py", "-3.13", "--version"],
        ]
    )
    runtime_git_ok, runtime_git_detail = _command_check([["git", "--version"]])
    runtime_npm_ok, runtime_npm_detail = _command_check([["npm", "--version"], ["npm.cmd", "--version"]])

    runtime_env_detail = {
        "shell": runtime_shell or "unknown",
        "pathext_present": bool(os.getenv("PATHEXT")),
        "path_present": bool(os.getenv("PATH")),
        "python_detail": runtime_python_detail,
        "git_detail": runtime_git_detail,
        "npm_detail": runtime_npm_detail,
    }

    return {
        "status": "ok" if all_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "feature_flags": feature_flags,
        "runtime_shell_ok": bool(runtime_shell),
        "runtime_python_ok": runtime_python_ok,
        "runtime_git_ok": runtime_git_ok,
        "runtime_npm_ok": runtime_npm_ok,
        "runtime_env_detail": runtime_env_detail,
    }
