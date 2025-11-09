# Implementation Checkpoint - Domain-Aware Anti-Hallucination (Phases 1-2)

**Date:** 2025-01-08
**Status:** Phase 1 Complete (100%), Phase 2 Started (25%)
**Next Session:** Continue with Phase 2.2 or jump to Phase 3

---

## What Was Implemented

### ✅ PHASE 1: IMMEDIATE FIXES - **100% COMPLETE**

#### 1. Cross-Survey Comparison Warning System
**File:** `/src/domain_warnings.py` (312 lines)

**Features:**
- Detects unsafe cross-survey amplitude comparisons
- Detects missing units in responses
- Generates comprehensive warning messages
- Provides safe/unsafe comparison examples
- Singleton pattern for efficiency

**Key Classes:**
- `DomainWarning` - dataclass for warning details
- `DomainWarningSystem` - main detection logic
- `get_warning_system()` - singleton accessor
- `check_response_for_domain_issues()` - convenience function

**What It Prevents:**
```python
# Blocks statements like:
❌ "Sepia has 15-30x higher amplitudes than BS500"
❌ "Max amplitude 2487 vs 164" (between surveys)
❌ Any amplitude comparison without normalization

# Allows statements like:
✅ "Sepia has SNR of 18.5 dB, BS500 has 24.3 dB"
✅ "After RMS normalization, Sepia variance 1.2 vs BS500 1.1"
✅ "Within Sepia: inline 55000 shows 2x amplitude contrast"
```

#### 2. Tool Description Updates with Domain Knowledge
**File:** `/src/openvds_mcp_server.py`

**Updated Tools:**
- `extract_inline_image` - Added full domain knowledge and units requirements
- `extract_crossline_image` - Added domain knowledge and units
- `extract_timeslice_image` - Added domain knowledge and units
- `agent_start_extraction` - Added units information

**Each Tool Now Includes:**
```markdown
📊 UNITS REQUIREMENT:
- Amplitude values: (unitless)
- Sample numbers: (samples)
- Line numbers: (line numbers)
- Frequencies: Hz
- Dimensions: (pixels), (traces), (samples)

⚠️ DOMAIN KNOWLEDGE - AMPLITUDE INTERPRETATION:
- CRITICAL: Amplitudes are UNITLESS
- SAFE: Compare within ONE survey
- UNSAFE: Compare between surveys without normalization
- FOR CROSS-SURVEY: Use normalized metrics or quality tools

ALWAYS specify units or explicitly state (unitless)!
```

**Import Added:**
```python
from .domain_warnings import get_warning_system, check_response_for_domain_issues
```

#### 3. Geoscientist Review Checklist
**File:** `/GEOSCIENTIST_REVIEW_CHECKLIST.md`

**Contains:**
- 20 comprehensive test cases across 7 categories
- Clear expected patterns and red flags for each test
- Confidence rating scale (1-5)
- Evaluation criteria
- Summary evaluation template

**Test Categories:**
1. Single Survey Quality Assessment (3 cases)
2. Cross-Survey Comparisons (3 cases)
3. Units Compliance (2 cases)
4. QC Metrics (2 cases) - if QC agent implemented
5. Structural Interpretation (1 case)
6. Data Integrity Validation (2 cases)
7. Edge Cases and Error Handling (2 cases)

**Ready For:**
- Geoscientist validation session (Week 4-5 of roadmap)
- Systematic testing of all domain rules
- Confidence assessment for production readiness

---

### ✅ PHASE 2: NORMALIZED METRICS - **25% COMPLETE**

#### 4. Amplitude Normalization Module
**File:** `/src/amplitude_normalization.py` (463 lines)

**Features:**
- Three industry-standard normalization methods
- Comprehensive units annotations on ALL outputs
- Statistical contrast analysis for anomaly detection
- Singleton pattern + convenience functions

**Normalization Methods:**

**A. RMS Normalization** (Industry Standard)
```python
normalizer = get_normalizer()
result = normalizer.normalize_by_rms(data)

# Returns:
{
  "normalized_data": [...],  # Values in units of RMS
  "statistics": {
    "original_rms": 487.2,
    "original_rms_units": "unitless (arbitrary from acquisition/processing)",
    "normalized_statistics": {
      "min": -2.56,
      "max": 5.10,
      "mean": 0.025,
      "units": "unitless (RMS-normalized, typically -3 to +3)"
    },
    "interpretation": "Values represent amplitude in units of RMS..."
  },
  "units": "unitless (RMS-normalized)"
}
```

