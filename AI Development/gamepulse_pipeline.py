"""
GamePulse 2025 - data pull + cleaning pipeline
==============================================

What it does
  1. RAWG      -> finds popular PC games released in 2025 (and their Steam links)
  2. Steam     -> confirms release year, free vs paid, and pulls real player reviews
  3. IGDB      -> (optional) adds IGDB rating / genres
  4. Cleans    -> removes junk reviews and writes a simple CSV

Outputs (in ./output)
  gamepulse_reviews_clean.csv   <- main file: one row per review, game info included
  gamepulse_games_clean.csv     <- the 20 selected games (handy for your Games table)
  cleaning_log.csv              <- how many rows each cleaning step removed

Review sentiment is scored from review text with VADER. Its compound score is
mapped from -1..1 to 0..100, then grouped into five 20-point rating categories.
The existing sentiment_label remains the reviewer's Steam vote when available.

Supplemental data in ./Data CSVs is included in these outputs:
  steam 2025.csv                 <- additional Steam reviews and games
  xbox-games-2025.csv            <- Xbox game catalog and ratings

Run:  python gamepulse_pipeline.py
Raw API responses are cached in ./data/raw so re-runs are fast.
Delete that folder if you want a completely fresh pull.
"""

import html
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# --------------------------------------------------------------------------
# CONFIG - change these as needed
# --------------------------------------------------------------------------
YEAR = 2025
FREE_TARGET = 10            # free-to-play games to keep
PAID_TARGET = 10            # paid games to keep
RAWG_PAGES = 4              # 40 games per page -> candidate pool (more = slower)
REVIEWS_TO_FETCH = 150      # raw Steam reviews per game (cleaning removes some)
MIN_WORDS = 4               # reviews shorter than this are "low information"
REQUEST_DELAY = 1.0         # seconds between live API calls (be polite to Steam)

RAWG_KEY = os.getenv("RAWG_API_KEY")
IGDB_CLIENT_ID = os.getenv("IGDB_CLIENT_ID")
IGDB_CLIENT_SECRET = os.getenv("IGDB_CLIENT_SECRET")

RAW_DIR = BASE_DIR / "data" / "raw"
OUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "Data CSVs"
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Short reviews are kept if they contain one of these (they say something specific)
GAMING_TERMS = {
    "fps", "lag", "laggy", "bug", "bugs", "buggy", "crash", "crashes", "crashing",
    "grind", "grindy", "p2w", "pay2win", "dlc", "gacha", "toxic",
    "cheaters", "hackers", "aimbot", "stutter", "stuttering", "optimization",
    "unoptimized", "microtransactions", "servers", "matchmaking", "netcode",
    "overpriced", "goty", "refund", "refunded",
}

session = requests.Session()
session.headers["User-Agent"] = "GamePulse-Capstone/1.0 (student project)"


# --------------------------------------------------------------------------
# HTTP + caching helpers
# --------------------------------------------------------------------------
def get_json(url, params=None, method="get", data=None, headers=None, retries=3):
    """Request JSON with simple retry/backoff. Returns None on failure."""
    for attempt in range(retries):
        try:
            r = session.request(method, url, params=params, data=data,
                                headers=headers, timeout=30)
            if r.status_code == 429:  # rate limited
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return r.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"   ! request failed ({exc.__class__.__name__}), retry {attempt + 1}/{retries}")
            time.sleep(2 * (attempt + 1))
    return None


def cached(name, fn, *args):
    """Run fn(*args) once and save the result to data/raw/<name>.json."""
    path = RAW_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    result = fn(*args)
    if result is not None:  # None = network failure, so don't cache it
        path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


# --------------------------------------------------------------------------
# 1. RAWG - candidate 2025 games
# --------------------------------------------------------------------------
def fetch_rawg_candidates():
    games = []
    for page in range(1, RAWG_PAGES + 1):
        data = get_json("https://api.rawg.io/api/games", params={
            "key": RAWG_KEY,
            "dates": f"{YEAR}-01-01,{YEAR}-12-31",
            "platforms": 4,          # 4 = PC (we need Steam reviews)
            "ordering": "-added",    # most-added-to-libraries = popular
            "page_size": 40,
            "page": page,
        })
        if data is None:
            return None if not games else games
        games.extend(data.get("results", []))
        if not data.get("next"):
            break
    return games


