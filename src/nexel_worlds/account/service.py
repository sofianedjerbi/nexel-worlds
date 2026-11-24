"""The account service: a few JSON answers over HTTP, apart from any world.

    POST /code    {email}                 a six-digit code is mailed (the answer never says if the email is known)
    POST /login   {email, code}        -> {session}          the browser keeps it, thirty days
    POST /ticket  {session, world}     -> {ticket}           what a world's door asks for (tickets.py)
    POST /logout  {session}
    POST /forget  {session}               the account and its email are deleted
    GET  /key                          -> {key}              the public key worlds check tickets with

    uv run python -m megastructure.account --origin http://127.0.0.1:7777      (mail goes to Mailpit: 127.0.0.1:1025)
"""

import collections
import json
import logging
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import tickets
from .mail import Mailer
from .store import Accounts, clean_email

log = logging.getLogger("megastructure.account")
# What one email, and one address, may ask for in an hour. Guessing a code is already five tries per code
# (store.py); these stop asking for code after code, and flooding someone's inbox.
LIMITS = {"code/email": (5, 3600), "code/ip": (20, 3600), "login/ip": (30, 3600), "ticket/ip": (600, 3600)}
MAX_BODY = 4096


class Limiter:
    def __init__(self):
        self.hits = collections.defaultdict(collections.deque)

    def allow(self, kind: str, who: str, now: float | None = None) -> bool:
        n, window = LIMITS[kind]
        q, now = self.hits[kind, who], time.monotonic() if now is None else now
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= n:
            return False
        q.append(now)
        return True


class Service:
    def __init__(self, folder: Path, mailer: Mailer, origins: list[str], ip_header: str = ""):
        self.accounts, self.mailer, self.origins, self.ip_header = Accounts(folder), mailer, set(origins), ip_header
        self.key = tickets.load_key(folder / "signing.key")
        self.limits = Limiter()

    def answer(self, path: str, said: dict, ip: str) -> tuple[int, dict]:
        """One request -> (HTTP status, JSON answer)."""
        if path == "/code":
            email = clean_email(said.get("email"))
            if not email:
                return 400, {"ok": False, "error": "bad_email"}
            if not self.limits.allow("code/ip", ip) or not self.limits.allow("code/email", email):
                return 429, {"ok": False, "error": "too_many"}
            try:
                self.mailer.send_code(email, self.accounts.new_code(email))
            except OSError as e:
                log.error("the mail did not leave: %s", e)
                return 503, {"ok": False, "error": "mail_down"}
            return 200, {"ok": True}
        if path == "/login":
            email = clean_email(said.get("email"))
            if not self.limits.allow("login/ip", ip):
                return 429, {"ok": False, "error": "too_many"}
            got = email and self.accounts.login(email, str(said.get("code", "")).strip())
            if not got:
                return 400, {"ok": False, "error": "bad_code"}
            return 200, {"ok": True, "session": got[0]}
        account = self.accounts.account(said.get("session", ""))
        if path in ("/ticket", "/logout", "/forget") and not account:
            return 401, {"ok": False, "error": "no_session"}
        if path == "/ticket":
            world = str(said.get("world", ""))
            if not world or len(world) > 200 or not self.limits.allow("ticket/ip", ip):
                return 400, {"ok": False, "error": "bad_world"}
            return 200, {"ok": True, "ticket": tickets.sign(self.key, account, world)}
        if path == "/logout":
            self.accounts.logout(said["session"])
            return 200, {"ok": True}
        if path == "/forget":
            self.accounts.forget(account)
            return 200, {"ok": True}
        return 404, {"ok": False, "error": "unknown"}

    def handler(self):
        service = self

        class Handler(BaseHTTPRequestHandler):
            def send(self, status: int, body: dict):
                raw = json.dumps(body).encode()
                self.send_response(status)
                origin = self.headers.get("Origin")
                if origin in service.origins:                # only the game's own pages may read the answers
                    self.send_header("Access-Control-Allow-Origin", origin)
                    self.send_header("Access-Control-Allow-Headers", "Content-Type")
                    self.send_header("Vary", "Origin")
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)

            def do_OPTIONS(self):
                self.send(204 if self.headers.get("Origin") in service.origins else 403, {})

            def do_GET(self):
                if self.path == "/key":
                    return self.send(200, {"ok": True, "alg": "ed25519", "key": tickets.public_text(service.key)})
                self.send(404, {"ok": False, "error": "unknown"})

            def do_POST(self):
                origin = self.headers.get("Origin")
                if origin and origin not in service.origins:  # a page that is not the game's: no
                    return self.send(403, {"ok": False, "error": "bad_origin"})
                try:
                    n = int(self.headers.get("Content-Length", "0"))
                    said = json.loads(self.rfile.read(n)) if 0 < n <= MAX_BODY else None
                except ValueError:
                    said = None
                if not isinstance(said, dict):
                    return self.send(400, {"ok": False, "error": "bad_json"})
                ip = (service.ip_header and self.headers.get(service.ip_header)) or self.client_address[0]
                self.send(*service.answer(self.path.split("?")[0], said, ip))

            def log_message(self, fmt, *args):               # (no request lines in the log: they would carry nothing useful)
                pass

        return Handler


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=7780)
    p.add_argument("--data", default="accounts", help="folder for the accounts file and the keys")
    p.add_argument("--origin", action="append", default=[], help="a game page allowed to log in here, e.g. http://127.0.0.1:7777")
    p.add_argument("--smtp", default="127.0.0.1:1025", help="where mail goes (Mailpit by default)")
    p.add_argument("--smtp-user", default="")
    p.add_argument("--smtp-password-file", default="")
    p.add_argument("--smtp-tls", action="store_true")
    p.add_argument("--sender", default="Nexel Worlds <login@nexel.test>")
    p.add_argument("--ip-header", default="", help="behind a proxy: the header that carries the visitor's address")
    a = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    host, _, port = a.smtp.rpartition(":")
    password = Path(a.smtp_password_file).read_text().strip() if a.smtp_password_file else ""
    service = Service(Path(a.data), Mailer(host, int(port), a.sender, a.smtp_user, password, a.smtp_tls), a.origin, a.ip_header)
    httpd = ThreadingHTTPServer((a.host, a.port), service.handler())
    log.info("accounts on http://%s:%d (mail to %s, pages allowed: %s)", a.host, a.port, a.smtp, ", ".join(a.origin) or "none")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
