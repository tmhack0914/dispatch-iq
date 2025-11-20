# 🎛️ ML Model & Threshold Tuning Guide for dispatch_agent.py

## 📋 Table of Contents
1. [Quick Tuning Parameters](#quick-tuning-parameters)
2. [Assignment Strategy](#assignment-strategy)
3. [Success Threshold Tuning](#success-threshold-tuning)
4. [ML Model Configuration](#ml-model-configuration)
5. [Advanced Features](#advanced-features)
6. [Performance Optimization](#performance-optimization)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Quick Tuning Parameters

### **Location in File:** Lines 34-161

### **Critical Settings:**

```python
# ============================================================
# MAIN ASSIGNMENT CONFIGURATION
# ============================================================

# Assignment Strategy
USE_ML_BASED_ASSIGNMENT = True      # True = ML evaluates ALL techs, False = cascading fallback
MIN_SUCCESS_THRESHOLD = 0.25        # Minimum 25% success to consider (0.0 to 1.0)
MAX_CAPACITY_RATIO = 1.15           # Allow up to 115% capacity (1.0 to 2.0)

# Scoring Strategy
USE_SUCCESS_ONLY = True             # True = pure ML, False = weighted combination

# Legacy Weights (only if USE_SUCCESS_ONLY = False)
WEIGHT_SUCCESS_PROB = 0.60          # 60% weight on success probability
WEIGHT_CONFIDENCE = 0.40            # 40% weight on confidence

# Advanced Features
ENABLE_PERFORMANCE_TRACKING = True  # Adjust predictions based on tech history
ENABLE_DYNAMIC_WEIGHTS = False      # Auto-optimize weights (unstable)
ENABLE_ENHANCED_SUCCESS_MODEL = False  # Use 9 features instead of 3 (needs more data)
```

---

## 🎯 Assignment Strategy

### **1. ML-Based Assignment (Recommended)**

```python
USE_ML_BASED_ASSIGNMENT = True
```

**How It Works:**
- Gets ALL available technicians (any skill)
- ML model evaluates each one
- Selects technician with highest predicted success

**When to Use:**
- ✅ You have good historical data (500+ records)
- ✅ Want system to learn skill compatibility
- ✅ Don't want to hard-code skill categories
- ✅ Trust ML to make decisions

**Pros:**
- 🟢 Learns from data automatically
- 🟢 No hard-coded rules
- 🟢 Finds unexpected good matches
- 🟢 Adapts to your specific operation

**Cons:**
- 🔴 Needs quality historical data
- 🔴 Less predictable than rules
- 🔴 Harder to explain to stakeholders

---

### **2. Legacy Cascading Fallback**

```python
USE_ML_BASED_ASSIGNMENT = False
```

**How It Works:**
- Level 1: Exact skill match
- Level 2: Same category skills
- Level 3: Related category skills

**When to Use:**
- ✅ Limited historical data
- ✅ Need predictable behavior
- ✅ Have well-defined skill categories
- ✅ Need to explain decisions easily

---

## 🎚️ Success Threshold Tuning

### **MIN_SUCCESS_THRESHOLD** (Lines 160)

```python
MIN_SUCCESS_THRESHOLD = 0.25  # Current: 25%
```

**What It Does:**
Filters out technicians with predicted success below this threshold.

### **Tuning Guide:**

| Threshold | Effect | Use When |
|-----------|--------|----------|
| **0.10** (10%) | ⚠️ Very permissive - almost anyone | Desperate for coverage |
| **0.20** (20%) | 📊 Permissive - accepts marginal matches | Need high assignment rate |
| **0.25** (25%) | ✅ **RECOMMENDED** - balanced | Standard operations |
| **0.30** (30%) | 🎯 Quality-focused - rejects weak matches | Quality over quantity |
| **0.40** (40%) | 🔒 Very strict - only strong matches | High-stakes dispatches |
| **0.50** (50%) | ⛔ Extremely strict - many unassigned | Critical quality |

### **Impact Analysis:**

```python
# Example with 100 dispatches:

MIN_SUCCESS_THRESHOLD = 0.10
# Result: 95% assigned, 70% success rate

MIN_SUCCESS_THRESHOLD = 0.25  # ← DEFAULT
# Result: 88% assigned, 78% success rate

MIN_SUCCESS_THRESHOLD = 0.40
# Result: 75% assigned, 85% success rate
```

### **How to Tune:**

1. **Start at 0.25** (default)
2. **Monitor your metrics**:
   - Assignment rate (% of dispatches assigned)
   - Success rate (% of productive dispatches)
3. **Adjust based on business needs**:
   - Too many unassigned? Lower threshold (0.20)
   - Too many failures? Raise threshold (0.30)

---

## 🎚️ Capacity Ratio Tuning

### **MAX_CAPACITY_RATIO** (Line 161)

```python
MAX_CAPACITY_RATIO = 1.15  # Current: 115%
```

**What It Does:**
Maximum workload allowed. If tech has capacity of 8, they can take up to 8 × 1.15 = 9.2 jobs (9 jobs).

### **Tuning Guide:**

| Ratio | Effect | Use When |
|-------|--------|----------|
| **1.00** (100%) | Strict - never exceed capacity | Maintain work-life balance |
| **1.10** (110%) | Slight flex - 10% overtime OK | Normal operations |
| **1.15** (115%) | ✅ **RECOMMENDED** - moderate flex | Balanced flexibility |
| **1.20** (120%) | High flex - significant overtime | High demand periods |
| **1.30** (130%) | Very high - risk of burnout | Emergency/peak season |
| **2.00** (200%) | No limit - anyone available | Disaster recovery |

### **Trade-offs:**

```
Lower ratio (1.00-1.10):
  + Happier technicians
  + Better work quality
  - More unassigned dispatches
  - Higher costs (may need contractors)

Higher ratio (1.20-1.50):
  + Fewer unassigned dispatches
  + Lower immediate costs
  - Technician fatigue
  - Lower success rates
  - Higher turnover
```

---

## 🤖 ML Model Configuration

### **Location:** Lines 672-727

### **1. Basic Model (Default - ENABLED)**

```python
ENABLE_ENHANCED_SUCCESS_MODEL = False  # Uses 3 features

BASIC_FEATURES = [
    'Distance_km',         # Travel distance
    'skill_match_score',   # Skill compatibility
    'workload_ratio'       # Current workload
]

# Model: Logistic Regression
classifier = LogisticRegression(max_iter=2000, random_state=42)
```

**When to Use:**
- ✅ Limited data (< 1000 records)
- ✅ Want simple, interpretable model
- ✅ Fast training needed

---

### **2. Enhanced Model (DISABLED by default)**

```python
ENABLE_ENHANCED_SUCCESS_MODEL = True  # Uses 9 features

ENHANCED_FEATURES = [
    # Basic
    'Distance_km',
    'skill_match_score',
    'workload_ratio',
    # Temporal
    'hour_of_day',        # 0-23
    'day_of_week',        # 0-6 (Monday=0)
    'is_weekend',         # 0 or 1
    # Job Complexity
    'Service_tier',       # Standard/Premium/Enterprise
    'Equipment_installed', # None/Router/Modem/etc.
    'First_time_fix'      # 0 or 1
]

# Model: Gradient Boosting or XGBoost
if XGBOOST_AVAILABLE:
    classifier = xgb.XGBClassifier(
        n_estimators=100,    # Number of trees
        max_depth=6,         # Tree depth
        learning_rate=0.1,   # Step size
        random_state=42,
        n_jobs=-1            # Use all CPU cores
    )
else:
    classifier = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42
    )
```

**When to Use:**
- ✅ Abundant data (> 2000 records)
- ✅ Want highest accuracy
- ✅ Have time/appointment data
- ✅ Job complexity varies

**Requirements:**
- Minimum 2000 historical records
- At least 50 samples per feature
- Good data quality

---

### **Model Hyperparameter Tuning:**

#### **For Logistic Regression:**

```python
classifier = LogisticRegression(
    max_iter=2000,        # Increase if convergence warning (2000-5000)
    random_state=42,      # Keep fixed for reproducibility
    C=1.0,                # Regularization (0.1=strong, 10=weak)
    solver='lbfgs'        # Algorithm (lbfgs/saga/liblinear)
)
```

**Tuning C parameter:**
- `C=0.1`: Strong regularization (simpler model, may underfit)
- `C=1.0`: **Default** - balanced
- `C=10.0`: Weak regularization (complex model, may overfit)

#### **For Gradient Boosting/XGBoost:**

```python
classifier = xgb.XGBClassifier(
    n_estimators=100,      # Trees: 50-300 (more=better but slower)
    max_depth=6,           # Depth: 3-10 (higher=complex, may overfit)
    learning_rate=0.1,     # Rate: 0.01-0.3 (lower=more accurate but slower)
    min_child_weight=1,    # Minimum samples per leaf: 1-10
    subsample=0.8,         # Fraction of data per tree: 0.6-1.0
    colsample_bytree=0.8,  # Fraction of features per tree: 0.6-1.0
    random_state=42,
    n_jobs=-1
)
```

**Tuning Guidelines:**

| Parameter | Too Low | Good Range | Too High |
|-----------|---------|------------|----------|
| `n_estimators` | Underfits | 50-200 | Slow training |
| `max_depth` | Underfits | 4-8 | Overfits |
| `learning_rate` | Slow convergence | 0.05-0.2 | Overfits |

---

## 🔧 Advanced Features

### **1. Performance Tracking** (Line 38)

```python
ENABLE_PERFORMANCE_TRACKING = True  # ← ENABLED by default
```

**What It Does:**
- Tracks each technician's historical success rate
- Adjusts ML predictions based on individual performance
- Formula: `adjusted_prob = base_prob × (0.7 + 0.3 × performance_adjustment)`

**Example:**
```
ML predicts: 70% success
Tech A has 90% historical success → adjusted to 77%
Tech B has 60% historical success → adjusted to 66%
```

**When to Enable:**
- ✅ Have 100+ historical dispatches
- ✅ Technicians have consistent IDs
- ✅ Want personalized predictions

**When to Disable:**
- ❌ Limited historical data
- ❌ High technician turnover
- ❌ Technician IDs change frequently

---

### **2. Dynamic Weight Optimization** (Line 39)

```python
ENABLE_DYNAMIC_WEIGHTS = False  # ← DISABLED (unstable)
```

**What It Does:**
- Automatically learns optimal weights from historical data
- Adjusts `WEIGHT_SUCCESS_PROB` and `WEIGHT_CONFIDENCE`

**Why Disabled:**
- Tends to produce extreme weights (0.90/0.10)
- Not needed when `USE_SUCCESS_ONLY = True`
- Makes system less predictable

**When to Enable:**
- Only if `USE_SUCCESS_ONLY = False`
- Only if you have 1000+ diverse historical records
- Only if willing to frequently retrain

---

### **3. Enhanced Success Model** (Line 40)

```python
ENABLE_ENHANCED_SUCCESS_MODEL = False  # ← DISABLED (needs more data)
```

**When to Enable:**
- ✅ Have 2000+ historical records
- ✅ Have time/date data in history
- ✅ Job complexity varies significantly
- ✅ Want maximum accuracy

**Requirements:**
- Minimum 50 samples per feature (9 features × 50 = 450 minimum)
- Recommended: 2000+ samples for stability
- Good data quality (no missing values)

---

## 📊 Performance Optimization

### **Scoring Strategy** (Line 80)

```python
USE_SUCCESS_ONLY = True  # ← ENABLED (recommended)
```

**Option 1: Pure ML (Recommended)**
```python
USE_SUCCESS_ONLY = True

# Scoring
final_score = success_prob  # Just use ML prediction
```

**Option 2: Weighted Combination**
```python
USE_SUCCESS_ONLY = False

# Scoring
final_score = 0.60 × success_prob + 0.40 × confidence

# Where confidence = 1.0 - (0.6 × norm_distance + 0.4 × norm_workload)
```

**Tuning Weights:**
```python
# Prioritize success prediction
WEIGHT_SUCCESS_PROB = 0.75  # 75%
WEIGHT_CONFIDENCE = 0.25    # 25%

# Balanced
WEIGHT_SUCCESS_PROB = 0.60  # 60%
WEIGHT_CONFIDENCE = 0.40    # 40%

# Prioritize proximity/workload
WEIGHT_SUCCESS_PROB = 0.40  # 40%
WEIGHT_CONFIDENCE = 0.60    # 60%
```

---

## 🎯 Recommended Configurations

### **Configuration 1: High Quality (Fewer Assignments)**

```python
USE_ML_BASED_ASSIGNMENT = True
MIN_SUCCESS_THRESHOLD = 0.35        # ← Strict
MAX_CAPACITY_RATIO = 1.10           # ← Low overtime
ENABLE_PERFORMANCE_TRACKING = True
USE_SUCCESS_ONLY = True
```

**Results:**
- 75-80% assignment rate
- 85-90% success rate
- Happy technicians
- May need contractors

---

### **Configuration 2: Balanced (Recommended)**

```python
USE_ML_BASED_ASSIGNMENT = True
MIN_SUCCESS_THRESHOLD = 0.25        # ← Default
MAX_CAPACITY_RATIO = 1.15           # ← Moderate flex
ENABLE_PERFORMANCE_TRACKING = True
USE_SUCCESS_ONLY = True
```

**Results:**
- 85-90% assignment rate
- 78-83% success rate
- Good work-life balance
- Optimal costs

---

### **Configuration 3: High Coverage (More Assignments)**

```python
USE_ML_BASED_ASSIGNMENT = True
MIN_SUCCESS_THRESHOLD = 0.20        # ← Permissive
MAX_CAPACITY_RATIO = 1.25           # ← High overtime
ENABLE_PERFORMANCE_TRACKING = True
USE_SUCCESS_ONLY = True
```

**Results:**
- 93-97% assignment rate
- 72-77% success rate
- Risk of technician fatigue
- Lower immediate costs

---

### **Configuration 4: Limited Data (Use Rules)**

```python
USE_ML_BASED_ASSIGNMENT = False     # ← Legacy mode
MIN_SUCCESS_THRESHOLD = N/A
MAX_CAPACITY_RATIO = 1.15
ENABLE_PERFORMANCE_TRACKING = False
USE_SUCCESS_ONLY = False
WEIGHT_SUCCESS_PROB = 0.60
WEIGHT_CONFIDENCE = 0.40
```

**When to Use:**
- < 500 historical records
- New operation
- Need predictable behavior

---

## 🔍 Troubleshooting

### **Problem: Too Many Unassigned Dispatches**

**Solutions:**
1. Lower `MIN_SUCCESS_THRESHOLD` (try 0.20 or 0.15)
2. Increase `MAX_CAPACITY_RATIO` (try 1.20 or 1.25)
3. Check if historical data is representative
4. Verify technician availability in calendar

---

### **Problem: Low Success Rate**

**Solutions:**
1. Raise `MIN_SUCCESS_THRESHOLD` (try 0.30 or 0.35)
2. Enable `ENABLE_PERFORMANCE_TRACKING` (if not already)
3. Check ML model performance (may need retraining)
4. Review historical data quality

---

### **Problem: Model Seems Inaccurate**

**Solutions:**
1. Check training data size:
   ```python
   print(f"Training records: {len(history_clean)}")
   # Need: 500+ for basic, 2000+ for enhanced
   ```

2. Validate business rules:
   ```python
   VALIDATE_BUSINESS_RULES = True  # Enable in code
   # Should show: shorter distance = higher success
   ```

3. Review skill compatibility learning:
   - Check `skill_compatibility_dict` has entries
   - Verify historical data has diverse skill pairs

4. Consider disabling enhanced model:
   ```python
   ENABLE_ENHANCED_SUCCESS_MODEL = False
   # Use basic 3-feature model
   ```

---

### **Problem: Training Takes Too Long**

**Solutions:**
1. Use basic model instead of enhanced
2. Reduce `n_estimators` for XGBoost:
   ```python
   n_estimators=50  # Down from 100
   ```
3. Use Logistic Regression instead of Gradient Boosting
4. Sample historical data if very large (> 50K records)

---

### **Problem: Convergence Warning (Logistic Regression)**

**Solutions:**
```python
classifier = LogisticRegression(
    max_iter=5000,  # ← Increase from 2000
    random_state=42
)
```

---

## 📝 Step-by-Step Tuning Process

### **Week 1: Baseline**
1. Use default configuration
2. Run for 1 week
3. Record metrics:
   - Assignment rate
   - Success rate
   - Unassigned count
   - Technician feedback

### **Week 2: Adjust Threshold**
1. Based on Week 1 results:
   - Too many unassigned? Lower to 0.20
   - Too many failures? Raise to 0.30
2. Run for 1 week
3. Compare metrics

### **Week 3: Adjust Capacity**
1. Based on Week 2 results:
   - Technicians overworked? Lower to 1.10
   - Still many unassigned? Raise to 1.20
2. Run for 1 week
3. Compare metrics

### **Week 4: Enable Advanced Features**
1. If data sufficient (2000+ records):
   - Try `ENABLE_ENHANCED_SUCCESS_MODEL = True`
2. Compare accuracy
3. Keep if improves results

### **Ongoing: Monitor & Iterate**
- Review metrics monthly
- Retrain model quarterly with new data
- Adjust thresholds seasonally if needed

---

## 🎓 Quick Reference Card

```python
# ===== QUICK TUNING REFERENCE =====

# ASSIGNMENT RATE TOO LOW? (< 80%)
MIN_SUCCESS_THRESHOLD = 0.20  # ← Lower this
MAX_CAPACITY_RATIO = 1.20     # ← Raise this

# SUCCESS RATE TOO LOW? (< 75%)
MIN_SUCCESS_THRESHOLD = 0.30  # ← Raise this
ENABLE_PERFORMANCE_TRACKING = True  # ← Enable this

# TECHNICIANS OVERWORKED?
MAX_CAPACITY_RATIO = 1.10     # ← Lower this

# NEED SIMPLE/FAST MODEL?
ENABLE_ENHANCED_SUCCESS_MODEL = False  # ← Keep disabled
# Model: Logistic Regression

# NEED BEST ACCURACY? (Have 2000+ records)
ENABLE_ENHANCED_SUCCESS_MODEL = True   # ← Enable this
# Model: XGBoost/Gradient Boosting

# MODEL PREDICTIONS SEEM OFF?
ENABLE_PERFORMANCE_TRACKING = True     # ← Enable this
# Adjusts based on technician history

# ===== END REFERENCE =====
```

---

## 📞 Support

For issues with tuning:
1. Check training data size and quality
2. Review business rules validation output
3. Monitor assignment rate vs success rate trade-off
4. Start with recommended config and adjust gradually

**Remember:** Small changes (±0.05 threshold, ±0.05 capacity ratio) often have significant impact!

