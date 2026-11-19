#!/bin/sh
# Build the in-browser demo and publish it to GitHub Pages from a public repo that only holds the built site
# (the main repo stays private, and GitHub Pages needs a public repo on this plan).
#   tools/publish_demo.sh            first run: creates sofianedjerbi/nexel-worlds-demo and turns Pages on
set -e
cd "$(dirname "$0")/.."
REPO=sofianedjerbi/nexel-worlds-demo
SHA=$(git rev-parse --short HEAD)
uv run python tools/build_pages.py dist
cp tools/README.demo.md dist/README.md
gh repo view "$REPO" >/dev/null 2>&1 || gh repo create "$REPO" --public --description "Nexel Worlds: playable in-browser demo"
cd dist
git init -q -b main
git add -A
git commit -qm "Demo build of $SHA"
git push -qf "git@github.com:$REPO.git" main
gh api "repos/$REPO/pages" >/dev/null 2>&1 || gh api -X POST "repos/$REPO/pages" -f "source[branch]=main" -f "source[path]=/" >/dev/null
echo "published: https://sofianedjerbi.github.io/nexel-worlds-demo/ (Pages takes a minute or two to update)"
