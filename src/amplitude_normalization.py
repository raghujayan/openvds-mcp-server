"""
Amplitude Normalization for Geophysically Meaningful Cross-Survey Comparisons

Provides normalization methods that make amplitude values comparable across
different surveys with different acquisition and processing.

Core Principle: "Raw amplitudes are meaningless across surveys, normalized are comparable"

Example:
❌ "Sepia max 2487 vs BS500 max 164" - meaningless (different scaling)
✅ "Sepia RMS-normalized variance 1.2 vs BS500 1.1" - comparable (same scale)

All methods return values with explicit units:
- RMS-normalized: (unitless, scaled by RMS)
- Z-score: (unitless, number of standard deviations from mean)
- Percentile-normalized: (unitless, 0-1 range)
- Contrast ratios: (unitless ratio)
"""

import numpy as np
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("amplitude-normalization")


@dataclass
class NormalizationResult:
    """Result of amplitude normalization"""
    method: str  # "rms", "zscore", "percentile"
    normalized_data: np.ndarray
    statistics: Dict[str, Any]
    units: str  # Description of units for normalized values


class AmplitudeNormalizer:
    """
    Provides geophysically sound amplitude normalization methods.

    All methods preserve relative patterns while making values comparable
    across different surveys.
    """

    def __init__(self):
        logger.info("Amplitude Normalizer initialized")

    def normalize_by_rms(
        self,
        data: np.ndarray,
        return_stats: bool = True
    ) -> NormalizationResult:
        """
        RMS (Root Mean Square) normalization - INDUSTRY STANDARD for cross-survey comparison.

        Divides all values by the RMS of the dataset. This removes the arbitrary
        scaling factor while preserving relative amplitude patterns.

        Normalized values typically range from -3 to +3 (in units of RMS).

        Args:
            data: Raw amplitude data (unitless, arbitrary scaling)
            return_stats: Whether to return detailed statistics

        Returns:
            NormalizationResult with:
            - normalized_data: values in units of RMS (unitless, RMS-scaled)
            - statistics: original RMS, mean, etc. with units
            - units: "unitless (RMS-normalized)"

        Example:
            Raw data: [-1247.3, 2487.3, 12.4, ...]
            RMS: 487.2
            Normalized: [-2.56, 5.10, 0.025, ...] (units: RMS-normalized unitless)
        """
        # Compute RMS
        rms = np.sqrt(np.mean(data**2))

        if rms == 0:
            logger.warning("RMS is zero, cannot normalize. Returning zeros.")
            normalized = np.zeros_like(data)
            rms = 1.0  # Avoid division by zero in stats
        else:
            # Normalize: divide by RMS
            normalized = data / rms

        stats = {
            "method": "RMS normalization",
            "original_rms": float(rms),
            "original_rms_units": "unitless (arbitrary from acquisition/processing)",
            "normalization_factor": float(rms),
            "normalization_factor_units": "unitless (RMS value used for scaling)",
            "normalized_range": {
                "min": float(np.min(normalized)),
                "max": float(np.max(normalized)),
                "units": "unitless (RMS-normalized, typically -3 to +3)"
            },
            "normalized_statistics": {
                "min": float(np.min(normalized)),
                "max": float(np.max(normalized)),
                "mean": float(np.mean(normalized)),
                "std": float(np.std(normalized)),
                "rms": 1.0,  # RMS of RMS-normalized data is always 1.0
                "units": "unitless (RMS-normalized)"
            },
            "interpretation": (
                "Values represent amplitude in units of RMS. "
                "Typical range -3 to +3. Values >3 are strong anomalies. "
                "This normalization is COMPARABLE across surveys with different acquisition/processing."
            )
        }

        return NormalizationResult(
            method="rms",
            normalized_data=normalized,
            statistics=stats,
            units="unitless (RMS-normalized)"
        )

    def normalize_by_zscore(
        self,
        data: np.ndarray,
        return_stats: bool = True
    ) -> NormalizationResult:
        """
        Z-score normalization (standardization) - statistical standard.

        Transforms data to have mean=0 and std=1 by: (value - mean) / std
        Values represent number of standard deviations from mean.

        Useful for detecting anomalies and comparing distributions.

        Args:
            data: Raw amplitude data (unitless, arbitrary scaling)
            return_stats: Whether to return detailed statistics

        Returns:
            NormalizationResult with:
            - normalized_data: z-scores (unitless, std deviations from mean)
            - statistics: original mean, std with units
            - units: "unitless (z-score: standard deviations from mean)"

        Example:
            Raw data: [-1247.3, 2487.3, 12.4, ...]
            Mean: 12.4, Std: 487.2
            Normalized: [-2.59, 5.08, 0.0, ...] (units: standard deviations from mean)
        """
        mean = np.mean(data)
        std = np.std(data)

        if std == 0:
            logger.warning("Standard deviation is zero, cannot z-score normalize. Returning zeros.")
            normalized = np.zeros_like(data)
            std = 1.0  # Avoid division by zero in stats
        else:
            # Z-score: (value - mean) / std
            normalized = (data - mean) / std

        stats = {
            "method": "Z-score normalization (standardization)",
            "original_mean": float(mean),
            "original_mean_units": "unitless (arbitrary from acquisition/processing)",
            "original_std": float(std),
            "original_std_units": "unitless (arbitrary from acquisition/processing)",
            "normalized_statistics": {
                "mean": 0.0,  # Z-score always has mean 0
                "std": 1.0,   # Z-score always has std 1
                "min": float(np.min(normalized)),
                "max": float(np.max(normalized)),
                "units": "unitless (z-score: standard deviations from mean)"
            },
            "interpretation": (
                "Values represent number of standard deviations from mean. "
                "0 = mean, ±1 = one std dev, ±2 = two std devs, etc. "
                "Values >3 or <-3 are strong anomalies (>99.7% of data within ±3). "
                "This normalization is COMPARABLE across surveys."
            )
        }

        return NormalizationResult(
            method="zscore",
            normalized_data=normalized,
            statistics=stats,
            units="unitless (z-score: standard deviations from mean)"
        )

    def normalize_by_percentile(
        self,
        data: np.ndarray,
        clip_percentile: float = 99.0,
        return_stats: bool = True
    ) -> NormalizationResult:
        """
        Percentile normalization - clips outliers and scales to [0, 1].

        Clips data to percentile range (e.g., 1st to 99th percentile) then
        scales linearly to [0, 1] range. Robust to extreme outliers.

        Args:
            data: Raw amplitude data (unitless, arbitrary scaling)
            clip_percentile: Percentile to clip at (default 99.0)
            return_stats: Whether to return detailed statistics

        Returns:
            NormalizationResult with:
            - normalized_data: values in [0, 1] range (unitless, percentile-normalized)
            - statistics: clipping thresholds with units
            - units: "unitless (percentile-normalized, 0-1 range)"

        Example:
            Raw data: [-1247.3, 2487.3, 12.4, ...]
            1st percentile: -1100, 99th percentile: 2200
            Normalized: [0.044, 1.0, 0.34, ...] (units: 0-1 range)
        """
        # Compute clipping thresholds
        lower_percentile = 100 - clip_percentile
        p_low = np.percentile(data, lower_percentile)
        p_high = np.percentile(data, clip_percentile)

        # Clip data
        clipped = np.clip(data, p_low, p_high)

        # Scale to [0, 1]
        data_range = p_high - p_low
        if data_range == 0:
            logger.warning("Percentile range is zero, cannot normalize. Returning 0.5 for all values.")
            normalized = np.full_like(data, 0.5, dtype=float)
        else:
            normalized = (clipped - p_low) / data_range

        stats = {
            "method": f"Percentile normalization (clip at {clip_percentile}%)",
            "clipping_thresholds": {
                "lower": float(p_low),
                "upper": float(p_high),
                "lower_percentile": lower_percentile,
                "upper_percentile": clip_percentile,
                "units": "unitless (original data units before clipping)"
            },
            "normalized_statistics": {
                "min": 0.0,  # Always 0 after normalization
                "max": 1.0,  # Always 1 after normalization
                "mean": float(np.mean(normalized)),
                "median": float(np.median(normalized)),
                "units": "unitless (percentile-normalized, 0-1 range)"
            },
            "interpretation": (
                f"Values clipped to {lower_percentile}th - {clip_percentile}th percentile range, "
                f"then scaled to [0, 1]. 0 = {lower_percentile}th percentile, 1 = {clip_percentile}th percentile. "
                "Robust to extreme outliers. This normalization is COMPARABLE across surveys."
            )
        }

        return NormalizationResult(
            method="percentile",
            normalized_data=normalized,
            statistics=stats,
            units="unitless (percentile-normalized, 0-1 range)"
        )

    def compute_relative_contrast(
        self,
        data: np.ndarray,
        reference: str = "median",
        threshold_sigma: float = 3.0
    ) -> Dict[str, Any]:
        """
        Compute relative amplitude contrast (anomaly detection).

        Identifies values that stand out from background using statistical thresholds.
        Returns contrast ratios and anomaly counts.

        Args:
            data: Raw amplitude data (unitless)
            reference: Reference level - "median" or "mean"
            threshold_sigma: Number of standard deviations for anomaly threshold

        Returns:
            Dictionary with:
            - background_level: median or mean (unitless)
            - threshold: statistical threshold (unitless)
            - anomaly_count: number of values exceeding threshold
            - contrast_ratios: ratios of anomalies to background (unitless ratios)
            - statistics: all with proper units

        Example:
            Background (median): 8.7 (unitless)
            Threshold (mean + 3σ): 1474.4 (unitless)
            Contrast ratio: 169x above background (unitless ratio)
        """
        # Choose reference level
        if reference == "median":
            ref_level = np.median(np.abs(data))
            ref_name = "median absolute amplitude"
        elif reference == "mean":
            ref_level = np.mean(np.abs(data))
            ref_name = "mean absolute amplitude"
        else:
            raise ValueError(f"Unknown reference: {reference}. Use 'median' or 'mean'")

        # Compute threshold
        mean = np.mean(data)
        std = np.std(data)
        threshold = mean + threshold_sigma * std

        # Find anomalies
        anomalies = data > threshold
        anomaly_count = np.sum(anomalies)
        anomaly_values = data[anomalies]

        # Compute contrast ratios
        if len(anomaly_values) > 0 and ref_level != 0:
            contrast_ratios = anomaly_values / ref_level
        else:
            contrast_ratios = np.array([])

        result = {
            "method": "Relative contrast analysis",
            "reference_level": {
                "value": float(ref_level),
                "type": ref_name,
                "units": "unitless (arbitrary from acquisition/processing)"
            },
            "threshold": {
                "value": float(threshold),
                "method": f"mean + {threshold_sigma}σ",
                "mean": float(mean),
                "std": float(std),
                "sigma_multiplier": threshold_sigma,
                "units": "unitless (arbitrary from acquisition/processing)"
            },
            "anomalies": {
                "count": int(anomaly_count),
                "percentage": float(anomaly_count / len(data) * 100),
                "percentage_units": "%"
            },
            "contrast_ratios": {
                "values": contrast_ratios.tolist() if len(contrast_ratios) > 0 else [],
                "min": float(np.min(contrast_ratios)) if len(contrast_ratios) > 0 else None,
                "max": float(np.max(contrast_ratios)) if len(contrast_ratios) > 0 else None,
                "mean": float(np.mean(contrast_ratios)) if len(contrast_ratios) > 0 else None,
                "units": "unitless (ratio to background)",
                "interpretation": (
                    f"Anomaly amplitudes are X times background {ref_name}. "
                    f"E.g., contrast ratio 2.5 means amplitude is 2.5x the background."
                )
            },
            "interpretation": (
                f"Found {anomaly_count} anomalies ({anomaly_count / len(data) * 100:.1f}%) "
                f"exceeding threshold of {threshold:.1f} (mean + {threshold_sigma}σ). "
                f"Contrast ratios show how many times brighter than background {ref_name}."
            )
        }

        return result


