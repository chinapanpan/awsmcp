# AWS Agent Remote MCP Server

基于 Strands Agents SDK 开发的 AWS 云服务 AI Agent，集成 aws-api-mcp-server 和 AgentSkills.io Skill 系统，封装为 Remote MCP Server 供外部 Agent 调用。

## 架构

```
外部 Agent (Claude Code 等)
    ↓ MCP (streamable-http, port 8080)
Remote MCP Server (FastMCP)
    ↓
Strands Agent (Claude Sonnet 4.6 via Bedrock)
    ├── MCP Servers (aws-api 等, 配置驱动)
    └── Skills (SKILL.md, 渐进式加载)
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

### 添加 Skill (AgentSkills.io SKILL.md)

1. 创建 `skills/my-skill/SKILL.md`：

```markdown
---
name: my-skill
description: 描述 Agent 何时应激活此 Skill
---

# Skill 指令
按以下步骤操作...
```

2. 在 `agent_config.json` 中添加：

```json
{ "source": "./skills/my-skill", "enabled": true }
```

3. 重启服务，Agent 自动发现并按需激活 Skill。

也支持从 URL 加载：`{ "source": "https://...SKILL.md", "enabled": true }`

## 内置 Skills

| Skill | 说明 |
|-------|------|
| `aws-cost-advisor` | 分析 AWS 费用趋势，提供优化建议 |
| `aws-security-check` | AWS 安全态势评估，检查 IAM/网络/数据保护 |

## 文档

- [技术方案设计](docs/design.md)
- [测试验证报告](docs/test_report.md)
