# Query Best Practices for Large VDS Datasets

## MCP Message Size Limits

The MCP (Model Context Protocol) has a **1MB message size limit**. When querying large VDS datasets (like 2858+ surveys), you need to use pagination and filtering to keep responses under this limit.

## Common Issues

### Problem: "Size too large > 1MB" errors

This occurs when querying returns too many surveys or too much metadata in a single response.

### Solutions

## 1. Use Filters to Narrow Results

Always filter your queries when possible:

```python
# Filter by region
surveys = await list_surveys(filter_region="Gulf of Mexico")

# Filter by year
surveys = await list_surveys(filter_year=2023)

# Combine filters
surveys = await list_surveys(
    filter_region="North Sea",
    filter_year=2024
)
```

## 2. Limit Result Count

Use the `max_results` parameter (default: 50, max: 200):

```python
# Get first 50 surveys (default)
surveys = await list_surveys()

# Get more results if needed
surveys = await list_surveys(max_results=100)

# Maximum allowed
surveys = await list_surveys(max_results=200)
```

## 3. Use Summary Mode for Overview

When you just need to know what's available without full details:

```python
# Get count and first 5 surveys only
result = await list_surveys(summary_only=True)
# Returns:
# {
#   "total_count": 2858,
#   "returned_count": 5,
#   "sample_surveys": [<first 5 surveys>],
#   "note": "Showing first 5 of 2858 surveys..."
# }
```

## 4. Query Specific Surveys

Once you know which survey you want, query it directly:

```python
# Get detailed metadata for a specific survey
metadata = await get_survey_info(survey_id="my_survey_name")
```

## Example Workflows

### Workflow 1: Explore and Filter

```python
# Step 1: Get overview
summary = await list_surveys(summary_only=True)
print(f"Total surveys available: {summary['total_count']}")

# Step 2: Filter by region
gulf_surveys = await list_surveys(
    filter_region="Gulf",
    max_results=50
)

# Step 3: Get details for specific survey
survey = await get_survey_info(survey_id=gulf_surveys[0]['id'])
```

### Workflow 2: Search by Name Pattern

```python
# Filter by path/name pattern (uses Elasticsearch query_string)
surveys = await list_surveys(
    filter_region="my_project_name",
    max_results=100
)
```

### Workflow 3: Paginate Through Results

```python
# Note: True pagination not yet implemented
# Current workaround: Use multiple filtered queries

# Query by different criteria
q1 = await list_surveys(filter_region="Gulf", max_results=200)
q2 = await list_surveys(filter_region="North", max_results=200)
q3 = await list_surveys(filter_region="Permian", max_results=200)
```

## Response Size Guidelines

Approximate response sizes:

- **Single survey (basic)**: ~1-2 KB
- **Single survey (with verbose metadata)**: ~5-10 KB
- **50 surveys (basic)**: ~50-100 KB ✅ Safe
- **200 surveys (basic)**: ~200-400 KB ✅ Safe
- **1000+ surveys (basic)**: ~2+ MB ❌ Will fail

## Configuration

Environment variables to control behavior:

```bash
# Elasticsearch (for fast metadata queries)
ES_ENABLED=true
ES_URL=http://elasticsearch:9200
ES_INDEX=vds-metadata

# Mount health checking
MOUNT_HEALTH_CHECK_ENABLED=true
MOUNT_HEALTH_CHECK_TIMEOUT=10
MOUNT_HEALTH_CHECK_RETRIES=3
```

## Troubleshooting

### Error: "Size too large > 1MB"

**Solution**: Reduce `max_results` or use `summary_only=true`

### Error: "Elasticsearch not connected"

**Solution**: The server will fall back to demo mode or direct VDS scanning. Use filters aggressively to limit results.

### Slow queries

**Solution**:
1. Ensure Elasticsearch is running and connected
2. Use specific filters rather than broad queries
3. Query specific surveys by ID when possible

## Future Improvements

Planned features:
- [ ] Cursor-based pagination for large result sets
- [ ] Streaming responses for large datasets
- [ ] Response compression
- [ ] Field selection (return only specific fields)
