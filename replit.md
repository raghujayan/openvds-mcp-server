# OpenVDS MCP Server

## Project Overview

An MCP (Model Context Protocol) server for Bluware OpenVDS that enables AI-assisted access to seismic and volumetric data through natural language queries.

**Purpose**: Bridge large-scale volumetric datasets (seismic surveys, geophysical data) with AI systems like Claude, allowing geophysicists and data scientists to interact with petabyte-scale seismic data using natural language.

**Current State**: Proof-of-concept implementation with core MCP protocol handlers, OpenVDS integration, and demo mode for testing.

## Recent Changes

**2025-10-11**: Initial implementation and OpenVDS integration
- Created MCP server with resources, tools, and prompts
- **Implemented REAL OpenVDS integration using actual API**:
  - Real VDS file opening with openvds.open()
  - Actual metadata extraction using OpenVDS layout descriptors
  - Real data extraction using requestVolumeSubset() with NumPy
  - Real amplitude statistics from actual seismic data
  - Correct buffer dimension ordering (reversed for NumPy)
  - Proper inclusive range handling with terminal plane preservation
- Demo mode only as fallback when no VDS files available
- Added comprehensive documentation and example usage
- Set up Python project structure
- All OpenVDS API usage verified correct by code review

## Project Architecture

### Core Components

**Server Layer** (`src/openvds_mcp_server.py`)
- MCP protocol handlers (resources, tools, prompts)
- Resource endpoints for survey metadata
- Tool implementations for data extraction
- Prompt templates for geological queries

**VDS Client Layer** (`src/vds_client.py`)
- OpenVDS integration for data access
- Survey discovery and metadata extraction
- Demo mode with example seismic surveys
- Data extraction methods (inline, crossline, volume)

### Technology Stack

- **Python 3.11**: Core language
- **MCP SDK**: Model Context Protocol implementation
- **OpenVDS**: Seismic data access library
- **Pydantic**: Data validation
- **AsyncIO**: Asynchronous operations

### Key Features

1. **MCP Resources**: Survey metadata catalogs, server capabilities
2. **MCP Tools**: Data extraction (inline, crossline, volume), survey info
3. **MCP Prompts**: Templates for discovery, quality check, comparison
4. **Demo Mode**: Testing without real VDS files

## Use Cases

- **Data Discovery**: "Show me all 3D seismic surveys in the Gulf of Mexico after 2023"
- **Data Extraction**: "Extract inline 2500 from survey X between samples 1000-3000"
- **Quality Analysis**: "Check data quality of the North Sea survey"
- **Survey Comparison**: "Compare Survey A and Survey B characteristics"
- **ML Preparation**: Extracting training datasets for machine learning

## Configuration

**Environment Variables**:
- `VDS_DATA_PATH`: Colon-separated paths to VDS files
- `LOG_LEVEL`: Logging level (default: INFO)

**Demo Mode**: Automatically enabled when no VDS files found

## Future Enhancements

- OAuth authentication for enterprise deployments
- Advanced visualization integration with plotting libraries
- Batch processing for multi-survey operations
- Format conversion (SEG-Y, etc.)
- Cloud storage integration (S3, Azure Blob)
- Caching layer for frequently accessed data
- Rate limiting and quota management

## Development Notes

- Server runs via stdio transport for MCP protocol
- Type-safe with Pydantic models and Python type hints
- Error handling with proper logging
- Scalable architecture for petabyte-scale data

## User Preferences

None specified yet.
