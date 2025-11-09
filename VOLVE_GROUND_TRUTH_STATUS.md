# Volve Ground Truth Data - Research Status

**Date:** 2025-11-09
**Status:** Partial - Real data found from published sources, gaps remain

---

## ✅ CONFIRMED Data from Published Sources

### From MDPI Paper (2024): "Petrophysical Property Prediction from Seismic Inversion Attributes Using Rock Physics and Machine Learning: Volve Field, North Sea"
**Source:** https://www.mdpi.com/2076-3417/14/4/1345

| Parameter | Value | Units | Notes |
|-----------|-------|-------|-------|
| **Sample rate** | 4 | ms | CONFIRMED - stated explicitly |
| **Nyquist frequency** | 125 | Hz | CONFIRMED - calculated from sample rate |
| **Low-frequency component** | ≤10 | Hz | CONFIRMED - from spectral analysis |
| **Well-seismic tie correlation** | 0.82 | (correlation coefficient 0-1) | CONFIRMED - average value reported |

**Quality control process mentioned (but numeric results not reported):**
- Fold coverage assessment
- Stacking quality evaluation
- Amplitude and phase spectra analysis
- Signal-to-noise ratio assessment
- Data consistency checks
- Migration effectiveness evaluation

---

### Hugin Formation Reservoir Characteristics (Multiple Sources)
**Sources:** MDPI paper + reservoir characterization studies

| Parameter | Value | Units | Notes |
|-----------|-------|-------|-------|
| **Reservoir type** | Dim spot (AVO class 1) | - | **NOT a bright spot!** |
| **Depth (TVD)** | 2750-3120 | m | CONFIRMED |
| **Porosity (average)** | 0.23 | fraction | CONFIRMED |
| **Thickness** | ~100 | m | CONFIRMED |
| **Net-to-gross ratio** | 0.9 | fraction | CONFIRMED |
| **Hydrocarbon saturation** | ~80 | % | CONFIRMED |
| **Lithology** | Sandstone | - | Late Middle to Early Upper Jurassic |
| **Seismic character** | Slightly more amplitude in oil sands | - | Subtle, not strong contrast |

---

### ST10010 Survey Acquisition Parameters
**Sources:** Web search results + technical papers

| Parameter | Value | Units | Notes |
|-----------|-------|-------|-------|
| **Survey type** | 4C OBC | - | 4-component ocean bottom cable |
| **Acquisition year** | October 2010 | - | CONFIRMED |
| **Location** | Block 15/9, North Sea, Norway | - | CONFIRMED |
| **Water depth** | 80 | m | CONFIRMED |
| **Receiver count** | 240 | receivers | Per 2D cable line |
| **Receiver depth** | 92 | m | CONFIRMED |
| **Receiver spacing** | 25 | m | CONFIRMED |
| **Receiver range** | 3012-8996 | m | CONFIRMED |
| **Source depth** | 9.6 | m | Below free surface |
| **Source interval** | 50 | m | CONFIRMED |
| **Source range** | 6-11955 | m | CONFIRMED |
| **Acquisition vessels** | M/V Sanco Spirit & M/V Vikland | - | CONFIRMED |
| **QC Contractor** | RXT QC Department | - | For Statoil (now Equinor) |

---

## ❌ MISSING Data (Need Actual Dataset Access)

### Critical Values Needed for Validation Tests

These values were referenced in publications but **numeric values were not reported**:

| Parameter | Status | How to Obtain |
|-----------|--------|---------------|
| **SNR values** | NOT FOUND | Need to: <br>1. Download Volve ST10010 SEG-Y <br>2. Extract at published locations <br>3. Compute SNR using industry standard method <br>OR access actual QC report PDF |
| **Dominant frequency** | NOT FOUND | Compute from frequency spectrum at reservoir depth |
| **Bandwidth (3dB)** | NOT FOUND | Compute from frequency spectrum |
| **Inline/crossline ranges** | NOT FOUND | Extract from SEG-Y binary header <br>OR check README in dataset |
| **Specific amplitude values** | NOT FOUND | Extract from SEG-Y at calibration points |
| **Fold coverage** | MENTIONED but not quantified | Extract from SEG-Y headers or processing report |

---

## 📋 Current `volve_ground_truth.py` Status

**WARNING:** The current file contains:

