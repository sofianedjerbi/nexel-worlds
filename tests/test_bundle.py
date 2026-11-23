"""The client as few files (web_bundle.py), what the server sends (web_static.py), and Python's library for the demo
(tools/build_stdlib.py): the bundle says what the plain files say, a picture in the pack is its file, nothing the
game uses is left out of the library."""

import gzip
import shutil
import sys
import types
import zipfile
from pathlib import Path

import pytest

from megastructure import art, web_bundle, web_static

ROOT = Path(__file__).parent.parent
WEB = ROOT / "src" / "megastructure" / "web"
sys.path.insert(0, str(ROOT / "tools"))
import build_stdlib  # noqa: E402

needs_art = pytest.mark.skipif(not art.installed(), reason="the Sprout Lands art is not installed (tools/install_assets.py, README 'Art')")


def test_notes_and_indents_go_and_strings_templates_and_regular_expressions_stay():
    src = ("const a = `x // not a note\n   ${b ? `in // ner ${ {c: 1}.c }` : 2} y`; // gone\n"
           "  const r = /['\"/]\\//.test(s) ? 1 / 2 : \"http://x\"; /* gone */ let u = 'a//b';\n\n\n   f(); // c\n"
           "  return /\\/\\/ kept/.test(q) || q.split(/[/*]+/);\n  const d = (a + b) / 2; // half\n  x = y / z; // gone\n")
    out = web_bundle.strip(src)
    assert out == ("const a = `x // not a note\n   ${b ? `in // ner ${ {c: 1}.c }` : 2} y`;\n"
                   "const r = /['\"/]\\//.test(s) ? 1 / 2 : \"http://x\";  let u = 'a//b';\nf();\n"
                   "return /\\/\\/ kept/.test(q) || q.split(/[/*]+/);\nconst d = (a + b) / 2;\nx = y / z;\n")


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_one_script_is_every_script_smaller_and_node_reads_it():
    page = (WEB / "index.html").read_text()
    names = web_bundle.SCRIPT.findall(page)
    js = web_bundle.script(WEB, page)
    plain = sum(len((WEB / "js" / n).read_text()) for n in names)
    assert len(names) > 90 and web_bundle.checked(js) and len(js) < .8 * plain
    for n in names:                                         # (each file's code is there: its longest line of code, to the letter)
        line = max((s.strip() for s in web_bundle.strip((WEB / "js" / n).read_text()).split("\n")), key=len)
        assert line in js, n


def test_the_one_script_is_cut_at_files_starts_into_parts_of_about_the_same_size():
    """Each part is run as a script of its own, a task of its own: the page answers between them (index.html's wait moves).
    A part begins where a file does: the files share the page's scope as the plain ones do in development."""
    page = (WEB / "index.html").read_text()
    starts = []
    js = web_bundle.script(WEB, page, starts=starts).encode()
    cut = web_bundle.cuts(starts, len(js))
    assert len(cut) == 3 and all(c in starts for c in cut) and cut == sorted(cut)
    sizes = [b - a for a, b in zip([0] + cut, cut + [len(js)])]
    assert max(sizes) < len(js) / 2, sizes
    assert all(js[c - 2:c] == b";\n" for c in cut)           # (between two files)


@needs_art
def test_the_page_names_one_script_and_the_pack_holds_each_picture_as_its_file():
    page, files = web_bundle.packed(WEB)
    (js_name, js), (pack_name, pack) = files.items()
    # (the one script is read by the page itself, its bytes counted for the wait's bar, and run where its tag was: no tag of it)
    assert page.count("<script src=") == 0 and f'"game":"{js_name}"' in page and '<link rel="stylesheet"' not in page
    assert js_name.startswith("js/game.") and pack_name.startswith("assets/pack.") and web_bundle.mark(js) in js_name and web_bundle.mark(pack) in pack_name
    assert page.index("window.ASSET_PACK") < page.index("</head>") < page.index('<div id="joinbox"') < page.index("ASSET_PACK.run()") < page.index("</body>")
    _, table, need = web_bundle.pack(WEB)
    assert len(table) > 60 and "gen.txt" in table
    late = web_bundle.late(WEB)                 # (the sheets the first screen never shows: after all the others, past what it waits for)
    assert "emoji.png" in late and "character.png" not in late and all((table[n][0] >= need) == (n in late) for n in table)
    for name, (at, size) in table.items():
        assert pack[at:at + size] == (WEB / "assets" / name).read_bytes(), name
    assert "url(../" not in page and "url(assets/panel.png)" in page          # (the styles are in the page: their pictures from where the page is)


