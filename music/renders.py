"""The game's music, rendered again only where what makes it has changed (tools/build_game.sh, and CI's cache of
site/audio: .github/workflows/game.yml).

    python3 music/renders.py          # render what is stale, then master and refit if anything was
    python3 music/renders.py stale    # print what is stale (nothing printed: all is fresh), render nothing

Each render is one entry of a script's list (a piece of pieces.py, a palette of bright.py, a take of slowtide.py), and
its fingerprint is that entry and the code that plays it: the script and the music modules it imports, read as code
(a comment changes nothing), every list of entries left out but the entry's own. So a new piece, or one piece's sounds
changed, renders that piece alone; a change to surge.py or to how pieces.py plays renders all that use it. The
fingerprints are kept in site/audio/stamps.json beside the renders. Plain Python: no packages, to plan without them.
"""

import ast
import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "site" / "audio"
STAMPS = OUT / "stamps.json"
SURGE = ["uv", "run", "--no-project", "--python", "3.11", "--with", "dawdreamer", "--with", "numpy", "python"]   # (DawDreamer hosts Surge XT: 3.11)
AUDIO = ["uv", "run", "--extra", "audio", "python"]
LISTS = {"PIECES", "PALETTES", "VARIANTS"}              # the lists of entries, one render each
RENDERS = [  # script, its list, the entries the game plays (master.py reads them all: far shore night D too), the file each writes
    ("pieces.py", "PIECES", ["cute1", "shore", "mc1", "shore_night_c", "shore_night_d", "mossback2"], "piece_{}"),
    ("adventure.py", "PIECES", ["trail"], "piece_{}"),
    ("bright.py", "PALETTES", ["dream"], "bright_{}"),
    ("slowtide.py", "VARIANTS", ["high", "full"], "menu_tide_{}"),
    ("rush.py", "VARIANTS", ["nyxwing"], "rush_{}"),
]
AFTER = [("master.py", AUDIO, "final_bright_dream"), ("refit.py", SURGE, "fixed_old_mossback")]   # (and a file each writes)


def is_list(node) -> bool:
    """PIECES = [...] or VARIANTS.append(...): entries, not code."""
    if isinstance(node, ast.Assign):
        return any(isinstance(t, ast.Name) and t.id in LISTS for t in node.targets)
    return (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
            and isinstance(node.value.func.value, ast.Name) and node.value.func.value.id in LISTS)


def code(name: str, seen: set) -> str:
    """The script, then every music module it imports (once each), as code, their lists of entries left out."""
    path = HERE / name
    if name in seen or not path.exists():
        return ""
    seen.add(name)
    tree = ast.parse(path.read_text())
    used = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    used |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    own = "\n".join(ast.unparse(n) for n in tree.body if not is_list(n))
    return f"# {name}\n{own}\n" + "".join(code(m + ".py", seen) for m in sorted(used))


def entry(script: str, item: str) -> str:
    """One entry of the script's lists: its dict(id=...), as code."""
    for n in ast.walk(ast.parse((HERE / script).read_text())):
        if isinstance(n, ast.Call) and any(k.arg == "id" and isinstance(k.value, ast.Constant) and k.value.value == item for k in n.keywords):
            return ast.unparse(n)
    raise SystemExit(f"music/{script} has no entry {item!r}")


def mark(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def plan() -> tuple[list, dict]:
    """The renders that are stale ((script, entry, file)), and every fingerprint as it is now."""
    old = json.loads(STAMPS.read_text()) if STAMPS.exists() else {}
    if not old and (OUT / ".stamp").exists():          # (renders made before stamps.json, under one stamp for them all: taken as they are, once)
        old = {f.format(i): None for _, _, items, f in RENDERS for i in items} | {s: None for s, _, _ in AFTER}
    now, stale = {}, []
    for script, _, items, file in RENDERS:
        shared = code(script, set())
        for i in items:
            f = file.format(i)
            now[f] = mark(shared + entry(script, i))
            if (old.get(f, "") not in (now[f], None)) or not (OUT / f"{f}.wav").exists():
                stale.append((script, i, f))
    for script, _, f in AFTER:
        now[script] = mark(code(script, set()))
        if stale or old.get(script, "") not in (now[script], None) or not (OUT / f"{f}.wav").exists():
            stale.append((script, None, script))
    return stale, now


def run(cmd: list):
    """A render job, an hour at most: one that fails can hang on its way out (Surge's threads keep it alive)."""
    p = subprocess.Popen(cmd, cwd=HERE.parent, start_new_session=True)
    try:
        code = p.wait(timeout=3600)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        raise SystemExit(f"{' '.join(cmd[-2:])}: still running after an hour")
    if code:
        raise SystemExit(code)


def build():
    stale, now = plan()
    if not stale:                                      # (fresh: their fingerprints are what they are now, kept so)
        STAMPS.write_text(json.dumps(now, indent=1))
        (OUT / ".stamp").unlink(missing_ok=True)
        return print("music: every render is fresh")
    OUT.mkdir(parents=True, exist_ok=True)              # (not in git: a fresh checkout has no music/site/audio)
    done = json.loads(STAMPS.read_text()) if STAMPS.exists() else {}
    for script, _, items, _ in RENDERS:                # one script after the other: each loads dozens of Surge instances
        todo = [(i, f) for s, i, f in stale if s == script]
        if todo:
            print(f"music: rendering {script} {' '.join(i for i, _ in todo)}", flush=True)
            run(SURGE + [f"music/{script}"] + [i for i, _ in todo])
            done |= {f: now[f] for _, f in todo}
            STAMPS.write_text(json.dumps(done, indent=1))
    for script, cmd, _ in AFTER:
        run(cmd + [f"music/{script}"])
        done[script] = now[script]
    STAMPS.write_text(json.dumps(done, indent=1))
    (OUT / ".stamp").unlink(missing_ok=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["stale"]:
        print(" ".join(f for _, _, f in plan()[0]))
    else:
        build()
