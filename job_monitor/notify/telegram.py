"""
Push notifications via the Telegram Bot API - free, official, no ToS risk.

Setup (see README): create a bot via @BotFather to get a token, message the
bot once from your account to get your chat id, then set TELEGRAM_BOT_TOKEN
and TELEGRAM_CHAT_ID.
"""
import os
import requests

TIMEOUT = 10
API_BASE = "https://api.telegram.org"


def _bot_token():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set")
    return token


def _chat_id():
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID environment variable is not set")
    return chat_id


def _escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_message(company_name, job, category_label, detected_at_local):
    lines = ["\U0001F6A8 <b>New Job Found</b>", ""]
    lines.append(f"<b>Company:</b> {_escape(company_name)}")
    lines.append(f"<b>Role:</b> {_escape(job['title'])}")
    if job.get("location"):
        lines.append(f"<b>Location:</b> {_escape(job['location'])}")
    if job.get("employment_type"):
        lines.append(f"<b>Type:</b> {_escape(job['employment_type'])}")
    if job.get("experience"):
        lines.append(f"<b>Experience:</b> {_escape(job['experience'])}")
    lines.append(f"<b>Category:</b> {_escape(category_label)}")
    lines.append(f"<b>Detected:</b> {_escape(detected_at_local)}")
    if job.get("source"):
        lines.append(f"<b>Source:</b> {_escape(job['source'])}")
    if job.get("url"):
        lines.append("")
        lines.append(f'<a href="{job["url"]}">Apply here</a>')
    return "\n".join(lines)


def _redact(message, token):
    """Strip the bot token out of an error string before it's logged/persisted -
    request errors (e.g. from raise_for_status) embed the full URL, token included."""
    if token and message:
        message = message.replace(token, "<redacted>")
    return message


def send(company_name, job, category_label, detected_at_local):
    """Send one push notification for a single matching job. Returns (success, error)."""
    text = format_message(company_name, job, category_label, detected_at_local)
    token = None
    try:
        token = _bot_token()
        url = f"{API_BASE}/bot{token}/sendMessage"
        payload = {
            "chat_id": _chat_id(),
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
        try:
            data = resp.json()
        except ValueError:
            data = {}
        if data.get("ok"):
            return True, None
        # Telegram's error responses are valid JSON with a real `description`
        # even on 4xx status - read that before falling back to a generic
        # "N Client Error" message from raise_for_status.
        description = data.get("description")
        if description:
            return False, description
        resp.raise_for_status()
        return False, "unknown Telegram API error"
    except Exception as e:  # noqa: BLE001 - record any failure and keep going
        return False, _redact(str(e), token)
