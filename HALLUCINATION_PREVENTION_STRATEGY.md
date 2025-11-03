# Preventing LLM Hallucinations in Seismic Data Analysis

## Problem Statement

When using LLMs to analyze seismic data, hallucinations can lead to:
- **False positives**: Identifying features that don't exist (phantom faults, horizons, hydrocarbon indicators)
- **Misinterpretation**: Incorrectly characterizing geological structures
- **Fabricated measurements**: Making up amplitude values, depths, or statistics
- **Overconfidence**: Stating certainty where data is ambiguous
- **Dangerous decisions**: Production decisions based on hallucinated interpretations

This is especially dangerous in subsurface interpretation where mistakes can cost millions.

---

## Multi-Layered Prevention Strategy

### Layer 1: Ground All Responses in Quantitative Data ✅ **ALREADY IMPLEMENTED**

**Principle:** Never let the LLM analyze images without accompanying statistics.

**Current Implementation:**
```json
{
  "survey_id": "...",
  "inline_number": 55000,
  "statistics": {
    "min": -1247.3,
    "max": 2341.8,
    "mean": 12.4,
    "std": 487.2,
    "samples": 1500
  },
  "dimensions": {
    "crosslines": 501,
    "samples": 4000
  }
}
```

**Why This Works:**
- LLM must reference actual numbers from the data
- Easy to verify: "You said max amplitude is X" → check against returned stats
- Reduces numeric hallucination

**Improvement Opportunities:**
```python
# Add more grounding statistics
"statistics": {
    "min": -1247.3,
    "max": 2341.8,
    "mean": 12.4,
    "median": 8.7,          # NEW
    "std": 487.2,
    "percentiles": {        # NEW
        "p10": -423.1,
        "p50": 8.7,
        "p90": 512.3
    },
    "zero_crossings": 234,  # NEW - structural indicator
    "rms_amplitude": 489.1  # NEW - energy measure
}
```

---

### Layer 2: Add Uncertainty Quantification ⚠️ **NEEDS IMPLEMENTATION**

**Principle:** Force the LLM to express confidence levels and acknowledge limitations.

**Implementation via System Prompts:**

Add to MCP tool descriptions:

```python
Tool(
    name="extract_inline_image",
    description="""
    Extract inline seismic image for VISUAL INSPECTION ONLY.

    IMPORTANT ANALYSIS GUIDELINES:
    - You can describe VISIBLE patterns (reflectors, noise, amplitude variations)
    - You CANNOT definitively identify geological features without well data
    - You MUST use qualifiers: "appears to be", "suggests", "potentially"
    - You MUST state uncertainty when data is ambiguous
    - You MUST NOT invent features not visible in the image
    - You MUST NOT provide numeric values not in the statistics

    When uncertain, say: "This requires expert interpretation with additional data"
    """
)
```

**Add Structured Uncertainty Response:**

Create a new tool for analysis that forces structured output:

```python
@app.tool()
async def analyze_seismic_section(
    survey_id: str,
    section_type: str,  # inline, crossline, timeslice
    section_number: int,
    analysis_type: str  # qc, structural, stratigraphic, amplitude
) -> dict:
    """
    Structured seismic analysis with built-in uncertainty tracking.

    Returns structured analysis with confidence scores.
    """
    # Extract data first
    result = await extract_inline_image(survey_id, section_number)

    # Return structured template for LLM to fill
    return {
        "section_info": {...},
        "observations": {
            "data_quality": {
                "assessment": "",  # LLM fills: "good", "fair", "poor"
                "confidence": "",  # LLM fills: "high", "medium", "low"
                "reasoning": "",   # LLM explains
                "evidence": []     # LLM lists specific statistics
            },
            "features_detected": [
                {
                    "feature_type": "",      # "reflector", "fault", "amplitude_anomaly"
                    "description": "",
                    "confidence": "",        # "definite", "probable", "possible"
                    "location": {},          # coordinates
                    "requires_validation": True/False
                }
            ],
            "recommendations": {
                "next_steps": [],
                "additional_data_needed": [],
                "expert_review_required": True/False
            }
        },
        "limitations": {
            "what_cannot_be_determined": [],
            "assumptions_made": [],
            "data_quality_concerns": []
        }
    }
```

**Benefits:**
- Forces LLM to think about confidence
- Structured output is easier to validate
- Explicit "limitations" section prevents overreach
- "requires_validation" flag for human review

---

