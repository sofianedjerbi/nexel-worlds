#!/usr/bin/env bash
# merge.sh <repo-dir> <pr>: squash-merge only when every required (non-browser) check is COMPLETED and none failed
# (Conventional Commits on branch commits is ignored: the PR title is the squash subject). Refuses otherwise.
set -euo pipefail
cd "$1"; pr=$2
draft=$(gh pr view "$pr" --json isDraft -q .isDraft); if [ "$draft" = true ]; then echo "REFUSED #$pr: draft"; exit 1; fi
read -r pend red < <(gh pr view "$pr" --json statusCheckRollup -q '"\([.statusCheckRollup[]|select(.name|startswith("Browser tests (")|not)|select(.status!="COMPLETED")]|length) \([.statusCheckRollup[]|select(.name|startswith("Browser tests (")|not)|select(.conclusion=="FAILURE")|select(.name!="Conventional Commits")|.name]|join(",")|if .=="" then "-" else . end)"')
if [ "$pend" != 0 ]; then echo "REFUSED #$pr: $pend required checks still pending"; exit 1; fi
if [ "$red" != "-" ]; then echo "REFUSED #$pr: red required checks: $red"; exit 1; fi
title=$(gh pr view "$pr" --json title -q .title); n=$(( ${#title} + ${#pr} + 4 ))
if [ "$n" -gt 100 ]; then echo "REFUSED #$pr: squash subject would be $n chars (title + ' (#$pr)'), over commitlint's 100: shorten the PR title"; exit 1; fi
gh pr merge "$pr" --squash >/dev/null 2>&1 || true
gh pr view "$pr" --json state,mergeCommit -q '"#\(.number) \(.state) \(.mergeCommit.oid[0:8] // "")"'
