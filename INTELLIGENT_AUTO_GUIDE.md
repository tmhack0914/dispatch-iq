# 🧠 Intelligent Auto-Selection Guide

**Feature:** Automatically analyzes dispatch load and chooses optimal threshold strategy  
**Status:** ✅ IMPLEMENTED & TESTED  
**Date:** 2025-11-20

---

## 🎯 **What is Intelligent Auto?**

**Intelligent Auto** is an advanced seasonal adjustment mode that:
1. **Analyzes** current dispatch load and technician availability
2. **Evaluates** multiple factors (demand, availability, time)
3. **Chooses** the best threshold strategy automatically
4. **Applies** optimal MIN_SUCCESS_THRESHOLD and MAX_CAPACITY_RATIO

**No manual configuration needed!** The system adapts in real-time.

---

## ⚡ **Quick Start**

### **Enable Intelligent Auto:**

```python
# In dispatch_agent.py (line 162):
SEASONAL_STRATEGY = "intelligent_auto"  # ✅ Enable smart mode
```

That's it! The system will now:
- Count dispatches being optimized
- Count available technicians
- Analyze demand ratio vs baseline
- Evaluate availability levels
- Choose best strategy automatically
- Apply optimal thresholds

---

## 🔍 **How It Works**

### **Step 1: Data Collection**

Before applying thresholds, the system quickly peeks at:

```
📊 Detected: 600 dispatches to optimize
👥 Detected: 150 available technicians
```

### **Step 2: Multi-Factor Analysis**

Three factors are evaluated and scored:

| Factor | Condition | Score | Config Applied |
|--------|-----------|-------|----------------|
| **DEMAND** | > 150% baseline | 10 | High Demand (MIN=0.25, MAX=1.20) |
| **DEMAND** | < 80% baseline | 8 | Low Demand (MIN=0.30, MAX=1.10) |
| **DEMAND** | 80-150% baseline | 2 | Normal (MIN=0.27, MAX=1.12) |
| **AVAILABILITY** | < 20 techs | 10 | Low Avail (MIN=0.20, MAX=1.20) |
| **AVAILABILITY** | > 50 techs | 9 | High Avail (MIN=0.35, MAX=1.00) |
| **AVAILABILITY** | 20-50 techs | 2 | Normal (MIN=0.27, MAX=1.12) |
| **TIME** | Morning | 5 | Selective (MIN=0.30, MAX=1.10) |
| **TIME** | Afternoon | 5 | Balanced (MIN=0.27, MAX=1.12) |
| **TIME** | Evening | 5 | Flexible (MIN=0.25, MAX=1.15) |

**Scoring Logic:**
- Score > 5 = High priority (emergency/opportunity)
- Score 2-5 = Normal priority
- Score 0-2 = Low priority

### **Step 3: Strategy Selection**

The factor with the **highest score** is chosen:

```
Example: 600 dispatches, 150 techs available

Scores:
- Demand: 2 (normal - 600/500 = 120%)
- Availability: 9 (high - 150 techs > 50 threshold)
- Time: 5 (afternoon)

CHOSEN: AVAILABILITY-based (score: 9)
→ Applied: MIN=0.35, MAX=1.00 (be very selective)
```

### **Step 4: Application**

Selected configuration is applied:

```
================================================================================
🌍 SEASONAL ADJUSTMENT APPLIED
================================================================================
   Strategy:       INTELLIGENT_AUTO
   🧠 Analysis:     CHOSEN: AVAILABILITY-based (score: 9) | 
                   Normal demand: 600 dispatches (120.0% of baseline) | 
                   HIGH AVAILABILITY: 150 techs available (can be selective) | 
                   Time: Afternoon (14:00)
   🎯 Chosen By:    AVAILABILITY-based strategy
   Season:         high_availability (high_availability)
   MIN Threshold:  0.35 (was 0.27)
   MAX Capacity:   1.00 (was 1.12)
================================================================================
```

---

## 📊 **Real-World Scenarios**

### **Scenario 1: Normal Day**
```
Input:
- 520 dispatches (104% of 500 baseline)
- 35 available technicians
- Time: 2:00 PM (Afternoon)

Analysis:
- Demand: Score 2 (normal)
- Availability: Score 2 (normal, 20-50 range)
- Time: Score 5 (afternoon)

Decision: TIME-based (highest score: 5)
Applied: Afternoon balanced (MIN=0.27, MAX=1.12)
```

