# OpenVDS MCP Server - Example Usage

## Getting Started

The OpenVDS MCP server enables AI systems to interact with seismic data using natural language. Here are practical examples of how to use it with Claude or other MCP-compatible AI systems.

## Example 1: Survey Discovery

**User Query:**
```
"I'm looking for seismic surveys in the Gulf of Mexico acquired after 2023. 
What's available?"
```

**AI Response Flow:**
1. Uses the `list_available_surveys` tool with region and year filters
2. Retrieves matching surveys
3. Presents results in natural language with key metadata

**Expected Output:**
```
I found 1 survey matching your criteria:

Gulf of Mexico 3D Survey 2023
- Acquisition Date: June 15, 2023
- Coverage: Inlines 1000-2500, Crosslines 500-1800
- Sample Range: 0-4000 (4ms interval)
- Data Type: 3D Seismic
- Estimated Size: 12.5 GB

This survey has excellent coverage with 98.7% complete traces 
and a signal-to-noise ratio of 8.5.
```

## Example 2: Data Extraction

**User Query:**
```
"Extract inline 2500 from the Gulf of Mexico 2023 survey between 
samples 1000-3000"
```

**AI Response Flow:**
1. Validates inline number is within survey range
2. Uses `extract_inline` tool
3. Returns extraction results with statistics

**Expected Output:**
```
Successfully extracted inline 2500:

Dimensions:
- Crosslines: 1,300 traces
- Samples: 2,000 points
- Amplitude Range: -850 to 920
- Mean Amplitude: 12.3

The data shows good quality with no null traces. 
Ready for visualization or further analysis.
```

## Example 3: Data Quality Assessment

**User Query:**
```
"Check the data quality of the North Sea Prospect 4D Monitor survey"
```

**AI Response Flow:**
1. Uses `get_survey_info` with statistics enabled
2. Analyzes quality indicators
3. Provides comprehensive assessment

**Expected Output:**
```
Data Quality Assessment for North Sea Prospect 4D Monitor:

Survey Metadata:
- Acquisition: March 20, 2024
- Coverage: 1,100 inlines × 1,100 crosslines
- Total Traces: 1,210,000

Quality Indicators:
✓ Signal-to-Noise Ratio: 8.5 (Excellent)
✓ Coverage: 98.7% (Very Good)
✓ Null Traces: 0.3% (Excellent)

Amplitude Statistics:
- Range: -1000 to 1000
- Mean: 0.5
- RMS: 250.3

Recommendation: This dataset is high quality and suitable 
for detailed interpretation and 4D analysis.
```

## Example 4: Volume Extraction

**User Query:**
```
"I need a subset of the Permian Basin survey: 
inlines 1500-1700, crosslines 1000-1200"
```

**AI Response Flow:**
1. Validates ranges against survey bounds
2. Uses `extract_volume_subset` tool
3. Calculates volume statistics and size

**Expected Output:**
```
Volume Subset Extracted:

Dimensions:
- Inlines: 200 (1500-1700)
- Crosslines: 200 (1000-1200)  
- Samples: 5,000
- Total Traces: 40,000

Volume Statistics:
- Estimated Size: 381.47 MB
- Amplitude Range: -920 to 1050
- Mean Amplitude: 15.2

This subset contains approximately 381 MB of data 
and is ready for export or analysis.
```

## Example 5: Survey Comparison

**User Query:**
```
"Compare the Gulf of Mexico 2023 survey with the Permian Basin 2022 survey"
```

**AI Response Flow:**
1. Retrieves metadata for both surveys
2. Uses `get_survey_info` for each
3. Compares key characteristics

**Expected Output:**
```
Survey Comparison:

Gulf of Mexico 2023:
- Coverage: 1,500 × 1,300 (1.95M traces)
- Sample Interval: 4ms
- Data Size: 12.5 GB
- SNR: 8.5

Permian Basin 2022:
- Coverage: 1,800 × 1,600 (2.88M traces)
- Sample Interval: 4ms  
- Data Size: ~18 GB (estimated)
- SNR: Similar range expected

Key Differences:
- Permian Basin has 48% more traces
- Same sample interval (compatible for processing)
- Different geological settings (offshore vs onshore)

Recommendation: These surveys are compatible for 
separate analysis but not suitable for direct 4D 
comparison due to different locations.
```

## Example 6: Using Prompt Templates

**Using the `data_quality_check` prompt:**
```
Prompt: data_quality_check
Arguments:
  survey_id: demo_north_sea_2024
```

**AI automatically performs:**
1. Retrieves survey metadata
2. Analyzes statistics
3. Identifies quality issues
4. Provides recommendations

**Output:**
```
Comprehensive Data Quality Analysis:

[Detailed quality report with recommendations]
```

## Example 7: Automated Workflows

**Complex Multi-Step Query:**
```
"I need to prepare a dataset for machine learning. Find the best quality 
survey in the Gulf of Mexico, extract a representative volume, and tell 
me about the amplitude characteristics."
```

**AI Response Flow:**
1. Lists Gulf of Mexico surveys
2. Compares quality indicators
3. Selects best quality survey
4. Extracts representative volume
5. Analyzes amplitude distribution
6. Provides ML preparation recommendations

## Tips for Effective Use

### 1. Be Specific
- Specify exact inline/crossline numbers
- Include sample ranges when needed
- Mention regions and dates for filtering

### 2. Start Broad, Then Narrow
```
1. "What surveys are available?"
2. "Tell me about the Gulf of Mexico 2023 survey"
3. "Extract inline 2000 from that survey"
```

### 3. Use Natural Language
The AI understands geological terminology:
- "inline", "crossline", "sample", "trace"
- "amplitude", "signal-to-noise ratio", "coverage"
- "3D seismic", "4D monitor", "time-lapse"

### 4. Leverage Prompts
Use built-in prompts for common tasks:
- `survey_discovery` - Find surveys
- `data_quality_check` - Assess quality
- `extract_seismic_section` - Get data
- `compare_surveys` - Compare datasets

## Integration with AI Tools

### Claude Desktop
Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "openvds": {
      "command": "python",
      "args": ["src/openvds_mcp_server.py"]
    }
  }
}
```

### Custom Applications
Use the MCP Python SDK to integrate with your applications:
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["src/openvds_mcp_server.py"]
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        # Use MCP tools and resources
```

## Demo Mode

When no VDS files are available, the server runs in demo mode with example data:
- Gulf of Mexico 2023 survey
- North Sea 2024 survey  
- Permian Basin 2022 survey

This allows you to test and understand the capabilities before connecting to real data.
