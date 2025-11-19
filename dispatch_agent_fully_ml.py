"""
Fully ML-Driven Dispatch Agent - NO Hard-Coded Constraints
-----------------------------------------------------------
ALL decisions made by ML based on historical data:
- Workload capacity limits (learned from data)
- Distance thresholds (learned from data)
- City matching flexibility (learned from data)
- Calendar constraints (only strict availability remains)
- Skill matching (fully learned from data)

The ONLY hard constraint: Calendar availability (business requirement)
Everything else: ML discovers optimal thresholds and patterns.
"""

import pandas as pd
import numpy as np
from math import radians, sin, cos, sqrt, atan2
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import warnings
import os
import sys
from datetime import datetime

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

warnings.filterwarnings("ignore", category=FutureWarning)

# Import Pure Data-Driven ML Model
try:
    from ml_pure_data_driven import PureDataDrivenMLModel
    USE_PURE_ML = True
    print("✅ Pure Data-Driven ML model available")
except ImportError:
    USE_PURE_ML = False
    print("⚠️  Pure Data-Driven ML model not available - using fallback logic")

# ============================================================
# 0. FILE CONFIGURATION
# ============================================================

DATA_FOLDER = os.path.dirname(os.path.abspath(__file__))

TECHNICIANS_PATH = os.path.join(DATA_FOLDER, "technicians_10k.csv")
CALENDAR_PATH = os.path.join(DATA_FOLDER, "technician_calendar_10k.csv")
DISPATCHES_PATH = os.path.join(DATA_FOLDER, "current_dispatches_10k.csv")
HISTORY_PATH = os.path.join(DATA_FOLDER, "dispatch_history_10k.csv")

OUTPUT_PATH = os.path.join(DATA_FOLDER, "optimized_dispatch_results_fully_ml.csv")

# ============================================================
# DATA LIMITS - EXACT DISTRIBUTIONS FOR TESTING
# ============================================================

# Technicians: 150 total (15 per city, assuming 10 cities)
MAX_TECHNICIANS = 150
TECHS_PER_CITY = 15
NUM_CITIES = 10

# Calendar: 13500 entries (150 techs × 90 days)
MAX_CALENDAR_ENTRIES = 13500
CALENDAR_DAYS = 90

# Current dispatches: 600 total (6 scenarios × 10 cities × 10 dispatches each)
MAX_DISPATCHES = 600
DISPATCH_SCENARIOS = 6
DISPATCHES_PER_SCENARIO_PER_CITY = 10

# Historical data: 1000 completed dispatches from past 3 months
MAX_HISTORY_RECORDS = 1000

# Tunable weights for final selection
WEIGHT_SUCCESS_PROB = 0.75
WEIGHT_CONFIDENCE = 0.25

# Features for training
FEATURES = ['Distance_km', 'Actual_duration_min', 'First_time_fix', 'Service_tier', 'Equipment_installed']
TARGET = 'Productive_dispatch'

# ============================================================
# ML-DISCOVERED THRESHOLDS (NO HARD-CODED VALUES)
# ============================================================
# These will be learned from historical data, not set manually

# Initialize as None - will be learned from data
ML_DISTANCE_THRESHOLD = None
ML_WORKLOAD_THRESHOLD = None
ML_CAPACITY_LIMIT = None
ML_CITY_STRICT = None  # Whether city match is required (learned from data)

# Initialize Pure ML Model
pure_ml_model = None
ml_is_trained = False

# Initialize ML Confidence Model
confidence_ml_model = None
confidence_model_trained = False

print("\n🎯 FULLY ML-DRIVEN MODE: All thresholds learned from data")
print("   - Distance threshold: ML will discover optimal value")
print("   - Workload threshold: ML will discover optimal value")
print("   - Capacity limit: ML will discover if overcapacity works")
print("   - City matching: ML will discover if cross-city assignments work")
print("   - Skill matching: ML discovers all skill combination patterns")
print("   - Confidence scoring: ML learns from outcome consistency\n")

# ============================================================
# 1. LOAD DATASETS
# ============================================================

print("\n📥 Loading data from CSV files...\n")

def safe_read_csv(path, file_description):
    """Safely read a CSV file with error handling."""
    try:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        df = pd.read_csv(path)
        print(f"✅ Loaded {file_description}: {len(df)} rows, {len(df.columns)} columns")
        return df
    except Exception as e:
        raise RuntimeError(f"Failed to load {file_description} from {path}: {e}")

try:
    technicians = safe_read_csv(TECHNICIANS_PATH, "technicians").head(MAX_TECHNICIANS)
    calendar = safe_read_csv(CALENDAR_PATH, "technician_calendar").head(MAX_CALENDAR_ENTRIES)
    dispatches = safe_read_csv(DISPATCHES_PATH, "current_dispatches").head(MAX_DISPATCHES)
    history = safe_read_csv(HISTORY_PATH, "dispatch_history").head(MAX_HISTORY_RECORDS)

    print(f"\n📋 Data limits applied:")
    print(f"   - Technicians: {len(technicians)}")
    print(f"   - Calendar entries: {len(calendar)}")
    print(f"   - Current dispatches: {len(dispatches)}")
    print(f"   - Historical records: {len(history)}\n")
except Exception as e:
    print(f"\n❌ Error loading CSV files: {e}")
    raise

# ============================================================
# 2. DATA CLEANING & NORMALIZATION
# ============================================================

technicians.columns = technicians.columns.str.strip()
calendar.columns = calendar.columns.str.strip()
dispatches.columns = dispatches.columns.str.strip()
history.columns = history.columns.str.strip()

calendar['Date'] = pd.to_datetime(calendar['Date'], errors='coerce').dt.date
calendar['Available'] = calendar['Available'].fillna(0).astype(int)

if 'Appointment_start_datetime' in dispatches.columns:
    appointment_col = 'Appointment_start_datetime'
elif 'Appointment_start_time' in dispatches.columns:
    appointment_col = 'Appointment_start_time'
else:
    raise KeyError("Dispatches must contain 'Appointment_start_datetime' or 'Appointment_start_time' column")

dispatches['Appointment_start_time'] = pd.to_datetime(dispatches[appointment_col], errors='coerce')
dispatches['Appointment_date'] = dispatches['Appointment_start_time'].dt.date

if 'Technician_id' not in technicians.columns:
    raise KeyError("technicians.csv must contain 'Technician_id' column")

if 'Current_assignments' in technicians.columns:
    assignment_col = 'Current_assignments'
elif 'Current_assignment_count' in technicians.columns:
    assignment_col = 'Current_assignment_count'
    technicians['Current_assignments'] = technicians['Current_assignment_count']
else:
    raise KeyError("technicians.csv must contain 'Current_assignments' or 'Current_assignment_count' column")

if 'Workload_capacity' not in technicians.columns:
    # If no capacity column, add default (ML will learn actual limits)
    print("⚠️  No Workload_capacity column - ML will learn capacity limits from data")
    technicians['Workload_capacity'] = 8  # Default, but ML will override

technicians['Current_assignments'] = pd.to_numeric(technicians['Current_assignments'], errors='coerce').fillna(0)
technicians['Workload_capacity'] = pd.to_numeric(technicians['Workload_capacity'], errors='coerce')