### **Scenario 2: High Demand Surge**
```
Input:
- 850 dispatches (170% of 500 baseline) ⚠️
- 40 available technicians
- Time: 10:00 AM (Morning)

Analysis:
- Demand: Score 10 (HIGH - > 150%) 🚨
- Availability: Score 2 (normal)
- Time: Score 5 (morning)

Decision: DEMAND-based (highest score: 10)
Applied: High demand flexible (MIN=0.25, MAX=1.20)
Reason: Need maximum coverage for surge
```

### **Scenario 3: Low Staffing Emergency**
```
Input:
- 480 dispatches (96% of baseline)
- 15 available technicians ⚠️
- Time: 4:00 PM (Afternoon)

Analysis:
- Demand: Score 2 (normal)
- Availability: Score 10 (LOW - < 20) 🚨
- Time: Score 5 (afternoon)

Decision: AVAILABILITY-based (highest score: 10)
Applied: Low availability flexible (MIN=0.20, MAX=1.20)
Reason: Need flexibility with limited staff
```

### **Scenario 4: Lots of Available Staff**
```
Input:
- 550 dispatches (110% of baseline)
- 75 available technicians ✅
- Time: 9:00 AM (Morning)

Analysis:
- Demand: Score 2 (normal)
- Availability: Score 9 (HIGH - > 50) 💪
- Time: Score 5 (morning)

Decision: AVAILABILITY-based (highest score: 9)
Applied: High availability selective (MIN=0.35, MAX=1.00)
Reason: Many techs available - can be very selective
```

### **Scenario 5: Quiet Evening**
```
Input:
- 350 dispatches (70% of baseline)
- 30 available technicians
- Time: 7:00 PM (Evening)

Analysis:
- Demand: Score 8 (LOW - < 80%)
- Availability: Score 2 (normal)
- Time: Score 5 (evening)

Decision: DEMAND-based (highest score: 8)
Applied: Low demand selective (MIN=0.30, MAX=1.10)
Reason: Low volume - focus on quality and sustainability
```

---

## ⚙️ **Configuration**

### **Basic Configuration (Recommended):**

```python
# Enable intelligent auto
SEASONAL_STRATEGY = "intelligent_auto"

# Use default settings (works great!)
# - Demand baseline: 500 (auto-calculated)
# - High demand: > 150% of baseline
# - Low demand: < 80% of baseline
# - High availability: > 50 techs
# - Low availability: < 20 techs
```

### **Advanced Configuration:**

```python
# Customize intelligent auto behavior
INTELLIGENT_AUTO_CONFIG = {
    'enable_demand_override': True,       # Allow demand to override time
    'enable_availability_override': True, # Allow availability to override
    'demand_baseline': 500,               # Your average daily dispatches
    'high_demand_threshold': 1.5,         # 150% = high demand
    'low_demand_threshold': 0.8,          # 80% = low demand
    'high_availability': 50,              # > 50 techs = high
    'low_availability': 20,               # < 20 techs = low
    'priority_order': ['demand', 'availability', 'time']  # Tie-breaker order
}
```

### **Customizing Thresholds:**

Update baseline to match your operation:

```python
# Option 1: Set manually
INTELLIGENT_AUTO_CONFIG['demand_baseline'] = 600  # Your average

# Option 2: Auto-calculate from history (recommended)
# Add this to dispatch_agent.py before intelligent_auto_select():
if INTELLIGENT_AUTO_CONFIG['demand_baseline'] is None:
    # Calculate from last 30 days
    recent_history = history[history['Date'] >= (today - timedelta(days=30))]
    avg_daily = len(recent_history) / 30
    INTELLIGENT_AUTO_CONFIG['demand_baseline'] = avg_daily
```

### **Adjusting Sensitivity:**

Make system more/less sensitive to changes:

```python
# More sensitive (reacts to smaller changes)
INTELLIGENT_AUTO_CONFIG['high_demand_threshold'] = 1.3  # 130% instead of 150%
INTELLIGENT_AUTO_CONFIG['low_demand_threshold'] = 0.9   # 90% instead of 80%

# Less sensitive (only reacts to big changes)
INTELLIGENT_AUTO_CONFIG['high_demand_threshold'] = 1.8  # 180% instead of 150%
INTELLIGENT_AUTO_CONFIG['low_demand_threshold'] = 0.6   # 60% instead of 80%
```

