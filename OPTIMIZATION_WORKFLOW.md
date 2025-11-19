# 🔄 Optimization Workflow Guide

## Overview

The optimization engine (`optimize_dispatches.py`) requires local execution because it connects to a database and uses ML models that aren't deployed to Streamlit Cloud.

---

## 🏗️ Architecture

```
┌─────────────────────────┐
│   Local Development     │
│                         │
│  1. PostgreSQL Database │
│  2. ML Models (pickle)  │
│  3. optimize_dispatches │
└───────────┬─────────────┘
            │
            ↓ (generates)
┌─────────────────────────┐
│ optimized_assignments   │
│        .csv             │
└───────────┬─────────────┘
            │
            ↓ (upload to)
┌─────────────────────────┐
│   GitHub Repository     │
│  tmhack0914/dashboard   │
│         test            │
└───────────┬─────────────┘
            │
            ↓ (deploys to)
┌─────────────────────────┐
│   Streamlit Cloud       │
│   dashboard_app.py      │
│   (read-only)           │
└─────────────────────────┘
```

---

## 📋 Current Workflow

### **Step 1: Run Optimization Locally**

```bash
# On your local machine
cd C:\Users\ftrhack127\Desktop\Smart_dispatch_agent

# Run the optimization engine
python optimize_dispatches.py
```

**This will:**
- Connect to PostgreSQL database
- Load dispatch data
- Run ML predictions
- Optimize technician assignments
- Generate `optimized_assignments.csv`

**Output:**
```
optimized_assignments.csv (525 rows, 13 columns)
optimization_warnings.csv (if any warnings)
```

---

### **Step 2: Upload Results to GitHub**

```bash
# Add the generated file
git add optimized_assignments.csv

# Commit
git commit -m "Update optimization results - [date]"

# Push to GitHub
git push origin main
```

**Note:** Push to your dashboard repository: `tmhack0914/dashboardtest`

---

### **Step 3: Streamlit Cloud Auto-Updates**

- Streamlit Cloud detects the file change
- Automatically rebuilds the dashboard (1-2 minutes)
- New data appears in all views

**No manual refresh needed!**

---

## ⚠️ Why Can't We Run Optimization on Streamlit Cloud?

### **Missing Dependencies:**

1. **Database Connection**
   - `optimize_dispatches.py` connects to PostgreSQL
   - Database credentials not available on Streamlit Cloud
   - Security: Don't expose database credentials in public repo

2. **ML Models & Preprocessor**
   - Requires pickled model files:
     - `preprocessor.pkl`
     - `success_model.pkl`
     - `duration_model.pkl`
   - These files are large (50+ MB)
   - Not suitable for Git repository

3. **Custom Python Modules**
   - `data_loader.py` - Database connection wrapper
   - `config.py` - Configuration management
   - `business_rules.py` - Business logic
   - These aren't in the dashboard repository

---

## ✅ Alternative Solutions

### **Option 1: Scheduled Optimization (RECOMMENDED)**

**Setup:**
1. Run optimization locally on a schedule (e.g., daily at 6 AM)
2. Use GitHub Actions or Task Scheduler to automate
3. Results automatically update dashboard

**Automation Script:**
```bash
#!/bin/bash
# optimize_and_upload.sh

# Run optimization
cd /path/to/project
python optimize_dispatches.py

# Upload to GitHub
git add optimized_assignments.csv
git commit -m "Automated optimization update - $(date)"
git push origin main

echo "Optimization complete and uploaded!"
```

**Schedule with cron (Linux/Mac):**
```bash
0 6 * * * /path/to/optimize_and_upload.sh
```

**Schedule with Task Scheduler (Windows):**
- Create task to run script daily

---

### **Option 2: API-Based Optimization**

**Architecture:**
```
Streamlit Cloud Dashboard
         ↓ (API call)
    Local API Server
         ↓ (runs)
  optimize_dispatches.py
         ↓ (returns)
  optimized_assignments.csv
         ↓ (saves to)
      GitHub
```

**Requirements:**
- Local API server (Flask/FastAPI)
- Exposed endpoint for optimization
- Webhook to update GitHub

