"""
GamePulse 2025 - data acquisition + cleaning pipeline
=====================================================

What it does
  1. IGDB   -> bulk-downloads 2025 releases (ratings, hype/follows, genres, themes,
               modes, platforms, companies, keywords, Steam link)   [Twitch keys]
  2. RAWG   -> bulk-downloads popular 2025 releases on every platform, plus
               full details (developers, publishers, ESRB, tags, community ratings)
  3. Steam  -> candidate pool from RAWG + IGDB, then store details, review
               summary, and two review samples per game (recent + most helpful)
  4. Cleans -> removes junk reviews, scores sentiment with VADER
  5. Merges -> enriches every game with IGDB + RAWG data and adds games that only
               exist in IGDB / RAWG

New acquired data (saved into ./Data CSVs so it can be reused / inspected)
  igdb-games-2025.csv            <- IGDB 2025 releases
  rawg-games-2025.csv            <- RAWG 2025 releases (top by popularity)

Outputs (in ./output)
  gamepulse_reviews_clean.csv    <- one row per review, rich game info attached
  gamepulse_games_clean.csv      <- all games (Steam, Xbox, IGDB, RAWG) enriched; every
                                    game gets a developer and one 0/1 column per genre
  gamepulse_game_summary.csv     <- one row per reviewed game: sentiment metrics
  cleaning_log.csv               <- how many rows each cleaning step removed

Supplemental data in ./Data CSVs is included when present:
  steam 2025.csv                 <- additional Steam reviews and games
  xbox-games-2025.csv            <- Xbox game catalog and ratings

Review sentiment is scored clause by clause with VADER (contrast words such as
"but" start a new clause). Positive and negative clauses offset each other, so
mixed reviews land mid-scale; the 0-100 score is grouped into five 20-point
rating categories and mixed reviews are flagged in sentiment_mixed.
sentiment_label remains the reviewer's Steam vote when available.

Run:  python gamepulse_pipeline.py
Raw API responses are cached in ./data/raw so re-runs are fast.
Delete that folder if you want a completely fresh pull.
"""

import hashlib
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
RAWG_PAGES = 4              # 40 games per page -> Steam candidate pool
RAWG_BULK_PAGES = 25        # 40 games per page -> rawg-games-2025.csv (1000 games)
RAWG_DETAIL_LIMIT = 200     # games that also get a full RAWG detail lookup
IGDB_EXTRA_CANDIDATES = 120  # extra Steam candidates taken from IGDB (by follows)
REVIEWS_RECENT = 150        # newest Steam reviews per game
REVIEWS_HELPFUL = 150       # most helpful Steam reviews (last 365 days) per game
MIN_WORDS = 4               # reviews shorter than this are "low information"
REQUEST_DELAY = 1.0         # seconds between live API calls (be polite)
IGDB_DELAY = 0.3            # IGDB allows ~4 requests/second

RAWG_KEY = os.getenv("RAWG_API_KEY")
IGDB_CLIENT_ID = os.getenv("IGDB_CLIENT_ID")
IGDB_CLIENT_SECRET = os.getenv("IGDB_CLIENT_SECRET")

RAW_DIR = BASE_DIR / "data" / "raw"
OUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "Data CSVs"
RAW_DIR.mkdir(parents=True, exist_ok=True)
MAX_CACHE_NAME = 70
OUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Short reviews are kept if they contain one of these (they say something specific)
GAMING_TERMS = {
    "fps", "lag", "laggy", "bug", "bugs", "buggy", "crash", "crashes", "crashing",
    "grind", "grindy", "p2w", "pay2win", "dlc", "gacha", "toxic",
    "cheaters", "hackers", "aimbot", "stutter", "stuttering", "optimization",
    "unoptimized", "microtransactions", "servers", "matchmaking", "netcode",
    "overpriced", "goty", "refund", "refunded",
}

session = requests.Session()
session.headers["User-Agent"] = "GamePulse-Capstone/2.0 (student project)"


# --------------------------------------------------------------------------
# HTTP + caching helpers
# --------------------------------------------------------------------------
def get_json(url, params=None, method="get", data=None, headers=None,
             retries=3, delay=None):
    """Request JSON with simple retry/backoff. Returns None on failure."""
    delay = REQUEST_DELAY if delay is None else delay
    for attempt in range(retries):
        try:
            r = session.request(method, url, params=params, data=data,
                                headers=headers, timeout=30)
            if r.status_code == 429:  # rate limited
                time.sleep(5 * (attempt + 1))
                continue
            if 400 <= r.status_code < 500:  # retrying will not help
                print(f"   ! HTTP {r.status_code} from {url}: {r.text[:200]}")
                return None
            r.raise_for_status()
            time.sleep(delay)
            return r.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"   ! request failed ({exc.__class__.__name__}), retry {attempt + 1}/{retries}")
            time.sleep(2 * (attempt + 1))
    return None


def cached(name, fn, *args):
    """Run fn(*args) once and save the result to data/raw/<name>.json."""
    if len(name) > MAX_CACHE_NAME:  # keep file names short; hash keeps them unique
        digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:10]
        name = f"{name[:MAX_CACHE_NAME - 11]}_{digest}"
    path = RAW_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    result = fn(*args)
    if result is not None:  # None = network failure, so don't cache it
        path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


def join_names(items, key="name", limit=None):
    """['a','b'] or [{'name': 'a'}, ...] -> 'a; b'."""
    out = []
    for item in items or []:
        value = item.get(key) if isinstance(item, dict) else item
        if value:
            out.append(str(value))
    return "; ".join(out[:limit] if limit else out)


def name_key(name):
    """Normalised game title used to match the same game across sources."""
    t = unicodedata.normalize("NFKD", str(name or "")).lower()
    t = t.replace("&", "and")
    return re.sub(r"[^a-z0-9]", "", t)


def ts_to_date(ts):
    if ts is None or pd.isna(ts):
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")


# --------------------------------------------------------------------------
# 1. IGDB - bulk 2025 releases (needs Twitch Client ID + Client Secret)
# --------------------------------------------------------------------------
IGDB_FIELDS = (
    "name,slug,url,summary,first_release_date,game_type.type,"
    "total_rating,total_rating_count,rating,rating_count,"
    "aggregated_rating,aggregated_rating_count,hypes,follows,"
    "genres.name,themes.name,game_modes.name,player_perspectives.name,"
    "platforms.name,keywords.name,franchises.name,"
    "involved_companies.company.name,involved_companies.developer,"
    "involved_companies.publisher,"
    "external_games.external_game_source,external_games.uid,external_games.url"
)


