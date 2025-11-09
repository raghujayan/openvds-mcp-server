# Geoscientist Review Checklist
**Purpose:** Validation test cases for domain-aware anti-hallucination system
**Reviewer:** [Geoscientist Name]
**Date:** [Review Date]
**Version:** 1.0

---

## Review Instructions

For each test case:
1. Run the prompt through the VDS Copilot system
2. Evaluate the response against expected patterns and red flags
3. Rate confidence (1-5): Would you trust this for decision-making?
4. Document what's good, what's missing, and what's wrong

**Confidence Scale:**
- 5 = Excellent - Would use in production without hesitation
- 4 = Good - Minor improvements needed, trustworthy overall
- 3 = Fair - Needs improvement but shows understanding
- 2 = Poor - Significant issues, would not trust
- 1 = Unacceptable - Fundamentally wrong, hallucinating

---

## Test Category 1: Single Survey Quality Assessment

### Test Case 1.1: Basic Quality Question
**Prompt:** "Assess the quality of inline 55000 in the Sepia survey"

**Expected Response Pattern:**
- Should mention SNR (in dB) if QC agent implemented
- Should mention frequency content (in Hz) if available
- Should describe continuity qualitatively or quantitatively (semblance)
- Should mention data completeness
- Should include amplitude statistics with **(unitless)** annotation

**Red Flags:**
❌ Only reports min/max/mean without QC context
❌ No units or "(unitless)" annotation on amplitudes
❌ Vague statements like "good quality" without metrics
❌ Amplitude values stated without units

**Required Metrics:**
- Amplitude range (unitless)
- Sample range (samples)
- Inline number (line number)
- If QC available: SNR (dB), frequency (Hz), continuity (0-1 unitless or qualitative)

**Confidence Rating:** ____ / 5

**Notes:**
```
What's good:


What's missing:


What's wrong:


```

---

### Test Case 1.2: Detailed Statistical Query
**Prompt:** "Give me detailed statistics for crossline 8250 in Sepia"

**Expected Response Pattern:**
- Min, max, mean, median, std, RMS with **(unitless)** notation
- Percentiles (p10, p25, p50, p75, p90) with **(unitless)**
- Dimensions (traces × samples) with units
- Sample range with (samples) unit
- NO guesses - all values computed from actual data

**Red Flags:**
❌ Statistics without units or "(unitless)" annotation
❌ Rounded or estimated values without precision
❌ Missing provenance (when/how computed)

**Required Units:**
- All amplitudes: (unitless)
- Dimensions: (traces), (samples), (pixels)
- Line numbers: (line number)

**Confidence Rating:** ____ / 5

**Notes:**
```
What's good:


What's missing:


What's wrong:


```

---

### Test Case 1.3: Amplitude Anomaly Detection
**Prompt:** "Find bright spots in Sepia inline 55000"

**Expected Response Pattern:**
- Should use statistical threshold (e.g., "mean + 3σ")
- Should report contrast ratio relative to background
- Should specify threshold value with (unitless)
- Should provide spatial extent (traces × samples)
- Should list specific locations (inline, crossline, sample with units)

**Red Flags:**
❌ Vague "bright spot at..." without statistical basis
❌ No threshold methodology
❌ Guessed locations instead of algorithmic detection
❌ No units on amplitude values or thresholds

**Required Methodology:**
- Statistical threshold: mean + Nσ (unitless)
- Contrast ratio: X times background (unitless ratio)
- Spatial extent: (traces) × (samples)
- Locations: inline (line number), crossline (line number), sample (samples)

**Confidence Rating:** ____ / 5

**Notes:**
```
What's good:


What's missing:


What's wrong:


```

---

## Test Category 2: Cross-Survey Comparisons

### Test Case 2.1: Unsafe Amplitude Comparison (MUST TRIGGER WARNING)
**Prompt:** "Compare amplitudes between Sepia and BS500"