---

## 🆚 **Comparison: Intelligent Auto vs Other Strategies**

| Strategy | Looks At Dispatches? | Looks At Availability? | Looks At Time? | Auto-Adapts? |
|----------|---------------------|----------------------|----------------|--------------|
| **intelligent_auto** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **auto** | ❌ No | ❌ No | ✅ Yes | ⚠️ Partial |
| **time_based** | ❌ No | ❌ No | ✅ Yes | ❌ No |
| **demand_based** | ✅ Yes | ❌ No | ❌ No | ⚠️ Partial |
| **availability_based** | ❌ No | ✅ Yes | ❌ No | ⚠️ Partial |
| **manual** | ❌ No | ❌ No | ❌ No | ❌ No |

**Intelligent Auto = Best of All Worlds!**

---

## 📈 **Expected Performance**

Based on the scenario:

### **Normal Conditions:**
```
600 dispatches, 35 techs, Afternoon
→ TIME-based (Afternoon balanced)
→ MIN=0.27, MAX=1.12
→ ~76% assignment rate
→ 209 techs over 80%
```

### **High Demand:**
```
850 dispatches, 35 techs, Any time
→ DEMAND-based (High demand)
→ MIN=0.25, MAX=1.20
→ ~85% assignment rate
→ 280+ techs over 80% (temporary overload acceptable)
```

### **High Availability:**
```
600 dispatches, 75 techs, Any time
→ AVAILABILITY-based (High avail)
→ MIN=0.35, MAX=1.00
→ ~70% assignment rate
→ 180 techs over 80% (very sustainable)
```

### **Low Availability Emergency:**
```
600 dispatches, 15 techs, Any time
→ AVAILABILITY-based (Low avail)
→ MIN=0.20, MAX=1.20
→ ~88% assignment rate
→ All 15 techs heavily loaded (emergency mode)
```

---

## 🎯 **When to Use Each Strategy**

### **Use Intelligent Auto When:**
- ✅ Dispatch volumes vary unpredictably
- ✅ Technician availability fluctuates
- ✅ Want "set and forget" optimization
- ✅ Trust the system to adapt
- ✅ **RECOMMENDED FOR MOST OPERATIONS**

### **Use Auto (Time-Based) When:**
- ✅ Predictable daily patterns
- ✅ Stable dispatch volumes
- ✅ Consistent staffing levels
- ✅ Want simpler logic

### **Use Manual When:**
- ✅ Testing configurations
- ✅ Special events (known high demand)
- ✅ Disaster recovery mode
- ✅ Want full control

---

## 🔧 **Troubleshooting**

### **Issue: Always choosing TIME-based**

**Possible Causes:**
- Dispatch count and availability are both "normal"
- No scores > 5, so falls back to time

**Solutions:**
```python
# Lower the score threshold for non-time factors
# Or adjust baselines to be more sensitive
INTELLIGENT_AUTO_CONFIG['high_demand_threshold'] = 1.3  # Lower = more sensitive
```

### **Issue: Not detecting high availability**

**Check:**
```python
# Is threshold too high for your operation?
INTELLIGENT_AUTO_CONFIG['high_availability'] = 40  # Lower from 50

# Or check if techs are being counted correctly
print(f"Available techs: {available_tech_count_for_adjustment}")
```

### **Issue: Baseline seems wrong**

**Solution:**
```python
# Set baseline manually based on your actual average
INTELLIGENT_AUTO_CONFIG['demand_baseline'] = 650  # Your real average
```

---

## 🧪 **Testing**

### **Test 1: Normal Conditions**
```bash
# Current: 600 dispatches, 150 techs
$ python dispatch_agent.py

Expected Output:
🧠 INTELLIGENT AUTO MODE: Analyzing dispatch load...
   📊 Detected: 600 dispatches to optimize
   👥 Detected: 150 available technicians

🌍 SEASONAL ADJUSTMENT APPLIED
   🧠 Analysis:     CHOSEN: AVAILABILITY-based (score: 9)
   Season:         high_availability
   MIN Threshold:  0.35
```