def igdb_token():
    data = get_json("https://id.twitch.tv/oauth2/token", method="post", params={
        "client_id": IGDB_CLIENT_ID,
        "client_secret": IGDB_CLIENT_SECRET,
        "grant_type": "client_credentials",
    })
    return (data or {}).get("access_token")


def fetch_igdb_page(offset, token):
    start = int(datetime(YEAR, 1, 1, tzinfo=timezone.utc).timestamp())
    end = int(datetime(YEAR + 1, 1, 1, tzinfo=timezone.utc).timestamp())
    body = (f"fields {IGDB_FIELDS}; "
            f"where first_release_date >= {start} & first_release_date < {end} "
            f"& (total_rating_count > 0 | follows > 0 | hypes > 0); "
            f"sort id asc; limit 500; offset {offset};")
    return get_json("https://api.igdb.com/v4/games", method="post", data=body,
                    headers={"Client-ID": IGDB_CLIENT_ID,
                             "Authorization": f"Bearer {token}"},
                    delay=IGDB_DELAY)


def flatten_igdb(g):
    companies = g.get("involved_companies") or []
    steam_appid = None
    for e in g.get("external_games") or []:
        m = re.search(r"store\.steampowered\.com/app/(\d+)", e.get("url") or "")
        if m:
            steam_appid = int(m.group(1))
            break
        if e.get("external_game_source") == 1 and str(e.get("uid", "")).isdigit():
            steam_appid = int(e["uid"])
            break
    rating = g.get("total_rating")
    critic = g.get("aggregated_rating")
    user = g.get("rating")
    return {
        "igdb_id": g.get("id"),
        "steam_appid": steam_appid,
        "game_name": g.get("name"),
        "igdb_slug": g.get("slug"),
        "igdb_url": g.get("url"),
        "release_date": ts_to_date(g.get("first_release_date")),
        "igdb_game_type": (g.get("game_type") or {}).get("type"),
        "igdb_rating": round(rating, 1) if rating else None,
        "igdb_rating_count": g.get("total_rating_count"),
        "igdb_user_rating": round(user, 1) if user else None,
        "igdb_user_rating_count": g.get("rating_count"),
        "igdb_critic_rating": round(critic, 1) if critic else None,
        "igdb_critic_count": g.get("aggregated_rating_count"),
        "igdb_hypes": g.get("hypes"),
        "igdb_follows": g.get("follows"),
        "igdb_genres": join_names(g.get("genres")),
        "igdb_themes": join_names(g.get("themes")),
        "igdb_game_modes": join_names(g.get("game_modes")),
        "igdb_perspectives": join_names(g.get("player_perspectives")),
        "igdb_platforms": join_names(g.get("platforms")),
        "igdb_developers": "; ".join(
            c["company"]["name"] for c in companies
            if c.get("developer") and (c.get("company") or {}).get("name")),
        "igdb_publishers": "; ".join(
            c["company"]["name"] for c in companies
            if c.get("publisher") and (c.get("company") or {}).get("name")),
        "igdb_keywords": join_names(g.get("keywords"), limit=15),
        "igdb_franchises": join_names(g.get("franchises")),
        "igdb_summary": g.get("summary"),
    }


def acquire_igdb():
    """Download all popular/rated 2025 IGDB games to Data CSVs/igdb-games-2025.csv."""
    if not (IGDB_CLIENT_ID and IGDB_CLIENT_SECRET):
        print("      IGDB skipped (no IGDB_CLIENT_ID / IGDB_CLIENT_SECRET in .env)")
        return pd.DataFrame()
    token = igdb_token()
    if not token:
        print("      ! IGDB login failed (needs Twitch Client ID + Client Secret) - skipping")
        return pd.DataFrame()
    rows, offset = [], 0
    while True:
        page = cached(f"igdb_games_{YEAR}_{offset}", fetch_igdb_page, offset, token)
        if page is None:
            print(f"      ! IGDB page at offset {offset} failed - using what we have")
            break
        rows.extend(flatten_igdb(g) for g in page)
        if len(page) < 500:
            break
        offset += 500
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values("igdb_follows", ascending=False, na_position="last")
    df = df.drop_duplicates("igdb_id").reset_index(drop=True)
    df.to_csv(DATA_DIR / "igdb-games-2025.csv", index=False, encoding="utf-8-sig")
    print(f"      {len(df)} IGDB games -> Data CSVs/igdb-games-2025.csv")
    return df


# --------------------------------------------------------------------------
# 2. RAWG - bulk 2025 releases + details
# --------------------------------------------------------------------------
def fetch_rawg_candidates():
    """PC-only pool used to find Steam games."""
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


def fetch_rawg_page(page):
    return get_json("https://api.rawg.io/api/games", params={
        "key": RAWG_KEY,
        "dates": f"{YEAR}-01-01,{YEAR}-12-31",
        "ordering": "-added",
        "page_size": 40,
        "page": page,
    })


def fetch_rawg_detail(rawg_id):
    return get_json(f"https://api.rawg.io/api/games/{rawg_id}", params={"key": RAWG_KEY})


def fetch_rawg_development_team(rawg_id):
    """Return RAWG's individual development-team credits for a game."""
    return get_json(
        f"https://api.rawg.io/api/games/{rawg_id}/development-team",
        params={"key": RAWG_KEY},
    )


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


def flatten_rawg(g, detail=None):
    ratings = {r.get("title"): r.get("percent") for r in g.get("ratings") or []}
    status = g.get("added_by_status") or {}
    detail = detail or {}
    description = detail.get("description_raw") or ""
    return {
        "rawg_id": g.get("id"),
        "rawg_slug": g.get("slug"),
        "game_name": g.get("name"),
        "release_date": g.get("released"),
        "rawg_rating": g.get("rating"),
        "rawg_ratings_count": g.get("ratings_count"),
        "rawg_reviews_count": g.get("reviews_count"),
        "metacritic": g.get("metacritic"),
        "rawg_playtime_hrs": g.get("playtime"),
        "rawg_added": g.get("added"),
        "rawg_pct_exceptional": ratings.get("exceptional"),
        "rawg_pct_recommended": ratings.get("recommended"),
        "rawg_pct_meh": ratings.get("meh"),
        "rawg_pct_skip": ratings.get("skip"),
        "rawg_owned": status.get("owned"),
        "rawg_playing": status.get("playing"),
        "rawg_beaten": status.get("beaten"),
        "rawg_dropped": status.get("dropped"),
        "rawg_esrb": (g.get("esrb_rating") or {}).get("name"),
        "rawg_platforms": join_names([p.get("platform") for p in g.get("platforms") or []]),
        "rawg_genres": join_names(g.get("genres")),
        "rawg_tags": join_names(g.get("tags"), limit=15),
        "rawg_stores": join_names([s.get("store") for s in g.get("stores") or []]),
        "rawg_developers": join_names(detail.get("developers")),
        "rawg_publishers": join_names(detail.get("publishers")),
        "rawg_website": detail.get("website"),
        "rawg_reddit_url": detail.get("reddit_url"),
        "rawg_achievements": detail.get("achievements_count"),
        "rawg_description": description[:1000] if description else None,
    }


