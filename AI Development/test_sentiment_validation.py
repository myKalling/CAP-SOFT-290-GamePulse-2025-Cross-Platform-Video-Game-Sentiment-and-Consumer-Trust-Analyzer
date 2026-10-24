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
def test_train_and_test_run_10_epochs(data, activation):
    x_train, x_test, y_train, y_test = data
    params, history = sv.train(x_train, y_train, activation)
    assert len(history) == sv.EPOCHS == 10
    assert np.isfinite(history["train_loss"]).all()
    assert history["train_loss"].iloc[-1] < history["train_loss"].iloc[0]
    metrics = sv.test(params, x_test, y_test, activation)
    assert 0.0 <= metrics["test_accuracy"] <= 1.0
    assert np.isfinite(metrics["test_loss"])


def test_unknown_activation_rejected(data):
    x_train, _, y_train, _ = data
    with pytest.raises(ValueError):
        sv.train(x_train, y_train, "tanh", epochs=1)
