#!/usr/bin/env python3
"""
run.py — Single-command launcher for Drug Safety Signal Detector
Usage:  python run.py          # start both backend and frontend
        python run.py --stop   # kill any running instances on the used ports
        python run.py --check  # verify environment without starting

Works on Windows, macOS, and Linux. No extra dependencies beyond what is
already in src/requirements.txt (uses only stdlib: subprocess, os, sys,
pathlib, time, signal, threading, argparse, shutil).

Auto-venv: if a .venv exists in the repo root and the current interpreter is
NOT inside it, this script re-launches itself using the venv's Python
automatically — no manual activation needed.
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Auto-venv bootstrap  (must run before any other imports)
# ---------------------------------------------------------------------------
def _bootstrap_venv():
    """Re-launch inside .venv if we are not already running from it."""
    repo_root = Path(__file__).resolve().parent
    # Already inside a venv — nothing to do
    if sys.prefix != sys.base_prefix:
        return

    # Find venv Python
    candidates = [
        repo_root / ".venv" / "Scripts" / "python.exe",  # Windows
        repo_root / ".venv" / "bin"     / "python3",     # Unix
        repo_root / ".venv" / "bin"     / "python",      # Unix fallback
        repo_root / "venv"  / "Scripts" / "python.exe",
        repo_root / "venv"  / "bin"     / "python3",
        repo_root / "venv"  / "bin"     / "python",
    ]
    venv_python = next((str(c) for c in candidates if c.exists()), None)
    if venv_python is None:
        # No venv found — continue with system Python and warn later
        return

    # Re-exec this script inside the venv
    import subprocess
    result = subprocess.run([venv_python] + sys.argv)
    sys.exit(result.returncode)

_bootstrap_venv()

# ---------------------------------------------------------------------------
# Normal imports (safe after bootstrap)
# ---------------------------------------------------------------------------
import argparse
import shutil
import signal
import subprocess
import time
import threading

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REPO_ROOT   = Path(__file__).resolve().parent
SRC_DIR     = REPO_ROOT / "src"
ENV_FILE    = SRC_DIR / ".env"
ENV_EXAMPLE = SRC_DIR / ".env.example"
BACKEND_PORT  = 8000
FRONTEND_PORT = 8501

# Colours (disabled on Windows unless ANSICON / WT is detected)
USE_COLOUR = sys.platform != "win32" or os.environ.get("WT_SESSION")
def _c(code, text): return f"\033[{code}m{text}\033[0m" if USE_COLOUR else text
GREEN  = lambda t: _c("32;1", t)
YELLOW = lambda t: _c("33;1", t)
RED    = lambda t: _c("31;1", t)
CYAN   = lambda t: _c("36;1", t)
BOLD   = lambda t: _c("1",    t)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def banner():
    print()
    print(BOLD("=" * 60))
    print(BOLD("  Drug Safety Signal Detector & Submission Readiness Checker"))
    print(BOLD("=" * 60))
    print()


def find_python():
    """Return the Python executable for the active venv, or sys.executable."""
    # If already inside a venv, use it directly
    if sys.prefix != sys.base_prefix:
        return sys.executable
    # Try common venv locations relative to repo root
    for candidate in [
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",  # Windows
        REPO_ROOT / ".venv" / "bin"     / "python",      # Unix
        REPO_ROOT / "venv"  / "Scripts" / "python.exe",
        REPO_ROOT / "venv"  / "bin"     / "python",
    ]:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def find_executable(name):
    """Find an executable in the active venv or PATH."""
    python = find_python()
    venv_bin = Path(python).parent
    for stem in [name, name + ".exe", name + ".cmd"]:
        candidate = venv_bin / stem
        if candidate.exists():
            return str(candidate)
    return shutil.which(name)


def check_env():
    """Return list of warning strings about missing env/setup."""
    warnings = []
    if not ENV_FILE.exists():
        warnings.append(
            f".env file not found at {ENV_FILE}\n"
            f"  → Run:  cp src/.env.example src/.env   then fill in your credentials"
        )
    else:
        content = ENV_FILE.read_text()
        for var in ("WATSONX_API_KEY", "WATSONX_PROJECT_ID", "WATSONX_URL"):
            if f"{var}=your_" in content or f"{var}=" not in content:
                warnings.append(
                    f"{var} not set in src/.env\n"
                    f"  → LLM features will return stub responses until this is filled in"
                )
                break  # one warning is enough
    req = SRC_DIR / "requirements.txt"
    if not req.exists():
        warnings.append("src/requirements.txt not found — run: pip install -r src/requirements.txt")
    return warnings


def port_is_free(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) != 0


def wait_for_port(port, timeout=30):
    """Block until *port* accepts connections, or timeout."""
    import socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def kill_port(port):
    """Best-effort: kill whatever is listening on *port*."""
    if sys.platform == "win32":
        result = subprocess.run(
            f"for /f \"tokens=5\" %a in ('netstat -aon ^| find \":{port}\"') do taskkill /F /PID %a",
            shell=True, capture_output=True, text=True
        )
    else:
        result = subprocess.run(
            f"lsof -ti:{port} | xargs kill -9 2>/dev/null || true",
            shell=True, capture_output=True
        )
    return result.returncode == 0


def stream_output(proc, prefix, colour_fn):
    """Thread target: forward subprocess stdout/stderr with a coloured prefix."""
    try:
        for line in iter(proc.stdout.readline, b""):
            text = line.decode(errors="replace").rstrip()
            if text:
                print(colour_fn(f"[{prefix}] ") + text)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def action_check():
    banner()
    print(BOLD("Environment check"))
    print()

    # Venv
    in_venv = sys.prefix != sys.base_prefix
    venv_label = GREEN(f"active ({sys.prefix})") if in_venv else YELLOW("NOT active — run: source .venv/bin/activate  (or .venv\\Scripts\\Activate.ps1 on Windows)")
    print(f"  venv       : {venv_label}")

    python = find_python()
    print(f"  Python     : {python}")

    uvicorn_bin = find_executable("uvicorn")
    streamlit_bin = find_executable("streamlit")
    no_dep_msg = RED("NOT FOUND") + " — with venv active run: pip install -r src/requirements.txt"
    print(f"  uvicorn    : {uvicorn_bin or no_dep_msg}")
    print(f"  streamlit  : {streamlit_bin or no_dep_msg}")
    print(f"  .env file  : {GREEN(str(ENV_FILE)) if ENV_FILE.exists() else RED('MISSING') + ' — run: cp src/.env.example src/.env'}")
    print(f"  Backend port {BACKEND_PORT}  : {GREEN('free') if port_is_free(BACKEND_PORT) else YELLOW('IN USE')}")
    print(f"  Frontend port {FRONTEND_PORT}: {GREEN('free') if port_is_free(FRONTEND_PORT) else YELLOW('IN USE')}")
    print()

    warnings = check_env()
    if warnings:
        print(YELLOW("Warnings:"))
        for w in warnings:
            print(f"  ⚠  {w}")
        print()
    else:
        print(GREEN("✅  Everything looks good — ready to run."))
    print()


def action_stop():
    banner()
    print(BOLD("Stopping running instances..."))
    for port, name in [(BACKEND_PORT, "backend"), (FRONTEND_PORT, "frontend")]:
        if port_is_free(port):
            print(f"  {name} (:{port}) — {CYAN('not running')}")
        else:
            print(f"  {name} (:{port}) — {YELLOW('killing...')} ", end="", flush=True)
            kill_port(port)
            time.sleep(0.5)
            if port_is_free(port):
                print(GREEN("stopped"))
            else:
                print(RED("could not stop — kill manually"))
    print()


def action_start(open_browser=True):
    banner()

    # ------------------------------------------------------------------
    # Venv status notice
    # ------------------------------------------------------------------
    if sys.prefix == sys.base_prefix:
        print(YELLOW("⚠  Running outside a virtual environment (system Python)."))
        print(YELLOW("   If you see import errors, create and activate a venv first:"))
        print(YELLOW("     python -m venv .venv"))
        print(YELLOW("     source .venv/bin/activate   # macOS/Linux"))
        print(YELLOW("     .venv\\Scripts\\Activate.ps1  # Windows PowerShell"))
        print(YELLOW("     pip install -r src/requirements.txt"))
        print()
    else:
        print(CYAN(f"  venv active: {sys.prefix}"))
        print()

    # ------------------------------------------------------------------
    # Pre-flight
    # ------------------------------------------------------------------
    warnings = check_env()
    for w in warnings:
        print(YELLOW(f"⚠  {w}"))
    if warnings:
        print()

    uvicorn_bin  = find_executable("uvicorn")
    streamlit_bin = find_executable("streamlit")
    if not uvicorn_bin:
        print(RED("ERROR: uvicorn not found."))
        print(RED("  Fix: activate your venv, then run:"))
        print(RED("       pip install -r src/requirements.txt"))
        sys.exit(1)
    if not streamlit_bin:
        print(RED("ERROR: streamlit not found."))
        print(RED("  Fix: activate your venv, then run:"))
        print(RED("       pip install -r src/requirements.txt"))
        sys.exit(1)

    # Check ports
    for port, name in [(BACKEND_PORT, "backend"), (FRONTEND_PORT, "frontend")]:
        if not port_is_free(port):
            print(YELLOW(f"Port {port} ({name}) is already in use."))
            ans = input(f"  Kill existing process on :{port}? [y/N] ").strip().lower()
            if ans == "y":
                kill_port(port)
                time.sleep(0.8)
            else:
                print(RED("Aborting. Free the port and try again."))
                sys.exit(1)

    # ------------------------------------------------------------------
    # Start backend
    # ------------------------------------------------------------------
    print(BOLD("Starting backend  (FastAPI)..."))
    env = {**os.environ, "PYTHONPATH": str(SRC_DIR)}
    if ENV_FILE.exists():
        # Load .env vars into the subprocess environment
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip()

    backend_cmd = [
        uvicorn_bin,
        "backend.main:app",
        "--host", "0.0.0.0",
        "--port", str(BACKEND_PORT),
        "--reload",
    ]
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=str(SRC_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    threading.Thread(
        target=stream_output,
        args=(backend_proc, "API", CYAN),
        daemon=True,
    ).start()

    print(f"  Waiting for backend on :{BACKEND_PORT}...", end="", flush=True)
    if wait_for_port(BACKEND_PORT, timeout=30):
        print(GREEN(" ready"))
    else:
        print(RED(" timed out — check output above"))
        backend_proc.terminate()
        sys.exit(1)

    # ------------------------------------------------------------------
    # Start frontend
    # ------------------------------------------------------------------
    print(BOLD("Starting frontend (Streamlit)..."))
    frontend_cmd = [
        streamlit_bin,
        "run",
        "frontend/app.py",
        "--server.port", str(FRONTEND_PORT),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=str(SRC_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    threading.Thread(
        target=stream_output,
        args=(frontend_proc, "UI ", GREEN),
        daemon=True,
    ).start()

    print(f"  Waiting for frontend on :{FRONTEND_PORT}...", end="", flush=True)
    if wait_for_port(FRONTEND_PORT, timeout=30):
        print(GREEN(" ready"))
    else:
        print(RED(" timed out — check output above"))
        backend_proc.terminate()
        frontend_proc.terminate()
        sys.exit(1)

    # ------------------------------------------------------------------
    # Open browser
    # ------------------------------------------------------------------
    if open_browser:
        import webbrowser
        time.sleep(0.5)
        webbrowser.open(f"http://localhost:{FRONTEND_PORT}")

    # ------------------------------------------------------------------
    # Running — wait for Ctrl+C
    # ------------------------------------------------------------------
    print()
    print(BOLD("=" * 60))
    print(GREEN("  ✅  App is running!"))
    print()
    print(f"  🌐  UI       →  http://localhost:{FRONTEND_PORT}")
    print(f"  📡  API      →  http://localhost:{BACKEND_PORT}")
    print(f"  📖  Swagger  →  http://localhost:{BACKEND_PORT}/docs")
    print()
    print("  Press  Ctrl+C  to stop both servers")
    print(BOLD("=" * 60))
    print()

    def _shutdown(signum=None, frame=None):
        print()
        print(BOLD("Shutting down..."))
        frontend_proc.terminate()
        backend_proc.terminate()
        try:
            frontend_proc.wait(timeout=5)
            backend_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            frontend_proc.kill()
            backend_proc.kill()
        print(GREEN("Stopped. Goodbye."))
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Keep main thread alive; exit if either child dies unexpectedly
    while True:
        if backend_proc.poll() is not None:
            print(RED("\n[API] Backend exited unexpectedly."))
            _shutdown()
        if frontend_proc.poll() is not None:
            print(RED("\n[UI ] Frontend exited unexpectedly."))
            _shutdown()
        time.sleep(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Launch the Drug Safety Signal Detector application.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py              Start both servers and open browser
  python run.py --no-browser Start both servers, skip auto browser-open
  python run.py --check      Check environment without starting
  python run.py --stop       Kill any running instances on ports 8000/8501
        """,
    )
    parser.add_argument("--check",      action="store_true", help="Check environment only, do not start")
    parser.add_argument("--stop",       action="store_true", help="Stop running instances and exit")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_args()

    if args.check:
        action_check()
    elif args.stop:
        action_stop()
    else:
        action_start(open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