def acquire_rawg():
    """Download popular 2025 RAWG games to Data CSVs/rawg-games-2025.csv."""
    listing = []
    for page in range(1, RAWG_BULK_PAGES + 1):
        data = cached(f"rawg_bulk_page_{page}", fetch_rawg_page, page)
        if data is None:
            print(f"      ! RAWG page {page} failed - using what we have")
            break
        listing.extend(data.get("results", []))
        if not data.get("next"):
            break
    rows = []
    for i, g in enumerate(listing):
        detail = None
        if i < RAWG_DETAIL_LIMIT:
            detail = cached(f"rawg_detail_{g['id']}", fetch_rawg_detail, g["id"])
        rows.append(flatten_rawg(g, detail))
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.drop_duplicates("rawg_id").reset_index(drop=True)
    df.to_csv(DATA_DIR / "rawg-games-2025.csv", index=False, encoding="utf-8-sig")
    print(f"      {len(df)} RAWG games -> Data CSVs/rawg-games-2025.csv")
    return df


# --------------------------------------------------------------------------
# 3. Steam - details, review summary, reviews
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
    plats = d.get("platforms") or {}
    languages = re.sub(r"<[^>]+>", "", d.get("supported_languages") or "")
    return {
        "steam_appid": appid,
        "game_name": d.get("name"),
        "is_free": bool(d.get("is_free")),
        "price_usd": (price.get("final", 0) / 100) if price else 0.0,
        "release_date_raw": (d.get("release_date") or {}).get("date"),
        "coming_soon": (d.get("release_date") or {}).get("coming_soon", False),
        "genres": join_names(d.get("genres"), key="description"),
        "developers": "; ".join(d.get("developers", [])),
        "publishers": "; ".join(d.get("publishers", [])),
        "short_description": d.get("short_description"),
        "steam_categories": join_names(d.get("categories"), key="description"),
        "steam_required_age": d.get("required_age"),
        "steam_metacritic": (d.get("metacritic") or {}).get("score"),
        "steam_recommendations": (d.get("recommendations") or {}).get("total"),
        "steam_achievements": (d.get("achievements") or {}).get("total"),
        "steam_dlc_count": len(d.get("dlc") or []),
        "steam_languages": languages,
        "steam_platforms": "; ".join(k.title() for k, v in plats.items() if v),
        "steam_website": d.get("website"),
        "steam_header_image": d.get("header_image"),
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


def fetch_steam_reviews(appid, review_filter, limit):
    reviews, cursor = [], "*"
    while len(reviews) < limit:
        params = {
            "json": 1,
            "filter": review_filter,
            "language": "english",
            "review_type": "all",
            "purchase_type": "all",
            "num_per_page": 100,
            "cursor": cursor,
        }
        if review_filter == "all":
            params["day_range"] = 365   # "all" = most helpful within the range
        data = get_json(f"https://store.steampowered.com/appreviews/{appid}", params=params)
        if data is None:
            return None if not reviews else reviews[:limit]
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
    return reviews[:limit]


def flatten_review(r, appid, pull):
    a = r.get("author", {}) or {}
    return {
        "data_source": "Steam API",
        "review_pull": pull,
        "steam_appid": appid,
        "recommendation_id": str(r.get("recommendationid")),
        "language": r.get("language"),
        "review_text": r.get("review"),
        "created_ts": r.get("timestamp_created"),
        "voted_up": r.get("voted_up"),
        "votes_up": r.get("votes_up"),
        "votes_funny": r.get("votes_funny"),
        "comment_count": r.get("comment_count"),
        "weighted_vote_score": pd.to_numeric(r.get("weighted_vote_score"), errors="coerce"),
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
    """Load supplied Steam reviews and catalog, or continue when the file is absent."""
    source_path = DATA_DIR / "steam 2025.csv"
    if not source_path.exists():
        print("      ! steam 2025.csv not found; continuing without supplemental Steam data.")
        return pd.DataFrame(), pd.DataFrame(columns=["appid", "game_name"])

    required = {
        "appid", "recommendation_id", "review", "voted_up", "votes_up",
        "votes_funny", "timestamp_created", "steam_purchase",
        "received_for_free", "early_access", "playtime_forever",
        "playtime_at_review",
    }
    source = pd.read_csv(
        source_path,
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
        "review_pull": "supplemental",
        "steam_appid": pd.to_numeric(source["appid"], errors="raise").astype("Int64"),
        "recommendation_id": source["recommendation_id"].astype("string"),
        "language": pd.NA,
        "review_text": source["review"],
        "created_ts": pd.to_numeric(source["timestamp_created"], errors="raise"),
        "voted_up": voted_up,
        "votes_up": pd.to_numeric(source["votes_up"], errors="coerce"),
        "votes_funny": pd.to_numeric(source["votes_funny"], errors="coerce"),
        "comment_count": pd.NA,
        "weighted_vote_score": pd.NA,
        "steam_purchase": source["steam_purchase"].map(parse_source_bool),
        "received_for_free": source["received_for_free"].map(parse_source_bool),
        "early_access": source["early_access"].map(parse_source_bool),
        "playtime_at_review_min": pd.to_numeric(source["playtime_at_review"], errors="coerce"),
        "playtime_forever_min": pd.to_numeric(source["playtime_forever"], errors="coerce"),
        "author_num_reviews": pd.NA,
        "author_num_games_owned": pd.NA,
    })
    return reviews, source[["appid", "game_name"]]


# --------------------------------------------------------------------------
# Games table: Steam + Xbox + IGDB + RAWG
# --------------------------------------------------------------------------
IGDB_COLS = [
    "igdb_id", "igdb_slug", "igdb_game_type", "igdb_rating", "igdb_rating_count",
    "igdb_user_rating", "igdb_user_rating_count", "igdb_critic_rating",
    "igdb_critic_count", "igdb_hypes", "igdb_follows", "igdb_genres", "igdb_themes",
    "igdb_game_modes", "igdb_perspectives", "igdb_platforms", "igdb_developers",
    "igdb_publishers", "igdb_keywords", "igdb_franchises", "igdb_summary",
]
RAWG_COLS = [
    "rawg_id", "rawg_slug", "rawg_rating", "rawg_ratings_count", "rawg_reviews_count",
    "metacritic", "rawg_playtime_hrs", "rawg_added", "rawg_pct_exceptional",
    "rawg_pct_recommended", "rawg_pct_meh", "rawg_pct_skip", "rawg_owned",
    "rawg_playing", "rawg_beaten", "rawg_dropped", "rawg_esrb", "rawg_platforms",
    "rawg_genres", "rawg_tags", "rawg_stores", "rawg_developers", "rawg_publishers",
    "rawg_website", "rawg_reddit_url", "rawg_achievements", "rawg_description",
]


def supplemental_game_rows(selected, steam_catalog):
    """Combine selected Steam games with the supplied Steam and Xbox catalogs."""
    games = selected.copy()
    games["platform"] = "Steam"
    games["data_source"] = "RAWG/IGDB + Steam API"
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


def attach(games, ref, id_col, cols):
    """Fill `cols` on games from ref, matching on id_col first, then title."""
    if ref.empty:
        return games
    out = games.copy()
    ref = ref[ref["name_key"] != ""]
    by_key = ref.drop_duplicates("name_key").set_index("name_key")
    by_id, ids = None, None
    if id_col in ref.columns and id_col in out.columns:
        r = ref.dropna(subset=[id_col]).copy()
        r[id_col] = pd.to_numeric(r[id_col]).astype("float64")
        by_id = r.drop_duplicates(id_col).set_index(id_col, drop=False)
        ids = pd.to_numeric(out[id_col], errors="coerce").astype("float64")
    for c in cols:
        filled = out["name_key"].map(by_key[c])
        if by_id is not None:
            filled = ids.map(by_id[c]).where(lambda s: s.notna(), filled)
        if c in out.columns:
            out[c] = out[c].where(out[c].notna(), filled)
        else:
            out[c] = filled
    return out


def merge_all_games(base, igdb, rawg):
    """Enrich the base games with IGDB + RAWG, then append games only they know."""
    base = base.copy()
    base["name_key"] = base["game_name"].map(name_key)
    for df in (igdb, rawg):
        if not df.empty:
            df["name_key"] = df["game_name"].map(name_key)

    games = attach(base, igdb, "steam_appid", IGDB_COLS)
    games = attach(games, rawg, "rawg_id", RAWG_COLS)

    # fill the generic columns from whichever source knows the answer
    def fill(target, *sources):
        for s in sources:
            if s in games.columns:
                if target not in games.columns:
                    games[target] = pd.NA
                empty = games[target].isna() | games[target].astype(str).str.strip().eq("")
                games[target] = games[target].where(~empty, games[s])

    fill("genres", "igdb_genres", "rawg_genres")
    fill("developers", "igdb_developers", "rawg_developers")
    fill("publishers", "igdb_publishers", "rawg_publishers")
    fill("short_description", "igdb_summary", "rawg_description")

    known_keys = set(games["name_key"])
    known_ids = set(pd.to_numeric(games["steam_appid"], errors="coerce").dropna().astype(int))

    extras = []
    if not igdb.empty:
        new = igdb[~igdb["name_key"].isin(known_keys)].copy()
        new_app = pd.to_numeric(new["steam_appid"], errors="coerce")
        new = new[~new_app.isin(known_ids)]
        rows = new[["game_name", "release_date", "steam_appid", "name_key"] + IGDB_COLS].copy()
        rows["genres"] = new["igdb_genres"]
        rows["developers"] = new["igdb_developers"]
        rows["publishers"] = new["igdb_publishers"]
        rows["short_description"] = new["igdb_summary"]
        rows["platform"] = new["igdb_platforms"]
        rows["data_source"] = "igdb-games-2025.csv"
        extras.append(rows)
        known_keys |= set(rows["name_key"])
    if not rawg.empty:
        new = rawg[~rawg["name_key"].isin(known_keys)].copy()
        rows = new[["game_name", "release_date", "name_key"] + RAWG_COLS].copy()
        rows["genres"] = new["rawg_genres"]
        rows["developers"] = new["rawg_developers"]
        rows["publishers"] = new["rawg_publishers"]
        rows["short_description"] = new["rawg_description"]
        rows["platform"] = new["rawg_platforms"]
        rows["data_source"] = "rawg-games-2025.csv"
        extras.append(rows)

    if extras:
        games = pd.concat([games] + [e for e in extras if not e.empty],
                          ignore_index=True, sort=False)
    if "total_reviews" in games.columns:
        total = pd.to_numeric(games["total_reviews"], errors="coerce")
        pos = pd.to_numeric(games["total_positive"], errors="coerce")
        games["steam_pct_positive"] = (pos / total * 100).round(1)
    games["steam_appid"] = pd.to_numeric(games["steam_appid"], errors="coerce").astype("Int64")
    return games.drop(columns=["name_key"])


# --------------------------------------------------------------------------
# Developer backfill: every game should end up with a developer name
# --------------------------------------------------------------------------
EDITION_WORDS = (
    r"(?:game of the year|goty|definitive|complete|deluxe|ultimate|gold|standard|"
    r"remastered|remake|enhanced|anniversary|director'?s cut|special|collector'?s)"
)
EDITION_SUFFIX = re.compile(rf"[\s:–—-]+(?:the\s+)?(?:{EDITION_WORDS}\s*)+(?:edition|version|cut|bundle)?\s*$", re.I)
TRAILING_BRACKET = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]\s*$")
TRADEMARKS = re.compile(r"[™®©]")


