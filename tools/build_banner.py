"""The README's banner (assets/banner.gif): the first screen's island as the game itself draws it, with a scene played
on it: Tobi builds a little wooden hut, wall by wall, and takes it down again with his axe, while Mira and Nell, beside
him, talk it over in speech bubbles. The view drifts gently along; the logo is laid over it: the emblem (web/assets/emblem.png,
tools/build_emblem.py) beside the wordmark (assets/banner_logo.png), both at the wordmark's own 5 px a pixel.
The scene is played exactly once a loop and the island is otherwise held still (its hour, its crops, its animals, the
others), so that the GIF loops with no seam. One of its frames is the repo's social preview (assets/social_preview.png).

    uv run --with pillow python tools/build_banner.py      (a minute; after the island, its art or its people change)

It starts a game server of its own on a throwaway world, opens the first screen in Chrome (ZOOM screen pixels an art
pixel) and hides the page's own window and words. The page's clock is held (Playwright's): each frame is the island
exactly MS later than the one before, however long a picture takes to take, so everything moves evenly."""

import io
import math
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT, LOGO = ROOT / "assets" / "banner.gif", ROOT / "assets" / "banner_logo.png"
SOCIAL = ROOT / "assets" / "social_preview.png"    # the repo's social preview (GitHub: Settings > Social preview)
EMBLEM = ROOT / "src" / "nexel_worlds" / "web" / "assets" / "emblem.png"
WORD, UNIT, GAP = (220, 199, 355, 45), 5, 20      # where the wordmark lies in banner_logo.png (x, y, w, h); its px; emblem to word
W, H, MS, LOOP = 800, 320, 50, 100          # 20 frames a second; the scene: 100 of the island's ticks (10 s)
FRAMES = LOOP * 100 // MS                   # (a tick is 100 ms)
ZOOM = 2                                    # screen px an art px: close enough to see who is who
VIEW = (43.5, 40), 2                         # the view's middle at the start, in the island's tiles, and how far east it drifts and back
                                            # (the scene in the upper half: the logo lies over the lower)
