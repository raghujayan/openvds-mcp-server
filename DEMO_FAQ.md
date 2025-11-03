# Demo Stability FAQ

## Your Concerns Addressed

### Q1: "What happens if I lose VPN during a demo?"

**Short Answer:** Metadata queries work, but data extraction fails.

**What Keeps Working:**
- ✅ `search_surveys` - Queries Elasticsearch, not VDS files
- ✅ `get_facets` - Pre-computed facets from ES
- ✅ `get_survey_info` - Metadata from ES (includes coordinates, dimensions, etc.)
- ✅ `get_survey_stats` - Aggregate statistics

**What Fails:**
- ❌ `extract_inline_image` - Needs to read VDS file
- ❌ `extract_crossline_image` - Needs VDS access
- ❌ `extract_volume_subset` - Needs VDS access
- ❌ Any actual seismic data extraction

**Recovery Time if VPN Drops:**
1. Reconnect VPN: ~30 seconds
2. NFS mount auto-recovers: ~5-10 seconds
3. Restart MCP server: ~5 seconds
4. **Total: ~1 minute downtime**

**Demo Fallback Strategy:**
```
"So here we have 2,858 VDS datasets indexed in Elasticsearch.
Let me show you how fast we can search and filter this metadata...
[Use search_surveys, get_facets, get_survey_info]
...and when we need the actual seismic data, we can extract it like this..."
[If VPN is back, proceed with extraction]
```

---

### Q2: "Do multiple chat sessions create multiple MCP server instances?"

**Yes**, and this is **by design** but can cause issues.

#### How It Works:
- Each Claude Desktop **chat session** spawns its own MCP server container
- Each container:
  - Loads 500 surveys into memory (~200MB RAM)
  - Connects to Elasticsearch (uses connection from pool)
  - Mounts the same NFS volume (read-only, safe)

#### When This Becomes a Problem:

**Resource Exhaustion:**
```
1 session:   1 container × 500MB RAM = 500MB
5 sessions:  5 containers × 500MB RAM = 2.5GB
10 sessions: 10 containers × 500MB RAM = 5GB ⚠️
```

**Elasticsearch Connection Limits:**
- Default ES connection pool: ~10,000 connections
- Each MCP server: ~10 connections
- **Safe up to ~100 concurrent sessions** (not realistic)

**NFS File Handle Limits:**
- NFS server has max file handles (usually 100,000+)
- Each MCP server opens VDS files on-demand
- **Risk starts at ~50+ concurrent sessions with active extractions**

#### Current Setup Analysis:

**Your Logs Showed:**
```
admiring_jang       (container 1)
focused_cartwright  (container 2)
openvds-mcp-server  (container 3)
```

This means 3 separate containers were running (likely from different chat sessions or restarts).

**Is This a Problem?**
- For demos with 1-5 concurrent users: **No problem**
- For production with 20+ users: **Needs optimization**

---

### Q3: "What should I do to prevent issues?"

#### Before Demo (5 minutes):
```bash
./demo-prepare.sh
```

This checks:
- ✅ VPN connection
- ✅ NFS mount health
- ✅ Docker running
- ✅ Elasticsearch healthy
- ✅ Cleans up old containers
- ✅ Tests MCP server startup

#### During Demo (separate terminal):
```bash
./demo-monitor.sh
```

Real-time monitoring of:
- 🌐 VPN status
- 💾 NFS mount health
- 🐳 Running containers
- 🔍 Elasticsearch status
- 📊 Resource usage

#### If Multiple Sessions Expected:

**Option 1: Limit concurrent sessions**
- Use 1 main demo session
- Close other chat windows
- Clean up with: `docker stop $(docker ps -q --filter "ancestor=openvds-mcp-server")`

