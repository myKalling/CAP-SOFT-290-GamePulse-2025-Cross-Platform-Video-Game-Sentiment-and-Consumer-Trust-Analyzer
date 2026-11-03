"""GamePulse API backed by the restored SQL Server database."""

import re
from typing import Annotated

import pyodbc
from fastapi import Depends, FastAPI, HTTPException, Query

from app.database import get_connection
from app.schemas import (
    Developer, Game, GameGenre, GamePlatform, GameReviewSummary, Platform,
    Review, SentimentRequest, SentimentResult,
)

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:  # Keep catalog endpoints usable when optional NLP deps are absent.
    SentimentIntensityAnalyzer = None

app = FastAPI(
    title="GamePulse API",
    description="Read game, platform, developer, genre, and sentiment review data.",
    version="1.0.0",
)

Connection = Annotated[pyodbc.Connection, Depends(get_connection)]

SENTIMENT_CATEGORIES = {1: "Very Poor", 2: "Poor", 3: "Mid", 4: "Good", 5: "Very Good"}
GAMING_LEXICON = {
    "goated": 3.0, "banger": 2.5, "addictive": 1.5, "polished": 2.0, "immersive": 2.0,
    "mid": -1.0, "buggy": -2.0, "bugs": -1.5, "bug": -1.5, "crash": -2.0,
    "crashes": -2.0, "crashing": -2.0, "stutter": -1.5, "stuttering": -1.5,
    "laggy": -2.0, "lag": -1.5, "p2w": -2.5, "pay2win": -2.5, "grindy": -1.5,
    "grind": -1.0, "unoptimized": -2.0, "overpriced": -2.0, "cheaters": -2.5,
    "hackers": -2.0, "aimbot": -2.5, "refund": -1.5, "refunded": -2.0,
    "microtransactions": -1.5, "repetitive": -1.5, "unplayable": -3.0,
}
SEGMENT_SPLIT = re.compile(
    r"[.!?;\n]+|,?\s+\b(?:but|however|although|though|yet|except|unfortunately|sadly|despite|whereas)\b",
    re.IGNORECASE,
)