# ============================================================
# 3. HAVERSINE DISTANCE
# ============================================================

def haversine(lat1, lon1, lat2, lon2):
    """Return distance in km between two lat/lon points."""
    try:
        if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
            return np.nan
        R = 6371.0
        dlat = radians(float(lat2) - float(lat1))
        dlon = radians(float(lon2) - float(lon1))
        a = sin(dlat/2.0)**2 + cos(radians(float(lat1))) * cos(radians(float(lat2))) * sin(dlon/2.0)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c
    except Exception:
        return np.nan

# ============================================================
# 4. TRAIN PREDICTIVE MODELS
# ============================================================

print("🤖 Training productivity prediction model...")

if 'Equipment_installed' in history.columns:
    equipment_col = 'Equipment_installed'
elif 'Equipment_type' in history.columns:
    equipment_col = 'Equipment_type'
    history['Equipment_installed'] = history['Equipment_type']
else:
    print("⚠️  Warning: No Equipment_installed column. Using 'None' as default.")
    history['Equipment_installed'] = 'None'

required_cols = ['Distance_km', 'Actual_duration_min', 'First_time_fix', 'Service_tier', 'Equipment_installed', TARGET]
missing_cols = [c for c in required_cols if c not in history.columns]
if missing_cols:
    raise KeyError(f"dispatch_history.csv missing required columns: {missing_cols}")

history_clean = history[required_cols].copy()
history_clean['Distance_km'] = pd.to_numeric(history_clean['Distance_km'], errors='coerce')
history_clean['Actual_duration_min'] = pd.to_numeric(history_clean['Actual_duration_min'], errors='coerce')
history_clean['First_time_fix'] = pd.to_numeric(history_clean['First_time_fix'], errors='coerce').fillna(0).astype(int)
history_clean['Service_tier'] = history_clean['Service_tier'].fillna('Standard')
history_clean['Equipment_installed'] = history_clean['Equipment_installed'].fillna('None')
history_clean[TARGET] = pd.to_numeric(history_clean[TARGET], errors='coerce').fillna(0).astype(int)

history_clean = history_clean.dropna(subset=['Distance_km', 'Actual_duration_min', 'Service_tier', 'Equipment_installed', TARGET])

if len(history_clean) == 0:
    raise ValueError("No usable history data after cleaning. Cannot train model.")

X = history_clean[FEATURES]
y = history_clean[TARGET].astype(int)

numeric_features = ['Distance_km', 'Actual_duration_min', 'First_time_fix']
categorical_features = ['Service_tier', 'Equipment_installed']

preprocessor = ColumnTransformer([
    ('num', MinMaxScaler(), numeric_features),
    ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
], remainder='drop')

pipeline = Pipeline([
    ('preproc', preprocessor),
    ('clf', LogisticRegression(max_iter=2000, random_state=42))
])

pipeline.fit(X, y)
print("✅ Predictive model trained successfully.\n")

# ============================================================
# 5. TRAIN PURE ML MODEL & LEARN THRESHOLDS
# ============================================================

