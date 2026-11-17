"""Endpoints for the stored procedures supplied with GamePulse."""

import logging
from decimal import Decimal
from typing import Annotated, Any

import pyodbc
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/procedures", tags=["stored procedures"])
Connection = Annotated[pyodbc.Connection, Depends(get_connection)]


def execute_procedure(
    connection: pyodbc.Connection, sql: str, params: tuple = ()
) -> list[dict[str, Any]]:
    """Execute a fixed, parameterized procedure call and return its result set."""
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        while cursor.description is None:
            if not cursor.nextset():
                logger.error("Stored procedure returned no result set: %s", sql)
                raise HTTPException(status_code=500, detail="Stored procedure returned no result set")
        columns = [column[0] for column in cursor.description]
        rows = [
            {
                column: float(value) if isinstance(value, Decimal) else value
                for column, value in zip(columns, row)
            }
            for row in cursor.fetchall()
        ]
        # Several supplied procedures report SQL errors as a one-column result.
        if len(columns) == 1 and columns[0].lower() == "errormessage" and rows:
            logger.error("Stored procedure %s failed: %s", sql, rows[0][columns[0]])
            raise HTTPException(status_code=500, detail="Stored procedure execution failed")
        return rows
    except pyodbc.Error:
        logger.exception("Stored procedure execution failed: %s", sql)
        raise HTTPException(status_code=500, detail="Stored procedure execution failed") from None
    finally:
        if cursor is not None:
            cursor.close()


def procedure_one(connection: pyodbc.Connection, sql: str, value: int) -> dict[str, Any]:
    rows = execute_procedure(connection, sql, (value,))
    if not rows:
        raise HTTPException(status_code=404, detail="Record not found")
    return rows[0]

developers_router = APIRouter(prefix="/developers", tags=["developers"])
games_router = APIRouter(prefix="/games", tags=["games"])
platforms_router = APIRouter(prefix="/platforms", tags=["platforms"])
genres_router = APIRouter(prefix="/genres", tags=["genres"])


@developers_router.get("/developers")
def all_developers(connection: Connection) -> list[dict[str, Any]]:
    return execute_procedure(connection, "EXEC dbo.GetAllDevelopers")


@developers_router.get("/developers/{developer_id}")
def developer(developer_id: int, connection: Connection) -> dict[str, Any]:
    return procedure_one(connection, "EXEC dbo.GetDevelopers @DeveloperID = ?", developer_id)


@platforms_router.get("/platforms")
def all_platforms(connection: Connection) -> list[dict[str, Any]]:
    return execute_procedure(connection, "EXEC dbo.GetAllPlatforms")


@platforms_router.get("/platforms/{platform_id}")
def platform(platform_id: int, connection: Connection) -> dict[str, Any]:
    return procedure_one(connection, "EXEC dbo.GetPlatform @PlatformID = ?", platform_id)


@genres_router.get("/genres")
def all_genres(connection: Connection) -> list[dict[str, Any]]:
    return execute_procedure(connection, "EXEC dbo.GetAllGenres")


@genres_router.get("/genres/{genre_id}")
def genre(genre_id: int, connection: Connection) -> dict[str, Any]:
    return procedure_one(connection, "EXEC dbo.GetGenre @GenreID = ?", genre_id)


@games_router.get("/games")
def all_games(connection: Connection) -> list[dict[str, Any]]:
    return execute_procedure(connection, "EXEC dbo.GetALLGames")


@games_router.get("/games/search")
def search_games(
    connection: Connection, search_term: str = Query(default="", max_length=100)
) -> list[dict[str, Any]]:
    return execute_procedure(connection, "EXEC dbo.SearchGames @SearchTerm = ?", (search_term,))


@games_router.get("/games/top/free")
def top_free_games(connection: Connection) -> list[dict[str, Any]]:
    return execute_procedure(connection, "EXEC dbo.GetTop10FreeGames")


@games_router.get("/games/top/paid")
def top_paid_games(connection: Connection) -> list[dict[str, Any]]:
    return execute_procedure(connection, "EXEC dbo.GetTop10PaidGames")


@games_router.get("/games/{game_id}")
def game(game_id: int, connection: Connection) -> dict[str, Any]:
    return procedure_one(connection, "EXEC dbo.GetGame @GameID = ?", game_id)


@games_router.get("/games/{game_id}/reviews")
def game_reviews(game_id: int, connection: Connection) -> list[dict[str, Any]]:
    return execute_procedure(connection, "EXEC dbo.GetGameReviews @GameID = ?", (game_id,))


@reviews_router.get("/reviews/{review_id}")
def review(review_id: int, connection: Connection) -> dict[str, Any]:
    return procedure_one(connection, "EXEC dbo.GetReview @ReviewID = ?", review_id)