def infer_sentiment(text: str) -> dict:
    if SentimentIntensityAnalyzer is None:
        raise HTTPException(status_code=503, detail="Sentiment model dependency is not installed")
    analyzer = SentimentIntensityAnalyzer()
    analyzer.lexicon.update(GAMING_LEXICON)
    positive = negative = 0.0
    opinionated = 0
    for segment in [part.strip() for part in SEGMENT_SPLIT.split(text) if part.strip()][:60]:
        compound = analyzer.polarity_scores(segment)["compound"]
        if compound >= 0.05:
            positive += compound
        elif compound <= -0.05:
            negative -= compound
        else:
            continue
        opinionated += 1
    if not opinionated:
        score, positive_share, negative_share, mixed = 50.0, 0.0, 0.0, False
    else:
        score = round(50 + 50 * max(-1.0, min(1.0, ((positive - negative) / opinionated) * 1.25)), 1)
        total = positive + negative
        positive_share, negative_share = round(positive / total, 2), round(negative / total, 2)
        mixed = min(positive_share, negative_share) >= 0.25
    rating = min(int(score // 20) + 1, 5)
    return {
        "score_100": score, "positive_share": positive_share,
        "negative_share": negative_share, "mixed": mixed,
        "rating": rating, "category": SENTIMENT_CATEGORIES[rating],
    }


def fetch_all(connection: pyodbc.Connection, sql: str, params: tuple = ()) -> list[dict]:
    cursor = connection.cursor()
    try:
        cursor.execute(sql, params)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        cursor.close()


def fetch_one(connection: pyodbc.Connection, sql: str, params: tuple = ()) -> dict | None:
    rows = fetch_all(connection, sql, params)
    return rows[0] if rows else None


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "GamePulse API is running", "database": "GamePulse"}


@app.post("/sentiment", response_model=SentimentResult)
def score_sentiment(request: SentimentRequest) -> dict:
    """Infer review sentiment using the same clause-aware VADER rule as the data pipeline."""
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")
    return infer_sentiment(request.text)


@app.get("/health/db")
def database_health(connection: Connection) -> dict[str, str]:
    try:
        fetch_one(connection, "SELECT DB_NAME() AS database_name")
    except pyodbc.Error as exc:
        raise HTTPException(status_code=503, detail="Could not connect to the GamePulse database") from exc
    return {"status": "connected", "database": "GamePulse"}


@app.get("/developers", response_model=list[Developer])
def list_developers(connection: Connection) -> list[dict]:
    return fetch_all(
        connection,
        "SELECT DeveloperID, DeveloperName FROM dbo.Developer ORDER BY DeveloperName",
    )


@app.get("/platforms", response_model=list[Platform])
def list_platforms(connection: Connection) -> list[dict]:
    return fetch_all(
        connection,
        "SELECT PlatformID, PlatformName FROM dbo.Platform ORDER BY PlatformName",
    )


@app.get("/games", response_model=list[Game])
def list_games(
    connection: Connection,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    developer_id: int | None = Query(default=None, gt=0),
) -> list[dict]:
    sql = """
        SELECT g.GameID, g.Title, g.DeveloperID, d.DeveloperName
        FROM dbo.Game AS g
        INNER JOIN dbo.Developer AS d ON d.DeveloperID = g.DeveloperID
    """
    params: tuple = ()
    if developer_id is not None:
        sql += " WHERE g.DeveloperID = ?"
        params = (developer_id,)
    sql += " ORDER BY g.Title OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    return fetch_all(connection, sql, (*params, offset, limit))


@app.get("/games/{game_id}", response_model=Game)
def get_game(game_id: int, connection: Connection) -> dict:
    game = fetch_one(
        connection,
        """
        SELECT g.GameID, g.Title, g.DeveloperID, d.DeveloperName
        FROM dbo.Game AS g
        INNER JOIN dbo.Developer AS d ON d.DeveloperID = g.DeveloperID
        WHERE g.GameID = ?
        """,
        (game_id,),
    )
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@app.get("/games/{game_id}/summary", response_model=GameReviewSummary)
def get_game_review_summary(game_id: int, connection: Connection) -> dict:
    summary = fetch_one(
        connection,
        """
        SELECT g.GameID, g.Title,
               COUNT(r.ReviewID) AS ReviewCount,
               AVG(CAST(r.Sentiment AS FLOAT)) AS AverageSentiment,
               COALESCE(SUM(CASE WHEN r.Sentiment > 0 THEN 1 ELSE 0 END), 0) AS PositiveReviews,
               COALESCE(SUM(CASE WHEN r.Sentiment < 0 THEN 1 ELSE 0 END), 0) AS NegativeReviews,
               COALESCE(SUM(CASE WHEN r.Sentiment = 0 THEN 1 ELSE 0 END), 0) AS NeutralReviews
        FROM dbo.Game AS g
        LEFT JOIN dbo.GamePlatforms AS gp ON gp.GameID = g.GameID
        LEFT JOIN dbo.Review AS r ON r.GamePlatformsID = gp.GamePlatformsID
        WHERE g.GameID = ?
        GROUP BY g.GameID, g.Title
        """,
        (game_id,),
    )
    if summary is None:
        raise HTTPException(status_code=404, detail="Game not found")
    if summary["AverageSentiment"] is not None:
        summary["AverageSentiment"] = round(summary["AverageSentiment"], 2)
    return summary


@app.get("/game-platforms", response_model=list[GamePlatform])
def list_game_platforms(
    connection: Connection,
    game_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    sql = """
        SELECT gp.GamePlatformsID, gp.GameID, gp.PlatformID, p.PlatformName,
               gp.ReleaseDate, gp.Price
        FROM dbo.GamePlatforms AS gp
        INNER JOIN dbo.Platform AS p ON p.PlatformID = gp.PlatformID
    """
    params: tuple = ()
    if game_id is not None:
        sql += " WHERE gp.GameID = ?"
        params = (game_id,)
    sql += " ORDER BY gp.GameID, p.PlatformName OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    return fetch_all(connection, sql, (*params, offset, limit))


@app.get("/genres", response_model=list[GameGenre])
def list_game_genres(
    connection: Connection,
    game_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    sql = """
        SELECT gg.GameID, gg.GenreID, gr.Genre
        FROM dbo.GameGenres AS gg
        INNER JOIN dbo.Genre AS gr ON gr.GenreID = gg.GenreID
    """
    params: tuple = ()
    if game_id is not None:
        sql += " WHERE gg.GameID = ?"
        params = (game_id,)
    sql += " ORDER BY gg.GameID, gr.Genre OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    return fetch_all(connection, sql, (*params, offset, limit))


@app.get("/reviews", response_model=list[Review])
def list_reviews(
    connection: Connection,
    game_id: int | None = Query(default=None, gt=0),
    sentiment: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    sql = """
        SELECT r.ReviewID, r.GamePlatformsID, r.Review, r.Sentiment
        FROM dbo.Review AS r
        INNER JOIN dbo.GamePlatforms AS gp ON gp.GamePlatformsID = r.GamePlatformsID
    """
    conditions = []
    params: list[int] = []
    if game_id is not None:
        conditions.append("gp.GameID = ?")
        params.append(game_id)
    if sentiment is not None:
        conditions.append("r.Sentiment = ?")
        params.append(sentiment)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY r.ReviewID OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    params.extend((offset, limit))
    return fetch_all(connection, sql, tuple(params))
