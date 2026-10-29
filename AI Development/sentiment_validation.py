"""
GamePulse 2025 - sentiment validation training
==============================================

Builds x_train / y_train from output/gamepulse_sentiment_validation_sample.csv and
trains the same small binary sentiment network with three hidden-layer
activations (relu, sigmoid, linear) so they can be compared.

Standard setup (typical for small text-classification validation runs)
  features   TF-IDF, 1-2 grams, English stop words, min_df=2, max 2000 terms
  split      80/20 stratified train/test, fixed seed
  network    input -> Dense(16, activation) -> Dense(1, sigmoid)
  loss       binary cross-entropy
  optimizer  Adam, learning rate 0.001, mini-batches of 32
  epochs     10

Labels: manual_sentiment_label (positive/negative) when annotators have filled it
in; otherwise the reviewer's Steam vote (sentiment_label) from the cleaned
reviews file is used as a proxy. neutral/mixed/blank manual labels are skipped
because the model is binary.

Run:  python sentiment_validation.py
Writes output/sentiment_validation_results.csv (per-epoch history + test metrics).
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "output"
SAMPLE_PATH = OUT_DIR / "gamepulse_sentiment_validation_sample.csv"
REVIEWS_PATH = OUT_DIR / "gamepulse_reviews_clean.csv"
RESULTS_PATH = OUT_DIR / "sentiment_validation_results.csv"
DATA_DIR = BASE_DIR.parent / "Data CSVs"
MULTISOURCE_NAMES = ("amazon2023", "amazon2018", "metacritic")

EPOCHS = 10
BATCH_SIZE = 32
LEARNING_RATE = 0.001
HIDDEN_UNITS = 16
TEST_SIZE = 0.2
RANDOM_STATE = 42
MAX_FEATURES = 2000
ACTIVATIONS = ("relu", "sigmoid", "linear")
LABELS = {"positive": 1, "negative": 0}


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def load_labeled_sample(sample_path=SAMPLE_PATH, reviews_path=REVIEWS_PATH):
    """Return (text, label 0/1, label_source) for every usable sample row."""
    sample = pd.read_csv(sample_path, dtype={"recommendation_id": str})
    manual = sample["manual_sentiment_label"].astype("string").str.strip().str.lower()
    sample["label"] = manual.map(LABELS)
    sample["label_source"] = np.where(sample["label"].notna(), "manual", "")

    missing = sample["label"].isna() & manual.isna()   # untouched rows fall back to the vote
    if missing.any():
        votes = pd.read_csv(reviews_path, usecols=["recommendation_id", "sentiment_label"],
                            dtype={"recommendation_id": str})
        proxy = (votes.drop_duplicates("recommendation_id")
                 .set_index("recommendation_id")["sentiment_label"].map(LABELS))
        fallback = sample.loc[missing, "recommendation_id"].map(proxy)
        sample.loc[missing, "label"] = fallback
        sample.loc[missing & fallback.notna(), "label_source"] = "steam_vote"

    usable = sample.dropna(subset=["label", "review_text"])
    return usable["review_text"].astype(str), usable["label"].astype(int), usable["label_source"]


def load_multisource_sample(per_class_per_source=10_000, sources=None, data_dir=DATA_DIR,
                            random_state=RANDOM_STATE):
    """Class-balanced sample from the public corpora built by prepare_training_data.py.

    Returns (text, label 0/1, source). Draws up to per_class_per_source positive and
    negative reviews from each source so the skewed star distributions don't dominate.
    """
    sources = sources or MULTISOURCE_NAMES
    parts = []
    for name in sources:
        path = Path(data_dir) / f"{name}_normalized.csv"
        if not path.exists():
            raise FileNotFoundError(f"{path} missing - run prepare_training_data.py first")
        df = pd.read_csv(path, usecols=["text", "label", "source"])
        for label in (0, 1):
            group = df[df["label"] == label]
            parts.append(group.sample(min(len(group), per_class_per_source),
                                      random_state=random_state))
    combined = (pd.concat(parts).drop_duplicates("text")   # 2018 and 2023 overlap
                .sample(frac=1, random_state=random_state).dropna(subset=["text"]))
    return combined["text"].astype(str), combined["label"].astype(int), combined["source"]


def build_training_data(text, labels, test_size=TEST_SIZE, random_state=RANDOM_STATE,
                        max_features=MAX_FEATURES):
    """TF-IDF features + stratified split -> x_train, x_test, y_train, y_test."""
    text_train, text_test, y_train, y_test = train_test_split(
        text, labels, test_size=test_size, random_state=random_state, stratify=labels)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", min_df=2,
                                 max_features=max_features, sublinear_tf=True)
    x_train = vectorizer.fit_transform(text_train).toarray().astype("float32")  # fit on train only
    x_test = vectorizer.transform(text_test).toarray().astype("float32")
    return (x_train, x_test,
            y_train.to_numpy(dtype="float32").reshape(-1, 1),
            y_test.to_numpy(dtype="float32").reshape(-1, 1))


# --------------------------------------------------------------------------
# Model (NumPy, so no deep-learning framework is required)
# --------------------------------------------------------------------------
def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def _activate(z, name):
    if name == "relu":
        return np.maximum(z, 0.0)
    if name == "sigmoid":
        return _sigmoid(z)
    if name == "linear":
        return z
    raise ValueError(f"Unknown activation: {name}")


def _activation_grad(z, a, name):
    if name == "relu":
        return (z > 0).astype(z.dtype)
    if name == "sigmoid":
        return a * (1.0 - a)
    return np.ones_like(z)


def _init_params(n_features, activation, rng):
    # He init for relu, Glorot otherwise (the usual defaults)
    scale = np.sqrt(2.0 / n_features) if activation == "relu" else np.sqrt(1.0 / n_features)
    return {
        "W1": rng.normal(0, scale, (n_features, HIDDEN_UNITS)).astype("float32"),
        "b1": np.zeros(HIDDEN_UNITS, dtype="float32"),
        "W2": rng.normal(0, np.sqrt(1.0 / HIDDEN_UNITS), (HIDDEN_UNITS, 1)).astype("float32"),
        "b2": np.zeros(1, dtype="float32"),
    }


def _forward(params, x, activation):
    z1 = x @ params["W1"] + params["b1"]
    a1 = _activate(z1, activation)
    return z1, a1, _sigmoid(a1 @ params["W2"] + params["b2"])


def _loss_and_accuracy(y_true, y_prob):
    p = np.clip(y_prob, 1e-7, 1 - 1e-7)
    loss = float(-np.mean(y_true * np.log(p) + (1 - y_true) * np.log(1 - p)))
    return loss, float(np.mean((y_prob >= 0.5) == (y_true >= 0.5)))


def train(x_train, y_train, activation, epochs=EPOCHS, batch_size=BATCH_SIZE,
          learning_rate=LEARNING_RATE, random_state=RANDOM_STATE):
    """Train with Adam on mini-batches. Returns (params, per-epoch history DataFrame)."""
    rng = np.random.default_rng(random_state)
    params = _init_params(x_train.shape[1], activation, rng)
    m = {k: np.zeros_like(v) for k, v in params.items()}
    v = {k: np.zeros_like(p) for k, p in params.items()}
    beta1, beta2, eps, step = 0.9, 0.999, 1e-7, 0
    history = []
    n = len(x_train)

    for epoch in range(1, epochs + 1):
        order = rng.permutation(n)
        for start in range(0, n, batch_size):
            idx = order[start:start + batch_size]
            xb, yb = x_train[idx], y_train[idx]
            z1, a1, out = _forward(params, xb, activation)
            d_out = (out - yb) / len(idx)                      # BCE + sigmoid gradient
            d_a1 = d_out @ params["W2"].T
            d_z1 = d_a1 * _activation_grad(z1, a1, activation)
            grads = {"W2": a1.T @ d_out, "b2": d_out.sum(0),
                     "W1": xb.T @ d_z1, "b1": d_z1.sum(0)}
            step += 1
            for k in params:
                m[k] = beta1 * m[k] + (1 - beta1) * grads[k]
                v[k] = beta2 * v[k] + (1 - beta2) * grads[k] ** 2
                m_hat = m[k] / (1 - beta1 ** step)
                v_hat = v[k] / (1 - beta2 ** step)
                params[k] -= (learning_rate * m_hat / (np.sqrt(v_hat) + eps)).astype("float32")

        loss, acc = _loss_and_accuracy(y_train, _forward(params, x_train, activation)[2])
        history.append({"activation": activation, "epoch": epoch, "train_loss": loss,
                        "train_accuracy": acc})
    return params, pd.DataFrame(history)


def test(params, x_test, y_test, activation):
    """Evaluate on held-out data: loss, accuracy, precision, recall, F1."""
    prob = _forward(params, x_test, activation)[2]
    loss, acc = _loss_and_accuracy(y_test, prob)
    pred, true = (prob >= 0.5).ravel(), (y_test >= 0.5).ravel()
    tp = int(np.sum(pred & true))
    precision = tp / pred.sum() if pred.sum() else 0.0
    recall = tp / true.sum() if true.sum() else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"activation": activation, "test_loss": loss, "test_accuracy": acc,
            "test_precision": precision, "test_recall": recall, "test_f1": f1}


def run_validation(activations=ACTIVATIONS, epochs=EPOCHS, multisource=False,
                   per_class_per_source=10_000, max_features=MAX_FEATURES):
    if multisource:
        text, labels, sources = load_multisource_sample(per_class_per_source)
    else:
        text, labels, sources = load_labeled_sample()
    x_train, x_test, y_train, y_test = build_training_data(text, labels,
                                                           max_features=max_features)
    print(f"Labeled rows: {len(labels)} ({sources.value_counts().to_dict()}), "
          f"positive share {labels.mean():.2f}")
    print(f"x_train {x_train.shape}, y_train {y_train.shape}, "
          f"x_test {x_test.shape}, y_test {y_test.shape}")

    histories, summary = [], []
    for activation in activations:
        params, history = train(x_train, y_train, activation, epochs=epochs)
        metrics = test(params, x_test, y_test, activation)
        histories.append(history)
        summary.append(metrics)
        print(f"{activation:<8} train_acc={history['train_accuracy'].iloc[-1]:.3f} "
              f"test_acc={metrics['test_accuracy']:.3f} test_f1={metrics['test_f1']:.3f}")

    results = pd.concat(histories, ignore_index=True).merge(
        pd.DataFrame(summary), on="activation")
    results.to_csv(RESULTS_PATH, index=False)
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GamePulse sentiment validation")
    parser.add_argument("--multisource", action="store_true",
                        help="train on the Amazon 2023/2018 + Metacritic corpora")
    parser.add_argument("--per-class", type=int, default=10_000,
                        help="reviews per class per source (multisource only)")
    parser.add_argument("--max-features", type=int, default=MAX_FEATURES)
    args = parser.parse_args()
    run_validation(multisource=args.multisource, per_class_per_source=args.per_class,
                   max_features=args.max_features)
