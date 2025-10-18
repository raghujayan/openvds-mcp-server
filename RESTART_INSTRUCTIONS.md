# How to Apply the Conversational Interface Updates

## Quick Steps

### 1. Rebuild the Docker Image (REQUIRED)
```bash
cd /Users/raghu/code/openvds-mcp-server
docker-compose build openvds-mcp
```

This rebuilds the image with the new code:
- New `search_surveys` tool
- New `get_survey_stats` tool
- Updated pagination logic
- Free-text search capabilities

### 2. Restart Claude Desktop

**macOS**:
```bash
# Option A: Kill and reopen
killall "Claude"
open -a "Claude"

# Option B: Use the menu
# Claude Desktop → Quit Claude
# Then reopen from Applications
```

That's it! The MCP server will automatically restart when Claude Desktop launches.

---

## Verification

After restarting, try these commands in Claude Desktop:

### Test 1: Statistics
```
"What VDS surveys are available?"
```
Should use `get_survey_stats` and show total count, distributions, etc.

### Test 2: Search
```
"Search for Brazilian surveys"
```
Should use `search_surveys` and show paginated results with total count.

### Test 3: Pagination
```
"Show me the next page"
```
Should use `search_surveys` with offset to get next batch.

### Test 4: Details
```
"Tell me about survey <name>"
```
Should use `get_survey_info` to get full metadata.

---

## Troubleshooting

### Issue: Old tools still showing

**Symptom**: Claude still tries to use `list_available_surveys` (old tool)

**Solution**:
```bash
# Force rebuild without cache
docker-compose build --no-cache openvds-mcp

# Restart Claude Desktop
killall "Claude" && open -a "Claude"
```

### Issue: MCP server not starting

**Symptom**: Error messages about missing tools or connection failures

**Check logs**:
```bash
# View MCP server logs in Claude Desktop
# Go to: Claude Desktop → Settings → Developer → View Logs
# Look for "openvds-mcp-server" errors
```

**Common fixes**:
```bash
# 1. Check Elasticsearch is running
curl http://localhost:9200/_cluster/health

# 2. Check Docker is running
docker ps

# 3. Rebuild image
docker-compose build openvds-mcp

# 4. Restart Claude Desktop
```

### Issue: Search not finding results

**Symptom**: `search_surveys` returns empty results

**Possible causes**:
1. Elasticsearch not connected (server will fall back to cached data)
2. Filters too restrictive
3. Search query doesn't match file paths

**Check**:
```
"Get survey statistics"
```
This will show total surveys available and confirm ES connection.

---

## What Changed

### New Tools Available
- ✅ `search_surveys` - Free-text search with pagination
- ✅ `get_survey_stats` - Aggregate statistics
- ⚠️ `list_available_surveys` - DEPRECATED (but still works)

### New Parameters
- `search_query` - Free-text search across all fields
- `offset` - For pagination (0, 20, 40, ...)
- `limit` - Results per page (default 20, max 100)

### Response Changes
All responses now include:
- `pagination` info (total, offset, has_more, next_offset)
- `help` hints for next steps
- Smaller payloads (no verbose metadata by default)

---

## Quick Test Script

Run this to verify everything works:

```bash
./test_quick.sh
```

Expected output:
```
✓ Initialized in ~0.1 seconds
✓ Elasticsearch: Yes
✓ Cached surveys: 500
✓ Response size limits working
✓ 50 surveys: 21.9 KB ✓ SAFE
✓ 200 surveys: 87.9 KB ✓ SAFE
```

---

## Complete Restart Checklist

- [ ] Rebuild Docker image: `docker-compose build openvds-mcp`
- [ ] Quit Claude Desktop completely
- [ ] Reopen Claude Desktop
- [ ] Test: "What VDS surveys are available?"
- [ ] Test: "Search for <region>"
- [ ] Test: "Show me more results"
- [ ] Verify pagination works
- [ ] Verify response sizes are small

---

## Need Help?

If issues persist:

1. Check `CONVERSATIONAL_INTERFACE.md` for usage patterns
2. Review `QUERY_BEST_PRACTICES.md` for technical details
3. Run `./test_quick.sh` to verify MCP server works standalone
4. Check Claude Desktop logs for MCP errors

The key is: **Always rebuild the Docker image when code changes!**
