# Conversational Interface for VDS Data Discovery

## Overview

The VDS MCP server provides a **conversational interface** for exploring and querying large VDS datasets (2858+ surveys). Unlike traditional UIs with dropdowns and pagination controls, this interface uses natural language and **progressive discovery** through multi-stage queries.

## The Challenge

**Problem**: MCP has a 1MB message size limit, but our dataset has 2858+ surveys. We can't return everything at once.

**Solution**: Multi-stage conversational discovery with:
1. **Statistics first** - Understand what's available
2. **Search and filter** - Narrow down results
3. **Pagination** - Browse through matches
4. **Details on demand** - Get full metadata for specific surveys

---

## Three-Stage Discovery Pattern

### Stage 1: Overview (Statistics)

**When to use**: Starting fresh, want to understand the dataset

**Tool**: `get_survey_stats`

**Example conversation**:
```
User: "What VDS surveys are available?"

Claude: Let me check what's available...
[Uses get_survey_stats]

Response shows:
- Total: 2858 surveys
- Types: 3D Seismic (2100), 4D Monitor (400), etc.
- Top regions: Santos Basin (350), Gulf of Mexico (280), etc.
- Sample surveys: First 5 examples

Claude: "I found 2858 surveys! The largest groups are:
- Santos Basin (350 surveys)
- Gulf of Mexico (280 surveys)
- North Sea (220 surveys)

What region interests you?"
```

### Stage 2: Search and Filter

**When to use**: User wants to explore a specific subset

**Tool**: `search_surveys`

**Parameters**:
- `search_query`: Free-text search (e.g., "Brazil", "PSTM", "Santos")
- `filter_region`: Region/location filter
- `filter_year`: Year filter
- `limit`: Results per page (default 20, max 100)
- `offset`: For pagination (default 0)

**Example conversation**:
```
User: "Show me surveys from Brazil"

Claude: [Uses search_surveys with search_query="Brazil", limit=20]

Response shows:
- Total matching: 450 surveys
- Returned: 20 surveys (offset 0)
- Has more: true
- Next offset: 20
- Sample results with names and paths

Claude: "I found 450 surveys from Brazil. Here are the first 20:

1. Santos Basin 3D PSTM 2023
2. Campos Basin 4D Monitor
3. ...
20. Espirito Santo Survey

Would you like to:
- See the next 20 results?
- Filter further (by year, type, etc.)?
- Get details on a specific survey?"
```

### Stage 3: Pagination

**When to use**: User wants to see more results

**Tool**: `search_surveys` with `offset`

**Example conversation**:
```
User: "Show me the next batch"

Claude: [Uses search_surveys with offset=20, same filters]

Response shows:
- Total matching: 450 surveys (unchanged)
- Returned: 20 surveys (offset 20)
- Has more: true
- Next offset: 40

Claude: "Here are surveys 21-40 from Brazil:

21. Pre-salt Survey 2022
22. ...
40. Tupi Field 3D

Still 410 more surveys available. Continue?"
```

### Stage 4: Details on Demand

**When to use**: User found a survey they want to examine

**Tool**: `get_survey_info`

**Example conversation**:
```
User: "Tell me more about the Santos Basin PSTM survey"

Claude: [Uses get_survey_info with survey_id="santos_basin_pstm_2023"]

Response shows:
- Full metadata
- Inline/crossline/sample ranges
- CRS information
- Statistics
- File size and location

Claude: "Santos Basin 3D PSTM 2023:
- Dimensions: 3D Seismic
- Inlines: 1000-5500
- Crosslines: 2000-8000
- Sample range: 0-6000 ms
- Size: 45.2 GB
- CRS: WGS84 / UTM Zone 23S

Ready to extract data from this survey?"
```

---

## Conversational Patterns

### Pattern 1: Exploratory ("What's available?")

```
User: "What seismic data do you have?"
→ get_survey_stats

User: "Show me Gulf of Mexico surveys"
→ search_surveys(filter_region="Gulf")

User: "Which ones are from 2023?"
→ search_surveys(filter_region="Gulf", filter_year=2023)

User: "Show me the first one in detail"
→ get_survey_info(survey_id=<first_result>)
```

### Pattern 2: Targeted Search ("Find specific data")

```
User: "Find PSTM processed surveys in Santos Basin"
→ search_surveys(search_query="PSTM Santos")

User: "Are there any from 2024?"
→ search_surveys(search_query="PSTM Santos", filter_year=2024)

User: "Show me more results"
→ search_surveys(search_query="PSTM Santos", filter_year=2024, offset=20)
```

### Pattern 3: Browse and Compare

```
User: "List surveys in the North Sea"
→ search_surveys(filter_region="North Sea", limit=50)

User: "Show me the next 50"
→ search_surveys(filter_region="North Sea", limit=50, offset=50)

User: "Compare surveys #3 and #7"
→ get_survey_info for both
→ Present comparison
```

### Pattern 4: Refine Search

```
User: "Search for 4D seismic data"
→ search_surveys(search_query="4D")
→ Returns 400 surveys

User: "Too many! Only show Gulf of Mexico"
→ search_surveys(search_query="4D", filter_region="Gulf")
→ Returns 45 surveys

User: "Perfect! Show me the first 10"
→ Already showing first 20 by default
→ Can adjust with limit parameter
```

---

## Response Structure

### Statistics Response (`get_survey_stats`)

