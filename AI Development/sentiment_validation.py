"""
GamePulse 2025 - sentiment validation training
==============================================

Builds x_train / y_train from output/gamepulse_sentiment_validation_sample.csv and
trains the same small binary sentiment network with three hidden-layer
activations (relu, sigmoid, linear) so they can be compared.

Standard setup (typical for small text-classification validation runs)
  features   TF-IDF, 1-2 grams, English stop words, min_df=2, max 2000 terms
  split      20% held-out test, then 15% of the rest as a validation slice (about
             68/12/20 train/val/test), stratified by platform + 4-way label, seed 42,
             made BEFORE any fitting and saved to sentiment_validation_split.csv.
             TF-IDF and the network only ever see the train rows; the validation slice
             logs val_loss/val_accuracy each epoch (used to pick the epoch count) and
             the test rows are scored once at the end.
  network    input -> Dense(16, activation) -> Dense(1, sigmoid)
  loss       binary cross-entropy
  optimizer  Adam, learning rate 0.001, mini-batches of 32
  epochs     30 (10 under-trains the sigmoid network; relu/linear overfit past ~30)

Labels (4-way: positive / negative / neutral / mixed)
  Steam   manual_sentiment_label (AI-assigned, not human-verified).
  Xbox    reviewer star rating: 4-5 positive, 3 neutral, 1-2 negative (proxy; no
          "mixed" ground truth exists for Xbox).
Role of neutral/mixed rows: the neural network is binary, so they are NOT used to
train it or to score its precision/recall. They stay in the held-out split and are
used to evaluate the separate VADER pipeline (gamepulse_pipeline.score_review_text,
the sentiment_score_100 column), which is lexicon-based, needs no training, and has
a middle band (rating 3 / score 40-60) that neutral and mixed reviews should land in.

Run:  python sentiment_validation.py [--refresh-sample]
Writes in output/: sentiment_validation_results.csv (per-epoch history + test metrics),
sentiment_validation_summary.csv (one row per model/pipeline) and
sentiment_validation_split.csv (which review is train / test).
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
SUMMARY_PATH = OUT_DIR / "sentiment_validation_summary.csv"
SPLIT_PATH = OUT_DIR / "sentiment_validation_split.csv"
XBOX_PER_CLASS = 200   # Xbox sample rows per class (positive / negative / neutral)
XBOX_NOTE = "Xbox star-rating proxy (4-5 positive, 3 neutral, 1-2 negative); not human-verified"
DATA_DIR = BASE_DIR.parent / "Data CSVs"
MULTISOURCE_NAMES = ("amazon2023", "amazon2018", "metacritic")

EPOCHS = 30
BATCH_SIZE = 32
LEARNING_RATE = 0.001
HIDDEN_UNITS = 16
TEST_SIZE = 0.2
VAL_SIZE = 0.15   # share of the non-test rows held back as the validation slice
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


def refresh_xbox_sample(sample_path=SAMPLE_PATH, reviews_path=REVIEWS_PATH,
                        per_class=XBOX_PER_CLASS, random_state=RANDOM_STATE):
    """Replace the Xbox rows of the sample with a class-balanced, star-labeled draw.

    A plain random Xbox draw is ~64% positive with few 3-star reviews, which leaves
    almost no neutral rows in a held-out split. Steam rows are left untouched.
    """
    sample = pd.read_csv(sample_path, dtype={"recommendation_id": str})
    reviews = pd.read_csv(
        reviews_path, dtype={"recommendation_id": str},
        usecols=["recommendation_id", "platform", "steam_appid", "xbox_store_id", "game_name",
                 "review_date", "review_text", "sentiment_label"])
    pool = reviews[reviews["platform"].eq("Xbox") & reviews["review_text"].notna()]
    draw = pd.concat([
        pool[pool["sentiment_label"].eq(label)].pipe(lambda g: g.sample(
            min(len(g), per_class), random_state=random_state))
        for label in ("positive", "negative", "neutral")
    ]).drop(columns="platform").rename(columns={"sentiment_label": "manual_sentiment_label"})
    draw["annotation_notes"] = XBOX_NOTE
    steam = sample[sample["xbox_store_id"].isna()]
    out = pd.concat([steam, draw.sample(frac=1, random_state=random_state)], ignore_index=True)
    out = out[sample.columns]
    out.to_csv(sample_path, index=False, encoding="utf-8-sig")
    return out


def load_all_labeled(sample_path=SAMPLE_PATH, reviews_path=REVIEWS_PATH):
    """Every sample row with a label (positive/negative/neutral/mixed) plus its VADER columns."""
    sample = pd.read_csv(sample_path, dtype={"recommendation_id": str})
    reviews = pd.read_csv(
        reviews_path, dtype={"recommendation_id": str},
        usecols=["recommendation_id", "platform", "sentiment_label", "sentiment_score_100",
                 "sentiment_rating", "sentiment_mixed"]).drop_duplicates("recommendation_id")
    df = sample.merge(reviews, on="recommendation_id", how="left")
    manual = df["manual_sentiment_label"].astype("string").str.strip().str.lower()
    vote = df["sentiment_label"].where(df["sentiment_label"].isin(["positive", "negative", "neutral"]))
    df["label4"] = manual.where(manual.isin(["positive", "negative", "neutral", "mixed"]), vote)
    df["label_source"] = np.where(manual.notna() & manual.isin(
        ["positive", "negative", "neutral", "mixed"]), "manual", "reviewer_vote")
    df = df.dropna(subset=["label4", "review_text", "sentiment_score_100"])
    df["platform"] = df["platform"].fillna("Unknown")
    return df.reset_index(drop=True)


def make_heldout_split(df, test_size=TEST_SIZE, val_size=VAL_SIZE, random_state=RANDOM_STATE):
    """Stratified (platform + label) train/val/test assignment; returns a 'split' Series.

    The test rows are carved out first (so they do not depend on val_size); the
    validation slice is then taken from the remaining rows and is used only to
    watch per-epoch generalisation and choose the epoch count, never for the final metrics.
    """
    strata = df["platform"] + "|" + df["label4"]
    rest_idx, test_idx = train_test_split(df.index, test_size=test_size,
                                          random_state=random_state, stratify=strata)
    split = pd.Series("train", index=df.index, name="split")
    split.loc[test_idx] = "test"
    if val_size:
        _, val_idx = train_test_split(rest_idx, test_size=val_size,
                                      random_state=random_state, stratify=strata.loc[rest_idx])
        split.loc[val_idx] = "val"
    return split


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
    return _vectorize(text_train, text_test, y_train, y_test, max_features)


def _vectorize(text_train, text_test, y_train, y_test, max_features=MAX_FEATURES,
               text_val=None, y_val=None):
    """TF-IDF fit on train only. Returns 4 arrays, or 6 (adding x_val, y_val) if text_val given."""
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", min_df=2,
                                 max_features=max_features, sublinear_tf=True)
    x_train = vectorizer.fit_transform(text_train).toarray().astype("float32")  # fit on train only
    x_test = vectorizer.transform(text_test).toarray().astype("float32")
    out = (x_train, x_test,
           y_train.to_numpy(dtype="float32").reshape(-1, 1),
           y_test.to_numpy(dtype="float32").reshape(-1, 1))
    if text_val is None:
        return out
    x_val = vectorizer.transform(text_val).toarray().astype("float32")
    return out + (x_val, y_val.to_numpy(dtype="float32").reshape(-1, 1))


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
          learning_rate=LEARNING_RATE, random_state=RANDOM_STATE, validation=None):
    """Train with Adam on mini-batches. Returns (params, per-epoch history DataFrame).

    validation=(x_val, y_val) adds val_loss / val_accuracy columns (never used to update weights).
    """
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
        row = {"activation": activation, "epoch": epoch, "train_loss": loss,
               "train_accuracy": acc}
        if validation is not None:
            row["val_loss"], row["val_accuracy"] = _loss_and_accuracy(
                validation[1], _forward(params, validation[0], activation)[2])
        history.append(row)
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


def _binary_metrics(true, pred):
    """Accuracy/precision/recall/F1 for the positive class (boolean arrays)."""
    tp = int(np.sum(pred & true))
    precision = tp / pred.sum() if pred.sum() else 0.0
    recall = tp / true.sum() if true.sum() else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"accuracy": float(np.mean(pred == true)), "precision": precision,
            "recall": recall, "f1": f1}


def evaluate_vader(test_df):
    """Score the separate VADER pipeline (sentiment_score_100) on the held-out rows.

    binary   positive vs negative rows only, positive when score >= 50 (same task as
             the neural network, so the numbers are comparable).
    3-class  all held-out rows: score >= 60 -> positive, < 40 -> negative, otherwise
             "mid"; the true class is positive / negative / mid (= neutral or mixed).
    Returns (summary rows, per-label profile DataFrame).
    """
    rows = []
    pn = test_df[test_df["label4"].isin(["positive", "negative"])]
    m = _binary_metrics((pn["label4"] == "positive").to_numpy(),
                        (pn["sentiment_score_100"] >= 50).to_numpy())
    rows.append({"model": "vader_binary", "n_test": len(pn), "test_accuracy": m["accuracy"],
                 "test_precision": m["precision"], "test_recall": m["recall"],
                 "test_f1": m["f1"]})

    true3 = test_df["label4"].replace({"neutral": "mid", "mixed": "mid"})
    score = test_df["sentiment_score_100"]
    pred3 = pd.Series("mid", index=test_df.index).mask(score >= 60, "positive").mask(score < 40, "negative")
    per_class = {}
    for cls in ("positive", "negative", "mid"):
        per_class[cls] = _binary_metrics((true3 == cls).to_numpy(), (pred3 == cls).to_numpy())
    rows.append({"model": "vader_3class_macro", "n_test": len(test_df),
                 "test_accuracy": float((true3 == pred3).mean()),
                 "test_precision": np.mean([v["precision"] for v in per_class.values()]),
                 "test_recall": np.mean([v["recall"] for v in per_class.values()]),
                 "test_f1": np.mean([v["f1"] for v in per_class.values()])})
    for cls, v in per_class.items():
        rows.append({"model": f"vader_3class_{cls}", "n_test": int((true3 == cls).sum()),
                     "test_accuracy": v["accuracy"], "test_precision": v["precision"],
                     "test_recall": v["recall"], "test_f1": v["f1"]})

    profile = (test_df.groupby("label4")
               .agg(n=("label4", "size"), mean_score=("sentiment_score_100", "mean"),
                    share_flagged_mixed=("sentiment_mixed", "mean"))
               .round(3).reset_index())
    profile["share_in_mid_band"] = (profile["label4"].map(
        test_df.assign(mid=pred3.eq("mid")).groupby("label4")["mid"].mean()).round(3))
    return rows, profile


def run_validation(activations=ACTIVATIONS, epochs=EPOCHS, multisource=False,
                   per_class_per_source=10_000, max_features=MAX_FEATURES):
    val = None
    if multisource:
        text, labels, sources = load_multisource_sample(per_class_per_source)
        x_train, x_test, y_train, y_test = build_training_data(text, labels,
                                                               max_features=max_features)
        vader_rows, profile = [], None
    else:
        df = load_all_labeled()
        df["split"] = make_heldout_split(df)
        df[["recommendation_id", "platform", "label4", "label_source", "split"]].to_csv(
            SPLIT_PATH, index=False)
        train_df, test_df = df[df["split"] == "train"], df[df["split"] == "test"]
        val_df = df[df["split"] == "val"]
        print(f"Split ({SPLIT_PATH.name}): {len(train_df)} train / {len(val_df)} validation / "
              f"{len(test_df)} held-out test, seed {RANDOM_STATE}, stratified by platform+label")
        print(pd.crosstab(df["label4"], df["split"]).to_string())
        bin_train = train_df[train_df["label4"].isin(LABELS)]
        bin_val = val_df[val_df["label4"].isin(LABELS)]
        bin_test = test_df[test_df["label4"].isin(LABELS)]
        x_train, x_test, y_train, y_test, x_val, y_val = _vectorize(
            bin_train["review_text"].astype(str), bin_test["review_text"].astype(str),
            bin_train["label4"].map(LABELS), bin_test["label4"].map(LABELS), max_features,
            text_val=bin_val["review_text"].astype(str), y_val=bin_val["label4"].map(LABELS))
        val = (x_val, y_val)
        vader_rows, profile = evaluate_vader(test_df)
    print(f"x_train {x_train.shape}, y_train {y_train.shape}, "
          f"x_test {x_test.shape}, y_test {y_test.shape}")

    histories, summary = [], []
    for activation in activations:
        params, history = train(x_train, y_train, activation, epochs=epochs, validation=val)
        metrics = test(params, x_test, y_test, activation)
        histories.append(history)
        summary.append(metrics)
        msg = (f"{activation:<8} train_acc={history['train_accuracy'].iloc[-1]:.3f} "
               f"test_acc={metrics['test_accuracy']:.3f} test_f1={metrics['test_f1']:.3f}")
        if val is not None:
            best = history.loc[history["val_loss"].idxmin()]
            msg += (f" | val_acc={history['val_accuracy'].iloc[-1]:.3f} "
                    f"best_val_loss_epoch={int(best['epoch'])}")
        print(msg)

    results = pd.concat(histories, ignore_index=True).merge(
        pd.DataFrame(summary), on="activation")
    results.to_csv(RESULTS_PATH, index=False)
    if vader_rows:
        nn_rows = [{"model": f"nn_{s['activation']}", "n_test": len(y_test),
                    **{k: s[k] for k in ("test_accuracy", "test_precision", "test_recall",
                                         "test_f1")}} for s in summary]
        table = pd.DataFrame(nn_rows + vader_rows)
        table.to_csv(SUMMARY_PATH, index=False)
        print("\n" + table.round(3).to_string(index=False))
        print("\nVADER profile by true label (held-out rows):\n" + profile.to_string(index=False))
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GamePulse sentiment validation")
    parser.add_argument("--multisource", action="store_true",
                        help="train on the Amazon 2023/2018 + Metacritic corpora")
    parser.add_argument("--refresh-sample", action="store_true",
                        help="rebuild the Xbox rows of the validation sample (class-balanced)")
    parser.add_argument("--per-class", type=int, default=10_000,
                        help="reviews per class per source (multisource only)")
    parser.add_argument("--max-features", type=int, default=MAX_FEATURES)
    args = parser.parse_args()
    if args.refresh_sample:
        refresh_xbox_sample()
    run_validation(multisource=args.multisource, per_class_per_source=args.per_class,
                   max_features=args.max_features)
