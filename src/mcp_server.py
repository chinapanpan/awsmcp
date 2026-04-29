import logging
import sys
from mcp.server.fastmcp import FastMCP
from src.agent import AWSAgent
from src.config import load_agent_config, MCP_SERVER_HOST, MCP_SERVER_PORT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

config = load_agent_config()
server_cfg = config.get("remote_mcp_server", {})

mcp = FastMCP(
    server_cfg.get("name", "aws-agent-mcp-server"),
    host=server_cfg.get("host", MCP_SERVER_HOST),
    port=server_cfg.get("port", MCP_SERVER_PORT),
)

aws_agent = AWSAgent()


@mcp.tool()
def aws_agent_chat(message: str) -> str:
    """与 AWS 专家 Agent 进行自然语言对话。可以询问 AWS 相关问题、查询资源状态、执行云服务操作等。

    Args:
        message: 发送给 AWS Agent 的消息，支持自然语言描述的 AWS 操作请求。
                 例如："列出所有S3存储桶"、"查看us-east-1区域的EC2实例"、"描述Lambda函数列表"
    """
    return aws_agent.chat(message)


@mcp.tool()
def aws_agent_execute(task: str) -> str:
    """执行特定的 AWS 云服务操作任务。适用于明确的操作指令。

    Args:
        task: 需要执行的 AWS 操作任务描述。
              例如："列出所有S3存储桶及其大小"、"查看当前账号的IAM用户列表"
    """
    prompt = f"请执行以下AWS操作任务，直接返回结果：\n{task}"
    return aws_agent.chat(prompt)


def main():
    host = server_cfg.get("host", MCP_SERVER_HOST)
    port = server_cfg.get("port", MCP_SERVER_PORT)
    logger.info(f"Starting Remote MCP Server on {host}:{port}")
    try:
        aws_agent.start()
        logger.info("AWS Agent initialized, starting MCP server...")
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        aws_agent.stop()


if __name__ == "__main__":
    main()
