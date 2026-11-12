"""Plain HTTP for the browser client: the page, its scripts and styles, and the art."""

import logging
from pathlib import Path

from websockets.datastructures import Headers
from websockets.http11 import Response

WEB = Path(__file__).parent / "web"


def serve_http(connection, request):
    """Plain HTTP GETs (no websocket upgrade) get the browser client."""
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return None
    path = request.path.split("?")[0]
    if path in ("/", "/index.html"):
        return _file(WEB / "index.html", "text/html; charset=utf-8")
    folder, _, name = path.lstrip("/").partition("/")
    if folder in STATIC:
        root = (WEB / folder).resolve()
        f = (root / name).resolve()
        if f.parent == root and f.is_file() and f.suffix in CONTENT_TYPES:   # no subfolders, no "..": only our files
            return _file(f, CONTENT_TYPES[f.suffix], cache="no-cache" if f.suffix == ".json" else STATIC[folder])
        if folder == "audio" and name == "sfx.json":
            logging.getLogger(__name__).warning("no sound effects built: run `uv run python tools/build_audio.py`")
    return connection.respond(404, "not found\n")

STATIC = {"assets": "max-age=3600", "js": "no-cache", "css": "no-cache",   # folder -> Cache-Control
          "audio": "max-age=3600"}       # built by tools/build_audio.py; the client asks for files as name?v=<build>

CONTENT_TYPES = {".png": "image/png", ".ttf": "font/ttf", ".txt": "text/plain", ".wav": "audio/wav", ".json": "application/json",
                 ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}

def web_stamp() -> int:
    """When the client's code last changed: a page that reconnects and finds a newer one reloads itself (state.js)."""
    if not (WEB / "index.html").exists():
        return 0                                             # (the in-browser demo: the page is the client, nothing to compare)
    return int(max(f.stat().st_mtime for f in [WEB / "index.html", *(WEB / "js").glob("*.js"), *(WEB / "css").glob("*.css")]))


def _file(path: Path, ctype: str, cache: str = "no-cache") -> Response:
    body = path.read_bytes()
    return Response(200, "OK", Headers([("Content-Type", ctype), ("Content-Length", str(len(body))),
                                        ("Cache-Control", cache)]), body)
