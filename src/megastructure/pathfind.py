"""Bounded 4-connected A* over the tile grid."""

import heapq

NEIGHBOURS = ((0, -1), (1, 0), (0, 1), (-1, 0))


def astar(passable, start, goal, max_nodes=2500, max_dist=64, occupied=frozenset(), step=None):
    """Return a list of tiles from start (exclusive) to goal (inclusive), or None.

    If the goal itself is impassable, path to an adjacent tile instead. `step(a, b)`, if given, says whether you
    can go from tile a to its neighbour b (cliffs and stairs).
    Ties are broken deterministically by insertion order.
    """
    sx, sy = start
    gx, gy = goal
    if abs(gx - sx) + abs(gy - sy) > max_dist:
        return None
    memo = {}

    def ok(p):
        v = memo.get(p)
        if v is None:
            v = memo[p] = passable(*p) and p not in occupied
        return v

    goals = {goal}
    slack = 0
    if not ok(goal):
        goals = {(gx + dx, gy + dy) for dx, dy in NEIGHBOURS if ok((gx + dx, gy + dy))}
        if not goals:
            return None
        slack = 1
    if start in goals:
        return []

    counter = 0
    open_ = [(abs(gx - sx) + abs(gy - sy), 0, start)]
    came = {start: None}
    cost = {start: 0}
    while open_ and len(came) < max_nodes:
        _, _, cur = heapq.heappop(open_)
        if cur in goals:
            path = []
            while cur != start:
                path.append(cur)
                cur = came[cur]
            return path[::-1]
        cx, cy = cur
        c1 = cost[cur] + 1
        for dx, dy in NEIGHBOURS:
            nxt = (cx + dx, cy + dy)
            if nxt in cost or not ok(nxt) or (step is not None and not step(cur, nxt)):
                continue
            if abs(nxt[0] - sx) + abs(nxt[1] - sy) > max_dist:
                continue
            cost[nxt] = c1
            came[nxt] = cur
            counter += 1
            h = abs(gx - nxt[0]) + abs(gy - nxt[1]) - slack
            heapq.heappush(open_, (c1 + h, counter, nxt))
    return None
