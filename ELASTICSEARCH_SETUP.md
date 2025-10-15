# Elasticsearch Integration Setup Guide

## Overview

The OpenVDS MCP Server now supports Elasticsearch integration for fast metadata queries across hundreds of VDS datasets. This eliminates the need to open every VDS file on startup.

## Features

1. **Mount Health Checking**: Detects stale NFS mounts after VPN reconnect
2. **Elasticsearch Metadata**: Fast queries without opening VDS files
3. **Graceful Fallback**: Works without Elasticsearch (falls back to direct scanning)
4. **Scalable**: Handles 100+ VDS files efficiently

## Architecture

```
MCP Server → Elasticsearch (metadata queries)
           ↓
         VDS Files (data extraction only)
```

## Setup Instructions

### Step 1: Start Services with Elasticsearch

```bash
# Start both MCP server and Elasticsearch
docker-compose up -d

# Check logs
docker-compose logs -f openvds-mcp
```

The MCP server will start but Elasticsearch will be empty. You'll see:
```
Elasticsearch index 'vds-metadata' does not exist
Falling back to direct VDS scanning
```

### Step 2: Populate Elasticsearch Index

Use the vds-metadata-crawler to index your VDS files:

```bash
cd ../vds-metadata-crawler

# Run crawler to populate ES
python vds_crawler.py \
  --root-path /Users/raghu/vds-data \
  --es-hosts localhost:9200 \
  --skip-checksum \
  --skip-existing

# This will:
# - Scan all VDS files
# - Extract metadata using OpenVDS
# - Index into Elasticsearch
# - Save progress for resuming
```

**First run options:**
```bash
# Full scan (slow but complete)
python vds_crawler.py \
  --root-path /Users/raghu/vds-data \
  --es-hosts localhost:9200 \
  --skip-checksum

# Resume interrupted scan
python vds_crawler.py \
  --root-path /Users/raghu/vds-data \
  --es-hosts localhost:9200 \
  --skip-checksum \
  --resume
```

**Incremental updates (for new VDS files):**
```bash
# Only index new files not already in ES
python vds_crawler.py \
  --root-path /Users/raghu/vds-data \
  --es-hosts localhost:9200 \
  --skip-checksum \
  --skip-existing
```

### Step 3: Restart MCP Server

```bash
# Restart to pick up Elasticsearch data
docker-compose restart openvds-mcp

# You should see:
# ✓ Elasticsearch connected - using fast metadata queries
# Loaded N surveys from Elasticsearch
```

## Configuration

### Environment Variables

Configure via docker-compose.yml:

```yaml
environment:
  # Elasticsearch
  - ES_ENABLED=true                    # Enable/disable ES integration
  - ES_URL=http://elasticsearch:9200   # ES connection URL
  - ES_INDEX=vds-metadata              # ES index name

  # Mount Health Checking
  - MOUNT_HEALTH_CHECK_ENABLED=true    # Enable/disable mount checking
  - MOUNT_HEALTH_CHECK_TIMEOUT=10      # Timeout in seconds
  - MOUNT_HEALTH_CHECK_RETRIES=3       # Number of retries
```

### Disabling Elasticsearch

To run without Elasticsearch (direct VDS scanning):

```yaml
environment:
  - ES_ENABLED=false
```

Or just start the MCP server alone:
```bash
docker-compose up openvds-mcp
```

## Operational Modes

The MCP server operates in different modes based on configuration:

### Mode 1: Elasticsearch + Mount Health (Recommended)
- Fast metadata queries from ES
- Mount health validation
- Best for production with many VDS files

**Startup time:** < 5 seconds (regardless of VDS file count)

### Mode 2: Direct VDS Scanning + Mount Health
- Scans VDS files on startup
- Mount health validation
- Use when ES unavailable

**Startup time:** ~1-2 seconds per VDS file

### Mode 3: Demo Mode
- Uses synthetic demo data
- No real VDS files needed
- For testing/development

## Mount Health Checking

The system now validates NFS mount health and detects stale mounts:

### Healthy Mount
```
✓ Mount /vds-data/Howard_New: HEALTHY (45.2ms)
✓ Mount /vds-data/Howard_Old: HEALTHY (52.1ms)
```

