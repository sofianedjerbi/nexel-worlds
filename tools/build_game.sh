#!/bin/sh
# The game, from its sources, into OUT (default dist/): what a browser plays (tools/build_pages.py), with every sound
# and every piece of music rendered here, nothing taken from a machine's own renders.
#
#   tools/build_game.sh [out_dir]          needs uv; music to render needs Surge XT (macOS: brew install --cask surge-xt;
#                                          Linux: its .deb, see .github/workflows/game.yml)
#
#   1. the game's music, played on Surge XT (music/pieces.py, bright.py, slowtide.py), mastered (music/master.py) and
#      corrected for small speakers (music/refit.py), into music/site/audio/: only the renders whose own entry or code
#      changed since they were made (music/renders.py)
#   2. the sound effects, and the music cut into streamed pieces (tools/build_audio.py), into web/audio/
#   3. the in-browser game (tools/build_pages.py)
#
# Not made here: the art. It is drawn from a licensed pack that may not be shared (assets/CREDITS.md), so the sheets the
# game uses are committed as they are. Surge's sounds have random phases: a render is the same music as the last one,
# never the same samples.
set -e
cd "$(dirname "$0")/.."
OUT=${1:-dist}
AUDIO="uv run --extra audio python"
python3 music/renders.py
$AUDIO tools/build_audio.py
$AUDIO tools/build_pages.py "$OUT"