**B. Z-Score Normalization** (Statistical Standard)
```python
result = normalizer.normalize_by_zscore(data)

# Returns values as standard deviations from mean
# Mean = 0, Std = 1 after normalization
# Units: "unitless (z-score: standard deviations from mean)"
```

**C. Percentile Normalization** (Robust to Outliers)
```python
result = normalizer.normalize_by_percentile(data, clip_percentile=99.0)

# Clips to 1st-99th percentile, scales to [0, 1]
# Units: "unitless (percentile-normalized, 0-1 range)"
```

**D. Relative Contrast Analysis** (Anomaly Detection)
```python
result = normalizer.compute_relative_contrast(data, reference="median", threshold_sigma=3.0)

# Returns:
{
  "background_level": {"value": 8.7, "units": "unitless (...)"},
  "threshold": {"value": 1474.4, "method": "mean + 3σ", "units": "unitless (...)"},
  "anomalies": {"count": 23, "percentage": 1.2, "percentage_units": "%"},
  "contrast_ratios": {
    "values": [2.3, 3.1, 2.8, ...],
    "units": "unitless (ratio to background)",
    "interpretation": "Anomaly amplitudes are X times background..."
  }
}
```

**Convenience Function for Cross-Survey Comparison:**
```python
from amplitude_normalization import normalize_for_comparison

result1, result2 = normalize_for_comparison(sepia_data, bs500_data, method="rms")

# Now result1 and result2 are COMPARABLE across surveys!
print(f"Sepia RMS-normalized variance: {np.var(result1.normalized_data):.2f}")
print(f"BS500 RMS-normalized variance: {np.var(result2.normalized_data):.2f}")
```

---

## Files Created (Summary)

### New Modules (4 Python files)
1. `/src/domain_warnings.py` - 312 lines
   - Cross-survey comparison detection
   - Units validation
   - Warning generation

2. `/src/amplitude_normalization.py` - 463 lines
   - RMS normalization
   - Z-score normalization
   - Percentile normalization
   - Relative contrast analysis

### Documentation (3 Markdown files)
3. `/GEOSCIENTIST_REVIEW_CHECKLIST.md`
   - 20 test cases
   - Validation framework

4. `/DOMAIN_AWARE_ANTI_HALLUCINATION_PLAN.md`
   - Full 6-phase roadmap
   - Detailed TODO items
   - 4-6 week timeline

5. `/ARCHITECT_FEEDBACK_RESPONSE.md`
   - Executive summary for stakeholders
   - Response to architect concerns

6. **THIS FILE:** `/CHECKPOINT_PHASE_1_2_IMPLEMENTATION.md`

### Modified Files
7. `/src/openvds_mcp_server.py`
   - Added imports for domain_warnings
   - Updated 4 tool descriptions with domain knowledge and units

---

## What Still Needs To Be Done

### 📋 PHASE 2 (Remaining - 2-3 hours)

**Phase 2.2: Add MCP Tools for Normalized Comparisons**
Estimated: 1-2 hours

Create two new MCP tools:

**Tool 1: get_normalized_amplitude_statistics**
```python
Tool(
    name="get_normalized_amplitude_statistics",
    description="""
    Get normalized amplitude statistics for cross-survey comparison.

    Returns RMS-normalized, z-score, or percentile-normalized statistics
    that ARE meaningful across different surveys.

    USE THIS instead of raw amplitude statistics when comparing surveys.
    """,
    inputSchema={
        "survey_id": str,
        "section_type": str,
        "section_number": int,
        "normalization_method": ["rms", "zscore", "percentile"]
    }
)

# Handler implementation needed in openvds_mcp_server.py:
# 1. Extract data using existing extraction methods (with return_data=True)
# 2. Call amplitude_normalization.get_normalizer().normalize_by_X()
# 3. Return normalized statistics with units
```