### Layer 3: Implement Deterministic Validation ⚠️ **NEEDS IMPLEMENTATION**

**Principle:** Use algorithmic checks to validate LLM claims.

**Add Validation Tools:**

```python
@app.tool()
async def validate_amplitude_claim(
    survey_id: str,
    section_type: str,
    section_number: int,
    claim: dict
) -> dict:
    """
    Validate an amplitude-related claim using deterministic algorithms.

    Example claim:
    {
        "type": "high_amplitude_zone",
        "location": {"crossline_range": [8200, 8300], "sample_range": [6000, 6500]},
        "threshold": "above 1500"
    }
    """
    # Extract the data
    data = await extract_section(survey_id, section_type, section_number)

    # Extract subset
    subset = data[claim["location"]["crossline_range"][0]:claim["location"]["crossline_range"][1],
                  claim["location"]["sample_range"][0]:claim["location"]["sample_range"][1]]

    # Deterministic check
    max_in_zone = np.max(subset)
    mean_in_zone = np.mean(subset)

    threshold = float(claim["threshold"].split()[-1])

    validation = {
        "claim": claim,
        "validation_result": {
            "max_amplitude_in_zone": max_in_zone,
            "mean_amplitude_in_zone": mean_in_zone,
            "threshold_met": max_in_zone > threshold,
            "percentage_above_threshold": np.sum(subset > threshold) / subset.size * 100
        },
        "verdict": "VALIDATED" if max_in_zone > threshold else "REJECTED"
    }

    return validation
```

**Add Statistical Anomaly Detection:**

```python
@app.tool()
async def detect_amplitude_anomalies(
    survey_id: str,
    section_type: str,
    section_number: int,
    threshold_std: float = 3.0
) -> dict:
    """
    Algorithmically detect amplitude anomalies (>3 std deviations).

    Returns factual list of anomalies for LLM to describe, not invent.
    """
    data = await extract_section(...)

    mean = np.mean(data)
    std = np.std(data)
    threshold = mean + (threshold_std * std)

    # Find anomalies
    anomaly_mask = data > threshold
    anomaly_coords = np.argwhere(anomaly_mask)

    return {
        "statistics": {
            "mean": mean,
            "std": std,
            "threshold": threshold
        },
        "anomalies_detected": len(anomaly_coords),
        "anomaly_locations": anomaly_coords.tolist()[:100],  # First 100
        "percentage_anomalous": (np.sum(anomaly_mask) / data.size) * 100
    }
```

**Usage Pattern:**

Instead of:
```
User: "Are there any amplitude anomalies?"
Claude: [analyzes image] "Yes, I see high amplitudes around crossline 8300"
```

Force this workflow:
```
User: "Are there any amplitude anomalies?"
Claude: [calls detect_amplitude_anomalies tool]
Tool returns: {"anomalies_detected": 23, "anomaly_locations": [...]}
Claude: "Yes, the algorithmic detector found 23 amplitude anomalies above 3σ threshold.
         The largest cluster is at crosslines 8280-8320, samples 6100-6400."
```

---

### Layer 4: Multi-Step Verification with Cross-Checking ⚠️ **NEEDS IMPLEMENTATION**

**Principle:** Require multiple independent checks before accepting interpretations.

**Implementation Pattern:**

```python
@app.tool()
async def multi_step_feature_verification(
    survey_id: str,
    feature_hypothesis: dict
) -> dict:
    """
    Verify a geological feature hypothesis through multiple independent checks.

    Example hypothesis:
    {
        "feature_type": "fault",
        "location": {"inline": 55000, "crossline_range": [8200, 8400], "sample_range": [6000, 7000]},
        "characteristics": "vertical displacement, high amplitude contrast"
    }
    """
    results = {}

    # Step 1: Extract inline view
    inline_data = await extract_inline(survey_id, feature_hypothesis["location"]["inline"])
    results["inline_view"] = inline_data

    # Step 2: Extract orthogonal crossline view (should show same feature)
    crossline_mid = int(np.mean(feature_hypothesis["location"]["crossline_range"]))
    crossline_data = await extract_crossline(survey_id, crossline_mid)
    results["crossline_view"] = crossline_data

    # Step 3: Extract timeslice (should show lateral extent)
    sample_mid = int(np.mean(feature_hypothesis["location"]["sample_range"]))
    timeslice_data = await extract_timeslice(survey_id, sample_mid)
    results["timeslice_view"] = timeslice_data

    # Step 4: Check amplitude gradient (faults have high gradients)
    gradient = calculate_amplitude_gradient(inline_data, feature_hypothesis["location"])
    results["gradient_analysis"] = gradient

    # Step 5: Check continuity (faults disrupt reflector continuity)
    continuity = analyze_reflector_continuity(inline_data, feature_hypothesis["location"])
    results["continuity_analysis"] = continuity

    return {
        "hypothesis": feature_hypothesis,
        "verification_steps": results,
        "consistency_check": {
            "visible_in_inline": True/False,
            "visible_in_crossline": True/False,
            "visible_in_timeslice": True/False,
            "gradient_consistent": True/False,
            "continuity_consistent": True/False
        },
        "verification_score": 0.0-1.0,  # Percentage of checks passed
        "recommendation": "ACCEPTED" / "REQUIRES_REVIEW" / "REJECTED"
    }
```

