#!/bin/bash

set -e

echo "============================================================"
echo "OpenVDS MCP Server - Docker Setup"
echo "============================================================"

if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    echo "Please install Docker Desktop for Mac from https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "Error: Docker daemon is not running"
    echo "Please start Docker Desktop"
    exit 1
fi

echo "Building Docker image..."
docker-compose build

echo ""
echo "Docker image built successfully!"
echo ""
echo "============================================================"
echo "Next Steps:"
echo "============================================================"
echo ""
echo "1. To run the MCP server interactively:"
echo "   docker-compose run --rm openvds-mcp"
echo ""
echo "2. To use with Claude Desktop, add this to your config:"
echo "   ~/Library/Application Support/Claude/claude_desktop_config.json"
echo ""
echo '   {'
echo '     "mcpServers": {'
echo '       "openvds": {'
echo '         "command": "docker",'
echo '         "args": ["run", "--rm", "-i",'
echo '                  "-v", "/Volumes/Hue NFS mount/datasets:/data:ro",'
echo '                  "openvds-mcp-server",'
echo '                  "python", "src/openvds_mcp_server.py"]'
echo '       }'
echo '     }'
echo '   }'
echo ""
echo "3. Restart Claude Desktop to connect to the server"
echo ""
echo "============================================================"
