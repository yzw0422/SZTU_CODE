"""
核心循环层 - Agentic Loop

设计的思想是（ReAct 模式）
后续也会添加其他模式，例如plan-execute
multi-agent模式
"""

from sztu_agent.api.Base import BaseProvider
from sztu_agent.permission import PermissionManager
from sztu_agent.tools import ToolRegistry
from sztu_agent.system_types import Message, SimpleCallbacks, LoopResult, Role, ToolUseContent, ToolResult, ToolResultContent, \
    TextContent, TokenUsage


class AgenticLoop:
    def __init__(
            self,
            api_client:BaseProvider,
            tool_registry:ToolRegistry,
            permission:PermissionManager
    ):
        self.api_client = api_client

        self.tool_registry = tool_registry
        self._permission_manager = permission

    async def run(
            self,
            system_prompt:str,
            messages:list[Message],
            *,
            max_turns:int=25,
            callbacks:SimpleCallbacks|None=None,
    )->LoopResult:
        """
        运行循环

        :param system_prompt: 系统提示
        :param messages: 初始消息
        :param max_turns: 最大轮数
        :param callbacks: 回调函数
        :return: 循环结果
        """
        turns_used:int =0
        total_input=0
        total_output=0
        reached_max_turns=False

        while turns_used<max_turns:
            turns_used+=1

            #第一步，发送请求给LLM
            response = await self.api_client.send_message(
                system_prompt=system_prompt,
                messages=messages,
                tools=self.tool_registry.to_definitions(),
                on_text_delta=callbacks.on_text_delta if callbacks else None,
            )

            total_input+=response.token_usage.input_tokens
            total_output+=response.token_usage.output_tokens

            assistant_message = Message(
                role=Role.ASSISTANT,
                content=response.content
            )
            messages.append(assistant_message)

            #第二步，处理工具调用
            if response.stop_reason!="tool_use":
                break

            tool_use_block = [
                b for b in response.content if isinstance(b,ToolUseContent)
            ]
            tool_results:list[ToolResultContent] = []
            for tool_use in tool_use_block:
                tool_results.append(await self._execute_tool(tool_use,callbacks))

            user_message = Message(
                role=Role.USER,
                content=tool_results
            )
            messages.append(user_message)

        if turns_used>=max_turns:
            reached_max_turns=True

        #提取最终文本回复
        final_text = self._extract_final_text(messages)

        if callbacks and callbacks.on_complete:
            callbacks.on_complete("")

        return LoopResult(
            final_text=final_text,
            turn_used=turns_used,
            total_tokens=TokenUsage(
                input_tokens=total_input,
                output_tokens=total_output,
            ),
            reached_max_turns=reached_max_turns,
        )

    async def _execute_tool(self,tool_use:ToolUseContent,callbacks:SimpleCallbacks|None)->ToolResultContent:
        """
        执行工具调用

        :param tool_use: 工具调用内容
        :param callbacks: 回调函数
        :return: 工具调用结果
        """
        tool = self.tool_registry.get(tool_use.name)

        if tool is None:
            return ToolResultContent(
                tool_user_id=tool_use.id,
                content=f"Tool {tool_use.name} not found",
                is_error=True,
            )

        decision = self._permission_manager.check(tool,tool_use.input)

        if decision.value=='deny':
            return ToolResultContent(
                tool_user_id=tool_use.id,
                content=f"Permission denied for tool {tool_use.name}",
                is_error=True,
            )
        if decision=='ask':
            allowed = False
            if callbacks and callbacks.on_permission_ask:
                allowed = await callbacks.on_permission_ask(tool_use.name,tool_use.input)

            if not allowed:
                return ToolResultContent(
                    tool_user_id=tool_use.id,
                    content=f"Permission denied for tool {tool_use.name} by user",
                    is_error=True,
                )

        #执行工具
        if  callbacks and callbacks.on_tool_start:
            callbacks.on_tool_start(tool_use.name,tool_use.input)

        try:
            result = await tool.call(**tool_use.input)
            if callbacks and callbacks.on_tool_end:
                callbacks.on_tool_end(tool_use.name,result)

            return ToolResultContent(
                tool_user_id=tool_use.id,
                content=result.content,
                is_error=False,
            )
        except Exception as e:
            error_result = ToolResult(content=f"Tool execution error: {e}",is_error=True)
            if callbacks and callbacks.on_tool_end:
                callbacks.on_tool_end(tool_use.name,error_result)

            return ToolResultContent(
                tool_user_id=tool_use.id,
                content=error_result.content,
                is_error=True,
            )
    def _extract_final_text(self, messages: list[Message]) -> str:
        """从消息历史中提取最终文本回复"""
        for msg in reversed(messages):
            if msg.role == Role.ASSISTANT:
                if isinstance(msg.content, str):
                    return msg.content
                text_parts = [
                    b.text for b in msg.content if isinstance(b, TextContent)
                ]
                return "\n".join(text_parts)
        return ""