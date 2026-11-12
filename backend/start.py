#!/usr/bin/env python3
"""Safe local backend startup. Dependencies must be installed beforehand."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main() -> None:
    if not (ROOT / ".env").is_file():
        raise SystemExit(
            "Missing backend/.env. Copy backend/env.example to .env, "
            "replace every secret placeholder, then retry."
        )
    print("Applying Alembic migrations (no test data will be seeded)...")
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                   cwd=ROOT, check=True)
    subprocess.run([sys.executable, "create_admin.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app",
                    "--host", "127.0.0.1", "--port", "8039", "--reload", "--no-proxy-headers"],
                   cwd=ROOT, check=True)

if __name__ == "__main__":
    main()
