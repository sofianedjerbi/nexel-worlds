"""A world that asks who you are, in Chrome: your email, the code mailed to it, then the first screen as before.
The account service runs here with a mailer that keeps the codes; the world is a server of its own with --accounts."""

import socket
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer

import pytest
from conftest import ROOT, free_port

from megastructure.account.service import Service


class Post:
    def __init__(self):
        self.codes = {}

    def send_code(self, to, code):
        self.codes[to] = code


@pytest.fixture(scope="module")
def door(tmp_path_factory):
    """(the world's page, the account service) of a world with a door."""
    folder, port = tmp_path_factory.mktemp("door"), free_port()
    url = f"http://127.0.0.1:{port}"
    service = Service(folder / "accounts", Post(), [url])
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), service.handler())
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    proc = subprocess.Popen([sys.executable, "-m", "megastructure.server", "--saves", str(folder / "saves"), "--world", "door", "--port", str(port),
                             "--seed", "7", "--dev", "--accounts", f"http://127.0.0.1:{httpd.server_address[1]}"], cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=open(folder / "server.log", "w"))
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=.2).close()
            break
        except OSError:
            time.sleep(.1)
    yield url, service
    proc.terminate()
    proc.wait(10)
    httpd.shutdown()


HELLO = """(msg) => new Promise((done) => { const ws = new WebSocket(wsBase + '/agent');
  ws.onopen = () => ws.send(JSON.stringify({id: 1, op: 'hello', ...msg})); ws.onmessage = (m) => { done(JSON.parse(m.data)); ws.close(); }; })"""


def test_you_log_in_with_a_code_mailed_to_you(browser, door):
    url, service = door
    ctx = browser.new_context(viewport={"width": 1280, "height": 760})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url)
    page.wait_for_function("typeof ready !== 'undefined' && IMG.character && IMG.character.complete")
    js = page.evaluate
    shown = "[...document.querySelectorAll('#joinbox .menu > *')].filter((e) => e.offsetParent).map((e) => e.id || e.querySelector('input').id)"
    assert js("TITLE.step") == "mail" and js("document.activeElement.id") == "email"
    assert js(shown) == ["email", "sendcode", "watch", "titlehelp", "titlesound"]                 # one step on the screen: no name, no races yet
    page.keyboard.type("not an email")
    page.keyboard.press("Enter")
    page.wait_for_function("$('email').classList.contains('need')")
    assert not service.mailer.codes
    page.fill("#email", "Milo@Example.com")
    page.keyboard.press("Enter")
    page.wait_for_function("TITLE.step === 'code'")
    assert js(shown) == ["code", "login", "startover", "watch", "titlehelp", "titlesound"] and js("document.activeElement.id") == "code"
    code = service.mailer.codes["milo@example.com"]
    page.keyboard.type(f"{(int(code) + 1) % 10 ** 6:06d}")                                        # a wrong one: said, and the field is yours again
    page.wait_for_function("$('code').classList.contains('need') && $('code').value === ''")
    assert js("TITLE.step") == "code" and "not the code" in js("$('toastt').textContent")
    page.keyboard.type(code)                                                                      # six digits: no key to press
    page.wait_for_function("TITLE.step === 'me' && document.activeElement.id === 'name'")
    assert js(shown) == ["name", "raceslot", "join", "watch", "titlehelp", "titlesound", "logout"] and js("$('logoutv').textContent") == "Milo@Example.com"
    assert js("!$('name').readOnly")
    assert js(HELLO, {"name": "Thief", "token": "x"})["error"] == "login_needed"                  # the door: no ticket, no way in
    assert js(HELLO, {"name": "Thief", "token": "x", "ticket": "made.up"})["error"] == "bad_ticket"
    page.keyboard.type("Milo")
    page.keyboard.press("Enter")
    page.wait_for_function("me === 'Milo' && meObs", timeout=25000)
    assert (js("rpc('dev_give', {item: 'wood', n: 1})").get("error")) == "unknown_op"             # (the QA tools are not for who came by ticket)
    assert js(HELLO, {"name": "Milo", "token": js("localStorage.getItem('megastructure-token-Milo')")})["error"] == "login_needed"   # Milo is the account's now

    page.reload()                                                                                 # back: still logged in, and Milo is not asked again
    page.wait_for_function("typeof ready !== 'undefined' && ACCOUNT.named === 'Milo'")
    assert js("TITLE.step") == "me" and js("$('name').value") == "Milo" and js("$('name').readOnly")
    page.keyboard.press("Enter")
    page.wait_for_function("me === 'Milo' && meObs", timeout=25000)

    page.reload()
    page.wait_for_function("typeof ready !== 'undefined' && ACCOUNT.named === 'Milo'")
    page.click("#logout")                                                                         # log out: nobody again, and the session is dead
    page.wait_for_function("TITLE.step === 'mail'")
    assert js("localStorage.getItem('megastructure-session')") is None and js("$('email').value") == "Milo@Example.com"
    assert not service.accounts.db.execute("SELECT 1 FROM sessions").fetchall()
    assert not errors, errors
    ctx.close()


def test_a_world_without_accounts_asks_nothing(browser, server):
    page = browser.new_page(viewport={"width": 1280, "height": 760})
    page.goto(server)
    page.wait_for_function("typeof ready !== 'undefined'")
    assert page.evaluate("TITLE.step") == "me" and page.evaluate("getComputedStyle($('logout')).display") == "none"
    assert page.evaluate("TITLE.rows") == ["racepick", "join", "watch", "titlehelp", "titlesound"]
    page.close()