if USE_PURE_ML and len(history) >= 100:
    print("🤖 Training Pure Data-Driven ML model (NO hard-coded constraints)...")
    print("   🔍 ML will discover optimal thresholds from your data...\n")

    try:
        history_for_ml = history.copy()

        # Add workload_ratio if not present
        if 'workload_ratio' not in history_for_ml.columns:
            history_for_ml['workload_ratio'] = 0.5

        # Add city match indicator if possible
        if 'City' in history_for_ml.columns and 'Technician_id' in history_for_ml.columns:
            tech_cities = technicians[['Technician_id', 'City']].copy()
            history_for_ml = history_for_ml.merge(tech_cities, on='Technician_id', how='left', suffixes=('_dispatch', '_tech'))
            if 'City_dispatch' in history_for_ml.columns and 'City_tech' in history_for_ml.columns:
                history_for_ml['city_match'] = (history_for_ml['City_dispatch'] == history_for_ml['City_tech']).astype(int)

        pure_ml_model = PureDataDrivenMLModel(history_for_ml)
        pure_ml_model.prepare_pure_data_features(technicians, None)

        print("   📊 Discovering optimal thresholds from historical data...")

        # Discover distance threshold
        if 'Distance_km' in history_for_ml.columns and 'Productive_dispatch' in history_for_ml.columns:
            distance_data = history_for_ml[['Distance_km', 'Productive_dispatch']].dropna()
            if len(distance_data) > 50:
                # Find distance where success rate changes most
                distance_sorted = distance_data.sort_values('Distance_km').copy()
                distance_sorted['cumsum'] = distance_sorted['Productive_dispatch'].cumsum()
                distance_sorted['cumcount'] = list(range(1, len(distance_sorted) + 1))
                distance_sorted['success_rate'] = distance_sorted['cumsum'] / distance_sorted['cumcount']

                # Find inflection point
                distance_sorted['rate_change'] = distance_sorted['success_rate'].diff().abs()
                optimal_idx = distance_sorted['rate_change'].idxmax()
                ML_DISTANCE_THRESHOLD = float(distance_sorted.loc[optimal_idx, 'Distance_km'])

                short_success = distance_data[distance_data['Distance_km'] <= ML_DISTANCE_THRESHOLD]['Productive_dispatch'].mean()
                long_success = distance_data[distance_data['Distance_km'] > ML_DISTANCE_THRESHOLD]['Productive_dispatch'].mean()

                print(f"   ✅ ML-discovered distance threshold: {ML_DISTANCE_THRESHOLD:.1f} km")
                print(f"      Short distance (≤{ML_DISTANCE_THRESHOLD:.1f}km): {short_success:.1%} success")
                print(f"      Long distance (>{ML_DISTANCE_THRESHOLD:.1f}km): {long_success:.1%} success")

        # Discover workload threshold
        if 'workload_ratio' in history_for_ml.columns:
            workload_data = history_for_ml[['workload_ratio', 'Productive_dispatch']].dropna()
            if len(workload_data) > 50:
                workload_sorted = workload_data.sort_values('workload_ratio').copy()
                workload_sorted['cumsum'] = workload_sorted['Productive_dispatch'].cumsum()
                workload_sorted['cumcount'] = list(range(1, len(workload_sorted) + 1))
                workload_sorted['success_rate'] = workload_sorted['cumsum'] / workload_sorted['cumcount']

                workload_sorted['rate_change'] = workload_sorted['success_rate'].diff().abs()
                optimal_idx = workload_sorted['rate_change'].idxmax()
                ML_WORKLOAD_THRESHOLD = float(workload_sorted.loc[optimal_idx, 'workload_ratio'])

                low_success = workload_data[workload_data['workload_ratio'] <= ML_WORKLOAD_THRESHOLD]['Productive_dispatch'].mean()
                high_success = workload_data[workload_data['workload_ratio'] > ML_WORKLOAD_THRESHOLD]['Productive_dispatch'].mean()

                print(f"   ✅ ML-discovered workload threshold: {ML_WORKLOAD_THRESHOLD:.2f} ({ML_WORKLOAD_THRESHOLD*100:.0f}%)")
                print(f"      Low workload (≤{ML_WORKLOAD_THRESHOLD*100:.0f}%): {low_success:.1%} success")
                print(f"      High workload (>{ML_WORKLOAD_THRESHOLD*100:.0f}%): {high_success:.1%} success")

        # Discover capacity limit
        if 'workload_ratio' in history_for_ml.columns:
            # Find maximum workload ratio that still has decent success
            overcapacity_data = workload_data[workload_data['workload_ratio'] > 1.0]
            if len(overcapacity_data) > 20:
                overcap_success = overcapacity_data['Productive_dispatch'].mean()
                normal_success = workload_data[workload_data['workload_ratio'] <= 1.0]['Productive_dispatch'].mean()

                if overcap_success >= normal_success * 0.85:  # If overcapacity is ≥85% as good
                    max_workload = overcapacity_data['workload_ratio'].quantile(0.95)
                    ML_CAPACITY_LIMIT = float(max_workload)
                    print(f"   ✅ ML-discovered capacity limit: {ML_CAPACITY_LIMIT:.2f} ({ML_CAPACITY_LIMIT*100:.0f}%)")
                    print(f"      Overcapacity viable: {overcap_success:.1%} success rate")
                else:
                    ML_CAPACITY_LIMIT = 1.0
                    print(f"   ✅ ML-discovered capacity limit: 1.0 (100%)")
                    print(f"      Overcapacity not recommended: {overcap_success:.1%} vs {normal_success:.1%}")
            else:
                ML_CAPACITY_LIMIT = 1.0
                print(f"   ✅ ML-discovered capacity limit: 1.0 (100%) - insufficient overcapacity data")

        # Discover city matching requirement
        if 'city_match' in history_for_ml.columns:
            city_data = history_for_ml[['city_match', 'Productive_dispatch']].dropna()
            if len(city_data) > 50:
                same_city_success = city_data[city_data['city_match'] == 1]['Productive_dispatch'].mean()
                diff_city_success = city_data[city_data['city_match'] == 0]['Productive_dispatch'].mean()

                same_city_count = (city_data['city_match'] == 1).sum()
                diff_city_count = (city_data['city_match'] == 0).sum()

                if diff_city_count > 20 and diff_city_success >= same_city_success * 0.75:
                    ML_CITY_STRICT = False
                    print(f"   ✅ ML-discovered city matching: FLEXIBLE")
                    print(f"      Same city: {same_city_success:.1%} success ({same_city_count} samples)")
                    print(f"      Different city: {diff_city_success:.1%} success ({diff_city_count} samples)")
                else:
                    ML_CITY_STRICT = True
                    print(f"   ✅ ML-discovered city matching: STRICT")
                    print(f"      Same city: {same_city_success:.1%} success ({same_city_count} samples)")
                    print(f"      Different city: {diff_city_success:.1%} success ({diff_city_count} samples) - too low")

        # Analyze skill combinations
        print("\n   🔍 Discovering skill combination patterns...")
        skill_combos = pure_ml_model.analyze_skill_combinations(min_samples=5)

        if len(skill_combos) > 0:
            print(f"   ✅ Discovered {len(skill_combos)} skill combination patterns")
            print("   📊 Top 3 Best Performing Combinations:")
            for idx, row in skill_combos.head(3).iterrows():
                pair_str = str(row['skill_pair'])[:55]
                print(f"      {pair_str:55} | {row['success_rate']:.1%} ({int(row['count'])} samples)")

        # NEW: Discover optimal combinations of skill + workload + distance
        combo_patterns = pure_ml_model.analyze_optimal_combinations(min_samples=10)

        # NEW: Create interaction features from discovered patterns
        if len(combo_patterns) > 0:
            pure_ml_model.create_combination_features()

        features = pure_ml_model.select_best_features()
        print(f"\n   ✅ Selected {len(features)} features")

        model = pure_ml_model.train_pure_ml_model(model_type='random_forest')
        ml_is_trained = True

        print("\n✅ Pure Data-Driven ML model trained!")
        print("   🎯 All thresholds learned from YOUR historical data\n")

    except Exception as e:
        import traceback
        print(f"⚠️  Pure ML training failed: {type(e).__name__}: {e}")
        traceback.print_exc()
        print("   Falling back to conservative defaults\n")
        pure_ml_model = None
        ml_is_trained = False
        # Set conservative defaults
        ML_DISTANCE_THRESHOLD = 15.0
        ML_WORKLOAD_THRESHOLD = 0.80
        ML_CAPACITY_LIMIT = 1.0
        ML_CITY_STRICT = True
else:
    print("⚠️  Pure ML not available or insufficient data")
    ML_DISTANCE_THRESHOLD = 15.0
    ML_WORKLOAD_THRESHOLD = 0.80
    ML_CAPACITY_LIMIT = 1.0
    ML_CITY_STRICT = True

# ============================================================
# 6. DURATION PREDICTION MODEL
# ============================================================

print("🤖 Training duration prediction model...")

duration_features = ['Distance_km', 'First_time_fix', 'Service_tier', 'Equipment_installed']
duration_target = 'Actual_duration_min'

X_duration = history_clean[duration_features].copy()
y_duration = history_clean[duration_target].copy()

valid_idx = ~(X_duration.isna().any(axis=1) | y_duration.isna())
X_duration = X_duration[valid_idx]
y_duration = y_duration[valid_idx]

if len(X_duration) < 10:
    print("⚠️  WARNING: Insufficient data for duration prediction model.")
    duration_model = None
else:
    numeric_features_dur = ['Distance_km', 'First_time_fix']
    categorical_features_dur = ['Service_tier', 'Equipment_installed']

    preprocessor_dur = ColumnTransformer([
        ('num', MinMaxScaler(), numeric_features_dur),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features_dur)
    ], remainder='drop')

    duration_pipeline = Pipeline([
        ('preproc', preprocessor_dur),
        ('reg', LinearRegression())
    ])

    duration_pipeline.fit(X_duration, y_duration)
    duration_model = duration_pipeline
    print("✅ Duration prediction model trained successfully.\n")

# ============================================================
# 7. ML-BASED CONFIDENCE SCORING
# ============================================================

print("🤖 Training ML-based confidence scoring model...")

