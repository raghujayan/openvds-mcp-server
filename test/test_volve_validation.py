"""
Volve Dataset Validation Tests

Tests QC agent computations against published Volve ground truth values.
This provides independent external validation (not AI validating AI).

Run these tests after implementing Phase 3 (QC Agent) to validate:
- SNR computations match published reports (±3 dB tolerance for VDS)
- Frequency analysis matches published values (±5 Hz tolerance)
- Amplitude extraction is accurate (±5-8% tolerance for VDS compression)

SETUP REQUIRED:
1. Download Volve dataset from https://www.equinor.com/energy/volve-data-sharing
2. Convert SEG-Y to VDS format (or load SEG-Y directly)
3. Add to VDS data directory as "Volve_ST10010"
4. Implement Phase 3 QC Agent (signal_quality.py, etc.)

INTERPRETING RESULTS:
✅ PASS within published range → Computation is correct
✅ PASS within tolerance → VDS conversion acceptable, computation correct
⚠️  FAIL but close → Investigate VDS conversion quality
❌ FAIL significantly → Bug in computation or data issue

Usage:
    pytest test_volve_validation.py -v
    pytest test_volve_validation.py -v -k "critical"  # Run critical tests only
"""

import pytest
import numpy as np
from typing import Dict, Any

try:
    from volve_ground_truth import (
        VOLVE_VALIDATION_TESTS,
        VOLVE_SURVEY_GEOMETRY,
        get_critical_tests,
        get_tests_by_metric,
        check_tolerance,
        VDS_CONVERSION_NOTES,
    )
except ImportError:
    pytest.skip("volve_ground_truth not found", allow_module_level=True)

# These imports will work once Phase 3 is implemented
try:
    from src.qc.signal_quality import SignalQualityAnalyzer
    from src.qc.spatial_quality import SpatialQualityAnalyzer
    from src.vds_client import VDSClient
    QC_AGENT_AVAILABLE = True
except ImportError:
    QC_AGENT_AVAILABLE = False
    pytest.skip("QC Agent not yet implemented (Phase 3)", allow_module_level=True)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture(scope="module")
def vds_client():
    """Create VDS client for Volve data access"""
    client = VDSClient()
    return client


@pytest.fixture(scope="module")
def volve_survey_check(vds_client):
    """Verify Volve survey is available"""
    surveys = vds_client.list_surveys()
    volve_id = VOLVE_SURVEY_GEOMETRY["survey_id"]

    if volve_id not in surveys:
        pytest.skip(f"Volve survey '{volve_id}' not found. Download from Equinor and add to VDS data directory.")

    return volve_id


# ==============================================================================
# PARAMETRIZED VALIDATION TESTS
# ==============================================================================

