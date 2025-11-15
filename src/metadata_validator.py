"""
VDS Metadata Validator
Anti-hallucination tool for verifying LLM claims about VDS metadata

This module validates claims about:
- SEGY text headers (processing history, acquisition params)
- CRS/projection information (UTM zone, datum, EPSG codes)
- Dimension ranges (inline/crossline/sample extent)
- Import metadata (filenames, timestamps)
"""

import re
import struct
from typing import Dict, List, Any, Optional, Tuple
import openvds
import logging

logger = logging.getLogger(__name__)


class MetadataValidator:
    """Validates LLM claims about VDS metadata against ground truth"""

    def __init__(self, handle, layout):
        """
        Args:
            handle: OpenVDS handle
            layout: OpenVDS layout object
        """
        self.handle = handle
        self.layout = layout

    # ========================================================================
    # SEGY Header Extraction
    # ========================================================================

    def get_segy_text_header(self) -> Optional[str]:
        """
        Extract SEGY 3200-byte text header (40 cards x 80 chars)

        Returns:
            Text header as string, or None if not available
        """
        # Try multiple category/name combinations
        locations = [
            ("SEGY", "TextHeader"),
            ("SEG-Y", "TextHeader"),
            ("", "SEGYTextHeader")
        ]

        for category, name in locations:
            if self.layout.isMetadataBLOBAvailable(category, name):
                try:
                    blob = self.layout.getMetadataBLOB(category, name)
                    # SEGY text header is EBCDIC encoded
                    # Convert to ASCII for readability
                    text = self._ebcdic_to_ascii(blob)
                    return text
                except Exception as e:
                    logger.warning(f"Failed to read SEGY header at ({category}, {name}): {e}")
                    continue

        logger.warning("SEGY text header not found in any standard location")
        return None

    def get_segy_binary_header(self) -> Optional[bytes]:
        """
        Extract SEGY 400-byte binary header

        Returns:
            Binary header bytes, or None if not available
        """
        locations = [
            ("SEGY", "BinaryHeader"),
            ("SEG-Y", "BinaryHeader"),
            ("", "SEGYBinaryHeader")
        ]

        for category, name in locations:
            if self.layout.isMetadataBLOBAvailable(category, name):
                try:
                    return self.layout.getMetadataBLOB(category, name)
                except Exception as e:
                    logger.warning(f"Failed to read binary header at ({category}, {name}): {e}")
                    continue

        return None

    def _ebcdic_to_ascii(self, ebcdic_bytes: bytes) -> str:
        """Convert EBCDIC encoded bytes to ASCII string"""
        # EBCDIC to ASCII translation table
        # This is a simplified version - production code should use full table
        ascii_chars = []
        for byte in ebcdic_bytes:
            # Basic EBCDIC to ASCII conversion
            # For production, use proper EBCDIC codec
            if 64 <= byte <= 201:  # Rough mapping for printable chars
                ascii_chars.append(chr(byte))
            elif byte == 64:  # Space
                ascii_chars.append(' ')
            else:
                ascii_chars.append('.')  # Non-printable

        return ''.join(ascii_chars)

    def parse_sample_interval_from_binary_header(self) -> Optional[float]:
        """
        Parse sample interval from SEGY binary header (bytes 17-18)

        Returns:
            Sample interval in microseconds, or None
        """
        binary_header = self.get_segy_binary_header()
        if not binary_header or len(binary_header) < 18:
            return None

        try:
            # Bytes 17-18: sample interval in microseconds (big-endian int16)
            sample_interval = struct.unpack('>H', binary_header[16:18])[0]
            return float(sample_interval)
        except Exception as e:
            logger.error(f"Failed to parse sample interval: {e}")
            return None

    # ========================================================================
    # CRS Information Extraction
    # ========================================================================

    def extract_crs_from_text_header(self, text_header: str) -> Dict[str, Any]:
        """
        Extract CRS information from SEGY text header

        Args:
            text_header: SEGY text header string

        Returns:
            Dict with keys: utm_zone, hemisphere, datum, epsg_code
        """
        crs_info = {
            "utm_zone": None,
            "hemisphere": None,
            "datum": None,
            "epsg_code": None
        }

        # Search for UTM zone patterns
        utm_patterns = [
            r'UTM\s+ZONE\s+(\d+)\s*([NS])?',
            r'ZONE\s+(\d+)\s*([NS])?',
            r'UTM(\d+)([NS])?'
        ]

        for pattern in utm_patterns:
            match = re.search(pattern, text_header, re.IGNORECASE)
            if match:
                crs_info["utm_zone"] = int(match.group(1))
                if match.lastindex >= 2 and match.group(2):
                    crs_info["hemisphere"] = match.group(2).upper()
                break

        # Search for datum
        datum_patterns = [
            r'DATUM[:\s]+(\w+)',
            r'(WGS84|WGS-84|NAD27|NAD83)',
        ]

        for pattern in datum_patterns:
            match = re.search(pattern, text_header, re.IGNORECASE)
            if match:
                crs_info["datum"] = match.group(1).upper()
                break

        # Search for EPSG code
        epsg_match = re.search(r'EPSG[:\s]+(\d+)', text_header, re.IGNORECASE)
        if epsg_match:
            crs_info["epsg_code"] = int(epsg_match.group(1))

        return crs_info

    def get_crs_from_metadata(self) -> Optional[str]:
        """
        Get CRS string from OpenVDS metadata

        Returns:
            CRS string (e.g., "WGS84 / UTM zone 31N"), or None
        """
        # Check for CRS in various metadata locations
        crs_locations = [
            ("SpatialReference", "WellKnownText"),
            ("CoordinateSystem", "CRS"),
            ("", "CoordinateReferenceSystem")
        ]

        for category, name in crs_locations:
            if self.layout.isMetadataStringAvailable(category, name):
                try:
                    return self.layout.getMetadataString(category, name)
                except:
                    continue

        return None

    # ========================================================================
    # Dimension Information
    # ========================================================================

    def get_dimension_info(self) -> Dict[str, Any]:
        """
        Get dimension ranges (inline/crossline/sample)

        Returns:
            Dict with dimension_name -> {min, max, count, unit}
        """
        dims = {}

        for dim_idx in range(3):
            axis = self.layout.getAxisDescriptor(dim_idx)

            dim_info = {
                "name": axis.getName(),
                "unit": axis.getUnit(),
                "min": axis.getCoordinateMin(),
                "max": axis.getCoordinateMax(),
                "count": self.layout.getDimensionNumSamples(dim_idx),
                "sample_min_index": 0,
                "sample_max_index": self.layout.getDimensionNumSamples(dim_idx) - 1
            }

            dims[axis.getName()] = dim_info

        return dims

    # ========================================================================
    # Import Information
    # ========================================================================

    def get_import_info(self) -> Dict[str, Any]:
        """
        Get import metadata (original filename, timestamp, etc.)

        Returns:
            Dict with import information
        """
        import_info = {
            "input_filename": None,
            "import_timestamp": None,
            "vds_version": None
        }

        # Try to get input filename
        filename_locations = [
            ("ImportInformation", "InputFileName"),
            ("", "InputFileName"),
            ("SEGY", "OriginalFileName")
        ]

        for category, name in filename_locations:
            if self.layout.isMetadataStringAvailable(category, name):
                try:
                    import_info["input_filename"] = self.layout.getMetadataString(category, name)
                    break
                except:
                    continue

        # Try to get import timestamp
        timestamp_locations = [
            ("ImportInformation", "ImportTimeStamp"),
            ("", "ImportTimeStamp")
        ]

        for category, name in timestamp_locations:
            if self.layout.isMetadataStringAvailable(category, name):
                try:
                    import_info["import_timestamp"] = self.layout.getMetadataString(category, name)
                    break
                except:
                    continue

        # Get VDS version
        try:
            import_info["vds_version"] = f"{self.layout.getLayoutDescriptor().getFormatVersion()}"
        except:
            pass

        return import_info

    # ========================================================================
    # Validation Methods
    # ========================================================================

    def validate_segy_header_claim(
        self,
        claimed_value: str,
        field_name: str,
        tolerance: str = "exact"
    ) -> Dict[str, Any]:
        """
        Validate a claim about SEGY header content

        Args:
            claimed_value: What the LLM claims is in the header
            field_name: What field this claim is about (e.g., "sample_interval", "processing_history")
            tolerance: "exact" or "substring"

        Returns:
            {
                "valid": bool,
                "claimed": str,
                "actual": str,
                "match_type": "exact" | "substring" | "not_found",
                "details": str
            }
        """
        text_header = self.get_segy_text_header()

        if text_header is None:
            return {
                "valid": False,
                "claimed": claimed_value,
                "actual": None,
                "match_type": "not_found",
                "details": "SEGY text header not available in this VDS file"
            }

        # Special handling for sample_interval
        if field_name == "sample_interval":
            actual_interval = self.parse_sample_interval_from_binary_header()
            if actual_interval is None:
                return {
                    "valid": False,
                    "claimed": claimed_value,
                    "actual": None,
                    "match_type": "not_found",
                    "details": "Sample interval not found in binary header"
                }

            try:
                claimed_float = float(claimed_value)
                # Allow 1% tolerance for floating point
                diff = abs(claimed_float - actual_interval) / actual_interval
                valid = diff < 0.01

                return {
                    "valid": valid,
                    "claimed": claimed_value,
                    "actual": str(actual_interval),
                    "match_type": "exact" if valid else "mismatch",
                    "details": f"Claimed {claimed_float}, actual {actual_interval} ({diff*100:.2f}% difference)"
                }
            except ValueError:
                return {
                    "valid": False,
                    "claimed": claimed_value,
                    "actual": str(actual_interval),
                    "match_type": "format_error",
                    "details": "Claimed value is not a valid number"
                }

        # General text search
        if tolerance == "exact":
            valid = claimed_value in text_header
            match_type = "exact" if valid else "not_found"
        else:  # substring
            # Case-insensitive substring match
            valid = claimed_value.lower() in text_header.lower()
            match_type = "substring" if valid else "not_found"

        return {
            "valid": valid,
            "claimed": claimed_value,
            "actual": text_header[:500] + "..." if len(text_header) > 500 else text_header,
            "match_type": match_type,
            "details": f"Text {'found' if valid else 'not found'} in SEGY header"
        }

    def validate_crs_claim(self, claimed_crs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate claims about CRS/projection

        Args:
            claimed_crs: Dict with keys like utm_zone, hemisphere, datum, epsg_code

        Returns:
            Validation result with field-by-field comparison
        """
        text_header = self.get_segy_text_header()
        if text_header:
            actual_crs = self.extract_crs_from_text_header(text_header)
        else:
            actual_crs = {
                "utm_zone": None,
                "hemisphere": None,
                "datum": None,
                "epsg_code": None
            }

        # Also check metadata CRS
        metadata_crs = self.get_crs_from_metadata()

        results = []
        all_valid = True

        for key, claimed_value in claimed_crs.items():
            if claimed_value is None:
                continue  # Skip unclaimed fields

            actual_value = actual_crs.get(key)

            if actual_value is None:
                valid = False
                details = f"Field '{key}' not found in VDS metadata"
            elif str(claimed_value).upper() == str(actual_value).upper():
                valid = True
                details = "Match"
            else:
                valid = False
                details = f"Mismatch: claimed '{claimed_value}', actual '{actual_value}'"

            results.append({
                "field": key,
                "valid": valid,
                "claimed": claimed_value,
                "actual": actual_value,
                "details": details
            })

            if not valid:
                all_valid = False

        return {
            "overall_valid": all_valid,
            "field_results": results,
            "metadata_crs_string": metadata_crs
        }

    def validate_dimensions_claim(self, claimed_dims: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate claims about dimension ranges

        Args:
            claimed_dims: Dict with dimension_name -> {min, max} or {count}

        Returns:
            Validation result with field-by-field comparison
        """
        actual_dims = self.get_dimension_info()

        results = []
        all_valid = True

        for dim_name, claimed_info in claimed_dims.items():
            if dim_name not in actual_dims:
                results.append({
                    "dimension": dim_name,
                    "valid": False,
                    "details": f"Dimension '{dim_name}' not found in VDS"
                })
                all_valid = False
                continue

            actual_info = actual_dims[dim_name]

            # Validate each claimed field
            for field, claimed_value in claimed_info.items():
                actual_value = actual_info.get(field)

                if actual_value is None:
                    valid = False
                    details = f"Field '{field}' not available"
                elif isinstance(claimed_value, (int, float)) and isinstance(actual_value, (int, float)):
                    # Numeric comparison with tolerance
                    if field in ["min", "max"]:
                        # Allow 0.1% tolerance for min/max coordinates
                        tolerance = 0.001
                        diff = abs(claimed_value - actual_value)
                        max_diff = abs(actual_value) * tolerance
                        valid = diff <= max_diff
                        details = f"Claimed {claimed_value}, actual {actual_value}"
                    else:
                        # Exact match for counts
                        valid = claimed_value == actual_value
                        details = f"Claimed {claimed_value}, actual {actual_value}"
                else:
                    # String comparison
                    valid = str(claimed_value) == str(actual_value)
                    details = f"Claimed '{claimed_value}', actual '{actual_value}'"

                results.append({
                    "dimension": dim_name,
                    "field": field,
                    "valid": valid,
                    "claimed": claimed_value,
                    "actual": actual_value,
                    "details": details
                })

                if not valid:
                    all_valid = False

        return {
            "overall_valid": all_valid,
            "field_results": results,
            "actual_dimensions": actual_dims
        }

    def validate_import_info_claim(self, claimed_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate claims about import metadata

        Args:
            claimed_info: Dict with keys like input_filename, import_timestamp

        Returns:
            Validation result
        """
        actual_info = self.get_import_info()

        results = []
        all_valid = True

        for key, claimed_value in claimed_info.items():
            if claimed_value is None:
                continue

            actual_value = actual_info.get(key)

            if actual_value is None:
                valid = False
                details = f"Field '{key}' not found in import metadata"
            elif key == "input_filename":
                # Filename can be partial match (basename vs full path)
                claimed_base = claimed_value.split('/')[-1]
                actual_base = actual_value.split('/')[-1] if actual_value else ""
                valid = claimed_base.lower() == actual_base.lower()
                details = f"Filename: claimed '{claimed_base}', actual '{actual_base}'"
            else:
                # Exact match for other fields
                valid = str(claimed_value) == str(actual_value)
                details = f"Claimed '{claimed_value}', actual '{actual_value}'"

            results.append({
                "field": key,
                "valid": valid,
                "claimed": claimed_value,
                "actual": actual_value,
                "details": details
            })

            if not valid:
                all_valid = False

        return {
            "overall_valid": all_valid,
            "field_results": results,
            "actual_import_info": actual_info
        }
