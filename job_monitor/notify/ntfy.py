"""
Push notifications via ntfy.sh - free, no account required.

Setup (see README): install the ntfy app on your phone, subscribe to a
private/unguessable topic name, and set that same topic as NTFY_TOPIC.
"""
import os
import requests

TIMEOUT = 10
DEFAULT_SERVER = "https://ntfy.sh"


def _server():
    return os.environ.get("NTFY_SERVER", DEFAULT_SERVER).rstrip("/")


def _topic():
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        raise RuntimeError("NTFY_TOPIC environment variable is not set")
    return topic


def format_message(company_name, job, category_label, detected_at_local):
    lines = [f"Company: {company_name}", f"Role: {job['title']}"]
    if job.get("location"):
        lines.append(f"Location: {job['location']}")
    if job.get("employment_type"):
        lines.append(f"Type: {job['employment_type']}")
    if job.get("experience"):
        lines.append(f"Experience: {job['experience']}")
    lines.append(f"Category: {category_label}")
    lines.append(f"Detected: {detected_at_local}")
    if job.get("source"):
        lines.append(f"Source: {job['source']}")
    return "\n".join(lines)


def send(company_name, job, category_label, detected_at_local):
    """Send one push notification for a single matching job. Returns (success, error)."""
    body = format_message(company_name, job, category_label, detected_at_local)
    url = f"{_server()}/{_topic()}"
    headers = {
        "Title": f"New Job: {job['title']} @ {company_name}".encode("utf-8"),
        "Priority": "high",
        "Tags": "briefcase,rotating_light",
    }
    if job.get("url"):
        headers["Click"] = job["url"]

    try:
        resp = requests.post(url, data=body.encode("utf-8"), headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        return True, None
    except Exception as e:  # noqa: BLE001 - we want to record any failure and keep going
        return False, str(e)
