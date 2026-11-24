#!/bin/sh
# The game, from its sources, into OUT (default dist/): what a browser plays (tools/build_pages.py), with every sound
# and every piece of music rendered here, nothing taken from a machine's own renders.
#
#   tools/build_game.sh [out_dir]          needs uv; the music needs Surge XT (macOS: brew install --cask surge-xt;
#                                          Linux: its .deb, see .github/workflows/game.yml) and, on Linux, 7z
#
#   1. the recorded instruments (music/fetch_samples.py: about 600 MB, kept in music/samples/, fetched once)
#   2. the game's music, played on them and on Surge XT (music/pieces.py, bright.py, slowtide.py), mastered
#      (music/master.py) and corrected for small speakers (music/refit.py), into music/site/audio/
#   3. the sound effects, and the music cut into streamed pieces (tools/build_audio.py), into web/audio/
#   4. the in-browser game (tools/build_pages.py)
#
# Not made here: the art. It is drawn from a licensed pack that may not be shared (assets/CREDITS.md), so the sheets the
# game uses are committed as they are. Surge's sounds have random phases: a render is the same music as the last one,
# never the same samples.
set -e
cd "$(dirname "$0")/.."
OUT=${1:-dist}
AUDIO="uv run --extra audio python"
SURGE="uv run --no-project --python 3.11 --with dawdreamer --with numpy python"   # (DawDreamer hosts Surge XT: Python 3.11)

$AUDIO music/fetch_samples.py
$AUDIO music/sampler.py
# the pieces the game plays (master.py reads all of its list: far shore night D too), at once, then the rest
$SURGE music/pieces.py cute1 shore mc1 shore_night_c shore_night_d mossback2 & a=$!
$SURGE music/bright.py & b=$!
$SURGE music/slowtide.py high full & c=$!
wait $a                                        # each waited for by name, each its own line: a bare `wait`, or a chain
wait $b                                        # of them joined by &&, would let a failed render pass under set -e
wait $c
$AUDIO music/master.py
$SURGE music/refit.py
$AUDIO tools/build_audio.py
$AUDIO tools/build_pages.py "$OUT"
