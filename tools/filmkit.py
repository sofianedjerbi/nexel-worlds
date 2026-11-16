"""What the showcase clips are filmed with (tools/film_*.py, on the demo's "What's new" page), nothing but what the
project already has: a game server of its own on a throwaway world; a player in Chrome (tests/e2e/game.py) who plays
a scene with the keyboard, a caption and the keys pressed drawn over the page; every frame Chrome paints kept (its
screencast); each then given to Chrome's own H.264 encoder (WebCodecs) and the samples written here as a plain MP4,
its index before its data so that it plays while it loads and can be sought. (Chrome's MediaRecorder writes a
streaming MP4 with no length; Playwright's own recorder needs a download.)

    shoot(scene, out_dir, "name")       scene(g, rec): g the Game, rec.start() and rec.stop() around what is kept,
                                        rec.poster() when the page shows what the poster should (else its end)"""

import base64
import functools
import http.server
import json
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests" / "e2e"))
W, H, BITRATE = 1280, 720, 1400000
SLOT = "(n) => String((slots.indexOf(n) + 1) % 10)"           # the key of the bar's slot that holds it
OVERLAY = """() => {
  const css = document.createElement('style');
  css.textContent = `#goalhint, #goals { display:none !important; }
    #cap { position:fixed; left:16px; top:14px; z-index:50; max-width:560px; font:26px/32px SproutPixel, monospace; color:#5b3f36; background:#fff6e2; border:3px solid #5b3f36;
      border-bottom-width:6px; border-radius:6px; padding:8px 14px; box-shadow:0 3px 0 rgba(60,40,30,.25); }
    #cap:empty { display:none; }
    #capkeys { position:fixed; left:16px; bottom:150px; z-index:50; display:flex; gap:8px; align-items:flex-end; }
    #capkeys span { font:24px/26px SproutPixel, monospace; color:#5b3f36; background:#f7e7c6; border:3px solid #5b3f36; border-bottom-width:7px; border-radius:6px; padding:5px 12px; min-width:44px; text-align:center; }
    #capkeys span.up { opacity:.45; }`;
  document.head.appendChild(css);
  const cap = document.createElement('div'); cap.id = 'cap'; document.body.appendChild(cap);
  const box = document.createElement('div'); box.id = 'capkeys'; document.body.appendChild(box);
  const name = (k) => ({' ': 'Space', ArrowLeft: '←', ArrowRight: '→', ArrowUp: '↑', ArrowDown: '↓', Escape: 'Esc'}[k] || (k.length === 1 ? k.toUpperCase() : k)), held = new Map();
  const draw = () => { box.innerHTML = ''; for (const [k, v] of held) { const s = document.createElement('span'); s.textContent = name(k); if (v.up) s.className = 'up'; box.appendChild(s); } };
  addEventListener('keydown', (e) => { const v = held.get(e.key); if (v) clearTimeout(v.t); held.delete(e.key); held.set(e.key, {up: false}); draw(); }, true);
  addEventListener('keyup', (e) => { const v = held.get(e.key); if (!v) return; v.up = true; v.t = setTimeout(() => { held.delete(e.key); draw(); }, 550); draw(); }, true);
  window.caption = (t) => { cap.textContent = t; };
}"""
ENCODE = """<!DOCTYPE html><meta charset="utf-8"><script>
// Each filmed frame given to Chrome's H.264 encoder with its own time; what comes out goes back as samples.
async function encode(bitrate) {
  const times = await (await fetch("frames/times.json")).json(), out = []; let desc = null, fail = null;
  const enc = new VideoEncoder({error: (e) => { fail = String(e); }, output: (chunk, meta) => {
    if (meta && meta.decoderConfig && meta.decoderConfig.description) desc = new Uint8Array(meta.decoderConfig.description);
    const b = new Uint8Array(chunk.byteLength); chunk.copyTo(b); out.push({key: chunk.type === "key", ts: chunk.timestamp, data: b}); }});
  const config = {codec: "avc1.640028", width: 1280, height: 720, bitrate, framerate: 30, avc: {format: "avc"}, latencyMode: "realtime", bitrateMode: "variable"};
  const ok = await VideoEncoder.isConfigSupported(config);
  if (!ok.supported) return {error: "not supported"};
  enc.configure(config);
  for (let i = 0; i < times.length; i++) {
    const bmp = await createImageBitmap(await (await fetch(`frames/${String(i).padStart(5, "0")}.jpg`)).blob());
    const f = new VideoFrame(bmp, {timestamp: Math.round((times[i] - times[0]) * 1e6)});
    enc.encode(f, {keyFrame: i % 60 === 0}); f.close(); bmp.close();
    while (enc.encodeQueueSize > 8) await new Promise((r) => setTimeout(r, 5));
    if (fail) return {error: fail};
  }
  await enc.flush();
  const total = out.reduce((n, c) => n + c.data.length, 0), all = new Uint8Array(total); let o = 0;
  for (const c of out) { all.set(c.data, o); o += c.data.length; }
  const b64 = (u) => { let s = ""; for (let k = 0; k < u.length; k += 32768) s += String.fromCharCode.apply(null, u.subarray(k, k + 32768)); return btoa(s); };
  return {desc: b64(desc), data: b64(all), samples: out.map((c) => [c.ts, c.data.length, c.key ? 1 : 0])};
}
</script>"""


