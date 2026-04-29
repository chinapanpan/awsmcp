# 技术方案设计：AWS Agent with Remote MCP

## 1. 项目概述

### 1.1 目标
基于 Strands Agents SDK 开发一个 AI Agent，该 Agent 集成 AWS API MCP Server 以获得 AWS 云服务操作能力，然后将该 Agent 封装为一个 Remote MCP Server，使外部 Agent（如 Claude Code）可以通过 MCP 协议远程调用。

### 1.2 核心价值
- **统一 AWS 操作入口**：通过自然语言与 AWS 云服务交互
- **Agent 即服务**：将 Agent 能力通过标准 MCP 协议对外暴露
- **可组合性**：外部 Agent 可以像调用工具一样调用本 Agent
- **配置驱动扩展**：通过 JSON 配置文件即可添加新的 MCP Server 和 Skill，无需修改代码

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    外部 Agent (Claude Code 等)                    │
│                         │                                        │
│              MCP Client (streamable-http)                        │
└─────────────┬───────────────────────────────────────────────────┘
              │ HTTP (port 8080)
              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Remote MCP Server Layer                              │
│         (FastMCP, streamable-http transport)                     │
│                                                                  │
│  Exposed Tools:                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ aws_agent_chat: 与 AWS Agent 自然语言对话                  │   │
│  │ aws_agent_execute: 执行特定 AWS 操作                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                        │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Strands Agent Core                            │   │
│  │  - Model: Bedrock (Claude Sonnet 4.6)                     │   │
│  │  - System Prompt: AWS 专家 (可配置)                        │   │
│  │  - Tools: 从 agent_config.json 动态加载                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│              │                              │                     │
│     MCP Servers (配置驱动)           Skills (配置驱动)            │
│              │                              │                     │
│  ┌───────────────────┐      ┌──────────────────────────────┐   │
│  │ aws-api-mcp-server│      │ builtin: strands_tools.*     │   │
│  │ (stdio, uvx)      │      │ custom:  ./skills/*.py       │   │
│  ├───────────────────┤      │ package: pip install xxx     │   │
│  │ 更多 MCP Server...│      ├──────────────────────────────┤   │
│  │ (配置即生效)       │      │ 更多 Skill...               │   │
│  └───────────────────┘      │ (配置即生效)                  │   │
│              │               └──────────────────────────────┘   │
│         IAM Role                                                 │
│              │                                                   │
│              ▼                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              AWS Cloud Services                            │   │
│  │  (S3, EC2, Lambda, DynamoDB, IAM, etc.)                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 3. 技术选型

| 组件 | 技术选择 | 版本 | 说明 |
|------|----------|------|------|
| Agent 框架 | Strands Agents SDK | 1.37.0 | AWS 官方 Agent 框架 |
| LLM | Amazon Bedrock (Claude Sonnet) | - | 通过 EC2 IAM Role 访问 |
| AWS 操作 | aws-api-mcp-server | latest | AWS 官方 MCP Server |
| MCP Server | mcp (FastMCP) | 1.27.0 | MCP 协议官方实现 |
| 运行时 | Python | 3.12 | EC2 环境已安装 |
| HTTP Server | uvicorn | 0.46.0 | FastMCP 内置使用 |

## 4. 模块设计

### 4.1 项目结构

```
awsmcp/
├── docs/
│   ├── design.md           # 技术方案设计文档
│   └── test_report.md      # 测试验证报告
├── src/
│   ├── __init__.py
│   ├── agent.py            # Strands Agent 核心（配置驱动加载 MCP + Skill）
│   ├── mcp_server.py       # Remote MCP Server 封装
│   └── config.py           # 配置管理
├── skills/                 # 自定义 Skill 目录（放入 .py 文件即可）
│   └── example_custom_skill.py  # Skill 模板
├── scripts/
│   ├── start_server.sh     # 启动脚本
│   └── test_client.py      # 测试客户端
├── agent_config.json       # ★ 核心配置（MCP + Skill + Agent 参数全在此）
├── requirements.txt
└── README.md
```

### 4.2 核心模块

#### 4.2.1 config.py - 配置管理
- AWS Region 配置
- Bedrock 模型 ID 配置
- MCP Server 端口配置
- aws-api-mcp-server 启动参数

#### 4.2.2 agent.py - Agent 核心（配置驱动）
- 从 `agent_config.json` 读取配置
- 动态加载所有启用的 **MCP Server** (MCPClient)
- 动态加载所有启用的 **Skill** (builtin/custom/package)
- 初始化 BedrockModel，创建 Strands Agent
- 提供 `chat()` 方法供外部调用

#### 4.2.3 mcp_server.py - Remote MCP Server
- 使用 FastMCP 创建 MCP Server
- 定义两个工具：
  - `aws_agent_chat(message: str) -> str`：自然语言对话
  - `aws_agent_execute(task: str) -> str`：执行特定 AWS 操作任务
- 以 streamable-http 模式启动，监听 0.0.0.0:8080

## 5. 数据流

### 5.1 外部 Agent 调用流程

```
1. 外部 Agent → MCP Client 连接 http://host:8080/mcp/
2. MCP Client → 调用 aws_agent_chat(message="列出所有S3 buckets")
3. Remote MCP Server → 调用 Strands Agent.chat()
4. Strands Agent → 思考并调用 MCPClient (aws-api-mcp-server)
5. MCPClient → aws-api-mcp-server → 执行 `aws s3 ls`
6. 结果逐层返回 → 外部 Agent 获得格式化结果
```

## 6. 安全设计

- **认证**：EC2 IAM Role，无需 AK/SK
- **权限控制**：通过 IAM Policy 限制可操作的 AWS 服务
- **网络**：MCP Server 默认监听 localhost，可通过安全组控制外部访问
- **操作审计**：Agent 的每次操作都会记录日志

## 7. 部署方案

### 7.1 当前 EC2 部署
- 直接在 EC2 上运行 Python 服务
- 使用 EC2 绑定的 IAM Role 访问 AWS 服务和 Bedrock
- MCP Server 监听 8080 端口

### 7.2 启动流程
1. 设置环境变量 (AWS_REGION 等)
2. 启动 `mcp_server.py`（内部自动启动 aws-api-mcp-server 子进程和 Strands Agent）
3. 外部 Agent 通过 HTTP 连接 MCP Server

## 8. 配置驱动扩展设计（MCP + Skill）

### 8.1 核心理念
Agent 的所有能力（MCP Server 和 Skill）均通过 `agent_config.json` 配置。从 marketplace 下载新 MCP 或 Skill 后，只需添加一行配置、重启服务即可生效，**零代码修改**。

### 8.2 配置文件结构总览

```json
{
  "agent": { "model_id": "...", "region": "...", "system_prompt_file": null },
  "mcp_servers": [ ... ],
  "skills": [ ... ],
  "remote_mcp_server": { "name": "...", "host": "...", "port": 8080 }
}
```

### 8.3 添加新 MCP Server

在 `mcp_servers` 数组中添加一项：

```json
{
  "name": "filesystem",
  "enabled": true,
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
  "env": {},
  "startup_timeout": 30
}
```

支持的 MCP 类型：

| 类型 | 配置字段 | 说明 | 典型来源 |
|------|----------|------|----------|
| `stdio` | command, args, env | 本地子进程 | uvx/npx 安装的 MCP 包 |
| `sse` | url | 远程 SSE 连接 | 已部署的 MCP Server |

### 8.4 添加新 Skill

在 `skills` 数组中添加一项。支持三种 Skill 类型：

#### 方式一：内置 Skill（Strands Tools 库）

```json
{
  "name": "current_time",
  "enabled": true,
  "type": "builtin",
  "module": "strands_tools.current_time"
}
```

可用的内置 Skill 包括：`current_time`, `think`, `calculator`, `http_request`, `shell`, `file_read`, `file_write`, `python_repl`, `use_aws` 等 40+ 个。

#### 方式二：自定义 Skill（本地 Python 文件）

```json
{
  "name": "my_custom_skill",
  "enabled": true,
  "type": "custom",
  "path": "./skills/my_custom_skill.py"
}
```

自定义 Skill 文件模板（放入 `skills/` 目录）：

```python
from strands import tool

@tool
def my_custom_skill(param1: str, param2: int = 0) -> str:
    """Skill 描述 — Agent 根据此决定何时调用。

    Args:
        param1: 参数说明。
        param2: 参数说明。
    """
    return f"Result: {param1}, {param2}"
```

#### 方式三：第三方包 Skill（pip 安装）

```json
{
  "name": "some_tool",
  "enabled": true,
  "type": "package",
  "module": "some_package.tools.some_tool"
}
```

从 marketplace 下载后 `pip install xxx`，然后配置 module 路径即可。

### 8.5 扩展操作流程

```
1. 获取新能力（pip install / uvx / 编写 .py 文件 / 部署远程 MCP）
2. 编辑 agent_config.json，添加对应配置项
3. 重启服务：./scripts/start_server.sh
4. Agent 自动集成所有新工具，外部调用者无感知
```

### 8.6 其它可配置项
- **模型切换**：修改 `agent.model_id` 即可切换 Bedrock 模型
- **System Prompt**：设置 `agent.system_prompt_file` 指向自定义 prompt 文件
- **端口/Host**：修改 `remote_mcp_server.host/port`
- **启用/禁用**：任何 MCP 或 Skill 设置 `"enabled": false` 即可关闭

## 9. 测试方案

### 8.1 测试环境
- EC2 实例，已配置 IAM Role
- Python 3.12 + 所有依赖已安装

### 8.2 测试用例
1. **Agent 基础功能**：Agent 能否正确响应 AWS 相关问题
2. **AWS 操作**：Agent 能否通过 aws-api-mcp-server 执行真实 AWS 操作
3. **Remote MCP 连接**：外部客户端能否连接到 Remote MCP Server
4. **端到端调用**：Claude Code 作为外部 Agent 通过 MCP 调用并获取 AWS 操作结果
