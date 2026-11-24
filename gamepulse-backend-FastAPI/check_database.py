"""Check the configured SQL Server driver and connection without changing data."""

import os
from pathlib import Path
import sys

try:
    import pyodbc
    from dotenv import load_dotenv
    from fastapi import HTTPException
    from app.database import connect
except ImportError as error:
    print(
        f"Database check requires the backend dependencies ({error}). "
        "Run the project setup first.",
        file=sys.stderr,
    )
    sys.exit(1)


def main():
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.is_file():
        load_dotenv(env_file)
    else:
        print("Backend .env not found; checking environment variables and defaults.", flush=True)

    driver = os.getenv("GAMEPULSE_SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    if driver not in pyodbc.drivers():
        print(
            f"ODBC driver '{driver}' was not found. Install the configured driver "
            "and check GAMEPULSE_SQL_DRIVER.",
            file=sys.stderr,
        )
        return 1
    print(f"ODBC driver found: {driver}", flush=True)

    try:
        connection = connect()
        connection.close()
    except HTTPException as error:
        print(f"Database configuration error: {error.detail}", file=sys.stderr)
        return 1
    except pyodbc.Error as error:
        print(
            f"SQL Server connection failed ({type(error).__name__}). Check the server, "
            "database, credentials, and account permissions.",
            file=sys.stderr,
        )
        return 1
    print("SQL Server connection succeeded.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
