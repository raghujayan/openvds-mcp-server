# Seismic Data QC Agent Design

**Purpose:** Build two specialized agents for seismic QC without hallucination
**Target Release:** v0.5.0 (after anti-hallucination foundation in v0.4.0)

---

## Two-Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SEISMIC QC SYSTEM                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ├──────────────────┬──────────────────┐
                            ▼                  ▼                  ▼
                ┌───────────────────┐  ┌──────────────┐  ┌──────────────┐
                │ DATA INTEGRITY    │  │ QUALITY      │  │ LLM          │
                │ AGENT             │  │ ASSESSMENT   │  │ INTERPRETER  │
                │                   │  │ AGENT        │  │              │
                │ "Truth Guardian"  │  │ "QC Analyst" │  │ "Summarizer" │
                └───────────────────┘  └──────────────┘  └──────────────┘
                         │                    │                  │
                         │                    │                  │
                    Validates              Detects            Describes
                    extracted             problems           findings
                    values                objectively        naturally
```

---

## Agent 1: Data Integrity Agent (Truth Guardian)

### Purpose
**Ensures extracted values are mathematically correct and traceable to source**

### Core Principle
**"Never trust, always verify" - Every extracted value must be algorithmically verifiable**

---

### Responsibilities

#### 1. Value Extraction Validation

**What it does:**
- Verifies statistical values match the actual data
- Confirms spatial coordinates are accurate
- Validates numerical consistency

**How it prevents hallucination:**
```python
# User/LLM claims: "Max amplitude is 2500"
# Agent extracts actual data and computes
actual_max = np.max(data)  # Result: 2487.3

validation = {
    "claimed_value": 2500,
    "actual_value": 2487.3,
    "difference": 12.7,
    "percent_error": 0.51,
    "verdict": "FAIL - claimed value incorrect",
    "tolerance": "±5% acceptable",
    "corrected_statement": "Max amplitude is 2487.3"
}
```

**Deterministic Checks:**
- [ ] Min/max values from numpy.min/max
- [ ] Mean from numpy.mean
- [ ] Standard deviation from numpy.std
- [ ] Percentiles from numpy.percentile
- [ ] RMS from numpy.sqrt(numpy.mean(data**2))
- [ ] Sample counts from data.shape

---

#### 2. Spatial Coordinate Validation

**What it does:**
- Verifies inline/crossline/sample numbers are within survey bounds
- Confirms coordinate transformations are correct
- Validates depth/time conversions

**Example:**
```python
# User claims: "Feature at inline 55000, crossline 8250, sample 6200"
# Agent validates:

validation = {
    "inline": {
        "claimed": 55000,
        "survey_range": [51001, 59001],
        "valid": True
    },
    "crossline": {
        "claimed": 8250,
        "survey_range": [8001, 8501],
        "valid": True
    },
    "sample": {
        "claimed": 6200,
        "survey_range": [4500, 8500],
        "valid": True
    },
    "verdict": "VALID - all coordinates within survey bounds"
}
```

---

#### 3. Data Provenance Tracking

**What it does:**
- Records exact data source and extraction parameters
- Maintains chain of custody for every value
- Enables reproducibility

**Provenance Record:**
```python
{
    "value": 2487.3,
    "metric": "max_amplitude",
    "source": {
        "vds_file": "/path/to/Sepia_3D_PSTM.vds",
        "file_hash": "sha256:abc123...",
        "section_type": "inline",
        "section_number": 55000,
        "sample_range": [6000, 7000],
        "extraction_time": "2025-11-01T12:34:56Z"
    },
    "computation": {
        "method": "numpy.max",
        "version": "1.24.3",
        "code_hash": "sha256:def456..."
    },
    "reproducible": True,
    "verification_command": "python verify.py --inline=55000 --metric=max"
}
```

---

#### 4. Numerical Consistency Checks

**What it does:**
- Validates mathematical relationships between statistics
- Catches impossible values
- Detects internal contradictions

**Consistency Rules:**
```python
def validate_statistics_consistency(stats):
    """Check if statistics are mathematically consistent"""

    checks = []

    # Rule 1: min ≤ mean ≤ max
    if not (stats['min'] <= stats['mean'] <= stats['max']):
        checks.append({
            "rule": "min ≤ mean ≤ max",
            "passed": False,
            "issue": f"Mean {stats['mean']} outside bounds [{stats['min']}, {stats['max']}]"
        })

    # Rule 2: median between p25 and p75
    if 'percentiles' in stats:
        if not (stats['percentiles']['p25'] <= stats['median'] <= stats['percentiles']['p75']):
            checks.append({
                "rule": "p25 ≤ median ≤ p75",
                "passed": False,
                "issue": "Median outside interquartile range"
            })

    # Rule 3: RMS ≥ mean (for seismic data)
    if 'rms' in stats:
        if stats['rms'] < abs(stats['mean']):
            checks.append({
                "rule": "RMS ≥ |mean|",
                "passed": False,
                "issue": "RMS inconsistent with mean"
            })

    # Rule 4: Percentiles are monotonically increasing
    if 'percentiles' in stats:
        percentile_values = [stats['percentiles'][f'p{p}'] for p in [10, 25, 50, 75, 90]]
        if percentile_values != sorted(percentile_values):
            checks.append({
                "rule": "Percentiles monotonically increasing",
                "passed": False,
                "issue": "Percentile order violation"
            })

    return {
        "all_consistent": all(c['passed'] for c in checks if 'passed' in c),
        "checks": checks
    }
