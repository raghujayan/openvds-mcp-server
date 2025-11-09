"""
Domain Warning System for Geophysically Meaningless Interpretations

Prevents LLM from making domain-incorrect statements that are statistically
accurate but geophysically nonsensical.

Core Principle: "Statistically correct ≠ Geophysically meaningful"

Example of what we prevent:
❌ "Sepia has 15-30x higher amplitudes than BS500"
   → Statistically true, geophysically meaningless
   → Raw amplitudes have no absolute units

✅ "After RMS normalization, Sepia shows similar amplitude variance to BS500"
   → Uses domain-appropriate comparison method
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass

logger = logging.getLogger("domain-warnings")


@dataclass
class DomainWarning:
    """A domain-specific warning about interpretation"""
    warning_type: str  # "cross_survey_amplitude", "missing_units", etc.
    severity: str  # "critical", "high", "medium", "low"
    message: str
    context: Dict[str, Any]
    recommendation: str


class DomainWarningSystem:
    """
    Detects and prevents geophysically meaningless interpretations
    """

    def __init__(self):
        logger.info("Domain Warning System initialized")

        # Patterns that indicate cross-survey comparisons
        self.cross_survey_patterns = [
            r'(?i)\b(compare|comparison|versus|vs\.?)\b.*\b(survey|surveys)\b',
            r'(?i)\b(higher|lower|greater|less|brighter|stronger)\b.*\bthan\b',
            r'(?i)\b(\w+)\s+(?:has|shows|displays)\s+(?:higher|lower|greater)\b',
        ]

        # Amplitude-related keywords that are dangerous in cross-survey context
        self.amplitude_keywords = [
            'amplitude', 'amplitudes', 'brightness', 'brighter', 'stronger',
            'max', 'maximum', 'min', 'minimum', 'mean', 'rms', 'value', 'values'
        ]

        # Safe comparison keywords (indicate normalization or proper metrics)
        self.safe_comparison_keywords = [
            'normalized', 'normalization', 'rms-normalized', 'z-score',
            'snr', 'signal-to-noise', 'frequency', 'bandwidth', 'continuity',
            'semblance', 'coherence', 'quality'
        ]

    def detect_cross_survey_comparison(
        self,
        context: str,
        survey_ids: Optional[Set[str]] = None
    ) -> Optional[DomainWarning]:
        """
        Detect if context contains cross-survey amplitude comparison.

        Args:
            context: Text to analyze (user prompt, LLM response, etc.)
            survey_ids: Optional set of survey IDs mentioned in context

        Returns:
            DomainWarning if unsafe comparison detected, None otherwise
        """
        context_lower = context.lower()

        # Check if multiple surveys mentioned
        if survey_ids and len(survey_ids) > 1:
            logger.info(f"Multiple surveys detected: {survey_ids}")

            # Check if amplitude-related comparison
            has_amplitude_keyword = any(
                keyword in context_lower
                for keyword in self.amplitude_keywords
            )

            # Check if comparison pattern exists
            has_comparison_pattern = any(
                re.search(pattern, context_lower)
                for pattern in self.cross_survey_patterns
            )

            # Check if safe comparison keywords present
            has_safe_keywords = any(
                keyword in context_lower
                for keyword in self.safe_comparison_keywords
            )

            if has_amplitude_keyword and has_comparison_pattern and not has_safe_keywords:
                return DomainWarning(
                    warning_type="cross_survey_amplitude_comparison",
                    severity="critical",
                    message=self._generate_amplitude_comparison_warning(survey_ids),
                    context={
                        "surveys": list(survey_ids),
                        "amplitude_keyword_found": has_amplitude_keyword,
                        "comparison_pattern_found": has_comparison_pattern,
                        "safe_keywords_found": has_safe_keywords
                    },
                    recommendation=self._get_safe_comparison_recommendation()
                )

        return None

    def check_units_in_response(
        self,
        response_data: Dict[str, Any]
    ) -> List[DomainWarning]:
        """
        Check if all quantities in response have units specified.

        Args:
            response_data: Dictionary containing response data with quantities

        Returns:
            List of warnings for quantities missing units
        """
        warnings = []

        # Check if statistics are present
        if "statistics" in response_data:
            stats = response_data["statistics"]

            # Quantities that MUST have units or "(unitless)" annotation
            quantities_to_check = [
                "min", "max", "mean", "median", "std", "rms",
                "p10", "p25", "p50", "p75", "p90"
            ]

            for quantity in quantities_to_check:
                if quantity in stats:
                    value = stats[quantity]
                    # Check if it's just a number without unit context
                    if isinstance(value, (int, float)):
                        warnings.append(DomainWarning(
                            warning_type="missing_units",
                            severity="medium",
                            message=f"Quantity '{quantity}' = {value} has no units specified",
                            context={"quantity": quantity, "value": value},
                            recommendation=(
                                f"Add units or specify as '(unitless)'. "
                                f"Seismic amplitudes are typically unitless relative values, "
                                f"but this MUST be stated explicitly."
                            )
                        ))

        # Check for frequency-related quantities (MUST have Hz)
        frequency_keys = ["dominant_frequency", "bandwidth", "frequency_range"]
        for key in frequency_keys:
            if key in response_data:
                value = response_data[key]
                if isinstance(value, (int, float)):
                    # Check if "hz" is mentioned nearby
                    if "hz" not in str(response_data.get(f"{key}_unit", "")).lower():
                        warnings.append(DomainWarning(
                            warning_type="missing_units",
                            severity="high",
                            message=f"Frequency quantity '{key}' = {value} must have units (Hz)",
                            context={"quantity": key, "value": value},
                            recommendation=f"Specify as '{value} Hz' for {key}"
                        ))

        return warnings

    def validate_comparison_context(
        self,
        comparison_data: Dict[str, Any]
    ) -> Optional[DomainWarning]:
        """
        Validate that a comparison has proper domain context.

        Args:
            comparison_data: Dictionary with comparison information

        Returns:
            Warning if comparison lacks proper context
        """
        required_context = ["normalization_method", "metric_type", "units"]

        missing_context = [
            ctx for ctx in required_context
            if ctx not in comparison_data
        ]

        if missing_context:
            return DomainWarning(
                warning_type="incomplete_comparison_context",
                severity="high",
                message=f"Comparison missing required context: {missing_context}",
                context={"missing": missing_context},
                recommendation=(
                    "Cross-survey comparisons MUST include:\n"
                    "1. Normalization method (RMS, z-score, etc.)\n"
                    "2. Metric type (SNR, frequency, continuity, NOT raw amplitude)\n"
                    "3. Units for all quantities (or explicit '(unitless)' notation)"
                )
            )

        return None

    def _generate_amplitude_comparison_warning(
        self,
        survey_ids: Set[str]
    ) -> str:
        """Generate detailed warning for cross-survey amplitude comparison"""
        surveys_str = ", ".join(sorted(survey_ids))

        return f"""