class Ask:
    def __init__(self, path, **headers):
        self.path, self.headers = path, types.SimpleNamespace(get=lambda k, d="": {k.lower(): v for k, v in headers.items()}.get(k.lower(), d))


@needs_art
def test_the_server_sends_text_packed_and_says_not_modified(monkeypatch):
    plain = web_static.serve_http(None, Ask("/js/state.js"))
    assert plain.status_code == 200 and "Content-Encoding" not in plain.headers and plain.body == (WEB / "js" / "state.js").read_bytes()
    small = web_static.serve_http(None, Ask("/js/state.js", **{"Accept-Encoding": "gzip, deflate"}))
    assert small.headers["Content-Encoding"] == "gzip" and gzip.decompress(small.body) == plain.body and len(small.body) < len(plain.body) / 2
    assert small.headers["ETag"] == plain.headers["ETag"] and small.headers["Cache-Control"] == "no-cache"
    again = web_static.serve_http(None, Ask("/js/state.js", **{"If-None-Match": plain.headers["ETag"]}))
    assert again.status_code == 304 and again.body == b""
    art = web_static.serve_http(None, Ask("/assets/grass.png", **{"Accept-Encoding": "gzip"}))
    assert "Content-Encoding" not in art.headers and art.body == (WEB / "assets" / "grass.png").read_bytes()      # (a picture is packed already)
    page = web_static.serve_http(None, Ask("/"))
    assert page.body.count(b"<script src=") > 90                                # (the plain files, unless asked)
    monkeypatch.setattr(web_static, "BUNDLE", [True])
    page = web_static.serve_http(None, Ask("/", **{"Accept-Encoding": "gzip"}), accounts="http://a")
    body = gzip.decompress(page.body).decode()
    assert body.count("<script src=") == 0 and body.count("ASSET_PACK.run()") == 1 and '<body data-accounts="http://a">' in body and page.headers["Cache-Control"] == "no-cache"
    name = body.split('"game":"')[1].split('"')[0]
    js = web_static.serve_http(None, Ask("/" + name, **{"Accept-Encoding": "gzip"}))
    assert js.status_code == 200 and "immutable" in js.headers["Cache-Control"] and b"function joinGame" in gzip.decompress(js.body)
    pack = web_static.serve_http(None, Ask("/" + body.split('"url":"')[1].split('"')[0]))
    assert pack.status_code == 200 and pack.headers["Content-Type"] == "application/octet-stream" and len(pack.body) > 300000


def test_no_sounds_built_is_said_without_an_error(monkeypatch, tmp_path):
    """A checkout with no sounds built (they are not in git): the page asks for their list and plays without them.
    The answer was a 404: an error in every page's console (the bundle's browser test failed on it)."""
    (tmp_path / "audio").mkdir()
    monkeypatch.setattr(web_static, "WEB", tmp_path)
    r = web_static.serve_http(None, Ask("/audio/sfx.json"))
    assert r.status_code == 204 and r.body == b""


def test_nothing_the_game_uses_is_left_out_of_pythons_library(tmp_path):
    used = (ROOT / "tools" / "stdlib_used.txt").read_text().split()
    assert len(used) > 150 and "asyncio" in used and "json.decoder" in used
    for m in used:                                           # (a module is a file or a folder of the library; built-in ones are in neither)
        top = m.split(".")[0]
        assert top not in build_stdlib.DROP and top + ".py" not in build_stdlib.DROP, m
        if top == "encodings" and "." in m:
            assert m.split(".")[1] in build_stdlib.KEEP_CODES, m
    full = tmp_path / "full.zip"
    with zipfile.ZipFile(full, "w") as z:
        for name in ("os.py", "json/__init__.py", "encodings/utf_8.py", "encodings/cp932.py", "unittest/__init__.py", "pdb.py", "email/__init__.py"):
            z.writestr(name, "x = 1\n")
    assert build_stdlib.trim(full, tmp_path / "out.zip") == (4, 7)
    assert zipfile.ZipFile(tmp_path / "out.zip").namelist() == ["os.py", "json/__init__.py", "encodings/utf_8.py", "email/__init__.py"]
    first = (tmp_path / "out.zip").read_bytes()
    build_stdlib.trim(full, tmp_path / "out.zip")
    assert (tmp_path / "out.zip").read_bytes() == first      # (the same files: the same bytes, the same name in the build)