def title_variations(title):
    """Likely alternate spellings of a game title, most specific first."""
    base = unicodedata.normalize("NFKC", TRADEMARKS.sub("", str(title or ""))).strip()
    variants = [base]
    stripped = base
    for _ in range(3):
        new = EDITION_SUFFIX.sub("", TRAILING_BRACKET.sub("", stripped)).strip()
        if new == stripped:
            break
        stripped = new
        variants.append(stripped)
    for v in list(variants):
        variants.append(re.sub(r"^(?:the|a|an)\s+", "", v, flags=re.I))
        variants.append(re.sub(r"\s*[:–—]\s+.*$|\s+-\s+.*$", "", v))   # drop subtitle
        variants.append(v.replace("&", "and"))
    seen, out = set(), []
    for v in variants:
        key = name_key(v)
        if len(key) >= 3 and key not in seen:
            seen.add(key)
            out.append(v.strip())
    return out


def is_blank(value):
    return pd.isna(value) or str(value).strip().lower() in ("", "nan", "none", "[]")


def rawg_title_matches(title):
    """Yield RAWG search hits whose name matches any variation of the title."""
    variations = title_variations(title)
    wanted = {name_key(x) for x in variations}
    for variant in variations:
        results = cached(f"rawg_search_{name_key(variant)}", lambda v=variant: get_json(
            "https://api.rawg.io/api/games",
            params={"key": RAWG_KEY, "search": v, "search_precise": "true", "page_size": 10}))
        for hit in (results or {}).get("results", []):
            if name_key(hit.get("name")) in wanted:
                yield hit


