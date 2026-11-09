"""Underground layers. Each level below the surface is a region of the same world, LAYER tiles east of the one above:
tile (x, y) at depth d is stored at (x + d * LAYER, y). So digging, building, items, creatures and saving work
unchanged down there, and people on different levels are simply too far apart to see or hear each other.
The surface is |x| < LAYER / 2."""

LAYER = 1_000_000


def depth(x: int) -> int:
    """0 on the surface, 1 one level down, and so on."""
    return max(0, (x + LAYER // 2) // LAYER)


def local_x(x: int) -> int:
    """The x of this tile on its own level (the same x as the surface tile right above it)."""
    return x - depth(x) * LAYER
