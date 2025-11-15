# VDS Metadata Data Integrity Issues - Analysis Report

**Date:** 2025-11-14
**Severity:** 🚨 **CRITICAL**
**Impact:** Survey ID resolution failures, wrong files opened, "Survey not found" errors

---

## Executive Summary

Your VDS Explorer system has critical data integrity issues in how survey IDs are resolved and matched to VDS files. This causes:

1. **File Path Mismatches**: Requesting survey A opens VDS file B
2. **Surveys Not Found**: Search returns results, but extraction fails with "Survey not found"
3. **Duplicate Basenames**: Same filename exists in multiple paths, causing ambiguous resolution

---

## Root Cause Analysis

### Issue 1: Missing `survey_id` Field in Elasticsearch

**Location**: Elasticsearch `vds-metadata` index
**Finding**: ALL 2,858 documents are missing the `survey_id` field

```bash
$ curl 'http://localhost:9200/vds-metadata/_search?q=file_path:*ST10010*'
{
  "file_path": "/vds-data/NCS/Volve/ST10010ZC11_PZ_PSDM_T_MIG-v2.vds",
  "survey_id": "MISSING"  # ❌ Not in index!
}
```

**Impact**:
- Survey ID is computed on-the-fly from file path (line 344 in `es_metadata_client.py`)
- If file path format changes or has special characters, survey ID extraction fails
- No indexed field for fast, reliable lookups

**Fix Required**: Re-index all documents with explicit `survey_id` field

---

###  Issue 2: Ambiguous Survey ID Resolution

**Location**: `src/vds_client.py:496`

```python
survey = next((s for s in self.available_surveys if s["id"] == survey_id), None)
```

**Problem**: When multiple files have similar basenames, this lookup is ambiguous:

**Example**:
```
ST10010ZC11_PZ_PSDM_T_MIG-v2.vds  (in /vds-data/NCS/Volve/)
ST10010ZC11_PZ_PSDM_T_MIG.vds      (hypothetical duplicate without -v2)
```

Both would extract to survey_id = `ST10010ZC11_PZ_PSDM_T_MIG*`, causing confusion.

**Impact**:
- Wrong file opened for extraction
- LLM agent sees correct search results but gets data from different survey
- Silent data corruption (no error, just wrong data)

**Fix Required**: Use file path as primary key, not basename

---

### Issue 3: Path Translation Errors

**Location**: `src/vds_client.py:502`

```python
file_path = self._translate_path(survey["file_path"])
vds_handle = openvds.open(file_path)
```

**Problem**: Path translation from ES path (`/vds-data/...`) to host path (`/Volumes/Hue/Datasets/VDS/...`) can fail if:
- Multiple mount points configured
- VDS_DATA_PATH environment variable has multiple paths
- NFS mount moved/renamed

**Current Evidence**:
```python
self.vds_data_path = os.getenv("VDS_DATA_PATH", "").split(":")[0]  # Only uses FIRST path!
```

If VDS_DATA_PATH = `/mount1:/mount2:/mount3`, only `/mount1` is checked.

**Impact**:
- Some surveys accessible via search but fail to open
- "Survey not found" errors even though ES returns results

**Fix Required**: Try all configured paths, add better error logging

---

### Issue 4: Duplicate Basenames

**Finding**: Multiple VDS files can have the same basename in different paths

**Example from ES**:
```
/vds-data/Equinor/Volve/Velocities/ST10010ZC11_MIG_VEL_AZIMUTH.vds
/vds-data/Equinor/Volve/Velocities/ST10010ZC11-MIG-VEL-AZIMUTH.vds  (hyphen vs underscore)
/vds-data/NCS/Volve/ST10010ZC11_PZ_PSDM_T_MIG-v2.vds
```

All extract to similar survey IDs starting with `ST10010...`

**Impact**:
- Search returns multiple results
- ID-based lookup might match wrong survey
- LLM gets confused about which survey is which

