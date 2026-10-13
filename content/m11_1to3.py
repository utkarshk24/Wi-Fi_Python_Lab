"""Phase 11 final interview round, part 1: rapid-fire, output puzzles, coding round."""


# --------------------------------------------------------------------------- 11.1
FACTS_CORE = '''import copy  ## Shallow vs deep copies


def append_to(item, bucket=[]):  ## The default list is created ONCE, when def runs
    bucket.append(item)  ## Mutates that shared list
    return bucket  ## Same object every call


print("1 mutable default:", append_to(1), append_to(2))  ## [1, 2] [1, 2]: both calls share one list
a, b = [1], [1]  ## Equal contents, two objects
print("2 == vs is:", a == b, a is b)  ## True False: value equality vs identity
nested = [[1], [2]]  ## A list of lists
shallow, deep = nested.copy(), copy.deepcopy(nested)  ## Copy the outer list only / copy everything
nested[0].append(9)  ## Change an inner list
print("3 copies:", shallow[0], deep[0])  ## [1, 9] [1]: the shallow copy shares inner lists
late = [lambda: i for i in range(3)]  ## Closures look up i when CALLED
early = [lambda i=i: i for i in range(3)]  ## Default argument captures the value now
print("4 closures:", [f() for f in late], [f() for f in early])  ## [2, 2, 2] [0, 1, 2]
print("5 dict order:", list({"b": 1, "a": 2, "c": 3}))  ## Insertion order is guaranteed (3.7+)
squares = (n * n for n in range(4))  ## A generator: single pass
print("6 generators:", list(squares), list(squares))  ## [0, 1, 4, 9] []: exhausted after one pass
print("7 and/or:", [] or "default", 0 and 1 / 0)  ## Return an operand, short-circuit (1/0 never runs)
runs = [("b", 1), ("a", 2), ("c", 1)]  ## Ties on the key
print("8 stable sort:", sorted(runs, key=lambda r: r[1]))  ## Equal keys keep their original order
print("9 chained compare:", 1 < 5 < 10, 1 < 5 > 10)  ## Means 1<5 and 5<10 / 1<5 and 5>10
print("10 one-tuple:", type((1)).__name__, type((1,)).__name__)  ## The comma makes the tuple, not the parentheses


def collect(*args, **kwargs):  ## Variadic parameters
    return args, kwargs  ## A tuple and a dict


print("11 *args/**kwargs:", collect(1, 2, band="5G"))  ## ((1, 2), {'band': '5G'})
name = "ap-lab-07"  ## Strings are immutable
print("12 immutability:", name.upper(), name)  ## upper() returns a new string; the original is unchanged'''

FACTS_RUNTIME = '''import math  ## isclose
from datetime import datetime, timezone  ## Naive vs aware


def returns_in_try():  ## finally always runs
    try:  ## Even when try returns
        return "returned"  ## Return value is remembered...
    finally:  ## ...then this runs before the function exits
        print("1 finally ran first")  ## Printed before the caller sees the value


print(returns_in_try())  ## "returned"
try:  ## Exception chaining
    try:  ## Low-level failure
        int("5G")  ## ValueError
    except ValueError as err:  ## Catch it...
        raise RuntimeError("bad channel config") from err  ## ...and raise a clearer one, keeping the cause
except RuntimeError as e:  ## The caller's view
    print("2 chained:", e, "<- caused by", type(e.__cause__).__name__)  ## Both are available
for ch in (36, 40, 44):  ## for/else
    if ch == 52:  ## Never true here
        break  ## Would skip the else
else:  ## Runs only if the loop did NOT break
    print("3 for/else: channel 52 not found")  ## "no break" branch


class Bench:  ## A context manager
    def __enter__(self):  ## On with-entry
        return self  ## Bound by "as"

    def __exit__(self, exc_type, exc, tb):  ## Always called, even on error
        print("4 __exit__ saw", exc_type.__name__)  ## Cleanup can see the exception
        return True  ## True = swallow it (rarely what you want)


with Bench():  ## Enter
    raise TimeoutError("iperf hung")  ## Exit still runs
print("5 round half to even:", round(0.5), round(1.5), round(2.5))  ## 0 2 2: banker's rounding
print("6 floats:", 0.1 + 0.2 == 0.3, math.isclose(0.1 + 0.2, 0.3))  ## Compare floats with a tolerance
try:  ## Naive vs aware datetimes
    print(datetime.now() < datetime.now(timezone.utc))  ## Can't compare
except TypeError as e:  ## Raised
    print("7 datetimes:", e)  ## Use timezone-aware datetimes everywhere
config = {"band": "5G"}  ## EAFP vs LBYL
print("8 dict access:", config.get("channel", 36), "channel" in config)  ## Default instead of KeyError
print("9 truthiness:", [bool(x) for x in (0, "", [], None, "0", [0])])  ## Empty/zero/None are falsy; "0" and [0] are not
print("10 integer division:", 7 // 2, -7 // 2, -7 % 2)  ## Floor division rounds toward minus infinity'''

