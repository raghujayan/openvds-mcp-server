# VolumeGPT Demo Script
## Conversational Data Analysis & QC with Autonomous Agents

**Duration:** 10-12 minutes
**Objective:** Showcase conversational approach to seismic data discovery, analysis, and QC using LLMs + Autonomous Agents

---

## Phase 1: Data Discovery (2-3 minutes)

### Prompt 1: Initial Discovery
```
What VDS datasets do you have available? Give me a summary of the different regions and data types.
```

**Expected Outcome:**
- Shows search_surveys capability
- Lists datasets by region (Brazil, Australia, etc.)
- Shows data diversity (3D surveys, different vintages)

**What This Demonstrates:**
- Elasticsearch-powered fast metadata queries
- No need to open VDS files for discovery
- Natural language interface

---

### Prompt 2: Focus on Santos Basin
```
Show me all the Santos Basin datasets. What's their coverage and quality?
```

**Expected Outcome:**
- Filters to Santos-related datasets using faceted search
- Shows inline/crossline ranges, sample depths
- Displays file sizes and locations

**What This Demonstrates:**
- Faceted search capabilities
- Geographic/basin-level filtering
- Metadata richness (ranges, dimensions, attributes)

---

### Prompt 3: Pick a Specific Dataset
```
Tell me more about the Sepia survey. What are the dimensions, coordinate system, and data characteristics?
```

**Expected Outcome:**
- Detailed metadata for: `0282_BM_S_FASE2_3D_Sepia_Crop_IAI_FS_tol1`
- Inline range: 51001-59001
- Crossline range: 8001-8501
- Sample range: 4500-8500ms
- Coordinate system, annotation info
- File size and chunk layout

**What This Demonstrates:**
- Deep metadata inspection
- Survey-level detail without opening file
- Understanding data extent for planning

---

## Phase 2: Conversational QC Analysis (3-4 minutes)

### Prompt 4: Initial QC Check
```
I want to do a quick QC check on the Sepia survey. Extract 3 representative inlines: one near the start, one in the middle, and one near the end. Focus on the depth range 5500-7000m.
```

**Expected Outcome:**
- Agent parses instruction into 3 inline extractions:
  - Inline 51500 (near start)
  - Inline 55000 (middle)
  - Inline 58500 (near end)
- Depth range: 5500-7000m
- Returns session_id immediately
- Agent works in background

**What This Demonstrates:**
- **Autonomous agent** - no manual tool selection
- Natural language instruction parsing
- Non-blocking execution
- Smart interpretation (start/middle/end)

---

### Prompt 5: Check Agent Status
```
What's the status of my extraction?
```

**Expected Outcome:**
- Shows progress: "2/3 completed (66.7%)"
- Current task: "Extracting inline 58500"
- State: RUNNING or COMPLETED

**What This Demonstrates:**
- Real-time progress tracking
- Asynchronous background execution
- Session-based orchestration

---

### Prompt 6: Review QC Results
```
Show me the results of the QC extraction. What did you find?
```

**Expected Outcome:**
- Returns completed extraction statistics:
  - Image dimensions
  - Amplitude ranges (min/max)
  - Data quality indicators
  - Completion times
- Links to extracted images (if visualization enabled)

**What This Demonstrates:**
- Agent results retrieval
- Metadata from extractions
- Foundation for QC assessment

---

### Prompt 7: Conversational Follow-up
```
Based on those extractions, do you see any data quality issues? Are there any gaps or anomalies I should be aware of?
```

**Expected Outcome:**
- LLM analyzes amplitude statistics
- Identifies if amplitude ranges are consistent
- Notes if any sections have unusual characteristics
- Suggests additional QC if needed

**What This Demonstrates:**
- **LLM reasoning** over data
- Conversational analysis
- Expert-level interpretation suggestions
- Proactive QC recommendations

---

## Phase 3: Targeted Analysis with Agent (3-4 minutes)