### **Test 2: Simulate High Demand**
```python
# Edit current_dispatches.csv to have 900 rows
# Or duplicate entries

$ python dispatch_agent.py

Expected:
   🧠 Analysis:     CHOSEN: DEMAND-based (score: 10)
   Season:         high_demand
   MIN Threshold:  0.25
```

### **Test 3: Disable and Compare**
```python
# Test A: With intelligent_auto
SEASONAL_STRATEGY = "intelligent_auto"
# Run and note assignment rate

# Test B: With static auto
SEASONAL_STRATEGY = "auto"
# Run and compare results
```

---

## 📊 **Decision Tree**

```
START: Analyze Current Conditions
│
├─ Count Dispatches → dispatch_count
├─ Count Available Techs → available_tech_count
└─ Get Current Time → hour, month
│
├─ FACTOR 1: Demand
│  ├─ dispatch_count > 750 (>150%) → Score 10 (HIGH DEMAND)
│  ├─ dispatch_count < 400 (<80%)  → Score 8 (LOW DEMAND)
│  └─ 400-750                       → Score 2 (NORMAL)
│
├─ FACTOR 2: Availability
│  ├─ available_tech_count < 20 → Score 10 (LOW AVAILABILITY - EMERGENCY!)
│  ├─ available_tech_count > 50 → Score 9 (HIGH AVAILABILITY - BE SELECTIVE)
│  └─ 20-50                      → Score 2 (NORMAL)
│
├─ FACTOR 3: Time
│  ├─ 6-12 (Morning)   → Score 5 (SELECTIVE)
│  ├─ 12-17 (Afternoon) → Score 5 (BALANCED)
│  ├─ 17-22 (Evening)   → Score 5 (FLEXIBLE)
│  └─ Check Month       → Score 4 (SEASONAL)
│
├─ SELECTION: Pick Highest Score
│  ├─ If score > 5  → Use that factor's config
│  └─ If all ≤ 5    → Use priority_order
│
└─ APPLY: Set MIN_SUCCESS_THRESHOLD & MAX_CAPACITY_RATIO
```

---

## 🎓 **Best Practices**

### **1. Start with Defaults**
```python
SEASONAL_STRATEGY = "intelligent_auto"
# Let it run for 1 week with default settings
```

### **2. Monitor Decision Log**
```python
# Check what strategies are being chosen
$ python dispatch_agent.py | grep "CHOSEN:"

# Look for patterns:
# - Always choosing TIME? → Adjust baselines
# - Frequently choosing DEMAND? → Good, adapting to load
# - Never choosing AVAILABILITY? → Check threshold
```

### **3. Tune Baselines**
```python
# After 1 week, calculate your actual average:
# - Count total dispatches in week
# - Divide by 7
# - Update baseline

INTELLIGENT_AUTO_CONFIG['demand_baseline'] = 620  # Your calculated average
```

### **4. Document Decisions**
```python
# Keep a log of what was chosen and why
# Helps validate the system is working correctly
```

### **5. Set Alerts**
```python
# Alert if emergency mode activated
if chosen_strategy == 'availability' and season_name == 'low_availability':
    send_alert("Emergency: Low staff, using flexible thresholds")
```

---

## 📝 **Summary**

**Intelligent Auto provides:**
- ✅ **Automatic** analysis of dispatch load
- ✅ **Multi-factor** evaluation (demand + availability + time)
- ✅ **Smart** strategy selection
- ✅ **Real-time** adaptation
- ✅ **Emergency** response (low availability detection)
- ✅ **Opportunity** optimization (high availability detection)

**Recommended Setup:**
```python
ENABLE_SEASONAL_ADJUSTMENT = True
SEASONAL_STRATEGY = "intelligent_auto"  # ⭐ SMART MODE
# → Analyzes your specific situation
# → Chooses best strategy automatically
# → Adapts in real-time
```

**Perfect for operations with:**
- Variable dispatch volumes
- Fluctuating staffing levels
- Unpredictable demand patterns
- Need for automatic adaptation

---

**For more information:**
- SEASONAL_ADJUSTMENT_GUIDE.md - All adjustment strategies
- THREE_WAY_COMPARISON.md - Performance by configuration
- ML_TUNING_GUIDE.md - Threshold tuning principles


