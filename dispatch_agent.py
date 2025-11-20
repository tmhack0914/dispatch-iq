"""
Optimized Dispatch Agent - CSV Version
----------------------------------------
Loads data from CSV files, optimizes technician assignments,
and writes results back to CSV file.
"""

import pandas as pd
import numpy as np
from math import radians, sin, cos, sqrt, atan2
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, GradientBoostingClassifier
from scipy import stats
import warnings
import os
from datetime import datetime

# Try to import XGBoost (fallback to GradientBoosting if not available)
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("⚠️  XGBoost not available. Using GradientBoostingRegressor instead.")
    print("   Install XGBoost for better performance: pip install xgboost\n")

warnings.filterwarnings("ignore", category=FutureWarning)

# No Pure ML imports - using hard-coded categories
USE_PURE_ML = False

# Enable advanced assignment optimization features
ENABLE_PERFORMANCE_TRACKING = True
ENABLE_DYNAMIC_WEIGHTS = False  # DISABLED - weights were too extreme (0.90/0.10)
# ENABLED - Now using dispatch_history_hackathon_10k.csv with 15,000 high-quality records (see DATASET_EVALUATION_REPORT.md)
ENABLE_ENHANCED_SUCCESS_MODEL = True  # Was False - Now enabled due to excellent dataset (15K records, 97/100 quality score)

# ============================================================
# 0. FILE CONFIGURATION
# ============================================================

# CSV file paths (relative to script location)
DATA_FOLDER = os.path.dirname(os.path.abspath(__file__))

# Using hackathon dataset (15,000 records, high quality - see DATASET_EVALUATION_REPORT.md)
TECHNICIANS_PATH = os.path.join(DATA_FOLDER, "technicians_hackathon_10k.csv")
CALENDAR_PATH = os.path.join(DATA_FOLDER, "technician_calendar_hackathon_10k.csv")
DISPATCHES_PATH = os.path.join(DATA_FOLDER, "current_dispatches_hackathon_10k.csv")
HISTORY_PATH = os.path.join(DATA_FOLDER, "dispatch_history_hackathon_10k.csv")

# Output file
OUTPUT_PATH = os.path.join(DATA_FOLDER, "optimized_dispatch_results.csv")

# ============================================================
# DATA LIMITS
# ============================================================
# Limit the data to specific sizes for testing/simulation purposes

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

# Scoring strategy: Use success probability only (simplified)
USE_SUCCESS_ONLY = True  # If True, only use ML success probability (no confidence mixing)

# Legacy weights (only used if USE_SUCCESS_ONLY = False)
WEIGHT_SUCCESS_PROB = 0.60  # Reduced from 0.75 for better balance
WEIGHT_CONFIDENCE = 0.40    # Increased from 0.25 for better balance

# Features expected from history for training
# Basic features (original)
BASIC_FEATURES = ['Distance_km', 'skill_match_score', 'workload_ratio']

# Enhanced features for improved success prediction
ENHANCED_FEATURES = BASIC_FEATURES + [
    'hour_of_day', 'day_of_week', 'is_weekend',
    'Service_tier', 'Equipment_installed', 'First_time_fix'
]

# Use enhanced features if enabled
FEATURES = ENHANCED_FEATURES if ENABLE_ENHANCED_SUCCESS_MODEL else BASIC_FEATURES
TARGET = 'Productive_dispatch'

# ============================================================
# BUSINESS RULES: Core Performance Principles
# ============================================================
# These fundamental rules guide both model training and assignments:
# 1. Shorter distance = Better performance
# 2. Lower workload = Better performance  
# 3. Better skill match = Better performance

SUCCESS_RATE_FACTORS = {
    'perfect_skill_match': 0.92,      # When skills match perfectly
    'short_distance': 0.88,           # When distance < 10km
    'low_workload': 0.85,             # When technician workload < 80%
    'all_factors_aligned': 0.95,      # When all three factors align
    'baseline': 0.60                  # Baseline success rate
}

DISTANCE_THRESHOLD_KM = 10.0          # Distance threshold for "short distance"
WORKLOAD_THRESHOLD = 0.80             # Workload threshold for "low workload"
SKILL_MATCH_THRESHOLD = 0.90          # Threshold for "good" skill match

# Validate these principles are learned by the model
VALIDATE_BUSINESS_RULES = True

# ============================================================
# SKILL FALLBACK HIERARCHY
# ============================================================
# HARD-CODED APPROACH:
# - Manual skill categories
# - Pre-defined relationships between categories
# - Category-based fallback hierarchy

# Skill categories (HARD-CODED)
SKILL_CATEGORIES = {
    'critical': ['Network troubleshooting', 'Line repair', 'Service restoration', 'Connectivity diagnosis'],
    'installation': ['Fiber ONT installation', 'Copper ONT installation', 'GPON equipment setup', 'Router installation'],
    'upgrade': ['Equipment upgrade', 'Bandwidth upgrade', 'Service migration'],
    'support': ['Network support', 'Cable maintenance', 'Equipment check']
}

# Category relationships (HARD-CODED)
CATEGORY_RELATIONSHIPS = {
    'critical': ['support', 'installation'],
    'installation': ['upgrade', 'support'],
    'upgrade': ['installation', 'support'],
    'support': ['critical', 'installation']
}

# Confidence multipliers (DEFAULT - will be learned from data if enabled)
FALLBACK_CONFIDENCE_MULTIPLIER = {
    'exact_match': 1.0,           # Exact skill match
    'same_category': 0.85,        # Same category
    'related_category': 0.60,     # Related category
    'any_available': 0.40,        # Any technician (Level 4)
    'no_match': 0.0               # No technician found
}

# ============================================================
# SEASONAL ADJUSTMENT LOGIC
# ============================================================
# Automatically adjust thresholds based on time of year, demand, or availability

ENABLE_SEASONAL_ADJUSTMENT = True  # Enable dynamic threshold adjustment

# Seasonal Strategy Selection
SEASONAL_STRATEGY = "intelligent_auto"  # Options: "intelligent_auto", "auto", "manual", "time_based", "demand_based", "availability_based"
# "intelligent_auto" = NEW! Automatically analyzes dispatch load and chooses best strategy
# "auto" = Time-based only (original behavior)

# Manual season override (if SEASONAL_STRATEGY = "manual")
MANUAL_SEASON = "normal"  # Options: "peak", "normal", "low"

# Intelligent Auto Settings
INTELLIGENT_AUTO_CONFIG = {
    'enable_demand_override': True,   # Allow demand to override time-based
    'enable_availability_override': True,  # Allow availability to override
    'demand_baseline': 500,           # Average daily dispatches (auto-calculated if None)
    'high_demand_threshold': 1.5,     # > 150% of average
    'low_demand_threshold': 0.8,      # < 80% of average
    'high_availability': 50,          # > 50 techs
    'low_availability': 20,           # < 20 techs
    'priority_order': ['demand', 'availability', 'time']  # Which factors take precedence
}

# Define threshold configurations for each season
SEASONAL_CONFIGS = {
    'peak': {
        'name': 'Peak Season',
        'min_success_threshold': 0.25,
        'max_capacity_ratio': 1.15,
        'description': 'Maximize coverage - holidays, high demand',
        'months': [11, 12],  # November, December
        'days_of_week': None,  # All days
        'hours': None  # All hours
    },
    'normal': {
        'name': 'Normal Operations',
        'min_success_threshold': 0.27,
        'max_capacity_ratio': 1.12,
        'description': 'Balanced - year-round default',
        'months': [3, 4, 5, 6, 7, 8, 9, 10],  # Mar-Oct
        'days_of_week': None,
        'hours': None
    },
    'low': {
        'name': 'Low Season',
        'min_success_threshold': 0.30,
        'max_capacity_ratio': 1.10,
        'description': 'Sustainability focus - low demand periods',
        'months': [1, 2],  # January, February
        'days_of_week': None,
        'hours': None
    },
    # Time-of-day variations
    'morning': {
        'name': 'Morning (Selective)',
        'min_success_threshold': 0.30,
        'max_capacity_ratio': 1.10,
        'description': 'Be selective early - plenty of time',
        'months': None,
        'days_of_week': None,
        'hours': list(range(6, 12))  # 6 AM - 12 PM
    },
    'afternoon': {
        'name': 'Afternoon (Balanced)',
        'min_success_threshold': 0.27,
        'max_capacity_ratio': 1.12,
        'description': 'Balanced approach',
        'months': None,
        'days_of_week': None,
        'hours': list(range(12, 17))  # 12 PM - 5 PM
    },
    'evening': {
        'name': 'Evening (Flexible)',
        'min_success_threshold': 0.25,
        'max_capacity_ratio': 1.15,
        'description': 'More flexible - time running out',
        'months': None,
        'days_of_week': None,
        'hours': list(range(17, 22))  # 5 PM - 10 PM
    }
}

# Demand-based thresholds (requires dispatch count estimation)
DEMAND_THRESHOLDS = {
    'high_demand': {  # > 150% of average
        'min_success_threshold': 0.25,
        'max_capacity_ratio': 1.20,
        'description': 'High demand - be flexible'
    },
    'normal_demand': {  # 80-150% of average
        'min_success_threshold': 0.27,
        'max_capacity_ratio': 1.12,
        'description': 'Normal demand - balanced'
    },
    'low_demand': {  # < 80% of average
        'min_success_threshold': 0.30,
        'max_capacity_ratio': 1.10,
        'description': 'Low demand - be selective'
    }
}

# Availability-based thresholds (requires technician availability data)
AVAILABILITY_THRESHOLDS = {
    'high_availability': {  # > 50 techs available
        'min_success_threshold': 0.35,
        'max_capacity_ratio': 1.00,
        'description': 'Many techs available - be very selective'
    },
    'normal_availability': {  # 20-50 techs available
        'min_success_threshold': 0.27,
        'max_capacity_ratio': 1.12,
        'description': 'Normal availability - balanced'
    },
    'low_availability': {  # < 20 techs available
        'min_success_threshold': 0.20,
        'max_capacity_ratio': 1.20,
        'description': 'Few techs available - be flexible'
    }
}

# ============================================================
# ML-BASED ASSIGNMENT (replaces hard-coded fallback levels)
# ============================================================
USE_ML_BASED_ASSIGNMENT = True  # Use ML model to evaluate all technicians

# Base thresholds (will be overridden by seasonal adjustment if enabled)
MIN_SUCCESS_THRESHOLD = 0.27     # BALANCED: Middle ground (default if seasonal disabled)
MAX_CAPACITY_RATIO = 1.12        # BALANCED: Middle ground (default if seasonal disabled)

# Legacy fallback system (DEPRECATED - kept for reference only)
# The ML model now evaluates all technicians directly based on:
# 1. Distance (shorter = better)
# 2. Workload (lower = better)  
# 3. Skill match (better = better)
# No need for hard-coded confidence multipliers or cascading levels

LEARN_FALLBACK_MULTIPLIERS = False  # Disabled (only for legacy fallback system)

# DEPRECATED: Hard-coded cascading fallback levels
# These are replaced by ML-based evaluation of all available technicians
CASCADING_FALLBACK_LEVELS = [
    {
        'name': 'level_1',
        'description': 'Exact skill + Under 100% capacity',
        'confidence_multiplier': 1.0,
        'allow_overcapacity': False,
        'use_skill_fallback': None
    },
    {
        'name': 'level_2',
        'description': 'Same category skill + Under 100% capacity',
        'confidence_multiplier': 0.85,
        'allow_overcapacity': False,
        'use_skill_fallback': 'same_category'
    },
    {
        'name': 'level_3',
        'description': 'Related category skill + Under 100% capacity',
        'confidence_multiplier': 0.70,
        'allow_overcapacity': False,
        'use_skill_fallback': 'related_category'
    },
    {
        'name': 'level_4',
        'description': 'Any skill + Under 110% capacity (RELAXED)',
        'confidence_multiplier': 0.50,
        'allow_overcapacity': True,
        'max_capacity_ratio': 1.10,
        'use_skill_fallback': 'any'
    }
]

def get_skill_category(skill):
    """Get category for a given skill."""
    if pd.isna(skill):
        return None
    for category, skills in SKILL_CATEGORIES.items():
        if skill in skills:
            return category
    return None

def get_fallback_skills(required_skill):
    """Get fallback skills in priority order."""
    if pd.isna(required_skill):
        return []

    fallbacks = [(required_skill, 'exact_match')]
    req_category = get_skill_category(required_skill)

    if req_category:
        # Same category skills
        for skill in SKILL_CATEGORIES[req_category]:
            if skill != required_skill:
                fallbacks.append((skill, 'same_category'))

        # Related category skills
        for related_cat in CATEGORY_RELATIONSHIPS.get(req_category, []):
            for skill in SKILL_CATEGORIES.get(related_cat, []):
                fallbacks.append((skill, 'related_category'))

    return fallbacks

# ============================================================
# SEASONAL ADJUSTMENT FUNCTION
# ============================================================

