# Domain-Aware Anti-Hallucination Implementation Plan

**Purpose:** Address architect feedback on geophysically meaningless interpretations and implement domain-aware interpretation layer

**Context:** While Data Integrity Agent prevents statistical hallucinations, we need to prevent *geophysically meaningless* interpretations like cross-survey amplitude comparisons.

**Target Completion:** 4-6 weeks
**Priority:** HIGH - Critical for geoscientist credibility

---

## Executive Summary

### The Problem
Current system can produce statistically accurate but geophysically nonsensical statements:
- ❌ "Sepia has 15-30x HIGHER amplitudes than BS500!" (meaningless - no absolute units)
- ❌ Comparing raw amplitudes across surveys (different gain/processing)
- ❌ Superficial stats without domain context (SNR, frequency content, etc.)

### The Solution
Implement domain-aware interpretation layer with:
- ✅ Cross-survey comparison warnings and guardrails
- ✅ Normalized amplitude metrics (geophysically meaningful)
- ✅ Quality Assessment Agent (SNR, frequency, continuity)
- ✅ Geoscientist validation loop
- ✅ Geospatial awareness for regional analysis

---

## Phase 1: Immediate Fixes (Week 1)
**Goal:** Stop producing geophysically meaningless comparisons NOW

### TODO 1.1: Add Cross-Survey Comparison Warnings
**Priority:** CRITICAL
**Effort:** 2 hours
**Files to modify:**
- `/src/openvds_mcp_server.py` (tool descriptions)
- Create new file: `/src/domain_warnings.py` (comparison validators)

**Tasks:**
- [ ] Create `domain_warnings.py` module with:
  - [ ] `detect_cross_survey_comparison()` - Detects when multiple survey_ids in context
  - [ ] `generate_amplitude_comparison_warning()` - Returns standardized warning
  - [ ] `validate_comparison_context()` - Checks if normalization mentioned

- [ ] Update ALL image extraction tool descriptions with:
  ```
  ⚠️ AMPLITUDE INTERPRETATION WARNING:
  Raw amplitude values have NO absolute physical units and vary by:
  - Acquisition equipment (different receivers/sources)
  - Processing workflows (different gain/scaling)
  - Arbitrary scaling factors

  RULES FOR AMPLITUDE INTERPRETATION:
  1. NEVER compare raw amplitudes between different surveys
  2. Within a survey: Use relative contrasts and patterns
  3. Between surveys: Must normalize first (RMS normalization, etc.)
  4. Always mention processing/acquisition differences when comparing

  Safe comparisons:
  ✓ "Inline 55000 shows 2x higher amplitude than inline 54000 (same survey)"
  ✓ "After RMS normalization, Sepia shows similar amplitude patterns to BS500"

  UNSAFE comparisons:
  ✗ "Sepia has higher amplitudes than BS500" (no normalization)
  ✗ "Max amplitude 2487 vs 164" (raw values, different surveys)
  ```

- [ ] Add warning injection in MCP server response handler
  - [ ] Check if response mentions multiple surveys
  - [ ] Check if response contains amplitude comparisons
  - [ ] Auto-inject warning if unsafe comparison detected

**Acceptance Criteria:**
- [ ] System detects cross-survey amplitude comparisons
- [ ] Warning appears in Claude's response
- [ ] Tool descriptions include geophysical context

**Testing:**
- [ ] Test prompt: "Compare amplitudes between Sepia and BS500"
- [ ] Verify warning appears
- [ ] Test prompt: "What's the max amplitude in Sepia inline 55000?" (no warning)

---

### TODO 1.2: Update System Prompts with Domain Knowledge
**Priority:** HIGH
**Effort:** 1 hour
**Files to modify:**
- `/src/openvds_mcp_server.py` (server initialization, tool descriptions)

**Tasks:**
- [ ] Add geophysical interpretation guidelines to tool descriptions:
  ```
  DOMAIN KNOWLEDGE - SEISMIC AMPLITUDE INTERPRETATION:

  Amplitude values in seismic data:
  - Are NOT absolute physical measurements
  - Vary arbitrarily between surveys (acquisition/processing differences)
  - Only meaningful as RELATIVE patterns within a single survey

  What amplitudes CAN tell you (within one survey):
  - Relative contrasts (bright spot vs background)
  - Lateral variations (facies changes, fluids)
  - Vertical patterns (layering, interfaces)

  What amplitudes CANNOT tell you (between surveys):
  - Absolute strength comparisons
  - "Which survey is brighter"
  - Direct numeric comparisons without normalization

  When comparing surveys, focus on:
  - Structural patterns (faults, folds)
  - Continuity/quality metrics (SNR, frequency content)
  - Relative patterns (not absolute values)
  ```

- [ ] Add this to all extraction tool descriptions
- [ ] Add to agent_start_extraction description
- [ ] Add to comprehensive_search description

**Acceptance Criteria:**
- [ ] Domain knowledge visible in all relevant tool descriptions
- [ ] Claude has context about amplitude meaning before responding

---

### TODO 1.3: Create Geoscientist Review Checklist
**Priority:** HIGH
**Effort:** 3 hours (includes creating test cases)
**File to create:**
- `/GEOSCIENTIST_REVIEW_CHECKLIST.md`
- `/test/review_test_cases.md`

**Tasks:**
- [ ] Document 20 test prompts covering:
  - [ ] Single survey quality questions
  - [ ] Cross-survey comparison questions
  - [ ] Structural interpretation questions
  - [ ] Amplitude anomaly detection
  - [ ] Data quality assessment

