"""Local receiver for Alertmanager webhook notifications."""

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent / "logs" / "alerts.jsonl"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok\n")

    def do_POST(self):
        if self.path != "/alerts":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1_048_576:
                raise ValueError("Invalid payload size")

            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object")

            alerts = payload.get("alerts")
            if not isinstance(alerts, list) or not all(
                isinstance(alert, dict)
                and isinstance(alert.get("labels"), dict)
                for alert in alerts
            ):
                raise ValueError("Expected alerts with labels")
        except (ValueError, UnicodeDecodeError):
            self.send_error(400, "Invalid alert payload")
            return

        record = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }

        try:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record) + "\n")
        except OSError:
            self.send_error(500, "Could not save notification")
            return

        for alert in alerts:
            print(
                record["received_at"],
                alert.get("status", "unknown").upper(),
                alert["labels"].get("alertname", "unknown"),
                alert["labels"].get("job", ""),
                flush=True,
            )

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"received\n")


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8002), Handler)
    print("Alert receiver listening on http://127.0.0.1:8002", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
