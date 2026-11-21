"""A static server that is a phone's line: for measuring how the demo loads (tools/perf_load.py), never for playing.

    python tools/perf_serve.py dist --port 7819 --line fast3g [--pyodide DIR]

It serves a folder the way GitHub Pages does (gzip for text and wasm, `Cache-Control: max-age=600`, an ETag and 304s),
and everything it sends goes through ONE line of a given speed, with a given time to the server and back:

    fast3g   1.6 Mbit/s down, 150 ms there and back     (WebPageTest's "Fast 3G")
    4g       9 Mbit/s down, 170 ms                      (WebPageTest's "4G")
    none     as fast as the machine

Pages speaks HTTP/2: many files on one connection, each waiting one trip, all at once. This server speaks HTTP/1.1,
six connections a browser. So a request that comes on a connection straight after the answer before it (the
browser's own queue) does not wait a trip again; one that comes after a pause (a file that names another) does.
`--pyodide DIR` serves a copy of Pyodide at /pyodide/ as the CDN does (kept a year, and counted on the line at its
brotli size, `<file>.br` beside it if there is one: Chrome asks for no brotli over plain http).
`/__log` answers what was sent (JSON), `/__reset` forgets it.
"""

import argparse
import gzip
import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LINES = {"fast3g": (1.6e6 / 8, .150), "4g": (9e6 / 8, .170), "none": (0, 0)}
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".json": "application/json", ".png": "image/png", ".webp": "image/webp", ".ttf": "font/ttf", ".txt": "text/plain", ".flac": "audio/flac",
         ".wasm": "application/wasm", ".zip": "application/zip", ".bin": "application/octet-stream", ".mp4": "video/mp4", ".jpg": "image/jpeg", ".gif": "image/gif"}
GZIP = {".html", ".js", ".mjs", ".css", ".json", ".txt", ".wasm"}


class Line:
    """One line shared by every connection: a piece is sent when the pieces before it have gone."""

    def __init__(self, rate: float, trip: float):
        self.rate, self.trip, self.free, self.lock, self.log = rate, trip, 0.0, threading.Lock(), []

    def wait(self, wire: float):
        if not self.rate:
            return
        with self.lock:
            self.free = max(self.free, time.monotonic()) + wire / self.rate
            until = self.free
        time.sleep(max(0, until - time.monotonic()))


def handler(root: Path, pyodide: Path | None, line: Line, keep: int = 600):
    packed = {}                                              # (path, mtime) -> gzip body

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def setup(self):
            super().setup()
            self.last = None                                 # when this connection's last answer ended
            time.sleep(2 * line.trip)                        # (a new connection: TCP, then TLS)

        def log_message(self, *a):
            pass

        def handle(self):
            try:
                super().handle()
            except (BrokenPipeError, ConnectionResetError):          # (the page went away mid-file)
                pass

        def answer(self, code, headers, body=b"", wire=None):
            self.send_response(code)
            for k, v in headers.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            wire = (len(body) if wire is None else wire) + 300          # (and the headers)
            share = wire / max(1, len(body))
            line.wait(300)
            for i in range(0, len(body), 8192):
                piece = body[i:i + 8192]
                line.wait(len(piece) * share)
                self.wfile.write(piece)
            self.wfile.flush()
            self.last = time.monotonic()
            return wire

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/__log":
                return self.answer(200, {"Content-Type": "application/json"}, json.dumps(line.log).encode(), 0)
            if path == "/__reset":
                line.log.clear()
                return self.answer(200, {}, b"ok", 0)
            if self.last is None or time.monotonic() - self.last > .05:
                time.sleep(line.trip)                        # (the request's own trip: see the note above)
            if path.endswith("/"):
                path += "index.html"
            cdn = pyodide is not None and path.startswith("/pyodide/")
            f = ((pyodide / path[len("/pyodide/"):]) if cdn else (root / path.lstrip("/"))).resolve()
            if not f.is_file() or (root.resolve() not in f.parents and not cdn):
                line.log.append({"path": self.path, "status": 404, "wire": 300})
                return self.answer(404, {}, b"not found\n")
            st = f.stat()
            etag = '"' + hashlib.sha1(f"{f}{st.st_mtime_ns}{st.st_size}".encode()).hexdigest()[:16] + '"'
            head = {"Content-Type": TYPES.get(f.suffix, "application/octet-stream"), "ETag": etag, "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "public, max-age=31536000, immutable" if cdn else f"max-age={keep}"}
            if self.headers.get("If-None-Match") == etag:
                line.log.append({"path": self.path, "status": 304, "wire": 300})
                return self.answer(304, head)
            body, wire = f.read_bytes(), None
            if f.suffix in GZIP and "gzip" in self.headers.get("Accept-Encoding", ""):
                key = (f, st.st_mtime_ns)
                if key not in packed:
                    packed[key] = gzip.compress(body, 6)
                raw, body = len(body), packed[key]
                head["Content-Encoding"] = "gzip"
                br = f.with_name(f.name + ".br")
                wire = br.stat().st_size if cdn and br.exists() else len(body)
            sent = self.answer(200, head, body, wire)
            line.log.append({"path": self.path, "status": 200, "wire": int(sent), "raw": st.st_size})

    return H


def serve(root, port, name="none", pyodide=None, keep=600):
    """keep: seconds a browser may keep a file of the site without asking (Pages: 600; 0: a visit the day after)."""
    rate, trip = LINES[name]
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler(Path(root), Path(pyodide) if pyodide else None, Line(rate, trip), keep))
    httpd.daemon_threads = True
    return httpd


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("--port", type=int, default=7819)
    p.add_argument("--line", default="none", choices=list(LINES))
    p.add_argument("--pyodide")
    a = p.parse_args()
    serve(a.root, a.port, a.line, a.pyodide).serve_forever()
