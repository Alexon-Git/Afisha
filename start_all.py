#!/usr/bin/env python3
"""Launch frontend and backend without modifying the process working directory."""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main() -> None:
    backend = ROOT / "backend"
    frontend = ROOT / "frontend"
    if not backend.is_dir() or not frontend.is_dir():
        raise SystemExit("Missing backend/ or frontend/ directory.")
    print("Start backend with Alembic migrations and frontend in development mode.")
    print("Set backend/.env and install Python/npm dependencies first.")
    processes = []
    try:
        processes.append(subprocess.Popen([sys.executable, "start.py"], cwd=backend))
        processes.append(subprocess.Popen(["npm", "start"], cwd=frontend))
        while all(proc.poll() is None for proc in processes):
            time.sleep(0.5)
        for proc in processes:
            if proc.returncode is not None and proc.returncode != 0:
                raise SystemExit(f"Development process exited: {proc.returncode}")
    except KeyboardInterrupt:
        print("Stopping development servers.")
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

if __name__ == "__main__":
    main()
