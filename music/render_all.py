"""Render everything, as fast as the machine allows: every track at once, then the game's audio.

    uv run python music/render_all.py        # about 40 s (it was about 5 minutes one after the other)
"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
t0 = time.time()
jobs = {name: subprocess.Popen([sys.executable, str(HERE / name)], cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for name in ("compose.py", "night.py", "boss.py", "day.py")}
failed = False
for name, p in jobs.items():
    out, _ = p.communicate()
    lines = [l for l in out.splitlines() if "notes," in l or "loop" in l or "clash" in l or "staircase" in l or "not in the chord" in l or p.returncode]
    print(f"{name}: " + ("FAILED\n" + out if p.returncode else " | ".join(l.strip() for l in lines)))
    failed |= bool(p.returncode)
if failed:
    sys.exit(1)
print(subprocess.run([sys.executable, str(HERE.parent / "tools" / "build_audio.py")], capture_output=True, text=True).stdout.strip().splitlines()[-1])
print(f"all in {time.time() - t0:.0f}s")
