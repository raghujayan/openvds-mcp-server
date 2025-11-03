#!/bin/bash
# Demo Preparation Script - Run before live demos
# Ensures VPN, NFS mount, and MCP infrastructure are healthy

set -e

echo "🎯 Preparing OpenVDS MCP Demo Environment..."
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track if any checks fail
FAILED=0

# 1. Check VPN Connection
echo "1️⃣  Checking VPN connection to NFS server..."
if ping -c 1 -W 2 10.3.3.5 &>/dev/null; then
    echo -e "${GREEN}✅ VPN connected to 10.3.3.5${NC}"
else
    echo -e "${RED}❌ VPN not connected to 10.3.3.5${NC}"
    echo "   Action: Connect to VPN before demo"
    FAILED=1
fi
echo ""

# 2. Check NFS Mount Accessibility
echo "2️⃣  Checking NFS mount accessibility..."
if ls /Volumes/Hue/Datasets/VDS &>/dev/null; then
    # Measure mount speed (macOS compatible)
    START=$(python3 -c "import time; print(int(time.time() * 1000))")
    ls /Volumes/Hue/Datasets/VDS/Brazil &>/dev/null
    END=$(python3 -c "import time; print(int(time.time() * 1000))")
    ELAPSED_MS=$(( END - START ))

    if [ $ELAPSED_MS -lt 1000 ]; then
        echo -e "${GREEN}✅ NFS mount is HEALTHY (${ELAPSED_MS}ms)${NC}"
    else
        echo -e "${YELLOW}⚠️  NFS mount is SLOW (${ELAPSED_MS}ms) - possible network issues${NC}"
    fi
else
    echo -e "${RED}❌ NFS mount not accessible or stale${NC}"
    echo "   Path: /Volumes/Hue/Datasets/VDS"
    echo "   Action: Check VPN and remount if needed"
    FAILED=1
fi
echo ""

# 3. Check Docker is running
echo "3️⃣  Checking Docker daemon..."
if docker info &>/dev/null; then
    echo -e "${GREEN}✅ Docker is running${NC}"
else
    echo -e "${RED}❌ Docker is not running${NC}"
    echo "   Action: Start Docker Desktop"
    FAILED=1
fi
echo ""

# 4. Check Elasticsearch health
echo "4️⃣  Checking Elasticsearch..."
if curl -sf http://localhost:9200/_cluster/health &>/dev/null; then
    ES_STATUS=$(curl -s http://localhost:9200/_cluster/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    ES_COUNT=$(curl -s http://localhost:9200/vds-metadata/_count | grep -o '"count":[0-9]*' | cut -d':' -f2)

    if [ "$ES_STATUS" = "green" ] || [ "$ES_STATUS" = "yellow" ]; then
        echo -e "${GREEN}✅ Elasticsearch is ${ES_STATUS}${NC}"
        echo "   📊 ${ES_COUNT} VDS datasets indexed"
    else
        echo -e "${YELLOW}⚠️  Elasticsearch status: ${ES_STATUS}${NC}"
    fi
else
    echo -e "${RED}❌ Elasticsearch not accessible${NC}"
    echo "   Action: Start Elasticsearch container"
    echo "   Run: docker start vds-shared-elasticsearch"
    FAILED=1
fi
echo ""

# 5. Clean up old MCP containers
echo "5️⃣  Cleaning up old MCP server containers..."
OLD_CONTAINERS=$(docker ps -aq --filter "ancestor=openvds-mcp-server" 2>/dev/null || echo "")
if [ -n "$OLD_CONTAINERS" ]; then
    echo "   Found old containers, cleaning up..."
    docker stop $OLD_CONTAINERS 2>/dev/null || true
    docker rm $OLD_CONTAINERS 2>/dev/null || true
    echo -e "${GREEN}✅ Cleaned up old containers${NC}"
else
    echo -e "${GREEN}✅ No old containers to clean${NC}"
fi
echo ""

# 6. Check MCP server image exists
echo "6️⃣  Checking MCP server image..."
if docker images | grep -q openvds-mcp-server; then
    IMAGE_DATE=$(docker inspect openvds-mcp-server:latest | grep -o '"Created":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo -e "${GREEN}✅ MCP server image exists${NC}"
    echo "   Built: $IMAGE_DATE"
else
    echo -e "${YELLOW}⚠️  MCP server image not found${NC}"
    echo "   Action: Build image with: docker-compose build"
fi
echo ""

# 7. Test MCP server startup (if all checks passed)
if [ $FAILED -eq 0 ]; then
    echo "7️⃣  Testing MCP server startup..."

    # Start in background and capture logs
    docker-compose up -d 2>&1
    sleep 3

    if docker logs openvds-mcp-server 2>&1 | grep -q "VDS Client initialized"; then
        SURVEY_COUNT=$(docker logs openvds-mcp-server 2>&1 | grep "Surveys available:" | tail -1 | grep -o '[0-9]*' | tail -1)
        echo -e "${GREEN}✅ MCP server started successfully${NC}"
        echo "   📊 ${SURVEY_COUNT} surveys loaded"

        # Stop it (Claude Desktop will start when needed)
        docker-compose down >/dev/null 2>&1
    else
        echo -e "${RED}❌ MCP server failed to initialize${NC}"
        echo "   Check logs: docker logs openvds-mcp-server"
        FAILED=1
    fi
else
    echo "7️⃣  Skipping MCP server test due to previous failures"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ DEMO ENVIRONMENT READY!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Keep this terminal open during demo"
    echo "  2. If VPN disconnects, metadata queries still work"
    echo "  3. Monitor with: docker logs -f openvds-mcp-server"
    echo ""
    echo "Emergency fallback:"
    echo "  If data extraction fails, use: search_surveys, get_facets"
    echo "  (Elasticsearch works independently of VDS files)"
else
    echo -e "${RED}❌ DEMO ENVIRONMENT NOT READY${NC}"
    echo ""
    echo "Fix the issues above before starting demo"
    exit 1
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