def fetch_steam_appid(rawg_id):
    """RAWG lists store links per game; pull the Steam app id out of the URL."""
    data = get_json(f"https://api.rawg.io/api/games/{rawg_id}/stores",
                    params={"key": RAWG_KEY})
    if data is None:
        return None
    for store in data.get("results", []):
        m = re.search(r"store\.steampowered\.com/app/(\d+)", store.get("url") or "")
        if m:
            return {"appid": int(m.group(1))}
    return {"appid": None}


# --------------------------------------------------------------------------
# 2. Steam - details, review summary, reviews
# --------------------------------------------------------------------------
def fetch_steam_details(appid):
    data = get_json("https://store.steampowered.com/api/appdetails",
                    params={"appids": appid, "cc": "us", "l": "english"})
    if data is None:
        return None
    entry = data.get(str(appid), {})
    if not entry.get("success"):
        return {}
    d = entry["data"]
    if d.get("type") != "game":
        return {}
    price = d.get("price_overview") or {}
    return {
        "steam_appid": appid,
        "game_name": d.get("name"),
        "is_free": bool(d.get("is_free")),
        "price_usd": (price.get("final", 0) / 100) if price else 0.0,
        "release_date_raw": (d.get("release_date") or {}).get("date"),
        "coming_soon": (d.get("release_date") or {}).get("coming_soon", False),
        "genres": "; ".join(g["description"] for g in d.get("genres", [])),
        "developers": "; ".join(d.get("developers", [])),
        "short_description": d.get("short_description"),
    }


def fetch_review_summary(appid):
    data = get_json(f"https://store.steampowered.com/appreviews/{appid}", params={
        "json": 1, "language": "all", "num_per_page": 0, "purchase_type": "all",
    })
    if data is None:
        return None
    s = data.get("query_summary", {})
    return {
        "total_reviews": s.get("total_reviews", 0),
        "total_positive": s.get("total_positive", 0),
        "total_negative": s.get("total_negative", 0),
        "review_score_desc": s.get("review_score_desc"),
    }


def fetch_steam_reviews(appid):
    reviews, cursor = [], "*"
    while len(reviews) < REVIEWS_TO_FETCH:
        data = get_json(f"https://store.steampowered.com/appreviews/{appid}", params={
            "json": 1,
            "filter": "recent",
            "language": "english",
            "review_type": "all",
            "purchase_type": "all",
            "num_per_page": 100,
            "cursor": cursor,
        })
        if data is None:
            return None if not reviews else reviews
        if data.get("success") != 1:
            break
        batch = data.get("reviews", [])
        if not batch:
            break
        reviews.extend(batch)
        new_cursor = data.get("cursor")
        if not new_cursor or new_cursor == cursor:
            break
        cursor = new_cursor
    return reviews[:REVIEWS_TO_FETCH]


def flatten_review(r, appid):
    a = r.get("author", {}) or {}
    return {
        "data_source": "Steam API",
        "steam_appid": appid,
        "recommendation_id": str(r.get("recommendationid")),
        "language": r.get("language"),
        "review_text": r.get("review"),
        "created_ts": r.get("timestamp_created"),
        "voted_up": r.get("voted_up"),
        "votes_up": r.get("votes_up"),
        "votes_funny": r.get("votes_funny"),
        "steam_purchase": r.get("steam_purchase"),
        "received_for_free": r.get("received_for_free"),
        "early_access": r.get("written_during_early_access"),
        "playtime_at_review_min": a.get("playtime_at_review"),
        "playtime_forever_min": a.get("playtime_forever"),
        "author_num_reviews": a.get("num_reviews"),
        "author_num_games_owned": a.get("num_games_owned"),
    }


def parse_source_bool(value):
    """Parse common CSV boolean values without guessing unknown labels."""
    if pd.isna(value):
        return pd.NA
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return pd.NA


