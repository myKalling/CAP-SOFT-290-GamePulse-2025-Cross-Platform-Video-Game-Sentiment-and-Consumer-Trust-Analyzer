"""Install GamePulse's project dependencies without changing system packages."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def run(command, cwd):
    print(f"\n> {' '.join(str(part) for part in command)}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def copy_environment(directory):
    example = directory / ".env.example"
    destination = directory / ".env"
    try:
        with example.open("rb") as source, destination.open("xb") as target:
            shutil.copyfileobj(source, target)
    except FileExistsError:
        print(f"Keeping existing {destination}", flush=True)
    else:
        print(f"Created {destination}", flush=True)


def install_python(directory):
    environment = directory / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not environment.exists():
        run([sys.executable, "-m", "venv", str(environment)], ROOT)
    elif not python.is_file():
        raise RuntimeError(f"Existing virtual environment is incomplete: {environment}")
    else:
        print(f"Using existing virtual environment: {environment}", flush=True)
    run([str(python), "-c", "import sys; sys.exit(sys.version_info < (3, 11))"], directory)
    requirements = "requirements-dev.txt" if directory.name == "gamepulse-backend-FastAPI" else "requirements.txt"
    run([str(python), "-m", "pip", "install", "-r", requirements], directory)


def preflight():
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11 or newer is required; Python 3.12 is recommended.")

    node = shutil.which("node")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not node or not npm:
        raise RuntimeError("Node.js and npm are required. Install Node.js 24.3+ (24.x) first.")

    version = subprocess.run(
        [node, "-p", "process.versions.node"], check=True, capture_output=True, text=True
    ).stdout.strip()
    major, minor, *_ = (int(part) for part in version.split("."))
    if not ((major == 22 and minor >= 13) or (major == 24 and minor >= 3) or major >= 26):
        raise RuntimeError(f"Unsupported Node.js {version}; use Node.js 24.3+ (24.x).")

    subprocess.run([npm, "--version"], check=True, stdout=subprocess.DEVNULL)
    print(f"Preflight passed: Python {sys.version.split()[0]}, Node.js {version}, and npm.", flush=True)
    return npm


def check_database(backend):
    python = backend / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        raise RuntimeError(
            "The backend virtual environment is missing or incomplete. "
            "Run setup first, configure the backend .env, then retry the database check."
        )
    run([str(python), "check_database.py"], backend)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check prerequisites and install GamePulse dependencies.")
    parser.add_argument("--check-only", action="store_true", help="Check prerequisites without installing or changing files.")
    parser.add_argument(
        "--check-database", action="store_true",
        help="Also check the configured ODBC driver and SQL Server using the existing backend environment.",
    )
    args = parser.parse_args(argv)
    npm = preflight()

    backend = ROOT / "gamepulse-backend-FastAPI"
    frontend = ROOT / "front-end"
    pipeline = ROOT / "AI Development"
    if args.check_database:
        check_database(backend)
    else:
        print("Database check skipped; use --check-only --check-database after backend setup.", flush=True)
    if args.check_only:
        return
    for directory in (backend, frontend, pipeline):
        copy_environment(directory)
    install_python(backend)
    install_python(pipeline)
    run([npm, "ci"], frontend)
    print("\nDependencies installed. Configure SQL Server and API keys as described in README.md.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Setup failed: {error}", file=sys.stderr)
        sys.exit(1)
