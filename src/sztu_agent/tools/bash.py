"""
Bash 工具-执行Shell命令

这是最强大的工具也是最危险的工具，因为你可以执行任何Shell命令，包括删除文件、修改系统配置等。
因此权限系统对它的管控最严格

设计思想：
- 给AI完整的shell能力
- 超时机制防止命令卡死
- 输出长度限制防止token爆炸
"""
from __future__ import annotations
import asyncio
import os
from typing import Any
from sztu_agent.tools.base import Tool
from sztu_agent.system_types import ToolResult
# 最大输出长度
MAX_OUTPUT_LENGTH:int=30000
# 默认超时时间
DEFAULT_TIMEOUT:int=120

class BashTool(Tool):
   """Bash 工具-执行Shell命令"""
   @property
   def name(self)->str:
       return "bash"
   @property
   def description(self)->str:
       return (
           "Execute a bash command in the shell. "
           "Use this for running programs, installing packages, git operations, searching files, etc. "
           "Commands run in the project root directory by default. "
           "Long-running commands (like dev servers) should NOT be run with this tool. "
           f"Max output is truncated if it exceeds {MAX_OUTPUT_LENGTH} characters."
       )

   @property
   def input_schema(self)->dict[str,Any]:
       return {
           "type": "object",
           "properties": {
               "command": {
                   "type": "string",
                   "description": "The bash command to execute.",
               },
               "cwd":{
                   "type": "string",
                   "description": "Working directory (optional, defaults to project root)",
               },
               "timeout":{
                   "type": "integer",
                   "description": f"Timeout in seconds (optional, defaults to {DEFAULT_TIMEOUT})",
               },
           },
           "required": ["command"],
       }
   @property
   def is_read_only(self) -> bool:
       return False

   async def call(self,**kwargs: Any) -> ToolResult:
       command:str=kwargs.get("command")
       cwd:str|None=kwargs.get("cwd",os.getcwd())
       timeout:int=kwargs.get("timeout",DEFAULT_TIMEOUT)

       try:
              env = {**os.environ,"TERM":"dumb"}

              process = await asyncio.create_subprocess_shell(
                  command,
                  stdout=asyncio.subprocess.PIPE,
                  stderr=asyncio.subprocess.PIPE,
                  cwd=cwd,
                  env=env,
              )

              try:
                  stdout_bytes,stderr_bytes=await asyncio.wait_for(
                      process.communicate(),
                      timeout=timeout,
                  )
              except asyncio.TimeoutError:
                  process.kill()
                  return ToolResult(
                      content="Error: Command timeout after {} seconds".format(timeout),
                      is_error=True,
                  )

              stdout = stdout_bytes.decode("gbk",errors="replace")
              stderr = stderr_bytes.decode("gbk",errors="replace")
              # 合并输出
              output = ""
              if stdout:
                  output += stdout
              if stderr:
                  output += ("\n" if stdout else "")+f"[stderr]\n{stderr}"
              # 截断输出
              if len(output) > MAX_OUTPUT_LENGTH:
                  output = output[:MAX_OUTPUT_LENGTH]
                  output += "\n...Truncated to {} characters".format(MAX_OUTPUT_LENGTH)

              # 检测退出码
              if process.returncode!=0:
                  return ToolResult(
                      content=f"Command failed (exit code {process.returncode}):\n{output}" if output else f"Command failed with exit code {process.returncode}",
                      is_error=True,
                  )
              return ToolResult(content=output or "(no output)")
       except Exception as e:
           return ToolResult(content=f"Error executing command: {e}", is_error=True)

if __name__ == '__main__':
    bash_tool=BashTool()
    print(asyncio.run(bash_tool.call(command="dir")))