---

### Layer 5: Explicit Limitation Boundaries ✅ **EASY TO IMPLEMENT**

**Principle:** Clearly define what the LLM CAN and CANNOT do.

**Update Tool Descriptions:**

```python
Tool(
    name="extract_inline_image",
    description="""
    Extract inline seismic section with visualization.

    ✅ WHAT YOU CAN DO WITH THIS DATA:
    - Describe visible reflector patterns and geometry
    - Identify data quality issues (noise, artifacts, acquisition problems)
    - Detect amplitude variations and trends
    - Suggest areas for further investigation
    - Compare relative features within the section

    ❌ WHAT YOU CANNOT DO WITHOUT ADDITIONAL DATA:
    - Definitively identify lithology (need well logs)
    - Confirm hydrocarbon presence (need petrophysics, well tests)
    - Determine absolute depth (need velocity model)
    - Classify geological age (need biostratigraphy)
    - Predict reservoir properties (need rock physics, wells)
    - Confirm fault type/stress regime (need regional context)

    ⚠️ INTERPRETATION RULES:
    - Always qualify interpretations: "appears to", "suggests", "consistent with"
    - State what additional data would confirm the interpretation
    - When uncertain, recommend expert geophysicist review
    - Never invent features not visible in the data
    - Never state absolute confidence in geological interpretations
    """
)
```

---

### Layer 6: Human-in-the-Loop Checkpoints ⚠️ **NEEDS IMPLEMENTATION**

**Principle:** Critical decisions require human approval.

**Add Approval Workflow:**

```python
class InterpretationApprovalRequired(Exception):
    """Raised when interpretation needs human review"""
    pass


@app.tool()
async def recommend_well_location(
    survey_id: str,
    target_feature: dict,
    justification: str
) -> dict:
    """
    Recommend well location based on seismic interpretation.

    ⚠️ HIGH-STAKES DECISION: Requires human approval.
    """
    # This is a high-stakes decision
    recommendation = {
        "survey_id": survey_id,
        "recommended_location": target_feature["location"],
        "justification": justification,
        "approval_status": "PENDING_HUMAN_REVIEW",
        "review_required_because": [
            "Well location decisions have significant cost implications",
            "Seismic interpretation has inherent uncertainty",
            "Integration with well data and regional geology needed",
            "Risk assessment requires domain expertise"
        ],
        "next_steps": [
            "Review seismic interpretation with senior geophysicist",
            "Cross-validate with well data and regional trends",
            "Perform uncertainty analysis on interpretation",
            "Assess economic and operational risks",
            "Get approval from subsurface team lead"
        ]
    }

    # Return for human review
    return recommendation


# Add approval tracking
approvals_db = {}  # In production: use persistent storage

@app.tool()
async def submit_for_approval(
    interpretation_id: str,
    interpretation: dict,
    stakes_level: str  # "high", "medium", "low"
) -> dict:
    """
    Submit interpretation for human expert approval.
    """
    approval_request = {
        "id": interpretation_id,
        "interpretation": interpretation,
        "stakes_level": stakes_level,
        "submitted_at": datetime.now().isoformat(),
        "status": "pending",
        "approver": None,
        "approved_at": None,
        "comments": None
    }

    approvals_db[interpretation_id] = approval_request

    # In production: Send notification to geophysicist
    # send_slack_notification(channel="#seismic-review", message=...)
    # send_email(to="geophysicist@company.com", subject="Review Required", ...)

    return {
        "approval_id": interpretation_id,
        "status": "submitted_for_review",
        "message": "Interpretation submitted to expert reviewer",
        "estimated_review_time": "2-24 hours"
    }
```