- [ ] For each test case, document:
  - [ ] User prompt
  - [ ] Expected response pattern (what SHOULD be said)
  - [ ] Red flags (what SHOULD NOT be said)
  - [ ] Required metrics/context

- [ ] Create review form with questions:
  - [ ] "Are amplitude comparisons geophysically sound?"
  - [ ] "Are statistics meaningful or superficial?"
  - [ ] "Would you trust this for decision-making?"
  - [ ] "What's missing that a geoscientist would need?"
  - [ ] "Rate confidence in interpretation (1-5)"

**Example Test Cases:**
```markdown
## Test Case 1: Single Survey Quality
**Prompt:** "Assess the quality of inline 55000 in Sepia"
**Expected:** SNR, frequency content, continuity, completeness
**Red Flags:** Only basic stats (min/max/mean) without QC context
**Confidence Target:** 4/5

## Test Case 2: Cross-Survey Comparison
**Prompt:** "Compare Sepia and BS500 quality"
**Expected:** Normalized metrics, SNR comparison, structural clarity
**Red Flags:** Raw amplitude comparison without normalization
**Confidence Target:** 4/5

## Test Case 3: Amplitude Anomaly
**Prompt:** "Find bright spots in Sepia"
**Expected:** Statistical threshold, spatial extent, contrast ratio
**Red Flags:** Guessed locations, no threshold methodology
**Confidence Target:** 5/5 (algorithmic detection)
```

**Acceptance Criteria:**
- [ ] 20 test cases documented
- [ ] Review checklist ready for geoscientist
- [ ] Clear criteria for what's acceptable vs superficial

---

## Phase 2: Normalized Metrics & Domain-Aware Tools (Week 2-3)
**Goal:** Provide geophysically meaningful comparison tools

### TODO 2.1: Implement Normalized Amplitude Metrics
**Priority:** HIGH
**Effort:** 1 day
**File to create:**
- `/src/amplitude_normalization.py`

**Tasks:**
- [ ] Create `AmplitudeNormalizer` class with methods:

  **RMS Normalization:**
  - [ ] `normalize_by_rms(data: np.ndarray) -> np.ndarray`
    - Divide all values by RMS of dataset
    - Returns normalized data in range typically [-3, +3]

  **Z-Score Normalization:**
  - [ ] `normalize_by_zscore(data: np.ndarray) -> np.ndarray`
    - Subtract mean, divide by std dev
    - Returns standardized data (mean=0, std=1)

  **Percentile Normalization:**
  - [ ] `normalize_by_percentile(data: np.ndarray, clip_pct: float = 99.0) -> np.ndarray`
    - Clip to percentile range, scale to [0, 1]

  **Relative Contrast:**
  - [ ] `compute_relative_contrast(data: np.ndarray, reference: str = "median") -> float`
    - Compare amplitude to background (median or percentile)
    - Returns contrast ratio (e.g., "3x above background")

- [ ] Add unit tests for each normalization method
- [ ] Add docstrings with geophysical context

**Acceptance Criteria:**
- [ ] All normalization methods implemented
- [ ] Unit tests pass
- [ ] Normalized values are geophysically interpretable

---

### TODO 2.2: Add MCP Tools for Normalized Comparisons
**Priority:** HIGH
**Effort:** 1 day
**File to modify:**
- `/src/openvds_mcp_server.py`

**Tasks:**
- [ ] Add tool: `get_normalized_amplitude_statistics`
  ```python
  Tool(
      name="get_normalized_amplitude_statistics",
      description="""
      Get normalized amplitude statistics suitable for cross-survey comparison.

      Returns RMS-normalized, z-score normalized, and relative contrast metrics
      that ARE meaningful to compare across different surveys.

      USE THIS instead of raw amplitude statistics when comparing surveys.
      """,
      inputSchema={
          "survey_id": str,
          "section_type": str,
          "section_number": int,
          "normalization_method": ["rms", "zscore", "percentile"]
      }
  )
  ```

- [ ] Add tool: `compare_survey_quality_metrics`
  ```python
  Tool(
      name="compare_survey_quality_metrics",
      description="""
      Compare quality metrics between surveys using DOMAIN-APPROPRIATE measures.

      Returns:
      - SNR comparison (signal-to-noise ratio in dB)
      - Frequency content comparison (bandwidth, dominant freq)
      - Continuity metrics (semblance, coherence)
      - Data completeness (% valid traces)

      Does NOT compare raw amplitudes (geophysically meaningless).
      """,
      inputSchema={
          "survey_ids": List[str],
          "section_pairs": List[Tuple[str, int]]  # [(type, number), ...]
      }
  )
  ```

- [ ] Implement handlers for both tools
- [ ] Add validation: warn if surveys have very different processing

**Acceptance Criteria:**
- [ ] Tools return normalized, comparable metrics
- [ ] Cross-survey comparisons use domain-appropriate measures
- [ ] Raw amplitude comparisons are deprecated

---

### TODO 2.3: Add Relative Pattern Detection
**Priority:** MEDIUM
**Effort:** 1 day
**File to create:**
- `/src/pattern_analysis.py`

