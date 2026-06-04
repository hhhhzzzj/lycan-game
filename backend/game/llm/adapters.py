"""LLM 适配器实现 — OpenAI / Anthropic / Google AI"""
import asyncio
import logging
import random
import time
from typing import Optional
from .base import LLMResponse, BaseLLMAdapter

logger = logging.getLogger("werewolf.llm")


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI 兼容接口适配器（GPT、DeepSeek、Qwen 等）"""

    _locks = {}
    _last_call_at = {}

    async def call(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        max_retries = 4
        for attempt in range(max_retries):
            try:
                await self._throttle()
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=self.model,
                        messages=self._build_messages(system_prompt, user_prompt),
                        temperature=0.9,
                        max_tokens=self._max_tokens(),
                    ),
                    timeout=90.0,
                )
                message = response.choices[0].message
                text = message.content or ""
                if not text.strip():
                    logger.warning(
                        "[LLM空响应] model=%s base_url=%s finish=%s reasoning_len=%s attempt=%s",
                        self.model,
                        self.base_url,
                        response.choices[0].finish_reason,
                        len(getattr(message, "reasoning_content", "") or ""),
                        attempt + 1,
                    )
                    if attempt < max_retries - 1:
                        user_prompt = (
                            user_prompt
                            + "\n\n【系统重试提示】你上一次没有输出可见内容。"
                            + "请立刻输出合法 JSON，action 不能为空，thinking 保持简短。"
                        )
                        await asyncio.sleep(self._retry_delay(attempt))
                        continue
                return LLMResponse.from_text(text)
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(self._retry_delay(attempt))
                    continue
                return LLMResponse(thinking=f"API 超时（重试{max_retries}次后失败）", action="弃票")
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(self._retry_delay(attempt, e))
                    continue
                return LLMResponse(thinking=f"API 错误（重试{max_retries}次后失败）: {e}", action="弃票")

        return LLMResponse(thinking="API 返回空内容（多次重试后失败）", action="（本轮无法形成有效发言）")

    def _max_tokens(self) -> int:
        """Reasoning models may spend much of max_tokens on hidden reasoning."""
        model = (self.model or "").lower()
        if "deepseek-v4-pro" in model:
            return 6144
        if any(name in model for name in ("deepseek-v4", "mimo", "minimax-m")):
            return 3072
        return 1536

    def _retry_delay(self, attempt: int, exc: Optional[Exception] = None) -> float:
        text = str(exc or "").lower()
        if "429" in text or "too many requests" in text or "limitation" in text:
            return 20.0 * (attempt + 1) + random.uniform(0, 3)
        return min(2 ** attempt, 8) + random.uniform(0, 0.5)

    async def _throttle(self):
        base = self.base_url or "default"
        lock = self._locks.setdefault(base, asyncio.Lock())
        async with lock:
            min_interval = 1.0
            if "xiaomimimo" in base or "mimo" in base:
                min_interval = 12.0
            elif "deepseek" in base:
                min_interval = 2.0
            last = self._last_call_at.get(base, 0.0)
            wait = min_interval - (time.monotonic() - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call_at[base] = time.monotonic()

    def _build_messages(self, system: str, user: str) -> list:
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]


class AnthropicAdapter(BaseLLMAdapter):
    """Anthropic Claude 适配器"""

    async def call(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.api_key)

        try:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system=system_prompt,
                    messages=self._build_messages(system_prompt, user_prompt),
                ),
                timeout=60.0,
            )
            text = response.content[0].text
            return LLMResponse.from_text(text)
        except asyncio.TimeoutError:
            return LLMResponse(thinking="API 超时", action="弃票")
        except Exception as e:
            return LLMResponse(thinking=f"API 错误: {e}", action="弃票")

    def _build_messages(self, system: str, user: str) -> list:
        return [{"role": "user", "content": user}]


class GoogleAIAdapter(BaseLLMAdapter):
    """Google Gemini 适配器"""

    async def call(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)

        try:
            model = genai.GenerativeModel(self.model)
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    model.generate_content,
                    full_prompt,
                ),
                timeout=60.0,
            )
            text = response.text
            return LLMResponse.from_text(text)
        except asyncio.TimeoutError:
            return LLMResponse(thinking="API 超时", action="弃票")
        except Exception as e:
            return LLMResponse(thinking=f"API 错误: {e}", action="弃票")

    def _build_messages(self, system: str, user: str) -> list:
        return [{"role": "user", "content": f"{system}\n\n{user}"}]


_PROVIDER_REGISTRY = {
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
    "google": GoogleAIAdapter,
}


def create_adapter(
    provider: str,
    model: str,
    api_key: str,
    base_url: Optional[str] = None,
) -> BaseLLMAdapter:
    adapter_cls = _PROVIDER_REGISTRY.get(provider)
    if adapter_cls is None:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Available: {list(_PROVIDER_REGISTRY.keys())}"
        )
    return adapter_cls(model=model, api_key=api_key, base_url=base_url)
