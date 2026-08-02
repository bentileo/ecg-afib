"""Store and retrieve screening results in Supabase.

Two credentials are used, deliberately:

  - the PUBLISHABLE key writes results. It is embedded in the application and
    must be assumed public, so the table's row-level security grants it INSERT
    and nothing else.
  - the SECRET key reads them. Streamlit executes on the server, never in the
    browser, so this key is safe here and never reaches a client. Reading is
    additionally gated behind an admin password in the interface.

Every function is a no-op when the relevant credential is absent, so the
project runs without a Supabase account.
"""

import logging
from datetime import datetime, timezone

from . import settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    """Whether results can be written."""
    return bool(settings.SUPABASE_URL and settings.SUPABASE_KEY)


def admin_available() -> bool:
    """Whether results can be read back, which needs the secret key."""
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SECRET_KEY)


def _client(key: str):
    """Build a Supabase client for the given key, or None."""
    if not (settings.SUPABASE_URL and key):
        return None
    try:
        from supabase import create_client
    except ImportError:
        logger.warning("supabase package not installed")
        return None
    return create_client(settings.SUPABASE_URL, key)


def save_prediction(source: str, result: dict) -> bool:
    """Record one screening result using the write-only key.

    Args:
        source: Where the ECG came from, e.g. a sample name or "upload".
        result: The dict returned by main.screen.

    Returns:
        True if the row was written.
    """
    client = _client(settings.SUPABASE_KEY)
    if client is None:
        return False

    row = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "probability": result.get("probability"),
        "flagged": result.get("flagged"),
        "heart_rate_bpm": result.get("heart_rate"),
        "rr_cv": result.get("features", {}).get("rr_cv"),
    }
    try:
        client.table(settings.SUPABASE_TABLE).insert(row).execute()
        return True
    except Exception as error:
        logger.warning("Could not save prediction: %s", error)
        return False


def fetch_predictions(limit: int = 200) -> list:
    """Retrieve recent screening results, newest first.

    Requires the secret key. Returns an empty list without it, so an
    unconfigured deployment simply shows nothing rather than failing.

    Args:
        limit: Maximum rows to return.

    Returns:
        A list of row dicts.
    """
    client = _client(settings.SUPABASE_SECRET_KEY)
    if client is None:
        return []
    try:
        response = (
            client.table(settings.SUPABASE_TABLE)
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as error:
        logger.warning("Could not fetch predictions: %s", error)
        return []