---

### **Option 3: Upload Pre-Generated Results**

**Manual Process:**
1. Run optimization locally whenever needed
2. Manually upload `optimized_assignments.csv` to GitHub
3. Dashboard reflects changes automatically

**Pros:**
- Simple, no automation needed
- Full control over when to optimize

**Cons:**
- Manual process
- Can forget to update

---

## 🔧 Current Dashboard Behavior

### **Run Optimization Button Status:**

**On Streamlit Cloud:**
- Button is **disabled**
- Shows: "⚠️ Optimization unavailable"
- Info message explains local execution needed

**Locally (if running dashboard locally):**
- Button is **enabled**
- Clicking runs `optimize_dispatches.py`
- Results update immediately

---

## 📊 Data Flow

### **Current Working Flow:**

```
1. Local Machine:
   - Run: python optimize_dispatches.py
   - Generates: optimized_assignments.csv

2. GitHub:
   - Upload: optimized_assignments.csv
   - Commit & Push

3. Streamlit Cloud:
   - Detects: file change
   - Rebuilds: automatically
   - Loads: new data
   - Displays: updated results
```

---

## 🎯 Best Practices

### **For Regular Updates:**

1. **Daily Optimization**
   - Run optimization every morning
   - Upload results before business hours
   - Dashboard shows fresh data all day

2. **Version Control**
   - Keep historical results if needed
   - Use meaningful commit messages
   - Track optimization parameters

3. **Monitoring**
   - Check optimization logs
   - Monitor warning counts
   - Review unassigned dispatches

### **For Development:**

1. **Test Locally First**
   - Run optimization locally
   - Verify results in local dashboard
   - Then upload to production

2. **Backup Data**
   - Keep copies of optimization results
   - Save warnings for analysis
   - Archive historical data

---

## 🚀 Quick Start Checklist

- [ ] PostgreSQL database is running
- [ ] ML models are trained and saved
- [ ] `current_dispatches.csv` has latest data
- [ ] Run: `python optimize_dispatches.py`
- [ ] Verify: `optimized_assignments.csv` generated
- [ ] Upload to GitHub
- [ ] Wait for Streamlit Cloud rebuild
- [ ] Check dashboard for updated data

---

## ❓ Troubleshooting

### **Problem: Optimization fails**
**Solution:** 
- Check database connection
- Verify ML models exist
- Review error logs

### **Problem: Dashboard shows old data**
**Solution:**
- Verify file uploaded to GitHub
- Check Streamlit Cloud build status
- Click "Refresh" button in dashboard

### **Problem: Button disabled on local machine**
**Solution:**
- Ensure `optimize_dispatches.py` exists in project root
- Check file permissions
- Restart Streamlit server

---

## 📞 Support

**For issues with:**
- **Optimization:** Check `optimize_dispatches.py` logs
- **Dashboard:** Check Streamlit Cloud logs
- **Data:** Verify CSV file format and columns

---

## 🔄 Future Enhancements

### **Planned Improvements:**

1. **API Integration**
   - RESTful API for optimization
   - Secure endpoint on local server
   - Dashboard triggers via API call

2. **Cloud Database**
   - Migrate to cloud PostgreSQL
   - Enable Streamlit Cloud access
   - Run optimization in cloud

3. **Scheduled Jobs**
   - GitHub Actions automation
   - Cron-based optimization
   - Email notifications

4. **Real-Time Updates**
   - WebSocket connection
   - Live optimization status
   - Progress indicators

---

## 📚 Related Documentation

- `DASHBOARD_OPTIMIZATION_UPDATE.md` - Dashboard integration details
- `COLUMN_COMPARISON_SUMMARY.md` - Data structure analysis
- `DASHBOARD_ENHANCEMENT_RECOMMENDATIONS.md` - Future features

---

## 🎉 Summary

**Current State:** 
- Optimization runs **locally**
- Results uploaded to **GitHub**
- Dashboard reads from **repository**

**Future State:**
- Automated optimization
- API-based triggering
- Real-time updates

**For now:** Run locally, upload manually, dashboard updates automatically! ✅