def caption(g, t):
    g.js("(t) => caption(t)", t)


def keys(g, seq, wait=170):
    for k in seq:
        g.press(k, wait)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Recorder:
    """Chrome's screencast of the page, kept between start() and stop(): work/frames/00000.jpg... and their times."""

    def __init__(self, ctx, page, work: Path):
        self.cdp, self.frames, self.on, self.dir, self.page = ctx.new_cdp_session(page), [], False, work / "frames", page
        self.dir.mkdir()
        self.cdp.on("Page.screencastFrame", self._frame)

    def _frame(self, ev):
        try:
            self.cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})
        except Exception:                                      # (a frame that came as the page closed)
            return
        if self.on:
            (self.dir / f"{len(self.frames):05d}.jpg").write_bytes(base64.b64decode(ev["data"]))
            self.frames.append(ev["metadata"]["timestamp"])

    def start(self):
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 93, "maxWidth": W, "maxHeight": H, "everyNthFrame": 2})
        self.on = True

    def stop(self):
        self.on = False
        self.cdp.send("Page.stopScreencast")
        (self.dir / "times.json").write_text(json.dumps(self.frames))

    def poster(self):
        """The page as it is now as the clip's poster: its last frame while filming (a screenshot would jolt the
        screencast), else a screenshot."""
        if self.on and self.frames:
            shutil.copy(self.dir / f"{len(self.frames) - 1:05d}.jpg", self.dir.parent / "poster.jpg")
        else:
            self.page.screenshot(path=str(self.dir.parent / "poster.jpg"), type="jpeg", quality=85)


def film(pw, url: str, work: Path, scene, zoom: int) -> list:
    """Play the scene, keep its frames, and a poster where it ends -> the frames' times."""
    from game import Game
    b = pw.chromium.launch(channel="chrome", headless=True)
    ctx = b.new_context(viewport={"width": W, "height": H})
    page = ctx.new_page()
    rec, g = Recorder(ctx, page, work), Game(page, url)
    g.join("Ada", zoom)
    g.js(OVERLAY)
    scene(g, rec)
    assert not g.errors, g.errors
    if not (work / "poster.jpg").exists():
        rec.poster()
    ctx.close()
    b.close()
    return rec.frames


def encode(pw, work: Path) -> dict:
    """The frames through Chrome's encoder (a page served from `work`: a page from a file may not fetch them)."""
    (work / "encode.html").write_text(ENCODE)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(work)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    b = pw.chromium.launch(channel="chrome", headless=True)
    page = b.new_page()
    page.set_default_timeout(600000)
    page.goto(f"http://127.0.0.1:{srv.server_address[1]}/encode.html")
    r = page.evaluate("(br) => encode(br)", BITRATE)
    b.close()
    srv.shutdown()
    if "error" in r:
        sys.exit("encoder: " + r["error"])
    return r


def box(kind, *parts):
    body = b"".join(parts)
    return struct.pack(">I4s", 8 + len(body), kind) + body


def full(kind, version, flags, *parts):
    return box(kind, struct.pack(">I", version << 24 | flags), *parts)


