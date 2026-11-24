"""The land's cells: a tile's column, what is in it, how it is saved and sent."""

from functools import lru_cache

# The world is cells, solid or empty. A tile's column is its cells from the bottom (LOW) up to the top (HIGH), a bit
# each, set where the cell is solid (a number as long as it needs: Python's); cell z is the block whose top is at
# height z, so land h high is solid up to cell h (0: sea level). Nothing else is kept about relief: a cave is empty
# cells with solid ones over them, a pit a column dug low. (It was 32 cells, -16 to 15: "make the underground reach
# -512 and the sky max block should be 512 too".) SEA: what a height is added to, to be sent as a char (views.py).
LOW, HIGH, SEA = -512, 512, 1024


@lru_cache(maxsize=None)
def col_solid(level: int) -> int:
    """A plain column: solid up to `level`."""
    return (1 << (max(LOW, min(HIGH, level)) - LOW + 1)) - 1


def col_cave(floor: int, head: int, top: int) -> int:
    """Land `top` high with `head` cells empty over a floor at `floor`."""
    return col_solid(top) & ~(col_solid(min(floor + head, top - 1)) ^ col_solid(floor)) if top > floor + 1 and head > 0 else col_solid(floor)


def col_top(col: int) -> int:
    """The highest solid cell: the land as seen from above."""
    return col.bit_length() - 1 + LOW


def col_floor(col: int) -> int:
    """The lowest ground: the top of the solid cells standing on the bottom."""
    return (~col & (col + 1)).bit_length() - 2 + LOW


def col_surfaces(col: int) -> list[int]:
    """Every height you can stand at in this column: a solid cell with an empty one over it. Lowest first."""
    return _bits(col & ~(col >> 1))


def _bits(v: int) -> list[int]:
    """The heights of the cells whose bit is set, lowest first (a bit at a time: a column is a thousand long)."""
    out = []
    while v:
        low = v & -v
        out.append(low.bit_length() - 1 + LOW)
        v ^= low
    return out


def col_runs(col: int) -> list[int]:
    """The column as the heights where it changes, from the bottom up: solid up to the first, empty up to the second,
    solid up to the third... An odd count: a plain column is one height; a cave under a hill three (its floor, its
    ceiling, the hill's top). How a column is saved and sent."""
    return _bits(col ^ (col >> 1))


def runs_col(runs) -> int:
    col = col_solid(runs[0])
    for i in range(1, len(runs) - 1, 2):
        col |= col_solid(runs[i + 1]) & ~col_solid(runs[i])
    return col
