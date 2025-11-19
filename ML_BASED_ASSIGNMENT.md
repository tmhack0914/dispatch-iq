# ML-BASED ASSIGNMENT SYSTEM

## Overview

The ML-Based Assignment System **removes all hard-coded fallback levels** and instead uses the **trained machine learning model to evaluate ALL available technicians** directly. This approach is more data-driven, simpler, and aligns with the core business principles.

---

## Key Changes

### ❌ REMOVED: Hard-Coded Fallback Levels

Previously, the system used 4 manually defined fallback levels with hard-coded confidence multipliers:

```
Level 1: Exact skill match (multiplier: 1.0)
Level 2: Same category (multiplier: 0.85)
Level 3: Related category (multiplier: 0.70)
Level 4: Any skill (multiplier: 0.50)
```

**Problem**: These multipliers were arbitrary and didn't reflect actual historical performance.

### ✅ NEW: ML-Based Evaluation

Now, the system:

1. **Gets ALL available technicians** in the city (regardless of skill)
2. **Uses the ML model to predict success probability** for each technician
3. **Filters by minimum threshold** (default: 25% success probability)
4. **Sorts by success probability** (highest first)
5. **Assigns the best technician**

---

## How It Works

### 1. ML Model Evaluation

For each available technician, the model considers:

- ✅ **Distance** (shorter = better performance)
- ✅ **Workload** (lower = better performance)
- ✅ **Skill match** (better = better performance)
- ✅ **Temporal factors** (time of day, day of week)
- ✅ **Technician performance history** (if tracking enabled)
- ✅ **Service tier & equipment** (job complexity factors)

### 2. Success Probability Threshold

The model only considers technicians with predicted success probability ≥ **25%** (configurable via `MIN_SUCCESS_THRESHOLD`).

This ensures:
- Poor matches are automatically filtered out
- No manual fallback level configuration needed
- Data-driven decision making

### 3. Capacity Management

Allows up to **115% capacity** (configurable via `MAX_CAPACITY_RATIO`) to handle peak demand while respecting technician workload limits.

---

## Business Rule Alignment

The ML model **automatically learns** the three core business principles:

### ✅ Principle 1: Shorter Distance = Better Performance
The model learns that technicians closer to the job site have higher success rates.

### ✅ Principle 2: Lower Workload = Better Performance
The model learns that technicians with lighter workloads perform better.

### ✅ Principle 3: Better Skill Match = Better Performance
The model learns that exact skill matches lead to higher success rates.

**Validation**: The system explicitly tests these principles after training to ensure the model learned correctly.

---

## Configuration

### Enable ML-Based Assignment

```python
USE_ML_BASED_ASSIGNMENT = True  # Enable ML-based assignment
MIN_SUCCESS_THRESHOLD = 0.25    # Minimum 25% success probability
MAX_CAPACITY_RATIO = 1.15       # Allow up to 115% capacity
```

### Revert to Legacy Mode (Not Recommended)

```python
USE_ML_BASED_ASSIGNMENT = False  # Use old cascading fallback system
```

---

## Benefits

### 🎯 Data-Driven Decisions
- No more arbitrary confidence multipliers
- Model learns from actual historical performance
- Automatically adapts to changing patterns

### 🧠 Simpler Logic
- Removed complex cascading fallback code
- Single evaluation pass for all technicians
- Easier to understand and maintain

### 📈 Better Performance
- Model considers ALL factors simultaneously
- Optimal weighting learned from data
- Respects all three business principles

### 🔄 Flexible Matching
- Can assign any technician if success probability is high enough
- Automatically handles skill versatility
- No artificial restrictions on technician selection

---

## Example Scenarios

### Scenario 1: Perfect Match Available
**Technician A**: Exact skill match, 5km away, 60% workload
→ **Success Probability: 92%** ✅ Assigned

### Scenario 2: Cross-Skill Assignment
**Technician B**: Different skill, 3km away, 40% workload
→ **Success Probability: 68%** ✅ Assigned (better than exact match far away)

**Technician C**: Exact skill match, 50km away, 95% workload
→ **Success Probability: 45%** ❌ Not assigned (ML model predicted poor outcome)

### Scenario 3: No Good Options
**All Technicians**: Success probability < 25%
→ **No Assignment** (better than forcing a poor assignment)

---

## Comparison: ML-Based vs Legacy

| Aspect | ML-Based | Legacy Fallback |
|--------|----------|-----------------|
| **Skill Matching** | Learned from data | Hard-coded levels |
| **Distance** | ML-weighted | Manual formula |
| **Workload** | ML-weighted | Manual formula |
| **Confidence Multipliers** | Not needed | Hard-coded (1.0, 0.85, 0.70, 0.50) |
| **Technician Evaluation** | All at once | Sequential fallback |
| **Flexibility** | High (any tech if good probability) | Limited (strict levels) |
| **Adaptability** | Learns from new data | Static rules |
| **Complexity** | Low (single pass) | High (4 levels, categories) |

