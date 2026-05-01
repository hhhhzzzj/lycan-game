"""LLM 适配器基础类"""
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    """AI 玩家的响应"""
    thinking: str
    action: str

    @classmethod
    def from_text(cls, text: str) -> "LLMResponse":
        # 尝试提取 JSON
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return cls(
                    thinking=data.get("thinking", ""),
                    action=data.get("action", ""),
                )
            except json.JSONDecodeError:
                pass

        # 尝试直接解析 JSON
        try:
            data = json.loads(text)
            return cls(
                thinking=data.get("thinking", ""),
                action=data.get("action", ""),
            )
        except json.JSONDecodeError:
            pass

        # 降级：整个文本作为 action
        return cls(thinking="", action=text.strip())


class BaseLLMAdapter(ABC):
    """LLM 适配器抽象基类"""

    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    async def call(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        ...

    @abstractmethod
    def _build_messages(self, system: str, user: str) -> list:
        ...
