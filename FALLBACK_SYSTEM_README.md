# PostgreSQL to CSV Fallback System

## Overview

The dispatch optimization system now includes a robust fallback mechanism that automatically switches to CSV files when PostgreSQL database connection fails.

## Architecture

```
┌─────────────────────────────────────────┐
│   optimize_dispatches.py                │
│   (Main Optimization Engine)            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   data_loader.py                        │
│   (Smart Data Loading)                  │
└──────────────┬──────────────────────────┘
               │
               ├─── TRY: PostgreSQL Database
               │    ├─ current_dispatches_csv
               │    ├─ technicians_10k
               │    └─ technician_calendar_10k
               │
               └─── FALLBACK: CSV Files
                    ├─ current_dispatches.csv ✓
                    ├─ technicians.csv ✓
                    ├─ calendar.csv (auto-generated)
                    └─ dispatch_history.csv ✓
```

## Files Created

### 1. **data_loader.py**
- Handles PostgreSQL connections
- Automatically falls back to CSV when database unavailable
- Creates `calendar.csv` from PostgreSQL if it doesn't exist
- Generates default calendar if both PostgreSQL and CSV fail

### 2. **config.py**
- Central configuration for all settings
- Model paths
- Database credentials (from environment variables)
- Optimization weights and thresholds
- Business rules configuration

### 3. **business_rules.py**
- Business logic for success probability
- Rule-based calculations
- Validation logic
- Blending function for ML + Rules hybrid

## How It Works

### Normal Operation (PostgreSQL Available)
```bash
python optimize_dispatches.py
```

**Output:**
```
[1/6] Loading data...
  Attempting PostgreSQL connection...
  ✓ Connected to PostgreSQL database
  ✓ Loaded 150 dispatches from PostgreSQL
  ✓ Loaded 10000 technicians from PostgreSQL
  ✓ Loaded 50000 calendar entries from PostgreSQL
  ✓ Created calendar.csv for future fallback use

  🗄️  Data Source: PostgreSQL Database
  ✓ Total: 150 dispatches, 10000 technicians, 50000 calendar entries
```

### Fallback Operation (PostgreSQL Unavailable)
```bash
python optimize_dispatches.py
```

**Output:**
```
[1/6] Loading data...
  Attempting PostgreSQL connection...
  ⚠️  PostgreSQL connection failed: could not connect to server
  → Falling back to CSV files...
  ✓ Loaded 150 dispatches from CSV (filtered >= 2025-11-12)
  ✓ Loaded 10000 technicians from CSV
  ✓ Loaded 50000 calendar entries from CSV

  📁 Data Source: CSV Files (PostgreSQL unavailable)
  ✓ Total: 150 dispatches, 10000 technicians, 50000 calendar entries
```

## CSV Files Required

### In GitHub Repository:
- ✅ `current_dispatches.csv` - Active dispatch orders
- ✅ `technicians.csv` - Technician roster and details
- ✅ `dispatch_history.csv` - Historical dispatch data
- 🔄 `calendar.csv` - Technician availability (auto-generated if missing)

### Auto-Generated Files:
- `optimized_assignments.csv` - Output: Optimized technician assignments
- `optimization_warnings.csv` - Output: Any warnings during optimization
- `optimization_report.txt` - Output: Detailed optimization report

## Environment Variables

Set these for PostgreSQL connection (optional):

```bash
# Database Connection
export DB_HOST=your-database-host.com
export DB_PORT=5432
export DB_NAME=dispatch_db
export DB_USER=your_username
export DB_PASSWORD=your_password
export DB_SCHEMA=team_faiber_force
```

If not set, the system will automatically use CSV fallback.

## Calendar CSV Generation

If `calendar.csv` doesn't exist:

1. **First try**: Export from PostgreSQL
   ```python
   from data_loader import DataLoader
   loader = DataLoader()
   loader.connect()
   loader.export_calendar_from_db()
   ```

2. **Fallback**: Generate default 30-day calendar
   - All technicians available 8:00-17:00
   - Max 8 assignments per day
   - Monday-Friday availability

## Testing the Fallback

### Test with CSVs only:
```bash
# Temporarily disable PostgreSQL
export DB_HOST=invalid_host

# Run optimization
python optimize_dispatches.py

# Should see CSV fallback messages
```

### Test data loader directly:
```bash
python data_loader.py
```

## Workflow

### Production (with PostgreSQL):
```bash
# 1. Run optimization (uses PostgreSQL)
python optimize_dispatches.py

# 2. View results in dashboard
streamlit run dashboard_app.py
```

### Development/Offline (CSV only):
```bash
# 1. Ensure CSV files exist
ls *.csv

# 2. Run optimization (uses CSV fallback)
python optimize_dispatches.py

# 3. View results in dashboard
streamlit run dashboard_app.py
```

## Error Handling

The system gracefully handles:
- ✅ PostgreSQL connection timeout
- ✅ Database credentials issues
- ✅ Missing CSV files (generates defaults where possible)
- ✅ Malformed CSV data (with warnings)
- ✅ Missing calendar data (generates default)

## Benefits

1. **Resilience**: Works offline or without database access
2. **Development**: Easy local development without database setup
3. **Testing**: Can test with sample CSV data
4. **Backup**: CSV files serve as data backup
5. **Portability**: Can run anywhere with just CSV files
6. **Version Control**: CSV data can be version controlled in Git

## Troubleshooting

### "FileNotFoundError: technicians.csv not found"
→ Ensure CSV files are in the same directory as `optimize_dispatches.py`

### "No calendar data available"
→ System will auto-generate default calendar for next 30 days

### "Connection refused" but still shows database errors
→ Check that fallback is working: look for "→ Falling back to CSV..." message

### Calendar has no entries
→ Run: `python data_loader.py` to test calendar generation

## Performance

| Data Source | Load Time | Dispatches | Technicians |
|------------|-----------|------------|-------------|
| PostgreSQL | ~2-5 sec  | All        | All (10k)   |
| CSV Files  | <1 sec    | Filtered   | All (10k)   |

CSV is actually faster for local operations!

## Next Steps

1. ✅ Fallback system implemented
2. ✅ Calendar auto-generation added
3. 🔄 Test with real data
4. 🔄 Deploy to production
5. 🔄 Monitor fallback usage

## Support

For issues with the fallback system:
1. Check CSV files exist and are not corrupted
2. Run `python data_loader.py` to test directly
3. Check environment variables are set correctly
4. Verify CSV column names match expected format

