"""
webhook/listener.py
FastAPI application that handles Meta Webhook events for Instagram.

Routes
------
GET  /webhook  — Meta hub verification (returns hub.challenge)
POST /webhook  — Receives real-time push events (messages, echoes, postbacks)
GET  /         — Health check
"""

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse

from config.settings import VERIFY_TOKEN
from core.database import init_db, upsert_contact, save_message

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("webhook")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Instagram CRM Webhook Listener")


@app.on_event("startup")
def on_startup():
    """Initialise the database schema when Uvicorn starts."""
    init_db()
    log.info("Database initialised. Webhook listener ready.")


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=PlainTextResponse)
async def health():
    return "OK"


# ─────────────────────────────────────────────────────────────────────────────
# GET /webhook — Meta hub verification
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Meta sends a GET request with hub.mode=subscribe when you save the webhook
    URL on the developer dashboard.  We must echo hub.challenge as a plain
    integer to confirm ownership of the endpoint.
    """
    if mode == "subscribe" and token == VERIFY_TOKEN:
        log.info("Webhook verified successfully.")
        # Return the challenge as a plain integer string (Meta requirement)
        return PlainTextResponse(content=challenge, status_code=200)

    log.warning("Webhook verification failed — token mismatch or wrong mode.")
    raise HTTPException(status_code=403, detail="Verification failed")


# ─────────────────────────────────────────────────────────────────────────────
# POST /webhook — Real-time event receiver
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/webhook")
async def receive_webhook(request: Request):
    """
    Processes incoming Meta push events.

    Supported messaging fields:
      - messages        → inbound message from user
      - message_echoes  → outbound message sent via IG app (not from our API)
      - messaging_postbacks → button taps stored as inbound text
    """
    try:
        body: dict = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if body.get("object") != "instagram":
        # Not an Instagram event; silently acknowledge
        return {"status": "ignored"}

    for entry in body.get("entry", []):
        for messaging_event in entry.get("messaging", []):
            _process_messaging_event(messaging_event)

    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# Internal event routing
# ─────────────────────────────────────────────────────────────────────────────

def _process_messaging_event(event: dict) -> None:
    """Route a single messaging event to the appropriate handler."""
    if "message" in event:
        is_echo = event["message"].get("is_echo", False)
        if is_echo:
            _handle_echo(event)
        else:
            _handle_inbound(event)
    elif "postback" in event:
        _handle_postback(event)


def _handle_inbound(event: dict) -> None:
    """
    Inbound message FROM a user TO our account.
    - upsert contact using sender IGSID
    - save message with direction='inbound'
    - update last_inbound_at (done inside save_message)
    """
    sender_igsid: str = event.get("sender", {}).get("id", "")
    if not sender_igsid:
        log.warning("Inbound event missing sender.id — skipping.")
        return

    message: dict = event.get("message", {})
    mid: str = message.get("mid", "")
    text: str = message.get("text", "")
    raw_ts: int = event.get("timestamp", 0)

    if not text:
        # Sticker / attachment only — store placeholder
        text = "[non-text content]"

    ts = _ts_to_datetime(raw_ts)
    contact_id = upsert_contact(sender_igsid)
    inserted = save_message(contact_id, mid, "inbound", text, ts)

    if inserted:
        log.info("Saved inbound message mid=%s from igsid=%s", mid, sender_igsid)
    else:
        log.debug("Duplicate inbound mid=%s — ignored.", mid)


def _handle_echo(event: dict) -> None:
    """
    Message echo: we sent a reply via the Instagram app (not via our API).
    - uses recipient IGSID (the person we replied to) as the contact key
    - direction='outbound'
    - does NOT update last_inbound_at
    """
    # For echoes the contact is the *recipient*, not the sender
    recipient_igsid: str = event.get("recipient", {}).get("id", "")
    if not recipient_igsid:
        log.warning("Echo event missing recipient.id — skipping.")
        return

    message: dict = event.get("message", {})
    mid: str = message.get("mid", "")
    text: str = message.get("text", "")
    raw_ts: int = event.get("timestamp", 0)

    if not text:
        text = "[non-text content]"

    ts = _ts_to_datetime(raw_ts)
    contact_id = upsert_contact(recipient_igsid)
    inserted = save_message(contact_id, mid, "outbound", text, ts)

    if inserted:
        log.info("Saved outbound echo mid=%s to igsid=%s", mid, recipient_igsid)
    else:
        log.debug("Duplicate echo mid=%s — ignored.", mid)


def _handle_postback(event: dict) -> None:
    """
    Button tap / postback — store as an inbound message with the payload text.
    """
    sender_igsid: str = event.get("sender", {}).get("id", "")
    postback: dict = event.get("postback", {})
    payload_text: str = postback.get("title") or postback.get("payload", "[postback]")
    raw_ts: int = event.get("timestamp", 0)
    ts = _ts_to_datetime(raw_ts)

    contact_id = upsert_contact(sender_igsid)
    save_message(contact_id, None, "inbound", f"[Button] {payload_text}", ts)
    log.info("Saved postback from igsid=%s: %s", sender_igsid, payload_text)


# ─────────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────────

def _ts_to_datetime(ms_timestamp: int) -> datetime:
    """Convert Meta's millisecond Unix timestamp to a UTC datetime."""
    if ms_timestamp:
        return datetime.fromtimestamp(ms_timestamp / 1000, tz=timezone.utc).replace(
            tzinfo=None
        )
    return datetime.utcnow()