⚠️ GEOPHYSICAL INTERPRETATION WARNING ⚠️

Cross-survey amplitude comparison detected for: {surveys_str}

CRITICAL ISSUE:
Raw seismic amplitude values have NO absolute physical units and are
NOT comparable between different surveys.

WHY THIS IS PROBLEMATIC:
• Different acquisition equipment → different gain settings
• Different processing workflows → different scaling factors
• Arbitrary normalization → no physical meaning
• Values are RELATIVE within each survey, not ABSOLUTE across surveys

ANALOGY:
Comparing raw amplitudes between surveys is like comparing thermometer
readings where one is in Celsius and another is in an arbitrary scale
invented during processing.

WHAT YOU CAN SAY (SAFE):
✓ "Within Sepia survey: inline 55000 shows 2x higher amplitude than inline 54000"
✓ "Sepia has SNR of 18.5 dB, BS500 has SNR of 24.3 dB (SNR is comparable)"
✓ "After RMS normalization: Sepia shows similar amplitude variance to BS500"
✓ "Sepia bandwidth: 45 Hz, BS500 bandwidth: 52 Hz (frequency is comparable)"

WHAT YOU CANNOT SAY (UNSAFE):
✗ "Sepia has higher amplitudes than BS500" (no normalization)
✗ "Sepia is brighter than BS500" (meaningless without normalization)
✗ "Max amplitude 2487 vs 164" (raw values, different surveys)
✗ "Sepia shows 15-30x higher amplitudes" (geophysically nonsensical)

