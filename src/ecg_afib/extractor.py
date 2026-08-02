"""Extract raw ECG data: patient metadata, diagnostic labels, and waveforms."""

import ast
import logging

import pandas as pd
import wfdb

from . import settings

logger = logging.getLogger(__name__)


def has_afib(scp_codes: dict) -> bool:
    """Whether a record carries an atrial fibrillation diagnosis.

    Args:
        scp_codes: The record's SCP statement dictionary.

    Returns:
        True if AFIB is present.

    Note:
        Key presence is the label. PTB-XL leaves rhythm-statement likelihoods
        at 0.0 by default, so a likelihood of zero does not mean "ruled out".
    """
    return "AFIB" in scp_codes


def load_metadata(path=None) -> pd.DataFrame:
    """Load the PTB-XL metadata table with diagnostic labels attached.

    Args:
        path: Location of ptbxl_database.csv. Defaults to settings.

    Returns:
        One row per record, with an added boolean ``has_afib`` column.
    """
    path = path or settings.METADATA_PATH
    df = pd.read_csv(path)
    df["scp_codes"] = df["scp_codes"].apply(ast.literal_eval)
    df[settings.TARGET] = df["scp_codes"].apply(has_afib)

    logger.info(
        "Loaded %d records, %d AFib (%.2f%%)",
        len(df), df[settings.TARGET].sum(), df[settings.TARGET].mean() * 100,
    )
    return df


def load_signal(record_row, lead_index=None):
    """Read one ECG recording from disk.

    Args:
        record_row: A metadata row containing ``filename_lr``.
        lead_index: Which lead to return. Defaults to lead II.

    Returns:
        A 1-D numpy array of voltages in millivolts.
    """
    lead_index = settings.LEAD_INDEX if lead_index is None else lead_index
    path = settings.PTBXL_DIR / record_row["filename_lr"]
    record = wfdb.rdrecord(str(path))
    return record.p_signal[:, lead_index]


def load_signal_csv(source):
    """Read a single-lead signal from a one-column CSV.

    Args:
        source: A file path or file-like object.

    Returns:
        A 1-D numpy array of voltages in millivolts.
    """
    return pd.read_csv(source).iloc[:, 0].to_numpy(dtype=float)
