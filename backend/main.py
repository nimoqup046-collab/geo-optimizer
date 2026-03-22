from contextlib import asynccontextmanager
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# MVP 核心路由（始终加载）.
from api.analysis import router as analysis_router
from api.assets import router as assets_router
from api.brands import router as brands_router
from api.content_v2 import router as content_router
from api.demo import router as demo_router
from api.exports import router as exports_router
from api.expert_team import router as expert_team_router
from api.industries import router as industries_router
from api.optimization import router as optimization_router
from api.performance import router as performance_router
from api.prompt_profiles import router as prompt_profiles_router
from api.publish_tasks import router as publish_tasks_router
from api.system import router as system_router
from config import settings
from database import engine, init_db
from services.bootstrap import ensure_default_workspace


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.EXPORT_DIR).mkdir(parents=True, exist_ok=True)
    await init_db()
    await ensure_default_workspace()
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="GEO 闭环优化助手",
    lifespan=lifespan,
)


@app.middleware("http")
async def internal_api_key_guard(request: Request, call_next):
    if not settings.INTERNAL_API_KEY:
        return await call_next(request)

    # Allow health/docs without key.
    if request.url.path in {
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/api/v1/system/readiness",
    }:
        return await call_next(request)
    if request.url.path.startswith("/api/v1/demo/") and settings.DEBUG:
        return await call_next(request)

    provided = request.headers.get("x-api-key")
    if provided != settings.INTERNAL_API_KEY:
        return JSONResponse(status_code=401, content={"detail": "API Key 无效"})
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === MVP 核心路由（始终加载）===
app.include_router(brands_router, prefix=settings.API_V1_PREFIX)
app.include_router(assets_router, prefix=settings.API_V1_PREFIX)
app.include_router(analysis_router, prefix=settings.API_V1_PREFIX)
app.include_router(content_router, prefix=settings.API_V1_PREFIX)
app.include_router(expert_team_router, prefix=settings.API_V1_PREFIX)
app.include_router(exports_router, prefix=settings.API_V1_PREFIX)
app.include_router(publish_tasks_router, prefix=settings.API_V1_PREFIX)
app.include_router(performance_router, prefix=settings.API_V1_PREFIX)
app.include_router(optimization_router, prefix=settings.API_V1_PREFIX)
app.include_router(system_router, prefix=settings.API_V1_PREFIX)
app.include_router(demo_router, prefix=settings.API_V1_PREFIX)
app.include_router(industries_router, prefix=settings.API_V1_PREFIX)
app.include_router(prompt_profiles_router, prefix=settings.API_V1_PREFIX)

# === V1.1 增强路由（Feature Flag 控制）===
if settings.FEATURE_SEO_AUDIT:
    from api.seo_audit import router as seo_audit_router
    app.include_router(seo_audit_router, prefix=settings.API_V1_PREFIX)

if settings.FEATURE_AI_CRAWL:
    from api.ai_crawl import router as ai_crawl_router
    app.include_router(ai_crawl_router, prefix=settings.API_V1_PREFIX)

if settings.FEATURE_SCHEMA_GEN:
    from api.schema_gen import router as schema_gen_router
    app.include_router(schema_gen_router, prefix=settings.API_V1_PREFIX)

if settings.FEATURE_CASE_CORPUS:
    from api.case_corpus import router as case_corpus_router
    app.include_router(case_corpus_router, prefix=settings.API_V1_PREFIX)

if settings.FEATURE_ENTITY_AUTHORITY:
    from api.entity_authority import router as entity_authority_router
    app.include_router(entity_authority_router, prefix=settings.API_V1_PREFIX)

# === V2 高级路由（Feature Flag 控制）===
if settings.FEATURE_BRAND_CITATION:
    from api.brand_citation import router as brand_citation_router
    app.include_router(brand_citation_router, prefix=settings.API_V1_PREFIX)

if settings.FEATURE_WORKFLOW_STEPS:
    from api.workflow_steps import router as workflow_steps_router
    app.include_router(workflow_steps_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "llm_provider": settings.DEFAULT_LLM_PROVIDER,
    }


@app.get("/", tags=["system"])
async def root():
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": settings.API_V1_PREFIX,
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        log_level="info",
    )
