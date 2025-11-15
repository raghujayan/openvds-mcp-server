# VDS Metadata Validation Tool - Design Document

**Purpose**: Anti-hallucination validation for LLM claims about VDS file metadata
**Created**: 2025-11-10
**Status**: Ready for Implementation

---

## Problem Statement

Current anti-hallucination tools validate:
- ✓ Numerical statistics from extracted data (`validate_extracted_statistics`)
- ✓ Spatial coordinates within bounds (`verify_spatial_coordinates`)
- ✓ Mathematical consistency (`check_statistical_consistency`)

**Gap**: No validation for LLM claims about VDS **file metadata**, such as:
- Coordinate reference systems (CRS/projection)
- SEGY text headers (acquisition parameters, processing history)
- Data format specifications
- Import/provenance metadata

**Risk**: LLM may hallucinate metadata claims that sound plausible but are factually incorrect.

---

## Solution: `validate_vds_metadata` Tool

### High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│  LLM generates claim about VDS metadata             │
│  Example: "This survey uses UTM Zone 31N WGS84"     │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  validate_vds_metadata(survey_id, claims)           │
│  ┌───────────────────────────────────────────────┐  │
│  │ 1. Open VDS file                              │  │
│  │ 2. Extract ground truth from OpenVDS API      │  │
│  │ 3. Compare claims vs. actual metadata         │  │
│  │ 4. Return PASS/FAIL + corrections             │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  Result: { status: "FAIL", corrections: {...} }     │
│  Actual: "UTM Zone 33N WGS84" (not Zone 31N)       │
└─────────────────────────────────────────────────────┘
```

---

## API Design

### Tool Signature

```python
async def validate_vds_metadata(
    survey_id: str,
    claimed_metadata: Dict[str, Any],
    validation_type: str = "all"  # "segy_header", "crs", "dimensions", "import_info", "all"
) -> Dict[str, Any]:
    """
    Validate LLM claims about VDS metadata against ground truth

    Args:
        survey_id: VDS file identifier
        claimed_metadata: Dictionary of LLM claims to validate
        validation_type: What aspect of metadata to validate

    Returns:
        {
            "survey_id": str,
            "validation_type": str,
            "results": [
                {
                    "claim_key": str,
                    "claimed_value": Any,
                    "actual_value": Any,
                    "status": "PASS" | "FAIL",
                    "message": str
                }
            ],
            "overall_status": "PASS" | "FAIL",
            "pass_count": int,
            "fail_count": int
        }
    """
```

### Example Usage

```python
# Example 1: Validate CRS claim
result = await validate_vds_metadata(
    survey_id="0282_BM_S_FASE2_3D_Sepia_Crop_IAI_FS_tol1",
    claimed_metadata={
        "crs": "UTM Zone 31N WGS84",
        "projection": "Universal Transverse Mercator"
    },
    validation_type="crs"
)

# Result:
{
    "overall_status": "FAIL",
    "results": [
        {
            "claim_key": "crs",
            "claimed_value": "UTM Zone 31N WGS84",
            "actual_value": "UTM Zone 33N WGS84",
            "status": "FAIL",
            "message": "CRS mismatch: claimed Zone 31N but actual is Zone 33N"
        }
    ]
}

# Example 2: Validate SEGY header content
result = await validate_vds_metadata(
    survey_id="survey_123",
    claimed_metadata={
        "sample_interval_ms": 4.0,
        "migration_algorithm": "Kirchhoff"
    },
    validation_type="segy_header"
)

