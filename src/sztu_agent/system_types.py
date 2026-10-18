"""
核心类型定义
整个框架的基础类型，所有模块共享
"""

from __future__ import annotations

from dataclasses import dataclass,field
from enum import Enum
from typing import Any,Awaitable,Callable,Protocol


class Role(str,Enum):
    USER='user'
    ASSISTANT='assistant'
    SYSTEM='system'

@dataclass
class TextContent:
    """纯文本内容块"""
    type: str='text'
    text: str=""


@dataclass
class ToolUseContent:
    """工具调用内容块"""
    type:str="tool_use"
    id:str=""
    name:str=""
    input:dict[str,Any]=field(default_factory=dict)

@dataclass
class ToolResultContent:
    """工具调用结果内容块"""
    type:str="tool_result"
    tool_user_id:str=""
    content:str=""
    is_error:bool=False

ContentBlock = TextContent | ToolUseContent | ToolResultContent
@dataclass
class Message:
    """对话消息"""
    role:Role
    content:str|list[ContentBlock]


@dataclass
class ToolDefinition:
    """工具定义"""
    name:str=""
    description:str=""
    input_schema:dict[str,Any]=field(default_factory=dict)


@dataclass
class ToolResult:
    """工具调用结果"""
    content:str
    is_error:bool=False

#permission 类型-权限裁决

class PermissionDecision(str,Enum):
    ALLOW='allow'
    ASK='ask'
    DENY='deny'

@dataclass
class PermissionRule:
    """权限规则"""
    tool:str
    decision:PermissionDecision
    pattern:str|None=None

@dataclass
class ProviderType(str,Enum):
    """提供者类型"""
    OPENAI='openai'
    ANTHROPIC='anthropic'
@dataclass
class EngineConfig:
    """引擎配置"""
    api_key:str=""
    provider:str='openai'
    model:str="deepseek-v4-flash"
    base_url:str|None=None

    max_turns:int=20
    max_token:int = 4096
    project_root:str="."
    custom_system_prompt:str|None=None

    permission_rules : list[PermissionRule]=field(default_factory=list)

    auto_compact:bool=True
    compact_threshold:int=80000

@dataclass
class TokenUsage:
    """Token 使用统计"""
    input_tokens:int=0
    output_tokens:int=0

@dataclass
class LoopResult:
    """Agentic Loop 执行结果"""
    final_text:str=""
    turn_used:int=0
    total_tokens:TokenUsage=field(default_factory=TokenUsage)
    reached_max_turns:bool=False

class AgentCallbacks(Protocol):
    """Agent 事件回调协议"""
    def on_text_delta(self,text:str):
        """文本文本增量回调"""

    def on_tool_start(self,tool_name:str,tool_input:dict[str,Any]=None):
        """工具调用开始回调"""

    def on_tool_end(self,tool_name:str,tool_result:ToolResult):
        """工具调用结束回调"""

    async def on_permission_ask(self,tool_name:str,tool_input:dict[str,Any])->bool:
        """询问用户是否允许调用工具,同意返回True，否则返回False"""

    def on_complete(self,final_output:str):
        """循环完成回调"""

    def on_error(self,error:Exception):
        """错误回调"""

@dataclass
class SimpleCallbacks:
    """简单回调实现"""
    on_text_delta:Callable[[str],None]|None=None
    on_tool_start:Callable[[str,dict[str,dict[str,Any]]],None]|None=None
    on_tool_end:Callable[[str,ToolResult],None]|None=None
    on_permission_ask:Callable[[str,dict[str,Any]],bool]|None=None
    on_complete:Callable[[str],None]|None=None
    on_error:Callable[[Exception],None]|None=None

