# Testing: MCP Server Lifecycle per Chat Session

## The Question

**Does each chat tab have a persistent MCP server, even when not active?**

## Expected Behaviors (Hypothesis)

### Scenario A: "Lazy Start" (Optimized)
- MCP server starts ONLY when you use MCP tools
- Exits after idle timeout or when you switch tabs
- Multiple tabs share 1 server OR each spawns on-demand

### Scenario B: "Persistent Per Tab" (Resource Heavy)
- Each chat tab spawns MCP server on creation
- Server stays running for entire tab lifetime
- Switching tabs doesn't stop servers
- Only exits when tab is closed

## How to Test

### Test 1: Single Chat Tab Behavior

```bash
# Step 1: Check baseline (no containers)
./check-containers.sh

# Step 2: Open Claude Desktop with 1 chat
# (Don't use any MCP tools yet)

# Step 3: Check containers
./check-containers.sh

# Expected Result:
# - Scenario A: 0 containers (not started yet)
# - Scenario B: 1 container (started on tab creation)
```

### Test 2: Using MCP Tools

```bash
# Step 1: In Claude chat, use MCP tool (e.g., search_surveys)

# Step 2: Check containers immediately
./check-containers.sh

# Expected: 1 container running

# Step 3: Wait 5 minutes (idle)

# Step 4: Check containers again
./check-containers.sh

# Expected Result:
# - Scenario A: 0 containers (stopped after idle)
# - Scenario B: 1 container (still running)
```

### Test 3: Multiple Chat Tabs

```bash
# Step 1: Open 3 chat tabs in Claude Desktop
# (Don't use MCP tools in any)

# Step 2: Check containers
./check-containers.sh

# Expected Result:
# - Scenario A: 0 containers
# - Scenario B: 3 containers

# Step 3: Use MCP tool in Tab 1 only

# Step 4: Check containers
./check-containers.sh

# Expected Result:
# - Scenario A: 1 container
# - Scenario B: 3 containers (all still running)
```

### Test 4: Switching Tabs

```bash
# Step 1: Use MCP tool in Tab 1
# Step 2: Check containers (should be 1+)

# Step 3: Switch to Tab 2 (don't use MCP)
# Step 4: Check containers immediately

# Expected Result:
# - Scenario A: 0-1 containers (may have stopped)
# - Scenario B: 1+ containers (Tab 1 server still running)

# Step 5: Wait 2 minutes
# Step 6: Check containers again

# Expected Result:
# - Scenario A: 0 containers (idle timeout)
# - Scenario B: 1+ containers (persistent)
```

## Run These Tests

Please run these tests and report back:

1. **Test 1**: Open Claude Desktop → Check containers
2. **Test 2**: Use an MCP tool → Check containers → Wait 5 min → Check again
3. **Test 3**: Open 3 chat tabs → Check containers
4. **Test 4**: Switch between tabs → Check containers

## Commands to Use

```bash
# Quick check
./check-containers.sh

# Detailed check with timestamps
docker ps --filter "ancestor=openvds-mcp-server" \
  --format "table {{.Names}}\t{{.Status}}\t{{.CreatedAt}}"

# Watch in real-time (run in separate terminal)
watch -n 2 './check-containers.sh'
```

## My Prediction

Based on typical MCP implementation, I predict **Scenario B**:
- Each chat session spawns its own MCP server
- Servers persist for the lifetime of the chat tab
- Switching tabs does NOT stop servers
- Only closing the tab (or Claude Desktop) stops the server

**Why?** stdio-based MCP servers need persistent stdin/stdout pipes, which are tied to the chat session lifecycle.

## What This Means for You

If Scenario B is correct (likely):

### Resource Usage
```
1 chat tab  = 1 container × ~500MB RAM = 500MB
5 chat tabs = 5 containers × ~500MB RAM = 2.5GB
10 chat tabs = 10 containers × ~500MB RAM = 5GB ⚠️
```

### Best Practices
1. **Close unused chat tabs** to free resources
2. **Before demos**: Close all chats, reopen 1 fresh chat
3. **Monitor**: Use `./demo-monitor.sh` to watch container count
4. **Cleanup**: If you see 10+ containers, close tabs or run cleanup

### Not a Bug - By Design
This is actually **correct behavior** for stdio-based MCP:
- Each chat needs dedicated stdin/stdout pipes
- Can't share servers between chats (separate contexts)
- Ensures isolation between chat sessions

## Action Items

1. **Run the tests above** to confirm behavior
2. **Report findings** (I'm 90% sure it's Scenario B)
3. **Update demo workflow** based on findings:
   - Close all tabs before demos
   - Keep only 1-2 chat tabs open during demos
   - Monitor container count

## Alternative: HTTP-based MCP (Future)

If resource usage becomes a problem, we could migrate to HTTP-based MCP:
- Single shared server
- All chats connect to same instance
- Connection pooling
- Better resource management

But for demos with 1-5 concurrent chats, current setup is fine! ✅
