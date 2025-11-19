# Column Comparison: current_dispatches.csv vs optimized_assignments.csv

## Executive Summary

**Current Status:**
- `current_dispatches.csv`: **24 columns**, 600 rows
- `optimized_assignments.csv`: **13 columns**, 525 rows
- **18 columns missing** from optimized_assignments.csv
- **7 new columns** added by optimization engine

---

## 📋 Missing Columns (18 total)

These columns exist in `current_dispatches.csv` but are **missing** from `optimized_assignments.csv`:

### **Critical for Dashboard (12 columns):**

| Column | Usage | Impact |
|--------|-------|--------|
| `Service_tier` | Technician View cards, Analytics | **HIGH** - Used in card details |
| `Equipment_installed` | Technician View cards, Analytics | **HIGH** - Used in card details |
| `Appointment_start_datetime` | Date/time filters, All views | **HIGH** - Core filtering |
| `Appointment_end_datetime` | Date/time filters, Duration calc | **HIGH** - Core filtering |
| `City` | All views, Filters, Location | **HIGH** - Essential for routing |
| `Customer_latitude` | Maps, Distance calc, Location | **HIGH** - Essential for routing |
| `Customer_longitude` | Maps, Distance calc, Location | **HIGH** - Essential for routing |
| `Duration_min` | Time estimates, Planning | **MEDIUM** - Alternative exists |
| `Order_type` | Filtering, Analytics | **MEDIUM** - Nice to have |
| `Status` | Filtering, Tracking | **MEDIUM** - Nice to have |
| `Street` | Full address display | **LOW** - Detail only |
| `County` | Location hierarchy | **LOW** - Detail only |
| `State` | Location hierarchy | **LOW** - Detail only |
| `Postal_code` | Address validation | **LOW** - Detail only |

### **Optional/Administrative (6 columns):**

| Column | Purpose | Impact |
|--------|---------|--------|
| `Optimization_confidence` | Quality metric | **LOW** - Replaced by score |
| `Optimization_status` | Processing state | **LOW** - Not needed post-opt |
| `Optimization_timestamp` | Audit trail | **LOW** - Added by dashboard |
| `Resolution_type` | Historical tracking | **LOW** - Future dispatches |
| `Completion_notes` | Historical notes | **LOW** - Future dispatches |
| `Skill_category` | Skill grouping | **LOW** - Nice to have |

---

## ➕ New Columns Added by Optimization (7 total)

These columns are **new** in `optimized_assignments.csv`:

| Column | Description | Source |
|--------|-------------|--------|
| `success_probability` | ML-predicted success rate (0-1) | **ML Model** |
| `estimated_duration` | Predicted job duration (minutes) | **ML Model** |
| `distance` | Travel distance (km) | **Calculation** |
| `skill_match` | Skill compatibility (0 or 1) | **Business Rules** |
| `score` | Composite optimization score (0-100) | **Weighted Algorithm** |
| `has_warnings` | Warning flag (True/False) | **Validation** |
| `warning_count` | Number of warnings | **Validation** |

---

## 🔧 Current Dashboard Workaround

The dashboard currently handles missing columns by:

1. **Merging with `current_dispatches.csv`** - Gets most missing columns
2. **Using `.get()` with defaults** - Prevents KeyErrors
3. **Providing fallback values** - Ensures graceful degradation

### Default Values Used:
```python
'Service_tier': 'Standard'
'Equipment_installed': 'None'
'City': 'N/A'
'Customer_latitude': 0
'Customer_longitude': 0
'Duration_min': 0
```

---

## ⚠️ Critical Issues

### **1. Location Data Missing**
- `City`, `Customer_latitude`, `Customer_longitude` are **essential**
- Without these, distance calculations are impossible
- Dashboard merge with `current_dispatches.csv` solves this

### **2. DateTime Fields Missing**
- `Appointment_start_datetime` and `Appointment_end_datetime` critical for scheduling
- Technician View date filters depend on these
- Dashboard merge provides these fields

### **3. Service Details Missing**
- `Service_tier` and `Equipment_installed` needed for Technician View cards
- Shows as defaults ("Standard", "None") without merge

---

## ✅ Recommended Solutions

### **Option 1: Enhance optimize_dispatches.py (RECOMMENDED)**

Add these columns to `optimized_assignments.csv` output:

```python
# Essential columns to add:
essential_columns = [
    'City',
    'Customer_latitude',
    'Customer_longitude',
    'Appointment_start_datetime',
    'Appointment_end_datetime',
    'Service_tier',
    'Equipment_installed',
    'Duration_min',
    'Street',
    'State',
    'Postal_code'
]
```

**Benefits:**
- ✅ Self-contained optimization output
- ✅ No merge required in dashboard
- ✅ Faster dashboard loading
- ✅ Complete data for all views

