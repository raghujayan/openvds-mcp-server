#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Stopping VDS Explorer Stack${NC}"
echo -e "${YELLOW}========================================${NC}"

# Stop frontend (port 3000)
echo -e "\n${YELLOW}Stopping frontend server...${NC}"
if lsof -ti:3000 >/dev/null 2>&1; then
    lsof -ti:3000 | xargs kill -9
    echo -e "${GREEN}✓ Frontend stopped${NC}"
else
    echo -e "${YELLOW}Frontend not running${NC}"
fi

# Stop backend (port 8000)
echo -e "\n${YELLOW}Stopping backend server...${NC}"
if lsof -ti:8000 >/dev/null 2>&1; then
    lsof -ti:8000 | xargs kill -9
    echo -e "${GREEN}✓ Backend stopped${NC}"
else
    echo -e "${YELLOW}Backend not running${NC}"
fi

# Stop Docker containers
echo -e "\n${YELLOW}Stopping Docker services...${NC}"
cd /Users/raghu/code/openvds-mcp-server
docker-compose down
echo -e "${GREEN}✓ Docker services stopped${NC}"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}All services stopped!${NC}"
echo -e "${GREEN}========================================${NC}"