```

---

### Implementation: Data Integrity Tools

#### Tool 1: validate_extracted_statistics

```python
@app.tool()
async def validate_extracted_statistics(
    survey_id: str,
    section_type: str,
    section_number: int,
    claimed_statistics: dict
) -> dict:
    """
    Validate claimed statistics against actual data.

    This is the Truth Guardian - it re-extracts data and verifies
    every claimed statistic is correct.

    Args:
        survey_id: Survey identifier
        section_type: 'inline', 'crossline', or 'timeslice'
        section_number: Section number
        claimed_statistics: Dict of claimed values to verify
            e.g., {"max": 2500, "mean": 145.3, "std": 487.2}

    Returns:
        Validation report with pass/fail for each claim
    """
    # Extract actual data
    data = await extract_section_data(survey_id, section_type, section_number)

    # Compute actual statistics
    actual_stats = {
        "min": float(np.min(data)),
        "max": float(np.max(data)),
        "mean": float(np.mean(data)),
        "median": float(np.median(data)),
        "std": float(np.std(data)),
        "rms": float(np.sqrt(np.mean(data**2)))
    }

    # Validate each claim
    validations = {}
    tolerance = 0.05  # 5% tolerance

    for metric, claimed_value in claimed_statistics.items():
        if metric not in actual_stats:
            validations[metric] = {
                "verdict": "UNKNOWN",
                "reason": f"Metric '{metric}' not computable"
            }
            continue

        actual_value = actual_stats[metric]
        error = abs(claimed_value - actual_value)
        percent_error = (error / abs(actual_value)) * 100 if actual_value != 0 else float('inf')

        passed = percent_error <= (tolerance * 100)

        validations[metric] = {
            "claimed": claimed_value,
            "actual": actual_value,
            "error": error,
            "percent_error": percent_error,
            "tolerance": f"±{tolerance*100}%",
            "verdict": "PASS" if passed else "FAIL",
            "corrected_statement": f"{metric.title()} is {actual_value:.2f}" if not passed else None
        }

    # Overall verdict
    all_passed = all(v['verdict'] == 'PASS' for v in validations.values() if v['verdict'] in ['PASS', 'FAIL'])

    return {
        "survey_id": survey_id,
        "section": f"{section_type} {section_number}",
        "validations": validations,
        "overall_verdict": "VALIDATED" if all_passed else "ERRORS_FOUND",
        "summary": f"{sum(1 for v in validations.values() if v['verdict'] == 'PASS')}/{len(validations)} claims validated",
        "provenance": {
            "extraction_time": datetime.now().isoformat(),
            "data_hash": hashlib.sha256(data.tobytes()).hexdigest()
        }
    }
```

#### Tool 2: verify_spatial_coordinates

```python
@app.tool()
async def verify_spatial_coordinates(
    survey_id: str,
    claimed_location: dict
) -> dict:
    """
    Verify spatial coordinates are within survey bounds.

    Args:
        claimed_location: {
            "inline": 55000,
            "crossline": 8250,
            "sample": 6200
        }

    Returns:
        Validation with survey bounds and validity
    """
    # Get survey metadata
    survey_info = await get_survey_metadata(survey_id)

    validations = {}

    for coord_type in ['inline', 'crossline', 'sample']:
        if coord_type in claimed_location:
            claimed = claimed_location[coord_type]
            range_key = f"{coord_type}_range"

            if range_key in survey_info:
                min_val, max_val = survey_info[range_key]
                valid = min_val <= claimed <= max_val

                validations[coord_type] = {
                    "claimed": claimed,
                    "survey_range": [min_val, max_val],
                    "valid": valid,
                    "issue": None if valid else f"{coord_type} {claimed} outside survey bounds [{min_val}, {max_val}]"
                }

    all_valid = all(v['valid'] for v in validations.values())

    return {
        "survey_id": survey_id,
        "validations": validations,
        "verdict": "VALID" if all_valid else "OUT_OF_BOUNDS",
        "recommendation": None if all_valid else "Verify claimed location or check for transcription error"
    }
