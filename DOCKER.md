# Docker Deployment Guide

This guide explains how to run the OpenVDS MCP Server in a Docker container on macOS. This is necessary because OpenVDS Python wheels are not available for macOS - Docker provides a Linux environment where the wheels work correctly.

## Prerequisites

1. **Docker Desktop for Mac** - [Download here](https://www.docker.com/products/docker-desktop)
2. **VDS files accessible on your Mac** - Your VDS data at `/Volumes/Hue/Datasets/VDS/`
3. **Claude Desktop** - [Download here](https://claude.ai/download)

## Quick Start

### 1. Build the Docker Image

Run the setup script:

```bash
./run-docker.sh
```

This will:
- Check that Docker is installed and running
- Build the Docker image with all dependencies
- Show you the next steps

### 2. Test the Server (Optional)

You can test that the server initializes correctly:

```bash
docker run --rm -i \
  -v "/Volumes/Hue/Datasets/VDS:/vds-data:ro" \
  -e VDS_DATA_PATH=/vds-data \
  openvds-mcp-server \
  python test_server.py
```

**Expected output**:
- `demo_mode=False` if VDS files are found
- List of your actual VDS surveys
- Or `demo_mode=True` if no VDS files detected (check the path)

### 3. Configure Claude Desktop

Edit your Claude Desktop configuration file:

**Location**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Add this configuration**:

```json
{
  "mcpServers": {
    "openvds": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--platform",
        "linux/amd64",
        "-v",
        "/Volumes/Hue/Datasets/VDS:/vds-data:ro",
        "-e",
        "VDS_DATA_PATH=/vds-data",
        "openvds-mcp-server",
        "python",
        "src/openvds_mcp_server.py"
      ]
    }
  }
}
```

**Important**: If you have other MCP servers configured, add the `openvds` entry to the existing `mcpServers` object.

### 4. Restart Claude Desktop

1. Quit Claude Desktop completely
2. Start it again
3. Look for the 🔌 icon - you should see "openvds" connected
4. You can now ask Claude questions about your seismic data!

## How It Works

1. **Docker Container**: Runs a Linux amd64 environment where `openvds` Python wheels work
2. **Volume Mount**: Your Mac's `/Volumes/Hue/Datasets/VDS` is mounted read-only into the container at `/vds-data`
3. **MCP Protocol**: Uses stdio transport so Claude Desktop can communicate with the containerized server
4. **Environment**: `VDS_DATA_PATH=/vds-data` tells the server where to find VDS files

## Troubleshooting

### Docker not running

```bash
Error: Docker daemon is not running
```

**Solution**: Start Docker Desktop from your Applications folder

### VDS files not found

If the server shows `demo_mode=True`:

1. **Check your VDS data directory is accessible**:
   ```bash
   ls "/Volumes/Hue/Datasets/VDS"
   ```

2. **Verify the path in docker-compose.yml matches your actual location**:
   ```yaml
   volumes:
     - /Volumes/Hue/Datasets/VDS:/vds-data:ro
   ```

3. **Update the path if needed** and rebuild:
   ```bash
   ./run-docker.sh
   ```

### Claude Desktop can't connect

1. **Check the config syntax** - JSON must be valid (no trailing commas)
2. **Verify the image name** - Should be `openvds-mcp-server` (matches what was built)
3. **Check Claude Desktop logs**:
   ```bash
   tail -f ~/Library/Logs/Claude/mcp*.log
   ```

### Permission denied on VDS data

If you get permission errors accessing VDS files:

1. **Check directory permissions**:
   ```bash
   ls -la "/Volumes/Hue/Datasets/VDS"
   ```

2. **Ensure Docker has file sharing permission**:
   - Open Docker Desktop → Settings → Resources → File Sharing
   - Add `/Volumes` if not already there

## Manual Usage

### Run interactively

```bash
docker-compose run --rm openvds-mcp
```

### Run with custom VDS path

```bash
docker run --rm -i --platform linux/amd64 \
  -v "/path/to/your/vds/files:/vds-data:ro" \
  -e VDS_DATA_PATH=/vds-data \
  openvds-mcp-server \
  python src/openvds_mcp_server.py
```

### Enable debug logging

```bash
docker run --rm -i --platform linux/amd64 \
  -v "/Volumes/Hue/Datasets/VDS:/vds-data:ro" \
  -e VDS_DATA_PATH=/vds-data \
  -e LOG_LEVEL=DEBUG \
  openvds-mcp-server \
  python src/openvds_mcp_server.py
```

## Updating the Server

When you make changes to the code:

1. **Rebuild the image**:
   ```bash
   docker-compose build
   ```

2. **Restart Claude Desktop** to pick up the new version

## Architecture

```
┌─────────────────┐
│ Claude Desktop  │
│   (macOS)       │
└────────┬────────┘
         │ stdio (MCP Protocol)
         │
┌────────▼────────────────────────┐
│ Docker Container (Linux amd64)  │
│ ┌─────────────────────────────┐ │
│ │ OpenVDS MCP Server          │ │
│ │ - Python 3.10               │ │
│ │ - openvds 3.4.6             │ │
│ │ - MCP SDK                   │ │
│ └─────────────────────────────┘ │
│                                  │
│ Volume Mount:                    │
│ /vds-data → /Volumes/Hue/.../VDS │
└──────────────────────────────────┘
         │
         │ read VDS files
         │
┌────────▼────────────────────────┐
│ VDS Data (macOS)                │
│ /Volumes/Hue/Datasets/VDS       │
└─────────────────────────────────┘
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VDS_DATA_PATH` | `/vds-data` | Colon-separated paths to VDS files |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Security Notes

- NFS mount is read-only (`:ro`) in the container for safety
- No network ports are exposed - uses stdio only
- Container runs with default user permissions
- VDS files remain on your secure network mount

## Alternative: Local Installation

If you prefer to build OpenVDS from source on macOS instead of using Docker, see the main README for build instructions. Note that this is significantly more complex.
