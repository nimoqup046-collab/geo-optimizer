"""Workflow step execution engine with adapter registry and retry logic.

Adapters are registered by name and dispatched at runtime. Each adapter
receives the step's input_payload + config and returns an output dict.
Failed steps are retried with exponential backoff up to retry_limit.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Adapter base class & registry
# ---------------------------------------------------------------------------

class BaseAdapter(ABC):
    """Base class for workflow step adapters."""

    name: str = "base"

    @abstractmethod
    async def execute(
        self,
        input_payload: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute the adapter logic and return output dict.

        Raises Exception on failure (will trigger retry).
        """
        ...


class AdapterRegistry:
    """Registry for workflow step adapters."""

    _adapters: Dict[str, Type[BaseAdapter]] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register an adapter class."""

        def wrapper(adapter_cls: Type[BaseAdapter]):
            adapter_cls.name = name
            cls._adapters[name] = adapter_cls
            return adapter_cls

        return wrapper

    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseAdapter]]:
        return cls._adapters.get(name)

    @classmethod
    def list_adapters(cls) -> list[str]:
        return sorted(cls._adapters.keys())


# ---------------------------------------------------------------------------
# Execution result
# ---------------------------------------------------------------------------

@dataclass
class ExecutionResult:
    """Result of a workflow step execution."""

    status: str  # "completed" | "failed" | "retrying"
    output_payload: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0
    retry_count: int = 0
    started_at: str = ""
    finished_at: str = ""


# ---------------------------------------------------------------------------
# Built-in adapters
# ---------------------------------------------------------------------------

@AdapterRegistry.register("mock")
class MockAdapter(BaseAdapter):
    """Mock adapter for testing."""

    async def execute(
        self, input_payload: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        await asyncio.sleep(0.1)  # Simulate work
        return {
            "adapter": "mock",
            "status": "mock_completed",
            "input_echo": input_payload,
            "message": "Mock adapter executed successfully.",
        }


@AdapterRegistry.register("content_generate")
class ContentGenerateAdapter(BaseAdapter):
    """Generate content for a specific platform using the LLM pipeline."""

    async def execute(
        self, input_payload: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        from services.llm_service import generate_content
        from services.template_manager import format_generation_prompt

        topic = input_payload.get("topic", "")
        platform = input_payload.get("platform", "wechat")
        brand_name = input_payload.get("brand_name", "brand")
        provider = config.get("provider")

        prompt = format_generation_prompt(
            platform=platform,
            topic=topic,
            brand_name=brand_name,
            tone_of_voice=input_payload.get("tone_of_voice", ""),
            call_to_action=input_payload.get("call_to_action", ""),
            banned_words=input_payload.get("banned_words", ""),
            industry=input_payload.get("industry", ""),
        )

        result = await generate_content(prompt=prompt, provider=provider)
        return {
            "adapter": "content_generate",
            "platform": platform,
            "topic": topic,
            "content": result,
            "char_count": len(result),
        }


@AdapterRegistry.register("wechat_rich_post")
class WechatRichPostAdapter(BaseAdapter):
    """Generate a WeChat rich post article."""

    async def execute(
        self, input_payload: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        from services.wechat_rich_post import generate_wechat_article

        article = await generate_wechat_article(
            topic=input_payload.get("topic", ""),
            brand_name=input_payload.get("brand_name", ""),
            tone_of_voice=input_payload.get("tone_of_voice", ""),
            industry=input_payload.get("industry", ""),
            style_hint=input_payload.get("style_hint", ""),
        )
        return {
            "adapter": "wechat_rich_post",
            **article.to_dict(),
        }


@AdapterRegistry.register("geo_score")
class GeoScoreAdapter(BaseAdapter):
    """Compute GEO scores for given content text."""

    async def execute(
        self, input_payload: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        from services.geo_scorer import compute_geo_score

        content = input_payload.get("content", "")
        platform = input_payload.get("platform", "wechat")
        keywords = input_payload.get("keywords")

        score_card = compute_geo_score(content, keywords=keywords, platform=platform)
        return {
            "adapter": "geo_score",
            "platform": platform,
            "scores": score_card.to_dict(),
        }


@AdapterRegistry.register("geo_optimize")
class GeoOptimizeAdapter(BaseAdapter):
    """Apply GEO optimization strategies to content."""

    async def execute(
        self, input_payload: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        from services.geo_strategies import apply_multiple_strategies

        content = input_payload.get("content", "")
        strategies = input_payload.get(
            "strategies", ["citation_enhancement", "statistics_addition"]
        )
        provider = config.get("provider")

        results = await apply_multiple_strategies(content, strategies, provider=provider)
        return {
            "adapter": "geo_optimize",
            "strategies_applied": strategies,
            "results": results,
        }


@AdapterRegistry.register("expert_pipeline")
class ExpertPipelineAdapter(BaseAdapter):
    """Run the 5-expert GEO analysis pipeline."""

    async def execute(
        self, input_payload: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        from services.expert_team import run_expert_pipeline

        report = await run_expert_pipeline(
            topic=input_payload.get("topic", ""),
            brand_data=input_payload.get("brand_data"),
            keyword_layers=input_payload.get("keyword_layers"),
        )
        return {
            "adapter": "expert_pipeline",
            **report.to_dict(),
        }


@AdapterRegistry.register("full_pipeline")
class FullPipelineAdapter(BaseAdapter):
    """End-to-end content pipeline: generate -> score -> auto-optimize -> score."""

    async def execute(
        self, input_payload: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        from services.geo_scorer import (
            compute_geo_score,
            suggest_optimization_strategies,
        )
        from services.geo_strategies import apply_strategy

        # Step 1: Generate content.
        gen_adapter = AdapterRegistry.get("content_generate")
        if not gen_adapter:
            raise RuntimeError("content_generate adapter not registered")
        gen_result = await gen_adapter().execute(input_payload, config)
        content = gen_result.get("content", "")

        # Step 2: Score.
        keywords = input_payload.get("keywords", [])
        platform = input_payload.get("platform")
        score_card = compute_geo_score(content, keywords=keywords, platform=platform)
        scores = score_card.to_dict()

        # Step 3: Auto-optimize if below threshold.
        threshold = config.get("threshold", 68.0)
        strategies_applied = []
        strategy_errors: Dict[str, str] = {}
        if score_card.overall < threshold:
            strategies = suggest_optimization_strategies(score_card)
            if strategies:
                for s_name in strategies[:2]:
                    try:
                        result = await apply_strategy(
                            s_name,
                            content,
                            provider=config.get("provider"),
                        )
                        content = result.optimized_text
                        strategies_applied.append(s_name)
                    except Exception as exc:
                        strategy_errors[s_name] = str(exc)
                        logger.warning(
                            "full_pipeline strategy apply failed: %s (%s)",
                            s_name,
                            exc,
                        )
                score_card = compute_geo_score(
                    content, keywords=keywords, platform=platform
                )
                scores = score_card.to_dict()

        return {
            "adapter": "full_pipeline",
            "content": content,
            "scores": scores,
            "auto_optimized": bool(strategies_applied),
            "strategies_applied": strategies_applied,
            "strategy_errors": strategy_errors,
        }


# ---------------------------------------------------------------------------
# Execution engine with retry
# ---------------------------------------------------------------------------

async def execute_step(
    adapter_name: str,
    input_payload: Dict[str, Any],
    config: Dict[str, Any],
    retry_limit: int = 2,
) -> ExecutionResult:
    """Execute a workflow step with retry logic.

    Uses exponential backoff: 1s, 2s, 4s, ...
    Returns ExecutionResult with final status.
    """
    adapter_cls = AdapterRegistry.get(adapter_name)
    if not adapter_cls:
        return ExecutionResult(
            status="failed",
            error=(
                f"unknown adapter: {adapter_name}; "
                f"available adapters: {AdapterRegistry.list_adapters()}"
            ),
            started_at=datetime.now(timezone.utc).isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
        )

    adapter = adapter_cls()
    last_error = None

    for attempt in range(retry_limit + 1):
        started_at = datetime.now(timezone.utc).isoformat()
        t0 = time.monotonic()

        try:
            output = await adapter.execute(input_payload, config)
            duration_ms = (time.monotonic() - t0) * 1000
            return ExecutionResult(
                status="completed",
                output_payload=output,
                duration_ms=round(duration_ms, 2),
                retry_count=attempt,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as exc:
            duration_ms = (time.monotonic() - t0) * 1000
            last_error = str(exc)
            logger.warning(
                "Adapter '%s' attempt %d/%d failed (%.0fms): %s",
                adapter_name,
                attempt + 1,
                retry_limit + 1,
                duration_ms,
                last_error,
            )

            if attempt < retry_limit:
                backoff = 2**attempt  # 1s, 2s, 4s, ...
                await asyncio.sleep(backoff)

    return ExecutionResult(
        status="failed",
        error=last_error,
        duration_ms=0,
        retry_count=retry_limit,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc).isoformat(),
    )
