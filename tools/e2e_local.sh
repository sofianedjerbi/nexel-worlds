#!/bin/sh
# Loop ONE browser test on the Mac as a GitHub runner plays it (#275): the land drawn on the CPU, the page's CPU slowed
# (tests/e2e/conftest.py RUNNER_LIKE), frames ~100-120 ms as in the CI logs. To turn a flake red in minutes, not a CI hour
# a try. Never the whole suite (GitHub runs that): one test id, up to n times (10 if not said), stopping at its first red.
#   tools/e2e_local.sh 'tests/e2e/test_e2e_leap_terrain.py::test_a_jump_that_comes_down_against_a_step_goes_on_up_it[True]' 20
# Two loops on the Mac at most (CLAUDE.md: keep it usable): two lock slots, and none taken while the load is 8 or more; at nice 10.
# E2E_RUNNER_LIKE: the CPU slowdown (30: frames ~100-120 ms on an M-series Mac, as the runners'); PYTHON: the interpreter (the worktree's .venv).
set -u
[ $# -ge 1 ] || { echo "usage: $0 <test id> [n]" >&2; exit 2; }
id=$1 n=${2:-10}
cd "$(dirname "$0")/.." || exit 2
py=${PYTHON:-.venv/bin/python}
load() { sysctl -n vm.loadavg | awk '{print int($2)}'; }
lock=
while [ -z "$lock" ]; do
  for s in 1 2; do
    l=/tmp/nexel-e2e-local.$s.lock
    [ -d "$l" ] && ! kill -0 "$(cat "$l/pid" 2>/dev/null)" 2>/dev/null && rm -rf "$l"   # (its loop gone)
    if [ "$(load)" -lt 8 ] && mkdir "$l" 2>/dev/null; then lock=$l; break; fi
  done
  [ -n "$lock" ] || { echo "waiting: load $(load), loops: $(cat /tmp/nexel-e2e-local.*.lock/what 2>/dev/null | tr '\n' ' ')"; sleep 30; }
done
echo $$ > "$lock/pid"; echo "$id" > "$lock/what"
trap 'rm -rf "$lock"' EXIT INT TERM
out=$(mktemp -d)
red=0
for k in $(seq 1 "$n"); do
  E2E_RUNNER_LIKE=${E2E_RUNNER_LIKE:-30} nice -n 10 "$py" -m pytest -m e2e -n 0 -p no:randomly -p no:cacheprovider -q --timeout=300 "$id" > "$out/$k.txt" 2>&1
  r=$?
  frame=$(grep -o 'a frame of the game: [0-9]* ms' "$out/$k.txt" | grep -o '[0-9]*')
  if [ $r -eq 0 ]; then echo "run $k: pass (frame ${frame:-?} ms)"; else red=$((red + 1)); echo "run $k: FAIL (frame ${frame:-?} ms): $out/$k.txt"; grep -m1 -E '^E ' "$out/$k.txt" | cut -c1-300; break; fi
done
echo "$red red in $k runs ($id); logs in $out"
[ $red -eq 0 ]
