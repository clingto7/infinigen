"""Local server for the interactive Spraybot workpiece generator.

Run from the repository root with:
    uv run python scripts/spraybot_generator_ui_server.py
"""

import json
import gzip
import os
import subprocess
import sys
import tempfile
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "scripts" / "spraybot-generator-ui" / "index.html"
WORKER = Path(__file__).with_name("spraybot_generator_ui_worker.py")
os.environ.setdefault("PYTHONPATH", str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from spraybot_review_root import (  # noqa: E402
    index as review_index,
    read_episode,
    read_review,
    save_episode,
    save_review,
)

from infinigen2.workpieces import CATEGORY_IDS as WORKPIECE_IDS  # noqa: E402
from infinigen2.objects.spraybot import CATEGORY_IDS as SPRAYBOT_IDS  # noqa: E402


GENERATORS = [
    *({"id": f"workpiece:{item}", "label": f"workpiece:{item} - {item.replace('_', ' ')}", "group": "Workpieces"} for item in WORKPIECE_IDS),
    *({"id": f"spraybot:{item}", "label": f"spraybot:{item} - {item.replace('_', ' ')}", "group": "Spraybot"} for item in SPRAYBOT_IDS),
]
ALLOWED = {item["id"] for item in GENERATORS}
REVIEW_ROOT = Path(os.environ["SPRAYBOT_REVIEW_ROOT"]).resolve() if os.environ.get("SPRAYBOT_REVIEW_ROOT") else None
TRAJECTORY_ROOT = Path(os.environ["SPRAYBOT_TRAJECTORY_ROOT"]).resolve() if os.environ.get("SPRAYBOT_TRAJECTORY_ROOT") else None


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type="application/json; charset=utf-8"):
        encoded = body if isinstance(body, bytes) else body.encode("utf-8")
        compress = (content_type.startswith("application/json")
                    and "gzip" in self.headers.get("Accept-Encoding", "").lower()
                    and len(encoded) > 4096)
        if compress:
            encoded = gzip.compress(encoded, compresslevel=3)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        if compress:
            self.send_header("Content-Encoding", "gzip")
        if content_type.startswith("application/json"):
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        parsed = urlsplit(self.path)
        path = parsed.path
        if path in ("/", "/generator"):
            self.respond(200, UI.read_bytes(), "text/html; charset=utf-8")
        elif path == "/parametric-surfaces.js":
            self.respond(200, (UI.parent / "parametric-surfaces.js").read_bytes(), "text/javascript; charset=utf-8")
        elif path == "/api/generators":
            self.respond(200, json.dumps(GENERATORS))
        elif path == "/api/review-root":
            self.respond(200, json.dumps(review_index(REVIEW_ROOT) if REVIEW_ROOT else {"root": None, "interfaces": []}))
        elif path.startswith("/api/trajectory/") and TRAJECTORY_ROOT:
            parts = [unquote(part) for part in path.split("/")]
            if (len(parts) != 5 or parts[3] not in ALLOWED
                    or not parts[4].startswith("seed_") or len(parts[4]) != 15
                    or not parts[4][5:].isdigit()):
                self.respond(404, json.dumps({"error": "trajectory artifact not found"}))
            else:
                artifact = TRAJECTORY_ROOT / parts[3] / f"{parts[4]}.json"
                self.respond(200, artifact.read_bytes()) if artifact.is_file() else self.respond(
                    404, json.dumps({"error": "trajectory artifact not found"}))
        elif path.startswith("/api/review/") and REVIEW_ROOT:
            parts = [unquote(part) for part in path.split("/")]
            if len(parts) == 5 and parts[4] == "review":
                self.respond(200, json.dumps(read_review(REVIEW_ROOT, parts[3])))
            elif len(parts) == 6 and parts[4] == "episodes":
                self.respond(200, json.dumps(read_episode(REVIEW_ROOT, parts[3], parts[5])))
            else:
                self.respond(404, json.dumps({"error": "review artifact not found"}))
        else:
            self.respond(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if self.path not in ("/api/generate", "/api/review"):
            self.respond(404, json.dumps({"error": "not found"}))
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(size))
            if self.path == "/api/review":
                if not REVIEW_ROOT:
                    raise ValueError("server has no --review-root; start it with SPRAYBOT_REVIEW_ROOT")
                path = save_review(REVIEW_ROOT, request["interface_id"], request)
                self.respond(200, json.dumps({"saved": str(path),
                                              "interface_status": read_review(REVIEW_ROOT, request["interface_id"])["interface_status"]}))
                return
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
                payload = json.loads(output.read_text(encoding="utf-8"))
                item = next(item for item in GENERATORS if item["id"] == generator)
                payload.update({"label": item["label"], "group": item["group"]})
                if REVIEW_ROOT:
                    save_episode(REVIEW_ROOT, payload)
                self.respond(200, json.dumps(payload, ensure_ascii=False))
        except Exception as error:
            self.respond(500, json.dumps({"error": str(error)}))

    def log_message(self, format, *args):
        print("[generator-ui] " + format % args, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.environ.get("SPRAYBOT_UI_PORT", "8765")))
    parser.add_argument("--review-root", type=Path, default=None)
    parser.add_argument("--trajectory-root", type=Path, default=None)
    args = parser.parse_args()
    if args.review_root:
        REVIEW_ROOT = args.review_root.resolve()
    if args.trajectory_root:
        TRAJECTORY_ROOT = args.trajectory_root.resolve()
    port = args.port
    print(f"Spraybot generator UI: http://127.0.0.1:{port}/ review_root={REVIEW_ROOT or '-'}", flush=True)
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