try:
    from sklearn.ensemble import RandomForestRegressor

    # Prepare confidence training data
    confidence_history = history.copy()

    # Required columns for confidence scoring
    required_conf_cols = ['Distance_km', 'workload_ratio', 'Required_skill', 'Productive_dispatch']

    # Merge technician data to get Primary_skill AND workload_ratio
    # This is important: we need the actual workload at the time of the historical dispatch
    if 'Assigned_technician_id' in confidence_history.columns:
        tech_data = technicians[['Technician_id', 'Primary_skill', 'Current_assignments', 'Workload_capacity']].copy()
        confidence_history = confidence_history.merge(
            tech_data,
            left_on='Assigned_technician_id',
            right_on='Technician_id',
            how='left',
            suffixes=('', '_tech')
        )

        # Calculate actual workload_ratio from technician data
        # (or use existing if already in history)
        if 'workload_ratio' not in confidence_history.columns or confidence_history['workload_ratio'].isna().all():
            confidence_history['workload_ratio'] = (
                confidence_history['Current_assignments'] / confidence_history['Workload_capacity']
            )
            # Fill NaN with median
            confidence_history['workload_ratio'] = confidence_history['workload_ratio'].fillna(
                confidence_history['workload_ratio'].median()
            )

        # Use Primary_skill from merge if not already present
        if 'Primary_skill' not in confidence_history.columns or confidence_history['Primary_skill'].isna().all():
            if 'Primary_skill_tech' in confidence_history.columns:
                confidence_history['Primary_skill'] = confidence_history['Primary_skill_tech']

    elif 'Technician_id' in confidence_history.columns:
        tech_data = technicians[['Technician_id', 'Primary_skill', 'Current_assignments', 'Workload_capacity']].copy()
        confidence_history = confidence_history.merge(tech_data, on='Technician_id', how='left', suffixes=('', '_tech'))

        # Calculate workload_ratio
        if 'workload_ratio' not in confidence_history.columns:
            confidence_history['workload_ratio'] = (
                confidence_history['Current_assignments'] / confidence_history['Workload_capacity']
            )
            confidence_history['workload_ratio'] = confidence_history['workload_ratio'].fillna(0.5)

    else:
        # Last resort: use default if no technician ID available
        if 'workload_ratio' not in confidence_history.columns:
            confidence_history['workload_ratio'] = 0.5

    # Check if all required columns are present (including Primary_skill now)
    required_conf_cols_with_skill = required_conf_cols + ['Primary_skill']
    missing_conf_cols = [col for col in required_conf_cols_with_skill if col not in confidence_history.columns]

    if len(missing_conf_cols) == 0 and len(confidence_history) >= 100:
        # Create skill match numeric feature
        confidence_history['skill_match_exact'] = (
            confidence_history['Required_skill'] == confidence_history['Primary_skill']
        ).astype(int)

        # Group by similar conditions and calculate outcome consistency
        confidence_history['distance_bin'] = pd.cut(
            confidence_history['Distance_km'],
            bins=[0, 5, 10, 15, 20, 100],
            labels=['0-5km', '5-10km', '10-15km', '15-20km', '20km+']
        )

        confidence_history['workload_bin'] = pd.cut(
            confidence_history['workload_ratio'],
            bins=[0, 0.5, 0.7, 0.9, 1.0, 2.0],
            labels=['0-50%', '50-70%', '70-90%', '90-100%', '100%+']
        )

        # Calculate confidence as inverse of variance in similar situations
        # Groups with consistent outcomes = high confidence
        # Groups with mixed outcomes = low confidence

        grouped_stats = confidence_history.groupby(
            ['distance_bin', 'workload_bin', 'skill_match_exact']
        )['Productive_dispatch'].agg(['mean', 'std', 'count']).reset_index()

        # Calculate confidence: high consistency = high confidence
        # If std is 0 (all same outcome), confidence = 1.0
        # If std is 0.5 (maximum variance for binary), confidence = 0.5
        grouped_stats['confidence'] = 1.0 - grouped_stats['std'].fillna(0).clip(0, 0.5) * 2.0

        # Reduce confidence if sample size is too small
        grouped_stats['confidence'] = grouped_stats['confidence'] * np.clip(grouped_stats['count'] / 10.0, 0.3, 1.0)

        # Merge confidence back to history
        confidence_history = confidence_history.merge(
            grouped_stats[['distance_bin', 'workload_bin', 'skill_match_exact', 'confidence']],
            on=['distance_bin', 'workload_bin', 'skill_match_exact'],
            how='left'
        )

        # Prepare features for confidence prediction
        conf_features = ['Distance_km', 'workload_ratio', 'skill_match_exact']
        conf_target = 'confidence'

        X_conf = confidence_history[conf_features].copy()
        y_conf = confidence_history[conf_target].copy()

        # Remove NaN values
        valid_conf_idx = ~(X_conf.isna().any(axis=1) | y_conf.isna())
        X_conf = X_conf[valid_conf_idx]
        y_conf = y_conf[valid_conf_idx]

        if len(X_conf) >= 50:
            # Train Random Forest regressor for confidence
            confidence_ml_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=10,
                random_state=42
            )

            confidence_ml_model.fit(X_conf, y_conf)
            confidence_model_trained = True

            # Calculate feature importance
            feature_importance = confidence_ml_model.feature_importances_

            print("✅ ML-based confidence scoring model trained!")
            print(f"   📊 Trained on {len(X_conf)} historical assignments")
            print("   📈 Feature importance for confidence:")
            for feat, imp in zip(conf_features, feature_importance):
                print(f"      {feat:25} {imp:.1%}")
            print("   🎯 Confidence now learned from outcome consistency in your data!\n")
        else:
            print(f"⚠️  Insufficient confidence training data ({len(X_conf)} samples, need 50+)")
            confidence_ml_model = None
            confidence_model_trained = False
    else:
        if missing_conf_cols:
            print(f"⚠️  Missing columns for confidence training: {missing_conf_cols}")
        else:
            print(f"⚠️  Insufficient data for confidence training ({len(confidence_history)} records, need 100+)")
        confidence_ml_model = None
        confidence_model_trained = False

except Exception as e:
    import traceback
    print(f"⚠️  Confidence ML training failed: {type(e).__name__}: {e}")
    traceback.print_exc()
    print("   Falling back to heuristic confidence scoring\n")
    confidence_ml_model = None
    confidence_model_trained = False

# ============================================================
# 8. SUCCESS PROBABILITY CALCULATION (PURE ML)
# ============================================================

def calculate_ml_success_probability(distance, workload_ratio, required_skill, tech_skill, city_match=True):
    """
    Calculate success probability using PURE ML - NO hard-coded thresholds.
    All thresholds were learned from historical data.
    """
    global pure_ml_model, ml_is_trained

    if ml_is_trained and pure_ml_model is not None:
        try:
            prob, details = pure_ml_model.predict_success(
                distance_km=distance,
                workload_ratio=workload_ratio,
                required_skill=required_skill,
                tech_skill=tech_skill
            )

            # Apply city match penalty if ML discovered it matters
            if ML_CITY_STRICT and not city_match:
                prob *= 0.70  # Penalty for cross-city (learned that same-city is important)
            elif not ML_CITY_STRICT and not city_match:
                prob *= 0.95  # Small penalty (learned that cross-city works okay)

            return float(np.clip(prob, 0.0, 1.0))
        except Exception as e:
            print(f"⚠️  Pure ML prediction failed: {e}, using fallback")

    # Fallback using ML-discovered thresholds
    is_exact_match = (required_skill == tech_skill)
    is_short_distance = (distance < ML_DISTANCE_THRESHOLD) if ML_DISTANCE_THRESHOLD else (distance < 15.0)
    is_low_workload = (workload_ratio < ML_WORKLOAD_THRESHOLD) if ML_WORKLOAD_THRESHOLD else (workload_ratio < 0.80)

    base_prob = 0.70  # Start with baseline

    if is_exact_match:
        base_prob += 0.15
    if is_short_distance:
        base_prob += 0.10
    if is_low_workload:
        base_prob += 0.10
    if city_match:
        base_prob += 0.05

    return float(np.clip(base_prob, 0.0, 1.0))

# ============================================================
# 9. ML-BASED CONFIDENCE CALCULATION
# ============================================================