# Result:
{
    "overall_status": "PARTIAL",
    "results": [
        {
            "claim_key": "sample_interval_ms",
            "claimed_value": 4.0,
            "actual_value": 4.0,
            "status": "PASS",
            "message": "Sample interval matches SEGY binary header"
        },
        {
            "claim_key": "migration_algorithm",
            "claimed_value": "Kirchhoff",
            "actual_value": "RTM (Reverse Time Migration)",
            "status": "FAIL",
            "message": "Processing history in SEGY text header shows RTM, not Kirchhoff"
        }
    ]
}
```

---

## Implementation Details

### Core Metadata Extraction (from OpenVDS API)

Based on research in this session:

```python
def extract_segy_text_header(layout: openvds.VolumeDataLayout) -> str:
    """Extract 3200-byte SEGY text header"""
    # Known metadata categories for SEGY text header:
    # - "SEGY/TextHeader"
    # - "SEG-Y/TextHeader"
    # - "/SEGYTextHeader"

    for category, name in [
        ("SEGY", "TextHeader"),
        ("SEG-Y", "TextHeader"),
        ("", "SEGYTextHeader")
    ]:
        try:
            blob = layout.getMetadataBLOB(category, name)
            return blob.decode('ascii', errors='replace')
        except:
            continue

    return None

def parse_segy_header_cards(header_text: str) -> List[str]:
    """Parse 40 cards of 80 characters each"""
    cards = []
    for i in range(40):
        start = i * 80
        end = start + 80
        if start < len(header_text):
            card = header_text[start:end].rstrip()
            if card:
                cards.append(card)
    return cards

def extract_crs_from_segy(cards: List[str]) -> Optional[str]:
    """Extract CRS information from SEGY text header"""
    crs_keywords = ['UTM', 'WGS84', 'EPSG', 'ZONE', 'PROJECTION', 'DATUM', 'NAD']
    crs_cards = []

    for card in cards:
        if any(keyword in card.upper() for keyword in crs_keywords):
            crs_cards.append(card)

    # Parse to extract structured CRS info
    # (implementation details based on actual SEGY header formats)
    return "\n".join(crs_cards) if crs_cards else None

def extract_sample_interval(layout: openvds.VolumeDataLayout) -> float:
    """Extract sample interval from SEGY binary header or axis descriptor"""
    # Try SEGY binary header first
    try:
        binary_header = layout.getMetadataBLOB("SEGY", "BinaryHeader")
        # Bytes 17-18 contain sample interval in microseconds
        sample_interval_us = int.from_bytes(binary_header[16:18], 'big')
        return sample_interval_us / 1000.0  # Convert to milliseconds
    except:
        pass

    # Fallback to axis descriptor
    sample_axis = layout.getAxisDescriptor(0)  # Sample dimension
    return sample_axis.getCoordinateStep()
```

### OpenVDS Metadata API Reference

**Available methods** (discovered in this session):
```python
layout.getMetadataBLOB(category: str, name: str) -> bytes
layout.getMetadataString(category: str, name: str) -> str
layout.getMetadataInt(category: str, name: str) -> int
layout.getMetadataFloat(category: str, name: str) -> float
layout.getMetadataDouble(category: str, name: str) -> float
layout.isMetadataBLOBAvailable(category: str, name: str) -> bool
layout.getMetadataKeys() -> List[MetadataKey]
```

**Known metadata categories** (from `openvds.KnownMetadata`):
- `categorySEGY` - SEGY-specific metadata
- `categoryImportInformation` - File provenance
- `categoryStatistics` - Pre-computed statistics
- `categorySurveyCoordinateSystem` - CRS information
- `categoryTraceCoordinates` - Trace positioning

**SEGY metadata keys**:
- `SEGYTextHeader` - 3200-byte ASCII header
- `SEGYBinaryHeader` - 400-byte binary header
- `SEGYDataSampleFormatCode` - Sample format (IBM float, etc.)
- `SEGYEndianness` - Byte order

---

## Validation Types

### 1. SEGY Header Validation (`validation_type="segy_header"`)

**Validates claims against SEGY text header content**

Supported claims:
- Sample interval (ms)
- Acquisition parameters (source type, receiver type)
- Processing history (migration algorithm, filters applied)
- Survey geometry claims

Implementation:
```python
def validate_segy_header_claims(
    layout: openvds.VolumeDataLayout,
    claims: Dict[str, Any]
) -> List[ValidationResult]:
    text_header = extract_segy_text_header(layout)
    cards = parse_segy_header_cards(text_header)

    results = []
    for key, claimed_value in claims.items():
        if key == "sample_interval_ms":
            actual = extract_sample_interval(layout)
            status = "PASS" if abs(actual - claimed_value) < 0.1 else "FAIL"
            results.append({
                "claim_key": key,
                "claimed_value": claimed_value,
                "actual_value": actual,
                "status": status
            })
        elif key == "migration_algorithm":
            # Search cards for migration mentions
            migration_cards = [c for c in cards if 'MIGRATION' in c.upper()]
            actual = parse_migration_algorithm(migration_cards)
            status = "PASS" if actual.lower() in str(claimed_value).lower() else "FAIL"
            results.append(...)

    return results
