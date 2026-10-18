"""
兼容OpenAI 的所有模型
"""



from __future__ import annotations

import json
from typing import Any,Callable

from openai import OpenAI

from sztu_agent.api.Base import APIResponse,BaseProvider
from sztu_agent.system_types import (
    ContentBlock,
    Message,
    Role,
    TextContent,
    TokenUsage,
    ToolDefinition,
    ToolResultContent,
    ToolUseContent,
)
# ============================================================
# 预设的 Provider 配置（方便用户快速使用）
# ============================================================

PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-v4-pro",
    },
    "mimo": {
        "base_url": "https://api.mimo.xiaomi.com/v1",
        "default_model": "mimo-v2.5-pro",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-max",
    },
    "glm": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "deepseek/deepseek-v4-pro",
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "default_model": "deepseek-ai/DeepSeek-V3",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3",
    },
}

class OpenAIProvider(BaseProvider):
    def __init__(
            self,
            *,
            api_key: str,
            model: str='deepseek-v4-pro',
            max_tokens: int=4096,
            base_url: str,
       )->None:
        kwargs:dict[str,Any]={"api_key":api_key}
        if base_url:
            kwargs['base_url'] = base_url
        self._client = OpenAI(**kwargs)
        self._model = model
        self._max_tokens = max_tokens
        self._base_url = base_url
    async def send_message(self, *, system_prompt: str = "", messages: list[Message],
                           tools: list[ToolDefinition] | None = None,
                           on_text_delta: Callable[[str], None] | None = None) -> APIResponse:
        """发送消息"""
        api_messages=self._convert_message(system_prompt,messages)

        #构建请求参数
        request_params:dict[str,Any]={
            "model":self._model,
            "max_tokens":self._max_tokens,
            "messages":api_messages,
            "stream":True,
        }

        if tools:
            request_params["tools"]=[
                {
                    "type":"function",
                    "function":{
                        "name":t.name,
                        "description":t.description,
                        "parameters":t.input_schema,
                    }
                } for t in tools
            ]

        #流式调用
        content_blocks:list[ContentBlock] = []
        full_text:str=""
        tool_calls_data:dict[int,dict[str,Any]]={}
        input_tokens=0
        output_tokens=0
        stop_reason="end_turn"

        stream = self._client.chat.completions.create(**request_params)

        for chunk in stream:
            if getattr(chunk, "usage", None):
                input_tokens = chunk.usage.prompt_tokens or 0
                output_tokens = chunk.usage.completion_tokens or 0

            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta

            if delta and delta.content:
                full_text += delta.content
                if on_text_delta:
                    on_text_delta(delta.content)

            if delta and delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_data:
                        tool_calls_data[idx] = {
                            "id": tc.id or "",
                            "name": "",
                            "arguments": "",
                        }
                    if tc.id:
                        tool_calls_data[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_data[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_data[idx]["arguments"] += tc.function.arguments

            if choice.finish_reason:
                if choice.finish_reason == "tool_calls":
                    stop_reason = "tool_use"
                elif choice.finish_reason == "length":
                    stop_reason = "max_tokens"
                else:
                    stop_reason = "end_turn"

        if full_text:
            content_blocks.append(TextContent(text=full_text))

        for _idx, tc_data in sorted(tool_calls_data.items()):
            try:
                arguments = json.loads(tc_data["arguments"]) if tc_data.get("arguments") else {}
            except json.JSONDecodeError:
                arguments = {}
            content_blocks.append(ToolUseContent(
                id=tc_data["id"],
                name=tc_data["name"],
                input=arguments,
            ))
            stop_reason = "tool_use"

        return APIResponse(
            content=content_blocks,
            stop_reason=stop_reason,
            token_usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)
        )
    def _convert_message(self,system_prompt: str, messages: list[Message]) -> list[dict[str, Any]]:
        """将消息转换为OpenAI格式"""
        api_messages:list[dict[str, Any]]=[]

        api_messages.append({"role":"system","content":system_prompt})

        for msg in messages:
            if msg.role==Role.SYSTEM:
                continue
            if isinstance(msg.content,str):
                api_messages.append({"role":msg.role.value,"content":msg.content})
            else:
                #处理复杂内容（如工具调用）
                if msg.role==Role.ASSISTANT:
                    text_part =[]
                    tool_calls:list[dict[str, Any]]=[]

                    for block in msg.content:
                        if isinstance(block,TextContent):
                            text_part.append(block.text)
                        elif isinstance(block,ToolUseContent):
                            tool_calls.append({
                                "id":block.id,
                                "type":"function",
                                "function":{
                                    "name":block.name,
                                    "arguments":json.dumps(block.input,ensure_ascii=False),
                                }
                            })
                    assistant_msg:dict[str, Any] = {"role":"assistant"}
                    if text_part:
                        assistant_msg["content"]="\n".join(text_part)
                    else:
                        assistant_msg["content"]=""
                    if tool_calls:
                        assistant_msg["tool_calls"]=tool_calls
                    api_messages.append(assistant_msg)
                elif msg.role==Role.USER:
                    for block in msg.content:
                        if isinstance(block,ToolResultContent):
                            api_messages.append({
                                "role":"tool",
                                "tool_call_id":block.tool_user_id,
                                "content":block.content,
                            })
                        elif isinstance(block,TextContent):
                            api_messages.append({"role":"user","content":block.text})
        return api_messages

    @property
    def model(self)->str:
        return self._model

    @model.setter
    def model(self, value:str):
        self._model = value

    @property
    def provider_name(self)->str:
        return "openai"