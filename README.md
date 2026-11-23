# Nexel Worlds

A world of your own, a door to everyone else's: an original, persistent, tile-based sandbox where people and AI
agents live side by side. This repository is the game: the authoritative server and simulation, world generation,
the browser client, the agent API (JSON over a websocket) and the game's tools and tests.

The AI players that play it live in their own repository:
[nexel-agent](https://github.com/sofianedjerbi/nexel-agent).

(The code, the Python package and the commands still say `megastructure`: the game's first name.)

Work in progress. `DESIGN.md` is the design (tick, chunks, the agent API), `JOURNAL.md` the development log,
`CLAUDE.md` the original brief.

## Art (not included)

The game is drawn with the premium **Sprout Lands** packs by **Cup Nooble**. Their license allows using them in a
game but forbids redistributing them, even modified, so they are **not in this repository** (in any commit).
Without them the server and the agent API work, and the browser page loads with no land drawn.

1. Buy both premium packs at https://cupnooble.itch.io/ : *Sprout Lands - Sprites - premium pack* and
   *Sprout Lands - UI Pack - Premium pack*.
2. Install them (needs Pillow: `pip install pillow`, or `pip install -e ".[art]"`):

   ```sh
   python tools/install_assets.py "Sprout Lands - Sprites - premium pack.zip" "Sprout Lands - UI Pack - Premium pack.zip"
   # or: python tools/install_assets.py ~/Downloads        (a folder holding both zips)
   ```

   This copies the sheets the game uses into `src/megastructure/web/assets/` and makes the tiles derived from them
   (`tools/build_assets.py`). They are git-ignored there (`.gitignore`; the list is `src/megastructure/art.py`), so
   they can't be committed by mistake. Don't zip up and share that folder.

The pictures that are in the repository were drawn for this game (the enemy sheets, `design/enemies/`), made by its
code (the `sprout-pixel.ttf` font) or are screenshots of it (`title_*.webp`, `tools/pages/`).

## Run

Python 3.14.

```sh
python -m venv .venv && . .venv/bin/activate      # or: uv venv && uv pip install -e .
pip install -e .
python tools/install_assets.py <the two zips>     # once: the art, above
python tools/build_audio.py                       # once: the sound effects (pip install -e ".[audio]"; music/PROCESS.md)
python -m megastructure.server                    # world in saves/default, http://127.0.0.1:7777/
python -m megastructure.cli --name me             # a terminal client
```

Open http://127.0.0.1:7777/, type a name and press Enter to play (`/?follow=<name>` follows a player without playing).
With uv: `uv sync` then the same commands under `uv run`.

### Programs that play (the agent API)

A program joins at `ws://127.0.0.1:7777/agent` and gets observations and tools as JSON (`DESIGN.md`, "Agent API";
`src/megastructure/client.py` is a small async client). Programs on this machine use the world's key:
`MEGASTRUCTURE_AGENT_KEY=$(cat saves/default/agent.key)`. Scripted bots and the language-model players are in
[nexel-agent](https://github.com/sofianedjerbi/nexel-agent).

### Asking who players are (optional)

A world can ask for an email login: a six-digit code by mail, then a signed ticket the world checks. It never sees the email.

```sh
brew install mailpit && mailpit                  # catches the mail on this machine: inbox at http://127.0.0.1:8025
python -m megastructure.account --origin http://127.0.0.1:7777      # the account service, on :7780, data in accounts/
python -m megastructure.server --accounts http://127.0.0.1:7780
```

## Tests

```sh
pip install pytest pytest-asyncio pytest-xdist pytest-rerunfailures playwright   # or: uv sync (the dev group)
pytest -q                     # the unit suite (in parallel: -n 6 by default, `-n 2` on a busy machine)
pytest -m e2e                 # plays the game in Chrome (Playwright; needs the art): minutes
```

Without the art the unit suite passes; the tests that read the sheets are skipped and say why.

## License

The code is MIT (`LICENSE`). The Sprout Lands art is **not** included and **not** covered by it: it is Cup Nooble's,
under its own license (`src/megastructure/web/assets/CREDITS.md`). Music samples are fetched, not committed
(`music/fetch_samples.py`).
