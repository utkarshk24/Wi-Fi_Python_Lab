"""Phase 2 content: modules 2.4-2.6."""

M_2_4 = {
    "id": "2.4",
    "title": "Comprehensions",
    "hours": 2.5,
    "summary": "List, dict and set comprehensions with conditions, nested comprehensions for test matrices, and generator expressions for memory-light pipelines.",
    "concepts": [
        {
            "title": "List, dict and set comprehensions",
            "concept": "A comprehension builds a collection from an iterable in one expression: `[expr for item in iterable if condition]`. Swap the brackets for `{k: v for ...}` to build a dict or `{expr for ...}` for a set. A trailing `if` **filters** items; a conditional expression in the output (`a if cond else b`) **chooses** a value for every item. Several `for` clauses nest left to right, like nested loops.",
            "why": "Selecting 6 GHz stations, building a MAC-to-RSSI table and expanding a band × width test matrix are each one readable line instead of a four-line loop with an empty list and append.",
            "syntax": "[f(x) for x in xs if keep(x)]        # list\n{k: v for k, v in pairs}             # dict\n{x.band for x in stas}               # set\n[a if c else b for x in xs]          # choose per item\n[(b, w) for b in bands for w in widths]  # nested",
            "code": """def main() -> None:
    stations = [  ## Parsed station records
        {"mac": "aa:01", "band": "6G", "rssi": -52},  ## Strong 6 GHz client
        {"mac": "aa:02", "band": "5G", "rssi": -71},  ## Weak 5 GHz client
        {"mac": "aa:03", "band": "6G", "rssi": -66},  ## Weak 6 GHz client
        {"mac": "aa:04", "band": "2G", "rssi": -45},  ## Strong 2.4 GHz client
    ]
    macs_6g = [s["mac"] for s in stations if s["band"] == "6G"]  ## Filter with a trailing if, keep only the MAC
    print(macs_6g)  ## Two 6 GHz clients
    rssi_by_mac = {s["mac"]: s["rssi"] for s in stations}  ## Dict comprehension: key: value pairs
    print(rssi_by_mac)  ## Fast lookup table by MAC
    bands = {s["band"] for s in stations}  ## Set comprehension: duplicates collapse
    print(sorted(bands))  ## Sorted for stable output
    labels = ["weak" if s["rssi"] < -65 else "ok" for s in stations]  ## Conditional expression: one label for EVERY item
    print(labels)  ## Same length as the input
    widths = {"5G": [80, 160], "6G": [160, 320]}  ## Allowed channel widths per band under test
    matrix = [(band, w) for band, ws in widths.items() for w in ws]  ## Two for clauses: outer loop first, inner loop second
    print(matrix)  ## Every (band, width) test case


if __name__ == "__main__":
    main()""",
            "under": "A comprehension runs in its **own scope** (since Python 3), so its loop variable doesn't leak into the surrounding function. CPython 3.12 inlines list, dict and set comprehensions into the enclosing function for speed, but keeps that isolation. A list comprehension is typically somewhat faster than the equivalent loop with `append`, because the append happens through a dedicated bytecode instead of a method lookup each time.",
            "gotchas": [
                {
                    "title": "Using a comprehension for side effects",
                    "note": "This builds a throwaway list of None values just to call print. Use a plain loop when you want an action, not a collection.",
                    "wrong": """channels = [36, 40, 44]
result = [print(f"testing ch{c}") for c in channels]
print(result)""",
                    "fixed": """channels = [36, 40, 44]
for c in channels:
    print(f"testing ch{c}")""",
                },
                {
                    "title": "if/else in the wrong place",
                    "note": "A filter goes after the for; a value choice goes before it. `[x for x in xs if c else y]` is a SyntaxError.",
                    "wrong": """rssi = [-52, -71, -45]
print([r for r in rssi if r > -60])""",
                    "fixed": """rssi = [-52, -71, -45]
print([r for r in rssi if r > -60], [r if r > -60 else None for r in rssi])""",
                },
            ],
            "best": "Use a comprehension when you are building a collection and the logic fits on one or two lines. If you need more than two `for` clauses or any nested condition, write a loop or a helper function. Name the result for what it holds (`macs_6g`, not `lst`).",
        },
        {
            "title": "Generator expressions",
            "concept": "Writing a comprehension with parentheses, `(expr for x in xs)`, creates a **generator expression**: a lazy iterator that yields one value at a time instead of building a list. It uses constant memory no matter how many items it processes. Functions that consume an iterable (`sum`, `max`, `any`, `all`, `\"\".join`) accept one directly: `sum(x for x in xs)`. Like `map`, a generator can be consumed only once.",
            "why": "A 6-hour soak test can produce millions of log lines. Summing bytes or finding the minimum RSSI with a generator expression processes them one at a time instead of loading everything into memory.",
            "syntax": "(f(x) for x in xs if keep(x))   # lazy\nsum(x * 2 for x in xs)           # parentheses of the call are enough\nany(r < -80 for r in rssi)       # stops at the first True",
            "code": """import sys  ## getsizeof() reports an object's own memory footprint


def main() -> None:
    samples = range(1_000_000)  ## A million sample indices (range itself is lazy)
    as_list = [s * 2 for s in samples]  ## Builds all one million results now
    as_gen = (s * 2 for s in samples)  ## Builds nothing yet: just a generator object
    print(sys.getsizeof(as_list) > 1_000_000, sys.getsizeof(as_gen) < 500)  ## The list needs megabytes; the generator a few hundred bytes
    print(sum(s * 2 for s in samples))  ## Consumed one value at a time by sum()
    lines = ["RSSI=-54", "noise", "RSSI=-61", "RSSI=-49"]  ## A few log lines, one of them irrelevant
    values = (int(ln.split("=")[1]) for ln in lines if ln.startswith("RSSI="))  ## Filter and convert lazily
    print(max(values))  ## max() pulls every value from the generator
    print(list(values))  ## Already exhausted, so this is empty
    print(any(int(ln.split("=")[1]) < -60 for ln in lines if "=" in ln))  ## any() stops as soon as it finds a True


if __name__ == "__main__":
    main()""",
            "under": "A generator expression compiles to a hidden generator function. Each `next()` resumes it, runs until it produces the next value, and suspends again with its local state intact. `sys.getsizeof` of the list grows with the number of items (about 8 bytes per pointer, plus the int objects themselves), while the generator stays the same size. Generators are covered in depth in Module 3.7.",
            "gotchas": [
                {
                    "title": "Iterating a generator twice",
                    "note": "The first consumer drains it; later ones see nothing, with no error.",
                    "wrong": """mbps = (float(x) for x in ["910.2", "905.7", "899.1"])
print(max(mbps), min(mbps, default="nothing left"))""",
                    "fixed": """mbps = [float(x) for x in ["910.2", "905.7", "899.1"]]
print(max(mbps), min(mbps))""",
                }
            ],
            "best": "Pass a generator expression straight into `sum`, `max`, `any`, `all` or `join` when you need the values once. Build a list when you need them twice, need `len()`, or need indexing.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Build a list of the 20 MHz channels 36 to 64 inclusive (step 4) that are DFS channels (52 and above) using a comprehension.",
            "solution": "range() for the channels and a trailing if for the DFS condition.",
            "solution_code": """dfs = [ch for ch in range(36, 65, 4) if ch >= 52]
print(dfs)""",
        },
        {
            "level": "Medium",
            "prompt": "Invert `{'aa:01': 'ap-1', 'aa:02': 'ap-2', 'aa:03': 'ap-1'}` into `{ap: sorted list of MACs}` using a dict comprehension over the set of APs.",
            "solution": "Comprehend over the unique values and filter the original items for each one.",
            "solution_code": """assoc = {"aa:01": "ap-1", "aa:02": "ap-2", "aa:03": "ap-1"}
by_ap = {ap: sorted(m for m, a in assoc.items() if a == ap) for ap in set(assoc.values())}
print(dict(sorted(by_ap.items())))""",
        },
        {
            "level": "Hard",
            "prompt": "Generate every test case for bands {5G: [80, 160], 6G: [160, 320]} × security [WPA2, WPA3] as dicts, skipping WPA2 on 6G (6 GHz requires WPA3 or OWE). Print the count and the first two.",
            "solution": "Three for clauses and one filter, producing dicts.",
            "solution_code": """widths = {"5G": [80, 160], "6G": [160, 320]}
cases = [
    {"band": b, "width": w, "security": sec}
    for b, ws in widths.items()
    for w in ws
    for sec in ["WPA2", "WPA3"]
    if not (b == "6G" and sec == "WPA2")
]
print(len(cases), cases[:2])""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What is the difference between a list comprehension and a generator expression?", "a": "Square brackets build the whole list immediately. Parentheses create a lazy generator that yields items one at a time, uses constant memory and can be iterated only once.", "follow": "When must you use a list? (When you need len(), indexing or more than one pass.)"},
        {"level": "Intermediate", "q": "Where does the if go in a comprehension?", "a": "A trailing `if` after the for filters items. A conditional expression before the for (`a if cond else b for x in xs`) chooses a value for every item and keeps the length the same.", "follow": "Can you have both? (Yes: `[a if c else b for x in xs if keep(x)]`.)"},
        {"level": "Intermediate", "q": "Does a comprehension's loop variable leak into the enclosing scope?", "a": "No, not in Python 3. Comprehensions have their own scope. (In Python 2, list comprehensions did leak.)", "follow": "Does the walrus operator inside a comprehension leak? (Yes: `:=` binds in the enclosing scope by design.)"},
        {"level": "Advanced", "q": "Why is sum(x for x in xs) often better than sum([x for x in xs])?", "a": "The generator version never materialises the full list, so memory stays constant. For very large inputs that avoids a big temporary allocation. For small inputs the list version can be marginally faster, so readability decides.", "follow": "How does any() benefit? (It short-circuits on the first True and never evaluates the rest.)"},
    ],
    "quiz": [
        {"q": "What does `{x % 3 for x in range(6)}` produce?", "options": ["[0, 1, 2, 0, 1, 2]", "{0, 1, 2}", "{0: 0, 1: 1}", "(0, 1, 2)"], "answer": 1, "why": "A set comprehension removes duplicates."},
        {"q": "Which is a generator expression?", "options": ["[x for x in xs]", "(x for x in xs)", "{x for x in xs}", "{x: x for x in xs}"], "answer": 1, "why": "Parentheses create a generator."},
        {"q": "Order of `[(a, b) for a in 'xy' for b in '12']`?", "options": ["x1 x2 y1 y2", "x1 y1 x2 y2", "1x 2x 1y 2y", "Error"], "answer": 0, "why": "The first for is the outer loop."},
        {"q": "`[r if r > 0 else 0 for r in [-1, 2]]` gives?", "options": ["[2]", "[0, 2]", "[-1, 2]", "SyntaxError"], "answer": 1, "why": "The conditional expression picks a value for each item."},
        {"q": "Why avoid `[print(x) for x in xs]`?", "options": ["It doesn't print", "It builds a useless list of None", "It's a SyntaxError", "It prints twice"], "answer": 1, "why": "Use a loop for side effects."},
    ],
    "cards": [
        {"front": "Filter vs choose in a comprehension", "back": "`[x for x in xs if c]` filters; `[a if c else b for x in xs]` chooses."},
        {"front": "Dict comprehension", "back": "`{k: v for k, v in pairs}`"},
        {"front": "Generator expression", "back": "`(expr for x in xs)`: lazy, single-use, constant memory."},
        {"front": "Nested for clause order", "back": "Left to right = outer to inner loop."},
    ],
}


M_2_5 = {
    "id": "2.5",
    "title": "Exceptions",
    "hours": 3,
    "summary": "try/except/else/finally, catching the right exceptions, custom exception hierarchies, chaining with raise from, guaranteed cleanup and ExceptionGroup.",
    "concepts": [
        {
            "title": "try, except, else, finally",
            "concept": "Code in `try` runs until an exception is raised. The first matching `except` clause handles it; exceptions match their own class **and every subclass**. `else` runs only if `try` raised nothing, which keeps the protected region small. `finally` **always** runs, whether the block succeeded, failed or returned. `raise` signals an error; a bare `raise` inside `except` re-raises the current one.",
            "why": "Parsing unreliable tool output, talking to devices that time out and validating configs all raise exceptions. Catching the right ones, and only those, decides whether a failure is reported clearly or hidden.",
            "syntax": "try:\n    risky()\nexcept (KeyError, IndexError) as err:\n    handle(err)\nexcept ValueError:\n    raise            # re-raise\nelse:\n    on_success()\nfinally:\n    cleanup()        # always runs",
            "code": """def parse_rssi(token: str) -> int:  ## Parse and validate one RSSI value
    value = int(token)  ## int() raises ValueError for text like "abc"
    if not -100 <= value <= 0:  ## A positive RSSI can't be right
        raise ValueError(f"RSSI out of range: {value}")  ## Raise our own ValueError with a clear message
    return value  ## Only reached for valid input


def main() -> None:
    for token in ["-54", "abc", "12"]:  ## One valid, one non-numeric, one out of range
        try:  ## Keep only the risky call inside try
            value = parse_rssi(token)  ## May raise ValueError
        except ValueError as err:  ## Handles both int() failures and our range check
            print(f"{token!r}: rejected ({err})")  ## The exception message explains why
        else:  ## Runs only when try raised nothing
            print(f"{token!r}: ok {value}")  ## Success path, outside the try block
        finally:  ## Runs in every case
            print("  checked", token)  ## Typical use: cleanup or logging
    print(issubclass(KeyError, LookupError), issubclass(LookupError, Exception))  ## Part of the built-in hierarchy
    try:  ## A failing dict lookup
        {"5G": 36}["6G"]  ## No 6G key
    except (KeyError, IndexError) as err:  ## A tuple catches any of several types
        print(type(err).__name__, err)  ## KeyError '6G'


if __name__ == "__main__":
    main()""",
            "under": "When an exception is raised, Python unwinds the call stack frame by frame looking for a matching `except`. `except Cls` uses `isinstance`, so catching `LookupError` also catches `KeyError` and `IndexError`. Entering a `try` block is almost free since Python 3.11 (\"zero-cost\" exceptions); raising and catching is relatively expensive, so don't use exceptions for normal control flow in tight loops.",
            "gotchas": [
                {
                    "title": "A bare except hides real bugs",
                    "note": "`except:` catches everything, including the TypeError from passing None, and even KeyboardInterrupt. The function silently returns a default for input that should have been an error.",
                    "wrong": """def read_channel(cfg):
    try:
        return cfg["channel"]
    except:
        return 36

print(read_channel(None))""",
                    "fixed": """def read_channel(cfg):
    try:
        return cfg["channel"]
    except KeyError:
        return 36

print(read_channel({}))
try:
    read_channel(None)
except TypeError as err:
    print("TypeError:", err)""",
                },
                {
                    "title": "Too much code inside try",
                    "note": "When the whole function sits in try, an unrelated KeyError further down gets reported as a parse failure. Keep try narrow and put the follow-up work in else.",
                    "wrong": """record = {"rssi": "-54"}
try:
    rssi = int(record["rssi"])
    snr = rssi - record["noise"]
except (ValueError, KeyError):
    print("bad RSSI value")""",
                    "fixed": """record = {"rssi": "-54"}
try:
    rssi = int(record["rssi"])
except (ValueError, KeyError):
    print("bad RSSI value")
else:
    noise = record.get("noise")
    print("snr unknown: no noise floor" if noise is None else rssi - noise)""",
                },
            ],
            "best": "Catch the most specific exception you can handle, keep `try` blocks to the lines that can raise it, and put success-only code in `else`. Never use a bare `except:`; if you must catch broadly at a top level, use `except Exception` and log the traceback.",
        },
        {
            "title": "Custom exceptions, raise from, cleanup and ExceptionGroup",
            "concept": "Define a **base exception** for your framework and subclass it for specific failures, so callers can catch everything from your code with one clause or a single failure precisely. `raise NewError(...) from err` chains the original cause onto the new exception (`__cause__`), keeping the low-level detail. `finally` guarantees that lab state is restored. `ExceptionGroup` (3.11+) bundles several independent failures, and `except*` handles each type inside the group.",
            "why": "A bench health check that fails on three devices should report all three, not just the first. An attenuator left at 40 dB after a crash ruins every later test; `finally` puts it back.",
            "syntax": "class LabError(Exception): ...\nclass DUTUnreachableError(LabError): ...\n\nraise DUTUnreachableError(host) from err\n\ntry:\n    ...\nexcept* LabError as group:\n    group.exceptions   # tuple of matching errors",
            "code": """class LabError(Exception):  ## Base class for every error our framework raises
    \"\"\"Base class for every error raised by the lab framework.\"\"\"  ## Docstring is enough of a body


class DUTUnreachableError(LabError):  ## A specific, catchable failure
    def __init__(self, host: str, attempts: int) -> None:  ## preview: classes are taught in Module 3.1
        super().__init__(f"{host} unreachable after {attempts} attempts")  ## The message str(err) will show
        self.host = host  ## Extra attributes give handlers structured data
        self.attempts = attempts  ## e.g. for a retry report


class FakeAttenuator:  ## Stands in for a programmable attenuator
    def __init__(self) -> None:  ## Starts at 0 dB
        self.db = 0  ## Current attenuation

    def set(self, db: int) -> None:  ## Change the attenuation
        self.db = db  ## A real driver would send a command here


def connect(host: str) -> None:  ## Simulates a device connection that times out
    try:  ## The low-level operation
        raise TimeoutError("ssh timed out")  ## What the SSH library would raise
    except TimeoutError as err:  ## Translate the low-level error...
        raise DUTUnreachableError(host, attempts=3) from err  ## ...into our domain error, keeping the cause


def run_step(att: FakeAttenuator) -> None:  ## A test step that must always restore the attenuator
    original = att.db  ## Remember the starting state
    try:  ## The part that can fail
        att.set(40)  ## Change lab state
        connect("10.0.0.5")  ## Fails with DUTUnreachableError
    finally:  ## Runs even though an exception is propagating
        att.set(original)  ## Restore state, then the exception continues upward


def main() -> None:
    att = FakeAttenuator()  ## Fresh lab state
    try:  ## Catch at the level that can report it
        run_step(att)  ## Raises after restoring the attenuator
    except LabError as err:  ## Catches DUTUnreachableError via its base class
        print(type(err).__name__, "-", err)  ## The specific type and its message
        print("caused by:", repr(err.__cause__))  ## The chained original exception
        print("attenuator restored to", att.db, "dB")  ## finally did its job
    errors = [DUTUnreachableError("ap-1", 3), ValueError("bad channel 14 on 5G")]  ## Failures collected from several checks
    try:  ## Report them all at once
        raise ExceptionGroup("bench check failed", errors)  ## 3.11+: one exception carrying many
    except* LabError as group:  ## except* matches the LabError part of the group
        print("lab errors:", [str(e) for e in group.exceptions])  ## The matching subset
    except* ValueError as group:  ## Each except* clause handles its own part
        print("config errors:", [str(e) for e in group.exceptions])  ## Both clauses run


if __name__ == "__main__":
    main()""",
            "under": "`raise X from Y` sets `X.__cause__ = Y` and the traceback prints both, joined by \"The above exception was the direct cause of the following exception\". Raising inside an `except` block without `from` still records the original in `__context__` (\"During handling of the above exception, another exception occurred\"). `raise X from None` suppresses the context entirely. With `except*`, Python splits the group by type, runs every matching clause once with a sub-group, and re-raises anything left unhandled.",
            "gotchas": [
                {
                    "title": "Swallowing the error with pass",
                    "note": "The test continues with partial data and later fails somewhere unrelated, or worse, passes. Handle, log, or let it propagate.",
                    "wrong": """results = {}
for ch in [36, 40]:
    try:
        results[ch] = 900 / (ch - 40)
    except Exception:
        pass
print(results)""",
                    "fixed": """results, errors = {}, {}
for ch in [36, 40]:
    try:
        results[ch] = 900 / (ch - 40)
    except ZeroDivisionError as err:
        errors[ch] = str(err)
print(results, errors)""",
                }
            ],
            "best": "Give your framework one base exception and a few meaningful subclasses with useful attributes. Translate library exceptions at the boundary with `raise ... from err`. Restore lab state in `finally` (or a context manager, Module 3.9). Collect independent failures and raise an ExceptionGroup when every one of them matters.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write `safe_float(text, default=None)` that returns float(text) or the default when the text isn't a number.",
            "solution": "Catch only ValueError.",
            "solution_code": """def safe_float(text, default=None):
    try:
        return float(text)
    except ValueError:
        return default


print(safe_float("912.4"), safe_float("n/a"), safe_float("n/a", 0.0))""",
        },
        {
            "level": "Medium",
            "prompt": "Create `ConfigError(LabError)` and raise it from inside a parser when a channel is invalid for its band (e.g. channel 14 on 5G). Catch it as LabError and print the message and the band attribute.",
            "solution": "Store the extra fields as attributes and pass a message to super().__init__.",
            "solution_code": """class LabError(Exception):
    pass


class ConfigError(LabError):
    def __init__(self, band, channel):
        super().__init__(f"channel {channel} is not valid on {band}")
        self.band = band
        self.channel = channel


VALID = {"2G": range(1, 14), "5G": range(36, 166)}


def check(band, channel):
    if channel not in VALID[band]:
        raise ConfigError(band, channel)
    return True


try:
    check("5G", 14)
except LabError as err:
    print(err, "| band:", err.band)""",
        },
        {
            "level": "Hard",
            "prompt": "Check three devices, collect every failure, and raise one ExceptionGroup at the end only if something failed. Handle the group with except* and print how many devices failed.",
            "solution": "Append failures to a list inside the loop; raise the group after it.",
            "solution_code": """def ping(host):
    if host.endswith("2") or host.endswith("3"):
        raise ConnectionError(f"{host}: no reply")
    return True


failures = []
for host in ["ap-1", "ap-2", "ap-3"]:
    try:
        ping(host)
    except ConnectionError as err:
        failures.append(err)

try:
    if failures:
        raise ExceptionGroup("health check", failures)
except* ConnectionError as group:
    print(len(group.exceptions), "devices failed:", [str(e) for e in group.exceptions])""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "When does the else block of a try statement run?", "a": "Only when the try block finished without raising. It keeps the try region small, so exceptions from follow-up code aren't accidentally caught by the same except.", "follow": "And finally? (Always: on success, on exception, and even after return or break.)"},
        {"level": "Intermediate", "q": "Why is a bare except: dangerous?", "a": "It catches everything, including KeyboardInterrupt and SystemExit, and hides programming errors such as TypeError or NameError. Catch specific exceptions; at most use `except Exception` at a top-level boundary and log the traceback.", "follow": "What's the difference between Exception and BaseException? (BaseException also covers KeyboardInterrupt, SystemExit and GeneratorExit.)"},
        {"level": "Intermediate", "q": "What does raise ... from err do?", "a": "It chains the original exception as `__cause__`, so the traceback shows both the low-level error and your domain error. `from None` suppresses the original when it adds nothing.", "follow": "What happens if you raise inside except without from? (The original is still attached as `__context__`.)"},
        {"level": "Intermediate", "q": "Why define a custom exception hierarchy?", "a": "Callers can catch everything from your framework with one base class, or handle specific failures precisely. Subclasses can carry structured data (host, attempts, band) for reporting and retry decisions.", "follow": "Which built-in should a 'bad value' error subclass? (Usually ValueError, or your own base class plus ValueError.)"},
        {"level": "Advanced", "q": "What are ExceptionGroup and except*?", "a": "Python 3.11 added ExceptionGroup to raise several unrelated exceptions together, e.g. from parallel tasks (asyncio.TaskGroup uses it). `except* T` handles the T-typed members of the group; several except* clauses can run for one group, and unhandled members are re-raised.", "follow": "Can you mix except and except* in one try? (No.)"},
    ],
    "quiz": [
        {"q": "Which block always runs?", "options": ["try", "except", "else", "finally"], "answer": 3, "why": "finally runs on success, failure and return."},
        {"q": "Does `except LookupError` catch a KeyError?", "options": ["Yes", "No", "Only with as", "Only in 3.11+"], "answer": 0, "why": "KeyError subclasses LookupError."},
        {"q": "What attribute does `raise B from a` set on B?", "options": ["__context__", "__cause__", "__traceback__", "args"], "answer": 1, "why": "from sets __cause__."},
        {"q": "When does try's else run?", "options": ["Always", "On any exception", "When try raised nothing", "After finally"], "answer": 2, "why": "else is the no-exception path."},
        {"q": "What does `except*` work with?", "options": ["Any exception", "ExceptionGroup members", "Only KeyboardInterrupt", "Warnings"], "answer": 1, "why": "except* splits an ExceptionGroup by type."},
    ],
    "cards": [
        {"front": "try / except / else / finally order", "back": "try → except (if raised) or else (if not) → finally always."},
        {"front": "raise X from err", "back": "Chains err as X.__cause__."},
        {"front": "Why not bare except:", "back": "It catches everything, even KeyboardInterrupt, and hides bugs."},
        {"front": "ExceptionGroup", "back": "Several exceptions raised together (3.11+), handled with except*."},
        {"front": "Re-raise the current exception", "back": "A bare `raise` inside except."},
    ],
}


