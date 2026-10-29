"""
GamePulse 2025 - public sentiment training data downloader / normalizer
=======================================================================

Downloads three public video-game review corpora into the repo's "Data CSVs" folder
and writes one normalized CSV per source (columns: text, rating, label, source).

  amazon2023   Amazon Reviews 2023, Video_Games (McAuley Lab, UCSD) - first
               AMAZON_2023_MAX_ROWS reviews of the 2.7 GB raw file are streamed
  amazon2018   Amazon Reviews 2018, Video Games 5-core (Julian McAuley, UCSD)
  metacritic   Metacritic player reviews (Wada1/Metacritic_Games_Reviews_Dataset,
               Hugging Face, CC BY 4.0)

Labels (binary, matching the model): Amazon stars >=4 -> 1, <=2 -> 0, 3 dropped.
Metacritic 0-10 user score >=7 -> 1, <=4 -> 0, 5-6 dropped.

Amazon data is for research / non-commercial use; see the dataset pages for terms.

Run:  python prepare_training_data.py [--force]
"""

import argparse
import gzip
import json
from pathlib import Path

import pandas as pd
import requests

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "Data CSVs"

AMAZON_2023_URL = ("https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/"
                   "resolve/main/raw/review_categories/Video_Games.jsonl")
AMAZON_2018_URL = "http://jmcauley.ucsd.edu/data/amazon_v2/categoryFilesSmall/Video_Games_5.json.gz"
METACRITIC_URL = ("https://huggingface.co/datasets/Wada1/Metacritic_Games_Reviews_Dataset/"
                  "resolve/main/data/train-00000-of-00001.parquet")

AMAZON_2023_MAX_ROWS = 500_000
AMAZON_2018_RAW = DATA_DIR / "amazon2018_Video_Games_5.json.gz"
METACRITIC_RAW = DATA_DIR / "metacritic_player_reviews.parquet"

NORMALIZED = {name: DATA_DIR / f"{name}_normalized.csv"
              for name in ("amazon2023", "amazon2018", "metacritic")}
COLUMNS = ["text", "rating", "label", "source"]


def amazon_label(stars):
    return 1 if stars >= 4 else 0 if stars <= 2 else None


def metacritic_label(score):
    return 1 if score >= 7 else 0 if score <= 4 else None


def _download(url, dest, verify=True):
    if dest.exists():
        return
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=60, verify=verify) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.replace(dest)


def _frame(rows, source):
    df = pd.DataFrame(rows, columns=["text", "rating"])
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() > 0]
    df["label"] = df["rating"].map(amazon_label if source.startswith("amazon") else metacritic_label)
    df = df.dropna(subset=["label"]).drop_duplicates("text")
    df["label"] = df["label"].astype(int)
    df["source"] = source
    return df[COLUMNS]


def _combine(title, text):
    title, text = (title or "").strip(), (text or "").strip()
    return f"{title}. {text}" if title and text else title or text


def build_amazon_2023(max_rows=AMAZON_2023_MAX_ROWS):
    rows = []
    with requests.get(AMAZON_2023_URL, stream=True, timeout=60) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            rec = json.loads(line)
            rows.append((_combine(rec.get("title"), rec.get("text")), rec.get("rating")))
            if len(rows) >= max_rows:
                break  # stop early instead of pulling the whole 2.7 GB file
    return _frame(rows, "amazon2023")


def build_amazon_2018():
    _download(AMAZON_2018_URL, AMAZON_2018_RAW)
    rows = []
    with gzip.open(AMAZON_2018_RAW, "rt", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            rows.append((_combine(rec.get("summary"), rec.get("reviewText")), rec.get("overall")))
    return _frame(rows, "amazon2018")


def build_metacritic():
    _download(METACRITIC_URL, METACRITIC_RAW)
    raw = pd.read_parquet(METACRITIC_RAW, columns=["Review", "Score"])
    return _frame(zip(raw["Review"], raw["Score"]), "metacritic")


BUILDERS = {"amazon2023": build_amazon_2023, "amazon2018": build_amazon_2018,
            "metacritic": build_metacritic}


def prepare(force=False):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, builder in BUILDERS.items():
        path = NORMALIZED[name]
        if path.exists() and not force:
            print(f"{name}: {path.name} exists, skipping")
            continue
        df = builder()
        df.to_csv(path, index=False)
        print(f"{name}: {len(df):,} rows, positive share {df['label'].mean():.2f} -> {path.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--force", action="store_true", help="rebuild existing normalized CSVs")
    prepare(parser.parse_args().force)
