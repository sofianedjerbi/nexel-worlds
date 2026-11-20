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

import clock


class Pages:
    """A browser whose pages are paced, counted and shut."""

    def __init__(self, inner):
        self._inner, self.made, self.next = inner, [], None

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def new_page(self, **kw):
        page = clock.paced(self._inner.new_page(**kw))
        self.made.append(page)
        return page

    def new_context(self, **kw):
        ctx = Context(self._inner.new_context(**kw))
        self.made.append(ctx)
        return ctx

    def shut(self):
        """Every page and context the test made and left open."""
        left = 0
        for p in self.made:
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
        self.made.append(page)
        return made


class Context:
    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def new_page(self, **kw):
        return clock.paced(self._inner.new_page(**kw))
