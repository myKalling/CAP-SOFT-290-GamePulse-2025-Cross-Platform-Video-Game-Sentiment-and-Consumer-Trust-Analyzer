# GamePulse

GamePulse displays the top 10 free and top 10 paid games of 2025, including
database-backed sentiment summaries. It includes an Expo front end, a FastAPI
backend, a SQL Server database backup, and a separate data and sentiment pipeline.

## Requirements

- Git and internet access.
- Python 3.11 or newer; Python 3.12 is the tested choice. Use a 64-bit build.
- Node.js 24.3 or later within the 24.x release line, with npm. The current
  React Native dependencies also support Node 22.13+ (22.x) and Node 26+.
- Microsoft SQL Server with a restored GamePulse database, plus
  [Microsoft ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server).
  Install SQL Server locally or use an accessible instance. On macOS, SQL Server
  requires a separate compatible host or container; check Microsoft's platform
  and architecture support before installing.
- For refreshing the AI pipeline data: a RAWG API key. IGDB/Twitch credentials
  are optional. The application itself can use the provided database without
  these keys.

The setup script installs project dependencies only; it does **not** install
Python, Node.js, SQL Server or ODBC, restore a database, or obtain credentials.

### Install Node.js

1. Download Node.js from the [official download page](https://nodejs.org/en/download).
   Select Node.js 24.x, version 24.3 or newer, and follow the instructions for
   your operating system. On Windows, run the Windows installer and keep npm
   selected.
2. Open a new terminal and verify the installation. On Windows PowerShell:

   ```powershell
   node --version
   npm.cmd --version
   ```

   On macOS or Linux, use `npm --version` instead. If either command is not
   found, restart your terminal and check that Node.js is on your PATH.

## Install

Clone this repository and run the setup script from its root:

```powershell
git clone https://github.com/myKalling/CAP-SOFT-290-GamePulse-2025-Cross-Platform-Video-Game-Sentiment-and-Consumer-Trust-Analyzer.git
cd CAP-SOFT-290-GamePulse-2025-Cross-Platform-Video-Game-Sentiment-and-Consumer-Trust-Analyzer
py -3.12 setup_gamepulse.py
```

On macOS or Linux, use `python3 setup_gamepulse.py` instead of `py -3.12`.
Select a compatible interpreter if `python3` is older than 3.11.

To check Python, Node.js, and npm without changing files or installing packages:

```powershell
py -3.12 setup_gamepulse.py --check-only
```

After installing the backend dependencies and configuring its `.env`, add
`--check-database` to also check the configured ODBC driver and attempt a
SQL Server connection. This check is optional and is not needed for the AI
pipeline. On macOS or Linux, use `python3` in these commands.

The script creates or reuses separate virtual environments for the API and AI
pipeline, installs their requirements, runs `npm ci` for the front end, and
creates `.env` files from examples when missing. **`npm ci` replaces the
front-end `node_modules` directory**; stop any running Expo server first.
Existing `.env` files are never overwritten. Check the output for errors before
continuing.

## Configure the database

1. Restore [`Database/GamePulse.bak`](Database/GamePulse.bak) as `GamePulse`
   on SQL Server using an administrator account. See
   [Microsoft's restore instructions](https://learn.microsoft.com/sql/relational-databases/backup-restore/restore-a-database-backup-using-ssms).
   SQL Server must be able to read the backup path; move it to an accessible
   location if the server runs in a container or on another host. Do not
   overwrite an existing database without first backing it up.
2. Edit `gamepulse-backend-FastAPI/.env`. The defaults use the local default
   SQL Server instance and Windows integrated authentication. For another
   instance, set `GAMEPULSE_SQL_SERVER` and `GAMEPULSE_SQL_DATABASE`; for SQL
   authentication set **both** `GAMEPULSE_SQL_USER` and
   `GAMEPULSE_SQL_PASSWORD`. On macOS and Linux, use an appropriately configured
   authentication method for your SQL Server; SQL authentication is the
   simplest option when Windows integrated authentication is unavailable.
3. Give the API account read access and permission to execute the stored
   procedures. The backup already contains the procedures. The development
   connection encrypts traffic but trusts the server certificate; use an
   appropriately secured SQL Server.

Keep all `.env` files and credentials out of Git. The web front end's default
`EXPO_PUBLIC_API_URL` is `http://127.0.0.1:8000`. Expo embeds `EXPO_PUBLIC_`
values in the client, so never put secrets there.

## Run the application

Use two terminals. On Windows:

```powershell
cd gamepulse-backend-FastAPI
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file .env
```

```powershell
cd front-end
npm.cmd run web -- --port 8081
```

On macOS or Linux, use `.venv/bin/python` in place of
`.\.venv\Scripts\python.exe` and `npm` in place of `npm.cmd`. Using `npm.cmd`
on Windows avoids PowerShell execution-policy restrictions on `npm.ps1`. Open
<http://localhost:8081/games>. API documentation is at
<http://127.0.0.1:8000/docs>, and <http://127.0.0.1:8000/health/db> checks the
database connection. Stop each process with Ctrl+C.

These settings are for local web development. The API currently permits browser
requests from `localhost:8081` and `127.0.0.1:8081` only. Mobile devices,
remote access, and production deployment require appropriate network addresses,
API binding, CORS, and security configuration; localhost on a phone refers to
the phone itself.

Existing stored-procedure routes retain their original paths; their
`/procedures` aliases and the direct-query `/queries` routes are listed in the
[API guide](gamepulse-backend-FastAPI/README.md).

Review inputs currently keep reviews only in the open application; they are not
saved to the database. The current sign-in stores a local username and is not
server authentication.

## AI data pipeline

Edit `AI Development/.env` to add `RAWG_API_KEY` and, optionally, both IGDB
credentials. Never commit the file. The required Xbox input CSV is included in
`AI Development/Data CSVs`. From the `AI Development` directory:

```powershell
.\.venv\Scripts\python.exe gamepulse_pipeline.py
```

On macOS or Linux, run `.venv/bin/python gamepulse_pipeline.py`. A full refresh
may take hours and contacts external APIs. Outputs are written to `output/`;
the pipeline does not automatically import them into SQL Server. See the
[pipeline guide](AI%20Development/README.md) for inputs, optional training
data, validation, and dataset usage restrictions.

## Checks and troubleshooting

- Front end: from `front-end`, run `npm.cmd run lint` and `npx.cmd tsc --noEmit`
  on Windows; use `npm` and `npx` on macOS/Linux.
- API: from `gamepulse-backend-FastAPI`, run
  `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` on Windows, or
  `.venv/bin/python -m unittest discover -s tests -v` on macOS/Linux.
- Setup script: from the root, run `python -m unittest discover -s tests -v`
  (use `python3` on macOS/Linux).
- If `/health/db` fails, check SQL Server availability, the restored database,
  ODBC Driver 18, credentials, and account permissions. If the games screen
  cannot connect, confirm both servers are running and the front-end API URL
  matches the backend.

For route and procedure details, see the [API guide](gamepulse-backend-FastAPI/README.md).
