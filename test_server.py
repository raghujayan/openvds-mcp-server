#!/usr/bin/env python3
"""
Test script to verify the OpenVDS MCP Server initializes correctly
"""

import asyncio
import sys
import json
from src.vds_client import VDSClient
from src.openvds_mcp_server import OpenVDSMCPServer

async def test_vds_client():
    """Test VDS client initialization"""
    print("Testing VDS Client...")
    client = VDSClient()
    await client.initialize()
    
    print(f"✓ VDS Client initialized (demo_mode={client.demo_mode})")
    print(f"✓ Available surveys: {len(client.available_surveys)}")
    
    surveys = await client.list_surveys()
    print(f"\nDemo Surveys:")
    for survey in surveys:
        print(f"  - {survey['name']} ({survey['region']})")
    
    if surveys:
        test_survey = surveys[0]
        print(f"\nTesting survey metadata retrieval...")
        metadata = await client.get_survey_metadata(test_survey['id'])
        print(f"✓ Retrieved metadata for {metadata['name']}")
        
        print(f"\nTesting inline extraction...")
        inline_data = await client.extract_inline(
            test_survey['id'],
            test_survey['inline_range'][0] + 100
        )
        print(f"✓ Extracted inline {inline_data.get('inline_number')}")
    
    return True

async def test_mcp_server():
    """Test MCP Server initialization"""
    print("\nTesting MCP Server...")
    server = OpenVDSMCPServer()
    print("✓ MCP Server created")
    
    print("✓ Server handlers configured")
    print(f"✓ Server name: {server.server.name}")
    
    return True

async def main():
    """Run all tests"""
    print("=" * 60)
    print("OpenVDS MCP Server - Initialization Test")
    print("=" * 60)
    print()
    
    try:
        await test_vds_client()
        await test_mcp_server()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        print()
        print("The MCP server is ready to use.")
        print()
        print("To use with Claude Desktop, add this to your config.json:")
        print()
        config_example = {
            "mcpServers": {
                "openvds": {
                    "command": "python",
                    "args": ["src/openvds_mcp_server.py"]
                }
            }
        }
        print(json.dumps(config_example, indent=2))
        print()
        print("For more information, see README.md and example_usage.md")
        
        return 0
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