@pytest.mark.parametrize("test_spec", VOLVE_VALIDATION_TESTS, ids=lambda t: t.test_id)
def test_volve_validation(test_spec, vds_client, volve_survey_check):
    """
    Validate QC metric against published Volve ground truth

    This test:
    1. Extracts data from Volve VDS at specified location
    2. Computes metric using our QC agent
    3. Compares to published value from Equinor reports
    4. Accounts for VDS conversion tolerance

    Each test is independent and validates a specific metric.
    """

    print(f"\n{'='*70}")
    print(f"Test: {test_spec.test_id} - {test_spec.description}")
    print(f"Source: {test_spec.source_reference}")
    print(f"{'='*70}")

    # Skip if location is survey-wide (not yet implemented)
    if test_spec.location is None:
        pytest.skip("Survey-wide metrics not yet implemented")

    # Extract data from VDS
    inline = test_spec.location["inline"]
    crossline = test_spec.location.get("crossline")
    sample_range_ms = test_spec.location.get("sample_range_ms")

    # Convert ms to sample indices (4ms sample rate)
    if sample_range_ms:
        sample_range = [t // 4 for t in sample_range_ms]
    else:
        sample_range = None

    # Extract inline data
    extraction = vds_client.extract_inline(
        survey_id=volve_survey_check,
        inline_number=inline,
        sample_range=sample_range,
        return_data=True  # Get raw data for QC computation
    )

    data = extraction.get("data")
    if data is None:
        pytest.fail(f"Failed to extract data from Volve at inline {inline}")

    print(f"Extracted data shape: {data.shape}")

    # Compute metric based on test type
    if test_spec.metric == "snr_db":
        # Compute SNR using our QC agent
        signal_analyzer = SignalQualityAnalyzer()
        result = signal_analyzer.compute_snr(data, sample_rate=4.0)  # 4ms sample rate
        computed = result["snr_db"]
        print(f"Computed SNR: {computed:.2f} dB")

    elif test_spec.metric == "dominant_frequency_hz":
        # Compute dominant frequency
        signal_analyzer = SignalQualityAnalyzer()
        result = signal_analyzer.analyze_frequency_content(data, sample_rate=4.0)
        computed = result["dominant_frequency_hz"]
        print(f"Computed Dominant Frequency: {computed:.1f} Hz")

    elif test_spec.metric == "bandwidth_hz":
        # Compute bandwidth
        signal_analyzer = SignalQualityAnalyzer()
        result = signal_analyzer.analyze_frequency_content(data, sample_rate=4.0)
        computed = result["bandwidth_hz"]
        print(f"Computed Bandwidth: {computed:.1f} Hz")

    elif test_spec.metric == "max_amplitude":
        # Extract max amplitude
        computed = float(np.max(np.abs(data)))
        print(f"Computed Max Amplitude: {computed:.1f} (unitless)")

    elif test_spec.metric == "rms_amplitude":
        # Extract RMS amplitude
        computed = float(np.sqrt(np.mean(data**2)))
        print(f"Computed RMS Amplitude: {computed:.1f} (unitless)")

    elif test_spec.metric == "fold_coverage":
        # Fold coverage (from metadata, not data)
        fold = extraction.get("fold_coverage")
        if fold is None:
            pytest.skip("Fold coverage not available in VDS metadata")
        computed = fold
        print(f"Fold Coverage: {computed} traces/bin")

    else:
        pytest.skip(f"Metric '{test_spec.metric}' not yet implemented")

    # Validate against expected value
    validation_result = check_tolerance(
        computed=computed,
        expected=test_spec.expected_value,
        tolerance=test_spec.tolerance,
        units=test_spec.units,
    )

    print(f"\nExpected: {test_spec.expected_value} {test_spec.units}")
    print(f"Computed: {computed:.2f} {test_spec.units}")
    print(f"Tolerance: ±{test_spec.tolerance} {test_spec.units}")
    print(f"Verdict: {validation_result['verdict']}")

    if not validation_result["passed"]:
        # Test failed - provide detailed diagnostic
        print(f"\n⚠️  VALIDATION FAILED")
        print(f"This could indicate:")
        print(f"  1. VDS conversion introduced more loss than expected")
        print(f"  2. Bug in QC computation algorithm")
        print(f"  3. Incorrect ground truth value")
        print(f"\nDiagnostic Information:")
        print(f"  Within published range: {validation_result.get('within_published_range', 'N/A')}")
        print(f"  Difference: {validation_result.get('difference', 'N/A')}")
        print(f"\nNext Steps:")
        print(f"  - Check VDS conversion quality")
        print(f"  - Compare to SEG-Y extraction")
        print(f"  - Review computation algorithm")

    # Assert passes (will fail test if validation failed)
    assert validation_result["passed"], validation_result["verdict"]

    print(f"\n✅ Test {test_spec.test_id} PASSED")


# ==============================================================================
# CRITICAL TESTS (Must Pass for Production)
# ==============================================================================

@pytest.mark.critical
@pytest.mark.parametrize("test_spec", get_critical_tests(), ids=lambda t: t.test_id)
def test_critical_validations(test_spec, vds_client, volve_survey_check):
    """
    Critical validation tests - must pass for production deployment

    These test the most important QC metrics:
    - SNR at multiple depths
    - Dominant frequency at reservoir
    - Key amplitude calibration points

    If any critical test fails, DO NOT deploy to production.
    """
    # Same implementation as test_volve_validation
    # (parametrization will run only critical tests when marked)
    test_volve_validation(test_spec, vds_client, volve_survey_check)


# ==============================================================================
# METRIC-SPECIFIC TEST GROUPS
# ==============================================================================

@pytest.mark.snr
@pytest.mark.parametrize("test_spec", get_tests_by_metric("snr_db"), ids=lambda t: t.test_id)
def test_snr_validation(test_spec, vds_client, volve_survey_check):
    """SNR validation tests only"""
    test_volve_validation(test_spec, vds_client, volve_survey_check)


@pytest.mark.frequency
@pytest.mark.parametrize(
    "test_spec",
    get_tests_by_metric("dominant_frequency_hz") + get_tests_by_metric("bandwidth_hz"),
    ids=lambda t: t.test_id
)
def test_frequency_validation(test_spec, vds_client, volve_survey_check):
    """Frequency analysis validation tests only"""
    test_volve_validation(test_spec, vds_client, volve_survey_check)


@pytest.mark.amplitude
@pytest.mark.parametrize(
    "test_spec",
    get_tests_by_metric("max_amplitude") + get_tests_by_metric("rms_amplitude"),
    ids=lambda t: t.test_id
)
def test_amplitude_validation(test_spec, vds_client, volve_survey_check):
    """Amplitude extraction validation tests only"""
    test_volve_validation(test_spec, vds_client, volve_survey_check)


# ==============================================================================
# SUMMARY REPORT
# ==============================================================================

def test_validation_summary(vds_client, volve_survey_check):
    """
    Generate validation summary report

    This test always passes but prints a summary of what was validated.
    Run after all other tests to see overall status.
    """
    print("\n" + "="*70)
    print("VOLVE VALIDATION SUMMARY")
    print("="*70)

    print(f"\nDataset: {VOLVE_SURVEY_GEOMETRY['survey_name']}")
    print(f"Survey ID: {VOLVE_SURVEY_GEOMETRY['survey_id']}")
    print(f"Acquisition Year: {VOLVE_SURVEY_GEOMETRY['acquisition_year']}")

    print(f"\nTotal Validation Tests: {len(VOLVE_VALIDATION_TESTS)}")
    print(f"Critical Tests: {len(get_critical_tests())}")

    print("\nTest Categories:")
    for metric in ["snr_db", "dominant_frequency_hz", "bandwidth_hz", "max_amplitude", "rms_amplitude"]:
        count = len(get_tests_by_metric(metric))
        if count > 0:
            print(f"  {metric}: {count} tests")

    print("\nVDS Conversion Notes:")
    print("-" * 70)
    for line in VDS_CONVERSION_NOTES.split('\n')[:10]:
        print(line)

    print("\n" + "="*70)
    print("All validation tests configured. Run with:")
    print("  pytest test_volve_validation.py -v           # All tests")
    print("  pytest test_volve_validation.py -v -m critical  # Critical only")
    print("  pytest test_volve_validation.py -v -m snr       # SNR tests only")
    print("="*70)

    # This test always passes
    assert True


# ==============================================================================
# STANDALONE USAGE (for debugging)
# ==============================================================================

if __name__ == "__main__":
    print("Volve Validation Test Suite")
    print("=" * 70)
    print(f"Total Tests: {len(VOLVE_VALIDATION_TESTS)}")
    print(f"Critical Tests: {len(get_critical_tests())}")
    print("\nTo run tests:")
    print("  pytest test_volve_validation.py -v")
    print("\nTo run critical tests only:")
    print("  pytest test_volve_validation.py -v -m critical")
    print("\nTo run specific metric tests:")
    print("  pytest test_volve_validation.py -v -m snr")
    print("  pytest test_volve_validation.py -v -m frequency")
    print("  pytest test_volve_validation.py -v -m amplitude")