### Prompt 8: Zone of Interest Exploration
```
I'm interested in the depth zone around 6000-6500m, which might contain reservoir targets. Extract every 500th inline across the survey at this depth range so I can assess lateral continuity.
```

**Expected Outcome:**
- Agent parses "every 500th inline" with depth 6000-6500m
- Creates extraction plan:
  - Inlines: 51001, 51501, 52001, 52501, ... 58501, 59001
  - Approximately 16 inlines
  - Depth: 6000-6500m
- Starts execution in background
- Returns session_id

**What This Demonstrates:**
- Complex instruction parsing ("every 500th")
- Range-based extraction
- Depth windowing
- Autonomous task planning

---

### Prompt 9: Check Progress While Running
```
How's the extraction going? How many are done?
```

**Expected Outcome:**
- Shows progress: "8/16 completed (50%)"
- Current task: "Extracting inline 55001"
- Estimated remaining time (if available)

**What This Demonstrates:**
- Long-running task monitoring
- Non-blocking interface (can ask questions while agent works)
- Real-time status updates

---

### Prompt 10: Pause and Resume (Optional)
```
Pause the agent for a moment, I want to check something.
```

**Wait 10 seconds**

```
Resume the extraction.
```

**Expected Outcome:**
- Agent pauses after current task completes
- Status shows "PAUSED"
- Resume command restarts execution

**What This Demonstrates:**
- Agent control capabilities
- Graceful pause/resume
- User control over long-running tasks

---

### Prompt 11: Final Results and Analysis
```
Show me the final results. What's the overall data quality for this depth zone? Are there any interesting features?
```

**Expected Outcome:**
- Summary of all 16 completed extractions
- Amplitude statistics across the zone
- LLM analysis of lateral continuity
- Identification of potential features (channels, faults, etc.)

**What This Demonstrates:**
- **LLM-powered interpretation**
- Synthesis across multiple extractions
- Geophysical insight generation
- Conversational reporting

---

## Phase 4: Comparative Analysis (2-3 minutes) [Optional if time allows]

### Prompt 12: Multi-Survey Comparison
```
Now compare this to another Santos dataset. What other surveys do we have in the same basin?
```

**Expected Outcome:**
- Lists other Santos/Brazil surveys
- Shows adjacent or overlapping surveys
- Suggests comparison candidates

**What This Demonstrates:**
- Cross-survey discovery
- Basin-scale analysis
- Regional context

---

### Prompt 13: Extraction from Comparison Survey
```
Extract inline 55000 from the [other survey name] at the same depth range (6000-6500m) so I can compare them.
```

**Expected Outcome:**
- Instant extraction from second survey
- Same depth window for direct comparison
- Returns results quickly

**What This Demonstrates:**
- Multi-survey workflows
- Comparative analysis
- Rapid survey switching

---

## Demo Wrap-up (1 minute)

### Prompt 14: Summary Question
```
Summarize what we learned about the Sepia survey today. What would be the next steps for a full QC campaign?
```

**Expected Outcome:**
- LLM synthesizes all previous interactions
- Summarizes findings:
  - Survey dimensions and coverage
  - Data quality assessment
  - Identified zones of interest
- Recommends next steps:
  - Full inline/crossline grid extraction
  - Horizon picking in target zones
  - Attribute analysis (amplitude, frequency)
  - Integration with well data

**What This Demonstrates:**
- **Conversation memory and context**
- Executive summary generation
- Workflow planning
- Expert guidance

---

## Key Messages to Emphasize During Demo

1. **No Code Required**
   - "Notice I'm just talking naturally, no API calls or scripts"
   - Traditional approach: Write Python scripts, manage loops, handle errors
   - VolumeGPT: Conversational interface

2. **Autonomous Agents**
   - "The agent is working in the background while I continue talking"
   - Traditional: Blocking operations, wait for each extraction
   - VolumeGPT: Asynchronous, non-blocking

3. **LLM Intelligence**
   - "The LLM understands 'start, middle, end' without explicit numbers"
   - "It's analyzing data quality and suggesting next steps"
   - Traditional: Manual scripting of every step
   - VolumeGPT: Intelligent interpretation and recommendations