```json
{
  "total_surveys": 2858,
  "filters_applied": {
    "region": null,
    "year": null
  },
  "type_distribution": {
    "3D Seismic": 2100,
    "4D Monitor": 400,
    "Other": 358
  },
  "top_regions": {
    "Santos": 350,
    "GulfOfMexico": 280,
    "NorthSea": 220
  },
  "sample_surveys": [<5 examples>],
  "recommendations": {
    "total_surveys": 2858,
    "suggestion": "Use search_surveys with filters to narrow down results"
  }
}
```

### Search Response (`search_surveys`)

```json
{
  "search_query": "Brazil",
  "filters": {
    "region": "Brazil",
    "year": null
  },
  "pagination": {
    "total_results": 450,
    "offset": 0,
    "limit": 20,
    "returned": 20,
    "has_more": true,
    "next_offset": 20
  },
  "surveys": [<20 survey objects>],
  "help": {
    "next_page": "To get next page, use offset=20",
    "refine_search": "Use filter_region or filter_year to narrow results",
    "get_details": "Use get_survey_info with a specific survey_id for full metadata"
  }
}
```

### Detail Response (`get_survey_info`)

```json
{
  "id": "santos_basin_pstm_2023",
  "name": "Santos Basin 3D PSTM 2023",
  "file_path": "/vds-data/Brazil/Santos/...",
  "inline_range": [1000, 5500],
  "crossline_range": [2000, 8000],
  "sample_range": [0, 6000],
  "dimensionality": 3,
  "data_type": "3D Seismic",
  "statistics": {
    "file_size_gb": 45.2,
    "total_samples": 125000000
  },
  "crs_info": {...},
  "spatial_extent": {...}
}
```

---

## Smart Defaults

The interface uses smart defaults to optimize the conversation:

1. **First query returns stats** - If user asks broadly, show overview
2. **Search returns 20 results** - Good balance between context and speed
3. **Pagination is explicit** - User must ask for "next page"
4. **Filters are sticky** - When paginating, previous filters apply
5. **Help hints included** - Every response suggests next steps

---

## Response Size Management

| Query Type | Typical Size | Max Size | Safe? |
|------------|-------------|----------|-------|
| Statistics | ~5 KB | ~10 KB | ✅ Always safe |
| Search (20 results) | ~8 KB | ~15 KB | ✅ Always safe |
| Search (100 results) | ~40 KB | ~80 KB | ✅ Always safe |
| Survey detail | ~2 KB | ~10 KB | ✅ Always safe |
| Search (1000 results) | ~400 KB | ~800 KB | ✅ Safe with limits |

All responses stay well under the 1MB MCP limit!

---

## Claude's Internal Strategy

When Claude receives a user query, it should:

1. **Classify the intent**:
   - Overview? → `get_survey_stats`
   - Search? → `search_surveys`
   - Details? → `get_survey_info`
   - Next page? → `search_surveys` with offset

2. **Apply filters progressively**:
   - Start broad
   - Narrow based on user feedback
   - Track what filters are active

3. **Manage pagination state**:
   - Remember current offset
   - Track total results
   - Suggest when to refine vs paginate

4. **Provide guidance**:
   - Too many results? Suggest filters
   - Too few results? Suggest broadening
   - Found what they want? Offer details

---

## Example: Full Discovery Session

```
User: "What VDS data do you have?"

Claude: [get_survey_stats]
"I have 2858 VDS surveys across multiple regions:
- Santos Basin (350)
- Gulf of Mexico (280)
- North Sea (220)
- Australia (180)
- Others (1828)

What would you like to explore?"

---

User: "Show me Australian surveys"

Claude: [search_surveys(filter_region="Australia", limit=20)]
"Found 180 Australian surveys. Here are the first 20:
1. Browse Basin 3D 2023
2. Gippsland 4D Monitor
...
20. Carnarvon Survey

See more? Or get details on one of these?"

---

User: "Are any from 2024?"

Claude: [search_surveys(filter_region="Australia", filter_year=2024, limit=20)]
"Found 15 Australian surveys from 2024:
1. Browse Basin 3D 2024
2. Perth Basin PSTM
...
15. North West Shelf Survey

These are all 15 results - no more pages needed."

---

User: "Tell me about the Browse Basin survey"

Claude: [get_survey_info("browse_basin_3d_2024")]
"Browse Basin 3D 2024:
- Type: 3D Seismic PSTM
- Coverage: Inlines 1000-3500, Crosslines 4000-7800
- Depth: 0-8000 ms
- Size: 28.5 GB
- Location: Browse Basin, NW Australia
- CRS: GDA94 / MGA Zone 51

Would you like to extract data from this survey?"
```

---

## Best Practices for Claude

### DO:
✅ Start with stats for broad queries
✅ Use search with filters for specific requests
✅ Paginate when users want to browse
✅ Get details when users ask about specific surveys
✅ Track applied filters across pagination
✅ Suggest refinements when too many results
✅ Show sample results to help users decide

### DON'T:
❌ Try to return all 2858 surveys at once
❌ Forget what filters were applied
❌ Skip straight to details without context
❌ Paginate unnecessarily for small result sets
❌ Use verbose metadata in list views
❌ Assume user knows survey IDs

---

## Summary

The conversational interface mimics a UI's progressive disclosure pattern:

**Traditional UI**:
1. Dashboard with stats
2. Search/filter controls
3. Results list with pagination
4. Detail view on click

**Conversational Interface**:
1. `get_survey_stats` → Dashboard
2. `search_surveys` → Search + Filter
3. `offset` parameter → Pagination
4. `get_survey_info` → Detail view

The key difference: **State is maintained through conversation context**, not UI controls!
