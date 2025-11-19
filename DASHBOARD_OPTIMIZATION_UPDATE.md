# Dashboard Update: Integration with optimize_dispatches.py

## Overview
The dashboard has been updated to work with the new optimization engine (`optimize_dispatches.py`) and its output file (`optimized_assignments.csv`).

## What Changed

### 1. **New Data Source**
- **Primary Source**: `optimized_assignments.csv` (from `optimize_dispatches.py`)
- **Fallback Source**: `optimized_dispatch_results.csv` (legacy format)

### 2. **Enhanced Data Loading**
The dashboard now:
- Automatically detects and loads `optimized_assignments.csv`
- Merges optimization results with full dispatch details from `current_dispatches.csv`
- Maps column names to ensure compatibility with existing dashboard features
- Adds derived metrics for comparison and analysis

### 3. **New Sidebar Features**

#### **Data Management Section**
- **Data Source Info**: Shows which file is being used and when it was last updated
- **Run Optimization Button**: Execute `optimize_dispatches.py` directly from the dashboard
- **Refresh Data Button**: Reload data without running optimization
- **Optimization Info**: Displays the scoring weights and data flow

#### **File Information Display**
- File name and status
- Last modified timestamp
- File size

### 4. **Data Source Indicator**
- Header shows current data source and last update time
- Provides transparency about which optimization results are being displayed

## How to Use

### Method 1: Run Optimization from Dashboard
1. Open the dashboard: `streamlit run dashboard_app.py`
2. Click **"🚀 Run Optimization"** in the sidebar
3. Wait for optimization to complete (may take a few minutes)
4. Dashboard automatically refreshes with new data

### Method 2: Run Optimization Manually
1. Run the optimization script:
   ```bash
   python optimize_dispatches.py
   ```
2. Start or refresh the dashboard:
   ```bash
   streamlit run dashboard_app.py
   ```
3. Click **"🔄 Refresh"** if dashboard is already running

### Method 3: Legacy Mode
If `optimized_assignments.csv` is not available, the dashboard will automatically fall back to `optimized_dispatch_results.csv` (if it exists).

## Column Mapping

The dashboard automatically maps columns from `optimized_assignments.csv`:

| Source Column | Dashboard Column | Description |
|--------------|------------------|-------------|
| `dispatch_id` | `Dispatch_id` | Unique dispatch identifier |
| `optimized_technician_id` | `Optimized_technician_id` | Assigned technician |
| `success_probability` | `Predicted_success_prob` | ML-predicted success rate |
| `estimated_duration` | `Optimized_predicted_duration_min` | Job duration estimate |
| `distance` | `Optimized_distance_km` | Travel distance |
| `skill_match` | `Skill_match_score` | Skill compatibility score |
| `score` | `Optimization_score` | Overall assignment score |
| `has_warnings` | `Has_warnings` | Warning flag |
| `warning_count` | `Warning_count` | Number of warnings |

## Derived Metrics

The dashboard adds these metrics for analysis:

- **Success_prob_improvement**: Optimized vs initial success probability
- **Distance_change_km**: Optimized vs initial distance
- **Workload_ratio_change**: Optimized vs initial workload
- **Optimization_confidence**: Confidence in the assignment
- **Fallback_level**: Assignment method indicator (`ml_optimized`)

## Optimization Engine Configuration

The `optimize_dispatches.py` script uses these weights:

- **Success Probability**: 50% - Likelihood of first-time fix
- **Workload Balance**: 35% - Technician capacity management
- **Travel Distance**: 10% - Minimize travel time
- **Estimated Overrun**: 5% - Avoid schedule conflicts

## Data Flow

```
current_dispatches.csv
         ↓
  optimize_dispatches.py
         ↓
optimized_assignments.csv ←→ current_dispatches.csv
         ↓                              ↓
         └──────── Merge ───────────────┘
                    ↓
            dashboard_app.py
                    ↓
         Interactive Dashboard
```

## Requirements

### Files Needed:
1. `current_dispatches.csv` - Source dispatch data
2. `optimize_dispatches.py` - Optimization script
3. `optimized_assignments.csv` - Optimization results (generated)
4. `dashboard_app.py` - Dashboard application

### Python Packages:
- streamlit
- pandas
- plotly
- numpy
- Other dependencies from `requirements.txt`

## Troubleshooting

### Issue: "No results file found"
**Solution**: Run optimization first:
```bash
python optimize_dispatches.py
```

### Issue: "current_dispatches.csv not found"
**Solution**: Ensure you have the source dispatch data file in the project directory.

### Issue: "Optimization timed out"
**Solution**: 
- Check the size of your input data
- Increase timeout in dashboard code if needed
- Run optimization manually from terminal

### Issue: Column mapping errors
**Solution**: 
- Check that `current_dispatches.csv` has the expected columns
- Verify `optimized_assignments.csv` structure matches expected format

## Benefits

### 1. **Unified Data Source**
- Single source of truth for optimization results
- Consistent data across all dashboard views

### 2. **Real-Time Optimization**
- Run optimization without leaving the dashboard
- Immediate feedback on optimization results

### 3. **Better Data Management**
- Clear visibility into data source and freshness
- Easy refresh and reload capabilities

### 4. **Flexibility**
- Supports both new and legacy data formats
- Graceful fallback if new format unavailable

### 5. **Enhanced Analytics**
- All existing dashboard features work with new data
- Improved metric calculations
- Better comparison capabilities

## Future Enhancements

Potential improvements:
1. Auto-refresh on file changes
2. Historical comparison of optimization runs
3. A/B testing between optimization strategies
4. Real-time optimization status tracking
5. Custom weight configuration from dashboard

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the data flow diagram
3. Verify all required files are present
4. Check the terminal output for detailed error messages

