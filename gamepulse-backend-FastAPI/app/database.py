"""SQL Server connection helpers for the GamePulse API."""

import os
from collections.abc import Iterator

import pyodbc
from fastapi import HTTPException


def connect() -> pyodbc.Connection:
    """Open a connection using environment configuration.

    By default this uses Windows integrated authentication against the local
    default SQL Server instance. Set GAMEPULSE_SQL_USER and
    GAMEPULSE_SQL_PASSWORD together to use SQL authentication instead.
    """
    driver = os.getenv("GAMEPULSE_SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    server = os.getenv("GAMEPULSE_SQL_SERVER", "localhost")
    database = os.getenv("GAMEPULSE_SQL_DATABASE", "GamePulse")
    username = os.getenv("GAMEPULSE_SQL_USER")
    password = os.getenv("GAMEPULSE_SQL_PASSWORD")

    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
        f"DATABASE={database}",
        "Encrypt=yes",
        "TrustServerCertificate=yes",
    ]
    if username and password:
        parts.extend((f"UID={username}", f"PWD={password}"))
    else:
        parts.append("Trusted_Connection=yes")

    return pyodbc.connect(";".join(parts), timeout=5)


def get_connection() -> Iterator[pyodbc.Connection]:
    """FastAPI dependency that closes each request's connection."""
    try:
        connection = connect()
    except pyodbc.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not connect to the GamePulse database",
        ) from exc
    try:
        yield connection
    finally:
        connection.close()
