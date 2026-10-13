"""Phase 2 content: modules 2.1-2.3."""

M_2_1 = {
    "id": "2.1",
    "title": "Functions & Arguments",
    "hours": 3,
    "summary": "Defining and returning, defaults and keyword arguments, *args and **kwargs, keyword-only and positional-only parameters, and the mutable-default trap.",
    "concepts": [
        {
            "title": "Defining, calling and returning",
            "concept": "`def` creates a **function object** and binds it to a name. Parameters receive arguments **positionally** or **by keyword**, and parameters with defaults may be omitted. `return` sends a value back; returning several values really returns one tuple, which the caller can unpack. A function without `return` returns `None`. The first string in the body is the **docstring**.",
            "why": "Every pass/fail decision in a test suite should live in one small, named, tested function rather than being copied into twenty test cases. Clear signatures are the interface your teammates use.",
            "syntax": "def name(a, b, c=10) -> ResultType:\n    \"\"\"One-line summary.\"\"\"\n    ...\n    return value          # or: return x, y  (a tuple)\n\nname(1, 2)                # positional\nname(1, b=2, c=3)         # keyword",
            "code": """def throughput_verdict(measured: float, baseline: float, tolerance: float = 0.05) -> tuple[bool, float]:  ## Two required parameters and one with a default; the hint says it returns (bool, float)
    \"\"\"Return (passed, delta_pct) for a measurement against a baseline.\"\"\"  ## Docstring: shown by help() and IDEs
    delta_pct = (measured - baseline) / baseline * 100  ## Percentage change relative to the baseline
    passed = delta_pct >= -tolerance * 100  ## Pass if we are no more than `tolerance` below baseline
    return passed, round(delta_pct, 2)  ## Two values become one tuple


def main() -> None:
    ok, delta = throughput_verdict(905.0, 920.0)  ## Positional arguments; the returned tuple is unpacked into two names
    print(ok, delta)  ## 1.63% below baseline is within 5%
    print(throughput_verdict(850.0, 920.0, tolerance=0.10))  ## Override the default by keyword: -7.61% passes with a 10% tolerance
    print(throughput_verdict(baseline=920.0, measured=930.0))  ## All-keyword call: order no longer matters
    print(throughput_verdict.__doc__)  ## The docstring is stored on the function object
    check = throughput_verdict  ## Functions are objects: bind a second name to the same function
    print(check is throughput_verdict, check(920.0, 920.0))  ## Same object, callable through either name


if __name__ == "__main__":
    main()""",
            "under": "`def` is an executable statement: when Python reaches it, it builds a function object holding the compiled code, the default values and a reference to the module's globals. Defaults are evaluated **once, at definition time**, which is the root of the mutable-default trap in the next concept. Each call creates a new frame for the local variables.",
            "gotchas": [
                {
                    "title": "Forgetting return",
                    "note": "A function that computes a value but never returns it gives back None, and the bug shows up later as a confusing TypeError.",
                    "wrong": """def to_mw(dbm):
    10 ** (dbm / 10)

print(to_mw(20))""",
                    "fixed": """def to_mw(dbm):
    return 10 ** (dbm / 10)

print(to_mw(20))""",
                },
                {
                    "title": "Positional arguments in the wrong order",
                    "note": "Swapping two floats produces a wrong verdict (here a PASS for a 6.5% drop), not an error. Pass easily confused arguments by keyword.",
                    "wrong": """def verdict(measured, baseline):
    return measured >= 0.95 * baseline

print(verdict(920.0, 860.0))""",
                    "fixed": """def verdict(measured, baseline):
    return measured >= 0.95 * baseline

print(verdict(measured=860.0, baseline=920.0))""",
                },
            ],
            "best": "Keep functions small and single-purpose, give them a docstring and type hints, and return data instead of printing it so callers (and tests) can use the result. Call with keywords whenever two arguments have the same type.",
        },
        {
            "title": "*args, **kwargs, keyword-only and positional-only",
            "concept": "`*args` collects extra positional arguments into a **tuple**; `**kwargs` collects extra keyword arguments into a **dict**. A bare `*` in the signature makes every following parameter **keyword-only**; a `/` makes every preceding parameter **positional-only**. At the call site, `*seq` and `**mapping` unpack values into arguments. Defaults must never be mutable objects: use `None` and create the object inside.",
            "why": "Wrappers around iperf3, SSH commands and loggers forward options to lower layers. Keyword-only flags (`reverse=True`) prevent unreadable calls like `run(\"10.0.0.2\", 30, 4, True)`.",
            "syntax": "def f(pos_only, /, normal, *, kw_only=1): ...\ndef g(*args, **kwargs): ...   # tuple, dict\ng(*[1, 2], **{\"x\": 3})       # unpack at the call\n\ndef add(x, items=None):        # never items=[]\n    if items is None:\n        items = []",
            "code": """def run_iperf(server: str, /, *, duration: int = 10, parallel: int = 1, reverse: bool = False) -> list[str]:  ## server is positional-only (/); everything after * is keyword-only
    cmd = ["iperf3", "-c", server, "-t", str(duration), "-P", str(parallel)]  ## Build the command as a list of arguments
    if reverse:  ## Only add -R when asked
        cmd.append("-R")  ## -R makes the server send (downlink test)
    return cmd  ## Return the command; a later module runs it with subprocess


def log_event(kind: str, *details: str, **fields: object) -> str:  ## *details gathers extra positionals; **fields gathers extra keywords
    extra = " ".join(f"{k}={v}" for k, v in fields.items())  ## Turn the keyword dict into key=value text
    return f"[{kind}] {' '.join(details)} {extra}".strip()  ## strip() removes the trailing space when there are no fields


def add_station(mac: str, stations: list[str] | None = None) -> list[str]:  ## The None default is the safe pattern for a mutable default
    if stations is None:  ## No list was passed in...
        stations = []  ## ...so create a fresh one for THIS call
    stations.append(mac)  ## Mutate the list we own
    return stations  ## Hand it back


def main() -> None:
    print(run_iperf("192.168.1.10", duration=30, reverse=True))  ## Flags passed by name: readable at the call site
    try:  ## Show what happens when a keyword-only argument is passed positionally
        run_iperf("192.168.1.10", 30)  ## 30 has nowhere to go: duration is keyword-only
    except TypeError as err:  ## Python enforces the signature
        print("TypeError:", err)  ## The message explains the problem
    print(log_event("roam", "sta1", "ap-1 -> ap-2", latency_ms=42, band="5G"))  ## Two extra positionals, two extra keywords
    options = {"duration": 5, "parallel": 4}  ## Options loaded from a config file, say
    print(run_iperf("10.0.0.2", **options))  ## ** unpacks the dict into keyword arguments
    print(add_station("aa:01"), add_station("aa:02"))  ## Each call gets its own new list


if __name__ == "__main__":
    main()""",
            "under": "Python matches arguments to parameters in a fixed order: positional arguments fill positional slots left to right, then keyword arguments fill slots by name, then defaults fill whatever is left. Extra positionals go to `*args`, extra keywords to `**kwargs`, and anything that still doesn't fit raises `TypeError`. The `/` marker (Python 3.8+) lets library authors rename a parameter later without breaking callers.",
            "gotchas": [
                {
                    "title": "The mutable default argument",
                    "note": "The default list is created once, when `def` runs, and shared by every call that uses it. Stations from earlier calls leak into later ones.",
                    "wrong": """def add_station(mac, stations=[]):
    stations.append(mac)
    return stations

print(add_station("aa:01"))
print(add_station("aa:02"))""",
                    "fixed": """def add_station(mac, stations=None):
    if stations is None:
        stations = []
    stations.append(mac)
    return stations

print(add_station("aa:01"))
print(add_station("aa:02"))""",
                },
                {
                    "title": "Passing a dict without unpacking it",
                    "note": "Without `**`, the dict is passed as a single positional argument.",
                    "wrong": """def connect(host, port=22, timeout=10):
    return f"{host}:{port} timeout={timeout}"

opts = {"port": 2222, "timeout": 5}
print(connect("ap-1", opts))""",
                    "fixed": """def connect(host, port=22, timeout=10):
    return f"{host}:{port} timeout={timeout}"

opts = {"port": 2222, "timeout": 5}
print(connect("ap-1", **opts))""",
                },
            ],
            "best": "Make boolean flags and tuning options keyword-only with a bare `*`. Use `None` as the default for any list, dict or set parameter. Use `*args`/`**kwargs` mainly in wrappers that forward arguments; elsewhere, explicit parameters document themselves better.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write `mw_to_dbm(mw)` and `dbm_to_mw(dbm)` and show that converting 100 mW to dBm and back returns 100.",
            "solution": "Two one-line functions with return statements. Round to hide float noise.",
            "solution_code": """import math


def mw_to_dbm(mw: float) -> float:
    return 10 * math.log10(mw)


def dbm_to_mw(dbm: float) -> float:
    return 10 ** (dbm / 10)


print(mw_to_dbm(100), round(dbm_to_mw(mw_to_dbm(100)), 6))""",
        },
        {
            "level": "Medium",
            "prompt": "Write `summarize(*samples, unit=\"Mbps\")` that returns `\"n=4 min=... max=... mean=... Mbps\"`, and raises ValueError when called with no samples.",
            "solution": "`*samples` arrives as a tuple; `unit` after it is automatically keyword-only.",
            "solution_code": """def summarize(*samples: float, unit: str = "Mbps") -> str:
    if not samples:
        raise ValueError("need at least one sample")
    mean = sum(samples) / len(samples)
    return f"n={len(samples)} min={min(samples)} max={max(samples)} mean={mean:.1f} {unit}"


print(summarize(910.2, 905.7, 899.1, 912.4))
print(summarize(-52, -55, unit="dBm"))""",
        },
        {
            "level": "Hard",
            "prompt": "Write `retry_call(func, *args, attempts=3, **kwargs)` that calls `func(*args, **kwargs)` up to `attempts` times, returning the first result that doesn't raise, and re-raising the last error otherwise. Test it with a function that fails twice.",
            "solution": "Forward the arguments untouched with * and **. Keep the last exception and raise it after the loop.",
            "solution_code": """def retry_call(func, *args, attempts=3, **kwargs):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return func(*args, **kwargs)
        except ConnectionError as err:
            print(f"attempt {attempt} failed: {err}")
            last_error = err
    raise last_error


calls = {"n": 0}


def flaky_ping(host, timeout=1):
    calls["n"] += 1
    if calls["n"] < 3:
        raise ConnectionError(f"{host} no reply in {timeout}s")
    return f"{host} up"


print(retry_call(flaky_ping, "ap-1", timeout=2))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What does a function return if it has no return statement?", "a": "`None`. The same is true for a bare `return`. Forgetting to return a computed value is a common bug that surfaces later as a TypeError on None.", "follow": "How do you return several values? (Return a tuple, e.g. `return ok, delta`, and unpack it at the call site.)"},
        {"level": "Intermediate", "q": "Explain the mutable default argument problem.", "a": "Default values are evaluated once, when `def` executes, and stored on the function. A mutable default such as `[]` is therefore shared across calls, so mutations accumulate. Use `None` as the default and create a new object inside the function.", "follow": "Is there ever a legitimate use? (Deliberate caching, but an explicit dict or functools.lru_cache is clearer.)"},
        {"level": "Intermediate", "q": "What do *args and **kwargs do?", "a": "In a signature, `*args` gathers extra positional arguments into a tuple and `**kwargs` gathers extra keyword arguments into a dict. At a call site, `*seq` and `**mapping` unpack values into arguments. Together they let wrappers forward arguments they don't need to understand.", "follow": "What order must parameters appear in? (Positional-only, normal, *args, keyword-only, **kwargs.)"},
        {"level": "Intermediate", "q": "What do * and / mean in a function signature?", "a": "A bare `*` makes every later parameter keyword-only. A `/` makes every earlier parameter positional-only (3.8+). Keyword-only parameters make calls self-documenting; positional-only parameters let you rename them without breaking callers.", "follow": "Which built-ins use positional-only parameters? (Many, e.g. `len(obj, /)`, which is why `len(obj=x)` fails.)"},
        {"level": "Advanced", "q": "Are Python functions first-class objects? What follows from that?", "a": "Yes. They can be assigned to names, stored in lists and dicts, passed as arguments and returned from other functions. That enables callbacks, dispatch tables (`handlers[event](...)`), decorators and closures.", "follow": "What attributes does a function object carry? (`__name__`, `__doc__`, `__defaults__`, `__code__`, `__closure__` and more.)"},
    ],
    "quiz": [
        {"q": "What does `def f(): pass` return when called?", "options": ["0", "None", "''", "It raises"], "answer": 1, "why": "Functions without a return value return None."},
        {"q": "In `def f(a, *, b)`, how must b be passed?", "options": ["Positionally", "By keyword", "Either way", "It can't be passed"], "answer": 1, "why": "Parameters after a bare * are keyword-only."},
        {"q": "What type is `args` inside `def f(*args)`?", "options": ["list", "tuple", "dict", "set"], "answer": 1, "why": "Extra positionals are collected into a tuple."},
        {"q": "When are default argument values evaluated?", "options": ["On every call", "Once, when def runs", "When first used", "At import of the caller"], "answer": 1, "why": "That is why mutable defaults are shared."},
        {"q": "What does `f(**{'x': 1})` do?", "options": ["Passes a dict as one argument", "Passes x=1 as a keyword argument", "Raises SyntaxError", "Passes 'x' positionally"], "answer": 1, "why": "** unpacks a mapping into keyword arguments."},
    ],
    "cards": [
        {"front": "Safe default for a list parameter", "back": "`items=None`, then `if items is None: items = []`"},
        {"front": "*args / **kwargs types", "back": "tuple / dict"},
        {"front": "Bare `*` in a signature", "back": "Everything after it is keyword-only."},
        {"front": "`/` in a signature", "back": "Everything before it is positional-only (3.8+)."},
        {"front": "Return several values", "back": "`return a, b` returns a tuple; unpack with `x, y = f()`."},
    ],
}


M_2_2 = {
    "id": "2.2",
    "title": "Scope (LEGB) & Lambda",
    "hours": 2,
    "summary": "How Python finds a name, global and nonlocal, closures that remember state, lambda expressions and the late-binding trap.",
    "concepts": [
        {
            "title": "LEGB, global and nonlocal",
            "concept": "Python looks a name up in four scopes, in order: **L**ocal (the current function), **E**nclosing (outer functions), **G**lobal (the module) and **B**uilt-in. Assigning to a name inside a function makes it **local** for the whole function body. `global name` rebinds a module-level name; `nonlocal name` rebinds a name in the nearest enclosing function. A function that keeps using an enclosing variable after the outer function returns is a **closure**.",
            "why": "Retry counters, per-test state and callback factories all depend on scope rules. The `UnboundLocalError` you get from touching a module-level counter is one of the most common surprises in test helpers.",
            "syntax": "x = 1               # global\ndef outer():\n    y = 2           # enclosing (for inner)\n    def inner():\n        nonlocal y\n        y += 1      # rebinds outer's y\n    return inner",
            "code": """import builtins  ## The module that holds len, print and the other built-ins

RETRY_LIMIT = 3  ## A module-level (global) name


def make_counter():  ## A factory that returns a function
    count = 0  ## Local to make_counter, and the enclosing scope for bump

    def bump() -> int:  ## Defined inside make_counter, so it can see `count`
        nonlocal count  ## We want to rebind the enclosing `count`, not create a new local one
        count += 1  ## Rebinding is allowed because of nonlocal
        return count  ## Return the new value

    return bump  ## Return the function itself (not a call): a closure carrying `count`


def show_scope() -> None:  ## Demonstrates shadowing
    RETRY_LIMIT = 5  ## This creates a NEW local name; the global is untouched
    print("local:", RETRY_LIMIT)  ## Local lookup wins


def main() -> None:
    show_scope()  ## Prints the local value
    print("global:", RETRY_LIMIT)  ## The global still holds 3
    retries = make_counter()  ## make_counter has returned, but its `count` lives on in the closure
    retries()  ## count = 1
    retries()  ## count = 2
    print("retries so far:", retries())  ## count = 3
    print(len is builtins.len)  ## `len` was found in the Built-in scope (B in LEGB)


if __name__ == "__main__":
    main()""",
            "under": "The compiler decides each name's scope when it compiles the function: any assignment in the body makes the name local everywhere in that function, even on lines before the assignment. Local variables live in a fast array on the frame. Variables captured by an inner function are stored in **cell objects**, which you can see in `bump.__closure__`, so they outlive the outer call.",
            "gotchas": [
                {
                    "title": "UnboundLocalError on a module-level counter",
                    "note": "`failures += 1` assigns to `failures`, so the compiler treats it as local for the whole function, and reading it before assignment fails.",
                    "wrong": """failures = 0

def record_failure():
    failures += 1

record_failure()""",
                    "fixed": """def record_failure(failures: int) -> int:
    return failures + 1

failures = 0
failures = record_failure(failures)
print(failures)""",
                },
                {
                    "title": "Shadowing a built-in inside a function",
                    "note": "A local named `max` hides the built-in for the whole function.",
                    "wrong": """def best(samples):
    max = 0
    for s in samples:
        if s > max:
            max = s
    return max(samples)

print(best([1, 3, 2]))""",
                    "fixed": """def best(samples):
    highest = 0
    for s in samples:
        if s > highest:
            highest = s
    return highest, max(samples)

print(best([1, 3, 2]))""",
                },
            ],
            "best": "Avoid `global`: pass values in and return results out, or keep state in an object (Phase 3). Use `nonlocal` only for small closures such as counters. Never reuse built-in names for variables.",
        },
        {
            "title": "lambda and late binding",
            "concept": "`lambda params: expression` creates a small anonymous function whose body is a single expression. It is most useful inline, as a `key=` for sorting or a short callback. Closures (including lambdas) look up captured variables **when they are called**, not when they are created: this is **late binding**. Lambdas created in a loop therefore all see the loop variable's final value unless you capture it with a default argument.",
            "why": "Sorting scan results, choosing a strongest BSSID, and registering per-channel callbacks all use lambdas. The late-binding bug is a classic interview puzzle and a real source of \"every callback tested channel 44\" failures.",
            "syntax": "key=lambda item: item[1]         # inline key function\nlambda x, y=2: x * y             # defaults allowed\nlambda ch=ch: ch                 # capture the current value",
            "code": """def main() -> None:
    scan = [("ap-3", -61), ("ap-1", -48), ("ap-2", -70)]  ## (BSSID, RSSI) pairs
    print(sorted(scan, key=lambda item: item[1], reverse=True))  ## The lambda tells sorted() to compare by RSSI; strongest first
    print(max(scan, key=lambda item: item[1])[0])  ## Same key with max(): the strongest BSSID
    callbacks = [lambda: ch for ch in [36, 40, 44]]  ## Three lambdas that each refer to the name `ch`
    print([cb() for cb in callbacks])  ## All see ch's FINAL value: late binding
    fixed = [lambda ch=ch: ch for ch in [36, 40, 44]]  ## A default argument is evaluated now, freezing each value
    print([cb() for cb in fixed])  ## 36, 40, 44 as intended


if __name__ == "__main__":
    main()""",
            "under": "A lambda compiles to an ordinary function object whose `__name__` is `'<lambda>'`; there is no performance difference from `def`. In the comprehension, all three lambdas close over the same variable `ch` in the comprehension's scope. By the time they run, the loop has finished and `ch` is 44. A default parameter is evaluated when the lambda is created, so `ch=ch` stores each value separately.",
            "gotchas": [
                {
                    "title": "Naming a lambda",
                    "note": "Assigning a lambda to a name gives you a function called `<lambda>` in tracebacks. PEP 8 (and linters, rule E731) say use def.",
                    "wrong": """to_mw = lambda dbm: 10 ** (dbm / 10)
print(to_mw.__name__)""",
                    "fixed": """def to_mw(dbm):
    return 10 ** (dbm / 10)

print(to_mw.__name__, to_mw(20))""",
                }
            ],
            "best": "Use lambda only inline (sort keys, small callbacks); write `def` for anything named or longer than one expression. When creating functions in a loop, capture loop values with a default argument or `functools.partial` (Module 2.12).",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Sort `[\"ap-10\", \"ap-2\", \"ap-1\"]` numerically by the number after the dash using a lambda.",
            "solution": "Split on '-' and convert the second part to int in the key.",
            "solution_code": """names = ["ap-10", "ap-2", "ap-1"]
print(sorted(names), sorted(names, key=lambda n: int(n.split("-")[1])))""",
        },
        {
            "level": "Medium",
            "prompt": "Write `make_threshold(limit)` that returns a function testing whether a throughput value meets that limit. Create checks for 900 and 2500 Mbps and apply them.",
            "solution": "The inner function closes over `limit`.",
            "solution_code": """def make_threshold(limit: float):
    def check(value: float) -> bool:
        return value >= limit
    return check


five_g = make_threshold(900)
six_g = make_threshold(2500)
print(five_g(912.4), five_g(880.0), six_g(2841.0))""",
        },
        {
            "level": "Hard",
            "prompt": "Build a dict of per-channel handlers `{36: f, 40: f, 44: f}` in a loop, where each handler returns `f\"tested ch{ch}\"`. Make sure every handler reports its own channel.",
            "solution": "Capture the loop variable with a default argument so each lambda keeps its own value.",
            "solution_code": """handlers = {ch: (lambda ch=ch: f"tested ch{ch}") for ch in [36, 40, 44]}
print([handlers[ch]() for ch in [36, 40, 44]])""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What does LEGB stand for?", "a": "The name lookup order: Local, Enclosing, Global, Built-in. Python searches each in turn and uses the first match.", "follow": "Where does a class body fit? (Class scope is not part of the chain for methods; methods access class attributes through `self` or the class name.)"},
        {"level": "Intermediate", "q": "Why does `count += 1` inside a function raise UnboundLocalError when count is a global?", "a": "Assignment anywhere in a function makes the name local for the whole body. `count += 1` reads the local before it is assigned. Fix it by passing and returning the value, or (sparingly) with `global count`.", "follow": "What is the difference between global and nonlocal? (global targets the module scope; nonlocal targets the nearest enclosing function.)"},
        {"level": "Intermediate", "q": "What is a closure?", "a": "A function that remembers variables from the scope where it was defined, even after that scope has finished. Python stores those captured variables in cell objects on the function's `__closure__`.", "follow": "Give a practical use. (Counters, configured callbacks, decorators.)"},
        {"level": "Advanced", "q": "What does `[lambda: i for i in range(3)]` produce when each function is called, and how do you fix it?", "a": "Each returns 2. Closures look up `i` when called (late binding), and by then the loop has ended. Capture the current value with a default: `lambda i=i: i`, or use `functools.partial`.", "follow": "Does the same happen with a normal for loop and def? (Yes; it's about closures, not lambda.)"},
    ],
    "quiz": [
        {"q": "Which scope does Python check first?", "options": ["Global", "Built-in", "Local", "Enclosing"], "answer": 2, "why": "LEGB starts with Local."},
        {"q": "Which keyword rebinds a variable in an enclosing function?", "options": ["global", "nonlocal", "outer", "static"], "answer": 1, "why": "nonlocal targets the nearest enclosing function scope."},
        {"q": "What is `[f() for f in [lambda: x for x in 'ab']]`?", "options": ["['a', 'b']", "['b', 'b']", "['a', 'a']", "Error"], "answer": 1, "why": "Late binding: both see the final value."},
        {"q": "Which is best for a sort key you use once?", "options": ["A lambda inline", "A global variable", "A class", "eval()"], "answer": 0, "why": "Inline lambdas are ideal for one-off keys."},
        {"q": "What error does reading a local before assigning it raise?", "options": ["NameError", "UnboundLocalError", "KeyError", "ValueError"], "answer": 1, "why": "UnboundLocalError is a subclass of NameError for exactly this case."},
    ],
    "cards": [
        {"front": "LEGB", "back": "Local, Enclosing, Global, Built-in"},
        {"front": "global vs nonlocal", "back": "Module scope vs nearest enclosing function scope."},
        {"front": "Closure", "back": "A function that keeps access to variables from its defining scope."},
        {"front": "Fix late binding in a loop", "back": "`lambda ch=ch: ...` or functools.partial"},
        {"front": "Why not `f = lambda ...`?", "back": "PEP 8 / E731: use def so the function has a real name."},
    ],
}


M_2_3 = {
    "id": "2.3",
    "title": "map, filter, sorted with key",
    "hours": 1.5,
    "summary": "Lazy transformation with map and filter, sorting and ranking with key functions, multi-key sorts and itemgetter.",
    "concepts": [
        {
            "title": "map, filter and key functions",
            "concept": "`map(func, iterable)` applies a function to every item; `filter(func, iterable)` keeps items where the function returns truthy. Both return **lazy iterators** that produce values only when asked and can be consumed **once**. `sorted()`, `min()` and `max()` accept a `key=` function: the comparison uses `key(item)` while the original items are returned. A tuple key sorts by several fields; Python's sort is **stable**.",
            "why": "Converting parsed text to numbers, keeping only strong BSSIDs and ranking scan results by band and signal strength are daily data-shaping steps. Knowing that `map` is lazy explains why a second loop over it suddenly finds nothing.",
            "syntax": "list(map(int, strings))\nlist(filter(lambda r: r > -60, rssi))\nsorted(items, key=lambda x: (x[\"band\"], -x[\"rssi\"]))\nmax(items, key=itemgetter(\"rssi\"))",
            "code": """from operator import itemgetter  ## itemgetter('rssi') is a fast, named alternative to lambda d: d['rssi']


def main() -> None:
    raw = ["-54", "-61", "-48", "-77"]  ## RSSI values parsed from text
    rssi = list(map(int, raw))  ## Apply int to every item; list() forces the lazy map to run
    print(rssi)  ## Now real ints
    strong = list(filter(lambda r: r > -60, rssi))  ## Keep only values stronger than -60 dBm
    print(strong)  ## Two survivors
    lazy = map(int, raw)  ## A map object: nothing has been computed yet
    print(type(lazy).__name__, next(lazy), list(lazy), list(lazy))  ## next() takes one item, list() takes the rest, the second list() finds it empty
    scan = [  ## Scan results as dicts
        {"bssid": "ap-3", "band": "6G", "rssi": -61},  ## 6 GHz, weaker
        {"bssid": "ap-1", "band": "5G", "rssi": -48},  ## 5 GHz, strongest overall
        {"bssid": "ap-2", "band": "5G", "rssi": -70},  ## 5 GHz, weakest
        {"bssid": "ap-4", "band": "6G", "rssi": -52},  ## 6 GHz, stronger
    ]
    ranked = sorted(scan, key=lambda s: (s["band"], -s["rssi"]))  ## Tuple key: band A-Z, then RSSI strongest first (negated)
    print([s["bssid"] for s in ranked])  ## The order produced by the two-part key
    print(max(scan, key=itemgetter("rssi"))["bssid"])  ## Highest RSSI value wins; max returns the whole dict
    names = ["ap-10", "ap-2", "ap-1"]  ## Names with numbers inside
    print(sorted(names), sorted(names, key=lambda n: int(n.split("-")[1])))  ## Text order puts ap-10 before ap-2; a numeric key fixes it


if __name__ == "__main__":
    main()""",
            "under": "`map` and `filter` are iterator objects holding the function and an iterator over the input; each `next()` pulls one input item and processes it. Sorting with a key computes `key(item)` exactly once per item (decorate-sort-undecorate), then Timsort compares the keys. Tuples compare element by element, which is what makes multi-field keys work. Stability means items with equal keys keep their input order.",
            "gotchas": [
                {
                    "title": "Consuming a map or filter twice",
                    "note": "The second pass gets nothing, silently. Convert to a list if you need the values more than once.",
                    "wrong": """values = map(float, ["910.2", "905.7"])
print(sum(values), max(values, default="empty!"))""",
                    "fixed": """values = list(map(float, ["910.2", "905.7"]))
print(sum(values), max(values))""",
                },
                {
                    "title": "Sorting mixed types",
                    "note": "Python 3 refuses to order unrelated types. Normalise first (here: convert all channels to int).",
                    "wrong": """print(sorted([36, "40", 44]))""",
                    "fixed": """print(sorted(int(c) for c in [36, "40", 44]))""",
                },
            ],
            "best": "Prefer comprehensions (Module 2.4) when the transformation needs a lambda; use `map` with existing functions (`map(int, xs)`). Put ranking rules into a key function with a tuple, and negate numeric fields to reverse just one part.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Convert `['36', '40', '149']` to ints with map and print their sum.",
            "solution": "`sum(map(int, ...))` consumes the iterator once, which is fine here.",
            "solution_code": """print(sum(map(int, ["36", "40", "149"])))""",
        },
        {
            "level": "Medium",
            "prompt": "From test results `(name, verdict, duration_s)`, list the names of failed tests ordered by duration, longest first.",
            "solution": "filter on the verdict, then sorted with a key and reverse=True.",
            "solution_code": """results = [("roam_11r", "FAIL", 42.0), ("tput_5g", "PASS", 30.5), ("dfs_cac", "FAIL", 61.2), ("assoc_wpa3", "FAIL", 8.3)]
failed = filter(lambda r: r[1] == "FAIL", results)
print([r[0] for r in sorted(failed, key=lambda r: r[2], reverse=True)])""",
        },
        {
            "level": "Hard",
            "prompt": "Rank stations first by band preference 6G > 5G > 2G, then by RSSI strongest first, using a single sort.",
            "solution": "Map each band to a priority number inside the key, and negate RSSI.",
            "solution_code": """PRIORITY = {"6G": 0, "5G": 1, "2G": 2}
stas = [("aa:01", "5G", -50), ("aa:02", "6G", -66), ("aa:03", "2G", -40), ("aa:04", "6G", -58)]
for row in sorted(stas, key=lambda s: (PRIORITY[s[1]], -s[2])):
    print(row)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What do map() and filter() return in Python 3?", "a": "Lazy iterators, not lists. They compute values on demand and can be consumed only once. Wrap them in `list()` if you need the values again.", "follow": "Why lazy? (Memory: they can process huge or infinite inputs one item at a time.)"},
        {"level": "Intermediate", "q": "How do you sort by two fields, one ascending and one descending?", "a": "Use a tuple key and negate the numeric field: `key=lambda s: (s['band'], -s['rssi'])`. For non-numeric fields, sort twice relying on stability: first by the secondary key, then by the primary.", "follow": "What does 'stable' guarantee? (Equal keys keep their original relative order.)"},
        {"level": "Intermediate", "q": "map/filter or a comprehension?", "a": "Comprehensions are usually clearer, especially when you would need a lambda. `map` is neat with an existing function (`map(int, xs)`). Performance is similar; readability decides.", "follow": "Which is lazy? (map/filter and generator expressions; list comprehensions build the list immediately.)"},
        {"level": "Advanced", "q": "How many times is the key function called when sorting n items?", "a": "Exactly n times: Python computes all keys first, then sorts the keys. That's why an expensive key is still acceptable, and why `functools.cmp_to_key` exists only for legacy comparison functions.", "follow": "What does itemgetter give you over a lambda? (A small speedup, a readable name, and support for several keys: `itemgetter('band', 'rssi')`.)"},
    ],
    "quiz": [
        {"q": "What does `list(filter(None, [0, 1, '', 'a']))` return?", "options": ["[0, '']", "[1, 'a']", "[0, 1, '', 'a']", "[]"], "answer": 1, "why": "With None as the function, filter keeps truthy items."},
        {"q": "`m = map(int, ['1','2']); list(m); list(m)` — what is the second result?", "options": ["[1, 2]", "[]", "None", "Error"], "answer": 1, "why": "The iterator was already exhausted."},
        {"q": "Which key sorts by band ascending, then RSSI strongest first?", "options": ["(s['band'], s['rssi'])", "(s['band'], -s['rssi'])", "(-s['band'], s['rssi'])", "s['rssi']"], "answer": 1, "why": "Negating RSSI reverses only that part."},
        {"q": "`sorted(['ap-10', 'ap-2'])` gives?", "options": ["['ap-2', 'ap-10']", "['ap-10', 'ap-2']", "Error", "['ap-10']"], "answer": 1, "why": "Strings compare character by character: '1' < '2'."},
        {"q": "What does max(items, key=f) return?", "options": ["The largest f(item)", "The item with the largest f(item)", "The index", "A list"], "answer": 1, "why": "The key only drives the comparison."},
    ],
    "cards": [
        {"front": "map/filter return type", "back": "Lazy, single-use iterators."},
        {"front": "Multi-key sort, mixed direction", "back": "Tuple key with negated numeric field."},
        {"front": "Sort stability", "back": "Equal keys keep their original order."},
        {"front": "itemgetter('rssi')", "back": "A callable equivalent to `lambda d: d['rssi']`."},
    ],
}
