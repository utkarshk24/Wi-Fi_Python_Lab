"""Phase 3 content: modules 3.11-3.15."""

THREADS_NOTE = "uses threads or processes, which the in-browser runner doesn't support"

M_3_11 = {
    "id": "3.11",
    "title": "Type Hints & mypy",
    "hours": 3,
    "summary": "Annotating functions and data, unions and Optional, generics, TypedDict, Literal, Callable and Final, narrowing and exhaustiveness, and catching bugs with mypy before a long run.",
    "concepts": [
        {
            "title": "Annotations, generics and typed data",
            "concept": "Type hints describe what a function accepts and returns: `def f(x: int) -> str`. `X | None` (or `Optional[X]`) means \"X or None\". Built-in containers take parameters: `list[int]`, `dict[str, float]`. `Literal[\"5G\", \"6G\"]` restricts values; `TypedDict` describes the keys and value types of a dict; `Callable[[int], int]` describes a function argument; `Final` marks a constant. Python 3.12 adds compact generic syntax: `def first[T](items: list[T]) -> T | None`. **Hints are not enforced at runtime**; static checkers such as mypy enforce them.",
            "why": "A framework's public API (drivers, fixtures, result types) is used by many people. Hints document it in a machine-checkable way, so passing `\"6g\"` where a band is expected, or forgetting that a lookup can return None, is caught in CI instead of at hour five of a regression.",
            "syntax": "def strongest(rows: list[Row], band: Band | None = None) -> Row | None: ...\nBand = Literal[\"2G\", \"5G\", \"6G\"]\nclass Row(TypedDict):\n    mac: str\n    rssi: int\nMAX_TX: Final = 30\ndef apply(xs: list[int], fn: Callable[[int], int]) -> list[int]: ...\ndef first[T](items: list[T]) -> T | None: ...   # 3.12+",
            "code": """from typing import Callable, Final, Literal, TypedDict  ## Typing constructs used below

Band = Literal["2G", "5G", "6G"]  ## A type alias: only these three strings are valid
MAX_TX_DBM: Final = 30  ## Final: checkers flag any reassignment


class StationRow(TypedDict):  ## Describes a dict's keys and value types (no runtime class change)
    mac: str  ## Required key with a str value
    rssi: int  ## Required key with an int value
    band: Band  ## Value must be one of the Literal strings


def strongest(rows: list[StationRow], band: Band | None = None) -> StationRow | None:  ## Optional filter; may return None
    candidates = [r for r in rows if band is None or r["band"] == band]  ## No filter when band is None
    return max(candidates, key=lambda r: r["rssi"], default=None)  ## default=None covers an empty list


def apply(values: list[int], fn: Callable[[int], int]) -> list[int]:  ## fn takes an int and returns an int
    return [fn(v) for v in values]  ## Call it on each value


def first[T](items: list[T]) -> T | None:  ## 3.12 generic syntax: T is whatever the list holds
    return items[0] if items else None  ## Returns the same type the list contains


def main() -> None:
    rows: list[StationRow] = [  ## A plain list of plain dicts; the hint is for the checker
        {"mac": "aa:01", "rssi": -61, "band": "5G"},  ## Matches StationRow
        {"mac": "aa:02", "rssi": -48, "band": "6G"},  ## Matches StationRow
    ]
    print(strongest(rows), strongest(rows, "5G"), strongest([], "6G"))  ## Overall, filtered, and the None case
    print(apply([-54, -61], abs), first(["ap-1", "ap-2"]), first([]))  ## Callable and generic in use
    print(type(rows[0]).__name__, MAX_TX_DBM)  ## TypedDict values are still ordinary dicts at runtime
    print(strongest([{"mac": 1, "rssi": "oops", "band": "9G"}]))  ## Wrong types run anyway: hints are NOT checked at runtime


if __name__ == "__main__":
    main()""",
            "under": "Annotations are stored on objects (`func.__annotations__`) and otherwise ignored by the interpreter, so they cost almost nothing at runtime. Tools read them: mypy and pyright for static checking, IDEs for completion, dataclasses and pydantic for field definitions. `TypedDict` and `Literal` exist only for checkers; at runtime the data is a normal dict and a normal string.",
            "gotchas": [
                {
                    "title": "Assuming hints validate input",
                    "note": "Nothing stops a wrong type at runtime. Validate data from outside (config files, CLI, APIs) explicitly, or with pydantic (Module 4.4).",
                    "wrong": """def set_channel(channel: int) -> str:
    return f"ch{channel + 4}"

print(set_channel("36"))""",
                    "fixed": """def set_channel(channel: int) -> str:
    if not isinstance(channel, int):
        raise TypeError(f"channel must be int, got {type(channel).__name__}")
    return f"ch{channel + 4}"

try:
    set_channel("36")
except TypeError as err:
    print("TypeError:", err)""",
                }
            ],
            "best": "Annotate every public function and data class in the framework, use `X | None` honestly whenever a value can be missing, and prefer precise types (`Literal`, `TypedDict`, enums, dataclasses) over `dict` and `str`. Validate external input at the boundary; trust the types inside.",
        },
        {
            "title": "Narrowing, exhaustiveness and mypy",
            "concept": "Checkers **narrow** a union type after a test: after `if raw is None: return`, `raw` can't be None; after `isinstance(raw, str)` it's a str. `typing.assert_never(x)` marks code that should be unreachable, so mypy reports a `match` or `if` chain that forgets a case, and at runtime it raises if reached. `reveal_type(x)` asks the checker (and, since 3.11, the runtime) what type it sees. You run mypy as a separate command, typically `mypy --strict yourpackage/` in pre-commit and CI.",
            "why": "Adding a new verdict such as `ERROR` to a Literal should break the build until every place that maps verdicts to colours or exit codes handles it. That's exactly what exhaustiveness checking gives you.",
            "syntax": "if raw is None: ...           # narrows away None\nif isinstance(raw, str): ...  # narrows to str\ncase _: assert_never(v)       # exhaustive match\n\n$ mypy --strict wifitest/\nwifitest/sweep.py:12: error: Argument 1 to \"set_db\" of \"Attenuator\" has incompatible type \"str\"; expected \"int\"  [arg-type]",
            "code": """from typing import Literal, assert_never, reveal_type  ## 3.11+ runtime helpers

Verdict = Literal["PASS", "FAIL", "SKIP"]  ## The closed set of verdicts


def colour(v: Verdict) -> str:  ## Map each verdict to a report colour
    match v:  ## Pattern matching on the literal values
        case "PASS":  ## First case
            return "green"  ## Passed
        case "FAIL":  ## Second case
            return "red"  ## Failed
        case "SKIP":  ## Third case
            return "grey"  ## Skipped
        case _:  ## Unreachable if every Literal value is handled
            assert_never(v)  ## mypy errors here if a case is missing; at runtime it raises


def parse_rssi(raw: str | int | None) -> int:  ## Accepts three possible input types
    if raw is None:  ## After this branch, mypy knows raw is str | int
        return -100  ## Treat missing as no signal
    if isinstance(raw, str):  ## Inside: raw is str
        raw = int(raw.removesuffix(" dBm"))  ## Convert text like "-54 dBm"
    return raw  ## Here mypy knows raw is int


def main() -> None:
    print([colour(v) for v in ("PASS", "FAIL", "SKIP")])  ## Every case handled
    print(parse_rssi("-54 dBm"), parse_rssi(-61), parse_rssi(None))  ## All three input types
    reveal_type(parse_rssi(None))  ## Prints the runtime type to stderr; mypy prints its inferred type
    try:  ## A value outside the Literal (mypy would reject this call)
        colour("ERROR")  # type: ignore[arg-type]  ## Silences the checker for this deliberate mistake
    except AssertionError as err:  ## assert_never raises at runtime
        print("AssertionError:", err)  ## Shows the unexpected value


if __name__ == "__main__":
    main()""",
            "under": "mypy builds a type for every expression and tracks how conditions narrow unions along each code path. `assert_never` accepts only the type `Never`; if any value can still reach it (because a case is missing), the argument's type isn't Never and mypy reports an error. At runtime, `reveal_type` just prints `Runtime type is '...'` to stderr and returns its argument.",
            "gotchas": [
                {
                    "title": "Forgetting that a lookup can return None",
                    "note": "dict.get returns `X | None`. Without a check, the None crashes later; mypy would flag the attribute access on an Optional.",
                    "wrong": """bench_ips: dict[str, str] = {"ap-1": "10.0.0.11"}
ip = bench_ips.get("ap-9")
print(ip.split("."))""",
                    "fixed": """bench_ips: dict[str, str] = {"ap-1": "10.0.0.11"}
ip = bench_ips.get("ap-9")
if ip is None:
    print("ap-9 is not in the testbed file")
else:
    print(ip.split("."))""",
                }
            ],
            "best": "Run mypy (or pyright) in pre-commit and CI with strict settings on new code, and tighten older modules gradually with per-module overrides. Use `assert_never` in every dispatch over a Literal or Enum, and keep `# type: ignore[code]` comments rare and specific.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Annotate `mean(values)` that returns a float or None for an empty list, and call it both ways.",
            "solution": "The return type is `float | None`.",
            "solution_code": """def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


print(mean([910.2, 905.7]), mean([]))""",
        },
        {
            "level": "Medium",
            "prompt": "Define a TypedDict `IperfSummary` (mbps: float, retransmits: int, protocol: Literal['TCP', 'UDP']) and a function that builds one from an iperf3 JSON dict.",
            "solution": "TypedDict is constructed like a normal dict; the hint guides the checker.",
            "solution_code": """from typing import Literal, TypedDict


class IperfSummary(TypedDict):
    mbps: float
    retransmits: int
    protocol: Literal["TCP", "UDP"]


def summarize(data: dict) -> IperfSummary:
    return {
        "mbps": round(data["end"]["sum_received"]["bits_per_second"] / 1e6, 1),
        "retransmits": data["end"]["sum_sent"].get("retransmits", 0),
        "protocol": data["start"]["test_start"]["protocol"],
    }


raw = {"start": {"test_start": {"protocol": "TCP"}}, "end": {"sum_sent": {"retransmits": 4}, "sum_received": {"bits_per_second": 941_300_000}}}
print(summarize(raw))""",
        },
        {
            "level": "Hard",
            "prompt": "Write a generic `group_by[K, V](items: list[V], key: Callable[[V], K]) -> dict[K, list[V]]` using 3.12 syntax, and use it to group stations by band.",
            "solution": "Two type parameters: K for keys, V for items.",
            "solution_code": """from typing import Callable


def group_by[K, V](items: list[V], key: Callable[[V], K]) -> dict[K, list[V]]:
    groups: dict[K, list[V]] = {}
    for item in items:
        groups.setdefault(key(item), []).append(item)
    return groups


stations = [("aa:01", "5G"), ("aa:02", "6G"), ("aa:03", "5G")]
print(group_by(stations, key=lambda s: s[1]))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Does Python enforce type hints?", "a": "No. The interpreter stores them but doesn't check them. Static checkers (mypy, pyright) and some libraries (pydantic, dataclasses for field discovery) use them.", "follow": "Then why use them? (Early bug detection in CI, better IDE help, and self-documenting APIs.)"},
        {"level": "Intermediate", "q": "Optional[X] vs X | None?", "a": "They mean the same thing: X or None. The | syntax works in annotations from Python 3.10. Optional doesn't mean 'optional argument'; a parameter is optional only if it has a default.", "follow": "Is `def f(x: int = None)` correct? (No; it should be `int | None = None`.)"},
        {"level": "Intermediate", "q": "TypedDict vs dataclass?", "a": "TypedDict types existing dict-shaped data (JSON, API responses) without changing it at runtime. A dataclass creates a real class with attributes, methods and generated __init__/__eq__. Use TypedDict at the JSON boundary and dataclasses for domain objects.", "follow": "Can TypedDict keys be optional? (Yes: NotRequired[...] or total=False.)"},
        {"level": "Advanced", "q": "What is type narrowing, and how does assert_never help?", "a": "The checker refines a union after conditions like `is None` or `isinstance`. assert_never(x) only accepts Never, so if any case of a Literal/Enum/union isn't handled, x isn't Never there and mypy reports an error, making dispatch code exhaustive.", "follow": "What does assert_never do at runtime? (Raises AssertionError with the unexpected value.)"},
    ],
    "quiz": [
        {"q": "What happens when you call `f(x: int)` with a str?", "options": ["TypeError from the interpreter", "It runs; only checkers complain", "SyntaxError", "Auto-conversion"], "answer": 1, "why": "Hints aren't enforced at runtime."},
        {"q": "`int | None` means...", "options": ["int, required", "int or None", "Optional argument", "Any"], "answer": 1, "why": "A union with None."},
        {"q": "Which describes dict keys and value types?", "options": ["Literal", "TypedDict", "Final", "Callable"], "answer": 1, "why": "TypedDict types dict shapes."},
        {"q": "Which flags a missing case in a match over a Literal?", "options": ["reveal_type", "assert_never", "cast", "Final"], "answer": 1, "why": "Exhaustiveness checking."},
        {"q": "How do you run the type checker?", "options": ["python -m typing", "mypy package/", "pytest --types", "Automatically on import"], "answer": 1, "why": "mypy is a separate tool."},
    ],
    "cards": [
        {"front": "Hints at runtime", "back": "Not enforced; checked by mypy/pyright."},
        {"front": "Maybe-missing value", "back": "`X | None` (= Optional[X])"},
        {"front": "Restrict to specific strings", "back": "`Literal['5G', '6G']`"},
        {"front": "Typed dict shape", "back": "`class Row(TypedDict): mac: str`"},
        {"front": "Exhaustive dispatch", "back": "`case _: assert_never(v)`"},
        {"front": "3.12 generic function", "back": "`def first[T](xs: list[T]) -> T | None`"},
    ],
}


M_3_12 = {
    "id": "3.12",
    "title": "Memory Model, GC & the GIL",
    "hours": 2,
    "summary": "Reference counting and when objects are freed, cyclic garbage collection, weak references, leaks in long-running monitors, and what the GIL means for threads.",
    "concepts": [
        {
            "title": "Reference counting, cycles and weak references",
            "concept": "CPython frees most objects by **reference counting**: every object counts the references to it and is destroyed the moment the count reaches zero. Objects that reference each other in a **cycle** keep each other's counts above zero, so a separate **cyclic garbage collector** (`gc`) finds and frees unreachable cycles periodically. A **weak reference** (`weakref.ref`, `WeakSet`, `WeakValueDictionary`) points at an object without keeping it alive.",
            "why": "A soak-test monitor that registers callbacks or caches device sessions in a global list can quietly hold every object it ever saw. Knowing when objects die, and using weak references for registries, is how a 24-hour run avoids growing to gigabytes.",
            "syntax": "sys.getrefcount(obj)       # (includes the call's own reference)\nr = weakref.ref(obj); r()  # the object, or None once freed\ngc.collect()               # run the cycle collector now\nweakref.WeakSet()          # members don't stay alive because of the set",
            "code": """import gc  ## The cyclic garbage collector
import sys  ## getrefcount and getsizeof
import weakref  ## References that don't keep objects alive


class Session:  ## Stands in for an SSH session object
    def __init__(self, host: str) -> None:  ## Minimal state
        self.host = host  ## Which device
        self.peer: "Session | None" = None  ## Used to build a reference cycle

    def __repr__(self) -> str:  ## Readable output
        return f"Session({self.host})"  ## Host only


def main() -> None:
    s = Session("ap-1")  ## One reference: the name s
    base = sys.getrefcount(s)  ## Current count (getrefcount adds its own temporary reference)
    alias = s  ## A second name for the object
    print(sys.getrefcount(s) - base)  ## One more reference
    del alias  ## Remove that name
    print(sys.getrefcount(s) - base)  ## Back to the baseline
    r = weakref.ref(s)  ## A weak reference doesn't increase the count
    print(r() is s)  ## Calling it returns the object while it's alive
    del s  ## The last strong reference is gone...
    print(r())  ## ...so refcounting freed it immediately: None
    a, b = Session("ap-1"), Session("ap-2")  ## Two new sessions
    a.peer, b.peer = b, a  ## Each references the other: a cycle
    ra = weakref.ref(a)  ## Watch a without keeping it alive
    del a, b  ## No names left, but the cycle keeps both counts at 1
    print(ra() is not None)  ## Still alive: refcounting alone can't free a cycle
    gc.collect()  ## The cycle collector finds unreachable cycles
    print(ra())  ## Now freed: None
    print(sys.getsizeof([]) < sys.getsizeof([1, 2, 3]))  ## getsizeof reports an object's own memory (not what it points to)


if __name__ == "__main__":
    main()""",
            "under": "Every CPython object header holds `ob_refcnt`. Assignments, function arguments and container slots increment it; leaving scope, `del` and reassignment decrement it. Container objects are also tracked in GC generations; when allocations exceed a threshold, the collector scans a generation, subtracts references that come from inside the tracked set, and frees groups whose remaining count is zero. Objects with `__del__` in cycles are handled too since Python 3.4.",
            "gotchas": [
                {
                    "title": "A registry that keeps everything alive",
                    "note": "A plain list holds strong references, so every session ever registered stays in memory. A WeakSet lets them go when nothing else uses them.",
                    "wrong": """import weakref

class Session:
    pass

registry = []
s = Session()
registry.append(s)
r = weakref.ref(s)
del s
print("still alive:", r() is not None)""",
                    "fixed": """import weakref

class Session:
    pass

registry = weakref.WeakSet()
s = Session()
registry.add(s)
r = weakref.ref(s)
del s
print("still alive:", r() is not None, "| registry size:", len(registry))""",
                }
            ],
            "best": "Let objects go out of scope naturally; avoid global lists and caches that grow forever. Use `WeakSet`/`WeakValueDictionary` for registries of live objects, bound caches with `maxsize`, and use `tracemalloc` (Module 3.15) to find what's growing in long runs.",
        },
        {
            "title": "The GIL: CPU-bound vs I/O-bound threads",
            "local_only": THREADS_NOTE,
            "concept": "In the standard CPython build, the **Global Interpreter Lock** lets only one thread execute Python bytecode at a time. Threads still help with **I/O-bound** work (SSH, HTTP, sleeping on devices), because a thread waiting on I/O releases the GIL. They don't speed up **CPU-bound** Python code; for that you use processes (Module 3.13) or libraries that release the GIL (numpy). Python 3.13 also ships an optional **free-threaded** build (3.13t) without the GIL, still experimental.",
            "why": "Polling 40 APs over SSH in threads is fast; parsing 200 pcaps in threads isn't. Choosing threads, processes or asyncio correctly is a classic interview topic and a real performance decision in test frameworks.",
            "syntax": "ThreadPoolExecutor(max_workers=n).map(io_bound_fn, items)    # good\nThreadPoolExecutor(...).map(cpu_bound_fn, items)               # no speed-up\nProcessPoolExecutor(...).map(cpu_bound_fn, items)              # uses cores\nsys._is_gil_enabled()   # 3.13+",
            "code": """import sys  ## To ask whether the GIL is enabled
import time  ## sleep and perf_counter
from concurrent.futures import ThreadPoolExecutor  ## A pool of worker threads


def io_work(seconds: float) -> float:  ## Simulates waiting on a device (SSH, HTTP, serial)
    time.sleep(seconds)  ## Sleeping releases the GIL
    return seconds  ## Nothing to compute


def cpu_work(n: int) -> int:  ## Pure Python computation
    total = 0  ## Accumulator
    for i in range(n):  ## Holds the GIL the whole time
        total += i * i  ## Arithmetic in bytecode
    return total  ## Result


def timed(fn) -> float:  ## Measure how long fn() takes
    t0 = time.perf_counter()  ## Start
    fn()  ## Run
    return time.perf_counter() - t0  ## Elapsed seconds


def main() -> None:
    gil = getattr(sys, "_is_gil_enabled", lambda: True)()  ## 3.13+ can report it; older versions always have the GIL
    print("GIL enabled:", gil)  ## True on the standard build
    with ThreadPoolExecutor(max_workers=4) as pool:  ## Four worker threads
        serial_io = timed(lambda: [io_work(0.2) for _ in range(4)])  ## 4 waits one after another: about 0.8 s
        threaded_io = timed(lambda: list(pool.map(io_work, [0.2] * 4)))  ## 4 waits overlapping: about 0.2 s
        serial_cpu = timed(lambda: [cpu_work(300_000) for _ in range(4)])  ## 4 computations in a row
        threaded_cpu = timed(lambda: list(pool.map(cpu_work, [300_000] * 4)))  ## Same work in 4 threads
    print("I/O-bound speed-up with threads:", "yes" if serial_io / threaded_io > 2.5 else "no")  ## Waiting overlaps
    print("CPU-bound speed-up with threads:", "yes" if serial_cpu / threaded_cpu > 1.5 else "no")  ## The GIL serialises bytecode


if __name__ == "__main__":
    main()""",
            "under": "A thread holding the GIL is asked to release it periodically (every 5 ms by default, `sys.getswitchinterval()`) and always releases it around blocking I/O and `time.sleep`. Many C extensions (zlib, hashlib, numpy, most socket and file operations) release it while they work, so those parts can run in parallel. The free-threaded build replaces the GIL with finer-grained locking at some single-thread cost.",
            "gotchas": [],
            "best": "Use threads (or asyncio) for many concurrent device operations that mostly wait; use processes for CPU-heavy parsing and analysis. Measure before and after: the GIL is a reason to test, not a reason to guess.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Show with a weak reference that an object is freed as soon as its last name is deleted.",
            "solution": "weakref.ref returns None after the object is collected.",
            "solution_code": """import weakref


class Capture:
    pass


c = Capture()
r = weakref.ref(c)
print(r() is c)
del c
print(r())""",
        },
        {
            "level": "Medium",
            "prompt": "Build a cache of device sessions keyed by host with WeakValueDictionary, and show that an entry disappears once the session isn't used anywhere else.",
            "solution": "WeakValueDictionary drops entries whose values are no longer strongly referenced.",
            "solution_code": """import weakref


class Session:
    def __init__(self, host):
        self.host = host


cache = weakref.WeakValueDictionary()
s1 = Session("ap-1")
cache["ap-1"] = s1
cache["ap-2"] = Session("ap-2")
print(sorted(cache.keys()))""",
        },
        {
            "level": "Hard",
            "prompt": "Create a reference cycle between a Bench and its AP objects (each AP points back to its bench), confirm it survives `del`, then break it by making the back-reference weak.",
            "solution": "Store the parent as weakref.ref(bench) in each child; then refcounting frees everything.",
            "solution_code": """import gc
import weakref


class Bench:
    def __init__(self):
        self.aps = []


class AP:
    def __init__(self, bench, weak):
        self._bench = weakref.ref(bench) if weak else bench
        bench.aps.append(self)


for weak in (False, True):
    gc.disable()
    b = Bench()
    AP(b, weak); AP(b, weak)
    rb = weakref.ref(b)
    del b
    print("weak back-ref" if weak else "strong back-ref", "-> bench alive after del:", rb() is not None)
    gc.enable()
    gc.collect()""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "How does Python free memory?", "a": "Mainly by reference counting: an object is destroyed as soon as its count drops to zero. A generational cyclic garbage collector additionally finds groups of objects that only reference each other and frees them.", "follow": "Why can't refcounting free cycles? (Each object in the cycle still has a reference from another one.)"},
        {"level": "Intermediate", "q": "What is the GIL?", "a": "The Global Interpreter Lock in standard CPython allows only one thread at a time to execute Python bytecode. It simplifies memory management (refcounts) but prevents CPU-bound Python threads from running in parallel. Threads still overlap I/O waits.", "follow": "What changed in 3.13? (An optional experimental free-threaded build without the GIL.)"},
        {"level": "Advanced", "q": "How would you find a memory leak in a long-running test monitor?", "a": "Measure growth over time (RSS, tracemalloc snapshots), compare snapshots to see which lines allocate the growing objects, and look for unbounded containers, caches without limits, and callbacks or registries holding strong references. Fix with bounded caches, weak references or explicit cleanup.", "follow": "Which stdlib tool compares memory snapshots? (tracemalloc.take_snapshot().compare_to().)"},
        {"level": "Advanced", "q": "Threads, processes or asyncio for checking 500 APs over SSH?", "a": "The work is I/O-bound, so asyncio (with asyncssh) or a thread pool both work well; asyncio scales to many connections with one thread and explicit concurrency limits. Processes add overhead and only help when each check does heavy CPU work.", "follow": "And parsing 500 pcaps? (Processes, since it's CPU-bound.)"},
    ],
    "quiz": [
        {"q": "When is an object without cycles freed?", "options": ["At program exit", "When gc.collect runs", "When its refcount hits zero", "Every 5 ms"], "answer": 2, "why": "Refcounting frees it immediately."},
        {"q": "What does a weak reference do?", "options": ["Copies the object", "Refers without keeping it alive", "Locks it", "Makes it immutable"], "answer": 1, "why": "It doesn't increase the refcount."},
        {"q": "Threads speed up which work under the GIL?", "options": ["CPU-bound Python loops", "I/O waits", "Neither", "Both equally"], "answer": 1, "why": "Waiting releases the GIL."},
        {"q": "Which frees reference cycles?", "options": ["del", "The gc module's collector", "weakref", "sys.getrefcount"], "answer": 1, "why": "Cycle detection is gc's job."},
        {"q": "Best fix for a registry that keeps sessions alive?", "options": ["gc.disable()", "weakref.WeakSet", "A bigger list", "sys.setrecursionlimit"], "answer": 1, "why": "Members can be freed normally."},
    ],
    "cards": [
        {"front": "Main memory mechanism", "back": "Reference counting; the gc module handles cycles."},
        {"front": "Weak reference", "back": "weakref.ref(obj)() returns the object or None."},
        {"front": "GIL in one line", "back": "One thread runs Python bytecode at a time (standard CPython)."},
        {"front": "Threads help with...", "back": "I/O-bound work; use processes for CPU-bound."},
    ],
}


