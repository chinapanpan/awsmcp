# AWS Agent Remote MCP Server

基于 Strands Agents SDK 开发的 AWS 云服务 AI Agent，集成 aws-api-mcp-server 和可扩展 Skill 系统，封装为 Remote MCP Server 供外部 Agent 调用。

## 架构

```
外部 Agent (Claude Code 等)
    ↓ MCP (streamable-http, port 8080)
Remote MCP Server (FastMCP)
    ↓
Strands Agent (Claude Sonnet 4.6 via Bedrock)
    ↓                    ↓
MCP Servers           Skills
(aws-api 等)     (builtin/custom/package)
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

所有能力通过 `agent_config.json` 配置，无需修改代码。

### 添加 MCP Server

```json
{
  "name": "filesystem",
  "enabled": true,
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
}
```

### 添加 Skill

三种方式：

```json
// 内置 Skill (strands_tools 库)
{ "name": "calculator", "enabled": true, "type": "builtin", "module": "strands_tools.calculator" }

// 自定义 Skill (本地 Python 文件)
{ "name": "my_skill", "enabled": true, "type": "custom", "path": "./skills/my_skill.py" }

// 第三方包 Skill (pip install 后配置)
{ "name": "some_tool", "enabled": true, "type": "package", "module": "some_package.some_tool" }
```

重启服务后，Agent 自动集成所有新能力。

## 暴露的 MCP 工具

| 工具 | 说明 |
|------|------|
| `aws_agent_chat` | 与 AWS 专家 Agent 自然语言对话 |
| `aws_agent_execute` | 执行特定 AWS 操作任务 |

## 文档

- [技术方案设计](docs/design.md)
- [测试验证报告](docs/test_report.md)
