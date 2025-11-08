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
