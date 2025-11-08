#!/bin/bash

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Starting VDS Explorer Stack${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to check if Docker is running
check_docker() {
    echo -e "\n${YELLOW}Checking Docker...${NC}"
    if ! docker info >/dev/null 2>&1; then
        echo -e "${YELLOW}Docker not running. Starting Docker Desktop...${NC}"
        open -a Docker

        # Wait for Docker to be ready (max 60 seconds)
        for i in {1..30}; do
            if docker info >/dev/null 2>&1; then
                echo -e "${GREEN}✓ Docker is ready!${NC}"
                return 0
            fi
            echo "Waiting for Docker... ($i/30)"
            sleep 2
        done

        echo -e "${RED}✗ Docker failed to start${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ Docker is already running${NC}"
    fi
}

# Function to start docker-compose services
start_docker_services() {
    echo -e "\n${YELLOW}Starting Docker services (Elasticsearch, Kibana)...${NC}"
    cd /Users/raghu/code/openvds-mcp-server
    docker-compose up -d

    # Wait for Elasticsearch to be healthy
    echo -e "${YELLOW}Waiting for Elasticsearch to be healthy...${NC}"
    for i in {1..30}; do
        if curl -s http://localhost:9200/_cluster/health >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Elasticsearch is ready!${NC}"
            break
        fi
        echo "Waiting for Elasticsearch... ($i/30)"
        sleep 2
    done

    # Check Kibana
    if docker ps | grep -q vds-shared-kibana; then
        echo -e "${GREEN}✓ Kibana is running on http://localhost:5601${NC}"
    fi
}

# Function to build OpenVDS MCP Docker image if needed
build_mcp_image() {
    echo -e "\n${YELLOW}Checking OpenVDS MCP Docker image...${NC}"
    if ! docker images | grep -q openvds-mcp-server; then
        echo -e "${YELLOW}Building OpenVDS MCP server image...${NC}"
        cd /Users/raghu/code/openvds-mcp-server
        docker-compose build openvds-mcp
        echo -e "${GREEN}✓ OpenVDS MCP image built${NC}"
    else
        echo -e "${GREEN}✓ OpenVDS MCP image exists${NC}"
    fi
}

# Function to start backend server
start_backend() {
    echo -e "\n${YELLOW}Starting Backend Server...${NC}"
    cd /Users/raghu/code/openvds-mcp-server/mcp-ui-client/backend

    # Check if venv exists
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi

    # Activate venv and install dependencies
    source venv/bin/activate

    # Check if dependencies are installed
    if ! pip list | grep -q fastapi; then
        echo -e "${YELLOW}Installing backend dependencies...${NC}"
        pip install -r requirements.txt
    fi

    # Kill any existing backend process
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true

    # Start backend in background
    echo -e "${YELLOW}Starting FastAPI server on port 8000...${NC}"
    nohup python -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0 > /tmp/backend.log 2>&1 &
    BACKEND_PID=$!

    # Wait a bit and check if it's running
    sleep 3
    if ps -p $BACKEND_PID > /dev/null; then
        echo -e "${GREEN}✓ Backend server started (PID: $BACKEND_PID)${NC}"
        echo -e "${GREEN}  API: http://localhost:5000${NC}"
        echo -e "${GREEN}  Logs: tail -f /tmp/backend.log${NC}"
    else
        echo -e "${RED}✗ Backend failed to start. Check logs: tail -f /tmp/backend.log${NC}"
        exit 1
    fi
}

# Function to start frontend server
start_frontend() {
    echo -e "\n${YELLOW}Starting Frontend Server...${NC}"
    cd /Users/raghu/code/openvds-mcp-server/mcp-ui-client/frontend

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing frontend dependencies...${NC}"
        npm install
    fi

    # Kill any existing frontend process
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true

    # Start frontend in background
    echo -e "${YELLOW}Starting Vite dev server on port 3000...${NC}"
    nohup npm run dev > /tmp/frontend.log 2>&1 &
    FRONTEND_PID=$!

    # Wait a bit and check if it's running
    sleep 5
    if ps -p $FRONTEND_PID > /dev/null; then
        echo -e "${GREEN}✓ Frontend server started (PID: $FRONTEND_PID)${NC}"
        echo -e "${GREEN}  UI: http://localhost:3000${NC}"
        echo -e "${GREEN}  Logs: tail -f /tmp/frontend.log${NC}"
    else
        echo -e "${RED}✗ Frontend failed to start. Check logs: tail -f /tmp/frontend.log${NC}"
        exit 1
    fi
}

# Function to show status
show_status() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}All Services Started!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "\n${YELLOW}Service Status:${NC}"
    echo -e "  ${GREEN}✓${NC} Elasticsearch: http://localhost:9200"
    echo -e "  ${GREEN}✓${NC} Kibana: http://localhost:5601"
    echo -e "  ${GREEN}✓${NC} Backend API: http://localhost:8000"
    echo -e "  ${GREEN}✓${NC} Frontend UI: http://localhost:3000"

    echo -e "\n${YELLOW}Logs:${NC}"
    echo -e "  Backend:  tail -f /tmp/backend.log"
    echo -e "  Frontend: tail -f /tmp/frontend.log"

    echo -e "\n${YELLOW}To stop all services:${NC}"
    echo -e "  ./stop-all.sh"

    echo -e "\n${GREEN}Opening browser...${NC}"
    sleep 2
    open http://localhost:3000
}

# Main execution
main() {
    check_docker
    start_docker_services
    build_mcp_image
    start_backend
    start_frontend
    show_status
}

# Run main function
main