```

#### Tool 3: check_statistical_consistency

```python
@app.tool()
async def check_statistical_consistency(
    statistics: dict
) -> dict:
    """
    Check if reported statistics are internally consistent.

    Catches impossible combinations like mean > max, or percentiles
    out of order.

    Args:
        statistics: Dict of statistical values

    Returns:
        Consistency check results
    """
    return validate_statistics_consistency(statistics)
```

---

## Agent 2: Quality Assessment Agent (QC Analyst)

### Purpose
**Objectively assess seismic data quality using deterministic algorithms**

### Core Principle
**"Measure, don't guess" - All quality assessments based on quantitative metrics**

---

## Seismic QC Aspects (Comprehensive List)

### Category 1: Signal Quality

#### 1.1 Signal-to-Noise Ratio (SNR)

**What it measures:** Ratio of signal power to noise power

**Deterministic Computation:**
```python
def compute_snr(data: np.ndarray) -> dict:
    """
    Compute SNR using multiple methods
    """
    # Method 1: RMS-based
    # Assume signal is coherent energy, noise is incoherent
    signal_rms = np.sqrt(np.mean(data**2))

    # Estimate noise from difference between adjacent traces
    noise_estimate = np.std(np.diff(data, axis=1))

    snr_rms = 20 * np.log10(signal_rms / noise_estimate) if noise_estimate > 0 else float('inf')

    # Method 2: Coherency-based
    # Compute cross-correlation between adjacent traces
    coherency = []
    for i in range(data.shape[1] - 1):
        corr = np.corrcoef(data[:, i], data[:, i+1])[0, 1]
        coherency.append(corr)

    avg_coherency = np.mean(coherency)

    return {
        "snr_db": snr_rms,
        "noise_level": noise_estimate,
        "signal_level": signal_rms,
        "coherency": avg_coherency,
        "quality_grade": grade_snr(snr_rms)
    }

def grade_snr(snr_db: float) -> str:
    """Grade SNR on standard scale"""
    if snr_db >= 30: return "Excellent"
    elif snr_db >= 20: return "Good"
    elif snr_db >= 10: return "Fair"
    elif snr_db >= 5: return "Poor"
    else: return "Very Poor"
```

**Quality Thresholds:**
- Excellent: SNR > 30 dB
- Good: SNR 20-30 dB
- Fair: SNR 10-20 dB
- Poor: SNR 5-10 dB
- Very Poor: SNR < 5 dB

---

#### 1.2 Frequency Content (Bandwidth)

**What it measures:** Frequency spectrum and bandwidth

**Deterministic Computation:**
```python
def analyze_frequency_content(data: np.ndarray, sample_rate: float) -> dict:
    """
    Analyze frequency content using FFT
    """
    # Compute power spectrum
    fft = np.fft.rfft(data, axis=0)
    power_spectrum = np.abs(fft)**2
    avg_power_spectrum = np.mean(power_spectrum, axis=1)

    # Frequency axis
    freqs = np.fft.rfftfreq(data.shape[0], 1/sample_rate)

    # Find dominant frequency
    dominant_freq = freqs[np.argmax(avg_power_spectrum)]

    # Compute bandwidth (frequencies containing 90% of energy)
    cumulative_energy = np.cumsum(avg_power_spectrum)
    total_energy = cumulative_energy[-1]

    low_freq_idx = np.where(cumulative_energy >= 0.05 * total_energy)[0][0]
    high_freq_idx = np.where(cumulative_energy >= 0.95 * total_energy)[0][0]

    bandwidth = freqs[high_freq_idx] - freqs[low_freq_idx]

    return {
        "dominant_frequency_hz": dominant_freq,
        "bandwidth_hz": bandwidth,
        "low_frequency_hz": freqs[low_freq_idx],
        "high_frequency_hz": freqs[high_freq_idx],
        "frequency_range": [freqs[low_freq_idx], freqs[high_freq_idx]],
        "quality_grade": grade_bandwidth(bandwidth)
    }

def grade_bandwidth(bandwidth: float) -> str:
    """Grade bandwidth on standard scale"""
    if bandwidth >= 60: return "Excellent (broadband)"
    elif bandwidth >= 40: return "Good"
    elif bandwidth >= 25: return "Fair"
    else: return "Poor (narrowband)"
