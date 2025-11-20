"""
Configuration file for Dispatch Optimization
Contains model paths and system settings
"""

import os

# Model file paths
MODEL_CONFIG = {
    'preprocessor_path': 'models/preprocessor.pkl',
    'success_model_path': 'models/success_model.pkl',
    'duration_model_path': 'models/duration_model.pkl',
}

# Database configuration (from environment variables)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'dispatch_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'schema': os.getenv('DB_SCHEMA', 'team_faiber_force'),
}

# Optimization weights
OPTIMIZATION_WEIGHTS = {
    'success_probability': 50.0,  # 50%
    'workload_balance': 35.0,     # 35%
    'travel_distance': 10.0,      # 10%
    'estimated_overrun': 5.0,     # 5%
}

# Priority levels (for sorting)
PRIORITY_ORDER = {
    'Critical': 0,
    'High': 1,
    'Normal': 2,
    'Low': 3
}

# Overlap thresholds by priority
OVERLAP_THRESHOLD = {
    'Critical': 0.20,  # 20% workload overlap allowed
    'High': 0.25,      # 25% workload overlap allowed
}

# Date filter for optimization
DATE_FILTER = '2025-11-12'  # Only process dispatches from this date onwards

# CSV fallback file paths
CSV_FILES = {
    'dispatches': 'current_dispatches.csv',
    'technicians': 'technicians.csv',
    'calendar': 'technician_calendar_10k.csv',
    'dispatch_history': 'dispatch_history.csv',
}

# Output file paths
OUTPUT_FILES = {
    'assignments': 'optimized_assignments.csv',
    'warnings': 'optimization_warnings.csv',
    'report': 'optimization_report.txt',
}

# Hybrid model configuration
HYBRID_CONFIG = {
    'use_hybrid': True,       # Use hybrid ML + rules approach
    'rule_weight': 0.7,       # Weight for rule-based component (0-1)
    'ml_weight': 0.3,         # Weight for ML component (automatically 1 - rule_weight)
}

# Business rules thresholds
BUSINESS_RULES = {
    'max_distance_km': 250,           # Maximum reasonable distance
    'ideal_distance_km': 50,          # Ideal distance threshold
    'max_workload_ratio': 1.2,        # Maximum workload before penalties
    'ideal_workload_ratio': 0.8,      # Ideal workload threshold
    'skill_match_bonus': 0.15,        # Bonus for skill match
    'skill_mismatch_penalty': 0.25,   # Penalty for skill mismatch
}

# Model check and warning
def check_models_exist():
    """Check if required model files exist"""
    missing_models = []
    for name, path in MODEL_CONFIG.items():
        if not os.path.exists(path):
            missing_models.append(path)
    
    if missing_models:
        print("\n⚠️  WARNING: Missing model files:")
        for model in missing_models:
            print(f"  - {model}")
        print("\nOptimization will use rule-based approach only.")
        print("To use ML models, ensure model files are in the 'models/' directory.\n")
        return False
    return True


if __name__ == "__main__":
    print("Configuration loaded:")
    print(f"  Database Schema: {DB_CONFIG['schema']}")
    print(f"  Date Filter: {DATE_FILTER}")
    print(f"  Use Hybrid: {HYBRID_CONFIG['use_hybrid']}")
    print(f"\nOptimization Weights:")
    for key, value in OPTIMIZATION_WEIGHTS.items():
        print(f"  - {key}: {value}%")
    
    print(f"\nModel files exist: {check_models_exist()}")