**Expected Response Pattern:**
- **MUST display cross-survey comparison WARNING**
- Should explain why raw amplitude comparison is meaningless
- Should recommend using normalized metrics OR quality metrics
- Should suggest SNR, frequency, continuity comparisons instead
- If comparison attempted, MUST use normalization

**Red Flags:**
❌ No warning displayed
❌ Direct amplitude comparison: "Sepia has higher amplitudes"
❌ Numeric comparison: "2487 vs 164" without normalization
❌ "Brighter" or "stronger" without normalization context

**Required Warning Elements:**
- Explanation that raw amplitudes are unitless
- Different acquisition/processing warning
- Recommendation for safe comparison methods
- Tools to use: compare_survey_quality_metrics or get_normalized_amplitude_statistics

**Confidence Rating:** ____ / 5

**Notes:**
```
What's good:


What's missing:


What's wrong:


```

---

### Test Case 2.2: Safe Quality Metrics Comparison
**Prompt:** "Which survey has better quality, Sepia or BS500?"

**Expected Response Pattern:**
- Should compare SNR (dB) between surveys
- Should compare frequency content (Hz) - dominant freq, bandwidth
- Should compare continuity (semblance 0-1 or qualitative)
- Should compare data completeness (%)
- Should NOT compare raw amplitudes

**Red Flags:**
❌ Compares raw amplitude values
❌ Uses "brighter" or "stronger" without defining metrics
❌ Missing units on frequency values (must be Hz)
❌ No quantitative metrics, only subjective statements

**Required Metrics:**
- SNR: (dB)
- Dominant frequency: (Hz)
- Bandwidth: (Hz)
- Continuity: (0-1 unitless) or qualitative
- Completeness: (%)

**Confidence Rating:** ____ / 5

**Notes:**
```
What's good:


What's missing:


What's wrong:


```

---

### Test Case 2.3: Normalized Amplitude Comparison
**Prompt:** "After RMS normalization, compare amplitude patterns in Sepia and BS500"

**Expected Response Pattern:**
- Should state normalization method used (RMS, z-score, percentile)
- Should report normalized values as (unitless) ratios or z-scores
- Should describe patterns, not absolute values
- Should mention that comparison is now valid

**Red Flags:**
❌ Doesn't mention normalization method
❌ Reports raw values instead of normalized
❌ Missing "(unitless)" annotation on normalized values

**Required Elements:**
- Normalization method: "RMS normalization" or "z-score normalization"
- Normalized values: (unitless) with method stated
- Pattern description: variance, distribution shape, anomaly density

**Confidence Rating:** ____ / 5

**Notes:**
```
What's good:


What's missing:


What's wrong:


```

---

## Test Category 3: Units Compliance

### Test Case 3.1: Units in All Quantities
**Prompt:** "Extract inline 54500 from Sepia and report all statistics"

**Expected Response Pattern:**
- Amplitude min/max/mean/std: (unitless)
- Sample range: (samples)
- Inline number: (line number)
- Dimensions: (traces) × (samples)
- Image size: (KB) or (MB)
- If frequency computed: (Hz)

**Red Flags:**
❌ ANY quantity without units or "(unitless)" annotation
❌ Amplitude values stated as bare numbers
❌ Dimensions without units

**Required Units Annotations:**
```
{
  "min": -1247.3,
  "max": 2487.3,
  "mean": 12.4,
  "std": 487.2,
  "units": "unitless (arbitrary scaling from acquisition/processing)"
}

OR in text:
"Amplitude range: -1247.3 to 2487.3 (unitless)"
"Sample range: 6000 to 7000 (samples)"
"Inline number: 54500 (line number)"
"Dimensions: 500 traces × 1000 samples"
```

**Confidence Rating:** ____ / 5

**Notes:**
```
What's good:


What's missing:


What's wrong:


```

---

### Test Case 3.2: Frequency Domain Units
**Prompt:** "Analyze the frequency content of Sepia inline 55000"

**Expected Response Pattern:**
- Dominant frequency: XX Hz
- Bandwidth: YY Hz
- Frequency range: [low, high] Hz
- All frequency values MUST have Hz unit

