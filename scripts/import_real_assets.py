from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


def discover_root() -> Path:
    here = Path(__file__).resolve()
    candidates = [*here.parents, Path.cwd().resolve(), *Path.cwd().resolve().parents]
    for candidate in candidates:
        if (candidate / "backend" / "main.py").exists() and (
            candidate / "frontend" / "package.json"
        ).exists():
            return candidate
    return here.parents[1]


ROOT = discover_root()
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Keep import logs clean for batch users.
os.environ.setdefault("DEBUG", "False")
# Keep local import DB aligned with local backend app database.
os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{(BACKEND_DIR / 'data' / 'geo_optimizer.db').as_posix()}",
)

from database import async_session_maker, init_db  # noqa: E402
from models.brand import BrandProfile  # noqa: E402
from models.source_asset import SourceAsset  # noqa: E402
from models.workspace import Workspace  # noqa: E402
from services.asset_parser import parse_text_from_file  # noqa: E402
from sqlalchemy import select  # noqa: E402


REPORT_DIR = ROOT / "data" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".docx", ".pdf", ".xlsx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | IMAGE_EXTENSIONS


@dataclass
class ImportItem:
    path: str
    ext: str
    status: str
    reason: str
    asset_id: str = ""
    title: str = ""
    platform: str = "mixed"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_ext(path: Path) -> str:
    return path.suffix.lower().strip()


def detect_platform(path: Path) -> str:
    value = str(path).lower()
    if any(hit in value for hit in ("xiaohongshu", "xhs", "小红书")):
        return "xiaohongshu"
    if any(hit in value for hit in ("zhihu", "知乎")):
        return "zhihu"
    if any(hit in value for hit in ("baijiahao", "百家号")):
        return "baijiahao"
    if any(hit in value for hit in ("wechat", "公众号", "微信")):
        return "wechat"
    if any(hit in value for hit in ("douyin", "tiktok", "视频", "短视频")):
        return "video"
    return "mixed"


def priority_for(path: Path) -> int:
    ext = normalize_ext(path)
    if ext in {".txt", ".md", ".docx", ".pdf"}:
        return 0
    if ext == ".xlsx":
        return 1
    if ext in IMAGE_EXTENSIONS:
        return 2
    return 3


def pick_core_files(source_root: Path, max_count: int) -> list[Path]:
    files = [
        p
        for p in source_root.rglob("*")
        if p.is_file() and normalize_ext(p) in SUPPORTED_EXTENSIONS
    ]
    files.sort(key=lambda p: (priority_for(p), str(p).lower()))
    return files[:max_count]


async def ensure_workspace_and_brand(
    *,
    workspace_name: str,
    brand_name: str,
    industry: str,
) -> tuple[str, str]:
    async with async_session_maker() as session:
        workspace_result = await session.execute(
            select(Workspace).where(Workspace.name == workspace_name)
        )
        workspace = workspace_result.scalar_one_or_none()
        if workspace is None:
            workspace = Workspace(id=str(uuid.uuid4()), name=workspace_name)
            session.add(workspace)
            await session.flush()

        brand_result = await session.execute(
            select(BrandProfile).where(
                BrandProfile.workspace_id == workspace.id,
                BrandProfile.name == brand_name,
            )
        )
        brand = brand_result.scalar_one_or_none()
        if brand is None:
            brand = BrandProfile(
                id=str(uuid.uuid4()),
                workspace_id=workspace.id,
                name=brand_name,
                industry=industry,
                service_description="Imported from real source assets.",
                target_audience="To be refined after first analysis.",
                tone_of_voice="Professional, warm, actionable.",
                call_to_action="Submit your scenario for a step-by-step suggestion.",
                region="CN",
                competitors=[],
                banned_words=[],
                glossary={},
                platform_preferences={},
                content_boundaries="No guaranteed claims. Keep legal and platform compliance.",
            )
            session.add(brand)
            await session.flush()

        await session.commit()
        return workspace.id, brand.id


async def load_existing_hashes(*, workspace_id: str, brand_id: str) -> set[str]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(SourceAsset).where(
                SourceAsset.workspace_id == workspace_id,
                SourceAsset.brand_id == brand_id,
            )
        )
        hashes: set[str] = set()
        for asset in result.scalars().all():
            for tag in asset.tags or []:
                if isinstance(tag, str) and tag.startswith("import_hash:"):
                    hashes.add(tag.split(":", 1)[1])
        return hashes


def summarize_text(parsed_text: str, parse_status: str) -> str:
    if parsed_text.strip():
        return parsed_text[:300]
    if parse_status == "image_uploaded_no_ocr":
        return "Image imported as placeholder. OCR is not enabled in V1."
    return f"Imported without parsed text. status={parse_status}"


