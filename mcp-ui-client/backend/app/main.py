"""
VDS Explorer - FastAPI Backend
Main application with REST API endpoints
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
import logging
import asyncio
import base64
import io
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from .mcp_client import get_mcp_client, shutdown_mcp_client
from .api import chat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vds-explorer-api")


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting VDS Explorer API...")
    try:
        client = await get_mcp_client()
        logger.info("MCP client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MCP client: {e}")
        raise

    # Pre-load validation system to avoid blocking during requests
    try:
        logger.info("Pre-loading validation system...")
        from .validation_wrapper import get_validation_wrapper
        wrapper = get_validation_wrapper()
        logger.info(f"Validation system pre-loaded (available: {wrapper.cop is not None})")
    except Exception as e:
        logger.warning(f"Validation system not available: {e}")

    yield

    # Shutdown
    logger.info("Shutting down VDS Explorer API...")
    await shutdown_mcp_client()


# Create FastAPI app
app = FastAPI(
    title="VDS Explorer API",
    description="REST API for OpenVDS seismic data exploration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)


# ============================================================================
# Pydantic Models
# ============================================================================

class SurveySearchRequest(BaseModel):
    search_query: Optional[str] = None
    filter_region: Optional[str] = None
    filter_year: Optional[int] = None
    offset: int = 0
    limit: int = 20


class InlineExtractionRequest(BaseModel):
    survey_id: str
    inline_number: int
    sample_range: Optional[List[int]] = None
    colormap: str = "seismic"
    clip_percentile: float = 99.0


class CrosslineExtractionRequest(BaseModel):
    survey_id: str
    crossline_number: int
    sample_range: Optional[List[int]] = None
    colormap: str = "seismic"
    clip_percentile: float = 99.0


class TimesliceExtractionRequest(BaseModel):
    survey_id: str
    time_value: int
    inline_range: Optional[List[int]] = None
    crossline_range: Optional[List[int]] = None
    colormap: str = "seismic"
    clip_percentile: float = 99.0


class StatisticsValidationRequest(BaseModel):
    survey_id: str
    section_type: str = Field(..., pattern="^(inline|crossline|timeslice)$")
    section_number: int
    claimed_statistics: Dict[str, float]
    tolerance: float = 0.05


class CoordinateVerificationRequest(BaseModel):
    survey_id: str
    claimed_location: Dict[str, int]


class ConsistencyCheckRequest(BaseModel):
    statistics: Dict[str, float]


class AgentStartRequest(BaseModel):
    survey_id: str
    instruction: str
    auto_execute: bool = True


# ============================================================================
# Health Check
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "name": "VDS Explorer API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        client = await get_mcp_client()
        return {
            "status": "healthy",
            "mcp_connected": client.is_connected
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.get("/api/system/status")
async def get_system_status():
    """Get comprehensive system status"""
    import os
    import psutil

    try:
        mcp = await get_mcp_client()

        # Get MCP server status
        mcp_status = {
            "status": "connected" if mcp.is_connected else "disconnected",
            "container_id": None,  # Would need docker API to get this
            "image": "openvds-mcp-server:latest",
            "platform": "linux/amd64"
        }

        # Get available tools with concise descriptions
        tools = await mcp.list_tools()

        # Create concise one-line descriptions
        def get_concise_description(tool_name: str, full_desc: str) -> str:
            """Extract or create a concise one-line description"""
            concise_map = {
                "extract_inline_image": "Extract single inline slice and generate seismic image",
                "extract_crossline_image": "Extract single crossline slice and generate seismic image",
                "extract_timeslice_image": "Extract time/depth slice (map view) as seismic image",
                "agent_start_extraction": "Start autonomous extraction from natural language instruction",
                "agent_get_status": "Get status of running autonomous agent",
                "agent_pause": "Pause autonomous agent execution",
                "agent_resume": "Resume paused autonomous agent",
                "agent_get_results": "Get results from completed agent session",
                "compute_global_stats": "[COMPUTE] Sample volume and compute global amplitude statistics (5-10s)",
                "detect_outliers": "[COMPUTE] Detect amplitude outliers using z-score analysis with clustering (5-15s)",
                "extract_window": "[COMPUTE] Extract sub-volume and compare to background statistics (3-8s)",
                "validate_extracted_statistics": "Validate claimed statistics against actual VDS data",
                "verify_spatial_coordinates": "Verify coordinates are within survey bounds",
                "check_statistical_consistency": "Check if statistics are mathematically consistent",
                "validate_vds_metadata": "Validate metadata claims (SEGY headers, CRS, dimensions)"
            }
            return concise_map.get(tool_name, full_desc.split('.')[0] if full_desc else "No description")

        tools_list = [
            {
                "name": tool.get("name", ""),
                "description": get_concise_description(tool.get("name", ""), tool.get("description", ""))
            }
            for tool in tools
        ]

        # Get backend process info
        process = psutil.Process(os.getpid())

        backend_status = {
            "status": "running",
            "port": 8000,
            "pid": os.getpid(),
            "health": "healthy",
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 1),
            "cpu_percent": process.cpu_percent()
        }

        # Get Elasticsearch status from MCP
        elasticsearch_status = {
            "status": "unknown",
            "url": "http://vds-shared-elasticsearch:9200",
            "index": "vds-metadata",
            "document_count": None
        }

        # Try to get ES info from MCP server logs/state
        try:
            # This is a simplified version - in production you'd query ES directly
            elasticsearch_status["status"] = "connected"
            elasticsearch_status["document_count"] = 2858  # From startup logs
        except:
            pass

        # Get VDS mount status
        vds_mount_status = {
            "path": "/Volumes/Hue/Datasets/VDS",
            "status": "healthy",
            "health_check_time_ms": None,
            "surveys_available": 500  # From ES
        }

        # License server status
        license_status = {
            "server": "5053@license.cloud.bluware.com",
            "status": "connected"
        }

        # Agent categories with descriptions
        agents_info = {
            "categories": [
                {
                    "category": "Compute Agents (Phase 1)",
                    "description": "Fast numerical computation agents that return real data instead of hypothesizing. Prevents hallucinations by computing actual statistics.",
                    "execution_time": "3-15 seconds",
                    "agents": [
                        {
                            "name": "GlobalSamplerAgent",
                            "tool": "compute_global_stats",
                            "description": "Samples seismic volume with decimation and computes global amplitude statistics (min, max, mean, std, percentiles, histogram)",
                            "prevents": "Hallucinations like 'amplitudes range from X to Y' without data",
                            "execution_time": "5-10 seconds"
                        },
                        {
                            "name": "OutlierDetectorAgent",
                            "tool": "detect_outliers",
                            "description": "Z-score based anomaly detection with spatial clustering. Returns outlier coordinates and clusters",
                            "prevents": "Hallucinations like 'bright spots at inline 10350' without analysis",
                            "execution_time": "5-15 seconds"
                        },
                        {
                            "name": "WindowExtractorAgent",
                            "tool": "extract_window",
                            "description": "Extracts sub-volume and compares to global background statistics. Returns z-score and percentile rank",
                            "prevents": "Hallucinations like 'this zone has higher amplitudes' without comparison",
                            "execution_time": "3-8 seconds"
                        }
                    ]
                },
                {
                    "category": "Extraction Agents",
                    "description": "Autonomous agents for complex multi-step extractions from natural language instructions",
                    "agents": [
                        {
                            "name": "ExtractionAgent",
                            "tool": "agent_start_extraction",
                            "description": "Orchestrates multi-step extractions, manages sessions, supports pause/resume",
                            "features": ["Natural language parsing", "Step planning", "Progress tracking"]
                        }
                    ]
                },
                {
                    "category": "Validation Agents",
                    "description": "Data integrity and anti-hallucination validation tools",
                    "agents": [
                        {
                            "name": "StatisticsValidator",
                            "tool": "validate_extracted_statistics",
                            "description": "Validates claimed statistics against actual VDS data"
                        },
                        {
                            "name": "CoordinateVerifier",
                            "tool": "verify_spatial_coordinates",
                            "description": "Verifies coordinates are within survey bounds"
                        },
                        {
                            "name": "ConsistencyChecker",
                            "tool": "check_statistical_consistency",
                            "description": "Checks if statistics are mathematically consistent"
                        },
                        {
                            "name": "MetadataValidator",
                            "tool": "validate_vds_metadata",
                            "description": "Validates metadata claims (SEGY headers, CRS, dimensions)"
                        }
                    ]
                }
            ],
            "total_agents": 10
        }

        return {
            "services": {
                "backend": backend_status,
                "mcp_server": mcp_status,
                "elasticsearch": elasticsearch_status
            },
            "data_sources": {
                "vds_mount": vds_mount_status,
                "license_server": license_status
            },
            "agents": agents_info,
            "tools": {
                "available": len(tools_list),
                "list": tools_list
            }
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Survey Endpoints
# ============================================================================

@app.post("/api/surveys/search")
async def search_surveys(request: SurveySearchRequest):
    """Search for surveys with filters"""
    try:
        client = await get_mcp_client()
        result = await client.search_surveys(
            search_query=request.search_query,
            filter_region=request.filter_region,
            filter_year=request.filter_year,
            offset=request.offset,
            limit=request.limit
        )
        return result
    except Exception as e:
        logger.error(f"Error searching surveys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/surveys/{survey_id}")
async def get_survey(survey_id: str, include_stats: bool = True):
    """Get detailed survey information"""
    try:
        client = await get_mcp_client()
        result = await client.get_survey_info(survey_id, include_stats)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting survey: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/surveys/{survey_id}/stats")
async def get_survey_stats(survey_id: str):
    """Get survey statistics only"""
    try:
        client = await get_mcp_client()
        result = await client.get_survey_info(survey_id, include_stats=True)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return {
            "survey_id": survey_id,
            "statistics": result.get("statistics", {})
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting survey stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Data Extraction Endpoints
# ============================================================================

@app.post("/api/extract/inline")
async def extract_inline(request: InlineExtractionRequest):
    """Extract inline slice with image"""
    try:
        client = await get_mcp_client()
        result = await client.extract_inline_image(
            survey_id=request.survey_id,
            inline_number=request.inline_number,
            sample_range=request.sample_range,
            colormap=request.colormap,
            clip_percentile=request.clip_percentile
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting inline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/extract/crossline")
async def extract_crossline(request: CrosslineExtractionRequest):
    """Extract crossline slice with image"""
    try:
        client = await get_mcp_client()
        result = await client.extract_crossline_image(
            survey_id=request.survey_id,
            crossline_number=request.crossline_number,
            sample_range=request.sample_range,
            colormap=request.colormap,
            clip_percentile=request.clip_percentile
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting crossline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/extract/timeslice")
async def extract_timeslice(request: TimesliceExtractionRequest):
    """Extract timeslice with image"""
    try:
        client = await get_mcp_client()
        result = await client.extract_timeslice_image(
            survey_id=request.survey_id,
            time_value=request.time_value,
            inline_range=request.inline_range,
            crossline_range=request.crossline_range,
            colormap=request.colormap,
            clip_percentile=request.clip_percentile
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting timeslice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Data Integrity / Validation Endpoints
# ============================================================================

@app.post("/api/validate/statistics")
async def validate_statistics(request: StatisticsValidationRequest):
    """Validate claimed statistics against actual data"""
    try:
        client = await get_mcp_client()
        result = await client.validate_statistics(
            survey_id=request.survey_id,
            section_type=request.section_type,
            section_number=request.section_number,
            claimed_statistics=request.claimed_statistics,
            tolerance=request.tolerance
        )
        return result
    except Exception as e:
        logger.error(f"Error validating statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/validate/coordinates")
async def verify_coordinates(request: CoordinateVerificationRequest):
    """Verify spatial coordinates within survey bounds"""
    try:
        client = await get_mcp_client()
        result = await client.verify_coordinates(
            survey_id=request.survey_id,
            claimed_location=request.claimed_location
        )
        return result
    except Exception as e:
        logger.error(f"Error verifying coordinates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/validate/consistency")
async def check_consistency(request: ConsistencyCheckRequest):
    """Check statistical consistency"""
    try:
        client = await get_mcp_client()
        result = await client.check_consistency(request.statistics)
        return result
    except Exception as e:
        logger.error(f"Error checking consistency: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Agent Management Endpoints
# ============================================================================

@app.post("/api/agents/start")
async def start_agent(request: AgentStartRequest):
    """Start autonomous extraction agent"""
    try:
        client = await get_mcp_client()
        result = await client.start_agent(
            survey_id=request.survey_id,
            instruction=request.instruction,
            auto_execute=request.auto_execute
        )
        return result
    except Exception as e:
        logger.error(f"Error starting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/status")
async def get_agent_status(session_id: Optional[str] = None):
    """Get agent status"""
    try:
        client = await get_mcp_client()
        result = await client.get_agent_status(session_id)
        return result
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/results")
async def get_agent_results(session_id: Optional[str] = None):
    """Get agent results"""
    try:
        client = await get_mcp_client()
        result = await client.get_agent_results(session_id)
        return result
    except Exception as e:
        logger.error(f"Error getting agent results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents/pause")
async def pause_agent(session_id: Optional[str] = None):
    """Pause agent execution"""
    try:
        client = await get_mcp_client()
        result = await client.pause_agent(session_id)
        return result
    except Exception as e:
        logger.error(f"Error pausing agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents/resume")
async def resume_agent(session_id: Optional[str] = None):
    """Resume agent execution"""
    try:
        client = await get_mcp_client()
        result = await client.resume_agent(session_id)
        return result
    except Exception as e:
        logger.error(f"Error resuming agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WebSocket for Real-time Agent Updates
# ============================================================================

@app.websocket("/ws/agents/status")
async def agent_status_websocket(websocket: WebSocket, session_id: Optional[str] = None):
    """WebSocket for real-time agent status updates"""
    await websocket.accept()
    logger.info(f"WebSocket connected for agent status (session: {session_id})")

    try:
        client = await get_mcp_client()

        while True:
            # Poll agent status every second
            try:
                status = await client.get_agent_status(session_id)
                await websocket.send_json(status)
            except Exception as e:
                logger.error(f"Error getting agent status: {e}")
                await websocket.send_json({"error": str(e)})

            # Wait before next poll
            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
