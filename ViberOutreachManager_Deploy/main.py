"""
main.py
Application launcher for the Instagram Graph API CRM.

Starts two processes side-by-side:
  1. Uvicorn (FastAPI webhook listener) on port 8000 — background thread
  2. Streamlit dashboard on port 8501 — foreground subprocess

Usage:
    python main.py

Stop with Ctrl+C.
"""

import subprocess
import sys
import threading
import time
import os
import signal

import uvicorn

# ── Project root on path (so imports in ui/ and webhook/ work correctly) ──────
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ─────────────────────────────────────────────────────────────────────────────
# Startup banner
# ─────────────────────────────────────────────────────────────────────────────

BANNER = r"""
╔════════════════════════════════════════════════════════╗
║        📸  Instagram Graph API CRM  ─  Starting…       ║
╠════════════════════════════════════════════════════════╣
║  Webhook listener  →  http://localhost:8000/webhook    ║
║  Streamlit UI      →  http://localhost:8501            ║
╠════════════════════════════════════════════════════════╣
║  Ngrok setup (run in a second terminal):               ║
║    ngrok http 8000                                     ║
║  Then paste the Ngrok HTTPS URL into the Meta          ║
║  App Dashboard → Webhooks → Callback URL.              ║
╚════════════════════════════════════════════════════════╝
"""


# ─────────────────────────────────────────────────────────────────────────────
# Uvicorn thread
# ─────────────────────────────────────────────────────────────────────────────

def _run_uvicorn() -> None:
    """Run the FastAPI app inside a background daemon thread."""
    uvicorn.run(
        "webhook.listener:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        # Reload disabled intentionally — we want a stable server in production
        reload=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print(BANNER)

    # ── 1. Start Uvicorn in a background daemon thread ────────────────────────
    uvicorn_thread = threading.Thread(target=_run_uvicorn, daemon=True, name="uvicorn")
    uvicorn_thread.start()
    print("[launcher] Uvicorn thread started.")

    # Give Uvicorn a moment to bind the port before Streamlit opens
    time.sleep(1.5)

    # ── 2. Start Streamlit as a subprocess (foreground) ───────────────────────
    streamlit_cmd = [
        sys.executable, "-m", "streamlit", "run",
        os.path.join(_project_root, "ui", "app.py"),
        "--server.port", "8501",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]

    print("[launcher] Starting Streamlit…")
    try:
        streamlit_proc = subprocess.Popen(
            streamlit_cmd,
            cwd=_project_root,
        )
        # Block main thread until Streamlit exits (or user hits Ctrl+C)
        streamlit_proc.wait()
    except KeyboardInterrupt:
        print("\n[launcher] Shutdown requested — stopping Streamlit…")
        streamlit_proc.terminate()
        streamlit_proc.wait()
        print("[launcher] Stopped. Bye!")
    except FileNotFoundError:
        print("[launcher] ERROR: streamlit not found. Run:  pip install streamlit")
        sys.exit(1)


if __name__ == "__main__":
    main()
