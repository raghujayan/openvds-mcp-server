# Virtual Environment Setup for VDS Explorer

This project uses Python virtual environments (venv) to isolate dependencies.

---

## Quick Setup

The setup script automatically creates a virtual environment for you:

```bash
./setup_env.sh
```

This creates `backend/venv/` with all necessary Python packages isolated from your system Python.

---

## Manual Setup (if needed)

If you need to manually create or recreate the virtual environment:

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Using the Virtual Environment

### Activating

Every time you start a new terminal session to work on the backend, activate the venv:

```bash
cd backend
source venv/bin/activate
```

You'll see `(venv)` prefix in your terminal prompt when activated:
```
(venv) user@machine:~/mcp-ui-client/backend$
```

### Running Commands

With venv activated, all pip installs and Python commands use the isolated environment:

```bash
# Install new package (adds to venv only)
pip install some-package

# Run backend
uvicorn app.main:app --reload

# Run tests
pytest

# Type checking
mypy app/
```

### Deactivating

To exit the virtual environment:

```bash
deactivate
```

---

## Why Use Virtual Environments?

1. **Dependency Isolation** - Project dependencies don't affect system Python
2. **Version Control** - Each project can use different package versions
3. **Clean Installation** - Easy to delete and recreate
4. **Reproducibility** - requirements.txt guarantees same versions
5. **No sudo Required** - Install packages without admin privileges

---

## Common Workflows

### Starting Backend Development

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### Installing New Packages

```bash
cd backend
source venv/bin/activate
pip install new-package
pip freeze > requirements.txt  # Update requirements
```

### Updating Dependencies

```bash
cd backend
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### Recreating Virtual Environment

```bash
cd backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Troubleshooting

### Problem: "python3: command not found"

Install Python 3.10 or newer:
```bash
# macOS
brew install python@3.10

# Ubuntu/Debian
sudo apt install python3.10 python3.10-venv

# Check version
python3 --version
```

### Problem: "venv activation not working"

Make sure you're sourcing the correct activation script:
```bash
# macOS/Linux
source venv/bin/activate

# Windows (Git Bash)
source venv/Scripts/activate

# Windows (CMD)
venv\Scripts\activate.bat

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

### Problem: "Module not found" even with venv activated

1. Check venv is actually activated (see `(venv)` in prompt)
2. Verify you're in the backend directory
3. Reinstall dependencies:
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

### Problem: "Permission denied" when creating venv

Check you have write permissions in the backend directory:
```bash
ls -la backend/
# Should show you as owner

# If not, fix permissions
chmod 755 backend/
```

---

## IDE Configuration

### VS Code

VS Code should automatically detect the venv. If not:

1. Open Command Palette (Cmd/Ctrl + Shift + P)
2. Type "Python: Select Interpreter"
3. Choose `./backend/venv/bin/python`

Or add to `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/venv/bin/python"
}
```

### PyCharm

1. Go to Settings → Project → Python Interpreter
2. Click gear icon → Add
3. Select "Existing environment"
4. Choose `backend/venv/bin/python`

---

## What's Installed

The virtual environment includes:

**Core Framework:**
- fastapi - Web framework
- uvicorn - ASGI server
- pydantic - Data validation

**Claude Integration:**
- anthropic - Claude API client

**MCP:**
- mcp - Model Context Protocol SDK

**Database:**
- sqlalchemy - ORM
- aiosqlite - Async SQLite

**Utilities:**
- python-multipart - File uploads
- python-dotenv - Environment variables
- sse-starlette - Server-sent events
- httpx - HTTP client

**MCP Server Dependencies:**
- numpy - Numerical computing
- matplotlib - Plotting
- elasticsearch - Search integration
- Pillow - Image processing

See `backend/requirements.txt` for full list with versions.

---

## Best Practices

1. **Always activate venv** before running backend commands
2. **Update requirements.txt** when adding new packages
3. **Don't commit venv/** to git (already in .gitignore)
4. **Use same Python version** across team (3.10+)
5. **Recreate venv** if requirements.txt changes significantly

---

## Quick Reference

```bash
# Create venv
python3 -m venv backend/venv

# Activate venv
source backend/venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run backend
uvicorn app.main:app --reload

# Deactivate venv
deactivate

# Remove venv
rm -rf backend/venv
```

---

For more information, see:
- **Setup:** CHAT_APP_QUICKSTART.md
- **Development:** README_CHAT_APP.md
- **Python venv docs:** https://docs.python.org/3/library/venv.html
