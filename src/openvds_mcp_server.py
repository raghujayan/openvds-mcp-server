#!/usr/bin/env python3
"""
OpenVDS MCP Server

An MCP (Model Context Protocol) server that enables AI-assisted access to 
Bluware OpenVDS seismic and volumetric data through natural language queries.
"""

import asyncio
import logging
import base64
from typing import Any, Optional
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    Prompt,
    PromptArgument,
    GetPromptResult,
    PromptMessage,
)
from pydantic import BaseModel, Field, AnyUrl
import json


def detect_image_format(img_bytes: bytes) -> str:
    """Detect image format from magic bytes"""
    if img_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    elif img_bytes[:3] == b'\xff\xd8\xff':
        return "image/jpeg"
    else:
        return "image/png"  # Default to PNG


try:
    from .vds_client import VDSClient
    from .agent_manager import SeismicAgentManager
except ImportError:
    from vds_client import VDSClient
    from agent_manager import SeismicAgentManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openvds-mcp-server")


class OpenVDSMCPServer:
    """MCP Server for OpenVDS data access"""
    
    def __init__(self):
        self.server = Server("openvds-mcp-server")
        self.vds_client: Optional[VDSClient] = None
        self.agent_manager: Optional[SeismicAgentManager] = None
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up MCP protocol handlers"""
        
        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """List available VDS resources (surveys, metadata)"""
            resources = []
            
            if self.vds_client and self.vds_client.is_connected:
                try:
                    surveys = await self.vds_client.list_surveys()
                    for survey in surveys:
                        resources.append(
                            Resource(
                                uri=AnyUrl(f"vds://survey/{survey['id']}"),
                                name=f"Survey: {survey['name']}",
                                description=f"Seismic survey metadata for {survey['name']}",
                                mimeType="application/json"
                            )
                        )
                except Exception as e:
                    logger.error(f"Error listing surveys: {e}")
            
            resources.append(
                Resource(
                    uri=AnyUrl("vds://info/capabilities"),
                    name="VDS Server Capabilities",
                    description="Information about VDS server capabilities and configuration",
                    mimeType="application/json"
                )
            )
            
            return resources
        
        @self.server.read_resource()
        async def read_resource(uri: AnyUrl) -> str:
            """Read a specific VDS resource"""
            uri_str = str(uri)
            logger.info(f"Reading resource: {uri_str}")
            
            if uri_str == "vds://info/capabilities":
                capabilities = {
                    "server_version": "1.0.0",
                    "openvds_version": "3.4.8",
                    "connected": self.vds_client.is_connected if self.vds_client else False,
                    "supported_formats": ["VDS", "SEG-Y (via conversion)"],
                    "supported_operations": [
                        "metadata_query",
                        "inline_extraction",
                        "crossline_extraction",
                        "volume_subsetting",
                        "survey_listing"
                    ]
                }
                return json.dumps(capabilities, indent=2)
            
            if uri_str.startswith("vds://survey/"):
                survey_id = uri_str.replace("vds://survey/", "")
                if self.vds_client:
                    metadata = await self.vds_client.get_survey_metadata(survey_id)
                    return json.dumps(metadata, indent=2)
                else:
                    return json.dumps({"error": "VDS client not connected"})
            
            return json.dumps({"error": f"Unknown resource: {uri}"})
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available VDS data extraction tools"""
            return [
                Tool(
                    name="extract_inline",
                    description="Extract a specific inline slice from a seismic survey",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "survey_id": {
                                "type": "string",
                                "description": "Survey identifier or path to VDS file"
                            },
                            "inline_number": {
                                "type": "integer",
                                "description": "Inline number to extract"
                            },
                            "sample_range": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Optional [start, end] sample range",
                                "minItems": 2,
                                "maxItems": 2
                            }
                        },
                        "required": ["survey_id", "inline_number"]
                    }
                ),
                Tool(
                    name="extract_crossline",
                    description="Extract a specific crossline slice from a seismic survey",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "survey_id": {
                                "type": "string",
                                "description": "Survey identifier or path to VDS file"
                            },
                            "crossline_number": {
                                "type": "integer",
                                "description": "Crossline number to extract"
                            },
                            "sample_range": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Optional [start, end] sample range",
                                "minItems": 2,
                                "maxItems": 2
                            }
                        },
                        "required": ["survey_id", "crossline_number"]
                    }
                ),
                Tool(
                    name="extract_volume_subset",
                    description="Extract a volumetric subset from a seismic survey",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "survey_id": {
                                "type": "string",
                                "description": "Survey identifier or path to VDS file"
                            },
                            "inline_range": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "[start, end] inline range",
                                "minItems": 2,
                                "maxItems": 2
                            },
                            "crossline_range": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "[start, end] crossline range",
                                "minItems": 2,
                                "maxItems": 2
                            },
                            "sample_range": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Optional [start, end] sample range",
                                "minItems": 2,
                                "maxItems": 2
                            }
                        },
                        "required": ["survey_id", "inline_range", "crossline_range"]
                    }
                ),
                Tool(
                    name="get_survey_info",
                    description="Get detailed metadata and statistics for a seismic survey",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "survey_id": {
                                "type": "string",
                                "description": "Survey identifier or path to VDS file"
                            },
                            "include_stats": {
                                "type": "boolean",
                                "description": "Include statistical analysis (min/max/mean amplitudes)",
                                "default": True
                            }
                        },
                        "required": ["survey_id"]
                    }
                ),
                Tool(
                    name="search_surveys",
                    description="Search and explore VDS surveys interactively. Use this for initial discovery and filtering. Returns summary statistics and sample results to help users refine their search.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "search_query": {
                                "type": "string",
                                "description": "Free-text search query (searches file paths, names, regions). Examples: 'Brazil', 'Santos Basin', '2023', 'PSTM'"
                            },
                            "filter_region": {
                                "type": "string",
                                "description": "Filter by region/location in file path"
                            },
                            "filter_year": {
                                "type": "integer",
                                "description": "Filter by year in file path or metadata"
                            },
                            "offset": {
                                "type": "integer",
                                "description": "Offset for pagination (default 0). Use this to get next batch of results.",
                                "default": 0,
                                "minimum": 0
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of results per page (default 20, max 100)",
                                "default": 20,
                                "minimum": 1,
                                "maximum": 100
                            }
                        }
                    }
                ),
                Tool(
                    name="get_survey_stats",
                    description="Get aggregate statistics about available surveys without loading individual records. Use this to understand the dataset before querying.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter_region": {
                                "type": "string",
                                "description": "Optional region filter"
                            },
                            "filter_year": {
                                "type": "integer",
                                "description": "Optional year filter"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_facets",
                    description="Get pre-computed facets (filters) for instant filtering. Returns available regions, years, data types, and counts. MUCH faster than search_surveys for initial exploration.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter_region": {
                                "type": "string",
                                "description": "Pre-filter by region before computing facets"
                            },
                            "filter_year": {
                                "type": "integer",
                                "description": "Pre-filter by year before computing facets"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_cache_stats",
                    description="Get cache performance statistics to understand query performance",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="extract_inline_image",
                    description="Extract a SINGLE inline slice and generate a seismic image visualization. Returns PNG image that Claude can view and analyze for structural features, faults, and data quality. FOR BULK EXTRACTIONS (multiple inlines, ranges, patterns like 'every Nth'), use agent_start_extraction instead.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "survey_id": {
                                "type": "string",
                                "description": "Survey identifier"
                            },
                            "inline_number": {
                                "type": "integer",
                                "description": "Inline number to extract"
                            },
                            "sample_range": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Optional [start, end] sample range",
                                "minItems": 2,
                                "maxItems": 2
                            },
                            "colormap": {
                                "type": "string",
                                "description": "Color scheme: 'seismic' (red-white-blue), 'gray', or 'petrel'",
                                "default": "seismic",
                                "enum": ["seismic", "gray", "petrel"]
                            },
                            "clip_percentile": {
                                "type": "number",
                                "description": "Amplitude clipping percentile (default 99.0)",
                                "default": 99.0,
                                "minimum": 90.0,
                                "maximum": 100.0
                            }
                        },
                        "required": ["survey_id", "inline_number"]
                    }
                ),
                Tool(
                    name="extract_crossline_image",
                    description="Extract a SINGLE crossline slice and generate a seismic image visualization. Returns PNG image for visual analysis. FOR BULK EXTRACTIONS (multiple crosslines, ranges, patterns like 'every Nth', 'skipping 100'), use agent_start_extraction instead.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "survey_id": {
                                "type": "string",
                                "description": "Survey identifier"
                            },
                            "crossline_number": {
                                "type": "integer",
                                "description": "Crossline number to extract"
                            },
                            "sample_range": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Optional [start, end] sample range",
                                "minItems": 2,
                                "maxItems": 2
                            },
                            "colormap": {
                                "type": "string",
                                "description": "Color scheme: 'seismic', 'gray', or 'petrel'",
                                "default": "seismic",
                                "enum": ["seismic", "gray", "petrel"]
                            },
                            "clip_percentile": {
                                "type": "number",
                                "description": "Amplitude clipping percentile (default 99.0)",
                                "default": 99.0,
                                "minimum": 90.0,
                                "maximum": 100.0
                            }
                        },
                        "required": ["survey_id", "crossline_number"]
                    }
                ),
                Tool(
                    name="extract_timeslice_image",
                    description="Extract a time/depth slice (map view) and generate a seismic image visualization. Returns PNG image showing amplitude distribution across the survey area at a specific time/depth.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "survey_id": {
                                "type": "string",
                                "description": "Survey identifier"
                            },
                            "time_value": {
                                "type": "integer",
                                "description": "Time/depth value to extract"
                            },
                            "inline_range": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Optional [start, end] inline range",
                                "minItems": 2,
                                "maxItems": 2
                            },
                            "crossline_range": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Optional [start, end] crossline range",
                                "minItems": 2,
                                "maxItems": 2
                            },
                            "colormap": {
                                "type": "string",
                                "description": "Color scheme: 'seismic', 'gray', or 'petrel'",
                                "default": "seismic",
                                "enum": ["seismic", "gray", "petrel"]
                            },
                            "clip_percentile": {
                                "type": "number",
                                "description": "Amplitude clipping percentile (default 99.0)",
                                "default": 99.0,
                                "minimum": 90.0,
                                "maximum": 100.0
                            }
                        },
                        "required": ["survey_id", "time_value"]
                    }
                ),
                # Agent tools
                Tool(
                    name="agent_start_extraction",
                    description="**USE THIS FOR BULK/MULTIPLE EXTRACTIONS** - Start autonomous extraction from natural language instruction. The agent will parse the instruction and execute extractions in the background (non-blocking). Use this for: multiple slices, ranges, patterns (every Nth, skipping N), or any instruction with 'all', 'every', 'multiple'. Check progress with agent_get_status. Examples: 'Extract all inlines from 51000 to 59000 at 2000 spacing', 'Extract crosslines skipping 100 for QC', 'Extract every 500th inline', 'Extract 3 representative inlines'",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "survey_id": {
                                "type": "string",
                                "description": "VDS survey identifier"
                            },
                            "instruction": {
                                "type": "string",
                                "description": "Natural language extraction instruction"
                            },
                            "auto_execute": {
                                "type": "boolean",
                                "description": "Start execution immediately (default: True)",
                                "default": True
                            }
                        },
                        "required": ["survey_id", "instruction"]
                    }
                ),
                Tool(
                    name="agent_get_status",
                    description="Get status of autonomous agent including progress, state, and current task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Optional session ID (defaults to active session)"
                            }
                        }
                    }
                ),
                Tool(
                    name="agent_pause",
                    description="Pause agent execution. The agent will pause after completing the current task. Use agent_resume to continue.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Optional session ID (defaults to active session)"
                            }
                        }
                    }
                ),
                Tool(
                    name="agent_resume",
                    description="Resume paused agent execution",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Optional session ID (defaults to active session)"
                            }
                        }
                    }
                ),
                Tool(
                    name="agent_get_results",
                    description="Get extraction results from completed or active session. Returns all completed and failed tasks with statistics.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Optional session ID (defaults to active session)"
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent | ImageContent]:
            """Execute a VDS data extraction tool"""
            logger.info(f"Calling tool: {name} with args: {arguments}")

            if not self.vds_client:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "VDS client not initialized"})
                )]

            try:
                if name == "extract_inline":
                    result = await self.vds_client.extract_inline(
                        arguments["survey_id"],
                        arguments["inline_number"],
                        arguments.get("sample_range")
                    )
                elif name == "extract_crossline":
                    result = await self.vds_client.extract_crossline(
                        arguments["survey_id"],
                        arguments["crossline_number"],
                        arguments.get("sample_range")
                    )
                elif name == "extract_volume_subset":
                    result = await self.vds_client.extract_volume_subset(
                        arguments["survey_id"],
                        arguments["inline_range"],
                        arguments["crossline_range"],
                        arguments.get("sample_range")
                    )
                elif name == "get_survey_info":
                    result = await self.vds_client.get_survey_metadata(
                        arguments["survey_id"],
                        arguments.get("include_stats", True)
                    )
                elif name == "search_surveys":
                    search_query = arguments.get("search_query")
                    filter_region = arguments.get("filter_region")
                    filter_year = arguments.get("filter_year")
                    offset = arguments.get("offset", 0)
                    limit = arguments.get("limit", 20)

                    # Get all matching surveys (up to reasonable limit)
                    all_matching = await self.vds_client.search_surveys(
                        search_query=search_query,
                        filter_region=filter_region,
                        filter_year=filter_year,
                        max_results=1000  # Internal limit to prevent ES overload
                    )

                    total_count = len(all_matching)
                    page_surveys = all_matching[offset:offset + limit]

                    result = {
                        "search_query": search_query or "all",
                        "filters": {
                            "region": filter_region,
                            "year": filter_year
                        },
                        "pagination": {
                            "total_results": total_count,
                            "offset": offset,
                            "limit": limit,
                            "returned": len(page_surveys),
                            "has_more": offset + limit < total_count,
                            "next_offset": offset + limit if offset + limit < total_count else None
                        },
                        "surveys": page_surveys,
                        "help": {
                            "next_page": f"To get next page, use offset={offset + limit}" if offset + limit < total_count else "No more results",
                            "refine_search": "Use filter_region or filter_year to narrow results",
                            "get_details": "Use get_survey_info with a specific survey_id for full metadata"
                        }
                    }

                elif name == "get_survey_stats":
                    result = await self.vds_client.get_survey_statistics(
                        filter_region=arguments.get("filter_region"),
                        filter_year=arguments.get("filter_year")
                    )

                elif name == "get_facets":
                    result = await self.vds_client.get_facets(
                        filter_region=arguments.get("filter_region"),
                        filter_year=arguments.get("filter_year")
                    )

                elif name == "get_cache_stats":
                    result = self.vds_client.get_cache_stats()

                elif name == "extract_inline_image":
                    result = await self.vds_client.extract_inline_image(
                        arguments["survey_id"],
                        arguments["inline_number"],
                        arguments.get("sample_range"),
                        arguments.get("colormap", "seismic"),
                        arguments.get("clip_percentile", 99.0)
                    )
                    if "image_data" in result:
                        # Return image as ImageContent along with metadata as TextContent
                        img_bytes = result["image_data"]
                        img_format = detect_image_format(img_bytes)
                        img_base64 = base64.b64encode(img_bytes).decode()
                        # Use data_summary or statistics depending on which exists
                        stats = result.get("statistics") or result.get("data_summary", {})
                        metadata = {
                            "survey_id": result["survey_id"],
                            "inline_number": result["inline_number"],
                            "statistics": stats,
                            "colormap": result["colormap"],
                            "image_size_kb": result["image_size_kb"],
                            "image_format": img_format
                        }
                        return [
                            ImageContent(
                                type="image",
                                data=img_base64,
                                mimeType=img_format
                            ),
                            TextContent(
                                type="text",
                                text=json.dumps(metadata, indent=2)
                            )
                        ]
                    else:
                        # Error case - return text
                        return [TextContent(
                            type="text",
                            text=json.dumps(result, indent=2)
                        )]

                elif name == "extract_crossline_image":
                    result = await self.vds_client.extract_crossline_image(
                        arguments["survey_id"],
                        arguments["crossline_number"],
                        arguments.get("sample_range"),
                        arguments.get("colormap", "seismic"),
                        arguments.get("clip_percentile", 99.0)
                    )
                    if "image_data" in result:
                        # Return image as ImageContent along with metadata as TextContent
                        img_bytes = result["image_data"]
                        img_format = detect_image_format(img_bytes)
                        img_base64 = base64.b64encode(img_bytes).decode()
                        # Use data_summary or statistics depending on which exists
                        stats = result.get("statistics") or result.get("data_summary", {})
                        metadata = {
                            "survey_id": result["survey_id"],
                            "crossline_number": result["crossline_number"],
                            "statistics": stats,
                            "colormap": result["colormap"],
                            "image_size_kb": result["image_size_kb"],
                            "image_format": img_format
                        }
                        return [
                            ImageContent(
                                type="image",
                                data=img_base64,
                                mimeType=img_format
                            ),
                            TextContent(
                                type="text",
                                text=json.dumps(metadata, indent=2)
                            )
                        ]
                    else:
                        # Error case - return text
                        return [TextContent(
                            type="text",
                            text=json.dumps(result, indent=2)
                        )]

                elif name == "extract_timeslice_image":
                    result = await self.vds_client.extract_timeslice_image(
                        arguments["survey_id"],
                        arguments["time_value"],
                        arguments.get("inline_range"),
                        arguments.get("crossline_range"),
                        arguments.get("colormap", "seismic"),
                        arguments.get("clip_percentile", 99.0)
                    )
                    if "image_data" in result:
                        # Return image as ImageContent along with metadata as TextContent
                        img_bytes = result["image_data"]
                        img_format = detect_image_format(img_bytes)
                        img_base64 = base64.b64encode(img_bytes).decode()
                        # Use data_summary or statistics depending on which exists
                        stats = result.get("statistics") or result.get("data_summary", {})
                        metadata = {
                            "survey_id": result["survey_id"],
                            "time_value": result["time_value"],
                            "inline_range": result["inline_range"],
                            "crossline_range": result["crossline_range"],
                            "statistics": stats,
                            "colormap": result["colormap"],
                            "image_size_kb": result["image_size_kb"],
                            "image_format": img_format
                        }
                        return [
                            ImageContent(
                                type="image",
                                data=img_base64,
                                mimeType=img_format
                            ),
                            TextContent(
                                type="text",
                                text=json.dumps(metadata, indent=2)
                            )
                        ]
                    else:
                        # Error case - return text
                        return [TextContent(
                            type="text",
                            text=json.dumps(result, indent=2)
                        )]

                # Agent tools
                elif name == "agent_start_extraction":
                    if not self.agent_manager:
                        return [TextContent(
                            type="text",
                            text=json.dumps({"error": "Agent manager not initialized"})
                        )]
                    result = await self.agent_manager.start_extraction(
                        arguments["survey_id"],
                        arguments["instruction"],
                        arguments.get("auto_execute", True)
                    )

                elif name == "agent_get_status":
                    if not self.agent_manager:
                        return [TextContent(
                            type="text",
                            text=json.dumps({"error": "Agent manager not initialized"})
                        )]
                    result = self.agent_manager.get_status(
                        arguments.get("session_id")
                    )

                elif name == "agent_pause":
                    if not self.agent_manager:
                        return [TextContent(
                            type="text",
                            text=json.dumps({"error": "Agent manager not initialized"})
                        )]
                    result = self.agent_manager.pause_session(
                        arguments.get("session_id")
                    )

                elif name == "agent_resume":
                    if not self.agent_manager:
                        return [TextContent(
                            type="text",
                            text=json.dumps({"error": "Agent manager not initialized"})
                        )]
                    result = self.agent_manager.resume_session(
                        arguments.get("session_id")
                    )

                elif name == "agent_get_results":
                    if not self.agent_manager:
                        return [TextContent(
                            type="text",
                            text=json.dumps({"error": "Agent manager not initialized"})
                        )]
                    result = self.agent_manager.get_results(
                        arguments.get("session_id")
                    )

                else:
                    result = {"error": f"Unknown tool: {name}"}

                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)})
                )]
        
        @self.server.list_prompts()
        async def list_prompts() -> list[Prompt]:
            """List available prompt templates for common geological queries"""
            return [
                Prompt(
                    name="survey_discovery",
                    description="Discover seismic surveys matching specific criteria",
                    arguments=[
                        PromptArgument(
                            name="region",
                            description="Geographic region (e.g., 'Gulf of Mexico', 'North Sea')",
                            required=False
                        ),
                        PromptArgument(
                            name="year",
                            description="Acquisition year or year range",
                            required=False
                        )
                    ]
                ),
                Prompt(
                    name="data_quality_check",
                    description="Analyze data quality for a survey",
                    arguments=[
                        PromptArgument(
                            name="survey_id",
                            description="Survey identifier to analyze",
                            required=True
                        )
                    ]
                ),
                Prompt(
                    name="extract_seismic_section",
                    description="Extract a specific seismic section for analysis",
                    arguments=[
                        PromptArgument(
                            name="survey_id",
                            description="Survey identifier",
                            required=True
                        ),
                        PromptArgument(
                            name="section_type",
                            description="Type of section: 'inline', 'crossline', or 'volume'",
                            required=True
                        ),
                        PromptArgument(
                            name="location",
                            description="Section location (line number or range)",
                            required=True
                        )
                    ]
                ),
                Prompt(
                    name="compare_surveys",
                    description="Compare characteristics between two surveys",
                    arguments=[
                        PromptArgument(
                            name="survey_a",
                            description="First survey identifier",
                            required=True
                        ),
                        PromptArgument(
                            name="survey_b",
                            description="Second survey identifier",
                            required=True
                        )
                    ]
                )
            ]
        
        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
            """Get a specific prompt template with arguments filled in"""
            args = arguments or {}
            
            if name == "survey_discovery":
                region = args.get("region", "any region")
                year = args.get("year", "any year")
                prompt_text = f"""I need to find seismic surveys that match these criteria:
- Region: {region}
- Acquisition year: {year}

Please use the list_available_surveys tool to find matching surveys and provide:
1. A summary of available surveys
2. Key metadata for each (acquisition date, coverage area, data quality indicators)
3. Recommendations on which survey might be most suitable for analysis"""
                
            elif name == "data_quality_check":
                survey_id = args.get("survey_id", "")
                prompt_text = f"""I need a comprehensive data quality analysis for survey: {survey_id}

Please:
1. Use get_survey_info to retrieve metadata and statistics
2. Analyze amplitude distributions, sample ranges, and coverage
3. Identify any potential data quality issues or anomalies
4. Provide recommendations for data usage and any preprocessing needs"""
                
            elif name == "extract_seismic_section":
                survey_id = args.get("survey_id", "")
                section_type = args.get("section_type", "inline")
                location = args.get("location", "")
                prompt_text = f"""I need to extract a {section_type} section from survey: {survey_id}
Location: {location}

Please:
1. First get survey info to understand the data structure
2. Extract the requested section using the appropriate tool
3. Provide statistics about the extracted data (amplitude range, quality indicators)
4. Suggest any useful visualizations or further analysis"""
                
            elif name == "compare_surveys":
                survey_a = args.get("survey_a", "")
                survey_b = args.get("survey_b", "")
                prompt_text = f"""I need to compare these two seismic surveys:
- Survey A: {survey_a}
- Survey B: {survey_b}

Please:
1. Retrieve metadata for both surveys
2. Compare key characteristics (acquisition parameters, coverage, data quality)
3. Identify similarities and differences
4. Assess compatibility for joint analysis or 4D seismic monitoring"""
            
            else:
                prompt_text = f"Unknown prompt: {name}"
            
            return GetPromptResult(
                description=f"Prompt template: {name}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=prompt_text)
                    )
                ]
            )
    
    async def run(self):
        """Run the MCP server"""
        self.vds_client = VDSClient()
        await self.vds_client.initialize()

        # Initialize agent manager
        self.agent_manager = SeismicAgentManager(self.vds_client)
        logger.info("✓ Agent manager initialized and ready")

        logger.info("Starting OpenVDS MCP Server...")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point"""
    server = OpenVDSMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
