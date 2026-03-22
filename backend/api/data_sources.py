"""API routes for keyword data source management and enrichment."""

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from services.data_providers import get_provider, list_providers

router = APIRouter(prefix="/data-sources", tags=["data_sources"])


class FetchRequest(BaseModel):
    keywords: List[str]
    provider: Optional[str] = None


class EnrichRequest(BaseModel):
    keywords: List[str]
    provider: Optional[str] = None


@router.get("/providers")
async def get_providers():
    """List available data providers and their status."""
    providers = list_providers()
    return {"providers": providers}


@router.post("/fetch")
async def fetch_keyword_data(req: FetchRequest):
    """Fetch keyword metrics from the configured data provider."""
    if not req.keywords:
        return {"metrics": [], "source": "none"}

    provider = get_provider(req.provider)
    metrics = await provider.fetch_keyword_metrics(req.keywords[:50])  # cap at 50
    return {
        "metrics": [m.to_dict() for m in metrics],
        "count": len(metrics),
        "source": metrics[0].source if metrics else "none",
    }


@router.post("/enrich-analysis")
async def enrich_analysis(req: EnrichRequest):
    """Enrich keywords with data metrics for analysis integration."""
    if not req.keywords:
        return {"enriched": [], "summary": {}}

    provider = get_provider(req.provider)
    metrics = await provider.fetch_keyword_metrics(req.keywords[:50])

    # Compute summary statistics.
    volumes = [m.search_volume for m in metrics]
    competitions = [m.competition_score for m in metrics]
    ai_potentials = [m.ai_citation_potential for m in metrics]

    summary = {
        "total_keywords": len(metrics),
        "avg_search_volume": round(sum(volumes) / max(1, len(volumes))),
        "avg_competition": round(sum(competitions) / max(1, len(competitions)), 1),
        "avg_ai_potential": round(sum(ai_potentials) / max(1, len(ai_potentials)), 1),
        "high_volume_keywords": [m.keyword for m in metrics if m.search_volume > 5000],
        "high_ai_potential_keywords": [m.keyword for m in metrics if m.ai_citation_potential > 70],
        "source": metrics[0].source if metrics else "none",
    }

    return {
        "enriched": [m.to_dict() for m in metrics],
        "summary": summary,
    }
