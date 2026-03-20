from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import text

from config import settings
from database import engine


router = APIRouter(prefix="/system", tags=["system"])


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
            f"wechat_rich_post={settings.FEATURE_WECHAT_RICH_POST}, "
            f"prompt_profiles={settings.FEATURE_PROMPT_PROFILES}, "
            f"workflow_steps={settings.FEATURE_WORKFLOW_STEPS}"
        ),
    }

    all_ok = all(item["ok"] for item in checks.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
