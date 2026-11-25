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

import os
import re
import sys
from pathlib import Path

import clock

# A failing test's last picture, for runs where nobody watches (CI uploads the folder): E2E_SHOTS names a folder; unset, none.
# A page shut while its test's error is on its way out (`finally: page.close()`), or left open by a test that failed,
# is photographed first, named after the test.
SHOTS = Path(os.environ["E2E_SHOTS"]) if os.environ.get("E2E_SHOTS") else None


def shoot(page):
    if SHOTS is None or page.is_closed():
        return
    test = os.environ.get("PYTEST_CURRENT_TEST", "test").rsplit(" ", 1)[0]
    SHOTS.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^\w.-]+", "_", test.removeprefix("tests/e2e/"))[:150]
    path, n = SHOTS / f"{name}.png", 1
    while path.exists():
        n += 1
        path = SHOTS / f"{name}-{n}.png"
    try:
        page.screenshot(path=str(path), timeout=10000)
    except Exception:  # noqa: BLE001, S110 - a page that fell: no picture of it
        pass


def kept(page):
    """The page, its close photographing it first when an error is on its way out."""
    if SHOTS is None:
        return page
    close = page.close

    def closing(*a, **kw):
        if sys.exc_info()[1] is not None:
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
        left = 0
        for p in self.made:
            if failed:
                for q in p.pages if isinstance(p, Context) else [p]:
                    shoot(q)
            try:
                left += 0 if getattr(p, "is_closed", lambda: False)() else 1
                p.close()
            except Exception:  # noqa: BLE001, S110 - gone already (a context shut with its pages, a browser that fell)
                pass
        self.made.clear()
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
        return clock.paced(self._inner.new_page(**kw))

    def close(self, *a, **kw):
        if sys.exc_info()[1] is not None:
            for q in self._inner.pages:
                shoot(q)
        return self._inner.close(*a, **kw)
