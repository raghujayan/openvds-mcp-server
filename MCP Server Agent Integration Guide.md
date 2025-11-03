# MCP Server Agent Integration Guide

## Overview
This guide shows you how to integrate the autonomous agent into your existing OpenVDS MCP server.

## File Structure

```
your_mcp_server/
├── server.py                 # Your main MCP server (MODIFY)
├── openvds_tools.py          # Your existing OpenVDS tools
├── agent_manager.py          # NEW - Agent code from previous artifact
└── requirements.txt          # Update dependencies
```

## Step 1: Add Dependencies

Add to your `requirements.txt`:
```
# Existing dependencies
openvds
numpy
Pillow

# New for agent (if not already present)
python-dateutil
```

## Step 2: Modify Your MCP Server

Update your `server.py` to initialize the agent on startup:

```python
# server.py - UPDATED

from mcp.server import Server
from mcp.server.stdio import stdio_server
from agent_manager import SeismicAgentManager  # NEW IMPORT
import openvds_tools  # Your existing tools

# Initialize MCP server
app = Server("openvds-seismic-server")

# Initialize your existing OpenVDS tools
openvds = openvds_tools.OpenVDSTools()  # However you initialize it

# NEW: Initialize agent manager
agent_manager = SeismicAgentManager(openvds)
print("✓ Agent manager initialized and ready", file=sys.stderr)


# ============================================================================
# EXISTING TOOLS (keep as-is)
# ============================================================================

@app.tool()
async def extract_inline(
    survey_id: str,
    inline_number: int,
    sample_range: list[int] = None
) -> dict:
    """Extract inline slice"""
    return await openvds.extract_inline(survey_id, inline_number, sample_range)

@app.tool()
async def extract_crossline(
    survey_id: str,
    crossline_number: int,
    sample_range: list[int] = None
) -> dict:
    """Extract crossline slice"""
    return await openvds.extract_crossline(survey_id, crossline_number, sample_range)

# ... other existing tools ...


# ============================================================================
# NEW AGENT TOOLS
# ============================================================================

@app.tool()
async def agent_start_extraction(
    survey_id: str,
    instruction: str,
    auto_execute: bool = True
) -> dict:
    """
    Start autonomous extraction from natural language instruction.
    
    The agent will parse the instruction and execute extractions in the background.
    You can check progress with agent_get_status.
    
    Examples:
    - "Extract all inlines from 51000 to 59000 at 2000 spacing, depth 5500-7000m"
    - "Extract crosslines 8300, 8400, 8500, 8600 at depth 5800-6800m"
    - "Extract every 500th inline for QC"
    
    Args:
        survey_id: VDS survey identifier
        instruction: Natural language extraction instruction
        auto_execute: Start execution immediately (default: True)
    
    Returns:
        Session info with extraction plan
    """
    return await agent_manager.start_extraction(survey_id, instruction, auto_execute)


@app.tool()
async def agent_get_status(session_id: str = None) -> dict:
    """
    Get status of autonomous agent.
    
    Args:
        session_id: Optional session ID (defaults to active session)
    
    Returns:
        Current status including progress, state, and current task
    """
    return agent_manager.get_status(session_id)


@app.tool()
async def agent_pause(session_id: str = None) -> dict:
    """
    Pause agent execution.
    
    The agent will pause after completing the current task.
    Use agent_resume to continue.
    """
    return agent_manager.pause_session(session_id)


@app.tool()
async def agent_resume(session_id: str = None) -> dict:
    """Resume paused agent execution."""
    return agent_manager.resume_session(session_id)


@app.tool()
async def agent_get_results(session_id: str = None) -> dict:
    """
    Get extraction results from completed or active session.
    
    Returns:
        All completed and failed tasks with statistics
    """
    return agent_manager.get_results(session_id)


# ============================================================================
# SERVER STARTUP
# ============================================================================

async def main():
    async with stdio_server() as (read_stream, write_stream):
        print("OpenVDS MCP Server with Agent starting...", file=sys.stderr)
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Step 3: Test the Integration

### 3.1 Start your MCP server
```bash
cd your_mcp_server
python server.py
```

You should see:
```
✓ Agent manager initialized and ready
OpenVDS MCP Server with Agent starting...
```

### 3.2 Test from Claude

Now when you talk to Claude (me!), I can use the agent tools:

**You:** "Extract inlines 53000, 55000, and 57000 from the Sepia survey at depth 5500-7000m"

**I'll do:**
```
agent_start_extraction(
    survey_id='0282_BM_S_FASE2_3D_Sepia_Crop_IAI_FS_tol1',
    instruction='Extract inlines 53000, 55000, 57000 at depth 5500-7000m'
)
```

The agent starts working in the background!

**You:** "What's the status?"

**I'll do:**
```
agent_get_status()
```

**Response:**
```json
{
  "state": "running",
  "progress": {
    "total": 3,
    "completed": 1,
    "pending": 2,
    "percent": 33.3
  },
  "current_task": {
    "type": "inline",
    "number": 55000
  }
}
```

## Step 4: Usage Examples

### Example 1: Start Large Extraction and Come Back Later

**You:** "Extract every 1000th inline across the Sepia survey, depth 5000-7500m. I'll check back in an hour."

**Me:** "Starting extraction... The agent will process approximately 8 inlines. I've started the extraction, it will run in the background. Check back anytime!"

[Agent runs autonomously on server]

**You (1 hour later):** "How did the extraction go?"

**Me:** "Let me check... ✓ Complete! Successfully extracted 8 inlines, all tasks completed successfully. Would you like me to analyze the results or extract more sections?"

### Example 2: Monitor Progress

**You:** "Extract crosslines 8200 to 8700 at spacing 100, depth 5800-6800m"

**Me:** [Starts agent] "Extraction started with 6 crosslines..."

**You (5 minutes later):** "Status?"

**Me:** "Currently processing crossline 8400 (3/6 completed, 50% done)"

### Example 3: Pause and Resume

**You:** "Pause the agent, I need to check something"

**Me:** [Pauses] "Agent paused after current task"

**You:** "Resume"

**Me:** "Agent resumed, continuing with remaining tasks"

## Step 5: Advanced Features (Optional)

### 5.1 Add Result Storage

Modify `_execute_single_task` in `agent_manager.py` to save results:

```python
async def _execute_single_task(self, survey_id: str, task: ExtractionTask):
    result = await self.openvds.extract_inline_image(...)
    
    # NEW: Save to disk
    import os
    os.makedirs('./extractions', exist_ok=True)
    
    filename = f"./extractions/{task.type}_{task.number}.png"
    # Save image to disk
    with open(filename, 'wb') as f:
        f.write(result['image_bytes'])
    
    result['saved_path'] = filename
    return result
```

### 5.2 Add Email Notifications

```python
# At end of _execute_tasks
if session.state == AgentState.COMPLETED:
    await self._send_notification(
        f"Extraction complete: {session.completed_count} successful"
    )
```

## Troubleshooting

### Agent not starting?
- Check server logs for errors
- Verify OpenVDS tools are working: `extract_inline` should work first
- Ensure no Python syntax errors in `agent_manager.py`

### Tasks failing?
- Check individual task errors: `agent_get_results()` shows error messages
- Verify inline/crossline numbers are within survey bounds
- Check depth ranges are valid

### Want more detailed logs?
Add to `agent_manager.py`:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

## Next Steps

1. **Pull down the code**: Copy `agent_manager.py` to your MCP server directory
2. **Modify server.py**: Add the agent tools as shown above
3. **Restart server**: `python server.py`
4. **Test with me (Claude)**: I can now control the agent!

Once integrated, you can give me instructions like:
- "Extract 100 random sections for training data"
- "Extract a dense grid around the most interesting features"
- "Run QC extractions on the entire survey overnight"

And the agent will work autonomously while you focus on ML model development!

## Questions?

Let me know if you need help with:
- Specific server setup
- Claude API integration for smarter instruction parsing
- Custom extraction patterns
- Result post-processing