def load_supplemental_steam_data():
    """Load and normalize the supplied Steam reviews and game catalog."""
    required = {
        "appid", "recommendation_id", "review", "voted_up", "votes_up",
        "votes_funny", "timestamp_created", "steam_purchase",
        "received_for_free", "early_access", "playtime_forever",
        "playtime_at_review",
    }
    source = pd.read_csv(
        DATA_DIR / "steam 2025.csv",
        usecols=required | {"game_name"},
        low_memory=False,
    )

    voted_up = source["voted_up"].map(parse_source_bool)
    unknown_votes = int((source["voted_up"].notna() & voted_up.isna()).sum())
    if unknown_votes:
        print(f"      ! {unknown_votes} supplemental Steam reviews have unrecognized "
              "voted_up values; sentiment will be left unlabeled.")

    reviews = pd.DataFrame({
        "data_source": "steam 2025.csv",
        "steam_appid": pd.to_numeric(source["appid"], errors="raise").astype("Int64"),
        "recommendation_id": source["recommendation_id"].astype("string"),
        "language": pd.NA,
        "review_text": source["review"],
        "created_ts": pd.to_numeric(source["timestamp_created"], errors="raise"),
        "voted_up": voted_up,
        "votes_up": pd.to_numeric(source["votes_up"], errors="coerce"),
        "votes_funny": pd.to_numeric(source["votes_funny"], errors="coerce"),
        "steam_purchase": source["steam_purchase"].map(parse_source_bool),
        "received_for_free": source["received_for_free"].map(parse_source_bool),
        "early_access": source["early_access"].map(parse_source_bool),
        "playtime_at_review_min": pd.to_numeric(source["playtime_at_review"], errors="coerce"),
        "playtime_forever_min": pd.to_numeric(source["playtime_forever"], errors="coerce"),
        "author_num_reviews": pd.NA,
        "author_num_games_owned": pd.NA,
    })
    return reviews, source[["appid", "game_name"]]


def supplemental_game_rows(selected, steam_catalog):
    """Combine selected Steam games with the supplied Steam and Xbox catalogs."""
    games = selected.copy()
    games["platform"] = "Steam"
    games["data_source"] = "RAWG + Steam API"
    games["xbox_store_id"] = pd.NA
    games["xbox_rank"] = pd.NA
    games["xbox_average_rating"] = pd.NA
    games["xbox_rating_count"] = pd.NA

    steam = steam_catalog.copy()
    steam = steam.dropna(subset=["appid", "game_name"]).drop_duplicates("appid")
    selected_ids = set(pd.to_numeric(games["steam_appid"], errors="raise").astype(int))
    steam["steam_appid"] = pd.to_numeric(steam["appid"], errors="raise").astype("Int64")
    steam = steam[~steam["steam_appid"].isin(selected_ids)].copy()
    steam_rows = pd.DataFrame({column: pd.NA for column in games.columns}, index=steam.index)
    steam_rows["steam_appid"] = steam["steam_appid"]
    steam_rows["game_name"] = steam["game_name"]
    steam_rows["platform"] = "Steam"
    steam_rows["data_source"] = "steam 2025.csv"

    xbox = pd.read_csv(DATA_DIR / "xbox-games-2025.csv")
    xbox_required = {
        "rank", "title", "store_id", "release_date", "average_rating", "rating_count",
    }
    missing = xbox_required - set(xbox.columns)
    if missing:
        raise ValueError(f"xbox-games-2025.csv is missing required columns: {sorted(missing)}")
    xbox["release_date"] = pd.to_datetime(xbox["release_date"], format="mixed", errors="raise")
    if not xbox["release_date"].dt.year.eq(YEAR).all():
        raise ValueError(f"xbox-games-2025.csv contains a release date outside {YEAR}.")

    xbox_rows = pd.DataFrame({column: pd.NA for column in games.columns}, index=xbox.index)
    xbox_rows["game_name"] = xbox["title"]
    xbox_rows["release_date"] = xbox["release_date"].dt.strftime("%Y-%m-%d")
    xbox_rows["platform"] = "Xbox"
    xbox_rows["data_source"] = "xbox-games-2025.csv"
    xbox_rows["xbox_store_id"] = xbox["store_id"]
    xbox_rows["xbox_rank"] = pd.to_numeric(xbox["rank"], errors="raise")
    xbox_rows["xbox_average_rating"] = pd.to_numeric(xbox["average_rating"], errors="raise")
    xbox_rows["xbox_rating_count"] = pd.to_numeric(xbox["rating_count"], errors="raise")

    return pd.concat([games, steam_rows, xbox_rows], ignore_index=True, sort=False)


