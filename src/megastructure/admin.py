"""Admins: an operator role outside the world (the owner asked, 2026-11-22). The world itself keeps no masters: its
rules (claims, who may dig what) are the same for everyone; an admin only has the server's commands from the chat
line (/tp, /summon, /give... admin_cmds.py), as a server's operator has in many sandbox games. Nothing in the world
shows it: a crown by the name in the list Tab shows (who.js), and that is all.

Who is one: a name in the world's save (meta `admins`), given by the server's `--admin NAME`, by a line of
saves/<world>/admins.txt (read when the server starts), or by `/op NAME` from an admin. An AI player (any persona but
"human") is never one, whatever a list says. Banned names (meta `banned`) are turned away at the door. Every command
an admin gives is written to events.jsonl (who, what, what came of it)."""

import asyncio
import json
from pathlib import Path

from .admin_cmds import COMMANDS, CmdError, Ctx


class Admins:
    def __init__(self, server, world_dir: Path, names=()):
        self.server, self.sim, self.file = server, server.sim, Path(world_dir) / "admins.txt"
        stored = self.sim.store.get_meta("admins", []) or []
        self.names = set(stored) | set(self._file_names()) | {n.strip() for n in names if n.strip()}
        self.banned = set(self.sim.store.get_meta("banned", []) or [])
        self.sim.admins = self                               # (the dev tools' dev_admin, for the browser tests)
        self.save()

    def _file_names(self) -> list[str]:
        if not self.file.exists():
            return []
        return [ln.strip() for ln in self.file.read_text().splitlines() if ln.strip() and not ln.strip().startswith("#")]

    def save(self):
        self.sim.store.set_meta("admins", sorted(self.names))
        self.sim.store.set_meta("banned", sorted(self.banned))
        self.sim.store.commit()

    def is_admin(self, a) -> bool:
        return a is not None and not a.bot and a.name in self.names

    def op(self, name: str) -> str:
        a = self.sim.by_name.get(name)
        if a is None:
            raise CmdError(f"No player called {name}")
        if a.bot:
            raise CmdError(f"{name} is an AI player: AI players can't be admins")
        if name in self.names:
            return f"{name} is already an admin"
        self.names.add(name)
        self.save()
        return f"{name} is now an admin"

    def deop(self, name: str) -> str:
        if name not in self.names:
            raise CmdError(f"{name} is not an admin")
        self.names.discard(name)
        if name in self._file_names():                     # (or the file gives it back when the server starts again)
            self.file.write_text("".join(ln + "\n" for ln in self.file.read_text().splitlines() if ln.strip() != name))
        self.save()
        return f"{name} is no longer an admin"

    def refuse(self, a) -> bool:
        """At the door: a banned name is sent away (True)."""
        if a.name not in self.banned:
            return False
        self.sim.logout(a)
        return True

    def kick(self, a, why: str):
        ws = self.server.conns.get(a.id)
        if ws is not None:
            asyncio.get_running_loop().create_task(ws.close(4001, why))

    # ------------------------------------------------------------ the chat line
    def cmds(self, a) -> dict:
        """What this player may use (the page's list and /help), and what the arguments can be."""
        mine = self.is_admin(a)
        return {"cmds": [{"name": n, "usage": c.usage, "desc": c.desc, "args": list(c.args)}
                         for n, c in COMMANDS.items() if mine or not c.admin],
                "all": list(COMMANDS), "admin": mine, **Ctx.choices()}

    def run(self, a, line: str) -> dict:
        """One command typed in the chat line ("/tp 0 0"): {"ok", "text"} (and "unknown" if it is no command here)."""
        line = line.strip()
        words = line.lstrip("/").split()                   # (no shlex: the demo's Python has only what the game uses, tools/stdlib_used.txt)
        if not words:
            return {"ok": False, "text": "Type /help", "unknown": True}
        name, args = words[0].lower(), words[1:]
        c = COMMANDS.get(name)
        if c is None:
            return {"ok": False, "text": f"Unknown command /{name}: type /help", "unknown": True}
        if c.admin and not self.is_admin(a):
            out = {"ok": False, "text": "You can't do that"}
            self.log(a, line, out)                         # (tried and refused: written down too)
            return out
        try:
            out = {"ok": True, "text": c.fn(Ctx(self, a), args)}
        except CmdError as e:
            out = {"ok": False, "text": str(e)}
        except (ValueError, IndexError):
            out = {"ok": False, "text": f"Usage: {c.usage}"}
        if c.admin:
            self.log(a, line, out)
        return out

    def log(self, a, line: str, out: dict):
        log = self.sim.event_log
        if log:
            log.write(json.dumps({"tick": self.sim.tick, "type": "admin", "by": a.name, "cmd": line[:200],
                                  "ok": out["ok"], "text": out["text"][:200]}, separators=(",", ":")) + "\n")
            log.flush()
