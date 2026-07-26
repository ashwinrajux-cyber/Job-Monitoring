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
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set")
    return token


def _chat_id():
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
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


def send(company_name, job, category_label, detected_at_local):
    """Send one push notification for a single matching job. Returns (success, error)."""
    text = format_message(company_name, job, category_label, detected_at_local)
    try:
        url = f"{API_BASE}/bot{_bot_token()}/sendMessage"
        payload = {
            "chat_id": _chat_id(),
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            return False, data.get("description", "unknown Telegram API error")
        return True, None
    except Exception as e:  # noqa: BLE001 - record any failure and keep going
        return False, str(e)
