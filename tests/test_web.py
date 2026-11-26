"""The browser client is plain scripts sharing one global scope: check they parse, separately and together
(a name declared twice in two files only fails when the page loads them all)."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

WEB = Path(__file__).parent.parent / "src" / "nexel_worlds" / "web"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def scripts() -> list[Path]:
    """The scripts the page loads, in order (web/scripts.txt, named where index.html says: web_bundle.plain_page)."""
    from nexel_worlds.web_bundle import plain_page
    names = re.findall(r'<script src="js/([\w.]+)"></script>', plain_page(WEB))
    return [WEB / "js" / n for n in names]


def test_every_script_is_loaded_and_exists():
    loaded = {p.name for p in scripts()} | {"local.js", "local_worker.js"}   # (only the Pages build loads them)
    assert loaded == {p.name for p in (WEB / "js").glob("*.js")}


@pytest.mark.parametrize("path", scripts(), ids=lambda p: p.name)
def test_script_parses(path):
    r = subprocess.run([NODE, "--check", str(path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_scripts_parse_together(tmp_path):
    bundle = tmp_path / "bundle.js"
    bundle.write_text("\n".join(p.read_text() for p in scripts()))
    r = subprocess.run([NODE, "--check", str(bundle)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_the_page_s_scripts_have_one_owner():
    """index.html says where its scripts go and names none of them: their list and order are web/scripts.txt's alone, so a
    module split in parts adds lines there, not to the page (#203: the page was 299 lines of its 300, most of them scripts)."""
    page = (WEB / "index.html").read_text()
    assert "<script src=" not in page and page.count("<!-- scripts.txt -->") == 1
