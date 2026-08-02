"""Tests for label construction and signal loading."""

import io

from ecg_afib import extractor


def test_has_afib_detects_the_code():
    assert extractor.has_afib({"AFIB": 0.0, "NORM": 50.0})


def test_has_afib_ignores_other_codes():
    assert not extractor.has_afib({"NORM": 100.0, "IMI": 80.0})


def test_zero_likelihood_still_counts_as_present():
    """PTB-XL leaves rhythm likelihoods at zero; presence is the label."""
    assert extractor.has_afib({"AFIB": 0.0})


def test_load_signal_csv_reads_one_column():
    csv = io.StringIO("voltage_mv\n0.1\n0.2\n0.3\n")
    signal = extractor.load_signal_csv(csv)
    assert len(signal) == 3
    assert signal[0] == 0.1
