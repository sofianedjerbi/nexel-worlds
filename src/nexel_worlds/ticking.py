"""The world's clock (server.py's): a tick TICK_HZ times a second of the wall's (as fast as dev_pace says, only with
--dev), the land made in the time to spare. Or LOCKSTEP (browser tests, #276: only with --dev, devtools.py): the ticks
come when the page driving the world asks for them (dev_step), so a page and its world keep one time however slow the
machine draws. The sim runs on ticks alone: lockstep is a mode of this loop, not of the sim."""

import asyncio
import logging
import time

from .sim import TICK_HZ

log = logging.getLogger("nexel_worlds")
FLUSH_EVERY = 10 * TICK_HZ  # ticks (10 s)


class Ticking:
    """Server mixin: the world's clock. Ticks on the wall's clock (TICK_HZ, paced by dev_pace), or in lockstep: the socket
    driving the ticks, the tick it asked for, and the two waits (a tick owed, a tick made)."""

    async def tick_loop(self):
        loop = asyncio.get_running_loop()
        period = 1.0 / TICK_HZ
        nxt = loop.time()
        while not self.stopping.is_set():
            nxt = await self.owed(loop, nxt)            # (lockstep: until the page asks for this tick)
            t0 = time.perf_counter()
            chunks0 = len(self.sim.world.chunks)
            try:
                self.sim.step()
            except Exception:                            # (a bug: written down, and the world goes on: never a clock stopped in silence)
                log.exception("tick %d broke", self.sim.tick)
            self.push_ticks()
            t1 = time.perf_counter()
            if self.sim.tick % FLUSH_EVERY == 0:
                self.sim.flush()
                self.sim.maintain()
            dt = (time.perf_counter() - t0) * 1000
            self.tick_ms.append(dt)
            self.tick_parts.append((self.sim.tick, round(dt, 1), round((t1 - t0) * 1000, 1), self.sim.tick % FLUSH_EVERY == 0))
            if dt > 50:
                log.warning("slow tick %d: %.0f ms (step %.0f ms, chunks %d -> %d)", self.sim.tick, dt,
                            (t1 - t0) * 1000, chunks0, len(self.sim.world.chunks))
            self.ticked.set()
            if self.driver is not None:              # (lockstep: the next tick when the page asks for it, not on the wall's;
                await asyncio.sleep(0)               # each tick sent and answered before the next, however many are owed)
                continue
            nxt += period / getattr(self.sim, "clock_rate", 1)      # (pace: the browser tests' clock, devtools.py dev_pace: only with --dev)
            # In the browser (no threads) land is made in the time to spare, 8 ms at a time, the loop turning three times
            # between two (heard, answered, sent): what the tick said leaves first and the page is answered meanwhile
            # (made in one go, both waited 65 ms behind the land, one tick in six; more on a phone).
            while nxt - loop.time() > 0.03 and not self.sim.world.work(0):
                for _ in range(3):
                    await asyncio.sleep(0)
                self.sim.world.work(time.perf_counter() + min(0.008, nxt - loop.time() - 0.03))
            delay = nxt - loop.time()
            if delay < -1.0:  # fell far behind (e.g. laptop sleep): don't try to catch up
                nxt = loop.time()
                delay = 0
            await asyncio.sleep(max(0.0, delay))

    def init_clock(self):
        self.driver = None             # the socket driving the ticks (dev_lockstep), or None: the wall's clock
        self.step_to = 0               # the tick it asked the world to be at
        self.ticked = asyncio.Event()  # set at each tick made: a dev_step waits for its own
        self.owe = asyncio.Event()     # set when a tick is owed or the driver lets go: the loop waits for it
        self.steps: set = set()        # the dev_step answers on their way (kept: a task nobody holds may be collected mid-wait)

    def dev_clock(self, ws, op: str, msg: dict, answer):
        """dev_lockstep, answered at once; dev_step, answered when its tick is made (the socket goes on meanwhile)."""
        if op == "dev_lockstep":
            return answer(self.lockstep(ws, msg))

        async def stepped():
            answer(await self.step(ws, msg))
        task = asyncio.get_running_loop().create_task(stepped())
        self.steps.add(task)
        task.add_done_callback(self.stepped)

    def stepped(self, task):
        self.steps.discard(task)
        if not task.cancelled() and task.exception() is not None:
            log.error("dev_step broke", exc_info=task.exception())

    async def owed(self, loop, nxt: float) -> float:
        """Before a tick, in lockstep: until one is owed (the driver asked for a later one) or the driver lets go, the
        world's spare work (land made, 8 ms at a time) as on the wall's clock. -> when the next tick is due on the
        wall's clock: now, once it waited (let go again, nothing to catch up), else `nxt` as it was."""
        if self.driver is None:
            return nxt
        while self.driver is not None and self.sim.tick >= self.step_to and not self.stopping.is_set():
            if self.sim.world.work(time.perf_counter() + 0.008):     # (nothing left to make: wait to be owed one)
                self.owe.clear()
                await self.owe.wait()
            else:
                await asyncio.sleep(0)
        return loop.time()

    def jumped(self, t0: int):
        """After a dev op or a /command: the world sent on outside this loop (dev_time, dev_skip, /time set) tells its
        screens the tick it left, in lockstep: a page waits for the tick it asked for to come, and none of theirs was sent."""
        if self.driver is not None and self.sim.tick != t0:
            self.push_ticks()

    def lockstep(self, ws, msg: dict) -> dict:
        """dev_lockstep {on}: this socket drives the world's ticks (dev_step), or lets them go back to the wall's clock."""
        if msg.get("on"):
            self.driver, self.step_to = ws, self.sim.tick
        elif self.driver is ws or msg.get("force"):
            self.driver = None
        self.owe.set()
        self.ticked.set()
        return {"lockstep": self.driver is not None, "tick": self.sim.tick}

    async def step(self, ws, msg: dict) -> dict:
        """dev_step {to}: the world at tick `to` (absolute: asked again, or late, nothing is made twice), answered once
        that tick is made and sent to the screens. At most 100 ticks on (10 s) from where it is."""
        if self.driver is not ws:
            return {"ok": False, "error": "not_driver", "tick": self.sim.tick}
        to = min(int(msg.get("to", self.sim.tick + 1)), self.sim.tick + 100)
        self.step_to = max(self.step_to, to)
        self.owe.set()
        while self.sim.tick < to and self.driver is ws and not self.stopping.is_set():
            self.ticked.clear()
            await self.ticked.wait()
        return {"tick": self.sim.tick}
