"""What the account service remembers, in one SQLite file: accounts (an id and an email, nothing else), the code
each email is waiting to type, and who is logged in. Codes and sessions are kept hashed: the file, stolen, opens
no door."""

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path

CODE_S = 600                 # a code works for ten minutes,
CODE_TRIES = 5               # for five guesses (one in 200,000 of guessing it),
SESSION_S = 30 * 86400       # and a browser stays logged in for thirty days
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s.]+(\.[^@\s.]+)+$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY, email TEXT UNIQUE, created REAL);
CREATE TABLE IF NOT EXISTS codes(email TEXT PRIMARY KEY, hash TEXT, expires REAL, tries INTEGER);
CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY, account TEXT, expires REAL);
"""


def clean_email(text) -> str | None:
    email = str(text or "").strip().lower()
    return email if len(email) <= 254 and EMAIL.match(email) else None


class Accounts:
    def __init__(self, folder: Path):
        folder.mkdir(parents=True, exist_ok=True)
        folder.chmod(0o700)                                  # (emails and keys: this user's eyes only)
        self.db = sqlite3.connect(folder / "accounts.sqlite", check_same_thread=False, isolation_level=None)
        self.db.executescript(SCHEMA)
        self.lock = threading.Lock()                         # (the service answers on several threads)
        pepper = folder / "pepper.key"                       # mixed into every hash: the file alone cannot be guessed against
        if not pepper.exists():
            fd = os.open(pepper, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(secrets.token_bytes(32))
        self.pepper = pepper.read_bytes()

    def _hash(self, *parts: str) -> str:
        return hmac.new(self.pepper, "\0".join(parts).encode(), hashlib.sha256).hexdigest()

    def new_code(self, email: str, now: float | None = None) -> str:
        """A fresh code for this email; the one before it, if any, is dead."""
        now = time.time() if now is None else now
        code = f"{secrets.randbelow(10 ** 6):06d}"
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO codes VALUES(?,?,?,0)", (email, self._hash(email, code), now + CODE_S))
        return code

    def login(self, email: str, code: str, now: float | None = None) -> tuple[str, str] | None:
        """(session, account id) for the right code. A wrong one costs a try; out of tries or of time, the code is dead.
        An email seen for the first time gets its account here: signing up and logging in are the same thing."""
        now = time.time() if now is None else now
        with self.lock:
            row = self.db.execute("SELECT hash, expires, tries FROM codes WHERE email=?", (email,)).fetchone()
            if row is None:
                return None
            want, expires, tries = row
            if now > expires or tries >= CODE_TRIES:
                self.db.execute("DELETE FROM codes WHERE email=?", (email,))
                return None
            if not hmac.compare_digest(want, self._hash(email, str(code))):
                self.db.execute("UPDATE codes SET tries=tries+1 WHERE email=?", (email,))
                return None
            self.db.execute("DELETE FROM codes WHERE email=?", (email,))            # a code is used once
            got = self.db.execute("SELECT id FROM accounts WHERE email=?", (email,)).fetchone()
            account = got[0] if got else secrets.token_hex(16)
            if not got:
                self.db.execute("INSERT INTO accounts VALUES(?,?,?)", (account, email, now))
            session = secrets.token_urlsafe(32)
            self.db.execute("DELETE FROM sessions WHERE expires<?", (now,))
            self.db.execute("INSERT INTO sessions VALUES(?,?,?)", (self._hash(session), account, now + SESSION_S))
            return session, account

    def account(self, session: str, now: float | None = None) -> str | None:
        now = time.time() if now is None else now
        with self.lock:
            row = self.db.execute("SELECT account FROM sessions WHERE hash=? AND expires>?", (self._hash(str(session)), now)).fetchone()
        return row[0] if row else None

    def logout(self, session: str):
        with self.lock:
            self.db.execute("DELETE FROM sessions WHERE hash=?", (self._hash(str(session)),))

    def forget(self, account: str):
        """The account is gone: its email, and every browser logged in as it."""
        with self.lock:
            self.db.execute("DELETE FROM sessions WHERE account=?", (account,))
            email = self.db.execute("SELECT email FROM accounts WHERE id=?", (account,)).fetchone()
            if email:
                self.db.execute("DELETE FROM codes WHERE email=?", email)
            self.db.execute("DELETE FROM accounts WHERE id=?", (account,))
