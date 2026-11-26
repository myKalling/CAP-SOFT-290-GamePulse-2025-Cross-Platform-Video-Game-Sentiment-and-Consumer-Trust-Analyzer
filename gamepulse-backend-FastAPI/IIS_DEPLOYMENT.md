# IIS deployment for GamePulse FastAPI

IIS serves as a reverse proxy; FastAPI itself runs as a separate Uvicorn process bound only to `127.0.0.1:8000`.

## Prerequisites

Run this on Windows with the IIS Web Server role enabled. Enable IIS Management
Tools as well if you plan to configure the production hostname or HTTPS through
IIS Manager. `setup-iis.ps1` requires an elevated PowerShell session and does
not install or enable Windows/IIS features.

Install Microsoft IIS URL Rewrite 2.1 first, then Application Request Routing
(ARR) 3.0 (x64). ARR depends on URL Rewrite:

- [URL Rewrite 2.1](https://www.iis.net/downloads/microsoft/url-rewrite)
- [Application Request Routing 3.0](https://www.iis.net/downloads/microsoft/application-request-routing)

Python 3.10 or newer, the Microsoft ODBC Driver 18 for SQL Server, and an
accessible GamePulse database are also required. See the [backend setup
guide](README.md) and [root requirements](../README.md#requirements) for API
dependencies and database configuration.

## Prepare the API

From this directory in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` for the SQL Server connection. With the default Windows integrated authentication, the Windows account that runs Uvicorn must be allowed to connect to the GamePulse database. The current-user `.env` does not provide secrets by default.

## Configure IIS

Open an elevated PowerShell window, change to this directory, and run:

```powershell
.\setup-iis.ps1
```

The script enables ARR proxying and creates a dedicated IIS site named `GamePulseApi` bound to `127.0.0.1:8080`, using a no-managed-code application pool. It stops with an error if that site already exists. The site uses the included `web.config` to forward requests to Uvicorn.

For a local smoke check, start the backend in a separate PowerShell window:

```powershell
.\run-api.ps1
```

Then open `http://127.0.0.1:8080/` and `http://127.0.0.1:8080/docs`. The backend must remain running. `run-api.ps1` is a foreground launch helper, not a Windows service. For production, run Uvicorn under a dedicated Windows service account/service manager with only the database permissions it needs; that account must also be able to read `.env` and the virtual environment. Configure the production hostname and HTTPS certificate in IIS Manager before exposing the site externally; the script intentionally binds only HTTP on port 8080 for local verification.