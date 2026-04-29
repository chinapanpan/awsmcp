#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

export AWS_REGION="${AWS_REGION:-us-east-1}"
export MCP_SERVER_HOST="${MCP_SERVER_HOST:-0.0.0.0}"
export MCP_SERVER_PORT="${MCP_SERVER_PORT:-8080}"

echo "Starting AWS Agent Remote MCP Server..."
echo "  Region: $AWS_REGION"
echo "  Host:   $MCP_SERVER_HOST"
echo "  Port:   $MCP_SERVER_PORT"

cd "$PROJECT_DIR"
python3.12 -m src.mcp_server
