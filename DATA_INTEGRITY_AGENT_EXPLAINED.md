# Data Integrity Agent - Simple Explanation

## The Problem It Solves

**Scenario without Data Integrity Agent:**

```
You: "What's the maximum amplitude in inline 55000?"

Claude (analyzing the image):
"The maximum amplitude appears to be around 2500"
                                        ↑
                                    MADE UP!
                      (Claude guessed from looking at the image)
```

**The issue:** Claude might:
- Guess numbers that look right but are wrong
- Round incorrectly
- Misread the colorbar scale
- Hallucinate values entirely

---

## What the Data Integrity Agent Does

**It's a fact-checker that verifies EVERY number**

Think of it like this:
- Claude is a smart assistant who describes what they see
- Data Integrity Agent is the calculator that checks Claude's math

---

## How It Works - Step by Step

### Example 1: Catching Hallucinated Statistics

**Step 1: User asks a question**
```
You: "What's the maximum amplitude in inline 55000?"
```

**Step 2: Claude (WITHOUT Data Integrity Agent) might say:**
```
Claude: "Looking at the image, the maximum amplitude appears to be
         around 2500 based on the color scale"
```
❌ **Problem:** Claude guessed "2500" from the image!

---

**Step 2b: Claude (WITH Data Integrity Agent):**
```
Claude's internal thought:
"I need to get the actual statistics, not guess from the image"

→ Claude calls: get_survey_metadata(inline=55000)

Tool returns:
{
  "statistics": {
    "min": -1247.3,
    "max": 2487.3,    ← ACTUAL VALUE from the data
    "mean": 12.4,
    "std": 487.2
  }
}

Claude responds:
"The maximum amplitude in inline 55000 is 2487.3"
```
✅ **Solution:** Claude uses the actual computed value!

---

### Example 2: User Makes a Claim (Agent Validates It)

**Scenario:** You or Claude makes a statement about the data

**Step 1: Claude (or you) makes a claim**
```
Claude: "I analyzed the section and found:
  - Maximum amplitude: 2500
  - Mean amplitude: 145
  - Standard deviation: 490"
```

**Step 2: Data Integrity Agent validates the claim**
```python
# Agent calls validate_extracted_statistics
validate_extracted_statistics(
    survey_id="Sepia",
    section_type="inline",
    section_number=55000,
    claimed_statistics={
        "max": 2500,
        "mean": 145,
        "std": 490
    }
)
```

**Step 3: Agent re-extracts data and computes actual values**
```python
# Behind the scenes:
data = extract_inline_data(survey_id="Sepia", inline=55000)

actual_max = np.max(data)      # Result: 2487.3
actual_mean = np.mean(data)    # Result: 12.4
actual_std = np.std(data)      # Result: 487.2
```

**Step 4: Agent compares claimed vs actual**
```
Validation Results:
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│ Metric   │ Claimed  │ Actual   │ Error    │ Verdict  │
├──────────┼──────────┼──────────┼──────────┼──────────┤
│ max      │ 2500     │ 2487.3   │ +12.7    │ ✅ PASS  │
│          │          │          │ (0.5%)   │          │
├──────────┼──────────┼──────────┼──────────┼──────────┤
│ mean     │ 145      │ 12.4     │ +132.6   │ ❌ FAIL  │
│          │          │          │ (1069%)  │          │
├──────────┼──────────┼──────────┼──────────┼──────────┤
│ std      │ 490      │ 487.2    │ +2.8     │ ✅ PASS  │
│          │          │          │ (0.6%)   │          │
└──────────┴──────────┴──────────┴──────────┴──────────┘

Overall: ERRORS FOUND
        Mean value is incorrect (claimed 145, actual 12.4)
```

**Step 5: Agent corrects Claude**
```
Data Integrity Agent: "⚠️ Validation failed!

  Claimed mean amplitude of 145 is incorrect.
  Actual mean amplitude is 12.4

  Corrected statistics:
  - Maximum amplitude: 2487.3 ✓
  - Mean amplitude: 12.4 (not 145)
  - Standard deviation: 487.2 ✓"
```

---

## Real-World Example: Complete Conversation

### Without Data Integrity Agent ❌

