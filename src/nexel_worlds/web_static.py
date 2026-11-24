"""Plain HTTP for the browser client: the page, its scripts and styles, and the art.

Text goes out gzipped to a browser that takes it, and every file has a mark (ETag): asked for again unchanged, the
answer is "not modified" and no body (a page loaded again sent its hundred scripts whole, 1.3 MB, every time).
Started with `--bundle` (or MEGASTRUCTURE_BUNDLE=1) the server sends the client as few files (web_bundle.py): one
script, the styles in the page, the pictures in one pack, each kept by the browser for good under its own name.
For a phone or a far player; development and the tests keep the plain files."""

import gzip
import hashlib
import logging
import os
from pathlib import Path

from websockets.datastructures import Headers
from websockets.http11 import Response

WEB = Path(__file__).parent / "web"
BUNDLE = [os.environ.get("MEGASTRUCTURE_BUNDLE") == "1"]
FOR_GOOD = "public, max-age=31536000, immutable"
_packed, _built = {}, {}           # (path, changed) -> (mark, gzip body or None);  the client's stamp -> (page, files)


def set_bundle(on: bool):
    BUNDLE[0] = BUNDLE[0] or bool(on)


def serve_http(connection, request, accounts=None):
    """Plain HTTP GETs (no websocket upgrade) get the browser client. A world that asks who you are (gate.py)
    tells the page where to log in."""
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return None
    path = request.path.split("?")[0]
    page, files = _bundle() if BUNDLE[0] else (None, {})
    if path in ("/", "/index.html"):
        body = page.encode() if page else (WEB / "index.html").read_bytes()
        if accounts:
            body = body.replace(b"<body>", f'<body data-accounts="{accounts}">'.encode(), 1)
        return _answer(request, body, "text/html; charset=utf-8", "no-cache", ("page", bool(page), accounts, web_stamp()))
    if path.lstrip("/") in files:
        return _answer(request, files[path.lstrip("/")], CONTENT_TYPES[Path(path).suffix], FOR_GOOD, (path,))
    folder, _, name = path.lstrip("/").partition("/")
    if folder in STATIC:
        root = (WEB / folder).resolve()
        f = (root / name).resolve()
        if f.parent == root and f.is_file() and f.suffix in CONTENT_TYPES:   # no subfolders, no "..": only our files
            return _answer(request, f.read_bytes(), CONTENT_TYPES[f.suffix], "no-cache" if f.suffix == ".json" else STATIC[folder], (str(f), f.stat().st_mtime_ns))
        if folder == "audio" and name == "sfx.json":
            logging.getLogger(__name__).warning("no sound effects built: run `uv run python tools/build_audio.py`")
            return Response(204, "No Content", Headers([("Cache-Control", "no-cache")]), b"")   # (a state, not a missing file: the page plays without them (audio.js), and its console has no error. It was a 404: every page of a new checkout had one)
    return connection.respond(404, "not found\n")

STATIC = {"assets": "max-age=3600", "js": "no-cache", "css": "no-cache",   # folder -> Cache-Control
          "audio": "max-age=3600"}       # built by tools/build_audio.py; the client asks for files as name?v=<build>

CONTENT_TYPES = {".png": "image/png", ".webp": "image/webp", ".ttf": "font/ttf", ".txt": "text/plain", ".wav": "audio/wav", ".flac": "audio/flac", ".json": "application/json",
                 ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".bin": "application/octet-stream"}
TEXT = ("text/", "application/json")

def web_stamp() -> int:
    """When the client's code last changed: a page that reconnects and finds a newer one reloads itself (state.js)."""
    if not (WEB / "index.html").exists():
        return 0                                             # (the in-browser demo: the page is the client, nothing to compare)
    return int(max(f.stat().st_mtime for f in [WEB / "index.html", *(WEB / "js").glob("*.js"), *(WEB / "css").glob("*.css")]))


def _bundle():
    stamp = web_stamp()
    if stamp not in _built:
        _built.clear()
        from . import web_bundle                             # (not in the demo's tab: it has no files to pack)
        _built[stamp] = web_bundle.packed(WEB)
    return _built[stamp]


def _answer(request, body: bytes, ctype: str, cache: str, key: tuple) -> Response:
    if key not in _packed:
        if len(_packed) > 600:
            _packed.clear()
        _packed[key] = ('"' + hashlib.sha1(body).hexdigest()[:16] + '"', gzip.compress(body, 6) if ctype.startswith(TEXT) and len(body) > 600 else None)
    mark, small = _packed[key]
    head = [("Content-Type", ctype), ("Cache-Control", cache), ("ETag", mark), ("Vary", "Accept-Encoding")]
    if request.headers.get("If-None-Match") == mark:
        return Response(304, "Not Modified", Headers(head), b"")
    if small is not None and "gzip" in request.headers.get("Accept-Encoding", ""):
        body, head = small, head + [("Content-Encoding", "gzip")]
    return Response(200, "OK", Headers(head + [("Content-Length", str(len(body)))]), body)