def intelligent_auto_select(dispatch_count, available_tech_count, current_date=None):
    """
    INTELLIGENT AUTO-SELECTION: Analyzes current conditions and chooses best strategy.
    
    This is the "smart" mode that looks at actual dispatch load and availability
    to automatically decide whether to use demand-based, availability-based, or time-based.
    
    Args:
        dispatch_count: Number of dispatches to optimize today
        available_tech_count: Number of available technicians
        current_date: datetime object (defaults to now)
    
    Returns:
        tuple: (chosen_strategy, season_name, config_dict, reason)
    """
    import datetime
    
    if current_date is None:
        current_date = datetime.datetime.now()
    
    reasons = []
    scores = {'demand': 0, 'availability': 0, 'time': 0}
    
    # Calculate demand baseline (use config or estimate from history)
    baseline = INTELLIGENT_AUTO_CONFIG.get('demand_baseline', 500)
    
    # FACTOR 1: Demand Analysis
    if dispatch_count is not None and INTELLIGENT_AUTO_CONFIG.get('enable_demand_override', True):
        demand_ratio = dispatch_count / baseline
        
        if demand_ratio > INTELLIGENT_AUTO_CONFIG['high_demand_threshold']:
            scores['demand'] = 10  # High priority
            reasons.append(f"HIGH DEMAND: {dispatch_count} dispatches ({demand_ratio:.1%} of baseline)")
            demand_config = DEMAND_THRESHOLDS['high_demand']
            demand_season = 'high_demand'
        elif demand_ratio < INTELLIGENT_AUTO_CONFIG['low_demand_threshold']:
            scores['demand'] = 8  # Medium-high priority
            reasons.append(f"LOW DEMAND: {dispatch_count} dispatches ({demand_ratio:.1%} of baseline)")
            demand_config = DEMAND_THRESHOLDS['low_demand']
            demand_season = 'low_demand'
        else:
            scores['demand'] = 2  # Low priority (normal)
            reasons.append(f"Normal demand: {dispatch_count} dispatches ({demand_ratio:.1%} of baseline)")
            demand_config = DEMAND_THRESHOLDS['normal_demand']
            demand_season = 'normal_demand'
    else:
        demand_config = None
        demand_season = None
    
    # FACTOR 2: Availability Analysis
    if available_tech_count is not None and INTELLIGENT_AUTO_CONFIG.get('enable_availability_override', True):
        if available_tech_count > INTELLIGENT_AUTO_CONFIG['high_availability']:
            scores['availability'] = 9  # High priority
            reasons.append(f"HIGH AVAILABILITY: {available_tech_count} techs available (can be selective)")
            avail_config = AVAILABILITY_THRESHOLDS['high_availability']
            avail_season = 'high_availability'
        elif available_tech_count < INTELLIGENT_AUTO_CONFIG['low_availability']:
            scores['availability'] = 10  # Highest priority (emergency)
            reasons.append(f"LOW AVAILABILITY: Only {available_tech_count} techs available (need flexibility)")
            avail_config = AVAILABILITY_THRESHOLDS['low_availability']
            avail_season = 'low_availability'
        else:
            scores['availability'] = 2  # Low priority (normal)
            reasons.append(f"Normal availability: {available_tech_count} techs")
            avail_config = AVAILABILITY_THRESHOLDS['normal_availability']
            avail_season = 'normal_availability'
    else:
        avail_config = None
        avail_season = None
    
    # FACTOR 3: Time-based (always available as fallback)
    current_hour = current_date.hour
    current_month = current_date.month
    
    # Check time of day
    time_config = None
    time_season = None
    for season_key in ['morning', 'afternoon', 'evening']:
        config = SEASONAL_CONFIGS[season_key]
        if config['hours'] and current_hour in config['hours']:
            time_config = config
            time_season = season_key
            scores['time'] = 5  # Medium priority
            reasons.append(f"Time: {season_key.capitalize()} ({current_hour}:00)")
            break
    
    # If no time match, check month
    if time_config is None:
        for season_key in ['peak', 'low', 'normal']:
            config = SEASONAL_CONFIGS[season_key]
            if config['months'] and current_month in config['months']:
                time_config = config
                time_season = season_key
                scores['time'] = 4  # Lower priority
                reasons.append(f"Season: {season_key.capitalize()} (Month {current_month})")
                break
    
    # Default time fallback
    if time_config is None:
        time_config = SEASONAL_CONFIGS['normal']
        time_season = 'normal'
        scores['time'] = 1
        reasons.append("Time: Default (normal)")
    
    # DECISION LOGIC: Follow priority order
    priority_order = INTELLIGENT_AUTO_CONFIG.get('priority_order', ['demand', 'availability', 'time'])
    
    # Sort by score (highest first), then by priority order
    factors = [
        ('demand', scores['demand'], demand_config, demand_season),
        ('availability', scores['availability'], avail_config, avail_season),
        ('time', scores['time'], time_config, time_season)
    ]
    
    # Sort by score descending
    factors_sorted = sorted(factors, key=lambda x: x[1], reverse=True)
    
    # Choose the highest scoring factor that has a config
    chosen_factor = None
    chosen_config = None
    chosen_season = None
    
    for factor_name, score, config, season in factors_sorted:
        if config is not None and score > 5:  # Only choose if high priority
            chosen_factor = factor_name
            chosen_config = config
            chosen_season = season
            break
    
    # If no high-priority factor, use priority order
    if chosen_factor is None:
        for factor_name in priority_order:
            if factor_name == 'demand' and demand_config:
                chosen_factor = 'demand'
                chosen_config = demand_config
                chosen_season = demand_season
                break
            elif factor_name == 'availability' and avail_config:
                chosen_factor = 'availability'
                chosen_config = avail_config
                chosen_season = avail_season
                break
            elif factor_name == 'time' and time_config:
                chosen_factor = 'time'
                chosen_config = time_config
                chosen_season = time_season
                break
    
    # Final fallback
    if chosen_config is None:
        chosen_factor = 'time'
        chosen_config = time_config
        chosen_season = time_season
    
    # Build reason string
    reason_str = " | ".join(reasons)
    decision_str = f"CHOSEN: {chosen_factor.upper()}-based (score: {scores[chosen_factor]})"
    
    return chosen_factor, chosen_season, chosen_config, f"{decision_str} | {reason_str}"


def determine_season(strategy='auto', manual_season='normal', current_date=None, 
                     dispatch_count=None, available_tech_count=None):
    """
    Determine the appropriate season/configuration based on strategy.
    
    Args:
        strategy: "auto", "manual", "time_based", "demand_based", or "availability_based"
        manual_season: Manual override season if strategy="manual"
        current_date: datetime object (defaults to now)
        dispatch_count: Number of dispatches to assign (for demand-based)
        available_tech_count: Number of available technicians (for availability-based)
    
    Returns:
        tuple: (season_name, config_dict)
    """
    import datetime
    
    if current_date is None:
        current_date = datetime.datetime.now()
    
    current_month = current_date.month
    current_hour = current_date.hour
    current_day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
    
    # Intelligent auto-selection (NEW!)
    if strategy == "intelligent_auto":
        chosen_strategy, season_name, config, reason = intelligent_auto_select(
            dispatch_count=dispatch_count,
            available_tech_count=available_tech_count,
            current_date=current_date
        )
        # Add metadata for display
        config['chosen_by'] = chosen_strategy
        config['selection_reason'] = reason
        return season_name, config
    
    # Manual override
    if strategy == "manual":
        if manual_season in SEASONAL_CONFIGS:
            config = SEASONAL_CONFIGS[manual_season]
            return manual_season, config
        else:
            print(f"⚠️  Invalid manual season '{manual_season}', defaulting to 'normal'")
            return 'normal', SEASONAL_CONFIGS['normal']
    
    # Time-based: Check time of day first, then month
    if strategy == "time_based" or strategy == "auto":
        # Check time of day
        for season_key in ['morning', 'afternoon', 'evening']:
            config = SEASONAL_CONFIGS[season_key]
            if config['hours'] and current_hour in config['hours']:
                return season_key, config
        
        # Check month-based seasons
        for season_key in ['peak', 'low', 'normal']:
            config = SEASONAL_CONFIGS[season_key]
            if config['months'] and current_month in config['months']:
                return season_key, config
        
        # Default to normal
        return 'normal', SEASONAL_CONFIGS['normal']
    
    # Demand-based
    if strategy == "demand_based":
        if dispatch_count is None:
            print("⚠️  Demand-based strategy requires dispatch_count, using normal")
            return 'normal_demand', DEMAND_THRESHOLDS['normal_demand']
        
        # Estimate average (this could be calculated from historical data)
        average_daily_dispatches = 500  # Adjust based on your operation
        demand_ratio = dispatch_count / average_daily_dispatches
        
        if demand_ratio > 1.5:
            return 'high_demand', DEMAND_THRESHOLDS['high_demand']
        elif demand_ratio < 0.8:
            return 'low_demand', DEMAND_THRESHOLDS['low_demand']
        else:
            return 'normal_demand', DEMAND_THRESHOLDS['normal_demand']
    
    # Availability-based
    if strategy == "availability_based":
        if available_tech_count is None:
            print("⚠️  Availability-based strategy requires available_tech_count, using normal")
            return 'normal_availability', AVAILABILITY_THRESHOLDS['normal_availability']
        
        if available_tech_count > 50:
            return 'high_availability', AVAILABILITY_THRESHOLDS['high_availability']
        elif available_tech_count < 20:
            return 'low_availability', AVAILABILITY_THRESHOLDS['low_availability']
        else:
            return 'normal_availability', AVAILABILITY_THRESHOLDS['normal_availability']
    
    # Default fallback
    print(f"⚠️  Unknown strategy '{strategy}', defaulting to 'normal'")
    return 'normal', SEASONAL_CONFIGS['normal']


def apply_seasonal_adjustment(enable=True, strategy='auto', manual_season='normal',
                              dispatch_count=None, available_tech_count=None):
    """
    Apply seasonal threshold adjustments.
    
    Returns:
        tuple: (min_success_threshold, max_capacity_ratio, season_name, description)
    """
    global MIN_SUCCESS_THRESHOLD, MAX_CAPACITY_RATIO
    
    if not enable:
        print("\n🔧 Seasonal adjustment: DISABLED")
        print(f"   Using static thresholds: MIN={MIN_SUCCESS_THRESHOLD}, MAX={MAX_CAPACITY_RATIO}")
        return MIN_SUCCESS_THRESHOLD, MAX_CAPACITY_RATIO, "static", "Static configuration"
    
    # Determine current season
    season_name, config = determine_season(
        strategy=strategy,
        manual_season=manual_season,
        dispatch_count=dispatch_count,
        available_tech_count=available_tech_count
    )
    
    # Extract thresholds
    new_min_threshold = config.get('min_success_threshold', MIN_SUCCESS_THRESHOLD)
    new_max_capacity = config.get('max_capacity_ratio', MAX_CAPACITY_RATIO)
    description = config.get('description', 'No description')
    config_name = config.get('name', season_name)
    
    # Apply adjustments
    MIN_SUCCESS_THRESHOLD = new_min_threshold
    MAX_CAPACITY_RATIO = new_max_capacity
    
    print("\n" + "="*80)
    print("🌍 SEASONAL ADJUSTMENT APPLIED")
    print("="*80)
    print(f"   Strategy:       {strategy.upper()}")
    
    # Show intelligent auto details if available
    if strategy == "intelligent_auto" and 'selection_reason' in config:
        print(f"   🧠 Analysis:     {config['selection_reason']}")
        if 'chosen_by' in config:
            print(f"   🎯 Chosen By:    {config['chosen_by'].upper()}-based strategy")
    
    print(f"   Season:         {config_name} ({season_name})")
    print(f"   Description:    {description}")
    print(f"   MIN Threshold:  {new_min_threshold:.2f} (was {0.27:.2f})")
    print(f"   MAX Capacity:   {new_max_capacity:.2f} (was {1.12:.2f})")
    print("="*80)
    
    return new_min_threshold, new_max_capacity, season_name, description


# ============================================================
# 1. LOAD DATASETS FROM CSV FILES
# ============================================================

# Apply seasonal adjustment before loading data
# For intelligent_auto, we need to peek at dispatch/tech counts first
dispatch_count_for_adjustment = None
available_tech_count_for_adjustment = None

if ENABLE_SEASONAL_ADJUSTMENT and SEASONAL_STRATEGY == "intelligent_auto":
    print("\n🧠 INTELLIGENT AUTO MODE: Analyzing dispatch load...\n")
    
    # Quick peek at dispatch count (without full processing)
    try:
        import pandas as pd
        temp_dispatches = pd.read_csv(DISPATCHES_PATH)
        dispatch_count_for_adjustment = min(len(temp_dispatches), MAX_DISPATCHES)
        print(f"   📊 Detected: {dispatch_count_for_adjustment} dispatches to optimize")
    except Exception as e:
        print(f"   ⚠️  Could not read dispatch count: {e}")
        dispatch_count_for_adjustment = None
    
    # Quick peek at available technician count
    try:
        temp_calendar = pd.read_csv(CALENDAR_PATH)
        # Count unique available technicians (assuming 'Available' column or similar)
        if 'Available' in temp_calendar.columns:
            available_tech_count_for_adjustment = temp_calendar[temp_calendar['Available'] == True]['Technician_id'].nunique()
        elif 'Technician_id' in temp_calendar.columns:
            available_tech_count_for_adjustment = temp_calendar['Technician_id'].nunique()
        else:
            available_tech_count_for_adjustment = None
        
        if available_tech_count_for_adjustment:
            print(f"   👥 Detected: {available_tech_count_for_adjustment} available technicians")
    except Exception as e:
        print(f"   ⚠️  Could not read technician count: {e}")
        available_tech_count_for_adjustment = None
    
    print()

if ENABLE_SEASONAL_ADJUSTMENT:
    MIN_SUCCESS_THRESHOLD, MAX_CAPACITY_RATIO, current_season, season_desc = apply_seasonal_adjustment(
        enable=ENABLE_SEASONAL_ADJUSTMENT,
        strategy=SEASONAL_STRATEGY,
        manual_season=MANUAL_SEASON,
        dispatch_count=dispatch_count_for_adjustment,
        available_tech_count=available_tech_count_for_adjustment
    )

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
    # Load data with limits applied
    technicians = safe_read_csv(TECHNICIANS_PATH, "technicians")
    technicians = technicians.head(MAX_TECHNICIANS)  # Limit to 150 technicians

    calendar = safe_read_csv(CALENDAR_PATH, "technician_calendar")
    calendar = calendar.head(MAX_CALENDAR_ENTRIES)  # Limit to 13500 entries

    dispatches = safe_read_csv(DISPATCHES_PATH, "current_dispatches")
    dispatches = dispatches.head(MAX_DISPATCHES)  # Limit to 600 dispatches

    history = safe_read_csv(HISTORY_PATH, "dispatch_history")
    history = history.head(MAX_HISTORY_RECORDS)  # Limit to 1000 records

    print(f"\n📋 Data limits applied:")
    print(f"   - Technicians: {len(technicians)}/{MAX_TECHNICIANS} (target: {TECHS_PER_CITY} per city × {NUM_CITIES} cities)")
    print(f"   - Calendar entries: {len(calendar)}/{MAX_CALENDAR_ENTRIES} (target: {MAX_TECHNICIANS} techs × {CALENDAR_DAYS} days)")
    print(f"   - Current dispatches: {len(dispatches)}/{MAX_DISPATCHES} (target: {DISPATCH_SCENARIOS} scenarios × {NUM_CITIES} cities × {DISPATCHES_PER_SCENARIO_PER_CITY} each)")
    print(f"   - Historical records: {len(history)}/{MAX_HISTORY_RECORDS}")
    print()
except Exception as e:
    print(f"\n❌ Error loading CSV files: {e}")
    print("\nMake sure the following CSV files exist in the same folder as this script:")
    print(f"  - {TECHNICIANS_PATH}")
    print(f"  - {CALENDAR_PATH}")
    print(f"  - {DISPATCHES_PATH}")
    print(f"  - {HISTORY_PATH}")
    raise

# ============================================================
# 2. DATA CLEANING & NORMALIZATION
# ============================================================

# Normalize column names (strip whitespace)
technicians.columns = technicians.columns.str.strip()
calendar.columns = calendar.columns.str.strip()
dispatches.columns = dispatches.columns.str.strip()
history.columns = history.columns.str.strip()

# Calendar date -> date object
if 'Date' not in calendar.columns:
    raise KeyError("technician_calendar.csv must contain 'Date' column")
calendar['Date'] = pd.to_datetime(calendar['Date'], errors='coerce').dt.date

# Ensure Available exists and is 0/1
if 'Available' not in calendar.columns:
    raise KeyError("technician_calendar.csv must contain 'Available' column")
calendar['Available'] = calendar['Available'].fillna(0).astype(int)

# Dispatch appointment -> datetime and date
# Handle both possible column names
if 'Appointment_start_datetime' in dispatches.columns:
    appointment_col = 'Appointment_start_datetime'
elif 'Appointment_start_time' in dispatches.columns:
    appointment_col = 'Appointment_start_time'
else:
    raise KeyError("current_disapatches.csv must contain 'Appointment_start_datetime' or 'Appointment_start_time' column")

dispatches['Appointment_start_time'] = pd.to_datetime(dispatches[appointment_col], errors='coerce')
dispatches['Appointment_date'] = dispatches['Appointment_start_time'].dt.date

# Ensure technicians has expected workload and id columns
if 'Technician_id' not in technicians.columns:
    raise KeyError("technicians.csv must contain 'Technician_id' column")

# Handle both possible column names for current assignments
if 'Current_assignments' in technicians.columns:
    assignment_col = 'Current_assignments'
elif 'Current_assignment_count' in technicians.columns:
    assignment_col = 'Current_assignment_count'
    technicians['Current_assignments'] = technicians['Current_assignment_count']
else:
    raise KeyError("technicians.csv must contain 'Current_assignments' or 'Current_assignment_count' column")

