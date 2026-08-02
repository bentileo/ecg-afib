"""Tests for feature extraction and the signal-quality gate."""

import numpy as np

from ecg_afib import processor, settings


def test_extract_features_returns_every_named_feature(regular_ecg):
    features = processor.extract_features(regular_ecg)
    assert set(settings.FEATURE_NAMES) <= set(features)


def test_regular_rhythm_has_low_variability(regular_ecg):
    features = processor.extract_features(regular_ecg)
    assert features["rr_cv"] < 0.05


def test_irregular_rhythm_has_high_variability(irregular_ecg):
    features = processor.extract_features(irregular_ecg)
    assert features["rr_cv"] > 0.10


def test_irregular_rhythm_separates_from_regular(regular_ecg, irregular_ecg):
    regular = processor.extract_features(regular_ecg)
    irregular = processor.extract_features(irregular_ecg)
    assert irregular["rr_cv"] > regular["rr_cv"]


def test_undefined_features_are_nan_not_zero():
    """A single beat yields no interval, so interval features must be NaN."""
    from tests.conftest import make_ecg
    features = processor.extract_features(make_ecg(n_beats=1))
    assert np.isnan(features["rr_cv"])
    assert not np.isnan(features["n_beats"])


def test_detect_r_peaks_finds_every_beat(regular_ecg):
    _, r_peaks = processor.detect_r_peaks(regular_ecg)
    assert len(r_peaks) >= 10


def test_quality_gate_rejects_flat_signal(flat_signal):
    features = processor.extract_features(flat_signal)
    assert not processor.is_quality_ok(features)


def test_quality_gate_accepts_normal_rhythm(regular_ecg):
    features = processor.extract_features(regular_ecg)
    assert processor.is_quality_ok(features)


def test_filter_quality_removes_bad_records(feature_table):
    table = feature_table.copy()
    table.loc[0, "n_beats"] = 1
    table.loc[1, "rr_max_ms"] = 9000
    filtered = processor.filter_quality(table)
    assert len(filtered) == len(table) - 2
