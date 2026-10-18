"""
文件编辑工具 -- 字符串替换式编辑

设计思想
- 不是“全文替换”，而是“精准替换”
- AI 提供old_string 和 new_string,系统找到并替换
- 比全文覆盖更安全，避免误操作，更省token
- 如果old_string 找不到或者有多个匹配，报错
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

from sztu_agent.tools.base import Tool
from sztu_agent.system_types import ToolResult

class FileEditTool(Tool):
    @property
    def name(self)->str:
        return "file_edit"

    @property
    def description(self)->str:
        return (
            "Make a targeted edit to an existing file by replacing a specific string. "
            "Provide the exact text to find (old_string) and the replacement (new_string). "
            "The old_string must match EXACTLY (including whitespace and indentation). "
            "If old_string appears multiple times, the edit will fail — include more context to make it unique."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to edit",
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact string to find and replace",
                },
                "new_string": {
                    "type": "string",
                    "description": "The replacement string",
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        }
    @property
    def is_read_only(self) -> bool:
        return False

    async def call(self,**kwargs) -> ToolResult:
        file_path=kwargs["file_path"]
        old_string=kwargs["old_string"]
        new_string=kwargs["new_string"]

        try:
            resolve = Path(file_path).resolve()

            if not resolve.is_file():
                return ToolResult(
                    content=f"The file {file_path} does not exist.",
                    is_error=True,
                )
            content = resolve.read_text(encoding="utf-8")
            # 检查 old_string 出现次数
            occurrences = content.count(old_string)
            if occurrences == 0:
                return ToolResult(
                    content=f"The string {old_string} does not exist in the file {file_path}，Make sure it matches exactly (including whitespace).",
                    is_error=True,
                )
            if occurrences >1:
                return ToolResult(
                    content=f"The string {old_string} appears multiple times in the file {file_path}，Make sure it is unique.",
                    is_error=True,
                )
            #执行替换
            new_content = content.replace(old_string, new_string,1)
            resolve.write_text(new_content,encoding="utf-8")
            return ToolResult(
                content=f"The string {old_string} in the file {file_path} has been replaced with {new_string}.",
            )
        except Exception as e:
            return ToolResult(
                content=f"Error editing file {file_path}: {e}",
                is_error=True,
            )

if __name__ == '__main__':
    import asyncio
    tool=FileEditTool()
    print(asyncio.run(tool.call(file_path="./bash.py",old_string="hang",new_string="")))
