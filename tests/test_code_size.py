"""Keep files small enough to read: every source file stays under MAX_LINES (split by concern when one grows)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
MAX_LINES = 300
FILES = sorted(p for d in ("src", "tests", "tools") for ext in ("py", "js", "css", "html")
               for p in (ROOT / d).rglob(f"*.{ext}") if "__pycache__" not in p.parts)


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_file_is_small_enough(path):
    n = len(path.read_text().splitlines())
    assert n <= MAX_LINES, f"{path.relative_to(ROOT)} has {n} lines (max {MAX_LINES}): split it by concern"
