"""Async client for the Agent API (used by the CLI, scripted bots and the thinker harness)."""

import asyncio
import itertools
import json

from websockets.asyncio.client import connect


class ApiError(Exception):
    def __init__(self, reply: dict):
        super().__init__(f"{reply.get('error')}: {reply.get('detail')}")
        self.reply = reply
        self.code = reply.get("error")


class Client:
    def __init__(self, url: str = "ws://127.0.0.1:7777/agent"):
        self.url = url
        self.ws = None
        self.ids = itertools.count(1)
        self.pending: dict[int, asyncio.Future] = {}
        self.reader = None
        self.agent = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def connect(self):
        self.ws = await connect(self.url, max_size=2**22)
        self.reader = asyncio.create_task(self._read())

    async def close(self):
        if self.reader:
            self.reader.cancel()
        if self.ws:
            await self.ws.close()

    async def _read(self):
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                fut = self.pending.pop(msg.get("id"), None)
                if fut and not fut.done():
                    fut.set_result(msg)
        finally:
            for fut in self.pending.values():
                if not fut.done():
                    fut.set_exception(ConnectionError("connection closed"))
            self.pending.clear()

    async def request(self, op: str, **kw) -> dict:
        mid = next(self.ids)
        fut = asyncio.get_running_loop().create_future()
        self.pending[mid] = fut
        await self.ws.send(json.dumps({"id": mid, "op": op, **kw}))
        return await fut

    async def hello(self, name: str, token: str, persona: str = "") -> dict:
        r = await self.request("hello", name=name, token=token, persona=persona)
        if not r.get("ok"):
            raise ApiError(r)
        self.agent = r["agent"]
        return r

    async def observe(self) -> dict:
        r = await self.request("observe")
        if not r.get("ok"):
            raise ApiError(r)
        return r["obs"]

    async def act(self, tool: str, **args) -> dict:
        """Run one action and return the full reply ({ok, result} or {ok: False, error, detail})."""
        return await self.request("act", tool=tool, args=args)
