"""Shared fixtures for the test suite."""

import numpy as np
import pandas as pd
import pytest

from ecg_afib import settings


def _wave(t, center, width, amplitude):
    """A single gaussian bump, used to build synthetic beats."""
    return amplitude * np.exp(-0.5 * ((t - center) / width) ** 2)


def make_ecg(rr_ms=850, n_beats=12, jitter_ms=0, seed=0):
    """Build a synthetic ECG with a known rhythm.

    Args:
        rr_ms: Mean interval between beats.
        n_beats: How many beats to generate.
        jitter_ms: Random variation in interval length, for irregular rhythms.
        seed: Random seed.

    Returns:
        A 1-D array of voltages at settings.SAMPLING_RATE.
    """
    rng = np.random.default_rng(seed)
    beats = []
    for _ in range(n_beats):
        interval = rr_ms + (rng.uniform(-jitter_ms, jitter_ms) if jitter_ms else 0)
        samples = int(interval / 1000 * settings.SAMPLING_RATE)
        t = np.arange(samples) / settings.SAMPLING_RATE * 1000
        beats.append(
            _wave(t, interval * 0.15, 20, 0.15)      # P wave
            + _wave(t, interval * 0.30, 8, 1.2)      # QRS
            + _wave(t, interval * 0.55, 40, 0.3)     # T wave
        )
    return np.concatenate(beats)


@pytest.fixture
def regular_ecg():
    """A metronomic sinus rhythm."""
    return make_ecg()


@pytest.fixture
def irregular_ecg():
    """An irregularly irregular rhythm, as seen in atrial fibrillation."""
    return make_ecg(rr_ms=700, n_beats=14, jitter_ms=300)


@pytest.fixture
def flat_signal():
    """A signal with no detectable beats."""
    return np.random.default_rng(0).normal(0, 0.001, 1000)


@pytest.fixture
def feature_table():
    """A small synthetic feature table with a learnable AFib signal."""
    rng = np.random.default_rng(0)
    n = 400
    rr_cv = rng.uniform(0, 0.4, n)
    return pd.DataFrame({
        "mean_hr_bpm": rng.normal(75, 15, n),
        "n_beats": rng.integers(8, 16, n),
        "rr_mean_ms": rng.normal(850, 120, n),
        "rr_std_ms": rr_cv * 850,
        "rr_cv": rr_cv,
        "rr_min_ms": rng.normal(700, 100, n),
        "rr_max_ms": rng.normal(1000, 150, n),
        "rr_range_ms": rng.normal(300, 80, n),
        "rmssd_ms": rr_cv * 900,
        settings.GROUP_COLUMN: rng.integers(0, 300, n),
        settings.TARGET: rr_cv > 0.12,
    })
