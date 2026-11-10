import json
import logging
from datetime import datetime, timezone

from flask import g, request


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            payload["requestId"] = record.request_id
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(app):
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    @app.after_request
    def access_log(response):
        app.logger.info(
            "%s %s -> %s",
            request.method,
            request.path,
            response.status_code,
            extra={"request_id": getattr(g, "request_id", None)},
        )
        return response
