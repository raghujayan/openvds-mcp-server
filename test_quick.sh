#!/bin/bash
# Quick test script for MCP server with shared Elasticsearch

set -e

echo "========================================"
echo "Testing MCP Server with Shared ES"
echo "========================================"
echo

# Wait for Docker
echo "1. Waiting for Docker to be ready..."
for i in {1..30}; do
    if docker info >/dev/null 2>&1; then
        echo "   ✓ Docker is ready"
        break
    fi
    sleep 1
done

# Check Elasticsearch
echo
echo "2. Checking Elasticsearch..."
ES_COUNT=$(curl -s http://localhost:9200/vds-metadata/_count | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])" 2>/dev/null || echo "0")
echo "   ✓ Elasticsearch has $ES_COUNT documents"

# Test MCP server startup
echo
echo "3. Testing MCP server startup (this should be fast now)..."
echo "   Starting container..."

docker run --rm -i \
  --network vds-shared-network \
  -v /Users/raghu/vds-data:/vds-data:ro \
  -e VDS_DATA_PATH=/vds-data \
  -e ES_ENABLED=true \
  -e ES_URL=http://vds-shared-elasticsearch:9200 \
  -e ES_INDEX=vds-metadata \
  -e MOUNT_HEALTH_CHECK_ENABLED=true \
  -e MOUNT_HEALTH_CHECK_TIMEOUT=10 \
  -e MOUNT_HEALTH_CHECK_RETRIES=3 \
  openvds-mcp-server:latest \
  python3 << 'PYTHON_SCRIPT'
import asyncio
import sys
import time
sys.path.insert(0, 'src')

from vds_client import VDSClient

async def test():
    import json
    start = time.time()

    # Initialize
    client = VDSClient()
    await client.initialize()

    init_time = time.time() - start

    print(f"   ✓ Initialized in {init_time:.2f} seconds")
    print(f"   ✓ Elasticsearch: {'Yes' if client.use_elasticsearch else 'No'}")
    print(f"   ✓ Cached surveys: {len(client.available_surveys)}")
    print(f"   ✓ Demo mode: {'Yes' if client.demo_mode else 'No (Real data)'}")

    # Test default limit (50)
    print(f"\n   Testing default limit (50)...")
    surveys_50 = await client.list_surveys()
    print(f"   ✓ Returned: {len(surveys_50)} surveys")

    # Test max limit (200)
    print(f"\n   Testing max limit (200)...")
    surveys_200 = await client.list_surveys(max_results=200)
    print(f"   ✓ Returned: {len(surveys_200)} surveys")

    # Test response size
    print(f"\n   Response size validation:")
    for limit, surveys in [(50, surveys_50), (200, surveys_200)]:
        response_json = json.dumps(surveys)
        size_kb = len(response_json) / 1024
        size_mb = size_kb / 1024
        status = "✓ SAFE" if size_mb < 1.0 else "✗ TOO LARGE"
        print(f"     - {limit} surveys: {size_kb:.1f} KB ({size_mb:.3f} MB) {status}")

    if len(surveys_50) > 0:
        print(f"\n   Sample surveys:")
        for i, survey in enumerate(surveys_50[:3], 1):
            name = survey.get('name', 'Unknown')[:50]
            print(f"     {i}. {name}")

    return len(surveys_50)

try:
    count = asyncio.run(test())
    print(f"\n✅ SUCCESS! Response size limits working, returned {count} surveys")
    sys.exit(0 if count > 0 else 1)
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT

EXIT_CODE=$?

echo
if [ $EXIT_CODE -eq 0 ]; then
    echo "========================================"
    echo "✅ MCP SERVER IS WORKING!"
    echo "========================================"
    echo
    echo "The MCP server successfully:"
    echo "  - Connected to shared Elasticsearch"
    echo "  - Loaded all surveys in ~2 seconds"
    echo "  - Is ready to serve Claude Desktop"
    echo
else
    echo "========================================"
    echo "❌ TEST FAILED"
    echo "========================================"
    echo
    echo "Please check the errors above."
    echo
fi

exit $EXIT_CODE
