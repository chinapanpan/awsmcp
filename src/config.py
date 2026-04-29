import os
import json

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
MCP_SERVER_HOST = os.environ.get("MCP_SERVER_HOST", "0.0.0.0")
MCP_SERVER_PORT = int(os.environ.get("MCP_SERVER_PORT", "8080"))

CONFIG_PATH = os.environ.get(
    "AGENT_CONFIG_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "agent_config.json"),
)

SYSTEM_PROMPT = """你是一个 AWS 云服务专家 Agent。你可以通过 AWS CLI 工具帮助用户管理和操作 AWS 云服务。

你的能力包括：
- 查询和管理 AWS 资源（S3, EC2, Lambda, DynamoDB, IAM 等）
- 执行 AWS CLI 命令
- 解释 AWS 服务的状态和配置
- 提供 AWS 最佳实践建议

请用中文回答，结果要简洁清晰。当需要执行 AWS 操作时，使用可用的工具。"""


def load_agent_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"mcp_servers": [], "tools": []}
