# LLM Seismic Interpretation: Reality Check

## Executive Summary

This document provides an honest assessment of what Large Language Models (LLMs) can and cannot do for seismic interpretation, specifically in the context of the OpenVDS MCP server. It addresses critical questions about LLM capabilities, the "Volve effect," and how to position this technology for stakeholder demos.

**Key Takeaways:**
- LLMs have basic seismic knowledge, not expert interpretation skills
- MCP provides data access, not interpretation expertise
- Current value: Augmentation and efficiency, not replacement
- Future potential: Achievable with proper tooling and calibration

---

## Table of Contents

1. [Understanding LLM Seismic Knowledge](#understanding-llm-seismic-knowledge)
2. [The Volve Effect: Does Prior Knowledge Matter?](#the-volve-effect-does-prior-knowledge-matter)
3. [Current Capabilities vs Limitations](#current-capabilities-vs-limitations)
4. [The MCP Game-Changer](#the-mcp-game-changer)
5. [The Interpretation Spectrum](#the-interpretation-spectrum)
6. [Demo Strategy and Positioning](#demo-strategy-and-positioning)
7. [Roadmap: From Basic to Advanced](#roadmap-from-basic-to-advanced)
8. [Recommendations](#recommendations)

---

## Understanding LLM Seismic Knowledge

### What LLMs Actually "Know" About Seismic

LLMs like Claude Sonnet 4.5 have **general geological concepts** from training on textbooks, papers, and public datasets:

#### ✅ Basic Concepts They Understand

- **Seismic fundamentals:**
  - Seismic reflections represent geological boundaries
  - Reflectivity is controlled by acoustic impedance contrasts
  - Two-way time (TWT) vs depth domain

- **Structural interpretation basics:**
  - Faults appear as discontinuities in reflections
  - Normal, reverse, and strike-slip fault geometries
  - Folding and structural deformation patterns

- **Amplitude interpretation:**
  - Bright spots can indicate hydrocarbons (gas)
  - Dim spots may indicate oil accumulations
  - Amplitude anomalies require careful analysis

- **Data orientation:**
  - Inline vs crossline vs timeslice
  - 3D seismic cube navigation
  - Basic survey geometry

- **General terminology:**
  - Amplitude, frequency, phase
  - Coherence, curvature, AVO
  - Horizon, fault, channel, etc.

#### ❌ What They DON'T Really Know

- **Subtle interpretation techniques** used by experienced G&Gs
  - Play-specific interpretation workflows
  - Basin-specific calibration approaches
  - Integrated interpretation methodologies

- **Regional geology nuances** (unless extensively documented publicly)
  - Local stratigraphic frameworks
  - Basin-specific fluid indicators
  - Area-specific seismic character

- **Advanced attribute analysis**
  - Detailed AVO modeling and classification
  - Spectral decomposition interpretation
  - Seismic inversion workflows
  - Anisotropy analysis

- **Drilling risk assessment** from seismic character
  - Probability of success calculations
  - Geohazard identification
  - Wellbore stability predictions

- **Reservoir-specific signatures** in your basin
  - Lithology discrimination
  - Fluid contacts and transitions
  - Reservoir quality indicators

### Knowledge Source: Training Data

**What's in LLM training data:**
- Published papers (SPE, AAPG, SEG, etc.)
- Textbooks (Seismic Data Analysis by Yilmaz, etc.)
- Public datasets documentation (Volve, F3 Netherlands, etc.)
- Online educational content
- General geological literature

**What's NOT in training data:**
- Your proprietary seismic data
- Your company's interpretation guidelines
- Basin-specific knowledge from your geologists
- Proprietary algorithms and workflows
- Confidential well data and calibrations

**Implication:** LLMs have "book knowledge" but lack "field experience" and proprietary domain expertise.

---

## The Volve Effect: Does Prior Knowledge Matter?

### The Question

> "Using Volve for demo is kind of cheating... perhaps a new survey might not get so much success with the analysis?"

### The Answer: Partially True, But Not What You Think

**Yes, Sonnet 4.5 has some knowledge about Volve** - but this advantage is much smaller than you might fear.

### What Sonnet 4.5 Actually "Knows" About Volve

#### Public Domain Information

1. **Dataset metadata:**
   - Released by Equinor (Statoil) in 2018
   - Located in Norwegian North Sea
   - Contains wells, 3D/4D seismic, production data
   - Released for educational/research purposes

2. **General geology:**
   - Hugin Formation (primary reservoir)
   - Draupne Formation (source rock)
   - Jurassic age reservoirs
   - Structural setting in North Sea

3. **Well-documented features:**
   - Field has been produced
   - Known fault systems
   - General reservoir characteristics

#### What It Does NOT Know

- **Actual seismic amplitude values** at specific locations
- **Precise fault locations** in the 3D volume coordinates
- **Specific inline/crossline interpretations** (e.g., "inline 5234 has...")
- **Image content** until you show it via MCP
- **Detailed subsurface model** beyond published summaries

### The Real Advantage of Volve for Demo

**It's NOT about LLM memory - it's about YOUR advantage:**

| Advantage | Why It Matters |
|-----------|----------------|
| ✅ **Well-documented dataset** | You can verify AI suggestions against known interpretations |
| ✅ **Benchmark quality** | Shows what "good analysis" looks like with clean data |
| ✅ **Credibility** | Industry-standard reference dataset builds trust |
| ✅ **Teaching tool** | Audience may already know Volve, making comparison easier |
| ✅ **No confidentiality issues** | Safe to show in presentations |

### Will a "New" Survey Get Less Success?

**No - here's the detailed breakdown:**

#### What Actually Matters for Analysis

| Factor | Volve | Brand New Survey | Impact on AI Analysis |
|--------|-------|------------------|----------------------|
| **Seismic data quality** | Good (clean acquisition) | Varies | **CRITICAL** - AI needs interpretable data |
| **Structural complexity** | Moderate | Varies | More complex = harder for AI (and humans) |
| **Signal-to-noise ratio** | High | Varies | **CRITICAL** - Noise confuses pattern recognition |
| **MCP tool access** | ✅ Via OpenVDS | ✅ Via OpenVDS | **EQUAL** - Same tools work identically |
| **Visual analysis capability** | ✅ Sees images | ✅ Sees images | **EQUAL** - Same visual reasoning |
| **LLM prior knowledge** | Some metadata | None | **MINOR** - Less important than data quality |

**Key Insight:** Data quality matters far more than prior knowledge. A clean, new survey will get better analysis than a noisy, well-known survey.

### Before vs After MCP: The Real Difference

#### Before MCP (Pure LLM Memory)

```
User: "Analyze the Volve seismic dataset"

Claude: "The Volve field is located in the Norwegian North Sea.
         Based on published literature, it contains Jurassic reservoirs
         in the Hugin Formation. Typical interpretation challenges include
         fault identification and..."

         [Generic advice based on training data]
```

**For a new survey:**
```
User: "Analyze the Mystery_2025 seismic dataset"

Claude: "I don't have specific information about that survey.
         However, general seismic interpretation involves..."

         [Even more generic advice]
```

#### After MCP (Actual Data Access)

```
User: "Analyze the Volve seismic dataset"

Claude:
1. search_surveys(search_query="Volve")
2. get_survey_info(survey_id="ST10010")
3. extract_inline_image(survey_id="ST10010", inline=5000)
4. [Actually sees the seismic image]
5. "Looking at inline 5000, I observe:
    - Continuous horizontal reflections at 1200-1800ms
    - A discontinuity at crossline 3200-3400, dipping ~45° east
    - This appears to be a normal fault with ~50ms throw
    - Amplitude dimming below the fault suggests possible fluid effects
    - Recommendation: Check crosslines 3200-3400 for fault extent"

    [Specific analysis based on actual visual data]
```

**For a new survey (SAME QUALITY ANALYSIS):**
```
User: "Analyze the Mystery_2025 seismic dataset"

Claude:
1. search_surveys(search_query="Mystery_2025")
2. get_survey_info(survey_id="XYZ789")
3. extract_inline_image(survey_id="XYZ789", inline=2500)
4. [Actually sees the seismic image]
5. "Looking at inline 2500, I observe:
    - Chaotic reflections in upper 500ms suggesting shallow gas
    - Strong, continuous reflector at 1800ms (potential reservoir top)
    - Subtle amplitude variations along this horizon
    - Recommendation: Extract timeslice at 1800ms to map amplitude"

    [EQUALLY SPECIFIC analysis - no prior knowledge needed!]
```

**This works EQUALLY well for Volve or a survey acquired yesterday.**

### Proof: The Analysis is Visual, Not Memory-Based

**Test to demonstrate in your demo:**

1. **Show different inlines from Volve:**
   - Inline 5000: "I see fault A at crossline X"
   - Inline 5100: "I see different structure, fault B at crossline Y"
   - **Proves:** AI adapts based on what it SEES, not what it "remembers"

2. **Ask about random locations NOT in public docs:**
   - "What's the amplitude character at inline 5234, crossline 2891?"
   - AI must analyze actual data, can't rely on published interpretations

3. **Use a completely different survey:**
   - Show it works identically on proprietary data
   - Proves generalization

---

## Current Capabilities vs Limitations

### Phase 1: Current State (Visualization + Basic QC)

#### What Your MCP Server Does NOW

**Available tools:**
```
search_surveys          → Find datasets
get_survey_info         → Get metadata
get_facets             → Browse available filters
extract_inline_image    → Visualize inline slices
extract_crossline_image → Visualize crossline slices
extract_timeslice_image → Visualize time/depth slices
```

**Example workflow:**
```
User: "Show me inline 5000 from Volve"

Process:
1. MCP extracts amplitude data from OpenVDS
2. Generates PNG with seismic colormap
3. Compresses to <800KB
4. Returns image + metadata to Claude
5. Claude sees and analyzes the image
```

**Level of analysis currently possible:**

| Analysis Type | Capability | Example |
|---------------|------------|---------|
| **Descriptive** | ✅ Good | "I see layered reflections dipping to the east" |
| **Pattern recognition** | ✅ Basic | "This discontinuity looks like a normal fault" |
| **Anomaly detection** | ✅ Basic | "Bright amplitude at 1500ms may indicate gas" |
| **Spatial reasoning** | ✅ Good | "The fault extends from crossline 3200 to 3400" |
| **Data quality QC** | ✅ Good | "NaN values present in upper 200ms" |
| **Generic interpretation** | ✅ Basic | "Amplitude dimming may suggest fluid contact" |

**This is roughly equivalent to:**
- A smart graduate student with basic seismic training
- Someone who understands concepts but lacks field experience
- **NOT** an experienced interpreter with 20 years in your basin

#### Current Limitations

**What's missing:**

1. **No context integration:**
   - Can't access well logs for calibration
   - Can't reference regional geology
   - Can't compare to analogues

2. **No attribute analysis:**
   - No coherence for fault enhancement
   - No curvature for fracture detection
   - No AVO analysis for fluid prediction

3. **No calibration:**
   - Wells not tied to seismic
   - No synthetic seismograms
   - No velocity models

4. **No basin-specific knowledge:**
   - Doesn't know your area's typical fluid signatures
   - Can't apply local interpretation best practices
   - No historical performance data

5. **No quantitative analysis:**
   - No picks/horizons exported
   - No fault polygon generation
   - No volume/reserve calculations

### What Real G&G Interpretation Requires

**The full interpretation workflow:**

```
┌─────────────────────────────────────────────────────┐
│ 1. Data Loading & QC                               │
│    - Load seismic volumes                          │
│    - Check acquisition parameters                  │
│    - QC for noise, artifacts                       │  ← MCP can help here
│    - Assess data quality                           │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 2. Well Integration                                │
│    - Load well logs, markers                       │
│    - Tie wells to seismic (synthetic seis)         │
│    - Calibrate time-depth relationship             │  ← MCP cannot do (yet)
│    - Validate amplitude response                   │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 3. Attribute Analysis                              │
│    - Compute coherence, curvature                  │
│    - AVO analysis                                  │
│    - Spectral decomposition                        │  ← MCP cannot do (yet)
│    - Custom attributes for play type               │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 4. Structural Interpretation                       │
│    - Pick horizons                                 │
│    - Map faults                                    │
│    - Build structural framework                    │  ← Partially possible
│    - Depth conversion                              │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 5. Stratigraphic Interpretation                    │
│    - Identify facies from seismic character        │
│    - Map depositional systems                      │
│    - Correlate with well data                      │  ← MCP cannot do
│    - Predict reservoir distribution                │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 6. Reservoir Characterization                      │
│    - AVO/DHI analysis for fluids                   │
│    - Porosity/saturation prediction                │
│    - Net pay mapping                               │  ← MCP cannot do
│    - Uncertainty assessment                        │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 7. Prospect/Lead Generation                        │
│    - Integrate all data                            │
│    - Risk assessment (trap, seal, source, timing)  │
│    - Volume calculations                           │  ← MCP cannot do
│    - Well location recommendations                 │
└─────────────────────────────────────────────────────┘
```

**Current MCP server covers:** Step 1 (partially)
**Phase 2 could add:** Parts of Steps 3-4
**Phase 3+ would need:** Specialized AI models + integration framework

---

## The MCP Game-Changer

### What MCP Actually Provides

**MCP (Model Context Protocol) is NOT:**
- ❌ A seismic interpretation AI
- ❌ A replacement for interpreter expertise
- ❌ A magic solution that makes LLMs "understand" seismic

**MCP IS:**
- ✅ A **communication protocol** that gives LLMs access to external data
- ✅ A **tool framework** for structured data retrieval
- ✅ An **interface** between AI and your proprietary systems

### The Innovation: Data Access, Not Interpretation

**Before MCP:**
```
┌─────────────┐         ┌──────────────┐
│   Your      │         │     LLM      │
│  Seismic    │    X    │   (Claude)   │
│   Data      │         │              │
└─────────────┘         └──────────────┘

    No connection - LLM can only provide generic advice
```

**After MCP:**
```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│   Your      │  MCP    │     MCP      │  API    │     LLM      │
│  Seismic    │ ←────→  │    Server    │ ←────→  │   (Claude)   │
│   Data      │ Tools   │  (OpenVDS)   │ Calls   │              │
└─────────────┘         └──────────────┘         └──────────────┘

    LLM can request specific data and analyze what it receives
```

### Why This Matters

#### Traditional Workflow (Without MCP)

```
Interpreter at workstation:
1. Open Petrel/Kingdom
2. Load seismic cube
3. Navigate to inline 5000
4. Visually scan for features
5. Manually pick faults
6. Write interpretation notes
7. Generate maps
8. Create presentation

Time: Hours to days
```

**LLM can't help here - it has no access to the data.**

#### MCP-Enabled Workflow

```
Interpreter with MCP:
1. "Show me inline 5000 from Volve"
   → MCP retrieves and visualizes (2 seconds)

2. "Are there any faults visible?"
   → LLM analyzes image, identifies candidates

3. "Show me crosslines 3200-3400 to see fault extent"
   → MCP generates multiple images quickly

4. "What's the amplitude character below the fault?"
   → LLM describes observations

5. "Generate a summary of findings"
   → LLM creates documented interpretation

Time: Minutes instead of hours
```

**Value proposition: Speed + Documentation, not replacement**

### Real-World Performance Gains

**From PERFORMANCE_OPTIMIZATION.md:**

| Operation | Without Cache | With Cache | Speedup |
|-----------|--------------|------------|---------|
| Search surveys | 200-500ms | 0.001ms | **576x** |
| Get facets | 500-1000ms | 0.02ms | **10,000x** |
| Browse 2858 surveys | Manual exploration | Instant filtering | **Massive** |

**Typical conversation (7 interactions):**
- With caching: ~371ms total
- Without: ~2,500ms+
- **Overall speedup: 6.7x**

### What Makes MCP Different from Traditional Software

| Feature | Traditional Petrel Plugin | MCP Server |
|---------|---------------------------|------------|
| **Interface** | GUI buttons, scripts | Natural language |
| **Flexibility** | Fixed workflows | Conversational exploration |
| **Documentation** | Manual note-taking | Auto-generated summaries |
| **Learning curve** | Weeks of training | Immediate (if you can talk, you can use it) |
| **Customization** | Code new plugins | Just ask differently |
| **Integration** | Tight coupling to Petrel | Works with any MCP client (Claude, etc.) |

**The MCP advantage:** Lower barrier to entry, faster iteration, better documentation.

---

## The Interpretation Spectrum

### Where LLMs Fit in the Skill Hierarchy

```
BASIC                    INTERMEDIATE                 EXPERT
(LLM can do NOW)         (LLM could do with tools)    (LLM cannot do yet)
│                        │                            │
├─ Navigate volumes      ├─ Fault picking             ├─ Drilling risk assessment
├─ Describe patterns     ├─ Horizon tracking          ├─ Reservoir prediction
├─ Spot obvious faults   ├─ Attribute analysis        ├─ Basin-specific calibration
├─ QC data quality       ├─ AVO classification        ├─ Prospect ranking
├─ Generate viz          ├─ Coherence interpretation  ├─ Well placement
├─ Document findings     ├─ Feature detection         ├─ Reserve estimation
│                        │                            │
▼                        ▼                            ▼
Phase 1 (COMPLETE)       Phase 2 (ACHIEVABLE)         Phase 3 (RESEARCH NEEDED)
```

### Phase 1: Current Capabilities (Complete)

**Tools available:**
- Search and browse 2858+ VDS datasets
- Extract and visualize inline/crossline/timeslice images
- Apply seismic colormaps (classic, grayscale, Petrel-style)
- Basic amplitude statistics
- Multi-level caching for performance

**Use cases:**
- ✅ Quick data exploration: "What surveys do we have in Santos Basin?"
- ✅ Rapid visualization: "Show me inline 5000"
- ✅ QC workflows: "Check for NaN values in this survey"
- ✅ Documentation: "Summarize what you see in this inline"
- ✅ Teaching: Show new hires how to read seismic

**Limitations:**
- No quantitative picking
- No attribute computation
- No well integration
- Basic pattern recognition only

### Phase 2: Achievable Next Steps (3-6 months)

**Proposed additional tools:**

#### Attribute Computation
```python
compute_coherence_slice(survey_id, inline, method='eigenstructure')
compute_curvature_slice(survey_id, inline, type='most_positive')
extract_amplitude_envelope(survey_id, inline)
```

**Value:** Enhance fault/fracture detection

#### Fault Detection Assistance
```python
detect_fault_candidates(survey_id, inline_range, confidence_threshold=0.7)
suggest_interpretation_priorities(survey_id, anomaly_type='structural')
```

**Value:** Guide interpreter where to focus effort

#### Well Integration (if well data available)
```python
get_wells_in_survey(survey_id)
get_well_markers(well_id)
overlay_well_on_seismic(survey_id, inline, well_id)
```

**Value:** Calibration and validation

#### Multi-Slice Analysis
```python
extract_inline_sequence(survey_id, inline_start, inline_end, step=10)
compare_slices(image_list, highlight_differences=True)
```

**Value:** Track features across volume

**Expected capabilities:**
- ✅ Fault candidate detection (not definitive picking)
- ✅ Anomaly prioritization (where to look first)
- ✅ Basic attribute interpretation (coherence = fault proxy)
- ✅ Pattern tracking across slices
- ⚠️ Still requires expert validation

**Use cases:**
- "Find potential fault zones in this survey"
- "Show me areas with amplitude anomalies"
- "Which inlines should I focus on for structural interpretation?"

### Phase 3: Advanced Capabilities (12+ months, requires research)

**Would require:**

1. **Specialized AI models:**
   - Not general-purpose LLMs
   - Models trained specifically on seismic data
   - Fine-tuned on your basin's geology

2. **Comprehensive integration:**
   - Well logs, production data
   - Regional geological models
   - Historical interpretation database

3. **Quantitative workflows:**
   - Automated horizon tracking
   - Fault polygon generation
   - Volume calculations
   - Uncertainty quantification

4. **Basin-specific training:**
   - Learn from your company's historical interpretations
   - Calibrate to your area's fluid signatures
   - Incorporate proprietary knowledge

**Expected capabilities:**
- ✅ Semi-automated interpretation (with human oversight)
- ✅ Basin-aware fluid prediction
- ✅ Risk-assessed prospect generation
- ✅ Integration with drilling/production data

**Use cases:**
- "Generate fault framework for this survey"
- "Predict reservoir distribution based on wells + seismic"
- "Rank leads by probability of success"

**Still NOT:**
- ❌ Fully autonomous interpretation
- ❌ Replacement for expert judgment
- ❌ Guaranteed drilling success

---

## Demo Strategy and Positioning

### The Demo Dilemma: Volve vs Proprietary Data

#### Option 1: Use Volve Only

**Pros:**
- ✅ Safe, no confidentiality concerns
- ✅ Known dataset - audience can verify results
- ✅ Shows proof of concept clearly
- ✅ Well-documented for comparison

**Cons:**
- ⚠️ Might trigger "but you trained on Volve!" skepticism
- ⚠️ Doesn't prove generalization to unseen data
- ⚠️ May seem like cherry-picking

**When to use:**
- Initial demo to non-technical stakeholders
- Public presentations
- Teaching/training sessions

#### Option 2: Use Proprietary Survey Only

**Pros:**
- ✅ **Proves zero prior knowledge** - strongest demonstration
- ✅ Shows real-world applicability
- ✅ More impressive to technical stakeholders
- ✅ Builds confidence in production use

**Cons:**
- ⚠️ Data security concerns (you mentioned oil companies are cautious)
- ⚠️ Results less verifiable (no ground truth)
- ⚠️ Data quality issues may confuse demo
- ⚠️ May not be as "clean" as Volve

**When to use:**
- Internal team presentations
- Technical stakeholders who understand the technology
- When data classification allows

#### Option 3: Hybrid Approach (RECOMMENDED)

**Structure:**

```
Part 1: MCP Concept with Volve (5 minutes)
├─ Explain what MCP is
├─ Show basic workflow (search → visualize → analyze)
├─ Acknowledge: "Yes, this is public domain"
└─ Purpose: Demonstrate the MECHANISM

Part 2: Real-World Application with Proprietary Data (10 minutes)
├─ "Now let's try a survey Claude has NEVER seen"
├─ Show same tools work identically
├─ Prove generalization
├─ Demonstrate real value for your workflows
└─ Purpose: Prove APPLICABILITY

Part 3: Address Skepticism Head-On (5 minutes)
├─ "Does the LLM 'remember' Volve? Somewhat - metadata only"
├─ "Does it remember YOUR seismic? No - seeing it for first time"
├─ "The analysis is visual pattern recognition, not memorization"
└─ Show proof: Different inlines = different analysis
```

**Why this works:**
- Builds understanding with safe example
- Proves capability with real data
- Addresses concerns proactively
- Shows both concept AND value

### Recommended Demo Script

#### Slide 1: The Problem

```
Current Seismic Interpretation Workflow:

1. Open Petrel/Kingdom (slow startup)
2. Load seismic cube (minutes)
3. Manual navigation (click, click, click...)
4. Visual analysis (hours)
5. Manual documentation (tedious)
6. Share findings (screenshots, PowerPoint)

Time: Hours to days per survey
Barrier: Requires specialized software + training
Documentation: Manual, inconsistent
```

#### Slide 2: The MCP Solution

```
What is MCP?

MCP = Model Context Protocol (by Anthropic)
- Open standard for AI to access external data
- Like an API, but conversational
- Connects LLMs to your tools/data

Our Implementation:
- OpenVDS MCP Server
- Access to 2858+ VDS seismic datasets
- Natural language interface via Claude
```

#### Slide 3: Live Demo Part 1 - Volve (Proof of Concept)

**Script:**
```
"Let's start with Volve - a public domain dataset -
to show HOW the technology works."

Demo:
1. "What VDS datasets are available?"
   → Shows facets (regions, years, types)

2. "Show me the Volve survey"
   → Retrieves ST10010 metadata

3. "Extract inline 5000"
   → Generates seismic image in 2 seconds

4. "What do you see?"
   → Claude describes: faults, amplitudes, structure

5. "Show me crosslines 3200 to 3400"
   → Rapid multi-image generation

Acknowledge: "Yes, Claude has some general knowledge about
Volve from public documentation. But notice - it's analyzing
the ACTUAL pixel patterns, not reciting memorized facts."
```

#### Slide 4: Live Demo Part 2 - Proprietary Data (Proof of Generalization)

**Script:**
```
"Now let's try a survey that Claude has NEVER seen before -
one of OUR proprietary datasets."

Demo:
1. "Search for [YourBasin] surveys from 2024"
   → Shows results Claude couldn't have known

2. "Show me inline 2500 from [SurveyX]"
   → Same 2-second visualization

3. "Analyze this inline"
   → Claude provides EQUALLY SPECIFIC analysis:
       - Identifies features
       - Describes amplitude character
       - Suggests follow-up analyses

4. "Compare this to inline 2600"
   → Tracks changes, identifies trends

Emphasize: "Same quality analysis. Same speed.
No prior knowledge needed. This is the power of MCP -
giving AI EYES to see your actual data."
```

#### Slide 5: What It Can Do (Current - Phase 1)

```
✅ Rapid Data Exploration
   - Search 2858+ surveys in milliseconds
   - Filter by region, year, type

✅ Fast Visualization
   - Any inline/crossline/timeslice in 2 seconds
   - vs minutes in traditional software

✅ Basic Analysis
   - Describe patterns
   - Identify obvious features (faults, amplitudes)
   - QC data quality

✅ Automated Documentation
   - Natural language summaries
   - Copy-paste ready for reports

✅ Lower Barrier to Entry
   - No specialized software training needed
   - If you can talk, you can explore seismic
```

#### Slide 6: What It Cannot Do (Honest Limitations)

```
❌ Does NOT Replace Expert Interpreters
   - Basic pattern recognition, not 20 years of experience
   - No basin-specific calibration (yet)
   - No integration with wells, production data (yet)

❌ Does NOT Provide Definitive Interpretations
   - Suggestions, not drilling decisions
   - Always requires expert validation
   - Think: Smart assistant, not autonomous geophysicist

❌ Does NOT Handle Full Workflows
   - No quantitative picking (yet)
   - No attribute computation (yet)
   - No risk assessment (yet)

Current Level: Graduate student with basic training
NOT: Senior geophysicist with basin expertise
```

#### Slide 7: Value Proposition

```
What This Gives You TODAY:

⏱️ Time Savings
   - Quick-look QC: Minutes instead of hours
   - Rapid browsing: 2 sec/image vs manual navigation
   - Automated documentation: Copy-paste summaries

🎯 Efficiency Gains
   - Search 2858 surveys instantly vs manual catalog
   - 576x faster queries (with caching)
   - 10,000x faster facet browsing

📚 Knowledge Sharing
   - Lower barrier for new hires
   - Consistent documentation format
   - Easy collaboration (share conversation links)

🔬 Exploration Support
   - "Show me all surveys with [feature]"
   - Pattern recognition across datasets
   - Hypothesis testing at conversation speed
```

#### Slide 8: Addressing Data Security Concerns

**The Concern:**
> "Oil companies are reluctant to send data to the cloud"

**The Solutions:**

```
1. On-Premise Deployment via AWS Bedrock
   ├─ Run Claude in YOUR AWS VPC
   ├─ Data never leaves your infrastructure
   ├─ Full control over data flows
   └─ Example: Woodside Energy uses Claude via AWS

2. Data Classification Strategy
   ├─ Use MCP for non-confidential exploration data
   ├─ Keep drilling decisions on traditional systems
   ├─ Hybrid approach: AI for efficiency, humans for risk
   └─ Progressive adoption as confidence builds

3. Industry Precedents
   ├─ ExxonMobil: Partnered with Microsoft for AI/cloud
   ├─ Shell: Uses Google Cloud for seismic processing
   ├─ BP: AWS partnership for subsurface analytics
   ├─ Equinor: Released Volve to encourage AI research
   └─ Trend: Increasing AI adoption with proper governance
```

**Key Message:**
> "This is NOT about sending data to OpenAI's servers.
> It's about using AI WITHIN your security perimeter,
> accessing YOUR data, on YOUR infrastructure."

#### Slide 9: Roadmap

```
Phase 1: Visualization + Basic QC ✅ COMPLETE
├─ Search and browse datasets
├─ Extract inline/crossline/timeslice images
├─ Basic amplitude statistics
├─ Performance optimization (caching)
└─ Natural language interface

Phase 2: Fault Detection Assistance 🔄 NEXT (3-6 months)
├─ Coherence/curvature computation
├─ Fault candidate detection
├─ Anomaly prioritization
├─ Well overlay (if available)
└─ Multi-slice pattern tracking

Phase 3: Advanced Integration 🔮 FUTURE (12+ months)
├─ Basin-specific fine-tuning
├─ Well log integration
├─ Quantitative workflows
├─ Risk assessment support
└─ Prospect generation assistance
```

#### Slide 10: Call to Action

```
How to Get Started:

1. Pilot Program
   ├─ Select non-confidential dataset
   ├─ 2-week trial with your interpretation team
   ├─ Measure time savings vs traditional workflow
   └─ Gather feedback for Phase 2 priorities

2. Infrastructure Setup
   ├─ Deploy on your AWS/Azure (if security required)
   ├─ Or use Anthropic's Claude Pro (for faster start)
   ├─ Connect to your VDS data
   └─ Configure user access

3. Success Metrics
   ├─ Time saved on quick-look QC
   ├─ Number of surveys explored per day
   ├─ Documentation quality improvement
   └─ User satisfaction scores

Next Steps: [Your specific ask - budget approval, pilot approval, etc.]
```

### Handling Tough Questions

#### Q: "Why not just use Petrel? We already have it."

**A:**
> "Great question. Petrel is excellent for detailed interpretation work,
> and we're not replacing that. This is for a DIFFERENT use case:
>
> - Quick exploration: 'Show me all surveys with X characteristic'
> - Rapid QC: 'Check these 20 surveys for data quality issues'
> - Documentation: 'Summarize findings in natural language'
> - Lower barrier: New hires can explore data from day 1
>
> Think of it as complementary: MCP for breadth, Petrel for depth."

#### Q: "How do I know the AI's interpretations are correct?"

**A:**
> "You don't - and you shouldn't trust them blindly. That's why we position
> this as an ASSISTANT, not an autonomous interpreter.
>
> Current workflow:
> 1. AI suggests: 'Potential fault at crossline 3200-3400'
> 2. YOU verify: Load in Petrel, check with wells, validate
> 3. YOU decide: Is this worth pursuing?
>
> The value is in SPEED - AI scans 100 inlines in minutes, points you
> to interesting areas, then YOU do the expert validation. It's like having
> a junior interpreter do the first pass."

#### Q: "What if it hallucinates or gives wrong answers?"

**A:**
> "LLMs can hallucinate when asked about things they don't know.
> But here's the key difference with MCP:
>
> WITHOUT MCP (bad):
> User: 'Tell me about inline 5000 in survey X'
> AI: [Makes something up - no data access]
>
> WITH MCP (better):
> User: 'Tell me about inline 5000 in survey X'
> AI: [Calls extract_inline_image, SEES actual data, describes what's visible]
>
> The MCP grounding reduces hallucination significantly. But yes,
> always verify important interpretations - same as you would with
> a junior team member."

#### Q: "This seems expensive. What's the ROI?"

**A:**
> "Let's do the math on just ONE use case - quick-look QC:
>
> Traditional approach:
> - Senior geophysicist: $150/hour
> - Time to QC 20 surveys manually: ~10 hours
> - Cost: $1,500
>
> MCP approach:
> - Same person asks: 'QC these 20 surveys for data quality'
> - AI scans all 20, flags 3 with issues: ~30 minutes
> - Human validates the 3 flagged surveys: ~2 hours
> - Cost: $375 (75% savings)
>
> Now multiply by:
> - How many QC tasks per month?
> - How many exploration campaigns?
> - How much faster can new hires contribute?
>
> Plus intangibles:
> - Better documentation
> - Knowledge retention
> - Faster decision cycles"

#### Q: "Won't this make geophysicists obsolete?"

**A:**
> "No. This is like asking if Excel made accountants obsolete.
>
> What happened with Excel:
> - Eliminated tedious manual calculations
> - Allowed accountants to focus on analysis and strategy
> - Created MORE demand for skilled analysts who could use the tools
>
> What will happen with MCP:
> - Eliminates tedious data wrangling
> - Allows geophysicists to focus on complex interpretation
> - Creates demand for G&Gs who can leverage AI effectively
>
> The interpreters who LEARN to use these tools will be far more
> productive than those who don't. It's augmentation, not replacement."

---

## Roadmap: From Basic to Advanced

### Phase 1: Visualization + Basic QC ✅ COMPLETE

**Delivered capabilities:**

| Feature | Status | Performance |
|---------|--------|-------------|
| Search surveys | ✅ | <15ms (cached: 0.001ms) |
| Get facets | ✅ | ~207ms (cached: 0.02ms) |
| Extract inline images | ✅ | ~2 seconds |
| Extract crossline images | ✅ | ~2 seconds |
| Extract timeslice images | ✅ | ~2 seconds |
| Seismic colormaps | ✅ | Classic, Gray, Petrel |
| Metadata queries | ✅ | Instant |
| Multi-level caching | ✅ | 576x-10,000x speedup |

**Technical stack:**
- OpenVDS 3.4.6 for data access
- Elasticsearch 8.11 for metadata (2858 surveys)
- Docker containerized deployment
- MCP protocol via Anthropic Claude
- Matplotlib + Pillow for visualization
- LRU caching for performance

**Use cases enabled:**
- ✅ Quick-look exploration
- ✅ Data quality QC
- ✅ Survey discovery and filtering
- ✅ Basic amplitude analysis
- ✅ Natural language documentation

**What's still manual:**
- Detailed fault picking
- Horizon tracking
- Attribute analysis
- Well integration

### Phase 2: Fault Detection Assistance 🔄 NEXT

**Timeline:** 3-6 months
**Status:** Design phase

**Proposed new tools:**

#### 1. Attribute Computation

```python
# Tool: compute_coherence_slice
compute_coherence_slice(
    survey_id: str,
    inline: int,
    method: str = 'eigenstructure',  # or 'semblance'
    window_size: int = 5
) -> dict

# Returns:
{
    "coherence_image": bytes,  # PNG visualization
    "statistics": {
        "mean": 0.78,
        "std": 0.12,
        "min": 0.23,
        "max": 0.99
    },
    "low_coherence_zones": [  # Potential faults
        {"crossline_range": [3200, 3250], "confidence": 0.85},
        {"crossline_range": [4100, 4180], "confidence": 0.72}
    ]
}
```

**Other attributes:**
- `compute_curvature_slice()` - Most positive/negative curvature
- `compute_amplitude_envelope()` - Instantaneous amplitude
- `compute_cosine_phase()` - Phase analysis

**Value:** Enhance fault/fracture visibility beyond raw amplitude

#### 2. Fault Candidate Detection

```python
# Tool: detect_fault_candidates
detect_fault_candidates(
    survey_id: str,
    inline_range: tuple[int, int],
    confidence_threshold: float = 0.7,
    min_throw_ms: int = 20
) -> dict

# Returns:
{
    "candidates": [
        {
            "inline_range": [4990, 5120],
            "crossline_range": [3200, 3400],
            "estimated_throw_ms": 45,
            "dip_direction": "east",
            "confidence": 0.85,
            "evidence": ["coherence_low", "amplitude_offset", "reflection_termination"]
        }
    ],
    "summary_image": bytes,  # Map view showing all candidates
    "recommendation": "Focus on candidate #1 (highest confidence)"
}
```

**Algorithm approach:**
- Edge detection on coherence volumes
- Amplitude discontinuity tracking
- Reflection termination analysis
- Supervised learning from labeled examples (if available)

**Value:** Guide interpreter where to focus detailed picking effort

#### 3. Well Integration

```python
# Tool: get_wells_in_survey
get_wells_in_survey(survey_id: str) -> list

# Tool: overlay_well_on_seismic
overlay_well_on_seismic(
    survey_id: str,
    inline: int,
    well_id: str,
    show_markers: bool = True
) -> dict

# Returns:
{
    "image": bytes,  # Seismic with well path overlay
    "well_intersection": {
        "crossline": 3245,
        "twt_ms": [1200, 2800],  # Well trajectory through inline
        "markers": [
            {"name": "Top_Reservoir", "twt_ms": 1850, "md": 2450},
            {"name": "Base_Reservoir", "twt_ms": 1920, "md": 2580}
        ]
    }
}
```

**Value:** Calibration and validation of seismic interpretation

#### 4. Multi-Slice Analysis

```python
# Tool: extract_inline_sequence
extract_inline_sequence(
    survey_id: str,
    inline_start: int,
    inline_end: int,
    step: int = 10,
    create_animation: bool = False
) -> dict

# Returns:
{
    "images": [bytes, bytes, ...],  # Individual PNG files
    "animation": bytes,  # Optional GIF animation
    "analysis": {
        "tracked_features": [
            {
                "feature_type": "fault",
                "inline_range": [5000, 5200],
                "crossline_range": [3200, 3400],
                "trend": "dip_increasing_eastward"
            }
        ]
    }
}
```

**Value:** Track features across volume, identify trends

**Implementation requirements:**
- Add scipy for signal processing
- Add scikit-image for edge detection
- Well data access (if available in OpenVDS or separate DB)
- Additional compute time for attributes (~5-10 sec per slice)

**Expected user experience:**
```
User: "Find potential faults in survey ST10010, inlines 5000-5500"

MCP:
1. Computes coherence for inline range
2. Detects low-coherence zones
3. Filters by size/throw criteria
4. Returns ranked list of candidates

Claude: "I found 3 high-confidence fault candidates:

1. Inline 5050-5180, Crossline 3200-3400 (confidence: 85%)
   - Estimated throw: ~45ms
   - Dipping east
   - Recommend: Start detailed picking here

2. Inline 5230-5290, Crossline 4100-4180 (confidence: 72%)
   - Estimated throw: ~30ms
   - Sub-vertical
   - Recommend: Verify with crossline views

3. Inline 5410-5480, Crossline 2800-2950 (confidence: 68%)
   - Estimated throw: ~25ms
   - Recommend: Check if artifact or real structure

Should I generate detailed images for any of these candidates?"
```

**Limitations of Phase 2:**
- Still not definitive picking (requires expert validation)
- Confidence scores are estimates, not guarantees
- May miss subtle faults or flag artifacts as faults
- Best for moderate-to-good quality data

### Phase 3: Advanced Integration 🔮 RESEARCH

**Timeline:** 12+ months
**Status:** Conceptual

**Would require:**

#### 1. Specialized AI Models

**Current:** General-purpose LLMs (Claude Sonnet 4.5)
- Trained on broad internet corpus
- Good at language, reasoning, visual patterns
- NOT trained specifically on seismic

**Phase 3:** Domain-specific models
- Pre-trained on large seismic datasets
- Fine-tuned on your basin's geology
- Optimized for interpretation tasks

**Examples:**
- FaultSeg (research model for fault detection)
- SeismicNet (MIT research)
- Custom models trained on your historical interpretations

**Challenges:**
- Requires large labeled dataset (1000s of interpreted surveys)
- Compute-intensive training
- Ongoing model maintenance
- Validation against ground truth

#### 2. Comprehensive Data Integration

**Current:** Seismic only

**Phase 3:** Multi-modal integration
```
┌─────────────────────────────────────────────────────┐
│ Integrated Subsurface Model                        │
├─────────────────────────────────────────────────────┤
│ • 3D/4D Seismic volumes                            │
│ • Well logs (GR, resistivity, density, etc.)       │
│ • Well markers and stratigraphic tops              │
│ • Core data and facies descriptions                │
│ • Production data (rates, pressures, fluids)       │
│ • Regional geological framework                    │
│ • Analogues from offset fields                     │
│ • Geochemistry (source rock, fluid typing)         │
└─────────────────────────────────────────────────────┘
                      ↓
          AI-Integrated Interpretation
```

**Enables:**
- Seismic-well ties with AI-suggested adjustments
- Facies prediction from seismic + well logs
- Fluid prediction from AVO + production history
- Risk assessment using analogue database

#### 3. Quantitative Workflows

**Auto-picking with QC:**
```python
# Tool: auto_track_horizon
auto_track_horizon(
    survey_id: str,
    seed_point: dict,  # {inline: 5000, crossline: 3200, twt: 1850}
    tracking_parameters: dict
) -> dict

# Returns:
{
    "horizon_surface": {
        "grid": np.array,  # 2D surface in TWT
        "quality_flags": np.array,  # Confidence per grid cell
        "total_picks": 125000,
        "high_confidence_pct": 87.5
    },
    "qc_locations": [
        {"inline": 5123, "crossline": 3456, "issue": "low_confidence"},
        # ... areas needing manual review
    ],
    "statistics": {...}
}
```

**Fault polygons:**
```python
# Tool: generate_fault_polygon
generate_fault_polygon(
    survey_id: str,
    fault_candidate_id: str,
    refinement_level: int = 2
) -> dict

# Returns:
{
    "fault_sticks": [...],  # 3D polylines
    "fault_surface": {...},  # Triangulated mesh
    "throw_map": np.array,
    "export_formats": {
        "petrel": bytes,  # .dat format
        "charisma": bytes
    }
}
```

**Volume calculations:**
```python
# Tool: calculate_prospect_volume
calculate_prospect_volume(
    survey_id: str,
    top_horizon: str,
    base_horizon: str,
    polygon_boundary: list,
    porosity_model: str
) -> dict

# Returns GRV, uncertainties, etc.
```

#### 4. Basin-Specific Fine-Tuning

**Concept:** Train AI on YOUR company's interpretation history

**Data required:**
- 100+ interpreted surveys from your basin
- Labeled faults, horizons, prospects
- Outcomes (dry holes, producers, reserves)
- Interpreter notes and rationales

**Process:**
1. Extract interpretation data from Petrel/Kingdom
2. Create labeled training set
3. Fine-tune base model on your data
4. Validate against held-out surveys
5. Deploy custom model via MCP

**Benefits:**
- AI learns YOUR basin's geological patterns
- AI learns YOUR team's interpretation standards
- Higher accuracy for basin-specific features
- Incorporates proprietary knowledge

**Challenges:**
- Data privacy/security (model training location)
- Requires significant data volume
- Ongoing maintenance as new data acquired
- Validation and quality control

**Example use case:**
```
Generic LLM: "This bright spot might indicate gas or salt"
(Uncertain, general knowledge)

Basin-tuned model: "In this basin, bright spots at this depth
with this AVO character have historically been gas sands
(8/10 wells successful). Recommend Class 3 AVO analysis."
(Specific, calibrated to your area)
```

### Phase Comparison Matrix

| Capability | Phase 1 | Phase 2 | Phase 3 |
|-----------|---------|---------|---------|
| **Data Access** | Seismic only | Seismic + basic wells | Full integration |
| **Visualization** | ✅ Excellent | ✅ Enhanced | ✅ Advanced |
| **Fault Detection** | ❌ Manual only | ⚠️ Candidate suggestions | ✅ Semi-automated |
| **Horizon Tracking** | ❌ None | ❌ None | ✅ Auto-track + QC |
| **Attribute Analysis** | ❌ None | ✅ Basic | ✅ Advanced |
| **Well Integration** | ❌ None | ⚠️ Basic overlay | ✅ Full tie + calibration |
| **Quantitative Output** | ❌ None | ❌ None | ✅ Picks, polygons, volumes |
| **Basin Calibration** | ❌ Generic | ❌ Generic | ✅ Custom-trained |
| **Risk Assessment** | ❌ None | ❌ None | ⚠️ Basic |
| **Production Ready** | ✅ Yes (QC, exploration) | ⚠️ Pilot projects | ⚠️ Supervised use |

**Timeline summary:**
- **Phase 1:** Complete (demo ready)
- **Phase 2:** 3-6 months (with dedicated development)
- **Phase 3:** 12-24 months (research + validation required)

---

## Recommendations

### For Your Demo

**1. Use the Hybrid Approach**
- Start with Volve (explain mechanism)
- Switch to proprietary data (prove generalization)
- Address skepticism head-on

**2. Be Honest About Limitations**
- Don't oversell current capabilities
- Position as "augmentation, not replacement"
- Show clear roadmap from current to future

**3. Focus on Measurable Value**
- Time savings (quantify in dollars)
- Lower barrier to entry (training cost reduction)
- Better documentation (compliance, knowledge retention)

**4. Prepare for Tough Questions**
- Data security → AWS Bedrock solution
- Accuracy concerns → Validation workflow
- ROI questions → Concrete use case math

### For Phase 2 Planning

**1. Prioritize Based on User Feedback**
- Which features would save the most time?
- What are current pain points?
- Where is manual work most tedious?

**2. Start with Low-Hanging Fruit**
- Coherence computation (well-established algorithm)
- Multi-slice extraction (simple extension)
- Well overlay (if well data accessible)

**3. Build Validation Framework**
- Test against known interpretations
- Measure accuracy on labeled datasets
- Define acceptance criteria before development

**4. Maintain Transparency**
- Show confidence scores
- Flag uncertain results
- Always provide review mechanism

### For Long-Term Strategy

**1. Data Collection**
- Start archiving interpretations systematically
- Label datasets for future training
- Document outcomes (wells, production)

**2. Industry Partnerships**
- Collaborate with other operators on generic tools
- Share non-competitive development costs
- Build industry standards for AI interpretation

**3. Incremental Adoption**
- Use MCP for low-risk exploration
- Build confidence gradually
- Expand to higher-stakes decisions as validation improves

**4. Talent Development**
- Train G&Gs to use AI tools effectively
- Don't see it as job threat, see as skill enhancement
- Reward those who leverage AI for productivity

### Key Messages to Emphasize

**1. MCP Gives LLMs Eyes, Not Expertise**
- The innovation is DATA ACCESS
- Interpretation skill comes from training/experience
- Current LLMs have basic knowledge, not expert calibration

**2. Augmentation, Not Replacement**
- Think Excel for accountants
- Eliminates tedious work
- Allows focus on high-value analysis

**3. The Volve Effect is Small**
- Visual analysis >> prior knowledge
- Works equally well on new surveys
- Proof: Show diverse examples

**4. Security is Solvable**
- On-premise deployment available
- Industry precedents exist
- It's about governance, not prohibition

**5. Realistic Roadmap**
- Phase 1: Production ready for QC/exploration
- Phase 2: Achievable with standard algorithms
- Phase 3: Requires research, but similar to industry trends

---

## Conclusion

### The Bottom Line

**Question:** "Do LLMs know how to analyze seismic?"

**Answer:**
- **Basic analysis:** Yes (pattern recognition, description)
- **Intermediate analysis:** Possible with MCP tool augmentation
- **Expert analysis:** No (requires specialization + calibration)

**Question:** "Is using Volve for demo cheating?"

**Answer:**
- LLMs have basic metadata knowledge about Volve
- But actual analysis is VISUAL, not memory-based
- Works equally well on brand new surveys
- Use hybrid demo: Volve (concept) + Proprietary (proof)

**Question:** "What's the real value?"

**Answer:**
- **Time savings:** 576x faster queries, minutes vs hours for QC
- **Lower barrier:** Natural language vs specialized software
- **Better documentation:** Auto-generated summaries
- **Efficiency:** Explore 2858 surveys at conversation speed

### The Honest Pitch

**What we've built:**
> "An MCP server that gives Claude visual access to seismic data.
> It can rapidly explore volumes, generate visualizations, describe
> patterns, and assist with QC workflows. It's like having a smart
> assistant who can navigate Petrel at conversation speed."

**What it's NOT:**
> "This is not a replacement for expert geophysicists. It's not making
> drilling decisions. It's not trained on your basin's specific geology.
> It's a productivity tool, not an autonomous interpreter."

**Where we're going:**
> "Phase 1 (complete) proves the concept. Phase 2 (3-6 months) will add
> fault detection assistance and attribute analysis. Phase 3 (research)
> could enable basin-specific fine-tuning and semi-automated workflows.
> But each phase requires validation, and humans remain in the loop."

**Why you should care:**
> "Because interpretation workflows haven't fundamentally changed in 20 years.
> We're still clicking through inlines manually. We're still copy-pasting
> screenshots into PowerPoint. We're still training people for months before
> they're productive. MCP changes that. And early adopters will have a
> significant competitive advantage in exploration efficiency."

---

## Appendix: Technical Implementation Notes

### Current Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Claude Desktop                         │
│                     (MCP Client via API)                      │
└───────────────────────────┬──────────────────────────────────┘
                            │ MCP Protocol (stdio/HTTP)
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                   OpenVDS MCP Server                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tool Handlers (Python)                              │   │
│  │  - search_surveys                                    │   │
│  │  - get_survey_info                                   │   │
│  │  - get_facets                                        │   │
│  │  - extract_inline_image                              │   │
│  │  - extract_crossline_image                           │   │
│  │  - extract_timeslice_image                           │   │
│  │  - get_cache_stats                                   │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  VDS Client (src/vds_client.py)                      │   │
│  │  - OpenVDS data access                               │   │
│  │  - Elasticsearch metadata client                     │   │
│  │  - SeismicVisualizer integration                     │   │
│  │  - Multi-level LRU caching                           │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────┬────────────────────┬─────────────────────┘
                    │                    │
                    ↓                    ↓
        ┌──────────────────┐  ┌──────────────────┐
        │  Elasticsearch   │  │  VDS Data Files  │
        │  (Metadata)      │  │  (OpenVDS)       │
        │  2858 surveys    │  │  /vds-data       │
        └──────────────────┘  └──────────────────┘
```

### Performance Characteristics

**Current (Phase 1):**
- Search query (first): ~14ms
- Search query (cached): ~0.001ms (576x faster)
- Facets (first): ~207ms
- Facets (cached): ~0.02ms (10,000x faster)
- Image extraction: ~2 seconds (includes OpenVDS read + PNG generation)
- Image size: <800KB (compressed to fit MCP 1MB limit)

**Caching strategy:**
- Search cache: 100 queries, 5 min TTL
- Facets cache: 50 facets, 15 min TTL
- LRU eviction policy

### Data Flow Example

```
User: "Show me inline 5000 from Volve"
    ↓
Claude interprets intent
    ↓
Claude calls MCP tool: extract_inline_image(
    survey_id="ST10010",
    inline=5000,
    colormap="seismic"
)
    ↓
MCP server receives request
    ↓
VDS Client:
1. Looks up survey metadata in Elasticsearch
2. Opens VDS file via OpenVDS
3. Extracts 2D amplitude slice [crosslines × samples]
4. Passes to SeismicVisualizer
    ↓
SeismicVisualizer:
1. Creates matplotlib figure
2. Applies seismic colormap (Red-White-Blue)
3. Adds annotations (labels, colorbar, statistics)
4. Renders to PNG
5. Compresses if >800KB
    ↓
Returns to MCP server:
{
    "image_data": bytes (PNG),
    "survey_id": "ST10010",
    "inline_number": 5000,
    "statistics": {"min": -1234, "max": 5678, "mean": 123},
    "image_size_kb": 456
}
    ↓
MCP server formats as MCP response:
[
    ImageContent(data=base64_png, mimeType="image/png"),
    TextContent(text=json_metadata)
]
    ↓
Claude receives image + metadata
    ↓
Claude analyzes image visually
    ↓
Claude responds to user: "Here's inline 5000. I observe..."
```

**Total latency:** ~2-3 seconds from request to display

---

**Document Version:** 1.0
**Last Updated:** 2025-10-21
**Author:** OpenVDS MCP Server Team
**Purpose:** Demo preparation and stakeholder communication
