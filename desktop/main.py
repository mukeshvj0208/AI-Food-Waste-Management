"""Launch FoodBridge as a desktop application with reliable service readiness."""
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import webview

ROOT = Path(__file__).resolve().parents[1]
API_PORT = 8010
FRONTEND_PORT = 5174


def wait_for(url: str, process: subprocess.Popen, label: str, timeout: int = 45) -> None:
    """Wait for a process's HTTP endpoint, failing clearly if it exits."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{label} stopped during startup (exit code {process.returncode}).")
        try:
            with urlopen(url, timeout=1) as response:
                if 200 <= response.status < 400:
                    return
        except URLError:
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {label} at {url}.")


def run() -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "backend")}
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(API_PORT)],
        cwd=ROOT / "backend",
        env=env,
    )
    frontend = subprocess.Popen(["npm.cmd", "run", "dev"], cwd=ROOT / "frontend")
    try:
        wait_for(f"http://127.0.0.1:{API_PORT}/api/health", api, "FoodBridge API")
        wait_for(f"http://127.0.0.1:{FRONTEND_PORT}", frontend, "FoodBridge frontend")
        webview.create_window(
            "FoodBridge",
            f"http://127.0.0.1:{FRONTEND_PORT}",
            width=1440,
            height=940,
            min_size=(1000, 700),
        )
        webview.start()
    except RuntimeError as error:
        print(f"FoodBridge could not start: {error}")
        raise SystemExit(1)
    finally:
        for process in (frontend, api):
            if process.poll() is None:
                # npm.cmd launches Node as a child process on Windows. Kill the
                # process tree so closing the desktop window never leaves Vite running.
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)


if __name__ == "__main__":
    run()
