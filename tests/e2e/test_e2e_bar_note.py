"""The note over the health bar is words for the player, never JSON (#382: "the messages over the health bar sometimes
show JSON"). What writes there (ui.js toast -> overBar): an action's refusal (agent.js errorText, from the world's
code, its data, its agents' sentence), an action's result (a sign, a name, a chest, a crumble, a look far), the
world's events (a letter, a mailbox opened). Each kind is played through the page's own path: every refusal code the
world's code can send (read from its source, so a new one is in here), with no data, with data short of what its words
read, and with an agents' sentence that is a table (rate_limited's was "limits: {'act': (900, 60.0), ...}"); and one
refusal the world really sends."""

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

SRC = Path(__file__).parents[2] / "src/nexel_worlds"
# every refusal code in the world's source: ActionError("code", ...), {"error": "code"}, reply(..., error="code")
CODES = sorted({m[1] for f in SRC.rglob("*.py") for p in (r'ActionError\(\s*"([a-z_]+)"', r'"error":\s*"([a-z_]+)"', r'\berror="([a-z_]+)"')
                for m in re.finditer(p, f.read_text())})
RAW = "limits: {'act': (900, 60.0), 'say': (20, 60.0)}"   # (an agents' sentence that is a table)
BAD = ("{", "}", "[", "]", "undefined", "[object", "NaN", "null")

# each reply played through act() with the world's answer stubbed, the bar read after it -> [[the reply, the bar's text, said]]
PLAY = """async (replies) => { const rpc0 = rpc, out = [];
  try {
    for (const r of replies) {
      rpc = async (op) => (op === 'act' ? r : rpc0(op));
      const bar = $('heldname'); bar.textContent = ''; bar.className = '';
      await act('dig', {dir: 's'});
      out.push([JSON.stringify(r), bar.textContent, bar.classList.contains('on')]);
    }
  } finally { rpc = rpc0; }
  return out; }"""


def bad(text):
    return [b for b in BAD if b in text]


def test_every_refusal_result_and_event_is_said_in_words_over_the_bar(game):
    assert len(CODES) > 30 and "rate_limited" in CODES, CODES
    texts = game.js("Object.keys(ERROR_TEXT)")
    quiet = {"interrupted", "offline", "too_soon"}          # (not said: agent.js act)
    replies = []
    for code in sorted(set(CODES) | set(texts)):
        if code in quiet:
            continue
        for data, detail in ((None, None), ({}, None), (None, RAW), ({}, RAW), ({"why": "far"}, None)):
            r = {"ok": False, "status": "failed", "error": code}
            if data is not None:
                r["data"] = data
            if detail is not None:
                r["detail"] = detail
            replies.append(r)
    replies += [{"ok": False, "error": None}, {"ok": False}, {"ok": False, "error": "no_such_code", "detail": {"a": 1}}]
    said = game.js(PLAY, replies)
    wrong = [s for s in said if not s[2] or not s[1].strip() or bad(s[1])]
    assert not wrong, "not words over the bar: " + json.dumps(wrong[:12])

    # an action's results, and the world's events
    results = [{"ok": True, "result": r} for r in ({"lost": "the ore crumbled"}, {"named": "Bess"}, {"took": {}},
                                                   {"chest": {"wood": 2, "stone": 1}}, {"rows_near_to_far": [], "agents": []},
                                                   {"text": "Keep out"})]
    said = game.js(PLAY, results)
    wrong = [s for s in said if not s[2] or bad(s[1])]
    assert not wrong, "a result not in words over the bar: " + json.dumps(wrong)
    events = game.js("""() => { const out = [], bar = $('heldname');
      for (const e of [{type: 'mail', to: me, from: 'Ana', x: 3, y: 4}, {type: 'mail_opened', owner: me, by: 'Ana', n: 2}]) {
        bar.textContent = ''; onEvent(e); out.push([e.type, bar.textContent, bar.classList.contains('on')]); }
      return out; }""")
    wrong = [s for s in events if not s[2] or not s[1].strip() or bad(s[1])]
    assert not wrong, "an event not in words over the bar: " + json.dumps(events)

    # and one the world really sends: an action it doesn't know (its agents' sentence lists its tools)
    got = game.js("(async () => { const bar = $('heldname'); bar.textContent = ''; const r = await act('fly', {}); return [r.error, bar.textContent]; })()")
    assert got[0] == "unknown_tool" and got[1] and not bad(got[1]), got
    assert not game.errors, game.errors
