"""Code that a trailing `//` comment on the same line swallowed.

The web files are long lines of statements with a note at the end. Four times a statement was typed (or merged) after
the note and so was never run: the last one left the land's fog and the lantern measured from the world's origin
(the land turned sky blue 60 tiles from it). A note that goes on with something that reads as a statement is flagged.
"""
import re
from pathlib import Path

JS = Path(__file__).resolve().parents[1] / "src" / "megastructure" / "web" / "js"
NOTE = re.compile(r"""(?<![:"'`\\])//(?!/)(.*)$""")
CODE = [re.compile(p) for p in (
    r"\bgl\.\w+\(.*\);",                              # a WebGL call
    r"\b(const|let|var)\s+[\w$\[{].*=.*;",            # a declaration
    r"\)\s+[\w$.]+\([^()]*(\([^()]*\)[^()]*)*\);",    # "(a note) call(...);"
    r"\)\s+[\w$.\[\]]+\s*[-+*/|&]?=[^=>].*;",         # "(a note) name = ...;"
    r"\b(return|continue|break)\b[^.]*;\s*(}|$)",     # the end of a body
    r"\b(if|for|while)\s*\(.*\)\s*[\w$.{].*;",        # a branch or a loop with a body
)]


def swallowed(line):
    m = NOTE.search(line)
    return bool(m) and any(c.search(m.group(1)) for c in CODE)


def test_the_rule_sees_the_bug_it_was_written_for():
    assert swallowed('gl.uniform3fv(u("go"), sorg);   // (not "st") gl.uniform3fv(u("eye"), eye);')
    assert swallowed("x = 1;   // (a note) y = 2;")
    assert swallowed("a();   // one more  const b = c();")
    assert not swallowed("a();   // HdThings.at(x, y) -> the boxes; card(c, x, y, spr, X);")
    assert not swallowed('const u = "http://a/b"; go(u);')


def test_no_statement_sits_inside_a_trailing_note():
    bad = [f"{f.name}:{n}: {line.strip()[:160]}" for f in sorted(JS.glob("*.js"))
           for n, line in enumerate(f.read_text().splitlines(), 1) if swallowed(line)]
    assert not bad, "a statement after `//` on the same line is never run:\n" + "\n".join(bad)