RAPID = [
    ("Beginner", "List vs tuple?", "Lists are mutable and for homogeneous, changing collections; tuples are immutable, hashable when their items are, and used for fixed records (like `(band, channel)`) and dict keys."),
    ("Beginner", "What is a dict lookup's time complexity?", "Average O(1) via hashing; worst case O(n) with many collisions. Keys must be hashable."),
    ("Beginner", "`is` vs `==`?", "`==` compares values via `__eq__`; `is` compares identity (same object). Use `is` only for singletons like `None`."),
    ("Beginner", "Why is a mutable default argument a bug?", "Defaults are evaluated once when `def` runs, so every call shares the same list or dict. Use `None` and create a new one inside."),
    ("Beginner", "What does `if __name__ == \"__main__\":` do?", "Runs the block only when the file is executed directly, not when imported, so modules can be imported by tests without side effects."),
    ("Beginner", "List comprehension vs generator expression?", "`[...]` builds the whole list in memory; `(...)` produces items lazily, one pass only. Use generators for large or streaming data."),
    ("Intermediate", "What is a decorator?", "A callable that takes a function and returns a replacement, usually a wrapper adding behaviour (retry, timing, logging). `@d` above `def f` means `f = d(f)`; use `functools.wraps` to keep the name and docstring."),
    ("Intermediate", "What is a closure?", "An inner function that remembers variables from its enclosing scope after that scope has returned. Variables are looked up at call time (late binding)."),
    ("Intermediate", "Shallow vs deep copy?", "A shallow copy duplicates the outer container but shares the inner objects; `copy.deepcopy` recursively copies everything."),
    ("Intermediate", "What is the GIL and when does it matter?", "CPython's global interpreter lock lets one thread run Python bytecode at a time. It limits CPU-bound threading (use processes) but not I/O-bound work, where threads or asyncio work well. Free-threaded builds (3.13+) are experimental."),
    ("Intermediate", "Threads vs asyncio vs multiprocessing?", "Threads: simple I/O concurrency with blocking libraries. asyncio: many concurrent I/O tasks in one thread with async libraries. Multiprocessing: CPU-bound work across cores."),
    ("Intermediate", "What does `yield` do?", "Makes the function a generator: it pauses at `yield`, hands out a value, and resumes on the next `next()`. State is kept between calls."),
    ("Intermediate", "What is a context manager?", "An object with `__enter__`/`__exit__` (or a `@contextmanager` generator) used with `with` to guarantee setup and cleanup, even when an exception occurs."),
    ("Intermediate", "`*args` and `**kwargs`?", "Collect extra positional arguments into a tuple and extra keyword arguments into a dict; also used to unpack when calling."),
    ("Intermediate", "How are exceptions chained?", "`raise New(...) from err` sets `__cause__`; raising inside an `except` without `from` sets `__context__`. Tracebacks show both."),
    ("Intermediate", "`@staticmethod` vs `@classmethod`?", "A staticmethod gets no implicit argument; a classmethod gets the class (`cls`), which makes it ideal for alternative constructors like `Bench.from_yaml()`."),
    ("Intermediate", "What are dataclasses for?", "Generating `__init__`, `__repr__` and `__eq__` for record-like classes from type-annotated fields; `frozen=True` makes them immutable and hashable."),
    ("Advanced", "How does Python manage memory?", "Reference counting frees most objects immediately; a cyclic garbage collector handles reference cycles. Small objects come from pymalloc arenas."),
    ("Advanced", "What is `__slots__`?", "A class attribute listing allowed instance attributes; it removes the per-instance `__dict__`, saving memory and preventing typos, at the cost of flexibility."),
    ("Advanced", "Explain the descriptor protocol briefly.", "Objects defining `__get__`/`__set__`/`__delete__` control attribute access on classes that hold them; `property`, methods and `classmethod` are built on it."),
    ("Beginner", "pytest fixture: what and why?", "A function providing setup (and teardown after `yield`) that tests request by parameter name; scopes (function/module/session) control reuse. It replaces setUp/tearDown with composable dependencies."),
    ("Beginner", "How do you parametrize a test?", "`@pytest.mark.parametrize(\"band,mbps\", [(\"5G\", 900), (\"6G\", 2000)])` runs the test once per tuple, each reported separately."),
    ("Intermediate", "What is conftest.py?", "A file pytest loads automatically for its directory and below: shared fixtures, hooks and options, with no import needed."),
    ("Intermediate", "How do you skip or mark expected failures?", "`pytest.mark.skip`/`skipif(condition, reason=...)` for not applicable; `xfail` for known bugs (strict=True so a fix is noticed); `pytest.skip()` at runtime."),
    ("Intermediate", "How do you mock in pytest?", "`monkeypatch` to replace attributes and environment variables, or `unittest.mock.patch`/`MagicMock` to replace objects and assert calls. Patch where the name is looked up, not where it is defined."),
    ("Intermediate", "What is `tmp_path`?", "A built-in fixture giving each test a unique temporary `pathlib.Path` directory, cleaned up automatically by retention policy."),
    ("Intermediate", "How do you test that code raises?", "`with pytest.raises(ValueError, match=\"channel\"):` around the call; the `match` regex checks the message."),
    ("Intermediate", "How do you handle flaky tests?", "Find the cause first (timing, shared state, environment). Use polling with timeouts instead of sleeps, isolate state, and quarantine with a marker and a ticket. Reruns are a temporary bandage that must stay visible."),
    ("Advanced", "Name some useful pytest hooks.", "`pytest_addoption` (CLI options), `pytest_collection_modifyitems` (reorder/skip), `pytest_runtest_makereport` (results, e.g. for screenshots/log capture), `pytest_configure` (markers, plugins)."),
    ("Advanced", "How do you run pytest in parallel safely?", "pytest-xdist `-n auto` for independent tests; anything touching shared hardware needs per-worker resources (one bench per worker via `worker_id`) or locks."),
    ("Beginner", "How do you run a shell command safely from Python?", "`subprocess.run([\"ping\", \"-c\", \"1\", host], capture_output=True, text=True, timeout=10, check=True)`: list arguments, no `shell=True`, always a timeout."),
    ("Beginner", "How do you call a REST API robustly?", "requests/httpx with a session, timeouts, `raise_for_status()`, retries with backoff for idempotent calls, and credentials from the environment or a vault."),
    ("Intermediate", "Netmiko vs Paramiko vs NETCONF/RESTCONF?", "Paramiko is raw SSH; Netmiko adds device-aware CLI handling (prompts, paging, config mode); NETCONF/RESTCONF give structured, model-driven data and transactional config, preferred when the device supports them."),
    ("Intermediate", "How do you run commands on 200 devices quickly?", "Concurrency: a thread pool with Netmiko or asyncio with asyncssh/scrapli, bounded by a semaphore, with per-device timeouts and results/errors collected per device."),
    ("Intermediate", "How do you parse CLI output?", "Prefer structured output (JSON, NETCONF). Otherwise TextFSM/ttp templates or named-group regexes, with tests on captured outputs from each firmware version."),
    ("Intermediate", "What is SNMP used for in automation?", "Polling counters and state (interfaces, clients, CPU) and receiving traps; SNMPv3 for authentication and encryption. Counters wrap, so compute rates with wrap handling."),
    ("Intermediate", "How do you capture and analyse packets from Python?", "Capture with tcpdump/tshark (monitor mode for 802.11), analyse with scapy (`rdpcap`/`PcapReader`) or pyshark/tshark JSON; build per-flow or per-client state machines for KPIs."),
    ("Intermediate", "How do you make a lab automation step idempotent?", "Check current state before changing it (desired-state), make re-runs harmless, and verify after applying, so retries and partial failures are safe."),
    ("Advanced", "How do you control lab equipment (attenuators, traffic generators)?", "Wrap each instrument (SCPI over TCP, REST, vendor API) in a small class with connect/verify/reset, verify every set with a read-back, enforce timeouts, and always restore a safe state in teardown."),
    ("Advanced", "What makes Wi-Fi throughput tests trustworthy?", "Controlled RF (shielding/attenuation), verified settings, warm-up and settle time, several iterations with median and worst case, full metadata, and comparison against KPIs and a baseline with tolerances from measured variance."),
    ("Beginner", "What is CI vs CD?", "CI: every change is built and tested automatically. CD: changes that pass are automatically deliverable (continuous delivery) or deployed (continuous deployment)."),
    ("Beginner", "How do you pin dependencies?", "Declare ranges in pyproject.toml, lock exact versions (pip-tools, uv or poetry lock files) for reproducible CI and benches, and update deliberately."),
    ("Intermediate", "What is a virtual environment?", "An isolated interpreter with its own site-packages (`python -m venv .venv`), so projects don't conflict and installs are reproducible."),
    ("Intermediate", "What goes in a good CI pipeline for a test framework?", "Lint/format (ruff), type check (mypy), unit tests with coverage, build the package, then hardware tests on lab agents, publishing JUnit and artifacts."),
    ("Intermediate", "Declarative vs scripted Jenkins pipelines?", "Declarative has a fixed structure (`pipeline`, `stages`, `post`) that is easier to read and validate; scripted is plain Groovy with full flexibility. Prefer declarative and keep logic in scripts."),
    ("Intermediate", "How do you keep secrets out of code and logs?", "Credentials bindings or a vault, environment variables at runtime, masked output, no secrets in repos (pre-commit/secret scanning), and least privilege."),
    ("Intermediate", "What does `git bisect` do?", "Binary-searches history between a good and a bad commit to find the change that introduced a bug; `git bisect run <script>` automates it with an exit-code test."),
    ("Intermediate", "How do you version a test framework?", "Semantic versioning (major for breaking changes), tags and a changelog, ideally generated from Conventional Commits; pin the framework version per firmware branch."),
    ("Advanced", "How would you speed up a 10-hour nightly suite?", "Measure first (durations), parallelise across benches with sharding by duration, select tests by change, move checks down the pyramid (unit/simulator), cut fixed sleeps, and fail fast with pre-flight checks."),
    ("Advanced", "What do you log in an automation framework?", "Structured logs with test id, bench, device and step; DEBUG to file, INFO to console; device console and command transcripts attached on failure; timestamps in UTC; no secrets."),
]

