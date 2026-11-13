"""Downloads the recorded instruments the music is played on, into music/samples/raw (not committed, about 600 MB).
All three libraries are public domain (CC0 1.0): VCSL and VSCO 2 Community Edition by Versilian Studios, and the
Spanish classical guitar of the FreePats project.      uv run python music/fetch_samples.py"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen, Request
import json
import subprocess

RAW = Path(__file__).with_name("samples") / "raw"
GUITAR = "https://freepats.zenvoid.org/Guitar/SpanishClassicalGuitar/SpanishClassicalGuitar-SFZ+FLAC-20190618.7z"
WANT = {       # our name: (repository, folder)
    "marimba": ("VCSL", "Idiophones/Struck Idiophones/Marimba"),
    "vibes": ("VCSL", "Idiophones/Struck Idiophones/Vibraphone/Soft Mallets"),
    "shaker": ("VCSL", "Idiophones/Struck Idiophones/Shaker, Small"),
    "woodblock": ("VCSL", "Idiophones/Struck Idiophones/Woodblock"),
    "harp": ("VCSL", "Chordophones/Composite Chordophones/Concert Harp"),
    "harmonica": ("VCSL", "Aerophones/Free Aerophones/Harmonica-Hohner-Super64/Sustains/Normal"),
    "bassdrum": ("VCSL", "Membranophones/Struck Membranophones/Bass Drum 1"),
    "flute": ("VSCO-2-CE", "Woodwinds/Flute/susNV"),
    "clarinet": ("VSCO-2-CE", "Woodwinds/Clarinet/susLong"),
    "oboe": ("VSCO-2-CE", "Woodwinds/Oboe/Sus"),
    "bass": ("VSCO-2-CE", "Strings/Solo Contrabass/Pizz"),
    "horn": ("VSCO-2-CE", "Brass/F Horn/sus"),
    "viola": ("VSCO-2-CE", "Strings/Viola Section/susvib"),
    "cello": ("VSCO-2-CE", "Strings/Cello Section/susvib"),
    "cellopizz": ("VSCO-2-CE", "Strings/Cello Section/pizzT"),
}


def get(url):
    return urlopen(Request(url, headers={"User-Agent": "curl/8"}), timeout=120).read()


def one(job):
    url, path = job
    if not path.exists():
        data = get(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.with_suffix(".part").write_bytes(data)
        path.with_suffix(".part").rename(path)
    return path


def main():
    jobs = []
    for repo in sorted({r for r, _ in WANT.values()}):
        tree = json.loads(get(f"https://api.github.com/repos/sgossner/{repo}/git/trees/master?recursive=1"))["tree"]
        for name, (r, folder) in WANT.items():
            if r != repo:
                continue
            for e in tree:
                p = e["path"]
                if e["type"] == "blob" and p.startswith(folder + "/") and "/" not in p[len(folder) + 1:] and p.lower().endswith(".wav"):
                    jobs.append((f"https://raw.githubusercontent.com/sgossner/{repo}/master/{quote(p)}", RAW / name / p.split("/")[-1]))
    with ThreadPoolExecutor(12) as pool:
        for k, _ in enumerate(pool.map(one, jobs)):
            if k % 50 == 0:
                print(f"{k}/{len(jobs)}", flush=True)
    g = RAW / "guitar"
    if not any(g.glob("*.wav")):
        g.mkdir(parents=True, exist_ok=True)
        arc = one((GUITAR, RAW / "guitar.7z"))
        subprocess.run(["bsdtar", "-xf", str(arc), "-C", str(g)], check=True)
        for f in g.rglob("*.flac"):
            subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI24", str(f), str(g / (f.stem + ".wav"))], check=True)
    for d in sorted(RAW.iterdir()):
        if d.is_dir():
            print(d.name, len(list(d.glob("*.wav"))))


if __name__ == "__main__":
    main()
