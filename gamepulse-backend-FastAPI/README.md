# GamePulse FastAPI backend

This API reads the local Microsoft SQL Server database restored from
`../Database/GamePulse.bak`.

## Setup

1. Install Microsoft ODBC Driver 18 for SQL Server and Python 3.10 or newer.
2. From this folder, create/activate a virtual environment and install the
   Python packages:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. The backup is restored as `GamePulse` on the local default SQL Server
   instance. By default, the API uses Windows integrated authentication, so
   the Windows account running Uvicorn needs access to the database. To use a
   different server or SQL authentication, set the `GAMEPULSE_SQL_*`
   environment variables shown in `.env.example` before starting the API.
4. Start the API from this folder:

   ```powershell
   uvicorn app.main:app --reload
   ```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Routes

- `GET /health/db` — check the SQL Server connection.
- `GET /developers` and `GET /platforms`
- `GET /games?limit=100&offset=0&developer_id=1`
- `GET /games/{game_id}`
- `GET /game-platforms?game_id=1&limit=100&offset=0`
- `GET /genres?game_id=1&limit=100&offset=0`
- `GET /reviews?game_id=1&sentiment=1&limit=100&offset=0`

List endpoints cap `limit` at 500. Review sentiment can be filtered by its
stored integer value. The included backup currently contains the schema but no rows, so
the list endpoints return empty lists until data is inserted.