4. **Speed (VDS + Elasticsearch)**
   - "Data discovery across 100+ datasets in <5 seconds"
   - "No need to open files for metadata queries"
   - Traditional: Scan all files, slow SEG-Y reads
   - VolumeGPT: Instant metadata, fast VDS extraction

5. **Natural Workflow**
   - "This is how geophysicists actually think and talk"
   - Traditional: Forced into rigid tool interfaces
   - VolumeGPT: Natural conversation

---

## Technical Setup Checklist (Before Demo)

- [ ] VPN connected to 10.3.3.5
- [ ] NFS mount healthy: `/Volumes/Hue/Datasets/VDS`
- [ ] Docker running
- [ ] Elasticsearch healthy with indexed metadata
- [ ] MCP server container running
- [ ] Claude Desktop connected to MCP server
- [ ] Run: `./demo-prepare.sh` (validates all above)

---

## Fallback Strategy (If Issues Arise)

**If VDS extraction fails:**
- Emphasize metadata/discovery capabilities
- "Even without live data access, we can search and plan extractions"
- Show search_surveys, get_facets, get_survey_metadata

**If agent fails:**
- Fall back to manual tool calls
- "Let me use the direct extraction tools instead"
- Use extract_inline, extract_crossline directly

**If Elasticsearch is down:**
- Use list_surveys (direct file system scan)
- "We can still access the data, just slower discovery"

---

## Timing Guide

| Phase | Duration | Key Capability |
|-------|----------|----------------|
| Discovery | 2-3 min | Fast metadata search |
| QC Analysis | 3-4 min | Autonomous agents + LLM reasoning |
| Targeted Analysis | 3-4 min | Complex instruction parsing |
| Comparison (Optional) | 2-3 min | Multi-survey workflows |
| Wrap-up | 1 min | Context synthesis |

**Total: 10-12 minutes**

---

## Audience-Specific Variations

### For Technical Audience (Developers, IT)
- Emphasize architecture: Elasticsearch, async agents, MCP protocol
- Show how instructions map to API calls
- Discuss scalability and multi-cloud deployment

### For Business Audience (Managers, Executives)
- Emphasize time savings: "What took hours now takes minutes"
- Focus on cost efficiency: Consumption-based pricing
- Highlight competitive advantage: First-mover in LLM + seismic

### For Geoscience Audience (Interpreters, Geophysicists)
- Focus on workflow naturalness
- Emphasize intelligent QC recommendations
- Show how it accelerates interpretation workflows

---

## Post-Demo Discussion Points

1. **Integration with Existing Workflows**
   - "How does this fit with your Petrel/Kingdom workflows?"
   - Answer: Complementary, handles bulk extraction and QC, feeds into interpretation tools

2. **Customization**
   - "Can we train it on our specific data?"
   - Answer: Yes, can fine-tune instruction parsing, add custom QC checks

3. **OSDU Integration**
   - "How does this work with our OSDU data platform?"
   - Answer: Phase 1 integration planned, reads from OSDU storage, creates work products

4. **Pricing**
   - "How much does this cost?"
   - Answer: Consumption-based, ~$0.10 per inline, no upfront costs

5. **Security & Compliance**
   - "Where does the data go?"
   - Answer: Can deploy in customer VPC, data never leaves your cloud

---

## Success Criteria

Demo is successful if audience:
- [ ] Understands the conversational interface advantage
- [ ] Sees the autonomous agent working in background
- [ ] Recognizes the speed improvement (VDS + Elasticsearch)
- [ ] Appreciates the LLM intelligence (interpretation, recommendations)
- [ ] Asks about pricing, integration, or next steps

---

## Next Steps After Demo

1. **Provide access** - Set up trial account
2. **Onboarding call** - Map to their specific workflows
3. **Beta program** - Invite to closed beta
4. **Custom demo** - Using their actual datasets
5. **Pilot project** - 3-month pilot with 2-3 users