```
You: "Analyze inline 55000 and tell me the statistics"

Claude: [looks at image]
"Based on the seismic section:
  - Maximum amplitude: approximately 2500
  - Mean amplitude: around 150
  - The data shows good quality with strong reflectors"

You: [Uses these numbers in a report]
      ↓
   WRONG NUMBERS IN REPORT!
```

---

### With Data Integrity Agent ✅

```
You: "Analyze inline 55000 and tell me the statistics"

Claude: [calls extract_inline_image tool]

Tool returns:
{
  "statistics": {
    "min": -1247.3,
    "max": 2487.3,
    "mean": 12.4,
    "median": 8.7,
    "std": 487.2
  },
  "image_data": "..."
}

Claude: "I've extracted inline 55000. Here are the actual statistics:
  - Maximum amplitude: 2487.3
  - Mean amplitude: 12.4
  - Median amplitude: 8.7
  - Standard deviation: 487.2

  The data shows strong reflectors with a good signal distribution."

You: [Uses correct numbers in report]
      ↓
   ✓ ACCURATE NUMBERS!
```

---

## Why This Matters

### Scenario: Amplitude Anomaly Detection

**Without Data Integrity Agent:**
```
Geophysicist: "Find amplitude anomalies in the Sepia survey"

Claude: [Looks at images]
"I found high amplitudes at:
  - Inline 54500, crossline 8300: amplitude ~1800
  - Inline 55200, crossline 8450: amplitude ~2100
  - Inline 56000, crossline 8200: amplitude ~1950"

Problem: All these numbers are GUESSES from looking at images!
        Claude might have invented locations or values.
```

**With Data Integrity Agent:**
```
Geophysicist: "Find amplitude anomalies in the Sepia survey"

Claude: [Calls detect_amplitude_anomalies tool]

Tool: Algorithmically scans data and finds:
  - Threshold: mean + 3*std = 1474.4
  - 23 anomalies detected above threshold

Claude: "I ran an algorithmic anomaly detector (threshold: mean + 3σ = 1474.4).
         Found 23 high-amplitude zones:

  Location 1: Inline 54523, crossline 8287
    - Max amplitude: 1847.2
    - Extent: 15 traces × 40 samples

  Location 2: Inline 55187, crossline 8423
    - Max amplitude: 2134.6
    - Extent: 22 traces × 35 samples

  [... and 21 more ...]

  All locations and values verified by algorithmic detection."

Result: Every number is COMPUTED, not guessed!
        You can verify by re-running the detection algorithm.
```

---

## Three Main Functions

### Function 1: Verify Claimed Statistics

**When:** Someone (Claude or a user) claims a statistical value

**What it does:**
1. Re-extracts the raw data
2. Re-computes the statistic using numpy
3. Compares claimed vs actual
4. Returns PASS/FAIL

**Example:**
```python
Claim: "Standard deviation is 490"
Agent: Computes np.std(data) = 487.2
Result: PASS (within 5% tolerance)
```

---

### Function 2: Verify Spatial Coordinates

**When:** Someone claims a feature is at a specific location

**What it does:**
1. Checks if coordinates are within survey bounds
2. Validates inline/crossline/sample numbers exist
3. Flags impossible locations

**Example:**
```python
Claim: "Fault at inline 55000, crossline 8250, sample 6200"
Agent checks:
  - Survey inline range: [51001, 59001] → 55000 is valid ✓
  - Survey crossline range: [8001, 8501] → 8250 is valid ✓
  - Survey sample range: [4500, 8500] → 6200 is valid ✓
Result: VALID - all coordinates in bounds
```

**Counter-example:**
```python
Claim: "Feature at inline 60000, crossline 9000"
Agent checks:
  - Survey inline range: [51001, 59001] → 60000 OUT OF BOUNDS ✗
  - Survey crossline range: [8001, 8501] → 9000 OUT OF BOUNDS ✗
Result: INVALID - coordinates outside survey
```

---

### Function 3: Check Statistical Consistency

**When:** A set of statistics is reported

**What it does:**
Checks if statistics are mathematically possible

**Example 1: Catching Impossible Stats**
```python
Claimed: {
  "min": 100,
  "max": 500,
  "mean": 600  ← IMPOSSIBLE! Mean can't be > max
}

Agent: "❌ Statistics are inconsistent!
        Mean (600) cannot be greater than max (500)"
```

