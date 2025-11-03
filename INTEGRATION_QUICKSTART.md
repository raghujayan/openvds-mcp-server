# Third-Party Integration Quick Guide

## What You Have: OpenVDS MCP Server

Your current MCP server provides:
- Search 2,858+ VDS seismic surveys
- Extract inline/crossline/timeslice images
- Elasticsearch metadata queries
- Fast visualization (2-second response)

**Key insight:** This is already a fully functional MCP server. Third-party tools just need to add their own MCP servers alongside yours.

---

## Integration Pattern: Multiple MCP Servers

### Architecture

```
┌─────────────────────────────────────────────┐
│            Claude Desktop                    │
└────────────┬────────────────────────────────┘
             │
             ├─► OpenVDS MCP Server (you have this)
             │   - search_surveys
             │   - extract_inline_image
             │   - get_facets
             │
             ├─► Petrel MCP Connector (new)
             │   - list_petrel_projects
             │   - get_horizon_from_petrel
             │   - get_faults_from_petrel
             │
             └─► OSDU MCP Connector (new)
                 - search_osdu_data
                 - get_well_data
                 - get_interpretations
```

**Claude automatically uses whichever server has the right data.**

---

## How It Works: Claude Desktop Config

```json
// File: ~/.config/Claude/claude_desktop_config.json

{
  "mcpServers": {
    "openvds": {
      "command": "docker-compose",
      "args": ["-f", "/path/to/openvds-mcp-server/docker-compose.yml",
               "run", "--rm", "openvds-mcp"]
    },
    "petrel": {
      "command": "python",
      "args": ["/path/to/petrel_mcp_connector.py"]
    },
    "osdu": {
      "command": "python",
      "args": ["/path/to/osdu_mcp_connector.py"]
    }
  }
}
```

**That's it.** Claude now has access to all three systems.

---

## Integration Option 1: Petrel Connector (Easiest)

### What You Need to Build

A simple Python script that reads Petrel project files:

```python
# File: petrel_mcp_connector.py

from mcp.server import Server
from mcp.types import Tool, TextContent
import json
import os

server = Server("petrel-connector")

# Tool 1: List Petrel projects
@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="list_petrel_projects",
            description="List all Petrel projects in workspace",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_petrel_horizons",
            description="Get horizons from a Petrel project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"}
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "list_petrel_projects":
        # Read Petrel workspace directory
        workspace = "/path/to/petrel/workspace"
        projects = [d for d in os.listdir(workspace) if d.endswith('.ptd')]
        return [TextContent(type="text", text=json.dumps(projects))]

    elif name == "get_petrel_horizons":
        # Read Petrel project database
        project = arguments["project_name"]
        # Use Petrel SDK or parse .ptd file
        horizons = read_petrel_project(project)  # Your implementation
        return [TextContent(type="text", text=json.dumps(horizons))]

# Run server
if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server
    asyncio.run(stdio_server(server))
```

### User Experience

```
User: "What horizons are in my Petrel project GOM_2024?"

Claude:
1. Calls: petrel.list_petrel_projects()
2. Calls: petrel.get_petrel_horizons("GOM_2024")
3. Returns: "Found 5 horizons:
             - Top_Reservoir
             - Base_Reservoir
             - Top_Seal
             Should I overlay Top_Reservoir on seismic?"

User: "Yes"

Claude:
4. Calls: petrel.get_horizon_surface("GOM_2024", "Top_Reservoir")
   → Gets horizon points
5. Calls: openvds.extract_inline_image("Survey_XYZ", inline=5000)
   → Gets seismic
6. Overlays horizon on seismic image
7. Shows composite visualization
```

**Time to build:** 1-2 weeks for basic read-only connector

---

## Integration Option 2: OSDU Connector

### What You Need

An MCP connector that calls OSDU REST APIs:

```python
# File: osdu_mcp_connector.py

import requests
from mcp.server import Server
from mcp.types import Tool, TextContent
import json

server = Server("osdu-connector")

OSDU_ENDPOINT = "https://your-osdu-instance.com"
API_KEY = os.getenv("OSDU_API_KEY")

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search_osdu_seismic":
        # Call OSDU search API
        response = requests.post(
            f"{OSDU_ENDPOINT}/api/search/v2/query",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "kind": "osdu:wks:master-data--SeismicData:1.0.0",
                "query": arguments["query"]
            }
        )
        results = response.json()["results"]
        return [TextContent(type="text", text=json.dumps(results))]

    elif name == "get_osdu_seismic":
        # Get seismic data from OSDU
        osdu_id = arguments["osdu_id"]

        # 1. Get metadata from OSDU
        metadata = requests.get(
            f"{OSDU_ENDPOINT}/api/storage/v2/records/{osdu_id}",
            headers={"Authorization": f"Bearer {API_KEY}"}
        ).json()

        # 2. Get VDS file location
        vds_url = metadata["data"]["DataLocation"]

        # 3. Use your existing OpenVDS code to extract inline
        import openvds
        vds_handle = openvds.open(vds_url)
        # ... rest same as your current implementation
```

### User Experience

