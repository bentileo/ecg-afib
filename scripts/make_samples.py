"""Write a set of sample ECGs for the dashboard to demonstrate on.

The full dataset is several gigabytes and is not committed, so a deployed app
has no signals to show. This script extracts a handful and writes each as a
small one-column CSV into `samples/`. Those CSVs are committed.

Selection is not arbitrary. A record carrying the AFIB label is not necessarily
a clear example of it: some are atrial fibrillation with a rapid, deceptively
regular-looking ventricular response, and some are better explained by another
supraventricular rhythm. Since these samples exist to demonstrate what the model
detects, they are chosen by measured rhythm variability rather than by record
order — unambiguous examples of the pattern, at both ends.

Run once, locally, where the dataset is present:

    make samples
"""

import logging

import pandas as pd

from ecg_afib import extractor, processor, settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

SAMPLES_PER_CLASS = 3

# A clear case of atrial fibrillation has RR variability well above the AFib
# median of 0.197. A clear normal sits well below the non-AFib median of 0.026.
MIN_AFIB_VARIABILITY = 0.20
MAX_NORMAL_VARIABILITY = 0.03

# How many candidates to measure before giving up on finding enough.
SEARCH_LIMIT = 400


def pick_by_variability(candidates, wanted, above=None, below=None):
    """Choose records whose measured rhythm variability meets a bound.

    Args:
        candidates: Metadata rows to consider.
        wanted: How many records to return.
        above: Keep records whose rr_cv exceeds this.
        below: Keep records whose rr_cv falls under this.

    Returns:
        A list of (record, signal, rr_cv) for the chosen records.
    """
    chosen = []

    for _, record in candidates.head(SEARCH_LIMIT).iterrows():
        try:
            signal = extractor.load_signal(record)
        except FileNotFoundError:
            continue

        features = processor.extract_features(signal)
        if not processor.is_quality_ok(features):
            continue

        variability = features["rr_cv"]
        if above is not None and variability <= above:
            continue
        if below is not None and variability >= below:
            continue

        chosen.append((record, signal, variability))
        if len(chosen) == wanted:
            break

    return chosen


def write_samples(chosen, label):
    """Write each chosen signal to samples/<label>_<n>.csv."""
    for index, (record, signal, variability) in enumerate(chosen, start=1):
        path = settings.SAMPLES_DIR / f"{label}_{index}.csv"
        pd.DataFrame({"voltage_mv": signal}).to_csv(path, index=False)
        logger.info(
            "%-14s ecg_id %-6s rr_cv %.3f", path.name, record["ecg_id"], variability
        )


def main() -> None:
    """Extract clear examples of each rhythm into samples/."""
    metadata = extractor.load_metadata()
    settings.SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Selecting atrial fibrillation examples (rr_cv > %.2f)", MIN_AFIB_VARIABILITY)
    afib = pick_by_variability(
        metadata[metadata[settings.TARGET]],
        SAMPLES_PER_CLASS,
        above=MIN_AFIB_VARIABILITY,
    )
    write_samples(afib, "afib")

    logger.info("Selecting normal examples (rr_cv < %.2f)", MAX_NORMAL_VARIABILITY)
    normal = pick_by_variability(
        metadata[~metadata[settings.TARGET]],
        SAMPLES_PER_CLASS,
        below=MAX_NORMAL_VARIABILITY,
    )
    write_samples(normal, "normal")

    total = len(afib) + len(normal)
    logger.info("\n%d samples written to %s", total, settings.SAMPLES_DIR)
    if total < SAMPLES_PER_CLASS * 2:
        logger.warning(
            "Fewer samples than requested. Loosen the variability bounds or "
            "raise SEARCH_LIMIT."
        )


if __name__ == "__main__":
    main()