### Stale Mount (VPN Disconnected)
```
✗ Mount /vds-data/Howard_New: STALE - Mount check timed out after 10s
  Remediation:
  STALE NFS MOUNT DETECTED - This typically happens when VPN disconnects:
  1. Check VPN connection (try reconnecting)
  2. Force unmount: sudo umount -f /vds-data/Howard_New
  3. Remount the volume
  4. Restart the Docker container
```

## Maintenance

### Regular Updates

Run crawler periodically to keep ES updated:

```bash
# Daily/weekly via cron
0 2 * * * cd /path/to/vds-metadata-crawler && \
  python vds_crawler.py \
    --root-path /Users/raghu/vds-data \
    --es-hosts localhost:9200 \
    --skip-checksum \
    --skip-existing
```

### Monitor Elasticsearch

```bash
# Check ES health
curl http://localhost:9200/_cluster/health

# Check index stats
curl http://localhost:9200/vds-metadata/_count

# View index mapping
curl http://localhost:9200/vds-metadata/_mapping
```

### Clear and Rebuild Index

```bash
# Delete index
curl -X DELETE http://localhost:9200/vds-metadata

# Rebuild from scratch
cd ../vds-metadata-crawler
python vds_crawler.py \
  --root-path /Users/raghu/vds-data \
  --es-hosts localhost:9200 \
  --skip-checksum \
  --clear-progress
```

## Troubleshooting

### Issue: "Elasticsearch not connected"

**Cause:** ES container not running or not accessible

**Solution:**
```bash
# Check ES container
docker-compose ps

# Check ES logs
docker-compose logs elasticsearch

# Restart ES
docker-compose restart elasticsearch
```

### Issue: "Index does not exist"

**Cause:** ES running but not populated

**Solution:** Run vds-metadata-crawler (see Step 2)

### Issue: "Stale NFS mount"

**Cause:** VPN disconnected, mount is stale

**Solution:**
```bash
# 1. Reconnect VPN
# 2. Force unmount (on host machine)
sudo umount -f /Users/raghu/vds-data/Howard_New

# 3. Remount or restart Docker
docker-compose restart openvds-mcp
```

### Issue: Slow startup even with ES

**Cause:** Mount health check timing out

**Solution:** Increase timeout or disable:
```yaml
environment:
  - MOUNT_HEALTH_CHECK_TIMEOUT=30  # Increase timeout
  # OR
  - MOUNT_HEALTH_CHECK_ENABLED=false  # Disable
```

## Performance Comparison

| Mode | VDS Files | Startup Time | Query Time |
|------|-----------|--------------|------------|
| Direct Scan | 10 | ~10 sec | Instant |
| Direct Scan | 100 | ~100 sec | Instant |
| Elasticsearch | 10 | <5 sec | <100ms |
| Elasticsearch | 100 | <5 sec | <100ms |
| Elasticsearch | 1000 | <5 sec | <100ms |

## Testing

### Test Mount Health Checker

```bash
docker-compose exec openvds-mcp python src/mount_health.py /vds-data/Howard_New
```

### Test Elasticsearch Client

```bash
docker-compose exec openvds-mcp python src/es_metadata_client.py http://elasticsearch:9200
```

### Test Full Integration

```bash
# Start with ES enabled
docker-compose up

# Watch logs for:
# - Mount health checks
# - ES connection
# - Survey loading
```

## Migration from Old Setup

If you're upgrading from a version without ES:

1. **No changes to existing VDS files**
2. **Backward compatible** - works with or without ES
3. **Optional feature** - can be disabled

```bash
# Pull latest changes
git pull origin main

# Rebuild container
docker-compose build

# Start with ES
docker-compose up -d

# Populate ES (optional but recommended)
cd ../vds-metadata-crawler
python vds_crawler.py \
  --root-path /Users/raghu/vds-data \
  --es-hosts localhost:9200 \
  --skip-checksum
```

## Next Steps

1. Run the crawler to populate Elasticsearch
2. Set up a cron job for incremental updates
3. Monitor ES disk usage (typically ~1-5MB per VDS dataset)
4. Enjoy fast metadata queries!
