"""Plain HTTP for the browser client: the page, its scripts and styles, and the art."""

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
            return _file(f, CONTENT_TYPES[f.suffix], cache=STATIC[folder])
    return connection.respond(404, "not found\n")

STATIC = {"assets": "max-age=3600", "js": "no-cache", "css": "no-cache"}   # folder -> Cache-Control

CONTENT_TYPES = {".png": "image/png", ".ttf": "font/ttf", ".txt": "text/plain",
                 ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}

def _file(path: Path, ctype: str, cache: str = "no-cache") -> Response:
    body = path.read_bytes()
    return Response(200, "OK", Headers([("Content-Type", ctype), ("Content-Length", str(len(body))),
                                        ("Cache-Control", cache)]), body)
