# AWS Agent Remote MCP Server

基于 Strands Agents SDK 开发的 AWS 云服务 AI Agent，集成 aws-api-mcp-server，并封装为 Remote MCP Server 供外部 Agent 调用。

## 架构

```
外部 Agent (Claude Code 等)
    ↓ MCP (streamable-http, port 8080)
Remote MCP Server (FastMCP)
    ↓
Strands Agent (Claude Sonnet 4.6 via Bedrock)
    ↓ MCP (stdio)
aws-api-mcp-server
    ↓
AWS Cloud Services
```

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
./scripts/start_server.sh

# 3. 测试
python3.12 scripts/test_client.py
```

## 配置驱动扩展

编辑 `agent_config.json` 即可添加新的 MCP Server，无需修改代码：

```json
{
  "mcp_servers": [
    {
      "name": "new-mcp-server",
      "enabled": true,
      "type": "stdio",
      "command": "uvx",
      "args": ["some-mcp-server@latest"],
      "env": {},
      "startup_timeout": 60
    }
  ]
}
```

重启服务后，Agent 自动集成新工具。

## 暴露的 MCP 工具

| 工具 | 说明 |
|------|------|
| `aws_agent_chat` | 与 AWS 专家 Agent 自然语言对话 |
| `aws_agent_execute` | 执行特定 AWS 操作任务 |

## 文档

- [技术方案设计](docs/design.md)
- [测试验证报告](docs/test_report.md)
