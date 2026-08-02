"""Tests for model construction, evaluation, and prediction."""

from ecg_afib import model, settings


def test_build_model_uses_balanced_weights():
    classifier = model.build_model()
    assert classifier.class_weight == settings.CLASS_WEIGHT


def test_evaluate_returns_all_metrics(feature_table):
    metrics = model.evaluate(feature_table)
    assert set(metrics) == {"auprc", "auroc", "precision", "recall"}


def test_evaluate_beats_random_on_learnable_data(feature_table):
    metrics = model.evaluate(feature_table)
    assert metrics["auprc"] > feature_table[settings.TARGET].mean()


def test_save_and_load_round_trip(feature_table, tmp_path):
    classifier = model.train(feature_table)
    path = tmp_path / "model.joblib"
    model.save(classifier, path=path)

    bundle = model.load(path)
    assert bundle["threshold"] == settings.THRESHOLD
    assert bundle["features"] == settings.FEATURE_NAMES


def test_predict_returns_probability_and_flag(feature_table, tmp_path):
    path = tmp_path / "model.joblib"
    model.save(model.train(feature_table), path=path)
    bundle = model.load(path)

    features = {name: 0.3 if name == "rr_cv" else 800.0
                for name in settings.FEATURE_NAMES}
    probability, flagged = model.predict(bundle, features)

    assert 0.0 <= probability <= 1.0
    assert flagged == (probability >= bundle["threshold"])