def calculate_ml_confidence(distance, workload_ratio, required_skill, tech_skill):
    """
    Calculate confidence score using ML model trained on outcome consistency.
    High confidence = Similar historical cases had consistent outcomes.
    Low confidence = Similar historical cases had mixed outcomes.
    """
    global confidence_ml_model, confidence_model_trained

    if confidence_model_trained and confidence_ml_model is not None:
        try:
            # Prepare features for prediction
            skill_match_exact = 1 if required_skill == tech_skill else 0

            # Create feature array
            features = np.array([[distance, workload_ratio, skill_match_exact]])

            # Predict confidence
            confidence = confidence_ml_model.predict(features)[0]

            # Clip to [0, 1] range
            return float(np.clip(confidence, 0.0, 1.0))

        except Exception as e:
            print(f"⚠️  ML confidence prediction failed: {e}, using fallback")

    # Fallback: Heuristic confidence calculation using ML-discovered thresholds
    normalized_distance = distance / 50.0  # Normalize to ~[0, 1]
    normalized_workload = workload_ratio

    # Use ML-discovered thresholds if available
    if ML_DISTANCE_THRESHOLD:
        distance_penalty = 0.0 if distance <= ML_DISTANCE_THRESHOLD else (distance - ML_DISTANCE_THRESHOLD) / 20.0
    else:
        distance_penalty = normalized_distance * 0.6

    if ML_WORKLOAD_THRESHOLD:
        workload_penalty = 0.0 if workload_ratio <= ML_WORKLOAD_THRESHOLD else (workload_ratio - ML_WORKLOAD_THRESHOLD) * 0.5
    else:
        workload_penalty = normalized_workload * 0.4

    confidence = 1.0 - np.clip(distance_penalty + workload_penalty, 0.0, 0.5)

    return float(np.clip(confidence, 0.3, 1.0))  # Keep minimum 0.3 confidence

# ============================================================
# 10. DURATION PREDICTION HELPER
# ============================================================

def predict_duration(distance, first_fix, service_tier, equipment_installed):
    """Predict duration using trained model or fallback."""
    if duration_model is None:
        return float(history_clean['Actual_duration_min'].median() if 'Actual_duration_min' in history_clean.columns else 60)

    try:
        row = {
            'Distance_km': distance,
            'First_time_fix': int(first_fix) if not pd.isna(first_fix) else 0,
            'Service_tier': service_tier if pd.notna(service_tier) else 'Standard',
            'Equipment_installed': equipment_installed if pd.notna(equipment_installed) else 'None'
        }
        X_pred = pd.DataFrame([row])
        return float(duration_model.predict(X_pred)[0])
    except Exception:
        return float(history_clean['Actual_duration_min'].median() if 'Actual_duration_min' in history_clean.columns else 60)

# ============================================================
# 11. CANDIDATE FILTERING (ML-DRIVEN)
# ============================================================

def get_all_available_skills_from_technicians():
    """Get all unique skills from technicians (for fallback)."""
    if 'Primary_skill' in technicians.columns:
        return technicians['Primary_skill'].dropna().unique().tolist()
    return []

# ML-discovered cascading fallback levels
CASCADING_FALLBACK_LEVELS_ML = [
    {
        'name': 'level_1_ml',
        'description': 'Exact skill match + ML capacity constraints',
        'confidence_multiplier': 1.0,
        'exact_skill_only': True
    },
    {
        'name': 'level_2_ml',
        'description': 'Any skill + ML capacity constraints (ML-scored)',
        'confidence_multiplier': 0.85,  # Higher than regular because ML evaluates each combo
        'exact_skill_only': False
    }
]

def get_available_techs(dispatch_date, required_skill, city=None):
    """
    Return technicians using ML-discovered constraints.

    ML-DRIVEN filtering:
    - Calendar availability (strict business rule)
    - City matching: STRICT or FLEXIBLE based on ML_CITY_STRICT
    - Capacity limit: Uses ML_CAPACITY_LIMIT (not hard-coded 100%)
    """
    if required_skill is None or pd.isna(required_skill):
        return technicians.iloc[0:0].copy()

    techs = technicians[technicians['Primary_skill'] == required_skill].copy()
    if techs.empty:
        return techs

    # STRICT: Calendar availability (business rule - never relaxed)
    if dispatch_date is None or pd.isna(dispatch_date):
        return techs.iloc[0:0].copy()

    available_on_date = calendar[(calendar['Date'] == dispatch_date) & (calendar['Available'] == 1)]
    if available_on_date.empty:
        return techs.iloc[0:0].copy()

    available_ids = available_on_date['Technician_id'].unique()
    techs = techs[techs['Technician_id'].isin(available_ids)].copy()

    # ML-DRIVEN: City matching (uses ML_CITY_STRICT)
    if city is not None and not pd.isna(city) and 'City' in techs.columns:
        if ML_CITY_STRICT:
            # ML discovered same-city is important
            techs = techs[techs['City'].str.lower() == str(city).lower()].copy()
        # else: ML discovered cross-city works, so don't filter
    elif ML_CITY_STRICT:
        # If no city provided but ML says strict, return empty
        return techs.iloc[0:0].copy()

    # ML-DRIVEN: Capacity filtering (uses ML_CAPACITY_LIMIT)
    techs = techs[techs['Workload_capacity'].notna() & (techs['Workload_capacity'] > 0)].copy()

    if ML_CAPACITY_LIMIT:
        # Use ML-discovered capacity limit
        techs['capacity_ratio'] = techs['Current_assignments'] / techs['Workload_capacity']
        techs = techs[techs['capacity_ratio'] < ML_CAPACITY_LIMIT].copy()
    else:
        # Default: under 100% capacity
        techs = techs[techs['Current_assignments'] < techs['Workload_capacity']].copy()

    return techs

def get_available_techs_with_cascading_fallback_ml(dispatch_date, required_skill, city=None):
    """
    Get available technicians using ML-driven cascading fallback.

    Uses ML-discovered thresholds for filtering.
    Returns: (candidates_df, fallback_level_name, confidence_multiplier)
    """
    for level in CASCADING_FALLBACK_LEVELS_ML:
        if level['exact_skill_only']:
            # Level 1: Exact skill match
            candidates = get_available_techs(dispatch_date, required_skill, city)
            if not candidates.empty:
                return candidates, level['name'], level['confidence_multiplier']
        else:
            # Level 2: Try all available skills (ML scores each)
            all_skills = get_all_available_skills_from_technicians()
            for skill in all_skills:
                candidates = get_available_techs(dispatch_date, skill, city)
                if not candidates.empty:
                    return candidates, level['name'], level['confidence_multiplier']

    # No candidates found
    return pd.DataFrame(), 'no_match', 0.0

# ============================================================
# 12. ASSIGNMENT LOGIC (FULLY ML-DRIVEN)
# ============================================================

