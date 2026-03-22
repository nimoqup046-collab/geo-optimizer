"""Pluggable keyword data providers for search volume, trends, and competition metrics.

Default provider is ``MockDataProvider`` which returns deterministic mock data
based on keyword hashes — no external API keys required.
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class KeywordMetrics:
    """Enriched metrics for a single keyword."""

    keyword: str
    search_volume: int = 0
    trend_index: float = 0.0       # 0-100, higher = trending up
    competition_score: float = 0.0  # 0-100, higher = harder
    ai_citation_potential: float = 0.0  # 0-100
    related_keywords: List[str] = field(default_factory=list)
    source: str = "mock"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keyword": self.keyword,
            "search_volume": self.search_volume,
            "trend_index": round(self.trend_index, 1),
            "competition_score": round(self.competition_score, 1),
            "ai_citation_potential": round(self.ai_citation_potential, 1),
            "related_keywords": self.related_keywords,
            "source": self.source,
        }


class BaseDataProvider(ABC):
    """Abstract base class for keyword data providers."""

    name: str = "base"

    @abstractmethod
    async def fetch_keyword_metrics(self, keywords: List[str]) -> List[KeywordMetrics]:
        ...

    async def is_available(self) -> bool:
        return True


class MockDataProvider(BaseDataProvider):
    """Deterministic mock data provider — hash-based for consistency."""

    name = "mock"

    def _hash_seed(self, keyword: str) -> int:
        return int(hashlib.md5(keyword.encode()).hexdigest()[:8], 16)

    async def fetch_keyword_metrics(self, keywords: List[str]) -> List[KeywordMetrics]:
        results = []
        for kw in keywords:
            seed = self._hash_seed(kw)
            volume = 100 + (seed % 9900)  # 100 - 9999
            trend = (seed % 100)
            competition = ((seed >> 4) % 100)
            ai_potential = ((seed >> 8) % 100)

            # Generate related keywords based on the keyword text.
            related = []
            if len(kw) >= 2:
                related = [f"{kw}技巧", f"{kw}方法", f"如何{kw}"]

            results.append(KeywordMetrics(
                keyword=kw,
                search_volume=volume,
                trend_index=float(trend),
                competition_score=float(competition),
                ai_citation_potential=float(ai_potential),
                related_keywords=related,
                source="mock",
            ))
        return results


class BaiduIndexProvider(BaseDataProvider):
    """Baidu Index API integration (placeholder — requires API key)."""

    name = "baidu_index"

    async def is_available(self) -> bool:
        return bool(getattr(settings, "BAIDU_INDEX_API_KEY", None))

    async def fetch_keyword_metrics(self, keywords: List[str]) -> List[KeywordMetrics]:
        # TODO: Implement real Baidu Index API call.
        # For now, raise so fallback chain moves to next provider.
        raise NotImplementedError("百度指数 API 集成待实现，请配置 BAIDU_INDEX_API_KEY")


class Provider5118(BaseDataProvider):
    """5118 SEO data API integration (placeholder — requires API key)."""

    name = "5118"

    async def is_available(self) -> bool:
        return bool(getattr(settings, "PROVIDER_5118_API_KEY", None))

    async def fetch_keyword_metrics(self, keywords: List[str]) -> List[KeywordMetrics]:
        # TODO: Implement real 5118 API call.
        raise NotImplementedError("5118 API 集成待实现，请配置 PROVIDER_5118_API_KEY")


class DataProviderChain(BaseDataProvider):
    """Try providers in order, fall back to next on failure."""

    name = "chain"

    def __init__(self, providers: List[BaseDataProvider]):
        self.providers = providers

    async def fetch_keyword_metrics(self, keywords: List[str]) -> List[KeywordMetrics]:
        for provider in self.providers:
            try:
                if not await provider.is_available():
                    continue
                return await provider.fetch_keyword_metrics(keywords)
            except Exception:
                logger.warning("Provider %s failed, trying next", provider.name)
                continue
        # Should not happen — MockDataProvider always works.
        return await MockDataProvider().fetch_keyword_metrics(keywords)


# Provider registry.
_PROVIDERS: Dict[str, type] = {
    "mock": MockDataProvider,
    "baidu_index": BaiduIndexProvider,
    "5118": Provider5118,
}


def get_provider(provider_name: Optional[str] = None) -> BaseDataProvider:
    """Return configured data provider with fallback chain."""
    name = provider_name or getattr(settings, "DATA_PROVIDER", "mock")

    if name == "mock":
        return MockDataProvider()

    # Build chain: requested → mock fallback.
    chain: List[BaseDataProvider] = []
    cls = _PROVIDERS.get(name)
    if cls:
        chain.append(cls())
    chain.append(MockDataProvider())
    return DataProviderChain(chain)


def list_providers() -> List[Dict[str, Any]]:
    """Return metadata about all registered providers."""
    results = []
    for name, cls in _PROVIDERS.items():
        results.append({
            "name": name,
            "display_name": {
                "mock": "模拟数据",
                "baidu_index": "百度指数",
                "5118": "5118 SEO数据",
            }.get(name, name),
            "requires_key": name != "mock",
        })
    return results
