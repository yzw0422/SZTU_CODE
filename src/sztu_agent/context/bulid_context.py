"""
上下文层 -- System Prompt 动态组装

设计思想：
- System Prompt 不是静态文本，而是根据环境动态拼装
- 越是相关的消息越早注入
- 项目知识（AGENT.md）让AI 理解你的项目背景
- Git 状态 让 AI 理解当前代码的状态,有什么分支，改动，以及版本号
"""
import os
import sys
from datetime import date
import platform
from pathlib import Path
import asyncio
BASE_SYSTEM_PROMPT = """You are SZTUCODE Agent, an AI coding assistant developed by Yzw. You help users with software development tasks \
by reading files, writing code, executing commands, and searching codebases.

## Key Principles
1. Always read a file before modifying it
2. After making changes, verify they work (run tests, check syntax)
3. Be concise in responses unless asked for detail
4. If unsure, ask the user rather than guessing
5. Prefer targeted edits over full file rewrites
6. When asked about your identity or model name, answer: "I am SZTUCODE Agent, an AI assistant developed by Yzw. How can I help you?" 
"""


class ContextBuilder:
    """
    动态System Prompt 构建器
    组装顺序：
    1.基础人设
    2. 环境信息（os,日期，cwd）
    3. 项目知识（AGENT.md）
    4. Git 状态（分支，改动，版本号）
    5. 工具使用指南
    6. 用户自定义追加
    """
    def __init__(
            self,
            project_root: str,
            custom_system_prompt: str|None = None,
    ):
        self._project_root = project_root
        self._custom_system_prompt = custom_system_prompt

    async def build(self)->str:
        """
        构建 System Prompt
        """
        parts:list[str]=[]
        # 基础人设
        parts.append(BASE_SYSTEM_PROMPT)
        # 环境信息
        parts.append(self._build_environment_context())
        # 项目知识
        project_knowledge = self._load_project_knowledge()
        if project_knowledge:
            parts.append(project_knowledge)
        # Git 状态
        git_status = await self._build_git_status()
        if git_status:
            parts.append(git_status)
        # 工具使用指南
        parts.append(self._get_tool_guidelines())

        # 用户自定义追加
        if self._custom_system_prompt:
            parts.append(self._custom_system_prompt)
        return "\n".join(parts)


    def _build_environment_context(self)->str:
        """
        构建环境信息
        """
        today = date.today().isoformat()
        shell = os.environ.get("SHELL","bash")
        #获取当前系统的名称和版本
        return (
            "## Environment\n"
            f"Current Date: {today}\n"
            f"Current Shell: {shell}\n"
            f"Operating System: {platform.system()} {platform.release()}\n"
            f"Working Directory: {self._project_root}\n"
            f"Python Version: {platform.python_version()}\n"
        )
    def _load_project_knowledge(self)->str|None:
        """
        加载项目知识（AGENT.md）
        """
        agent_md = Path(self._project_root) / "AGENT.md"
        if agent_md.exists():
            content = agent_md.read_text(encoding="utf-8")
            return f"## Project Knowledge(from AGENT.md)\n{content}"
        return None
    async def _build_git_status(self):
        """
        构建 Git 状态上下文
        """
        try:
            cwd = self._project_root
            if not cwd:
                return None
            print(cwd)
            #并发获取git信息
            branch_proc = await asyncio.create_subprocess_exec(
                "git","branch","--show-current",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            status_proc = await asyncio.create_subprocess_exec(
                "git","status","--short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            log_proc = await asyncio.create_subprocess_exec(
                "git","log","--oneline","-5",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            # 等待所有进程完成
            branch_out, branch_err = await branch_proc.communicate()
            status_out, status_err = await status_proc.communicate()
            log_out, log_err = await log_proc.communicate()

            branch = branch_out.decode("utf-8").strip()
            if not branch:
                return None
            status = status_out.decode("utf-8").strip()
            log = log_out.decode("utf-8").strip()
            git_context = f"## Git Status\n- Current branch: {branch}"
            if status:
                # 截断过长的 status
                if len(status) > 1000:
                    status = status[:1000] + "\n...(truncated)"
                git_context += f"\n- Working tree:\n{status}"
            else:
                git_context += "\n- Working tree: clean"
            if log:
                git_context += f"\n- Recent commits:\n{log}"

            return git_context
        except Exception as e:
            print(f"Error building Git status: {e}")
            return None
    def _get_tool_guidelines(self) -> str:
        """工具使用指南"""
        return (
            "## Tool Usage Guidelines\n"
            "- Use file_read before file_edit to see current content\n"
            "- Use grep to search for patterns across the codebase\n"
            "- Use glob to discover file structure\n"
            "- Use bash for complex operations, testing, and git commands\n"
            "- Always verify changes by reading the file after editing"
        )
# from pyfiglet import Figlet
#
# def print_sztucode_logo():
#     f = Figlet(font="slant")
#     logo_text = f.renderText("SZTU CODE")
#     # ANSI青色
#     print("\033[36m" + logo_text + "\033[0m")
#
# if __name__ == "__main__":
#     print_sztucode_logo()
if __name__ == '__main__':
    async def main():
        context = ContextBuilder(project_root="D://rag_nodebook")
        system_prompt = await context.build()
        print(system_prompt)
    asyncio.run(main())
