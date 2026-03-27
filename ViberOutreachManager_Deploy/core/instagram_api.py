"""
core/instagram_api.py
Thin wrapper around the Meta Graph API for sending Instagram DMs.

Single public function: send_message(igsid, text)
"""

import requests
from config.settings import ACCESS_TOKEN, IG_ACCOUNT_ID

_GRAPH_BASE = "https://graph.facebook.com/v19.0"


def send_message(igsid: str, text: str) -> tuple[bool, dict]:
    """
    Send a text message to an Instagram user identified by their IGSID.

    Parameters
    ----------
    igsid : str
        The Instagram Scoped User ID of the recipient.
    text : str
        The message body (max 1 000 characters for IG Messenger API).

    Returns
    -------
    (success, response_json)
        success      : True when the API returns 2xx
        response_json: The parsed JSON body from Meta's response
    """
    if not ACCESS_TOKEN or not IG_ACCOUNT_ID:
        raise RuntimeError(
            "META_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID must be set in .env "
            "before sending messages."
        )

    url = f"{_GRAPH_BASE}/{IG_ACCOUNT_ID}/messages"
    payload = {
        "recipient": {"id": igsid},
        "message": {"text": text},
        "messaging_type": "RESPONSE",
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Network error contacting Meta API: {exc}") from exc

    response_json: dict = {}
    try:
        response_json = resp.json()
    except ValueError:
        response_json = {"raw": resp.text}

    if resp.status_code >= 400:
        error_msg = response_json.get("error", {}).get("message", resp.text)
        raise RuntimeError(
            f"Meta API returned {resp.status_code}: {error_msg}"
        )

    return True, response_json