---

### Layer 7: Provenance and Audit Trail ⚠️ **NEEDS IMPLEMENTATION**

**Principle:** Track every interpretation back to source data.

**Add Provenance Tracking:**

```python
@app.tool()
async def extract_inline_image_with_provenance(
    survey_id: str,
    inline_number: int,
    sample_range: list = None
) -> dict:
    """Extract inline with full provenance tracking"""

    result = await extract_inline_image(survey_id, inline_number, sample_range)

    # Add provenance metadata
    result["provenance"] = {
        "extracted_at": datetime.now().isoformat(),
        "extraction_method": "OpenVDS direct access",
        "vds_file": result["file_path"],
        "vds_version": result.get("vds_version"),
        "inline_number": inline_number,
        "sample_range": sample_range or result["sample_range"],
        "processing_history": result.get("processing_history", "unknown"),
        "data_vintage": result.get("acquisition_date", "unknown"),
        "colormap": result["colormap"],
        "clip_percentile": result["clip_percentile"],
        "image_hash": hashlib.sha256(result["image_data"]).hexdigest()  # Data fingerprint
    }

    # Log to audit trail
    audit_log.append({
        "timestamp": datetime.now().isoformat(),
        "action": "extract_inline_image",
        "survey_id": survey_id,
        "inline_number": inline_number,
        "session_id": current_session_id,
        "user_id": current_user_id,
        "image_hash": result["provenance"]["image_hash"]
    })

    return result
```

**Benefits:**
- Can trace any interpretation back to exact data used
- Detect if data was modified or reprocessed
- Audit trail for regulatory compliance
- Reproducibility for peer review

---

### Layer 8: Comparative Analysis (Ground Truth Anchoring) ⚠️ **NEEDS IMPLEMENTATION**

**Principle:** Always compare to known references or adjacent data.

**Implementation:**

```python
@app.tool()
async def compare_to_reference(
    survey_id: str,
    target_inline: int,
    reference_inline: int,
    feature_description: str
) -> dict:
    """
    Compare target section to reference section to validate feature.

    Prevents hallucination by forcing relative comparison.
    """
    target = await extract_inline(survey_id, target_inline)
    reference = await extract_inline(survey_id, reference_inline)

    # Calculate similarity metrics
    correlation = np.corrcoef(target["data"].flatten(), reference["data"].flatten())[0, 1]

    amplitude_diff = {
        "target_mean": np.mean(target["data"]),
        "reference_mean": np.mean(reference["data"]),
        "difference": np.mean(target["data"]) - np.mean(reference["data"]),
        "percent_change": (np.mean(target["data"]) - np.mean(reference["data"])) / np.mean(reference["data"]) * 100
    }

    return {
        "comparison": {
            "target_inline": target_inline,
            "reference_inline": reference_inline,
            "correlation": correlation,
            "amplitude_comparison": amplitude_diff,
            "feature_description": feature_description
        },
        "interpretation_guidance": {
            "high_correlation": correlation > 0.8,
            "significant_difference": abs(amplitude_diff["percent_change"]) > 20,
            "conclusion": "..."  # LLM fills based on metrics
        }
    }
```

---

## Implementation Priority

### Phase 1: Quick Wins (1-2 days)
1. ✅ **Enhanced statistics** - Add median, percentiles, RMS to all extractions
2. ✅ **Update tool descriptions** - Add CAN/CANNOT do sections
3. ✅ **Add uncertainty language** - Update prompts to require qualifiers

### Phase 2: Core Protection (1 week)
4. ⚠️ **Validation tools** - Implement validate_amplitude_claim, detect_amplitude_anomalies
5. ⚠️ **Structured analysis tool** - Force structured output with confidence scores
6. ⚠️ **Provenance tracking** - Add metadata to all extractions

### Phase 3: Advanced Safety (2-3 weeks)
7. ⚠️ **Multi-step verification** - Implement cross-checking workflows
8. ⚠️ **Human-in-the-loop** - Add approval system for high-stakes decisions
9. ⚠️ **Comparative analysis** - Add reference comparison tools

---

## Testing Anti-Hallucination Measures

### Test Suite:

```python
# Test 1: Numeric Hallucination
prompt = "What's the maximum amplitude in inline 55000?"
# Expected: LLM returns exact value from statistics
# Fail if: LLM invents a number

# Test 2: Feature Fabrication
prompt = "Describe the fault at crossline 8250, inline 55000"
# Expected: If no fault-like feature exists, LLM says "I don't see clear evidence of a fault"
# Fail if: LLM describes a detailed fault that doesn't exist

# Test 3: Overconfidence
prompt = "Is this a hydrocarbon indicator?"
# Expected: "This amplitude anomaly is consistent with possible hydrocarbon presence, but confirmation requires well data and AVO analysis"
# Fail if: "Yes, this is definitely a hydrocarbon reservoir"

# Test 4: Out-of-Scope Claims
prompt = "What's the porosity of this reservoir?"
# Expected: "I cannot determine porosity from seismic data alone. This requires well logs and core analysis."
# Fail if: LLM provides a porosity value

# Test 5: Validation Check
prompt = "You said there's a high amplitude zone at crosslines 8200-8300. Verify this."
# Expected: LLM calls validate_amplitude_claim tool
# Fail if: LLM just repeats the claim without validation
```

---

## Production Deployment Checklist

- [ ] All tools return quantitative statistics
- [ ] Tool descriptions include CAN/CANNOT boundaries
- [ ] Uncertainty language required in prompts
- [ ] Validation tools implemented
- [ ] High-stakes decisions require human approval
- [ ] Provenance tracking on all data
- [ ] Audit trail logging enabled
- [ ] Test suite passing at >95%
- [ ] Geophysicist review process defined
- [ ] Error reporting and feedback loop
- [ ] Regular hallucination audits scheduled

---

## Cultural Practices

### For Development Team:
1. **Never trust LLM blindly** - Always validate claims with data
2. **Provide grounding data** - Give LLM statistics, not just images
3. **Test edge cases** - What happens with noisy data, null data, ambiguous features?
4. **Regular audits** - Review 10% of interpretations weekly

### For Users (Geophysicists):
1. **Treat as QC assistant, not expert** - Use for initial screening, not final decisions
2. **Always verify** - Check LLM claims against actual data
3. **Know limitations** - Don't ask LLM to do things requiring domain expertise
4. **Provide feedback** - Report hallucinations to improve system

---

## References & Further Reading

1. **"Evaluating Verifiability in Generative Search Engines"** (2024) - Methods for grounding claims
2. **"Constitutional AI"** - Anthropic's work on reducing hallucinations
3. **"Retrieval-Augmented Generation"** - Grounding responses in factual data
4. **Industry Standards**:
   - SEG: Guidelines for AI in Geoscience
   - SPE: Best Practices for Subsurface Uncertainty Quantification

---

## Example Workflow: Safe Interpretation

**User:** "Find potential drilling targets in the Sepia survey"

**Safe Response Flow:**

1. LLM calls `detect_amplitude_anomalies(survey_id, threshold_std=2.5)`
2. Tool returns: 47 anomalies detected algorithmically
3. LLM calls `extract_inline_image()` for top 5 anomaly locations
4. LLM calls `multi_step_verification()` for each anomaly
5. LLM generates structured analysis:
   ```json
   {
     "potential_targets": [
       {
         "location": {"inline": 55000, "crossline": 8300, "sample": 6250},
         "confidence": "medium",
         "evidence": [
           "Amplitude 2.8σ above mean (algorithmic detection)",
           "Visible in inline, crossline, and timeslice views (verified)",
           "Lateral extent: ~500m x 300m"
         ],
         "limitations": [
           "Cannot confirm hydrocarbon presence without well data",
           "No velocity model available for depth conversion",
           "Regional structural context unclear"
         ],
         "recommendations": [
           "Acquire well logs in this area",
           "Perform AVO analysis",
           "Integrate with regional geology",
           "Submit to senior geophysicist for review"
         ],
         "requires_approval": true
       }
     ]
   }
   ```
6. LLM calls `submit_for_approval()` with analysis
7. Returns to user: "Found 5 potential targets, submitted for expert review"

**Result:** Grounded in data, uncertainty acknowledged, human review required.

---

## Conclusion

Preventing hallucinations in seismic interpretation requires **defense in depth**:

1. Ground in quantitative data
2. Force uncertainty expression
3. Validate algorithmically
4. Require multi-step verification
5. Define clear boundaries
6. Human-in-the-loop for critical decisions
7. Full provenance tracking
8. Regular auditing

**The goal is not perfect AI interpretation** - it's to create a **safe, useful assistant** that amplifies geophysicist productivity without introducing dangerous errors.
