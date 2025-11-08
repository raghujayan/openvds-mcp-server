"""
Data Integrity Agent - Truth Guardian

Ensures extracted values are mathematically correct and traceable to source.

Core Principle: "Never trust, always verify"
- Every statistical claim is re-computed from raw data
- Every coordinate is validated against survey bounds
- Every value has provenance tracking

This prevents LLM hallucinations by grounding all claims in actual computation.
"""

import numpy as np
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger("data-integrity")


class ValidationResult:
    """Result of a validation check"""

    def __init__(self, verdict: str, details: Dict[str, Any]):
        self.verdict = verdict  # "PASS", "FAIL", "UNKNOWN"
        self.details = details

    def passed(self) -> bool:
        return self.verdict == "PASS"

    def failed(self) -> bool:
        return self.verdict == "FAIL"


class DataIntegrityAgent:
    """
    Data Integrity Agent - validates all extracted values and claims
    """

    def __init__(self, tolerance: float = 0.05):
        """
        Initialize Data Integrity Agent

        Args:
            tolerance: Percentage tolerance for numeric validation (default 5%)
        """
        self.tolerance = tolerance
        logger.info(f"Data Integrity Agent initialized with {tolerance*100}% tolerance")

    def validate_statistics(
        self,
        data: np.ndarray,
        claimed_statistics: Dict[str, float],
        tolerance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Validate claimed statistics against actual data

        Re-computes all statistics from raw data and compares to claims.

        Args:
            data: Raw seismic data array
            claimed_statistics: Dictionary of claimed values
                e.g., {"max": 2500, "mean": 145.3, "std": 487.2}
            tolerance: Override default tolerance for this validation

        Returns:
            Validation report with pass/fail for each claim
        """
        if tolerance is None:
            tolerance = self.tolerance

        # Compute actual statistics from data
        actual_stats = self._compute_statistics(data)

        # Validate each claim
        validations = {}

        for metric, claimed_value in claimed_statistics.items():
            if metric not in actual_stats:
                validations[metric] = {
                    "verdict": "UNKNOWN",
                    "reason": f"Metric '{metric}' not computable",
                    "claimed": claimed_value
                }
                continue

            actual_value = actual_stats[metric]
            validation = self._validate_value(
                claimed_value,
                actual_value,
                tolerance,
                metric
            )
            validations[metric] = validation

        # Overall verdict
        fail_count = sum(1 for v in validations.values() if v['verdict'] == 'FAIL')
        pass_count = sum(1 for v in validations.values() if v['verdict'] == 'PASS')
        unknown_count = sum(1 for v in validations.values() if v['verdict'] == 'UNKNOWN')

        overall_verdict = "VALIDATED" if fail_count == 0 else "ERRORS_FOUND"

        return {
            "validations": validations,
            "overall_verdict": overall_verdict,
            "summary": {
                "total_claims": len(validations),
                "passed": pass_count,
                "failed": fail_count,
                "unknown": unknown_count
            },
            "tolerance_used": tolerance,
            "timestamp": datetime.now().isoformat()
        }

    def _compute_statistics(self, data: np.ndarray) -> Dict[str, float]:
        """
        Compute standard statistics from data

        Args:
            data: Raw data array

        Returns:
            Dictionary of computed statistics
        """
        # Remove NaN values for computation
        valid_data = data[~np.isnan(data)]

        if len(valid_data) == 0:
            logger.warning("No valid data for statistics computation")
            return {}

        stats = {
            "min": float(np.min(valid_data)),
            "max": float(np.max(valid_data)),
            "mean": float(np.mean(valid_data)),
            "median": float(np.median(valid_data)),
            "std": float(np.std(valid_data)),
            "rms": float(np.sqrt(np.mean(valid_data**2))),
            "p10": float(np.percentile(valid_data, 10)),
            "p25": float(np.percentile(valid_data, 25)),
            "p50": float(np.percentile(valid_data, 50)),
            "p75": float(np.percentile(valid_data, 75)),
            "p90": float(np.percentile(valid_data, 90)),
            "sample_count": int(len(valid_data))
        }

        return stats

    def _validate_value(
        self,
        claimed: float,
        actual: float,
        tolerance: float,
        metric: str
    ) -> Dict[str, Any]:
        """
        Validate a single value against actual

        Args:
            claimed: Claimed value
            actual: Actual computed value
            tolerance: Tolerance as decimal (0.05 = 5%)
            metric: Name of metric being validated

        Returns:
            Validation result dictionary
        """
        error = abs(claimed - actual)

        # Calculate percent error
        if actual != 0:
            percent_error = (error / abs(actual)) * 100
        else:
            # If actual is zero, use absolute error
            percent_error = error * 100

        # Determine if passed
        passed = percent_error <= (tolerance * 100)

        result = {
            "claimed": claimed,
            "actual": actual,
            "error": error,
            "percent_error": round(percent_error, 2),
            "tolerance_percent": tolerance * 100,
            "verdict": "PASS" if passed else "FAIL"
        }

        # Add correction if failed
        if not passed:
            result["corrected_statement"] = f"{metric.title()} is {actual:.2f} (not {claimed})"

        return result

    def verify_coordinates(
        self,
        claimed_location: Dict[str, int],
        survey_bounds: Dict[str, Tuple[int, int]]
    ) -> Dict[str, Any]:
        """
        Verify spatial coordinates are within survey bounds

        Args:
            claimed_location: Dictionary with coordinate claims
                e.g., {"inline": 55000, "crossline": 8250, "sample": 6200}
            survey_bounds: Dictionary with valid ranges
                e.g., {
                    "inline_range": (51001, 59001),
                    "crossline_range": (8001, 8501),
                    "sample_range": (4500, 8500)
                }

        Returns:
            Validation report with validity for each coordinate
        """
        validations = {}

        coord_map = {
            "inline": "inline_range",
            "crossline": "crossline_range",
            "sample": "sample_range"
        }

        for coord_type, claimed_value in claimed_location.items():
            range_key = coord_map.get(coord_type)

            if range_key and range_key in survey_bounds:
                min_val, max_val = survey_bounds[range_key]
                valid = min_val <= claimed_value <= max_val

                validation = {
                    "claimed": claimed_value,
                    "survey_range": [min_val, max_val],
                    "valid": valid
                }

                if not valid:
                    if claimed_value < min_val:
                        validation["issue"] = f"{coord_type} {claimed_value} is below survey minimum {min_val}"
                    else:
                        validation["issue"] = f"{coord_type} {claimed_value} is above survey maximum {max_val}"

                validations[coord_type] = validation
            else:
                validations[coord_type] = {
                    "claimed": claimed_value,
                    "valid": None,
                    "issue": f"No survey bounds available for {coord_type}"
                }

        # Overall verdict
        all_valid = all(
            v.get('valid', False) for v in validations.values()
        )

        return {
            "validations": validations,
            "verdict": "VALID" if all_valid else "OUT_OF_BOUNDS",
            "timestamp": datetime.now().isoformat()
        }

    def check_statistical_consistency(
        self,
        statistics: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Check if reported statistics are internally consistent

        Catches impossible combinations like mean > max, or percentiles out of order.

        Args:
            statistics: Dictionary of statistical values

        Returns:
            Consistency check results with list of violations
        """
        checks = []

        # Check 1: min ≤ mean ≤ max
        if all(k in statistics for k in ['min', 'mean', 'max']):
            if not (statistics['min'] <= statistics['mean'] <= statistics['max']):
                checks.append({
                    "rule": "min ≤ mean ≤ max",
                    "passed": False,
                    "issue": f"Mean ({statistics['mean']:.2f}) outside bounds [{statistics['min']:.2f}, {statistics['max']:.2f}]",
                    "severity": "high"
                })
            else:
                checks.append({
                    "rule": "min ≤ mean ≤ max",
                    "passed": True
                })

        # Check 2: min ≤ median ≤ max
        if all(k in statistics for k in ['min', 'median', 'max']):
            if not (statistics['min'] <= statistics['median'] <= statistics['max']):
                checks.append({
                    "rule": "min ≤ median ≤ max",
                    "passed": False,
                    "issue": f"Median ({statistics['median']:.2f}) outside bounds [{statistics['min']:.2f}, {statistics['max']:.2f}]",
                    "severity": "high"
                })
            else:
                checks.append({
                    "rule": "min ≤ median ≤ max",
                    "passed": True
                })

        # Check 3: p25 ≤ median ≤ p75
        if all(k in statistics for k in ['p25', 'median', 'p75']):
            if not (statistics['p25'] <= statistics['median'] <= statistics['p75']):
                checks.append({
                    "rule": "p25 ≤ median ≤ p75",
                    "passed": False,
                    "issue": f"Median ({statistics['median']:.2f}) outside interquartile range [{statistics['p25']:.2f}, {statistics['p75']:.2f}]",
                    "severity": "high"
                })
            else:
                checks.append({
                    "rule": "p25 ≤ median ≤ p75",
                    "passed": True
                })

        # Check 4: Percentiles are monotonically increasing
        percentile_keys = ['p10', 'p25', 'p50', 'p75', 'p90']
        available_percentiles = [k for k in percentile_keys if k in statistics]

        if len(available_percentiles) >= 2:
            percentile_values = [statistics[k] for k in available_percentiles]
            is_monotonic = all(percentile_values[i] <= percentile_values[i+1]
                              for i in range(len(percentile_values)-1))

            if not is_monotonic:
                checks.append({
                    "rule": "Percentiles monotonically increasing",
                    "passed": False,
                    "issue": f"Percentile order violation: {dict(zip(available_percentiles, percentile_values))}",
                    "severity": "high"
                })
            else:
                checks.append({
                    "rule": "Percentiles monotonically increasing",
                    "passed": True
                })

        # Check 5: Standard deviation ≥ 0
        if 'std' in statistics:
            if statistics['std'] < 0:
                checks.append({
                    "rule": "std ≥ 0",
                    "passed": False,
                    "issue": f"Standard deviation cannot be negative: {statistics['std']:.2f}",
                    "severity": "critical"
                })
            else:
                checks.append({
                    "rule": "std ≥ 0",
                    "passed": True
                })

        # Check 6: RMS ≥ |mean| (for seismic data, usually true)
        if all(k in statistics for k in ['rms', 'mean']):
            if statistics['rms'] < abs(statistics['mean']) * 0.9:  # Allow small tolerance
                checks.append({
                    "rule": "RMS ≥ |mean| (approximately)",
                    "passed": False,
                    "issue": f"RMS ({statistics['rms']:.2f}) unexpectedly smaller than |mean| ({abs(statistics['mean']):.2f})",
                    "severity": "medium"
                })
            else:
                checks.append({
                    "rule": "RMS ≥ |mean| (approximately)",
                    "passed": True
                })

        # Overall verdict
        all_consistent = all(c['passed'] for c in checks)
        failed_checks = [c for c in checks if not c['passed']]

        return {
            "all_consistent": all_consistent,
            "checks": checks,
            "failed_checks": failed_checks,
            "verdict": "CONSISTENT" if all_consistent else "INCONSISTENT",
            "severity": self._get_overall_severity(failed_checks),
            "timestamp": datetime.now().isoformat()
        }

    def _get_overall_severity(self, failed_checks: List[Dict]) -> str:
        """Determine overall severity from failed checks"""
        if not failed_checks:
            return "none"

        severities = [c.get('severity', 'medium') for c in failed_checks]

        if 'critical' in severities:
            return 'critical'
        elif 'high' in severities:
            return 'high'
        elif 'medium' in severities:
            return 'medium'
        else:
            return 'low'

    def create_provenance_record(
        self,
        data: np.ndarray,
        source_info: Dict[str, Any],
        extraction_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create provenance record for extracted data

        Args:
            data: Extracted data array
            source_info: Information about data source
                e.g., {"vds_file": "/path/to/file.vds", "survey_id": "Sepia"}
            extraction_params: Parameters used for extraction
                e.g., {"section_type": "inline", "section_number": 55000}

        Returns:
            Provenance record dictionary
        """
        # Compute data hash for verification
        data_hash = hashlib.sha256(data.tobytes()).hexdigest()

        provenance = {
            "extraction_timestamp": datetime.now().isoformat(),
            "source": source_info,
            "extraction_parameters": extraction_params,
            "data_fingerprint": {
                "hash": data_hash,
                "algorithm": "sha256",
                "shape": data.shape,
                "dtype": str(data.dtype)
            },
            "statistics": self._compute_statistics(data),
            "agent_version": "1.0.0",
            "verification_note": "All values computed directly from raw data"
        }

        return provenance


# Singleton instance
_integrity_agent: Optional[DataIntegrityAgent] = None


def get_integrity_agent(tolerance: float = 0.05) -> DataIntegrityAgent:
    """Get singleton integrity agent instance"""
    global _integrity_agent
    if _integrity_agent is None:
        _integrity_agent = DataIntegrityAgent(tolerance=tolerance)
    return _integrity_agent
