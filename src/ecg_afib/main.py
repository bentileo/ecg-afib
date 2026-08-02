"""Main entry point for the ECG atrial fibrillation screening pipeline."""

import logging

from . import database, extractor, model, processor, settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_training() -> dict:
    """Build the model from raw data, end to end.

    Returns:
        Cross-validated metrics for the trained model.
    """
    # 1. Extract the metadata and diagnostic labels
    logger.info("Step 1: extracting metadata")
    metadata = extractor.load_metadata()

    # 2. Turn every waveform into rhythm features
    logger.info("Step 2: extracting features from %d records", len(metadata))
    features = processor.build_feature_table(metadata)

    # 3. Drop records where R-peak detection failed
    logger.info("Step 3: filtering by signal quality")
    features = processor.filter_quality(features)
    settings.FEATURES_PATH.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(settings.FEATURES_PATH)

    # 4. Measure performance without patient leakage
    logger.info("Step 4: cross-validating")
    metrics = model.evaluate(features)

    # 5. Fit on everything and save for serving
    logger.info("Step 5: training final model")
    classifier = model.train(features)
    model.save(classifier, metrics=metrics)

    return metrics


def screen(signal, sampling_rate=None) -> dict:
    """Screen one ECG for atrial fibrillation.

    Args:
        signal: 1-D array of lead-II voltages in millivolts.
        sampling_rate: Signal sampling rate in Hz.

    Returns:
        A dict with the probability, whether it was flagged, the heart rate,
        the extracted features, and the R-peak positions for plotting.
        ``probability`` is None when signal quality is too poor to score.
    """
    bundle = model.load()
    sampling_rate = sampling_rate or bundle["sampling_rate"]

    # 1. Detect R-peaks and derive rhythm features
    cleaned, r_peaks = processor.detect_r_peaks(signal, sampling_rate)
    features = processor.extract_features(signal, sampling_rate)

    result = {
        "probability": None,
        "flagged": False,
        "threshold": bundle["threshold"],
        "heart_rate": features["mean_hr_bpm"],
        "features": features,
        "r_peaks": r_peaks,
        "cleaned": cleaned,
        "message": "",
    }

    # 2. Refuse signals the model was never trained to handle
    if not processor.is_quality_ok(features):
        result["message"] = "Signal quality too poor to screen reliably."
        return result

    # 3. Score, and compare against the operating threshold
    probability, flagged = model.predict(bundle, features)
    result["probability"] = probability
    result["flagged"] = flagged
    result["message"] = (
        "Rhythm consistent with atrial fibrillation. Clinician review advised."
        if flagged
        else "No atrial fibrillation detected."
    )
    return result


def screen_and_store(signal, source: str, sampling_rate=None) -> dict:
    """Screen an ECG and record the result.

    Args:
        signal: 1-D array of lead-II voltages.
        source: Where the ECG came from, for the history log.
        sampling_rate: Signal sampling rate in Hz.

    Returns:
        The same dict as screen.
    """
    result = screen(signal, sampling_rate)
    if result["probability"] is not None:
        database.save_prediction(source, result)
    return result


if __name__ == "__main__":
    run_training()
