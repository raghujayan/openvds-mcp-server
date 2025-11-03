#!/bin/bash
# Quick container status check

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🐳 MCP Server Container Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Count containers
RUNNING=$(docker ps -q --filter "ancestor=openvds-mcp-server" | wc -l | tr -d ' ')
EXITED=$(docker ps -aq --filter "ancestor=openvds-mcp-server" --filter "status=exited" | wc -l | tr -d ' ')
TOTAL=$(docker ps -aq --filter "ancestor=openvds-mcp-server" | wc -l | tr -d ' ')

echo ""
echo "📊 Container Counts:"
echo "   Running: $RUNNING"
echo "   Exited:  $EXITED"
echo "   Total:   $TOTAL"
echo ""

if [ $RUNNING -gt 0 ]; then
    echo "🟢 Running Containers:"
    docker ps --filter "ancestor=openvds-mcp-server" \
      --format "   {{.Names}} ({{.Status}}) - Created {{.CreatedAt}}"
    echo ""
fi

if [ $EXITED -gt 0 ]; then
    echo -e "${YELLOW}🟡 Exited Containers (orphaned):${NC}"
    docker ps -a --filter "ancestor=openvds-mcp-server" --filter "status=exited" \
      --format "   {{.Names}} ({{.Status}}) - Created {{.CreatedAt}}"
    echo ""
    echo "   💡 Cleanup command: docker rm \$(docker ps -aq --filter \"ancestor=openvds-mcp-server\" --filter \"status=exited\")"
    echo ""
fi

if [ $TOTAL -eq 0 ]; then
    echo -e "${GREEN}✅ No MCP containers found (clean state)${NC}"
    echo ""
fi

# Status summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $RUNNING -eq 0 ] && [ $EXITED -eq 0 ]; then
    echo -e "${GREEN}✅ System is clean - no containers${NC}"
elif [ $RUNNING -le 3 ] && [ $EXITED -eq 0 ]; then
    echo -e "${GREEN}✅ Normal - containers running for active sessions${NC}"
elif [ $EXITED -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Some orphaned containers - cleanup recommended${NC}"
elif [ $RUNNING -gt 10 ]; then
    echo -e "${RED}❌ Too many containers - possible leak${NC}"
fi

echo ""
echo "💡 Tip: Close all Claude Desktop chat sessions to auto-cleanup containers"
