"""
plan-execute模式，处理较为复杂的任务，让智能体先去生成一个一个计划，然后执行计划中的每个步骤

设计：
- 和主 AgenticLoop 共享同一个 messages 列表，保证上下文不丢失
- 每个 plan step 在共享 messages 上继续 ReAct 循环
- 所有执行细节自然累积到 messages，用户后续对话不会失忆
"""
from typing import Any

from sztu_agent.api.Base import BaseProvider
from sztu_agent.permission import PermissionManager
from sztu_agent.system_types import Message, SimpleCallbacks, TokenUsage, Role, LoopResult
from sztu_agent.tools import ToolRegistry

from sztu_agent.loop.loop import AgenticLoop


class PlanExecuteLoop:
    def __init__(
            self,
            api_client: BaseProvider,
            tool_registry: ToolRegistry,
            permission: PermissionManager
    ):
        self.api_client = api_client
        self.tool_registry = tool_registry
        self._permission_manager = permission

    async def run_plan_execute(
            self,
            system_prompt: str,
            plans: list[dict[str, Any]],
            messages: list[Message],
            *,
            max_turns: int = 100,
            callbacks: SimpleCallbacks | None = None
    ):
        turn_used: int = 0
        input_tokens = 0
        output_tokens = 0
        reached_max_turns = False

        executor_loop = AgenticLoop(
            self.api_client, self.tool_registry, self._permission_manager
        )

        for plan in plans:
            messages.append(Message(
                role=Role.USER,
                content=f"【执行计划步骤】{plan['id']}: {plan['description']}"
            ))

            result = await executor_loop.run(
                system_prompt,
                messages=messages,
                max_turns=25,
                callbacks=callbacks,
            )

            input_tokens += result.total_tokens.input_tokens
            output_tokens += result.total_tokens.output_tokens
            turn_used += result.turn_used
            plan["version"] = 1

            if turn_used >= max_turns:
                reached_max_turns = True
                break

        summary = await executor_loop.run(
            system_prompt,
            messages=messages,
            max_turns=5,
            callbacks=callbacks,
        )

        return LoopResult(
            final_text=summary.final_text,
            turn_used=turn_used + summary.turn_used,
            total_tokens=TokenUsage(
                input_tokens=input_tokens + summary.total_tokens.input_tokens,
                output_tokens=output_tokens + summary.total_tokens.output_tokens,
            ),
            reached_max_turns=reached_max_turns,
        )