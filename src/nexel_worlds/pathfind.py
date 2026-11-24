"""Bounded A* over the places a body can stand: a tile and a height (a floor over a room is another place than the
room under it)."""

import heapq


def astar(start, goal, moves, beside=False, max_nodes=2500, max_dist=64):
    """Return the list of places from `start` (exclusive) to the first one on the goal tile, or None.

    A place is (x, y, z); `goal` is a tile (x, y), or a place (x, y, z): that tile at that height; `moves(place)`
    gives the places one step away. `beside`: the goal cannot be stood on, so the way ends on a tile next to it.
    Ties are broken deterministically by insertion order.
    """
    sx, sy = start[:2]
    gx, gy = goal[:2]
    if abs(gx - sx) + abs(gy - sy) > max_dist:
        return None
    left = lambda n: abs(gx - n[0]) + abs(gy - n[1]) - beside
    counter = 0
    open_ = [(left(start), 0, start)]
    came = {start: None}
    cost = {start: 0}
    while open_ and len(came) < max_nodes:
        _, _, cur = heapq.heappop(open_)
        if left(cur) <= 0 and (beside or len(goal) < 3 or cur[2] == goal[2]):
            path = []
            while cur != start:
                path.append(cur)
                cur = came[cur]
            return path[::-1]
        c1 = cost[cur] + 1
        for nxt in moves(cur):
            if nxt in cost or abs(nxt[0] - sx) + abs(nxt[1] - sy) > max_dist:
                continue
            cost[nxt] = c1
            came[nxt] = cur
            counter += 1
            heapq.heappush(open_, (c1 + left(nxt), counter, nxt))
    return None