M_11_1 = {
    "id": "11.1",
    "title": "Rapid-Fire 50",
    "hours": 2,
    "summary": "Fifty short questions spanning the whole course (language, pytest, automation, CI/CD) with crisp answers, plus runnable proofs of the facts interviewers like to probe.",
    "concepts": [
        {
            "title": "Prove it: core language facts",
            "concept": "Rapid-fire rounds test whether you know the language's sharp edges. Answers land better when you can say *why*, and the fastest way to be sure is to have run each fact yourself. This block proves twelve classics: mutable defaults, identity vs equality, shallow vs deep copy, late-binding closures, dict order, single-pass generators, `and`/`or` returning operands, stable sorting, chained comparisons, the one-element tuple, `*args/**kwargs`, and string immutability.",
            "why": "Interviewers often follow \"what does this print?\" with \"why?\". Being able to point at the mechanism (\"defaults are evaluated once at def time\") is the difference between a memorised answer and understanding.",
            "syntax": "def f(x, bucket=None):\n    bucket = [] if bucket is None else bucket\n[lambda i=i: i for i in range(3)]",
            "code": FACTS_CORE,
            "under": "Most of these come down to one idea: Python names are references to objects. `bucket=[]` binds one object at definition time; `b = a` gives a second name for the same list; a shallow copy creates a new outer list holding references to the same inner lists; a closure stores a reference to the variable, not its value at creation.",
            "gotchas": [],
            "best": "Answer in three beats: the result, the mechanism, the fix or best practice. For example: \"[1, 2] twice; defaults are evaluated once; use None and create the list inside.\"",
        },
        {
            "title": "Prove it: errors, runtime and testing facts",
            "concept": "Ten more facts that come up in automation interviews: `finally` runs even after `return`, exception chaining with `from`, `for/else`, `__exit__` seeing exceptions, banker's rounding, float comparison, naive vs aware datetimes, `dict.get` defaults, truthiness, and floor division with negatives.",
            "why": "These are the facts behind real bugs: cleanup that didn't run, timestamps that can't be compared across benches, a KPI check that fails on `0.1 + 0.2`, a swallowed exception hiding a hung iperf. Knowing them is what interviewers are probing.",
            "syntax": "raise RuntimeError(\"...\") from err\nmath.isclose(a, b, rel_tol=1e-9)\ndatetime.now(timezone.utc)",
            "code": FACTS_RUNTIME,
            "under": "`round()` uses round-half-to-even to avoid systematic bias when summing many rounded values. Comparing a naive and an aware datetime raises because Python refuses to guess the time zone. Returning `True` from `__exit__` suppresses the exception, which is why the program carried on after the `TimeoutError`; in real code that is almost always a bug.",
            "gotchas": [],
            "best": "Store and compare times as UTC-aware datetimes, compare floats with tolerances, chain exceptions so the root cause survives, and never swallow exceptions in context managers unless that is the explicit purpose.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Fix `def add_result(r, results=[])` so each call without a list starts fresh, and show the fix works.",
            "solution": "Use `None` as the sentinel and create the list inside the function.",
            "solution_code": """def add_result(r, results=None):
    results = [] if results is None else results
    results.append(r)
    return results

print(add_result("pass"), add_result("fail"))
shared = []
print(add_result("pass", shared), add_result("skip", shared))""",
        },
        {
            "level": "Medium",
            "prompt": "Build three callbacks that each print their own channel (36, 40, 44) in three different ways: default argument, `functools.partial`, and a factory function.",
            "solution": "All three capture the value at creation time instead of looking up the loop variable later.",
            "solution_code": """from functools import partial

def report(ch):
    return f"ch{ch}"

by_default = [lambda ch=ch: report(ch) for ch in (36, 40, 44)]
by_partial = [partial(report, ch) for ch in (36, 40, 44)]

def make(ch):
    return lambda: report(ch)

by_factory = [make(ch) for ch in (36, 40, 44)]
for group in (by_default, by_partial, by_factory):
    print([f() for f in group])""",
        },
        {
            "level": "Hard",
            "prompt": "\"What happens when you run `python script.py`?\" Give a 60-second answer, and demonstrate the compile-then-execute step in code.",
            "solution": "Answer outline: the interpreter starts and sets up `sys.path`; the source is tokenised, parsed into an AST and compiled to bytecode (imported modules have theirs cached in `__pycache__/*.pyc`); the bytecode runs on the interpreter's evaluation loop in the `__main__` module's namespace; names are looked up at runtime (LEGB); objects are reference counted, and at exit `atexit` handlers run and buffers are flushed.",
            "solution_code": """import ast

source = "total = sum(range(5))"
tree = ast.parse(source)
print(type(tree.body[0]).__name__)
code = compile(tree, "<demo>", "exec")
namespace = {}
exec(code, namespace)
print(type(code).__name__, namespace["total"])""",
        },
    ],
    "interview": [{"level": lvl, "q": q, "a": a} for lvl, q, a in RAPID],
    "quiz": [
        {"q": "`round(2.5)` returns...", "options": ["3", "2", "2.0", "Error"], "answer": 1, "why": "Round half to even."},
        {"q": "`[] or 'x'` evaluates to...", "options": ["True", "[]", "'x'", "False"], "answer": 2, "why": "`or` returns the first truthy operand."},
        {"q": "Which makes a one-element tuple?", "options": ["(1)", "(1,)", "tuple(1)", "[1]"], "answer": 1, "why": "The comma makes the tuple."},
        {"q": "pytest's built-in fixture for a per-test temp directory is...", "options": ["tmpdir_session", "tmp_path", "tempfile", "workdir"], "answer": 1, "why": "tmp_path (pathlib.Path)."},
    ],
    "cards": [
        {"front": "Answer formula", "back": "Result → mechanism → fix/best practice"},
        {"front": "Defaults", "back": "Evaluated once at def time; use None for mutable defaults"},
        {"front": "GIL", "back": "Limits CPU-bound threads; I/O-bound threads and asyncio are fine"},
    ],
}


