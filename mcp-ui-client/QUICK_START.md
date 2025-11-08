# VDS Explorer - Quick Start Guide

Get the backend API running in 5 minutes!

## Prerequisites

- Python 3.10+
- OpenVDS MCP Server (parent directory)

## Start Backend API

```bash
cd mcp-ui-client/backend

# Install dependencies
pip install -r requirements.txt

# Set MCP server path (adjust path as needed)
export MCP_SERVER_PATH="../../src/openvds_mcp_server.py"

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
INFO:     MCP client initialized successfully
```

## Test the API

Open a new terminal:

### 1. Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "mcp_connected": true
}
```

### 2. Search Surveys
```bash
curl -X POST http://localhost:8000/api/surveys/search \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'
```

### 3. Get Survey Info
```bash
curl http://localhost:8000/api/surveys/Sepia
```

### 4. Extract Inline (with image)
```bash
curl -X POST http://localhost:8000/api/extract/inline \
  -H "Content-Type: application/json" \
  -d '{
    "survey_id": "Sepia",
    "inline_number": 55000,
    "colormap": "seismic"
  }' | jq .
```

## Interactive API Documentation

Visit in your browser:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Both provide interactive API testing directly in your browser!

## What You Can Do Now

With the backend running, you can:

✅ **Search surveys** - Find VDS datasets by name, region, year
✅ **Extract data** - Get inlines, crosslines, timeslices with images
✅ **Validate data** - Check statistics, coordinates, consistency
✅ **Manage agents** - Start autonomous extraction jobs
✅ **Real-time updates** - WebSocket for agent status

## Python Client Example

```python
import requests

# Base URL
API_URL = "http://localhost:8000"

# Search surveys
response = requests.post(
    f"{API_URL}/api/surveys/search",
    json={"search_query": "Sepia", "limit": 5}
)
surveys = response.json()
print(f"Found {surveys['pagination']['total_results']} surveys")

# Get survey info
survey = requests.get(f"{API_URL}/api/surveys/Sepia").json()
print(f"Survey: {survey['name']}")
print(f"Inline range: {survey['dimensions']['inline_range']}")

# Extract inline
result = requests.post(
    f"{API_URL}/api/extract/inline",
    json={
        "survey_id": "Sepia",
        "inline_number": 55000,
        "colormap": "seismic"
    }
).json()

# Image is returned as base64
import base64
image_data = base64.b64decode(result['image_data'])
with open('inline_55000.png', 'wb') as f:
    f.write(image_data)
print("Inline image saved!")
```

## JavaScript/Browser Example

```javascript
// Search surveys
const searchSurveys = async () => {
  const response = await fetch('http://localhost:8000/api/surveys/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ search_query: 'Sepia', limit: 5 })
  });
  const data = await response.json();
  console.log(`Found ${data.pagination.total_results} surveys`);
  return data;
};

// Extract inline
const extractInline = async (surveyId, inlineNumber) => {
  const response = await fetch('http://localhost:8000/api/extract/inline', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      survey_id: surveyId,
      inline_number: inlineNumber,
      colormap: 'seismic'
    })
  });
  const data = await response.json();

  // Display image
  const img = document.createElement('img');
  img.src = `data:${data.mimeType};base64,${data.image_data}`;
  document.body.appendChild(img);

  return data;
};

// Usage
searchSurveys();
extractInline('Sepia', 55000);
```

## Next Steps

1. **Test all endpoints** using Swagger UI at http://localhost:8000/docs
2. **Build your client** - Use any language/framework you prefer
3. **Or complete the React frontend** - See `IMPLEMENTATION_STATUS.md`

## Troubleshooting

**Error: "MCP server not found"**
```bash
# Check the path is correct
export MCP_SERVER_PATH="$(pwd)/../../src/openvds_mcp_server.py"
ls -la $MCP_SERVER_PATH  # Should exist
```

**Error: "Module not found"**
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

**Error: "Connection refused"**
```bash
# Make sure nothing else is using port 8000
lsof -i :8000
# Or run on a different port
uvicorn app.main:app --port 8001
```

## Support

- See `README.md` for comprehensive documentation
- See `IMPLEMENTATION_STATUS.md` for implementation details
- Check logs for detailed error messages

**You're ready to explore seismic data via API! 🚀**