**Tool 2: compare_survey_quality_metrics**
```python
Tool(
    name="compare_survey_quality_metrics",
    description="""
    Compare quality metrics between surveys using domain-appropriate measures.

    Returns:
    - SNR comparison (dB)
    - Frequency content (Hz)
    - Continuity metrics (0-1 unitless)
    - Data completeness (%)

    Does NOT compare raw amplitudes.
    """,
    inputSchema={
        "survey_pairs": List[Tuple[str, str, int]]  # [(survey_id, type, number), ...]
    }
)

# Handler implementation needed:
# 1. Extract sections from both surveys
# 2. Compute comparable metrics (will need Phase 3 QC agent for SNR/frequency)
# 3. For now: can compute normalized amplitude statistics
# 4. Return comparison with all units annotated
```

**Action Items:**
- [ ] Add tool definitions to openvds_mcp_server.py (after line 560)
- [ ] Implement handlers in call_tool() method
- [ ] Add import: `from .amplitude_normalization import get_normalizer`
- [ ] Test with example prompts

---

**Phase 2.3: Create pattern_analysis.py**
Estimated: 3-4 hours

Create module for relative pattern detection:

```python
# /src/pattern_analysis.py

class PatternAnalyzer:
    def detect_amplitude_anomalies(self, data, threshold_method="zscore", threshold=3.0):
        """
        Detect anomalies using statistical thresholds (NOT raw amplitude values)

        Returns:
        - Locations with units: inline (line number), crossline (line number), sample (samples)
        - Threshold value with units
        - Contrast ratios (unitless ratios)
        - Spatial extent (traces × samples)
        """

    def compute_amplitude_variation(self, data):
        """
        Coefficient of variation and spatial patterns

        Returns:
        - CV (%)
        - Spatial variation zones
        - All with proper units
        """

    def analyze_lateral_continuity(self, data):
        """
        Trace-to-trace similarity

        Returns:
        - Coherence (0-1 unitless)
        - Discontinuity locations with units
        """
```

**Action Items:**
- [ ] Create /src/pattern_analysis.py module
- [ ] Implement PatternAnalyzer class with 3 methods
- [ ] Add comprehensive units to all outputs
- [ ] Add singleton pattern
- [ ] Write docstrings with geophysical context

---

### 📋 PHASE 3: QUALITY ASSESSMENT AGENT (1-2 days)

**Phase 3.1: Signal Quality Analysis**
Estimated: 3-4 hours

Create `/src/qc/signal_quality.py`:

```python
class SignalQualityAnalyzer:
    def compute_snr(self, data: np.ndarray, sample_rate: float) -> dict:
        """
        SNR computation using RMS-based method

        Returns:
        {
          "snr_db": 18.5,  # dB unit!
          "snr_grade": "Good",
          "noise_level": 32.1,  # unitless
          "signal_level": 487.2,  # unitless
          "coherency": 0.78,  # 0-1 unitless
          "method": "RMS-based with adjacent trace differencing"
        }

        Grading:
        - Excellent: >30 dB
        - Good: 20-30 dB
        - Fair: 10-20 dB
        - Poor: <10 dB
        """

    def analyze_frequency_content(self, data, sample_rate):
        """
        FFT-based frequency analysis

        Returns ALL frequencies in Hz:
        {
          "dominant_frequency_hz": 45,  # Hz!
          "bandwidth_hz": 40,  # Hz!
          "frequency_range": [15, 55],  # Hz!
          "bandwidth_grade": "Good"
        }
        """

    def analyze_amplitude_consistency(self, data):
        """
        Amplitude jumps, dead traces, hot traces

        Returns:
        {
          "amplitude_jumps": {"count": 3, "severity": "low"},
          "weak_traces": {"count": 2, "percentage": 0.4, "percentage_units": "%"},
          "coefficient_of_variation_percent": 12.5  # %
        }
        """
```

**Reference:** SEISMIC_QC_AGENT_DESIGN.md lines 370-548

**Action Items:**
- [ ] Create /src/qc/ directory
- [ ] Create /src/qc/signal_quality.py
- [ ] Implement SignalQualityAnalyzer class
- [ ] Add SNR computation with dB units
- [ ] Add frequency analysis with Hz units
- [ ] Add amplitude consistency checks
- [ ] Write unit tests with synthetic data

---

**Phase 3.2: Spatial Quality Analysis**
Estimated: 2 hours

Create `/src/qc/spatial_quality.py`:

```python
class SpatialQualityAnalyzer:
    def analyze_reflector_continuity(self, data):
        """
        Semblance-based continuity

        Returns:
        {
          "mean_semblance": 0.72,  # 0-1 unitless
          "continuity_score": 72,  # 0-100 unitless
          "discontinuities": {"count": 5},
          "quality_grade": "Good"
        }
        """
```

