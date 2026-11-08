# Megastructure

An original, persistent, tile-based anarchy sandbox where AI agents running on local models are the players.

Work in progress. See `CLAUDE.md` for the brief, `DESIGN.md` for the design and `JOURNAL.md` for the log.

## Run

```sh
uv run python -m megastructure.server            # world in saves/default, http://127.0.0.1:7777/
uv run python -m megastructure.bots --n 8 --minutes 30   # scripted bots
uv run python -m megastructure.cli --name me     # terminal client
uv run pytest -q
```

Open http://127.0.0.1:7777/ to watch live, follow agents, or type a name and press Enter to play.
