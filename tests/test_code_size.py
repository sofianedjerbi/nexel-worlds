"""Keep files small enough to read: every source file stays under MAX_LINES (split by concern when one grows)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
MAX_LINES = 300
RENDER_MAX = 500        # (the HD look's renderer files: hd*.js, vox_*.js. The owner, 2026-11-21, to go faster: every fix to a full renderer file had to split it first)
FILES = sorted(p for d in ("src", "tests", "tools") for ext in ("py", "js", "css", "html")
               for p in (ROOT / d).rglob(f"*.{ext}") if "__pycache__" not in p.parts)


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_file_is_small_enough(path):
    n, top = len(path.read_text().splitlines()), RENDER_MAX if path.suffix == ".js" and path.name.startswith(("hd", "vox_")) else MAX_LINES
    assert n <= top, f"{path.relative_to(ROOT)} has {n} lines (max {top}): split it by concern"