**Reference:** SEISMIC_QC_AGENT_DESIGN.md lines 552-606

---

**Phase 3.3: Artifact Detection**
Estimated: 2 hours

Create `/src/qc/artifact_detection.py`:

```python
class ArtifactDetector:
    def detect_acquisition_footprint(self, data):
        """2D FFT wavenumber analysis"""

    def detect_data_gaps(self, data):
        """
        NaN/inf detection, dead traces

        Returns:
        {
          "dead_traces": {"count": 3, "percentage": 0.6, "percentage_units": "%"},
          "data_completeness_percent": 99.4  # %
        }
        """
```

**Reference:** SEISMIC_QC_AGENT_DESIGN.md lines 608-770

---

**Phase 3.4: Comprehensive QC Tool**
Estimated: 2-3 hours

Add to `/src/openvds_mcp_server.py`:

```python
Tool(
    name="comprehensive_qc_analysis",
    description="""
    Perform comprehensive QC analysis on seismic section.

    Returns DOMAIN-EXPERT QC metrics:
    - Signal quality: SNR (dB), frequency (Hz), amplitude consistency
    - Spatial continuity: semblance (0-1)
    - Artifacts: footprint, dead traces
    - Overall quality score (0-100)
    - Actionable recommendations

    ALL metrics include proper units!
    """,
    inputSchema={
        "survey_id": str,
        "section_type": str,
        "section_number": int
    }
)

# Handler:
async def handle_comprehensive_qc(self, arguments):
    # Extract data
    data = await extract_section_data(...)

    # Run all analyses
    from .qc.signal_quality import SignalQualityAnalyzer
    from .qc.spatial_quality import SpatialQualityAnalyzer
    from .qc.artifact_detection import ArtifactDetector

    signal_quality = SignalQualityAnalyzer().analyze(data)
    spatial_quality = SpatialQualityAnalyzer().analyze(data)
    artifacts = ArtifactDetector().analyze(data)

    # Compute overall score
    overall_score = compute_overall_quality_score(...)

    # Generate recommendations
    recommendations = generate_qc_recommendations(...)

    return {
        "overall_quality": overall_score,
        "signal_quality": signal_quality,
        "spatial_continuity": spatial_quality,
        "artifacts": artifacts,
        "recommendations": recommendations
    }
```

**Reference:** SEISMIC_QC_AGENT_DESIGN.md lines 774-962

---

### 📋 ADDITIONAL TASKS

**UNITS: Update Existing Extraction Tool Response Handlers**
Estimated: 2-3 hours

Currently, tool descriptions say to include units, but response handlers need updating:

**Files to modify:**
- `/src/openvds_mcp_server.py` - handlers starting at line 800
- `/src/vds_client.py` - extraction methods return dictionaries

**Changes needed:**

```python
# In handlers (openvds_mcp_server.py):

# BEFORE:
metadata = {
    "min": -1247.3,
    "max": 2487.3,
    "mean": 12.4
}

# AFTER:
metadata = {
    "amplitude_statistics": {
        "min": -1247.3,
        "max": 2487.3,
        "mean": 12.4,
        "units": "unitless (arbitrary scaling from acquisition/processing)"
    },
    "sample_range": {
        "start": 6000,
        "end": 7000,
        "units": "samples"
    },
    "dimensions": {
        "traces": 500,
        "samples": 1000,
        "units": "traces × samples"
    },
    "inline_number": {
        "value": 55000,
        "units": "line number"
    }
}
```

**Action Items:**
- [ ] Update extract_inline_image handler (line ~800)
- [ ] Update extract_crossline_image handler (line ~858)
- [ ] Update extract_timeslice_image handler (line ~916)
- [ ] Update get_survey_metadata to include units
- [ ] Test with existing extraction calls

---

**TEST: Create Validation Test Suite**
Estimated: 3-4 hours

Create `/test/test_domain_validation.py`:

```python
import pytest
from src.domain_warnings import get_warning_system
from src.amplitude_normalization import get_normalizer

def test_cross_survey_amplitude_comparison_blocked():
    """Verify system blocks raw amplitude comparisons"""
    system = get_warning_system()

    context = "Compare amplitudes between Sepia and BS500"
    survey_ids = {"Sepia", "BS500"}

    warning = system.detect_cross_survey_comparison(context, survey_ids)

    assert warning is not None
    assert warning.severity == "critical"
    assert "normalization" in warning.message.lower()

def test_units_required_in_statistics():
    """Verify all statistics have units"""
    # Test that responses include units
    response = {
        "statistics": {
            "min": -1247.3,
            "max": 2487.3
        }
    }

    warnings = get_warning_system().check_units_in_response(response)

    assert len(warnings) > 0
    assert warnings[0].warning_type == "missing_units"

def test_rms_normalization_has_units():
    """Verify normalization includes units"""
    normalizer = get_normalizer()
    data = np.random.randn(1000)

    result = normalizer.normalize_by_rms(data)

    assert result.units == "unitless (RMS-normalized)"
    assert "units" in result.statistics["normalized_statistics"]

# 15+ more tests...
```

**Action Items:**
- [ ] Create /test/ directory if not exists
- [ ] Create test_domain_validation.py
- [ ] Write 15+ domain validation tests
- [ ] Add to CI/CD pipeline
- [ ] Document test coverage

---

## How To Resume Implementation

### Quick Start (Next Session)

**Option A: Continue Phase 2 (Recommended - Completes normalized comparison tools)**
```bash
# Start here:
1. Open /src/openvds_mcp_server.py
2. Go to line ~560 (after agent tools)
3. Add get_normalized_amplitude_statistics tool definition
4. Add compare_survey_quality_metrics tool definition
5. Implement handlers in call_tool() method
6. Test with prompts:
   - "Get RMS-normalized statistics for Sepia inline 55000"
   - "Compare Sepia and BS500 using normalized metrics"
```

**Option B: Jump to Phase 3 (Higher Impact - QC Agent)**
```bash
# Start here:
1. Create /src/qc/ directory
2. Create /src/qc/signal_quality.py
3. Implement SignalQualityAnalyzer class
4. Focus on SNR computation first (highest value)
5. Test with: "What's the SNR of Sepia inline 55000?"
```

**Option C: Integration & Testing**
```bash
# Start here:
1. Create /test/test_domain_validation.py
2. Write tests for domain_warnings
3. Test cross-survey comparison blocking
4. Verify units in responses
```

---

### Testing Current Implementation

**Test 1: Cross-Survey Comparison Warning**
```python
# In Python/MCP client:
prompt = "Compare amplitudes between Sepia and BS500"

# Expected: System should display warning
# Should mention: normalization, unsafe comparison, recommended tools
```

**Test 2: Units in Tool Descriptions**
```python
# Check tool descriptions include units requirements
# All extraction tools should mention:
# - Amplitudes: (unitless)
# - Samples: (samples)
# - Line numbers: (line numbers)
```

**Test 3: Normalization Works**
```python
from src.amplitude_normalization import get_normalizer
import numpy as np

# Create test data
data = np.random.randn(1000) * 500 + 10

# Test RMS normalization
normalizer = get_normalizer()
result = normalizer.normalize_by_rms(data)

print(result.statistics)
# Should show units: "unitless (RMS-normalized)"
```

---

## Key Design Decisions Made

### 1. Units Everywhere
**Decision:** ALL quantities must have units or explicit "(unitless)" annotation
**Rationale:** Prevents superficial statistics, ensures domain awareness
**Impact:** Requires updating all response handlers

### 2. Warning-Based Approach
**Decision:** Warn about unsafe comparisons rather than blocking entirely
**Rationale:** Allows expert users to proceed with caution, educational for novices
**Impact:** Requires detection logic in domain_warnings.py

### 3. Normalization as Standard
**Decision:** Provide multiple normalization methods (RMS, z-score, percentile)
**Rationale:** Different methods suit different use cases, RMS is industry standard
**Impact:** Created comprehensive amplitude_normalization.py module

### 4. Geoscientist Validation Loop
**Decision:** 20-test-case checklist for expert validation
**Rationale:** Ensures system meets domain expert standards before production
**Impact:** Created GEOSCIENTIST_REVIEW_CHECKLIST.md

### 5. Phased Implementation
**Decision:** 3 phases (warnings → normalization → QC agent)
**Rationale:** Incremental value delivery, can deploy Phase 1 immediately
**Impact:** Clear checkpoint and resume points

---

## Dependencies & Integration Points