# --------------------------------------------------------------------------- 11.2
TRACE = '''nums = [1, 2, 2, 3]  ## The puzzle: remove every 2 while looping over the list
i = 0  ## A for-loop over a list is really an index that keeps increasing
while i < len(nums):  ## ...checked against the CURRENT length each time
    n = nums[i]  ## Fetch by index
    print(f"i={i} n={n} nums={nums}")  ## One row of the trace table
    if n == 2:  ## The puzzle's condition
        nums.remove(n)  ## Later items shift left by one...
    i += 1  ## ...but the index still advances, so one item is skipped
print("result:", nums)  ## [1, 2, 3]: the second 2 was never looked at'''

BINDING = '''a = [1, 2]  ## One list object
b = a  ## A second name for the SAME object
print("same object:", a is b)  ## True
b += [3]  ## += on a list mutates in place (extend)
print("after +=:", a, a is b)  ## [1, 2, 3] True: a sees the change
b = b + [4]  ## + builds a NEW list; = rebinds b to it
print("after +:", a, b, a is b)  ## a unchanged, b is a different object now
t = (1, 2)  ## Tuples are immutable
u = t  ## Same object
u += (3,)  ## Can't mutate, so += creates a new tuple and rebinds u
print("tuple +=:", t, u, t is u)  ## (1, 2) (1, 2, 3) False
grid = [[0] * 2] * 2  ## The outer * copies REFERENCES to one inner list
grid[0][0] = 9  ## Changes the single shared inner list
print("list * n:", grid)  ## [[9, 0], [9, 0]]
grid = [[0] * 2 for _ in range(2)]  ## A comprehension makes a fresh inner list each time
grid[0][0] = 9  ## Only the first row
print("comprehension:", grid)  ## [[9, 0], [0, 0]]'''

PUZZLES = [
    ("Easy", "a = [1, 2, 3]\nb = a\nb += [4]\nprint(a, a is b)",
     "`+=` on a list extends it in place, and `b` is just another name for the same list."),
    ("Easy", "t = (1, 2)\nu = t\nu += (3,)\nprint(t, u, t is u)",
     "Tuples are immutable, so `+=` builds a new tuple and rebinds `u`; `t` is untouched."),
    ("Easy", "x = [] or \"empty\"\ny = 0 and 1 / 0\nprint(x, y)",
     "`or` returns the first truthy operand; `and` returns the first falsy one and short-circuits, so the division never runs."),
    ("Easy", "print(0.1 + 0.2 == 0.3, round(0.1 + 0.2, 10) == 0.3)\nprint(round(2.5), round(3.5))",
     "Binary floats can't represent 0.1 exactly; compare with a tolerance. `round` uses round-half-to-even."),
    ("Easy", "s = \"ap-lab-07\"\nprint(s[::-1][:2], s.split(\"-\", 1), s.title())",
     "Reversed then first two characters; `maxsplit=1` splits once; `title()` capitalises after every non-letter."),
    ("Easy", "print(*\"abc\", sep=\"-\", end=\"!\\n\")",
     "`*` unpacks the string into three arguments; `sep` goes between them and `end` replaces the newline."),
    ("Easy", "print(f\"{3.14159:.2f}|{42:>5}|{255:#x}|{0.25:.0%}\")",
     "Format specs: two decimals, right-aligned in width 5, hex with prefix, percentage with no decimals."),
    ("Medium", "def add(item, bucket=[]):\n    bucket.append(item)\n    return bucket\n\nprint(add(1), add(2))\nprint(add(3, []))",
     "The default list is created once and shared; both calls in the first print return the same list, printed after both appends. Passing a list explicitly avoids the shared default."),
    ("Medium", "fs = [lambda: i * 10 for i in range(3)]\nprint([f() for f in fs])",
     "Closures look up `i` when called, after the loop finished with `i == 2`."),
    ("Medium", "g = (n * n for n in range(4))\nprint(sum(g), sum(g))",
     "A generator can be consumed only once; the second `sum` sees no items."),
    ("Medium", "d = {}\nd[1] = \"int\"\nd[1.0] = \"float\"\nd[True] = \"bool\"\nprint(d)",
     "`1 == 1.0 == True` and they hash equal, so they are the same key. The first key object is kept; the value is overwritten."),
    ("Medium", "def f():\n    try:\n        return \"try\"\n    finally:\n        print(\"finally runs\")\n\nprint(f())",
     "`finally` runs before the function actually returns, so its print appears first."),
    ("Medium", "a = [[0] * 2] * 2\na[0][0] = 9\nprint(a)",
     "The outer `* 2` repeats a reference to one inner list, so both rows are the same object."),
    ("Medium", "nums = [1, 2, 2, 3]\nfor n in nums:\n    if n == 2:\n        nums.remove(n)\nprint(nums)",
     "Removing shifts later items left while the loop's index moves on, so the second 2 is skipped. Iterate over a copy or build a new list."),
    ("Medium", "from collections import Counter\nc = Counter(\"deauth deauth radar\".split())\nc[\"crash\"] += 0\nprint(c.most_common(1), len(c), c[\"missing\"])",
     "`+= 0` creates the key; reading a missing key returns 0 without inserting it."),
    ("Medium", "def counter():\n    n = 0\n    def inc():\n        nonlocal n\n        n += 1\n        return n\n    return inc\n\na, b = counter(), counter()\nprint(a(), a(), b())",
     "Each call to `counter()` creates a new `n`; `nonlocal` lets `inc` rebind it."),
    ("Medium", "runs = [(\"5G\", 3), (\"6G\", 1), (\"2G\", 3), (\"5G\", 1)]\nprint(sorted(runs, key=lambda r: r[1]))",
     "Python's sort is stable: items with equal keys keep their original relative order."),
    ("Medium", "print(-7 // 2, -7 % 2, int(-7 / 2))",
     "`//` floors toward minus infinity; `%` takes the sign of the divisor; `int()` truncates toward zero."),
    ("Hard", "count = 0\n\ndef bump():\n    try:\n        count += 1\n    except UnboundLocalError as e:\n        print(type(e).__name__)\n\nbump()\nprint(count)",
     "Assigning to `count` anywhere in the function makes it local for the whole function, so reading it before assignment fails. Use `global` (or better, return a value)."),
    ("Hard", "class Bench:\n    tags = []\n    def __init__(self, name):\n        self.name = name\n        self.tags.append(name)\n\na, b = Bench(\"lab-07\"), Bench(\"lab-12\")\nprint(a.tags, b.tags is Bench.tags)",
     "`tags` is a class attribute shared by all instances; `self.tags.append` mutates it. Create per-instance lists in `__init__`."),
    ("Hard", "def tag(label):\n    def deco(fn):\n        def wrapper():\n            return f\"{label}({fn()})\"\n        return wrapper\n    return deco\n\n@tag(\"a\")\n@tag(\"b\")\ndef f():\n    return \"x\"\n\nprint(f())",
     "Decorators apply bottom-up (`f = tag(\"a\")(tag(\"b\")(f))`), so the outermost wrapper is `a`."),
    ("Hard", "class Mac:\n    def __init__(self, s):\n        self.s = s.lower()\n    def __eq__(self, other):\n        return self.s == other.s\n\nprint(Mac(\"AA:BB\") == Mac(\"aa:bb\"))\ntry:\n    {Mac(\"aa:bb\")}\nexcept TypeError as e:\n    print(e)",
     "Defining `__eq__` without `__hash__` sets `__hash__` to None, so instances can't go in sets or be dict keys. Define `__hash__` consistently (or use a frozen dataclass)."),
    ("Hard", "first, *middle, last = range(5)\nprint(first, middle, last)\na, b = b, a = 1, 2\nprint(a, b)",
     "Star-unpacking collects the middle into a list. In a chained assignment the value is assigned to each target list from left to right: first `a, b = 1, 2`, then `b, a = 1, 2`."),
    ("Hard", "import asyncio\n\nasync def job(name, delay):\n    await asyncio.sleep(delay)\n    print(name)\n    return name\n\nasync def main():\n    print(await asyncio.gather(job(\"slow\", 0.02), job(\"fast\", 0.01)))\n\nasyncio.run(main())",
     "Both jobs run concurrently, so the shorter one prints first, but `gather` returns results in the order the awaitables were passed."),
]

