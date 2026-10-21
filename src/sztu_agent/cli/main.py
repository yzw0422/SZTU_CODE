"""
CLI 入口 — REPL 交互循环

通过 .sztu_code 配置文件配置 Provider 和模型，支持项目级和用户级配置。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from sztu_agent.engine.engine import QueryEngine
from sztu_agent.system_types import SimpleCallbacks, ToolResult


# ============================================================
# 颜色辅助
# ============================================================

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"


def colorize(color: str, text: str) -> str:
    return f"{color}{text}{Colors.RESET}"


# ============================================================
# 配置加载（从 .sztu_code 文件）
# ============================================================


def load_config() -> "EngineConfig":
    """
    从 .sztu_code 配置文件加载配置

    查找顺序：
    1. ./.sztu_code  — 当前工作目录（项目级）
    2. ~/.sztu_code  — 用户主目录（全局）
    """
    from sztu_agent.config import find_config_path, load_config_file, build_engine_config

    config_path = find_config_path()

    if config_path is None:
        print(colorize(Colors.RED, "错误: 未找到 .sztu_code 配置文件"))
        print("")
        print("  请在以下位置之一创建 .sztu_code 文件：")
        print("    ./.sztu_code  — 当前目录（项目级）")
        print("    ~/.sztu_code  — 用户主目录（全局）")
        print("")
        print("  配置文件示例：")
        print('    [provider]')
        print('    type = "deepseek"')
        print('    api_key = "$DEEPSEEK_API_KEY"')
        print('    model = "deepseek-v4-pro"')
        print("")
        print('    [agent]')
        print('    max_turns = 25')
        print("")
        sys.exit(1)

    file_config = load_config_file(config_path)
    return build_engine_config(file_config)


# ============================================================
# 权限询问
# ============================================================

async def ask_permission(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """交互式权限确认"""
    input_str = json.dumps(tool_input, ensure_ascii=False)[:200]
    print(colorize(Colors.MAGENTA, f"\n  🔒 权限确认: {tool_name}"))
    print(colorize(Colors.DIM, f"     {input_str}"))
    try:
        answer = input(colorize(Colors.MAGENTA, "     允许? (y/n): "))
        return answer.strip().lower().startswith("y")
    except (EOFError, KeyboardInterrupt):
        return False


# ============================================================
# REPL 主循环
# ============================================================

async def run_chat(engine: QueryEngine, user_input: str) -> None:
    """执行一次对话"""
    is_first_text = True

    def on_text_delta(text: str) -> None:
        nonlocal is_first_text
        if is_first_text:
            sys.stdout.write("\n")
            is_first_text = False
        sys.stdout.write(text)
        sys.stdout.flush()

    def on_tool_start(name: str, tool_input: dict[str, Any]) -> None:
        input_str = json.dumps(tool_input, ensure_ascii=False)[:100]
        print(colorize(Colors.YELLOW, f"\n  ⚙ {name}") + colorize(Colors.DIM, f" {input_str}"))

    def on_tool_end(name: str, result: ToolResult) -> None:
        status = colorize(Colors.RED, "✗") if result.is_error else colorize(Colors.GREEN, "✓")
        preview = result.content[:80].replace("\n", " ")
        print(colorize(Colors.DIM, f"  {status} {preview}..."))

    def on_summary_start() -> None:
        print(colorize(Colors.YELLOW, "\n  📦 触发上下文压缩中..."))

    def on_summary_end() -> None:
        print(colorize(Colors.GREEN, "  ✓ 压缩完成\n"))

    callbacks = SimpleCallbacks(
        on_text_delta=on_text_delta,
        on_tool_start=on_tool_start,
        on_tool_end=on_tool_end,
        on_permission_ask=ask_permission,
        on_summary_start=on_summary_start,
        on_summary_end=on_summary_end,
    )

    result = await engine.chat(user_input, callbacks=callbacks)

    # 展示统计
    print("\n")
    tokens = result.total_tokens
    print(colorize(
        Colors.DIM,
        f"  [tokens: in={tokens.input_tokens} out={tokens.output_tokens} | turns: {result.turn_used}]",
    ))




async def async_main() -> None:
    """异步主函数"""
    from sztu_agent.config import find_config_path

    config_path = find_config_path()
    config = load_config()
    engine = QueryEngine(config)

    from pyfiglet import Figlet

   
    f = Figlet(font="slant")
    logo_text = f.renderText("SZTU CODE")
    # ANSI青色
    print("\033[36m" + logo_text + "\033[0m")
    print("")

    # 信息卡片
    print(colorize(Colors.BOLD, "  SZTU_Code") + colorize(Colors.DIM, " v0.2.1"))
    print("")
    print(colorize(Colors.DIM, "  Provider  : ") + colorize(Colors.GREEN, engine.provider_info))
    if config.base_url:
        print(colorize(Colors.DIM, "  Endpoint  : ") + colorize(Colors.DIM, config.base_url))
    if config_path:
        print(colorize(Colors.DIM, "  Config    : ") + colorize(Colors.DIM, str(config_path)))
    print(colorize(Colors.DIM, "  Project   : ") + colorize(Colors.DIM, config.project_root))
    print(colorize(Colors.DIM, "  ────────────────────────────────────────────────"))
    print("")
    print(colorize(Colors.DIM, "  输入需求开始对话"))
    print(colorize(Colors.DIM, "  /quit 退出  /clear 清空  /usage 消耗  /model 模型  /compact 压缩"))
    print("")

    while True:
        try:
            user_input = input(colorize(Colors.CYAN, "  ✦ "))
        except (EOFError, KeyboardInterrupt):
            print(colorize(Colors.DIM, "\nBye!"))
            break

        trimmed = user_input.strip()
        if not trimmed:
            continue

        # 斜杠命令
        if trimmed in ("/quit", "/exit"):
            print(colorize(Colors.DIM, "\nBye!"))
            break

        if trimmed == "/clear":
            engine.reset()
            print(colorize(Colors.DIM, "对话已清空。\n"))
            continue

        if trimmed == "/usage":
            usage = engine.usage
            print(colorize(
                Colors.CYAN,
                f"\nToken 消耗: input={usage.total_input}, output={usage.total_output}, turns={usage.turn_count}\n",
            ))
            continue
        if trimmed == "/compact":
            await engine.auto_compact()
            continue

        if trimmed == "/model":
            print(colorize(Colors.CYAN, f"\n  当前: {engine.provider_info}\n"))
            continue

        # 正常对话
        try:
            await run_chat(engine, trimmed)
        except Exception as e:
            print(colorize(Colors.RED, f"\n错误: {e}\n"))


def main() -> None:
    """入口函数"""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()