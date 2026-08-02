"""Turn raw ECG waveforms into a clean, model-ready feature table.

Features describe heart rate and rhythm regularity, derived entirely from
R-peak positions. See the README for why wave-morphology features are excluded.
"""

import logging

import neurokit2 as nk
import numpy as np
import pandas as pd

from . import settings
from .extractor import load_signal

logger = logging.getLogger(__name__)


def detect_r_peaks(signal, sampling_rate=None):
    """Clean a signal and locate its R-peaks.

    Args:
        signal: 1-D array of ECG voltages.
        sampling_rate: Signal sampling rate in Hz.

    Returns:
        A tuple of (cleaned signal, R-peak sample indices).
    """
    sampling_rate = sampling_rate or settings.SAMPLING_RATE
    cleaned = nk.ecg_clean(signal, sampling_rate=sampling_rate)
    _, info = nk.ecg_peaks(cleaned, sampling_rate=sampling_rate)
    return cleaned, info["ECG_R_Peaks"]


def extract_features(signal, sampling_rate=None) -> dict:
    """Compute rhythm features from one ECG signal.

    Args:
        signal: 1-D array of ECG voltages.
        sampling_rate: Signal sampling rate in Hz.

    Returns:
        A dict keyed by settings.FEATURE_NAMES. Values are NaN where a feature
        is undefined, never zero, which a model would read as a real value.
    """
    sampling_rate = sampling_rate or settings.SAMPLING_RATE
    _, r_peaks = detect_r_peaks(signal, sampling_rate)

    duration_sec = len(signal) / sampling_rate
    rr_ms = np.diff(r_peaks) / sampling_rate * 1000

    features = {name: np.nan for name in settings.FEATURE_NAMES}
    features["mean_hr_bpm"] = len(r_peaks) / duration_sec * 60
    features["n_beats"] = len(r_peaks)

    if len(rr_ms) == 0:
        return features

    rr_mean, rr_std = float(np.mean(rr_ms)), float(np.std(rr_ms))
    features.update({
        "rr_mean_ms": rr_mean,
        "rr_std_ms": rr_std,
        # Spread relative to rate. This is what detects AFib with a controlled
        # ventricular rate, which mean heart rate alone would call normal.
        "rr_cv": rr_std / rr_mean if rr_mean else np.nan,
        "rr_min_ms": float(np.min(rr_ms)),
        "rr_max_ms": float(np.max(rr_ms)),
        "rr_range_ms": float(np.max(rr_ms) - np.min(rr_ms)),
        "rmssd_ms": float(np.sqrt(np.mean(np.diff(rr_ms) ** 2))) if len(rr_ms) > 1 else np.nan,
    })
    return features


def is_quality_ok(features: dict) -> bool:
    """Whether R-peak detection succeeded well enough to trust the features.

    Args:
        features: A feature dict from extract_features.

    Returns:
        True if the record is usable.
    """
    return (
        np.isfinite(features.get("rr_cv", np.nan))
        and features.get("n_beats", 0) >= settings.MIN_BEATS
        and features.get("rr_max_ms", np.inf) <= settings.MAX_RR_MS
    )


def build_feature_table(metadata: pd.DataFrame) -> pd.DataFrame:
    """Extract features for every record in a metadata table.

    Args:
        metadata: Rows from extractor.load_metadata.

    Returns:
        One row per successfully processed record, with features plus
        ``ecg_id``, ``patient_id``, and the target column.
    """
    rows, failures = [], 0

    for _, record in metadata.iterrows():
        try:
            features = extract_features(load_signal(record))
        except Exception:
            failures += 1
            continue

        features["ecg_id"] = record["ecg_id"]
        features[settings.GROUP_COLUMN] = record[settings.GROUP_COLUMN]
        features[settings.TARGET] = record[settings.TARGET]
        rows.append(features)

    if failures:
        logger.warning("Could not read %d records", failures)

    return pd.DataFrame(rows)


def filter_quality(features: pd.DataFrame) -> pd.DataFrame:
    """Drop records whose R-peak detection failed.

    Args:
        features: A feature table from build_feature_table.

    Returns:
        The table without failed records.

    Note:
        These exclusions are label-biased: roughly 15% are AFib against a 6.9%
        baseline, because fibrillatory baselines are harder to delineate. This
        makes reported metrics modestly optimistic. See the README.
    """
    failed = (
        features["rr_cv"].isna()
        | (features["n_beats"] < settings.MIN_BEATS)
        | (features["rr_max_ms"] > settings.MAX_RR_MS)
    )
    logger.info(
        "Dropped %d low-quality records (%d AFib); %d remain",
        failed.sum(), features.loc[failed, settings.TARGET].sum(), (~failed).sum(),
    )
    return features[~failed].copy()
