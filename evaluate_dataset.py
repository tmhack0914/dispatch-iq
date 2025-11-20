"""
Evaluate dispatch_history_hackathon_10k.csv for ML training suitability
"""

import pandas as pd
import numpy as np
from datetime import datetime

print("="*80)
print("DISPATCH HISTORY DATASET EVALUATION")
print("="*80)

# Load dataset
print("\n[1/7] Loading dataset...")
df = pd.read_csv('dispatch_history_hackathon_10k.csv')
print(f"✓ Loaded: {len(df):,} records")

# Basic info
print("\n[2/7] Dataset Overview")
print("-"*80)
print(f"Total Records:        {len(df):,}")
print(f"Total Columns:        {len(df.columns)}")
print(f"Memory Usage:         {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
print(f"\nDate Range:")
if 'Appointment_start_time' in df.columns:
    df['Appointment_start_time'] = pd.to_datetime(df['Appointment_start_time'], errors='coerce')
    print(f"  From: {df['Appointment_start_time'].min()}")
    print(f"  To:   {df['Appointment_start_time'].max()}")
    print(f"  Span: {(df['Appointment_start_time'].max() - df['Appointment_start_time'].min()).days} days")

# Column analysis
print("\n[3/7] Column Completeness")
print("-"*80)
print(f"{'Column':<30} {'Non-Null':>10} {'Missing':>10} {'% Complete':>12}")
print("-"*80)

for col in df.columns:
    non_null = df[col].notna().sum()
    missing = df[col].isna().sum()
    pct = (non_null / len(df)) * 100
    status = "✓" if pct >= 90 else "⚠" if pct >= 70 else "✗"
    print(f"{status} {col:<28} {non_null:>10,} {missing:>10,} {pct:>11.1f}%")

# Critical ML features check
print("\n[4/7] ML Training Features Analysis")
print("-"*80)

critical_features = {
    'Distance_km': 'Distance to technician',
    'Required_skill': 'Required skill for dispatch',
    'Assigned_technician_id': 'Technician assignment',
    'Productive_dispatch': 'Target variable (success)',
    'Status': 'Dispatch completion status',
    'Duration_min': 'Expected duration',
    'Actual_duration_min': 'Actual duration'
}

feature_status = []
for feature, description in critical_features.items():
    if feature in df.columns:
        completeness = (df[feature].notna().sum() / len(df)) * 100
        if completeness >= 90:
            status = "✓ GOOD"
            color = "green"
        elif completeness >= 70:
            status = "⚠ WARN"
            color = "yellow"
        else:
            status = "✗ BAD"
            color = "red"
        
        feature_status.append((feature, status, completeness))
        print(f"{status:8} {feature:<30} {completeness:>6.1f}% - {description}")
    else:
        print(f"✗ MISSING {feature:<30} {'0.0':>6}% - {description}")
        feature_status.append((feature, "✗ MISSING", 0))

# Target variable analysis
print("\n[5/7] Target Variable: 'Productive_dispatch'")
print("-"*80)

if 'Productive_dispatch' in df.columns:
    productive_counts = df['Productive_dispatch'].value_counts()
    productive_pct = df['Productive_dispatch'].value_counts(normalize=True) * 100
    
    print(f"Distribution:")
    for value in sorted(productive_counts.index):
        count = productive_counts[value]
        pct = productive_pct[value]
        label = "Success" if value == 1 else "Failure" if value == 0 else f"Value {value}"
        print(f"  {label:12} (value={value}): {count:>6,} records ({pct:>5.1f}%)")
    
    # Check for class imbalance
    if len(productive_counts) >= 2:
        majority = productive_counts.max()
        minority = productive_counts.min()
        imbalance_ratio = majority / minority if minority > 0 else float('inf')
        
        print(f"\nClass Balance:")
        print(f"  Imbalance Ratio: {imbalance_ratio:.2f}:1")
        
        if imbalance_ratio < 3:
            print(f"  Status: ✓ GOOD - Well balanced")
        elif imbalance_ratio < 5:
            print(f"  Status: ⚠ OK - Slight imbalance (manageable)")
        else:
            print(f"  Status: ✗ WARN - Significant imbalance (may need SMOTE/weighting)")
    
    # Missing values in target
    missing_target = df['Productive_dispatch'].isna().sum()
    if missing_target > 0:
        print(f"\n⚠ WARNING: {missing_target:,} records missing target value")
else:
    print("✗ CRITICAL: 'Productive_dispatch' column not found!")

# Skill distribution
print("\n[6/7] Skill Distribution")
print("-"*80)

if 'Required_skill' in df.columns:
    skill_counts = df['Required_skill'].value_counts()
    print(f"Total Unique Skills: {len(skill_counts)}")
    print(f"\nTop 10 Skills:")
    for skill, count in skill_counts.head(10).items():
        pct = (count / len(df)) * 100
        print(f"  {str(skill):<35} {count:>6,} ({pct:>5.1f}%)")
    
    if len(skill_counts) > 10:
        print(f"  ... and {len(skill_counts) - 10} more skills")
    
    # Check for skill diversity
    if len(skill_counts) >= 5:
        print(f"\n✓ Good skill diversity ({len(skill_counts)} unique skills)")
    elif len(skill_counts) >= 3:
        print(f"\n⚠ Limited skill diversity ({len(skill_counts)} unique skills)")
    else:
        print(f"\n✗ Very limited skill diversity ({len(skill_counts)} unique skills)")

# Data quality issues
print("\n[7/7] Data Quality Assessment")
print("-"*80)

issues = []
warnings = []
passes = []

# Check 1: Sufficient sample size
if len(df) >= 2000:
    passes.append(f"✓ Sample size: {len(df):,} records (excellent for ML)")
elif len(df) >= 1000:
    warnings.append(f"⚠ Sample size: {len(df):,} records (sufficient, but more is better)")
else:
    issues.append(f"✗ Sample size: {len(df):,} records (minimum 1000 recommended)")

# Check 2: Target variable presence and completeness
if 'Productive_dispatch' in df.columns:
    target_complete = (df['Productive_dispatch'].notna().sum() / len(df)) * 100
    if target_complete >= 95:
        passes.append(f"✓ Target variable: {target_complete:.1f}% complete")
    elif target_complete >= 80:
        warnings.append(f"⚠ Target variable: {target_complete:.1f}% complete (some missing)")
    else:
        issues.append(f"✗ Target variable: {target_complete:.1f}% complete (too many missing)")
else:
    issues.append("✗ Target variable 'Productive_dispatch' not found")

# Check 3: Key features completeness
key_features = ['Distance_km', 'Required_skill', 'Assigned_technician_id']
missing_features = [f for f in key_features if f not in df.columns]
if not missing_features:
    avg_completeness = np.mean([
        (df[f].notna().sum() / len(df)) * 100 
        for f in key_features
    ])
    if avg_completeness >= 90:
        passes.append(f"✓ Key features: {avg_completeness:.1f}% average completeness")
    elif avg_completeness >= 75:
        warnings.append(f"⚠ Key features: {avg_completeness:.1f}% average completeness")
    else:
        issues.append(f"✗ Key features: {avg_completeness:.1f}% average completeness")
else:
    issues.append(f"✗ Missing key features: {', '.join(missing_features)}")

# Check 4: Technician diversity
if 'Assigned_technician_id' in df.columns:
    tech_count = df['Assigned_technician_id'].nunique()
    if tech_count >= 50:
        passes.append(f"✓ Technician diversity: {tech_count} unique technicians")
    elif tech_count >= 20:
        warnings.append(f"⚠ Technician diversity: {tech_count} unique technicians (limited)")
    else:
        issues.append(f"✗ Technician diversity: {tech_count} unique technicians (very limited)")

# Check 5: Distance data quality
if 'Distance_km' in df.columns:
    valid_distance = df['Distance_km'].notna() & (df['Distance_km'] > 0) & (df['Distance_km'] < 10000)
    valid_pct = (valid_distance.sum() / len(df)) * 100
    if valid_pct >= 90:
        passes.append(f"✓ Distance data: {valid_pct:.1f}% valid")
    elif valid_pct >= 70:
        warnings.append(f"⚠ Distance data: {valid_pct:.1f}% valid (some outliers)")
    else:
        issues.append(f"✗ Distance data: {valid_pct:.1f}% valid (many outliers/missing)")

# Check 6: Duplicate records
duplicates = df.duplicated(subset=['Dispatch_id']).sum() if 'Dispatch_id' in df.columns else 0
if duplicates == 0:
    passes.append(f"✓ No duplicate dispatch IDs")
elif duplicates < len(df) * 0.01:
    warnings.append(f"⚠ {duplicates} duplicate dispatch IDs (<1%)")
else:
    issues.append(f"✗ {duplicates} duplicate dispatch IDs (>{1}%)")

# Print results
print("\n✓ PASSES:")
for p in passes:
    print(f"  {p}")

if warnings:
    print("\n⚠ WARNINGS:")
    for w in warnings:
        print(f"  {w}")

if issues:
    print("\n✗ CRITICAL ISSUES:")
    for i in issues:
        print(f"  {i}")

# Final recommendation
print("\n" + "="*80)
print("FINAL RECOMMENDATION")
print("="*80)

if not issues:
    if not warnings:
        print("\n✅ EXCELLENT - Dataset is highly suitable for ML training!")
        print("\nRecommendation:")
        print("  - Proceed with ML model training")
        print("  - Use ENABLE_ENHANCED_SUCCESS_MODEL = True (if you have 2000+ records)")
        print("  - Expected model performance: High accuracy")
    else:
        print("\n✅ GOOD - Dataset is suitable for ML training with minor caveats")
        print("\nRecommendation:")
        print("  - Proceed with ML model training")
        print("  - Use ENABLE_ENHANCED_SUCCESS_MODEL = False (basic model)")
        print("  - Monitor model performance closely")
        print("  - Address warnings if possible")
elif len(issues) <= 2 and len(passes) >= 4:
    print("\n⚠️ ACCEPTABLE - Dataset can be used but with limitations")
    print("\nRecommendation:")
    print("  - Can proceed but fix critical issues first")
    print("  - Use ENABLE_ENHANCED_SUCCESS_MODEL = False")
    print("  - Consider data cleaning/augmentation")
    print("  - Monitor model performance very closely")
else:
    print("\n❌ NOT RECOMMENDED - Dataset has too many issues for reliable ML training")
    print("\nRecommendation:")
    print("  - Fix critical issues before training")
    print("  - Consider using business rules only")
    print("  - Collect more/better quality data")

# Training readiness score
total_checks = len(passes) + len(warnings) + len(issues)
score = (len(passes) * 3 + len(warnings) * 1) / (total_checks * 3) * 100 if total_checks > 0 else 0

print(f"\nTraining Readiness Score: {score:.0f}/100")

if score >= 80:
    print("Rating: ⭐⭐⭐⭐⭐ Excellent")
elif score >= 60:
    print("Rating: ⭐⭐⭐⭐ Good")
elif score >= 40:
    print("Rating: ⭐⭐⭐ Acceptable")
elif score >= 20:
    print("Rating: ⭐⭐ Poor")
else:
    print("Rating: ⭐ Very Poor")

print("\n" + "="*80)
print("Evaluation complete!")
print("="*80)

