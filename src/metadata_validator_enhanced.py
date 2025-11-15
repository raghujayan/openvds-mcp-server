"""
Enhanced VDS Metadata Validator v2.0
Anti-hallucination tool with intelligent field matching and WKT parsing

Enhancements over v1:
- Multi-location field search with aliases
- WKT (Well-Known Text) parser for CRS data
- Semantic value matching with fuzzy comparison
- Enhanced response format with confidence scoring
- Discovery mode for metadata exploration
- Batch validation with overall scoring

Phase 1: Core Improvements ✅
Phase 2: Smart Matching ✅
Phase 3: Discovery Mode ✅
"""

import re
import struct
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher
import openvds
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration: Field Aliases & Search Paths
# ============================================================================

FIELD_ALIASES = {
    "epsg_code": ["epsg", "EPSG", "epsg_code", "srs_code", "crs_code"],
    "sample_unit": ["sample_unit", "sampleUnit", "time_unit", "sample_rate_unit", "unit"],
    "datum": ["datum", "geodetic_datum", "horizontal_datum", "datum_name"],
    "utm_zone": ["utm_zone", "zone", "utm_zone_number", "zone_number"],
    "projection": ["projection", "projection_name", "crs_name", "coordinate_system"],
    "hemisphere": ["hemisphere", "utm_hemisphere", "ns"],
    "spheroid": ["spheroid", "ellipsoid", "reference_ellipsoid"],
}

SEARCH_PATHS = {
    "sample_unit": [
        "sample_unit",
        "import_info.sample_unit",
        "dimensions.Sample.unit",
        "metadata.sample_unit"
    ],
    "epsg_code": [
        "epsg",
        "crs_info.epsg",
        "crs.epsg_code",
        "crs_info.geoLocation.source_crs",
        "crs_info.crsWkt"  # Will parse from WKT
    ],
    "datum": [
        "datum",
        "crs_info.datum",
        "crs.datum",
        "crs_info.crsWkt"  # Will parse from WKT
    ],
    "projection": [
        "projection",
        "projection_name",
        "crs_name",
        "crs_info.crsWkt"  # Will parse from WKT
    ]
}

UNIT_EQUIVALENTS = {
    "ms": ["ms", "milliseconds", "millisecond", "msec", "Milliseconds"],
    "m": ["m", "meters", "metres", "meter", "metre", "Meters", "Metres"],
    "ft": ["ft", "feet", "foot", "Feet", "Foot"],
    "s": ["s", "seconds", "second", "sec", "Seconds"],
    "us": ["us", "microseconds", "microsecond", "usec", "Microseconds"]
}

FIELD_WEIGHTS = {
    "dimensions": 1.0,     # Critical - must be exact
    "epsg_code": 0.9,      # Important
    "datum": 0.8,          # Important
    "sample_unit": 0.7,    # Useful
    "projection": 0.7,     # Useful
    "data_type": 0.5       # Nice to have
}


