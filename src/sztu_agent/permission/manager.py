"""
权限层 - 简化版权限控制

设计思想
- AI 调用每个工具都需要经过权限裁决
- 三种策略：
  - 允许所有工具调用（Allow），一般用于只读工具
  - 拒绝所有工具调用（Deny），一般用于危险操作
  - 询问用户确认（Ask），写操作
"""

from __future__ import annotations

from typing import Any

from sztu_agent.tools.base import Tool
import re

from sztu_agent.tools.bash import BashTool
from sztu_agent.tools.glob import GlobTool
from sztu_agent.system_types import PermissionRule,PermissionDecision
#危险命令模式（一律拒绝）
DANGEROUS_PATTERNS=[
    "rm -rf /",
    "rm -rf ~",
    "sudo rm",
    ":(){:|:&};:",  # fork bomb
    "mkfs",
    "dd if=",
    "> /dev/sd",
]
# 默认安全命令模式（自动放行）
SAFE_PATTERNS = [
    "git status",
    "git log",
    "git branch",
    "git diff",
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "echo",
    "pwd",
    "which",
    "python --version",
    "pip --version",
    "pip list",
]

class PermissionManager:
    """
    权限管理器
    裁决逻辑（优先级从高到低）
    1. 检查用户自定义规则
    2. 只读工具默认允许调用->Allow
    3. 危险命令模式（一律拒绝）->Deny
    4. 默认安全命令模式（自动放行）->Allow
    5. 其他命令默认询问用户确认->Ask
    """
    def __init__(self,rules:list[PermissionRule]|None=None):
        self._rules:list[PermissionRule]=rules

    def check(self,tool:Tool,tool_input:dict[str,Any])->PermissionDecision:
        """
        检查工具调用权限

        :param tool: 工具实例
        :param tool_input: 工具输入参数
        :return: 权限决策
        """
        #1. 用户自定义规则
        custom = self._match_custom_rules(tool,tool_input)
        if custom is not None:
            return custom
        #2. 只读工具默认允许调用->Allow
        if tool.is_read_only:
            return PermissionDecision.ALLOW

        # 3.bash命令需要额外检查命令的内容
        if tool.name=="bash":
            command = tool_input.get("command","")
            return self._check_bash_command(command)
        return PermissionDecision.ASK

    def _check_bash_command(self,command:str)->PermissionDecision:
        """检查bash命令是否危险或安全"""
        normalized = command.strip().lower()

        #危险命令->deny
        for pattern in DANGEROUS_PATTERNS:
            if pattern.lower() in normalized:
                return PermissionDecision.DENY

        for pattern in SAFE_PATTERNS:
            if normalized.startswith(pattern.lower()):
                return PermissionDecision.ALLOW

        return PermissionDecision.ASK

    def _match_custom_rules(
            self,
            tool:Tool,
            tool_input:dict[str,Any]
    )->PermissionDecision|None:
        """匹配用户自定义的规则"""
        if not self._rules:
            return None
        for rule in self._rules:
            if rule.tool!='*' and rule.tool!=tool.name:
                continue

            #如果规则有pattern,匹配命令内容
            if rule.pattern:
                command = tool_input.get("command","")
                if not self._match_pattern(command,rule.pattern):
                    continue

            return rule.decision
        return None

    def _match_pattern(self,text:str,pattern:str)->bool:
        """简单的模式匹配"""
        regex_pattern = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
        return bool(re.match(regex_pattern, text))

    def add_rule(self,rule:PermissionRule):
        """添加用户自定义规则"""
        self._rules.insert(0,rule) #新规则优先级最高

if __name__ == '__main__':
    pm = PermissionManager()
    # print(pm.check(BashTool(),{'command':'git status'}))
    print(pm.check(GlobTool(),{'pattern':'*.py'}))
