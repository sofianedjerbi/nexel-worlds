"""Each browser test's failures over main's last full CI runs, worst first, as a markdown table (to post on #47).

    python3 tools/flake_rates.py [N]           # main's last N full runs (default 6), through `gh`
    python3 tools/flake_rates.py LOG...        # saved job logs instead, each its own run

A full run: a push to main, finished and not cancelled, whose browser jobs ran. Each browser job prints every test's
end (`-v`, ci.yml) and a short summary (`FAILED tests/e2e/...::test - why`); a test fails in a run when any of its
lines says FAILED or ERROR there. A test's runs are the runs it ended in (one added since counts only those), so the
table is fails/runs. Only tests that failed at least once are listed. Standard library only, as e2e_shards.py."""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = "sofianedjerbi/nexel-worlds"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
END = re.compile(r"^(?:\S+Z )?(tests/e2e/\S+?\.py::\S+) (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b", re.M)
SUMMARY = re.compile(r"^(?:\S+Z )?(FAILED|ERROR) (tests/e2e/\S+?\.py(?:::\S+)?)(?: - (.*))?$", re.M)
BAD = {"FAILED", "ERROR"}


def parse(log: str) -> dict[str, tuple[bool, str]]:
    """One job's log: each test that ended -> (failed, why). A file that failed to load is its own row (no ::)."""
    log = ANSI.sub("", log)
    out = {t: (o in BAD, "") for t, o in END.findall(log) if o != "SKIPPED"}
    for _, test, why in SUMMARY.findall(log):
        out[test] = (True, (why or "").strip() or out.get(test, (True, ""))[1])
    return out


def tally(runs: list[dict[str, tuple[bool, str]]]) -> list[tuple[str, int, int, str]]:
    """The runs, newest first -> (test, fails, runs, the newest failure's why), worst first."""
    seen, fails, why = {}, {}, {}
    for run in runs:
        for test, (bad, w) in run.items():
            seen[test] = seen.get(test, 0) + 1
            if bad:
                fails[test] = fails.get(test, 0) + 1
                why.setdefault(test, w)
    rows = [(t, n, seen[t], why[t]) for t, n in fails.items()]
    return sorted(rows, key=lambda r: (-r[1] / r[2], -r[1], r[0]))


def table(rows: list[tuple[str, int, int, str]], runs: int) -> str:
    out = [f"Browser tests failing on main, over its last {runs} full runs (tools/flake_rates.py):", "",
           "| test | fails | rate | last failure |", "|---|---|---|---|"]
    for test, n, seen, why in rows:
        why = why.replace("|", "\\|")
        out.append(f"| `{test.removeprefix('tests/e2e/')}` | {n}/{seen} | {n / seen:.0%} | "
                   f"{why[:90] + '…' if len(why) > 90 else why} |")
    if not rows:
        out.append("| (none) | | | |")
    return "\n".join(out)


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def fetch(n: int) -> list[tuple[str, dict[str, tuple[bool, str]]]]:
    """main's last n full runs, newest first: (run id, its tests)."""
    runs = json.loads(gh("run", "list", "-R", REPO, "-w", "CI", "-b", "main", "-e", "push", "-L", "60",
                         "--json", "databaseId,status,conclusion"))
    out = []
    for r in runs:
        if len(out) == n:
            break
        if r["status"] != "completed" or r["conclusion"] == "cancelled":
            continue
        jobs = json.loads(gh("run", "view", str(r["databaseId"]), "-R", REPO, "--json", "jobs"))["jobs"]
        tests = {}
        for job in jobs:
            if job["name"].startswith("Browser tests (") and job["conclusion"] in ("success", "failure", "timed_out"):
                tests |= parse(gh("api", "--allow-escape-sequences", f"repos/{REPO}/actions/jobs/{job['databaseId']}/logs"))
        if tests:
            out.append((str(r["databaseId"]), tests))
    return out


def main(argv: list[str]) -> None:
    if argv and not argv[0].isdigit():
        runs = [parse(Path(p).read_text(errors="replace")) for p in argv]
    else:
        got = fetch(int(argv[0]) if argv else 6)
        print("runs: " + " ".join(i for i, _ in got), file=sys.stderr)
        runs = [t for _, t in got]
    print(table(tally(runs), len(runs)))


if __name__ == "__main__":
    main(sys.argv[1:])
