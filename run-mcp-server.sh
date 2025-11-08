#!/bin/bash
set -e

# Change to the script's directory
cd "$(dirname "$0")"

# Wait for Docker to be ready (max 30 seconds)
for i in {1..30}; do
    if docker info >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# Run the MCP server with stdio for MCP protocol
# Use --no-deps to avoid starting other services (like Elasticsearch)
exec docker-compose run --rm --no-TTY --no-deps openvds-mcp python3 src/openvds_mcp_server.py
