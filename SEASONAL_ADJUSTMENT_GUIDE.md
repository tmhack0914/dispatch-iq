# 🌍 Seasonal Adjustment Guide for dispatch_agent.py

**Last Updated:** 2025-11-20  
**Feature Status:** ✅ IMPLEMENTED & TESTED

---

## 📋 Table of Contents
1. [Overview](#overview)
2. [Configuration Strategies](#configuration-strategies)
3. [Time-Based Adjustment](#time-based-adjustment)
4. [Demand-Based Adjustment](#demand-based-adjustment)
5. [Availability-Based Adjustment](#availability-based-adjustment)
6. [Manual Override](#manual-override)
7. [Testing & Examples](#testing--examples)
8. [Best Practices](#best-practices)

---

## 🎯 Overview

The **Seasonal Adjustment** feature automatically adjusts dispatch assignment thresholds based on:
- Time of day (morning/afternoon/evening)
- Month of year (peak season/normal/low season)
- Dispatch demand levels
- Technician availability

This ensures optimal performance across different operational contexts without manual intervention.

---

## ⚙️ Quick Start

### **Enable Seasonal Adjustment:**

```python
# In dispatch_agent.py (lines 158-172)

ENABLE_SEASONAL_ADJUSTMENT = True  # ✅ Enable dynamic thresholds

SEASONAL_STRATEGY = "auto"  # Recommended for most operations
# Options:
#   - "auto"               → Time-based (time of day + month)
#   - "time_based"         → Explicit time-based only
#   - "demand_based"       → Based on dispatch volume
#   - "availability_based" → Based on technician availability
#   - "manual"             → Manual override

MANUAL_SEASON = "normal"  # Only used if strategy="manual"
```

---

## 📊 Configuration Strategies

### **1. AUTO Strategy (Recommended)** ⭐

**What it does:**
- Checks time of day first (morning/afternoon/evening)
- Falls back to month-based season (peak/normal/low)
- Default configuration for most operations

**When to use:**
- ✅ General year-round operations
- ✅ Want automatic optimization
- ✅ Don't have real-time demand data

**Example:**
```python
SEASONAL_STRATEGY = "auto"
```

**Behavior:**
```
Current time: 3:00 PM (15:00)
→ Detected: Afternoon
→ Applied: Balanced (MIN=0.27, MAX=1.12)
→ Reason: "Balanced approach"

Current time: 8:00 AM (08:00), Month: December
→ Detected: Morning
→ Applied: Selective (MIN=0.30, MAX=1.10)
→ Reason: "Be selective early - plenty of time"
```

---

### **2. TIME_BASED Strategy**

**What it does:**
- Strictly follows time-of-day and month rules
- Three time blocks: morning, afternoon, evening
- Three seasonal blocks: peak, normal, low

**When to use:**
- ✅ Operations with clear daily patterns
- ✅ Seasonal variations are predictable
- ✅ Want consistent behavior by time

**Configuration:**

```python
SEASONAL_STRATEGY = "time_based"

# Time-of-Day Blocks (automatically applied):
Morning   (6 AM - 12 PM):  MIN=0.30, MAX=1.10  # Be selective
Afternoon (12 PM - 5 PM):  MIN=0.27, MAX=1.12  # Balanced
Evening   (5 PM - 10 PM):  MIN=0.25, MAX=1.15  # Flexible

# Month-Based Seasons (if no time match):
Peak Season (Nov-Dec):     MIN=0.25, MAX=1.15  # Max coverage
Normal (Mar-Oct):          MIN=0.27, MAX=1.12  # Balanced
Low Season (Jan-Feb):      MIN=0.30, MAX=1.10  # Sustainability
```

**Example Scenario:**
```
December 15, 2:30 PM
→ Time: Afternoon → MIN=0.27, MAX=1.12
→ (Month rule ignored - time takes precedence)

December 15, 11:00 PM (outside defined hours)
→ Time: No match → Check month
→ Month: December (Peak) → MIN=0.25, MAX=1.15
```

---

### **3. DEMAND_BASED Strategy**

**What it does:**
- Adjusts based on current dispatch volume
- Compares to historical average
- Three levels: high, normal, low demand

**When to use:**
- ✅ Have real-time dispatch count data
- ✅ Demand varies unpredictably
- ✅ Want to respond to surges/lulls

**Configuration:**

```python
SEASONAL_STRATEGY = "demand_based"

# Requires passing dispatch_count:
apply_seasonal_adjustment(
    enable=True,
    strategy="demand_based",
    dispatch_count=750  # Today's dispatch count
)

# Thresholds (automatically applied):
High Demand (>150% avg):   MIN=0.25, MAX=1.20  # Very flexible
Normal (80-150% avg):      MIN=0.27, MAX=1.12  # Balanced
Low Demand (<80% avg):     MIN=0.30, MAX=1.10  # Selective
```

**Example:**
```
Average daily dispatches: 500
Today's dispatches: 800 (160% of average)
→ Detected: High Demand
→ Applied: MIN=0.25, MAX=1.20
→ Reason: "High demand - be flexible"

Today's dispatches: 350 (70% of average)
→ Detected: Low Demand
→ Applied: MIN=0.30, MAX=1.10
→ Reason: "Low demand - be selective"
```

---

### **4. AVAILABILITY_BASED Strategy**

**What it does:**
- Adjusts based on available technician count
- More available = more selective
- Fewer available = more flexible

**When to use:**
- ✅ Have real-time technician availability data
- ✅ Availability varies significantly
- ✅ Want to optimize based on capacity

**Configuration:**

```python
SEASONAL_STRATEGY = "availability_based"

# Requires passing available_tech_count:
apply_seasonal_adjustment(
    enable=True,
    strategy="availability_based",
    available_tech_count=35  # Available technicians today
)

# Thresholds (automatically applied):
High Availability (>50):   MIN=0.35, MAX=1.00  # Very selective
Normal (20-50):            MIN=0.27, MAX=1.12  # Balanced
Low Availability (<20):    MIN=0.20, MAX=1.20  # Very flexible
```

**Example:**
```
Available technicians: 65
→ Detected: High Availability
→ Applied: MIN=0.35, MAX=1.00
→ Reason: "Many techs available - be very selective"

Available technicians: 12
→ Detected: Low Availability
→ Applied: MIN=0.20, MAX=1.20
→ Reason: "Few techs available - be flexible"
```

---

### **5. MANUAL Strategy**

**What it does:**
- Lets you manually select configuration
- No automatic detection
- Useful for testing or special events

**When to use:**
- ✅ Testing different configurations
- ✅ Special events (e.g., disaster response)
- ✅ Override automatic logic

**Configuration:**

```python
SEASONAL_STRATEGY = "manual"
MANUAL_SEASON = "peak"  # or "normal" or "low"
```

**Options:**
```
"peak"   → MIN=0.25, MAX=1.15  (Maximize coverage)
"normal" → MIN=0.27, MAX=1.12  (Balanced)
"low"    → MIN=0.30, MAX=1.10  (Sustainability focus)
```

---

## 🕐 Time-Based Adjustment Details

### **Daily Time Blocks:**

| Time Block | Hours | Thresholds | Rationale |
|------------|-------|------------|-----------|
| **Morning** | 6 AM - 12 PM | MIN=0.30, MAX=1.10 | Be selective early - plenty of time to find optimal matches |
| **Afternoon** | 12 PM - 5 PM | MIN=0.27, MAX=1.12 | Balanced - normal operations |
| **Evening** | 5 PM - 10 PM | MIN=0.25, MAX=1.15 | Be flexible - time running out, need coverage |

### **Annual Seasonal Blocks:**

| Season | Months | Thresholds | Rationale |
|--------|--------|------------|-----------|
| **Peak** | Nov-Dec | MIN=0.25, MAX=1.15 | Holidays, high demand - maximize coverage |
| **Normal** | Mar-Oct | MIN=0.27, MAX=1.12 | Standard operations - balanced approach |
| **Low** | Jan-Feb | MIN=0.30, MAX=1.10 | Post-holiday lull - focus on sustainability |

### **Customizing Time Blocks:**

```python
# Edit SEASONAL_CONFIGS in dispatch_agent.py:

SEASONAL_CONFIGS = {
    'morning': {
        'name': 'Morning (Selective)',
        'min_success_threshold': 0.30,
        'max_capacity_ratio': 1.10,
        'hours': list(range(6, 12)),  # ← Change these
        # ...
    },
    # Add custom blocks:
    'late_night': {
        'name': 'Late Night (Emergency Only)',
        'min_success_threshold': 0.20,
        'max_capacity_ratio': 1.30,
        'hours': list(range(22, 24)) + list(range(0, 6)),
        # ...
    }
}
```

---

## 📈 Demand-Based Adjustment Details

### **How It Works:**

1. **Calculate demand ratio:**
   ```python
   demand_ratio = today_dispatches / average_daily_dispatches
   ```

2. **Apply thresholds:**
   ```
   demand_ratio > 1.5  → High Demand    (MIN=0.25, MAX=1.20)
   0.8 <= ratio <= 1.5 → Normal Demand  (MIN=0.27, MAX=1.12)
   demand_ratio < 0.8  → Low Demand     (MIN=0.30, MAX=1.10)
   ```

### **Setting Average Baseline:**

```python
# In dispatch_agent.py, determine_season() function:
average_daily_dispatches = 500  # ← Update based on your operation

# Or calculate dynamically:
average_daily_dispatches = history['Dispatch_id'].nunique() / 30  # Last 30 days
```

### **Usage Example:**

```python
# When calling from another script:
from dispatch_agent import apply_seasonal_adjustment

min_thresh, max_cap, season, desc = apply_seasonal_adjustment(
    enable=True,
    strategy="demand_based",
    dispatch_count=len(current_dispatches)  # Pass actual count
)
```

---

## 👥 Availability-Based Adjustment Details

### **How It Works:**

1. **Count available technicians:**
   ```python
   available_techs = len(calendar[calendar['Available'] == True])
   ```

2. **Apply thresholds:**
   ```
   available > 50  → High Availability   (MIN=0.35, MAX=1.00)
   20 <= avail <= 50 → Normal            (MIN=0.27, MAX=1.12)
   available < 20  → Low Availability    (MIN=0.20, MAX=1.20)
   ```

### **Integration Example:**

```python
# In your main script:
available_count = calendar[
    (calendar['Date'] == today) & 
    (calendar['Available'] == True)
].shape[0]

apply_seasonal_adjustment(
    enable=True,
    strategy="availability_based",
    available_tech_count=available_count
)
```

---

## 🧪 Testing & Examples

### **Test 1: Morning Selectivity**

```bash
# Run at 9 AM:
$ python dispatch_agent.py

Output:
================================================================================
🌍 SEASONAL ADJUSTMENT APPLIED
================================================================================
   Strategy:       AUTO
   Season:         Morning (Selective) (morning)
   Description:    Be selective early - plenty of time
   MIN Threshold:  0.30 (was 0.27)
   MAX Capacity:   1.10 (was 1.12)
================================================================================
```

### **Test 2: Manual Override**

```python
# In dispatch_agent.py:
SEASONAL_STRATEGY = "manual"
MANUAL_SEASON = "peak"

$ python dispatch_agent.py

Output:
================================================================================
🌍 SEASONAL ADJUSTMENT APPLIED
================================================================================
   Strategy:       MANUAL
   Season:         Peak Season (peak)
   Description:    Maximize coverage - holidays, high demand
   MIN Threshold:  0.25 (was 0.27)
   MAX Capacity:   1.15 (was 1.12)
================================================================================
```

### **Test 3: High Demand**

```python
# Call programmatically:
apply_seasonal_adjustment(
    enable=True,
    strategy="demand_based",
    dispatch_count=850  # 170% of 500 average
)

Output:
   Season:         High Demand (high_demand)
   Description:    High demand - be flexible
   MIN Threshold:  0.25
   MAX Capacity:   1.20
```

---

## 📊 Performance Impact by Configuration

Based on our testing:

| Configuration | Assignment Rate | Techs Over 80% | Distance Saved | Use Case |
|---------------|----------------|----------------|----------------|----------|
| **Morning (0.30/1.10)** | ~74% | 206 | 9,183 km | Early day - be selective |
| **Afternoon (0.27/1.12)** | ~76% | 209 | 9,028 km | Normal ops - balanced |
| **Evening (0.25/1.15)** | ~83% | 259 | 8,049 km | Late day - maximize coverage |
| **Peak (0.25/1.15)** | ~83% | 259 | 8,049 km | Holidays - coverage priority |
| **Normal (0.27/1.12)** | ~76% | 209 | 9,028 km | Year-round - balanced |
| **Low (0.30/1.10)** | ~74% | 206 | 9,183 km | Post-holiday - sustainability |

---

## 🎯 Best Practices

### **1. Start with AUTO Strategy**
```python
ENABLE_SEASONAL_ADJUSTMENT = True
SEASONAL_STRATEGY = "auto"
```
- Easiest to implement
- Works well for most operations
- No additional data required

### **2. Monitor for 2 Weeks**
- Track assignment rates by time/season
- Monitor technician feedback
- Compare to expected patterns

### **3. Customize if Needed**
```python
# If morning too strict:
SEASONAL_CONFIGS['morning']['min_success_threshold'] = 0.28  # Less strict

# If evenings not flexible enough:
SEASONAL_CONFIGS['evening']['max_capacity_ratio'] = 1.18  # More flex
```

### **4. Consider Hybrid Approaches**
```python
# Use time-based weekdays, manual override weekends:
if datetime.datetime.now().weekday() >= 5:  # Weekend
    SEASONAL_STRATEGY = "manual"
    MANUAL_SEASON = "peak"  # More flexible on weekends
else:
    SEASONAL_STRATEGY = "auto"
```

### **5. Document Your Settings**
```python
# Add comments explaining your choices:
SEASONAL_CONFIGS['peak'] = {
    'months': [11, 12],  # Nov-Dec based on 2024 data showing 40% increase
    'min_success_threshold': 0.25,  # Relaxed to handle volume
    # ...
}
```

---

## ⚠️ Troubleshooting

### **Issue: Adjustments Not Applied**

**Check:**
1. `ENABLE_SEASONAL_ADJUSTMENT = True`?
2. Is `apply_seasonal_adjustment()` called before assignment logic?
3. Check console output for seasonal adjustment banner

### **Issue: Wrong Configuration Applied**

**Debug:**
```python
# Add debug prints in determine_season():
print(f"Current hour: {current_hour}")
print(f"Current month: {current_month}")
print(f"Checking configs: {SEASONAL_CONFIGS.keys()}")
```

### **Issue: Demand/Availability Strategy Not Working**

**Check:**
- Are you passing `dispatch_count` or `available_tech_count`?
- Is the baseline average correct?
- Add debug: `print(f"Demand ratio: {demand_ratio}")`

---

## 🚀 Advanced: Dynamic Baseline Calculation

Instead of hardcoding averages, calculate dynamically:

```python
def calculate_average_dispatches(history_df, lookback_days=30):
    """Calculate rolling average dispatch count."""
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=lookback_days)
    recent = history_df[history_df['Appointment_start_time'] >= cutoff_date]
    
    if len(recent) == 0:
        return 500  # Fallback default
    
    unique_days = recent['Appointment_start_time'].dt.date.nunique()
    total_dispatches = len(recent)
    
    return total_dispatches / unique_days if unique_days > 0 else 500

# Use it:
avg_dispatches = calculate_average_dispatches(dispatch_history)
```

---

## 📝 Configuration Template

Copy and customize:

```python
# ============================================================
# SEASONAL ADJUSTMENT CONFIGURATION
# ============================================================

# Enable feature
ENABLE_SEASONAL_ADJUSTMENT = True

# Choose strategy
SEASONAL_STRATEGY = "auto"  # auto | manual | time_based | demand_based | availability_based

# Manual override (if using manual strategy)
MANUAL_SEASON = "normal"  # peak | normal | low

# Customize time blocks (optional)
SEASONAL_CONFIGS['morning']['min_success_threshold'] = 0.30  # Your value
SEASONAL_CONFIGS['afternoon']['max_capacity_ratio'] = 1.12   # Your value
SEASONAL_CONFIGS['evening']['min_success_threshold'] = 0.25  # Your value

# Customize seasonal months (optional)
SEASONAL_CONFIGS['peak']['months'] = [11, 12]      # Nov-Dec
SEASONAL_CONFIGS['normal']['months'] = [3,4,5,6,7,8,9,10]  # Mar-Oct
SEASONAL_CONFIGS['low']['months'] = [1, 2]         # Jan-Feb

# Set demand baseline (if using demand_based)
AVERAGE_DAILY_DISPATCHES = 500  # Update based on your operation

# Set availability thresholds (if using availability_based)
HIGH_AVAILABILITY_THRESHOLD = 50  # Techs
LOW_AVAILABILITY_THRESHOLD = 20   # Techs
```

---

## 🎓 Summary

**Seasonal Adjustment provides:**
- ✅ Automatic threshold optimization
- ✅ Time-aware configurations
- ✅ Demand-responsive adjustments
- ✅ Availability-based flexibility
- ✅ Manual override capability

**Recommended Setup:**
```python
ENABLE_SEASONAL_ADJUSTMENT = True
SEASONAL_STRATEGY = "auto"
# → Automatically adjusts by time of day and month
# → No additional configuration needed
# → Works great for most operations!
```

---

**For questions or customization help, refer to:**
- THREE_WAY_COMPARISON.md - Performance by configuration
- ML_TUNING_GUIDE.md - Threshold tuning guidance
- TUNING_EXPERIMENT_RESULTS.md - Experimental evidence


