# SZTU_Code

> 一个面向代码任务的 AI Agent，ReAct 模式驱动，支持多 Provider、多工具、流式输出。

## ✨ 特性

- 🧠 **ReAct 推理循环** — 模型自主决定何时调用工具、何时继续思考
- 🔌 **多 Provider 支持** — DeepSeek、OpenAI（以及任意 OpenAI 兼容 API）
- 🛠️ **6 个内置工具** — 文件读写编辑、glob 查找、grep 搜索、bash 执行
- 💬 **流式输出** — Token 级实时显示，打字机体验
- 🔐 **权限管控** — 工具调用前自动拦截，支持 allow/deny 规则
- 📊 **Token 统计** — 实时追踪消耗，自动上下文压缩
- ⚡ **一键启动** — `sztu-code` 全局命令，双击 setup 脚本自动配置

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 一个支持的 AI Provider API Key（DeepSeek / OpenAI）

### 一行配置

**Windows（双击）：**
```
scripts\setup.bat
```

**Linux / macOS：**
```bash
bash scripts/setup.sh
```

脚本会自动完成：
1. 检查 Python 版本
2. 安装依赖（`pip install -e .`）
3. 创建 `.sztu_code` 配置文件（交互式输入 API Key）
4. 验证 `sztu-code` 命令可用

### 启动

```bash
sztu-code
```

## 📁 项目结构

```
sztu_code/
├── src/sztu_agent/
│   ├── api/              # Provider 抽象层（OpenAI / DeepSeek / ...）
│   ├── cli/              # 命令行入口 & REPL
│   ├── context/          # 上下文构建 & 压缩
│   ├── engine/           # 对话引擎，对外主接口
│   ├── loop/             # Agentic Loop（ReAct 循环）
│   ├── permission/       # 权限管理器
│   ├── tools/            # 工具注册表 & 内置工具实现
│   └── system_types.py   # 核心数据结构定义
├── scripts/
│   ├── setup.bat         # Windows 一键配置
│   ├── setup.ps1         # PowerShell 核心脚本
│   └── setup.sh          # Linux/macOS 一键配置
├── .sztu_code            # 用户配置（加入 .gitignore）
├── pyproject.toml        # 打包配置
└── .gitignore
```

## 🛠️ 内置工具

| 工具 | 用途 |
|------|------|
| `file_read` | 读取文件内容，支持 offset/limit 分段 |
| `file_write` | 创建或覆盖写入文件 |
| `file_edit` | 精确替换（old_string → new_string） |
| `glob` | 按通配符查找文件（如 `**/*.py`） |
| `grep` | 正则搜索文件内容 |
| `bash` | 执行 shell 命令 |

## ⌨️ CLI 命令

在 REPL 中可用：

| 命令 | 说明 |
|------|------|
| `/quit` | 退出 |
| `/clear` | 清空对话历史 |
| `/usage` | 查看 Token 消耗统计 |
| `/model` | 切换模型 |

## ⚙️ 配置文件

`.sztu_code` 按优先级查找：当前目录 → 项目根 → `~/.sztu_code`

```toml
[provider]
type = "deepseek"
api_key = "$DEEPSEEK_API_KEY"    # 支持 $ENV_VAR 环境变量引用
model = "deepseek-v4-flash"
# base_url = "https://api.deepseek.com/v1"   # 可选，预设自动填

[agent]
max_turns = 25          # 单次对话最大循环次数
max_tokens = 4096       # API 最大输出 token

[permissions]
# allow = ["bash:git *", "file_read"]     # 自动放行
# deny = ["bash:rm -rf *"]                # 自动拒绝
```

### Provider 预设

| type | 默认模型 | Base URL |
|------|---------|----------|
| `deepseek` | `deepseek-v4-flash` | `https://api.deepseek.com/v1` |
| `openai` | `gpt-4o-mini` | `https://api.openai.com/v1` |

也可以填任意自定义 `base_url` + `type = "openai"` 来接入其他 OpenAI 兼容 API（如阿里云百炼、硅基流动等）。

## 🏗️ 架构设计

```
用户输入
   │
   ▼
┌─────────────┐
│   CLI REPL  │  ← cli/main.py
└──────┬──────┘
       │ chat(user_input)
       ▼
┌─────────────┐
│   Engine    │  ← engine/engine.py   对外主接口，维护消息历史
└──────┬──────┘
       │ run(system_prompt, messages)
       ▼
┌─────────────┐
│ AgenticLoop │  ← loop/loop.py       ReAct 推理循环
└──┬───┬───┬──┘
   │   │   │
   ▼   │   ▼
Provider │  ToolRegistry
(api/)   │  (tools/)
         │
    Permission
    Manager
    (permission/)
```

核心循环逻辑（简化）：

```python
while turn < max_turns:
    response = provider.send_message(messages, tools)

    if response.stop_reason == "end_turn":
        break                              # 模型说"说完了"

    if response.stop_reason == "tool_use":
        for tool_use in response.tool_calls:
            result = registry.execute(tool_use)  # 权限检查 → 执行
            tool_results.append(result)

        messages.append(assistant_message)        # 本轮模型回复
        messages.append(tool_results_as_user)    # 工具结果作为下一轮输入
        continue
```

## 🔒 安全说明

- `.sztu_code` 已加入 `.gitignore`，不要将 API Key 提交到仓库
- 推荐使用 `$ENV_VAR` 方式引用环境变量，而非明文写入
- 权限管理器可拦截危险工具调用（`[permissions] deny = [...]`）

## 📝 License

MIT