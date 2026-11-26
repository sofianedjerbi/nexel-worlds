"""Every page a failing browser test opened has its picture (tests/e2e/pages.py, nexel-worlds#116): its own page, a
context's, the one it shut itself before the assert that failed; a test that passed leaves none."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "e2e"))
import pages  # noqa: E402


class Page:
    def __init__(self, log):
        self.log, self.shut = log, False

    def is_closed(self):
        return self.shut

    def screenshot(self, timeout=None):
        self.log.append("shot")
        return b"png"

    def close(self):
        self.shut = True


class Ctx:
    def __init__(self, log):
        self.log, self._pages = log, []

    @property
    def pages(self):
        return [p for p in self._pages if not p.shut]

    def new_page(self, **kw):
        p = Page(self.log)
        self._pages.append(p)
        return p

    def close(self):
        for p in self._pages:
            p.shut = True


class Browser:
    def __init__(self, log):
        self.log = log

    def new_page(self, **kw):
        return Page(self.log)

    def new_context(self, **kw):
        return Ctx(self.log)


def run(tmp_path, monkeypatch, failed, test):
    monkeypatch.setattr(pages, "SHOTS", tmp_path)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/e2e/test_x.py::test_y (call)")
    log = []
    b = pages.Pages(Browser(log))
    test(b)
    b.shut(failed=failed)
    return sorted(p.name for p in tmp_path.iterdir()), log


def own_pages(b):
    b.new_page().close()                                  # (shut before the assert that fails, as the title's tests do)
    b.new_page()                                          # (left open)
    ctx = b.new_context()
    ctx.new_page().close()
    ctx.new_page()
    ctx.close()


def test_a_failed_test_has_a_picture_of_every_page_it_opened(tmp_path, monkeypatch):
    names, log = run(tmp_path, monkeypatch, True, own_pages)
    assert len(names) == 4 and log == ["shot"] * 4, (names, log)
    assert "test_x.py_test_y.png" in names


def test_a_passed_test_leaves_no_picture_and_takes_none_of_the_pages_it_left_open(tmp_path, monkeypatch):
    names, log = run(tmp_path, monkeypatch, False, lambda b: b.new_page())
    assert names == [] and log == [] and pages.taken == []