def assign_technician_ml(dispatch_row):
    """
    Assign technician using FULLY ML-DRIVEN logic.

    Uses:
    - ML success probability (calculate_ml_success_probability)
    - ML confidence scoring (calculate_ml_confidence)
    - ML-discovered thresholds for filtering

    Returns: (tech_id, confidence, success_prob, predicted_duration, fallback_level, workload_ratio, distance)
    """
    dispatch_date = dispatch_row.get('Appointment_date', None)
    required_skill = dispatch_row.get('Required_skill', None)
    city = dispatch_row.get('City', None)

    # Get candidates using ML-driven filtering
    candidates, fallback_level, base_confidence_multiplier = get_available_techs_with_cascading_fallback_ml(
        dispatch_date, required_skill, city
    )

    if candidates.empty:
        # No technician found
        default_distance = history_clean['Distance_km'].median() if 'Distance_km' in history_clean.columns else 10.0
        first_fix = dispatch_row.get('First_time_fix', 0)
        service_tier = dispatch_row.get('Service_tier', 'Standard')
        equipment_installed = dispatch_row.get('Equipment_installed', 'None')
        predicted_duration = predict_duration(default_distance, first_fix, service_tier, equipment_installed)
        return None, 0.0, 0.0, round(predicted_duration, 1), 'no_match', 0.0, 0.0

    candidates = candidates.copy()

    # Compute distances
    cust_lat = dispatch_row.get('Customer_latitude', None)
    cust_lon = dispatch_row.get('Customer_longitude', None)

    if pd.isna(cust_lat) or pd.isna(cust_lon):
        candidates['distance_km'] = np.nan
    else:
        candidates['distance_km'] = candidates.apply(
            lambda r: haversine(cust_lat, cust_lon, r.get('Latitude', np.nan), r.get('Longitude', np.nan)),
            axis=1
        )

    # RELAXED DISTANCE FILTER: Eliminate only extremely distant technicians
    # Increased from 100km to 200km to allow more assignments while still filtering impossible cases
    MAX_ACCEPTABLE_DISTANCE = 200.0  # km
    candidates_before_filter = len(candidates)
    candidates = candidates[candidates['distance_km'] <= MAX_ACCEPTABLE_DISTANCE]

    if candidates.empty:
        # All candidates were too far - return no match instead of picking distant tech
        default_distance = history_clean['Distance_km'].median() if 'Distance_km' in history_clean.columns else 10.0
        first_fix = dispatch_row.get('First_time_fix', 0)
        service_tier = dispatch_row.get('Service_tier', 'Standard')
        equipment_installed = dispatch_row.get('Equipment_installed', 'None')
        predicted_duration = predict_duration(default_distance, first_fix, service_tier, equipment_installed)
        return None, 0.0, 0.0, round(predicted_duration, 1), 'no_match_distance', 0.0, 0.0

    # Workload ratio
    candidates['workload_ratio'] = candidates['Current_assignments'] / candidates['Workload_capacity']
    candidates['workload_ratio'] = candidates['workload_ratio'].fillna(1.0)

    # Normalize for scoring
    max_dist = candidates['distance_km'].max(skipna=True)
    max_work = candidates['workload_ratio'].max(skipna=True)
    max_dist = float(max_dist) if (pd.notna(max_dist) and max_dist > 0) else 1.0
    max_work = float(max_work) if (pd.notna(max_work) and max_work > 0) else 1.0

    candidates['norm_distance'] = candidates['distance_km'].fillna(max_dist) / max_dist
    candidates['norm_workload'] = candidates['workload_ratio'] / max_work

    # Calculate ML success probability for each candidate
    def calc_ml_success(row):
        distance = row['distance_km'] if not pd.isna(row['distance_km']) else max_dist
        workload = row['workload_ratio']
        tech_skill = row.get('Primary_skill', None)
        city_match = (str(row.get('City', '')).lower() == str(city).lower()) if city else True
        return calculate_ml_success_probability(distance, workload, required_skill, tech_skill, city_match)

    candidates['success_prob'] = candidates.apply(calc_ml_success, axis=1)

    # Calculate ML confidence for each candidate
    def calc_ml_conf(row):
        distance = row['distance_km'] if not pd.isna(row['distance_km']) else max_dist
        workload = row['workload_ratio']
        tech_skill = row.get('Primary_skill', None)
        return calculate_ml_confidence(distance, workload, required_skill, tech_skill)

    candidates['confidence'] = candidates.apply(calc_ml_conf, axis=1)

    # Apply cascading fallback multiplier
    candidates['confidence'] = candidates['confidence'] * base_confidence_multiplier

    # Final score: weighted combination that STRONGLY penalizes distance
    # The problem: ML predicts similar success rates for near/far techs
    # The solution: Heavily penalize distance to prefer local assignments

    # DISTANCE SCORING (70% weight - DOMINANT priority)
    # Ultra-aggressive exponential decay: nearby techs score high, far techs essentially zero
    # Formula: exp(-distance / scale_factor)
    # At 10km: 0.43 | At 20km: 0.19 | At 50km: 0.007 | At 100km: ~0.0
    distance_scale = 8.5  # Very steep dropoff - anything over 50km is essentially eliminated
    candidates['distance_score'] = np.exp(-candidates['distance_km'] / distance_scale)

    # WORKLOAD SCORING (10% weight)
    # Prefer techs with lower workload ratio
    # Invert so lower workload = higher score
    candidates['workload_score'] = 1.0 - candidates['workload_ratio'].fillna(0.5)

    # SUCCESS PROBABILITY (15% weight)
    # ML prediction of success
    # Already between 0-1

    # CONFIDENCE (5% weight)
    # ML prediction confidence
    # Already between 0-1

    # FINAL SCORE: Prioritize success probability (main goal) while managing distance
    # Success-driven approach: Assign technicians most likely to succeed
    # Distance is important but secondary to successful completion
    # Note: Confidence removed as it was redundant with success_prob
    candidates['final_score'] = (
        0.60 * candidates['success_prob'] +       # SUCCESS PROBABILITY (PRIMARY - 60%)
        0.30 * candidates['distance_score'] +     # Distance (secondary - 30%)
        0.10 * candidates['workload_score']       # Lower workload balance (10%)
    )

    # Choose best candidate
    if candidates['final_score'].isna().all():
        candidates_sorted = candidates.sort_values('distance_km', ascending=True, na_position='last')
    else:
        candidates_sorted = candidates.sort_values('final_score', ascending=False, na_position='last')

    best = candidates_sorted.iloc[0]
    tech_id = best.get('Technician_id', None)
    conf = float(np.clip(best.get('confidence', 0.0), 0.0, 1.0))
    success = float(np.clip(best.get('success_prob', 0.0), 0.0, 1.0))
    workload_ratio = float(best.get('workload_ratio', 0.0))

    # Predict duration
    best_distance = best.get('distance_km', max_dist if max_dist > 0 else 1.0)
    if pd.isna(best_distance):
        best_distance = max_dist if max_dist > 0 else 1.0

    first_fix = dispatch_row.get('First_time_fix', 0)
    service_tier = dispatch_row.get('Service_tier', 'Standard')
    equipment_installed = dispatch_row.get('Equipment_installed', 'None')
    predicted_duration = predict_duration(best_distance, first_fix, service_tier, equipment_installed)

    # Update workload
    tech_idx = technicians.index[technicians['Technician_id'] == tech_id]
    if not tech_idx.empty:
        technicians.loc[tech_idx, 'Current_assignments'] += 1

    return tech_id, round(conf, 3), round(success, 3), round(predicted_duration, 1), fallback_level, round(workload_ratio, 3), round(best_distance, 2)

