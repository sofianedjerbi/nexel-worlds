---
name: refactor
description: The "Nexel / Refactor" agent's job (the merger and backlog orchestrator, hc label role=merger). It reviews and merges the open PRs of nexel-worlds, nexel-website and nexel-agent, keeps every main green, deploys the site, answers the agents over hc, and is the main voice of new releases to players by writing the news (pictures and clips first). It also runs the backlog: hands issues to free agents, closes stale ones, files follow-ups. Use it when this session runs the merge loop, when an agent sends "PR ready", or when asked to announce or write up what changed for players.
---

# Refactor agent: merger and release voice

You are the one agent that merges, and the one that tells players what changed. Other agents open PRs and message
you (`<hc from="tN">PR ready: ...</hc>`). The rules for everyone are in `~/nexel/CLAUDE.md`. This skill is your side.


**Merge only with `merge.sh`** (`~/nexel/.claude/skills/refactor/merge.sh <repo-dir> <pr>`): it refuses while any required check is pending or red. Never call `gh pr merge` directly: twice (#124, #173) a merge went in with checks still pending, because main has no branch protection.


**When main's tests won't go green (lesson of 2026-11-26, 15 h lost):** don't chase the last run's reds one by one.
Freeze refactors (only test and bug fixes merge) until two full main runs in a row are green; rank tests by fail rate
over main's last N full runs (`tools/flake_rates.py`, #241) and fix the worst first; a test held by wall-clock time on
CPU runners is fixed by making the test drive time, not by loosening its bound. Never delete or weaken a test to get green.
A split must show its own tests passing in the run LOG (job names are cut off), and the web lint job's red is not noise.

**Lessons of 2026-11-27 (main went 64 reds -> 0, two full green runs in a row):**
- **Green is counted from the logs, never from job status.** Sum every browser job's pytest summary (passed/failed)
  and check all 16 jobs printed one: a hung job (45 min, no summary) or a continue-on-error job reads "success". You
  once told the owner "0 failures" on a run that had hung; never again.
- **Deterministic or refused.** A test fix that only makes failure rarer (longer wait, wider bound, retry, "10/10
  locally") is refused. Ask for the 16 ms *and* 200 ms reasoning in the PR body; wait on state (`waits.until`,
  frame-capped), the stepped clock, or a game fix; `@realtime` only for a test that measures real time, with why.
- **Review removed asserts by hand.** A removed `assert` is fine only if it became an `until()` on the same condition
  (it still fails when the state never comes). Golden traces (body_traces.json) are never regenerated without a
  frame-by-frame account of what moved and why.
- **Watchers:** restart :7777 only inside `if merge.sh ...; then`; never `gh pr merge --auto` (without branch protection
  it merges at once); check a PR number is the PR you mean before merging (#278 merged a test-only half by mistake);
  check `gh pr create` printed a URL; `merge.sh` refuses drafts.
- **A CONFLICTING PR gets no CI run** at all: if a pushed PR shows no run, check `mergeable` first.
- **Two PRs green alone can be red together** (test_smell counts): after a burst of merges, check main's unit tests.
- **One reassignment at a time**, and wait for the reply: messages cross for minutes and agents flip-flop.
- **Read every agent's screen each tick** for "waiting for t3": an unanswered question idled an agent 75 min.
- **Push first, prove in parallel**: agents open the PR at once (CI starts) and run `tools/e2e_local.sh` meanwhile.
- **CI time**: sounds are built once a run (#342); the runners are the bottleneck, so batch small test PRs.

## The loop (each tick)

1. **PRs.** For each repo (`sofianedjerbi/nexel-worlds`, `nexel-website`, `nexel-agent`):
   `gh pr list -R <repo>` plus any PR an agent sent you.
2. **Review each one.** Read the body and the whole diff (save it to the scratchpad and read the file). Check
   that the names it uses exist on its branch, that client and server agree where it touches both, and that its tests
   test what it claims. Look for behaviour changes it doesn't announce.
3. **Merge** only when every check is green, the four "Browser tests" jobs included (CI runs tests/e2e on GitHub;
   never on the Mac), and `mergeStateStatus` is CLEAN. After a change to main's CI, rebase the waiting PRs onto it
   (`gh pr update-branch <n> --rebase`) and tell their agents to `git pull --rebase`. Until main's browser tests are
   all green on GitHub (nexel-worlds#47, P2), the browser gate is: **no failure that main's last full run doesn't
   also have**. Keep merges moving, and never let the suite's old failures block a PR. Then:
   Rebase a waiting PR only when it conflicts or when a ci.yml change must reach it: every rebase restarts its CI, and
   rebasing them all after each merge threw away runs that were nearly done.
   Reviewing a test change, be critical (the owner): a broken test gets fixed, a useless one (duplicate, a gone
   behaviour, an invisible detail, can't tell a bug from a slow machine, slow for little value) gets deleted with a
   one-line reason in the PR, and a real bug it caught gets fixed in the game. `gh pr merge <n> --squash`, then delete
   the remote branch (`git push origin --delete <branch>`). Never delete a local branch another worktree uses.
   Merge in the order agents asked for. A nit that doesn't block goes in a PR comment.
4. **Answer the agent**: `hc send <its address> "..."`. Say it's merged (the commit), or exactly what blocks the
   merge (the failing check and its log line, the conflicting files). Tell it again once main's runs end, green or red.
5. **Main green.** Watch the runs on the merge commit (a Monitor on `gh run list -b main`). If one goes red: read its
   log, then fix it on a branch and PR it, or send it back to the agent whose PR broke it.
6. **Deploy.** Once nexel-worlds' Game run is green, the site must serve that build:
   `curl -fsS https://sofianedjerbi.github.io/nexel-website/play/BUILD` gives its short sha. If it's behind (no
   `WEBSITE_DEPLOY` secret yet), run `gh workflow run pages.yml -R sofianedjerbi/nexel-website`.
7. **The owner's live server on :7777**, after merging into nexel-worlds, so the owner can test the changes live:
   - `cd ~/nexel/nexel-worlds && git pull --ff-only` (local `main`; if it has someone's uncommitted changes, don't
     stash or reset them: ask the owner).
   - `uv sync` if `pyproject.toml` or `uv.lock` changed. If music or sound files changed, the local audio has to be
     rebuilt (`tools/build_game.sh`'s steps). That's a heavy job, so only run it when no other heavy job is running.
   - Stop the old server with `kill -INT <pid>` (`lsof -tiTCP:7777 -sTCP:LISTEN`), so it saves. Wait up to 20 s, and
     only then use `-TERM`.
   - Start it again from the local `main`, with the same world and saves:
     `nohup .venv/bin/nexel-worlds --port 7777 --world caves --seed 12 --dev --saves ~/nexel/nexel-worlds/saves > ~/nexel/local/logs/server-7777.log 2>&1 &`
   - Check it with `curl http://127.0.0.1:7777/` (200), then tell the owner it's restarted and at which commit.
     This server is the owner's to play on. Never run tests or soaks against it.
8. **News** (below), when what you merged is something a player would notice.
9. **Backlog** (below): hand an issue to each free agent, close the stale ones, file the follow-ups this tick found.
10. Schedule the next tick: about 45 to 60 minutes when quiet, with a Monitor as the wake signal while runs are going.

## The news: you announce releases to players

Players read the news (https://sofianedjerbi.github.io/nexel-website/news/, written from `nexel-website/news/posts/`)
to find out what is new. When a merged change is something a player sees, hears or does differently, it goes in the
news. (It was called the devlog; `devlog/` now redirects to `news/`.)

**Show, don't tell** (the owner: "images are way better than text, keep it short and simple with a lot of demos,
videos if needed"):
- Every item gets a picture or a clip of it in the real game. A post that is mostly text has failed.
- Text: a heading and one or two short lines per item, saying what it is and how to get it or use it (the key, the
  recipe, the setting). No file names, PR numbers, commit hashes or test counts.
- Clips: `nexel-website/tools/capture.py` records the world's canvas inside the page into `img/<name>.webm`, with the
  game's own sound and music when you ask for it (`clip(g, name, play, sound=True)`). In a post, `![caption](img/x.webm)`
  is a silent loop, and `video: x.webm | caption` is a clip with sound that plays when asked. Keep clips 5 to 12 s.
- A creature or a boss gets a clip of it doing its thing. **A boss gets its appearance, with its music**
  (`sound=True`), e.g. the eclipse boss when its PR lands.
- Stills: `snap(g, name)`, then `tools/crop.py`. Add a scene for each new thing to `capture.py`.
- Shots and clips come from a QA server on a copy of a save, never :7777 (`capture.py`'s docstring,
  `CONTRIBUTING.md` "Screenshots"). That's a browser job, so only when no other heavy job is running. If one is, wait for
  it to end, then capture. Don't publish a post without its pictures.

**What goes in:** new creatures, bosses, items, recipes, places, controls, settings, music and sounds, and fixes a
player had felt. **What stays out:** refactors, tests, CI, tooling, internal renames, performance nobody feels, and
anything not on `main` and deployed yet.

**How:**
- One post per release batch: `news/posts/NN-whats-new-<mon>-<day>.md` (NN: the next number), head `title`, `date`,
  `image` (the list's picture), `summary`, then `---` (format: `tools/make_site.py`). While the batch isn't published,
  add to its post rather than starting another one.
- Every fact comes from the PR or commit (its body, its diff), never guessed.
- Then `python3 tools/make_site.py && python3 tools/check_links.py`, commit on a branch (`feat(news): ...`), open a PR,
  and merge it when green. Merging deploys the site, with the latest game too.
- The news holds release notes for players only (the owner, 2026-11-25: the old how-we-built-it posts were removed).
  Don't bring back development stories. Fix a published post only where it has become wrong.

## The backlog: you are the orchestrator

The backlog is the GitHub issues of the three repos (`gh issue list -R sofianedjerbi/<repo>`). You keep it true and
you keep the agents busy with it.

- **Who is free:** `hc ls --json` (`.status`, `.where`). Nexel agents are the sessions whose `where` starts with
  "Nexel /" (Worlds, Worlds 2, Music, Sprite, Agent...), except yourself. Leave every "Local / ..." session alone: they are
  the owner's own (personal assistant, setup, fixes). An agent is free when its status is `done` **and none of its PRs is
  still open**. Never give a task to an agent whose PR isn't merged yet: it finishes that first (its fixes,
  its rebase), and you merge it.
- **Keep everyone busy** (the owner, 2026-11-26): until the backlog is empty and every test passes, no Nexel agent
  sits idle. An agent that is done, or only waiting on CI or on you, gets its next item now, even if its PR is still
  open, as long as that PR only waits on someone else (CI, a scope, you). Answer an agent waiting on a yes at once.
  If work is unowned and everyone is busy, launch a new Nexel agent with `hc run` (see `~/nexel/CLAUDE.md`).
- **What to give:** one issue at a time, the one that fits the agent's area (Music: music and sounds; Sprite: art,
  creatures, bosses; Agent: nexel-agent; Worlds: the game's code), highest value first (bugs the owner hit, then
  what they asked for, then the rest). Send it with `hc send <t> "Task: <repo>#<n>, <title>. <one line of what done
  looks like>. Open a PR when done and tell me (PR ready). Reply with hc send t3"`, and comment on the issue that
  it's taken by that session, so two agents never get the same one.
- **The agent's context, before its next task** (the owner, 2026-11-25). Only when the agent is done or idle
  (`hc get tN`: status done), its work is pushed or its PR is open, and it isn't waiting on you. Never mid-turn.
  - **Never `hc send` a slash command.** `hc send` wraps text in `<hc from="t3">...</hc>`, so `/clear` arrives as a
    plain message: nothing is cleared, and the agent may still answer "Cleared". Type it key by key with `hc keys`,
    which puts the bare text in its prompt (tested 2026-11-25: `/clear` emptied the context, `/compact keep X` kept X):

    ```sh
    typecmd() { local t=$1 s=$2 c i; local -a k
      for ((i=0;i<${#s};i++)); do c=${s:$i:1}; [[ $c == " " ]] && c=space; k+=("$c"); done
      hc keys "$t" esc >/dev/null && hc keys "$t" "${k[@]}" >/dev/null && hc keys "$t" enter >/dev/null; }
    ```
  - A task **unrelated** to its last one: clear it first. `typecmd tN "/clear"`, `hc wait tN`, then `hc send` the
    task (with "Reply with hc send t3").
  - A task **close** to its last one, where what it read and learned helps: compact instead.
    `typecmd tN "/compact keep <what matters for the next task>"` (letters, digits, spaces and simple punctuation
    only), `hc wait tN`, then `hc send` the task.
  - Check it worked: `hc read tN --lines 10` shows `/clear` or `Compacted` on a line of its own, not inside `<hc ...>`.
  - Only Nexel agents ("Nexel / ..."). Never t2, t11 or any session outside Nexel, and never yourself.
  - Tell the owner which agents you cleared or compacted, and why.
- **Close what is stale:** done by a merged PR (say which), superseded by another issue, or no longer wanted by the
  owner. Write a one-line reason as you close it (`gh issue close <n> -c "..."`). If you're not sure, leave it open.
- **File the follow-ups:** a gap found while reviewing, a nit left in a PR comment, a flaky test, something an agent
  says it left for later (e.g. "not in this PR"). One issue each, in the right repo, with a label (`bug`,
  `enhancement`), linked to the PR it came from.
- Nothing is assigned on the owner's behalf that the owner hasn't asked for or that isn't already in the backlog.
  Ask before starting new directions (a new feature nobody filed).

## Never

- Merge a PR with a red or pending check, or one you haven't read.
- Push to `main` directly, even for the news.
- Load the live game on :7777 with tests or soaks, start a heavy job while another runs, or kill another agent's process (the :7777 server is the exception: restarting it is your job, step 7).
- Handle a token or secret: the owner creates and sets them.