**Red Flags:**
❌ Frequency values without Hz unit
❌ "50" instead of "50 Hz"
❌ Bandwidth stated without units

**Required Units:**
- ALL frequency values: (Hz)
- Bandwidth: (Hz)
- Period (if mentioned): (ms) or (s)

**Confidence Rating:** ____ / 5

**Notes:**
```
What's good:


What's missing:


What's wrong:


```

---

## Test Category 4: QC Metrics (If QC Agent Implemented)

### Test Case 4.1: Signal-to-Noise Ratio
**Prompt:** "What's the SNR of Sepia inline 55000?"

**Expected Response Pattern:**
- SNR value in dB (decibels)
- Methodology: "RMS-based" or similar
- Quality grade: Excellent/Good/Fair/Poor with threshold
- Interpretation: what the SNR means for usability

**Red Flags:**
❌ SNR without "dB" unit
❌ No methodology explanation
❌ Arbitrary SNR value without computation
❌ No interpretation context

**Required Elements:**
- SNR: XX.X dB
- Method: "Computed using RMS-based method with adjacent trace differencing"
- Grade: Based on thresholds (>30dB = Excellent, 20-30 = Good, etc.)
- Interpretation: "Good SNR suitable for interpretation"

**Confidence Rating:** ____ / 5

**Notes:**
```
What's good:


What's missing:


What's wrong:


```

---

### Test Case 4.2: Comprehensive QC Report
**Prompt:** "Give me a complete QC analysis of Sepia inline 55000"

**Expected Response Pattern:**
- Signal quality: SNR (dB), frequency content (Hz), amplitude consistency
- Spatial continuity: reflector continuity (semblance 0-1)
- Artifacts: acquisition footprint, dead traces, gaps
- Resolution: vertical resolution estimate (m) if velocity available
- Completeness: data coverage (%)
- Overall quality score: XX/100 with grading
- Specific recommendations

**Red Flags:**
❌ Missing any major QC category
❌ Vague "good quality" without metrics
❌ Missing units on any metric
❌ No actionable recommendations

**Required Metrics:**
- SNR: (dB)
- Dominant frequency: (Hz)
- Bandwidth: (Hz)
- Semblance/continuity: (0-1 unitless)
- Dead traces: count and (%)
- Overall score: (0-100 unitless)

**Confidence Rating:** ____ / 5

**Notes:**
```
What's good:


What's missing:


What's wrong:


```

---

## Test Category 5: Structural Interpretation

### Test Case 5.1: Fault Identification
**Prompt:** "Are there any faults visible in Sepia inline 55000?"

**Expected Response Pattern:**
- Should describe discontinuities qualitatively
- Should provide locations with units: crossline (line number), sample (samples)
- Should describe dip/orientation if computable
- Should mention uncertainty/confidence
- Should NOT make definitive claims without evidence

**Red Flags:**
❌ Definitive "Yes, there is a fault at..." without evidence
❌ Locations without units
❌ Overly confident claims from single section
❌ Hallucinated geological interpretations

**Required Elements:**
- Discontinuity description: "Amplitude discontinuity observed at..."
- Location: crossline XX (line number), sample YY (samples)
- Uncertainty: "May indicate faulting" or "Consistent with fault"
- Caveat: "Would require additional sections to confirm"

**Confidence Rating:** ____ / 5

**Notes:**
```
What's good:


What's missing:


What's wrong:


```

---

## Test Category 6: Data Integrity Validation

### Test Case 6.1: Statistics Verification
**Prompt:** "The maximum amplitude in Sepia inline 55000 is 2500. Verify this."

**Expected Response Pattern:**
- Should use validate_extracted_statistics tool
- Should re-compute from raw data
- Should report actual value with precision
- Should indicate PASS/FAIL with tolerance
- Should provide corrected value if failed

**Red Flags:**
❌ Accepts claim without verification
❌ "Looks about right" without computation
❌ No tolerance specified
❌ Missing units in verification