```

### 2. CRS/Projection Validation (`validation_type="crs"`)

**Validates coordinate reference system claims**

Supported claims:
- UTM zone
- Datum (WGS84, NAD83, etc.)
- EPSG code
- Projection type

Implementation:
```python
def validate_crs_claims(
    layout: openvds.VolumeDataLayout,
    claims: Dict[str, Any]
) -> List[ValidationResult]:
    text_header = extract_segy_text_header(layout)
    cards = parse_segy_header_cards(text_header)
    crs_info = extract_crs_from_segy(cards)

    results = []
    for key, claimed_value in claims.items():
        if key == "utm_zone":
            # Parse actual UTM zone from CRS info
            actual = extract_utm_zone(crs_info)
            status = "PASS" if actual == claimed_value else "FAIL"
            results.append(...)
        elif key == "datum":
            actual = extract_datum(crs_info)
            status = "PASS" if actual == claimed_value else "FAIL"
            results.append(...)

    return results
```

### 3. Dimensions Validation (`validation_type="dimensions"`)

**Validates claims about survey dimensions**

Supported claims:
- Inline/crossline/sample ranges
- Survey extent
- Data type (2D, 3D, 4D)

Implementation:
```python
def validate_dimension_claims(
    layout: openvds.VolumeDataLayout,
    claims: Dict[str, Any]
) -> List[ValidationResult]:
    results = []

    for key, claimed_value in claims.items():
        if key == "inline_range":
            inline_axis = layout.getAxisDescriptor(2)
            actual_min = inline_axis.getCoordinateMin()
            actual_max = inline_axis.getCoordinateMax()
            actual = [int(actual_min), int(actual_max)]

            status = "PASS" if actual == claimed_value else "FAIL"
            results.append(...)

    return results
```

### 4. Import Info Validation (`validation_type="import_info"`)

**Validates claims about file provenance**

Supported claims:
- Original filename
- Import timestamp
- Data format
- File size

Implementation:
```python
def validate_import_info_claims(
    layout: openvds.VolumeDataLayout,
    claims: Dict[str, Any]
) -> List[ValidationResult]:
    results = []

    for key, claimed_value in claims.items():
        if key == "original_filename":
            actual = layout.getMetadataString(
                "ImportInformation",
                "InputFileName"
            )
            status = "PASS" if actual == claimed_value else "FAIL"
            results.append(...)

    return results
```

---

## Integration with Existing Code

### File Structure

```
src/
├── vds_client.py              # Add new method: validate_vds_metadata()
├── data_integrity.py          # Existing integrity agent
├── metadata_validator.py      # NEW: Metadata validation logic
└── openvds_mcp_server.py     # Register new MCP tool
```

### New File: `src/metadata_validator.py`

```python
"""
VDS Metadata Validator - Anti-hallucination for metadata claims

Validates LLM claims about VDS file metadata against ground truth extracted
directly from VDS files using OpenVDS API.
"""

import logging
from typing import Dict, List, Any, Optional
import openvds

logger = logging.getLogger("metadata-validator")