LOGO_BOX = (164, 173, 472, 96)              # x, y, w, h in px: where the emblem and wordmark lie (no bubble is drawn half under them)
SETTLED = "!HdLook.busy && !dirtyTiles.length"
BUILT = "document.body.classList.contains('scene') && HdLook.live && HdLook.builds > 0 && " + SETTLED
STAGE = """([LOOP, logo]) => {
  const css = document.createElement('style');               // (only the island is filmed: no window, no line, no button)
  css.textContent = '* { visibility: hidden !important; } canvas { visibility: visible !important; } #joinbox canvas { visibility: hidden !important; }';
  document.head.appendChild(css);
  const S = TitleScene.S, who = (n) => S.people.find((p) => p.name === n);
  // the view: where the film says, a frame at a time
  window.bannerAt = [cam.x - S.ox, cam.y - S.oy];
  (function hold() { cam.x = camT.x = S.ox + bannerAt[0]; cam.y = camT.y = S.oy + bannerAt[1]; requestAnimationFrame(hold); })();
  // the island held still, so that the end of the loop is its start: its hour, its crops, its animals, its shouts
  S.C.field = [0, 0, 0, 0]; for (const a of S.herd) a.wait = 1e9; TitleCast.hail = () => {};
  const [lx, ly, lw, lh] = logo; TitleScene.hides = (x, y, w, h) => x < lx + lw && lx < x + w && y < ly + lh && ly < y + h;
  BUBBLE.life = 3.4; BUBBLE.after = 1.4;                     // (a line read, then gone: none is left over at the loop's end)
  // the scene: each of its people a generator, a yield a tick, played over and over, LOOP ticks a time
  const pose = (p, o) => Object.assign(p, {doing: null, with: null, item: null, aim: null, dir: null, still: true, run: false, hold: 0, ...o});
  function* wait(p, n, o = {}) { pose(p, o); while (n-- > 0) yield; }
  function* walk(p, x, y) {
    for (const [ax, tx] of [["x", x], ["y", y]]) while (p[ax] !== tx) { p[ax] += Math.sign(tx - p[ax]); pose(p, {doing: "walk", still: false}); yield; yield; }
  }
  const say = (p, text) => { bubbles.push({name: p.name, text, t: performance.now() / 1000}); babble(p.name, text, S.ox + p.x, S.oy + p.y, false); };
  const put = (x, y, block, cause, p) => S.put(x, y, {block}, cause, p.name);
  // the hut across the path from the two talking (its walls clear of their bubbles): a wall, where to stand, the way to face
  const HUT = [[48, 36, 48, 37, "N"], [49, 36, 49, 37, "N"], [50, 36, 50, 37, "N"], [50, 37, 50, 38, "N"], [48, 37, 48, 38, "N"]];
  const START = {Tobi: [49, 38, "N"], Mira: [39, 40, "E"], Nell: [41, 40, "W"]};
  const was = new Map(HUT.map(([x, y]) => { const c = S.at(x, y)[0]; return [x + "," + y, GROUND.has(c) ? "none" : CH[c]]; }));   // (put back as it was)
  const SCENE = {
    *Tobi(p) {
      for (const [x, y, sx, sy, d] of HUT) { yield* walk(p, sx, sy); yield* wait(p, 4, {doing: "place", dir: d}); put(x, y, "wood_wall", "place", p); yield* wait(p, 1, {doing: "look", dir: d}); }
      emote(p.name, "star"); say(p, "Done!"); yield* wait(p, 8, {doing: "look", dir: "S"});
      for (const [x, y, sx, sy, d] of [...HUT].reverse()) { yield* walk(p, sx, sy); yield* wait(p, 4, {doing: "dig", with: "axe", dir: d, aim: [x, y]}); put(x, y, was.get(x + "," + y), "dig", p); }
      yield* walk(p, ...START.Tobi.slice(0, 2));
    },
    *Mira(p) {
      yield* wait(p, 2, {doing: "look", dir: "E"}); say(p, "Tobi's building again!");
      yield* wait(p, 40, {doing: "look", dir: "E"}); say(p, "And now it's coming down...");
      yield* wait(p, 30, {doing: "look", dir: "E"});
    },
    *Nell(p) {
      yield* wait(p, 22, {doing: "look", dir: "W"}); say(p, "A hut? For who?");
      yield* wait(p, 40, {doing: "look", dir: "W"}); say(p, "He just likes the axe."); emote(p.name, "laugh");
    },
  };
  // each of them a tick at a time: the scene, padded to exactly LOOP ticks, over and over
  function* play(name, p) {
    for (;;) {
      const [x, y, d] = START[name]; Object.assign(p, {x, y, swim: false, sail: false});
      let n = 0; for (const _ of SCENE[name](p)) { n++; yield; }
      if (n > LOOP) console.error(name + " takes " + n + " ticks, more than " + LOOP);
      for (; n < LOOP; n++) { pose(p, {doing: "look", dir: d}); yield; }
    }
  }
  const jobs = new Map(Object.keys(SCENE).map((n) => [n, play(n, who(n))]));
  // the others stand where they are (one out at sea: ashore at the pier, not left afloat with no boat)
  for (const p of S.people) if (!jobs.has(p.name)) { pose(p, {doing: p.swim ? null : "look", dir: "S"}); if (p.sail) [p.x, p.y] = S.C.pier; p.sail = false; jobs.set(p.name, (function* () { for (;;) yield; })()); }
  window.bannerTick = 0; const T0 = S.tick;
  TitleCast.live = (p) => {
    if (p === S.people[0]) { bannerTick++; S.tick = T0; }      // (the hour held: the tick is counted on from T0 each time)
    jobs.get(p.name).next();
  };
}"""
AT = "([x, y]) => { bannerAt = [x, y]; }"


def view(i: int) -> tuple[float, float]:
    """Where the view is at frame i: drifting east and back on a sine, so it never stops short or jumps."""
    (x, y), far = VIEW
    return x + far * (1 - math.cos(2 * math.pi * i / FRAMES)) / 2, y