**Tasks:**
- [ ] Create `PatternAnalyzer` class with:

  **Bright Spot Detection:**
  - [ ] `detect_amplitude_anomalies(data, threshold_method="zscore", threshold=3.0)`
    - Use statistical threshold (not raw amplitude)
    - Return locations, extents, contrast ratios
    - Include "relative to background" context

  **Amplitude Variation Coefficient:**
  - [ ] `compute_amplitude_variation(data) -> dict`
    - Coefficient of variation (CV = std/mean * 100%)
    - Spatial variation patterns
    - Identifies zones of high/low variability

  **Lateral Continuity:**
  - [ ] `analyze_lateral_continuity(data) -> dict`
    - Trace-to-trace similarity
    - Detect discontinuities (faults?)
    - Quantify spatial coherence

- [ ] All methods return CONTEXT with numbers:
  ```python
  {
      "anomaly_count": 5,
      "threshold_method": "mean + 3*std",
      "threshold_value": 1474.4,
      "background_amplitude": 12.4,
      "contrast_ratios": [2.3, 3.1, 2.8, 4.2, 2.9],
      "interpretation": "5 zones with amplitude 2-4x above background"
  }
  ```

**Acceptance Criteria:**
- [ ] Patterns described relative to background
- [ ] Statistical methodology always included
- [ ] No absolute amplitude claims without context

---

## Phase 3: Quality Assessment Agent (Week 3-4)
**Goal:** Implement domain-expert QC metrics from SEISMIC_QC_AGENT_DESIGN.md

### TODO 3.1: Implement Signal Quality Analysis
**Priority:** HIGH
**Effort:** 3 days
**File to create:**
- `/src/qc/signal_quality.py`

**Tasks:**
- [ ] Implement SNR computation (from design doc lines 381-420):
  ```python
  class SignalQualityAnalyzer:
      def compute_snr(self, data: np.ndarray) -> dict:
          """
          Compute signal-to-noise ratio using multiple methods

          Returns:
              {
                  "snr_db": float,
                  "snr_grade": "Excellent/Good/Fair/Poor",
                  "noise_level": float,
                  "signal_level": float,
                  "coherency": float,
                  "method": "RMS-based with adjacent trace differencing"
              }
          """
  ```
  - [ ] RMS-based SNR calculation
  - [ ] Noise estimation from trace differences
  - [ ] Coherency calculation
  - [ ] Grading scale: Excellent (>30dB), Good (20-30), Fair (10-20), Poor (<10)

- [ ] Implement frequency content analysis (lines 431-476):
  ```python
  def analyze_frequency_content(self, data: np.ndarray, sample_rate: float) -> dict:
      """
      Analyze frequency spectrum using FFT

      Returns:
          {
              "dominant_frequency_hz": float,
              "bandwidth_hz": float,
              "frequency_range": [low, high],
              "bandwidth_grade": "Excellent/Good/Fair/Poor",
              "note": "Frequency content affects vertical resolution"
          }
      """
  ```
  - [ ] FFT-based power spectrum
  - [ ] Dominant frequency detection
  - [ ] Bandwidth calculation (90% energy range)
  - [ ] Grading: Excellent (>60Hz), Good (40-60), Fair (25-40), Poor (<25)

- [ ] Implement amplitude consistency analysis (lines 486-548):
  ```python
  def analyze_amplitude_consistency(self, data: np.ndarray) -> dict:
      """
      Detect amplitude anomalies and consistency issues

      Returns:
          {
              "mean_trace_rms": float,
              "coefficient_of_variation_percent": float,
              "amplitude_jumps": {"count": int, "severity": str},
              "weak_traces": {"count": int, "percentage": float},
              "hot_traces": {"count": int, "percentage": float},
              "quality_grade": str
          }
      """
  ```
  - [ ] Trace-by-trace RMS analysis
  - [ ] Amplitude jump detection (>3σ changes)
  - [ ] Dead trace detection (<10% of median)
  - [ ] Hot trace detection (>mean + 3σ)

**Acceptance Criteria:**
- [ ] All three signal quality methods implemented
- [ ] Grades use industry-standard thresholds
- [ ] Results include interpretation context
- [ ] Unit tests with synthetic data

**Reference:** SEISMIC_QC_AGENT_DESIGN.md lines 370-548

---

### TODO 3.2: Implement Spatial Continuity Analysis
**Priority:** HIGH
**Effort:** 2 days
**File to create:**
- `/src/qc/spatial_quality.py`

**Tasks:**
- [ ] Implement reflector continuity analysis (lines 552-606):
  ```python
  class SpatialQualityAnalyzer:
      def analyze_reflector_continuity(self, data: np.ndarray) -> dict:
          """
          Measure reflector continuity using semblance

          Returns:
              {
                  "mean_semblance": float,
                  "continuity_score": float,  # 0-100 scale
                  "discontinuities": {"count": int, "locations": list},
                  "quality_grade": "Excellent/Good/Fair/Poor",
                  "interpretation": str
              }
          """
  ```
  - [ ] Multi-trace semblance computation
  - [ ] Discontinuity detection
  - [ ] Grading: Excellent (>0.8), Good (0.6-0.8), Fair (0.4-0.6), Poor (<0.4)

- [ ] Add interpretation context:
  - Low semblance → "May indicate faulting, poor migration, or low SNR"
  - High semblance → "Good reflector continuity, suitable for interpretation"

**Acceptance Criteria:**
- [ ] Semblance calculation validated against known datasets
- [ ] Grades correlate with geophysicist assessment
- [ ] Provides actionable interpretation

**Reference:** SEISMIC_QC_AGENT_DESIGN.md lines 552-606

---