M_3_13 = {
    "id": "3.13",
    "title": "threading, multiprocessing & concurrent.futures",
    "hours": 3,
    "summary": "Running device checks in parallel threads, locks and race conditions, collecting results as they finish, and using process pools for CPU-heavy parsing.",
    "concepts": [
        {
            "title": "Thread pools, as_completed and locks",
            "local_only": THREADS_NOTE,
            "concept": "`concurrent.futures.ThreadPoolExecutor` runs functions in a pool of threads. `submit()` returns a **Future**; `as_completed()` yields futures as they finish, and `future.result()` returns the value or **re-raises** the exception from the worker. Threads share memory, so code that updates shared state must protect it with a `threading.Lock` (`with lock:`), otherwise concurrent read-modify-write steps lose updates: a **race condition**.",
            "why": "A bench health check that SSHes into 40 APs one by one takes minutes; in a pool of 10 threads it takes seconds. Handling each result (and each failure) as it completes gives a live report instead of waiting for the slowest device.",
            "syntax": "with ThreadPoolExecutor(max_workers=10) as pool:\n    futures = {pool.submit(check, ap): ap for ap in aps}\n    for fut in as_completed(futures):\n        ap = futures[fut]\n        fut.result()      # value, or re-raises\n\nlock = threading.Lock()\nwith lock:\n    shared += 1",
            "code": """import threading  ## Thread and Lock
import time  ## sleep simulates device latency
from concurrent.futures import ThreadPoolExecutor, as_completed  ## High-level thread pool API

LATENCY = {"ap-1": 0.30, "ap-2": 0.10, "ap-3": 0.20, "ap-4": 0.05}  ## Pretend SSH round-trip times


def health_check(ap: str) -> str:  ## Runs in a worker thread
    time.sleep(LATENCY[ap])  ## Waiting on the device releases the GIL
    if ap == "ap-3":  ## One device is unhealthy
        raise ConnectionError(f"{ap}: ssh timeout")  ## Raised in the worker thread
    return f"{ap}: up"  ## Result travels back through the Future


def main() -> None:
    t0 = time.perf_counter()  ## Time the whole parallel run
    with ThreadPoolExecutor(max_workers=4) as pool:  ## Leaving the block waits for all workers
        futures = {pool.submit(health_check, ap): ap for ap in LATENCY}  ## Start every check; map Future -> AP
        for fut in as_completed(futures):  ## Yields futures in completion order, fastest first
            try:  ## result() re-raises the worker's exception here, in the main thread
                print(fut.result())  ## Successful check
            except ConnectionError as err:  ## Failed check
                print("FAILED", err, "| device:", futures[fut])  ## Report which device failed
    elapsed = time.perf_counter() - t0  ## Roughly the slowest single check, not the sum
    print("parallel time below the 0.65 s serial total:", elapsed < 0.6)  ## Waits overlapped
    lock = threading.Lock()  ## Protects the shared counter
    counter = {"done": 0}  ## Shared mutable state
    def worker() -> None:  ## Each thread increments 1000 times
        for _ in range(1000):  ## Many small updates
            with lock:  ## Only one thread at a time inside this block
                counter["done"] += 1  ## Read-modify-write, now safe
    threads = [threading.Thread(target=worker) for _ in range(4)]  ## Four raw threads
    for t in threads:  ## Start them all
        t.start()  ## Begins running worker()
    for t in threads:  ## Wait for each to finish
        t.join()  ## Blocks until that thread ends
    print(counter["done"])  ## Exactly 4000 thanks to the lock


if __name__ == "__main__":
    main()""",
            "under": "`submit()` puts a work item on a queue that idle worker threads pull from. A Future holds the eventual result or exception and lets the caller wait on it. `as_completed` waits on all of them and yields each one when it becomes done. `counter += 1` is several bytecode steps (load, add, store); a thread switch between the load and the store makes another thread's update disappear. A Lock makes the whole sequence atomic with respect to other threads using the same lock.",
            "gotchas": [
                {
                    "title": "Race condition on shared state",
                    "local_only": THREADS_NOTE,
                    "note": "Each thread reads the value, waits a moment, then writes back its own increment, so most updates are lost. A lock around the read-modify-write fixes it.",
                    "wrong": """import threading, time

state = {"passed": 0}

def record_pass():
    current = state["passed"]
    time.sleep(0.001)
    state["passed"] = current + 1

threads = [threading.Thread(target=record_pass) for _ in range(10)]
for t in threads: t.start()
for t in threads: t.join()
print("lost updates:", state["passed"] < 10)""",
                    "fixed": """import threading, time

state = {"passed": 0}
lock = threading.Lock()

def record_pass():
    with lock:
        current = state["passed"]
        time.sleep(0.001)
        state["passed"] = current + 1

threads = [threading.Thread(target=record_pass) for _ in range(10)]
for t in threads: t.start()
for t in threads: t.join()
print(state["passed"])""",
                }
            ],
            "best": "Prefer ThreadPoolExecutor over raw Thread objects, return results instead of mutating shared state, and when sharing is unavoidable protect it with one lock (or use `queue.Queue`, which is thread-safe). Always call `result()` on every future so exceptions in workers aren't silently lost.",
        },
        {
            "title": "Process pools for CPU-bound work",
            "local_only": THREADS_NOTE,
            "concept": "`ProcessPoolExecutor` runs functions in separate **processes**, each with its own interpreter and its own GIL, so CPU-bound work really runs on several cores. The cost: arguments and results are **pickled** and sent between processes, so they must be picklable (module-level functions, not lambdas or nested functions), and starting processes takes time. The entry point must be protected by `if __name__ == \"__main__\":` because child processes may re-import the main module.",
            "why": "Parsing a night's worth of pcaps or computing statistics over millions of samples is CPU-bound. Spreading files across a process pool can cut wall-clock time roughly by the number of cores.",
            "syntax": "def parse(path): ...          # module level, picklable\n\nif __name__ == \"__main__\":\n    with ProcessPoolExecutor(max_workers=os.cpu_count()) as pool:\n        results = list(pool.map(parse, paths))",
            "code": """import os  ## cpu_count
import time  ## perf_counter
from concurrent.futures import ProcessPoolExecutor  ## Pool of worker processes


def count_retries(n_frames: int) -> int:  ## Stands in for CPU-heavy capture parsing (must be module-level to pickle)
    retries = 0  ## Accumulator
    for i in range(n_frames):  ## Pure Python loop: holds the GIL in a single process
        if (i * 2654435761) % 97 == 0:  ## Pseudo-random 'retry bit set'
            retries += 1  ## Count it
    return retries  ## A small result: cheap to send back


def main() -> None:
    jobs = [1_500_000] * 4  ## Four 'capture files' of equal size
    t0 = time.perf_counter()  ## Serial baseline
    serial = [count_retries(n) for n in jobs]  ## One core
    t_serial = time.perf_counter() - t0  ## Serial time
    t0 = time.perf_counter()  ## Parallel run
    with ProcessPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as pool:  ## One process per core (up to 4)
        parallel = list(pool.map(count_retries, jobs))  ## Arguments are pickled to workers, results pickled back
    t_parallel = time.perf_counter() - t0  ## Parallel time
    print(serial == parallel, len(parallel))  ## Same answers either way
    print("process pool faster on a multi-core machine:", t_parallel < t_serial)  ## Separate GILs, real parallelism


if __name__ == "__main__":  ## REQUIRED for process pools: workers may re-import this module
    main()  ## Only the parent process runs main()""",
            "under": "On Linux the default start method has been `fork` (the child copies the parent's memory); macOS and Windows use `spawn`, which starts a fresh interpreter and imports your main module. Python 3.14 moves Linux's default away from fork, too. With spawn, any unguarded top-level code would run again in every worker, which is why the `__main__` guard is mandatory. Pickling costs scale with argument size, so send file paths, not file contents.",
            "gotchas": [
                {
                    "title": "Passing a lambda to a process pool",
                    "local_only": THREADS_NOTE,
                    "note": "Lambdas and nested functions can't be pickled by reference, so the job fails. Use a module-level function (functools.partial of one is fine).",
                    "wrong": """from concurrent.futures import ProcessPoolExecutor

if __name__ == "__main__":
    with ProcessPoolExecutor(2) as pool:
        try:
            print(list(pool.map(lambda x: x * 2, [1, 2])))
        except Exception as err:
            print(type(err).__name__)""",
                    "fixed": """from concurrent.futures import ProcessPoolExecutor

def double(x):
    return x * 2

if __name__ == "__main__":
    with ProcessPoolExecutor(2) as pool:
        print(list(pool.map(double, [1, 2])))""",
                }
            ],
            "best": "Use processes only for genuinely CPU-bound work, pass small arguments (paths, ids), return small results, and size the pool to the number of cores. Keep worker functions at module level and the entry point behind the `__main__` guard.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "local_only": THREADS_NOTE,
            "prompt": "Use ThreadPoolExecutor.map to 'ping' five hosts (simulated with sleep) and print the results in input order.",
            "solution": "map returns results in input order even if they finish out of order.",
            "solution_code": """import time
from concurrent.futures import ThreadPoolExecutor


def ping(host):
    time.sleep(0.05)
    return f"{host} ok"


with ThreadPoolExecutor(max_workers=5) as pool:
    print(list(pool.map(ping, [f"ap-{i}" for i in range(1, 6)])))""",
        },
        {
            "level": "Medium",
            "local_only": THREADS_NOTE,
            "prompt": "Collect results from parallel checks into a dict {ap: 'up' | error message}, using as_completed and handling exceptions per future.",
            "solution": "Map futures back to APs and catch around result().",
            "solution_code": """import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def check(ap):
    time.sleep(0.02)
    if ap == "ap-2":
        raise TimeoutError("no SSH banner")
    return "up"


status = {}
with ThreadPoolExecutor(max_workers=3) as pool:
    futures = {pool.submit(check, ap): ap for ap in ["ap-1", "ap-2", "ap-3"]}
    for fut in as_completed(futures):
        ap = futures[fut]
        try:
            status[ap] = fut.result()
        except TimeoutError as err:
            status[ap] = f"error: {err}"
print(dict(sorted(status.items())))""",
        },
        {
            "level": "Hard",
            "local_only": THREADS_NOTE,
            "prompt": "Implement a producer/consumer: one thread puts 10 log lines on a queue.Queue, two consumer threads count deauth lines, and a sentinel (None) per consumer shuts them down.",
            "solution": "queue.Queue is thread-safe; sentinels tell consumers to stop.",
            "solution_code": """import queue
import threading

q = queue.Queue()
counts = []
lock = threading.Lock()


def producer():
    for i in range(10):
        q.put("deauth reason=15" if i % 3 == 0 else "data")
    for _ in range(2):
        q.put(None)


def consumer():
    n = 0
    while (line := q.get()) is not None:
        n += "deauth" in line
    with lock:
        counts.append(n)


threads = [threading.Thread(target=producer)] + [threading.Thread(target=consumer) for _ in range(2)]
for t in threads: t.start()
for t in threads: t.join()
print("total deauth lines:", sum(counts))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Thread vs process?", "a": "Threads share one process's memory and, in standard CPython, one GIL, so they suit I/O-bound concurrency. Processes have separate memory and interpreters, so they run CPU-bound Python in parallel, at the cost of startup time and pickling data between them.", "follow": "Which needs locks more? (Threads, because they share memory.)"},
        {"level": "Intermediate", "q": "What is a race condition? Show one.", "a": "A bug where the result depends on thread timing. Classic case: two threads do `x = shared; shared = x + 1`; if both read before either writes, one increment is lost. Fix with a Lock around the read-modify-write, or avoid shared state by returning results.", "follow": "Is `counter += 1` atomic in Python? (No; it's several bytecode operations.)"},
        {"level": "Intermediate", "q": "map vs submit/as_completed in executors?", "a": "map returns results in input order and raises the first exception when you reach it. submit returns Futures; as_completed yields them as they finish, letting you process fast results early and handle each exception individually.", "follow": "What happens to an exception in a worker you never call result() on? (It's silently stored in the future and lost.)"},
        {"level": "Advanced", "q": "Why does a ProcessPoolExecutor need the __main__ guard?", "a": "With the spawn start method (default on macOS and Windows), each worker starts a new interpreter and imports the main module. Unguarded top-level code, including creating the pool, would run again in every child, causing recursion or duplicated work.", "follow": "What can't be sent to a process pool? (Unpicklable objects: lambdas, nested functions, open sockets, locks.)"},
    ],
    "quiz": [
        {"q": "What does future.result() do if the task raised?", "options": ["Returns None", "Re-raises the exception", "Returns the exception", "Hangs"], "answer": 1, "why": "Exceptions propagate to the caller."},
        {"q": "as_completed yields futures in which order?", "options": ["Submission order", "Completion order", "Random", "Alphabetical"], "answer": 1, "why": "Fastest first."},
        {"q": "Which protects shared state between threads?", "options": ["threading.Lock", "time.sleep", "gc.collect", "weakref"], "answer": 0, "why": "with lock: makes the block exclusive."},
        {"q": "Why can't a lambda be sent to a ProcessPoolExecutor?", "options": ["Too slow", "It can't be pickled by reference", "Lambdas are threads", "It can"], "answer": 1, "why": "Workers need importable functions."},
        {"q": "Best pool for parsing 200 large pcaps in pure Python?", "options": ["ThreadPoolExecutor", "ProcessPoolExecutor", "asyncio", "A single loop"], "answer": 1, "why": "CPU-bound work needs separate processes."},
    ],
    "cards": [
        {"front": "I/O-bound parallelism", "back": "ThreadPoolExecutor (or asyncio)"},
        {"front": "CPU-bound parallelism", "back": "ProcessPoolExecutor"},
        {"front": "Results as they finish", "back": "`for f in as_completed(futures): f.result()`"},
        {"front": "Protect shared state", "back": "`with lock:` around the read-modify-write"},
        {"front": "Process pool requirement", "back": "Module-level functions + `if __name__ == '__main__':`"},
    ],
}


M_3_14 = {
    "id": "3.14",
    "title": "asyncio",
    "hours": 4,
    "summary": "Coroutines and the event loop, running many device operations concurrently with gather and TaskGroup, timeouts, concurrency limits with Semaphore, collecting failures, and never blocking the loop.",
    "concepts": [
        {
            "title": "Coroutines, gather, TaskGroup and timeouts",
            "concept": "An `async def` function returns a **coroutine** when called; nothing runs until it's awaited or scheduled. `await` suspends the current coroutine until the awaited operation finishes, letting the **event loop** run others in the meantime; all of this happens in one thread. `asyncio.gather(*coros)` runs coroutines concurrently and returns their results in order. `asyncio.TaskGroup` (3.11+) does the same with structured error handling: if one task fails, the others are cancelled and the errors arrive as an ExceptionGroup. `asyncio.timeout(seconds)` cancels a block that takes too long. `asyncio.run(main())` starts the loop.",
            "why": "Collecting uptime and firmware versions from 100 APs concurrently with asyncssh takes about as long as the slowest AP, not the sum of all of them, and per-device timeouts stop one hung device from stalling the whole check.",
            "syntax": "async def fetch(ap): ...\nresults = await asyncio.gather(*(fetch(ap) for ap in aps))\nasync with asyncio.TaskGroup() as tg:\n    t = tg.create_task(fetch(ap))\nasync with asyncio.timeout(5):\n    await fetch(ap)\nasyncio.run(main())",
            "code": """import asyncio  ## The standard event-loop framework
import time  ## perf_counter to show the overlap

LATENCY = {"ap-1": 0.30, "ap-2": 0.10, "ap-3": 0.20}  ## Pretend per-device response times


async def fetch_uptime(ap: str) -> str:  ## A coroutine function
    await asyncio.sleep(LATENCY[ap])  ## Non-blocking wait: the loop runs other coroutines meanwhile
    return f"{ap}: up"  ## The coroutine's result


async def main() -> None:  ## The top-level coroutine
    t0 = time.perf_counter()  ## Start timing
    results = await asyncio.gather(*(fetch_uptime(ap) for ap in LATENCY))  ## Run all three concurrently
    print(results)  ## Results in INPUT order, regardless of finishing order
    print("concurrent:", time.perf_counter() - t0 < 0.45)  ## About 0.3 s (the slowest), not 0.6 s (the sum)
    async with asyncio.TaskGroup() as tg:  ## Structured concurrency (3.11+)
        tasks = {ap: tg.create_task(fetch_uptime(ap)) for ap in LATENCY}  ## Each task starts running right away
    print({ap: t.result() for ap, t in tasks.items()})  ## Leaving the block waited for every task
    try:  ## A per-device deadline
        async with asyncio.timeout(0.15):  ## Cancel the block after 150 ms
            await fetch_uptime("ap-1")  ## Takes 300 ms
    except TimeoutError:  ## asyncio.timeout raises the built-in TimeoutError
        print("ap-1 timed out after 150 ms")  ## Report and move on
    coro = fetch_uptime("ap-2")  ## Calling an async function only creates a coroutine object
    print(type(coro).__name__)  ## 'coroutine': nothing has run yet
    print(await coro)  ## Awaiting it actually runs it


if __name__ == "__main__":
    asyncio.run(main())  ## Create the event loop, run main() to completion, close the loop""",
            "under": "The event loop keeps a queue of ready callbacks and a set of waiting operations (timers, sockets). A coroutine runs until it hits an `await` on something not ready, then yields control back to the loop, which resumes whichever coroutine's operation completed next. Tasks wrap coroutines so they're scheduled independently. Because only one coroutine runs at a time and switches happen only at `await`, you rarely need locks, but any blocking call stalls everything.",
            "gotchas": [
                {
                    "title": "Forgetting await",
                    "note": "Without await you get a coroutine object, not the result, and the work never happens (Python later warns 'coroutine ... was never awaited').",
                    "wrong": """import asyncio

async def get_rssi():
    await asyncio.sleep(0.01)
    return -54

async def main():
    rssi = get_rssi()
    print(type(rssi).__name__)
    rssi.close()

asyncio.run(main())""",
                    "fixed": """import asyncio

async def get_rssi():
    await asyncio.sleep(0.01)
    return -54

async def main():
    rssi = await get_rssi()
    print(rssi)

asyncio.run(main())""",
                }
            ],
            "best": "Use `asyncio.run(main())` once at the entry point, TaskGroup for groups of tasks that should succeed or fail together, `gather(return_exceptions=True)` when you want every result whatever happens, and `asyncio.timeout` around every network operation.",
        },
        {
            "title": "Concurrency limits, failures and blocking calls",
            "concept": "`asyncio.Semaphore(n)` caps how many coroutines run a section at once, e.g. at most 10 SSH sessions. `gather(..., return_exceptions=True)` returns exceptions as values instead of raising the first one, so you can report every failure. Any **blocking** call inside a coroutine (`time.sleep`, `requests.get`, a slow parse) freezes the whole loop; use the async equivalent (`asyncio.sleep`, httpx, asyncssh) or push the blocking call to a thread with `await asyncio.to_thread(func, ...)`.",
            "why": "Pushing config to 100 APs with no limit can overload a controller or hit SSH connection limits. A semaphore of 10, with failures collected per device, gives a fast, polite and complete report.",
            "syntax": "sem = asyncio.Semaphore(10)\nasync with sem:\n    await push(ap)\nresults = await asyncio.gather(*coros, return_exceptions=True)\nawait asyncio.to_thread(blocking_func, arg)",
            "code": """import asyncio  ## Event loop, Semaphore, gather
import time  ## To show what a blocking sleep does

state = {"active": 0, "peak": 0}  ## Tracks how many pushes run at the same moment


async def push_config(ap: str, sem: asyncio.Semaphore) -> str:  ## One device's config push
    async with sem:  ## Waits here if the limit is already reached
        state["active"] += 1  ## Entered the limited section
        state["peak"] = max(state["peak"], state["active"])  ## Record the highest concurrency seen
        try:  ## Make sure the counter is decremented even on failure
            await asyncio.sleep(0.05)  ## The actual push (network I/O)
            if ap == "ap-4":  ## One device rejects us
                raise ConnectionError(f"{ap}: auth failed")  ## A per-device failure
            return ap  ## Success
        finally:  ## Leaving the limited section
            state["active"] -= 1  ## One fewer running


async def blocking_vs_async() -> tuple[float, float]:  ## Compare a blocking sleep with an async one
    async def bad() -> None:  ## Blocks the whole loop
        time.sleep(0.1)  ## Nothing else can run during this
    async def good() -> None:  ## Yields to the loop while waiting
        await asyncio.sleep(0.1)  ## Others run meanwhile
    t0 = time.perf_counter()  ## Time two blocking coroutines
    await asyncio.gather(bad(), bad())  ## They run one after the other
    t_bad = time.perf_counter() - t0  ## About 0.2 s
    t0 = time.perf_counter()  ## Time two async coroutines
    await asyncio.gather(good(), good())  ## They overlap
    return t_bad, time.perf_counter() - t0  ## About 0.1 s


async def main() -> None:
    sem = asyncio.Semaphore(2)  ## At most 2 pushes at once
    aps = [f"ap-{i}" for i in range(1, 7)]  ## Six devices
    results = await asyncio.gather(*(push_config(ap, sem) for ap in aps), return_exceptions=True)  ## Exceptions become values
    ok = [r for r in results if isinstance(r, str)]  ## Successful devices
    failed = [str(r) for r in results if isinstance(r, Exception)]  ## Failure messages
    print("ok:", ok)  ## Five devices
    print("failed:", failed)  ## One device, with its reason
    print("peak concurrency:", state["peak"])  ## Never more than the semaphore allows
    t_bad, t_good = await blocking_vs_async()  ## The cost of blocking the loop
    print("time.sleep serialised the coroutines:", t_bad >= 0.19, "| asyncio.sleep overlapped:", t_good < 0.15)  ## Booleans keep output stable


if __name__ == "__main__":
    asyncio.run(main())  ## Entry point""",
            "under": "A Semaphore holds a counter; `async with sem` decrements it or, if it's zero, suspends the coroutine until another one releases. `to_thread` runs the function in the default thread pool and awaits a future for it, which works because the blocking happens outside the loop's thread. CPU-heavy work still competes for the GIL; send that to a process pool with `loop.run_in_executor`.",
            "gotchas": [
                {
                    "title": "One failure cancels the batch",
                    "note": "Plain gather raises the first exception and you lose the other results. Use return_exceptions=True (or a TaskGroup and except*) to report every device.",
                    "wrong": """import asyncio

async def push(ap):
    await asyncio.sleep(0.01)
    if ap == "ap-2":
        raise ConnectionError(f"{ap} refused")
    return ap

async def main():
    try:
        print(await asyncio.gather(*(push(a) for a in ["ap-1", "ap-2", "ap-3"])))
    except ConnectionError as err:
        print("only know about:", err)

asyncio.run(main())""",
                    "fixed": """import asyncio

async def push(ap):
    await asyncio.sleep(0.01)
    if ap == "ap-2":
        raise ConnectionError(f"{ap} refused")
    return ap

async def main():
    results = await asyncio.gather(*(push(a) for a in ["ap-1", "ap-2", "ap-3"]), return_exceptions=True)
    print([r if isinstance(r, str) else f"FAILED: {r}" for r in results])

asyncio.run(main())""",
                }
            ],
            "best": "Bound every fan-out with a Semaphore sized to what the devices and controller tolerate, wrap each device operation in `asyncio.timeout`, collect failures per device, and keep blocking calls out of coroutines (use async libraries or `asyncio.to_thread`).",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write a coroutine `scan(channel)` that waits 0.02 s and returns the channel; gather it for channels 36, 40, 44 and print the results.",
            "solution": "gather keeps the input order.",
            "solution_code": """import asyncio


async def scan(channel):
    await asyncio.sleep(0.02)
    return channel


async def main():
    print(await asyncio.gather(*(scan(ch) for ch in [36, 40, 44])))


asyncio.run(main())""",
        },
        {
            "level": "Medium",
            "prompt": "Give each device a 100 ms timeout: devices with latency above that are reported as 'timeout', others as 'ok'.",
            "solution": "Wrap each call in asyncio.timeout inside a helper that converts TimeoutError into a status.",
            "solution_code": """import asyncio

LATENCY = {"ap-1": 0.05, "ap-2": 0.30, "ap-3": 0.08}


async def probe(ap):
    try:
        async with asyncio.timeout(0.1):
            await asyncio.sleep(LATENCY[ap])
            return ap, "ok"
    except TimeoutError:
        return ap, "timeout"


async def main():
    print(dict(await asyncio.gather(*(probe(ap) for ap in LATENCY))))


asyncio.run(main())""",
        },
        {
            "level": "Hard",
            "prompt": "Use a TaskGroup to check four devices where two fail, and handle the resulting ExceptionGroup with except*, printing the failed device names.",
            "solution": "TaskGroup raises an ExceptionGroup containing every failure.",
            "solution_code": """import asyncio


async def check(ap):
    await asyncio.sleep(0.01)
    if ap in ("ap-2", "ap-4"):
        raise ConnectionError(ap)
    return ap


async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            for ap in ["ap-1", "ap-2", "ap-3", "ap-4"]:
                tg.create_task(check(ap))
    except* ConnectionError as group:
        print("failed:", sorted(str(e) for e in group.exceptions))


asyncio.run(main())""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "asyncio vs threading for I/O-bound work?", "a": "Both overlap waiting. asyncio uses one thread and switches only at await points, so it scales to thousands of connections cheaply and rarely needs locks, but every library in the path must be async (or pushed to a thread). Threads work with ordinary blocking libraries but each costs more memory and needs locks for shared state.", "follow": "When would you pick threads anyway? (When the libraries you need are blocking-only.)"},
        {"level": "Intermediate", "q": "What happens if you call time.sleep() inside a coroutine?", "a": "It blocks the event loop thread, so no other coroutine runs during the sleep; concurrency disappears. Use await asyncio.sleep(), or await asyncio.to_thread() for unavoidable blocking calls.", "follow": "How would you detect this? (asyncio debug mode warns about slow callbacks.)"},
        {"level": "Intermediate", "q": "gather vs TaskGroup?", "a": "gather runs awaitables concurrently and returns results in order; by default the first exception propagates while other tasks keep running, and return_exceptions=True turns exceptions into results. TaskGroup (3.11+) cancels the remaining tasks when one fails and raises an ExceptionGroup of all failures: structured concurrency.", "follow": "How do you limit concurrency? (asyncio.Semaphore.)"},
        {"level": "Advanced", "q": "What's the difference between a coroutine and a Task?", "a": "A coroutine object is the paused function call; it does nothing until awaited. A Task wraps a coroutine and schedules it on the loop immediately, so it runs in the background and can be awaited, cancelled or inspected later.", "follow": "What does cancellation look like inside the coroutine? (CancelledError is raised at the current await.)"},
    ],
    "quiz": [
        {"q": "Calling an async def function returns...", "options": ["Its result", "A coroutine object", "A Task already running", "None"], "answer": 1, "why": "It runs only when awaited or scheduled."},
        {"q": "asyncio.gather returns results in...", "options": ["Completion order", "Input order", "Random order", "Reverse order"], "answer": 1, "why": "Order matches the arguments."},
        {"q": "Which limits concurrent coroutines?", "options": ["asyncio.Lock", "asyncio.Semaphore(n)", "asyncio.sleep", "asyncio.run"], "answer": 1, "why": "A semaphore admits n at a time."},
        {"q": "What does asyncio.timeout raise on expiry?", "options": ["asyncio.CancelledError to you", "TimeoutError", "ValueError", "Nothing"], "answer": 1, "why": "The built-in TimeoutError."},
        {"q": "Best way to run a blocking library call in async code?", "options": ["Call it directly", "await asyncio.to_thread(func)", "time.sleep first", "gc.collect()"], "answer": 1, "why": "Moves it off the loop thread."},
    ],
    "cards": [
        {"front": "Run concurrently, results in order", "back": "`await asyncio.gather(*coros)`"},
        {"front": "Structured concurrency", "back": "`async with asyncio.TaskGroup() as tg: tg.create_task(...)`"},
        {"front": "Per-operation deadline", "back": "`async with asyncio.timeout(s):`"},
        {"front": "Limit concurrency", "back": "`sem = asyncio.Semaphore(n); async with sem:`"},
        {"front": "Never inside a coroutine", "back": "Blocking calls like time.sleep; use asyncio.sleep or to_thread."},
    ],
}


M_3_15 = {
    "id": "3.15",
    "title": "Profiling & Performance",
    "hours": 2,
    "summary": "Measuring before optimising: timeit for micro-benchmarks, cProfile and pstats to find hot functions, tracemalloc for memory, and the optimisations that actually matter.",
    "concepts": [
        {
            "title": "timeit and cProfile",
            "concept": "`timeit` runs a small piece of code many times and reports total time, removing most noise; `timeit.repeat` gives several measurements so you can take the minimum. `cProfile` records every function call while your program runs; `pstats` sorts the results by **cumulative** time (including callees) or **total** time (own code only) to show where time goes. Profile first, then optimise the hottest function, then measure again.",
            "why": "A log analyzer that takes 90 s on a nightly log usually spends nearly all of it in one or two lines. Profiling finds them in minutes; guessing wastes hours optimising code that wasn't slow.",
            "syntax": "timeit.timeit(lambda: f(data), number=100)\nmin(timeit.repeat(lambda: f(data), number=10, repeat=5))\n\npython -m cProfile -s cumulative analyzer.py\npr = cProfile.Profile(); pr.enable(); ...; pr.disable()\npstats.Stats(pr).sort_stats(\"cumulative\").print_stats(10)",
            "code": """import cProfile  ## Deterministic function-level profiler
import pstats  ## Sorting and reporting profiler results
import re  ## Regex for the log analysis
import timeit  ## Micro-benchmarks

LINES = [f"10:00:{i % 60:02d} sta aa:{i % 50:02d} {'deauth reason=15' if i % 7 == 0 else 'data frame'}" for i in range(20_000)]  ## Synthetic log
PATTERN = re.compile(r"reason=(\\d+)")  ## Compiled once


def slow_count(lines: list[str]) -> dict[str, int]:  ## Runs a regex search on EVERY line
    counts: dict[str, int] = {}  ## reason -> count
    for line in lines:  ## 20,000 lines
        m = re.search(r"reason=(\\d+)", line)  ## Pattern lookup + full regex scan each time
        if m:  ## Only deauth lines match
            counts[m.group(1)] = counts.get(m.group(1), 0) + 1  ## Count it
    return counts  ## Result


def fast_count(lines: list[str]) -> dict[str, int]:  ## Cheap filter first, regex only when needed
    counts: dict[str, int] = {}  ## reason -> count
    for line in lines:  ## Same lines
        if "reason=" in line:  ## A substring test is far cheaper than a regex
            m = PATTERN.search(line)  ## Only about 1 line in 7 gets here
            counts[m.group(1)] = counts.get(m.group(1), 0) + 1  ## Count it
    return counts  ## Same result


def main() -> None:
    print("same result:", slow_count(LINES) == fast_count(LINES))  ## Always check correctness before speed
    t_slow = min(timeit.repeat(lambda: slow_count(LINES), number=3, repeat=3))  ## Best of 3 runs of 3 calls
    t_fast = min(timeit.repeat(lambda: fast_count(LINES), number=3, repeat=3))  ## Same for the fast version
    print("fast version wins:", t_fast < t_slow)  ## The exact times vary per machine, so we compare
    profiler = cProfile.Profile()  ## Create a profiler
    profiler.enable()  ## Start recording calls
    slow_count(LINES)  ## The code under investigation
    profiler.disable()  ## Stop recording
    stats = pstats.Stats(profiler)  ## Wrap the raw data
    by_calls = {func[2]: data[1] for func, data in stats.stats.items()}  ## function name -> number of calls
    print("re.search called once per line:", by_calls.get("search") == len(LINES))  ## The profiler shows the hot spot


if __name__ == "__main__":
    main()""",
            "under": "cProfile hooks every Python function call and return, so it adds overhead (often 2x) and slightly distorts very small functions, but the ranking of hot spots is reliable. Each `stats.stats` entry maps `(file, line, function)` to `(primitive calls, total calls, own time, cumulative time, callers)`. timeit disables garbage collection during timing by default and uses `perf_counter`.",
            "gotchas": [
                {
                    "title": "Benchmarking with one run",
                    "note": "A single measurement includes start-up effects and noise from other processes. Repeat and take the minimum (the least disturbed run).",
                    "wrong": """import time
t0 = time.perf_counter()
sorted(range(100_000, 0, -1))
single = time.perf_counter() - t0
print("one noisy number:", single > 0)""",
                    "fixed": """import timeit
runs = timeit.repeat(lambda: sorted(range(100_000, 0, -1)), number=5, repeat=5)
print("5 measurements:", len(runs), "| use the minimum:", min(runs) <= max(runs))""",
                }
            ],
            "best": "Write a correctness check first, profile with realistic data, fix the top item, then re-measure. Use `python -m cProfile -s cumulative script.py` for whole programs, timeit for comparing two small implementations, and keep a benchmark in the repo for performance-critical parsers.",
        },
        {
            "title": "Memory with tracemalloc and the optimisations that matter",
            "concept": "`tracemalloc` tracks memory allocated by Python code: current and peak usage, and snapshots that show which lines allocated the most. The optimisations that usually matter are **algorithmic**: the right data structure (a set for membership instead of a list), streaming instead of materialising (generators), doing expensive work only when needed (cheap filters first, caching), and pushing heavy numeric work into C libraries. Micro-tweaks rarely matter.",
            "why": "A soak monitor that builds a list of every sample can use gigabytes; a generator uses kilobytes. A list of 5,000 MACs checked once per frame turns a quick parser into a slow one; a set fixes it.",
            "syntax": "tracemalloc.start()\n...\ncurrent, peak = tracemalloc.get_traced_memory()\nsnap = tracemalloc.take_snapshot()\nsnap.statistics(\"lineno\")[:5]\ntracemalloc.stop()",
            "code": """import inspect  ## To find a line number for the snapshot check
import timeit  ## Compare lookups
import tracemalloc  ## Track Python memory allocations


def peak_kib(fn) -> float:  ## Peak memory allocated while fn() runs
    tracemalloc.start()  ## Begin tracking
    fn()  ## Run the code under test
    _, peak = tracemalloc.get_traced_memory()  ## (current, peak) in bytes
    tracemalloc.stop()  ## Stop and clear
    return peak / 1024  ## KiB


def main() -> None:
    list_peak = peak_kib(lambda: sum([x * x for x in range(200_000)]))  ## Builds a 200k-element list first
    gen_peak = peak_kib(lambda: sum(x * x for x in range(200_000)))  ## Streams one value at a time
    print("generator uses far less memory:", gen_peak < list_peak / 10)  ## Megabytes vs a few KiB
    macs = [f"aa:{i:04x}" for i in range(5000)]  ## Known station MACs
    mac_set = set(macs)  ## The same data as a hash set
    t_list = timeit.timeit(lambda: "aa:1387" in macs, number=2000)  ## Linear scan, near the end of the list
    t_set = timeit.timeit(lambda: "aa:1387" in mac_set, number=2000)  ## One hash lookup
    print("set lookup faster than list:", t_set < t_list)  ## O(1) vs O(n)
    tracemalloc.start()  ## Snapshot example: who allocated what?
    expected_line = inspect.currentframe().f_lineno + 1  ## The line number of the next statement
    table = {i: [0.0] * 50 for i in range(2000)}  ## A deliberately memory-hungry line
    top = tracemalloc.take_snapshot().statistics("lineno")[0]  ## The single biggest allocation site
    tracemalloc.stop()  ## Done tracking
    print("biggest allocation is the table line:", top.traceback[0].lineno == expected_line, len(table))  ## Points straight at the culprit


if __name__ == "__main__":
    main()""",
            "under": "tracemalloc installs hooks in Python's memory allocator and records a traceback for each allocation, so it slows the program and only sees memory allocated through Python (not, for example, memory a C library allocates itself). `in` on a list compares items one by one; on a set it hashes the value and checks a single bucket, which is why the gap grows with the collection's size.",
            "gotchas": [
                {
                    "title": "Repeated membership tests against a list",
                    "note": "Checking each frame's MAC against a big list is O(n) per check. Convert once to a set (both versions give the same answer; only the speed differs).",
                    "wrong": """import timeit
known = [f"aa:{i:04x}" for i in range(5000)]
frames = [f"aa:{i:04x}" for i in range(0, 10000, 7)]
t = timeit.timeit(lambda: sum(m in known for m in frames), number=3)
print(sum(m in known for m in frames))""",
                    "fixed": """import timeit
known = set(f"aa:{i:04x}" for i in range(5000))
frames = [f"aa:{i:04x}" for i in range(0, 10000, 7)]
t = timeit.timeit(lambda: sum(m in known for m in frames), number=3)
print(sum(m in known for m in frames))""",
                }
            ],
            "best": "Measure memory as well as time in long-running tools, prefer streaming over materialising, pick data structures by their operation costs (sets and dicts for lookups, deque for queues), and reach for numpy or pandas when you're crunching numbers in loops.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Compare `\"\".join(parts)` with repeated `+=` for building a 20,000-line report using timeit, and print only whether join was at least as fast.",
            "solution": "Time both with timeit.repeat. CPython can optimise += on strings in some cases, so the gap varies by version and machine; print the two numbers locally and compare. The lesson is to measure rather than assume.",
            "solution_code": """import timeit

parts = [f"ch{i % 165} ok\\n" for i in range(20_000)]


def with_join():
    return "".join(parts)


def with_plus():
    out = ""
    for p in parts:
        out += p
    return out


t_join = min(timeit.repeat(with_join, number=20, repeat=3))
t_plus = min(timeit.repeat(with_plus, number=20, repeat=3))
print("same text:", with_join() == with_plus())
print("both measured:", t_join > 0 and t_plus > 0)
# Print t_join and t_plus on your machine: the ratio depends on the Python version.""",
        },
        {
            "level": "Medium",
            "prompt": "Profile a function that calls a helper 10,000 times and report the helper's call count from pstats.",
            "solution": "pstats keys are (file, line, name); value[1] is the total call count.",
            "solution_code": """import cProfile
import pstats


def to_mw(dbm):
    return 10 ** (dbm / 10)


def convert_all():
    return [to_mw(d) for d in range(-90, -80) for _ in range(1000)]


pr = cProfile.Profile()
pr.enable()
convert_all()
pr.disable()
calls = {k[2]: v[1] for k, v in pstats.Stats(pr).stats.items()}
print("to_mw calls:", calls["to_mw"])""",
        },
        {
            "level": "Hard",
            "prompt": "Use tracemalloc snapshots before and after building a 'sample history' to show how many KiB it added, without printing machine-specific exact numbers.",
            "solution": "compare_to() lists the difference per line; sum the size_diff values.",
            "solution_code": """import tracemalloc

tracemalloc.start()
before = tracemalloc.take_snapshot()
history = [(t, -50 - t % 30) for t in range(50_000)]
after = tracemalloc.take_snapshot()
tracemalloc.stop()
grown = sum(stat.size_diff for stat in after.compare_to(before, "lineno")) / 1024
print("history added more than 1 MiB:", grown > 1024, "| samples:", len(history))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "How do you find out why a script is slow?", "a": "Profile it with realistic input: `python -m cProfile -s cumulative script.py` or a Profile object around the slow part. Look at cumulative time to find the expensive call path and total time for the functions doing the work. Optimise the top item and measure again.", "follow": "Cumulative vs total time? (Cumulative includes time in called functions; total is the function's own code.)"},
        {"level": "Intermediate", "q": "When do you use timeit instead of cProfile?", "a": "timeit compares small, isolated alternatives precisely by running them many times; cProfile shows where time goes in a whole program. Use cProfile to find the hot spot, then timeit to choose between fixes.", "follow": "Why take the minimum of repeated runs? (It's the run least disturbed by other activity.)"},
        {"level": "Intermediate", "q": "How do you find a memory leak?", "a": "Use tracemalloc: take snapshots at two points, compare them by line, and look at the top size differences. Typical causes are growing lists, unbounded caches and registries holding strong references.", "follow": "What can't tracemalloc see? (Memory allocated directly by C libraries outside Python's allocator.)"},
        {"level": "Advanced", "q": "Which optimisations usually give the biggest wins in Python?", "a": "Algorithmic ones: better data structures (set/dict lookups), avoiding repeated work (filter early, cache), streaming instead of materialising, and moving numeric loops to vectorised C libraries or processes. Micro-optimisations such as local-variable aliasing rarely matter compared with these.", "follow": "How do you make sure an optimisation didn't break anything? (A correctness check or test comparing old and new outputs.)"},
    ],
    "quiz": [
        {"q": "What does cumulative time include?", "options": ["Only the function's own lines", "The function plus everything it calls", "Import time", "Wall-clock of the program"], "answer": 1, "why": "Callees are included."},
        {"q": "Which tool measures peak Python memory?", "options": ["timeit", "tracemalloc", "cProfile", "gc"], "answer": 1, "why": "get_traced_memory returns (current, peak)."},
        {"q": "Fastest structure for repeated 'is this MAC known?' checks?", "options": ["list", "tuple", "set", "str"], "answer": 2, "why": "Average O(1) hash lookups."},
        {"q": "From timeit.repeat results you usually report...", "options": ["The maximum", "The minimum", "The first", "The sum"], "answer": 1, "why": "The least disturbed run."},
        {"q": "First step before optimising?", "options": ["Rewrite in C", "Profile with realistic data", "Add threads", "Remove type hints"], "answer": 1, "why": "Find the real hot spot first."},
    ],
    "cards": [
        {"front": "Profile a whole script", "back": "`python -m cProfile -s cumulative script.py`"},
        {"front": "Compare two snippets", "back": "`min(timeit.repeat(fn, number=n, repeat=r))`"},
        {"front": "Peak memory", "back": "`tracemalloc.get_traced_memory()`"},
        {"front": "Biggest wins", "back": "Algorithms and data structures, not micro-tweaks."},
    ],
}
