"""Deal the browser test files out to CI's runners by how long each takes, and measure that from CI's own runs.

    python3 tools/e2e_shards.py plan FILE...       # the runners' shares, as the JSON list ci.yml's matrix takes
    python3 tools/e2e_shards.py measure [RUN_ID]   # tests/e2e/durations.json from a main run (default: the last one
                                                   # whose browser jobs finished), through `gh`

plan: longest file first, each onto the runner with the least time so far, as many runners as TARGET seconds of tests
each asks for (at most RUNNERS, at most one a file). A file never measured counts as the median of those that were.
measure: each browser job prints every test's time (`--durations=0`, ci.yml); a file's time is the sum of its tests'
(setup, call, teardown). A file the run did not time (its job cut off) keeps the time it had. Standard library only:
the plan runs on a bare runner, before any `uv sync`."""

import json
import math
import re
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DURATIONS = ROOT / "tests/e2e/durations.json"
REPO = "sofianedjerbi/nexel-worlds"
RUNNERS = 16          # of the account's 20: the other checks of the run keep theirs
TARGET = 300          # s of tests a runner: with its ~20 s of setup, the run's wall time is about this
LINE = re.compile(r"(\d+(?:\.\d+)?)s (?:setup|call|teardown)\s+(tests/e2e/[^\s:]+\.py)::")


def plan(files: list[str], durations: dict[str, float]) -> list[str]:
    known = [durations[f] for f in files if f in durations] or list(durations.values()) or [60.0]
    guess = statistics.median(known)
    cost = {f: durations.get(f, guess) for f in files}
    n = min(RUNNERS, len(files), max(1, math.ceil(sum(cost.values()) / TARGET)))
    shards = [[0.0, []] for _ in range(n)]
    for f in sorted(files, key=lambda f: (-cost[f], f)):
        least = min(shards, key=lambda s: s[0])
        least[0] += cost[f]
        least[1].append(f)
    return [" ".join(sorted(s[1])) for s in shards if s[1]]


def parse(log: str) -> dict[str, float]:
    out = defaultdict(float)
    if "= slowest durations =" not in log:          # (`--durations=10`, as before: only some of the tests are in it)
        return {}
    for m in LINE.finditer(log):
        out[m.group(2)] += float(m.group(1))
    return dict(out)


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def measure(run_id: str | None) -> dict[str, float]:
    if run_id is None:
        runs = json.loads(gh("run", "list", "-R", REPO, "-w", "CI", "-b", "main", "-e", "push", "-L", "20",
                             "--json", "databaseId,status"))
        run_id = next(str(r["databaseId"]) for r in runs if r["status"] == "completed")
    jobs = json.loads(gh("run", "view", run_id, "-R", REPO, "--json", "jobs"))["jobs"]
    times = {}
    for job in jobs:
        if job["name"].startswith("Browser tests (") and job["conclusion"] in ("success", "failure"):
            times |= parse(gh("api", "--allow-escape-sequences", f"repos/{REPO}/actions/jobs/{job['databaseId']}/logs"))
    print(f"run {run_id}: {len(times)} files timed, {sum(times.values()) / 60:.0f} min of tests", file=sys.stderr)
    return times


def main(argv: list[str]) -> None:
    durations = json.loads(DURATIONS.read_text()) if DURATIONS.exists() else {}
    if argv[:1] == ["plan"]:
        print(json.dumps(plan(sorted(set(argv[1:])), durations)))
    elif argv[:1] == ["measure"]:
        durations |= {f: round(t) for f, t in measure(argv[1] if len(argv) > 1 else None).items()}
        live = {str(p.relative_to(ROOT)) for p in (ROOT / "tests/e2e").glob("test_*.py")}
        DURATIONS.write_text(json.dumps({f: durations[f] for f in sorted(durations) if f in live}, indent=0) + "\n")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
