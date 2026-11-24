"""Accounts: a code mailed to an email, a session, a signed ticket; and the world's door that reads the ticket."""

import socketserver
import threading
import time

import pytest

from nexel_worlds.account import tickets
from nexel_worlds.account.mail import Mailer
from nexel_worlds.account.service import LIMITS, Service
from nexel_worlds.account.store import CODE_S, CODE_TRIES, SESSION_S, Accounts, clean_email
from nexel_worlds.gate import Gate
from nexel_worlds.sim import ActionError


class Post:
    """A mailer that keeps the codes instead of sending them."""
    def __init__(self):
        self.codes = {}

    def send_code(self, to, code):
        self.codes[to] = code


@pytest.fixture
def service(tmp_path):
    return Service(tmp_path / "accounts", Post(), ["http://game.test"])


def logged_in(service, email="ash@example.com"):
    assert service.answer("/code", {"email": email}, "1.1.1.1") == (200, {"ok": True})
    status, said = service.answer("/login", {"email": email, "code": service.mailer.codes[email.strip().lower()]}, "1.1.1.1")
    assert status == 200
    return said["session"]


def test_a_code_logs_you_in_once(service):
    session = logged_in(service, " Ash@Example.com ")          # (an email is the same in any case)
    assert service.accounts.account(session)
    code = service.mailer.codes["ash@example.com"]
    assert service.answer("/login", {"email": "ash@example.com", "code": code}, "1.1.1.1")[1]["error"] == "bad_code"   # used: dead
    again = logged_in(service)                                         # the same email is the same account
    assert service.accounts.account(again) == service.accounts.account(session)
    assert service.answer("/code", {"email": "not an email"}, "1.1.1.1")[1]["error"] == "bad_email"
    assert clean_email("a@b") is None and clean_email("A@B.co") == "a@b.co"


def test_five_wrong_guesses_kill_a_code(service):
    service.answer("/code", {"email": "ash@example.com"}, "1.1.1.1")
    code = service.mailer.codes["ash@example.com"]
    wrong = f"{(int(code) + 1) % 10 ** 6:06d}"
    for _ in range(CODE_TRIES):
        assert service.answer("/login", {"email": "ash@example.com", "code": wrong}, "1.1.1.1")[0] == 400
    assert service.answer("/login", {"email": "ash@example.com", "code": code}, "1.1.1.1")[0] == 400     # even the right one, now


def test_codes_and_sessions_run_out(tmp_path):
    accounts = Accounts(tmp_path / "a")
    code = accounts.new_code("ash@example.com", now=1000)
    assert accounts.login("ash@example.com", code, now=1000 + CODE_S + 1) is None
    code = accounts.new_code("ash@example.com", now=2000)
    session, account = accounts.login("ash@example.com", code, now=2000)
    assert accounts.account(session, now=2000 + SESSION_S - 1) == account
    assert accounts.account(session, now=2000 + SESSION_S + 1) is None
    raw = (tmp_path / "a" / "accounts.sqlite").read_bytes()
    assert session.encode() not in raw and code.encode() not in raw    # neither is in the file as it is: hashed


def test_asking_for_codes_is_limited(service):
    n = LIMITS["code/email"][0]
    for _ in range(n):
        assert service.answer("/code", {"email": "ash@example.com"}, "1.1.1.1")[0] == 200
    assert service.answer("/code", {"email": "ash@example.com"}, "2.2.2.2") == (429, {"ok": False, "error": "too_many"})
    assert service.answer("/code", {"email": "other@example.com"}, "1.1.1.1")[0] == 200                   # (someone else still can)


def test_log_out_and_forget(service):
    session = logged_in(service)
    account = service.accounts.account(session)
    assert service.answer("/logout", {"session": session}, "1.1.1.1")[0] == 200
    assert service.answer("/ticket", {"session": session, "world": "w"}, "1.1.1.1") == (401, {"ok": False, "error": "no_session"})
    session = logged_in(service)
    assert service.answer("/forget", {"session": session}, "1.1.1.1")[0] == 200
    assert not service.accounts.account(session)
    assert b"ash@example.com" not in b"".join(str(r).encode() for r in service.accounts.db.execute("SELECT * FROM accounts"))
    assert service.accounts.account(logged_in(service)) != account     # back later: a new account