```
User: "Show me all seismic in Santos Basin from OSDU"

Claude:
1. Calls: osdu.search_osdu_seismic(query="Santos Basin")
   → Returns 47 surveys from OSDU
2. Ranks by quality/date
3. Shows top 5

User: "Show inline 2500 from the first survey"

Claude:
4. Calls: osdu.get_osdu_seismic(osdu_id="...", inline=2500)
   → Downloads VDS from OSDU cloud storage
   → Extracts inline using OpenVDS (your existing code)
   → Returns image
```

**Time to build:** 2-3 weeks (if you have OSDU access)

---

## Integration Option 3: Bi-Directional Workflow

### OpenVDS → Petrel (Export)

Add this tool to your existing OpenVDS MCP server:

```python
# Add to src/openvds_mcp_server.py

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    # ... existing tools ...

    elif name == "export_to_petrel":
        """Export AI findings to Petrel project"""
        survey_id = arguments["survey_id"]
        inline_range = arguments["inline_range"]
        petrel_project = arguments["petrel_project"]

        # 1. Extract seismic subset from VDS
        vds_handle = openvds.open(survey_id)
        data = extract_volume(vds_handle, inline_range, ...)

        # 2. Write to SEG-Y (Petrel can import)
        segy_file = write_segy(data, f"/tmp/{survey_id}_export.sgy")

        # 3. Create Petrel import script
        petrel_script = f"""
        # Petrel Ocean script
        import Petrel
        project = Petrel.Project.open("{petrel_project}")
        seismic = project.import_segy("{segy_file}")
        """

        return [TextContent(type="text", text=f"Created {segy_file}\n"
                                                f"Import to Petrel:\n{petrel_script}")]
```

### Petrel → OpenVDS (QC)

Add to Petrel connector:

```python
# In petrel_mcp_connector.py

elif name == "qc_petrel_interpretation":
    """Check Petrel horizon against seismic"""
    project = arguments["project"]
    horizon = arguments["horizon"]

    # 1. Get horizon from Petrel
    horizon_surface = get_horizon_from_petrel(project, horizon)

    # 2. Find matching seismic in OpenVDS
    survey_id = find_matching_survey(horizon_surface.bounds)

    # 3. Extract seismic inline
    # (Call your OpenVDS MCP server via subprocess or HTTP)
    result = subprocess.run([
        "docker-compose", "run", "openvds-mcp",
        "extract_inline_image", survey_id, "5000"
    ], capture_output=True)

    # 4. Overlay horizon on seismic
    composite = overlay_horizon_on_seismic(horizon_surface, seismic_image)

    return composite
```

---

## Quick Start: What to Build First

### Week 1: Petrel Connector (Read-Only)

**Minimal viable connector:**
1. List Petrel projects in workspace
2. Read horizon names from project
3. Export horizon as point cloud

**Deliverable:** Can ask Claude "What's in my Petrel project?"

---

### Week 2: Overlay Workflow

**Connect Petrel + OpenVDS:**
1. Get horizon from Petrel connector
2. Get seismic from OpenVDS connector
3. Overlay in Claude

**Deliverable:** QC Petrel interpretations against seismic via AI

---

### Week 3-4: Export to Petrel

**Add export tool:**
1. OpenVDS extracts seismic subset
2. Writes SEG-Y file
3. Creates Petrel import script

**Deliverable:** AI finds prospects → export to Petrel for detailed work

---

## Commercial Opportunities (Short Version)

### 1. JV Partner Access ($900K/year potential)
- Give JV partners AI access to shared data
- Charge $15K/month per partner
- No file transfers, instant access

### 2. License to Smaller Operators ($500K-$2M/year)
- Sell MCP server + connectors to other E&P companies
- $100K-$500K license + 20% annual support

### 3. Partner with Bluware
- They provide cloud infrastructure
- You provide MCP expertise
- Revenue share on joint product

---

## Summary: What You Actually Need to Do

### You Already Have:
✅ Working MCP server (OpenVDS)
✅ Docker deployment
✅ 2,858 surveys indexed

### To Add Third-Party Integration:

**Option A: Build Petrel Connector (1-2 weeks)**
```bash
# 1. Create petrel_mcp_connector.py (100 lines)
# 2. Add to Claude config
# 3. Test with your Petrel projects
```

**Option B: Build OSDU Connector (2-3 weeks, if you have OSDU)**
```bash
# 1. Create osdu_mcp_connector.py (150 lines)
# 2. Configure OSDU credentials
# 3. Add to Claude config
```

**Option C: Wait for Vendors (0 effort)**
```bash
# Let Schlumberger/Bluware build MCP into their products
# Just configure Claude to use their servers when available
```

**Recommended: Start with Option A (Petrel), it's highest value and easiest.**

---

## Next Steps

1. **Validate demand:** Survey your G&G team - do they want Petrel integration?
2. **Prototype:** Build minimal Petrel connector (1 week)
3. **Pilot:** Test with 3-5 users
4. **Decide:** Based on pilot, invest in full connector or wait for vendors

**The key insight:** You don't need to rebuild anything. Just add more MCP servers alongside your OpenVDS one. Claude orchestrates them automatically.