```

**Quality Thresholds:**
- Excellent: BW > 60 Hz (broadband)
- Good: BW 40-60 Hz
- Fair: BW 25-40 Hz
- Poor: BW < 25 Hz (narrowband)

---

#### 1.3 Amplitude Consistency

**What it measures:** Spatial consistency of amplitudes (no sudden jumps)

**Deterministic Computation:**
```python
def analyze_amplitude_consistency(data: np.ndarray) -> dict:
    """
    Detect amplitude inconsistencies (jumps, scaling errors)
    """
    # Compute RMS amplitude per trace
    trace_rms = np.sqrt(np.mean(data**2, axis=0))

    # Compute statistics
    mean_rms = np.mean(trace_rms)
    std_rms = np.std(trace_rms)
    cv = (std_rms / mean_rms) * 100  # Coefficient of variation

    # Detect amplitude jumps (trace-to-trace changes > 3 std)
    diff_rms = np.abs(np.diff(trace_rms))
    threshold = 3 * std_rms
    jumps = np.where(diff_rms > threshold)[0]

    # Detect dead/weak traces (RMS < 10% of mean)
    weak_threshold = 0.1 * mean_rms
    weak_traces = np.where(trace_rms < weak_threshold)[0]

    # Detect hot/strong traces (RMS > mean + 3*std)
    hot_threshold = mean_rms + 3 * std_rms
    hot_traces = np.where(trace_rms > hot_threshold)[0]

    return {
        "mean_trace_rms": mean_rms,
        "std_trace_rms": std_rms,
        "coefficient_of_variation_percent": cv,
        "amplitude_jumps": {
            "count": len(jumps),
            "locations": jumps.tolist() if len(jumps) < 50 else jumps[:50].tolist(),
            "severity": "high" if len(jumps) > 10 else "moderate" if len(jumps) > 3 else "low"
        },
        "weak_traces": {
            "count": len(weak_traces),
            "locations": weak_traces.tolist() if len(weak_traces) < 20 else weak_traces[:20].tolist()
        },
        "hot_traces": {
            "count": len(hot_traces),
            "locations": hot_traces.tolist() if len(hot_traces) < 20 else hot_traces[:20].tolist()
        },
        "quality_grade": grade_amplitude_consistency(cv, len(jumps), len(weak_traces))
    }

def grade_amplitude_consistency(cv: float, jumps: int, weak: int) -> str:
    """Grade amplitude consistency"""
    issues = 0
    if cv > 50: issues += 1
    if jumps > 10: issues += 1
    if weak > data.shape[1] * 0.05: issues += 1  # >5% weak traces

    if issues == 0: return "Excellent"
    elif issues == 1: return "Good"
    elif issues == 2: return "Fair"
    else: return "Poor"
