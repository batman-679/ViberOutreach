"""
ui/components.py
Reusable helpers for the Streamlit dashboard.

  format_countdown(last_inbound_at)  → (time_str, is_open)
  render_message_bubble(message)     → HTML string
  render_pipeline_card(contact)      → HTML string
"""

from datetime import datetime, timedelta
from typing import Optional
from config.settings import MESSAGING_WINDOW_HOURS


# ─────────────────────────────────────────────────────────────────────────────
# Countdown helper
# ─────────────────────────────────────────────────────────────────────────────

def format_countdown(last_inbound_at: Optional[str]) -> tuple[str, bool]:
    """
    Given the ISO/SQLite timestamp of the last inbound message, return:
      (time_str, is_open)

    time_str : "HH:MM:SS" remaining if open, "CLOSED" if expired or no message
    is_open  : True if the 24-hour messaging window is still active
    """
    if not last_inbound_at:
        return "NO MESSAGES", False

    try:
        last_dt = datetime.fromisoformat(str(last_inbound_at))
    except ValueError:
        return "INVALID DATE", False

    window = timedelta(hours=MESSAGING_WINDOW_HOURS)
    now = datetime.utcnow()
    elapsed = now - last_dt
    remaining = window - elapsed

    if remaining.total_seconds() <= 0:
        return "WINDOW CLOSED", False

    total_secs = int(remaining.total_seconds())
    hours, remainder = divmod(total_secs, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}", True


def _countdown_color(time_str: str, is_open: bool) -> str:
    """Map countdown state to a CSS color."""
    if not is_open:
        return "#e74c3c"  # red
    # Parse remaining hours to pick yellow vs green
    try:
        hours = int(time_str.split(":")[0])
    except (ValueError, IndexError):
        return "#e74c3c"
    if hours < 4:
        return "#f39c12"  # yellow/amber
    return "#2ecc71"  # green


# ─────────────────────────────────────────────────────────────────────────────
# Message bubble renderer
# ─────────────────────────────────────────────────────────────────────────────

def render_message_bubble(message: dict) -> str:
    """
    Return an HTML string for a single message bubble.

    Inbound  → left-aligned, light grey background
    Outbound → right-aligned, blue background
    """
    direction = message.get("direction", "inbound")
    body = message.get("body", "")
    ts = str(message.get("timestamp", ""))[:16]  # "YYYY-MM-DD HH:MM"

    # Escape any HTML in the body to prevent XSS
    body_safe = (
        body.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
    )

    if direction == "inbound":
        container_style = "display:flex; justify-content:flex-start; margin:6px 0;"
        bubble_style = (
            "background:#f0f0f0; color:#111; border-radius:18px 18px 18px 4px; "
            "padding:10px 14px; max-width:70%; font-size:14px; line-height:1.5;"
        )
    else:
        container_style = "display:flex; justify-content:flex-end; margin:6px 0;"
        bubble_style = (
            "background:#0084ff; color:#fff; border-radius:18px 18px 4px 18px; "
            "padding:10px 14px; max-width:70%; font-size:14px; line-height:1.5;"
        )

    ts_style = "font-size:10px; opacity:0.55; display:block; margin-top:4px;"

    return f"""
    <div style="{container_style}">
      <div style="{bubble_style}">
        {body_safe}
        <span style="{ts_style}">{ts}</span>
      </div>
    </div>
    """


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline card renderer
# ─────────────────────────────────────────────────────────────────────────────

def render_pipeline_card(contact: dict) -> str:
    """
    Return an HTML string for a Kanban card showing:
      - Display name (ig_username or IGSID fallback)
      - Live countdown chip
    """
    name = contact.get("ig_username") or contact.get("igsid", "Unknown")
    time_str, is_open = format_countdown(contact.get("last_inbound_at"))
    chip_color = _countdown_color(time_str, is_open)

    card_style = (
        "background:#1e1e2e; border:1px solid #333; border-radius:10px; "
        "padding:10px 12px; margin-bottom:8px;"
    )
    name_style = "font-weight:600; font-size:13px; color:#e0e0e0; margin-bottom:6px;"
    chip_style = (
        f"display:inline-block; background:{chip_color}22; color:{chip_color}; "
        "border:1px solid; border-radius:12px; padding:2px 8px; font-size:11px;"
        "font-family:monospace;"
    )

    return f"""
    <div style="{card_style}">
      <div style="{name_style}">{name}</div>
      <span style="{chip_style}">{time_str}</span>
    </div>
    """