def iter_import_tags(path: Path, ext: str, content_hash: str) -> Iterable[str]:
    yield "import_batch:core20"
    yield f"import_hash:{content_hash}"
    yield f"source_path:{path}"
    yield f"ext:{ext}"


async def import_files(
    *,
    workspace_id: str,
    brand_id: str,
    files: list[Path],
    dry_run: bool,
) -> tuple[list[ImportItem], int]:
    imported = 0
    results: list[ImportItem] = []
    existing_hashes = await load_existing_hashes(workspace_id=workspace_id, brand_id=brand_id)

    async with async_session_maker() as session:
        for file_path in files:
            ext = normalize_ext(file_path)
            current_hash = file_hash(file_path)
            platform = detect_platform(file_path)

            if current_hash in existing_hashes:
                results.append(
                    ImportItem(
                        path=str(file_path),
                        ext=ext,
                        platform=platform,
                        status="skipped",
                        reason="duplicate_hash",
                    )
                )
                continue

            parsed_text, parse_status = parse_text_from_file(str(file_path))
            title = file_path.stem

            if dry_run:
                results.append(
                    ImportItem(
                        path=str(file_path),
                        ext=ext,
                        platform=platform,
                        status="preview",
                        reason=parse_status,
                        title=title,
                    )
                )
                continue

            asset = SourceAsset(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                brand_id=brand_id,
                title=title,
                source_type="uploaded_file",
                platform=platform,
                file_name=file_path.name,
                file_path=str(file_path),
                mime_type="",
                raw_text=parsed_text,
                summary=summarize_text(parsed_text, parse_status),
                tags=list(iter_import_tags(file_path, ext, current_hash)),
                status=parse_status,
            )
            session.add(asset)
            await session.flush()
            imported += 1
            existing_hashes.add(current_hash)
            results.append(
                ImportItem(
                    path=str(file_path),
                    ext=ext,
                    platform=platform,
                    status="imported",
                    reason=parse_status,
                    asset_id=asset.id,
                    title=title,
                )
            )

        if not dry_run:
            await session.commit()

    return results, imported


def build_report(
    *,
    source_root: Path,
    selected_files: list[Path],
    result_items: list[ImportItem],
    imported_count: int,
    dry_run: bool,
    workspace_id: str,
    brand_id: str,
) -> dict:
    by_status: dict[str, int] = {}
    by_reason: dict[str, int] = {}
    by_platform: dict[str, int] = {}
    for item in result_items:
        by_status[item.status] = by_status.get(item.status, 0) + 1
        by_reason[item.reason] = by_reason.get(item.reason, 0) + 1
        by_platform[item.platform] = by_platform.get(item.platform, 0) + 1

    return {
        "status": "preview" if dry_run else "completed",
        "timestamp": datetime.now().isoformat(),
        "source_root": str(source_root),
        "selected_count": len(selected_files),
        "imported_count": imported_count,
        "workspace_id": workspace_id,
        "brand_id": brand_id,
        "summary": {
            "by_status": by_status,
            "by_reason": by_reason,
            "by_platform": by_platform,
        },
        "items": [asdict(item) for item in result_items],
    }


async def async_main(args: argparse.Namespace) -> int:
    await init_db()

    source_root = Path(args.source_root)
    if not source_root.exists():
        print(f"[import] source root not found: {source_root}")
        return 1

    selected_files = pick_core_files(source_root=source_root, max_count=args.max_count)
    if not selected_files:
        print(f"[import] no supported files under: {source_root}")
        return 1

    workspace_id, brand_id = await ensure_workspace_and_brand(
        workspace_name=args.workspace_name,
        brand_name=args.brand_name,
        industry=args.industry,
    )
    result_items, imported_count = await import_files(
        workspace_id=workspace_id,
        brand_id=brand_id,
        files=selected_files,
        dry_run=args.dry_run,
    )
    report = build_report(
        source_root=source_root,
        selected_files=selected_files,
        result_items=result_items,
        imported_count=imported_count,
        dry_run=args.dry_run,
        workspace_id=workspace_id,
        brand_id=brand_id,
    )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(args.report_path) if args.report_path else REPORT_DIR / f"import-report-{ts}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORT_DIR / "import-report-latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[import] dry_run={args.dry_run}")
    print(f"[import] selected={len(selected_files)} imported={imported_count}")
    print(f"[import] report={out_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import real assets into GEO V1")
    parser.add_argument(
        "--source-root",
        default=r"D:\geo_feedback_optimizer",
        help="Root directory containing real source assets.",
    )
    parser.add_argument("--max-count", type=int, default=20, help="Maximum number of files to import.")
    parser.add_argument("--workspace-name", default="default", help="Workspace name.")
    parser.add_argument("--brand-name", default="真实业务品牌", help="Brand name.")
    parser.add_argument("--industry", default="emotion_consulting", help="Brand industry.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not write to DB.")
    parser.add_argument("--report-path", default="", help="Optional report output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
