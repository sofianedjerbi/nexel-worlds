"""Tickets: how a world knows who is at its door without ever seeing an email.

The account service signs "account A may enter the world at address W until time T" with its secret key (Ed25519);
a world checks the signature with the public key, which anyone may have. A ticket is two base64 parts joined by a
dot: the JSON it says, and the signature over exactly those bytes.
"""

import base64
import json
import os
import time
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

TICKET_S = 120          # a ticket is asked for at the door and used at once


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _raw(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def load_key(path: Path) -> Ed25519PrivateKey:
    """The service's secret key: made the first time, readable by its owner only."""
    if path.exists():
        return Ed25519PrivateKey.from_private_bytes(path.read_bytes())
    key = Ed25519PrivateKey.generate()
    raw = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
    return key


def public_text(key: Ed25519PrivateKey) -> str:
    return _b64(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))


def sign(key: Ed25519PrivateKey, account: str, world: str, now: float | None = None) -> str:
    now = time.time() if now is None else now
    body = json.dumps({"sub": account, "aud": world, "exp": int(now) + TICKET_S}, separators=(",", ":")).encode()
    return _b64(body) + "." + _b64(key.sign(body))


def check(public: str, ticket: str, world: str, now: float | None = None) -> str | None:
    """The account a ticket is for, or None: forged, for another world, out of date or not a ticket at all."""
    try:
        body, _, sig = ticket.partition(".")
        body = _raw(body)
        Ed25519PublicKey.from_public_bytes(_raw(public)).verify(_raw(sig), body)
        said = json.loads(body)
        if said["aud"] != world or said["exp"] < (time.time() if now is None else now):
            return None
        return str(said["sub"])
    except (InvalidSignature, ValueError, KeyError, TypeError):
        return None