# Singleton instance
_normalizer: Optional[AmplitudeNormalizer] = None


def get_normalizer() -> AmplitudeNormalizer:
    """Get singleton normalizer instance"""
    global _normalizer
    if _normalizer is None:
        _normalizer = AmplitudeNormalizer()
    return _normalizer


def normalize_for_comparison(
    data1: np.ndarray,
    data2: np.ndarray,
    method: str = "rms",
    **kwargs
) -> Tuple[NormalizationResult, NormalizationResult]:
    """
    Convenience function to normalize two datasets for comparison.

    Args:
        data1: First dataset (unitless, arbitrary scaling)
        data2: Second dataset (unitless, arbitrary scaling)
        method: "rms", "zscore", or "percentile"
        **kwargs: Additional arguments for normalization method

    Returns:
        Tuple of (result1, result2) with normalized data and statistics

    Example:
        result1, result2 = normalize_for_comparison(sepia_data, bs500_data, method="rms")
        # Now result1 and result2 are comparable!
        print(f"Sepia RMS-normalized variance: {np.var(result1.normalized_data):.2f}")
        print(f"BS500 RMS-normalized variance: {np.var(result2.normalized_data):.2f}")
    """
    normalizer = get_normalizer()

    if method == "rms":
        result1 = normalizer.normalize_by_rms(data1, **kwargs)
        result2 = normalizer.normalize_by_rms(data2, **kwargs)
    elif method == "zscore":
        result1 = normalizer.normalize_by_zscore(data1, **kwargs)
        result2 = normalizer.normalize_by_zscore(data2, **kwargs)
    elif method == "percentile":
        result1 = normalizer.normalize_by_percentile(data1, **kwargs)
        result2 = normalizer.normalize_by_percentile(data2, **kwargs)
    else:
        raise ValueError(f"Unknown normalization method: {method}")

    logger.info(f"Normalized two datasets using {method} method - now comparable!")

    return result1, result2
