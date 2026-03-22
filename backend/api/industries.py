"""Industry configuration API.

Exposes the pluggable industry pack system so the frontend can list
available industries, fetch seed keywords, and retrieve platform-specific
hints.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.industry_config import (
    get_industry_config,
    get_industry_keywords,
    get_industry_platform_hints,
    list_industries,
)
from services.template_manager import PLATFORM_STYLES, SUPPORTED_PLATFORMS

router = APIRouter(prefix="/industries", tags=["industries"])


# -- Response models ---------------------------------------------------------


class IndustrySummary(BaseModel):
    id: str
    display_name: str
    description: str


class PlatformStyleResponse(BaseModel):
    platform: str
    tone: str
    min_words: int
    max_words: int
    structure: str
    emoji_density: str
    example_opening: Optional[str] = None


# -- Endpoints ---------------------------------------------------------------


@router.get("", response_model=List[IndustrySummary])
async def list_all_industries():
    """Return all available industry configuration packs."""
    return list_industries()


@router.get("/{industry_id}")
async def get_industry(industry_id: str):
    """Return full configuration for a specific industry."""
    cfg = get_industry_config(industry_id)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Industry not found")
    return cfg


@router.get("/{industry_id}/keywords", response_model=List[str])
async def get_keywords(industry_id: str):
    """Return seed keywords for a specific industry."""
    cfg = get_industry_config(industry_id)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Industry not found")
    return get_industry_keywords(industry_id)


@router.get("/{industry_id}/platform-hints/{platform}")
async def get_platform_hint(industry_id: str, platform: str):
    """Return platform-specific content hints for an industry."""
    hints = get_industry_platform_hints(industry_id, platform)
    if hints is None:
        raise HTTPException(
            status_code=404,
            detail="Industry or platform hints not found",
        )
    return hints


@router.get("/platforms/styles", response_model=List[PlatformStyleResponse])
async def list_platform_styles():
    """Return rich style metadata for all supported platforms."""
    result = []
    for platform in SUPPORTED_PLATFORMS:
        style = PLATFORM_STYLES[platform]
        result.append(
            PlatformStyleResponse(
                platform=platform,
                tone=style["tone"],
                min_words=style["min_words"],
                max_words=style["max_words"],
                structure=style["structure"],
                emoji_density=style["emoji_density"],
                example_opening=style.get("example_opening"),
            )
        )
    return result
