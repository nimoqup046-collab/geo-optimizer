import json
from typing import Any, Dict, List, Optional

import httpx
from zhipuai import ZhipuAI

from config import settings


class LLMService:
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.DEFAULT_LLM_PROVIDER
        self.client = None
        self.model = ""
        self._init_client()

    def _init_client(self):
        if self.provider == "zhipu":
            self.client = ZhipuAI(api_key=settings.ZHIPU_API_KEY)
            self.model = settings.ZHIPU_MODEL
        elif self.provider == "doubao":
            self.client = httpx.AsyncClient(timeout=60.0)
            self.model = settings.DOUBAO_MODEL
        elif self.provider == "openrouter":
            self.client = httpx.AsyncClient(timeout=60.0)
            self.model = settings.OPENROUTER_MODEL
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 3000,
        **kwargs,
    ) -> str:
        model = model or self.model
        if self.provider == "zhipu":
            return await self._generate_zhipu(messages, model, temperature, max_tokens, **kwargs)
        if self.provider == "doubao":
            return await self._generate_doubao(messages, model, temperature, max_tokens, **kwargs)
        return await self._generate_openrouter(messages, model, temperature, max_tokens, **kwargs)

    async def _generate_zhipu(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.choices[0].message.content

    async def _generate_doubao(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> str:
        if not settings.DOUBAO_API_KEY:
            raise RuntimeError("DOUBAO_API_KEY is missing")
        response = await self.client.post(
            f"{settings.DOUBAO_API_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.DOUBAO_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs,
            },
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]

    async def _generate_openrouter(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> str:
        if not settings.OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY is missing")
        response = await self.client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": settings.OPENROUTER_SITE_URL or "https://geo.local",
                "X-Title": settings.OPENROUTER_APP_NAME or "GEO Optimizer",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs,
            },
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]

    async def close(self):
        if isinstance(self.client, httpx.AsyncClient):
            await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


def build_system_prompt(role: str, context: Optional[Dict[str, Any]] = None) -> str:
    base = {
        "analysis_strategist": "你是 GEO 策略分析师。输出必须具体、可执行、可排序，避免空泛表述。",
        "content_generator": "你负责生成多平台内容，要求结构清晰、观点可引用、动作可执行。",
        "brand_editor": "你是品牌编辑。改写时必须对齐品牌语气、CTA、禁用词和合规边界。",
    }.get(role, "你是务实的内容与策略助手。")

    if context:
        return f"{base}\n\n上下文：\n{json.dumps(context, ensure_ascii=False, indent=2)}"
    return base


async def generate_with_expert_role(
    role: str,
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
    provider: str = "openrouter",
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> str:
    """Generate content using an expert role's dedicated model via OpenRouter.

    Automatically selects the correct model for the role from config.
    Falls back to default provider if OpenRouter is unavailable.
    """
    from config import settings as _settings

    role_model_map = {
        "chief_strategist": _settings.EXPERT_STRATEGY_MODEL,
        "content_architect": _settings.EXPERT_CONTENT_MODEL,
        "data_analyst": _settings.EXPERT_ANALYSIS_MODEL,
        "quality_reviewer": _settings.EXPERT_REVIEW_MODEL,
        "geo_optimizer": _settings.EXPERT_GEO_MODEL,
    }
    use_model = model or role_model_map.get(role, _settings.OPENROUTER_MODEL)

    from services.expert_prompts import get_expert_system_prompt

    system_prompt = get_expert_system_prompt(role, context)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    try:
        async with LLMService(provider) as llm:
            return await llm.generate(
                messages, model=use_model, temperature=temperature, max_tokens=max_tokens
            )
    except Exception:
        # Fallback to default provider.
        async with LLMService() as llm:
            return await llm.generate(
                messages, temperature=temperature, max_tokens=max_tokens
            )


async def generate_content(
    prompt: str,
    role: str = "content_generator",
    provider: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    system_prompt_override: Optional[str] = None,
    **kwargs,
) -> str:
    system_prompt = system_prompt_override or build_system_prompt(role, context)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    async with LLMService(provider) as llm:
        return await llm.generate(messages, **kwargs)