### Existing Systems
- **VDSClient** (`/src/vds_client.py`) - Data extraction
- **Data Integrity Agent** (`/src/data_integrity.py`) - Statistics validation
- **Bulk Operation Router** (`/src/bulk_operation_router.py`) - Agent routing
- **Seismic Agent Manager** (`/src/agent_manager.py`) - Bulk operations

### New Integrations Needed
- **Phase 2.2:** Import `amplitude_normalization` in `openvds_mcp_server.py`
- **Phase 3:** Create `/src/qc/` package and import in server
- **UNITS task:** Update response formatting in extraction handlers

### External Dependencies
- numpy - Already used
- scipy - May need for FFT (Phase 3.1)
- No new external dependencies required

---

## Performance Considerations

### Computational Cost
- **Domain warnings:** Negligible (<1ms regex matching)
- **Normalization:** ~10-50ms depending on data size
- **QC analysis (Phase 3):** ~100-500ms for comprehensive analysis
  - SNR: FFT computation
  - Semblance: Multi-trace correlation
  - Footprint: 2D FFT

### Optimization Opportunities
- Cache normalization results per section
- Parallelize QC analyses (signal/spatial/artifacts independent)
- Pre-compute statistics during extraction (already cached in Elasticsearch)

---

## Documentation Status

### Complete
- ✅ DOMAIN_AWARE_ANTI_HALLUCINATION_PLAN.md - Full roadmap
- ✅ ARCHITECT_FEEDBACK_RESPONSE.md - Executive summary
- ✅ GEOSCIENTIST_REVIEW_CHECKLIST.md - Validation framework
- ✅ **THIS FILE** - Implementation checkpoint

### To Create
- [ ] API documentation for new tools (Phase 2.2)
- [ ] QC metrics interpretation guide (Phase 3)
- [ ] User guide for normalization methods
- [ ] Integration guide for DataHub (Phase 6)

---

## Git Commit Strategy

### Commit 1: Phase 1 Complete
```
feat: Add domain-aware anti-hallucination layer (Phase 1)

- Add domain_warnings.py for cross-survey comparison detection
- Update all extraction tool descriptions with domain knowledge
- Add comprehensive units requirements
- Create geoscientist review checklist with 20 test cases

BREAKING CHANGE: Tool descriptions now include extensive domain warnings
```

### Commit 2: Phase 2.1 Complete
```
feat: Add amplitude normalization for cross-survey comparisons

- Implement RMS normalization (industry standard)
- Implement z-score normalization (statistical standard)
- Implement percentile normalization (robust to outliers)
- Add relative contrast analysis for anomaly detection
- All methods include comprehensive units annotations
```

### Future Commits
- Phase 2.2: "feat: Add MCP tools for normalized comparisons"
- Phase 2.3: "feat: Add pattern analysis module"
- Phase 3: "feat: Implement QC Agent with SNR/frequency/continuity metrics"

---

## Success Metrics (For Next Review)

### Phase 1 Validation
- [ ] No cross-survey amplitude comparisons without warnings
- [ ] All tool descriptions include units requirements
- [ ] Geoscientist review checklist ready for use

### Phase 2 Validation
- [ ] Normalized comparison tools functional
- [ ] Cross-survey comparisons use normalization or quality metrics
- [ ] No raw amplitude comparisons between surveys

### Phase 3 Validation
- [ ] SNR computed in dB with proper methodology
- [ ] Frequency analysis returns Hz units
- [ ] Comprehensive QC returns overall score with recommendations
- [ ] Geoscientist confidence rating >4/5

---

## Contact & Handoff Notes

**Current State:**
- All Phase 1 code ready for testing
- Phase 2.1 (normalization) complete and ready for integration
- Docker rebuild needed to test new modules
- No blocking issues identified

**Immediate Next Steps:**
1. Test domain warnings with example prompts
2. Implement Phase 2.2 MCP tools (1-2 hours)
3. OR jump to Phase 3.1 for highest impact (SNR analysis)

**Questions for Next Session:**
1. Which phase to prioritize next? (2.2 for completion vs 3.1 for impact)
2. When is geoscientist available for validation? (Schedule for Week 4-5)
3. What's priority for demo/milestone? (Warnings vs normalized tools vs QC agent)

---

**Checkpoint Complete!**
**Resume Point:** Phase 2.2 (Add MCP tools) or Phase 3.1 (QC Agent)
**Estimated Remaining:** 2-3 days for Phases 2-3 complete