class MetadataValidator:
    """Validates LLM claims about VDS metadata"""

    def validate(
        self,
        vds_handle: openvds.VolumeDataAccessManager,
        claimed_metadata: Dict[str, Any],
        validation_type: str = "all"
    ) -> Dict[str, Any]:
        """Main validation entry point"""

        layout = openvds.getLayout(vds_handle)

        if validation_type == "segy_header" or validation_type == "all":
            results = self._validate_segy_header(layout, claimed_metadata)
        elif validation_type == "crs":
            results = self._validate_crs(layout, claimed_metadata)
        elif validation_type == "dimensions":
            results = self._validate_dimensions(layout, claimed_metadata)
        elif validation_type == "import_info":
            results = self._validate_import_info(layout, claimed_metadata)
        else:
            raise ValueError(f"Unknown validation_type: {validation_type}")

        return self._format_results(results)

    def _validate_segy_header(self, layout, claims):
        """Validate SEGY header claims"""
        # Implementation from above
        pass

    def _validate_crs(self, layout, claims):
        """Validate CRS claims"""
        # Implementation from above
        pass

    # ... other validation methods

    def _format_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Format validation results"""
        pass_count = sum(1 for r in results if r["status"] == "PASS")
        fail_count = len(results) - pass_count

        return {
            "results": results,
            "overall_status": "PASS" if fail_count == 0 else "FAIL",
            "pass_count": pass_count,
            "fail_count": fail_count
        }


# Singleton instance
_validator = None

def get_metadata_validator() -> MetadataValidator:
    """Get singleton validator instance"""
    global _validator
    if _validator is None:
        _validator = MetadataValidator()
    return _validator
```

### Integration in `vds_client.py`

```python
from src.metadata_validator import get_metadata_validator

class VDSClient:
    # ... existing methods ...

    async def validate_vds_metadata(
        self,
        survey_id: str,
        claimed_metadata: Dict[str, Any],
        validation_type: str = "all"
    ) -> Dict[str, Any]:
        """
        Validate LLM claims about VDS metadata

        Anti-hallucination tool for metadata claims
        """
        survey = self._find_survey(survey_id)
        if not survey:
            return {"error": f"Survey not found: {survey_id}"}

        try:
            vds_handle = self._get_vds_handle(survey_id)
            if not vds_handle:
                return {"error": "Failed to open VDS file"}

            validator = get_metadata_validator()
            result = validator.validate(
                vds_handle,
                claimed_metadata,
                validation_type
            )

            result["survey_id"] = survey_id
            result["validation_type"] = validation_type

            return result

        except Exception as e:
            logger.error(f"Metadata validation error: {e}", exc_info=True)
            return {"error": str(e)}
```

### MCP Tool Registration in `openvds_mcp_server.py`

```python
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    # ... existing tools ...

    elif name == "validate_vds_metadata":
        result = await vds_client.validate_vds_metadata(
            survey_id=arguments["survey_id"],
            claimed_metadata=arguments["claimed_metadata"],
            validation_type=arguments.get("validation_type", "all")
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
```

Tool schema:
```python
Tool(
    name="validate_vds_metadata",
    description="""
    ⚠️ ANTI-HALLUCINATION VALIDATION ⚠️

    Validate LLM claims about VDS file metadata against ground truth.

    USE THIS TOOL to prevent hallucinations about:
    - Coordinate reference systems (CRS/projection)
    - SEGY text header content (acquisition, processing)
    - Survey dimensions and ranges
    - File provenance (import info)

    WHEN TO USE:
    - After making any claim about CRS/projection
    - After stating acquisition or processing parameters
    - After describing metadata from SEGY headers
    - When user asks to verify metadata claims

    The tool extracts actual metadata from VDS file using OpenVDS API
    and compares against your claims. Returns PASS/FAIL with corrections.
    """,
    inputSchema={
        "type": "object",
        "properties": {
            "survey_id": {
                "type": "string",
                "description": "VDS survey identifier"
            },
            "claimed_metadata": {
                "type": "object",
                "description": "Dictionary of metadata claims to validate",
                "additionalProperties": True
            },
            "validation_type": {
                "type": "string",
                "enum": ["all", "segy_header", "crs", "dimensions", "import_info"],
                "description": "Type of metadata to validate (default: all)"
            }
        },
        "required": ["survey_id", "claimed_metadata"]
    }
)
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_metadata_validator.py

def test_validate_segy_sample_interval():
    """Test sample interval validation"""
    # Open real VDS file
    # Extract actual sample interval
    # Test PASS case
    # Test FAIL case
    pass

def test_validate_crs_utm_zone():
    """Test UTM zone validation"""
    # Test correct zone -> PASS
    # Test wrong zone -> FAIL
    pass

def test_validate_dimensions():
    """Test dimension validation"""
    pass
```

### Integration Tests

```python
# tests/integration/test_metadata_validation_e2e.py

async def test_full_validation_flow():
    """End-to-end test of metadata validation"""
    # 1. Make claim via LLM
    # 2. Call validate_vds_metadata
    # 3. Verify correction provided
    pass
```

---

## Future Enhancements

1. **Cross-survey metadata comparison**
   - Validate claims like "Survey A and B have the same CRS"
   - Requires comparing metadata between multiple VDS files

2. **Fuzzy matching for text claims**
   - Use similarity metrics for SEGY text header matching
   - Handle variations in terminology ("Kirchhoff" vs "Kirchhoff Migration")

3. **Metadata caching**
   - Cache extracted metadata to avoid repeated VDS file opens
   - Integrate with existing query cache

4. **Metadata change detection**
   - Detect if VDS file metadata has been modified since last validation
   - Useful for long-running sessions

---

## Performance Considerations

1. **VDS File Access**
   - Opening VDS files is relatively fast (< 100ms)
   - Metadata extraction is lightweight (no data reading)
   - Consider caching opened handles (already implemented in VDSClient)

2. **SEGY Header Parsing**
   - Text header: 3200 bytes (trivial to parse)
   - Binary header: 400 bytes (simple struct parsing)
   - Minimal CPU overhead

3. **Validation Overhead**
   - Expect < 200ms per validation call
   - Mostly I/O bound (opening VDS file)
   - Can be done in parallel with data extraction

---

## Implementation Checklist

- [ ] Create `src/metadata_validator.py` with MetadataValidator class
- [ ] Implement SEGY text header extraction and parsing
- [ ] Implement CRS extraction from SEGY headers
- [ ] Implement sample interval extraction
- [ ] Add `validate_vds_metadata()` method to VDSClient
- [ ] Register MCP tool in openvds_mcp_server.py
- [ ] Write unit tests for each validation type
- [ ] Write integration tests for end-to-end flow
- [ ] Update MCP tool descriptions in main.py backend
- [ ] Add concise description to SystemStatusPanel UI
- [ ] Document usage patterns in CLAUDE.md or similar
- [ ] Test with real-world metadata claims

---

## Key Files for Implementation

**Existing files to reference**:
- `/Users/raghu/code/vds-metadata-crawler/parse_vdsinfo_complete.py` - SEGY header parsing patterns
- `/Users/raghu/code/openvds-mcp-server/src/data_integrity.py` - Anti-hallucination pattern reference
- `/Users/raghu/code/openvds-mcp-server/src/vds_client.py` - OpenVDS API usage patterns

**New files to create**:
- `/Users/raghu/code/openvds-mcp-server/src/metadata_validator.py` - Core implementation

**Files to modify**:
- `/Users/raghu/code/openvds-mcp-server/src/vds_client.py` - Add validate_vds_metadata() method
- `/Users/raghu/code/openvds-mcp-server/src/openvds_mcp_server.py` - Register MCP tool
- `/Users/raghu/code/openvds-mcp-server/mcp-ui-client/backend/app/main.py` - Add tool description

---

## Session Context (for implementation)

**OpenVDS API discoveries**:
- Metadata accessed via `layout.getMetadataBLOB()`, `layout.getMetadataString()`, etc.
- SEGY text header available at multiple category/name combinations:
  - `("SEGY", "TextHeader")`
  - `("SEG-Y", "TextHeader")`
  - `("", "SEGYTextHeader")`
- Known metadata in `openvds.KnownMetadata` enum
- MetadataWriteAccess requires write permissions (not available for read-only files)

**Current anti-hallucination toolset**:
1. `validate_extracted_statistics` - Numerical data validation
2. `verify_spatial_coordinates` - Bounds checking
3. `check_statistical_consistency` - Mathematical validation
4. **NEW**: `validate_vds_metadata` - Metadata validation (this design)

**System status**:
- All services running (Frontend: 3000, Backend: 8000, ES: 9200, Kibana: 5601)
- 19 MCP tools currently available
- 2858 VDS datasets indexed in Elasticsearch

---

**END OF DESIGN DOCUMENT**
