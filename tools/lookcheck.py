"""The HD look's scenes, shot the same way every time, against the last accepted set.

    PYTHONPATH=src .venv/bin/python tools/lookcheck.py [--accept] [--only meadow,cave] [--out DIR] [--jobs 3]

Each scene (tools/lookcheck_scenes.py: title, meadow, village, mountain, night, walls, build mode, stair, pit, shafts,
room, cave, gorge, way out) on the desk screen (1440x900) and the phone's (390x844, DPR 3), staged with dev ops on a
server copy of its own (free port, temp saves, seed 12: never 7777), the page's clock frozen for the shot. Up to
`--jobs` browsers at once, one per group of scenes and screen. Out: DIR/<scene>_<screen>.png, DIR/diff_*.png where a
scene changed, DIR/sheet.png (a changed scene has a red frame and its %), a one-line table. The accepted set is
.lookcheck/accepted/ (gitignored); --accept makes this run's shots the accepted ones."""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path


def _pillow():
    """Pillow: the venv's, or (it has none) the one of a python3 on this Mac of the same version, its folder added
    at the end of the path (no download, no uv)."""
    try:
        import PIL  # noqa: F401
        return
    except ImportError:
        pass
    want = f"{sys.version_info[0]}.{sys.version_info[1]}"
    for py in ("/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3", shutil.which("python3") or ""):
        if not py or not Path(py).exists():
            continue
        r = subprocess.run([py, "-c", "import sys, os, PIL; print('%d.%d' % sys.version_info[:2], os.path.dirname(os.path.dirname(PIL.__file__)))"],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.split()[0] == want:
            sys.path.append(r.stdout.split(None, 1)[1].strip())
            return
    sys.exit(f"lookcheck needs Pillow for python {want}: none found")


_pillow()
from PIL import Image, ImageChops, ImageDraw  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lookcheck_scenes import GROUPS, SCENES, SCREENS  # noqa: E402

ACCEPTED = ROOT / ".lookcheck" / "accepted"
TOL = 24          # a px is changed when a channel moved by more than this (a little slack for GPU dither)
NOISE = .1        # % of px under which a scene is not framed red: a key cap (DOM) one px off between two runs of the same code


def run_workers(out, only, jobs):
    py = str(ROOT / ".venv" / "bin" / "python") if (ROOT / ".venv").exists() else str(Path.home() / "nexel_worlds/.venv/bin/python")
    todo = [(gr, sc) for gr in GROUPS for sc in SCREENS if any(v[0] == gr and (not only or n in only) for n, v in SCENES.items())]
    todo.sort(key=lambda t: -sum(1 for v in SCENES.values() if v[0] == t[0]))       # (the long groups first)
    running, fails = [], []
    env = dict(__import__("os").environ, PYTHONPATH=str(ROOT / "src"))
    while todo or running:
        while todo and len(running) < jobs:
            gr, sc = todo.pop(0)
            cmd = [py, str(ROOT / "tools" / "lookcheck_scenes.py"), "--group", str(gr), "--screen", sc, "--out", str(out), "--only", ",".join(sorted(only))]
            running.append(((gr, sc), subprocess.Popen(cmd, env=env, cwd=str(ROOT), stdin=subprocess.DEVNULL)))
        time.sleep(.2)
        for r in list(running):
            if r[1].poll() is not None:
                running.remove(r)
                if r[1].returncode:
                    fails.append(r[0])
    return fails


def changed(a, b):
    """(% of px changed, diff picture) of two shots; 100 % if their sizes differ."""
    if a.size != b.size:
        return 100.0, None
    d = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    mask = d.convert("L").point(lambda v: 255 if v > TOL else 0)
    n = mask.histogram()[255]
    pct = 100.0 * n / (a.size[0] * a.size[1])
    if not n:
        return 0.0, None
    pic = Image.blend(b.convert("RGB"), Image.new("RGB", b.size, (0, 0, 0)), .6)
    pic.paste((255, 0, 40), mask=mask)
    return pct, pic


def sheet(out, rows, pcts):
    """All shots on one picture: a row per scene, the desk shot at a half, the phone's at a sixth (NEAREST); a changed
    scene in a red frame with its %."""
    dw, dh, pw, ph, pad, lab = 720, 450, 195, 422, 12, 22
    names = [n for n in SCENES if n in rows]
    cols = 2
    cw = dw + pw + 3 * pad
    rh = max(dh, ph) + lab + pad
    W, H = cols * cw, ((len(names) + cols - 1) // cols) * rh + pad
    s = Image.new("RGB", (W, H), (24, 22, 30))
    dr = ImageDraw.Draw(s)
    for k, n in enumerate(names):
        x0, y0 = (k % cols) * cw + pad, (k // cols) * rh + pad
        worst = max((pcts.get((n, sc)) or 0) for sc in SCREENS)
        worst = worst if worst > NOISE else 0
        dr.text((x0, y0 + 4), f"{n}" + (f"   changed {worst:.2f} %" if worst else ""), fill=(255, 80, 80) if worst else (230, 230, 230))
        for sc, (w, h, dx) in (("desk", (dw, dh, 0)), ("phone", (pw, ph, dw + pad))):
            f = rows[n].get(sc)
            if not f:
                continue
            im = Image.open(f).convert("RGB").resize((w, h), Image.NEAREST)
            s.paste(im, (x0 + dx, y0 + lab))
            p = pcts.get((n, sc))
            if p and p > NOISE:
                dr.rectangle([x0 + dx - 3, y0 + lab - 3, x0 + dx + w + 2, y0 + lab + h + 2], outline=(255, 0, 0), width=3)
                dr.text((x0 + dx + 4, y0 + lab + 4), f"{p:.2f} %", fill=(255, 40, 40))
    s.save(out / "sheet.png")
    return out / "sheet.png"


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--accept", action="store_true", help="make this run's shots the accepted set")
    a.add_argument("--only", default="", help="scene names, comma-separated: " + ",".join(SCENES))
    a.add_argument("--out", default=str(ROOT / ".lookcheck" / "last"))
    a.add_argument("--jobs", type=int, default=3)
    o = a.parse_args(argv)
    only = set(filter(None, o.only.split(",")))
    if only - set(SCENES):
        a.error(f"no scene {sorted(only - set(SCENES))}; scenes: {', '.join(SCENES)}")
    out = Path(o.out).resolve()
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    t0 = time.time()
    fails = run_workers(out, only, max(1, min(3, o.jobs)))
    rows, pcts, cells = {}, {}, []
    for n in SCENES:
        if only and n not in only:
            continue
        for sc in SCREENS:
            f = out / f"{n}_{sc}.png"
            if not f.exists():
                cells.append(f"{n}/{sc[0]}:MISSING")
                continue
            rows.setdefault(n, {})[sc] = f
            acc = ACCEPTED / f.name
            if not acc.exists():
                cells.append(f"{n}/{sc[0]}:new")
                continue
            p, pic = changed(Image.open(acc), Image.open(f))
            pcts[(n, sc)] = p
            if pic:
                pic.save(out / f"diff_{n}_{sc}.png")
            cells.append(f"{n}/{sc[0]}:{p:.2f}%" + ("!" if p > NOISE else ""))
    s = sheet(out, rows, pcts)
    print(f"lookcheck {time.time() - t0:.0f}s | " + " ".join(cells))
    print(f"sheet: {s}")
    if fails:
        print("workers failed:", fails)
    if o.accept:
        ACCEPTED.mkdir(parents=True, exist_ok=True)
        for f in out.glob("*_*.png"):
            if not f.name.startswith(("diff_", "sheet")):
                shutil.copy2(f, ACCEPTED / f.name)
        print(f"accepted -> {ACCEPTED}")
    return 1 if fails or any(v.endswith("MISSING") for v in cells) else 0


if __name__ == "__main__":
    sys.exit(main())
