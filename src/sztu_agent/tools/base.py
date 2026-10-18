"""
工具层 -- 基础工具定义

设计思想：
- 每个工具是一个独立的“能力单元”
- 统一接口：name+description+input_schema+call(
- AI 根据description和input_schema，生成符合要求的输入参数
- is_ready_only 标记影响权限检测的逻辑
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

from sztu_agent.system_types import ToolDefinition,ToolResult

class Tool(ABC):
    """
    基础工具类 - 所有工具必须继承自类
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（唯一标识）"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        ...
    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """工具输入参数定义"""
        ...

    @property
    def is_read_only(self) -> bool:
        """是否只读工具"""
        return False

    @abstractmethod
    async def call(self,**kwargs: dict[str, Any])->ToolResult:
        """执行工具"""
        ...

    def to_definition(self)->ToolDefinition:
        """将工具转换为工具Definition"""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
        )


class ToolRegistry:
    """
    工具注册器 - 用于管理所有工具
    """
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self,tool:Tool)->None:
        """注册工具"""
        if tool.name in self._tools:
            raise ValueError(f"工具名称 {tool.name} 已存在")
        self._tools[tool.name] = tool

    def register_all(self,tools:list[Tool])->None:
        """批量注册工具"""
        for tool in tools:
            self.register(tool)

    def get(self,name:str)->Tool|None:
        """根据名称获取工具"""
        return self._tools.get(name)

    def get_all(self)->list[Tool]:
        """获取所有工具"""
        return list(self._tools.values())

    def to_definitions(self)->list[ToolDefinition]:
        """将所有工具转换为工具Definition"""
        return [tool.to_definition() for tool in self._tools.values()]

    def has(self,name:str)->bool:
        """检查是否存在指定名称的工具"""
        return name in self._tools