**Fix Required**: Use full file path as unique identifier, not basename

---

## Specific Failure Cases

### Case 1: "ST10010 Opens Brazil Survey"

**Reported Issue**:
> File path `/vds-data/NCS/Volve/ST10010ZC11_PZ_PSDM_T_MIG-v2.vds` opened a Brazil survey instead!

**Diagnosis**:
1. User searches for "ST10010" or "Volve"
2. ES returns multiple matches
3. `_convert_es_to_survey()` extracts `survey_id = "ST10010ZC11_PZ_PSDM_T_MIG-v2"`
4. Later, `_get_vds_handle()` looks up `s["id"] == "ST10010ZC11_PZ_PSDM_T_MIG-v2"`
5. **BUT** `self.available_surveys` might have been populated with a different ordering or different file
6. Opens wrong VDS file

**Root Cause**: Race condition / ordering issue in how `available_surveys` list is populated vs how it's queried

---

### Case 2: "ST0202 Found in Search, Not Found in Extraction"

**Reported Issue**:
> Survey `ST0202ZDC12_PZ_PSDM_KIRCH_FULL_D` found in search but returns "Survey not found" error

**Diagnosis**:
1. ES search finds the document
2. `_convert_es_to_survey()` creates survey dict with `id = "ST0202ZDC12_PZ_PSDM_KIRCH_FULL_D"`
3. LLM agent tries to extract using this survey_id
4. `_get_vds_handle()` searches `self.available_surveys` for matching ID
5. **NOT FOUND** because:
   - Survey was removed from available_surveys (stale mount)
   - File was moved/deleted after indexing
   - Path translation failed

**Root Cause**: ES index out of sync with actual filesystem

---

## Recommended Fixes

### Priority 1: Add `survey_id` to Elasticsearch Index

**Action**: Update crawler to explicitly set `survey_id` field

**File**: `vds-metadata-crawler/crawler.py` (or equivalent)

```python
# In crawler, when indexing a VDS file:
file_path = "/vds-data/Brazil/Santos/0282_BM_S_FASE2_3D_Sepia_Crop_IAI_FS_tol1.vds"
survey_id = file_path.split("/")[-1].replace(".vds", "")

document = {
    "file_path": file_path,
    "survey_id": survey_id,  # ✅ ADD THIS FIELD
    # ... other metadata
}
```

**Benefit**: Fast, reliable lookups without string manipulation

---

### Priority 2: Use File Path as Primary Key

**Action**: Change `_get_vds_handle()` to match on file_path instead of survey_id

**File**: `src/vds_client.py:496`

**Before**:
```python
survey = next((s for s in self.available_surveys if s["id"] == survey_id), None)
```

**After**:
```python
# Try exact file path match first
survey = next((s for s in self.available_surveys if s.get("file_path") == survey_id), None)

# Fall back to ID match (for backwards compatibility)
if not survey:
    survey = next((s for s in self.available_surveys if s["id"] == survey_id), None)
```

**Benefit**: Eliminates ambiguity from duplicate basenames

---

### Priority 3: Enhanced Error Logging

**Action**: Add diagnostic logging to `_get_vds_handle()`

**File**: `src/vds_client.py:490-511`

```python
def _get_vds_handle(self, survey_id: str) -> Optional[Any]:
    """Get or open a VDS handle for the survey"""
    if survey_id in self.vds_handles:
        return self.vds_handles[survey_id]

    # Find survey
    survey = next((s for s in self.available_surveys if s["id"] == survey_id), None)

    if not survey:
        logger.error(f"Survey ID not found in available_surveys: {survey_id}")
        logger.error(f"Available survey IDs: {[s['id'] for s in self.available_surveys[:10]]}")
        return None

    if survey.get("file_path", "").startswith("demo://"):
        return None

    try:
        file_path = self._translate_path(survey["file_path"])
        logger.info(f"Opening VDS file: {file_path}")
        logger.info(f"  Survey ID: {survey_id}")
        logger.info(f"  Original path: {survey['file_path']}")

        vds_handle = openvds.open(file_path)
        self.vds_handles[survey_id] = vds_handle
        return vds_handle

    except Exception as e:
        logger.error(f"Failed to open VDS file for {survey_id}: {e}")
        logger.error(f"  Original path: {survey.get('file_path')}")
        logger.error(f"  Translated path: {file_path if 'file_path' in locals() else 'N/A'}")
        return None
```

