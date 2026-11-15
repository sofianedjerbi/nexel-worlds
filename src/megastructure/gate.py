"""The door of a world that asks who you are (server.py --accounts): a ticket signed by the account service for a
person, or this world's own key for the programs that play on this machine (the AI players, the tests).

The world never sees an email or a code: only "account 3f9a... may enter the world at this address for two
minutes", signed (account/tickets.py). The service's public key is asked for once and kept.
"""

import hmac
import json
import os
import secrets
import time
import urllib.request
from pathlib import Path

from .sim import ActionError


class Gate:
    def __init__(self, url: str, world_dir: Path):
        self.url, self.public, self.asked = url.rstrip("/"), None, 0.0
        key = world_dir / "agent.key"                        # for local programs: readable by this user only
        if not key.exists():
            fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(secrets.token_urlsafe(32))
        self.agent_key = key.read_text().strip()

    def _public(self, again: bool = False) -> str:
        if self.public is None or (again and time.monotonic() - self.asked > 60):
            self.asked = time.monotonic()
            try:
                with urllib.request.urlopen(self.url + "/key", timeout=3) as r:
                    self.public = json.load(r)["key"]
            except (OSError, ValueError, KeyError) as e:
                if self.public is None:
                    raise ActionError("accounts_down", "the account service does not answer") from e
        return self.public

    def account(self, ticket: str, address: str) -> str | None:
        """The account a ticket is for, if it is a good one for this world's address."""
        from .account import tickets                         # (only a world with a door needs the signature library)
        got = tickets.check(self._public(), ticket, address)
        if got is None:                                      # (the service may have a new key since we asked)
            got = tickets.check(self._public(again=True), ticket, address)
        return got

    def who(self, msg: dict, address: str) -> str | None:
        """Who says hello: an account id for a person with a ticket, None for a local program holding this world's
        key. Anyone else is turned away."""
        if msg.get("ticket"):
            account = self.account(str(msg["ticket"]), address)
            if account is None:
                raise ActionError("bad_ticket", "log in again")
            return account
        if hmac.compare_digest(str(msg.get("key", "")), self.agent_key):
            return None
        raise ActionError("login_needed", "this world asks who you are: log in with your email")
