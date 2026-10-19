"""
生成任务计划,输入任务描述,输出任务计划.
"""
import json
from typing import Any

from sztu_agent.system_types import ToolResult
from sztu_agent.tools import Tool

class MakePlanTool(Tool):
    @property
    def name(self) -> str:
        return 'make_plan'

    @property
    def description(self) -> str:
        return (
            "根据用户的问题生成一个分步执行的任务计划。"
            "请返回JSON数组字符串,每个元素包含:id(任务唯一标识),description(任务详细描述),version(版本号,初始为0)。"
            "格式示例: [{\"id\":\"task1\",\"description\":\"...\",\"version\":0},{\"id\":\"task2\",\"description\":\"...\",\"version\":0}]"
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
               "plan_json": {
                   "type": "string",
                   "description": "任务计划的JSON数组字符串,每个元素包含id、description、version字段",
               }
            },
            "required": ["plan_json"],
        }
    @property
    def is_read_only(self) -> bool:
        return True

    async def call(self, **kwargs: dict[str, Any]) -> ToolResult:
        plan_json = kwargs.get("plan_json", "")
        if not plan_json:
            return ToolResult(content="计划内容不能为空", is_error=True)
        try:
            task_list = json.loads(plan_json)
            if not isinstance(task_list, list):
                return ToolResult(content="计划必须为JSON数组", is_error=True)
            REQUIRED_FIELDS = {"id", "description"}
            for idx, item in enumerate(task_list):
                if not isinstance(item, dict):
                    return ToolResult(content=f"第{idx}个任务项必须为对象", is_error=True)
                missing = REQUIRED_FIELDS - set(item.keys())
                if missing:
                    return ToolResult(content=f"第{idx}个任务缺少必需字段: {missing}", is_error=True)
                item.setdefault("version", 0)
            return ToolResult(content=json.dumps(task_list, ensure_ascii=False), is_error=False)
        except json.JSONDecodeError as e:
            return ToolResult(content=f"计划JSON格式错误: {e}", is_error=True)
        except Exception as e:
            return ToolResult(content=f"制定计划失败: {e}", is_error=True)