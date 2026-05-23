"""Renew the YouTube WebSub (PubSubHubbub) subscription.

Run daily via cron to keep the push subscription alive.
Lease is set to 10 days (864000 seconds) — YouTube's practical maximum.

Example cron (runs every day at 8am UTC):
    0 8 * * * /path/to/venv/bin/python /path/to/jobs/renew_websub.py >> /var/log/renew_websub.log 2>&1
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "")
WEBHOOK_CALLBACK_URL = os.getenv(
    "WEBHOOK_CALLBACK_URL",
    "https://www.getstam.com/api/webhooks/youtube",
)

if not YOUTUBE_CHANNEL_ID:
    raise SystemExit("YOUTUBE_CHANNEL_ID is not set")

topic = f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={YOUTUBE_CHANNEL_ID}"

resp = requests.post(
    "https://pubsubhubbub.appspot.com/subscribe",
    data={
        "hub.callback": WEBHOOK_CALLBACK_URL,
        "hub.mode": "subscribe",
        "hub.topic": topic,
        "hub.verify_token": WEBHOOK_VERIFY_TOKEN,
        "hub.lease_seconds": "864000",  # 10 days
    },
    timeout=10,
)

if resp.status_code in (200, 202, 204):
    print(f"WebSub renewed OK (hub status {resp.status_code})")
else:
    print(f"WebSub renewal FAILED: {resp.status_code} — {resp.text[:300]}")
    raise SystemExit(1)
