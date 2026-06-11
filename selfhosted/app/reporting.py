# reporting.py - optional: push call events to the dashboard's ingest endpoint.
# No-op unless DASHBOARD_INGEST_URL is set. Failures never break a call.
import os

import urllib.request
import json

INGEST_URL = os.getenv("DASHBOARD_INGEST_URL", "")
INGEST_TOKEN = os.getenv("INGEST_TOKEN", "")


def _post(payload: dict):
    if not INGEST_URL:
        return
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            INGEST_URL,
            data=data,
            headers={"Content-Type": "application/json", "X-Ingest-Token": INGEST_TOKEN},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=3).read()
    except Exception as e:
        print("⚠️  dashboard report failed:", repr(e))


def call_started(call_uuid: str, caller: str = None):
    _post({"type": "call_started", "call_uuid": call_uuid, "caller": caller})


def message(call_uuid: str, role: str, text: str, language: str = None):
    _post({"type": "message", "call_uuid": call_uuid, "role": role, "text": text, "language": language})


def call_ended(call_uuid: str, status: str = "completed", duration_seconds: int = 0):
    _post({
        "type": "call_ended",
        "call_uuid": call_uuid,
        "status": status,
        "duration_seconds": duration_seconds,
    })