if 'Workload_capacity' not in technicians.columns:
    raise KeyError("technicians.csv must contain 'Workload_capacity' column")

# Ensure numeric workload columns
technicians['Current_assignments'] = pd.to_numeric(technicians['Current_assignments'], errors='coerce').fillna(0)
technicians['Workload_capacity'] = pd.to_numeric(technicians['Workload_capacity'], errors='coerce')

# ============================================================
# 4. HAVERSINE DISTANCE FUNCTION
# ============================================================

def haversine(lat1, lon1, lat2, lon2):
    """Return distance in km between two lat/lon points; return np.nan if coords invalid."""
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
# 5. PREPARE & TRAIN PREDICTIVE MODEL FROM HISTORY
# ============================================================

print("🤖 Training productivity prediction model...")
print("   Focusing on: Distance, Skill Match, Workload\n")

# Verify history has required columns
required_cols = ['Distance_km', 'Required_skill', 'Assigned_technician_id', TARGET]
missing_cols = [c for c in required_cols if c not in history.columns]
if missing_cols:
    raise KeyError(f"dispatch_history.csv missing required columns: {missing_cols}")

# Merge history with technicians to get skill information
history_with_techs = history.merge(
    technicians[['Technician_id', 'Primary_skill', 'Workload_capacity', 'Current_assignments']],
    left_on='Assigned_technician_id',
    right_on='Technician_id',
    how='inner'
)

# Parse appointment dates for workload estimation
history_with_techs['Appointment_date'] = pd.to_datetime(history_with_techs['Appointment_start_time'], errors='coerce').dt.date

# ============================================================
# LEARN SKILL COMPATIBILITY FROM HISTORICAL DATA
# ============================================================

print("📊 Learning skill compatibility from historical success data...")

# Calculate success rate for each skill pair (required_skill, tech_skill)
skill_compatibility = history_with_techs.groupby(['Required_skill', 'Primary_skill']).agg({
    TARGET: ['sum', 'count', 'mean']
}).reset_index()

skill_compatibility.columns = ['Required_skill', 'Tech_skill', 'success_count', 'total_count', 'success_rate']

# Calculate overall success rate for exact matches (for normalization)
exact_matches = skill_compatibility[skill_compatibility['Required_skill'] == skill_compatibility['Tech_skill']]
baseline_success_rate = exact_matches['success_rate'].mean() if len(exact_matches) > 0 else 0.5

print(f"   Baseline success rate (exact matches): {baseline_success_rate:.3f}")
print(f"   Found {len(skill_compatibility)} unique skill pairings\n")

# Create skill compatibility dictionary
# Score is based on actual success rate, normalized by baseline
skill_compatibility_dict = {}

for _, row in skill_compatibility.iterrows():
    req_skill = str(row['Required_skill'])
    tech_skill = str(row['Tech_skill'])
    success_rate = row['success_rate']
    count = row['total_count']
    
    # Use success rate as score, but require minimum samples for reliability
    if pd.isna(success_rate) or count < 3:  # Need at least 3 samples for reliability
        # For low-sample pairs, use conservative estimate
        if req_skill == tech_skill:
            score = 1.0  # Exact match always gets 1.0
        else:
            score = 0.3  # Unknown pairs get low score
    else:
        # Normalize success rate relative to baseline
        if req_skill == tech_skill:
            score = 1.0  # Exact match always gets 1.0
        else:
            # Normalize: if success rate is same as baseline = 0.5, higher = better, lower = worse
            normalized_score = 0.3 + 0.7 * (success_rate / baseline_success_rate) if baseline_success_rate > 0 else 0.5
            score = float(np.clip(normalized_score, 0.1, 0.95))  # Cap at 0.95 (exact match is always best)
    
    skill_compatibility_dict[(req_skill, tech_skill)] = {
        'score': score,
        'success_rate': success_rate,
        'count': count
    }

# Show top skill pairings by success rate
top_pairings = skill_compatibility[
    (skill_compatibility['Required_skill'] != skill_compatibility['Tech_skill']) &
    (skill_compatibility['total_count'] >= 3)
].nlargest(10, 'success_rate')

if len(top_pairings) > 0:
    print("   Top skill pairings (by success rate):")
    for _, row in top_pairings.head(5).iterrows():
        print(f"     {row['Required_skill']} → {row['Tech_skill']}: {row['success_rate']:.3f} ({int(row['total_count'])} samples)")

print()

# ============================================================
# LEARN OPTIMAL FALLBACK MULTIPLIERS FROM DATA
# ============================================================

if LEARN_FALLBACK_MULTIPLIERS and not USE_ML_BASED_ASSIGNMENT and len(history_with_techs) > 50:
    print("📊 Analyzing historical success rates by skill match level...")
    
    # Categorize each historical assignment by match type
    def categorize_skill_match(req_skill, tech_skill):
        """Determine skill match category for historical assignment"""
        if pd.isna(req_skill) or pd.isna(tech_skill):
            return 'unknown'
        
        req_skill_str = str(req_skill)
        tech_skill_str = str(tech_skill)
        
        # Exact match
        if req_skill_str == tech_skill_str:
            return 'exact_match'
        
        # Get categories
        req_category = get_skill_category(req_skill_str)
        tech_category = get_skill_category(tech_skill_str)
        
        if req_category and tech_category:
            # Same category
            if req_category == tech_category:
                return 'same_category'
            
            # Related category
            if tech_category in CATEGORY_RELATIONSHIPS.get(req_category, []):
                return 'related_category'
        
        # Different/unrelated
        return 'any_available'
    
    history_with_techs['match_type'] = history_with_techs.apply(
        lambda row: categorize_skill_match(
            row.get('Required_skill'), 
            row.get('Primary_skill')
        ),
        axis=1
    )
    
    # Calculate success rates by match type
    match_type_analysis = history_with_techs.groupby('match_type').agg({
        TARGET: ['sum', 'count', 'mean']
    }).reset_index()
    
    match_type_analysis.columns = ['match_type', 'success_count', 'total_count', 'success_rate']
    
    # Calculate optimal multipliers based on actual success rates
    # Normalize to exact_match = 1.0
    exact_match_rate = match_type_analysis[
        match_type_analysis['match_type'] == 'exact_match'
    ]['success_rate'].values
    
    if len(exact_match_rate) > 0 and exact_match_rate[0] > 0:
        baseline_rate = exact_match_rate[0]
        
        print(f"\n   Skill Match Success Rates (Historical):")
        print(f"   {'Match Type':<20} {'Success Rate':<15} {'Count':<10} {'Learned Multiplier':<20}")
        print(f"   {'-'*70}")
        
        learned_multipliers = {}
        
        for _, row in match_type_analysis.iterrows():
            match_type = row['match_type']
            success_rate = row['success_rate']
            count = int(row['total_count'])
            
            # Calculate multiplier relative to exact match
            # Use conservative estimation for low sample counts
            if count >= 10:
                # Enough samples - use actual rate
                multiplier = success_rate / baseline_rate
            elif count >= 5:
                # Some samples - blend with prior
                multiplier = (0.7 * success_rate / baseline_rate + 
                             0.3 * FALLBACK_CONFIDENCE_MULTIPLIER.get(match_type, 0.5))
            else:
                # Too few samples - use prior
                multiplier = FALLBACK_CONFIDENCE_MULTIPLIER.get(match_type, 0.5)
            
            # Ensure reasonable bounds
            multiplier = float(np.clip(multiplier, 0.3, 1.0))
            
            learned_multipliers[match_type] = multiplier
            
            print(f"   {match_type:<20} {success_rate:.3f} ({success_rate*100:.1f}%){'':<4} {count:<10} {multiplier:.3f}")
        
        # Update global multipliers with learned values
        for match_type, multiplier in learned_multipliers.items():
            if match_type != 'unknown':
                FALLBACK_CONFIDENCE_MULTIPLIER[match_type] = multiplier
        
        print(f"\n   ✅ Updated fallback multipliers based on historical data")
        print(f"   Baseline (exact match) success rate: {baseline_rate:.3f}")
        
    else:
        print(f"   ⚠️  Insufficient data for exact matches - using default multipliers")
    
    print()
else:
    if USE_ML_BASED_ASSIGNMENT:
        print("🤖 ML-BASED ASSIGNMENT: Fallback multipliers not needed (model evaluates all technicians)\n")
    elif not LEARN_FALLBACK_MULTIPLIERS:
        print("📊 Using default fallback multipliers (learning disabled)\n")
    else:
        print("📊 Insufficient historical data for learning multipliers (need 50+)\n")

def calculate_skill_match_score(required_skill, tech_skill):
    """
    Calculate skill match score based on learned compatibility from historical data.
    Returns score between 0.1 and 1.0 based on actual success rates.
    Always uses trained logic - no category fallback.
    """
    if pd.isna(required_skill) or pd.isna(tech_skill):
        return 0.3  # Unknown/low match
    
    req_skill = str(required_skill)
    tech_skill_str = str(tech_skill)
    
    # Exact match always gets 1.0
    if req_skill == tech_skill_str:
        return 1.0
    
    # Check compatibility dictionary (primary direction)
    key = (req_skill, tech_skill_str)
    if key in skill_compatibility_dict:
        return skill_compatibility_dict[key]['score']
    
    # Fallback: check reverse (sometimes data might be recorded differently)
    reverse_key = (tech_skill_str, req_skill)
    if reverse_key in skill_compatibility_dict:
        return skill_compatibility_dict[reverse_key]['score']
    
    # No historical data for this pair - use conservative default based on training data
    # Calculate average score for all non-exact matches in training data
    non_exact_scores = [
        v['score'] for k, v in skill_compatibility_dict.items()
        if k[0] != k[1]  # Not exact matches
    ]
    
    if len(non_exact_scores) > 0:
        # Use average of all learned non-exact match scores
        default_score = np.mean(non_exact_scores)
    else:
        # If no training data at all, use conservative default
        default_score = 0.4
    
    # Return conservative score for unknown pairs (always use trained data approach)
    return float(np.clip(default_score, 0.2, 0.6))  # Conservative range for unknown pairs

history_with_techs['skill_match_score'] = history_with_techs.apply(
    lambda row: calculate_skill_match_score(row.get('Required_skill'), row.get('Primary_skill')),
    axis=1
)

# ============================================================
# ADD TEMPORAL FEATURES TO HISTORY FOR SUCCESS PREDICTION
# ============================================================

if ENABLE_ENHANCED_SUCCESS_MODEL:
    print("🔧 Adding temporal features to history for enhanced success prediction...")
    
    # Extract temporal features from appointment time
    history_with_techs['hour_of_day'] = pd.to_datetime(
        history_with_techs['Appointment_start_time'], errors='coerce'
    ).dt.hour.fillna(12)  # Default to noon if missing
    
    history_with_techs['day_of_week'] = pd.to_datetime(
        history_with_techs['Appointment_start_time'], errors='coerce'
    ).dt.dayofweek.fillna(2)  # Default to Wednesday if missing
    
    history_with_techs['is_weekend'] = history_with_techs['day_of_week'].isin([5, 6]).astype(int)
    
    print(f"   ✓ Added hour_of_day, day_of_week, is_weekend to historical data\n")

# ============================================================
# ESTIMATE HISTORICAL WORKLOAD FROM DISPATCH COUNTS
# ============================================================

print("📊 Estimating historical workload from dispatch counts...")

# Sort by date and time to process chronologically
history_with_techs = history_with_techs.sort_values(['Appointment_date', 'Appointment_start_time']).reset_index(drop=True)

# Count assignments per technician per date BEFORE this dispatch
# This represents the workload state when this dispatch was assigned
# cumcount() gives 0 for first, 1 for second, etc. (number BEFORE current dispatch)
history_with_techs['assignments_before'] = history_with_techs.groupby(['Technician_id', 'Appointment_date']).cumcount()

# Calculate workload ratio using historical assignments count
# Workload = assignments on that date BEFORE assignment / capacity
# This represents the actual workload state when the dispatch was made
history_with_techs['workload_ratio'] = (
    history_with_techs['assignments_before'] /
    pd.to_numeric(history_with_techs['Workload_capacity'], errors='coerce')
).fillna(0.5)  # Default to 50% if capacity missing

# Clip workload ratio to reasonable range (0.0 to 2.0 to allow overcapacity in historical data)
history_with_techs['workload_ratio'] = history_with_techs['workload_ratio'].clip(0.0, 2.0)

print(f"   Estimated workload from {len(history_with_techs)} historical dispatches")
print(f"   Average workload ratio: {history_with_techs['workload_ratio'].mean():.3f}")
print(f"   Workload range: {history_with_techs['workload_ratio'].min():.3f} - {history_with_techs['workload_ratio'].max():.3f}\n")

# Clean data
history_clean = history_with_techs[[*FEATURES, TARGET]].copy()
history_clean['Distance_km'] = pd.to_numeric(history_clean['Distance_km'], errors='coerce')
history_clean['skill_match_score'] = pd.to_numeric(history_clean['skill_match_score'], errors='coerce')
history_clean['workload_ratio'] = pd.to_numeric(history_clean['workload_ratio'], errors='coerce').clip(0.0, 1.0)
history_clean[TARGET] = pd.to_numeric(history_clean[TARGET], errors='coerce').fillna(0).astype(int)

# Drop rows with missing critical data
history_clean = history_clean.dropna(subset=FEATURES + [TARGET])

if len(history_clean) < 20:
    print("⚠️  WARNING: history has fewer than 20 usable rows; model may be unreliable.")

if len(history_clean) == 0:
    raise ValueError("No usable history data after cleaning. Cannot train model.")

print(f"   Training on {len(history_clean)} historical records")
print(f"   Features: {', '.join(FEATURES)}")
print(f"   Target: {TARGET}\n")

X = history_clean[FEATURES]
y = history_clean[TARGET].astype(int)

# Identify numeric and categorical features
if ENABLE_ENHANCED_SUCCESS_MODEL:
    numeric_features_success = ['Distance_km', 'skill_match_score', 'workload_ratio',
                                'hour_of_day', 'day_of_week', 'is_weekend', 'First_time_fix']
    categorical_features_success = ['Service_tier', 'Equipment_installed']
    
    # Filter to only features present in data
    numeric_features_success = [f for f in numeric_features_success if f in X.columns]
    categorical_features_success = [f for f in categorical_features_success if f in X.columns]
    
    preprocessor = ColumnTransformer([
        ('num', MinMaxScaler(), numeric_features_success),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features_success)
    ], remainder='drop')
    
    # Use Gradient Boosting for better performance
    if XGBOOST_AVAILABLE:
        classifier = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1
        )
        model_type = "XGBoost Classifier"
    else:
        classifier = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        model_type = "Gradient Boosting Classifier"
else:
    # Basic features only - use simple logistic regression
    preprocessor = ColumnTransformer([
        ('num', MinMaxScaler(), FEATURES)
    ], remainder='drop')
    
    classifier = LogisticRegression(max_iter=2000, random_state=42)
    model_type = "Logistic Regression"

pipeline = Pipeline([
    ('preproc', preprocessor),
    ('clf', classifier)
])

pipeline.fit(X, y)

print(f"✅ Productivity prediction model trained successfully.")
print(f"   Model type: {model_type}")
print(f"   Features used: {len(FEATURES)}")
if ENABLE_ENHANCED_SUCCESS_MODEL:
    print(f"   Numeric features: {len(numeric_features_success)}")
    print(f"   Categorical features: {len(categorical_features_success)}")
print()

# Note: Business rules validation will run after predict_success() is defined

