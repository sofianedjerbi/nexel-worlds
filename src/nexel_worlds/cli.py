"""Interactive terminal client.

    uv run python -m nexel_worlds.cli --name Me --token secret

Commands: `o` (observe), `<tool> key=value ...` (e.g. `dig dir=N`, `move_to x=3 y=-4`,
`say text="hello there"`), shorthand `n/e/s/w` to step, `tools`, `recipes`, `q`.
"""

import argparse
import asyncio
import json
import shlex

from .client import Client

SHORT = {"n": "N", "e": "E", "s": "S", "w": "W"}


def show(obs):
    me = obs["self"]
    print("\n".join(obs["grid"]))
    print(f"{obs['time']}  ({me['x']},{me['y']})  hp {me['hp']}  hunger {me['hunger']}"
          f"  on {me['standing_on']}")
    print("inventory:", me["inventory"] or "empty")
    print("legend:", "  ".join(f"{k}={v}" for k, v in obs["legend"].items()))
    for e in obs["entities"][:8]:
        print("  near:", e)
    for e in obs["events"][-8:]:
        print("  event:", e)


def parse(line):
    parts = shlex.split(line)
    tool, args = parts[0], {}
    for p in parts[1:]:
        k, _, v = p.partition("=")
        args[k] = int(v) if v.lstrip("-").isdigit() else v
    return tool, args


async def main_async(a):
    loop = asyncio.get_running_loop()
    async with Client(a.url) as c:
        r = await c.hello(a.name, a.token, a.persona)
        print("logged in:", r["agent"])
        show(await c.observe())
        while True:
            line = (await loop.run_in_executor(None, input, "> ")).strip()
            if not line:
                continue
            if line == "q":
                break
            if line == "o":
                show(await c.observe())
                continue
            if line in ("tools", "recipes", "metrics"):
                print(json.dumps(await c.request(line), indent=1))
                continue
            if line in SHORT:
                tool, args = "step", {"dir": SHORT[line]}
            else:
                tool, args = parse(line)
            print(json.dumps(await c.act(tool, **args)))
            show(await c.observe())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="ws://127.0.0.1:7777/agent")
    p.add_argument("--name", default="human")
    p.add_argument("--token", default="human")
    p.add_argument("--persona", default="human player")
    asyncio.run(main_async(p.parse_args()))


if __name__ == "__main__":
    main()
