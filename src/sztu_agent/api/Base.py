"""
Provider 基础类 -- 所有LLM Provider 的统一接口
设计思想：
- 定义统一的send_message() 接口
- 上层（loop层）
- 不同的Provider 各自实现的细节
- 工厂函数 create_provider() 用于创建具体的Provider 实例
"""
from __future__ import annotations
from abc import ABC,abstractmethod
from dataclasses import dataclass,field
from typing import Any,Callable

from sztu_agent.system_types import (
ContentBlock,
Message,
TokenUsage,
ToolDefinition
)


#统一响应的API
@dataclass
class APIResponse:
    """
      统一的API 响应格式
      无论底层用哪个Provider，返回给Loop层都是这个格式
    """

    content:list[ContentBlock]=field(default_factory=list)
    #停止原因：end_turn=主动结束，tool_use=需要工具调用，max_tokens=最大token数超过
    stop_reason:str="end_turn"
    # 本次请求消耗的token 数
    token_usage:TokenUsage=field(default_factory=TokenUsage)

#Provider 基础类
class BaseProvider(ABC):
    """
    所有LLM Provider 的统一接口,
    所有Provider 必须实现 send_message() 方法
    """
    @abstractmethod
    async def send_message(
            self,
            *,
            system_prompt:str="",
            messages:list[Message],
            tools:list[ToolDefinition]|None=None,
            on_text_delta:Callable[[str],None]|None=None,
    )->APIResponse:
        """
        发送消息到Provider 并返回响应
        :param system_prompt: 系统提示
        :param messages: 对话消息
        :param tools: 工具定义
        :param on_text_delta: 文本增量回调
        :return: APIResponse
        """
        ...

    @property
    @abstractmethod
    def model(self)->str:
        """当前使用的模型名称"""

    @model.setter
    @abstractmethod
    def model(self,value:str)->str:
        """切换模型"""
        ...

    @property
    @abstractmethod
    def provider_name(self)->str:
        """Provider 名称"""

# 工厂函数
def create_provider(
        provider:str,
        *,
        api_key:str="",
        model:str="",
        max_tokens:int=4096,
        base_url:str|None=None,
)->BaseProvider:
    """
    创建Provider 实例
    :param provider: Provider 名称
    :param api_key: API 密钥
    :param model: 模型名称
    :param max_tokens: 最大token 数
    :param base_url: API 基础URL
    :return: Provider 实例
    """
    from sztu_agent.api.openai_provider import OpenAIProvider, PROVIDER_PRESETS

    if provider in PROVIDER_PRESETS:
        preset = PROVIDER_PRESETS[provider]
        if not model:
            model = preset["default_model"]
        if not base_url:
            base_url = preset["base_url"]
        provider = "openai"

    if provider == "anthropic":
        from sztu_agent.api.anthropic_provider import AnthropicProvider
        return AnthropicProvider(
            api_key=api_key,
            model=model or "claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            base_url=base_url or None,
        )

    return OpenAIProvider(
        api_key=api_key,
        model=model or "gpt-4o",
        max_tokens=max_tokens,
        base_url=base_url or "",
    )