def settle(page):
    """Run the held clock on until the land in view is all made (none is filmed flat and pale, half made)."""
    for _ in range(600):
        if page.evaluate(SETTLED):
            return
        page.clock.run_for(16)
    raise TimeoutError("the land in view was never made")


def film() -> list[Image.Image]:
    from playwright.sync_api import sync_playwright
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    work = tempfile.mkdtemp()
    server = subprocess.Popen([sys.executable, "-m", "nexel_worlds.server", "--saves", work, "--world", "banner", "--port", str(port), "--seed", "7"],
                              cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=.2).close(); break
            except OSError:
                time.sleep(.1)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
            errors = []
            page.on("console", lambda m: m.type == "error" and errors.append(m.text))
            page.clock.install()                                     # (the page's own time, runs as usual until it is held)
            page.goto(f"http://127.0.0.1:{port}/?zoom={ZOOM}")
            page.wait_for_function("typeof TitleScene !== 'undefined' && TitleScene.on", timeout=30000)
            page.wait_for_function(BUILT, timeout=60000)
            page.clock.pause_at(page.evaluate("Date.now()") + 1000)
            page.evaluate(STAGE, [LOOP, list(LOGO_BOX)])
            for i in [*range(0, FRAMES, FRAMES // 8), 0]:            # the land all along the drift made first: the HD look makes a block
                page.evaluate(AT, list(view(i)))                       # only as the view nears it
                page.clock.run_for(200); settle(page)
            page.clock.run_for(LOOP * 100)                             # (once through: the first loop's start was set mid-tick)
            while page.evaluate("bannerTick") % LOOP:                  # to the very start of the scene
                page.clock.run_for(100)
            frames = []
            for i in range(FRAMES):
                page.evaluate(AT, list(view(i)))
                page.clock.run_for(MS); settle(page)
                frames.append(Image.open(io.BytesIO(page.screenshot())).convert("RGB"))
            browser.close()
            assert not errors, errors
        return frames
    finally:
        server.terminate(); shutil.rmtree(work, ignore_errors=True)


def lockup() -> Image.Image:
    """The logo laid over the film: the emblem, then the wordmark, the two centred together on the wordmark's line."""
    x, y, w, h = WORD
    coin = Image.open(EMBLEM).convert("RGBA")
    coin = coin.resize((coin.width * UNIT, coin.height * UNIT), Image.NEAREST)
    left = (W - (coin.width + GAP + w)) // 2
    out = Image.new("RGBA", (W, H))
    out.alpha_composite(Image.open(LOGO).convert("RGBA").crop((x, y, x + w, y + h)), (left + coin.width + GAP, y))
    out.alpha_composite(coin, (left, y + h // 2 - coin.height // 2))
    lx, ly, lw, lh = LOGO_BOX
    assert lx <= left and left + coin.width + GAP + w <= lx + lw and ly <= y + h // 2 - coin.height // 2, "the logo is not inside LOGO_BOX"
    return out


def build():
    logo = lockup()
    frames = [Image.alpha_composite(f.convert("RGBA"), logo).convert("RGB") for f in film()]
    sample = Image.new("RGB", (W, H * 8))                                          # one palette for all (pixel art has few colours),
    for k in range(8):                                                             # from frames all through the loop (the hut's walls
        sample.paste(frames[k * len(frames) // 8], (0, k * H))                     # are not in the first)
    pal = sample.quantize(256, method=Image.Quantize.MEDIANCUT)
    out = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    out[0].save(OUT, save_all=True, append_images=out[1:], duration=MS, loop=0, optimize=True, disposal=1)
    print(f"{OUT.name}: {W} x {H}, {FRAMES} frames, {OUT.stat().st_size // 1024} KB")
    # the social preview: one moment of the scene (frame 84: the hut up, Nell asking who it's for, Tobi's "Done!", no
    # bubble cut or half written), its middle 640 x 320 round the logo, each pixel 2 x 2: GitHub's 1280 x 640, crisp
    still = frames[84].crop(((W - 640) // 2, 0, (W + 640) // 2, H))
    still.resize((1280, 640), Image.NEAREST).save(SOCIAL)
    print(f"{SOCIAL.name}: 1280 x 640")


if __name__ == "__main__":
    build()
