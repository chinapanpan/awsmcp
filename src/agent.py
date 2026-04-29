import logging
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from src.config import load_agent_config, SYSTEM_PROMPT, AWS_REGION, BEDROCK_MODEL_ID

logger = logging.getLogger(__name__)


def _create_mcp_client(server_cfg: dict) -> MCPClient:
    server_type = server_cfg.get("type", "stdio")
    name = server_cfg.get("name", "unknown")
    timeout = server_cfg.get("startup_timeout", 120)

    if server_type == "stdio":
        command = server_cfg["command"]
        args = server_cfg.get("args", [])
        env = server_cfg.get("env", {})
        client = MCPClient(
            transport_callable=lambda cmd=command, a=args, e=env: stdio_client(
                StdioServerParameters(command=cmd, args=a, env=e)
            ),
            startup_timeout=timeout,
        )
    elif server_type == "sse":
        url = server_cfg["url"]
        client = MCPClient(
            transport_callable=lambda u=url: sse_client(url=u),
            startup_timeout=timeout,
        )
    else:
        raise ValueError(f"Unsupported MCP server type: {server_type}")

    logger.info(f"Created MCP client for '{name}' ({server_type})")
    return client


class AWSAgent:
    def __init__(self):
        self._mcp_clients: list[MCPClient] = []
        self._agent = None

    def start(self):
        logger.info("Starting AWS Agent...")
        config = load_agent_config()

        agent_cfg = config.get("agent", {})
        model_id = agent_cfg.get("model_id", BEDROCK_MODEL_ID)
        region = agent_cfg.get("region", AWS_REGION)
        system_prompt = SYSTEM_PROMPT

        prompt_file = agent_cfg.get("system_prompt_file")
        if prompt_file:
            with open(prompt_file) as f:
                system_prompt = f.read()

        for server_cfg in config.get("mcp_servers", []):
            if not server_cfg.get("enabled", True):
                logger.info(f"Skipping disabled MCP server: {server_cfg.get('name')}")
                continue
            client = _create_mcp_client(server_cfg)
            self._mcp_clients.append(client)
            logger.info(f"MCP client '{server_cfg.get('name')}' created")

        model = BedrockModel(model_id=model_id, region_name=region)
        self._agent = Agent(
            model=model,
            tools=list(self._mcp_clients),
            system_prompt=system_prompt,
        )
        logger.info(f"AWS Agent ready with {len(self._mcp_clients)} MCP server(s)")

    def stop(self):
        for client in self._mcp_clients:
            try:
                client.stop(None, None, None)
            except Exception as e:
                logger.warning(f"Error stopping MCP client: {e}")
        self._mcp_clients.clear()
        logger.info("AWS Agent stopped")

    def chat(self, message: str) -> str:
        if not self._agent:
            raise RuntimeError("Agent not started. Call start() first.")
        logger.info(f"Agent received: {message[:100]}")
        result = self._agent(message)
        return str(result)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