def igdb_title_matches(title, token, fields, cache_prefix):
    """Yield IGDB search hits whose name matches any variation of the title."""
    variations = title_variations(title)
    wanted = {name_key(x) for x in variations}
    for variant in variations:
        safe = variant.replace("\\", " ").replace('"', " ")
        body = f'search "{safe}"; fields name,{fields}; limit 10;'
        hits = cached(f"{cache_prefix}_{name_key(variant)}", lambda b=body: get_json(
            "https://api.igdb.com/v4/games", method="post", data=b,
            headers={"Client-ID": IGDB_CLIENT_ID, "Authorization": f"Bearer {token}"}))
        for hit in hits or []:
            if name_key(hit.get("name")) in wanted:
                yield hit


def search_rawg_developers(title):
    """Search RAWG by every title variation; return developer names or ''."""
    for hit in rawg_title_matches(title):
        detail = cached(f"rawg_detail_{hit['id']}", fetch_rawg_detail, hit["id"])
        names = join_names((detail or {}).get("developers"))
        if names:
            return names
    return ""


def format_rawg_creator_credits(credits):
    """Format credited development-team members with their supplied roles."""
    if isinstance(credits, dict):
        credits = credits.get("results", [])
    by_name = {}
    for credit in credits or []:
        if isinstance(credit, str):
            name, positions = credit.strip(), []
        elif isinstance(credit, dict):
            name = str(credit.get("name") or "").strip()
            positions = (
                credit.get("positions")
                or credit.get("roles")
                or credit.get("position")
                or []
            )
            if isinstance(positions, (str, dict)):
                positions = [positions]
            positions = [
                str(position.get("name") or position.get("title") or "").strip()
                if isinstance(position, dict) else str(position).strip()
                for position in positions
            ]
            positions = [position for position in positions if position]
        else:
            continue
        if name:
            entry = by_name.setdefault(name_key(name), [name, []])
            entry[1].extend(role for role in positions if role not in entry[1])
    formatted = []
    for name, positions in by_name.values():
        roles = " / ".join(positions)
        formatted.append(f"{name} ({roles})" if roles else name)
    return "; ".join(formatted)


def search_rawg_creator_credits(title):
    """Find matching RAWG game credits when no developer studio is listed."""
    for hit in rawg_title_matches(title):
        credits = cached(
            f"rawg_development_team_{hit['id']}",
            fetch_rawg_development_team,
            hit["id"],
        )
        names = format_rawg_creator_credits(credits)
        if names:
            return names
    return ""


def igdb_search_developers(title, token):
    """Search IGDB by title variations; return developer company names or ''."""
    fields = "involved_companies.company.name,involved_companies.developer"
    for hit in igdb_title_matches(title, token, fields, "igdb_search"):
        devs = [ic["company"]["name"] for ic in hit.get("involved_companies") or []
                if ic.get("developer") and (ic.get("company") or {}).get("name")]
        if devs:
            return "; ".join(devs)
    return ""


def clean_developer_names(value):
    """Normalise separators and drop duplicate developer names ('A, B; a' -> 'A; B')."""
    if is_blank(value):
        return ""
    parts = re.split(r"\s*[;|]\s*|\s*,\s*(?!\s*(?:inc|llc|ltd|co)\b)", str(value), flags=re.I)
    seen, out = set(), []
    for p in parts:
        p = p.strip()
        if p and name_key(p) not in seen:
            seen.add(name_key(p))
            out.append(p)
    return "; ".join(out)


def fill_missing_developers(games):
    """Backfill blank developers: Steam -> RAWG -> IGDB, then RAWG team credits.

    Games still blank afterwards are written to output/games_missing_developer.csv.
    """
    games = games.copy()
    if "developers" not in games.columns:
        games["developers"] = pd.NA
    games["developers"] = games["developers"].map(clean_developer_names)
    missing = games.index[games["developers"].eq("")]
    print(f"      {len(missing)} games missing a developer - searching sources...")
    token = igdb_token() if IGDB_CLIENT_ID and IGDB_CLIENT_SECRET else None
    games["developer_source"] = games["developers"].map(lambda v: "catalog" if v else "")

    for i, idx in enumerate(missing, 1):
        row = games.loc[idx]
        found, source = "", ""
        appid = pd.to_numeric(row.get("steam_appid"), errors="coerce")
        rawg_id = pd.to_numeric(row.get("rawg_id"), errors="coerce")
        if pd.notna(appid):
            details = cached(f"steam_details_v2_{int(appid)}", fetch_steam_details, int(appid))
            found, source = clean_developer_names((details or {}).get("developers")), "steam"
        if not found and RAWG_KEY and pd.notna(rawg_id):
            details = cached(
                f"rawg_detail_{int(rawg_id)}",
                fetch_rawg_detail,
                int(rawg_id),
            )
            found = clean_developer_names(join_names((details or {}).get("developers")))
            if found:
                source = "rawg_detail"
        if not found and token:
            found, source = clean_developer_names(igdb_search_developers(row["game_name"], token)), "igdb_search"
        if not found and RAWG_KEY and pd.isna(rawg_id):
            found = clean_developer_names(search_rawg_developers(row["game_name"]))
            if found:
                source = "rawg_search"
        if not found and RAWG_KEY:
            if pd.notna(rawg_id):
                credits = cached(
                    f"rawg_development_team_{int(rawg_id)}",
                    fetch_rawg_development_team,
                    int(rawg_id),
                )
                found = clean_developer_names(format_rawg_creator_credits(credits))
            else:
                found = clean_developer_names(search_rawg_creator_credits(row["game_name"]))
            if found:
                source = "rawg_development_team"
        if found:
            games.at[idx, "developers"] = found
            games.at[idx, "developer_source"] = source
        if i % 100 == 0:
            print(f"      developer lookup {i}/{len(missing)}")

    still = games[games["developers"].eq("")]
    if not still.empty:
        cols = [c for c in ("steam_appid", "game_name", "platform", "data_source") if c in still.columns]
        still[cols].to_csv(OUT_DIR / "games_missing_developer.csv", index=False, encoding="utf-8-sig")
        print(f"      ! {len(still)} games still have no developer "
              f"(see output/games_missing_developer.csv)")
    return games


