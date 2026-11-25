#!/bin/sh
# The game, from its sources, into OUT (default dist/): what a browser plays (tools/build_pages.py), with every sound
# and every piece of music rendered here, nothing taken from a machine's own renders.
#
#   tools/build_game.sh [out_dir]          needs uv; the music needs Surge XT (macOS: brew install --cask surge-xt;
#                                          Linux: its .deb, see .github/workflows/game.yml) and, on Linux, 7z
#
#   1. the recorded instruments (music/fetch_samples.py: about 600 MB, kept in music/samples/, fetched once), and
#      steps 1 and 2 only when the music's sources changed since the last render (the stamp below)
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
# a render that fails can hang on its way out (Surge's threads keep the process alive): where GNU timeout is (Linux, CI),
# each render job is given an hour, so a failure fails instead of waiting for the job's own limit
LIMIT=$(command -v timeout >/dev/null 2>&1 && echo "timeout 3600" || true)

# The music is rendered again only when what makes it has changed: a stamp of the music's sources (its scripts and its
# data, music/*.py and *.json, less sfx*: the sound effects are made every time, in seconds) is kept beside the renders; the same stamp and every track there: the renders are kept.
# (CI keeps music/site/audio in its cache under the same stamp: .github/workflows/game.yml.)
RENDERS=music/site/audio
STAMP=$(python3 -c 'import hashlib, pathlib; print(hashlib.sha256(b"".join(p.name.encode() + p.read_bytes() for p in sorted(pathlib.Path("music").glob("*.[pj][ys]*")) if p.suffix in (".py", ".json") and not p.name.startswith("sfx"))).hexdigest()[:16])')
TRACKS="fixed_side_street_day fixed_far_shore_day fixed_side_street_night fixed_far_shore_night_c fixed_old_mossback final_bright_dream menu_tide_high menu_tide_full"
fresh=yes
[ "$(cat $RENDERS/.stamp 2>/dev/null)" = "$STAMP" ] || fresh=no
for t in $TRACKS; do [ -f "$RENDERS/$t.wav" ] || fresh=no; done
if [ "$fresh" = yes ]; then
  echo "music: its sources are unchanged ($STAMP): the renders are kept"
else
  echo "music: rendering ($STAMP)"
  mkdir -p $RENDERS                             # (not in git: a fresh checkout has no music/site/audio, and no script makes it)
  rm -f $RENDERS/.stamp
  $AUDIO music/fetch_samples.py
  $AUDIO music/sampler.py
  # the pieces the game plays (master.py reads all of its list: far shore night D too), one job after the other: each
  # loads dozens of Surge instances (slowtide.py its own pool of them), and three at once on a 4-core runner crawled
  # past 40 minutes where each alone takes a few
  $LIMIT $SURGE music/pieces.py cute1 shore mc1 shore_night_c shore_night_d mossback2
  $LIMIT $SURGE music/bright.py
  $LIMIT $SURGE music/slowtide.py high full
  $AUDIO music/master.py
  $SURGE music/refit.py
  echo "$STAMP" > $RENDERS/.stamp
fi
$AUDIO tools/build_audio.py
$AUDIO tools/build_pages.py "$OUT"
