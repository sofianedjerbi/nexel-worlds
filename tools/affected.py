"""Which tests to run for what changed.

    PYTHONPATH=src .venv/bin/python tools/affected.py [files...] [--run] [--why]

Changed files: those given, or `git diff --name-only main...HEAD` plus the working tree's changes and new files.
Printed: the e2e test files to run (and the unit test files), one a line. The map is static, built each time:
- a web/js file: the e2e tests whose text names one of the globals it makes (top-level const/let/var/function/class,
  window.X =; names of 4 letters or more) or the file itself ("hd_sun.js"); an hd*.js or vox_*.js file: and every
  test_e2e_hd*.py; and the unit tests naming the file (a vox_* file: those naming vox_, test_vox_layer.py);
- a .css file: the ui, menu, title and phone tests; web/index.html: those and the e2e tests naming an id it has changed (not
  read: all of the ui set);
- a python file of the game (src/megastructure/**.py, not web/): the unit tests that name its module, all of them if
  none does, and the server-facing e2e (tests naming the module, test_e2e_world.py, test_e2e_edits.py);
- a test file: itself; a helper of tests/e2e (game.py, waits.py, conftest.py...): the quick set only (below).
--run: the e2e files with `pytest -m e2e -n 3`, then the quick set (`-m "e2e and quick"`), then the unit files, each
with stdin from /dev/null. Exit code: the first run that failed."""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = "src/megastructure/web/js/"
E2E = "tests/e2e/"
UI_SET = ("test_e2e_ui.py", "test_e2e_menu.py", "test_e2e_title.py", "test_e2e_title_scene.py", "test_e2e_phone.py",
          "test_e2e_phone_taps.py", "test_e2e_hd_phone.py", "test_e2e_touch.py", "test_e2e_help.py")
SERVER_E2E = ("test_e2e_world.py", "test_e2e_edits.py")
TOP = re.compile(r"^(?:const|let|var)\s+([A-Za-z_$][\w$]*)|^(?:async\s+)?function\*?\s+([A-Za-z_$][\w$]*)|^class\s+([A-Za-z_$][\w$]*)"
                 r"|^window\.([A-Za-z_$][\w$]*)\s*=|^(?:const|let|var)\s+\{([^}]*)\}\s*=", re.M)


def globals_of(text: str) -> set[str]:
    """The names a plain script makes global (its top-level declarations), 4 letters or more."""
    out = set()
    for m in TOP.finditer(text):
        if m.group(5):
            out |= {n.split(":")[-1].strip() for n in m.group(5).split(",")}
        else:
            out.add(next(g for g in m.groups() if g))
    return {n for n in out if len(n) >= 4}


def mentions(text: str, names) -> list[str]:
    return [n for n in names if re.search(r"(?<![\w$])" + re.escape(n) + r"(?![\w$])", text)]


def named(text: str, filename: str) -> bool:
    """Does the text name the file ("hd_sun.js"; not a call like game.js(...))?"""
    return re.search(r"(?<![\w$])" + re.escape(filename) + r"(?![\w$(])", text) is not None


def tests(root: Path, kind="e2e") -> dict[str, str]:
    """test file (repo path) -> its text"""
    pat = (root / E2E).glob("test_e2e_*.py") if kind == "e2e" else (root / "tests").glob("test_*.py")
    return {str(p.relative_to(root)): code(p.read_text(errors="replace")) for p in sorted(pat)}


DOC = re.compile(r'^[ \t]*[rbu]?("""|\'\'\')[\s\S]*?\1', re.M)       # a docstring: a triple-quoted string that is a statement
NOTE = re.compile(r"(?:^|(?<=\s\s))#\s.*$", re.M)                    # a comment ("  # ..." or a line of one; not '#tA' in a selector)


def code(text: str) -> str:
    """A test's text without its docstrings and comments: the names it uses, not the words it says ("said", "xray")."""
    return NOTE.sub("", DOC.sub("", text))


