"""Store and retrieve screening results in Supabase.

Every function is a no-op when credentials are absent, so the project runs
without a Supabase account; only prediction history is unavailable.
"""

import logging
from datetime import UTC, datetime

from . import settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    """Whether Supabase credentials are present."""
    return bool(settings.SUPABASE_URL and settings.SUPABASE_KEY)


def get_client():
    """Create a Supabase client.

    Returns:
        A client, or None if credentials are missing or the library is absent.
    """
    if not is_configured():
        return None
    try:
        from supabase import create_client
    except ImportError:
        logger.warning("supabase package not installed")
        return None
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def save_prediction(source: str, result: dict) -> bool:
    """Record one screening result.

    Args:
        source: Where the ECG came from, e.g. a sample name or "upload".
        result: The dict returned by main.screen.

    Returns:
        True if the row was written.
    """
    client = get_client()
    if client is None:
        return False

    row = {
        "created_at": datetime.now(UTC).isoformat(),
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


def fetch_predictions(limit: int = 100) -> list:
    """Retrieve recent screening results, newest first.

    Args:
        limit: Maximum rows to return.

    Returns:
        A list of row dicts, empty if unavailable.
    """
    client = get_client()
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
