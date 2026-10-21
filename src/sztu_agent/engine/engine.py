"""
编排层 -- 会话引擎

设计思想：
- 这是“会话引擎”，管理这个对话的生命周期
- 它不关心API的调用细节，交给Provider
- 它不关心工具调用的细节，交给Loop
- 它关心的是：上下文构建，状态的管理、token追踪、自动压缩

职责：
1. 根据Provider 配置初始化对应的API客户端
2. 管理会话历史
3. 追踪token使用情况
4. 触发自动压缩
5. 暴露给外层调用
"""
import json
from dataclasses import dataclass

from sztu_agent.api.Base import BaseProvider, create_provider
from sztu_agent.context import ContextBuilder
from sztu_agent.loop import AgenticLoop
from sztu_agent.permission import PermissionManager
from sztu_agent.tools import create_default_tool_registry, Tool, create_plan_tool_registry
from sztu_agent.system_types import EngineConfig, Message, SimpleCallbacks, Role, PermissionRule, TextContent, ToolUseContent, ToolResultContent
from sztu_agent.loop.plan_execute import PlanExecuteLoop
@dataclass
class UsageStatus:
    """token 使用统计"""
    total_input: int = 0
    total_output:int =0
    turn_count:int =0


class QueryEngine:
    """
    会话引擎 — 整个框架对外暴露的核心接口

    支持多 Provider 的统一入口：

        engine = QueryEngine(EngineConfig(api_key="sk-ant-..."))

        # DeepSeek
        engine = QueryEngine(EngineConfig(
            provider="openai",
            api_key="sk-...",
            model="deepseek-v4-pro",
            base_url="https://api.deepseek.com/v1",
        ))

        # MiMo
        engine = QueryEngine(EngineConfig(
            provider="openai",
            api_key="sk-...",
            model="mimo-v2.5-pro",
            base_url="https://api.mimo.xiaomi.com/v1",
        ))

        # GPT-4o
        engine = QueryEngine(EngineConfig(
            provider="openai",
            api_key="sk-...",
            model="gpt-4o",
        ))
    """

    def __init__(self, engine_config: EngineConfig|None = None,**kwargs):
        """
        初始化会话引擎
        :param engine_config: 引擎配置
        :param kwargs: 其他参数
        """
        if engine_config is None:
            engine_config = EngineConfig(**kwargs)
        self._config = engine_config

        #1. 根据Provider 配置初始化对应的API客户端
        self._provider :BaseProvider=create_provider(
            provider=self._config.provider,
            api_key=self._config.api_key,
            model=self._config.model,
            base_url=self._config.base_url,
            max_tokens=self._config.max_token,
        )


        #初始化上下文
        self._context_builder = ContextBuilder(
            project_root=self._config.project_root,
            custom_system_prompt=self._config.custom_system_prompt,
        )

        #初始工具注册表
        self._tool_registry=create_default_tool_registry()
        self._tool_registry_with_plan_registry=create_plan_tool_registry()
        #初始化权限管理器
        self._permission_manager=PermissionManager(self._config.permission_rules)

        #组装AgenticLoop
        self._loop = AgenticLoop(
            api_client=self._provider,
            tool_registry=self._tool_registry_with_plan_registry,
            permission=self._permission_manager,
        )

        #组装PlanExecuteLoop
        #对话状态
        self._plan_loop=PlanExecuteLoop(
            api_client=self._provider,
            tool_registry=self._tool_registry,
            permission=self._permission_manager,
        )

        self._messages:list[Message]=[]
        self._usage = UsageStatus()

    async def chat(
            self,
            user_input:str,
            callbacks:SimpleCallbacks|None=None,
    ):
        """核心对话接口，也是整个框架对外暴露的核心接口"""
        #1. 将用户的消息，加入历史
        self._messages.append(Message(role=Role.USER,content=user_input))

        #2. 构建系统提示词
        system_prompt = await self._context_builder.build()
        # 3. 检查是否要自动压缩
        if self._should_compact():

            await self.auto_compact(callbacks)
        result = await self._loop.run(
            system_prompt=system_prompt,
            messages=self._messages,
            max_turns=self._config.max_turns,
            callbacks=callbacks,
        )
        #更新token 使用统计 
        self._usage.turn_count+=1
        self._usage.total_input+=result.total_tokens.input_tokens
        self._usage.total_output+=result.total_tokens.output_tokens
        final_result = result
        if result.need_plan:
            try:
                plans = json.loads(result.final_text)
                if not isinstance(plans, list):
                    return final_result
            except (json.JSONDecodeError, TypeError):
                return final_result
            plan_result = await self._plan_loop.run_plan_execute(
                system_prompt=system_prompt,
                plans=plans,
                messages=self._messages,
                max_turns=self._config.max_turns,
                callbacks=callbacks,
            )
            final_result.final_text += "\n" + plan_result.final_text
            final_result.total_tokens.input_tokens += plan_result.total_tokens.input_tokens
            final_result.total_tokens.output_tokens += plan_result.total_tokens.output_tokens
            final_result.turn_used += plan_result.turn_used
            if plan_result.reached_max_turns:
                final_result.reached_max_turns = True
        return final_result
    def _should_compact(self)->bool:
        """检查是否要自动压缩"""
        total=self._usage.total_input+self._usage.total_output
        return total>self._config.compact_threshold

    async def auto_compact(self, callbacks: SimpleCallbacks | None=None)->None:
        """自动压缩历史消息"""
        if len(self._messages)<4:
            return
        #1. 把结构化历史转成纯文本对话(绕开 function calling 约束)
        if callbacks is not None:
            callbacks.on_summary_start()
        dialogue_text = self._messages_to_text(self._messages)
        #2. 请求 LLM 生成摘要(不带 tools,也不传流式回调 —— 摘要短,用 start/end 状态提示足够)
        result = await self._provider.send_message(
            system_prompt="你是一个对话压缩助手。请将下面的对话历史压缩成一段简洁的中文摘要,保留关键事实、重要的工具调用结果、用户的核心需求,去掉冗余的过程描述。",
            messages=[Message(role=Role.USER,content=dialogue_text)],
        )
        summary = self._extract_text(result.content) or "(压缩摘要为空)"
        #3. 保留安全尾部
        safe_tail = self._find_safe_tail(self._messages, keep=4)
        #4. 新消息 = 摘要 + 安全尾部
        self._messages=[Message(role=Role.ASSISTANT,content=summary)]+safe_tail
        self._usage.total_input=result.token_usage.input_tokens
        self._usage.total_output=result.token_usage.output_tokens+self._estimate_tokens(safe_tail)
        if callbacks is not None:
            callbacks.on_summary_end()

    def _messages_to_text(self,messages:list[Message])->str:
        """
        把消息列表渲染成纯文本对话,用于交给 LLM 做摘要。
        这是绕开 function calling 约束的关键 —— 摘要请求不带 tools,
        所以历史里的 ToolUseContent/ToolResultContent 必须序列化为可读文字。
        """
        lines:list[str]=[]
        role_labels = {
            Role.USER: "用户",
            Role.ASSISTANT: "助手",
            Role.SYSTEM: "系统",
        }
        for msg in messages:
            label = role_labels.get(msg.role, msg.role.value)
            if isinstance(msg.content,str):
                text = msg.content
            else:
                text_parts:list[str]=[]
                for block in msg.content:
                    if isinstance(block,TextContent):
                        text_parts.append(block.text)
                    elif isinstance(block,ToolUseContent):
                        args_str = json.dumps(block.input,ensure_ascii=False)[:200]
                        text_parts.append(f"[调用工具 {block.name} 参数={args_str}]")
                    elif isinstance(block,ToolResultContent):
                        preview = block.content[:300].replace("\n"," ")
                        text_parts.append(f"[工具 {block.tool_user_id} 返回: {preview}]")
                text = "\n".join(text_parts)
            # 截断太长的单条
            if len(text)>800:
                text = text[:800]+"..."
            lines.append(f"【{label}】{text}")
        return "\n\n".join(lines)

    @staticmethod
    def _extract_text(content_blocks:list)->str:
        """从 APIResponse.content 里提取所有 TextContent 的文本,空则返回 ''"""
        return "\n".join(
            b.text for b in content_blocks if isinstance(b,TextContent) and b.text
        )

    def _find_safe_tail(self,messages:list[Message],keep:int=4)->list[Message]:
        """
        从尾部反向按"消息单元"保留,每个单元是:
          - 一个完整的 assistant(含 tool_use) + 紧随其后的 user(tool_result)
          - 或一条普通的 user/assistant 纯文本消息
        保证截断后不会出现 assistant(tool_calls) 后面没有 tool_result 的失配。
        """
        units:list[list[Message]]=[]
        i=len(messages)-1

        while i>=0 and len(units)<keep:
            msg=messages[i]

            if isinstance(msg.content,list):
                has_tool_use = any(isinstance(b,ToolUseContent) for b in msg.content)
                has_tool_result = any(isinstance(b,ToolResultContent) for b in msg.content)

                if has_tool_use and not has_tool_result:
                    # assistant 发了 tool_calls 但后面没 result —— 不完整,丢弃
                    i-=1
                    continue

                if has_tool_result:
                    # 这条是 tool result(role=USER),往前找触发它的 assistant(tool_use)
                    unit=[msg]
                    i-=1
                    if i>=0:
                        prev=messages[i]
                        if (prev.role==Role.ASSISTANT
                                and isinstance(prev.content,list)
                                and any(isinstance(b,ToolUseContent) for b in prev.content)):
                            unit.append(prev)
                            i-=1
                    unit.reverse()
                    units.append(unit)
                    continue

            # 纯文本消息,自己就是一个单元
            units.append([msg])
            i-=1

        units.reverse()
        return [m for unit in units for m in unit]
        

    def _estimate_tokens(self,messages:list[Message])->int:
        """进行token估计，4个字符=1个token"""
        char_count=0
        for msg in messages:
            if isinstance(msg.content, str):
                char_count+=len(msg.content)
            else:
                char_count+=len(json.dumps([vars(b) for b in msg.content],default=str))
        return char_count//4
    
    
    # 公开的查询/控制方法
    @property
    def messages(self)->list[Message]:
         return self._messages
    
    @property
    def usage(self)->UsageStatus:
        return self._usage
    
    @property
    def provider_info(self)->str:
        return f"{self._provider.provider_name}:{self._provider.model}"
    
    def reset(self):
        """重置会话状态"""
        self._messages.clear()
        self._usage=UsageStatus()
        
        
    def register_tool(self,tool:Tool):
        self._tool_registry.register(tool)
        self._tool_registry_with_plan_registry.register(tool)
        
    def add_permission(self,rule:PermissionRule):
        """添加权限规则"""
        self._permission_manager.add_rule(rule)