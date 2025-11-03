# Third-Party Data Management Integration Guide

## Executive Summary

This document outlines how third-party data management tools (Petrel, Kingdom, OSDU, Bluware, etc.) can integrate with the OpenVDS MCP Server, creating a unified AI-powered subsurface data ecosystem.

**Key Integration Patterns:**
1. **MCP as Data Bridge** - Third-party tools expose data via MCP protocol
2. **Bi-directional Workflow** - MCP → Petrel for detailed work, Petrel → MCP for AI analysis
3. **OSDU Integration** - Connect to enterprise data platforms
4. **Commercial Opportunities** - Partner with data management vendors

---

## Table of Contents

1. [Integration Architecture Overview](#integration-architecture-overview)
2. [Integration Pattern 1: Data Bridge](#integration-pattern-1-data-bridge)
3. [Integration Pattern 2: Bi-Directional Workflow](#integration-pattern-2-bi-directional-workflow)
4. [Integration Pattern 3: OSDU Data Platform](#integration-pattern-3-osdu-data-platform)
5. [Integration Pattern 4: Commercial Vendor Partnerships](#integration-pattern-4-commercial-vendor-partnerships)
6. [Specific Tool Integrations](#specific-tool-integrations)
7. [Technical Implementation](#technical-implementation)
8. [Commercial Opportunities](#commercial-opportunities)
9. [Security & Governance](#security--governance)
10. [Roadmap](#roadmap)

---

## Integration Architecture Overview

### Current State: Isolated Systems

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Petrel     │     │   Kingdom    │     │  OSDU/Other  │
│  (Desktop)   │     │  (Desktop)   │     │   (Cloud)    │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                     │
       │                    │                     │
       ▼                    ▼                     ▼
┌──────────────────────────────────────────────────────────┐
│            Shared File System / Database                  │
│         (VDS files, SEGY, project databases)              │
└──────────────────────────────────────────────────────────┘
                              │
                              │
                              ▼
                    ┌──────────────────┐
                    │  OpenVDS MCP     │
                    │     Server       │
                    └──────────────────┘
                              │
                              ▼
                         Claude AI

Problem: Data silos, manual handoffs, no AI awareness
```

### Future State: Unified AI-Enabled Ecosystem

```
┌─────────────────────────────────────────────────────────────┐
│                       Claude AI                              │
│            (Natural Language Interface)                      │
└───────────────────────┬─────────────────────────────────────┘
                        │ MCP Protocol
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   MCP Router / Gateway                       │
│         (Intelligent routing to appropriate backend)         │
└───┬─────────────┬─────────────┬──────────────┬──────────────┘
    │             │             │              │
    ▼             ▼             ▼              ▼
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐
│OpenVDS  │  │ Petrel  │  │ OSDU    │  │ Other Tools │
│  MCP    │  │  MCP    │  │  MCP    │  │   (MCP)     │
│ Server  │  │Connector│  │Connector│  │             │
└─────────┘  └─────────┘  └─────────┘  └─────────────┘
    │             │             │              │
    ▼             ▼             ▼              ▼
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐
│  VDS    │  │ Petrel  │  │  OSDU   │  │   Custom    │
│  Files  │  │Projects │  │   Data  │  │    Data     │
└─────────┘  └─────────┘  └─────────┘  └─────────────┘

Benefit: Single AI interface to entire subsurface data estate
```

### Key Concepts

**MCP (Model Context Protocol):**
- Open standard by Anthropic
- Allows AI to access external data sources
- **Vendor-neutral:** Any tool can implement MCP
- **Composable:** Multiple MCP servers can coexist

**Integration Philosophy:**
- **Augment, don't replace** existing tools
- **Gradual adoption** - start with read-only, expand to write
- **User choice** - AI routes to appropriate tool automatically

---

## Integration Pattern 1: Data Bridge

### Concept: Third-Party Tool as MCP Server

**Use Case:** Expose existing tool's data via MCP without changing the tool itself

```
User: "Show me the fault interpretation from Petrel project XYZ"

Claude → MCP Router → Petrel MCP Connector → Petrel Project Database
                                              ↓
                                         Extract fault polygons
                                              ↓
                                    Convert to MCP response
                                              ↓
Claude ← MCP Response ← "Here are 12 faults from Project XYZ..."
```

### Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Petrel Desktop                          │
│  (Existing installation, no modifications needed)          │
└────────────────────────────────────────────────────────────┘
                         │
                         │ File system access
                         ▼
┌────────────────────────────────────────────────────────────┐
│           Petrel MCP Connector (New Component)             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ MCP Server Implementation                            │ │
│  │  - Tools: list_projects, get_horizons, get_faults   │ │
│  │  - Resources: Project metadata, interpretation data │ │
│  └──────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Petrel SDK / File Readers                           │ │
│  │  - Read .ptd project files                          │ │
│  │  - Parse interpretation databases                   │ │
│  │  - Extract surfaces, faults, wells                  │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
                         │ MCP Protocol
                         ▼
                    Claude AI
```

### Implementation Options

#### Option A: Read-Only Connector (Low Complexity)

**What it does:**
- Reads Petrel project files (`.ptd`, interpretation databases)
- Exposes horizons, faults, wells as MCP resources
- Claude can query: "What horizons are picked in Project X?"

**Tools provided:**
```python
# Petrel MCP Connector Tools

list_petrel_projects() -> List[ProjectInfo]
# Returns: All Petrel projects in workspace

get_project_info(project_name: str) -> ProjectMetadata
# Returns: Surveys, wells, interpretations in project

get_horizon_list(project_name: str) -> List[Horizon]
# Returns: All picked horizons

get_fault_list(project_name: str) -> List[Fault]
# Returns: All fault interpretations

get_well_list(project_name: str) -> List[Well]
# Returns: All wells with markers

export_horizon_surface(project_name: str, horizon_name: str) -> bytes
# Returns: Surface as point cloud or mesh

compare_to_seismic(project_name: str, horizon_name: str, survey_id: str)
# Overlays Petrel interpretation on OpenVDS seismic
```

**Benefits:**
- ✅ No Petrel modification required
- ✅ Quick to implement (~2-4 weeks)
- ✅ Low risk (read-only)

**Limitations:**
- ❌ Can't modify Petrel projects via AI
- ❌ Requires Petrel to be installed (even if not running)

---

#### Option B: API-Based Connector (Medium Complexity)

**What it does:**
- Uses Petrel Ocean/Studio API
- Can READ and WRITE interpretations
- Allows AI to create/modify picks

**Additional tools:**
```python
create_horizon_interpretation(project_name: str, horizon_name: str,
                               seed_points: List[Point]) -> HorizonID
# AI suggests seed points, Petrel auto-tracks

create_fault_stick(project_name: str, fault_name: str,
                   fault_sticks: List[Polyline]) -> FaultID
# AI generates fault geometry, Petrel imports

update_well_marker(project_name: str, well_name: str,
                   marker_name: str, depth: float)
# AI suggests marker adjustment based on seismic tie
```

**Benefits:**
- ✅ Full integration (read + write)
- ✅ AI can assist with interpretation (not just view)
- ✅ Maintains Petrel as source of truth

**Limitations:**
- ⚠️ Requires Petrel Ocean license
- ⚠️ More complex implementation (2-3 months)
- ⚠️ Must handle version compatibility

---

#### Option C: Cloud-Based Proxy (High Complexity)

**What it does:**
- Petrel data synced to cloud database
- MCP server accesses cloud copy
- No local Petrel installation required

**Architecture:**
```
Petrel Desktop → Export daemon → Cloud Database (PostgreSQL/MongoDB)
                                         ↑
                                         │
                               Petrel MCP Connector
                                         ↑
                                         │
                                    Claude AI
```

**Benefits:**
- ✅ Works without Petrel installed
- ✅ Scalable (multiple users, cloud deployment)
- ✅ Fast queries (indexed database)

**Limitations:**
- ❌ Complex infrastructure (3-6 months)
- ❌ Sync latency (data not real-time)
- ❌ Storage costs for duplicated data

---

### Example Workflow: Petrel + OpenVDS Integration

**User request:**
> "Compare my Petrel horizon interpretation to the seismic"

**MCP Workflow:**
```
1. Claude calls: petrel_connector.get_horizon_surface("Project_ABC", "Top_Reservoir")
   → Returns: Surface as 3D point cloud (X, Y, Z coordinates)

2. Claude calls: openvds_mcp.get_survey_info("ST10010")
   → Returns: Survey geometry (inline/crossline ranges)

3. Claude calls: openvds_mcp.extract_inline_image("ST10010", inline=5000)
   → Returns: Seismic image

4. Claude calls: overlay_interpretation_on_seismic(
       seismic_image=seismic,
       horizon_surface=horizon,
       inline_number=5000
   )
   → Returns: Composite image showing both

5. Claude responds:
   "Here's your Top_Reservoir horizon overlaid on Inline 5000.
    I notice a 30ms mismatch at crossline 3200-3400. This could be:
    - Velocity model error
    - Mis-pick on the horizon
    - Fault offsetting the reservoir

    Should I show adjacent inlines to investigate?"
```

**Value:**
- Instant QC of interpretations vs seismic
- AI identifies mismatches automatically
- Saves hours of manual overlay work

---

## Integration Pattern 2: Bi-Directional Workflow

### Concept: MCP for Exploration, Petrel for Detailed Work

**Philosophy:** Use the right tool for the right job

```
AI/MCP excels at:                    Petrel excels at:
├─ Rapid exploration                 ├─ Detailed horizon picking
├─ Data discovery                    ├─ Complex fault modeling
├─ QC and anomaly detection         ├─ Depth conversion
├─ Natural language queries         ├─ Reservoir modeling
└─ Cross-survey analysis            └─ Integration with wells
```

### Workflow Example: Exploration to Production

**Phase 1: Exploration (MCP-led)**

```
User: "Find prospects in Gulf of Mexico 2024 surveys"

Claude (via MCP):
1. Searches 2,858 surveys, finds 14 in GOM 2024
2. Scans all for amplitude anomalies
3. Ranks by anomaly strength
4. Generates quick-look images
5. Presents top 3 candidates

Output: "Prospect A at Survey XYZ, Inline 2340 looks most promising"
Time: 5 minutes (vs 2-3 days manually)
```

**Phase 2: Detailed Assessment (MCP + Petrel)**

```
User: "Load Prospect A into Petrel for detailed analysis"

Claude (via MCP):
1. Calls: petrel_connector.create_new_project("Prospect_A")
2. Calls: petrel_connector.import_survey("XYZ", inline_range=[2200,2500])
3. Calls: petrel_connector.import_wells_nearby(lat, lon, radius=10km)
4. Opens Petrel with project pre-loaded

User switches to Petrel Desktop:
- Does detailed horizon tracking
- Builds structural framework
- Creates reservoir model

Time saved: 1-2 days (data gathering automated)
```

**Phase 3: Interpretation QC (Petrel → MCP)**

```
User: "Check if my interpretation makes sense"

Claude (via Petrel MCP Connector):
1. Reads picked horizons from Petrel
2. Overlays on seismic via OpenVDS
3. Checks for:
   - Horizon crossing itself (topology error)
   - Large gaps in picking
   - Mismatch with seismic character
4. Reports: "Horizon looks good, but gap at crosslines 3400-3500"

User fixes in Petrel, re-checks with Claude

Time saved: 2-3 hours of manual QC
```

**Phase 4: Documentation (MCP-led)**

```
User: "Create a prospect summary for management"

Claude (via MCP):
1. Reads Petrel interpretation
2. Extracts key seismic images
3. Pulls well data if available
4. Generates markdown report:
   - Executive summary
   - Seismic images with annotations
   - Structural framework
   - Risk assessment
5. Exports to PowerPoint or PDF

Time saved: 4-6 hours of manual report creation
```

### Handoff Mechanisms

**From MCP to Petrel:**
```python
# Tool: export_to_petrel
export_to_petrel(
    survey_id: str,
    inline_range: tuple,
    crossline_range: tuple,
    petrel_project: str,
    create_if_missing: bool = True
) -> str  # Returns: Petrel project path

# Creates Petrel project with:
# - Seismic volume (subset from OpenVDS)
# - AI-identified features as annotations
# - Recommended interpretation starting points
```

**From Petrel to MCP:**
```python
# Tool: import_from_petrel
import_from_petrel(
    petrel_project: str,
    items: List[str]  # ["horizons", "faults", "wells"]
) -> Dict

# Returns interpretations in MCP-compatible format
# For AI analysis, QC, or cross-survey comparison
```

---

## Integration Pattern 3: OSDU Data Platform

### What is OSDU?

**OSDU (Open Subsurface Data Universe):**
- Industry standard for subsurface data management
- Backed by major oil companies (Shell, Chevron, Equinor, etc.)
- Cloud-native, API-first architecture
- Replaces proprietary data management systems

**Key features:**
- **Unified data model** for all subsurface data types
- **REST APIs** for programmatic access
- **Cloud-agnostic** (AWS, Azure, Google Cloud)
- **Vendor ecosystem** (Schlumberger, Halliburton, etc.)

### OSDU + MCP Integration

**Architecture:**

```
┌───────────────────────────────────────────────────────────┐
│                      Claude AI                            │
└────────────────────┬──────────────────────────────────────┘
                     │ MCP Protocol
                     ▼
┌────────────────────────────────────────────────────────────┐
│              OSDU MCP Connector                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ MCP Tools                                            │ │
│  │  - search_osdu_data(query)                          │ │
│  │  - get_seismic_metadata(id)                         │ │
│  │  - get_well_data(id)                                │ │
│  │  - get_interpretation_data(id)                      │ │
│  └──────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ OSDU Client SDK                                      │ │
│  │  - Authentication (OAuth2)                           │ │
│  │  - REST API calls to OSDU platform                  │ │
│  │  - Data type conversions                            │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────┬───────────────────────────────────────┘
                     │ HTTPS REST API
                     ▼
┌────────────────────────────────────────────────────────────┐
│                 OSDU Data Platform (Cloud)                 │
│  ┌──────────┬──────────┬──────────┬──────────┬─────────┐ │
│  │ Seismic  │  Wells   │  Logs    │Interpre- │ Produc- │ │
│  │   Data   │          │          │  tation  │  tion   │ │
│  └──────────┴──────────┴──────────┴──────────┴─────────┘ │
└────────────────────────────────────────────────────────────┘
```

### OSDU MCP Tools (Example Implementation)

```python
# Tool: search_osdu_data
search_osdu_data(
    query: str,
    data_type: str = "SeismicData",  # or "WellLog", "Interpretation", etc.
    spatial_filter: Optional[BBox] = None,
    date_range: Optional[tuple] = None
) -> List[DataRecord]

# Example:
# search_osdu_data(
#     query="Santos Basin 3D seismic",
#     spatial_filter=BBox(lat_min=-25, lat_max=-23, lon_min=-44, lon_max=-42),
#     date_range=(2020, 2024)
# )
#
# Returns: List of OSDU records matching criteria

# Tool: get_seismic_from_osdu
get_seismic_from_osdu(
    osdu_id: str,
    inline: Optional[int] = None,
    crossline: Optional[int] = None
) -> Dict

# Retrieves seismic data from OSDU, extracts slice, visualizes
# Similar to current OpenVDS tools but data source is OSDU

# Tool: link_osdu_to_interpretation
link_osdu_to_interpretation(
    seismic_osdu_id: str,
    interpretation_osdu_id: str,
    action: str = "overlay"
) -> Image

# Overlays interpretation from OSDU on seismic from OSDU
# Returns composite visualization
```

### Benefits of OSDU Integration

**For enterprises using OSDU:**
1. **Single source of truth**
   - OSDU is authoritative data repository
   - MCP provides AI interface to OSDU
   - No data duplication

2. **Unified access model**
   - Seismic, wells, interpretations all accessible via same MCP interface
   - Claude doesn't need to know data is in OSDU vs VDS vs Petrel
   - Intelligent routing: "Show me seismic" → finds data wherever it lives

3. **Cloud-native**
   - OSDU already in cloud (AWS/Azure)
   - MCP connector runs as cloud service
   - Scalable to entire enterprise (1000s of users)

4. **Vendor neutral**
   - OSDU is open standard
   - MCP is open protocol
   - No lock-in to Schlumberger, Halliburton, etc.

### Example Workflow: OSDU + MCP

**Integrated subsurface analysis:**

```
User: "Analyze well ABC-123 vs seismic in the area"

Claude (via OSDU MCP):
1. search_osdu_data(query="ABC-123", data_type="Well")
   → Finds well record in OSDU

2. get_well_location(osdu_well_id)
   → Returns: Lat/Lon coordinates

3. search_osdu_data(
       data_type="SeismicData",
       spatial_filter=BBox(center=well_location, radius=5km)
   )
   → Finds 3 seismic surveys covering well location

4. get_seismic_from_osdu(
       osdu_seismic_id=survey_1,
       inline=closest_to_well
   )
   → Extracts inline passing through well

5. get_well_data(osdu_well_id)
   → Gets well logs, markers

6. overlay_well_on_seismic(seismic, well_data)
   → Creates composite visualization

7. Claude responds:
   "Here's well ABC-123 overlaid on seismic Survey XYZ.
    The Top_Reservoir marker at 2,450m MD corresponds to
    a strong reflection at 1,850ms TWT. The seismic shows
    amplitude dimming to the east, suggesting possible
    fluid contact. Should I check if other wells in OSDU
    support this interpretation?"
```

**Value:**
- All data retrieved automatically from OSDU
- No manual export/import
- Integrated analysis across data types
- Asks intelligent follow-up questions

---

## Integration Pattern 4: Commercial Vendor Partnerships

### Concept: Vendors Build Native MCP Support

**Instead of us building connectors, vendors add MCP to their products**

### Example: Bluware InteractivAI + MCP

**Bluware InteractivAI:**
- Cloud-native seismic interpretation platform
- AI-assisted horizon/fault picking
- VDS format creators

**Integration scenario:**
```
Bluware adds MCP server to InteractivAI:

Tools exposed:
- list_bluware_projects()
- get_ai_horizon_picks(project_id, horizon_name)
- get_ai_fault_candidates(project_id, confidence_threshold)
- run_ai_interpretation(project_id, survey_id, mode="auto")

User workflow:
1. Uses Claude: "Run AI interpretation on Survey XYZ"
2. Claude calls Bluware MCP: run_ai_interpretation(...)
3. Bluware processes in cloud (GPU-accelerated)
4. Returns results to Claude
5. Claude: "Interpretation complete. Found 15 horizons, 8 faults.
             Should I export to Petrel for QC?"
```

**Benefits:**
- ✅ Best of both worlds: Bluware's AI + Claude's conversational interface
- ✅ Vendor maintains connector (not our responsibility)
- ✅ Seamless updates when Bluware releases new features

---

### Example: Schlumberger Petrel + MCP

**If Schlumberger builds MCP into Petrel:**

**Petrel 2026 (hypothetical):**
```
New feature: "Claude Assistant for Petrel"

Built-in MCP server exposes:
- All Petrel data (surveys, wells, interpretations)
- All Petrel workflows (horizon tracking, fault modeling)
- Petrel automation (scripting via natural language)

User experience:
1. Opens Petrel
2. Types in "Claude Assistant" panel: "Pick Top_Reservoir on all inlines"
3. Claude (via Petrel MCP):
   - Understands context (current project, loaded surveys)
   - Calls Petrel API to run auto-tracker
   - Monitors progress
   - Reports: "Tracked 850 inlines, flagged 23 for manual QC"
4. User reviews flagged inlines, accepts/rejects
5. Claude: "Horizon complete. Should I create a time/depth surface?"
```

**Strategic value for Schlumberger:**
- Differentiates Petrel from competitors
- Attracts younger, AI-savvy users
- Reduces support burden (Claude answers basic questions)
- Creates new revenue stream (AI-augmented Petrel license)

---

### Partnership Opportunities

**Potential partners:**

| Vendor | Product | MCP Integration Opportunity |
|--------|---------|----------------------------|
| **Schlumberger** | Petrel, Studio | Native MCP in Petrel, "Claude mode" |
| **Halliburton** | Kingdom, DecisionSpace | MCP connector for DecisionSpace |
| **Emerson (Paradigm)** | SKUA-GOCAD, Stratimagic | Cloud API + MCP |
| **Bluware** | InteractivAI, Volume | Already cloud-native, easy MCP add |
| **IHS Markit** | Kingdom, Petra | Data lake + MCP for commercial data |
| **Landmark (Halliburton)** | OpenWorks | Enterprise data mgmt + MCP |
| **OSDU Forum** | OSDU Platform | Standard MCP connector for all OSDU deployments |

**Win-win proposition:**
- **For vendor:** Differentiation, modern AI interface, attract new users
- **For us:** Native integration, vendor-maintained, enterprise support

---

## Specific Tool Integrations

### 1. Petrel Integration (Detailed)

**Technical approach:**

#### Read-Only Connector (MVP)

**Technology stack:**
```
Python 3.10+
├─ petrel-sdk (Schlumberger Ocean SDK)
├─ mcp (Anthropic MCP SDK)
├─ numpy (data handling)
└─ sqlite3 (cache Petrel metadata)
```

**Implementation:**
```python
# File: src/petrel_mcp_connector.py

from mcp.server import Server
from mcp.types import Tool, TextContent
import petrel_sdk  # Hypothetical Petrel SDK

class PetrelMCPServer:
    def __init__(self, petrel_workspace_path: str):
        self.workspace = petrel_workspace_path
        self.server = Server("petrel-connector")

        # Define tools
        self.server.add_tool(Tool(
            name="list_petrel_projects",
            description="List all Petrel projects in workspace",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ))

        self.server.add_tool(Tool(
            name="get_horizon_from_petrel",
            description="Get horizon interpretation from Petrel project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "horizon_name": {"type": "string"}
                },
                "required": ["project_name", "horizon_name"]
            }
        ))

    async def handle_list_projects(self):
        """Read Petrel workspace, return project list"""
        projects = petrel_sdk.list_projects(self.workspace)
        return TextContent(
            type="text",
            text=json.dumps([{
                "name": p.name,
                "created": p.created_date,
                "surveys": len(p.surveys),
                "wells": len(p.wells)
            } for p in projects])
        )

    async def handle_get_horizon(self, project_name: str, horizon_name: str):
        """Extract horizon surface from Petrel"""
        project = petrel_sdk.open_project(f"{self.workspace}/{project_name}")
        horizon = project.get_horizon(horizon_name)

        # Convert to standard format
        surface_points = []
        for point in horizon.points:
            surface_points.append({
                "x": point.x,
                "y": point.y,
                "z": point.z,
                "inline": point.inline,
                "crossline": point.crossline,
                "twt_ms": point.twt
            })

        return TextContent(
            type="text",
            text=json.dumps({
                "horizon_name": horizon_name,
                "num_points": len(surface_points),
                "points": surface_points[:1000],  # Limit for MCP size
                "bounds": {
                    "inline_min": min(p["inline"] for p in surface_points),
                    "inline_max": max(p["inline"] for p in surface_points),
                    "crossline_min": min(p["crossline"] for p in surface_points),
                    "crossline_max": max(p["crossline"] for p in surface_points),
                    "twt_min": min(p["twt_ms"] for p in surface_points),
                    "twt_max": max(p["twt_ms"] for p in surface_points)
                }
            })
        )
```

**Deployment:**
```yaml
# File: petrel-mcp-config.json (added to Claude config)
{
  "mcpServers": {
    "openvds": {
      "command": "docker-compose",
      "args": ["run", "openvds-mcp"]
    },
    "petrel": {
      "command": "python",
      "args": ["src/petrel_mcp_connector.py", "--workspace", "/path/to/petrel/workspace"]
    }
  }
}
```

**User experience:**
```
User: "What horizons are picked in my Petrel project 'GOM_Prospect_A'?"

Claude:
1. Calls: petrel.list_petrel_projects()
2. Finds: "GOM_Prospect_A" exists
3. Calls: petrel.get_project_info("GOM_Prospect_A")
4. Returns: "Project has 5 horizons:
             - Top_Reservoir (5,234 points)
             - Base_Reservoir (4,987 points)
             - Top_Seal (6,123 points)
             - Fault_1 (1,234 fault sticks)
             - Fault_2 (987 fault sticks)"
```

---

### 2. Kingdom Integration

**Kingdom specifics:**
- Less API-friendly than Petrel (older architecture)
- File-based: `.kdb` databases (SQLite-based)
- Can read directly without Kingdom running

**Approach: File-based reader**

```python
# File: src/kingdom_mcp_connector.py

import sqlite3
import struct

class KingdomMCPServer:
    def __init__(self, kingdom_project_path: str):
        self.db_path = f"{kingdom_project_path}/project.kdb"
        self.conn = sqlite3.connect(self.db_path)

    async def handle_get_horizons(self, project_name: str):
        """Read horizons from Kingdom .kdb file"""
        cursor = self.conn.cursor()

        # Kingdom stores horizons in 'Interpretation' table
        cursor.execute("""
            SELECT name, type, num_points, color
            FROM Interpretation
            WHERE type = 'Horizon'
        """)

        horizons = []
        for row in cursor.fetchall():
            horizons.append({
                "name": row[0],
                "type": row[1],
                "points": row[2],
                "color": row[3]
            })

        return horizons

    async def handle_get_horizon_surface(self, horizon_name: str):
        """Extract horizon point cloud from Kingdom"""
        cursor = self.conn.cursor()

        # Kingdom stores points in binary blob
        cursor.execute("""
            SELECT geometry_blob
            FROM Interpretation
            WHERE name = ?
        """, (horizon_name,))

        blob = cursor.fetchone()[0]

        # Parse Kingdom's binary format (proprietary, requires documentation)
        points = self._parse_kingdom_geometry(blob)

        return points

    def _parse_kingdom_geometry(self, blob: bytes) -> List[Point]:
        """Parse Kingdom's proprietary geometry format"""
        # This would require Kingdom SDK or reverse engineering
        # Placeholder implementation
        pass
```

**Challenges:**
- Kingdom file format partially proprietary
- May need Kingdom SDK (if available)
- Alternative: Export from Kingdom, import to MCP

---

### 3. OSDU Integration (Detailed)

**OSDU APIs relevant to seismic:**

```python
# File: src/osdu_mcp_connector.py

import requests
from typing import Dict, List

class OSDUMCPServer:
    def __init__(self, osdu_endpoint: str, api_key: str):
        self.endpoint = osdu_endpoint
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "data-partition-id": "opendes"
        }

    async def handle_search_osdu(self, query: str, kind: str):
        """Search OSDU data lake"""
        url = f"{self.endpoint}/api/search/v2/query"

        payload = {
            "kind": kind,  # e.g., "osdu:wks:master-data--SeismicData:1.0.0"
            "query": query,
            "limit": 100
        }

        response = requests.post(url, json=payload, headers=self.headers)
        results = response.json()

        return results["results"]

    async def handle_get_seismic_metadata(self, osdu_id: str):
        """Get seismic survey metadata from OSDU"""
        url = f"{self.endpoint}/api/storage/v2/records/{osdu_id}"

        response = requests.get(url, headers=self.headers)
        record = response.json()

        return {
            "id": record["id"],
            "name": record["data"]["Name"],
            "spatial_coverage": record["data"]["SpatialCoverage"],
            "acquisition_date": record["data"]["AcquisitionDate"],
            "data_location": record["data"]["DataLocation"]
        }

    async def handle_get_seismic_data(self, osdu_id: str, inline: int):
        """Retrieve actual seismic data from OSDU storage"""
        # Get storage location from metadata
        metadata = await self.handle_get_seismic_metadata(osdu_id)
        data_url = metadata["data_location"]

        # OSDU stores seismic in cloud blob storage (S3/Azure Blob/GCS)
        # Would need to:
        # 1. Get signed URL from OSDU
        # 2. Download VDS/SEG-Y file
        # 3. Extract inline (similar to current OpenVDS approach)
        # 4. Return image

        # For VDS files in OSDU:
        vds_handle = openvds.open(data_url)
        # ... rest same as current implementation
```

**OSDU Data Kinds (relevant to subsurface):**

| Kind | Description | MCP Use Case |
|------|-------------|--------------|
| `master-data--SeismicData` | 2D/3D/4D seismic surveys | Search, visualize |
| `master-data--Well` | Well headers | Locate wells for seismic tie |
| `work-product-component--WellLog` | Well logs (GR, resistivity, etc.) | Overlay on seismic |
| `work-product-component--SeismicInterpretation` | Horizons, faults | QC vs seismic |
| `master-data--Field` | Field boundaries | Regional context |

**Full workflow: OSDU → MCP → Claude**

```
User: "Show me all seismic in the Santos Basin"

Claude:
1. osdu.search_osdu(
     query="Santos Basin",
     kind="master-data--SeismicData"
   )
   → Returns 47 OSDU records

2. For each record, extract key metadata:
   - Name
   - Acquisition year
   - Coverage area
   - Data quality score (if available)

3. Rank by quality and recency

4. Present: "Found 47 seismic surveys in Santos Basin.
             Top 5 by quality and recency:
             1. Santos_3D_2024_HighRes (2024, 2,400 sq km)
             2. Santos_4D_Monitor_2023 (2023, 1,800 sq km)
             ...
             Should I show you inline previews from Survey #1?"

User: "Yes"

Claude:
5. osdu.get_seismic_data(osdu_id="Santos_3D_2024_HighRes", inline=2500)
   → Downloads VDS from cloud storage
   → Extracts inline
   → Generates image
   → Returns visualization
```

---

### 4. GeoTeric Integration

**GeoTeric:**
- Advanced seismic interpretation (FFAid, facies classification)
- AI/ML for geological features
- Desktop application (like Petrel)

**Integration approach:**
- Similar to Petrel (file-based or API)
- GeoTeric projects stored as files
- Can read interpretation results

**Unique value:**
- GeoTeric's AI identifies geobodies (channels, reefs, etc.)
- MCP exposes these to Claude
- Claude correlates across surveys

**Example:**
```
User: "Find all channel systems identified by GeoTeric across our surveys"

Claude (via GeoTeric MCP):
1. geoteric.list_projects()
2. For each project:
   - geoteric.get_geobodies(type="channel")
3. Aggregates results
4. Returns: "Found 23 channel systems across 8 surveys:
             - Santos_2024: 7 channels (avg width 800m)
             - GOM_2023: 12 channels (avg width 1200m)
             ...
             All channels trending NE-SW. Likely deepwater turbidites.
             Should I map their distribution?"
```

---

## Technical Implementation

### MCP Router / Gateway

**Problem:** User has multiple MCP servers (OpenVDS, Petrel, OSDU, etc.)

**Solution:** Intelligent router that directs queries to appropriate backend

```python
# File: src/mcp_router.py

from mcp.server import Server
from typing import Dict, List

class MCPRouter:
    def __init__(self):
        self.backends = {
            "openvds": OpenVDSMCPServer(),
            "petrel": PetrelMCPServer(),
            "osdu": OSDUMCPServer(),
            "kingdom": KingdomMCPServer()
        }

        self.tool_routing = {
            # Seismic data tools → OpenVDS (fastest for VDS files)
            "search_surveys": "openvds",
            "extract_inline_image": "openvds",

            # Interpretation tools → Petrel (if available), else OSDU
            "get_horizon_list": self._route_interpretation,
            "get_fault_list": self._route_interpretation,

            # Well data → OSDU (if enterprise), else Petrel
            "get_well_data": self._route_well_data,

            # Advanced analysis → Best available backend
            "analyze_seismic": self._route_analysis
        }

    def _route_interpretation(self, args: Dict):
        """Decide where to get interpretation data"""
        # Check if Petrel project specified
        if "petrel_project" in args:
            return "petrel"
        # Check if OSDU ID specified
        elif "osdu_id" in args:
            return "osdu"
        # Default: search both, return combined
        else:
            return ["petrel", "osdu"]

    def _route_well_data(self, args: Dict):
        """Decide where to get well data"""
        # OSDU preferred (if available)
        if self.backends["osdu"].is_available():
            return "osdu"
        else:
            return "petrel"

    async def handle_tool_call(self, tool_name: str, args: Dict):
        """Route tool call to appropriate backend"""
        backend_name = self.tool_routing.get(tool_name)

        if callable(backend_name):
            # Dynamic routing
            backend_name = backend_name(args)

        if isinstance(backend_name, list):
            # Query multiple backends, merge results
            results = []
            for name in backend_name:
                result = await self.backends[name].handle_tool(tool_name, args)
                results.append(result)
            return self._merge_results(results)
        else:
            # Single backend
            return await self.backends[backend_name].handle_tool(tool_name, args)
```

**Benefit:** User doesn't care where data comes from, Claude figures it out

---

### Data Format Conversions

**Challenge:** Different tools use different formats

**Examples:**
- Petrel: Proprietary `.ptd` project files
- Kingdom: `.kdb` SQLite databases
- OSDU: JSON with cloud blob references
- OpenVDS: VDS binary format

**Solution: Common data model**

```python
# File: src/common_models.py

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SeismicSurvey:
    """Common representation of seismic survey across all backends"""
    id: str
    name: str
    source: str  # "openvds", "osdu", "petrel", etc.
    source_id: str  # Original ID in source system

    # Geometry
    inline_range: tuple[int, int]
    crossline_range: tuple[int, int]
    sample_range: tuple[int, int]

    # Metadata
    acquisition_date: Optional[str]
    survey_type: str  # "3D", "4D", "2D"
    region: Optional[str]

    # Data access
    data_location: str  # Path or URL to actual data

    def to_dict(self):
        """Convert to MCP-compatible dict"""
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "inline_range": self.inline_range,
            "crossline_range": self.crossline_range,
            # ... etc
        }

@dataclass
class HorizonInterpretation:
    """Common representation of horizon across all backends"""
    id: str
    name: str
    source: str
    source_id: str

    # Geometry
    points: List[tuple[float, float, float]]  # (x, y, z)
    inline_crossline_map: Dict[tuple[int, int], float]  # IL/XL → TWT

    # Metadata
    interpreter: Optional[str]
    date_picked: Optional[str]
    confidence: Optional[float]

    def to_geojson(self):
        """Export as GeoJSON for visualization"""
        pass

    def to_petrel_format(self):
        """Export for import to Petrel"""
        pass

# Similar models for:
# - FaultInterpretation
# - WellData
# - Geobody
# etc.
```

**Converters:**

```python
# File: src/converters.py

class DataConverter:
    @staticmethod
    def petrel_horizon_to_common(petrel_horizon) -> HorizonInterpretation:
        """Convert Petrel horizon to common format"""
        pass

    @staticmethod
    def osdu_horizon_to_common(osdu_record) -> HorizonInterpretation:
        """Convert OSDU horizon to common format"""
        pass

    @staticmethod
    def common_to_petrel_horizon(horizon: HorizonInterpretation):
        """Convert common format to Petrel"""
        pass
```

**Benefit:** MCP router works with common format, backends handle conversions

---

## Commercial Opportunities

### 1. MCP-as-a-Service for Joint Ventures

**Scenario:** Your company operates joint ventures with partners

**Opportunity:**
- Deploy MCP server with read-only access to JV data
- Partners pay subscription for AI-powered data access
- No need to send files back and forth

**Revenue model:**
```
Pricing tiers:
- Basic: $5K/month (1 user, search + visualization)
- Professional: $15K/month (5 users, + interpretation QC)
- Enterprise: $50K/month (unlimited users, + custom integrations)

Potential revenue:
- 5 JV partners × $15K/month = $75K/month = $900K/year
```

**Value proposition to partners:**
- Instant access to JV seismic data
- No need for Petrel licenses (expensive)
- Fast exploration workflows
- Always up-to-date (data in one place)

---

### 2. Technology Licensing to Other Operators

**Scenario:** Smaller E&P companies want similar capability

**Opportunity:**
- License MCP server software
- Provide implementation services
- Recurring revenue from support/updates

**Revenue model:**
```
One-time license: $100K-$500K (depending on company size)
Annual support: 20% of license fee ($20K-$100K/year)
Implementation services: $50K-$200K (one-time)

Potential:
- 3-5 operators/year = $500K-$2M initial + $100K-$500K recurring
```

---

### 3. Partnership with Bluware/Other Vendors

**Scenario:** Co-develop commercial product

**Opportunity:**
- Joint product: "Bluware InteractivAI + Claude MCP"
- Revenue share on sales
- Faster development (split costs)

**Business model:**
```
Bluware provides:
- VDS expertise
- Cloud infrastructure
- Sales/marketing

We provide:
- MCP server development
- AI integration expertise
- Customer pilot sites

Revenue share: 50/50 on AI-augmented product sales
```

---

## Security & Governance

### Data Access Control

**Challenge:** Not all users should see all data

**Solution: Role-based access control (RBAC)**

```python
# File: src/mcp_auth.py

class MCPAuthorization:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.permissions = self._load_permissions(user_id)

    def can_access_survey(self, survey_id: str) -> bool:
        """Check if user can access survey"""
        survey = Survey.get(survey_id)

        # Check region permissions
        if survey.region not in self.permissions["regions"]:
            return False

        # Check confidentiality level
        if survey.confidentiality > self.permissions["max_confidentiality"]:
            return False

        # Check data classification
        if survey.classification in self.permissions["blocked_classifications"]:
            return False

        return True

    def filter_search_results(self, results: List[Survey]) -> List[Survey]:
        """Filter survey list based on permissions"""
        return [s for s in results if self.can_access_survey(s.id)]
```

**User groups:**
```
Exploration team:
- Can access: Exploration data (low confidentiality)
- Cannot access: Appraisal/development data

Appraisal team:
- Can access: All data in assigned fields
- Cannot access: Data from other business units

Management:
- Can access: Metadata only (no actual seismic images)
- Purpose: Overview, not detailed interpretation

External (JV partners):
- Can access: Only JV-specific data
- Cannot access: Operator-confidential data
```

---

### Audit Logging

**Requirement:** Track who accessed what data when

```python
# File: src/mcp_audit.py

class AuditLogger:
    def log_access(self, user_id: str, action: str, resource: str, result: str):
        """Log data access for compliance"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,  # "search", "view_inline", "export", etc.
            "resource": resource,  # Survey ID, well ID, etc.
            "result": result,  # "allowed", "denied"
            "ip_address": request.remote_addr,
            "session_id": session.id
        }

        # Write to audit database
        AuditDB.insert(entry)

        # Also send to SIEM system for security monitoring
        SIEM.send(entry)

# Usage in MCP tools:
async def extract_inline_image(survey_id, inline, user_id):
    # Check permissions
    if not auth.can_access_survey(survey_id):
        audit.log_access(user_id, "view_inline", survey_id, "denied")
        raise PermissionError("Access denied")

    # Log successful access
    audit.log_access(user_id, "view_inline", survey_id, "allowed")

    # Proceed with extraction
    ...
```

**Compliance reports:**
- Who accessed confidential data last quarter?
- Which surveys has Partner X viewed?
- Has anyone accessed data outside their region?

---

### Data Classification Integration

**Integrate with corporate data classification:**

```python
# File: src/data_classification.py

class DataClassifier:
    LEVELS = {
        "PUBLIC": 0,           # Public domain (Volve, F3)
        "INTERNAL": 1,         # General internal use
        "CONFIDENTIAL": 2,     # Exploration data
        "RESTRICTED": 3,       # Appraisal/development
        "HIGHLY_RESTRICTED": 4 # Strategic assets
    }

    def classify_survey(self, survey: Survey) -> str:
        """Auto-classify survey based on metadata"""

        # Public domain datasets
        if survey.name in ["Volve", "F3_Netherlands"]:
            return "PUBLIC"

        # Legacy exploration data (>5 years old, no active wells)
        if survey.age_years > 5 and not survey.has_active_wells:
            return "INTERNAL"

        # Active exploration
        if survey.has_active_exploration:
            return "CONFIDENTIAL"

        # Producing fields
        if survey.has_production:
            return "RESTRICTED"

        # Strategic prospects (pre-drill)
        if survey.is_strategic_prospect:
            return "HIGHLY_RESTRICTED"

        # Default: Conservative
        return "RESTRICTED"
```

---

## Roadmap

### Phase 1: Foundation (Complete)
- ✅ OpenVDS MCP Server
- ✅ Search, visualization, basic analysis
- ✅ Elasticsearch metadata
- ✅ Performance optimization (caching)

### Phase 2: Petrel Integration (3-6 months)
- [ ] Read-only Petrel MCP connector
- [ ] Import horizons/faults from Petrel
- [ ] Overlay Petrel interpretations on seismic
- [ ] Basic QC workflows

**Deliverables:**
- Petrel connector supporting 80% of common queries
- Documented API for Petrel data access
- User guide for Petrel + MCP workflows

### Phase 3: OSDU Integration (6-9 months)
- [ ] OSDU MCP connector
- [ ] Search OSDU data lake
- [ ] Retrieve seismic, wells, interpretations from OSDU
- [ ] Unified interface (OSDU + OpenVDS + Petrel)

**Deliverables:**
- OSDU connector for enterprise deployment
- Multi-source search (query across all backends)
- OSDU certification (if pursuing)

### Phase 4: Write Capabilities (9-12 months)
- [ ] Export MCP results to Petrel projects
- [ ] AI-generated interpretations → Petrel import
- [ ] Bi-directional sync (MCP ↔ Petrel)

**Deliverables:**
- Full round-trip workflow
- AI suggests → User refines in Petrel → AI learns
- Feedback loop for AI improvement

### Phase 5: Commercial Deployment (12-18 months)
- [ ] Multi-tenant MCP server (SaaS model)
- [ ] JV partner access (pay-per-use)
- [ ] Vendor partnerships (Bluware, Schlumberger)
- [ ] Marketplace listing (AWS/Azure marketplace)

**Deliverables:**
- Commercial product
- Revenue-generating service
- Industry partnerships

---

## Conclusion

### Key Takeaways

**Third-party integration is:**
1. **Technically feasible** - MCP is designed for this
2. **Strategically valuable** - Unifies data access across tools
3. **Commercially viable** - Multiple revenue opportunities

**Recommended priorities:**
1. **Short-term (3 months):** Petrel read-only connector (high user demand)
2. **Medium-term (6 months):** OSDU integration (if enterprise uses OSDU)
3. **Long-term (12 months):** Commercial partnerships (revenue generation)

**Success metrics:**
- **Adoption:** 50%+ of users leverage Petrel integration
- **Efficiency:** 30%+ time savings vs manual Petrel ↔ seismic workflows
- **Revenue:** $500K-$1M annually from JV/licensing (if pursuing commercial)

**Next steps:**
1. Validate user demand (survey G&G team on Petrel integration priority)
2. Prototype Petrel connector (2-week MVP)
3. Evaluate OSDU relevance (is your company using OSDU?)
4. Explore vendor partnerships (reach out to Bluware, Schlumberger)

---

**Document prepared by:** OpenVDS MCP Server Team
**Date:** 2025-10-22
**Version:** 1.0
**For questions:** Contact project lead

---

## Appendix: MCP Protocol Basics (For Vendors)

**For third-party vendors interested in adding MCP support:**

### Minimal MCP Implementation

```python
# Example: Minimal MCP server in Python (50 lines)

from mcp.server import Server
from mcp.types import Tool, TextContent
import json

# 1. Create server
server = Server("my-tool-connector")

# 2. Define tools
server.add_tool(Tool(
    name="my_tool_function",
    description="What this tool does",
    inputSchema={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "First parameter"}
        },
        "required": ["param1"]
    }
))

# 3. Implement tool handler
@server.list_tools()
async def list_tools():
    return [tool for tool in server.tools]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "my_tool_function":
        result = my_actual_function(arguments["param1"])
        return [TextContent(type="text", text=json.dumps(result))]

# 4. Run server
if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    asyncio.run(stdio_server(server))
```

**That's it! Deploy this, and Claude can call your tools.**

**Resources:**
- MCP Specification: https://spec.modelcontextprotocol.io
- Python SDK: https://github.com/anthropics/mcp-python-sdk
- TypeScript SDK: https://github.com/anthropics/mcp-typescript-sdk
- Examples: https://github.com/anthropics/mcp-examples

**Vendor benefits:**
- Differentiate your product with AI integration
- Attract younger, AI-savvy users
- Reduce support burden (Claude answers basic questions)
- New revenue stream (AI-augmented licenses)

**Let's build the AI-enabled subsurface ecosystem together!**
