# VolumeGPT Demo - Quick Prompt Script
## Copy-paste prompts for live demo (10-12 minutes)

---

## 🔍 PHASE 1: DATA DISCOVERY (2-3 min)

### 1️⃣ Initial Discovery
```
What VDS datasets do you have available? Give me a summary of the different regions and data types.
```

### 2️⃣ Focus on Santos Basin
```
Show me all the Santos Basin datasets. What's their coverage and quality?
```

### 3️⃣ Deep Dive on Sepia
```
Tell me more about the Sepia survey. What are the dimensions, coordinate system, and data characteristics?
```

---

## 🎯 PHASE 2: CONVERSATIONAL QC (3-4 min)

### 4️⃣ Quick QC Check (Agent Start)
```
I want to do a quick QC check on the Sepia survey. Extract 3 representative inlines: one near the start, one in the middle, and one near the end. Focus on the depth range 5500-7000m.
```

**Alternative - Crossline QC:**
```
Extract crosslines for orthogonal QC skipping 100 everytime from the Sepia survey.
```

### 5️⃣ Check Status
```
What's the status of my extraction?
```

### 6️⃣ Get Results
```
Show me the results of the QC extraction. What did you find?
```

### 7️⃣ LLM Analysis
```
Based on those extractions, do you see any data quality issues? Are there any gaps or anomalies I should be aware of?
```

---

## 🎨 PHASE 3: TARGETED ANALYSIS (3-4 min)

### 8️⃣ Zone of Interest (Complex Agent Task)
```
I'm interested in the depth zone around 6000-6500m, which might contain reservoir targets. Extract every 500th inline across the survey at this depth range so I can assess lateral continuity.
```

### 9️⃣ Monitor Progress
```
How's the extraction going? How many are done?
```

### 🔟 Pause/Resume (Optional - show control)
```
Pause the agent for a moment, I want to check something.
```
*Wait 5-10 seconds*
```
Resume the extraction.
```

### 1️⃣1️⃣ Final Analysis
```
Show me the final results. What's the overall data quality for this depth zone? Are there any interesting features?
```

---

## 📊 PHASE 4: COMPARISON (Optional, 2-3 min)

### 1️⃣2️⃣ Multi-Survey Discovery
```
Now compare this to another Santos dataset. What other surveys do we have in the same basin?
```

### 1️⃣3️⃣ Comparative Extraction
```
Extract inline 55000 from [other survey name] at the same depth range (6000-6500m) so I can compare them.
```

---

## 🎤 WRAP-UP (1 min)

### 1️⃣4️⃣ Summary & Next Steps
```
Summarize what we learned about the Sepia survey today. What would be the next steps for a full QC campaign?
```

---

## 💡 KEY TALKING POINTS (As You Wait)

While agent is running or between prompts:

**Speed:**
"Notice how fast that metadata search was - 100+ datasets queried in under 5 seconds without opening any files."

**Natural Language:**
"I didn't write any code or specify exact inline numbers - the LLM understood 'start, middle, end' contextually."

**Asynchronous:**
"The agent is working in the background. I can continue the conversation, check status, or even pause it."

**Intelligence:**
"The LLM is not just extracting data - it's analyzing quality, suggesting next steps, and providing geophysical insights."

**Traditional vs. VolumeGPT:**
- Traditional: Write Python loops, manage errors, wait for each extraction
- VolumeGPT: Natural conversation, autonomous agents, intelligent analysis

---

## ⚠️ PRE-DEMO CHECKLIST

Run before starting:
```bash
./demo-prepare.sh
```

Should see all green checkmarks:
- ✅ VPN connected
- ✅ NFS mount healthy
- ✅ Docker running
- ✅ Elasticsearch indexed
- ✅ MCP server ready

---

## 🆘 FALLBACK IF THINGS BREAK

**Agent fails?**
→ "Let me use the direct extraction tool instead" (use extract_inline)

**VDS access fails?**
→ Emphasize discovery/search capabilities, explain extraction would work with proper mount

**Elasticsearch down?**
→ Use list_surveys (slower but works)

---

## 🎯 SUCCESS METRICS

Demo worked if audience says:
- "That's so much faster than our current workflow"
- "Can it work with our Petrel projects?"
- "What's the pricing?"
- "When can we try this?"
- "How do we integrate with our OSDU platform?"
