"""Install GamePulse's project dependencies without changing system packages."""

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


def main():
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11 or newer is required; Python 3.12 is recommended.")

    node = shutil.which("node")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not node or not npm:
        raise RuntimeError("Node.js and npm are required. Install a supported Node.js version first.")

    version = subprocess.run(
        [node, "-p", "process.versions.node"], check=True, capture_output=True, text=True
    ).stdout.strip()
    major, minor, *_ = (int(part) for part in version.split("."))
    if not ((major == 22 and minor >= 13) or (major == 24 and minor >= 3) or major >= 26):
        raise RuntimeError(f"Unsupported Node.js {version}; use Node.js 24.3+ (24.x).")

    backend = ROOT / "gamepulse-backend-FastAPI"
    frontend = ROOT / "front-end"
    pipeline = ROOT / "AI Development"
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
