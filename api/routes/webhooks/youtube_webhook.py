"""YouTube WebSub (PubSubHubbub) webhook — NO X-API-KEY guard."""

import os
import logging
from xml.etree import ElementTree

from flask import Blueprint, request, Response
from dotenv import load_dotenv

from ...services.blog_service import BlogService

load_dotenv()
logger = logging.getLogger(__name__)

WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "")

youtube_webhook_bp = Blueprint("youtube_webhook", __name__)


@youtube_webhook_bp.route("/api/webhooks/youtube", methods=["GET"])
def youtube_challenge():
    """WebSub subscription verification challenge."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge", "")

    if mode in ("subscribe", "unsubscribe") and token == WEBHOOK_VERIFY_TOKEN:
        logger.info("YouTube WebSub challenge accepted, mode=%s", mode)
        return Response(challenge, status=200, mimetype="text/plain")

    logger.warning("YouTube WebSub challenge failed: mode=%s, token=%s", mode, token)
    return Response("Forbidden", status=403)


@youtube_webhook_bp.route("/api/webhooks/youtube", methods=["POST"])
def youtube_notify():
    """Handle YouTube push notification (Atom XML feed)."""
    try:
        body = request.data
        # YouTube sends Atom XML
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }
        root = ElementTree.fromstring(body)

        # Find the yt:videoId element
        video_id_el = root.find(".//yt:videoId", ns)
        if video_id_el is None:
            logger.warning("YouTube webhook: no yt:videoId found in payload")
            return Response("OK", status=200)

        video_id = video_id_el.text.strip()
        logger.info("YouTube webhook: received video_id=%s", video_id)

        post_id, err = BlogService.generate_from_youtube(video_id)
        if err:
            logger.warning("generate_from_youtube(%s) error: %s", video_id, err)
        else:
            logger.info("Draft blog post created: id=%s for video=%s", post_id, video_id)

    except Exception as e:
        # Always return 200 so YouTube hub doesn't retry with backoff
        logger.error("YouTube webhook handler exception: %s", e)

    return Response("OK", status=200)
