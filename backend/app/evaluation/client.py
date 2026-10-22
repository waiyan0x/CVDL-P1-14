"""Small HTTP client for measuring the deployed comparison endpoint."""
import json
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ComparisonClient:
    def __init__(self, base_url: str, timeout: float = 180):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session_id = "benchmark-" + uuid.uuid4().hex
        self.frame_id = 0

    def _request(self, path: str, data=None, content_type=None):
        headers = {"Content-Type": content_type} if content_type else {}
        try:
            with urlopen(Request(self.base_url + path, data=data, headers=headers), timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            try:
                body = json.load(exc)
                message = body.get("error", {}).get("message", str(exc))
            except (ValueError, AttributeError):
                message = str(exc)
            raise RuntimeError(f"Comparison API returned HTTP {exc.code}: {message}") from exc
        except URLError as exc:
            raise RuntimeError(f"Cannot reach the running API at {self.base_url}: {exc.reason}") from exc

    def models(self):
        return self._request("/api/models")

    def compare(self, path: Path, options: dict):
        boundary = "eds-" + uuid.uuid4().hex
        values = {**options, "session_id": self.session_id, "frame_id": self.frame_id,
                  "source": "image", "source_timestamp_ms": 0,
                  "captured_at": datetime.now(timezone.utc).isoformat()}
        self.frame_id += 1
        body = bytearray()
        for key, value in values.items():
            body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        # A constant safe filename avoids quoting user-controlled path characters into multipart headers.
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="frame{path.suffix.lower()}"\r\nContent-Type: {mime}\r\n\r\n'.encode())
        body.extend(path.read_bytes())
        body.extend(f"\r\n--{boundary}--\r\n".encode())
        return self._request("/api/comparisons", bytes(body), f"multipart/form-data; boundary={boundary}")
