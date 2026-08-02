"""Central configuration for the ECG atrial fibrillation screening project."""

import os
from pathlib import Path

# --- Paths ----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent.parent

DATA_DIR = PROJECT_ROOT / "data"
PTBXL_DIR = DATA_DIR / "ptbxl"
METADATA_PATH = PTBXL_DIR / "ptbxl_database.csv"
FEATURES_PATH = DATA_DIR / "processed" / "features.parquet"

MODEL_PATH = PROJECT_ROOT / "models" / "afib_rf.joblib"
SAMPLES_DIR = PROJECT_ROOT / "samples"

# --- Signal ---------------------------------------------------------------
SAMPLING_RATE = 100          # Hz, PTB-XL low-resolution recordings
LEAD_INDEX = 1               # lead II; order is I, II, III, aVR, aVL, aVF, V1-V6
LEAD_NAME = "II"

# --- Signal quality -------------------------------------------------------
# A 10-second strip at 30-250 bpm holds 5-42 beats. Values outside these
# limits mean R-peak detection failed rather than an unusual rhythm.
MIN_BEATS = 3
MAX_RR_MS = 2000

# --- Features -------------------------------------------------------------
FEATURE_NAMES = [
    "mean_hr_bpm",
    "n_beats",
    "rr_mean_ms",
    "rr_std_ms",
    "rr_cv",
    "rr_min_ms",
    "rr_max_ms",
    "rr_range_ms",
    "rmssd_ms",
]

# --- Model ----------------------------------------------------------------
TARGET = "has_afib"
GROUP_COLUMN = "patient_id"

N_ESTIMATORS = 300
CLASS_WEIGHT = "balanced"
RANDOM_STATE = 42
N_SPLITS = 5

# Recall-first operating point: a missed AFib carries stroke risk, a false
# positive costs only a confirmatory review.
THRESHOLD = 0.10

# --- Supabase -------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "predictions")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