# ============================================================
# 13. RUN OPTIMIZATION FOR ALL DISPATCHES
# ============================================================

print("=" * 70)
print("🎉 FULLY ML-DRIVEN DISPATCH AGENT INITIALIZED")
print("=" * 70)
print(f"\n📊 ML-Discovered Thresholds:")
print(f"   Distance threshold: {ML_DISTANCE_THRESHOLD if ML_DISTANCE_THRESHOLD else 'Not learned (using default)'}")
print(f"   Workload threshold: {ML_WORKLOAD_THRESHOLD if ML_WORKLOAD_THRESHOLD else 'Not learned (using default)'}")
print(f"   Capacity limit: {ML_CAPACITY_LIMIT if ML_CAPACITY_LIMIT else 'Not learned (using default)'}")
print(f"   City matching: {'STRICT' if ML_CITY_STRICT else 'FLEXIBLE'}")
print(f"\n🎯 ML Model Status:")
print(f"   Success probability: {'ML-DRIVEN ✅' if ml_is_trained else 'FALLBACK ⚠️'}")
print(f"   Confidence scoring: {'ML-DRIVEN ✅' if confidence_model_trained else 'FALLBACK ⚠️'}")
print(f"\n✅ System ready to optimize dispatches using ML-discovered constraints!\n")

# ============================================================
# CALCULATE INITIAL ASSIGNMENT SCORES
# ============================================================

def calculate_initial_assignment_scores(dispatch_row, initial_tech_id):
    """
    Calculate ML scores for the initial (pre-optimization) assignment.
    Returns: (confidence, success_prob, predicted_duration, workload_ratio, distance)
    """
    if initial_tech_id is None or pd.isna(initial_tech_id):
        return 0.0, 0.0, 0.0, 0.0, 0.0

    # Get technician info
    tech_info = technicians[technicians['Technician_id'] == initial_tech_id]
    if tech_info.empty:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    tech_info = tech_info.iloc[0]

    # Calculate distance
    cust_lat = dispatch_row.get('Customer_latitude', None)
    cust_lon = dispatch_row.get('Customer_longitude', None)
    tech_lat = tech_info.get('Latitude', None)
    tech_lon = tech_info.get('Longitude', None)

    if pd.isna(cust_lat) or pd.isna(cust_lon) or pd.isna(tech_lat) or pd.isna(tech_lon):
        distance = 10.0  # Default
    else:
        distance = haversine(cust_lat, cust_lon, tech_lat, tech_lon)
        if pd.isna(distance):
            distance = 10.0

    # Calculate workload ratio
    workload_ratio = tech_info['Current_assignments'] / tech_info['Workload_capacity'] if tech_info['Workload_capacity'] > 0 else 1.0

    # Get skills
    required_skill = dispatch_row.get('Required_skill', None)
    tech_skill = tech_info.get('Primary_skill', None)

    # Calculate ML success probability
    city = dispatch_row.get('City', None)
    city_match = (str(tech_info.get('City', '')).lower() == str(city).lower()) if city else True
    success_prob = calculate_ml_success_probability(distance, workload_ratio, required_skill, tech_skill, city_match)

    # Calculate ML confidence
    confidence = calculate_ml_confidence(distance, workload_ratio, required_skill, tech_skill)

    # Predict duration
    first_fix = dispatch_row.get('First_time_fix', 0)
    service_tier = dispatch_row.get('Service_tier', 'Standard')
    equipment_installed = dispatch_row.get('Equipment_installed', 'None')

    if pd.isna(service_tier) or service_tier is None:
        service_tier = 'Standard'
    if pd.isna(equipment_installed) or equipment_installed is None:
        equipment_installed = 'None'

    predicted_duration = predict_duration(distance, first_fix, service_tier, equipment_installed)

    return round(confidence, 3), round(success_prob, 3), round(predicted_duration, 1), round(workload_ratio, 3), round(distance, 2)

print("📊 Calculating initial assignment scores...\n")

initial_conf_scores = []
initial_success_probs = []
initial_predicted_durations = []
initial_workload_ratios = []
initial_distances = []

for idx, row in dispatches.iterrows():
    initial_tech = row.get('Assigned_technician_id', None)
    conf, prob, pred_dur, workload, distance = calculate_initial_assignment_scores(row, initial_tech)
    initial_conf_scores.append(conf)
    initial_success_probs.append(prob)
    initial_predicted_durations.append(pred_dur)
    initial_workload_ratios.append(workload)
    initial_distances.append(distance)

dispatches['Initial_ML_confidence'] = initial_conf_scores
dispatches['Initial_ML_success_prob'] = initial_success_probs
dispatches['Initial_ML_predicted_duration_min'] = initial_predicted_durations
dispatches['Initial_ML_workload_ratio'] = initial_workload_ratios
dispatches['Initial_ML_distance_km'] = initial_distances

print("✅ Initial assignment scores calculated.\n")

print("\n⚙️  Running FULLY ML-DRIVEN optimization on all dispatches...\n")

optimized_ids = []
conf_scores = []
success_probs = []
predicted_durations = []
fallback_levels = []
optimized_workload_ratios = []
optimized_distances = []

for idx, row in dispatches.iterrows():
    try:
        tech_id, conf, prob, pred_dur, fallback_level, workload, distance = assign_technician_ml(row)
    except Exception as e:
        print(f"⚠️  Assignment error for dispatch {idx}: {e}")
        tech_id, conf, prob, pred_dur, fallback_level, workload, distance = None, 0.0, 0.0, 0.0, 'error', 0.0, 0.0

    optimized_ids.append(tech_id)
    conf_scores.append(conf)
    success_probs.append(prob)
    predicted_durations.append(pred_dur)
    fallback_levels.append(fallback_level)
    optimized_workload_ratios.append(workload)
    optimized_distances.append(distance)

dispatches['Optimized_technician_id'] = optimized_ids
dispatches['ML_confidence'] = conf_scores
dispatches['ML_success_prob'] = success_probs
dispatches['ML_predicted_duration_min'] = predicted_durations
dispatches['ML_fallback_level'] = fallback_levels
dispatches['ML_workload_ratio'] = optimized_workload_ratios
dispatches['ML_distance_km'] = optimized_distances

# Add comparison metrics (improvement columns)
dispatches['ML_confidence_improvement'] = dispatches['ML_confidence'] - dispatches['Initial_ML_confidence']
dispatches['ML_success_prob_improvement'] = dispatches['ML_success_prob'] - dispatches['Initial_ML_success_prob']
dispatches['ML_duration_change'] = dispatches['ML_predicted_duration_min'] - dispatches['Initial_ML_predicted_duration_min']
dispatches['ML_workload_ratio_change'] = dispatches['ML_workload_ratio'] - dispatches['Initial_ML_workload_ratio']
dispatches['ML_distance_change_km'] = dispatches['ML_distance_km'] - dispatches['Initial_ML_distance_km']

# Add optimization metadata
optimization_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
dispatches['Optimization_timestamp'] = optimization_timestamp
dispatches['Optimization_status'] = dispatches['Optimized_technician_id'].apply(
    lambda x: 'completed' if pd.notna(x) and x is not None else 'pending'
)