### TODO 3.3: Implement Artifact Detection
**Priority:** MEDIUM
**Effort:** 2 days
**File to create:**
- `/src/qc/artifact_detection.py`

**Tasks:**
- [ ] Implement acquisition footprint detection (lines 644-677):
  ```python
  class ArtifactDetector:
      def detect_acquisition_footprint(self, data: np.ndarray) -> dict:
          """
          Detect acquisition footprint using 2D FFT

          Returns:
              {
                  "footprint_ratio": float,
                  "footprint_detected": bool,
                  "severity": "high/moderate/low",
                  "quality_impact": str,
                  "recommendation": str
              }
          """
  ```
  - [ ] 2D FFT wavenumber analysis
  - [ ] Detect regular patterns vs smooth spectrum
  - [ ] Severity thresholds: High (>1000), Moderate (>100), Low (<100)

- [ ] Implement gap/dead trace detection (lines 727-770):
  ```python
  def detect_data_gaps(self, data: np.ndarray) -> dict:
      """
      Detect missing data, dead traces, NaN values

      Returns:
          {
              "nan_values": int,
              "dead_traces": {"count": int, "percentage": float},
              "data_completeness_percent": float,
              "quality_grade": str
          }
      """
  ```
  - [ ] NaN/inf detection
  - [ ] Dead trace detection (energy < 1% median)
  - [ ] Completeness grading: Excellent (>99%), Good (95-99%), Fair (90-95%), Poor (<90%)

**Acceptance Criteria:**
- [ ] Footprint detection works on test data with known footprint
- [ ] Gap detection identifies all dead traces
- [ ] Recommendations are actionable

**Reference:** SEISMIC_QC_AGENT_DESIGN.md lines 608-770

---

### TODO 3.4: Implement Comprehensive QC Tool
**Priority:** HIGH
**Effort:** 1 day
**File to modify:**
- `/src/openvds_mcp_server.py`

**Tasks:**
- [ ] Add MCP tool: `comprehensive_qc_analysis`
  ```python
  Tool(
      name="comprehensive_qc_analysis",
      description="""
      Perform comprehensive quality control analysis on seismic section.

      Returns DOMAIN-EXPERT QC metrics across all categories:
      1. Signal quality (SNR, frequency content, amplitude consistency)
      2. Spatial continuity (reflector continuity, coherence)
      3. Artifacts (acquisition footprint, dead traces)
      4. Resolution (vertical resolution estimate)
      5. Completeness (data gaps, coverage)

      All metrics are OBJECTIVE, ALGORITHMIC, and VERIFIABLE.
      Use this for quality assessment instead of guessing from images.
      """,
      inputSchema={
          "survey_id": str,
          "section_type": str,
          "section_number": int,
          "sample_range": Optional[List[int]]
      }
  )
  ```

- [ ] Implement comprehensive handler:
  ```python
  async def handle_comprehensive_qc(self, arguments):
      # Extract data
      data = await extract_section_data(...)

      # Run all QC analyses
      signal_quality = SignalQualityAnalyzer().analyze(data)
      spatial_quality = SpatialQualityAnalyzer().analyze(data)
      artifacts = ArtifactDetector().analyze(data)

      # Compute overall score (lines 850-900)
      overall_score = compute_overall_quality_score({
          "signal_quality": signal_quality,
          "spatial_continuity": spatial_quality,
          "artifacts": artifacts
      })

      # Generate recommendations (lines 903-962)
      recommendations = generate_qc_recommendations(qc_report)

      return {
          "overall_quality": overall_score,
          "signal_quality": signal_quality,
          "spatial_continuity": spatial_quality,
          "artifacts": artifacts,
          "recommendations": recommendations
      }
  ```

**Acceptance Criteria:**
- [ ] One tool call returns complete QC report
- [ ] Overall score is weighted properly (Signal 30%, Freq 20%, Amp 20%, Cont 15%, Complete 15%)
- [ ] Recommendations are specific and actionable
- [ ] Report is geoscientist-readable

**Reference:** SEISMIC_QC_AGENT_DESIGN.md lines 774-962

---

## Phase 4: Geoscientist Validation (Week 4-5)
**Goal:** Validate with real geoscientist feedback

### TODO 4.1: Run Test Cases with Geoscientist
**Priority:** CRITICAL
**Effort:** 4 hours (1 hour session + 3 hours iteration)
**Prerequisites:** Phase 1-3 complete

**Tasks:**
- [ ] Schedule 1-hour session with geoscientist
- [ ] Run through all 20 test cases from checklist
- [ ] Record feedback for each case:
  - [ ] What's good
  - [ ] What's missing
  - [ ] What's wrong
  - [ ] Confidence rating (1-5)

- [ ] Document gaps in `/GEOSCIENTIST_FEEDBACK_$(DATE).md`:
  ```markdown
  ## Test Case 1: Single Survey Quality
  **Prompt:** "Assess quality of inline 55000"
  **System Response:** [actual response]
  **Geoscientist Feedback:**
  - ✓ SNR metric is good
  - ✗ Missing velocity context for resolution estimate
  - ✗ Should mention if data is suitable for specific interpretation tasks
  **Confidence:** 3/5
  **Action Items:**
  - Add "suitable for" recommendations
  - Include velocity model context
  ```

- [ ] Prioritize fixes based on frequency/severity of issues

**Acceptance Criteria:**
- [ ] All 20 test cases reviewed
- [ ] Feedback documented with action items
- [ ] Average confidence >4/5 on critical test cases
- [ ] No "would never trust this" responses