---

## Technical Details

### New Function: `get_all_available_techs_ml()`

```python
def get_all_available_techs_ml(dispatch_date, city, max_capacity_ratio=1.15):
    """
    Return ALL available technicians in the city, regardless of skill.
    The ML model evaluates each technician's suitability.
    """
    # Filter by: availability, city, capacity
    # No skill filtering - ML model handles skill match evaluation
```

### Modified Function: `assign_technician()`

```python
if USE_ML_BASED_ASSIGNMENT:
    # Get ALL available technicians
    candidates = get_all_available_techs_ml(dispatch_date, city, MAX_CAPACITY_RATIO)
    
    # ML model predicts success for each
    candidates['success_prob'] = candidates.apply(calc_candidate_success, axis=1)
    
    # Filter by minimum threshold
    candidates = candidates[candidates['success_prob'] >= MIN_SUCCESS_THRESHOLD]
    
    # Sort by success probability and pick best
    best_technician = candidates.sort_values('success_prob', ascending=False).iloc[0]
```

---

## Performance Metrics

When running with ML-Based Assignment enabled, the output shows:

```
================================================================================
   ASSIGNMENT MODE
================================================================================
   Mode:                       🤖 ML-BASED ASSIGNMENT
   - Strategy:                 Evaluate ALL available technicians using ML model
   - Min success threshold:    25.0%
   - Max capacity ratio:       115%
   - Scoring:                  Pure ML success probability
   - No hard-coded fallback levels (model learns from data)
```

---

## Validation

The system validates that the ML model learned the core business principles:

```
🔍 Validating model learned core business principles...
   Testing: 1) Shorter distance = better  2) Lower workload = better  3) Better skill match = better

   ✓ Principle 1 (Distance):    Near (5km: 0.782) vs Far (40km: 0.623) → True
   ✓ Principle 2 (Workload):    Light (20%: 0.745) vs Busy (95%: 0.651) → True
   ✓ Principle 3 (Skill Match): Good (100%: 0.798) vs Poor (30%: 0.582) → True

   ✅ SUCCESS: All 3 business principles validated!
      Model correctly learned that shorter distance, lower workload, and better skill match = better performance
```

---

## Migration Guide

If you were using the legacy cascading fallback system:

### Step 1: Review Current Performance
Run the model once in legacy mode (`USE_ML_BASED_ASSIGNMENT = False`) to establish baseline metrics.

### Step 2: Enable ML-Based Assignment
Set `USE_ML_BASED_ASSIGNMENT = True` in `dispatch_agent.py`.

### Step 3: Adjust Threshold if Needed
If too many assignments are rejected:
- Lower `MIN_SUCCESS_THRESHOLD` (e.g., from 0.25 to 0.20)

If assignment quality is poor:
- Raise `MIN_SUCCESS_THRESHOLD` (e.g., from 0.25 to 0.30)

### Step 4: Monitor Performance
Compare optimized assignment metrics:
- Average success probability
- Average confidence
- Average distance
- Unassigned rate

---

## Troubleshooting

### Too Many Unassigned Dispatches

**Solution 1**: Lower the threshold
```python
MIN_SUCCESS_THRESHOLD = 0.20  # From default 0.25
```

**Solution 2**: Increase capacity allowance
```python
MAX_CAPACITY_RATIO = 1.20  # From default 1.15
```

### Poor Assignment Quality

**Solution**: Increase the threshold
```python
MIN_SUCCESS_THRESHOLD = 0.30  # From default 0.25
```

### Model Not Learning Business Principles

**Check**:
1. Training data quality - ensure it has examples demonstrating the principles
2. Sufficient data volume - need 100+ historical assignments
3. Feature availability - distance, workload, and skill match must be present

---

## Future Enhancements

1. **Dynamic Threshold**: Adjust `MIN_SUCCESS_THRESHOLD` based on current demand
2. **Multi-Objective Optimization**: Balance success probability with cost/distance
3. **Real-Time Learning**: Update model as new assignments complete
4. **Skill Transfer Learning**: Identify which skills are more versatile

---

## Summary

✅ **Removed**: Hard-coded fallback levels and confidence multipliers  
✅ **Added**: ML-based evaluation of all available technicians  
✅ **Result**: Simpler, more data-driven, and more effective assignment system  

The ML model automatically learns what makes a successful assignment and applies that knowledge to evaluate all technicians fairly and consistently.

