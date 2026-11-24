"""Who perceives what happens: one rule, for an AI player, a person at a screen, and a screen that only watches.

It was two. An agent heard an event inside a square of that event's radius (given at each `emit`); every screen was
sent every event in the world, and the page had no distance test: a person read every `say` of the whole world in
the chat, where an agent heard twelve tiles."""

from .constants import LAYER, SAY_R, SHOUT_R, VIEW_R

EVERYWHERE = None
# How far each kind of event carries, in tiles. What is not here carries as far as a body sees (VIEW_R).
RANGE = {"say": SAY_R, "give": SAY_R, "shout": SHOUT_R, "mail": SHOUT_R,
         "craft": 4, "chest": 4, "trough": 6, "xp": 8,                # small things: only who is right there
         "join": EVERYWHERE, "leave": EVERYWHERE, "death": EVERYWHERE,  # the world's news: the chat's own lines
         "water": -1}                                                  # (a step of running water: nobody is told each cell)
LAND = ("tile", "floor", "water")      # the land itself changing is no news: every screen is told, to keep its picture true


def hears(l, ev: dict) -> bool:
    """Does the listener `l` perceive `ev`? `l` has a place (x, y; z, its height, if it has one), maybe a name, and
    maybe a `rect` (a screen: the tiles it watches). Heard: what is everywhere, or said to be (`everywhere`); what
    names you (`to`, `owner`: a letter, a gift); what happens on your screen; what is within the event's range of you,
    a square as your view is one, with height counted where the event has one (a layer is half a tile)."""
    r = RANGE.get(ev["type"], VIEW_R)
    if r is EVERYWHERE or ev.get("everywhere") or (l.name and l.name in (ev.get("to"), ev.get("owner"))):
        return True
    x, y, rect = ev["x"], ev["y"], getattr(l, "rect", None)
    if rect and r >= 0 and rect[0] <= x < rect[0] + rect[2] and rect[1] <= y < rect[1] + rect[3]:
        return True
    if l.x is None:
        return False
    dz = (ev["z"] - l.z) * LAYER if "z" in ev and getattr(l, "z", None) is not None else 0
    return max(abs(l.x - x), abs(l.y - y), abs(dz)) <= r