---

### TODO 4.2: Iterate on Geoscientist Feedback
**Priority:** HIGH
**Effort:** 2-3 days
**Prerequisites:** TODO 4.1 complete

**Tasks:**
- [ ] For each piece of critical feedback:
  - [ ] Identify root cause (missing metric, wrong threshold, etc.)
  - [ ] Implement fix
  - [ ] Re-test with geoscientist

- [ ] Common fixes likely needed:
  - [ ] Adjust QC grading thresholds
  - [ ] Add missing context (velocity models, acquisition type, etc.)
  - [ ] Improve interpretation language
  - [ ] Add "suitable for X" recommendations

- [ ] Document changes in `/GEOSCIENTIST_ITERATION_LOG.md`

**Acceptance Criteria:**
- [ ] All critical feedback addressed
- [ ] Re-test shows improvement
- [ ] Geoscientist approves for production use

---

### TODO 4.3: Create Domain Expert Validation Suite
**Priority:** MEDIUM
**Effort:** 1 day
**File to create:**
- `/test/test_domain_validation.py`

**Tasks:**
- [ ] Create automated tests for domain rules:
  ```python
  def test_cross_survey_amplitude_comparison_blocked():
      """Verify system blocks raw amplitude comparisons"""
      response = ask("Compare amplitudes in Sepia vs BS500")
      assert "warning" in response.lower()
      assert "normalization" in response.lower()
      assert not any(bad_phrase in response for bad_phrase in [
          "higher amplitude", "stronger amplitude", "brighter"
      ])

  def test_qc_metrics_include_context():
      """Verify QC metrics include interpretation context"""
      response = get_comprehensive_qc("Sepia", "inline", 55000)
      assert "snr_db" in response
      assert "quality_grade" in response
      assert "interpretation" in response  # Must have context!

  def test_normalized_comparison_recommended():
      """Verify system recommends normalization for comparisons"""
      response = ask("Which survey has better quality, Sepia or BS500?")
      assert "normalized" in response.lower() or "snr" in response.lower()
      assert not "amplitude" in response.lower()  # Should use SNR, not amplitude
  ```

- [ ] Run tests in CI/CD pipeline
- [ ] Fail build if domain rules violated

**Acceptance Criteria:**
- [ ] 15+ domain validation tests
- [ ] All tests pass
- [ ] Tests cover critical geoscientist concerns

---

## Phase 5: Geospatial Integration (Week 5-6)
**Goal:** Enable geographic region queries and map integration

### TODO 5.1: Extract Geospatial Metadata from VDS
**Priority:** MEDIUM
**Effort:** 2 days
**File to create:**
- `/src/geospatial_metadata.py`

**Tasks:**
- [ ] Create `GeospatialMetadataExtractor` class:
  ```python
  class GeospatialMetadataExtractor:
      def extract_coordinate_system(self, vds_handle) -> dict:
          """
          Extract CRS, bounding box, and coordinate info from VDS

          Returns:
              {
                  "crs": "EPSG:32631",  # Coordinate reference system
                  "bounding_box": {
                      "min_x": 489000.0,
                      "max_x": 512000.0,
                      "min_y": 6789000.0,
                      "max_y": 6812000.0,
                      "units": "meters"
                  },
                  "geographic_bounds": {
                      "min_lon": -95.234,
                      "max_lon": -94.876,
                      "min_lat": 28.123,
                      "max_lat": 28.456
                  },
                  "inline_crossline_to_xy": [...],  # Transformation matrix
                  "center_point": {"lon": -95.055, "lat": 28.290}
              }
          """
  ```

- [ ] Use OpenVDS metadata API to extract:
  - [ ] Coordinate system (CRS/EPSG code)
  - [ ] Inline/crossline to X/Y transformation
  - [ ] X/Y bounding box
  - [ ] Convert to lat/lon using pyproj

- [ ] Add to survey metadata cache (update on initialization)

**Acceptance Criteria:**
- [ ] All VDS files have extracted geospatial metadata
- [ ] Bounding boxes displayed correctly on map
- [ ] Coordinate transforms are accurate

---

### TODO 5.2: Add Geospatial Query Tools
**Priority:** MEDIUM
**Effort:** 1 day
**File to modify:**
- `/src/openvds_mcp_server.py`

**Tasks:**
- [ ] Add tool: `get_survey_geospatial_info`
  ```python
  Tool(
      name="get_survey_geospatial_info",
      description="""
      Get geographic location and extent of a survey.

      Returns lat/lon bounding box, coordinate system, and center point.
      Use this for map visualization and geographic queries.
      """,
      inputSchema={
          "survey_id": str
      }
  )
  ```

- [ ] Add tool: `find_surveys_by_region`
  ```python
  Tool(
      name="find_surveys_by_region",
      description="""
      Find surveys within a geographic region.

      Examples:
      - "Find surveys in the Gulf of Mexico"
      - "Which surveys cover lat 28.5, lon -95.0?"
      - "Show me surveys near the Nigerian coast"
      """,
      inputSchema={
          "region": str,  # Natural language or bbox
          "bbox": Optional[List[float]]  # [min_lon, min_lat, max_lon, max_lat]
      }
  )
  ```

- [ ] Implement handlers using Elasticsearch geospatial queries

**Acceptance Criteria:**
- [ ] Can query surveys by region name
- [ ] Can query surveys by bounding box
- [ ] Returns accurate geographic metadata

---