# --------------------------------------------------------------------------
# Genre backfill: one 0/1 column per genre, and a genre for every game
# --------------------------------------------------------------------------
# Every source names genres differently; map them onto one shared vocabulary.
# Steam's non-genre labels ("Free To Play", "Early Access", software categories) are ignored.
GENRE_ALIASES = {
    "action": "Action", "adventure": "Adventure", "indie": "Indie", "casual": "Casual",
    "arcade": "Arcade", "puzzle": "Puzzle", "racing": "Racing", "fighting": "Fighting",
    "shooter": "Shooter", "tactical": "Tactical", "music": "Music", "moba": "MOBA",
    "pinball": "Pinball", "family": "Family", "visual novel": "Visual Novel",
    "role-playing (rpg)": "RPG", "role-playing": "RPG", "rpg": "RPG",
    "strategy": "Strategy", "real time strategy (rts)": "Strategy",
    "turn-based strategy (tbs)": "Strategy",
    "simulation": "Simulation", "simulator": "Simulation",
    "platform": "Platformer", "platformer": "Platformer",
    "sport": "Sports", "sports": "Sports",
    "hack and slash/beat 'em up": "Hack and Slash",
    "point-and-click": "Point-and-Click",
    "card & board game": "Card & Board Game", "board games": "Card & Board Game",
    "card": "Card & Board Game",
    "massively multiplayer": "Massively Multiplayer",
    "quiz/trivia": "Quiz/Trivia",
    "educational": "Educational", "education": "Educational",
}
GENRE_NAMES = tuple(sorted(set(GENRE_ALIASES.values())))


def genre_column(genre):
    return "genre_" + re.sub(r"[^a-z0-9]+", "_", genre.lower()).strip("_")


GENRE_FLAG_COLS = [genre_column(g) for g in GENRE_NAMES]
GENRE_OUTPUT_COLS = ["primary_genre", "genre_count", "genre_source"] + GENRE_FLAG_COLS


def normalize_genres(*values):
    """Merge genre strings from any source into shared names, first-seen order."""
    found = []
    for value in values:
        if is_blank(value):
            continue
        for part in re.split(r"\s*[;|]\s*", str(value)):
            genre = GENRE_ALIASES.get(part.strip().lower())
            if genre and genre not in found:
                found.append(genre)
    return found


def search_genres(row, token):
    """Look a game's genres up online. Returns (genres list, source name)."""
    appid = pd.to_numeric(row.get("steam_appid"), errors="coerce")
    rawg_id = pd.to_numeric(row.get("rawg_id"), errors="coerce")
    title = row["game_name"]
    if pd.notna(appid):
        details = cached(f"steam_details_v2_{int(appid)}", fetch_steam_details, int(appid))
        found = normalize_genres((details or {}).get("genres"))
        if found:
            return found, "steam"
    if RAWG_KEY and pd.notna(rawg_id):
        detail = cached(f"rawg_detail_{int(rawg_id)}", fetch_rawg_detail, int(rawg_id))
        found = normalize_genres(join_names((detail or {}).get("genres")))
        if found:
            return found, "rawg_detail"
    if token:
        for hit in igdb_title_matches(title, token, "genres.name", "igdb_genre_search"):
            found = normalize_genres(join_names(hit.get("genres")))
            if found:
                return found, "igdb_search"
    if RAWG_KEY and pd.isna(rawg_id):
        for hit in rawg_title_matches(title):
            found = normalize_genres(join_names(hit.get("genres")))
            if found:
                return found, "rawg_search"
    return [], ""


def fill_missing_genres(games):
    """Merge every source's genres, backfill blanks online, then split into columns.

    Adds genres (shared vocabulary), primary_genre, genre_count, genre_source and
    one 0/1 column per genre (genre_action, genre_rpg, ...). Games still without
    a genre are written to output/games_missing_genre.csv.
    """
    games = games.copy()
    for col in ("genres", "igdb_genres", "rawg_genres"):
        if col not in games.columns:
            games[col] = pd.NA
    merged = [normalize_genres(a, b, c)
              for a, b, c in zip(games["genres"], games["igdb_genres"], games["rawg_genres"])]
    source = pd.Series(["catalog" if g else "" for g in merged], index=games.index)
    missing = [i for i, g in enumerate(merged) if not g]
    print(f"      {len(missing)} games missing a genre - searching sources...")

    token = igdb_token() if IGDB_CLIENT_ID and IGDB_CLIENT_SECRET else None
    for n, pos in enumerate(missing, 1):
        found, found_source = search_genres(games.iloc[pos], token)
        if found:
            merged[pos], source.iloc[pos] = found, found_source
        if n % 100 == 0:
            print(f"      genre lookup {n}/{len(missing)}")

    games["genres"] = ["; ".join(g) for g in merged]
    games["genre_source"] = source
    games["primary_genre"] = [g[0] if g else "" for g in merged]
    games["genre_count"] = [len(g) for g in merged]
    for genre, col in zip(GENRE_NAMES, GENRE_FLAG_COLS):
        games[col] = [int(genre in g) for g in merged]

    still = games[games["genre_count"].eq(0)]
    if not still.empty:
        cols = [c for c in ("steam_appid", "game_name", "platform", "data_source") if c in still.columns]
        still[cols].to_csv(OUT_DIR / "games_missing_genre.csv", index=False, encoding="utf-8-sig")
        print(f"      ! {len(still)} games still have no genre "
              f"(see output/games_missing_genre.csv)")
    return games


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


GAMING_LEXICON = {
    "goated": 3.0, "banger": 2.5, "addictive": 1.5, "polished": 2.0, "immersive": 2.0,
    "mid": -1.0, "buggy": -2.0, "bugs": -1.5, "bug": -1.5, "crash": -2.0,
    "crashes": -2.0, "crashing": -2.0, "stutter": -1.5, "stuttering": -1.5,
    "laggy": -2.0, "lag": -1.5, "p2w": -2.5, "pay2win": -2.5, "grindy": -1.5,
    "grind": -1.0, "unoptimized": -2.0, "overpriced": -2.0, "cheaters": -2.5,
    "hackers": -2.0, "aimbot": -2.5, "refund": -1.5, "refunded": -2.0,
    "microtransactions": -1.5, "repetitive": -1.5, "unplayable": -3.0,
}
# Contrast words start a new clause so each side of "great, but ..." is scored alone
SEGMENT_SPLIT = re.compile(
    r"[.!?;\n]+|,?\s+\b(?:but|however|although|though|yet|except|unfortunately|"
    r"sadly|despite|whereas)\b",
    re.IGNORECASE,
)
NEUTRAL_BAND = 0.05      # |compound| below this is treated as neutral
MAX_SEGMENTS = 60        # cap work on very long reviews
MIXED_MIN_SHARE = 0.25   # minority polarity must carry >=25% of opinion to be "mixed"


