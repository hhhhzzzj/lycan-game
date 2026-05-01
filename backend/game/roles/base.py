# backend/game/roles/base.py
"""角色处理基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class RoleHandler(ABC):
    """角色处理抽象基类"""

    @abstractmethod
    def get_role_name(self) -> str:
        ...

    def get_night_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        return ""

    def get_day_speech_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        return ""

    def get_vote_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        return ""

    def get_last_words_prompt(self, player_name: str, view: Dict[str, Any]) -> str:
        return ""


_ROLE_REGISTRY: Dict[str, RoleHandler] = {}


def _register_role(role_name: str, handler: RoleHandler):
    _ROLE_REGISTRY[role_name] = handler


def get_role_handler(role_name: str) -> RoleHandler:
    if role_name not in _ROLE_REGISTRY:
        raise ValueError(f"Unknown role: {role_name}")
    return _ROLE_REGISTRY[role_name]
