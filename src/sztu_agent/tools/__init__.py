from sztu_agent.tools.base import Tool,ToolRegistry
from sztu_agent.tools.file_edit import FileEditTool
from sztu_agent.tools.glob import GlobTool
from sztu_agent.tools.file_read import FileReadTool
from sztu_agent.tools.file_write import FileWriteTool
from sztu_agent.tools.grep import GrepTool
from sztu_agent.tools.bash import BashTool

def create_default_tool_registry() -> ToolRegistry:
     registry = ToolRegistry()
     registry.register_all([
          FileEditTool(),
          GlobTool(),
          FileReadTool(),
          FileWriteTool(),
          GrepTool(),
          BashTool(),
     ])
     return registry

__all__ = \
     [
          'create_default_tool_registry',
          'ToolRegistry',
          'Tool',
          'ToolRegistry',
          'FileEditTool',
          'GlobTool',
          'FileReadTool',
          'FileWriteTool',
          'GrepTool',
          'BashTool'
      ]
