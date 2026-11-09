"""The browser client is plain scripts sharing one global scope: check they parse, separately and together
(a name declared twice in two files only fails when the page loads them all)."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

WEB = Path(__file__).parent.parent / "src" / "megastructure" / "web"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def scripts() -> list[Path]:
    """The scripts index.html loads, in order."""
    names = re.findall(r'<script src="js/([\w.]+)"></script>', (WEB / "index.html").read_text())
    return [WEB / "js" / n for n in names]


def test_every_script_is_loaded_and_exists():
    loaded = {p.name for p in scripts()} | {"local.js"}           # local.js: only the Pages build loads it
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
