import pytest

from services.workflow_executor import GeoScoreAdapter, execute_step


@pytest.mark.asyncio
async def test_geo_score_adapter_uses_compute_geo_score():
    adapter = GeoScoreAdapter()
    result = await adapter.execute(
        {
            "content": "结论：沟通频率每周 2-3 次更有利于关系修复。",
            "platform": "wechat",
            "keywords": ["婚姻修复", "沟通"],
        },
        {},
    )

    assert result["adapter"] == "geo_score"
    assert result["platform"] == "wechat"
    assert "scores" in result
    assert isinstance(result["scores"], dict)
    assert "overall" in result["scores"]


@pytest.mark.asyncio
async def test_execute_step_returns_structured_error_for_unknown_adapter():
    result = await execute_step("not_exists_adapter", {}, {}, retry_limit=0)
    assert result.status == "failed"
    assert result.error is not None
    assert "unknown adapter" in result.error

