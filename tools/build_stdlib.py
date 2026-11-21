"""Python's own library for the demo, without what the game never opens: 2.5 MB on the line down to about 1.3.

Pyodide fetches python_stdlib.zip whole before Python starts: 614 files, of which the game's server uses a hundred.
What is left out here is named, by hand (DROP: XML, tests, debuggers, a terminal, other processes, the web's
servers; and the tables of the world's old letter codes, 1.4 MB unpacked, bar the few any program uses: KEEP_CODES).
Everything else stays, used or not. `tools/stdlib_used.txt` is what a played session of the demo had loaded
(`worker.postMessage({t: "modules"})`, then `worldModules`): tests/test_bundle.py fails if a name in it is dropped.

    python tools/build_stdlib.py full.zip out.zip        (tools/build_pages.py does it, from the copy it keeps in .cache/)

The whole file is fetched once from the address js/local_worker.js names and kept in .cache/pyodide/. Where it cannot
be had (no line), the build goes without: the demo then takes Pyodide's own, as before.
"""

import re
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DROP = {"multiprocessing", "xml", "_pyrepl", "unittest", "pdb.py", "doctest.py", "tarfile.py", "pydoc.py", "pydoc_data", "html", "difflib.py",
        "xmlrpc", "pickletools.py", "wsgiref", "statistics.py", "imaplib.py", "mailbox.py", "smtplib.py", "ftplib.py", "poplib.py", "optparse.py", "configparser.py",
        "bdb.py", "cmd.py", "rlcompleter.py", "profile.py", "cProfile.py", "pstats.py", "timeit.py", "trace.py", "tabnanny.py", "pyclbr.py",
        "modulefinder.py", "zipapp.py", "webbrowser.py", "this.py", "antigravity.py", "__hello__.py", "__phello__", "turtle.py", "turtledemo", "tkinter", "idlelib",
        "ensurepip", "venv", "curses", "dbm", "shelve.py", "plistlib.py", "netrc.py", "mailcap.py", "cgi.py", "cgitb.py", "getpass.py",
        "symtable.py", "tty.py", "pty.py", "sched.py", "filecmp.py", "fileinput.py", "socketserver.py", 
        "tomllib", "zoneinfo", "nturl2path.py", 
        "lib2to3", "_osx_support.py", "_aix_support.py",
        "_android_support.py", "_ios_support.py", "_apple_support.py", "_markupbase.py"}
KEEP_CODES = {"__init__", "aliases", "utf_8", "utf_8_sig", "ascii", "latin_1", "utf_16", "utf_16_le", "utf_16_be", "utf_32", "utf_32_le", "utf_32_be", "cp437",
              "cp1252", "iso8859_1", "idna", "punycode", "raw_unicode_escape", "unicode_escape", "hex_codec", "base64_codec", "zlib_codec", "charmap", "undefined"}


def kept(name: str) -> bool:
    top, _, rest = name.partition("/")
    if top == "encodings":
        return rest.rsplit(".", 1)[0] in KEEP_CODES
    return top not in DROP


def trim(full: Path, out: Path) -> tuple[int, int]:
    """Write `out` from `full` without what is dropped; how many files stayed, of how many."""
    with zipfile.ZipFile(full) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as dst:
        names = [i for i in src.infolist() if kept(i.filename)]
        for i in names:
            info = zipfile.ZipInfo(i.filename, (1980, 1, 1, 0, 0, 0))            # (no dates: the same bytes for the same files)
            info.compress_type, info.external_attr = zipfile.ZIP_DEFLATED, i.external_attr
            dst.writestr(info, src.read(i), compresslevel=9)
        return len(names), len(src.infolist())


def full() -> Path | None:
    """Pyodide's whole python_stdlib.zip, of the version the demo's worker names: kept in .cache/, fetched once."""
    address = re.search(r'const PYODIDE = "(https://[^"]+)"', (ROOT / "src" / "megastructure" / "web" / "js" / "local_worker.js").read_text()).group(1)
    f = ROOT / ".cache" / "pyodide" / re.sub(r"\W+", "_", address) / "python_stdlib.zip"
    if not f.exists():
        try:
            body = urllib.request.urlopen(address + "python_stdlib.zip", timeout=20).read()
            zipfile.ZipFile(__import__("io").BytesIO(body)).testzip()
        except Exception as e:  # noqa: BLE001 - no line, or not a zip: the build goes without
            print(f"no smaller python_stdlib ({e}): the demo takes Pyodide's own")
            return None
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(body)
    return f


if __name__ == "__main__":
    print("kept %d of %d files" % trim(Path(sys.argv[1]), Path(sys.argv[2])), Path(sys.argv[2]).stat().st_size, "bytes")
