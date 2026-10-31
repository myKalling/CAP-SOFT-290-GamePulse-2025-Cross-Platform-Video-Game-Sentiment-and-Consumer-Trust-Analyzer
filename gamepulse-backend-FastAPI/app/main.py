"""GamePulse API backed by the restored SQL Server database."""

from typing import Annotated

import pyodbc
from fastapi import Depends, FastAPI, HTTPException, Query

from app.database import get_connection
from app.schemas import Developer, Game, GameGenre, GamePlatform, Platform, Review

app = FastAPI(
    title="GamePulse API",
    description="Read game, platform, developer, genre, and sentiment review data.",
    version="1.0.0",
)

Connection = Annotated[pyodbc.Connection, Depends(get_connection)]


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