# --------------------------------------------------------------------------
# 3. IGDB (optional enrichment) - needs Twitch Client ID + Client Secret
# --------------------------------------------------------------------------
def igdb_token():
    data = get_json("https://id.twitch.tv/oauth2/token", method="post", params={
        "client_id": IGDB_CLIENT_ID,
        "client_secret": IGDB_CLIENT_SECRET,
        "grant_type": "client_credentials",
    })
    return (data or {}).get("access_token")


def igdb_lookup(name, token):
    safe = name.replace("\\", "\\\\").replace('"', '\\"')
    start = int(datetime(YEAR, 1, 1, tzinfo=timezone.utc).timestamp())
    end = int(datetime(YEAR + 1, 1, 1, tzinfo=timezone.utc).timestamp())
    body = (f'fields name,total_rating,total_rating_count,genres.name; '
            f'where name = "{safe}" & first_release_date >= {start} '
            f'& first_release_date < {end}; limit 1;')
    data = get_json("https://api.igdb.com/v4/games", method="post", data=body,
                    headers={"Client-ID": IGDB_CLIENT_ID,
                             "Authorization": f"Bearer {token}"})
    if data is None:
        return None
    if not data:
        return {}
    g = data[0]
    return {
        "igdb_rating": round(g["total_rating"], 1) if g.get("total_rating") else None,
        "igdb_rating_count": g.get("total_rating_count"),
        "igdb_genres": "; ".join(x["name"] for x in g.get("genres", [])),
    }


# --------------------------------------------------------------------------
# CLEANING
# --------------------------------------------------------------------------
BBCODE = re.compile(r"\[/?(?:[a-zA-Z][a-zA-Z0-9]*|\*)(?:=[^\]]*)?\]")  # [h1] [b] [url=..] [*]
URL = re.compile(r"https?://\S+|www\.\S+")
ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u2060\ufeff]")
REPEATED_CHARS = re.compile(r"(.)\1{3,}")  # "sooooo" -> "sooo"


def clean_text(text):
    """Strip Steam markup, links, odd unicode, and extra whitespace."""
    t = unicodedata.normalize("NFKC", str(text))
    t = html.unescape(t)
    t = BBCODE.sub(" ", t)
    t = URL.sub(" ", t)
    t = ZERO_WIDTH.sub("", t)
    t = REPEATED_CHARS.sub(r"\1\1\1", t)
    return re.sub(r"\s+", " ", t).strip()


