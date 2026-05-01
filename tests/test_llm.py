# tests/test_llm.py
import pytest
from game.llm.base import LLMResponse, BaseLLMAdapter
from game.llm.adapters import create_adapter, OpenAIAdapter, AnthropicAdapter


def test_llm_response_parses_json():
    resp = LLMResponse.from_text("""
    ```json
    {"thinking": "吃了吗", "action": "投票给3号"}
    ```
    """)
    assert resp.thinking == "吃了吗"
    assert resp.action == "投票给3号"


def test_llm_response_parses_plain_json():
    resp = LLMResponse.from_text('{"thinking": "分析", "action": "刀5号"}')
    assert resp.thinking == "分析"
    assert resp.action == "刀5号"


def test_llm_response_parses_plain_text():
    resp = LLMResponse.from_text("我投票给3号")
    assert "3号" in resp.action or resp.action != ""


def test_create_openai_adapter():
    adapter = create_adapter("openai", "gpt-4o", "sk-test")
    assert isinstance(adapter, OpenAIAdapter)
    assert adapter.model == "gpt-4o"


def test_create_anthropic_adapter():
    adapter = create_adapter("anthropic", "claude-sonnet-4-6", "sk-test")
    assert isinstance(adapter, AnthropicAdapter)


def test_create_unknown_adapter_raises():
    with pytest.raises(ValueError, match="Unknown provider"):
        create_adapter("unknown", "model", "key")


def test_openai_adapter_builds_messages():
    adapter = OpenAIAdapter("gpt-4o", "sk-test")
    messages = adapter._build_messages(
        system="You are a player.",
        user="What do you do?",
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_anthropic_adapter_builds_messages():
    adapter = AnthropicAdapter("claude-sonnet-4-6", "sk-test")
    messages = adapter._build_messages(
        system="You are a player.",
        user="What do you do?",
    )
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "What do you do?"
