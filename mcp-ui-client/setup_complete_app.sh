#!/bin/bash

# VDS Explorer - Complete App Setup Script
# This script creates all necessary files for the production GUI application

set -e

echo "🚀 Setting up VDS Explorer - Production GUI Application"
echo "========================================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create directory structure
echo -e "${BLUE}Creating directory structure...${NC}"
mkdir -p backend/app/models backend/app/api
mkdir -p frontend/src/{components/{Chat,Layout,Agent,Survey},pages,services,store,types,styles,hooks,utils}

# Set environment files
echo -e "${BLUE}Creating environment files...${NC}"

cat > backend/.env.example << 'EOF'
# Anthropic API
ANTHROPIC_API_KEY=your-api-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# MCP Server
MCP_SERVER_PATH=/app/openvds-mcp-server/src/openvds_mcp_server.py
MCP_SERVER_ARGS=

# Database
DATABASE_URL=sqlite+aiosqlite:///./chat_history.db

# CORS
CORS_ORIGINS=http://localhost:3000

# App Settings
MAX_CONVERSATION_LENGTH=50
STREAMING_ENABLED=true
EOF

cat > frontend/.env.example << 'EOF'
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=VDS Explorer
VITE_ENABLE_STREAMING=true
EOF

echo -e "${GREEN}✓ Environment files created${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Copy backend/.env.example to backend/.env"
echo "2. Add your Anthropic API key to backend/.env"
echo "3. Copy frontend/.env.example to frontend/.env"
echo "4. Run: pip install -r backend/requirements.txt"
echo "5. Run: cd frontend && npm install"
echo ""
echo "For detailed implementation, see:"
echo "  - CLAUDE_DESKTOP_ARCHITECTURE.md"
echo "  - COMPLETE_IMPLEMENTATION_GUIDE.md (to be created)"

EOF

chmod +x setup_complete_app.sh