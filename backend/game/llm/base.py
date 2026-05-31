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
        # 剥离 DeepSeek Reasoner 的 <think>...</think> 标签
        think_content = ""
        remaining = text
        # 先尝试完整的 <think>...</think>
        think_match = re.search(r'<think>([\s\S]*?)</think>', text)
        if think_match:
            think_content = think_match.group(1).strip()
            remaining = text[:think_match.start()] + text[think_match.end():]
            remaining = remaining.strip()
        else:
            # 处理截断的 <think>（没有关闭标签）
            truncated = re.search(r'<think>([\s\S]*)', text)
            if truncated:
                after_think = truncated.group(1)
                # 尝试在 JSON 起始处分割
                json_start = re.search(r'\{["\']thinking["\']', after_think)
                if json_start:
                    think_content = after_think[:json_start.start()].strip()
                    remaining = after_think[json_start.start():].strip()
                else:
                    think_content = after_think.strip()
                    remaining = text[:truncated.start()].strip()

        # 尝试提取 JSON
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', remaining)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return cls(
                    thinking=think_content or data.get("thinking", ""),
                    action=data.get("action", ""),
                )
            except json.JSONDecodeError:
                pass

        # 尝试直接解析 JSON
        try:
            data = json.loads(remaining)
            return cls(
                thinking=think_content or data.get("thinking", ""),
                action=data.get("action", ""),
            )
        except json.JSONDecodeError:
            pass

        # 降级：剩余文本作为 action（think 内容作为 thinking）
        return cls(thinking=think_content, action=remaining.strip() if remaining.strip() else text.strip())


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
