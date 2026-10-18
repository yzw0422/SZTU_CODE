"""
Glob 工具 -- 文件模式搜索

AI 需要发现项目中有哪些文件。 Glob 就是它的“目录浏览器”
"""

from __future__ import annotations # 启用类型提示
from pathlib import Path
from typing import Any
from sztu_agent.tools.base import Tool
from sztu_agent.system_types import ToolResult
# 排除的目录
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

class GlobTool(Tool):

    @property
    def name(self) -> str:
        return "glob"

    @property
    def description(self) -> str:
        return (
            "Find files matching a glob pattern in the project. "
            "Use this to discover project structure, find specific file types, or locate files by name. "
            'Examples: "**/*.py", "src/**/test_*.py", "pyproject.toml"'
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The glob pattern to match files against",
                },
                "cwd": {
                    "type": "string",
                    "description": "Directory to search in (optional, defaults to project root)",
                },
            },
            "required": ["pattern"],
        }
    @property
    def is_read_only(self) -> bool:
        return True
    async def call(self, **kwargs: dict[str, Any]) -> ToolResult:
        pattern = kwargs.pop("pattern")
        cwd:str|None = kwargs.pop("cwd", None)

        try:
            search_dir = Path(cwd) if cwd else Path.cwd()

            #使用pathlib glob. 过滤排除目录
            matches :list[str]=[]

            for path in search_dir.glob(pattern):
                # 过滤排除目录
                if path.name  in EXCLUDED_DIRS:
                    continue

                #f返回相对路径
                try:
                    rel = path.relative_to(search_dir)
                    matches.append(str(rel))
                except ValueError:
                    matches.append(str(path))

                if len(matches) >=200:
                    break

            if not matches:
                return ToolResult(content=f"No matches found:{pattern}",is_error=True)
            return ToolResult(
                content=f"Found {len(matches)} file(s):\n" + "\n".join(matches)
            )
        except Exception as e:
            return ToolResult(content=f"Error: {e} ({str(e)})",is_error=True)

if __name__ == '__main__':
    import asyncio
    glob_tool = GlobTool()
    print(asyncio.run(glob_tool.call(pattern="*.py",cwd=r"D:\sztu_code\src\sztu_agent\api")).content)