def words_of(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def alpha_ratio(text):
    chars = text.replace(" ", "")
    return sum(c.isalpha() for c in chars) / len(chars) if chars else 0.0


def sentiment_rating(score):
    """Map a 0..100 sentiment score into one of five 20-point bands."""
    return min(int(score // 20) + 1, 5)


def add_sentiment_ratings(reviews):
    """Add text-derived VADER scores and five-band ratings to review rows."""
    analyzer = SentimentIntensityAnalyzer()
    compound = reviews["review_text"].fillna("").map(
        lambda text: analyzer.polarity_scores(str(text))["compound"]
    )
    score = ((compound + 1) * 50).clip(0, 100)

    rated = reviews.copy()
    rounded_score = score.round(1)
    rated["sentiment_score_100"] = rounded_score
    rated["sentiment_rating"] = rounded_score.map(sentiment_rating).astype("int8")
    rated["sentiment_category"] = rated["sentiment_rating"].map({
        1: "Very Poor",
        2: "Poor",
        3: "Mid",
        4: "Good",
        5: "Very Good",
    })
    return rated


def clean_reviews(raw):
    """Returns (clean_df, log) where log is a list of (step, rows_removed)."""
    df = raw.copy()
    log = [("raw reviews pulled", len(df))]

    def drop(label, bad):
        nonlocal df
        log.append((label, int(bad.sum())))
        df = df[~bad].copy()

    # normalise the text first so every later check sees the cleaned version
    df["review_text"] = df["review_text"].fillna("").map(clean_text)

    drop("empty after removing markup/links", df["review_text"] == "")
    language = df["language"].fillna("").str.lower()
    drop("known non-English", language.ne("") & language.ne("english"))
    drop("duplicate review id", df.duplicated("recommendation_id"))
    drop("symbol/ASCII-art spam (mostly non-letters)",
         df["review_text"].map(alpha_ratio) < 0.5)

    df["word_count"] = df["review_text"].map(lambda t: len(words_of(t)))
    has_term = df["review_text"].map(lambda t: bool(GAMING_TERMS & set(words_of(t))))
    drop(f"low information (<{MIN_WORDS} words, no gaming term)",
         (df["word_count"] < MIN_WORDS) & ~has_term)

    def too_repetitive(t):
        w = words_of(t)
        return len(w) >= 8 and len(set(w)) / len(w) < 0.3
    drop("repetitive filler text", df["review_text"].map(too_repetitive))

    norm = df["review_text"].str.lower().str.replace(r"[^a-z0-9 ]", "", regex=True)
    drop("duplicate / copy-paste review text", norm.duplicated())

    # ---- derived, analysis-friendly columns ----
    df = add_sentiment_ratings(df)
    df["sentiment_label"] = df["voted_up"].map(
        {True: "positive", False: "negative"}
    ).fillna("unlabeled")
    df["review_date"] = pd.to_datetime(df["created_ts"], unit="s", utc=True,
                                       errors="coerce").dt.strftime("%Y-%m-%d")
    df["playtime_at_review_hrs"] = (pd.to_numeric(df["playtime_at_review_min"],
                                                  errors="coerce") / 60).round(1)
    df["playtime_total_hrs"] = (pd.to_numeric(df["playtime_forever_min"],
                                              errors="coerce") / 60).round(1)
    df["short_playtime_flag"] = df["playtime_at_review_hrs"] < 1  # useful for review-bomb checks
    log.append(("clean reviews kept", len(df)))
    return df, log


def clean_games(games):
    g = games.copy()
    g["game_name"] = g["game_name"].fillna("").str.strip()
    g = g[g["game_name"] != ""].drop_duplicates("steam_appid")
    g["release_date"] = pd.to_datetime(g["release_date_raw"], errors="coerce", format="mixed")
    g = g[g["release_date"].dt.year == YEAR]          # 2025 releases only
    g["release_date"] = g["release_date"].dt.strftime("%Y-%m-%d")
    g["game_type"] = g["is_free"].map({True: "Free-to-Play", False: "Paid"})
    g.loc[g["is_free"], "price_usd"] = 0.0
    return g.drop(columns=["release_date_raw", "coming_soon"], errors="ignore")


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
def main():
    if not RAWG_KEY:
        sys.exit("Missing RAWG_API_KEY. Copy .env.example to .env and add your key.")

    # ---- 1. candidate pool -------------------------------------------------
    print(f"[1/5] Finding popular PC games released in {YEAR} (RAWG)...")
    candidates = cached("rawg_candidates", fetch_rawg_candidates)
    if not candidates:
        sys.exit("RAWG returned nothing - check your API key and internet connection.")
    print(f"      {len(candidates)} candidates")

    # ---- 2. Steam details for each candidate ------------------------------
    print("[2/5] Matching to Steam and checking release year / free vs paid...")
    pool = []
    for i, c in enumerate(candidates, 1):
        stores = cached(f"rawg_stores_{c['id']}", fetch_steam_appid, c["id"])
        appid = (stores or {}).get("appid")
        if not appid:
            continue
        details = cached(f"steam_details_{appid}", fetch_steam_details, appid)
        if not details:
            continue
        summary = cached(f"steam_summary_{appid}", fetch_review_summary, appid)
        if not summary:
            continue
        details.update(summary)
        details["rawg_id"] = c["id"]
        details["rawg_rating"] = c.get("rating")
        details["rawg_ratings_count"] = c.get("ratings_count")
        details["metacritic"] = c.get("metacritic")
        pool.append(details)
        if i % 10 == 0:
            print(f"      checked {i}/{len(candidates)}")

    games = clean_games(pd.DataFrame(pool))
    if games.empty:
        sys.exit("No usable 2025 Steam games found.")

    # ---- 3. pick top 10 free + top 10 paid by review volume ----------------
    free = games[games["is_free"]].nlargest(FREE_TARGET, "total_reviews")
    paid = games[~games["is_free"]].nlargest(PAID_TARGET, "total_reviews")
    if len(free) < FREE_TARGET or len(paid) < PAID_TARGET:
        print(f"      ! only found {len(free)} free / {len(paid)} paid games - "
              f"raise RAWG_PAGES for a bigger pool.")
    selected = pd.concat([free, paid]).reset_index(drop=True)
    print(f"[3/5] Selected {len(free)} free + {len(paid)} paid games")

    # ---- 4. optional IGDB enrichment --------------------------------------
    if IGDB_CLIENT_ID and IGDB_CLIENT_SECRET:
        print("[4/5] Adding IGDB data...")
        token = igdb_token()
        if token:
            extra = []
            for name in selected["game_name"]:
                key = re.sub(r"\W+", "_", name.lower())[:60]
                extra.append(cached(f"igdb_{key}", igdb_lookup, name, token) or {})
            selected = pd.concat([selected, pd.DataFrame(extra)], axis=1)
        else:
            print("      ! IGDB login failed (needs Twitch Client ID + Client Secret) - skipping")
    else:
        print("[4/5] IGDB skipped (no IGDB_CLIENT_ID / IGDB_CLIENT_SECRET in .env)")

    supplemental_reviews, steam_catalog = load_supplemental_steam_data()
    games_output = supplemental_game_rows(selected, steam_catalog)

    # ---- 5. reviews + cleaning --------------------------------------------
    print("[5/5] Pulling Steam reviews and cleaning...")
    rows = []
    for _, g in selected.iterrows():
        appid = int(g["steam_appid"])
        raw = cached(f"steam_reviews_{appid}", fetch_steam_reviews, appid) or []
        print(f"      {g['game_name']}: {len(raw)} raw reviews")
        rows.extend(flatten_review(r, appid) for r in raw)

    print(f"      steam 2025.csv: {len(supplemental_reviews)} supplemental reviews")
    rows.extend(supplemental_reviews.to_dict("records"))

    if not rows:
        sys.exit("No reviews were retrieved.")
    reviews, log = clean_reviews(pd.DataFrame(rows))

    game_cols = ["steam_appid", "game_name", "game_type", "release_date", "price_usd", "genres"]
    steam_game_details = games_output[games_output["platform"] == "Steam"]
    out = reviews.merge(steam_game_details[game_cols], on="steam_appid", how="left")
    review_cols = [
        "steam_appid", "game_name", "game_type", "release_date", "genres", "price_usd",
        "recommendation_id", "review_date", "review_text", "word_count",
        "sentiment_label", "sentiment_score_100", "sentiment_rating",
        "sentiment_category", "votes_up", "votes_funny",
        "playtime_at_review_hrs", "playtime_total_hrs", "short_playtime_flag",
        "steam_purchase", "received_for_free", "early_access", "data_source",
    ]
    out = out[review_cols]

    # utf-8-sig so Excel opens the file with correct characters
    out.to_csv(OUT_DIR / "gamepulse_reviews_clean.csv", index=False, encoding="utf-8-sig")
    games_output.to_csv(OUT_DIR / "gamepulse_games_clean.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(log, columns=["step", "rows"]).to_csv(OUT_DIR / "cleaning_log.csv", index=False)

    print("\nCleaning summary")
    for step, n in log:
        print(f"  {step:<55} {n:>6}")
    print(f"\nSaved {len(out)} reviews from {out['game_name'].nunique()} games to "
          f"{OUT_DIR / 'gamepulse_reviews_clean.csv'}")


if __name__ == "__main__":
    main()