### TODO 5.3: Prepare for Map Interface Integration
**Priority:** LOW (depends on UI team)
**Effort:** 1 day
**File to create:**
- `/docs/GEOSPATIAL_INTEGRATION_GUIDE.md`

**Tasks:**
- [ ] Document API endpoints for map integration:
  ```markdown
  ## Geospatial API Endpoints

  ### Get Survey Bounds
  GET /surveys/{survey_id}/geospatial
  Returns: {bounding_box, center_point, crs}

  ### Get All Survey Extents
  GET /surveys/geospatial/all
  Returns: [{survey_id, bounding_box, center_point}, ...]

  ### Query by Region
  POST /surveys/geospatial/query
  Body: {bbox: [min_lon, min_lat, max_lon, max_lat]}
  Returns: [survey_ids within bbox]
  ```

- [ ] Create example map integration code (Leaflet/MapLibre):
  ```javascript
  // Example: Display survey extents on map
  surveys.forEach(survey => {
      const bounds = survey.geographic_bounds;
      L.rectangle([
          [bounds.min_lat, bounds.min_lon],
          [bounds.max_lat, bounds.max_lon]
      ], {
          color: '#1976d2',
          weight: 2,
          fillOpacity: 0.1
      }).addTo(map).bindPopup(survey.survey_id);
  });
  ```

- [ ] Document coordinate system handling (CRS transformations)

**Acceptance Criteria:**
- [ ] Documentation complete for UI team
- [ ] Example code provided
- [ ] API endpoints documented

---

## Phase 6: DataHub Integration (Week 6)
**Goal:** Expose MCP server to DataHub for FAST integration

### TODO 6.1: Create DataHub MCP Bridge
**Priority:** HIGH (for DataHub integration)
**Effort:** 2 days
**File to create:**
- `/datahub_integration/mcp_bridge.py`

**Tasks:**
- [ ] Create bridge layer that:
  - [ ] Exposes MCP server as REST API (if not already available)
  - [ ] Handles authentication/authorization
  - [ ] Provides OpenAPI/Swagger spec
  - [ ] Includes CORS headers for web clients

- [ ] Implement DataHub-compatible endpoints:
  ```python
  # Example structure
  @app.get("/datahub/surveys")
  async def list_surveys():
      """List all available surveys (for DataHub UI)"""
      return await mcp_server.call_tool("list_surveys")

  @app.get("/datahub/surveys/{survey_id}/metadata")
  async def get_metadata(survey_id: str):
      """Get survey metadata (for DataHub)"""
      return await mcp_server.call_tool("get_survey_metadata",
                                        {"survey_id": survey_id})

  @app.post("/datahub/surveys/{survey_id}/qc")
  async def run_qc(survey_id: str, section: dict):
      """Run comprehensive QC (for DataHub QC module)"""
      return await mcp_server.call_tool("comprehensive_qc_analysis", {
          "survey_id": survey_id,
          **section
      })
  ```

**Acceptance Criteria:**
- [ ] All MCP tools accessible via REST API
- [ ] OpenAPI spec generated
- [ ] FAST can call endpoints successfully

---

### TODO 6.2: Create DataHub Integration Documentation
**Priority:** MEDIUM
**Effort:** 1 day
**File to create:**
- `/docs/DATAHUB_INTEGRATION.md`

**Tasks:**
- [ ] Document integration architecture:
  ```
  ┌─────────────────────────────────────────┐
  │         DataHub / FAST UI               │
  │  (Web application, map interface)       │
  └─────────────────┬───────────────────────┘
                    │ HTTP REST/GraphQL
                    ▼
  ┌─────────────────────────────────────────┐
  │      DataHub Backend / API Gateway      │
  │   (Authentication, routing, caching)    │
  └─────────────────┬───────────────────────┘
                    │ REST API calls
                    ▼
  ┌─────────────────────────────────────────┐
  │         MCP Bridge / REST Adapter       │
  │    (Translates REST → MCP tool calls)   │
  └─────────────────┬───────────────────────┘
                    │ MCP protocol
                    ▼
  ┌─────────────────────────────────────────┐
  │      OpenVDS MCP Server (This repo)     │
  │  - VDS file access                      │
  │  - Metadata queries (Elasticsearch)     │
  │  - Image extraction                     │
  │  - QC analysis                          │
  │  - Agent-based bulk operations          │
  └─────────────────┬───────────────────────┘
                    │
                    ▼
  ┌─────────────────────────────────────────┐
  │         VDS Files + Elasticsearch       │
  │   (Seismic data + indexed metadata)     │
  └─────────────────────────────────────────┘
  ```

- [ ] Document available capabilities for DataHub:
  - [ ] Survey discovery and metadata
  - [ ] Quality assessment (comprehensive QC)
  - [ ] Image extraction (inline/crossline/timeslice)
  - [ ] Bulk operations (agent-based)
  - [ ] Geospatial queries
  - [ ] Domain-aware interpretation layer

- [ ] Provide example usage from FAST:
  ```javascript
  // Example: FAST Quality Control module
  async function runQualityCheck(surveyId, inline) {
      const response = await fetch(
          `${MCP_BRIDGE_URL}/datahub/surveys/${surveyId}/qc`,
          {
              method: 'POST',
              body: JSON.stringify({
                  section_type: 'inline',
                  section_number: inline
              })
          }
      );

      const qcReport = await response.json();

      // Display QC results in UI
      displayQCScore(qcReport.overall_quality.score);
      displaySNR(qcReport.signal_quality.snr);
      displayRecommendations(qcReport.recommendations);
  }
  ```

