#!/bin/bash
# Real-time monitoring during demos
# Run in separate terminal to watch system health

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

while true; do
    clear
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  OpenVDS MCP Demo Monitor"
    echo "  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # VPN Check
    echo "🌐 VPN Status:"
    if ping -c 1 -W 1 10.3.3.5 &>/dev/null; then
        echo -e "   ${GREEN}✅ Connected to 10.3.3.5${NC}"
    else
        echo -e "   ${RED}❌ VPN DISCONNECTED${NC}"
    fi
    echo ""

    # NFS Mount Health
    echo "💾 NFS Mount:"
    if ls /Volumes/Hue/Datasets/VDS &>/dev/null 2>&1; then
        START=$(python3 -c "import time; print(int(time.time() * 1000))")
        ls /Volumes/Hue/Datasets/VDS/Brazil &>/dev/null 2>&1
        END=$(python3 -c "import time; print(int(time.time() * 1000))")
        ELAPSED_MS=$(( END - START ))

        if [ $ELAPSED_MS -lt 500 ]; then
            echo -e "   ${GREEN}✅ HEALTHY${NC} (${ELAPSED_MS}ms)"
        elif [ $ELAPSED_MS -lt 1000 ]; then
            echo -e "   ${YELLOW}⚠️  SLOW${NC} (${ELAPSED_MS}ms)"
        else
            echo -e "   ${RED}⚠️  VERY SLOW${NC} (${ELAPSED_MS}ms)"
        fi
    else
        echo -e "   ${RED}❌ STALE OR INACCESSIBLE${NC}"
    fi
    echo ""

    # MCP Server Containers
    echo "🐳 MCP Server Containers:"
    CONTAINERS=$(docker ps --filter "ancestor=openvds-mcp-server" --format "{{.Names}}\t{{.Status}}" 2>/dev/null)
    if [ -n "$CONTAINERS" ]; then
        echo "$CONTAINERS" | while IFS=$'\t' read -r name status; do
            echo "   📦 $name: $status"
        done
    else
        echo "   No running containers (normal - starts on demand)"
    fi

    # Count total MCP containers (including stopped)
    TOTAL=$(docker ps -a --filter "ancestor=openvds-mcp-server" --format "{{.Names}}" 2>/dev/null | wc -l)
    if [ $TOTAL -gt 1 ]; then
        echo -e "   ${YELLOW}⚠️  Warning: $TOTAL total containers (should cleanup)${NC}"
    fi
    echo ""

    # Elasticsearch
    echo "🔍 Elasticsearch:"
    if curl -sf http://localhost:9200/_cluster/health &>/dev/null; then
        ES_STATUS=$(curl -s http://localhost:9200/_cluster/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        ES_COUNT=$(curl -s http://localhost:9200/vds-metadata/_count | grep -o '"count":[0-9]*' | cut -d':' -f2)

        if [ "$ES_STATUS" = "green" ]; then
            echo -e "   ${GREEN}✅ Status: $ES_STATUS${NC}"
        elif [ "$ES_STATUS" = "yellow" ]; then
            echo -e "   ${YELLOW}⚠️  Status: $ES_STATUS${NC}"
        else
            echo -e "   ${RED}❌ Status: $ES_STATUS${NC}"
        fi
        echo "   📊 $ES_COUNT VDS datasets indexed"
    else
        echo -e "   ${RED}❌ Not accessible${NC}"
    fi
    echo ""

    # Docker Resources (if containers running)
    if docker ps --filter "ancestor=openvds-mcp-server" -q &>/dev/null | grep -q .; then
        echo "📊 Resource Usage:"
        docker stats --no-stream --format "   {{.Name}}: CPU {{.CPUPerc}} | RAM {{.MemUsage}}" \
            $(docker ps --filter "ancestor=openvds-mcp-server" -q) 2>/dev/null || echo "   (none running)"
        echo ""
    fi

    # Recent MCP logs (last 3 lines)
    if docker ps --filter "ancestor=openvds-mcp-server" -q &>/dev/null | grep -q .; then
        echo "📝 Recent MCP Logs:"
        LATEST_CONTAINER=$(docker ps --filter "ancestor=openvds-mcp-server" --format "{{.Names}}" | head -1)
        if [ -n "$LATEST_CONTAINER" ]; then
            docker logs --tail 3 "$LATEST_CONTAINER" 2>&1 | sed 's/^/   /'
        fi
        echo ""
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Press Ctrl+C to exit | Refreshing every 3 seconds..."

    sleep 3
done
