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
┌─────────────────────────────────────────────────────────┐
│                    外部 Agent (Claude Code)               │
│                         │                                │
│              MCP Client (streamable-http)                │
└─────────────┬───────────────────────────────────────────┘
              │ HTTP (port 8080)
              ▼
┌─────────────────────────────────────────────────────────┐
│              Remote MCP Server Layer                      │
│         (FastMCP, streamable-http transport)              │
│                                                          │
│  Exposed Tools:                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ aws_agent_chat: 与 AWS Agent 自然语言对话         │    │
│  │ aws_agent_execute: 执行特定 AWS 操作             │    │
│  └─────────────────────────────────────────────────┘    │
│                         │                                │
│                         ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │           Strands Agent Core                     │    │
│  │  - Model: Bedrock (Claude Sonnet)                │    │
│  │  - System Prompt: AWS 专家                       │    │
│  │  - Tools: MCPClient → aws-api-mcp-server         │    │
│  └─────────────────────────────────────────────────┘    │
│                         │                                │
│              MCPClient (stdio transport)                  │
│                         │                                │
│                         ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │         aws-api-mcp-server (subprocess)          │    │
│  │  - call_aws: 执行 AWS CLI 命令                   │    │
│  │  - suggest_aws_commands: 建议 AWS 命令           │    │
│  └─────────────────────────────────────────────────┘    │
│                         │                                │
│                    IAM Role                               │
│                         │                                │
│                         ▼                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │              AWS Cloud Services                   │    │
│  │  (S3, EC2, Lambda, DynamoDB, etc.)               │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
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
│   ├── agent.py            # Strands Agent 核心逻辑（配置驱动）
│   ├── mcp_server.py       # Remote MCP Server 封装
│   └── config.py           # 配置管理
├── scripts/
│   ├── start_server.sh     # 启动脚本
│   └── test_client.py      # 测试客户端
├── agent_config.json       # ★ 核心配置文件（添加 MCP/Skill 只需改此文件）
├── requirements.txt
└── README.md
```

### 4.2 核心模块

#### 4.2.1 config.py - 配置管理
- AWS Region 配置
- Bedrock 模型 ID 配置
- MCP Server 端口配置
- aws-api-mcp-server 启动参数

#### 4.2.2 agent.py - Agent 核心
- 初始化 BedrockModel (Claude Sonnet via Bedrock)
- 初始化 MCPClient 连接 aws-api-mcp-server (stdio 传输)
- 创建 Strands Agent，绑定模型和工具
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

## 8. 配置驱动扩展设计

### 8.1 核心理念
所有 MCP Server 和 Agent 参数均通过 `agent_config.json` 配置，新增能力无需修改代码。

### 8.2 添加新 MCP Server（Skill）
只需在 `agent_config.json` 的 `mcp_servers` 数组中添加一项：

```json
{
  "mcp_servers": [
    {
      "name": "aws-api",
      "enabled": true,
      "type": "stdio",
      "command": "uvx",
      "args": ["awslabs.aws-api-mcp-server@latest"],
      "env": {"AWS_REGION": "us-east-1"},
      "startup_timeout": 120
    },
    {
      "name": "filesystem",
      "enabled": true,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "env": {},
      "startup_timeout": 30
    },
    {
      "name": "remote-db-tool",
      "enabled": false,
      "type": "sse",
      "url": "http://db-mcp-server:9090/sse",
      "startup_timeout": 30
    }
  ]
}
```

### 8.3 支持的 MCP Server 类型

| 类型 | 配置字段 | 说明 |
|------|----------|------|
| `stdio` | command, args, env | 本地子进程模式，适合 uvx/npx 等包管理器 |
| `sse` | url | 远程 SSE 连接，适合已部署的 MCP Server |

### 8.4 扩展流程（零代码）
1. 编辑 `agent_config.json`，添加新 MCP Server 配置
2. 重启服务
3. Agent 自动发现并集成新 MCP Server 的所有工具
4. 外部调用者通过同一个 `aws_agent_chat` 工具即可使用新能力

### 8.5 其它可配置项
- **模型切换**：修改 `agent.model_id` 即可切换 Bedrock 模型
- **System Prompt**：设置 `agent.system_prompt_file` 指向自定义 prompt 文件
- **端口/Host**：修改 `remote_mcp_server.host/port`

## 9. 测试方案

### 8.1 测试环境
- EC2 实例，已配置 IAM Role
- Python 3.12 + 所有依赖已安装

### 8.2 测试用例
1. **Agent 基础功能**：Agent 能否正确响应 AWS 相关问题
2. **AWS 操作**：Agent 能否通过 aws-api-mcp-server 执行真实 AWS 操作
3. **Remote MCP 连接**：外部客户端能否连接到 Remote MCP Server
4. **端到端调用**：Claude Code 作为外部 Agent 通过 MCP 调用并获取 AWS 操作结果