EXPECTED = [
    "[1, 2, 3, 4] True",
    "(1, 2) (1, 2, 3) False",
    "empty 0",
    "False True\n2 4",
    "70 ['ap', 'lab-07'] Ap-Lab-07",
    "a-b-c!",
    "3.14|   42|0xff|25%",
    "[1, 2] [1, 2]\n[3]",
    "[20, 20, 20]",
    "14 0",
    "{1: 'bool'}",
    "finally runs\ntry",
    "[[9, 0], [9, 0]]",
    "[1, 2, 3]",
    "[('deauth', 2)] 3 0",
    "1 2 1",
    "[('6G', 1), ('5G', 1), ('5G', 3), ('2G', 3)]",
    "-4 1 -3",
    "UnboundLocalError\n0",
    "['lab-07', 'lab-12'] True",
    "a(b(x))",
    "True\nunhashable type: 'Mac'",
    "0 [1, 2, 3] 4\n2 1",
    "fast\nslow\n['slow', 'fast']",
]


def _puzzle(i, level, code, why, expected):
    shown = "\n".join(f"`{line}`" for line in expected.split("\n"))
    return {"level": level, "prompt": f"**Puzzle {i}.** Predict the exact output, then run it to check.",
            "code": code, "expected": expected,
            "solution": f"**Output:**\n{shown}\n\n{why}"}


