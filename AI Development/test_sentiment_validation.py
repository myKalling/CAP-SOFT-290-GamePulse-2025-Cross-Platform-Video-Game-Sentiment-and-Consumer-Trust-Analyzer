import numpy as np
import pytest

import sentiment_validation as sv


@pytest.fixture(scope="module")
def data():
    text, labels, _ = sv.load_labeled_sample()
    return sv.build_training_data(text, labels)


def test_split_shapes(data):
    x_train, x_test, y_train, y_test = data
    assert x_train.shape[0] == y_train.shape[0]
    assert x_test.shape[0] == y_test.shape[0]
    assert x_train.shape[1] == x_test.shape[1] <= sv.MAX_FEATURES
    assert set(np.unique(y_train)) <= {0.0, 1.0}
    assert abs(len(x_test) / (len(x_train) + len(x_test)) - sv.TEST_SIZE) < 0.02


@pytest.mark.parametrize("activation", sv.ACTIVATIONS)
def test_train_and_test_run_configured_epochs(data, activation):
    x_train, x_test, y_train, y_test = data
    params, history = sv.train(x_train, y_train, activation)
    assert len(history) == sv.EPOCHS == 30
    assert np.isfinite(history["train_loss"]).all()
    assert history["train_loss"].iloc[-1] < history["train_loss"].iloc[0]
    metrics = sv.test(params, x_test, y_test, activation)
    assert 0.0 <= metrics["test_accuracy"] <= 1.0
    assert np.isfinite(metrics["test_loss"])


def test_validation_slice_logged_per_epoch(data):
    x_train, x_test, y_train, y_test = data
    _, history = sv.train(x_train, y_train, "relu", epochs=2, validation=(x_test, y_test))
    assert {"val_loss", "val_accuracy"} <= set(history.columns)


def test_multisource_sample_is_balanced_per_source():
    pytest.importorskip("pyarrow")
    if not all((sv.DATA_DIR / f"{n}_normalized.csv").exists() for n in sv.MULTISOURCE_NAMES):
        pytest.skip("run prepare_training_data.py first")
    text, labels, sources = sv.load_multisource_sample(per_class_per_source=200)
    assert set(sources) == set(sv.MULTISOURCE_NAMES)
    assert set(labels.unique()) == {0, 1}
    assert text.is_unique
    counts = labels.groupby(sources).mean()
    assert ((counts > 0.35) & (counts < 0.65)).all()


def test_label_mapping():
    import prepare_training_data as ptd
    assert [ptd.amazon_label(s) for s in (1, 2, 3, 4, 5)] == [0, 0, None, 1, 1]
    assert [ptd.metacritic_label(s) for s in (0, 4, 5, 6, 7, 10)] == [0, 0, None, None, 1, 1]


def test_heldout_split_is_stratified_and_disjoint():
    df = sv.load_all_labeled()
    split = sv.make_heldout_split(df)
    assert set(split) == {"train", "val", "test"}
    assert abs((split == "test").mean() - sv.TEST_SIZE) < 0.02
    assert abs((split == "val").mean() - sv.VAL_SIZE * (1 - sv.TEST_SIZE)) < 0.02
    assert set(df["label4"]) == {"positive", "negative", "neutral", "mixed"}
    assert set(df.loc[split == "test", "label4"]) == set(df["label4"])
    assert (split == sv.make_heldout_split(df)).all()   # deterministic
    # test rows must not depend on whether a validation slice is carved out
    assert ((sv.make_heldout_split(df, val_size=0) == "test") == (split == "test")).all()


def test_vader_evaluation_reports_all_metrics():
    df = sv.load_all_labeled()
    test_df = df[sv.make_heldout_split(df) == "test"]
    rows, profile = sv.evaluate_vader(test_df)
    assert {r["model"] for r in rows} >= {"vader_binary", "vader_3class_macro"}
    for r in rows:
        assert all(0.0 <= r[k] <= 1.0 for k in
                   ("test_accuracy", "test_precision", "test_recall", "test_f1"))
    assert set(profile["label4"]) == {"positive", "negative", "neutral", "mixed"}


def test_unknown_activation_rejected(data):
    x_train, _, y_train, _ = data
    with pytest.raises(ValueError):
        sv.train(x_train, y_train, "tanh", epochs=1)
