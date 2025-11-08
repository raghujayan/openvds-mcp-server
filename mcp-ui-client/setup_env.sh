#!/bin/bash

# VDS Explorer - Environment Setup Script
# Creates .env files and Python virtual environment

set -e

echo "🔧 VDS Explorer - Environment Setup"
echo "===================================="
echo ""

# Check if running in correct directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Error: Must run from mcp-ui-client directory"
    exit 1
fi

# Create Python virtual environment for backend
echo "📦 Setting up Python virtual environment..."
if [ -d "backend/venv" ]; then
    echo "⚠️  backend/venv already exists"
    read -p "Recreate virtual environment? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf backend/venv
        cd backend
        python3 -m venv venv
        cd ..
        echo "✓ Recreated backend/venv"
    else
        echo "Keeping existing backend/venv"
    fi
else
    cd backend
    python3 -m venv venv
    cd ..
    echo "✓ Created backend/venv"
fi

# Backend .env
if [ -f "backend/.env" ]; then
    echo "⚠️  backend/.env already exists"
    read -p "Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping backend/.env"
    else
        cp backend/.env.example backend/.env
        echo "✓ Created backend/.env"
    fi
else
    cp backend/.env.example backend/.env
    echo "✓ Created backend/.env"
fi

# Frontend .env
if [ -f "frontend/.env" ]; then
    echo "⚠️  frontend/.env already exists"
    read -p "Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping frontend/.env"
    else
        cp frontend/.env.example frontend/.env
        echo "✓ Created frontend/.env"
    fi
else
    cp frontend/.env.example frontend/.env
    echo "✓ Created frontend/.env"
fi

echo ""
echo "📝 Next Steps:"
echo "=============="
echo ""
echo "1. Add your Anthropic API key to backend/.env:"
echo "   ANTHROPIC_API_KEY=sk-ant-..."
echo ""
echo "2. Update MCP_SERVER_PATH if needed (current: /app/openvds-mcp-server/src/openvds_mcp_server.py)"
echo ""
echo "3. Activate virtual environment and install backend dependencies:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   pip install -r requirements.txt"
echo ""
echo "4. Install frontend dependencies:"
echo "   cd ../frontend"
echo "   npm install"
echo ""
echo "5. Start the backend (from backend directory with venv activated):"
echo "   source venv/bin/activate  # if not already activated"
echo "   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "6. Start the frontend (in a new terminal):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "For more information, see CHAT_APP_QUICKSTART.md"