def mp4(desc: bytes, data: bytes, samples: list, w: int, h: int, scale: int = 90000) -> bytes:
    ts = [round(t * scale / 1e6) for t, _, _ in samples]
    assert all(b > a for a, b in zip(ts, ts[1:])), "samples out of order (B-frames): they need a ctts"
    deltas = [b - a for a, b in zip(ts, ts[1:])] + [round(scale / 30)]
    runs = []
    for d in deltas:                                           # (stts: runs of the same length)
        if runs and runs[-1][1] == d:
            runs[-1][0] += 1
        else:
            runs.append([1, d])
    dur, matrix = sum(deltas), struct.pack(">9I", 0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000)
    avc1 = box(b"avc1", bytes(6), struct.pack(">H", 1), bytes(16), struct.pack(">HHIIIH", w, h, 0x480000, 0x480000, 0, 1), bytes(32),
               struct.pack(">Hh", 0x18, -1), box(b"avcC", desc))
    stbl = lambda offset: box(b"stbl",
        full(b"stsd", 0, 0, struct.pack(">I", 1), avc1),
        full(b"stts", 0, 0, struct.pack(">I", len(runs)), *[struct.pack(">II", n, d) for n, d in runs]),
        full(b"stss", 0, 0, struct.pack(">I", sum(k for _, _, k in samples)), *[struct.pack(">I", i + 1) for i, s in enumerate(samples) if s[2]]),
        full(b"stsc", 0, 0, struct.pack(">IIII", 1, 1, len(samples), 1)),
        full(b"stsz", 0, 0, struct.pack(">II", 0, len(samples)), *[struct.pack(">I", n) for _, n, _ in samples]),
        full(b"stco", 0, 0, struct.pack(">II", 1, offset)))
    def moov(offset):
        ms = round(dur * 1000 / scale)
        return box(b"moov",
            full(b"mvhd", 0, 0, struct.pack(">IIIIIH", 0, 0, 1000, ms, 0x10000, 0x100), bytes(10), matrix, bytes(24), struct.pack(">I", 2)),
            box(b"trak",
                full(b"tkhd", 0, 3, struct.pack(">IIIII", 0, 0, 1, 0, ms), bytes(8), struct.pack(">HHHH", 0, 0, 0, 0), matrix, struct.pack(">II", w << 16, h << 16)),
                box(b"mdia",
                    full(b"mdhd", 0, 0, struct.pack(">IIIIHH", 0, 0, scale, dur, 0x55C4, 0)),
                    full(b"hdlr", 0, 0, struct.pack(">I4s", 0, b"vide"), bytes(12), b"VideoHandler\0"),
                    box(b"minf", full(b"vmhd", 0, 1, bytes(8)), box(b"dinf", full(b"dref", 0, 0, struct.pack(">I", 1), full(b"url ", 0, 1))), stbl(offset)))))
    ftyp = box(b"ftyp", b"isom", struct.pack(">I", 0x200), b"isomiso2avc1mp41")
    offset = len(ftyp) + len(moov(0)) + 8
    return ftyp + moov(offset) + struct.pack(">I4s", 8 + len(data), b"mdat") + data


def shoot(scene, out: Path, stem: str, seed: int = 7, zoom: int = 4, frames_only: bool = False):
    """Film scene(g, rec) on a throwaway world -> out/stem.mp4 and out/stem.jpg (its poster). frames_only: keep the
    filmed frames instead (in a folder it prints) and encode nothing, to look at them first."""
    from playwright.sync_api import sync_playwright
    work, port = Path(tempfile.mkdtemp()), free_port()
    server = subprocess.Popen([sys.executable, "-m", "megastructure.server", "--saves", str(work / "saves"), "--world", "film", "--port", str(port),
                               "--seed", str(seed), "--dev"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=.2).close()
                break
            except OSError:
                time.sleep(.1)
        with sync_playwright() as pw:
            frames = film(pw, f"http://127.0.0.1:{port}", work, scene, zoom)
            if frames_only:
                return print(f"{work}: {len(frames)} frames, {frames[-1] - frames[0]:.1f} s")
            r = encode(pw, work)
    finally:
        server.terminate()
    data, samples = base64.b64decode(r["data"]), r["samples"]
    (out / f"{stem}.mp4").write_bytes(mp4(base64.b64decode(r["desc"]), data, samples, W, H))
    shutil.copy(work / "poster.jpg", out / f"{stem}.jpg")
    shutil.rmtree(work, ignore_errors=True)
    print(f"{out / stem}.mp4: {len(data) // 1024} KB, {len(frames)} frames, {frames[-1] - frames[0]:.1f} s")
