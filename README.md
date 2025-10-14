# OpenVDS MCP Server

An MCP (Model Context Protocol) server that enables AI-assisted access to Bluware OpenVDS seismic and volumetric data through natural language queries.

## Overview

This MCP server bridges large-scale volumetric datasets (seismic surveys, geophysical data) with AI systems like Claude, enabling:

- **Natural Language Data Discovery**: Query surveys using plain English
- **Intelligent Data Extraction**: AI-assisted slice and volume extraction
- **Metadata Analysis**: Automated survey statistics and quality assessment
- **Comparative Analysis**: Cross-survey comparisons and temporal monitoring

## Features

### Real OpenVDS Integration ✅
**All data access uses the actual OpenVDS Python API:**
- Real VDS file opening with `openvds.open()`
- Actual metadata extraction using OpenVDS layout descriptors
- Real data extraction using `requestVolumeSubset()` with NumPy arrays
- Calculates statistics from actual seismic amplitude data
- Demo mode only as fallback when no VDS files are available

### MCP Resources
- Survey metadata catalogs (extracted from real VDS files)
- Server capabilities information
- Data structure documentation

### MCP Tools
- `extract_inline`: Extract inline slices from seismic surveys using OpenVDS
- `extract_crossline`: Extract crossline slices using OpenVDS
- `extract_volume_subset`: Extract volumetric subsets using OpenVDS
- `get_survey_info`: Get detailed survey metadata from VDS files
- `list_available_surveys`: List all available surveys with filtering

### MCP Prompts
- `survey_discovery`: Find surveys matching specific criteria
- `data_quality_check`: Analyze data quality for a survey
- `extract_seismic_section`: Extract specific seismic sections
- `compare_surveys`: Compare characteristics between surveys

## Installation

### macOS Users (Recommended: Docker)

**OpenVDS Python wheels are not available for macOS.** The easiest way to run this server on macOS is using Docker:

1. **Install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop)**

2. **Build the Docker image**:
   ```bash
   ./run-docker.sh
   ```

3. **Configure Claude Desktop** - See [DOCKER.md](DOCKER.md) for complete setup instructions

**📖 Full Docker Guide**: [DOCKER.md](DOCKER.md)

### Linux/Windows Users

#### Requirements
- Python 3.11+
- OpenVDS Python SDK (available via pip on Linux/Windows)
- MCP SDK

#### Setup

1. Install dependencies:
```bash
pip install mcp openvds anthropic pydantic aiohttp
```

2. Configure the server in your MCP client settings (e.g., Claude Desktop `config.json`):
```json
{
  "mcpServers": {
    "openvds": {
      "command": "python",
      "args": ["src/openvds_mcp_server.py"],
      "env": {
        "VDS_DATA_PATH": "/path/to/vds/files"
      }
    }
  }
}
```

3. Run the server:
```bash
python src/openvds_mcp_server.py
```

## Usage

### Demo Mode (Fallback Only)
The server runs in demo mode **only when no VDS files are found**. Demo mode returns simulated responses for testing the MCP protocol without real data.

### With Real VDS Files (Production Use)
**To use real OpenVDS data extraction**, set the `VDS_DATA_PATH` environment variable to point to your VDS data directories:
```bash
export VDS_DATA_PATH="/data/seismic:/data/surveys"
python src/openvds_mcp_server.py
```

The server will:
1. Scan all `.vds` files in the specified paths
2. Extract real metadata using OpenVDS layout API
3. Provide actual data extraction with real amplitude statistics
4. Calculate quality metrics from real seismic data

**Note**: Without real VDS files, you can test the MCP protocol but won't get actual seismic data.

### Example Queries

**Discover Surveys:**
```
"Show me all 3D seismic surveys acquired in the Gulf of Mexico after 2023"
```

**Extract Data:**
```
"Extract inline 2500 from the Gulf of Mexico 2023 survey"
```

**Data Quality:**
```
"Analyze the data quality of the North Sea survey and identify any issues"
```

**Compare Surveys:**
```
"Compare the Permian Basin 2022 survey with the Gulf of Mexico 2023 survey"
```

## Architecture

```
OpenVDS MCP Server
├── src/openvds_mcp_server.py  # Main MCP server implementation
├── src/vds_client.py           # OpenVDS integration layer
├── config.json                 # MCP client configuration
└── README.md                   # Documentation
```

## Key Components

### Server Layer (`openvds_mcp_server.py`)
Implements MCP protocol handlers:
- Resource listing and reading
- Tool execution
- Prompt templates

### VDS Client Layer (`vds_client.py`)
Provides OpenVDS integration:
- Survey discovery and metadata extraction
- Data slice extraction
- Statistics and quality analysis
- Demo mode for testing

## Use Cases

- **Data Discovery**: Natural language queries for available seismic surveys
- **Intelligent Extraction**: AI-assisted selection of data slices and volumes
- **Quality Control**: Automated data quality assessments
- **Report Generation**: Automated survey summary reports
- **ML Workflow Integration**: Preparing training datasets for ML models
- **Collaboration**: Natural language interface for non-technical stakeholders

## Security Considerations

- Authentication and authorization for enterprise deployments
- Rate limiting for large data requests
- Secure handling of cloud storage credentials
- Audit trails for data access

## Future Enhancements

- OAuth authentication for enterprise deployments
- Advanced visualization integration
- Batch processing capabilities
- Format conversion tools (SEG-Y, etc.)
- Cloud storage integration (S3, Azure Blob)
- Caching layer for frequently accessed data

## Contributing

This is a proof-of-concept demonstrating MCP integration with geophysical data. Contributions welcome!

## License

MIT License - See LICENSE file for details

## References

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [OpenVDS Documentation](https://osdu.pages.opengroup.org/platform/domain-data-mgmt-services/seismic/open-vds/)
- [Bluware VDS](https://www.bluware.com/)