# ============================================================
# 5A. TECHNICIAN PERFORMANCE TRACKING
# ============================================================

# Initialize performance tracking dictionary
technician_performance = {}

if ENABLE_PERFORMANCE_TRACKING:
    print("📊 Building technician performance profiles...")
    
    # Calculate performance metrics for each technician from historical data
    for tech_id in history_with_techs['Technician_id'].unique():
        tech_history = history_with_techs[history_with_techs['Technician_id'] == tech_id]
        
        if len(tech_history) > 0:
            # Success rate
            success_rate = tech_history[TARGET].mean() if TARGET in tech_history.columns else 0.75
            
            # Average distance they handle
            avg_distance = tech_history['Distance_km'].mean() if 'Distance_km' in tech_history.columns else 15.0
            
            # Count of completed jobs (experience)
            job_count = len(tech_history)
            
            # Average workload when they were assigned
            avg_workload = tech_history['workload_ratio'].mean() if 'workload_ratio' in tech_history.columns else 0.5
            
            # Performance score (weighted combination)
            performance_score = (
                0.6 * success_rate +  # 60% weight on success
                0.2 * min(job_count / 50, 1.0) +  # 20% on experience (capped at 50 jobs)
                0.2 * (1 - min(avg_workload, 1.0))  # 20% on not being overworked
            )
            
            technician_performance[tech_id] = {
                'success_rate': success_rate,
                'avg_distance': avg_distance,
                'job_count': job_count,
                'avg_workload': avg_workload,
                'performance_score': performance_score
            }
    
    print(f"   ✓ Built performance profiles for {len(technician_performance)} technicians")
    print(f"   Average success rate: {np.mean([p['success_rate'] for p in technician_performance.values()]):.3f}")
    print(f"   Average job count: {np.mean([p['job_count'] for p in technician_performance.values()]):.1f}")
    print()

# ============================================================
# 5B. DYNAMIC WEIGHT OPTIMIZATION
# ============================================================

# Default weights
optimal_weights = {'success': WEIGHT_SUCCESS_PROB, 'confidence': WEIGHT_CONFIDENCE}

if ENABLE_DYNAMIC_WEIGHTS:
    print("⚖️  Optimizing assignment weights from historical data...")
    
    # Analyze historical assignments to find optimal weights
    # We'll test different weight combinations and see which performs best
    
    from sklearn.metrics import roc_auc_score, accuracy_score
    
    if len(history_clean) > 50:  # Need sufficient data
        # Test different weight combinations
        best_auc = 0
        best_weights = optimal_weights.copy()
        
        # CONSTRAINED weight combinations (avoid extremes)
        weight_combinations = [
            (0.55, 0.45), (0.60, 0.40), (0.65, 0.35), (0.70, 0.30), (0.75, 0.25)
        ]
        
        for w_success, w_conf in weight_combinations:
            # Simulate scoring with these weights on historical data
            # (This is a simplified version - in production you'd do cross-validation)
            try:
                # Calculate what the final scores would have been
                history_scores = (
                    w_success * history_clean['skill_match_score'] +
                    w_conf * (1 - history_clean['Distance_km'] / history_clean['Distance_km'].max())
                )
                
                # Compare with actual outcomes
                if len(history_scores) == len(history_clean[TARGET]):
                    auc = roc_auc_score(history_clean[TARGET], history_scores)
                    
                    if auc > best_auc:
                        best_auc = auc
                        best_weights = {'success': w_success, 'confidence': w_conf}
            except:
                pass
        
        optimal_weights = best_weights
        
        print(f"   ✓ Optimal weights found:")
        print(f"     Success probability: {optimal_weights['success']:.2f}")
        print(f"     Confidence: {optimal_weights['confidence']:.2f}")
        print(f"     Historical AUC: {best_auc:.3f}")
    else:
        print(f"   ⚠️  Insufficient data for weight optimization (need 50+, have {len(history_clean)})")
        print(f"   Using default weights: success={optimal_weights['success']:.2f}, confidence={optimal_weights['confidence']:.2f}")
    print()

# Update global weights
WEIGHT_SUCCESS_PROB = optimal_weights['success']
WEIGHT_CONFIDENCE = optimal_weights['confidence']

# ============================================================
# 5C. NO ML MODEL TRAINING - USING HARD-CODED CATEGORIES
# ============================================================

# Using hard-coded skill categories and relationships
print("✅ Using hard-coded skill categories (no ML training needed)\n")

# ============================================================
# 5B. TRAIN ADVANCED DURATION PREDICTION MODEL
# ============================================================

print("🤖 Training advanced duration prediction model...")
print("   Enhancements: Temporal features, technician performance, XGBoost/GradientBoosting\n")

# ============================================================
# 5B.1. FEATURE ENGINEERING FOR DURATION PREDICTION
# ============================================================

print("🔧 Engineering features for duration prediction...")

# Create a copy of history for duration modeling
duration_data = history_with_techs.copy()

# --- TEMPORAL FEATURES ---
duration_data['appointment_datetime'] = pd.to_datetime(duration_data['Appointment_start_time'], errors='coerce')
duration_data['hour'] = duration_data['appointment_datetime'].dt.hour
duration_data['day_of_week'] = duration_data['appointment_datetime'].dt.dayofweek
duration_data['is_weekend'] = duration_data['day_of_week'].isin([5, 6]).astype(int)
duration_data['month'] = duration_data['appointment_datetime'].dt.month
duration_data['is_morning'] = (duration_data['hour'] >= 6) & (duration_data['hour'] < 12)
duration_data['is_afternoon'] = (duration_data['hour'] >= 12) & (duration_data['hour'] < 18)
duration_data['is_evening'] = (duration_data['hour'] >= 18) & (duration_data['hour'] < 22)

# --- TECHNICIAN-SPECIFIC FEATURES ---
# Calculate average duration per technician (using expanding mean to avoid data leakage)
duration_data = duration_data.sort_values('appointment_datetime')
duration_data['tech_avg_duration'] = duration_data.groupby('Technician_id')['Actual_duration_min'].transform(
    lambda x: x.expanding().mean().shift(1)  # shift to avoid using current value
)
# Fill NaN with overall mean for new technicians
duration_data['tech_avg_duration'] = duration_data['tech_avg_duration'].fillna(
    duration_data['Actual_duration_min'].mean()
)

# Technician experience proxy: count of previous jobs
duration_data['tech_job_count'] = duration_data.groupby('Technician_id').cumcount()

# --- SKILL MATCH QUALITY ---
duration_data['skill_match_score'] = duration_data.apply(
    lambda row: calculate_skill_match_score(row.get('Required_skill'), row.get('Primary_skill')),
    axis=1
)

# --- INTERACTION FEATURES ---
duration_data['distance_x_equipment'] = duration_data['Distance_km'] * (
    duration_data['Equipment_installed'].notna().astype(int)
)
duration_data['distance_x_first_fix'] = duration_data['Distance_km'] * duration_data['First_time_fix']

# --- GEOGRAPHIC FEATURES ---
if 'City' in duration_data.columns:
    # Frequency encoding for city (how many jobs in each city)
    city_counts = duration_data['City'].value_counts()
    duration_data['city_job_frequency'] = duration_data['City'].map(city_counts).fillna(0)
else:
    duration_data['city_job_frequency'] = 0

print(f"   ✓ Added temporal features: hour, day_of_week, is_weekend, month, time_of_day")
print(f"   ✓ Added technician features: avg_duration, job_count")
print(f"   ✓ Added skill match score")
print(f"   ✓ Added interaction features: distance × equipment, distance × first_fix")
print(f"   ✓ Added geographic features: city_job_frequency\n")

# ============================================================
# 5B.2. PREPARE DATASET FOR TRAINING
# ============================================================

# Define comprehensive feature set
duration_features = [
    # Original features
    'Distance_km', 'First_time_fix', 'Service_tier', 'Equipment_installed',
    # Temporal features
    'hour', 'day_of_week', 'is_weekend', 'month',
    'is_morning', 'is_afternoon', 'is_evening',
    # Technician features
    'tech_avg_duration', 'tech_job_count', 'workload_ratio',
    # Skill match
    'skill_match_score',
    # Interaction features
    'distance_x_equipment', 'distance_x_first_fix',
    # Geographic features
    'city_job_frequency'
]

duration_target = 'Actual_duration_min'

# Check if all features exist
available_features = [f for f in duration_features if f in duration_data.columns]
missing_features = [f for f in duration_features if f not in duration_data.columns]

if missing_features:
    print(f"⚠️  Missing features (will be excluded): {missing_features}")
    duration_features = available_features

# Prepare data
X_duration_full = duration_data[duration_features + [duration_target]].copy()

# Remove rows with missing target
X_duration_full = X_duration_full[X_duration_full[duration_target].notna()]

# ============================================================
# 5B.3. OUTLIER DETECTION AND REMOVAL
# ============================================================

print("🔍 Detecting and removing outliers...")

# Remove extreme outliers in target variable (duration)
initial_count = len(X_duration_full)
z_scores = np.abs(stats.zscore(X_duration_full[duration_target]))
X_duration_full = X_duration_full[z_scores < 3]  # Keep data within 3 standard deviations
outliers_removed = initial_count - len(X_duration_full)

print(f"   Removed {outliers_removed} outliers ({outliers_removed/initial_count*100:.1f}% of data)")
print(f"   Duration range after cleaning: {X_duration_full[duration_target].min():.1f} - {X_duration_full[duration_target].max():.1f} min\n")

# Separate features and target
y_duration = X_duration_full[duration_target].copy()
X_duration = X_duration_full[duration_features].copy()

# Remove any remaining NaN values in features
valid_idx = ~X_duration.isna().any(axis=1)
X_duration = X_duration[valid_idx]
y_duration = y_duration[valid_idx]

if len(X_duration) < 20:
    print("⚠️  WARNING: Insufficient data for duration prediction model.")
    duration_model = None
    duration_feature_importance = None
    duration_metrics = None
    min_duration_bound = 15.0
    max_duration_bound = 480.0
