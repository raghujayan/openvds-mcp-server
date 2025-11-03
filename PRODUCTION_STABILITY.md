# Production Stability Guide for Demos

## Critical Issues Identified

### 1. NFS Mount + VPN Stability Issues

**Problem:**
- VDS data is on NFS mount: `10.3.3.5:/Hue` → `/Volumes/Hue`
- When VPN disconnects during demo:
  - NFS mount becomes **stale** (operations hang/timeout)
  - Mount health check detects it, but **ongoing operations fail**
  - OpenVDS file operations hang indefinitely
  - Recovery requires VPN reconnect + remount
  - **Demo fails catastrophically**

**Impact:**
- High risk for live demos
- No graceful degradation
- Long recovery time (reconnect VPN, wait for mount, restart server)

### 2. Multiple MCP Server Instances

**Problem:**
- Each Claude Desktop chat session spawns **separate MCP server container**
- Earlier logs showed multiple instances: `admiring_jang`, `focused_cartwright`
- Potential issues:
  - **Resource exhaustion** (each loads 500 surveys into memory)
  - **Elasticsearch connection pool saturation**
  - **File handle exhaustion** on NFS mount
  - **Confusing logs** (which container failed?)

**Impact:**
- Unpredictable behavior during heavy usage
- Resource leaks if containers don't clean up
- Hard to debug which instance is failing

---

## Recommended Solutions

### Solution 1: Demo-Safe Data Strategy

#### Option A: Local Data Copy (RECOMMENDED for demos)
```bash
# Create local demo dataset (before demo)
mkdir -p ~/demo-vds-data
rsync -avz --progress /Volumes/Hue/Datasets/VDS/Brazil ~/demo-vds-data/

# Update docker-compose.yml for demo mode
volumes:
  - ~/demo-vds-data:/vds-data:ro  # Local, no NFS dependency
```

**Pros:**
- ✅ No VPN dependency
- ✅ Fast, reliable access
- ✅ Demo always works
- ✅ Can demo offline

**Cons:**
- ❌ Requires disk space (~100GB+ for Brazil dataset)
- ❌ Data not current (manual sync needed)

#### Option B: Hybrid with Fallback
```yaml
# docker-compose-demo.yml
volumes:
  # Try NFS first, fallback to local
  - /Volumes/Hue/Datasets/VDS:/vds-data:ro
  - ~/demo-vds-data:/vds-data-local:ro

environment:
  - VDS_DATA_PATH=/vds-data
  - VDS_FALLBACK_PATH=/vds-data-local  # If mount stale
```

Modify `vds_client.py` to:
1. Check mount health
2. If stale, switch to fallback path
3. Log warning but **keep serving**

### Solution 2: Resilient Mount Health Monitoring

**Current:** Mount check runs once at startup
**Needed:** Continuous monitoring with graceful degradation

#### Implement Periodic Health Checks
```python
# In vds_client.py
async def _start_mount_health_monitor(self):
    """Monitor mount health every 30s during operation"""
    while True:
        await asyncio.sleep(30)
        result = await self.mount_health_checker.check_mount_health(self.vds_path)

        if not result.is_healthy:
            logger.error(f"⚠️  Mount became unhealthy during operation: {result}")
            # Options:
            # 1. Switch to fallback path
            # 2. Use Elasticsearch-only mode (metadata queries work)
            # 3. Return cached results
            # 4. Raise clear error to user
```

#### Add Circuit Breaker Pattern
```python
class VDSClient:
    def __init__(self):
        self.mount_failures = 0
        self.mount_circuit_open = False

    async def open_vds(self, survey_id):
        if self.mount_circuit_open:
            raise MountUnavailableError(
                "VDS mount is unhealthy. Using cached metadata only."
            )

        try:
            # Attempt open with timeout
            handle = await asyncio.wait_for(
                self._open_vds_internal(survey_id),
                timeout=5.0  # Fast fail, don't hang demo
            )
            self.mount_failures = 0  # Reset on success
            return handle
        except asyncio.TimeoutError:
            self.mount_failures += 1
            if self.mount_failures > 3:
                self.mount_circuit_open = True
                logger.error("🔴 Circuit breaker OPEN - too many mount failures")
            raise
```

### Solution 3: Singleton MCP Server Architecture

**Current:** Each chat session = new container
**Better:** Shared server with connection pooling

#### Option A: Long-Running Daemon Mode
```yaml
# docker-compose.yml
services:
  openvds-mcp:
    restart: unless-stopped
    ports:
      - "3000:3000"  # Expose as HTTP API
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Then Claude Desktop connects to `http://localhost:3000` instead of spawning new containers.

**Pros:**
- ✅ Single shared instance
- ✅ Better resource management
- ✅ Easier monitoring
- ✅ Can add connection pooling

**Cons:**
- ❌ Requires MCP protocol changes (HTTP instead of stdio)
- ❌ More complex setup

#### Option B: Container Lifecycle Management
```json
// claude_desktop_config.json
{
  "mcpServers": {
    "openvds": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--name", "openvds-mcp-singleton",  // Fixed name prevents duplicates
        "--network", "vds-shared-network",
        "-v", "/Volumes/Hue/Datasets/VDS:/vds-data:ro",
        "openvds-mcp-server:latest"
      ]
    }
  }
}
```