TO MAKE A VALID COMPARISON:
1. Use domain-appropriate metrics (SNR, frequency, continuity - NOT amplitude)
2. If comparing amplitudes, MUST normalize first (RMS, z-score)
3. Always specify units or explicitly state "(unitless)"
4. Focus on quality metrics, not raw values

Use 'get_normalized_amplitude_statistics' or 'compare_survey_quality_metrics'
for valid cross-survey comparisons.
"""

    def _get_safe_comparison_recommendation(self) -> str:
        """Get recommendation for safe cross-survey comparison"""
        return """
RECOMMENDED APPROACH FOR CROSS-SURVEY COMPARISON:

1. Quality Metrics (SAFE - use these):
   • SNR (signal-to-noise ratio in dB)
   • Frequency content (dominant frequency in Hz, bandwidth in Hz)
   • Reflector continuity (semblance, 0-1 unitless)
   • Data completeness (percentage)

2. Normalized Amplitudes (SAFE - if normalization stated):
   • RMS-normalized: divide by survey RMS (unitless)
   • Z-score normalized: (value - mean) / std (unitless)
   • Percentile-normalized: scale to [0, 1] (unitless)

3. Relative Patterns (SAFE - within survey only):
   • Amplitude contrasts relative to background
   • Spatial variation patterns
   • Anomaly detection with statistical thresholds

4. Tools to Use:
   • compare_survey_quality_metrics() - domain-appropriate comparison
   • get_normalized_amplitude_statistics() - safe amplitude comparison
   • comprehensive_qc_analysis() - full quality assessment

ALWAYS include units or explicit "(unitless)" annotation!
"""

    def extract_survey_ids_from_context(
        self,
        context: str,
        known_surveys: List[str]
    ) -> Set[str]:
        """
        Extract survey IDs mentioned in context.

        Args:
            context: Text to analyze
            known_surveys: List of known survey IDs

        Returns:
            Set of survey IDs found in context
        """
        found_surveys = set()

        context_lower = context.lower()

        for survey_id in known_surveys:
            # Check if survey ID mentioned (case-insensitive)
            if survey_id.lower() in context_lower:
                found_surveys.add(survey_id)

        return found_surveys


# Singleton instance
_warning_system: Optional[DomainWarningSystem] = None


def get_warning_system() -> DomainWarningSystem:
    """Get singleton warning system instance"""
    global _warning_system
    if _warning_system is None:
        _warning_system = DomainWarningSystem()
    return _warning_system


def check_response_for_domain_issues(
    response: Dict[str, Any],
    context: str,
    known_surveys: List[str]
) -> List[DomainWarning]:
    """
    Convenience function to check response for all domain issues.

    Args:
        response: Response data to check
        context: Original context/prompt
        known_surveys: List of known survey IDs

    Returns:
        List of all domain warnings detected
    """
    system = get_warning_system()
    warnings = []

    # Check for cross-survey amplitude comparisons
    survey_ids = system.extract_survey_ids_from_context(context, known_surveys)
    cross_survey_warning = system.detect_cross_survey_comparison(context, survey_ids)
    if cross_survey_warning:
        warnings.append(cross_survey_warning)

    # Check for missing units
    unit_warnings = system.check_units_in_response(response)
    warnings.extend(unit_warnings)

    return warnings


def format_warning_for_display(warning: DomainWarning) -> str:
    """
    Format warning for display to user/LLM.

    Args:
        warning: DomainWarning to format

    Returns:
        Formatted warning message
    """
    severity_emojis = {
        "critical": "🚨",
        "high": "⚠️",
        "medium": "⚡",
        "low": "ℹ️"
    }

    emoji = severity_emojis.get(warning.severity, "⚠️")

    return f"""
{emoji} DOMAIN WARNING [{warning.severity.upper()}]: {warning.warning_type}

{warning.message}

RECOMMENDATION:
{warning.recommendation}
"""
