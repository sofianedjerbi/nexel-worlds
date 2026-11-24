"""Talking and writing: chat, shouts, signs, mail, looking far."""

from ..tiles import DIRS
from .constants import MAX_TEXT, VIEW_R
from .entities import ActionError


class Social:
    """Simulation mixin: talking and writing: chat, shouts, signs, mail, looking far."""

    def _text(self, args) -> str:
        text = str(args.get("text", "")).strip()
        if not text:
            raise ActionError("bad_args", "text required")
        return text[:MAX_TEXT]

    def _tool_say(self, a, args):
        text = self._text(args)
        yield from self.wait(a, 0.1)
        self.stats["chat"] += 1
        a.bump("said")
        self.emit("say", a.x, a.y, z=self.height(a), **{"from": a.name}, text=text, **({"bot": True} if a.bot else {}))   # (bot: the client says it in the robot voice)
        return {}

    def _tool_shout(self, a, args):
        text = self._text(args)
        yield from self.wait(a, 0.1)
        self.stats["chat"] += 1
        a.bump("said")
        self.emit("shout", a.x, a.y, z=self.height(a), **{"from": a.name}, text=text, **({"bot": True} if a.bot else {}))   # (bot: the client says it in the robot voice)
        return {}

    def _tool_write_sign(self, a, args):
        x, y = self.target(a, args)
        text = self._text(args)
        if self.world.block(x, y) not in ("sign", "flag"):
            raise ActionError("no_sign", f"{args.get('dir') or 'that tile'} is {self.describe(x, y)}, not a sign")
        yield from self.wait(a, 0.5)
        if self.world.block(x, y) not in ("sign", "flag"):
            raise ActionError("no_sign", "the sign is gone")
        self.world.set_meta(x, y, {"text": text, "by": a.name})
        self.emit("sign", x, y, by=a.name, text=text)
        return {}

    def _tool_read_sign(self, a, args):
        x, y = self.target(a, args)
        yield from self.wait(a, 0.1)
        m = self.world.meta.get((x, y))
        if self.world.block(x, y) not in ("sign", "flag") or not m:
            raise ActionError("no_sign", f"no readable sign {args.get('dir') or 'there'}")
        return {"text": m.get("text", ""), "by": m.get("by")}

    def _tool_look_far(self, a, args):
        d = str(args.get("dir", "")).upper()
        if d not in DIRS:
            raise ActionError("bad_args", "dir must be one of N, E, S, W")
        yield from self.wait(a, 0.2)
        fx, fy = DIRS[d]
        px, py = -fy, fx  # perpendicular
        rows, seen = [], []
        agents_at = {(o.x, o.y): o for o in self.agents.values() if o.online and o is not a}
        for dist in range(VIEW_R + 1, VIEW_R + 49, 2):
            row = []
            for side in range(-8, 9, 2):
                best = None
                for dd in (0, 1):
                    for ss in (0, 1):
                        x = a.x + fx * (dist + dd) + px * (side + ss)
                        y = a.y + fy * (dist + dd) + py * (side + ss)
                        if (x, y) in agents_at:
                            best = "P"
                            seen.append({"name": agents_at[(x, y)].name, "dx": x - a.x, "dy": y - a.y})
                        elif best is None or best in "~.,:'=o_":
                            ch = self.world.char(x, y)
                            if best is None or ch not in "~.,:'=o_":
                                best = ch
                row.append(best)
            rows.append("".join(row))
        return {"dir": d, "rows_near_to_far": rows,
                "note": f"each char = 2x2 tiles; rows start {VIEW_R + 1} tiles away, left-to-right "
                        f"is {'W->E' if d in 'NS' else 'N->S'}" + (" (reversed for S/W)" if d in "SW" else ""),
                "agents": seen}

    def _mailbox(self, a, args):
        x, y = self.target(a, args)
        if self.world.block(x, y) != "mailbox":
            raise ActionError("no_mailbox", f"{args.get('dir')} is {self.describe(x, y)}, not a mailbox")
        return x, y, dict(self.world.meta.get((x, y)) or {"owner": None, "letters": []})

    def _tool_post(self, a, args):
        """Put a letter in an adjacent mailbox (for its owner; anyone can open it, though)."""
        x, y, m = self._mailbox(a, args)
        text = self._text(args)
        if len(m.get("letters", [])) >= 20:
            raise ActionError("full", "this mailbox is full")
        yield from self.wait(a, 0.5)
        m["letters"] = m.get("letters", []) + [{"from": a.name, "text": text, "tick": self.tick}]
        self.world.set_meta(x, y, m)
        self.emit("mail", x, y, **{"from": a.name}, to=m.get("owner"))
        return {"owner": m.get("owner")}

    def _tool_open_mail(self, a, args):
        """Take every letter out of an adjacent mailbox (yours or not: anarchy)."""
        x, y, m = self._mailbox(a, args)
        yield from self.wait(a, 0.4)
        letters = m.get("letters", [])
        m["letters"] = []
        self.world.set_meta(x, y, m)
        if letters:
            self.emit("mail_opened", x, y, by=a.name, owner=m.get("owner"), n=len(letters))
        return {"owner": m.get("owner"), "letters": letters}