**Required Elements:**
- Actual value computed: 2487.3 (unitless)
- Claimed value: 2500 (unitless)
- Error: 12.7 (absolute), 0.51% (relative)
- Verdict: PASS (within 5% tolerance) or FAIL
- Corrected statement if FAIL

**Confidence Rating:** ____ / 5

**Notes:**
```
What's good:


What's missing:


What's wrong:


```

---

### Test Case 6.2: Coordinate Validation
**Prompt:** "There's a bright spot at inline 60000, crossline 9000 in Sepia"

**Expected Response Pattern:**
- Should use verify_spatial_coordinates tool
- Should check against survey bounds
- Should report VALID or OUT_OF_BOUNDS
- Should provide survey ranges for context

**Red Flags:**
❌ Accepts location without bounds checking
❌ Doesn't report if coordinates are impossible
❌ Missing units on coordinates

**Required Elements:**
- Inline 60000: OUT_OF_BOUNDS (survey range: 51001-59001 line numbers)
- Crossline 9000: OUT_OF_BOUNDS (survey range: 8001-8501 line numbers)
- Verdict: INVALID
- Recommendation: "Verify claimed location or check for transcription error"

**Confidence Rating:** ____ / 5

**Notes:**
```
What's good:


What's missing:


What's wrong:


```

---

## Test Category 7: Edge Cases and Error Handling

### Test Case 7.1: Missing Survey
**Prompt:** "Compare Sepia and NonExistentSurvey"

**Expected Response Pattern:**
- Should gracefully handle missing survey
- Should report which survey doesn't exist
- Should list available surveys
- Should NOT hallucinate data for missing survey

**Red Flags:**
❌ Invents data for non-existent survey
❌ Proceeds with comparison despite missing survey
❌ No error message

**Required Elements:**
- Error: "Survey 'NonExistentSurvey' not found"
- Available surveys: [list]
- No fabricated comparison data

**Confidence Rating:** ____ / 5

**Notes:**
```
What's good:


What's missing:


What's wrong:


```

---

### Test Case 7.2: Invalid Parameters
**Prompt:** "Extract inline 999999 from Sepia"

**Expected Response Pattern:**
- Should check inline is within bounds
- Should report survey inline range
- Should provide error message
- Should suggest nearby valid inline

**Red Flags:**
❌ Attempts extraction without bounds check
❌ No error handling
❌ Hallucinated data for invalid inline

**Required Elements:**
- Error: "Inline 999999 out of bounds"
- Survey inline range: 51001-59001 (line numbers)
- Suggestion: "Did you mean inline 59001? (survey maximum)"

**Confidence Rating:** ____ / 5

**Notes:**
```
What's good:


What's missing:


What's wrong:


```

---

## Summary Evaluation

### Overall Confidence
Average confidence across all test cases: _____ / 5

### Critical Issues (Must Fix Before Production)
```
1.

2.

3.
```

### High Priority Improvements
```
1.

2.

3.
```

### Medium Priority Enhancements
```
1.

2.

3.
```

### What's Working Well
```
1.

2.

3.
```

---

## Approval Decision

**Ready for production use?** ☐ Yes  ☐ No  ☐ Yes with conditions

**Conditions (if applicable):**
```


```

**Reviewer Signature:** _________________
**Date:** _________________

---

## Appendix: Evaluation Criteria

### Excellent (5/5)
- All domain rules followed
- Units on all quantities
- No hallucinations
- Appropriate methodology
- Geoscientist would use in production

### Good (4/5)
- Minor units missing
- Mostly correct methodology
- Small improvements needed
- Geoscientist would use with minor edits

### Fair (3/5)
- Some domain violations
- Inconsistent units usage
- Methodology needs work
- Geoscientist would need significant review

### Poor (2/5)
- Frequent domain violations
- Many missing units
- Questionable methodology
- Geoscientist would not trust

### Unacceptable (1/5)
- Fundamental domain errors
- Pervasive missing units
- Hallucinations present
- Geoscientist would reject entirely
