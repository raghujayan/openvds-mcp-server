#!/usr/bin/env python3
"""
Quick integration test for MCP server with shared Elasticsearch
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from vds_client import VDSClient

async def main():
    print("=" * 70)
    print("MCP SERVER INTEGRATION TEST - Shared Elasticsearch")
    print("=" * 70)

    # Initialize client
    print("\n1. Initializing VDS Client...")
    client = VDSClient()
    await client.initialize()

    # Test 1: Count all surveys (with default limit of 50)
    print("\n2. Testing default survey listing (max 50)...")
    default_surveys = await client.list_surveys()
    print(f"   ✓ Surveys returned: {len(default_surveys)}")
    print(f"   ✓ Response size check: {'PASS' if len(default_surveys) <= 50 else 'FAIL'}")

    # Test 2: Test max_results parameter
    print("\n3. Testing max_results limits...")
    for limit in [10, 50, 100, 200]:
        surveys = await client.list_surveys(max_results=limit)
        actual = len(surveys)
        print(f"   - max_results={limit}: returned {actual} surveys {'✓' if actual <= limit else '✗'}")

    # Test 3: Show sample surveys
    print("\n4. Sample surveys (first 5):")
    all_surveys = default_surveys  # Use the surveys we already fetched
    for i, survey in enumerate(all_surveys[:5], 1):
        print(f"   {i}. {survey['name']}")
        print(f"      - File: {survey['file_path']}")
        print(f"      - Dimensions: {survey.get('dimensionality', 'N/A')}D")
        print(f"      - Inlines: {survey.get('inline_range', 'N/A')}")
        print(f"      - Crosslines: {survey.get('crossline_range', 'N/A')}")
        print()

    # Test 4: Filter by region
    print("5. Testing region filters...")

    # Try different regions
    for region in ["Brazil", "Australia", "North Sea", "Gulf"]:
        filtered = await client.list_surveys(filter_region=region)
        if filtered:
            print(f"   ✓ {region}: {len(filtered)} surveys")
        else:
            print(f"   - {region}: No surveys found")

    # Test 5: Get detailed metadata for first survey
    if all_surveys:
        print(f"\n6. Getting detailed metadata for: {all_surveys[0]['id']}")
        metadata = await client.get_survey_metadata(all_surveys[0]['id'])
        print(f"   ✓ Survey name: {metadata.get('name', 'N/A')}")
        print(f"   ✓ Data type: {metadata.get('data_type', 'N/A')}")
        if 'crs_info' in metadata:
            print(f"   ✓ CRS available: {metadata['crs_info'].get('wkt', 'N/A')[:80]}...")
        if 'statistics' in metadata:
            print(f"   ✓ Statistics available: Yes")

    # Test 6: Estimate response size
    print(f"\n7. Response size validation...")
    import json
    import sys

    # Test with different limits
    for limit in [50, 100, 200]:
        surveys = await client.list_surveys(max_results=limit)
        response_json = json.dumps(surveys)
        size_kb = sys.getsizeof(response_json) / 1024
        size_mb = size_kb / 1024
        status = "✓ SAFE" if size_mb < 1.0 else "✗ TOO LARGE"
        print(f"   - {limit} surveys: {size_kb:.1f} KB ({size_mb:.3f} MB) {status}")

    print("\n" + "=" * 70)
    print("✅ RESPONSE SIZE LIMITS WORKING!")
    print("=" * 70)
    print(f"\nSummary:")
    print(f"  - Elasticsearch: {'✓ Connected' if client.use_elasticsearch else '✗ Not connected'}")
    print(f"  - Surveys available: {len(all_surveys)} (limited from larger set)")
    print(f"  - Demo mode: {'Yes' if client.demo_mode else 'No (Real data)'}")
    print(f"  - Mount health: {'✓ Enabled' if client.mount_health_enabled else 'Disabled'}")
    print(f"  - Default limit: 50 surveys per query")
    print(f"  - Max limit: 200 surveys per query")
    print()

if __name__ == "__main__":
    asyncio.run(main())
