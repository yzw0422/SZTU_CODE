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
from sztu_agent.tools import create_default_tool_registry, Tool
from sztu_agent.system_types import EngineConfig, Message, SimpleCallbacks, Role, PermissionRule

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
            max_tokens=self._config.max_token
        )

        #初始化上下文
        self._context_builder = ContextBuilder(
            project_root=self._config.project_root,
            custom_system_prompt=self._config.custom_system_prompt,
        )

        #初始工具注册表
        self._tool_registry=create_default_tool_registry()

        #初始化权限管理器
        self._permission_manager=PermissionManager(self._config.permission_rules)

        #组装AgenticLoop
        self._loop = AgenticLoop(
            api_client=self._provider,
            tool_registry=self._tool_registry,
            permission=self._permission_manager,
        )

        #对话状态
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

        #3. 检查是否要自动压缩
        if self._should_compact():
            await self._auto_compact()
            
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
        return result
    def _should_compact(self)->bool:
        """检查是否要自动压缩"""
        total=self._usage.total_input+self._usage.total_output
        return total>self._config.compact_threshold

    async def _auto_compact(self)->None:
        """自动压缩历史消息"""
        if len(self._messages)<4:
            return
        #1. 压缩历史消息
        result = await self._provider.send_message(system_prompt="请压缩历史消息，保持核心信息",messages=self._messages)
        summary = result.content[0].content
        last_messages=self._messages[-4:]
        self._messages=[Message(role=Role.ASSISTANT,content=summary)]+last_messages
        self._usage.total_input=result.token_usage.input_tokens
        self._usage.total_output=result.token_usage.output_tokens+self._estimate_tokens(last_messages)
        

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
        """注册工具"""
        self._tool_registry.register(tool)
        
    def add_permission(self,rule:PermissionRule):
        """添加权限规则"""
        self._permission_manager.add_rule(rule)