def score_review_text(text, analyzer):
    """Score a review clause by clause so opposing opinions offset each other.

    Whole-text VADER saturates toward +/-1 on long reviews, so a review with
    real praise and real complaints still reads as extreme. Here every clause is
    scored on its own; positive and negative strength are summed separately and
    the final score is the average opinion strength. Balanced praise/complaints
    land near 50, one-sided reviews stay near the ends.
    Returns (score_0_100, positive_share, negative_share, is_mixed).
    """
    segments = [s.strip() for s in SEGMENT_SPLIT.split(text or "") if s and s.strip()]
    pos = neg = 0.0
    opinionated = 0
    for seg in segments[:MAX_SEGMENTS]:
        c = analyzer.polarity_scores(seg)["compound"]
        if c >= NEUTRAL_BAND:
            pos += c
        elif c <= -NEUTRAL_BAND:
            neg += -c
        else:
            continue
        opinionated += 1
    if opinionated == 0:
        return 50.0, 0.0, 0.0, False
    avg_opinion = (pos - neg) / opinionated          # -1..1
    score = 50 + 50 * max(-1.0, min(1.0, avg_opinion * 1.25))
    total = pos + neg
    pos_share, neg_share = pos / total, neg / total
    return round(score, 1), round(pos_share, 2), round(neg_share, 2), \
        min(pos_share, neg_share) >= MIXED_MIN_SHARE


def add_sentiment_ratings(reviews):
    """Add clause-level VADER scores, mixed-sentiment flag and five-band ratings."""
    analyzer = SentimentIntensityAnalyzer()
    analyzer.lexicon.update(GAMING_LEXICON)
    results = [score_review_text(str(t), analyzer)
               for t in reviews["review_text"].fillna("")]
    scored = pd.DataFrame(results, index=reviews.index,
                          columns=["score", "pos_share", "neg_share", "mixed"])

    rated = reviews.copy()
    rated["sentiment_score_100"] = scored["score"]
    rated["sentiment_positive_share"] = scored["pos_share"]
    rated["sentiment_negative_share"] = scored["neg_share"]
    rated["sentiment_mixed"] = scored["mixed"].astype(bool)
    rated["sentiment_rating"] = scored["score"].map(sentiment_rating).astype("int8")
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
    created = pd.to_datetime(df["created_ts"], unit="s", utc=True, errors="coerce")
    df["review_date"] = created.dt.strftime("%Y-%m-%d")
    df["review_month"] = created.dt.strftime("%Y-%m")
    df["playtime_at_review_hrs"] = (pd.to_numeric(df["playtime_at_review_min"],
                                                  errors="coerce") / 60).round(1)
    df["playtime_total_hrs"] = (pd.to_numeric(df["playtime_forever_min"],
                                              errors="coerce") / 60).round(1)
    df["short_playtime_flag"] = df["playtime_at_review_hrs"] < 1  # useful for review-bomb checks
    # reviewer's vote contradicts the tone of their own text
    voted = df["voted_up"].map(parse_source_bool).astype("object")
    voted_up = voted.eq(True).fillna(False).astype(bool)
    voted_down = voted.eq(False).fillna(False).astype(bool)
    df["vote_text_mismatch"] = (
        (voted_up & (df["sentiment_rating"] <= 2))
        | (voted_down & (df["sentiment_rating"] >= 4))
    )
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


