# Implementation Plan: Elasticsearch Integration + Enhanced Mount Checking

## Overview
This plan integrates the MCP server with Elasticsearch for scalable VDS metadata access, plus adds robust VPN/NFS mount health checking.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Claude Desktop (macOS)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │ MCP Protocol (stdio)
┌────────────────────────────▼────────────────────────────────────┐
│              OpenVDS MCP Server (Docker Container)              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ VDS Client with Elasticsearch Integration                │  │
│  │  - Mount health checking (with VPN awareness)            │  │
│  │  - Elasticsearch client for metadata queries             │  │
│  │  - Direct VDS access for data extraction                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │           │                          │
│                          │           └─────────────┐            │
└──────────────────────────┼───────────────────────┐ │            │
                           │                       │ │            │
    ┌──────────────────────▼─────┐    ┌──────────▼─▼───────┐    │
    │  Elasticsearch Container   │    │  VDS Data Volume   │    │
    │  - vds-metadata index      │    │  /vds-data (NFS)   │    │
    │  - Real-time queries       │    │  with health check │    │
    └────────────────────────────┘    └────────────────────┘    │
```

## Phase 1: Mount Health Validation

### 1.1 Create Mount Health Checker Module (`src/mount_health.py`)
- Check if mount path exists
- Validate read access with timeout
- Detect stale NFS mounts (common after VPN disconnect)
- Retry logic with exponential backoff
- Clear error messages for troubleshooting

### 1.2 Integration Points
- Call health check during VDSClient initialization
- Periodic health checks (every 5 minutes)
- On-demand health check before VDS file access
- Graceful degradation if mount becomes unavailable

## Phase 2: Elasticsearch Integration

### 2.1 Update docker-compose.yml
- Add Elasticsearch service (single-node development mode)
- Network configuration for inter-service communication
- Volume for Elasticsearch data persistence
- Environment variables for Elasticsearch connection

### 2.2 Create Elasticsearch Metadata Client (`src/es_metadata_client.py`)
- Async Elasticsearch client
- Query interface matching VDSClient methods
- Connection health checking
- Fallback to direct scanning if ES unavailable

### 2.3 Update VDS Client (`src/vds_client.py`)
- Priority: Try Elasticsearch metadata first
- Fallback: Scan VDS files directly if ES unavailable
- Lazy loading: Only open VDS handles for data extraction
- Cache VDS handles after first access

## Phase 3: Implementation Details

### 3.1 Mount Health Checker (`src/mount_health.py`)

```python
class MountHealthChecker:
    async def check_mount_health(path: str) -> MountHealthStatus:
        - Test path.exists()
        - Try reading a test file with timeout
        - Check for stale NFS indicators
        - Return detailed status

    async def wait_for_mount_ready(path: str, max_retries: int) -> bool:
        - Exponential backoff retry logic
        - Log each attempt for debugging
        - Return success/failure
```

### 3.2 Elasticsearch Metadata Client (`src/es_metadata_client.py`)

```python
class ESMetadataClient:
    async def initialize(es_url: str) -> bool:
        - Connect to Elasticsearch
        - Verify vds-metadata index exists
        - Return connection status

    async def list_surveys(filter_region, filter_year) -> List[Dict]:
        - Query ES with filters
        - Return metadata without opening VDS files

    async def get_survey_metadata(survey_id: str) -> Dict:
        - Query ES for specific survey
        - Return complete metadata
```

### 3.3 Updated VDS Client Flow

```python
class VDSClient:
    async def initialize():
        1. Check mount health
        2. Try connecting to Elasticsearch
        3. If ES available: Use ES for metadata
        4. If ES unavailable: Fall back to direct scan
        5. Set operational mode flags

    async def list_surveys():
        1. If ES available: Query ES
        2. Else: Use direct scan results

    async def extract_inline():
        1. Get metadata (from ES or cache)
        2. Validate mount health
        3. Open VDS file handle (lazy)
        4. Extract data
        5. Cache handle for reuse
```

## Phase 4: Configuration

### 4.1 Environment Variables
```bash
# Elasticsearch connection
ES_ENABLED=true
ES_URL=http://elasticsearch:9200
ES_INDEX=vds-metadata

# Mount health checking
MOUNT_HEALTH_CHECK_ENABLED=true
MOUNT_HEALTH_CHECK_INTERVAL=300  # seconds
MOUNT_HEALTH_CHECK_TIMEOUT=10    # seconds
MOUNT_HEALTH_CHECK_RETRIES=3

# VDS data paths
VDS_DATA_PATH=/vds-data/Howard_New:/vds-data/Howard_Old
```

### 4.2 docker-compose.yml Structure
```yaml
services:
  openvds-mcp:
    # existing config
    depends_on:
      - elasticsearch
    environment:
      - ES_ENABLED=true
      - ES_URL=http://elasticsearch:9200
      - MOUNT_HEALTH_CHECK_ENABLED=true

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - es-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

volumes:
  es-data:
```

## Phase 5: Testing Strategy

### 5.1 Mount Health Testing
- Test with valid mount
- Test with disconnected VPN
- Test with stale mount
- Test retry logic
- Test timeout handling

### 5.2 Elasticsearch Integration Testing
- Test with ES available
- Test with ES unavailable (fallback)
- Test metadata queries
- Test performance improvements

### 5.3 Integration Testing
- Full workflow test
- VPN disconnect/reconnect scenario
- ES failure recovery
- Data extraction after metadata query

## Phase 6: Migration Path

### 6.1 Populate Elasticsearch Index
```bash
# Run the vds-metadata-crawler to populate ES
cd ../vds-metadata-crawler
python vds_crawler.py \
  --root-path /Users/raghu/vds-data \
  --es-hosts localhost:9200 \
  --skip-checksum \
  --skip-existing
```

### 6.2 Incremental Updates
- Run crawler periodically (daily/weekly)
- Use --skip-existing flag
- Consider automation with cron or systemd timer

## Success Criteria

1. **Mount Health**: System detects and reports mount issues clearly
2. **Scalability**: Can handle 100+ VDS files without slow startup
3. **Resilience**: Graceful degradation when ES or mount unavailable
4. **Performance**: Metadata queries < 100ms (vs. multiple seconds)
5. **Reliability**: VPN reconnect doesn't break the server

## Timeline

- Phase 1 (Mount Health): 1-2 hours
- Phase 2 (ES Integration): 2-3 hours
- Phase 3 (Integration): 1-2 hours
- Phase 4 (Testing): 1 hour
- **Total**: ~5-8 hours

## Rollback Plan

If issues arise:
1. Set `ES_ENABLED=false` to disable Elasticsearch
2. System falls back to direct VDS scanning
3. Mount health checking remains active
4. No data loss or corruption risk
