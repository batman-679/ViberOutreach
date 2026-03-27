"""
config/settings.py
Loads environment variables from .env and exposes typed constants to the rest
of the application.  Import this module wherever you need credentials or paths.
"""
from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env from the project root (one level up from this file)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

# ── Meta credentials ──────────────────────────────────────────────────────────
VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN", "")
ACCESS_TOKEN: str = os.getenv("META_ACCESS_TOKEN", "")
IG_ACCOUNT_ID: str = os.getenv("INSTAGRAM_ACCOUNT_ID", "")

# ── Database ──────────────────────────────────────────────────────────────────
# Resolve relative to the project root so both the FastAPI process and the
# Streamlit process point to the same file regardless of their cwd.
_project_root = Path(__file__).resolve().parent.parent
DB_PATH: str = str(_project_root / "instagram_crm.db")

# ── Messaging rules ───────────────────────────────────────────────────────────
MESSAGING_WINDOW_HOURS: int = 24