else:
    # ============================================================
    # 5B.4. TRAIN/TEST SPLIT
    # ============================================================
    
    print(f"📊 Splitting data: {len(X_duration)} samples")
    X_train, X_test, y_train, y_test = train_test_split(
        X_duration, y_duration, test_size=0.2, random_state=42, shuffle=True
    )
    print(f"   Training set: {len(X_train)} samples")
    print(f"   Test set: {len(X_test)} samples\n")
    
    # Calculate data-driven duration bounds from training data
    min_duration_bound = y_train.quantile(0.01)  # 1st percentile
    max_duration_bound = y_train.quantile(0.99)  # 99th percentile
    print(f"   Data-driven duration bounds: {min_duration_bound:.1f} - {max_duration_bound:.1f} min\n")
    
    # ============================================================
    # 5B.5. DEFINE PREPROCESSING & MODEL
    # ============================================================
    
    # Identify numeric and categorical features
    numeric_features_dur = ['Distance_km', 'First_time_fix', 'hour', 'day_of_week', 
                           'is_weekend', 'month', 'is_morning', 'is_afternoon', 'is_evening',
                           'tech_avg_duration', 'tech_job_count', 'workload_ratio',
                           'skill_match_score', 'distance_x_equipment', 'distance_x_first_fix',
                           'city_job_frequency']
    
    categorical_features_dur = ['Service_tier', 'Equipment_installed']
    
    # Filter to only features present in data
    numeric_features_dur = [f for f in numeric_features_dur if f in X_duration.columns]
    categorical_features_dur = [f for f in categorical_features_dur if f in X_duration.columns]
    
    print(f"   Numeric features ({len(numeric_features_dur)}): {', '.join(numeric_features_dur[:5])}...")
    print(f"   Categorical features ({len(categorical_features_dur)}): {', '.join(categorical_features_dur)}\n")
    
    # Preprocessing pipeline
    preprocessor_dur = ColumnTransformer([
        ('num', StandardScaler(), numeric_features_dur),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features_dur)
    ], remainder='drop')
    
    # ============================================================
    # 5B.6. MODEL SELECTION & HYPERPARAMETER TUNING
    # ============================================================
    
    print("🎯 Training and tuning model...")
    
    if XGBOOST_AVAILABLE:
        print("   Using XGBoost Regressor with hyperparameter tuning\n")
        
        # XGBoost with hyperparameter tuning
        param_grid = {
            'reg__n_estimators': [100, 200],
            'reg__max_depth': [4, 6, 8],
            'reg__learning_rate': [0.05, 0.1],
            'reg__subsample': [0.8, 1.0]
        }
        
        base_model = xgb.XGBRegressor(
            random_state=42,
            n_jobs=-1,
            objective='reg:squarederror'
        )
        
    else:
        print("   Using Gradient Boosting Regressor with hyperparameter tuning\n")
        
        # Gradient Boosting with hyperparameter tuning
        param_grid = {
            'reg__n_estimators': [100, 200],
            'reg__max_depth': [4, 6, 8],
            'reg__learning_rate': [0.05, 0.1],
            'reg__subsample': [0.8, 1.0]
        }
        
        base_model = GradientBoostingRegressor(random_state=42)
    
    # Create pipeline
    duration_pipeline = Pipeline([
        ('preproc', preprocessor_dur),
        ('reg', base_model)
    ])
    
    # Grid search with cross-validation (use 3 folds for speed with small data)
    n_folds = min(3, len(X_train) // 10)  # At least 10 samples per fold
    if n_folds < 2:
        n_folds = 2
    
    print(f"   Performing grid search with {n_folds}-fold cross-validation...")
    grid_search = GridSearchCV(
        duration_pipeline,
        param_grid,
        cv=n_folds,
        scoring='neg_mean_absolute_error',
        n_jobs=-1,
        verbose=0
    )
    
    grid_search.fit(X_train, y_train)
    duration_model = grid_search.best_estimator_
    
    print(f"   ✓ Best parameters found:")
    for param, value in grid_search.best_params_.items():
        print(f"     {param}: {value}")
    print()
    
    # ============================================================
    # 5B.7. MODEL EVALUATION
    # ============================================================
    
    print("📈 Evaluating model performance...")
    
    # Cross-validation scores on training data
    cv_scores = cross_val_score(
        duration_model, X_train, y_train,
        cv=n_folds, scoring='neg_mean_absolute_error'
    )
    cv_mae = -cv_scores.mean()
    cv_std = cv_scores.std()
    
    # Predictions on test set
    y_pred_train = duration_model.predict(X_train)
    y_pred_test = duration_model.predict(X_test)
    
    # Training metrics
    train_mae = mean_absolute_error(y_train, y_pred_train)
    train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
    train_r2 = r2_score(y_train, y_pred_train)
    
    # Test metrics
    test_mae = mean_absolute_error(y_test, y_pred_test)
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    test_r2 = r2_score(y_test, y_pred_test)
    
    # Store metrics for reporting
    duration_metrics = {
        'cv_mae': cv_mae,
        'cv_std': cv_std,
        'train_mae': train_mae,
        'train_rmse': train_rmse,
        'train_r2': train_r2,
        'test_mae': test_mae,
        'test_rmse': test_rmse,
        'test_r2': test_r2,
        'n_train': len(X_train),
        'n_test': len(X_test),
        'n_features': len(duration_features)
    }
    
    print(f"\n   Cross-Validation Results:")
    print(f"     MAE: {cv_mae:.2f} ± {cv_std:.2f} minutes")
    print(f"\n   Training Set Performance:")
    print(f"     MAE:  {train_mae:.2f} minutes")
    print(f"     RMSE: {train_rmse:.2f} minutes")
    print(f"     R²:   {train_r2:.3f}")
    print(f"\n   Test Set Performance:")
    print(f"     MAE:  {test_mae:.2f} minutes")
    print(f"     RMSE: {test_rmse:.2f} minutes")
    print(f"     R²:   {test_r2:.3f}")
    
    # Check for overfitting
    if train_mae < test_mae * 0.7:
        print(f"\n   ⚠️  Warning: Possible overfitting detected (train MAE much lower than test MAE)")
    else:
        print(f"\n   ✓ Model generalization looks good!")
    
    # ============================================================
    # 5B.8. FEATURE IMPORTANCE ANALYSIS
    # ============================================================
    
    print(f"\n🔍 Analyzing feature importance...")
    
    # Get feature importances from the model
    try:
        # Get the trained model from pipeline
        trained_model = duration_model.named_steps['reg']
        
        # Get feature names after preprocessing
        preprocessor = duration_model.named_steps['preproc']
        
        # Get feature names from transformers
        feature_names = []
        
        # Numeric features
        if 'num' in preprocessor.named_transformers_:
            feature_names.extend(numeric_features_dur)
        
        # Categorical features (one-hot encoded)
        if 'cat' in preprocessor.named_transformers_:
            cat_encoder = preprocessor.named_transformers_['cat']
            if hasattr(cat_encoder, 'get_feature_names_out'):
                cat_feature_names = cat_encoder.get_feature_names_out(categorical_features_dur)
                feature_names.extend(cat_feature_names)
        
        # Get importances
        if hasattr(trained_model, 'feature_importances_'):
            importances = trained_model.feature_importances_
            
            # Create importance dataframe
            importance_df = pd.DataFrame({
                'feature': feature_names[:len(importances)],
                'importance': importances
            }).sort_values('importance', ascending=False)
            
            duration_feature_importance = importance_df
            
            print(f"\n   Top 10 Most Important Features:")
            for idx, row in importance_df.head(10).iterrows():
                print(f"     {row['feature']:<30} {row['importance']:.4f}")
        else:
            duration_feature_importance = None
            print(f"   Feature importance not available for this model type")
    
    except Exception as e:
        duration_feature_importance = None
        print(f"   Could not extract feature importances: {e}")
    
    print("\n✅ Advanced duration prediction model trained successfully!\n")
    print("=" * 60)

def calculate_business_success_probability(distance, workload_ratio, required_skill, tech_skill):
    """
    Calculate success probability using HARD-CODED CATEGORIES.

    Uses manual skill categorization to determine success rates.

    Parameters:
        distance: Distance in km
        workload_ratio: Technician workload (current_assignments / capacity)
        required_skill: Required skill name
        tech_skill: Technician's skill name

    Returns:
        Success probability (0-1)
    """
    # Check if exact match
    is_exact_match = (required_skill == tech_skill)
    is_short_distance = (distance < DISTANCE_THRESHOLD_KM)
    is_low_workload = (workload_ratio < WORKLOAD_THRESHOLD)

    # Determine skill match type using categories
    if is_exact_match:
        skill_match_type = 'exact_match'
        base_success = SUCCESS_RATE_FACTORS['perfect_skill_match']
    else:
        # Check if same category
        req_category = get_skill_category(required_skill)
        tech_category = get_skill_category(tech_skill)

        if req_category and tech_category:
            if req_category == tech_category:
                skill_match_type = 'same_category'
                base_success = 0.88
            elif tech_category in CATEGORY_RELATIONSHIPS.get(req_category, []):
                skill_match_type = 'related_category'
                base_success = 0.85
            else:
                skill_match_type = 'different_category'
                base_success = 0.60
        else:
            skill_match_type = 'unknown_category'
            base_success = 0.60

    # Adjust for distance
    if is_short_distance:
        base_success += 0.03

    # Adjust for workload
    if is_low_workload:
        base_success += 0.02

    # All factors aligned
    if is_exact_match and is_short_distance and is_low_workload:
        base_success = SUCCESS_RATE_FACTORS['all_factors_aligned']

    return float(np.clip(base_success, 0.0, 1.0))

def predict_success(distance, skill_match_score, workload_ratio, 
                   hour_of_day=None, day_of_week=None, service_tier=None,
                   equipment_installed=None, first_time_fix=None, tech_id=None):
    """
    Return probability of productive dispatch given features.
    
    Parameters:
        distance: Distance in km to the technician
        skill_match_score: Skill match score (1.0 = exact match, 0.8 = same category, etc.)
        workload_ratio: Technician workload ratio (current_assignments / capacity)
        hour_of_day: Hour of day (0-23) - optional
        day_of_week: Day of week (0-6) - optional
        service_tier: Service tier - optional
        equipment_installed: Equipment type - optional
        first_time_fix: First time fix indicator - optional
        tech_id: Technician ID for performance adjustment - optional
    
    Returns:
        Probability of productive dispatch (0-1)
    """
    # Build feature dictionary
    row = {
        'Distance_km': distance,
        'skill_match_score': skill_match_score,
        'workload_ratio': workload_ratio
    }
    
    # Add enhanced features if model uses them
    if ENABLE_ENHANCED_SUCCESS_MODEL:
        row['hour_of_day'] = hour_of_day if hour_of_day is not None else 12
        row['day_of_week'] = day_of_week if day_of_week is not None else 2
        row['is_weekend'] = 1 if (day_of_week in [5, 6]) else 0
        row['Service_tier'] = service_tier if service_tier is not None else 'Standard'
        row['Equipment_installed'] = equipment_installed if equipment_installed is not None else 'None'
        row['First_time_fix'] = first_time_fix if first_time_fix is not None else 0
    
    # Create DataFrame with features the model expects
    df = pd.DataFrame([row])
    
    # Ensure all required features are present
    for feat in FEATURES:
        if feat not in df.columns:
            # Add default values for missing features
            if feat in ['hour_of_day']:
                df[feat] = 12
            elif feat in ['day_of_week']:
                df[feat] = 2
            elif feat in ['is_weekend', 'First_time_fix']:
                df[feat] = 0
            elif feat in ['Service_tier']:
                df[feat] = 'Standard'
            elif feat in ['Equipment_installed']:
                df[feat] = 'None'
            else:
                df[feat] = 0
    
    # Select only the features used in training
    df = df[FEATURES]
    
    try:
        prob = pipeline.predict_proba(df)[0][1]
        base_prob = float(np.clip(prob, 0.0, 1.0))
        
        # Adjust probability based on technician performance if enabled
        if ENABLE_PERFORMANCE_TRACKING and tech_id is not None and tech_id in technician_performance:
            tech_perf = technician_performance[tech_id]
            
            # Adjust prediction based on technician's historical success rate
            # If tech has 90% success rate and model predicts 70%, boost to ~77%
            # If tech has 60% success rate and model predicts 70%, reduce to ~66%
            performance_adjustment = tech_perf['success_rate'] / 0.75  # 0.75 is baseline
            adjusted_prob = base_prob * (0.7 + 0.3 * performance_adjustment)  # 70% model, 30% performance
            
            return float(np.clip(adjusted_prob, 0.0, 1.0))
        
        return base_prob
    except Exception as e:
        print(f"⚠️  predict_success: model failed -> {e}")
        return 0.0

# ============================================================
# VALIDATE BUSINESS RULES ARE LEARNED (after predict_success is defined)
# ============================================================

if VALIDATE_BUSINESS_RULES and 'pipeline' in globals():
    print(f"\n🔍 Validating model learned core business principles...")
    print(f"   Testing: 1) Shorter distance = better  2) Lower workload = better  3) Better skill match = better\n")
    
    # Test if model learned correct relationships
    validation_passed = True
    
    # Create test scenarios to validate directional relationships
    base_scenario = {
        'Distance_km': 20.0,
        'skill_match_score': 0.80,
        'workload_ratio': 0.60
    }
    
    try:
        # Test 1: Shorter distance = higher success
        prob_far = predict_success(40.0, 0.80, 0.60)  # Far
        prob_near = predict_success(5.0, 0.80, 0.60)  # Near
        
        distance_check = prob_near > prob_far
        print(f"   ✓ Principle 1 (Distance):    Near (5km: {prob_near:.3f}) vs Far (40km: {prob_far:.3f}) → {distance_check}")
        
        if not distance_check:
            print(f"      ⚠️  WARNING: Model did not learn that shorter distance = better performance!")
            validation_passed = False
        
        # Test 2: Lower workload = higher success
        prob_busy = predict_success(20.0, 0.80, 0.95)   # Busy (95%)
        prob_light = predict_success(20.0, 0.80, 0.20)  # Light (20%)
        
        workload_check = prob_light > prob_busy
        print(f"   ✓ Principle 2 (Workload):    Light (20%: {prob_light:.3f}) vs Busy (95%: {prob_busy:.3f}) → {workload_check}")
        
        if not workload_check:
            print(f"      ⚠️  WARNING: Model did not learn that lower workload = better performance!")
            validation_passed = False
        
        # Test 3: Better skill match = higher success
        prob_poor = predict_success(20.0, 0.30, 0.60)  # Poor match (30%)
        prob_good = predict_success(20.0, 1.00, 0.60)  # Perfect match (100%)
        
        skill_check = prob_good > prob_poor
        print(f"   ✓ Principle 3 (Skill Match): Good (100%: {prob_good:.3f}) vs Poor (30%: {prob_poor:.3f}) → {skill_check}")
        
        if not skill_check:
            print(f"      ⚠️  WARNING: Model did not learn that better skill match = better performance!")
            validation_passed = False
        
        if validation_passed:
            print(f"\n   ✅ SUCCESS: All 3 business principles validated!")
            print(f"      Model correctly learned that shorter distance, lower workload, and better skill match = better performance\n")
        else:
            print(f"\n   ⚠️  VALIDATION FAILED: Some principles not learned correctly!")
            print(f"      Check training data quality - ensure it demonstrates these patterns\n")
    
    except Exception as e:
        print(f"   ⚠️  Could not validate business rules: {e}\n")

def predict_duration(distance, first_fix, service_tier, equipment_installed, 
                     tech_id=None, appointment_time=None, workload_ratio=None,
                     required_skill=None, tech_skill=None, city=None):
    """
    Return predicted duration in minutes for a dispatch using advanced features.
    
    Parameters:
        distance: Distance in km
        first_fix: First time fix indicator (0/1)
        service_tier: Service tier (Standard, Premium, etc.)
        equipment_installed: Equipment type
        tech_id: Technician ID (optional, for tech-specific features)
        appointment_time: Appointment datetime (optional, for temporal features)
        workload_ratio: Current workload ratio (optional)
        required_skill: Required skill (optional, for skill match)
        tech_skill: Technician skill (optional, for skill match)
        city: City name (optional, for geographic features)
    """
    if duration_model is None:
        # Fallback: use median from history or default
        return float(history_clean['Actual_duration_min'].median() if 'Actual_duration_min' in history_clean.columns else 60)
    
    # Build feature dictionary with all required features
    row = {
        # Original features
        'Distance_km': float(distance) if pd.notna(distance) else 10.0,
        'First_time_fix': int(first_fix) if not pd.isna(first_fix) else 0,
        'Service_tier': service_tier if pd.notna(service_tier) else 'Standard',
        'Equipment_installed': equipment_installed if pd.notna(equipment_installed) else 'None'
    }
    
    # --- TEMPORAL FEATURES ---
    if appointment_time is not None and pd.notna(appointment_time):
        try:
            if isinstance(appointment_time, str):
                appointment_time = pd.to_datetime(appointment_time)
            row['hour'] = appointment_time.hour
            row['day_of_week'] = appointment_time.dayofweek
            row['is_weekend'] = 1 if appointment_time.dayofweek in [5, 6] else 0
            row['month'] = appointment_time.month
            row['is_morning'] = 1 if 6 <= appointment_time.hour < 12 else 0
            row['is_afternoon'] = 1 if 12 <= appointment_time.hour < 18 else 0
            row['is_evening'] = 1 if 18 <= appointment_time.hour < 22 else 0
        except:
            # Default temporal features (mid-day weekday)
            row['hour'] = 12
            row['day_of_week'] = 2  # Wednesday
            row['is_weekend'] = 0
            row['month'] = 6
            row['is_morning'] = 0
            row['is_afternoon'] = 1
            row['is_evening'] = 0
    else:
        # Default temporal features (mid-day weekday)
        row['hour'] = 12
        row['day_of_week'] = 2  # Wednesday
        row['is_weekend'] = 0
        row['month'] = 6
        row['is_morning'] = 0
        row['is_afternoon'] = 1
        row['is_evening'] = 0
    
    # --- TECHNICIAN-SPECIFIC FEATURES ---
    if tech_id is not None and pd.notna(tech_id):
        # Get technician's average duration from history
        tech_history = duration_data[duration_data['Technician_id'] == tech_id]
        if len(tech_history) > 0:
            row['tech_avg_duration'] = tech_history['Actual_duration_min'].mean()
            row['tech_job_count'] = len(tech_history)
        else:
            # New technician - use overall average
            row['tech_avg_duration'] = duration_data['Actual_duration_min'].mean() if 'Actual_duration_min' in duration_data.columns else 60.0
            row['tech_job_count'] = 0
    else:
        # Unknown technician - use overall average
        row['tech_avg_duration'] = duration_data['Actual_duration_min'].mean() if 'Actual_duration_min' in duration_data.columns else 60.0
        row['tech_job_count'] = 0
    
    # Workload ratio
    if workload_ratio is not None and pd.notna(workload_ratio):
        row['workload_ratio'] = float(workload_ratio)
    else:
        row['workload_ratio'] = 0.5  # Default to 50%
    
    # --- SKILL MATCH FEATURE ---
    if required_skill is not None and tech_skill is not None:
        row['skill_match_score'] = calculate_skill_match_score(required_skill, tech_skill)
    else:
        row['skill_match_score'] = 0.5  # Default moderate match
    
    # --- INTERACTION FEATURES ---
    row['distance_x_equipment'] = row['Distance_km'] * (1 if row['Equipment_installed'] != 'None' else 0)
    row['distance_x_first_fix'] = row['Distance_km'] * row['First_time_fix']
    
    # --- GEOGRAPHIC FEATURES ---
    if city is not None and pd.notna(city) and 'City' in duration_data.columns:
        city_counts = duration_data['City'].value_counts()
        row['city_job_frequency'] = city_counts.get(city, 0)
    else:
        row['city_job_frequency'] = duration_data['City'].value_counts().median() if 'City' in duration_data.columns else 0
    
    # Create DataFrame with only features that exist in the model
    df = pd.DataFrame([row])
    
    # Filter to only include features the model was trained on
    available_features = [f for f in duration_features if f in df.columns]
    df = df[available_features]
    
    try:
        pred_duration = duration_model.predict(df)[0]
        # Use data-driven bounds
        return float(np.clip(pred_duration, min_duration_bound, max_duration_bound))
    except Exception as e:
        print(f"⚠️  predict_duration: model failed -> {e}")
        # Fallback
        return float(history_clean['Actual_duration_min'].median() if 'Actual_duration_min' in history_clean.columns else 60)

# ============================================================
# 6. CANDIDATE FILTERING
# ============================================================

def get_available_techs_with_cascading_fallback(dispatch_date, required_skill, city=None):
    """
    Get available technicians using cascading fallback logic (CATEGORY-BASED).

    Strict constraints (never relaxed):
    - Calendar availability
    - City match
    - Capacity limit (100%)

    Progressive relaxation through 3 levels:
    Level 1: Exact skill match + Under capacity
    Level 2: Same category skills + Under capacity
    Level 3: Related category skills + Under capacity

    Uses hard-coded skill categories to determine fallbacks.

    Returns: (candidates_df, fallback_level_name, confidence_multiplier)
    """

    for level in CASCADING_FALLBACK_LEVELS:
        if level['use_skill_fallback'] is None:
            # Level 1: Try exact skill match only
            candidates = get_available_techs(
                dispatch_date,
                required_skill,
                city,
                allow_overcapacity=level['allow_overcapacity'],
                max_capacity_ratio=level.get('max_capacity_ratio', 1.0)
            )

            if not candidates.empty:
                return candidates, level['name'], level['confidence_multiplier']

        elif level['use_skill_fallback'] == 'same_category':
            # Level 2: Try same category skills
            fallback_skills = get_fallback_skills(required_skill)
            skills_to_try = [(skill, match_type) for skill, match_type in fallback_skills
                            if match_type == 'same_category']

            for skill, match_type in skills_to_try:
                candidates = get_available_techs(
                    dispatch_date,
                    skill,
                    city,
                    allow_overcapacity=level['allow_overcapacity'],
                    max_capacity_ratio=level.get('max_capacity_ratio', 1.0)
                )

                if not candidates.empty:
                    return candidates, level['name'], level['confidence_multiplier']

        elif level['use_skill_fallback'] == 'related_category':
            # Level 3: Try related category skills
            fallback_skills = get_fallback_skills(required_skill)
            skills_to_try = [(skill, match_type) for skill, match_type in fallback_skills
                            if match_type == 'related_category']

            for skill, match_type in skills_to_try:
                candidates = get_available_techs(
                    dispatch_date,
                    skill,
                    city,
                    allow_overcapacity=level['allow_overcapacity'],
                    max_capacity_ratio=level.get('max_capacity_ratio', 1.0)
                )

                if not candidates.empty:
                    return candidates, level['name'], level['confidence_multiplier']
        
        elif level['use_skill_fallback'] == 'any':
            # Level 4: Try ANY available technician (last resort)
            # Get all technicians in the city who are available, regardless of skill
            if city is not None and dispatch_date is not None:
                # Filter by city and availability only
                available_on_date = calendar[(calendar['Date'] == dispatch_date) & (calendar['Available'] == 1)]
                if not available_on_date.empty:
                    available_ids = available_on_date['Technician_id'].unique()
                    candidates = technicians[
                        (technicians['Technician_id'].isin(available_ids)) &
                        (technicians['City'].str.lower() == str(city).lower())
                    ].copy()
                    
                    # Apply capacity filter
                    candidates = candidates[candidates['Workload_capacity'].notna() & (candidates['Workload_capacity'] > 0)].copy()
                    
                    if level['allow_overcapacity']:
                        max_ratio = level.get('max_capacity_ratio', 1.10)
                        candidates['capacity_ratio'] = candidates['Current_assignments'] / candidates['Workload_capacity']
                        candidates = candidates[candidates['capacity_ratio'] <= max_ratio].copy()
                    else:
                        candidates = candidates[candidates['Current_assignments'] < candidates['Workload_capacity']].copy()
                    
                    if not candidates.empty:
                        return candidates, level['name'], level['confidence_multiplier']

    # No candidates found at any level
    return pd.DataFrame(), 'no_match', 0.0

def get_available_techs(dispatch_date, required_skill, city=None, allow_overcapacity=False, max_capacity_ratio=1.0):
    """
    Return technicians that:
     - have Primary_skill == required_skill
     - are listed as Available on the given dispatch_date in calendar
     - match city (REQUIRED - not optional)
     - respect capacity constraints based on allow_overcapacity parameter

    Parameters:
        dispatch_date: Required date for calendar check
        required_skill: Required primary skill
        city: Required city match (STRICT)
        allow_overcapacity: If True, allow technicians at or over capacity up to max_capacity_ratio
        max_capacity_ratio: Maximum allowed Current_assignments / Workload_capacity ratio (e.g., 1.10 = 110%)
    """
    if required_skill is None or pd.isna(required_skill):
        return technicians.iloc[0:0].copy()

    techs = technicians[technicians['Primary_skill'] == required_skill].copy()
    if techs.empty:
        return techs

    # STRICT: Calendar availability check (never relaxed)
    if dispatch_date is None or pd.isna(dispatch_date):
        return techs.iloc[0:0].copy()

    date_in_calendar = len(calendar[calendar['Date'] == dispatch_date]) > 0
    if not date_in_calendar:
        return techs.iloc[0:0].copy()

    available_on_date = calendar[(calendar['Date'] == dispatch_date) & (calendar['Available'] == 1)]
    if available_on_date.empty:
        return techs.iloc[0:0].copy()

    available_ids = available_on_date['Technician_id'].unique()
    techs = techs[techs['Technician_id'].isin(available_ids)].copy()

    # STRICT: City match (never relaxed - REQUIRED)
    if city is not None and not pd.isna(city) and 'City' in techs.columns:
        techs = techs[techs['City'].str.lower() == str(city).lower()].copy()
    else:
        # If no city provided, cannot match - return empty
        return techs.iloc[0:0].copy()

    # Filter by workload capacity (can be relaxed based on allow_overcapacity)
    techs = techs[techs['Workload_capacity'].notna() & (techs['Workload_capacity'] > 0)].copy()

    if allow_overcapacity:
        # Allow technicians up to max_capacity_ratio of their capacity
        techs['capacity_ratio'] = techs['Current_assignments'] / techs['Workload_capacity']
        techs = techs[techs['capacity_ratio'] <= max_capacity_ratio].copy()
    else:
        # Standard: only under capacity
        techs = techs[techs['Current_assignments'] < techs['Workload_capacity']].copy()

    return techs

def get_all_available_techs_ml(dispatch_date, city, max_capacity_ratio=1.15):
    """
    ML-BASED: Return ALL available technicians in the city, regardless of skill.
    The ML model will evaluate each technician's suitability based on:
    - Distance (shorter = better)
    - Workload (lower = better)
    - Skill match (better = better)
    
    Parameters:
        dispatch_date: Required date for calendar check
        city: Required city match
        max_capacity_ratio: Maximum allowed Current_assignments / Workload_capacity ratio (default 1.15 = 115%)
    
    Returns:
        DataFrame of all available technicians in the city
    """
    # STRICT: Calendar availability check
    if dispatch_date is None or pd.isna(dispatch_date):
        return technicians.iloc[0:0].copy()
    
    date_in_calendar = len(calendar[calendar['Date'] == dispatch_date]) > 0
    if not date_in_calendar:
        return technicians.iloc[0:0].copy()
    
    available_on_date = calendar[(calendar['Date'] == dispatch_date) & (calendar['Available'] == 1)]
    if available_on_date.empty:
        return technicians.iloc[0:0].copy()
    
    available_ids = available_on_date['Technician_id'].unique()
    techs = technicians[technicians['Technician_id'].isin(available_ids)].copy()
    
    # STRICT: City match (required)
    if city is not None and not pd.isna(city) and 'City' in techs.columns:
        techs = techs[techs['City'].str.lower() == str(city).lower()].copy()
    else:
        return technicians.iloc[0:0].copy()
    
    # Filter by workload capacity (allow up to max_capacity_ratio overcapacity)
    techs = techs[techs['Workload_capacity'].notna() & (techs['Workload_capacity'] > 0)].copy()
    techs['capacity_ratio'] = techs['Current_assignments'] / techs['Workload_capacity']
    techs = techs[techs['capacity_ratio'] <= max_capacity_ratio].copy()
    
    return techs

# ============================================================
# 7. ASSIGNMENT LOGIC
# ============================================================

def assign_technician(dispatch_row):
    """
    dispatch_row: pd.Series (row from dispatches)
    Returns: (Technician_id or None, confidence 0-1, success_prob 0-1, predicted_duration_min, fallback_level, workload_ratio, distance_km)
    """
    # Determine date and required skill
    dispatch_date = dispatch_row.get('Appointment_date', None)
    required_skill = dispatch_row.get('Required_skill', None)
    city = dispatch_row.get('City', None)

    # Choose assignment strategy
    if USE_ML_BASED_ASSIGNMENT:
        # ML-BASED: Get ALL available technicians and let ML model evaluate them
        candidates = get_all_available_techs_ml(dispatch_date, city, MAX_CAPACITY_RATIO)
        fallback_level = 'ml_based'
        base_confidence_multiplier = 1.0  # Not used in ML-based approach
    else:
        # LEGACY: Use cascading fallback logic
        candidates, fallback_level, base_confidence_multiplier = get_available_techs_with_cascading_fallback(dispatch_date, required_skill, city)

    if candidates.empty:
        # Even if no technician assigned, predict duration based on dispatch characteristics
        # Use default distance (median from history or 10km) for prediction
        default_distance = history_clean['Distance_km'].median() if 'Distance_km' in history_clean.columns else 10.0
        first_fix = dispatch_row.get('First_time_fix', 0)
        service_tier = dispatch_row.get('Service_tier', 'Standard')
        equipment_installed = dispatch_row.get('Equipment_installed', 'None')
        if pd.isna(service_tier) or service_tier is None:
            service_tier = 'Standard'
        if pd.isna(equipment_installed) or equipment_installed is None:
            equipment_installed = 'None'
        
        # Call predict_duration with all available context
        predicted_duration = predict_duration(
            distance=default_distance, 
            first_fix=first_fix, 
            service_tier=service_tier, 
            equipment_installed=equipment_installed,
            tech_id=None,
            appointment_time=dispatch_row.get('Appointment_start_time', None),
            workload_ratio=None,
            required_skill=required_skill,
            tech_skill=None,
            city=city
        )
        return None, 0.0, 0.0, round(predicted_duration, 1), 'no_match', 0.0, 0.0

    candidates = candidates.copy()

    # Compute distances
    cust_lat = dispatch_row.get('Customer_latitude', None)
    cust_lon = dispatch_row.get('Customer_longitude', None)

    if pd.isna(cust_lat) or pd.isna(cust_lon):
        candidates['distance_km'] = np.nan
    else:
        candidates['distance_km'] = candidates.apply(
            lambda r: haversine(
                cust_lat, cust_lon,
                r.get('Latitude', np.nan),
                r.get('Longitude', np.nan)
            ),
            axis=1
    )

    # Workload ratio
    candidates['workload_ratio'] = candidates['Current_assignments'] / candidates['Workload_capacity']
    candidates['workload_ratio'] = candidates['workload_ratio'].fillna(1.0)  # Penalize unknowns

    # Normalize components safely
    max_dist = candidates['distance_km'].max(skipna=True)
    max_work = candidates['workload_ratio'].max(skipna=True)
    max_dist = float(max_dist) if (pd.notna(max_dist) and max_dist > 0) else 1.0
    max_work = float(max_work) if (pd.notna(max_work) and max_work > 0) else 1.0

    candidates['norm_distance'] = candidates['distance_km'].fillna(max_dist) / max_dist
    candidates['norm_workload'] = candidates['workload_ratio'] / max_work

    # Get dispatch characteristics for success calculation
    first_fix = dispatch_row.get('First_time_fix', 0)
    service_tier = dispatch_row.get('Service_tier', 'Standard')
    equipment_installed = dispatch_row.get('Equipment_installed', 'None')

    if pd.isna(service_tier) or service_tier is None:
        service_tier = 'Standard'
    if pd.isna(equipment_installed) or equipment_installed is None:
        equipment_installed = 'None'

    # Calculate success probability for each candidate using ML model
    # Features: distance, skill_match_score, workload_ratio + enhanced features
    def calc_candidate_success(row):
        distance = row['distance_km'] if not pd.isna(row['distance_km']) else max_dist
        workload = row['workload_ratio']
        tech_skill = row.get('Primary_skill', None)
        tech_id = row.get('Technician_id', None)
        
        # Calculate skill match score
        skill_match = calculate_skill_match_score(required_skill, tech_skill)
        
        # Extract temporal features if available
        hour_of_day = None
        day_of_week = None
        if 'Appointment_start_time' in dispatch_row and pd.notna(dispatch_row['Appointment_start_time']):
            appt_time = pd.to_datetime(dispatch_row['Appointment_start_time'], errors='coerce')
            if pd.notna(appt_time):
                hour_of_day = appt_time.hour
                day_of_week = appt_time.dayofweek
        
        # Use ML model to predict success probability with all features
        return predict_success(
            distance=distance,
            skill_match_score=skill_match,
            workload_ratio=workload,
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            service_tier=service_tier,
            equipment_installed=equipment_installed,
            first_time_fix=first_fix,
            tech_id=tech_id
        )

    candidates['success_prob'] = candidates.apply(calc_candidate_success, axis=1)

    # ML-BASED ASSIGNMENT: Filter by minimum success threshold
    if USE_ML_BASED_ASSIGNMENT:
        # Only consider technicians above minimum success threshold
        candidates = candidates[candidates['success_prob'] >= MIN_SUCCESS_THRESHOLD].copy()
        
        if candidates.empty:
            # No technicians meet minimum threshold - return no assignment
            default_distance = history_clean['Distance_km'].median() if 'Distance_km' in history_clean.columns else 10.0
            first_fix = dispatch_row.get('First_time_fix', 0)
            service_tier = dispatch_row.get('Service_tier', 'Standard')
            equipment_installed = dispatch_row.get('Equipment_installed', 'None')
            if pd.isna(service_tier) or service_tier is None:
                service_tier = 'Standard'
            if pd.isna(equipment_installed) or equipment_installed is None:
                equipment_installed = 'None'
            
            predicted_duration = predict_duration(
                distance=default_distance, 
                first_fix=first_fix, 
                service_tier=service_tier, 
                equipment_installed=equipment_installed,
                tech_id=None,
                appointment_time=dispatch_row.get('Appointment_start_time', None),
                workload_ratio=None,
                required_skill=required_skill,
                tech_skill=None,
                city=city
            )
            return None, 0.0, 0.0, round(predicted_duration, 1), f'ml_below_threshold_{MIN_SUCCESS_THRESHOLD}', 0.0, 0.0

    # Confidence: based on distance, workload, and skill match quality
    # Base confidence from distance and workload
    candidates['confidence'] = 1.0 - (0.6 * candidates['norm_distance'] + 0.4 * candidates['norm_workload'])
    candidates['confidence'] = candidates['confidence'].clip(0.0, 1.0)

    # Apply cascading fallback confidence multiplier (only for legacy mode)
    if not USE_ML_BASED_ASSIGNMENT:
        candidates['confidence'] = candidates['confidence'] * base_confidence_multiplier

    # Final score calculation
    if USE_ML_BASED_ASSIGNMENT or USE_SUCCESS_ONLY:
        # ML-BASED or SIMPLIFIED: Use only success probability (already includes distance, workload, skill)
        candidates['final_score'] = candidates['success_prob']
    else:
        # LEGACY: Weighted combination of success probability and confidence
        candidates['final_score'] = (
            WEIGHT_SUCCESS_PROB * candidates['success_prob'] +
            WEIGHT_CONFIDENCE * candidates['confidence']
        )

    # Choose best candidate
    if candidates['final_score'].isna().all():
        # Fallback: pick nearest (if distance exists)
        candidates_sorted = candidates.sort_values('distance_km', ascending=True, na_position='last')
    else:
        candidates_sorted = candidates.sort_values('final_score', ascending=False, na_position='last')

    best = candidates_sorted.iloc[0]
    tech_id = best.get('Technician_id', None)
    conf = float(np.clip(best.get('confidence', 0.0), 0.0, 1.0))
    success = float(np.clip(best.get('success_prob', 0.0), 0.0, 1.0))
    workload_ratio = float(best.get('workload_ratio', 0.0))

    # Predict duration for the optimized assignment
    # Use the distance to the selected technician
    best_distance = best.get('distance_km', max_dist if max_dist > 0 else 1.0)
    if pd.isna(best_distance):
        best_distance = max_dist if max_dist > 0 else 1.0

    # Call predict_duration with all available context for better accuracy
    predicted_duration = predict_duration(
        distance=best_distance,
        first_fix=first_fix,
        service_tier=service_tier,
        equipment_installed=equipment_installed,
        tech_id=tech_id,
        appointment_time=dispatch_row.get('Appointment_start_time', None),
        workload_ratio=workload_ratio,
        required_skill=required_skill,
        tech_skill=best.get('Primary_skill', None),
        city=city
    )

    # Update workload (in-memory for next assignments)
    tech_idx = technicians.index[technicians['Technician_id'] == tech_id]
    if not tech_idx.empty:
        technicians.loc[tech_idx, 'Current_assignments'] += 1

    return tech_id, round(conf, 3), round(success, 3), round(predicted_duration, 1), fallback_level, round(workload_ratio, 3), round(best_distance, 2)

# ============================================================
# 8. RUN ASSIGNMENT FOR ALL DISPATCHES
# ============================================================

print("⚙️  Calculating scores for initial assignments...\n")

def calculate_assignment_scores(dispatch_row, tech_id):
    """
    Calculate confidence and success probability for a given technician assignment using business rules.
    Returns: (confidence, success_prob, predicted_duration, workload_ratio, distance_km)
    """
    if pd.isna(tech_id) or tech_id is None:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    # Get technician info
    tech_info = technicians[technicians['Technician_id'] == tech_id]
    if tech_info.empty:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    tech_info = tech_info.iloc[0]

    # Calculate distance
    cust_lat = dispatch_row.get('Customer_latitude', None)
    cust_lon = dispatch_row.get('Customer_longitude', None)
    tech_lat = tech_info.get('Latitude', None)
    tech_lon = tech_info.get('Longitude', None)

    distance = haversine(cust_lat, cust_lon, tech_lat, tech_lon)
    if pd.isna(distance):
        distance = 10.0  # Default distance

    # Calculate workload ratio
    workload_ratio = tech_info['Current_assignments'] / tech_info['Workload_capacity'] if tech_info['Workload_capacity'] > 0 else 1.0

    # Get skill names
    required_skill = dispatch_row.get('Required_skill', None)
    tech_skill = tech_info.get('Primary_skill', None)

    if pd.isna(required_skill) or pd.isna(tech_skill):
        return 0.0, 0.0, 0.0, 0.0, 0.0

    # Calculate confidence (based on distance and workload)
    norm_distance = min(distance / 50.0, 1.0)  # Normalize to 50km max
    norm_workload = min(workload_ratio, 1.0)
    confidence = 1.0 - (0.6 * norm_distance + 0.4 * norm_workload)
    confidence = max(0.0, min(1.0, confidence))

    # Calculate skill match score and use ML model for success probability
    skill_match = calculate_skill_match_score(required_skill, tech_skill)
    
    # Extract temporal and job features for enhanced prediction
    hour_of_day = None
    day_of_week = None
    if 'Appointment_start_time' in dispatch_row and pd.notna(dispatch_row.get('Appointment_start_time')):
        appt_time = pd.to_datetime(dispatch_row['Appointment_start_time'], errors='coerce')
        if pd.notna(appt_time):
            hour_of_day = appt_time.hour
            day_of_week = appt_time.dayofweek
    
    success_prob = predict_success(
        distance=distance,
        skill_match_score=skill_match,
        workload_ratio=workload_ratio,
        hour_of_day=hour_of_day,
        day_of_week=day_of_week,
        service_tier=dispatch_row.get('Service_tier', 'Standard'),
        equipment_installed=dispatch_row.get('Equipment_installed', 'None'),
        first_time_fix=dispatch_row.get('First_time_fix', 0),
        tech_id=tech_id
    )

    # Calculate predicted duration
    first_fix = dispatch_row.get('First_time_fix', 0)
    service_tier = dispatch_row.get('Service_tier', 'Standard')
    equipment_installed = dispatch_row.get('Equipment_installed', 'None')

    if pd.isna(service_tier) or service_tier is None:
        service_tier = 'Standard'
    if pd.isna(equipment_installed) or equipment_installed is None:
        equipment_installed = 'None'

    # Call predict_duration with all available context for better accuracy
    predicted_duration = predict_duration(
        distance=distance,
        first_fix=first_fix,
        service_tier=service_tier,
        equipment_installed=equipment_installed,
        tech_id=tech_id,
        appointment_time=dispatch_row.get('Appointment_start_time', None),
        workload_ratio=workload_ratio,
        required_skill=required_skill,
        tech_skill=tech_skill,
        city=dispatch_row.get('City', None)
    )

    return round(confidence, 3), round(success_prob, 3), round(predicted_duration, 1), round(workload_ratio, 3), round(distance, 2)

# Calculate scores for initial assignments
initial_conf_scores = []
initial_success_probs = []
initial_predicted_durations = []
initial_workload_ratios = []
initial_distances = []

print("Calculating initial assignment scores...")
for idx, row in dispatches.iterrows():
    initial_tech = row.get('Assigned_technician_id', None)
    conf, prob, pred_dur, workload, distance = calculate_assignment_scores(row, initial_tech)
    initial_conf_scores.append(conf)
    initial_success_probs.append(prob)
    initial_predicted_durations.append(pred_dur)
    initial_workload_ratios.append(workload)
    initial_distances.append(distance)

dispatches['Initial_confidence'] = initial_conf_scores
dispatches['Initial_success_prob'] = initial_success_probs
dispatches['Initial_predicted_duration_min'] = initial_predicted_durations
dispatches['Initial_workload_ratio'] = initial_workload_ratios
dispatches['Initial_distance_km'] = initial_distances

print("✅ Initial assignment scores calculated.\n")

print("⚙️  Running optimization on all dispatches...\n")

optimized_ids = []
conf_scores = []
success_probs = []
predicted_durations = []
fallback_levels = []
optimized_workload_ratios = []
optimized_distances = []

for idx, row in dispatches.iterrows():
    try:
        tech_id, conf, prob, pred_dur, fallback_level, workload, distance = assign_technician(row)
    except Exception as e:
        print(f"⚠️  Assignment error for index {idx}: {e}")
        tech_id, conf, prob, pred_dur, fallback_level, workload, distance = None, 0.0, 0.0, 0.0, 'error', 0.0, 0.0
    optimized_ids.append(tech_id)
    conf_scores.append(conf)
    success_probs.append(prob)
    predicted_durations.append(pred_dur)
    fallback_levels.append(fallback_level)
    optimized_workload_ratios.append(workload)
    optimized_distances.append(distance)

dispatches['Optimized_technician_id'] = optimized_ids
dispatches['Optimization_confidence'] = conf_scores
dispatches['Predicted_success_prob'] = success_probs
dispatches['Optimized_predicted_duration_min'] = predicted_durations
dispatches['Fallback_level'] = fallback_levels
dispatches['Optimized_workload_ratio'] = optimized_workload_ratios
dispatches['Optimized_distance_km'] = optimized_distances

# Add comparison metrics
dispatches['Confidence_improvement'] = dispatches['Optimization_confidence'] - dispatches['Initial_confidence']
dispatches['Success_prob_improvement'] = dispatches['Predicted_success_prob'] - dispatches['Initial_success_prob']
dispatches['Duration_change'] = dispatches['Optimized_predicted_duration_min'] - dispatches['Initial_predicted_duration_min']
dispatches['Workload_ratio_change'] = dispatches['Optimized_workload_ratio'] - dispatches['Initial_workload_ratio']
dispatches['Distance_change_km'] = dispatches['Optimized_distance_km'] - dispatches['Initial_distance_km']

# Set optimization timestamp for all dispatches (when optimization was run)
optimization_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
dispatches['Optimization_timestamp'] = optimization_timestamp

# Set optimization status
dispatches['Optimization_status'] = dispatches['Optimized_technician_id'].apply(
    lambda x: 'completed' if pd.notna(x) and x is not None else 'pending'
)

# ============================================================
# 9. WRITE RESULTS TO CSV FILE
# ============================================================

print(f"\n📤 Writing optimized results to CSV file...")

try:
    dispatches.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Results saved to: {OUTPUT_PATH}\n")
except Exception as e:
    raise RuntimeError(f"Failed to write results to CSV file: {e}")

# ============================================================
# 10. SUMMARY
# ============================================================

print("=" * 60)
print("🎉 Optimization completed successfully!")
print("=" * 60)
print(f"\nSummary:")
print(f"  - Total dispatches processed: {len(dispatches)}")
print(f"  - Assigned technicians: {sum(1 for x in optimized_ids if x is not None)}")
print(f"  - Unassigned dispatches: {sum(1 for x in optimized_ids if x is None)}")
print(f"\nHard-Coded Category Fallback Level Breakdown:")
print(f"  - Level 1 (Exact skill + Under capacity): {sum(1 for x in fallback_levels if x == 'level_1')}")
print(f"  - Level 2 (Same category + Under capacity): {sum(1 for x in fallback_levels if x == 'level_2')}")
print(f"  - Level 3 (Related category + Under capacity): {sum(1 for x in fallback_levels if x == 'level_3')}")
print(f"  - No match found: {sum(1 for x in fallback_levels if x == 'no_match')}")
print(f"\n🎯 Using hard-coded skill categories (no ML)")

print(f"\n📊 Initial vs Optimized Comparison:")
print(f"  Initial Assignments:")
print(f"    - Average confidence: {np.mean(initial_conf_scores):.3f}")
print(f"    - Average success probability: {np.mean(initial_success_probs):.3f}")
print(f"    - Average predicted duration: {np.mean(initial_predicted_durations):.1f} min")
print(f"    - Average workload ratio: {np.mean(initial_workload_ratios):.3f} ({np.mean(initial_workload_ratios)*100:.1f}%)")
print(f"    - Average distance: {np.mean(initial_distances):.2f} km")
print(f"  Optimized Assignments:")
print(f"    - Average confidence: {np.mean(conf_scores):.3f}")
print(f"    - Average success probability: {np.mean(success_probs):.3f}")
print(f"    - Average predicted duration: {np.mean(predicted_durations):.1f} min")
print(f"    - Average workload ratio: {np.mean(optimized_workload_ratios):.3f} ({np.mean(optimized_workload_ratios)*100:.1f}%)")
print(f"    - Average distance: {np.mean(optimized_distances):.2f} km")
print(f"  Improvements:")
print(f"    - Confidence improvement: {np.mean(conf_scores) - np.mean(initial_conf_scores):+.3f}")
print(f"    - Success probability improvement: {np.mean(success_probs) - np.mean(initial_success_probs):+.3f}")
print(f"    - Duration change: {np.mean(predicted_durations) - np.mean(initial_predicted_durations):+.1f} min")
print(f"    - Workload ratio change: {np.mean(optimized_workload_ratios) - np.mean(initial_workload_ratios):+.3f}")
print(f"    - Distance change: {np.mean(optimized_distances) - np.mean(initial_distances):+.2f} km")
print(f"    - Assignments improved: {sum(1 for x in dispatches['Confidence_improvement'] if x > 0)}")
print(f"    - Assignments worse: {sum(1 for x in dispatches['Confidence_improvement'] if x < 0)}")
print(f"    - Assignments unchanged: {sum(1 for x in dispatches['Confidence_improvement'] if x == 0)}")
print(f"\n⚠️  Workload Analysis (Note: Max capacity = 8 assignments/day):")
print(f"    - Technicians over 80% workload (initial): {sum(1 for x in initial_workload_ratios if x >= 0.80)}")
print(f"    - Technicians over 80% workload (optimized): {sum(1 for x in optimized_workload_ratios if x >= 0.80)}")
print(f"    - Technicians over 100% workload (initial): {sum(1 for x in initial_workload_ratios if x >= 1.00)}")
print(f"    - Technicians over 100% workload (optimized): {sum(1 for x in optimized_workload_ratios if x >= 1.00)}")

print("\n" + "=" * 60)

# ============================================================
# COMPREHENSIVE STATISTICAL COMPARISON
# ============================================================

print("\n📊 COMPREHENSIVE ASSIGNMENT ANALYSIS:")
print("=" * 60)

# Calculate comprehensive statistics
initial_stats = {
    'confidence': {
        'mean': np.mean(initial_conf_scores),
        'median': np.median(initial_conf_scores),
        'std': np.std(initial_conf_scores),
        'min': np.min(initial_conf_scores),
        'max': np.max(initial_conf_scores),
        'q25': np.percentile(initial_conf_scores, 25),
        'q75': np.percentile(initial_conf_scores, 75)
    },
    'success_prob': {
        'mean': np.mean(initial_success_probs),
        'median': np.median(initial_success_probs),
        'std': np.std(initial_success_probs),
        'min': np.min(initial_success_probs),
        'max': np.max(initial_success_probs)
    },
    'distance': {
        'mean': np.mean(initial_distances),
        'median': np.median(initial_distances),
        'total': np.sum(initial_distances),
        'std': np.std(initial_distances)
    },
    'workload': {
        'mean': np.mean(initial_workload_ratios),
        'median': np.median(initial_workload_ratios),
        'over_80_pct': sum(1 for x in initial_workload_ratios if x >= 0.80),
        'over_100_pct': sum(1 for x in initial_workload_ratios if x >= 1.00)
    },
    'duration': {
        'mean': np.mean(initial_predicted_durations),
        'total': np.sum(initial_predicted_durations),
        'median': np.median(initial_predicted_durations)
    }
}

optimized_stats = {
    'confidence': {
        'mean': np.mean(conf_scores),
        'median': np.median(conf_scores),
        'std': np.std(conf_scores),
        'min': np.min(conf_scores),
        'max': np.max(conf_scores),
        'q25': np.percentile(conf_scores, 25),
        'q75': np.percentile(conf_scores, 75)
    },
    'success_prob': {
        'mean': np.mean(success_probs),
        'median': np.median(success_probs),
        'std': np.std(success_probs),
        'min': np.min(success_probs),
        'max': np.max(success_probs)
    },
    'distance': {
        'mean': np.mean(optimized_distances),
        'median': np.median(optimized_distances),
        'total': np.sum(optimized_distances),
        'std': np.std(optimized_distances)
    },
    'workload': {
        'mean': np.mean(optimized_workload_ratios),
        'median': np.median(optimized_workload_ratios),
        'over_80_pct': sum(1 for x in optimized_workload_ratios if x >= 0.80),
        'over_100_pct': sum(1 for x in optimized_workload_ratios if x >= 1.00)
    },
    'duration': {
        'mean': np.mean(predicted_durations),
        'total': np.sum(predicted_durations),
        'median': np.median(predicted_durations)
    }
}

# Print comparison tables
print("\n1. CONFIDENCE SCORE COMPARISON")
print("-" * 60)
print(f"{'Metric':<20} {'Initial':<15} {'Optimized':<15} {'Improvement':<15}")
print("-" * 60)
print(f"{'Mean':<20} {initial_stats['confidence']['mean']:.4f}{'':<10} {optimized_stats['confidence']['mean']:.4f}{'':<10} {(optimized_stats['confidence']['mean'] - initial_stats['confidence']['mean']):.4f} ({((optimized_stats['confidence']['mean'] - initial_stats['confidence']['mean'])/initial_stats['confidence']['mean']*100):+.1f}%)")
print(f"{'Median':<20} {initial_stats['confidence']['median']:.4f}{'':<10} {optimized_stats['confidence']['median']:.4f}{'':<10} {(optimized_stats['confidence']['median'] - initial_stats['confidence']['median']):.4f}")
print(f"{'Std Dev':<20} {initial_stats['confidence']['std']:.4f}{'':<10} {optimized_stats['confidence']['std']:.4f}{'':<10} {(optimized_stats['confidence']['std'] - initial_stats['confidence']['std']):.4f}")
print(f"{'Min':<20} {initial_stats['confidence']['min']:.4f}{'':<10} {optimized_stats['confidence']['min']:.4f}{'':<10} {(optimized_stats['confidence']['min'] - initial_stats['confidence']['min']):.4f}")
print(f"{'Max':<20} {initial_stats['confidence']['max']:.4f}{'':<10} {optimized_stats['confidence']['max']:.4f}{'':<10} {(optimized_stats['confidence']['max'] - initial_stats['confidence']['max']):.4f}")
print(f"{'Q1 (25th pct)':<20} {initial_stats['confidence']['q25']:.4f}{'':<10} {optimized_stats['confidence']['q25']:.4f}")
print(f"{'Q3 (75th pct)':<20} {initial_stats['confidence']['q75']:.4f}{'':<10} {optimized_stats['confidence']['q75']:.4f}")

print("\n2. SUCCESS PROBABILITY COMPARISON")
print("-" * 60)
print(f"{'Metric':<20} {'Initial':<15} {'Optimized':<15} {'Improvement':<15}")
print("-" * 60)
print(f"{'Mean':<20} {initial_stats['success_prob']['mean']:.4f}{'':<10} {optimized_stats['success_prob']['mean']:.4f}{'':<10} {(optimized_stats['success_prob']['mean'] - initial_stats['success_prob']['mean']):.4f} ({((optimized_stats['success_prob']['mean'] - initial_stats['success_prob']['mean'])/initial_stats['success_prob']['mean']*100):+.1f}%)")
print(f"{'Median':<20} {initial_stats['success_prob']['median']:.4f}{'':<10} {optimized_stats['success_prob']['median']:.4f}{'':<10} {(optimized_stats['success_prob']['median'] - initial_stats['success_prob']['median']):.4f}")
print(f"{'Std Dev':<20} {initial_stats['success_prob']['std']:.4f}{'':<10} {optimized_stats['success_prob']['std']:.4f}")
print(f"{'Min':<20} {initial_stats['success_prob']['min']:.4f}{'':<10} {optimized_stats['success_prob']['min']:.4f}")
print(f"{'Max':<20} {initial_stats['success_prob']['max']:.4f}{'':<10} {optimized_stats['success_prob']['max']:.4f}")

print("\n3. DISTANCE OPTIMIZATION")
print("-" * 60)
print(f"{'Metric':<20} {'Initial':<15} {'Optimized':<15} {'Improvement':<15}")
print("-" * 60)
print(f"{'Mean Distance (km)':<20} {initial_stats['distance']['mean']:.2f}{'':<12} {optimized_stats['distance']['mean']:.2f}{'':<12} {(optimized_stats['distance']['mean'] - initial_stats['distance']['mean']):.2f} ({((optimized_stats['distance']['mean'] - initial_stats['distance']['mean'])/initial_stats['distance']['mean']*100):+.1f}%)")
print(f"{'Median Distance':<20} {initial_stats['distance']['median']:.2f}{'':<12} {optimized_stats['distance']['median']:.2f}{'':<12} {(optimized_stats['distance']['median'] - initial_stats['distance']['median']):.2f}")
print(f"{'Total Distance':<20} {initial_stats['distance']['total']:.2f}{'':<12} {optimized_stats['distance']['total']:.2f}{'':<12} {(optimized_stats['distance']['total'] - initial_stats['distance']['total']):.2f} km")
print(f"{'Std Dev':<20} {initial_stats['distance']['std']:.2f}{'':<12} {optimized_stats['distance']['std']:.2f}")

# Calculate distance savings
distance_saved = initial_stats['distance']['total'] - optimized_stats['distance']['total']
distance_saved_pct = (distance_saved / initial_stats['distance']['total'] * 100) if initial_stats['distance']['total'] > 0 else 0
print(f"\n   💡 Total distance saved: {distance_saved:.2f} km ({distance_saved_pct:.1f}%)")
if distance_saved > 0:
    print(f"   💰 Estimated fuel savings: ${distance_saved * 0.5:.2f} (assuming $0.50/km)")
    print(f"   ⏱️  Estimated time saved: {distance_saved * 2:.0f} minutes (assuming 2 min/km)")

print("\n4. WORKLOAD BALANCE")
print("-" * 60)
print(f"{'Metric':<25} {'Initial':<15} {'Optimized':<15} {'Change':<15}")
print("-" * 60)
print(f"{'Mean Workload Ratio':<25} {initial_stats['workload']['mean']:.3f} ({initial_stats['workload']['mean']*100:.1f}%){'':<3} {optimized_stats['workload']['mean']:.3f} ({optimized_stats['workload']['mean']*100:.1f}%){'':<3} {(optimized_stats['workload']['mean'] - initial_stats['workload']['mean']):.3f}")
print(f"{'Median Workload':<25} {initial_stats['workload']['median']:.3f}{'':<10} {optimized_stats['workload']['median']:.3f}{'':<10} {(optimized_stats['workload']['median'] - initial_stats['workload']['median']):.3f}")
print(f"{'Techs over 80% capacity':<25} {initial_stats['workload']['over_80_pct']:<15} {optimized_stats['workload']['over_80_pct']:<15} {(optimized_stats['workload']['over_80_pct'] - initial_stats['workload']['over_80_pct'])}")
print(f"{'Techs over 100% capacity':<25} {initial_stats['workload']['over_100_pct']:<15} {optimized_stats['workload']['over_100_pct']:<15} {(optimized_stats['workload']['over_100_pct'] - initial_stats['workload']['over_100_pct'])}")

print("\n5. DURATION PREDICTION")
print("-" * 60)
print(f"{'Metric':<25} {'Initial':<15} {'Optimized':<15} {'Change':<15}")
print("-" * 60)
print(f"{'Mean Duration (min)':<25} {initial_stats['duration']['mean']:.1f}{'':<13} {optimized_stats['duration']['mean']:.1f}{'':<13} {(optimized_stats['duration']['mean'] - initial_stats['duration']['mean']):+.1f}")
print(f"{'Median Duration':<25} {initial_stats['duration']['median']:.1f}{'':<13} {optimized_stats['duration']['median']:.1f}{'':<13} {(optimized_stats['duration']['median'] - initial_stats['duration']['median']):+.1f}")
print(f"{'Total Duration (hours)':<25} {initial_stats['duration']['total']/60:.1f}{'':<13} {optimized_stats['duration']['total']/60:.1f}{'':<13} {(optimized_stats['duration']['total'] - initial_stats['duration']['total'])/60:+.1f}")

print("\n6. ASSIGNMENT OUTCOME BREAKDOWN")
print("-" * 60)
assignments_improved = sum(1 for x in dispatches['Confidence_improvement'] if x > 0)
assignments_worse = sum(1 for x in dispatches['Confidence_improvement'] if x < 0)
assignments_unchanged = sum(1 for x in dispatches['Confidence_improvement'] if x == 0)
assignments_total = len(dispatches)

print(f"   ✅ Improved assignments:   {assignments_improved:>4} ({assignments_improved/assignments_total*100:>5.1f}%)")
print(f"   ⚠️  Worse assignments:      {assignments_worse:>4} ({assignments_worse/assignments_total*100:>5.1f}%)")
print(f"   ➖ Unchanged assignments:  {assignments_unchanged:>4} ({assignments_unchanged/assignments_total*100:>5.1f}%)")

# Fallback level analysis
print("\n7. FALLBACK LEVEL UTILIZATION")
print("-" * 60)
for level_name in ['level_1', 'level_2', 'level_3', 'no_match']:
    count = sum(1 for x in fallback_levels if x == level_name)
    pct = count / len(fallback_levels) * 100 if len(fallback_levels) > 0 else 0
    level_desc = {
        'level_1': 'Exact Skill Match',
        'level_2': 'Same Category',
        'level_3': 'Related Category',
        'no_match': 'No Match Found'
    }
    print(f"   {level_desc[level_name]:<25} {count:>4} ({pct:>5.1f}%)")

# Model enhancements status
print("\n8. OPTIMIZATION FEATURES USED")
print("-" * 60)
print(f"   Enhanced Success Model:     {'✅ ENABLED' if ENABLE_ENHANCED_SUCCESS_MODEL else '❌ Disabled'}")
if ENABLE_ENHANCED_SUCCESS_MODEL:
    print(f"   - Model features:           {len(FEATURES)} features")
    print(f"   - Model type:               {model_type}")
print(f"   Performance Tracking:       {'✅ ENABLED' if ENABLE_PERFORMANCE_TRACKING else '❌ Disabled'}")
if ENABLE_PERFORMANCE_TRACKING:
    print(f"   - Technicians tracked:      {len(technician_performance)}")
print(f"   Dynamic Weight Optimization: {'✅ ENABLED' if ENABLE_DYNAMIC_WEIGHTS else '❌ Disabled'}")
if ENABLE_DYNAMIC_WEIGHTS:
    print(f"   - Success weight:           {WEIGHT_SUCCESS_PROB:.3f}")
    print(f"   - Confidence weight:        {WEIGHT_CONFIDENCE:.3f}")

# Show assignment mode
print(f"\n{'='*80}")
print(f"   ASSIGNMENT MODE")
print(f"{'='*80}")
if USE_ML_BASED_ASSIGNMENT:
    print(f"   Mode:                       🤖 ML-BASED ASSIGNMENT")
    print(f"   - Strategy:                 Evaluate ALL available technicians using ML model")
    print(f"   - Min success threshold:    {MIN_SUCCESS_THRESHOLD:.1%}")
    print(f"   - Max capacity ratio:       {MAX_CAPACITY_RATIO:.0%}")
    
    # Show seasonal adjustment info if enabled
    if ENABLE_SEASONAL_ADJUSTMENT and 'current_season' in globals():
        print(f"   - Seasonal adjustment:      ✅ ENABLED ({current_season})")
        if 'season_desc' in globals():
            print(f"   - Configuration:            {season_desc}")
    else:
        print(f"   - Seasonal adjustment:      ❌ Disabled (static thresholds)")
    
    print(f"   - Scoring:                  Pure ML success probability")
    print(f"   - No hard-coded fallback levels (model learns from data)")
else:
    print(f"   Mode:                       📋 LEGACY CASCADING FALLBACK")
    print(f"   - Strategy:                 Hard-coded skill match levels")
    print(f"   - Fallback levels:          {len(CASCADING_FALLBACK_LEVELS)}")
    print(f"   Scoring Strategy:           {'✅ SUCCESS PROBABILITY ONLY' if USE_SUCCESS_ONLY else '⚖️  Weighted Combination'}")
    if USE_SUCCESS_ONLY:
        print(f"   - Using: ML success probability (includes distance, workload, skill)")
    else:
        print(f"   - Using: {WEIGHT_SUCCESS_PROB:.0%} success + {WEIGHT_CONFIDENCE:.0%} confidence")

# Overall improvement summary
print("\n9. KEY PERFORMANCE INDICATORS (KPIs)")
print("-" * 60)
success_improvement = optimized_stats['success_prob']['mean'] - initial_stats['success_prob']['mean']
confidence_improvement = optimized_stats['confidence']['mean'] - initial_stats['confidence']['mean']
distance_reduction_pct = -distance_saved_pct  # negative because we want reduction

print(f"   📈 Success Probability Increase:    {success_improvement:+.4f} ({success_improvement/initial_stats['success_prob']['mean']*100:+.1f}%)")
print(f"   📈 Confidence Score Increase:       {confidence_improvement:+.4f} ({confidence_improvement/initial_stats['confidence']['mean']*100:+.1f}%)")
print(f"   📉 Distance Reduction:              {distance_saved:.2f} km ({distance_saved_pct:.1f}%)")
print(f"   📊 Assignments Improved:            {assignments_improved}/{assignments_total} ({assignments_improved/assignments_total*100:.1f}%)")

# Provide interpretation
print("\n10. INTERPRETATION & RECOMMENDATIONS")
print("-" * 60)

if success_improvement > 0.05:
    print("   ✅ EXCELLENT: Success probability significantly improved!")
elif success_improvement > 0.02:
    print("   ✅ GOOD: Noticeable improvement in success probability")
elif success_improvement > 0:
    print("   ⚠️  MARGINAL: Small improvement in success probability")
else:
    print("   ⚠️  WARNING: Success probability did not improve")

if distance_saved > 0:
    print(f"   ✅ COST SAVINGS: Reduced travel distance will save time and fuel")
else:
    print(f"   ⚠️  Note: Optimized for success over distance (may increase travel)")

if optimized_stats['workload']['over_100_pct'] < initial_stats['workload']['over_100_pct']:
    print(f"   ✅ WORKLOAD: Reduced technician overload")
elif optimized_stats['workload']['over_100_pct'] > initial_stats['workload']['over_100_pct']:
    print(f"   ⚠️  WARNING: Some technicians still overloaded")

print("\n" + "=" * 60)

# Report Duration Model Performance
if duration_metrics is not None:
    print("\n📊 DURATION PREDICTION MODEL PERFORMANCE:")
    print("=" * 60)
    print(f"\nModel Type: {'XGBoost' if XGBOOST_AVAILABLE else 'Gradient Boosting'} Regressor")
    print(f"Training Samples: {duration_metrics['n_train']}")
    print(f"Test Samples: {duration_metrics['n_test']}")
    print(f"Number of Features: {duration_metrics['n_features']}")
    print(f"\nTest Set Accuracy:")
    print(f"  Mean Absolute Error (MAE): {duration_metrics['test_mae']:.2f} minutes")
    print(f"  Root Mean Squared Error (RMSE): {duration_metrics['test_rmse']:.2f} minutes")
    print(f"  R² Score: {duration_metrics['test_r2']:.3f}")
    print(f"\nCross-Validation (Training):")
    print(f"  MAE: {duration_metrics['cv_mae']:.2f} ± {duration_metrics['cv_std']:.2f} minutes")
    
    if duration_feature_importance is not None and len(duration_feature_importance) > 0:
        print(f"\nTop 5 Most Important Features:")
        for idx, row in duration_feature_importance.head(5).iterrows():
            print(f"  {idx+1}. {row['feature']:<30} {row['importance']:.4f}")
    
    print("\n" + "=" * 60)

print("\nSample comparison (first 10 dispatches):")
comparison_cols = ['Dispatch_id', 'Assigned_technician_id', 'Optimized_technician_id',
                   'Initial_distance_km', 'Optimized_distance_km',
                   'Initial_workload_ratio', 'Optimized_workload_ratio',
                   'Initial_confidence', 'Optimization_confidence',
                   'Initial_success_prob', 'Predicted_success_prob', 'Fallback_level']
print(dispatches[comparison_cols].head(10).to_string(index=False))
print("\n" + "=" * 60)
