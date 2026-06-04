"""LLM 适配器基础类"""
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


def _coerce_seat(value) -> Optional[int]:
    """把任意值转成合法座位号(1-6)，非法返回 None。"""
    if value is None:
        return None
    try:
        seat = int(value)
    except (ValueError, TypeError):
        return None
    return seat if 1 <= seat <= 6 else None


def _repair_json(s: str) -> str:
    """修复 JSON 字符串值中的未转义换行/回车符，避免 json.loads 失败。"""
    result = []
    in_string = False
    escape_next = False
    for ch in s:
        if escape_next:
            result.append(ch)
            escape_next = False
        elif ch == '\\':
            result.append(ch)
            escape_next = True
        elif ch == '"':
            in_string = not in_string
            result.append(ch)
        elif in_string and ch == '\n':
            result.append('\\n')
        elif in_string and ch == '\r':
            result.append('\\r')
        else:
            result.append(ch)
    return ''.join(result)


def _extract_field(text: str, field: str) -> Optional[str]:
    """从（可能截断的）JSON 字符串中提取指定字段值，容忍未闭合的字符串。"""
    # 先尝试严格匹配（有闭合引号）
    strict_pat = rf'"{field}"\s*:\s*"((?:[^"\\]|\\.)*)"'
    strict = re.search(strict_pat, text)
    if strict:
        raw = strict.group(1)
        return raw.replace('\\n', '\n').replace('\\r', '\r').replace('\\"', '"')
    # 再尝试宽松匹配（截断，无闭合引号）
    lenient_pat = rf'"{field}"\s*:\s*"([\s\S]+)'
    lenient = re.search(lenient_pat, text)
    if lenient:
        raw = lenient.group(1)
        # 截掉尾部可能残留的 JSON 片段（如 ", "target_seat"... 或 "} 等）
        raw = re.split(r'",\s*"(?:target_seat|thinking|action)"', raw)[0]
        raw = re.sub(r'"\s*\}?\s*$', '', raw)
        return raw.replace('\\n', '\n').replace('\\r', '\r').replace('\\"', '"')
    return None


@dataclass
class LLMResponse:
    """AI 玩家的响应"""
    thinking: str
    action: str
    target_seat: Optional[int] = None

    @classmethod
    def from_text(cls, text: str) -> "LLMResponse":
        return cls._from_text(text, depth=0)

    @classmethod
    def _from_text(cls, text: str, depth: int) -> "LLMResponse":
        if depth > 2:
            return cls(thinking="", action=text.strip())

        # 剥离 DeepSeek Reasoner 的 <think>...</think> 标签
        # 同时处理 MiniMax 的 <thinking>...</thinking> 标签
        think_content = ""
        remaining = text
        # 先尝试完整的 <think>...</think> 或 <thinking>...</thinking>
        think_match = re.search(r'<think(?:ing)?>([\s\S]*?)</think(?:ing)?>', text)
        if think_match:
            think_content = think_match.group(1).strip()
            remaining = text[:think_match.start()] + text[think_match.end():]
            remaining = remaining.strip()
        else:
            # 处理截断的 <think> 或 <thinking>（没有关闭标签）
            truncated = re.search(r'<think(?:ing)?>([\s\S]*)', text)
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

        # 尝试提取 ```json ``` 代码块中的 JSON
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', remaining)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return cls(
                    thinking=think_content or data.get("thinking", ""),
                    action=data.get("action", ""),
                    target_seat=_coerce_seat(data.get("target_seat")),
                )
            except json.JSONDecodeError:
                pass

        # 尝试直接解析 JSON
        try:
            data = json.loads(remaining)
            if isinstance(data, str):
                nested = cls._from_text(data, depth=depth + 1)
                return cls(
                    thinking=think_content or nested.thinking,
                    action=nested.action,
                    target_seat=nested.target_seat,
                )
            return cls(
                thinking=think_content or data.get("thinking", ""),
                action=data.get("action", ""),
                target_seat=_coerce_seat(data.get("target_seat")),
            )
        except json.JSONDecodeError:
            pass

        # 尝试修复未转义换行符后再解析（兼容模型在字符串值中输出实际换行的情况）
        try:
            data = json.loads(_repair_json(remaining))
            if isinstance(data, str):
                nested = cls._from_text(data, depth=depth + 1)
                return cls(
                    thinking=think_content or nested.thinking,
                    action=nested.action,
                    target_seat=nested.target_seat,
                )
            return cls(
                thinking=think_content or data.get("thinking", ""),
                action=data.get("action", ""),
                target_seat=_coerce_seat(data.get("target_seat")),
            )
        except json.JSONDecodeError:
            pass

        # 降级：字段提取（兼容 JSON 截断/未闭合引号的情况）
        if remaining.startswith('{') and '"action"' in remaining:
            action_val = _extract_field(remaining, "action")
            if action_val:
                thinking_val = _extract_field(remaining, "thinking") or ""
                seat_m = re.search(r'"target_seat"\s*:\s*(\d+)', remaining)
                return cls(
                    thinking=think_content or thinking_val,
                    action=action_val,
                    target_seat=_coerce_seat(seat_m.group(1)) if seat_m else None,
                )
            thinking_val = _extract_field(remaining, "thinking") or ""
            return cls(
                thinking=think_content or thinking_val,
                action="（发言内容解析失败）",
            )
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
