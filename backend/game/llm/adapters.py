"""LLM 适配器实现 — OpenAI / Anthropic / Google AI"""
import asyncio
from typing import Optional
from .base import LLMResponse, BaseLLMAdapter


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI 兼容接口适配器（GPT、DeepSeek、Qwen 等）"""

    async def call(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=self.model,
                    messages=self._build_messages(system_prompt, user_prompt),
                    temperature=0.9,
                    max_tokens=1024,
                ),
                timeout=60.0,
            )
            text = response.choices[0].message.content or ""
            return LLMResponse.from_text(text)
        except asyncio.TimeoutError:
            return LLMResponse(thinking="API 超时", action="弃票")
        except Exception as e:
            return LLMResponse(thinking=f"API 错误: {e}", action="弃票")

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