def build_game_summary(reviews, games):
    """One row per reviewed game with sentiment metrics next to catalog data."""
    grouped = reviews.groupby("steam_appid")
    summary = pd.DataFrame({
        "reviews_kept": grouped.size(),
        "pct_voted_positive": grouped["voted_up"].apply(
            lambda s: round(s.map(parse_source_bool).dropna().astype(bool).mean() * 100, 1)),
        "avg_sentiment_score_100": grouped["sentiment_score_100"].mean().round(1),
        "median_sentiment_score_100": grouped["sentiment_score_100"].median().round(1),
        "pct_very_poor_or_poor": grouped["sentiment_rating"].apply(
            lambda s: round((s <= 2).mean() * 100, 1)),
        "pct_good_or_very_good": grouped["sentiment_rating"].apply(
            lambda s: round((s >= 4).mean() * 100, 1)),
        "pct_mixed_sentiment": grouped["sentiment_mixed"].apply(
            lambda s: round(s.mean() * 100, 1)),
        "pct_vote_text_mismatch": grouped["vote_text_mismatch"].apply(
            lambda s: round(s.mean() * 100, 1)),
        "pct_short_playtime": grouped["short_playtime_flag"].apply(
            lambda s: round(s.mean() * 100, 1)),
        "median_playtime_at_review_hrs": grouped["playtime_at_review_hrs"].median(),
        "avg_votes_up": grouped["votes_up"].mean().round(1),
        "avg_word_count": grouped["word_count"].mean().round(1),
        "first_review_date": grouped["review_date"].min(),
        "last_review_date": grouped["review_date"].max(),
    }).reset_index()
    steam_games = games.dropna(subset=["steam_appid"]).drop_duplicates("steam_appid")
    summary["steam_appid"] = summary["steam_appid"].astype("Int64")
    return summary.merge(steam_games, on="steam_appid", how="left")


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
def main():
    if not RAWG_KEY:
        sys.exit("Missing RAWG_API_KEY. Copy .env.example to .env and add your key.")

    # ---- 1. IGDB + RAWG bulk acquisition -> Data CSVs ----------------------
    print(f"[1/6] Downloading {YEAR} releases from IGDB...")
    igdb = acquire_igdb()
    print(f"[2/6] Downloading {YEAR} releases from RAWG...")
    rawg = acquire_rawg()

    # ---- 3. Steam candidate pool (RAWG PC games + top IGDB Steam games) ----
    print("[3/6] Matching candidates to Steam (release year, free vs paid)...")
    candidates = cached("rawg_candidates", fetch_rawg_candidates) or []
    meta = {}   # appid -> metadata known before Steam is asked
    for i, c in enumerate(candidates, 1):
        stores = cached(f"rawg_stores_{c['id']}", fetch_steam_appid, c["id"])
        appid = (stores or {}).get("appid")
        if appid:
            meta[appid] = {"rawg_id": c["id"], "rawg_rating": c.get("rating"),
                           "rawg_ratings_count": c.get("ratings_count"),
                           "metacritic": c.get("metacritic")}
    if not igdb.empty:
        top = igdb.dropna(subset=["steam_appid"]).copy()
        top["_pop"] = (pd.to_numeric(top["igdb_follows"], errors="coerce").fillna(0)
                       + pd.to_numeric(top["igdb_rating_count"], errors="coerce").fillna(0))
        for appid in top.nlargest(IGDB_EXTRA_CANDIDATES, "_pop")["steam_appid"].astype(int):
            meta.setdefault(appid, {})
    if not meta:
        sys.exit("No candidates - check your API keys and internet connection.")
    print(f"      {len(meta)} candidate Steam apps")

    pool = []
    for i, (appid, m) in enumerate(meta.items(), 1):
        details = cached(f"steam_details_v2_{appid}", fetch_steam_details, appid)
        if not details:
            continue
        summary = cached(f"steam_summary_{appid}", fetch_review_summary, appid)
        if not summary:
            continue
        pool.append({**details, **summary, **m})
        if i % 20 == 0:
            print(f"      checked {i}/{len(meta)}")

    games = clean_games(pd.DataFrame(pool))
    if games.empty:
        sys.exit("No usable 2025 Steam games found.")

    # ---- 4. pick top free + top paid by review volume ----------------------
    free = games[games["is_free"]].nlargest(FREE_TARGET, "total_reviews")
    paid = games[~games["is_free"]].nlargest(PAID_TARGET, "total_reviews")
    if len(free) < FREE_TARGET or len(paid) < PAID_TARGET:
        print(f"      ! only found {len(free)} free / {len(paid)} paid games - "
              f"raise RAWG_PAGES / IGDB_EXTRA_CANDIDATES for a bigger pool.")
    selected = pd.concat([free, paid]).reset_index(drop=True)
    print(f"[4/6] Selected {len(free)} free + {len(paid)} paid games")

    supplemental_reviews, steam_catalog = load_supplemental_steam_data()
    base = supplemental_game_rows(selected, steam_catalog)
    games_output = fill_missing_genres(
        fill_missing_developers(merge_all_games(base, igdb, rawg)))

    # ---- 5. reviews + cleaning --------------------------------------------
    print("[5/6] Pulling Steam reviews (recent + most helpful) and cleaning...")
    rows = []
    for _, g in selected.iterrows():
        appid = int(g["steam_appid"])
        recent = cached(f"steam_reviews_{appid}_recent_{REVIEWS_RECENT}",
                        fetch_steam_reviews, appid, "recent", REVIEWS_RECENT) or []
        helpful = cached(f"steam_reviews_{appid}_helpful_{REVIEWS_HELPFUL}",
                         fetch_steam_reviews, appid, "all", REVIEWS_HELPFUL) or []
        print(f"      {g['game_name']}: {len(recent)} recent + {len(helpful)} helpful")
        rows.extend(flatten_review(r, appid, "recent") for r in recent)
        rows.extend(flatten_review(r, appid, "helpful") for r in helpful)

    print(f"      steam 2025.csv: {len(supplemental_reviews)} supplemental reviews")
    rows.extend(supplemental_reviews.to_dict("records"))

    if not rows:
        sys.exit("No reviews were retrieved.")
    reviews, log = clean_reviews(pd.DataFrame(rows))
    reviews["steam_appid"] = pd.to_numeric(reviews["steam_appid"]).astype("Int64")

    # ---- 6. write outputs --------------------------------------------------
    print("[6/6] Writing outputs...")
    game_cols = [
        "steam_appid", "game_name", "game_type", "release_date", "price_usd", "genres",
        "developers", "developer_source", "publishers", "steam_pct_positive", "total_reviews",
        "review_score_desc", "steam_metacritic", "metacritic", "rawg_rating",
        "rawg_esrb", "rawg_tags", "igdb_rating", "igdb_critic_rating", "igdb_follows",
        "igdb_themes", "igdb_game_modes", "igdb_perspectives", "igdb_platforms",
        "steam_categories", "steam_platforms",
    ] + GENRE_OUTPUT_COLS
    game_cols = [c for c in game_cols if c in games_output.columns]
    steam_games = games_output.dropna(subset=["steam_appid"]).drop_duplicates("steam_appid")
    out = reviews.merge(steam_games[game_cols], on="steam_appid", how="left")
    out = out.rename(columns={"total_reviews": "steam_total_reviews",
                              "review_score_desc": "steam_review_score_desc"})
    review_cols = [
        "steam_appid", "game_name", "game_type", "release_date", "genres", "primary_genre",
        "genre_count", "genre_source", *GENRE_FLAG_COLS, "price_usd",
        "developers", "developer_source", "publishers", "steam_total_reviews", "steam_pct_positive",
        "steam_review_score_desc", "steam_metacritic", "metacritic", "rawg_rating",
        "rawg_esrb", "rawg_tags", "igdb_rating", "igdb_critic_rating", "igdb_follows",
        "igdb_themes", "igdb_game_modes", "igdb_perspectives", "igdb_platforms",
        "steam_categories", "steam_platforms",
        "recommendation_id", "review_pull", "review_date", "review_month",
        "review_text", "word_count", "sentiment_label", "sentiment_score_100",
        "sentiment_rating", "sentiment_category", "sentiment_mixed",
        "sentiment_positive_share", "sentiment_negative_share", "vote_text_mismatch",
        "votes_up", "votes_funny", "comment_count", "weighted_vote_score",
        "playtime_at_review_hrs", "playtime_total_hrs", "short_playtime_flag",
        "steam_purchase", "received_for_free", "early_access",
        "author_num_reviews", "author_num_games_owned", "data_source",
    ]
    out = out[[c for c in review_cols if c in out.columns]]

    # utf-8-sig so Excel opens the file with correct characters
    out.to_csv(OUT_DIR / "gamepulse_reviews_clean.csv", index=False, encoding="utf-8-sig")
    games_output.to_csv(OUT_DIR / "gamepulse_games_clean.csv", index=False, encoding="utf-8-sig")
    build_game_summary(reviews, games_output).to_csv(
        OUT_DIR / "gamepulse_game_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(log, columns=["step", "rows"]).to_csv(OUT_DIR / "cleaning_log.csv", index=False)

    print("\nCleaning summary")
    for step, n in log:
        print(f"  {step:<55} {n:>6}")
    print(f"\nSaved {len(out)} reviews from {out['game_name'].nunique()} games and "
          f"{len(games_output)} catalog games to {OUT_DIR}")


if __name__ == "__main__":
    main()
