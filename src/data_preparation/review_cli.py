"""Local, token-protected review UI; no network service or model required."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import mimetypes
from pathlib import Path
import secrets
from urllib.parse import parse_qs, urlsplit
import webbrowser

from .annotation_review import ReviewProject


def make_handler(project, token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Keep the private access token out of request logs.

        def send(self, status, value, content_type="application/json"):
            payload = json.dumps(value).encode() if content_type == "application/json" else value
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(payload)

        def authorized(self):
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query)
            expected_host = f"127.0.0.1:{self.server.server_port}"
            origin = self.headers.get("Origin")
            if (self.headers.get("Host") != expected_host
                    or origin not in (None, f"http://{expected_host}")
                    or not secrets.compare_digest(query.get("token", [""])[0], token)):
                self.send(403, dict(error="Open the local URL printed by the review command."))
                return None
            return parsed.path, query

        def do_GET(self):
            route = self.authorized()
            if route is None:
                return
            path, query = route
            try:
                if path == "/":
                    self.send(200, Path(__file__).with_name("review.html").read_bytes(), "text/html; charset=utf-8")
                elif path == "/data":
                    self.send(200, project.report())
                elif path == "/image":
                    image = project.records[query["key"][0]]["path"]
                    self.send(200, image.read_bytes(), mimetypes.guess_type(image.name)[0] or "application/octet-stream")
                else:
                    self.send(404, dict(error="Not found"))
            except (ValueError, OSError, KeyError) as error:
                self.send(400, dict(error=str(error)))

        def do_POST(self):
            route = self.authorized()
            if route is None:
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 2_000_000 or self.headers.get("Content-Type") != "application/json":
                    raise ValueError("Expected a JSON request smaller than 2 MB")
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError("Expected a JSON object")
                if route[0] == "/decision":
                    project.save(body["key"], body)
                    self.send(200, dict(saved=True))
                elif route[0] == "/export":
                    self.send(200, dict(output=str(project.export(body["output"]))))
                else:
                    self.send(404, dict(error="Not found"))
            except (ValueError, OSError, KeyError, TypeError) as error:
                self.send(400, dict(error=str(error)))
    return Handler


def serve(project, port=8765):
    token = secrets.token_urlsafe(24)
    with HTTPServer(("127.0.0.1", port), make_handler(project, token)) as server:
        url = f"http://127.0.0.1:{server.server_port}/?token={token}"
        print(f"Review editor: {url}", flush=True)
        print("Keep this terminal open. Press Ctrl+C to stop; saved decisions persist.", flush=True)
        webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="Annotation experiment run containing data/labelled/<batch>")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--serve", action="store_true", help="Open the local image/box review editor")
    actions.add_argument("--export", type=Path, help="Export all explicitly accepted images under data/labelled/<version>")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        project = ReviewProject(args.run_dir)
        report = project.write_report()
        print(json.dumps(report["summary"], indent=2))
        print("Automatic checks complete; visual confirmation is still required for every image.")
        if args.export:
            print(f"Reviewed export: {project.export(args.export)}")
        elif args.serve:
            serve(project, args.port)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f"Review failed: {error}\n")