M_11_2 = {
    "id": "11.2",
    "title": "Output Puzzles",
    "hours": 2,
    "summary": "Twenty-four \"what does this print?\" puzzles, from easy to nasty, with a method for solving them: trace the state, separate rebinding from mutation, and know the handful of rules most puzzles are built on.",
    "concepts": [
        {
            "title": "Trace, don't guess",
            "concept": "Output puzzles reward a mechanical method: rewrite the tricky construct into what Python actually does, then keep a trace table of every variable after each step. Here the classic \"remove while iterating\" puzzle is rewritten as the index-based loop a `for` over a list really is, printing one trace row per iteration.",
            "why": "Under interview pressure intuition fails on exactly the cases puzzles are built from. A trace table is slow but always right, and talking through it out loud shows the interviewer how you debug.",
            "syntax": "# for x in seq:  ==  i = 0; while i < len(seq): x = seq[i]; ...; i += 1",
            "code": TRACE,
            "under": "A list iterator stores an index and compares it with the list's current length on every step, so removing items during iteration skips elements and appending can loop forever. Dicts and sets detect size changes and raise `RuntimeError` instead.",
            "gotchas": [],
            "best": "Never mutate a collection while iterating over it: iterate over a copy (`for n in nums[:]`) or build a new one (`[n for n in nums if n != 2]`).",
        },
        {
            "title": "Rebinding vs mutation: the rule behind most puzzles",
            "concept": "`=` binds a name to an object; methods like `append`, and `+=` on mutable types, change an object in place. Most \"surprising\" outputs (aliases that change together, tuples that don't, grids whose rows move together) are this one rule. The block checks identity with `is` at each step.",
            "why": "The same rule explains real automation bugs: a config dict shared between two benches, a results list that keeps growing across tests, a fixture returning the same mutable object to every test.",
            "syntax": "b = a        # same object\nb = a[:]     # new list (shallow)\nb += [x]     # list: mutate; tuple/str/int: rebind",
            "code": BINDING,
            "under": "`x += y` calls `x.__iadd__(y)` if it exists (lists have it and mutate), otherwise falls back to `x = x + y` (tuples, strings, ints), which creates a new object. `[row] * n` repeats references, never copies.",
            "gotchas": [],
            "best": "When a puzzle involves two names, ask first: same object or different objects? Then: does this operation mutate or rebind?",
        },
    ],
    "exercises": [_puzzle(i + 1, lvl, code, why, exp) for i, ((lvl, code, why), exp) in enumerate(zip(PUZZLES, EXPECTED, strict=True))],
    "interview": [
        {"level": "Intermediate", "q": "How do you approach a \"what does this print\" question?", "a": "Read it once fully, identify the trick category (mutation vs rebinding, scope, late binding, evaluation order, generator exhaustion, hashing), then trace step by step out loud with a small state table, and state the output with the rule that produces it.", "follow": "What if you're unsure? (Say which two outputs are possible and which rule decides, rather than guessing silently.)"},
        {"level": "Intermediate", "q": "Why does `[[0] * 3] * 3` give a broken grid?", "a": "The outer multiplication repeats a reference to the same inner list, so changing one row changes all of them. Use `[[0] * 3 for _ in range(3)]`.", "follow": "Why is `[0] * 3` fine? (Ints are immutable; you can only rebind elements, never mutate them.)"},
        {"level": "Advanced", "q": "Why can't instances of a class that defines `__eq__` go in a set?", "a": "Defining `__eq__` without `__hash__` sets `__hash__` to None, because equal objects must hash equally and Python can't guess a consistent hash. Define `__hash__` from the same fields, or use `@dataclass(frozen=True)`.", "follow": "Why must the hash fields be immutable? (If they change, the object is in the wrong bucket and lookups fail.)"},
    ],
    "quiz": [
        {"q": "`t = (1,); t += (2,)` does what?", "options": ["Mutates t", "Creates a new tuple and rebinds t", "Raises TypeError", "Nothing"], "answer": 1, "why": "Tuples have no __iadd__."},
        {"q": "`-7 // 2` is...", "options": ["-3", "-4", "-3.5", "3"], "answer": 1, "why": "Floor toward minus infinity."},
        {"q": "Stacked decorators `@a` over `@b` apply...", "options": ["a first", "b first (bottom-up)", "Simultaneously", "Only a"], "answer": 1, "why": "f = a(b(f))."},
    ],
    "cards": [
        {"front": "Puzzle checklist", "back": "Same object? Mutate or rebind? Scope? When is it evaluated? Single-pass?"},
        {"front": "x += y", "back": "__iadd__ if defined (mutates lists), else x = x + y (new object)"},
        {"front": "__eq__ without __hash__", "back": "Unhashable: not usable in sets or as dict keys"},
    ],
}


# --------------------------------------------------------------------------- 11.3
APPROACH = '''import random  ## Random test inputs


def longest_good_brute(rssi, floor=-70):  ## Step 2: obviously-correct brute force, O(n^2)
    best = 0  ## Longest run found
    for start in range(len(rssi)):  ## Every start...
        end = start  ## ...extend while samples stay good
        while end < len(rssi) and rssi[end] >= floor:  ## Still above the floor
            end += 1  ## Grow
        best = max(best, end - start)  ## Keep the longest
    return best  ## Seconds of good signal


def longest_good(rssi, floor=-70):  ## Step 3: one pass, O(n) time, O(1) space
    best = current = 0  ## Longest so far / current run
    for value in rssi:  ## Each sample once
        current = current + 1 if value >= floor else 0  ## Extend or reset the run
        best = max(best, current)  ## Track the maximum
    return best  ## Same answer, linear time


samples = [-65, -68, -72, -60, -61, -66, -69, -75, -64]  ## Step 1: a worked example (one RSSI sample per second)
print("example:", longest_good(samples))  ## 4 (-60, -61, -66, -69)
assert longest_good([]) == 0 and longest_good([-80]) == 0 and longest_good([-50] * 5) == 5  ## Step 4: edge cases
rng = random.Random(7)  ## Seeded: reproducible
for _ in range(500):  ## Step 4b: compare with the brute force on random inputs
    data = [rng.randint(-85, -50) for _ in range(rng.randint(0, 30))]  ## Random length and values
    assert longest_good(data) == longest_good_brute(data), data  ## Show the failing input if they differ
print("500 random cases agree with the brute force")  ## Confidence before optimising further'''

PATTERNS = '''import bisect  ## Binary search
import heapq  ## Top-k
from collections import Counter, deque  ## Counting, BFS queue

errors = ["timeout", "auth", "timeout", "crash", "timeout", "auth"]  ## Hash map counting, O(n)
print("count:", Counter(errors).most_common(2))  ## [('timeout', 3), ('auth', 2)]

mbps = {"ap1": 940, "ap2": 610, "ap3": 2400, "ap4": 120, "ap5": 1800}  ## Top-k with a heap, O(n log k)
print("top-2:", heapq.nlargest(2, mbps, key=mbps.get))  ## ['ap3', 'ap5']


def merge(intervals):  ## Interval merging, O(n log n): bench reservations
    out = []  ## Merged intervals
    for start, end in sorted(intervals):  ## By start time
        if out and start <= out[-1][1]:  ## Overlaps the last one
            out[-1][1] = max(out[-1][1], end)  ## Extend it
        else:  ## Gap
            out.append([start, end])  ## New interval
    return out  ## Non-overlapping


print("merge:", merge([(9, 11), (10, 12), (14, 15), (13, 14)]))  ## [[9, 12], [13, 15]]
atten = [0, 6, 12, 18, 24, 30, 36, 42]  ## Binary search on sorted data, O(log n)
throughput = [940, 938, 930, 905, 850, 666, 370, 136]  ## Falls as attenuation rises
first_below = bisect.bisect_left([-t for t in throughput], -500)  ## Negate to make it ascending
print("first point below 500 Mbps:", atten[first_below], "dB")  ## 36 dB


def hops(links, src, dst):  ## BFS shortest path in an unweighted mesh, O(V + E)
    seen, queue = {src}, deque([(src, 0)])  ## Visited set and frontier
    while queue:  ## Until exhausted
        node, dist = queue.popleft()  ## FIFO: nearest first
        if node == dst:  ## Found
            return dist  ## Fewest hops
        for nxt in links.get(node, ()):  ## Neighbours
            if nxt not in seen:  ## Not queued yet
                seen.add(nxt)  ## Mark
                queue.append((nxt, dist + 1))  ## Explore later
    return -1  ## Unreachable


mesh = {"root": ["mp1", "mp2"], "mp1": ["mp3"], "mp2": ["mp3"], "mp3": ["leaf"]}  ## Mesh AP links
print("hops root->leaf:", hops(mesh, "root", "leaf"))  ## 3'''