M_2_6 = {
    "id": "2.6",
    "title": "File I/O, pathlib & with",
    "hours": 2.5,
    "summary": "Opening files safely with with, text vs binary modes and encodings, streaming large logs line by line, and organising result folders with pathlib.",
    "concepts": [
        {
            "title": "Reading and writing files with with",
            "concept": "`open(path, mode, encoding=...)` returns a file object. Modes: `\"r\"` read (default), `\"w\"` write (**truncates** first), `\"a\"` append, `\"x\"` create only if absent, plus `\"b\"` for binary. The `with` statement **guarantees the file is closed** when the block ends, even after an exception. Iterating a text file yields one line at a time, so even huge files use little memory. Always pass `encoding=\"utf-8\"` for text.",
            "why": "AP syslogs, iperf JSON, captured console output and CSV results are all files. A test run that leaks open file handles or loads a 2 GB log with `read()` eventually falls over in CI.",
            "syntax": "with open(path, encoding=\"utf-8\") as f:\n    for line in f:          # streams line by line\n        ...\nwith open(path, \"a\", encoding=\"utf-8\") as f:\n    f.write(\"text\\n\")\nwith open(path, \"rb\") as f:\n    data = f.read(64)       # bytes",
            "code": """import tempfile  ## A throwaway directory so the example leaves nothing behind
from pathlib import Path  ## Object-oriented paths (next concept)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:  ## The directory and its contents are deleted at the end of this block
        log = Path(tmp) / "ap1_syslog.txt"  ## Build a path inside it with the / operator
        log.write_text(  ## Convenience method: open, write, close in one call
            "10:00:01 sta aa:01 associated\\n"  ## Adjacent string literals are joined into one string
            "10:00:07 sta aa:02 deauth reason=15\\n"  ## Second log line
            "10:00:09 sta aa:01 roamed to ap-2\\n",  ## Third log line
            encoding="utf-8",  ## Explicit encoding: the same result on every OS
        )
        with open(log, encoding="utf-8") as f:  ## Text mode read; `f` is closed automatically after the block
            for lineno, line in enumerate(f, start=1):  ## Iterating a file yields one line at a time
                if "deauth" in line:  ## Only the lines we care about
                    print(lineno, line.rstrip())  ## rstrip() removes the trailing newline
        with open(log, "a", encoding="utf-8") as f:  ## Append mode: keeps existing content
            f.write("10:00:12 sta aa:03 associated\\n")  ## write() does not add a newline for you
        print(len(log.read_text(encoding="utf-8").splitlines()), "lines")  ## Re-read: now four lines
        print(f.closed)  ## The with block closed the file even though `f` still exists
        with open(log, "rb") as f:  ## Binary mode: returns bytes, no decoding
            print(f.read(8))  ## The first 8 raw bytes


if __name__ == "__main__":
    main()""",
            "under": "A text file object wraps a buffered binary stream with a decoder. Iteration reads a buffer at a time (8 KB by default) and splits it into lines, so memory stays small. Without an explicit `encoding`, Python uses the platform's locale encoding, which is UTF-8 on Linux and macOS but often cp1252 on Windows; that is why a script that reads logs fine on a Linux agent fails on a Windows one. `with` calls the file's `__exit__` method, which closes it (context managers are covered in Module 3.9).",
            "gotchas": [
                {
                    "title": "Mode \"w\" erases the file first",
                    "note": "Opening a results file with \"w\" to add a line wipes everything already in it. Use \"a\" to append, or \"x\" to refuse to overwrite.",
                    "wrong": """import tempfile, pathlib
with tempfile.TemporaryDirectory() as tmp:
    p = pathlib.Path(tmp) / "results.csv"
    p.write_text("test,verdict\\nroam_11r,PASS\\n")
    with open(p, "w") as f:
        f.write("dfs_cac,FAIL\\n")
    print(p.read_text())""",
                    "fixed": """import tempfile, pathlib
with tempfile.TemporaryDirectory() as tmp:
    p = pathlib.Path(tmp) / "results.csv"
    p.write_text("test,verdict\\nroam_11r,PASS\\n")
    with open(p, "a") as f:
        f.write("dfs_cac,FAIL\\n")
    print(p.read_text())""",
                },
                {
                    "title": "Reading a huge file all at once",
                    "note": "`read()` or `readlines()` loads the entire file into memory. Iterate the file object instead; here both count the same lines, but only one scales to gigabytes.",
                    "wrong": """import tempfile, pathlib
with tempfile.TemporaryDirectory() as tmp:
    p = pathlib.Path(tmp) / "soak.log"
    p.write_text("deauth\\nok\\n" * 1000)
    lines = open(p).read().splitlines()
    print(sum("deauth" in ln for ln in lines))""",
                    "fixed": """import tempfile, pathlib
with tempfile.TemporaryDirectory() as tmp:
    p = pathlib.Path(tmp) / "soak.log"
    p.write_text("deauth\\nok\\n" * 1000)
    with open(p, encoding="utf-8") as f:
        print(sum("deauth" in ln for ln in f))""",
                },
            ],
            "best": "Always use `with`, always pass `encoding=\"utf-8\"` for text, iterate large files line by line, and use `\"x\"` mode when overwriting would destroy evidence. For tool output that may contain invalid bytes (serial consoles), add `errors=\"replace\"`.",
        },
        {
            "title": "Organising results with pathlib",
            "concept": "`pathlib.Path` represents a filesystem path as an object. The `/` operator joins parts portably. Properties such as `.name`, `.stem`, `.suffix` and `.parent` take paths apart without string slicing. Methods create directories (`mkdir(parents=True, exist_ok=True)`), list contents (`iterdir`, `glob`, `rglob`) and read or write whole files (`read_text`, `write_text`).",
            "why": "A well-organised results tree, `results/<build>/<testcase>/`, holding logs, pcaps and summaries, is what makes a failed nightly run debuggable. pathlib builds and searches that tree in a few readable lines that work on Linux agents and Windows laptops alike.",
            "syntax": "root = Path(\"results\")\nrun = root / build / testcase\nrun.mkdir(parents=True, exist_ok=True)\nfor p in run.glob(\"*.pcap\"): ...\np.stem, p.suffix, p.parent, p.exists()\np.with_suffix(\".html\")",
            "code": """import tempfile  ## Throwaway directory for the demo
from pathlib import Path  ## The Path class


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:  ## Cleaned up automatically
        root = Path(tmp)  ## Wrap the temp dir in a Path
        run_dir = root / "results" / "build-4.32.1" / "throughput_6g"  ## Join parts with / (portable across OSes)
        run_dir.mkdir(parents=True, exist_ok=True)  ## Create every missing parent; no error if it already exists
        for name in ["iperf.json", "sta1.pcap", "ap.log", "summary.csv"]:  ## Typical artifacts of one test case
            (run_dir / name).write_text("x")  ## Create small placeholder files
        print(run_dir.relative_to(root))  ## The path relative to the results root
        print(sorted(p.name for p in run_dir.glob("*.p*")))  ## glob() matches names inside one directory
        print(sorted(p.suffix for p in run_dir.iterdir()))  ## iterdir() lists everything; .suffix is the extension
        report = run_dir / "summary.csv"  ## One specific file
        print(report.stem, report.suffix, report.parent.name, report.exists())  ## Name without extension, extension, folder, existence
        print(len(list(root.rglob("*.log"))))  ## rglob() searches every subdirectory recursively
        print(report.with_suffix(".html").name)  ## A sibling path with a different extension (nothing is created)


if __name__ == "__main__":
    main()""",
            "under": "`Path(...)` returns a `PosixPath` or `WindowsPath` for the current OS, which handles separators and drive letters. Path operations are pure until you call something that touches the disk (`exists`, `mkdir`, `iterdir`, `read_text`). `glob` patterns use shell rules (`*`, `?`, `[abc]`, and `**` for any depth), and results come back in no guaranteed order, so sort them.",
            "gotchas": [
                {
                    "title": "Building paths with string concatenation",
                    "note": "Manual separators break across operating systems and produce doubled or missing slashes. Let Path join the parts.",
                    "wrong": """base = "results/"
build = "/build-4.32.1"
print(base + "/" + build + "/" + "ap.log")""",
                    "fixed": """from pathlib import Path
print(Path("results") / "build-4.32.1" / "ap.log")""",
                }
            ],
            "best": "Accept and return `Path` objects in your helpers, build every path with `/`, create directories with `mkdir(parents=True, exist_ok=True)`, and sort glob results before using them. Keep one function that decides the results layout so every test writes to the same structure.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write three lines to a temporary file, then print how many lines contain the word 'associated'.",
            "solution": "write_text, then iterate the file inside with.",
            "solution_code": """import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp) / "events.log"
    p.write_text("sta1 associated\\nsta2 deauth\\nsta3 associated\\n", encoding="utf-8")
    with open(p, encoding="utf-8") as f:
        print(sum("associated" in line for line in f))""",
        },
        {
            "level": "Medium",
            "prompt": "Create the layout `results/<build>/<test>/` for two builds and two tests, then use rglob to list every created directory that ends with 'roam_11r'.",
            "solution": "Nested loops with mkdir(parents=True); rglob with the directory name.",
            "solution_code": """import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp) / "results"
    for build in ["4.32.0", "4.32.1"]:
        for test in ["roam_11r", "tput_5g"]:
            (root / build / test).mkdir(parents=True, exist_ok=True)
    print(sorted(str(p.relative_to(root)) for p in root.rglob("roam_11r")))""",
        },
        {
            "level": "Hard",
            "prompt": "Stream a log file and write only deauth lines to a second file, prefixed with their line number, without ever holding the whole log in memory. Print the output file's contents.",
            "solution": "Open both files in one with statement and process line by line.",
            "solution_code": """import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    src = Path(tmp) / "ap.log"
    dst = Path(tmp) / "deauth.log"
    src.write_text("ok\\ndeauth reason=15\\nok\\ndeauth reason=3\\n", encoding="utf-8")
    with open(src, encoding="utf-8") as fin, open(dst, "w", encoding="utf-8") as fout:
        for n, line in enumerate(fin, start=1):
            if line.startswith("deauth"):
                fout.write(f"{n}: {line}")
    print(dst.read_text(encoding="utf-8"), end="")""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Why use with to open files?", "a": "It guarantees the file is closed when the block ends, even if an exception is raised, without writing try/finally yourself. Leaked file handles can exhaust OS limits in long runs.", "follow": "Can one with statement open two files? (Yes: `with open(a) as f, open(b, 'w') as g:`.)"},
        {"level": "Beginner", "q": "What's the difference between modes 'w', 'a' and 'x'?", "a": "'w' truncates (or creates) the file, 'a' appends to the end, 'x' creates the file and fails with FileExistsError if it already exists. Add 'b' for binary.", "follow": "What does 'r+' do? (Read and write without truncating.)"},
        {"level": "Intermediate", "q": "How do you process a 10 GB log file?", "a": "Iterate over the file object line by line inside `with`, so only one buffer is in memory, and aggregate as you go. Avoid `read()` and `readlines()`. For binary data, read fixed-size chunks.", "follow": "How would you speed it up? (Filter cheaply first, e.g. `if 'deauth' in line` before a regex; or split the file across processes.)"},
        {"level": "Intermediate", "q": "Why always specify an encoding?", "a": "The default depends on the platform locale, typically UTF-8 on Linux but often cp1252 on Windows, so the same script can read a file correctly on one CI agent and fail on another. `encoding='utf-8'` makes behaviour consistent.", "follow": "What does errors='replace' do? (Substitutes undecodable bytes instead of raising UnicodeDecodeError.)"},
        {"level": "Advanced", "q": "pathlib vs os.path?", "a": "pathlib wraps paths in objects with operators and methods (`/`, `.suffix`, `.glob`, `.read_text`), which is more readable and less error-prone than string functions. os.path still works and appears in older code; most APIs accept both via `os.PathLike`.", "follow": "How do you get a plain string from a Path? (`str(p)` or `os.fspath(p)`.)"},
    ],
    "quiz": [
        {"q": "Which mode keeps existing content and writes at the end?", "options": ["'w'", "'a'", "'x'", "'r'"], "answer": 1, "why": "'a' appends."},
        {"q": "What is `Path('run/summary.csv').stem`?", "options": ["'summary.csv'", "'summary'", "'.csv'", "'run'"], "answer": 1, "why": "stem is the name without the suffix."},
        {"q": "What does iterating a text file object yield?", "options": ["Bytes", "Characters", "Lines", "Words"], "answer": 2, "why": "One line at a time, newline included."},
        {"q": "After `with open(p) as f: ...`, what is `f.closed`?", "options": ["True", "False", "None", "NameError"], "answer": 0, "why": "with closes the file; the name still exists."},
        {"q": "Which call searches subdirectories recursively?", "options": ["glob", "iterdir", "rglob", "listdir"], "answer": 2, "why": "rglob is recursive glob."},
    ],
    "cards": [
        {"front": "Open modes", "back": "r read, w truncate+write, a append, x create-only, b binary"},
        {"front": "Stream a large file", "back": "`with open(p, encoding='utf-8') as f: for line in f: ...`"},
        {"front": "Create nested dirs safely", "back": "`p.mkdir(parents=True, exist_ok=True)`"},
        {"front": "Path parts", "back": ".name, .stem, .suffix, .parent"},
        {"front": "Why encoding='utf-8'", "back": "The default depends on the OS locale."},
    ],
}