**Option 2: Add resource limits** (already recommended in docker-compose.yml)
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
```

**Option 3: Periodic cleanup** (add to cron or run manually)
```bash
# Stop containers older than 1 hour
docker ps -a --filter "ancestor=openvds-mcp-server" --format "{{.ID}}" | \
  xargs -I {} sh -c 'docker inspect {} --format "{{.State.StartedAt}}" | \
  xargs -I @ bash -c "if [[ \$(date -j -f \"%Y-%m-%dT%H:%M:%S\" @ +%s) -lt \$(date -v-1H +%s) ]]; then docker stop {}; fi"'
```

---

## Quick Decision Matrix

### Demo with < 5 participants:
✅ Current setup is fine
✅ Run `./demo-prepare.sh` before demo
✅ Keep `./demo-monitor.sh` running in separate terminal

### Demo with 5-20 participants:
✅ Current setup probably okay
✅ Add resource limits to docker-compose.yml
✅ Monitor actively during demo
⚠️ Have fallback to metadata-only if issues arise

### Production with 20+ concurrent users:
❌ Current setup needs optimization
🔄 Consider singleton MCP server (HTTP-based)
🔄 Implement connection pooling
🔄 Add Redis caching layer
🔄 Load balancer with multiple servers

---

## Emergency Procedures

### If VPN Drops During Demo:
1. **Don't panic** - you have 1 minute to recover
2. **Switch to metadata queries** while reconnecting:
   ```
   "Let me show you the metadata architecture first...
   We have fast Elasticsearch queries for discovery..."
   ```
3. **Reconnect VPN** in background (30s)
4. **Continue demo** - mount recovers automatically
5. **Return to data extraction** when ready

### If Too Many Containers Running:
```bash
# Kill all MCP containers (safe - they restart on demand)
docker stop $(docker ps -q --filter "ancestor=openvds-mcp-server")
docker rm $(docker ps -aq --filter "ancestor=openvds-mcp-server")

# Claude Desktop will restart MCP server when needed
```

### If Elasticsearch Goes Down:
```bash
# Restart ES
docker start vds-shared-elasticsearch

# Wait for green/yellow status
watch -n 1 'curl -s http://localhost:9200/_cluster/health | jq .status'

# MCP server reconnects automatically
```

---

## Recommended Setup for Your Next Demo

```bash
# 1. Day before: Create local backup (optional but recommended)
rsync -avz /Volumes/Hue/Datasets/VDS/Brazil ~/demo-vds-backup/

# 2. Morning of demo: Prepare environment
cd ~/code/openvds-mcp-server
./demo-prepare.sh

# 3. Start monitoring (in separate terminal)
./demo-monitor.sh

# 4. Give demo in Claude Desktop
# - Keep monitor terminal visible
# - Watch for VPN/mount warnings

# 5. After demo: Cleanup
docker stop $(docker ps -q --filter "ancestor=openvds-mcp-server")
```

---

## Long-Term Recommendations

**For Demos (< 1 week):**
- Use current setup with `demo-prepare.sh` and `demo-monitor.sh`
- Consider local data copy for critical demos

**For Light Production (< 1 month):**
- Add periodic container cleanup cron job
- Implement mount health monitoring in VDS client
- Add circuit breaker for fast-fail on mount issues

**For Heavy Production (ongoing):**
- Migrate to singleton HTTP-based MCP server
- Implement Redis caching for metadata
- Add load balancing for multiple MCP servers
- Consider hosting VDS files on faster storage (SSD, local cache)
- Implement connection pooling and resource quotas

---

## Summary

**Your concerns are valid**, but manageable:

1. **VPN drops**: Metadata queries continue working, ~1min recovery time
2. **Multiple instances**: Current setup handles 5-10 sessions fine, needs optimization for 20+

**Immediate actions** (do before next demo):
- ✅ Run `./demo-prepare.sh`
- ✅ Use `./demo-monitor.sh` during demo
- ✅ Practice fallback to metadata-only queries

**You're ready for demos** with current setup! 🎯
