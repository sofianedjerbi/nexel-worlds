# A phone, measured

Two ways: a phone simulated on this Mac (`tools/phone_sim.py`), and the real phone over a cable.

## On this Mac

    PYTHONPATH=src ~/nexel/nexel-worlds/.venv/bin/python tools/phone_sim.py --preset mid
    PYTHONPATH=src ~/nexel/nexel-worlds/.venv/bin/python tools/phone_sim.py --preset low --gpu soft --profile stair
    PYTHONPATH=src ~/nexel/nexel-worlds/.venv/bin/python tools/phone_sim.py --bench --preset mid      (the calibration only)

- It starts its own server (a free port, a new world, never 7777) and one headless Chrome held like a phone: 390x844,
  3 device px a px (1170x2532, a phone's real px: its GPU is slowed by the px it fills), touch.
- **CPU** (`--preset mid|low`, or `--cpu 6`): Chrome slows its page's CPU by a rate. The rate is calibrated each run,
  as Chrome's DevTools makes its "mid-tier / low-tier mobile" presets: a fixed piece of JS (`BENCH`,
  `tools/phone_sim_js.py`) is timed here, and the rate is what makes it as slow as on the reference phone (`REF` in
  `phone_sim.py`: mid = a 2021 mid Android, Galaxy A52; low = a 2021 budget one, Moto G Power), checked once more at
  that rate. A busy Mac gets a lower rate.
- **GPU**: Chrome cannot slow a GPU. `--gpu soft` draws with SwiftShader (the CPU doing the GPU's work): far slower
  than this Mac's GPU, a pessimistic stand-in. `hw` is the Mac's GPU: its GPU ms say what is drawn, not a phone's time.
- **Line**: `--line 4g|fast3g` (the lines of `tools/perf_serve.py`).
- **The demo itself**: `--url http://127.0.0.1:PORT` plays a page served already (the demo's build:
  `python tools/build_pages.py DIR`, then `python -m http.server PORT` in DIR): its Python server in the page's worker,
  no dev tools, so `title,stand,walk,sprint` only, wherever the new player wakes.
- **The rate drifts**: on 2026-11-21 this Mac's BENCH was 11 ms (21.9 when `REF` was set), so `low` slowed it x27, twice
  the Geekbench ratio (x12.7), and Chrome's throttle is worse than linear past x10 (a land of 6 chunks: 7 ms at x1,
  61 at x8, 407 at x27). For numbers comparable with older ones, a fixed `--cpu 13`.
- **Place**: `--at 40,40` plays there (a teleport after waking). A new player wakes somewhere else each run, and what
  is round them (trees, water) moved walk's fps from 36 to 55 between two runs of the same code: to compare two versions,
  the same place, a fixed `--cpu` rate, and the runs of the two taken in turn (the Mac is shared: a run alone can be
  slowed by others' work; its GPU ms going up says so).
- **Scenarios** (`--only stand,walk,...`, `--secs 5` each): stand; walk and sprint (the touch stick pushed 40 / 80 px,
  east then west); stair (down a dug stair into a room under the land); swim (across deep water); title (the page
  loaded, the first screen, Wake up, until the land is drawn). Each is set up at full speed, then played slowed.
  The title's parts: `title` (the island shown till Wake up), `woke` (from Wake up on), each with fps, long tasks,
  `build_ms` (the land's making) and `hd_ms` (the HD look's script); `land_s` (Wake up to the land drawn, s);
  `long200` (tasks over 200 ms, s from the island shown: under 0 is the page's load). `went` holds timestamps, not
  durations. `--profile title` profiles the island's frames alone.
- **A frame**: its gap since the last, the script's ms, the HD look's draws and faces, the GPU's ms (the GPU's own
  clock: `js/gpu_time.js`), long tasks, the heap. `--profile stair,title`: a CPU profile of those, their top
  functions (self time, a canvas call named with the game's function that called it; and total time).
- Out: a table; `--dir` (default the job's mockups folder) `p1_<preset>_<gpu>.json` and `.png` (a bar a frame).

In the game itself: F3 (or `?perf=1`) shows the same per frame: fps, frame and script ms, and `GPU x ms a frame`
("n/a" where the browser has no timer: Safari).

## The real phone: Android (Chrome), by USB

1. On the phone: Settings, About phone, tap "Build number" seven times. Then Settings, Developer options: USB debugging on.
2. Cable to the Mac; on the phone, allow this computer. `adb devices` lists it.
3. Open Chrome on the phone (any page).
4. `PYTHONPATH=src ~/nexel/nexel-worlds/.venv/bin/python tools/phone_sim.py --device android --bench` prints the phone's
   own BENCH ms: written into `REF` (mid or low), the simulation matches that phone.
5. `PYTHONPATH=src ~/nexel/nexel-worlds/.venv/bin/python tools/phone_sim.py --device android` plays the same scenarios on
   the phone (`adb forward` reaches its Chrome, `adb reverse` lets it reach the server on the Mac), no slowing.
6. By hand: on the Mac, Chrome at `chrome://inspect#devices`, "Port forwarding" 7777 to localhost:7777; on the
   phone open `localhost:7777/?perf=1`; on the Mac, "inspect", the Performance panel: record while playing.

## The real phone: iPhone (Safari), by USB

1. On the iPhone: Settings, Apps, Safari, Advanced: Web Inspector on.
2. On the Mac: Safari, Settings, Advanced: "Show features for web developers".
3. Cable; the iPhone trusts the Mac. The iPhone opens the game: the demo's address, or the Mac's own on the same
   Wi-Fi (`--host 0.0.0.0` for the server, then `http://<the Mac's address>:7777/?perf=1`).
4. On the Mac: Safari, Develop, the iPhone's name, the game's page. Timelines: record while playing; "Rendering
   Frames" has each frame's ms, "JavaScript & Events" the functions, "CPU" the threads.
5. F3 on the iPhone: frames and script as anywhere; GPU n/a (Safari has no timer query).
