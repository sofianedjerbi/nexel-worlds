"""Spectrogram contact sheet for reviewing sound effects by eye: uv run python music/spectro.py music/site/sfx out.png [name,name,...]
Each tile: an envelope strip on top, then the spectrogram. Writes a PNG and prints the tile order."""
import sys, wave, zlib, struct, json, glob, os
import numpy as np

SFX = sys.argv[1]; OUTPNG = sys.argv[2]; names = sys.argv[3].split(",") if len(sys.argv) > 3 else None
SR = 48000; W, H, ENV, PAD, COLS = 320, 130, 22, 10, 4
TMAX = 1.6

def load(f):
    w = wave.open(f); return np.frombuffer(w.readframes(w.getnframes()), "<i2") / 32767

def spec(x):
    n, hop = 2048, 96
    x = np.pad(x, (0, n))
    frames = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * np.hanning(n)
    S = np.abs(np.fft.rfft(frames, axis=1)) + 1e-9
    db = 20 * np.log10(S); db -= db.max(); return np.clip((db + 70) / 70, 0, 1)   # frames x bins

def colour(v):   # dark blue -> purple -> orange -> pale yellow
    stops = np.array([[10, 12, 30], [70, 30, 110], [200, 70, 70], [250, 170, 60], [255, 250, 200]], float)
    p = v * (len(stops) - 1); i = np.clip(p.astype(int), 0, len(stops) - 2); f = (p - i)[..., None]
    return (stops[i] * (1 - f) + stops[i + 1] * f).astype(np.uint8)

def tile(x):
    img = np.full((ENV + H, W, 3), 255, np.uint8)
    S = spec(x); nf = S.shape[0]
    freqs = np.fft.rfftfreq(2048, 1 / SR)
    rows = np.geomspace(40, 16000, H)[::-1]
    bins = np.searchsorted(freqs, rows)
    cols = (np.arange(W) / W * TMAX * SR / 96).astype(int)
    vals = np.zeros((H, W))
    ok = cols < nf
    vals[:, ok] = S[cols[ok]][:, bins].T
    img[ENV:] = colour(vals)
    # envelope strip (peak per column, dB)
    seg = int(TMAX * SR / W)
    for c in range(W):
        s = x[c * seg:(c + 1) * seg]
        if len(s) == 0: break
        v = np.clip((20 * np.log10(np.abs(s).max() + 1e-6) + 50) / 50, 0, 1)
        h = int(v * (ENV - 2))
        img[ENV - 1 - h:ENV - 1, c] = (90, 63, 54)
    # grid lines at 100 Hz, 1 kHz, 10 kHz and every 0.5 s
    for fq in (100, 1000, 10000):
        r = ENV + int(np.argmin(np.abs(rows - fq))); img[r, ::4] = (255, 255, 255)
    for ts in (0.5, 1.0, 1.5):
        img[ENV:, int(ts / TMAX * W), :] = (200, 200, 200)
    return img

files = sorted(glob.glob(os.path.join(SFX, "*_0.wav")))
if names: files = [os.path.join(SFX, f"{n}_0.wav") for n in names]
rows_n = (len(files) + COLS - 1) // COLS
sheet = np.full((rows_n * (ENV + H + PAD) + PAD, COLS * (W + PAD) + PAD, 3), 245, np.uint8)
for k, f in enumerate(files):
    r, c = divmod(k, COLS)
    y0, x0 = PAD + r * (ENV + H + PAD), PAD + c * (W + PAD)
    sheet[y0:y0 + ENV + H, x0:x0 + W] = tile(load(f))
    print(f"r{r + 1}c{c + 1} {os.path.basename(f)[:-6]}", end="   " if c < COLS - 1 else "\n")
print()

def png(path, a):
    h, w, _ = a.shape
    raw = b"".join(b"\x00" + a[i].tobytes() for i in range(h))
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
png(OUTPNG, sheet)
