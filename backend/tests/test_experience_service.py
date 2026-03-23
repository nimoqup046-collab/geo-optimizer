"""Tests for optimization experience persistence and query flow."""

import asyncio
import sys
from pathlib import Path

# Allow imports from backend package when running from repo root.
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from services import experience_service  # noqa: E402
from services.experience_service import OptimizationExperience  # noqa: E402


def test_save_query_and_context_flow(tmp_path):
    experience_service._EXPERIENCE_DIR = tmp_path / "experiences"
    experience_service._FILE_LOCKS.clear()

    exp1 = OptimizationExperience(
        brand_id="brand-A",
        platform="wechat",
        industry="emotion",
        strategy_name="citation_enhancement",
        score_before=50,
        score_after=65,
        improvement=15,
        content_type="article",
    )
    exp2 = OptimizationExperience(
        brand_id="brand-A",
        platform="wechat",
        industry="emotion",
        strategy_name="qa_structuring",
        score_before=60,
        score_after=63,
        improvement=3,
        content_type="article",
    )

    asyncio.run(experience_service.save_experience(exp1))
    asyncio.run(experience_service.save_experience(exp2))

    queried = asyncio.run(
        experience_service.query_experiences(
            brand_id="brand-A",
            platform="wechat",
            min_improvement=5.0,
        )
    )
    assert len(queried) == 1
    assert queried[0].strategy_name == "citation_enhancement"

    context = asyncio.run(
        experience_service.build_experience_context("brand-A", "wechat")
    )
    assert "历史优化经验" in context
    assert "citation_enhancement" in context