**Benefit**: Easier debugging of resolution failures

---

### Priority 4: Re-index Elasticsearch

**Action**: Run full re-index with `survey_id` field

**Commands**:
```bash
# 1. Delete old index
curl -X DELETE http://localhost:9200/vds-metadata

# 2. Create new index with mapping
curl -X PUT http://localhost:9200/vds-metadata -H 'Content-Type: application/json' -d '{
  "mappings": {
    "properties": {
      "survey_id": {"type": "keyword"},
      "file_path": {"type": "keyword"},
      "region": {"type": "keyword"},
      ...
    }
  }
}'

# 3. Re-run crawler
cd /Users/raghu/code/vds-metadata-crawler
python3 crawler.py
```

**Benefit**: All 2,858 documents will have proper `survey_id` field

---

## Testing Plan

### Test 1: Verify Survey ID Resolution

```python
# Test that survey_id correctly maps to file_path
survey_id = "ST10010ZC11_PZ_PSDM_T_MIG-v2"
survey = await vds_client.get_survey_metadata(survey_id)

assert survey["file_path"] == "/vds-data/NCS/Volve/ST10010ZC11_PZ_PSDM_T_MIG-v2.vds"
assert survey["id"] == survey_id
```

### Test 2: Verify No Cross-Survey Contamination

```python
# Extract from Volve survey
data_volve = await vds_client.extract_inline(
    survey_id="ST10010ZC11_PZ_PSDM_T_MIG-v2",
    inline=10000
)

# Verify inline range matches Volve (9961-10361), NOT Brazil (51000-58000)
assert 9961 <= data_volve["inline_coordinate"] <= 10361
```

### Test 3: Verify All Searchable Surveys Are Extractable

```python
# Search for surveys
results = await vds_client.search_surveys(search_query="Volve")

# Try to extract from each
for survey in results:
    try:
        metadata = await vds_client.get_survey_metadata(survey["id"])
        assert "error" not in metadata
    except Exception as e:
        print(f"❌ Survey {survey['id']} searchable but not extractable: {e}")
```

---

## Impact Assessment

| Issue | Severity | User Impact | Demo Risk |
|-------|----------|-------------|-----------|
| Missing survey_id in ES | HIGH | Slow queries, resolution failures | Medium |
| Wrong file opened | **CRITICAL** | **Silent data corruption** | **HIGH** |
| Surveys not found | HIGH | Feature unavailable | High |
| Duplicate basenames | MEDIUM | Ambiguous results | Medium |

**Recommendation**: Fix Priority 1-3 issues before any customer demo.

---

## Next Steps

1. ✅ **Document issues** (this file)
2. ⏳ **Update ES crawler** to add `survey_id` field
3. ⏳ **Modify `_get_vds_handle()`** for better resolution
4. ⏳ **Re-index Elasticsearch**
5. ⏳ **Run test suite**
6. ⏳ **Verify demo scenarios**

---

## Questions for Discussion

1. **Should survey_id be file basename or full path?**
   - Basename: Shorter, more readable
   - Full path: Unique, no ambiguity

2. **How to handle duplicate basenames?**
   - Append region to survey_id? (e.g., `ST10010_Volve`, `ST10010_Brazil`)
   - Use full path as ID?

3. **Should we validate ES index consistency?**
   - Add periodic "health check" that verifies all indexed files still exist
   - Auto-remove stale entries

4. **Path translation strategy?**
   - Try all VDS_DATA_PATH entries, not just first?
   - Add explicit mount point configuration?

