"""The browser client as few files: one script, the styles in the page, the pictures in one pack.

The client is a hundred plain scripts and seventy small pictures, each named in index.html or assets.js: good to work on,
slow to fetch (a phone asked two hundred times before its first land). For the online demo (tools/build_pages.py) and
for a server started with `--bundle` (web_static.py) the same files are sent as:

    js/game.js       every script index.html names, in its order, without notes or indents (`strip`)
    assets/pack.bin  every picture assets.js loads, end to end; the page is told where each lies (`ASSET_PACK`)
    the page         with its styles in it, the one script, and the pack's table

Nothing is changed in what the files say: the scripts share one global scope in a page, and do so in one file; a
picture's bytes are its file's. Development and the tests keep the plain files.
"""

import hashlib
import json
import re
from pathlib import Path

SCRIPT = re.compile(r'<script src="js/([\w.]+)"></script>\n')
STYLE = re.compile(r'<link rel="stylesheet" href="css/([\w.]+)">\n?')
# after one of these a "/" begins a regular expression; after a name, a number or a closing bracket it divides
BEFORE_REGEX = set("(,=:[!&|?{};+-*%<>~^")
NAME, TRIM = re.compile(r"[\w$]+"), re.compile(r"[ \t]*\n\s*")
WORDS_BEFORE_REGEX = {"return", "typeof", "case", "in", "of", "void", "delete", "throw", "new", "else", "do"}


def strip(js: str) -> str:
    """The script without its notes, its indents and its empty lines. Strings, templates (the shaders) and regular
    expressions are left to the letter; lines stay lines (a line's end can end a statement)."""
    out, code, i, n, last, word, depth = [], [], 0, len(js), "", "", []    # last: the code character before ("a": a name's or a bracket's end)

    def raw(j):                                              # js[i:j] as it is, after the code before it
        out.append(TRIM.sub("\n", "".join(code))); code.clear(); out.append(js[i:j])
        return j, "a", ""

    while i < n:
        c = js[i]
        if c in "\"'":
            j = i + 1
            while j < n and js[j] != c:
                j += 2 if js[j] == "\\" else 1
            i, last, word = raw(j + 1)
        elif c == "`" or (c == "}" and depth and depth[-1] == 0):
            if c == "}":
                depth.pop()
            j = i + 1
            while j < n and js[j] != "`" and js[j:j + 2] != "${":
                j += 2 if js[j] == "\\" else 1
            if js[j:j + 2] == "${":
                depth.append(0); i, last, word = raw(j + 2); last = "("
            else:
                i, last, word = raw(j + 1)
        elif js[i:i + 2] == "//":
            while i < n and js[i] != "\n":
                i += 1
        elif js[i:i + 2] == "/*":
            i = js.index("*/", i) + 2
        elif c == "/" and (last == "" or last in BEFORE_REGEX or word in WORDS_BEFORE_REGEX):
            j, cls = i + 1, False
            while j < n and (js[j] != "/" or cls):
                cls = (cls or js[j] == "[") and js[j] != "]"
                j += 2 if js[j] == "\\" else 1
            i, last, word = raw(j + 1)
        elif m := NAME.match(js, i):
            code.append(m.group()); i, last, word = m.end(), "a", m.group()
        else:
            if depth and c in "{}":
                depth[-1] += 1 if c == "{" else -1
            if not c.isspace():
                last, word = ("a" if c in ")]" else c), ""
            code.append(c); i += 1
    out.append(TRIM.sub("\n", "".join(code)))
    return "".join(out).strip() + "\n"


def checked(js: str) -> bool:
    """Does node read it as a script? (No node: not known, taken as no: the plain text is sent.)"""
    import shutil
    import subprocess
    import tempfile
    if not shutil.which("node"):
        return False
    with tempfile.NamedTemporaryFile("w", suffix=".js") as f:
        f.write(js); f.flush()
        return subprocess.run(["node", "--check", f.name], capture_output=True).returncode == 0


def script(web: Path, page: str, skip=()) -> str:
    """Every script the page names, one after the other."""
    names = [n for n in SCRIPT.findall(page) if n not in skip]
    plain = ";\n".join((web / "js" / n).read_text() for n in names) + "\n"
    small = ";\n".join(strip((web / "js" / n).read_text()) for n in names) + "\n"
    return small if checked(small) else plain


def pictures(web: Path) -> list[str]:
    """The files assets.js asks for at the start, in its order: the sheets, and the generated sheet's names."""
    src = (web / "js" / "assets.js").read_text()
    lists = dict(re.findall(r"const (ANIMAL_SHEETS|ASSETS) = \[(.*?)\];", src, re.S))
    names = re.findall(r'"(\w+)"', lists["ANIMAL_SHEETS"]) + re.findall(r'"(\w+)"', lists["ASSETS"])
    assert len(names) > 60 and "character" in names, "assets.js no longer lists its sheets"
    return [n + ".png" for n in names] + ["gen.txt"]


def pack(web: Path) -> tuple[bytes, dict]:
    body, table = b"", {}
    for name in sorted(pictures(web), key=lambda n: n != "character.png"):     # (the cat's sheet first: the wait's cat walks from the pack's first 21 KB, js/loading.js)
        raw = (web / "assets" / name).read_bytes()
        table[name] = [len(body), len(raw)]
        body += raw
    return body, table


def mark(*parts: bytes) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(p)
    return h.hexdigest()[:10]


def packed(web: Path, page: str | None = None, skip=(), inline_styles=True) -> tuple[str, dict[str, bytes]]:
    """The page with one script, its styles in it and the pack's table; and the files it now names: path -> bytes."""
    import gzip
    page = (web / "index.html").read_text() if page is None else page
    js = script(web, page, skip).encode()
    body, table = pack(web)
    names = {"js": f"js/game.{mark(js)}.js", "pack": f"assets/pack.{mark(body)}.bin"}
    first = SCRIPT.search(page)
    assert first, "index.html names no script"
    # (the pack is asked for here, as the page is read; its bytes counted as they come, and the script's when it has
    #  come: the wait's cat walks as far, js/loading.js)
    tell = (f'<script>window.ASSET_PACK = {json.dumps({"url": names["pack"], "files": table, "size": len(body), "js": len(gzip.compress(js))}, separators=(",", ":"))};\n'
            'ASSET_PACK.got = 0; ASSET_PACK.blob = fetch(ASSET_PACK.url).then(async (r) => { if (!r.ok) throw new Error(r.status); if (!r.body) return r.blob();\n'
            '  const rd = r.body.getReader(), parts = ASSET_PACK.parts = []; for (;;) { const {done, value} = await rd.read(); if (done) break; parts.push(value); ASSET_PACK.got += value.length; } return new Blob(parts); }).catch(() => null);</script>\n')
    page = page[:first.start()] + f'<script src="{names["js"]}"></script>\n' + SCRIPT.sub(lambda m: m.group(0) if m.group(1) in skip else "", page[first.start():])
    if inline_styles:
        page, n = STYLE.subn(lambda m: "<style>\n" + (web / "css" / m.group(1)).read_text().replace("url(../", "url(") + "</style>\n", page)
        assert n >= 5, "index.html no longer names its styles"
    assert page.count("</head>") == 1
    return page.replace("</head>", tell + "</head>"), {names["js"]: js, names["pack"]: body}
