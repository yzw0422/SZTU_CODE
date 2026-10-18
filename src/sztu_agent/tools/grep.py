"""
Grep 工具 -- 代码内容搜索

AI 需要在项目中搜索特定的代码模式
比如找到某个函数的所有调用点，搜索错误消息来源等。

纯 Python 实现，跨平台（Windows / macOS / Linux）均可用
"""
from __future__ import annotations
import re
import asyncio
from typing import Any
from pathlib import Path
from sztu_agent.tools.base import Tool
from sztu_agent.system_types import ToolResult

EXCLUDED_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "egg-info",
}

MAX_RESULTS = 100
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB，跳过二进制/大文件


class GrepTool(Tool):
    @property
    def name(self) -> str:
        return "grep"

    @property
    def description(self) -> str:
        return (
            "Search for a regex pattern in file contents. "
            "Returns matching lines with file paths and line numbers. "
            "Use this to find function definitions, usages, error messages, etc."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The regex pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "Directory or file to search in (optional, defaults to project root)",
                },
                "include": {
                    "type": "string",
                    "description": 'File glob pattern to include (e.g., "*.py", "src/**/*.ts")',
                },
            },
            "required": ["pattern"],
        }

    @property
    def is_read_only(self) -> bool:
        return True

    async def call(self, **kwargs: dict[str, Any]) -> ToolResult:
        pattern: str = kwargs.get("pattern", "")
        path_arg: str | None = kwargs.get("path")
        include: str | None = kwargs.get("include")

        try:
            regex = re.compile(pattern)
        except re.error as e:
            return ToolResult(content=f"Invalid regex pattern: {e}", is_error=True)

        target = Path(path_arg) if path_arg else Path.cwd()
        results: list[str] = []

        try:
            if target.is_file():
                await self._search_file(target, regex, results)
            elif target.is_dir():
                glob_pattern = include if include else "**/*"
                for file_path in target.glob(glob_pattern):
                    if len(results) >= MAX_RESULTS:
                        break
                    if not file_path.is_file():
                        continue
                    if any(part in EXCLUDED_DIRS for part in file_path.parts):
                        continue
                    await self._search_file(file_path, regex, results)
            else:
                return ToolResult(
                    content=f"Path not found: {target}", is_error=True
                )
        except Exception as e:
            return ToolResult(content=f"Search error: {e}", is_error=True)

        if not results:
            return ToolResult(
                content=f"No matches found for '{pattern}' in {target}"
            )

        return ToolResult(
            content=f"Found {len(results)} match(es) for '{pattern}' in {target}:\n"
            + "\n".join(results)
        )

    async def _search_file(
        self, file_path: Path, regex: re.Pattern, results: list[str]
    ) -> None:
        try:
            if file_path.stat().st_size > MAX_FILE_SIZE:
                return
            content = await asyncio.to_thread(
                file_path.read_text, encoding="utf-8", errors="replace"
            )
        except (OSError, PermissionError):
            return

        for lineno, line in enumerate(content.splitlines(), start=1):
            if regex.search(line):
                results.append(f"{file_path}:{lineno}: {line.strip()}")
                if len(results) >= MAX_RESULTS:
                    return


if __name__ == "__main__":
    async def main():
        tool = GrepTool()
        result = await tool.call(
            pattern="asyncio",
            path=r"D:\sztu_code\src\sztu_agent\tools",
            include="*.py",
        )
        print(result.content)

    asyncio.run(main())