class EnhancedMetadataValidator:
    """Enhanced validator with intelligent field matching and WKT parsing"""

    def __init__(self, handle, layout, smart_matching=True, parse_wkt=True):
        """
        Args:
            handle: OpenVDS handle
            layout: OpenVDS layout object
            smart_matching: Enable intelligent field matching
            parse_wkt: Enable WKT parsing for CRS data
        """
        self.handle = handle
        self.layout = layout
        self.smart_matching = smart_matching
        self.parse_wkt = parse_wkt

        # Cache for parsed WKT and metadata
        self._wkt_cache = {}
        self._metadata_cache = {}

    # ========================================================================
    # WKT (Well-Known Text) Parser
    # ========================================================================

    def parse_wkt(self, wkt_string: str) -> Dict[str, Any]:
        """
        Parse WKT (Well-Known Text) CRS string into structured data

        Example WKT:
        PROJCS["ED50 / UTM zone 31N",
            GEOGCS["ED50",
                DATUM["European_Datum_1950",
                    SPHEROID["International 1924",6378388,297]],
            AUTHORITY["EPSG","23031"]]

        Returns:
            {
                "projection_name": "ED50 / UTM zone 31N",
                "datum": "European_Datum_1950",
                "spheroid": "International 1924",
                "epsg_code": 23031,
                "utm_zone": 31,
                "hemisphere": "N",
                "unit": "metre"
            }
        """
        if not wkt_string:
            return {}

        # Check cache first
        if wkt_string in self._wkt_cache:
            return self._wkt_cache[wkt_string]

        result = {}

        try:
            # Extract projection name (PROJCS["name", ...])
            projcs_match = re.search(r'PROJCS\["([^"]+)"', wkt_string)
            if projcs_match:
                result["projection_name"] = projcs_match.group(1)

                # Extract UTM zone and hemisphere from projection name
                utm_match = re.search(r'UTM[_ ]zone[_ ](\d+)([NS])', result["projection_name"], re.IGNORECASE)
                if utm_match:
                    result["utm_zone"] = int(utm_match.group(1))
                    result["hemisphere"] = utm_match.group(2).upper()

            # Extract datum name (DATUM["name", ...])
            datum_match = re.search(r'DATUM\["([^"]+)"', wkt_string)
            if datum_match:
                result["datum"] = datum_match.group(1)

            # Extract spheroid/ellipsoid (SPHEROID["name", ...])
            spheroid_match = re.search(r'SPHEROID\["([^"]+)"', wkt_string)
            if spheroid_match:
                result["spheroid"] = spheroid_match.group(1)

            # Extract EPSG code (AUTHORITY["EPSG","code"])
            epsg_match = re.search(r'AUTHORITY\["EPSG","(\d+)"\]', wkt_string)
            if epsg_match:
                result["epsg_code"] = int(epsg_match.group(1))

            # Extract unit (UNIT["name", conversion_factor])
            unit_match = re.search(r'UNIT\["([^"]+)"', wkt_string)
            if unit_match:
                result["unit"] = unit_match.group(1)

        except Exception as e:
            logger.warning(f"Failed to parse WKT: {e}")

        # Cache result
        self._wkt_cache[wkt_string] = result
        return result

    # ========================================================================
    # Smart Field Discovery
    # ========================================================================

    def find_field_value(self, field_name: str, metadata: Dict[str, Any]) -> Optional[Tuple[Any, str]]:
        """
        Intelligently search for field value in metadata using multiple strategies

        Args:
            field_name: Field to search for
            metadata: Metadata dictionary to search in

        Returns:
            (value, source_path) tuple if found, None otherwise
            source_path indicates where the value was found
        """
        # Strategy 1: Try direct match
        if field_name in metadata:
            return metadata[field_name], field_name

        # Strategy 2: Try all aliases
        if field_name in FIELD_ALIASES:
            for alias in FIELD_ALIASES[field_name]:
                if alias in metadata:
                    return metadata[alias], f"{alias} (alias of {field_name})"

        # Strategy 3: Try predefined search paths
        if field_name in SEARCH_PATHS:
            for path in SEARCH_PATHS[field_name]:
                value = self._get_nested_value(metadata, path)
                if value is not None:
                    # Special handling for WKT fields
                    if path.endswith("crsWkt") and self.parse_wkt:
                        parsed = self.parse_wkt(str(value))
                        if field_name in parsed:
                            return parsed[field_name], f"{path} (parsed from WKT)"
                    else:
                        return value, path

        # Strategy 4: Case-insensitive fuzzy search
        if self.smart_matching:
            for key in metadata.keys():
                if isinstance(key, str) and key.lower() == field_name.lower():
                    return metadata[key], f"{key} (case-insensitive match)"

        return None

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Optional[Any]:
        """
        Get value from nested dictionary using dot-notation path

        Example: "crs_info.geoLocation.lat" -> data["crs_info"]["geoLocation"]["lat"]
        """
        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    # ========================================================================
    # Semantic Value Matching
    # ========================================================================

    def values_match(self, claimed: Any, actual: Any, field_name: str = "", tolerance: float = 0.05) -> Tuple[bool, float, str]:
        """
        Check if two values match with semantic understanding

        Returns:
            (matches, confidence, match_type) tuple
            - matches: True if values are semantically equivalent
            - confidence: 0.0-1.0 score
            - match_type: Description of match type
        """
        # Exact match
        if claimed == actual:
            return True, 1.0, "exact"

        # None/null handling
        if claimed is None or actual is None:
            return False, 1.0, "one_is_none"

        # Numeric matching with tolerance
        if isinstance(claimed, (int, float)) and isinstance(actual, (int, float)):
            diff = abs(claimed - actual)
            max_diff = abs(actual) * tolerance if actual != 0 else tolerance
            if diff <= max_diff:
                confidence = 1.0 - (diff / max_diff) if max_diff > 0 else 1.0
                return True, confidence, "numeric_tolerance"

        # String matching
        if isinstance(claimed, str) and isinstance(actual, str):
            # Unit equivalence
            if self._are_units_equivalent(claimed, actual):
                return True, 1.0, "unit_equivalent"

            # Case-insensitive exact match
            if claimed.lower() == actual.lower():
                return True, 1.0, "case_insensitive"

            # Fuzzy string matching
            if self.smart_matching:
                similarity = SequenceMatcher(None, claimed.lower(), actual.lower()).ratio()
                if similarity > 0.85:
                    return True, similarity, "fuzzy_match"
                elif similarity > 0.7:
                    return True, similarity, "partial_match"

        return False, 0.0, "no_match"

    def _are_units_equivalent(self, unit1: str, unit2: str) -> bool:
        """Check if two unit strings are equivalent"""
        unit1_clean = unit1.strip().lower()
        unit2_clean = unit2.strip().lower()

        for canonical, variants in UNIT_EQUIVALENTS.items():
            variants_lower = [v.lower() for v in variants]
            if unit1_clean in variants_lower and unit2_clean in variants_lower:
                return True

        return False

    # ========================================================================
    # Enhanced Validation Methods
    # ========================================================================

    def validate_field_claim(
        self,
        field_name: str,
        claimed_value: Any,
        metadata: Dict[str, Any],
        tolerance: float = 0.05
    ) -> Dict[str, Any]:
        """
        Validate a single field claim with enhanced response format

        Returns:
            {
                "status": "PASS" | "FAIL" | "PARTIAL" | "NOT_FOUND",
                "field": field_name,
                "claimed": claimed_value,
                "actual": actual_value or None,
                "source": "path where value was found",
                "confidence": 0.0-1.0,
                "match_type": "exact" | "fuzzy_match" | etc,
                "message": "Human-readable description",
                "suggestions": ["suggestion1", ...],  # Only if FAIL/NOT_FOUND
                "alternatives": {key: value, ...}     # Related fields found
            }
        """
        result = {
            "field": field_name,
            "claimed": claimed_value,
            "suggestions": [],
            "alternatives": {}
        }

        # Try to find the field value
        found = self.find_field_value(field_name, metadata)

        if found is None:
            # Field not found anywhere
            result["status"] = "NOT_FOUND"
            result["actual"] = None
            result["source"] = None
            result["confidence"] = 1.0
            result["match_type"] = "not_found"
            result["message"] = f"Field '{field_name}' not found in VDS metadata"

            # Provide suggestions
            result["suggestions"] = self._get_field_suggestions(field_name, metadata)
            result["alternatives"] = self._get_similar_fields(field_name, metadata)

            return result

        actual_value, source_path = found
        result["actual"] = actual_value
        result["source"] = source_path

        # Check if values match
        matches, confidence, match_type = self.values_match(claimed_value, actual_value, field_name, tolerance)

        result["confidence"] = confidence
        result["match_type"] = match_type

        if matches:
            if confidence == 1.0:
                result["status"] = "PASS"
                result["message"] = f"Exact match found at {source_path}"
            else:
                result["status"] = "PARTIAL"
                result["message"] = f"Partial match found at {source_path} (confidence: {confidence:.2f})"
        else:
            result["status"] = "FAIL"
            result["message"] = f"Value mismatch: claimed '{claimed_value}' but actual is '{actual_value}' at {source_path}"
            result["suggestions"] = [f"Did you mean '{actual_value}' instead of '{claimed_value}'?"]

        return result

    def _get_field_suggestions(self, field_name: str, metadata: Dict[str, Any]) -> List[str]:
        """Generate helpful suggestions when field not found"""
        suggestions = []

        # Suggest aliases if they exist
        if field_name in FIELD_ALIASES:
            existing_aliases = [alias for alias in FIELD_ALIASES[field_name] if alias in metadata]
            if existing_aliases:
                suggestions.append(f"Found similar field '{existing_aliases[0]}' at root level")

        # Suggest similar field names
        for key in metadata.keys():
            if isinstance(key, str):
                similarity = SequenceMatcher(None, field_name.lower(), key.lower()).ratio()
                if similarity > 0.6:
                    suggestions.append(f"Did you mean '{key}'? (similarity: {similarity:.0%})")

        return suggestions[:3]  # Limit to top 3 suggestions

    def _get_similar_fields(self, field_name: str, metadata: Dict[str, Any], max_results: int = 3) -> Dict[str, Any]:
        """Find related fields in metadata"""
        related = {}

        # Look for fields with similar names
        for key, value in metadata.items():
            if isinstance(key, str):
                # Check if key contains any word from field_name
                field_words = set(field_name.lower().split('_'))
                key_words = set(key.lower().split('_'))

                if field_words & key_words:  # If there's any overlap
                    related[key] = value
                    if len(related) >= max_results:
                        break

        return related

    # ========================================================================
    # Discovery Mode
    # ========================================================================

    def discover_metadata(self, category: str = "all") -> Dict[str, Any]:
        """
        Explore available metadata without validation

        Args:
            category: "crs", "dimensions", "import_info", or "all"

        Returns:
            {
                "mode": "discovery",
                "category": category,
                "available_fields": {...},
                "suggested_claims": {...}
            }
        """
        result = {
            "mode": "discovery",
            "category": category,
            "available_fields": {},
            "suggested_claims": {}
        }

        # Get all metadata
        all_metadata = self._get_all_metadata()

        if category == "crs" or category == "all":
            crs_data = self._discover_crs_metadata(all_metadata)
            result["available_fields"]["crs"] = crs_data["fields"]
            result["suggested_claims"]["crs"] = crs_data["suggested"]

        if category == "dimensions" or category == "all":
            dims_data = self._discover_dimension_metadata()
            result["available_fields"]["dimensions"] = dims_data["fields"]
            result["suggested_claims"]["dimensions"] = dims_data["suggested"]

        if category == "import_info" or category == "all":
            import_data = self._discover_import_metadata(all_metadata)
            result["available_fields"]["import_info"] = import_data["fields"]
            result["suggested_claims"]["import_info"] = import_data["suggested"]

        return result

    def _get_all_metadata(self) -> Dict[str, Any]:
        """Extract all available metadata from VDS file"""
        if self._metadata_cache:
            return self._metadata_cache

        metadata = {}

        try:
            # Get all metadata keys
            keys = self.layout.getMetadataKeys()

            for category, name in keys:
                key = f"{category}.{name}" if category else name

                # Try different types
                try:
                    if self.layout.isMetadataIntAvailable(category, name):
                        metadata[key] = self.layout.getMetadataInt(category, name)
                    elif self.layout.isMetadataFloatAvailable(category, name):
                        metadata[key] = self.layout.getMetadataFloat(category, name)
                    elif self.layout.isMetadataStringAvailable(category, name):
                        metadata[key] = self.layout.getMetadataString(category, name)
                    elif self.layout.isMetadataBLOBAvailable(category, name):
                        metadata[key] = "<binary_data>"
                except Exception as e:
                    logger.warning(f"Failed to read metadata {key}: {e}")

        except Exception as e:
            logger.error(f"Failed to enumerate metadata: {e}")

        self._metadata_cache = metadata
        return metadata

    def _discover_crs_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Discover CRS-related metadata"""
        crs_fields = {}
        suggested = {}

        # Look for CRS-related keys
        crs_keys = [k for k in metadata.keys() if "crs" in k.lower() or "geo" in k.lower()]

        for key in crs_keys:
            value = metadata[key]
            crs_fields[key] = {"value": value}

            # If it's WKT, parse it
            if isinstance(value, str) and "PROJCS" in value and self.parse_wkt:
                parsed = self.parse_wkt(value)
                crs_fields[key]["parsed"] = parsed
                suggested.update(parsed)

        return {"fields": crs_fields, "suggested": suggested}

    def _discover_dimension_metadata(self) -> Dict[str, Any]:
        """Discover dimension metadata"""
        dims_fields = {}
        suggested = {}

        try:
            for dim in range(self.layout.getDimensionality()):
                axis = self.layout.getAxisDescriptor(dim)
                dim_name = axis.getName()

                dims_fields[dim_name] = {
                    "min": axis.getCoordinateMin(),
                    "max": axis.getCoordinateMax(),
                    "count": self.layout.getDimensionNumSamples(dim),
                    "unit": axis.getUnit()
                }

                suggested[dim_name] = dims_fields[dim_name].copy()

        except Exception as e:
            logger.error(f"Failed to discover dimensions: {e}")

        return {"fields": dims_fields, "suggested": suggested}

    def _discover_import_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Discover import-related metadata"""
        import_fields = {}
        suggested = {}

        # Look for import-related keys
        import_keys = [k for k in metadata.keys() if "import" in k.lower() or "input" in k.lower() or "source" in k.lower()]

        for key in import_keys:
            value = metadata[key]
            import_fields[key] = value

            # Suggest for common fields
            if any(term in key.lower() for term in ["filename", "name", "source"]):
                suggested["source_filename"] = value

        return {"fields": import_fields, "suggested": suggested}

    # ========================================================================
    # Batch Validation with Scoring
    # ========================================================================

    def validate_batch(
        self,
        claims: Dict[str, Any],
        metadata: Dict[str, Any],
        field_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Validate multiple field claims with overall scoring

        Returns:
            {
                "overall_status": "PASS" | "MOSTLY_VALID" | "PARTIALLY_VALID" | "FAIL",
                "validation_score": 0.0-1.0,
                "weighted_score": 0.0-1.0,
                "total_claims": int,
                "passed": int,
                "partial": int,
                "failed": int,
                "not_found": int,
                "details": {field_name: validation_result, ...}
            }
        """
        weights = field_weights or FIELD_WEIGHTS

        results = {}
        total = len(claims)
        passed = 0
        partial = 0
        failed = 0
        not_found = 0

        total_score = 0.0
        weighted_score_sum = 0.0
        total_weight = 0.0

        for field_name, claimed_value in claims.items():
            result = self.validate_field_claim(field_name, claimed_value, metadata)
            results[field_name] = result

            # Count statuses
            status = result["status"]
            if status == "PASS":
                passed += 1
                total_score += 1.0
            elif status == "PARTIAL":
                partial += 1
                total_score += result["confidence"]
            elif status == "FAIL":
                failed += 1
            elif status == "NOT_FOUND":
                not_found += 1

            # Weighted scoring
            weight = weights.get(field_name, 0.5)
            weighted_score_sum += result.get("confidence", 0.0) * weight
            total_weight += weight

        # Calculate scores
        validation_score = total_score / total if total > 0 else 0.0
        weighted_score = weighted_score_sum / total_weight if total_weight > 0 else 0.0

        # Determine overall status
        if validation_score >= 0.95:
            overall_status = "PASS"
        elif validation_score >= 0.75:
            overall_status = "MOSTLY_VALID"
        elif validation_score >= 0.50:
            overall_status = "PARTIALLY_VALID"
        else:
            overall_status = "FAIL"

        return {
            "overall_status": overall_status,
            "validation_score": round(validation_score, 3),
            "weighted_score": round(weighted_score, 3),
            "total_claims": total,
            "passed": passed,
            "partial": partial,
            "failed": failed,
            "not_found": not_found,
            "details": results
        }
