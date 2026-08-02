"""Tests for the Supabase layer's behavior without credentials."""

from ecg_afib import database


def test_not_configured_without_credentials(monkeypatch):
    monkeypatch.setattr(database.settings, "SUPABASE_URL", "")
    monkeypatch.setattr(database.settings, "SUPABASE_KEY", "")
    assert not database.is_configured()


def test_client_is_none_when_unconfigured(monkeypatch):
    monkeypatch.setattr(database.settings, "SUPABASE_URL", "")
    assert database.get_client() is None


def test_save_is_a_no_op_when_unconfigured(monkeypatch):
    monkeypatch.setattr(database.settings, "SUPABASE_URL", "")
    assert database.save_prediction("test", {"probability": 0.5}) is False


def test_fetch_returns_empty_when_unconfigured(monkeypatch):
    monkeypatch.setattr(database.settings, "SUPABASE_URL", "")
    assert database.fetch_predictions() == []