**Note:** This will fail if a container with that name exists. Need cleanup script:
```bash
#!/bin/bash
# cleanup-mcp.sh
docker stop openvds-mcp-singleton 2>/dev/null || true
docker rm openvds-mcp-singleton 2>/dev/null || true
```

---

## Recommended Demo Setup

### Before Demo Checklist:

```bash
#!/bin/bash
# demo-prepare.sh

echo "🎯 Preparing for demo..."

# 1. Check VPN connection
if ! ping -c 1 10.3.3.5 &>/dev/null; then
    echo "❌ VPN not connected to 10.3.3.5"
    exit 1
fi

# 2. Check NFS mount
if ! ls /Volumes/Hue/Datasets/VDS &>/dev/null; then
    echo "❌ NFS mount not accessible"
    exit 1
fi

# 3. Test mount speed (should be <1s)
time ls /Volumes/Hue/Datasets/VDS/Brazil &>/dev/null
echo "✅ Mount is fast and accessible"

# 4. Clean up old containers
docker stop $(docker ps -aq --filter "ancestor=openvds-mcp-server") 2>/dev/null || true
docker rm $(docker ps -aq --filter "ancestor=openvds-mcp-server") 2>/dev/null || true

# 5. Verify Elasticsearch
if ! curl -s http://localhost:9200/_cluster/health | grep -q "green\|yellow"; then
    echo "❌ Elasticsearch not healthy"
    exit 1
fi

# 6. Pre-warm the MCP server
docker-compose up -d
sleep 5
docker logs openvds-mcp-server | grep "VDS Client initialized"

echo "✅ Demo environment ready!"
echo "📊 $(curl -s http://localhost:9200/vds-metadata/_count | jq .count) VDS datasets indexed"
```

### During Demo Monitoring:

```bash
#!/bin/bash
# demo-monitor.sh

watch -n 2 '
echo "=== MCP Server Status ==="
docker ps --filter "ancestor=openvds-mcp-server" --format "table {{.Names}}\t{{.Status}}"
echo ""
echo "=== NFS Mount Health ==="
timeout 2 ls /Volumes/Hue/Datasets/VDS &>/dev/null && echo "✅ HEALTHY" || echo "❌ STALE"
echo ""
echo "=== Elasticsearch ==="
curl -s http://localhost:9200/_cluster/health | jq ".status"
'
```

---

## Emergency Recovery

If demo fails due to stale mount:

1. **Don't panic** - metadata queries still work via Elasticsearch
2. **Switch to metadata-only mode**:
   ```bash
   # Restart server without VDS mount
   docker stop openvds-mcp-server
   docker run --rm -i \
     --network vds-shared-network \
     -e VDS_DATA_PATH=/dev/null \
     -e ES_ENABLED=true \
     -e ES_URL=http://vds-shared-elasticsearch:9200 \
     openvds-mcp-server
   ```
3. **Continue demo** showing survey discovery, metadata queries, facets
4. **Explain to audience**: "Data extraction requires VPN, but metadata layer works independently"

---

## Long-Term Recommendations

1. **For production demos**: Use local data copy (Option A above)
2. **For development**: Implement hybrid fallback (Option B)
3. **Add monitoring**: Periodic mount health checks with circuit breaker
4. **Resource limits**: Add to docker-compose.yml:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 4G
       reservations:
         memory: 2G
   ```
5. **Container cleanup**: Add cleanup hook to Claude Desktop startup
6. **Consider**: Moving to persistent MCP server with HTTP API

---

## Testing Stability

### Simulate VPN Disconnect:
```bash
# Unmount NFS to simulate VPN loss
sudo umount -f /Volumes/Hue

# Try data extraction - should fail gracefully
# Test mount health check detection

# Remount
sudo mount -t nfs 10.3.3.5:/Hue /Volumes/Hue
```

### Test Multiple Instances:
```bash
# Spawn 5 MCP servers simultaneously
for i in {1..5}; do
    docker run --rm -d \
      --name mcp-test-$i \
      --network vds-shared-network \
      -v /Volumes/Hue/Datasets/VDS:/vds-data:ro \
      openvds-mcp-server &
done

# Monitor resource usage
docker stats

# Clean up
docker stop $(docker ps -q --filter "name=mcp-test-")
```

---

## Quick Wins for Next Demo

**Immediate actions (< 1 hour):**
1. ✅ Create `demo-prepare.sh` and run before demos
2. ✅ Create local copy of Brazil dataset for offline fallback
3. ✅ Add resource limits to docker-compose.yml
4. ✅ Test emergency metadata-only recovery procedure

**Soon (< 1 week):**
5. Add periodic mount health monitoring
6. Implement circuit breaker for fast-fail on stale mounts
7. Add fallback to local data if NFS unavailable

**Later (ongoing):**
8. Consider HTTP-based MCP server for better lifecycle management
9. Add comprehensive monitoring/alerting
10. Create demo recording as ultimate fallback 😉
