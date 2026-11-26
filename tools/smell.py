"""The web client's code-health counts (nexel-worlds#5, the duplicated-logic audit), and a ratchet on them.

    uv run python tools/smell.py            # the counts, the long functions, the special cases per file
    uv run python tools/smell.py --write    # after lowering a count: store the new counts in tools/smell.json

tests/test_smell.py fails when a count goes over what tools/smell.json holds, so a smell can only go down.
What each count is:
- patch_comments: lines telling the story of a past fix ("it was", "no longer", "used to"...), where a comment should
  say what the code does now.
- literal_16: the bare number 16 in code (a tile's or a level's art px), where a name says which (`P`, `RELIEF_STEP`).
- cell_defs: `CELL = 48` (a sprite cell) typed in more than one file.
- hdlook_chars, hdlook_branches: the size of the HD look's one closure (hd.js HdLook).
- long_functions: functions over 60 lines or 6000 characters.
- big_files: hand-written web files over BIG_FILE characters (nexel-worlds#11: lines that run to 700 characters
  kept files under the line cap of tests/test_code_size.py while they grew to 60 KB).
- long_lines: lines over LONG_LINE characters in the hand-written web files.
- special_cases: branches (`if`, `?`, `&&`, `||`) that test for one kind of place or body (ladder, stairs, water...),
  the guards each consumer adds for itself instead of asking one owner.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = ROOT / "src" / "nexel_worlds" / "web" / "js"
BASELINE = Path(__file__).with_name("smell.json")
GENERATED = {"rules.js", "title_map.js"}     # (written by rules.py and tools/build_title_scene.py, not by hand)
BIG_FILE, LONG_LINE = 24_000, 160

PATCH = re.compile(r"\b(It was|it was|It went|it went|They were|they were|was drawn|were drawn|stayed|no longer|used to"
                   r"|before:|as before|the old way)\b")
SIXTEEN = re.compile(r"(?<![\w.])16(?![\w.])")
CELL = re.compile(r"\bCELL = 48\b")
NOTE = re.compile(r"//.*$")
QUOTED = re.compile(r'"(\\.|[^"\\])*"|\'(\\.|[^\'\\])*\'|`[^`]*`')
FUNCTION = re.compile(r"^\s{0,6}(?:async )?function (\w+)\(|^\s{0,6}(?:const|let) (\w+) = (?:async )?(?:\([^)]*\)|\w+) => \{\s*(//.*)?$"
                      r"|^\s{0,6}(?:const|let) (\w+) = \(\(\) => \{|^\s{0,6}api\.(\w+) = (?:\([^)]*\)|\w+) => \{")
BRANCH = re.compile(r"\bif \(|\? ")
SPECIAL = {
    "ladder": r'"l"|ladder|onLadder|climbOf|Climb\.', "stairs": r'"stairs"|stair\(',
    "water": r"wet\(|swim|\.sail|water\(|H0\.water|Flow\.", "air": r"Leap\.|leapAt|\.fall\b|falling\(|\.hop\b",
    "roof/cave": r'hollow\(|"roof"|under\(|cov0?\b|roofAt|winMap|\bdep\b', "bridge/model": r"Models\.|bridge",
    "mine": r"id === myId|=== p\b|q === p|mine\b", "build": r"Build\.on", "title": r"TitleScene|p\.free|\.rush",
}


def sources():
    return {p.name: p.read_text().split("\n") for p in sorted(JS.glob("*.js"))}


def code(line):
    """A line without its note and with its strings emptied."""
    return QUOTED.sub("''", NOTE.sub("", line))


def functions(name, lines):
    """(lines, chars, branches, function name, file, line number) of each function, by counting its braces."""
    for i, line in enumerate(lines):
        m = FUNCTION.match(line)
        if not m:
            continue
        depth, started, chars, ifs, j = 0, False, 0, 0, i
        while j < len(lines):
            s = code(lines[j])
            for ch in s:
                if ch == "{":
                    depth, started = depth + 1, True
                elif ch == "}":
                    depth -= 1
            chars += len(lines[j])
            ifs += len(BRANCH.findall(s))
            if started and depth <= 0:
                break
            j += 1
        yield j - i + 1, chars, ifs, next(g for g in m.groups() if g and not g.startswith("//")), name, i + 1


def special(lines):
    found = Counter()
    for line in lines:
        for statement in NOTE.sub("", line).split(";"):
            if re.search(r"\bif \(|\?|&&|\|\|", statement):
                found.update(k for k, r in SPECIAL.items() if re.search(r, statement))
    return found


def report():
    src = sources()
    funcs = [f for name, lines in src.items() for f in functions(name, lines)]
    hd = next(f for f in funcs if f[3] == "HdLook" and f[4] == "hd.js")
    per = {name: special(lines) for name, lines in src.items()}
    patches = {name: sum(len(PATCH.findall(line)) for line in lines) for name, lines in src.items()}
    long = sorted((f for f in funcs if f[0] > 60 or f[1] > 6000), key=lambda f: -f[1])
    counts = {
        "patch_comments": sum(patches.values()),
        "literal_16": sum(len(SIXTEEN.findall(NOTE.sub("", line))) for lines in src.values() for line in lines),
        "cell_defs": sum(len(CELL.findall(line)) for lines in src.values() for line in lines),
        "hdlook_chars": hd[1], "hdlook_branches": hd[2],
        "long_functions": len(long),
        "special_cases": sum(sum(c.values()) for c in per.values()),
        "big_files": sum(len("\n".join(lines)) > BIG_FILE for name, lines in src.items() if name not in GENERATED),
        "long_lines": sum(len(line) > LONG_LINE for name, lines in src.items() if name not in GENERATED for line in lines),
    }
    return counts, patches, long, per


def counts():
    return report()[0]


def main(argv):
    found, patches, long, per = report()
    print("patch comments per file (the most first):")
    for name, n in sorted(patches.items(), key=lambda t: -t[1])[:20]:
        print(f"  {name}: {n}")
    print("functions over 60 lines or 6000 chars:")
    for lines, chars, ifs, name, file, at in long:
        print(f"  {file}:{at} {name} lines={lines} chars={chars} branches={ifs}")
    print("special cases per file (the most first):")
    keys = list(SPECIAL)
    print("  " + "file".ljust(22) + " ".join(k[:9].rjust(9) for k in keys) + "    sum")
    for name, c in sorted(per.items(), key=lambda t: -sum(t[1].values()))[:20]:
        print("  " + name.ljust(22) + " ".join(str(c[k]).rjust(9) for k in keys) + str(sum(c.values())).rjust(7))
    held = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
    print("counts (now / held in tools/smell.json):")
    for k, v in found.items():
        print(f"  {k}: {v} / {held.get(k, '-')}")
    if "--write" in argv:
        BASELINE.write_text(json.dumps(found, indent=2) + "\n")
        print(f"wrote {BASELINE.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