**Implementation:**
```python
# In optimize_dispatches.py, when creating output_data:
output_row = {
    'dispatch_id': dispatch.dispatch_id,
    'ticket_type': dispatch.ticket_type,
    'priority': dispatch.priority,
    'required_skill': dispatch.required_skill,
    
    # Add location data
    'city': dispatch.city,
    'customer_latitude': dispatch.customer_latitude,
    'customer_longitude': dispatch.customer_longitude,
    'street': dispatch.street,
    'state': dispatch.state,
    'postal_code': dispatch.postal_code,
    
    # Add datetime data
    'appointment_start_datetime': dispatch.appointment_start_datetime,
    'appointment_end_datetime': dispatch.appointment_end_datetime,
    
    # Add service details
    'service_tier': dispatch.service_tier,
    'equipment_installed': dispatch.equipment_installed,
    'duration_min': dispatch.duration_min,
    
    # Existing optimization data
    'assigned_technician_id': dispatch.assigned_technician_id,
    'optimized_technician_id': assignment.technician_id,
    'success_probability': assignment.success_probability,
    'estimated_duration': assignment.estimated_duration,
    'distance': assignment.distance,
    'skill_match': assignment.skill_match,
    'score': assignment.score,
    'has_warnings': assignment.has_warnings,
    'warning_count': len(assignment.warnings)
}
```

### **Option 2: Keep Current Merge Approach**

**Pros:**
- ✅ Already working
- ✅ No changes to optimize_dispatches.py
- ✅ Flexible

**Cons:**
- ❌ Requires two CSV files
- ❌ Slower dashboard loading
- ❌ More complex data loading logic

### **Option 3: Hybrid Approach**

Include only **essential** columns in optimized output:
- Location: `City`, `Customer_latitude`, `Customer_longitude`
- DateTime: `Appointment_start_datetime`
- Service: `Service_tier`, `Equipment_installed`

Get remaining details from merge if needed.

---

## 📊 Impact on Dashboard Views

### **Analytics Dashboard**
- ✅ Works with merge
- ⚠️ Location filters need City
- ⚠️ Charts need complete data

### **Manager Assignments**
- ✅ Works with merge
- ⚠️ Needs location data for display
- ⚠️ Needs datetime for sorting

### **Technician View**
- ⚠️ **Most impacted** - needs many fields
- ⚠️ Card view needs Service_tier, Equipment_installed
- ⚠️ Date filters need Appointment_start_datetime
- ⚠️ Map features need coordinates

---

## 🎯 Priority Actions

### **Immediate (Fix Now):**
1. ✅ Dashboard merge logic - **DONE**
2. ✅ Safe column access with `.get()` - **DONE**

### **Short Term (Next Sprint):**
1. Add essential columns to `optimize_dispatches.py` output
2. Test with enhanced optimized_assignments.csv
3. Remove merge dependency

### **Long Term (Future):**
1. Standardize column names across all files
2. Create data schema documentation
3. Add validation for required columns

---

## 📝 Column Naming Conventions

### **Current Inconsistencies:**

| Current Dispatches | Optimized Assignments | Standard |
|-------------------|----------------------|----------|
| `Dispatch_id` | `dispatch_id` | lowercase |
| `Ticket_type` | `ticket_type` | lowercase |
| `Customer_latitude` | (missing) | lowercase |

**Recommendation:** Use **lowercase with underscores** for all new columns.

---

## 🔍 Data Flow

```
┌─────────────────────────┐
│  current_dispatches.csv │
│  (24 columns, 600 rows) │
└───────────┬─────────────┘
            │
            ↓
┌─────────────────────────┐
│ optimize_dispatches.py  │
│  - Loads dispatches     │
│  - Runs ML models       │
│  - Assigns technicians  │
└───────────┬─────────────┘
            │
            ↓
┌─────────────────────────┐
│ optimized_assignments   │
│  (13 columns, 525 rows) │ ← MISSING 18 columns
└───────────┬─────────────┘
            │
            ↓
┌─────────────────────────┐
│   dashboard_app.py      │
│  - Merges with current  │ ← WORKAROUND
│  - Adds missing columns │
└─────────────────────────┘
```

**Ideal Flow:**
```
optimize_dispatches.py → optimized_assignments.csv (31 columns) → dashboard_app.py
```

---

## 📚 References

- **Data Loading:** `dashboard_app.py` lines 66-205
- **Column Mapping:** `dashboard_app.py` lines 106-140
- **Optimization Script:** `optimize_dispatches.py`
- **Technician View:** `dashboard_app.py` lines 446-859

---

## 💡 Summary

**Current State:** Dashboard works by merging `optimized_assignments.csv` with `current_dispatches.csv` to get missing columns.

**Recommendation:** Enhance `optimize_dispatches.py` to include essential columns (City, coordinates, datetime, service details) directly in output for better performance and simplicity.

**Priority:** **MEDIUM** - Current workaround is functional but not optimal.

