"""Public dev-config endpoint — NO X-API-KEY guard (it only exposes a boolean)."""

import os
from flask import Blueprint, jsonify

dev_config_bp = Blueprint("dev_config", __name__)


@dev_config_bp.route("/api/dev/config", methods=["GET"])
def dev_config():
    # Read per request (not at import) so it always reflects the running env.
    return jsonify({"dev_tools": os.getenv("FLASK_ENV") == "development"})
