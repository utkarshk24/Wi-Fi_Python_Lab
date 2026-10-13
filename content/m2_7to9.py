"""Phase 2 content: modules 2.7-2.9."""

M_2_7 = {
    "id": "2.7",
    "title": "Modules, Packages & Imports",
    "hours": 2.5,
    "summary": "What a module and a package are, the forms of import, how Python finds and caches modules, the __main__ guard, relative imports and circular imports.",
    "concepts": [
        {
            "title": "Modules, packages and import forms",
            "concept": "A **module** is a `.py` file; a **package** is a directory of modules, normally marked with an `__init__.py` that runs when the package is imported. `import pkg.mod` binds the top-level name; `from pkg.mod import name` binds just that object; `as` gives a local alias. Python searches the directories in `sys.path` and caches every imported module in `sys.modules`, so a module's top-level code runs **once** per process. Inside a package, **relative imports** (`from ..units import x`) refer to sibling modules.",
            "why": "A test framework grows into a package: `wifitest/drivers/ap.py`, `wifitest/units.py`, `wifitest/tests/...`. Understanding imports is what lets the same code run from pytest, from a CLI and from a Jenkins job without `ModuleNotFoundError`.",
            "syntax": "import wifitest.drivers.ap          # binds `wifitest`\nfrom wifitest.drivers import ap     # binds `ap`\nfrom wifitest.units import dbm_to_mw as to_mw\nfrom ..units import dbm_to_mw       # relative, inside the package\nimport sys; sys.path, sys.modules",
            "code": """import sys  ## sys.path (where to look) and sys.modules (what's already loaded)
import tempfile  ## A scratch directory to build a real package in
from pathlib import Path  ## For writing the package files


def build_package(root: Path) -> None:  ## Writes a tiny package to disk: wifitest/{__init__, units, drivers/ap}
    pkg = root / "wifitest"  ## The package directory
    (pkg / "drivers").mkdir(parents=True)  ## A sub-package
    (pkg / "__init__.py").write_text('__version__ = "0.1.0"\\n')  ## Runs on `import wifitest`; a common place for the version
    (pkg / "drivers" / "__init__.py").write_text("")  ## Marks drivers as a package
    (pkg / "units.py").write_text("def dbm_to_mw(dbm):\\n    return 10 ** (dbm / 10)\\n")  ## A helper module
    (pkg / "drivers" / "ap.py").write_text(  ## A driver module that uses the helper
        "from ..units import dbm_to_mw\\n"  ## Relative import: up one package, then units
        "def tx_power_mw(dbm):\\n"  ## The function this module provides
        "    return round(dbm_to_mw(dbm), 1)\\n"  ## Uses the imported helper
        "print('ap module loaded as', __name__)\\n"  ## Top-level code: shows when (and how often) the module runs
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:  ## Everything is deleted afterwards
        build_package(Path(tmp))  ## Create the files
        sys.path.insert(0, tmp)  ## Let Python find packages in tmp (normally the project root is already on the path)
        try:  ## Make sure we clean up even if an import fails
            import wifitest  ## Runs wifitest/__init__.py and binds the name `wifitest`
            from wifitest.drivers import ap  ## Loads drivers/ap.py (its print runs now) and binds `ap`
            from wifitest.drivers.ap import tx_power_mw as power  ## Binds one function under an alias
            print(wifitest.__version__, ap.tx_power_mw(20), power(23))  ## Three ways to reach code in the package
            import wifitest.drivers.ap  ## Already in sys.modules: no second "loaded" message
            print(wifitest.drivers.ap is ap, "wifitest.drivers.ap" in sys.modules)  ## Same module object, cached by its full name
            print(Path(ap.__file__).relative_to(tmp))  ## Where the module was loaded from
        finally:  ## Undo our changes to the interpreter
            sys.path.remove(tmp)  ## Stop searching the deleted directory
            for name in [m for m in sys.modules if m.startswith("wifitest")]:  ## Every wifitest module we loaded
                del sys.modules[name]  ## Forget it, so a rerun imports fresh copies


if __name__ == "__main__":
    main()""",
            "under": "`import x` asks each **finder** on `sys.meta_path` to locate `x`, usually by scanning the directories in `sys.path` in order. The first match wins, then a **loader** compiles it (caching bytecode in `__pycache__`), creates a module object, stores it in `sys.modules` **before** running its code, and finally executes the top-level statements. Importing a submodule imports every parent package first. Because of the cache, re-importing is a dictionary lookup.",
            "gotchas": [
                {
                    "title": "Running a package module as a script breaks relative imports",
                    "note": "`python wifitest/drivers/ap.py` runs the file without its package, so `from ..units import ...` has nothing to be relative to. Run it as a module instead: `python -m wifitest.drivers.ap` (here: runpy.run_module).",
                    "wrong": """import runpy, sys, tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    pkg = Path(tmp) / "wifitest"
    (pkg / "drivers").mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "drivers" / "__init__.py").write_text("")
    (pkg / "units.py").write_text("DB_PER_DECADE = 10\\n")
    (pkg / "drivers" / "ap.py").write_text("from ..units import DB_PER_DECADE\\nprint('ok', DB_PER_DECADE)\\n")
    try:
        runpy.run_path(str(pkg / "drivers" / "ap.py"), run_name="__main__")
    except ImportError as err:
        print("ImportError:", err)""",
                    "fixed": """import runpy, sys, tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    pkg = Path(tmp) / "wifitest"
    (pkg / "drivers").mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "drivers" / "__init__.py").write_text("")
    (pkg / "units.py").write_text("DB_PER_DECADE = 10\\n")
    (pkg / "drivers" / "ap.py").write_text("from ..units import DB_PER_DECADE\\nprint('ok', DB_PER_DECADE)\\n")
    sys.path.insert(0, tmp)
    runpy.run_module("wifitest.drivers.ap", run_name="__main__")
    sys.path.remove(tmp)
    for name in [m for m in sys.modules if m.startswith("wifitest")]:
        del sys.modules[name]""",
                }
            ],
            "best": "Use a `src/` layout with one top-level package, install it in editable mode (`pip install -e .`, Module 0.2) so imports work from anywhere, and run entry points with `python -m package.module`. Never name your files after standard-library modules (`json.py`, `random.py`, `logging.py`): they shadow the real ones.",
        },
        {
            "title": "The __main__ guard and circular imports",
            "concept": "Every module has a `__name__`: its import name when imported, or `\"__main__\"` when run directly. Code under `if __name__ == \"__main__\":` therefore runs only when the file is executed as a script, so the same file can be both an importable library and a command-line tool. A **circular import** happens when module A imports B while B imports A: one of them is still half-initialised when the other asks for a name from it, and Python raises `ImportError`.",
            "why": "Lab tools are often written as scripts and later imported by pytest; without the guard, importing them starts a scan or reboots a device. Circular imports appear as soon as `ap.py` needs `Station` and `sta.py` needs `AccessPoint`.",
            "syntax": "def main(): ...\n\nif __name__ == \"__main__\":\n    main()\n\n# break a cycle: move shared code to a third module,\n# or import the module (import ap) and use ap.AccessPoint at call time",
            "code": """import runpy  ## Runs a file as if from the command line
import sys  ## To add our scratch directory to the import path
import tempfile  ## Scratch directory
from pathlib import Path  ## Writing the demo modules

TOOL = '''def scan():  ## A small tool module, stored as text so we can write it to disk
    return ["ap-1", "ap-2"]  ## Pretend scan result

if __name__ == "__main__":  ## True only when the file is run directly
    print("running as a script:", scan())  ## Script behaviour
'''  ## End of the module text


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:  ## Cleaned up at the end
        root = Path(tmp)  ## The scratch directory as a Path
        (root / "scan_tool.py").write_text(TOOL)  ## Library + script in one file
        (root / "ap.py").write_text("from sta import Station\\nclass AccessPoint:\\n    pass\\n")  ## ap needs sta...
        (root / "sta.py").write_text("from ap import AccessPoint\\nclass Station:\\n    pass\\n")  ## ...and sta needs ap: a cycle
        sys.path.insert(0, tmp)  ## Make the modules importable
        try:  ## Always restore the interpreter state
            import scan_tool  ## Importing: __name__ is "scan_tool", so the guarded block does NOT run
            print("imported:", scan_tool.__name__, scan_tool.scan())  ## We can still call its functions
            runpy.run_path(str(root / "scan_tool.py"), run_name="__main__")  ## Like `python scan_tool.py`: the guard runs
            try:  ## Now trigger the circular import
                import ap  # noqa: F401  ## ap starts, imports sta, sta asks the half-built ap for AccessPoint
            except ImportError as err:  ## Python detects the half-initialised module
                print("ImportError:", str(err).split(" (/")[0])  ## The message (file path trimmed for readability)
        finally:  ## Clean up the import system
            sys.path.remove(tmp)  ## Stop searching the scratch directory
            for name in ["scan_tool", "ap", "sta"]:  ## Modules this demo may have loaded
                sys.modules.pop(name, None)  ## Remove them from the cache if present


if __name__ == "__main__":
    main()""",
            "under": "When `ap` is imported, Python registers an empty `ap` module in `sys.modules` and starts running it. Its first line imports `sta`, which runs `from ap import AccessPoint`. Python finds `ap` in `sys.modules`, but `AccessPoint` hasn't been defined yet because `ap` is still on line 1, so the `from` import fails with \"partially initialized module\". A plain `import ap` inside `sta` would succeed (it only needs the module object) as long as `ap.AccessPoint` is used later, at call time.",
            "gotchas": [
                {
                    "title": "Top-level code without a guard runs on import",
                    "note": "Importing a helper to reuse one function executes the whole script, including the action at the bottom.",
                    "wrong": """import sys, tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    Path(tmp, "reboot_tool.py").write_text("def reboot(ap):\\n    return f'rebooting {ap}'\\nprint(reboot('ap-1'))\\n")
    sys.path.insert(0, tmp)
    from reboot_tool import reboot
    sys.path.remove(tmp)
    sys.modules.pop("reboot_tool")""",
                    "fixed": """import sys, tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    Path(tmp, "reboot_tool.py").write_text("def reboot(ap):\\n    return f'rebooting {ap}'\\nif __name__ == '__main__':\\n    print(reboot('ap-1'))\\n")
    sys.path.insert(0, tmp)
    from reboot_tool import reboot
    print("imported without side effects:", reboot.__name__)
    sys.path.remove(tmp)
    sys.modules.pop("reboot_tool")""",
                }
            ],
            "best": "Put every script's behaviour in a `main()` function behind the `__main__` guard. Break import cycles by moving shared types into a lower-level module (`models.py`) that both import, so dependencies point one way: tests → libraries → drivers → models.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Print the `__name__` of the running script and of the imported `math` module.",
            "solution": "The script's name is `__main__`; an imported module's name is its import name.",
            "solution_code": """import math
print(__name__, math.__name__)""",
        },
        {
            "level": "Medium",
            "prompt": "Write a module `channels.py` (in a temp dir) with `DFS = [52, 56, 60, 64]` and `is_dfs(ch)`. Import it twice and prove its top-level code ran only once.",
            "solution": "Put a print at module level; the second import comes from sys.modules.",
            "solution_code": """import sys, tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    Path(tmp, "channels.py").write_text("print('loading channels')\\nDFS = [52, 56, 60, 64]\\ndef is_dfs(ch):\\n    return ch in DFS\\n")
    sys.path.insert(0, tmp)
    import channels
    import channels as again
    print(channels is again, channels.is_dfs(56), channels.is_dfs(36))
    sys.path.remove(tmp)
    sys.modules.pop("channels")""",
        },
        {
            "level": "Hard",
            "prompt": "Implement a driver plugin loader: a package `drivers` with modules `vendor_a.py` and `vendor_b.py`, each defining `NAME` and `connect(host)`. Load a driver chosen by a string at runtime with importlib.",
            "solution": "importlib.import_module builds the module path from text, which is how frameworks select drivers from config.",
            "solution_code": """import importlib, sys, tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    pkg = Path(tmp) / "drivers"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for vendor in ["vendor_a", "vendor_b"]:
        (pkg / f"{vendor}.py").write_text(f"NAME = '{vendor}'\\ndef connect(host):\\n    return f'{{NAME}} connected to {{host}}'\\n")
    sys.path.insert(0, tmp)
    for choice in ["vendor_b", "vendor_a"]:
        driver = importlib.import_module(f"drivers.{choice}")
        print(driver.connect("10.0.0.5"))
    sys.path.remove(tmp)
    for name in [m for m in sys.modules if m.startswith("drivers")]:
        del sys.modules[name]""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What does if __name__ == '__main__' do?", "a": "It runs the guarded code only when the file is executed directly (its `__name__` is then '__main__'), not when it is imported. It lets one file be both an importable module and a script.", "follow": "What is __name__ when the module is imported? (Its import name, e.g. 'wifitest.drivers.ap'.)"},
        {"level": "Intermediate", "q": "How does Python find a module when you import it?", "a": "It checks the `sys.modules` cache first; otherwise finders search `sys.path` in order (script directory, PYTHONPATH, standard library, site-packages). The first match is loaded, cached in sys.modules, and its top-level code runs once.", "follow": "Why can a file named json.py in your project break things? (It shadows the standard library module.)"},
        {"level": "Intermediate", "q": "What causes a circular import and how do you fix it?", "a": "Two modules import each other at the top level, so one asks for a name from the other before it has finished executing. Fix it by moving shared code into a third, lower-level module, by importing the module rather than names from it, or (last resort) by importing inside the function that needs it.", "follow": "What does the error message say? ('cannot import name ... from partially initialized module ... (most likely due to a circular import)'.)"},
        {"level": "Intermediate", "q": "What is __init__.py for?", "a": "It marks a directory as a regular package and runs when the package is first imported, so it can set `__version__`, expose a public API, or define `__all__`. Without it you get an implicit namespace package, which is meant for packages split across several directories.", "follow": "What does __all__ control? (What `from pkg import *` imports.)"},
        {"level": "Advanced", "q": "Why does 'attempted relative import with no known parent package' happen?", "a": "The module was run as a script (`python pkg/mod.py`), so its `__package__` is empty and relative imports can't be resolved. Run it as `python -m pkg.mod` from the project root, or install the package.", "follow": "What does -m change? (It imports the module by its package path and runs it as __main__.)"},
    ],
    "quiz": [
        {"q": "What is `__name__` in a file run with `python tool.py`?", "options": ["'tool'", "'__main__'", "'tool.py'", "None"], "answer": 1, "why": "The entry script is always __main__."},
        {"q": "Where are already-imported modules cached?", "options": ["sys.path", "sys.modules", "__pycache__ only", "os.environ"], "answer": 1, "why": "sys.modules maps names to module objects."},
        {"q": "`from ..units import x` is a...", "options": ["absolute import", "relative import", "syntax error", "wildcard import"], "answer": 1, "why": "Leading dots mean relative to the current package."},
        {"q": "How many times does a module's top-level code run per process (normally)?", "options": ["Every import", "Once", "Twice", "Never"], "answer": 1, "why": "Later imports hit the sys.modules cache."},
        {"q": "Best fix for ap.py and sta.py importing each other?", "options": ["Bare except", "Move shared types to a third module", "Rename one file", "Import *"], "answer": 1, "why": "Make dependencies point one way."},
    ],
    "cards": [
        {"front": "Module vs package", "back": "A .py file vs a directory of modules (usually with __init__.py)."},
        {"front": "sys.path / sys.modules", "back": "Where Python searches / what is already loaded."},
        {"front": "Run a package module as a script", "back": "`python -m pkg.module`"},
        {"front": "Circular import fix", "back": "Move shared code to a lower module; import modules, not names."},
        {"front": "__main__ guard", "back": "`if __name__ == '__main__': main()`"},
    ],
}


M_2_8 = {
    "id": "2.8",
    "title": "Regex for Log Parsing",
    "hours": 3.5,
    "summary": "Pulling structured data out of tool output: search, match, findall, finditer and sub, groups and named groups, verbose patterns, greedy vs lazy quantifiers and flags.",
    "concepts": [
        {
            "title": "Searching and extracting with groups",
            "concept": "The `re` module matches text against patterns. `re.search` finds the first match anywhere; `re.match` only at the start; `re.fullmatch` requires the whole string. `findall` returns every match (the group's text when the pattern has one group), and `finditer` yields match objects. Parentheses create **capture groups**; `(?P<name>...)` names them. `re.compile` pre-builds a pattern you reuse. Always write patterns as **raw strings** (`r\"...\"`).",
            "why": "`iw dev wlan0 station dump`, AP CLI output and supplicant logs are semi-structured text. A few named-group patterns turn them into numbers you can assert on: RSSI, bitrate, channel width, MCS and NSS per station.",
            "syntax": "\\d digit   \\s whitespace   \\w word char   .  any char\n+ one or more   * zero or more   ? optional   {17} exactly 17\n[0-9a-f:]  character class   ^ $  start / end\n(group)  (?P<name>group)  (?:non-capturing)\n\nm = re.search(r\"signal:\\s+(-?\\d+)\", text); m.group(1)",
            "code": """import re  ## The regular-expression module

STATION_DUMP = \"\"\"Station aa:bb:cc:00:00:01 (on wlan0)
\\tsignal:\\t\\t-54 dBm
\\ttx bitrate:\\t1200.9 MBit/s 160MHz HE-MCS 11 HE-NSS 2
Station aa:bb:cc:00:00:02 (on wlan0)
\\tsignal:\\t\\t-71 dBm
\\ttx bitrate:\\t288.2 MBit/s 80MHz HE-MCS 4 HE-NSS 2
\"\"\"  ## Trimmed `iw station dump` output for two stations (\\t is a tab)

MAC = re.compile(r"Station ([0-9a-f:]{17})")  ## One group: 17 characters of hex digits and colons
SIGNAL = re.compile(r"signal:\\s+(-?\\d+) dBm")  ## \\s+ eats the tabs; -? allows a minus sign; \\d+ is the number
RATE = re.compile(  ## A longer pattern with named groups
    r"tx bitrate:\\s+(?P<rate>[\\d.]+) MBit/s (?P<width>\\d+)MHz HE-MCS (?P<mcs>\\d+) HE-NSS (?P<nss>\\d+)"  ## Each (?P<name>...) captures one field
)


def main() -> None:
    print(MAC.findall(STATION_DUMP))  ## With one group, findall returns that group's text for every match
    print([int(s) for s in SIGNAL.findall(STATION_DUMP)])  ## Convert captured text to ints
    for m in RATE.finditer(STATION_DUMP):  ## finditer yields a match object per station
        print(m["rate"], m.group("width"), int(m["mcs"]), m.groupdict()["nss"])  ## Three equivalent ways to read named groups
    first = re.search(r"signal:\\s+(-?\\d+)", STATION_DUMP)  ## The first match anywhere in the text
    print(first.group(1), first.start(), first.end())  ## Captured text and where the whole match starts and ends
    print(re.match(r"signal", STATION_DUMP), bool(re.fullmatch(r"[0-9a-f:]{17}", "aa:bb:cc:00:00:01")))  ## match() only looks at the very start; fullmatch() validates a whole string
    print(re.sub(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", "<mac>", STATION_DUMP.splitlines()[0]))  ## Replace every MAC, e.g. to anonymise a log


if __name__ == "__main__":
    main()""",
            "under": "Python's `re` engine is a **backtracking** matcher: it tries the pattern at each position and backs up when a branch fails. `re.compile` parses the pattern into internal bytecode once (the module also caches recently used patterns, so compiling mostly buys readability and a named constant). Raw strings matter because `\"\\b\"` in a normal string is a backspace character before `re` ever sees it, while `r\"\\b\"` passes backslash-b, the word-boundary assertion.",
            "gotchas": [
                {
                    "title": "Forgetting the raw string",
                    "note": "In a normal string `\\b` becomes a backspace character, so this word-boundary search silently finds nothing.",
                    "wrong": """import re
print(re.search("\\bdeauth\\b", "sta1 deauth reason=15"))""",
                    "fixed": """import re
print(re.search(r"\\bdeauth\\b", "sta1 deauth reason=15"))""",
                },
                {
                    "title": "match() is anchored at the start",
                    "note": "`re.match` returns None for a word in the middle of a line. Use `search` unless you really mean \"starts with\".",
                    "wrong": """import re
print(re.match(r"reason=(\\d+)", "CTRL-EVENT-DISCONNECTED bssid=ap-1 reason=15"))""",
                    "fixed": """import re
m = re.search(r"reason=(\\d+)", "CTRL-EVENT-DISCONNECTED bssid=ap-1 reason=15")
print(m.group(1) if m else "no reason")""",
                },
            ],
            "best": "Compile each pattern once as a module-level constant with a descriptive name, use named groups for anything with more than one field, and always check the match object for None before using it. For plain splits or prefixes, string methods are faster and clearer than regex.",
        },
        {
            "title": "Verbose patterns, greedy vs lazy, flags",
            "concept": "`re.VERBOSE` lets a pattern span lines with comments, which makes long log patterns reviewable. `re.MULTILINE` makes `^` and `$` match at every line instead of only the whole string; `re.IGNORECASE` ignores case. Quantifiers are **greedy** by default (`.*` grabs as much as possible); adding `?` makes them **lazy** (`.*?` grabs as little as possible). Prefer specific classes such as `\\S+` or `[^ ]+` over `.*`.",
            "why": "Measuring the 4-way handshake means pulling the timestamps of EAPOL messages 1 and 4 out of a supplicant log, and extracting disconnect reasons means stopping a capture at the right character. Greedy `.*` is the classic cause of a regex that \"works\" on one line and grabs half the log on another.",
            "syntax": "re.compile(r\"\"\"\n    ^(?P<ts>\\d{2}:\\d{2}:\\d{2}\\.\\d{3})  # timestamp\n    \\s+EAPOL-Key\\s(?P<msg>[1-4])/4\n\"\"\", re.VERBOSE | re.MULTILINE)\n\n.*   greedy      .*?  lazy      \\S+  non-space run",
            "code": """import re  ## Regular expressions

LOG = \"\"\"10:00:01.120 wlan0: CTRL-EVENT-ASSOC bssid=ap-1
10:00:01.130 wlan0: EAPOL-Key 1/4 from ap-1
10:00:01.141 wlan0: EAPOL-Key 2/4 to ap-1
10:00:01.152 wlan0: EAPOL-Key 3/4 from ap-1
10:00:01.160 wlan0: EAPOL-Key 4/4 to ap-1
10:00:07.500 wlan0: CTRL-EVENT-DISCONNECTED bssid=ap-1 reason=15 locally_generated=1
\"\"\"  ## A supplicant-style log of one association, handshake and disconnect

EAPOL = re.compile(  ## A multi-line, commented pattern
    r\"\"\"
    ^(?P<ts>\\d{2}:\\d{2}:\\d{2}\\.\\d{3})  # timestamp hh:mm:ss.mmm
    \\s+\\w+:\\s+EAPOL-Key\\s           # interface name, then the event
    (?P<msg>[1-4])/4                     # handshake message number
    \"\"\",  ## In VERBOSE mode whitespace and # comments inside the pattern are ignored
    re.VERBOSE | re.MULTILINE,  ## MULTILINE: ^ matches at the start of every line
)


def to_seconds(ts: str) -> float:  ## "10:00:01.130" -> seconds since midnight
    h, m, s = ts.split(":")  ## Split into hours, minutes, seconds.millis
    return int(h) * 3600 + int(m) * 60 + float(s)  ## Combine into one number


def main() -> None:
    msgs = {int(m["msg"]): to_seconds(m["ts"]) for m in EAPOL.finditer(LOG)}  ## Message number -> timestamp
    print(sorted(msgs))  ## All four handshake messages were found
    print(f"4-way handshake: {(msgs[4] - msgs[1]) * 1000:.0f} ms")  ## Message 1 to message 4
    line = LOG.splitlines()[-1]  ## The disconnect line
    print(re.search(r"bssid=(.*) ", line).group(1))  ## Greedy .* runs to the LAST space it can find
    print(re.search(r"bssid=(.*?) ", line).group(1))  ## Lazy .*? stops at the FIRST space
    print(re.search(r"bssid=(\\S+)", line).group(1))  ## Clearer: one or more non-space characters
    fields = dict(re.findall(r"(\\w+)=(\\S+)", line))  ## Two groups: findall returns (key, value) tuples
    print(fields, int(fields["reason"]))  ## Reason 15 is a 4-way handshake timeout
    print(len(re.findall(r"^\\d", LOG, re.MULTILINE)), len(re.findall(r"^\\d", LOG)))  ## With MULTILINE, ^ matches 6 line starts; without it, only 1


if __name__ == "__main__":
    main()""",
            "under": "Greedy quantifiers try the longest match first and back off one character at a time until the rest of the pattern fits; lazy ones try the shortest first and extend. Patterns with nested quantifiers such as `(\\w+\\s?)+$` can backtrack exponentially on a line that almost matches (\"catastrophic backtracking\"), which looks like a hung test. Specific character classes avoid that and are faster.",
            "gotchas": [
                {
                    "title": "Greedy capture swallows the rest of the line",
                    "note": "`.*` is greedy, so the capture runs up to the last possible separator.",
                    "wrong": """import re
line = "assoc sta=aa:01 ap=ap-2 rssi=-58"
print(re.search(r"sta=(.*) ", line).group(1))""",
                    "fixed": """import re
line = "assoc sta=aa:01 ap=ap-2 rssi=-58"
print(re.search(r"sta=(\\S+)", line).group(1))""",
                }
            ],
            "best": "Write long patterns in VERBOSE mode with a comment per part, prefer `\\S+`, `\\d+` and `[^,]+` to `.*`, and test every pattern against real samples from each firmware version you support (pytest parametrize, Module 5.5).",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Extract every channel number from `\"scan: ch36 -54dBm, ch149 -61dBm, ch1 -70dBm\"` as ints.",
            "solution": "One group after the literal `ch`.",
            "solution_code": """import re
text = "scan: ch36 -54dBm, ch149 -61dBm, ch1 -70dBm"
print([int(c) for c in re.findall(r"ch(\\d+)", text)])""",
        },
        {
            "level": "Medium",
            "prompt": "Write a compiled pattern that validates MAC addresses in colon format (case-insensitive) and test it on four inputs, including one with a dash and one that's too short.",
            "solution": "fullmatch with a repeated group and IGNORECASE.",
            "solution_code": """import re
MAC = re.compile(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", re.IGNORECASE)
for s in ["aa:bb:cc:00:11:22", "AA:BB:CC:00:11:22", "aa-bb-cc-00-11-22", "aa:bb:cc:00:11"]:
    print(s, bool(MAC.fullmatch(s)))""",
        },
        {
            "level": "Hard",
            "prompt": "From the log below, count disconnect reasons and report each reason with how many times it occurred, most common first.",
            "code": """log = \"\"\"CTRL-EVENT-DISCONNECTED bssid=ap-1 reason=15
CTRL-EVENT-CONNECTED bssid=ap-2
CTRL-EVENT-DISCONNECTED bssid=ap-2 reason=3 locally_generated=1
CTRL-EVENT-DISCONNECTED bssid=ap-1 reason=15\"\"\"""",
            "solution": "findall with one group gives the reasons; a dict counts them, and sorted orders them.",
            "solution_code": """import re
log = \"\"\"CTRL-EVENT-DISCONNECTED bssid=ap-1 reason=15
CTRL-EVENT-CONNECTED bssid=ap-2
CTRL-EVENT-DISCONNECTED bssid=ap-2 reason=3 locally_generated=1
CTRL-EVENT-DISCONNECTED bssid=ap-1 reason=15\"\"\"
counts = {}
for reason in re.findall(r"DISCONNECTED.*?reason=(\\d+)", log):
    counts[reason] = counts.get(reason, 0) + 1
for reason, n in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
    print(f"reason {reason}: {n}")""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What's the difference between re.match, re.search and re.fullmatch?", "a": "match only matches at the start of the string, search finds the first match anywhere, and fullmatch requires the whole string to match. Use fullmatch for validation and search for extraction.", "follow": "What do they return on failure? (None, so always check before calling .group().)"},
        {"level": "Beginner", "q": "Why use raw strings for regex patterns?", "a": "Backslashes are interpreted by Python string literals first: `\"\\b\"` becomes a backspace and `\"\\d\"` triggers a SyntaxWarning in 3.12. A raw string passes the backslashes through to the regex engine unchanged.", "follow": "Does r'' change the string's type? (No, it's still a normal str.)"},
        {"level": "Intermediate", "q": "Explain greedy vs lazy quantifiers with an example.", "a": "Greedy (`.*`, `+`) matches as much as possible, lazy (`.*?`, `+?`) as little as possible. On `bssid=ap-1 reason=15 x`, `bssid=(.*) ` captures `ap-1 reason=15`, while `bssid=(.*?) ` captures `ap-1`. A specific class like `\\S+` is usually better than either.", "follow": "What is catastrophic backtracking? (Nested quantifiers that make the engine try exponentially many paths on near-matches.)"},
        {"level": "Intermediate", "q": "What does findall return when the pattern has groups?", "a": "With no groups: a list of whole-match strings. With one group: a list of that group's strings. With several groups: a list of tuples. Use finditer when you need match objects, positions or named groups.", "follow": "How do you group without capturing? (`(?:...)`.)"},
        {"level": "Advanced", "q": "When should you not use regex for parsing?", "a": "When the format is structured (JSON, XML, CSV) use a real parser; when a simple split or startswith works, use string methods; when output is tabular and vendor-specific, a template parser (TextFSM/TTP, Module 7.9) is easier to maintain. Regex is best for semi-structured lines.", "follow": "How do you keep regex parsers from breaking on new firmware? (Parametrized tests with real captured outputs per version.)"},
    ],
    "quiz": [
        {"q": "`re.findall(r'(\\d+)=(\\w+)', '1=a 2=b')` returns?", "options": ["['1=a', '2=b']", "[('1', 'a'), ('2', 'b')]", "['1', '2']", "{'1': 'a'}"], "answer": 1, "why": "Several groups give tuples."},
        {"q": "Which matches as little as possible?", "options": [".*", ".+", ".*?", "\\S+"], "answer": 2, "why": "The ? after a quantifier makes it lazy."},
        {"q": "What does re.MULTILINE change?", "options": [". matches newlines", "^ and $ match at each line", "Case is ignored", "Whitespace is ignored"], "answer": 1, "why": "MULTILINE affects the anchors; DOTALL affects '.'."},
        {"q": "How do you name a group?", "options": ["(name:...)", "(?P<name>...)", "{name}", "(?:name)"], "answer": 1, "why": "Python's named-group syntax."},
        {"q": "`re.match(r'b', 'abc')` returns?", "options": ["A match", "None", "'b'", "Error"], "answer": 1, "why": "match is anchored at position 0."},
    ],
    "cards": [
        {"front": "match / search / fullmatch", "back": "Start only / anywhere / whole string"},
        {"front": "Named group", "back": "`(?P<name>...)`, read with `m['name']`"},
        {"front": "Non-capturing group", "back": "`(?:...)`"},
        {"front": "Greedy vs lazy", "back": "`.*` as much as possible; `.*?` as little as possible"},
        {"front": "Why raw strings", "back": "So backslashes reach the regex engine unchanged."},
        {"front": "re.VERBOSE", "back": "Allows whitespace and # comments inside the pattern."},
    ],
}


M_2_9 = {
    "id": "2.9",
    "title": "datetime & zoneinfo",
    "hours": 1.5,
    "summary": "Dates, times and durations, aware vs naive datetimes, parsing and formatting, converting between time zones, and the right clock for measuring elapsed time.",
    "concepts": [
        {
            "title": "datetime, timedelta and time zones",
            "concept": "`datetime` holds a date and a time; `timedelta` is a duration. A datetime is **aware** when it carries a `tzinfo` (an offset from UTC) and **naive** when it doesn't. Only aware datetimes can be safely compared across hosts. `astimezone()` converts between zones; `isoformat()` / `fromisoformat()` write and read ISO 8601 text; `strftime()` / `strptime()` format and parse custom layouts. Fixed offsets come from `datetime.timezone`; real, DST-aware zones come from `zoneinfo.ZoneInfo`.",
            "why": "A nightly run starts at 21:30 IST on a Pune agent, the AP logs in UTC, and a remote bench logs in CET. Converting everything to aware UTC datetimes is what makes timelines and durations correct.",
            "syntax": "from datetime import datetime, timedelta, timezone\nfrom zoneinfo import ZoneInfo\n\ndatetime(2026, 10, 12, 21, 30, tzinfo=ZoneInfo(\"Asia/Kolkata\"))\ndt.astimezone(timezone.utc)\ndt + timedelta(hours=7)\ndatetime.fromisoformat(\"2026-10-12T16:00:05+00:00\")\ndt.strftime(\"%Y-%m-%d %H:%M %Z\")",
            "code": """from datetime import datetime, timedelta, timezone  ## The main types, plus fixed-offset time zones

IST = timezone(timedelta(hours=5, minutes=30), "IST")  ## India has no daylight saving, so a fixed +05:30 offset is exact


def main() -> None:
    start = datetime(2026, 10, 12, 21, 30, tzinfo=IST)  ## An aware datetime: nightly run start in Pune
    print(start.isoformat())  ## ISO 8601 text, including the offset
    utc = start.astimezone(timezone.utc)  ## The same instant expressed in UTC
    print(utc.isoformat(), utc.tzname())  ## 16:00 UTC
    end = start + timedelta(hours=7, minutes=45)  ## Add a duration
    print(end.strftime("%Y-%m-%d %H:%M %Z"), end - start)  ## Format with codes; subtracting datetimes gives a timedelta
    parsed = datetime.strptime("2026-10-12 21:30:05", "%Y-%m-%d %H:%M:%S")  ## Parse a custom layout: the result is NAIVE
    print(parsed.tzinfo, parsed.replace(tzinfo=IST) == start + timedelta(seconds=5))  ## Attach the known zone with replace()
    stamp = datetime.fromisoformat("2026-10-12T16:00:05+00:00")  ## Parse ISO text that includes an offset: AWARE
    print(stamp.astimezone(IST).time(), (stamp - utc).total_seconds())  ## Convert for display; differences work across zones
    print(f"{start:%d %b %Y, %H:%M}")  ## strftime codes work inside f-strings too


if __name__ == "__main__":
    main()""",
            "under": "An aware datetime stores local wall-clock fields plus a tzinfo object; comparisons and subtraction convert both sides to UTC first, so the zones don't need to match. A naive datetime has no idea what instant it represents, which is why Python refuses to subtract a naive one from an aware one. `ZoneInfo` reads the IANA time zone database (from the OS or the `tzdata` package) and knows each zone's historical and future DST rules.",
            "gotchas": [
                {
                    "title": "A fixed offset is not a time zone",
                    "note": "Germany is UTC+1 in winter but UTC+2 in summer. A hard-coded +01:00 is an hour off for half the year; `ZoneInfo` knows the rules. (This one needs the time zone database, so run it on your machine.)",
                    "local_only": "needs the IANA time zone database, which the in-browser runner doesn't include",
                    "wrong": """from datetime import datetime, timedelta, timezone
CET = timezone(timedelta(hours=1))
print(datetime(2026, 7, 1, 12, 0, tzinfo=CET).isoformat())""",
                    "fixed": """from datetime import datetime
from zoneinfo import ZoneInfo
print(datetime(2026, 7, 1, 12, 0, tzinfo=ZoneInfo("Europe/Berlin")).isoformat())""",
                },
                {
                    "title": "datetime.now() is naive",
                    "note": "Without an argument, now() returns local wall-clock time with no zone. Log timestamps should be aware, normally in UTC.",
                    "wrong": """from datetime import datetime
print(datetime.now().tzinfo)""",
                    "fixed": """from datetime import datetime, timezone
print(datetime.now(timezone.utc).tzinfo)""",
                },
            ],
            "best": "Store and compare times as aware UTC datetimes, convert to local zones only for display, write timestamps as ISO 8601 with an offset, and use `ZoneInfo(\"Area/City\")` for any zone with daylight saving.",
        },
        {
            "title": "Durations across hosts and the right clock",
            "concept": "Subtracting two aware datetimes gives a `timedelta`, even when they came from hosts in different time zones; `.total_seconds()` turns it into a number. For measuring how long **your own code** takes, don't use wall-clock time at all: `time.monotonic()` and `time.perf_counter()` only move forwards and aren't affected by NTP or manual clock changes. `perf_counter()` has the highest resolution.",
            "why": "Roam latency is the gap between the last frame through the old AP (logged in UTC) and the first frame through the new one (logged by the STA in IST). Timeouts and step durations inside the framework belong to the monotonic clock.",
            "syntax": "gap = datetime.fromisoformat(b) - datetime.fromisoformat(a)\ngap.total_seconds() * 1000      # ms\n\nt0 = time.perf_counter()\n...\nelapsed = time.perf_counter() - t0",
            "code": """import time  ## perf_counter() for measuring code
from datetime import datetime  ## Parsing log timestamps

AP_LOG = "2026-10-12T16:00:09.412+00:00 ap-1 last data frame from aa:01"  ## The old AP logs in UTC
STA_LOG = "2026-10-12T21:30:09.455+05:30 sta aa:01 first data frame via ap-2"  ## The station logs in IST


def ts(line: str) -> datetime:  ## Pull the timestamp from the start of a log line
    return datetime.fromisoformat(line.split()[0])  ## The first token is ISO 8601 with an offset, so the result is aware


def main() -> None:
    last_old = ts(AP_LOG)  ## 16:00:09.412 UTC
    first_new = ts(STA_LOG)  ## 21:30:09.455 IST, which is 16:00:09.455 UTC
    gap = first_new - last_old  ## Python converts both to UTC before subtracting
    print(gap, round(gap.total_seconds() * 1000), "ms")  ## A 43 ms data-path interruption during the roam
    naive = datetime.fromisoformat("2026-10-12T21:30:09.455")  ## The same text without an offset
    try:  ## Mixing naive and aware datetimes is refused
        naive - last_old  ## Which instant would `naive` be? Python won't guess
    except TypeError as err:  ## So it raises
        print("TypeError:", err)  ## Explains the mix-up
    t0 = time.perf_counter()  ## Start a high-resolution, monotonic timer
    sum(range(100_000))  ## Some work to measure
    elapsed = time.perf_counter() - t0  ## Seconds as a float
    print(elapsed > 0, type(elapsed).__name__)  ## Always positive; the exact value varies per run, so we don't print it


if __name__ == "__main__":
    main()""",
            "under": "`time.time()` returns wall-clock seconds since the Unix epoch and can jump when NTP corrects the clock, so a duration measured with it can be wrong or negative. `monotonic()` and `perf_counter()` count from an arbitrary starting point and never go backwards; their absolute value is meaningless, only differences are useful. `timedelta` stores days, seconds and microseconds, so it can represent the 43 ms gap exactly.",
            "gotchas": [
                {
                    "title": "Timing code with time.time()",
                    "note": "It usually works, until a clock correction lands mid-measurement. perf_counter is designed for this, and has better resolution.",
                    "wrong": """import time
t0 = time.time()
total = sum(range(10_000))
print(time.time() - t0 >= 0)""",
                    "fixed": """import time
t0 = time.perf_counter()
total = sum(range(10_000))
print(time.perf_counter() - t0 > 0)""",
                }
            ],
            "best": "Measure durations of your own steps with `perf_counter()` (or `monotonic()` for deadlines, Module 1.6). Compute cross-host latencies from aware log timestamps, and make sure the devices are NTP-synchronised before trusting sub-100 ms results.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "A soak test started at 2026-10-12 21:30 IST and must run 14 hours. Print the finish time in IST and in UTC.",
            "solution": "Add a timedelta to an aware datetime, then convert.",
            "solution_code": """from datetime import datetime, timedelta, timezone
IST = timezone(timedelta(hours=5, minutes=30), "IST")
start = datetime(2026, 10, 12, 21, 30, tzinfo=IST)
end = start + timedelta(hours=14)
print(end.isoformat(), end.astimezone(timezone.utc).isoformat())""",
        },
        {
            "level": "Medium",
            "prompt": "Parse `\"12/10/2026 09:15:30\"` (day/month/year) as IST and print it as ISO 8601 in UTC.",
            "solution": "strptime with the right codes, then replace the tzinfo and convert.",
            "solution_code": """from datetime import datetime, timedelta, timezone
IST = timezone(timedelta(hours=5, minutes=30))
dt = datetime.strptime("12/10/2026 09:15:30", "%d/%m/%Y %H:%M:%S").replace(tzinfo=IST)
print(dt.astimezone(timezone.utc).isoformat())""",
        },
        {
            "level": "Hard",
            "prompt": "Given event timestamps in mixed offsets, sort them into one timeline and print each with the gap from the previous event in ms.",
            "solution": "Parse all as aware datetimes, sort, then compute pairwise differences.",
            "solution_code": """from datetime import datetime
events = [
    ("2026-10-12T21:30:09.455+05:30", "sta: first frame via ap-2"),
    ("2026-10-12T16:00:09.200+00:00", "ap-1: BSS transition request sent"),
    ("2026-10-12T16:00:09.412+00:00", "ap-1: last frame from sta"),
    ("2026-10-12T18:00:09.430+02:00", "ap-2: reassociation accepted"),
]
timeline = sorted((datetime.fromisoformat(t), what) for t, what in events)
prev = None
for when, what in timeline:
    gap = "" if prev is None else f"+{(when - prev).total_seconds() * 1000:.0f} ms"
    print(f"{when.isoformat(timespec='milliseconds')}  {what:<34} {gap}")
    prev = when""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What is the difference between a naive and an aware datetime?", "a": "An aware datetime has a tzinfo, so it represents an exact instant; a naive one has none and is ambiguous. You can't compare or subtract a naive and an aware datetime (TypeError).", "follow": "How do you make one aware? (`dt.replace(tzinfo=...)` when you know the zone, or `astimezone()` to convert.)"},
        {"level": "Intermediate", "q": "Why use time.monotonic() or perf_counter() instead of time.time() for durations?", "a": "time.time() follows the wall clock, which can jump when NTP adjusts it, giving wrong or negative durations. monotonic and perf_counter never go backwards; perf_counter has the best resolution.", "follow": "Can you convert a monotonic value to a date? (No, its zero point is arbitrary.)"},
        {"level": "Intermediate", "q": "Why is timezone(timedelta(hours=1)) wrong for Berlin?", "a": "It's a fixed offset with no daylight-saving rules, so it is an hour off in summer. `ZoneInfo('Europe/Berlin')` uses the IANA database and switches between +01:00 and +02:00 correctly.", "follow": "Where does zoneinfo get its data? (The OS tz database, or the tzdata package on Windows and minimal containers.)"},
        {"level": "Advanced", "q": "How would you measure roaming latency from AP and STA logs?", "a": "Parse each log's timestamps as aware datetimes (or convert them to UTC), find the last frame through the old AP and the first through the new one, and subtract. Verify NTP sync between devices first; for sub-millisecond accuracy, use a single over-the-air capture instead of several clocks.", "follow": "Why might the result be negative? (Unsynchronised clocks between the devices.)"},
    ],
    "quiz": [
        {"q": "`datetime.now()` returns...", "options": ["An aware UTC time", "A naive local time", "A timedelta", "Seconds since epoch"], "answer": 1, "why": "Pass a tz to get an aware value."},
        {"q": "What does subtracting two datetimes give?", "options": ["int", "float", "timedelta", "datetime"], "answer": 2, "why": "A duration object."},
        {"q": "Best clock for timing code?", "options": ["time.time()", "datetime.now()", "time.perf_counter()", "time.ctime()"], "answer": 2, "why": "Monotonic and high resolution."},
        {"q": "`datetime.fromisoformat('2026-10-12T16:00:00+00:00')` is...", "options": ["Naive", "Aware", "A date", "Invalid"], "answer": 1, "why": "The offset in the text makes it aware."},
        {"q": "Which handles daylight saving correctly?", "options": ["timezone(timedelta(hours=1))", "ZoneInfo('Europe/Berlin')", "Both", "Neither"], "answer": 1, "why": "Only zoneinfo knows the DST rules."},
    ],
    "cards": [
        {"front": "Naive vs aware", "back": "No tzinfo (ambiguous) vs tzinfo (an exact instant)."},
        {"front": "Convert to UTC", "back": "`dt.astimezone(timezone.utc)`"},
        {"front": "Parse ISO 8601", "back": "`datetime.fromisoformat(s)`"},
        {"front": "Real time zone with DST", "back": "`ZoneInfo('Europe/Berlin')`"},
        {"front": "Timing your own code", "back": "`time.perf_counter()` differences"},
    ],
}
