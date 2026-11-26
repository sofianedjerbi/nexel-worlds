"""The pages of a test: every one on the tests' clock (clock.py), every one shut when its test is over, and the next
test's page loading while this one plays.

- A page a test opened and did not shut stayed open for the rest of the run: its player stood awake in the world, near
  where the next ones woke (new players wake round one place), and was drawn on their screens and counted with who
  was there (`HdLook.bodies()` in test_e2e_hd_land.py's deep room: the "chicken and somebody" seen one run in a few);
  and its page went on drawing the land sixty times a second beside every test after it.
- A page takes half a second to come (a hundred scripts, sixty sheets decoded) and the machine has cores to spare:
  the next test's page is asked for when this test's has been handed over (`ahead`: if the next test plays on the
  `game` fixture's page, and at that test's pace), and is at the first screen, waiting for a name, when the next
  test wants it (`take`). It is a new page of its own, as it always was: nothing of
  a test before it is in it. What it is not is new-born: the first screen has been up for as long as the test before
  took. A test about the first screen itself opens its own page."""

import base64
import os
import re
from pathlib import Path

import clock

# A failing test's last picture of each of its pages, for runs where nobody watches (CI uploads the folder): E2E_SHOTS
# names a folder; unset, none. Every page a test opens (its own, a context's, the `game` fixture's) is photographed as
# it is shut, into memory: most tests shut their page and then assert (`page.close(); assert not off`), so nothing was
# on its way out yet when it shut. A page left open is photographed when its test is over. They are written, named
# after the test, only if it failed (Pages.shut).
SHOTS = Path(os.environ["E2E_SHOTS"]) if os.environ.get("E2E_SHOTS") else None
taken = []          # (test, png) of this test's pages, as they were shut
quiet = False       # (shutting a passed test's pages: no picture)


def test_name():
    return os.environ.get("PYTEST_CURRENT_TEST", "test").rsplit(" ", 1)[0]


def shoot(page):
    """The page's picture now, kept for its test's end (nothing if E2E_SHOTS is unset or the page fell)."""
    if SHOTS is None or page.is_closed():
        return
    try:
        taken.append((test_name(), page.screenshot(timeout=10000)))
    except Exception:  # noqa: BLE001, S110 - a page that fell: no picture of it
        pass


def write(test, png):
    SHOTS.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^\w.-]+", "_", test.removeprefix("tests/e2e/"))[:150]
    path, n = SHOTS / f"{name}.png", 1
    while path.exists():
        n += 1
        path = SHOTS / f"{name}-{n}.png"
    path.write_bytes(png)


def kept(page):
    """The page, photographed as it is shut (SHOTS)."""
    if SHOTS is None:
        return page
    close = page.close

    def closing(*a, **kw):
        if not quiet:
            shoot(page)
        return close(*a, **kw)

    page.close = closing
    return page


class Pages:
    """A browser whose pages are paced, counted and shut."""

    def __init__(self, inner):
        self._inner, self.made, self.next = inner, [], None

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def new_page(self, **kw):
        page = kept(clock.paced(self._inner.new_page(**kw)))
        self.made.append(page)
        return page

    def new_context(self, **kw):
        ctx = Context(self._inner.new_context(**kw))
        self.made.append(ctx)
        return ctx

    def shut(self, failed=False):
        """Every page and context the test made and left open (photographed first if the test failed: SHOTS)."""
        global quiet
        left, quiet = 0, not failed
        for p in self.made:                               # (each photographed as it shuts, if the test failed: kept, Context.close)
            try:
                left += 0 if getattr(p, "is_closed", lambda: False)() else 1
                p.close()
            except Exception:  # noqa: BLE001, S110 - gone already (a context shut with its pages, a browser that fell)
                pass
        self.made.clear()
        quiet = False
        if failed:
            for test, png in taken:
                write(test, png)
        taken.clear()
        return left

    # ---- the next test's page
    def ahead(self, make):
        """Ask now for the page the next test will play on: `make(page)` -> what take() will hand over."""
        if self.next is None and clock.AHEAD and clock.coming:
            try:
                page = clock.paced(self._inner.new_page(viewport={"width": 1200, "height": 800}), clock.coming)
                self.next = (clock.coming, page, make(page))
            except Exception:  # noqa: BLE001 - not this time: the next test makes its own
                self.next = None

    def take(self):
        """The page asked for ahead, if it was made at this test's pace (another: it is shut, and None)."""
        if self.next is None:
            return None
        (pace, page, made), self.next = self.next, None
        if pace != clock.now or page.is_closed():
            page.close()
            return None
        self.made.append(kept(page))
        return made


class Context:
    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def new_page(self, **kw):
        return kept(clock.paced(self._inner.new_page(**kw)))

    def close(self, *a, **kw):
        for q in self._inner.pages if not quiet else []:
            shoot(q)
        return self._inner.close(*a, **kw)


def keep(name, pictures, info):
    """Pictures a test chose to keep (name -> a PNG data URL) and what it saw, in SHOTS/<name>/ (for the run's artifact,
    as a failing test's last picture is): a picture of what went wrong, not only of the page at its end. Unset: none."""
    if SHOTS is None:
        return
    out = SHOTS / name
    out.mkdir(parents=True, exist_ok=True)
    for view, url in pictures.items():
        (out / f"{view}.png").write_bytes(base64.b64decode(url.split(",", 1)[1]))
    (out / "info.txt").write_text(repr(info))
