"""The game reads codes, never the words written for people (#6): a reworded line must change no behaviour. The
build hints were the first: build mode told "nothing holds it" from the other answers by matching four sentences
(build.js UNHELD), so rewording one would have lost the dotted ghost. Their reasons are codes of one table now
(floors.js WHY), the words read from it only to be shown."""

import re
from pathlib import Path

JS = Path(__file__).parent.parent / "src" / "nexel_worlds" / "web" / "js"

# a hint's or a message's words compared with a sentence, or looked up in a set of them
PROSE = re.compile(r"""\btext\s*[!=]==?\s*["'`][A-Z]|["'`][A-Z][^"'`]*["'`]\s*[!=]==?\s*\w+\.text\b|\.has\(\s*\w+\.text\s*\)""")


def test_no_script_tells_answers_apart_by_their_words():
    hits = [f"{p.name}:{i}: {line.strip()[:120]}" for p in sorted(JS.glob("*.js"))
            for i, line in enumerate(p.read_text().splitlines(), 1) if PROSE.search(line)]
    assert not hits, hits


def test_the_reasons_build_mode_reads_are_codes_with_their_words_in_one_table():
    """UNHELD holds codes of WHY, and WHY's words are written nowhere else: a reason is given by its code."""
    floors = (JS / "floors.js").read_text()
    table = re.search(r"const WHY = \{(.*?)\};", floors, re.S).group(1)
    why = dict(re.findall(r"(\w+): \"([^\"]+)\"", table))
    unheld = set(re.findall(r"\"(\w+)\"", re.search(r"const UNHELD = new Set\(\[(.*?)\]\)", floors).group(1)))
    assert unheld and unheld <= set(why), unheld - set(why)
    rest = re.sub(r"//.*", "", floors.replace(table, "") + (JS / "build.js").read_text() + (JS / "climbing.js").read_text())   # (code, not its notes)
    unheld_words = [why[c] for c in unheld if f'"{why[c]}"' in rest]
    assert not unheld_words, unheld_words