def test_a_ticket_is_for_one_world_for_two_minutes(service):
    session = logged_in(service)
    account = service.accounts.account(session)
    ticket = service.answer("/ticket", {"session": session, "world": "play.test"}, "1.1.1.1")[1]["ticket"]
    public = tickets.public_text(service.key)
    assert tickets.check(public, ticket, "play.test") == account
    assert tickets.check(public, ticket, "other.test") is None                         # another world cannot use it
    assert tickets.check(public, ticket, "play.test", now=time.time() + tickets.TICKET_S + 5) is None
    body, _, sig = ticket.partition(".")
    forged = tickets._b64(tickets._raw(body).replace(account.encode(), b"0" * len(account))) + "." + sig
    assert tickets.check(public, forged, "play.test") is None                          # what it says cannot be changed
    assert tickets.check(public, "nonsense", "play.test") is None and tickets.check(public, "", "play.test") is None


def test_the_door_of_a_world(world, tmp_path, service):
    sim, old = world                                                   # (old: a character from before there were accounts)
    gate = Gate("http://accounts.test", tmp_path)
    gate.public = tickets.public_text(service.key)                     # (asked of the service once; given here)
    session = logged_in(service)
    account = service.accounts.account(session)
    ticket = service.answer("/ticket", {"session": session, "world": "play.test"}, "1.1.1.1")[1]["ticket"]
    assert gate.who({"ticket": ticket}, "play.test") == account
    with pytest.raises(ActionError) as e:
        gate.who({"ticket": ticket}, "elsewhere.test")
    assert e.value.code == "bad_ticket"
    with pytest.raises(ActionError) as e:                              # no ticket, no key: no
        gate.who({"name": "Ash", "token": "t"}, "play.test")
    assert e.value.code == "login_needed"
    assert gate.who({"key": gate.agent_key}, "play.test") is None      # a local program with this world's key
    assert (tmp_path / "agent.key").stat().st_mode & 0o077 == 0

    with pytest.raises(ActionError) as e:
        sim.enter(account, "", "t")
    assert e.value.code == "name_needed"
    a = sim.enter(account, "Milo", "browser-secret", "frog")           # the first time: the name becomes this account's
    assert a.name == "Milo" and a.race == "frog" and sim.owners[account] == a.id
    assert sim.enter(account, "Somebody else", "x") is a               # after that the account is Milo here, whatever it asks
    with pytest.raises(ActionError) as e:                              # and Milo opens to no secret, even the one it was made with
        sim.login("Milo", "browser-secret")
    assert e.value.code == "login_needed"
    with pytest.raises(ActionError) as e:
        sim.enter("another-account", "Milo", "browser-secret")
    assert e.value.code == "bad_token"
    with pytest.raises(ActionError) as e:                              # a character from before: not without its browser's secret
        sim.enter("another-account", old.name, "a guess")
    assert e.value.code == "bad_token" and "another-account" not in sim.owners
    assert dict(sim.store.db.execute("SELECT account, agent FROM owners")) == {account: a.id}


def test_an_old_character_is_claimed_by_its_own_browser(world):
    sim, old = world                                                   # (Ash, whose browser holds "tok": conftest.py)
    assert sim.enter("acct-1", "Ash", "tok") is old and sim.owners == {"acct-1": old.id}


class Sink(socketserver.StreamRequestHandler):
    """Just enough of a mail server to take one message."""
    def handle(self):
        say = lambda line: self.wfile.write(line.encode() + b"\r\n")
        say("220 sink")
        data = False
        for raw in self.rfile:
            line = raw.decode().rstrip("\r\n")
            if data:
                if line == ".":
                    data = False
                    say("250 ok")
                else:
                    self.server.got.append(line)
            elif line.upper().startswith("DATA"):
                data = True
                say("354 go")
            elif line.upper().startswith("QUIT"):
                say("221 bye")
                return
            else:
                say("250 ok")


def test_the_code_is_mailed():
    with socketserver.TCPServer(("127.0.0.1", 0), Sink) as server:
        server.got = []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        Mailer("127.0.0.1", server.server_address[1], "Nexel Worlds <login@nexel.test>").send_code("ash@example.com", "123456")
        server.shutdown()
    text = "\n".join(server.got)
    assert "To: ash@example.com" in text and "Subject: 123456 is your Nexel Worlds code" in text and "Your code is 123456" in text
