# backend/game/roles/__init__.py
"""角色模块 - 导入确保所有角色处理器注册"""
from .werewolf import WerewolfHandler
from .prophet import ProphetHandler
from .witch import WitchHandler
from .villager import VillagerHandler
