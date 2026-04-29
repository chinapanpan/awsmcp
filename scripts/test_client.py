"""Test client to verify the Remote MCP Server is working."""
import asyncio
import sys
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession


async def main():
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/mcp/"
    print(f"Connecting to MCP Server at {server_url}...")

    async with streamablehttp_client(server_url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("Connected and initialized!\n")

            tools = await session.list_tools()
            print(f"Available tools ({len(tools.tools)}):")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description[:80]}")
            print()

            if len(sys.argv) > 2:
                message = " ".join(sys.argv[2:])
            else:
                message = "列出当前AWS账号下的S3存储桶"

            print(f"Calling aws_agent_chat with: {message}")
            print("-" * 60)
            result = await session.call_tool("aws_agent_chat", {"message": message})
            for content in result.content:
                print(content.text if hasattr(content, "text") else content)
            print("-" * 60)
            print("Test completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