**Example 2: Catching Percentile Errors**
```python
Claimed: {
  "p10": 100,
  "p50": 80,   ← IMPOSSIBLE! p50 should be > p10
  "p90": 200
}

Agent: "❌ Percentiles are not monotonically increasing!
        p50 (80) should be ≥ p10 (100)"
```

---

## Visual Analogy

Think of it like a transaction at a store:

**Without Data Integrity Agent:**
```
Cashier: "Your total is $47.32"
You: "Okay" [pays without checking]
              ↓
         Hope it's correct!
```

**With Data Integrity Agent:**
```
Cashier: "Your total is $47.32"
Receipt machine: Prints itemized receipt
You: Check each item against what you bought
     ✓ Milk: $3.99 - correct
     ✓ Bread: $2.49 - correct
     ✗ "Premium steak": $35.00 - WAIT, I didn't buy steak!
              ↓
     "Excuse me, there's an error..."
```

The Data Integrity Agent is like the receipt machine + your checking - it provides an independent verification of every claim.

---

## When Does It Run?

### Automatic Mode (Recommended)

Every time data is extracted, statistics are automatically computed:

```python
# User calls:
extract_inline_image(survey_id="Sepia", inline=55000)

# Returns:
{
  "image_data": "...",
  "statistics": {        ← Always included!
    "min": -1247.3,
    "max": 2487.3,
    "mean": 12.4,
    ...
  },
  "provenance": {        ← Always tracked!
    "extraction_time": "2025-11-01T12:00:00Z",
    "data_hash": "sha256:abc123..."
  }
}
```

This way, Claude ALWAYS has the correct values available.

---

### On-Demand Mode

User explicitly asks to validate a claim:

```
You: "Claude said the max amplitude is 2500. Verify this."

→ Calls validate_extracted_statistics(claimed={"max": 2500})

→ Returns: "PASS - max is actually 2487.3 (0.5% error, within tolerance)"
```

---

## Benefits

### 1. Trust
"I can trust every number Claude gives me because they're computed, not guessed"

### 2. Reproducibility
"I can re-run the extraction and get the exact same statistics"

### 3. Audit Trail
"I know exactly when and how each value was computed"

### 4. Error Detection
"If Claude makes a mistake, it gets caught immediately"

### 5. No Hallucination
"Claude can't invent numbers - they must come from actual data"

---

## Comparison Table

| Aspect | Without Agent | With Agent |
|--------|--------------|------------|
| **Statistics Source** | Claude guesses from image | Computed from raw data |
| **Accuracy** | May be wrong | Mathematically correct |
| **Verification** | Can't verify | Every value verifiable |
| **Trust** | Have to trust Claude | Trust computation |
| **Hallucination Risk** | HIGH | ZERO |
| **Reproducibility** | No | Yes (includes hash) |
| **Audit Trail** | No | Full provenance |

---

## Summary in One Sentence

**The Data Integrity Agent ensures that every number Claude mentions comes from actual computation on the real data, not from guessing or hallucination.**

---

## Simple Mental Model

```
┌─────────────────────────────────────────────────────┐
│  Claude = Smart person who can describe things      │
│  Agent  = Calculator that provides exact numbers    │
│                                                      │
│  Without Agent: Claude guesses numbers from images  │
│  With Agent: Claude uses calculator for all numbers │
└─────────────────────────────────────────────────────┘
```

**Rule:** Claude should NEVER do math in its head when the calculator (Agent) is available!

---

## FAQ

### Q: Does this slow down responses?

**A:** Slightly, but it's worth it:
- Computing statistics adds ~50-100ms
- Prevents hours of work based on wrong numbers

### Q: What if Claude ignores the agent?

**A:** That's why tool descriptions are critical:
```python
description="""
⚠️ IMPORTANT: Always use the statistics provided by this tool.
NEVER estimate statistics from the image alone.
"""
```

### Q: Can users bypass the agent?

**A:** Yes, but they'll be working with unverified numbers.
We can add warnings if statistics aren't validated.

### Q: What's the tolerance for "passing" validation?

**A:** Default is ±5%, but it's configurable:
- ±5% for most statistics
- ±1% for critical values
- Exact match for counts (number of traces, etc.)

---

## Next Steps

Want me to:
1. Create a simpler diagram showing the flow?
2. Show you a real example with actual VDS data?
3. Explain how this integrates with the Quality Assessment Agent?
