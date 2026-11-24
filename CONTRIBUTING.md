# Contributing

## Commit messages: Conventional Commits

Every commit on main follows [Conventional Commits](https://www.conventionalcommits.org): CI checks each one
(`commitlint.config.mjs`: the conventional rules; body lines may be long).

    <type>(<scope>): <subject in lower case, no final full stop, about 72 characters at most>

    <body: what changed and why, as long as it needs>

- **type**: `feat` (new behaviour), `fix` (a bug), `perf`, `refactor` (no behaviour change), `test`, `docs`,
  `build` (pyproject, uv.lock), `ci` (.github), `chore` (tools, anything else), `style`, `revert`.
- **scope**: the main part touched: `web`, `sim`, `server`, `world`, `account`, `e2e`, `tests`, `music`,
  `design`, `pages`, `tools`, `deps`.
- Breaking changes (`feat!:` or a `BREAKING CHANGE:` footer) make a major release: none so far.

Optional hooks (ruff, and the message check at commit time): `uvx pre-commit install`.

## Releases: tag to release

Nobody bumps a version by hand.

1. Nothing releases on a push to main. To release, tag the commit `release` and push the tag
   (`git tag -f release && git push -f origin release`), or run the workflow from the Actions tab. That runs
   `.github/workflows/semantic-release.yml` on that commit (it must be main's newest), then deletes the `release` tag. python-semantic-release reads the commits
   since the last tag `vX.Y.Z`: a `feat` makes the next minor, a `fix` or `perf` the next patch (while the
   version is 0.x; `major_on_zero = false`). Other types make no release.
2. When there is one, it sets `project.version` in pyproject.toml (and uv.lock), adds it to CHANGELOG.md,
   commits `chore(release): vX.Y.Z`, tags `vX.Y.Z`, pushes, and makes the GitHub Release with the notes.
3. `.github/workflows/release.yml` builds the sdist and wheel (`uv build`) for the tag and attaches them to the
   release. Nothing goes to PyPI.

Preview what the next release would be: `uvx --from python-semantic-release semantic-release --noop version --print`.

## Checks

`.github/workflows/ci.yml` (pull requests and main): ruff, the unit tests (`uv run pytest tests -q
--ignore=tests/e2e`, Python 3.14), prettier on the web client, commit messages. `security.yml` (pull
requests, main, weekly): CodeQL, uv audit, gitleaks, bandit. Not blocking for now: ruff format, prettier,
the ruff rules listed in `ignore` in pyproject.toml, and bandit.

## Working on the code

This repository is the game: the authoritative server and simulation, world generation, the browser client, the
agent API (JSON over a websocket), and the game's tools and tests. The AI players are in
[nexel-agent](https://github.com/sofianedjerbi/nexel-agent).

`DESIGN.md` is the design (tick, chunks, the agent API), `JOURNAL.md` the development log, `CLAUDE.md` the original
brief.

### Setup

Python 3.14.

```sh
python -m venv .venv && . .venv/bin/activate      # or: uv venv && uv pip install -e .
pip install -e ".[art]"
python tools/install_assets.py <the two zips>     # once: the art (README, "Art")
python tools/build_audio.py                       # once: the sound effects (pip install -e ".[audio]"; music/PROCESS.md)
nexel-worlds                                      # world in saves/default, http://127.0.0.1:7777/
python -m nexel_worlds.cli --name me              # a terminal client
```

Open http://127.0.0.1:7777/, type a name and press Enter to play (`/?follow=<name>` follows a player without
playing). With uv: `uv sync` then the same commands under `uv run`.

### The art

`tools/install_assets.py` copies the sheets the game uses into `src/nexel_worlds/web/assets/` and makes the tiles
derived from them (`tools/build_assets.py`). They are git-ignored there (`.gitignore`; the list is
`src/nexel_worlds/art.py`), so they can't be committed by mistake. Don't zip up and share that folder.

The pictures that are in the repository were drawn for this game (the enemy sheets, `design/enemies/`), made by its
code (the `sprout-pixel.ttf` font, `tools/build_font.py`) or are screenshots of it (`title_*.webp`, `tools/pages/`).
Credits: `src/nexel_worlds/web/assets/CREDITS.md`. Music samples are fetched, not committed
(`music/fetch_samples.py`).

### Programs that play (the agent API)

A program joins at `ws://127.0.0.1:7777/agent` and gets observations and tools as JSON (`DESIGN.md`, "Agent API";
`src/nexel_worlds/client.py` is a small async client). Programs on this machine use the world's key:
`NEXEL_AGENT_KEY=$(cat saves/default/agent.key)`. Scripted bots and the language-model players are in
[nexel-agent](https://github.com/sofianedjerbi/nexel-agent).

### Asking who players are (optional)

A world can ask for an email login: a six-digit code by mail, then a signed ticket the world checks. It never sees
the email.

```sh
brew install mailpit && mailpit                                    # catches the mail: inbox at http://127.0.0.1:8025
python -m nexel_worlds.account --origin http://127.0.0.1:7777      # the account service, on :7780, data in accounts/
nexel-worlds --accounts http://127.0.0.1:7780
```

### Tests

```sh
pip install pytest pytest-asyncio pytest-xdist pytest-rerunfailures playwright   # or: uv sync (the dev group)
pytest -q                     # the unit suite (in parallel: -n 6 by default, `-n 2` on a busy machine)
pytest -m e2e                 # plays the game in Chrome (Playwright; needs the art): minutes
```

Without the art the unit suite passes; the tests that read the sheets are skipped and say why.