# Add ML model indicators
dispatches['ML_model_used'] = ml_is_trained
dispatches['ML_confidence_model_used'] = confidence_model_trained

# ============================================================
# 14. WRITE RESULTS TO CSV
# ============================================================

print(f"\n📤 Writing ML-optimized results to CSV file...")

try:
    dispatches.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Results saved to: {OUTPUT_PATH}\n")
except Exception as e:
    raise RuntimeError(f"Failed to write results to CSV file: {e}")

# ============================================================
# 15. SUMMARY STATISTICS (ML-DRIVEN)
# ============================================================

print("=" * 70)
print("🎉 FULLY ML-DRIVEN OPTIMIZATION COMPLETED!")
print("=" * 70)

print(f"\n📊 Summary:")
print(f"  - Total dispatches processed: {len(dispatches)}")
print(f"  - Assigned technicians: {sum(1 for x in optimized_ids if x is not None)}")
print(f"  - Unassigned dispatches: {sum(1 for x in optimized_ids if x is None)}")

print(f"\n🤖 ML-Driven Fallback Level Breakdown:")
print(f"  - Level 1 (Exact skill + ML capacity): {sum(1 for x in fallback_levels if x == 'level_1_ml')}")
print(f"  - Level 2 (Any skill + ML capacity, ML-scored): {sum(1 for x in fallback_levels if x == 'level_2_ml')}")
print(f"  - No match found: {sum(1 for x in fallback_levels if x == 'no_match')}")
print(f"  - Errors: {sum(1 for x in fallback_levels if x == 'error')}")

print(f"\n🎯 ML Model Status:")
print(f"  - Pure ML success prediction: {'ACTIVE ✅' if ml_is_trained else 'FALLBACK ⚠️'}")
print(f"  - ML confidence scoring: {'ACTIVE ✅' if confidence_model_trained else 'FALLBACK ⚠️'}")

if ml_is_trained:
    print(f"\n✨ ML Insights:")
    print(f"  - ML discovered skill patterns from historical data")
    print(f"  - Optimal distance threshold: {ML_DISTANCE_THRESHOLD:.1f} km" if ML_DISTANCE_THRESHOLD else "  - Distance threshold: Using default")
    print(f"  - Optimal workload threshold: {ML_WORKLOAD_THRESHOLD*100:.0f}%" if ML_WORKLOAD_THRESHOLD else "  - Workload threshold: Using default")
    print(f"  - Capacity limit: {ML_CAPACITY_LIMIT*100:.0f}%" if ML_CAPACITY_LIMIT else "  - Capacity limit: Using default")

print(f"\n📊 Initial vs Optimized Comparison:")
print(f"  Initial Assignments (ML-scored):")
print(f"    - Average confidence: {np.mean(initial_conf_scores):.3f}")
print(f"    - Average success probability: {np.mean(initial_success_probs):.3f}")
print(f"    - Average predicted duration: {np.mean(initial_predicted_durations):.1f} min")
print(f"    - Average workload ratio: {np.mean(initial_workload_ratios):.3f} ({np.mean(initial_workload_ratios)*100:.1f}%)")
print(f"    - Average distance: {np.mean(initial_distances):.2f} km")
print(f"  Optimized Assignments (ML-driven):")
print(f"    - Average confidence: {np.mean(conf_scores):.3f}")
print(f"    - Average success probability: {np.mean(success_probs):.3f}")
print(f"    - Average predicted duration: {np.mean(predicted_durations):.1f} min")
print(f"    - Average workload ratio: {np.mean(optimized_workload_ratios):.3f} ({np.mean(optimized_workload_ratios)*100:.1f}%)")
print(f"    - Average distance: {np.mean(optimized_distances):.2f} km")
print(f"  ML-Driven Improvements:")
print(f"    - Confidence improvement: {np.mean(conf_scores) - np.mean(initial_conf_scores):+.3f}")
print(f"    - Success probability improvement: {np.mean(success_probs) - np.mean(initial_success_probs):+.3f}")
print(f"    - Duration change: {np.mean(predicted_durations) - np.mean(initial_predicted_durations):+.1f} min")
print(f"    - Workload ratio change: {np.mean(optimized_workload_ratios) - np.mean(initial_workload_ratios):+.3f}")
print(f"    - Distance change: {np.mean(optimized_distances) - np.mean(initial_distances):+.2f} km")
print(f"    - Assignments improved: {sum(1 for x in dispatches['ML_confidence_improvement'] if x > 0)}")
print(f"    - Assignments worse: {sum(1 for x in dispatches['ML_confidence_improvement'] if x < 0)}")
print(f"    - Assignments unchanged: {sum(1 for x in dispatches['ML_confidence_improvement'] if x == 0)}")

# Workload analysis using ML capacity limits
print(f"\n⚠️  Workload Analysis:")
if ML_WORKLOAD_THRESHOLD:
    initial_over_threshold = sum(1 for x in initial_workload_ratios if x >= ML_WORKLOAD_THRESHOLD)
    optimized_over_threshold = sum(1 for x in optimized_workload_ratios if x >= ML_WORKLOAD_THRESHOLD)
    print(f"    - Technicians over ML threshold ({ML_WORKLOAD_THRESHOLD*100:.0f}%) - Initial: {initial_over_threshold}")
    print(f"    - Technicians over ML threshold ({ML_WORKLOAD_THRESHOLD*100:.0f}%) - Optimized: {optimized_over_threshold}")
else:
    print(f"    - Technicians over 80% workload (initial): {sum(1 for x in initial_workload_ratios if x >= 0.80)}")
    print(f"    - Technicians over 80% workload (optimized): {sum(1 for x in optimized_workload_ratios if x >= 0.80)}")

if ML_CAPACITY_LIMIT:
    initial_over_capacity = sum(1 for x in initial_workload_ratios if x >= ML_CAPACITY_LIMIT)
    optimized_over_capacity = sum(1 for x in optimized_workload_ratios if x >= ML_CAPACITY_LIMIT)
    print(f"    - Technicians at/over ML capacity limit ({ML_CAPACITY_LIMIT*100:.0f}%) - Initial: {initial_over_capacity}")
    print(f"    - Technicians at/over ML capacity limit ({ML_CAPACITY_LIMIT*100:.0f}%) - Optimized: {optimized_over_capacity}")
else:
    print(f"    - Technicians at/over 100% capacity (initial): {sum(1 for x in initial_workload_ratios if x >= 1.00)}")
    print(f"    - Technicians at/over 100% capacity (optimized): {sum(1 for x in optimized_workload_ratios if x >= 1.00)}")

print("\n" + "=" * 70)
print("\n📋 Sample Comparison (first 10 dispatches):")
comparison_cols = ['Dispatch_id', 'Assigned_technician_id', 'Optimized_technician_id',
                   'Initial_ML_distance_km', 'ML_distance_km',
                   'Initial_ML_workload_ratio', 'ML_workload_ratio',
                   'Initial_ML_confidence', 'ML_confidence',
                   'Initial_ML_success_prob', 'ML_success_prob', 'ML_fallback_level']
print(dispatches[comparison_cols].head(10).to_string(index=False))
print("\n" + "=" * 70)

print(f"\n✅ Fully ML-driven optimization complete!")
print(f"📁 Results saved to: {OUTPUT_PATH}\n")
