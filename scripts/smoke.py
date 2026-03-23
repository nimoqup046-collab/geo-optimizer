from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    from runtime_tools import ensure_runtime_env
except Exception:  # pragma: no cover
    def ensure_runtime_env() -> dict[str, str]:
        os.environ.setdefault("SystemRoot", r"C:\Windows")
        os.environ.setdefault("windir", r"C:\Windows")
        os.environ.setdefault("ComSpec", r"C:\Windows\System32\cmd.exe")
        os.environ["PATHEXT"] = ".COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC;.CPL"
        return {}


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

    return here.parents[1]


ROOT = discover_root()
REPORT_DIR = ROOT / "data" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = os.getenv("GEO_BASE_URL", "http://localhost:8000").rstrip("/")
API_BASE = f"{BASE_URL}/api/v1"
API_KEY = os.getenv("GEO_INTERNAL_API_KEY", "").strip()


def http_json(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    body = None
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url=f"{API_BASE}{path}",
        data=body,
        headers=headers,
        method=method.upper(),
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"{method} {path} failed: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        winerror = getattr(reason, "winerror", None)
        errno = getattr(reason, "errno", None)
        reason_type = type(reason).__name__ if reason is not None else "unknown"
        raise RuntimeError(
            f"{method} {path} failed: URLError reason_type={reason_type} winerror={winerror} errno={errno}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"{method} {path} failed: {type(exc).__name__}: {repr(exc)}") from exc


def main() -> int:
    ensure_runtime_env()
    report: dict[str, Any] = {
        "status": "fail",
        "timestamp": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "steps": [],
    }

    suffix = uuid4().hex[:8]
    brand_name = f"smoke-brand-{suffix}"

    try:
        brand = http_json(
            "POST",
            "/brands",
            {
                "name": brand_name,
                "industry": "emotion_consulting",
                "tone_of_voice": "professional, warm, actionable",
                "service_description": "smoke test brand",
                "target_audience": "smoke test audience",
                "call_to_action": "contact us",
                "region": "CN",
                "competitors": ["competitor-a"],
                "banned_words": ["guaranteed result"],
                "glossary": {"GEO": "Generative Engine Optimization"},
                "platform_preferences": {"wechat": True},
                "content_boundaries": "no misleading claims",
            },
        )
        report["steps"].append({"step": "create_brand", "ok": True, "id": brand.get("id")})

        asset = http_json(
            "POST",
            "/assets/paste",
            {
                "brand_id": brand["id"],
                "title": "smoke asset",
                "platform": "wechat",
                "raw_text": "This is a smoke test asset used to verify the GEO closed-loop flow.",
                "tags": ["smoke"],
            },
        )
        report["steps"].append({"step": "paste_asset", "ok": True, "id": asset.get("id")})

        analysis = http_json(
            "POST",
            "/analysis/run",
            {
                "brand_id": brand["id"],
                "keyword_seeds": ["marriage recovery", "trust rebuilding plan", "emotion counseling"],
                "competitor_keywords": ["competitor-a reputation"],
                "asset_ids": [asset["id"]],
                "target_platforms": ["wechat", "xiaohongshu", "zhihu"],
            },
        )
        report["steps"].append({"step": "run_analysis", "ok": True, "report_id": analysis.get("report_id")})

        contents = http_json(
            "POST",
            "/content/generate",
            {
                "report_id": analysis["report_id"],
                "content_type": "article",
                "target_platforms": ["wechat", "xiaohongshu", "zhihu"],
                "count": 1,
            },
        )
        first_content = contents[0]
        first_variant = first_content["variants"][0]
        report["steps"].append({"step": "generate_content", "ok": True, "content_id": first_content.get("id")})

        task = http_json(
            "POST",
            "/publish-tasks",
            {
                "brand_id": brand["id"],
                "content_variant_id": first_variant["id"],
                "platform": first_variant["platform"],
            },
        )
        report["steps"].append({"step": "create_publish_task", "ok": True, "task_id": task.get("id")})

        perf = http_json(
            "POST",
            "/performance/import",
            {
                "brand_id": brand["id"],
                "entries": [
                    {
                        "publish_task_id": task["id"],
                        "content_variant_id": first_variant["id"],
                        "keyword": "marriage recovery",
                        "platform": first_variant["platform"],
                        "reads": 123,
                        "likes": 18,
                        "comments": 6,
                        "leads": 2,
                    }
                ],
            },
        )
        report["steps"].append({"step": "import_performance", "ok": True, "count": len(perf)})

        insights = http_json(
            "POST",
            "/optimization-insights/run",
            {"brand_id": brand["id"], "lookback_days": 30},
        )
        report["steps"].append({"step": "run_optimization_insights", "ok": True, "count": len(insights)})

        report["status"] = "pass"
    except Exception as exc:
        report["status"] = "fail"
        report["error"] = str(exc)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"smoke-report-{now}.json"
    latest_path = REPORT_DIR / "smoke-report-latest.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[smoke] status={report['status']}")
    print(f"[smoke] report={report_path}")
    if report["status"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
