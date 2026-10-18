"""
FileRead 工具 -- 读取文件的内容

这是最基础的工具之一。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from sztu_agent.tools.base import Tool
from sztu_agent.system_types import ToolResult

class FileReadTool(Tool):
    @property
    def name(self) -> str:
        return "file_read"
    @property
    def description(self) -> str:
        return (
            "Read the contents of a file from the local filesystem. "
            "Use this when you need to examine code, configuration files, or any text file. "
            "The file_path must be an absolute path or relative to the project root. "
            "For large files, use offset and limit to read specific sections."
        )
    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to read",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (0-indexed, optional)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (optional, default: 2000)",
                },
            },
            "required": ["file_path"],
        }
    @property
    def is_read_only(self) -> bool:
        return True

    async def call(self,**kwargs: dict[str, Any]) ->ToolResult:
        file_path = kwargs.get("file_path")
        offset = kwargs.get("offset",0)
        limit = kwargs.get("limit",100)

        try:
            resolve = Path(file_path).resolve()
            if not resolve.is_file():
                return ToolResult(
                    content=f"The file {file_path} does not exist.",
                    is_error=True,
                )
            if not resolve.is_file():
                return ToolResult(
                    content=f"The file {file_path} is not a file.",
                    is_error=True,
                )

            text = resolve.read_text(encoding="utf-8")
            lines = text.split("\n")
            total_lines = len(lines)

            # 应用 offset 和 limit
            sliced = lines[offset:offset+limit]
            result = []
            for i,line in enumerate(sliced,start=offset):
                result.append(f"{i}: {line}")

            if offset>0 or limit<total_lines:
                end=min(limit+offset,total_lines)
                result.append(
                    f"[Showing lines {offset+1}-{end} of {total_lines}]\n\n"
                )
            final_output="\n".join(result)
            return ToolResult(content=final_output, is_error=False)
        except UnicodeDecodeError:
            return ToolResult(
                content=f"File is not valid UTF-8 text: {file_path}",
                is_error=True,
            )
        except Exception as e:
            return ToolResult(
                content=f"An error occured: {e}",
                is_error=True,
            )

if __name__ == '__main__':
    import asyncio
    tool = FileReadTool()
    print(asyncio.run(tool.call(file_path="./bash.py")).content)