**Acceptance Criteria:**
- [ ] Architecture documented
- [ ] All available capabilities listed
- [ ] Example code for FAST integration provided

---

### TODO 6.3: Test DataHub Integration End-to-End
**Priority:** HIGH
**Effort:** 1 day
**Prerequisites:** TODO 6.1, 6.2 complete

**Tasks:**
- [ ] Set up test DataHub environment (or use staging)
- [ ] Test key workflows:
  - [ ] Survey discovery from DataHub UI
  - [ ] QC analysis triggered from FAST
  - [ ] Image extraction in FAST viewer
  - [ ] Map display of survey extents
  - [ ] Bulk operations (agent-based extraction)

- [ ] Performance test:
  - [ ] Response time for metadata queries (<500ms)
  - [ ] Response time for QC analysis (<5s)
  - [ ] Response time for image extraction (<3s)
  - [ ] Concurrent user load (10+ users)

- [ ] Document any issues in `/datahub_integration/INTEGRATION_TEST_RESULTS.md`

**Acceptance Criteria:**
- [ ] All workflows work end-to-end
- [ ] Performance meets targets
- [ ] No blocking issues identified

---

## Phase 7: Production Hardening (Ongoing)
**Goal:** Ensure system is production-ready and maintainable

### TODO 7.1: Implement Comprehensive Logging
**Priority:** MEDIUM
**Effort:** 1 day
**Files to modify:**
- All new modules

**Tasks:**
- [ ] Add structured logging to all new modules:
  ```python
  import logging
  logger = logging.getLogger(__name__)

  # Log domain violations
  logger.warning(
      "Cross-survey amplitude comparison detected",
      extra={
          "surveys": ["Sepia", "BS500"],
          "user_prompt": prompt,
          "warning_injected": True
      }
  )

  # Log QC analysis
  logger.info(
      "Comprehensive QC analysis completed",
      extra={
          "survey_id": survey_id,
          "section": f"{section_type} {section_number}",
          "overall_score": score,
          "execution_time_ms": elapsed_ms
      }
  )
  ```

- [ ] Add metrics tracking:
  - [ ] Count of domain warnings triggered
  - [ ] QC analysis execution times
  - [ ] Normalization method usage
  - [ ] Geoscientist confidence ratings (if available)

**Acceptance Criteria:**
- [ ] All domain-critical operations logged
- [ ] Logs are structured (JSON) for analysis
- [ ] Metrics available in dashboard

---

### TODO 7.2: Create Monitoring Dashboard
**Priority:** LOW
**Effort:** 2 days
**File to create:**
- `/monitoring/domain_health_dashboard.py`

**Tasks:**
- [ ] Create dashboard showing:
  - [ ] Domain warning rate (what % of queries trigger warnings)
  - [ ] QC analysis usage (how often comprehensive_qc called)
  - [ ] Normalized metric usage vs raw amplitude usage
  - [ ] Average geoscientist confidence rating (if tracked)
  - [ ] Top geophysical issues detected (SNR, footprint, etc.)

- [ ] Use Grafana, Kibana, or custom dashboard
- [ ] Alert if:
  - [ ] Domain warning rate >50% (users trying unsafe comparisons)
  - [ ] QC analysis errors >5%
  - [ ] Average confidence rating <3.5/5

**Acceptance Criteria:**
- [ ] Dashboard displays key domain health metrics
- [ ] Alerts fire for critical issues
- [ ] Dashboard accessible to product/engineering team

---

### TODO 7.3: Document Domain Knowledge for Future Maintainers
**Priority:** MEDIUM
**Effort:** 1 day
**File to create:**
- `/docs/GEOPHYSICAL_DOMAIN_KNOWLEDGE.md`

**Tasks:**
- [ ] Document key domain concepts for engineers:
  ```markdown
  ## Why Amplitude Comparisons Are Problematic

  Seismic amplitudes are NOT like temperatures or pressures - they are
  relative, unitless values that depend on:
  - Acquisition: Source strength, receiver sensitivity, geometry
  - Processing: Gain functions, filters, normalization, migration
  - Arbitrary scaling: No physical units (Pa, N, etc.)

  ### Safe Comparisons (Within One Survey)
  ✓ Relative contrasts: "3x brighter than background"
  ✓ Statistical thresholds: "Exceeds mean + 3σ"
  ✓ Patterns: "Stronger reflectivity in upper section"

  ### Unsafe Comparisons (Between Surveys)
  ✗ Raw values: "Survey A has higher amplitudes than B"
  ✗ Direct numeric: "Max 2487 vs max 164"
  ✗ Without normalization: "Brighter" without RMS normalization

  ### Domain-Appropriate Metrics for Cross-Survey Comparison
  ✓ SNR (signal-to-noise ratio in dB)
  ✓ Frequency content (Hz)
  ✓ Continuity (semblance 0-1)
  ✓ Normalized amplitudes (RMS or z-score)
  ```

- [ ] Document QC metric meanings:
  - [ ] What is SNR and why it matters
  - [ ] What is semblance and what it indicates
  - [ ] What is acquisition footprint and why it's bad
  - [ ] What are multiples and how they affect interpretation

- [ ] Document when to involve geoscientist:
  - [ ] New QC metric requests
  - [ ] Threshold tuning
  - [ ] Validation of new features
  - [ ] Interpretation of edge cases

