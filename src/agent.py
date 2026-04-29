import importlib
import logging
import os
import sys
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp import MCPClient
from strands.tools.decorator import DecoratedFunctionTool
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


def _load_skill(skill_cfg: dict):
    """Load a skill (Python tool) from config.

    Supports three types:
      - builtin:  module path in strands_tools, e.g. "strands_tools.current_time"
      - custom:   a local .py file path, e.g. "./skills/my_skill.py"
      - package:  an installed pip package module, e.g. "some_package.tools.my_tool"
    """
    skill_type = skill_cfg.get("type", "builtin")
    name = skill_cfg.get("name", "unknown")

    if skill_type == "builtin":
        module_path = skill_cfg["module"]
        logger.info(f"Loading builtin skill '{name}' from {module_path}")
        return module_path

    elif skill_type == "custom":
        file_path = skill_cfg["path"]
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Skill file not found: {file_path}")
        logger.info(f"Loading custom skill '{name}' from {file_path}")
        return file_path

    elif skill_type == "package":
        module_path = skill_cfg["module"]
        logger.info(f"Loading package skill '{name}' from {module_path}")
        return module_path

    else:
        raise ValueError(f"Unsupported skill type: {skill_type}")


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

        tools: list = []

        # --- Load MCP Servers ---
        for server_cfg in config.get("mcp_servers", []):
            if not server_cfg.get("enabled", True):
                logger.info(f"Skipping disabled MCP server: {server_cfg.get('name')}")
                continue
            client = _create_mcp_client(server_cfg)
            self._mcp_clients.append(client)
            tools.append(client)
            logger.info(f"MCP server '{server_cfg.get('name')}' queued")

        # --- Load Skills ---
        for skill_cfg in config.get("skills", []):
            if not skill_cfg.get("enabled", True):
                logger.info(f"Skipping disabled skill: {skill_cfg.get('name')}")
                continue
            try:
                skill_ref = _load_skill(skill_cfg)
                tools.append(skill_ref)
                logger.info(f"Skill '{skill_cfg.get('name')}' loaded")
            except Exception as e:
                logger.error(f"Failed to load skill '{skill_cfg.get('name')}': {e}")

        model = BedrockModel(model_id=model_id, region_name=region)
        self._agent = Agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
        )
        logger.info(
            f"AWS Agent ready with {len(self._mcp_clients)} MCP server(s) "
            f"and {len(tools) - len(self._mcp_clients)} skill(s)"
        )

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
