#!/bin/sh
# Turns on the repo's git hooks (.githooks/: commit message, staged lint, the unit tests before a push) for this
# checkout and every worktree made from it: git reads core.hooksPath from the shared config, relative to each
# worktree's own root, so each runs the hooks of its own branch.
git config core.hooksPath .githooks && chmod +x .githooks/* && echo "git hooks on: .githooks/ (skip once: --no-verify)"
