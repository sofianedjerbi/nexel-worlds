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


def script(web: Path, page: str, skip=(), starts: list | None = None) -> str:
    """Every script the page names, one after the other. starts: filled with where each file begins in it (bytes)."""
    names = [n for n in SCRIPT.findall(page) if n not in skip]
    plain = [(web / "js" / n).read_text() for n in names]
    small = [strip(t) for t in plain]
    parts = small if checked(";\n".join(small) + "\n") else plain
    if starts is not None:
        at = 0
        for p in parts:
            starts.append(at)
            at += len(p.encode()) + 2
    return ";\n".join(parts) + "\n"


def cuts(starts: list[int], size: int, n: int = 4) -> list[int]:
    """Where to cut the one script into n of about the same size, each at a file's start: each is run as a script of its own,
    a task of its own (the page's thread answers between them; one script of all was one task of 0.18 s on a phone's CPU)."""
    out = []
    for k in range(1, n):
        at = min(starts, key=lambda s: abs(s - size * k / n))
        if 0 < at < size and at not in out:
            out.append(at)
    return sorted(out)


def pictures(web: Path) -> list[str]:
    """The files assets.js asks for at the start, in its order: the sheets, and the generated sheet's names."""
    src = (web / "js" / "assets.js").read_text()
    lists = dict(re.findall(r"const (ANIMAL_SHEETS|ASSETS) = \[(.*?)\];", src, re.S))
    names = re.findall(r'"(\w+)"', lists["ANIMAL_SHEETS"]) + re.findall(r'"(\w+)"', lists["ASSETS"])
    assert len(names) > 60 and "character" in names, "assets.js no longer lists its sheets"
    return [n + ".png" for n in names] + ["gen.txt"]


def late(web: Path) -> set[str]:
    """The sheets the first screen does not wait for (assets.js LATE)."""
    m = re.search(r"const LATE = \[(.*?)\];", (web / "js" / "assets.js").read_text())
    assert m, "assets.js no longer lists its late sheets"
    return {n + ".png" for n in re.findall(r'"(\w+)"', m.group(1))}


def pack(web: Path) -> tuple[bytes, dict, int]:
    """The pictures one after the other -> the bytes, where each is, and how many bytes the first screen waits for:
    the sheets it shows first, the ones it never shows (assets.js LATE) after them, as the page reads them as they come."""
    body, table, after = b"", {}, late(web)
    for name in sorted(pictures(web), key=lambda n: n in after):
        raw = (web / "assets" / name).read_bytes()
        table[name] = [len(body), len(raw)]
        body += raw
    return body, table, min([table[n][0] for n in after] or [len(body)])


def mark(*parts: bytes) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(p)
    return h.hexdigest()[:10]


def packed(web: Path, page: str | None = None, skip=(), inline_styles=True) -> tuple[str, dict[str, bytes]]:
    """The page with one script, its styles in it and the pack's table; and the files it now names: path -> bytes."""
    import gzip
    page = (web / "index.html").read_text() if page is None else page
    starts = []
    js = script(web, page, skip, starts).encode()
    body, table, need = pack(web)
    names = {"js": f"js/game.{mark(js)}.js", "pack": f"assets/pack.{mark(body)}.bin"}
    first = SCRIPT.search(page)
    assert first, "index.html names no script"
    # (the pack is asked for here, as the page is read; its bytes counted as they come: the wait's bar, index.html #boot.
    #  upto(n): the bytes so far once n of them are in: each picture is made as soon as its own have come, assets.js;
    #  need: the first screen's share, the world starts to come after it, local.js)
    # (and the game's script (`game`) the same way, from here: read as it comes (jsGot of jsLen; js: its bytes on the line), then run where its tag was
    #  (run(): the page read to there) as a script of its own (a blob's address: a script, not an eval). It was a tag: no byte of it was counted
    #  till it had run, and the bar leapt a third of its length. Run after the page is read, its DOMContentLoaded is said again for it (options.js waits
    #  for it); if it cannot be read so, the tag as it was)
    tell = (f'<script>window.ASSET_PACK = {json.dumps({"url": names["pack"], "files": table, "size": len(body), "need": need, "game": names["js"], "js": len(gzip.compress(js)), "jsLen": len(js), "cuts": cuts(starts, len(js))}, separators=(",", ":"))};\n'
            'ASSET_PACK.got = 0; ASSET_PACK.parts = []; ASSET_PACK.jsGot = 0; (() => { const P = ASSET_PACK, wait = [], all = (b) => wait.splice(0).forEach((w) => w[1](b));\n'
            '  const go = () => { if (!P.here || P.code === undefined || P.ran) return; P.ran = true; const at = [0, ...P.cuts, P.jsLen];   // (each part a task of its own: web_bundle.py cuts)\n'
            '    const one = (i) => { const s = document.createElement("script"), last = !P.code || i + 2 >= at.length; s.src = P.code ? URL.createObjectURL(P.code.slice(at[i], at[i + 1], "text/javascript")) : P.game;\n'
            '      s.onload = () => { if (!last) return one(i + 1); if (document.readyState !== "loading") document.dispatchEvent(new Event("DOMContentLoaded", {bubbles: true})); }; document.body.appendChild(s); };\n'
            '    one(0); };\n'
            '  P.run = () => { P.here = true; go(); };\n'
            '  fetch(P.game).then(async (r) => { if (!r.ok || !r.body) throw new Error(r.status); const rd = r.body.getReader(), l = [];   // (asked for first: it runs while the pictures come)\n'
            '    for (;;) { const {done, value} = await rd.read(); if (done) break; l.push(value); P.jsGot += value.length; } return new Blob(l, {type: "text/javascript"}); })\n'
            '    .catch(() => null).then((b) => { P.code = b; go(); });\n'
            '  const sofar = () => P.bn === P.parts.length ? P.bb : (P.bn = P.parts.length, P.bb = new Blob(P.parts));   // (one blob of what has come, not one a picture: 70 of them were 40 ms of a phone\'s first script)\n'
            '  P.upto = (n) => P.got >= n && P.parts.length ? Promise.resolve(sofar()) : P.done ? P.blob : new Promise((ok) => wait.push([n, ok]));\n'
            '  P.blob = fetch(P.url).then(async (r) => { if (!r.ok) throw new Error(r.status); if (!r.body) return r.blob();\n'
            '    const rd = r.body.getReader(); for (;;) { const {done, value} = await rd.read(); if (done) break; P.parts.push(value); P.got += value.length;\n'
            '      if (wait.some((w) => w[0] <= P.got)) { const b = sofar(); for (let i = wait.length; i--;) if (wait[i][0] <= P.got) wait.splice(i, 1)[0][1](b); } }\n'
            '    return new Blob(P.parts); }).catch(() => null).then((b) => { P.done = true; all(b); return b; }); })();</script>\n')
    page = page[:first.start()] + "<script>ASSET_PACK.run();</script>\n" + SCRIPT.sub(lambda m: m.group(0) if m.group(1) in skip else "", page[first.start():])
    if inline_styles:
        page, n = STYLE.subn(lambda m: "<style>\n" + (web / "css" / m.group(1)).read_text().replace("url(../", "url(") + "</style>\n", page)
        assert n >= 5, "index.html no longer names its styles"
    assert page.count("</head>") == 1
    return page.replace("</head>", tell + "</head>"), {names["js"]: js, names["pack"]: body}