**Acceptance Criteria:**
- [ ] Document covers all critical domain concepts
- [ ] Engineers can understand why certain rules exist
- [ ] Clear escalation path for domain questions

---

## Testing & Validation Summary

### Automated Tests (Minimum Required)
- [ ] 15+ domain validation tests (TODO 4.3)
- [ ] Unit tests for all QC metrics (TODO 3.1-3.3)
- [ ] Integration tests for MCP tools (TODO 2.2, 3.4)
- [ ] Cross-survey comparison warning tests (TODO 1.1)

### Manual Validation
- [ ] Geoscientist review of 20 test cases (TODO 4.1)
- [ ] Iteration on feedback (TODO 4.2)
- [ ] Average confidence >4/5 on critical tests
- [ ] DataHub integration end-to-end test (TODO 6.3)

### Performance Targets
- [ ] Metadata queries: <500ms
- [ ] QC analysis: <5s
- [ ] Image extraction: <3s
- [ ] Concurrent users: 10+ without degradation

---

## Success Criteria (Overall)

### Technical Criteria
- [ ] ✅ Zero cross-survey amplitude comparisons without normalization
- [ ] ✅ All QC metrics are algorithmic and verifiable
- [ ] ✅ Domain warnings appear when unsafe interpretations attempted
- [ ] ✅ Comprehensive QC returns geophysically meaningful metrics
- [ ] ✅ Geospatial queries work for map integration
- [ ] ✅ DataHub integration functional end-to-end

### Geoscientist Validation Criteria
- [ ] ✅ Average confidence rating >4/5 on quality assessment
- [ ] ✅ No "would never trust this" responses
- [ ] ✅ Geoscientist approves for production use
- [ ] ✅ Recommendations are actionable

### Production Criteria
- [ ] ✅ All automated tests passing
- [ ] ✅ Monitoring dashboard operational
- [ ] ✅ Documentation complete
- [ ] ✅ DataHub team trained on integration

---

## Priority Summary

### Critical (Must Have for V1)
1. TODO 1.1 - Cross-survey comparison warnings
2. TODO 1.2 - Domain knowledge in system prompts
3. TODO 2.1 - Normalized amplitude metrics
4. TODO 3.1 - Signal quality analysis (SNR, frequency)
5. TODO 3.4 - Comprehensive QC tool
6. TODO 4.1 - Geoscientist validation
7. TODO 6.1 - DataHub integration

### High (Should Have for V1)
8. TODO 1.3 - Geoscientist review checklist
9. TODO 2.2 - Normalized comparison tools
10. TODO 3.2 - Spatial continuity analysis
11. TODO 4.2 - Iteration on feedback
12. TODO 5.1 - Geospatial metadata extraction
13. TODO 6.2 - DataHub documentation

### Medium (Nice to Have for V1)
14. TODO 2.3 - Pattern analysis
15. TODO 3.3 - Artifact detection
16. TODO 4.3 - Domain validation suite
17. TODO 5.2 - Geospatial query tools
18. TODO 7.1 - Comprehensive logging

### Low (V2 Features)
19. TODO 5.3 - Map interface integration prep
20. TODO 7.2 - Monitoring dashboard
21. TODO 7.3 - Domain knowledge documentation

---

## Estimated Timeline

**Week 1:** Phase 1 (Immediate fixes)
- Days 1-2: TODO 1.1, 1.2 (Warnings and domain knowledge)
- Day 3: TODO 1.3 (Geoscientist checklist)

**Week 2-3:** Phase 2 (Normalized metrics)
- Days 4-5: TODO 2.1, 2.2 (Normalization tools)
- Day 6: TODO 2.3 (Pattern analysis)

**Week 3-4:** Phase 3 (QC Agent)
- Days 7-9: TODO 3.1 (Signal quality)
- Days 10-11: TODO 3.2 (Spatial quality)
- Days 12-13: TODO 3.3 (Artifacts)
- Day 14: TODO 3.4 (Comprehensive tool)

**Week 4-5:** Phase 4 (Validation)
- Day 15: TODO 4.1 (Geoscientist review)
- Days 16-18: TODO 4.2 (Iteration)
- Day 19: TODO 4.3 (Validation suite)

**Week 5-6:** Phase 5-6 (Geospatial & DataHub)
- Days 20-21: TODO 5.1, 5.2 (Geospatial)
- Days 22-23: TODO 6.1, 6.2 (DataHub integration)
- Day 24: TODO 6.3 (End-to-end testing)

**Ongoing:** Phase 7 (Hardening)
- Days 25-30: TODO 7.1, 7.2, 7.3 (Logging, monitoring, docs)

**Total: 4-6 weeks** (depending on feedback iteration cycles)

---

## Next Steps

**To get started:**
1. Review this plan with stakeholders
2. Confirm priorities (especially geoscientist availability for TODO 4.1)
3. Start with TODO 1.1 (cross-survey warnings) - highest impact, quick win
4. Schedule geoscientist session for Week 4-5

**Questions to resolve:**
- [ ] Who is the geoscientist validator? (Need name/availability for TODO 4.1)
- [ ] What's the DataHub integration timeline? (Affects priority of Phase 6)
- [ ] Do we have test datasets with known QC issues? (For validation)
- [ ] What's the target deployment date? (Affects timeline compression)

---

**Document Status:** ✅ Complete - Ready for Execution
**Last Updated:** 2025-01-08
**Owner:** To be assigned
**Est. Completion:** 4-6 weeks from start
