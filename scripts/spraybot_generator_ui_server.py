"""Local server for the interactive Spraybot workpiece generator.

Run from the repository root with:
    uv run python scripts/spraybot_generator_ui_server.py
"""

import json
import os
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "scripts" / "spraybot-generator-ui" / "index.html"
WORKER = Path(__file__).with_name("spraybot_generator_ui_worker.py")
os.environ.setdefault("PYTHONPATH", str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src"))

from infinigen2.workpieces import CATEGORY_IDS as WORKPIECE_IDS  # noqa: E402
from infinigen2.objects.spraybot import CATEGORY_IDS as SPRAYBOT_IDS  # noqa: E402


GENERATORS = [
    *({"id": f"workpiece:{item}", "label": item, "group": "Workpieces"} for item in WORKPIECE_IDS),
    *({"id": f"spraybot:{item}", "label": item, "group": "Spraybot"} for item in SPRAYBOT_IDS),
]
ALLOWED = {item["id"] for item in GENERATORS}


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type="application/json; charset=utf-8"):
        encoded = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ("/", "/generator"):
            self.respond(200, UI.read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/generators":
            self.respond(200, json.dumps(GENERATORS))
        else:
            self.respond(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if self.path != "/api/generate":
            self.respond(404, json.dumps({"error": "not found"}))
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(size))
            generator = str(request["generator"])
            seed = int(request.get("seed", 0))
            if generator not in ALLOWED or seed < 0 or seed > 2**31 - 1:
                raise ValueError("unknown generator or seed outside 32-bit range")
            with tempfile.TemporaryDirectory(prefix="spraybot-ui-") as temp_dir:
                output = Path(temp_dir) / "model.json"
                environment = os.environ.copy()
                environment["PYTHONPATH"] = str(ROOT / "src")
                process = subprocess.run(
                    [sys.executable, str(WORKER), generator, str(seed), str(output)],
                    cwd=ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=240,
                )
                if process.returncode:
                    raise RuntimeError(process.stderr[-3000:] or process.stdout[-3000:])
                self.respond(200, output.read_text(encoding="utf-8"))
        except Exception as error:
            self.respond(500, json.dumps({"error": str(error)}))

    def log_message(self, format, *args):
        print("[generator-ui] " + format % args, flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("SPRAYBOT_UI_PORT", "8765"))
    print(f"Spraybot generator UI: http://127.0.0.1:{port}/", flush=True)
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
