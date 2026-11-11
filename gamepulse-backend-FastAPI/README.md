# GamePulse FastAPI backend

This API reads the local Microsoft SQL Server database restored from
`../Database/GamePulse.bak`. The backup contains data and the `dbo` stored
procedures used by the `/procedures` endpoints.

## 1. Requirements

- Python 3.10+ and Microsoft SQL Server with the restored GamePulse database.
- Microsoft ODBC Driver 18 for SQL Server and a database account with read
  access and permission to execute the stored procedures.

## 2. Set up the environment

1. Install Microsoft ODBC Driver 18 for SQL Server and Python 3.10 or newer.
2. From this folder, create/activate a virtual environment and install the
   Python packages:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

   `requirements.txt` installs FastAPI, Uvicorn, pyodbc, Pydantic and
   `vaderSentiment`. Uvicorn's standard extras include `python-dotenv` for
   loading the configuration file; no separate sentiment model download is
   needed.

3. Restore the backup as `GamePulse` on the local default SQL Server
   instance. By default, the API uses ODBC Driver 18 and Windows integrated
   authentication, so the Windows account running Uvicorn needs access to
   the database. The default settings in `.env.example` target this instance.
   To use a different server or SQL authentication, set the `GAMEPULSE_SQL_*`
   environment variables before starting the API. For SQL authentication,
   provide both `GAMEPULSE_SQL_USER` and `GAMEPULSE_SQL_PASSWORD`.
   Setting only one is a configuration error. The connection encrypts traffic
   but trusts the server certificate; use an appropriately secured SQL Server.
4. Start the API from this folder:

   ```powershell
   uvicorn app.main:app --reload --env-file .env
   ```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## 3. Stored procedures

The `/procedures` routes execute the procedures already included in the
GamePulse backup. The `.sql` files in `../Database` are their source
definitions; they do not need to be installed again after restoring this
backup. If deploying to a different database, install the corresponding
definitions using SQL Server Management Studio or `sqlcmd`, for example:

```powershell
sqlcmd -S localhost -d GamePulse -E -C -b -i ..\Database\GetAllDevelopers.sql
```

These source scripts use `CREATE PROCEDURE`, so do not rerun them unchanged
if the procedure already exists. `GetDeveloper.sql` creates
`dbo.GetDevelopers` (plural). The API login needs permission to execute the
procedures. The scripts use `USE [GamePulse]`; adjust that statement when
deploying to another database. The API does not install scripts or change the
database automatically.

| Route | Procedure |
| --- | --- |
| `GET /procedures/developers` | `dbo.GetAllDevelopers` |
| `GET /procedures/developers/{developer_id}` | `dbo.GetDevelopers` |
| `GET /procedures/platforms` | `dbo.GetAllPlatforms` |
| `GET /procedures/platforms/{platform_id}` | `dbo.GetPlatform` |
| `GET /procedures/genres` | `dbo.GetAllGenres` |
| `GET /procedures/genres/{genre_id}` | `dbo.GetGenre` |
| `GET /procedures/games` | `dbo.GetALLGames` |
| `GET /procedures/games/search?search_term=title` | `dbo.SearchGames` |
| `GET /procedures/games/top/free` | `dbo.GetTop10FreeGames` |
| `GET /procedures/games/top/paid` | `dbo.GetTop10PaidGames` |
| `GET /procedures/games/{game_id}` | `dbo.GetGame` |
| `GET /procedures/games/{game_id}/reviews` | `dbo.GetGameReviews` |
| `GET /procedures/reviews/{review_id}` | `dbo.GetReview` |

These routes return the columns supplied by each procedure as JSON objects;
list routes return arrays, including an empty array when there are no rows.
Individual lookup routes return 404 when no record exists. Search accepts up
to 100 characters and defaults to an empty search term, as in the script.
Database errors return a generic 500 response and are logged on the server.
The direct-query routes below also use the restored GamePulse schema.

## 4. Routes

- `GET /health/db` — check the SQL Server connection.
- `GET /developers` and `GET /platforms`
- `GET /games?limit=100&offset=0&developer_id=1`
- `GET /games/{game_id}`
- `GET /games/{game_id}/summary` — review count, average stored sentiment, and positive (60–100), neutral (40–<60), and negative (<40) counts.
- `GET /game-platforms?game_id=1&limit=100&offset=0`
- `GET /genres?game_id=1&limit=100&offset=0`
- `GET /reviews?game_id=1&sentiment=75.5&limit=100&offset=0` — exact stored score, from 0 to 100.
- `POST /sentiment` — infer sentiment from review text. Send JSON such as `{"text":"Great gameplay, but the game is buggy."}` to receive a 0–100 score, positive/negative shares, mixed flag, and five-band rating.

List endpoints cap `limit` at 500. Review sentiment scores are decimals from
0 to 100. The sentiment endpoint uses the same clause-aware VADER rules and
gaming lexicon as the pipeline in `../AI Development/gamepulse_pipeline.py`;
the mixed flag is calculated before the shares are rounded. The backend reads
the database and does not import the pipeline's CSV outputs automatically.

## 5. Tests

From this folder:

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

The default tests mock SQL Server and skip the read-only integration test.
To test the actual tables and all procedure routes, restore a populated
database, configure `.env`, and run:

```powershell
$env:GAMEPULSE_TEST_DATABASE = "1"
python -m dotenv -f .env run -- python -m unittest discover -s tests -v
Remove-Item Env:GAMEPULSE_TEST_DATABASE
```

The integration test requires at least one developer, platform, game, genre,
and review. It reads data but does not modify the database. Test requirements
include `httpx` and, on Python 3.11+, `httpx2` for the FastAPI/Starlette test
client across the supported dependency range.
