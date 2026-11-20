# Nexel Worlds

(The code, the repository and the commands still say `megastructure`: the game's first name.)

A world of your own, a door to everyone else's: an original, persistent, tile-based sandbox where people and AI agents running on local models live side by side.

Work in progress. See `CLAUDE.md` for the brief, `DESIGN.md` for the design and `JOURNAL.md` for the log.

## Run

```sh
uv run python tools/build_audio.py               # sound effects, once and after changing music/sfx.py (see music/PROCESS.md)
uv run python -m megastructure.server            # world in saves/default, http://127.0.0.1:7777/
uv run python -m megastructure.bots --n 8 --minutes 30   # scripted bots
uv run python -m megastructure.cli --name me     # terminal client
uv run pytest -q
```

Open http://127.0.0.1:7777/, type a name and press Enter to play (`/?follow=<name>` follows an agent without playing).

### Asking who players are (optional)

A world can ask for an email login: a six-digit code by mail, then a signed ticket the world checks. It never sees the email.

```sh
brew install mailpit && mailpit                  # catches the mail on this machine: inbox at http://127.0.0.1:8025
uv run python -m megastructure.account --origin http://127.0.0.1:7777      # the account service, on :7780, data in accounts/
uv run python -m megastructure.server --accounts http://127.0.0.1:7780
MEGASTRUCTURE_AGENT_KEY=$(cat saves/default/agent.key) uv run python -m megastructure.bots --n 8   # local programs use the world's key
```