def affected(changed, root: Path = ROOT, why=None):
    """(e2e test files, unit test files, quick: bool) for the changed files (repo paths)."""
    e2e, unit, quick = set(), set(), False
    why = {} if why is None else why
    E, U = tests(root, "e2e"), tests(root, "unit")

    def add(s, f, reason):
        s.add(f)
        why.setdefault(f, reason)
    for f in changed:
        p = Path(f)
        name = p.name
        if f.startswith(E2E):
            if name.startswith("test_e2e_") and name.endswith(".py"):
                if (root / f).exists():
                    add(e2e, f, "changed")
            else:
                quick = True                                   # (a helper: the quick set tries every area)
            continue
        if f.startswith("tests/") and name.startswith("test_") and name.endswith(".py"):
            if (root / f).exists():
                add(unit, f, "changed")
            continue
        if f.startswith(JS) and name.endswith(".js"):
            names = globals_of((root / f).read_text(errors="replace")) if (root / f).exists() else set()
            for t, text in E.items():
                hit = mentions(text, names) or ([name] if named(text, name) else [])
                if hit:
                    add(e2e, t, f"{name}: {hit[0]}")
            for t, text in U.items():
                if named(text, name) or (name.startswith("vox_") and "vox_" in text):
                    add(unit, t, f"{name}: named")
            if name.startswith(("hd", "vox_")):
                for t in E:
                    if Path(t).name.startswith("test_e2e_hd"):
                        add(e2e, t, f"{name}: the HD look")
            continue
        if name.endswith(".css") or (f.startswith("src/megastructure/web/") and name.endswith(".html")):
            for t in E:
                if Path(t).name in UI_SET:
                    add(e2e, t, f"{name}: the screen's layout")
            continue
        if f.startswith("src/megastructure/") and name.endswith(".py") and "/web/" not in f:
            mod = p.stem
            hit = [t for t, text in U.items() if re.search(r"(?<!\w)" + re.escape(mod) + r"(?!\w)", text)]
            for t in hit or U:
                add(unit, t, f"{name}" + ("" if hit else ": no unit test names it"))
            for t, text in E.items():
                if Path(t).name in SERVER_E2E or re.search(r"(?<!\w)" + re.escape(mod) + r"(?!\w)", text):
                    add(e2e, t, f"{name}: the server")
    return sorted(e2e), sorted(unit), quick


def git_changed(root: Path = ROOT) -> list[str]:
    def run(*a):
        r = subprocess.run(["git", *a], cwd=root, capture_output=True, text=True)
        return r.stdout.split("\n") if r.returncode == 0 else []
    files = run("diff", "--name-only", "main...HEAD") + run("diff", "--name-only", "HEAD") + run("ls-files", "--others", "--exclude-standard")
    return sorted({f.strip() for f in files if f.strip()})


def pytest(args):
    py = str(ROOT / ".venv" / "bin" / "python") if (ROOT / ".venv").exists() else str(Path.home() / "megastructure/.venv/bin/python")
    cmd = [py, "-m", "pytest", *args]
    print("$", " ".join(cmd[1:]), flush=True)
    with open("/dev/null") as nul:
        return subprocess.run(cmd, cwd=ROOT, stdin=nul, env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")}).returncode


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("files", nargs="*", help="changed files (repo paths); default: git's")
    a.add_argument("--run", action="store_true", help="run them (-n 3) and the quick set")
    a.add_argument("--why", action="store_true", help="say why each test is there")
    o = a.parse_args(argv)
    changed = o.files or git_changed()
    why = {}
    e2e, unit, quick = affected(changed, ROOT, why)
    print(f"# {len(changed)} changed file(s) -> {len(e2e)} e2e, {len(unit)} unit" + (" (a test helper changed: the quick set)" if quick else ""))
    for f in e2e + unit:
        print(f + (f"    # {why[f]}" if o.why else ""))
    if not o.run:
        return 0
    rc = 0
    if e2e:
        rc = pytest(["-m", "e2e", "-n", "3", *e2e]) or rc
    rc = pytest(["-m", "e2e and quick", "-n", "3", E2E]) or rc
    if unit:
        rc = pytest(["-q", "-n", "3", *unit]) or rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
