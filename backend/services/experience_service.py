"""GEO optimization experience service — inspired by Web Access Skill's site experience mechanism.

Records what strategies worked for what content types, building institutional
memory that improves recommendations over time.

Storage: lightweight JSON files under ``data/experiences/{brand_id}/``.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Base directory for experience data (relative to backend/).
_EXPERIENCE_DIR = Path(os.getenv("EXPERIENCE_DIR", "data/experiences"))


@dataclass
class OptimizationExperience:
    brand_id: str
    platform: str
    industry: str
    strategy_name: str
    score_before: float
    score_after: float
    improvement: float  # score_after - score_before
    content_type: str  # e.g., "长文", "问答", "测评"
    discovered_at: str = ""  # ISO date, auto-filled if empty
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.discovered_at:
            self.discovered_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _experience_path(brand_id: str, platform: str) -> Path:
    """Return the JSON file path for a brand+platform combination."""
    safe_brand = brand_id.replace("/", "_").replace("\\", "_")
    safe_platform = platform.replace("/", "_").replace("\\", "_")
    return _EXPERIENCE_DIR / safe_brand / f"{safe_platform}.json"


def _load_experiences(path: Path) -> List[Dict[str, Any]]:
    """Load experience records from a JSON file."""
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as exc:
        logger.warning("Failed to load experiences from %s: %s", path, exc)
        return []


async def save_experience(exp: OptimizationExperience) -> None:
    """Append an optimization experience record."""
    path = _experience_path(exp.brand_id, exp.platform)
    path.parent.mkdir(parents=True, exist_ok=True)

    records = _load_experiences(path)
    records.append(asdict(exp))

    # Keep at most 200 records per brand+platform to avoid unbounded growth.
    if len(records) > 200:
        records = records[-200:]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


async def query_experiences(
    brand_id: str,
    platform: Optional[str] = None,
    min_improvement: float = 5.0,
) -> List[OptimizationExperience]:
    """Query historical effective experiences for a brand."""
    results: List[OptimizationExperience] = []

    brand_dir = _EXPERIENCE_DIR / brand_id.replace("/", "_").replace("\\", "_")
    if not brand_dir.exists():
        return results

    files = (
        [_experience_path(brand_id, platform)]
        if platform
        else list(brand_dir.glob("*.json"))
    )

    for path in files:
        for record in _load_experiences(path):
            try:
                exp = OptimizationExperience(**record)
                if exp.improvement >= min_improvement:
                    results.append(exp)
            except Exception:
                continue

    return results


async def build_experience_context(brand_id: str, platform: str) -> str:
    """Build experience context string for injection into expert prompts.

    Returns empty string if no relevant experiences exist.
    """
    experiences = await query_experiences(brand_id, platform)
    if not experiences:
        return ""

    top = sorted(experiences, key=lambda e: e.improvement, reverse=True)[:5]
    lines = ["## 历史优化经验（仅供参考，策略效果可能随时间变化）"]
    for exp in top:
        lines.append(
            f"- {exp.strategy_name} 在 {exp.platform} 上提升了 "
            f"{exp.improvement:.1f} 分 ({exp.discovered_at})"
        )
    return "\n".join(lines)