```

---

### Category 2: Spatial Continuity

#### 2.1 Reflector Continuity

**What it measures:** How continuous reflectors are (not broken or choppy)

**Deterministic Computation:**
```python
def analyze_reflector_continuity(data: np.ndarray) -> dict:
    """
    Measure reflector continuity using semblance/correlation
    """
    # Compute local semblance (multi-trace coherence)
    window_size = 5  # traces
    semblance_map = []

    for i in range(window_size//2, data.shape[1] - window_size//2):
        window = data[:, i-window_size//2:i+window_size//2+1]
        # Semblance = (stack energy) / (sum of trace energies)
        stack = np.sum(window, axis=1)
        stack_energy = np.sum(stack**2)
        trace_energies = np.sum(np.sum(window**2, axis=0))
        semblance = stack_energy / (window_size * trace_energies) if trace_energies > 0 else 0
        semblance_map.append(semblance)

    semblance_map = np.array(semblance_map)

    # Statistics
    mean_semblance = np.mean(semblance_map)

    # High semblance = good continuity
    # Low semblance = poor continuity (faults, noise, etc.)

    # Detect discontinuities (drops in semblance)
    threshold = mean_semblance * 0.5
    discontinuities = np.where(semblance_map < threshold)[0]

    return {
        "mean_semblance": mean_semblance,
        "semblance_std": np.std(semblance_map),
        "continuity_score": mean_semblance * 100,  # 0-100 scale
        "discontinuities": {
            "count": len(discontinuities),
            "locations": discontinuities.tolist() if len(discontinuities) < 50 else discontinuities[:50].tolist()
        },
        "quality_grade": grade_continuity(mean_semblance)
    }

def grade_continuity(semblance: float) -> str:
    """Grade reflector continuity"""
    if semblance >= 0.8: return "Excellent (highly continuous)"
    elif semblance >= 0.6: return "Good"
    elif semblance >= 0.4: return "Fair (moderate discontinuity)"
    else: return "Poor (highly discontinuous)"
```

---

### Category 3: Artifacts and Noise

#### 3.1 Multiple Detection

**What it measures:** Presence of multiples (unwanted reflections)

**Deterministic Computation:**
```python
def detect_multiples(data: np.ndarray, primary_time: int, expected_multiple_time: int) -> dict:
    """
    Detect multiples by comparing energy at primary and multiple times
    """
    # Extract energy around primary
    primary_window = data[primary_time-10:primary_time+10, :]
    primary_energy = np.mean(np.abs(primary_window))

    # Extract energy around expected multiple
    multiple_window = data[expected_multiple_time-10:expected_multiple_time+10, :]
    multiple_energy = np.mean(np.abs(multiple_window))

    # Multiple-to-primary ratio
    ratio = multiple_energy / primary_energy if primary_energy > 0 else 0

    return {
        "primary_time": primary_time,
        "primary_energy": primary_energy,
        "multiple_time": expected_multiple_time,
        "multiple_energy": multiple_energy,
        "multiple_to_primary_ratio": ratio,
        "multiple_strength": "strong" if ratio > 0.3 else "moderate" if ratio > 0.1 else "weak",
        "quality_impact": "high" if ratio > 0.3 else "moderate" if ratio > 0.1 else "low"
    }
```

#### 3.2 Acquisition Footprint Detection

**What it measures:** Regular patterns from acquisition geometry

**Deterministic Computation:**
```python
def detect_acquisition_footprint(data: np.ndarray) -> dict:
    """
    Detect acquisition footprint using 2D FFT
    """
    # Compute 2D FFT
    fft_2d = np.fft.fft2(data)
    power_2d = np.abs(fft_2d)**2

    # Look for spikes in wavenumber domain (regular patterns)
    # High energy at specific wavenumbers = footprint

    # Sort power values
    sorted_power = np.sort(power_2d.flatten())[::-1]

    # Check if top values are much larger than background
    # (indicates discrete patterns rather than smooth spectrum)
    top_10_mean = np.mean(sorted_power[:10])
    background_mean = np.mean(sorted_power[100:])

    footprint_ratio = top_10_mean / background_mean if background_mean > 0 else 1

    return {
        "footprint_ratio": footprint_ratio,
        "footprint_detected": footprint_ratio > 100,  # Strong discrete patterns
        "severity": "high" if footprint_ratio > 1000 else "moderate" if footprint_ratio > 100 else "low",
        "quality_impact": "Acquisition footprint may obscure geological features" if footprint_ratio > 100 else "Minimal footprint"
    }
```

---

### Category 4: Resolution

#### 4.1 Vertical Resolution

**What it measures:** Ability to distinguish closely spaced reflectors

**Deterministic Computation:**
```python
def estimate_vertical_resolution(data: np.ndarray, sample_rate: float) -> dict:
    """
    Estimate vertical resolution from dominant wavelength

    Vertical resolution ≈ λ/4 (quarter wavelength rule)
    """
    # Get dominant frequency
    freq_analysis = analyze_frequency_content(data, sample_rate)
    dominant_freq = freq_analysis['dominant_frequency_hz']

    # Assume velocity (need velocity model in practice)
    assumed_velocity = 3000  # m/s (typical for sedimentary rocks)

    # Wavelength = velocity / frequency
    wavelength = assumed_velocity / dominant_freq if dominant_freq > 0 else 0

    # Vertical resolution
    resolution = wavelength / 4

    return {
        "dominant_frequency_hz": dominant_freq,
        "assumed_velocity_m_per_s": assumed_velocity,
        "wavelength_m": wavelength,
        "vertical_resolution_m": resolution,
        "quality_grade": grade_resolution(resolution),
        "note": "Actual resolution depends on velocity model"
    }

def grade_resolution(resolution_m: float) -> str:
    """Grade vertical resolution"""
    if resolution_m < 10: return "Excellent (high resolution)"
    elif resolution_m < 20: return "Good"
    elif resolution_m < 40: return "Fair"
    else: return "Poor (low resolution)"
```

---

### Category 5: Data Completeness

#### 5.1 Gap Detection

**What it measures:** Missing data or dropouts

**Deterministic Computation:**
```python
def detect_data_gaps(data: np.ndarray) -> dict:
    """
    Detect gaps, dead traces, NaN values
    """
    # Check for NaN/inf values
    nan_count = np.sum(np.isnan(data))
    inf_count = np.sum(np.isinf(data))

    # Detect dead traces (all zeros or near-zero)
    trace_energy = np.sum(np.abs(data), axis=0)
    dead_threshold = np.median(trace_energy) * 0.01  # <1% of median energy
    dead_traces = np.where(trace_energy < dead_threshold)[0]

    # Detect gaps in trace numbers (if trace headers available)
    # For now, just report dead traces

    return {
        "nan_values": int(nan_count),
        "inf_values": int(inf_count),
        "dead_traces": {
            "count": len(dead_traces),
            "locations": dead_traces.tolist() if len(dead_traces) < 50 else dead_traces[:50].tolist(),
            "percentage": (len(dead_traces) / data.shape[1]) * 100
        },
        "data_completeness_percent": ((data.shape[1] - len(dead_traces)) / data.shape[1]) * 100,
        "quality_grade": grade_completeness(len(dead_traces), data.shape[1])
    }

def grade_completeness(dead_count: int, total_traces: int) -> str:
    """Grade data completeness"""
    completeness = ((total_traces - dead_count) / total_traces) * 100
    if completeness >= 99: return "Excellent (>99% complete)"
    elif completeness >= 95: return "Good (95-99% complete)"
    elif completeness >= 90: return "Fair (90-95% complete)"
    else: return "Poor (<90% complete)"
```

---

## Quality Assessment Tool Design

### Tool: comprehensive_qc_analysis

```python
@app.tool()
async def comprehensive_qc_analysis(
    survey_id: str,
    section_type: str,
    section_number: int,
    sample_range: list = None
) -> dict:
    """
    Perform comprehensive QC analysis on seismic section.

    Returns objective quality metrics across all QC categories.
    All assessments are deterministic and verifiable.

    Categories analyzed:
    1. Signal quality (SNR, frequency content, amplitude consistency)
    2. Spatial continuity (reflector continuity)
    3. Artifacts (multiples, footprint)
    4. Resolution (vertical resolution estimate)
    5. Completeness (gaps, dead traces)

    Returns:
        Detailed QC report with:
        - Quantitative metrics for each category
        - Quality grades (Excellent/Good/Fair/Poor)
        - Specific issues detected with locations
        - Overall quality score (0-100)
        - Recommendations for improvement
    """
    # Extract data
    extraction = await extract_section(survey_id, section_type, section_number, sample_range)
    data = extraction['data']

    # Run all QC analyses
    qc_report = {
        "survey_id": survey_id,
        "section": f"{section_type} {section_number}",
        "analysis_timestamp": datetime.now().isoformat(),

        "signal_quality": {
            "snr": compute_snr(data),
            "frequency_content": analyze_frequency_content(data, sample_rate=4.0),  # 4ms sample rate typical
            "amplitude_consistency": analyze_amplitude_consistency(data)
        },

        "spatial_continuity": {
            "reflector_continuity": analyze_reflector_continuity(data)
        },

        "artifacts": {
            "acquisition_footprint": detect_acquisition_footprint(data)
            # "multiples": detect_multiples(data, ...)  # Needs user-specified times
        },

        "resolution": {
            "vertical_resolution": estimate_vertical_resolution(data, sample_rate=4.0)
        },

        "completeness": {
            "gaps": detect_data_gaps(data)
        }
    }

    # Compute overall quality score
    qc_report["overall_quality"] = compute_overall_quality_score(qc_report)

    # Generate recommendations
    qc_report["recommendations"] = generate_qc_recommendations(qc_report)

    return qc_report


def compute_overall_quality_score(qc_report: dict) -> dict:
    """
    Compute weighted overall quality score
    """
    # Grade to numeric score mapping
    grade_scores = {
        "Excellent": 100,
        "Good": 75,
        "Fair": 50,
        "Poor": 25,
        "Very Poor": 0
    }

    # Extract grades (handle varying text formats)
    def extract_score(grade_text):
        for grade, score in grade_scores.items():
            if grade.lower() in grade_text.lower():
                return score
        return 50  # Default to Fair

    # Weighted scoring
    weights = {
        "snr": 0.3,
        "frequency": 0.2,
        "amplitude": 0.2,
        "continuity": 0.15,
        "completeness": 0.15
    }

    scores = {
        "snr": extract_score(qc_report["signal_quality"]["snr"]["quality_grade"]),
        "frequency": extract_score(qc_report["signal_quality"]["frequency_content"]["quality_grade"]),
        "amplitude": extract_score(qc_report["signal_quality"]["amplitude_consistency"]["quality_grade"]),
        "continuity": extract_score(qc_report["spatial_continuity"]["reflector_continuity"]["quality_grade"]),
        "completeness": extract_score(qc_report["completeness"]["gaps"]["quality_grade"])
    }

    overall_score = sum(scores[k] * weights[k] for k in weights.keys())

    # Overall grade
    if overall_score >= 85: overall_grade = "Excellent"
    elif overall_score >= 70: overall_grade = "Good"
    elif overall_score >= 50: overall_grade = "Fair"
    else: overall_grade = "Poor"

    return {
        "score": overall_score,
        "grade": overall_grade,
        "component_scores": scores,
        "weights": weights
    }


def generate_qc_recommendations(qc_report: dict) -> list:
    """
    Generate specific recommendations based on QC findings
    """
    recommendations = []

    # SNR issues
    snr = qc_report["signal_quality"]["snr"]["snr_db"]
    if snr < 10:
        recommendations.append({
            "issue": "Low signal-to-noise ratio",
            "severity": "high",
            "recommendation": "Consider reprocessing with stronger noise attenuation (f-k filter, radon demultiple)"
        })

    # Frequency issues
    bandwidth = qc_report["signal_quality"]["frequency_content"]["bandwidth_hz"]
    if bandwidth < 25:
        recommendations.append({
            "issue": "Narrow bandwidth (poor resolution)",
            "severity": "medium",
            "recommendation": "Check acquisition parameters (source signature). Consider spectral whitening if data supports it."
        })

    # Amplitude jumps
    jumps = qc_report["signal_quality"]["amplitude_consistency"]["amplitude_jumps"]["count"]
    if jumps > 10:
        recommendations.append({
            "issue": f"{jumps} amplitude discontinuities detected",
            "severity": "high",
            "recommendation": "Check for acquisition issues, missing gain corrections, or line merging problems"
        })

    # Dead traces
    dead = qc_report["completeness"]["gaps"]["dead_traces"]["count"]
    if dead > 0:
        recommendations.append({
            "issue": f"{dead} dead/weak traces detected",
            "severity": "medium",
            "recommendation": "Interpolate dead traces or flag for exclusion from interpretation"
        })

    # Continuity issues
    continuity = qc_report["spatial_continuity"]["reflector_continuity"]["mean_semblance"]
    if continuity < 0.4:
        recommendations.append({
            "issue": "Poor reflector continuity",
            "severity": "medium",
            "recommendation": "May indicate heavy faulting, poor migration, or low SNR. Check velocity model and migration parameters."
        })

    # Footprint
    if qc_report["artifacts"]["acquisition_footprint"]["footprint_detected"]:
        recommendations.append({
            "issue": "Acquisition footprint detected",
            "severity": "high",
            "recommendation": "Apply spatial filtering or reprocess with better acquisition footprint suppression"
        })

    return recommendations
```

---

## LLM Integration Layer

### How LLM Uses QC Agents (Without Hallucinating)

**Pattern:**
1. LLM **never** computes QC metrics directly
2. LLM **always** calls QC tools
3. LLM **only** describes/interprets returned metrics

**Example Workflow:**

```
User: "What's the quality of inline 55000?"

LLM Thought Process:
1. I need objective QC metrics
2. Call comprehensive_qc_analysis tool
3. Receive quantitative results
4. Describe findings in natural language

LLM Action:
→ Calls comprehensive_qc_analysis(survey_id='Sepia', section_type='inline', section_number=55000)

Tool Returns:
{
  "overall_quality": {"score": 72, "grade": "Good"},
  "signal_quality": {
    "snr": {"snr_db": 18.5, "quality_grade": "Fair"},
    "frequency_content": {"bandwidth_hz": 45, "quality_grade": "Good"},
    "amplitude_consistency": {
      "quality_grade": "Good",
      "amplitude_jumps": {"count": 3, "severity": "low"}
    }
  },
  "recommendations": [
    {
      "issue": "Low signal-to-noise ratio",
      "recommendation": "Consider noise attenuation"
    }
  ]
}

LLM Response to User:
"I've completed a comprehensive QC analysis of inline 55000. The overall quality is **Good**
(score: 72/100).

**Findings:**
- **Signal Quality**: Fair SNR of 18.5 dB, which is acceptable but could be improved. Good
  bandwidth of 45 Hz provides reasonable resolution.
- **Amplitude Consistency**: Good overall, with only 3 minor amplitude jumps detected (low severity).
- **Spatial Continuity**: Reflectors are well-continuous (not shown in excerpt).
- **Data Completeness**: Complete dataset with no gaps.

**Recommendation**: The main limitation is the signal-to-noise ratio. Reprocessing with stronger
noise attenuation (f-k filter or radon demultiple) could improve this.

Overall, this is good quality data suitable for interpretation, with the caveat that SNR may
limit detectability of subtle features."
```

**Key Points:**
✅ LLM never invented metrics
✅ All numbers came from deterministic tools
✅ LLM provided helpful interpretation
✅ Recommendations are from tool, not LLM invention

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER QUERY                                       │
│  "What's the quality of inline 55000? Any problems with the data?"      │
└─────────────────────────────────────────────────────────────────────────┘
                                  ▼
                     ┌────────────────────────┐
                     │ LLM (Claude)           │
                     │ - Understands intent   │
                     │ - Routes to tools      │
                     │ - Interprets results   │
                     └────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
        ┌───────────────────────┐   ┌──────────────────────┐
        │ Data Integrity Agent  │   │ Quality Assessment   │
        │                       │   │ Agent                │
        │ ✓ Validates claims    │   │ ✓ Computes SNR       │
        │ ✓ Verifies numbers    │   │ ✓ Analyzes frequency │
        │ ✓ Checks consistency  │   │ ✓ Detects artifacts  │
        │ ✓ Tracks provenance   │   │ ✓ Grades quality     │
        └───────────────────────┘   └──────────────────────┘
                    │                           │
                    └─────────────┬─────────────┘
                                  ▼
                        ┌──────────────────┐
                        │ Deterministic    │
                        │ Algorithms       │
                        │                  │
                        │ • NumPy/SciPy    │
                        │ • FFT            │
                        │ • Correlation    │
                        │ • Thresholds     │
                        └──────────────────┘
                                  │
                                  ▼
                        ┌──────────────────┐
                        │ VDS Data         │
                        │ (Ground Truth)   │
                        └──────────────────┘
```

---

## Implementation Roadmap

### Phase 1: Data Integrity Agent (v0.5.0)
**Effort:** 2-3 weeks

**Week 1:**
- [ ] Implement validate_extracted_statistics
- [ ] Implement verify_spatial_coordinates
- [ ] Implement check_statistical_consistency
- [ ] Add provenance tracking to all extractions

**Week 2:**
- [ ] Test suite for validation tools
- [ ] Integration with existing extraction tools
- [ ] Update tool descriptions

**Week 3:**
- [ ] Documentation and examples
- [ ] Beta testing
- [ ] Production deployment

---

### Phase 2: Quality Assessment Agent (v0.6.0)
**Effort:** 4-5 weeks

**Week 1-2: Signal Quality**
- [ ] Implement SNR computation
- [ ] Implement frequency analysis
- [ ] Implement amplitude consistency checks
- [ ] Test against known datasets

**Week 3: Spatial & Artifacts**
- [ ] Implement reflector continuity analysis
- [ ] Implement footprint detection
- [ ] Implement gap detection

**Week 4: Integration**
- [ ] Implement comprehensive_qc_analysis tool
- [ ] Implement scoring system
- [ ] Implement recommendation engine

**Week 5: Testing & Deployment**
- [ ] Validate against expert QC reports
- [ ] Tune thresholds and grades
- [ ] Production deployment

---

## Success Metrics

### Data Integrity Agent
- [ ] 100% of numeric claims validated
- [ ] 0% hallucinated statistics
- [ ] All extractions have provenance

### Quality Assessment Agent
- [ ] QC metrics match expert assessment >90%
- [ ] Quality grades correlate with expert grades (r > 0.8)
- [ ] Recommendations are actionable (user survey >4/5)

---

## Testing Strategy

### Test Data Requirements

1. **High Quality Data** - Known good sections for baseline
2. **Poor Quality Data** - Known problematic sections
3. **Specific Artifacts** - Data with known multiples, footprint, etc.
4. **Edge Cases** - Dead traces, gaps, extreme values

### Validation Against Expert QC

- Get 50+ sections with expert QC reports
- Run automated QC on same sections
- Compare grades and recommendations
- Tune thresholds to match expert judgment

---

## Next Steps

1. **Decision:** Which agent to implement first?
   - Recommend: Data Integrity Agent (simpler, foundational)

2. **Technical Spike:** (1-2 days)
   - Prototype SNR computation
   - Test frequency analysis accuracy
   - Validate against synthetic data

3. **Implementation:**
   - Create feature branch: `feature/qc-agents`
   - Start with Data Integrity tools
   - Incremental deployment

---

**Document Status:** Planning Complete
**Target Release:** v0.5.0 (Data Integrity), v0.6.0 (Quality Assessment)
**Dependencies:** Anti-hallucination foundation (v0.4.0)