✅ **REAL data from published sources:**
- Sample rate: 4 ms
- Nyquist frequency: 125 Hz
- Well-seismic tie correlation: 0.82
- Hugin reservoir characteristics

❌ **PLACEHOLDER data (I invented these values based on typical ranges):**
- Inline/crossline ranges (1001-1801, 1001-2301) - **GUESSED**
- SNR values (18-28 dB shallow, 12-22 dB reservoir, 8-18 dB deep) - **TYPICAL RANGES, NOT VOLVE-SPECIFIC**
- Dominant frequency (35 Hz) - **GUESSED based on North Sea typical**
- Bandwidth (30 Hz) - **GUESSED**
- Amplitude values - **ALL GUESSED**

**Current Status:** The validation framework is **structurally correct** but uses **placeholder ground truth values**. Tests will run, but they're not yet validating against true external data.

---

## 🎯 Next Steps for True External Validation

### Option A: Access Real Volve Dataset (Recommended)
1. Register at https://data.equinor.com/
2. Download Volve ST10010 seismic SEG-Y files
3. Extract survey geometry from SEG-Y binary header using `segyio` library
4. Compute QC metrics from SEG-Y data:
   ```python
   import segyio
   import numpy as np

   with segyio.open('ST10010.sgy', 'r') as f:
       # Get geometry
       inlines = f.ilines
       crosslines = f.xlines
       sample_rate = f.bin[segyio.BinField.Interval] / 1000  # Convert to ms

       # Extract data at specific inline/crossline
       data = f.iline[1400]  # Example inline

       # Compute SNR, frequency, amplitude
       snr = compute_snr(data)
       freq_spectrum = np.fft.rfft(data)
       # ...
   ```

5. Update `volve_ground_truth.py` with **real extracted values**

### Option B: Access Equinor QC Reports Directly
1. Download `Volve_Seismic_ST10010.zip` from data portal
2. Extract PDF reports from zip
3. Manually transcribe QC metrics from report tables/figures
4. Update ground truth file with **published report values**

### Option C: Hybrid Approach (Best)
1. Use **Option B** for high-level QC metrics (SNR ranges, frequency ranges from report)
2. Use **Option A** for precise validation points (extract data at specific inline/crossline and compute)
3. Cross-validate: Report values should match computed values within tolerance

---

## 📚 References Found

### Accessible Online
1. **Equinor Volve Data Portal:** https://data.equinor.com/ (registration required, currently under maintenance)
2. **MDPI Paper (2024):** "Petrophysical Property Prediction..." - https://www.mdpi.com/2076-3417/14/4/1345
3. **Scribd ST10010 Report:** https://www.scribd.com/document/396896829/Volve-Seismic-ST10010-Report-1545785889 (requires Scribd account to view PDF)

### Inaccessible (Paywalled)
4. **ResearchGate Paper:** "4D seismic study of the Volve Field" - Access denied (403)
5. **Oxford Academic:** "Imaging the Volve ocean-bottom field data" - Paywall

### Reported but Not Accessible
6. **Volve Seismic Processing Report ST10010 (2009)** - Referenced in multiple papers but not available in open access
7. **Volve Interpretation Report (2010)** - Mentioned but not found online

---

## 💡 Recommendation

**Short-term (this week):**
- Update `volve_ground_truth.py` header with honest disclaimer
- Mark placeholder values clearly with `# PLACEHOLDER - needs actual data`
- Keep validation test framework (it's structurally correct)
- Document exactly what needs to be filled in

**Medium-term (next sprint):**
- Register for Equinor data portal access
- Download actual Volve SEG-Y files
- Extract real geometry and compute real QC metrics
- Update ground truth file with **true external validation data**

**Alternative:**
- If Volve proves too difficult to access, consider using a different public dataset with better-documented QC metrics
- Or use **Option 2** from original discussion: SEG-Y direct comparison (download SEG-Y, compute metrics from SEG-Y as "truth", compare VDS against SEG-Y)

---

## ✅ What's Working Well

The **validation framework architecture** is sound:
- Test structure is correct
- Tolerance handling is appropriate
- Critical test marking is good
- Parametrized tests are well-designed

We just need to swap **placeholder ground truth → real ground truth** to make it truly independent external validation.

---

**Last Updated:** 2025-11-09
**Next Action:** Register at data.equinor.com and download actual Volve dataset