M_11_3 = {
    "id": "11.3",
    "title": "Coding Round",
    "hours": 3,
    "summary": "How to run a live coding round (clarify, example, brute force, optimise, test), the half-dozen patterns that solve most automation-flavoured problems, and eight domain problems with solutions and complexity.",
    "concepts": [
        {
            "title": "The approach, shown on one problem",
            "concept": "A reliable five-step routine: (1) clarify inputs, outputs and edge cases and work one example by hand; (2) write the obviously-correct brute force; (3) optimise, naming the time and space complexity; (4) test with edge cases and, if time allows, random inputs checked against the brute force; (5) talk the whole time. The problem: given one RSSI sample per second, find the longest stretch at or above -70 dBm.",
            "why": "Interviewers score the process as much as the answer. A correct brute force plus a clear optimisation beats a half-finished clever solution, and checking against the brute force on random inputs catches off-by-one errors before the interviewer does.",
            "syntax": "assert fast(data) == brute(data), data   # compare on random inputs",
            "code": APPROACH,
            "under": "The optimisation works because the longest run ending at position i depends only on the run ending at i-1, so one variable replaces the inner loop. That observation (what does the answer at i need from i-1?) is the core of most linear-time improvements.",
            "gotchas": [],
            "best": "State complexity for both versions, keep the brute force as a test oracle, seed random tests so failures reproduce, and finish by listing what you'd add with more time (input validation, streaming input, type hints).",
        },
        {
            "title": "The pattern toolkit",
            "concept": "Most coding-round problems in automation interviews reduce to a few patterns: hash-map counting (`Counter`), top-k with a heap, interval merging after sorting, binary search on monotonic data (`bisect`), and BFS for shortest paths in unweighted graphs. Each appears here with a lab-flavoured example and its complexity.",
            "why": "Recognising the pattern is most of the work. \"Most common error\", \"top 3 APs by throughput\", \"merge bench reservations\", \"first attenuation where throughput drops below KPI\", and \"fewest hops to the root AP in a mesh\" are the same five tools in different clothes.",
            "syntax": "Counter(xs).most_common(k)\nheapq.nlargest(k, items, key=...)\nbisect.bisect_left(sorted_list, x)\ndeque() + visited set  # BFS",
            "code": PATTERNS,
            "under": "`heapq.nlargest(k, ...)` keeps a heap of size k, so it is O(n log k), better than sorting everything when k is small. `bisect` needs ascending data, which is why the falling throughput curve is negated first. BFS explores in rings of equal distance, which is why the first time it reaches the target is the shortest path; with weighted links you'd need Dijkstra (a heap instead of a queue).",
            "gotchas": [],
            "best": "Reach for the standard library first (`collections`, `heapq`, `bisect`, `itertools`): it is correct, fast, and shows you know the language. Name the pattern out loud when you spot it.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Normalise MAC addresses: accept `AA-BB-CC-DD-EE-FF`, `aabb.ccdd.eeff` and `aa:bb:cc:dd:ee:ff`, return lower-case colon form, and raise `ValueError` for anything else.",
            "solution": "Strip separators, validate 12 hex digits, re-insert colons. O(n) in the string length.",
            "solution_code": """import re

def normalise_mac(text):
    digits = re.sub(r"[-:.]", "", text).lower()
    if not re.fullmatch(r"[0-9a-f]{12}", digits):
        raise ValueError(f"not a MAC address: {text!r}")
    return ":".join(digits[i:i + 2] for i in range(0, 12, 2))

for raw in ("AA-BB-CC-DD-EE-FF", "aabb.ccdd.eeff", "aa:bb:cc:dd:ee:ff"):
    print(normalise_mac(raw))
try:
    normalise_mac("aa:bb:cc:dd:ee")
except ValueError as e:
    print(e)""",
        },
        {
            "level": "Easy",
            "prompt": "Given client MACs, find the top 3 vendors by OUI (first three octets) using a lookup table; unknown OUIs count as \"unknown\".",
            "solution": "Counter over the mapped OUI; O(n) to count plus O(u log u) for most_common over u vendors.",
            "solution_code": """from collections import Counter

OUI = {"a4:5e:60": "Apple", "f0:18:98": "Apple", "3c:84:6a": "TP-Link", "70:3a:cb": "Google"}
clients = ["a4:5e:60:11:22:33", "f0:18:98:44:55:66", "70:3a:cb:00:00:09", "a4:5e:60:aa:bb:cc",
           "02:00:00:00:00:01", "3c:84:6a:12:34:56", "70:3a:cb:00:00:10"]
vendors = Counter(OUI.get(mac[:8], "unknown") for mac in clients)
print(vendors.most_common(3))""",
        },
        {
            "level": "Medium",
            "prompt": "Bench reservations arrive as (start, end, owner). Detect every pair of reservations that overlap on the same bench so the scheduler can reject them.",
            "solution": "Group by bench, sort by start, sweep while keeping the reservations that haven't ended yet. O(n log n) for the sort plus the number of reported overlaps.",
            "solution_code": """from collections import defaultdict

bookings = [("lab-07", 9, 11, "ana"), ("lab-07", 10, 12, "raj"), ("lab-07", 12, 13, "li"),
            ("lab-12", 9, 17, "nightly"), ("lab-12", 16, 18, "ana"), ("lab-07", 10.5, 10.75, "sam")]
by_bench = defaultdict(list)
for bench, start, end, who in bookings:
    by_bench[bench].append((start, end, who))
for bench, items in sorted(by_bench.items()):
    active = []
    for start, end, who in sorted(items):
        active = [a for a in active if a[1] > start]
        for a_start, a_end, a_who in active:
            print(f"{bench}: {a_who} [{a_start}-{a_end}] overlaps {who} [{start}-{end}]")
        active.append((start, end, who))""",
        },
        {
            "level": "Medium",
            "prompt": "Implement an LRU cache for device sessions with capacity N: `get(host)` returns the session or None and marks it recently used; `put(host, session)` evicts the least recently used one when full. Both O(1).",
            "solution": "`OrderedDict` keeps order and supports O(1) `move_to_end` and `popitem(last=False)`.",
            "solution_code": """from collections import OrderedDict

class SessionCache:
    def __init__(self, capacity):
        self.capacity, self.items = capacity, OrderedDict()

    def get(self, host):
        if host not in self.items:
            return None
        self.items.move_to_end(host)
        return self.items[host]

    def put(self, host, session):
        self.items[host] = session
        self.items.move_to_end(host)
        if len(self.items) > self.capacity:
            evicted, _ = self.items.popitem(last=False)
            print("evicted", evicted)

cache = SessionCache(2)
cache.put("wlc-1", "s1")
cache.put("wlc-2", "s2")
cache.get("wlc-1")
cache.put("wlc-3", "s3")
print(list(cache.items))""",
        },
        {
            "level": "Medium",
            "prompt": "Throughput samples arrive once per second. Report every 5-second window whose average drops below 80% of the run's overall median (a dip detector), merging consecutive bad windows into one dip.",
            "solution": "Sliding window sum (O(n)) compared with a precomputed median; merge adjacent hits.",
            "solution_code": """import statistics

samples = [930, 925, 940, 935, 928, 700, 610, 590, 640, 720, 910, 932, 929, 931, 936]
threshold = 0.8 * statistics.median(samples)
k, total, dips = 5, sum(samples[:5]), []
for start in range(len(samples) - k + 1):
    if start:
        total += samples[start + k - 1] - samples[start - 1]
    if total / k < threshold:
        if dips and start <= dips[-1][1] + 1:
            dips[-1][1] = start + k - 1
        else:
            dips.append([start, start + k - 1])
print(f"threshold {threshold:.0f} Mbps; dips at seconds:", dips)""",
        },
        {
            "level": "Hard",
            "prompt": "Write a `retry` decorator with exponential backoff and jitter, retrying only on given exception types, with the sleep function injectable so tests run instantly. Show it recovering from two failures.",
            "solution": "A decorator factory; delays are `base * 2**attempt` plus jitter, capped; re-raise after the last attempt. Injecting `sleep` and the random source makes it deterministic in tests.",
            "solution_code": """import functools
import random

def retry(on=(Exception,), attempts=4, base=0.5, cap=8.0, sleep=None, rng=random.Random(1)):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(attempts):
                try:
                    return fn(*args, **kwargs)
                except on as e:
                    if attempt == attempts - 1:
                        raise
                    delay = min(cap, base * 2 ** attempt) * (0.5 + rng.random() / 2)
                    print(f"attempt {attempt + 1} failed ({e}); retrying in {delay:.2f}s")
                    (sleep or __import__("time").sleep)(delay)
        return wrapper
    return deco

calls = {"n": 0}

@retry(on=(ConnectionError,), sleep=lambda s: None)
def connect():
    calls["n"] += 1
    if calls["n"] < 3:
        raise ConnectionError("refused")
    return "connected"

print(connect(), "after", calls["n"], "calls")""",
        },
        {
            "level": "Hard",
            "prompt": "A mesh network has weighted links (cost = airtime per hop). Find the cheapest path from the root AP to every node, and print the path to one leaf.",
            "solution": "Dijkstra with a heap: O((V + E) log V). Keep a `prev` map to rebuild paths.",
            "solution_code": """import heapq

links = {"root": {"mp1": 1, "mp2": 4}, "mp1": {"mp2": 1, "mp3": 6}, "mp2": {"mp3": 2}, "mp3": {"leaf": 1}}
dist, prev, heap = {"root": 0}, {}, [(0, "root")]
while heap:
    d, node = heapq.heappop(heap)
    if d > dist[node]:
        continue
    for nxt, cost in links.get(node, {}).items():
        if d + cost < dist.get(nxt, float("inf")):
            dist[nxt], prev[nxt] = d + cost, node
            heapq.heappush(heap, (d + cost, nxt))
path, node = [], "leaf"
while node in prev or node == "root":
    path.append(node)
    if node == "root":
        break
    node = prev[node]
print(dist)
print(" -> ".join(reversed(path)))""",
        },
        {
            "level": "Hard",
            "prompt": "Token-bucket rate limiter for an API client: allow bursts up to `capacity`, refill at `rate` tokens per second, and return whether each request may go now. Make time injectable and show 10 requests at 0.1 s intervals with capacity 3 and rate 2/s.",
            "solution": "Refill lazily from the elapsed time on each call; O(1) per request.",
            "solution_code": """class TokenBucket:
    def __init__(self, capacity, rate, now):
        self.capacity, self.rate, self.tokens, self.last = capacity, rate, capacity, now

    def allow(self, now):
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

bucket = TokenBucket(capacity=3, rate=2, now=0.0)
print(["go" if bucket.allow(round(i * 0.1, 1)) else "wait" for i in range(10)])""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "You've written a working O(n^2) solution. How do you look for a faster one?", "a": "Ask what work is repeated: can a hash map replace an inner search (O(1) lookups), can sorting enable two pointers or binary search, can a running value carry the answer from i-1 to i, or can a heap maintain the best k? Then state the new complexity and test against the brute force.", "follow": "When is O(n^2) acceptable? (Small, bounded n, such as 8 radios or 20 benches: say so and move on.)"},
        {"level": "Intermediate", "q": "How do you test your solution in a live round?", "a": "Walk through the worked example, then edge cases (empty, one element, all equal, maximum values, invalid input), then if time permits compare with a brute force on seeded random inputs.", "follow": "What do you do when a test fails? (Shrink the failing input, trace it, fix, rerun all cases.)"},
        {"level": "Advanced", "q": "Implement an LRU cache in O(1): what data structures?", "a": "A hash map for lookup plus a doubly linked list for recency; in Python `OrderedDict` provides both (`move_to_end`, `popitem(last=False)`), and `functools.lru_cache` covers function memoisation.", "follow": "How would you make it thread-safe? (A lock around get/put, or per-shard caches.)"},
    ],
    "quiz": [
        {"q": "`heapq.nlargest(k, items)` is...", "options": ["O(n)", "O(n log k)", "O(n log n)", "O(k^2)"], "answer": 1, "why": "Heap of size k."},
        {"q": "Shortest path with weighted links needs...", "options": ["BFS", "DFS", "Dijkstra", "Binary search"], "answer": 2, "why": "BFS only for unweighted."},
        {"q": "`bisect` requires the list to be...", "options": ["Unique", "Sorted ascending", "Numeric", "Short"], "answer": 1, "why": "Binary search."},
    ],
    "cards": [
        {"front": "Coding round routine", "back": "Clarify + example → brute force → optimise (state O) → test → talk throughout"},
        {"front": "Five patterns", "back": "Counter, heap top-k, sort + merge intervals, bisect, BFS/Dijkstra"},
        {"front": "Test oracle", "back": "Keep the brute force; compare on seeded random inputs"},
    ],
}
