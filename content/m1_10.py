"""Phase 1 content: module 1.10."""

M_1_10 = {
    "id": "1.10",
    "title": "Mutability, Copying, is vs ==, Truthiness",
    "hours": 2,
    "summary": "Aliasing bugs, shallow vs deep copies, identity vs equality, and the values Python treats as false. The most common source of silent test-framework bugs.",
    "concepts": [
        {
            "title": "Mutability and aliasing",
            "concept": "A variable is a **name that points to an object**. Mutable objects (list, dict, set) can be changed in place; immutable ones (int, float, str, tuple, frozenset) never change. When two names point to the same mutable object, a change made through one name is visible through the other. This is **aliasing**.",
            "why": "Most \"test 3 fails only when test 2 runs first\" bugs come from aliasing: a shared baseline config, station list or matrix row is modified by one test and every later test sees the modified version.",
            "syntax": "b = a            # same object, no copy\nb.append(x)      # mutates that one object (visible via a and b)\nb = b + [x]      # builds a NEW object and rebinds only b\n\n# Immutable: int, float, complex, bool, str, bytes, tuple, frozenset, None\n# Mutable:   list, dict, set, bytearray, most class instances",
            "code": """def main() -> None:
    x = 10  ## Binds `x` to the int object 10
    y = x  ## `y` points to the same int object
    y += 1  ## int is immutable, so this builds a new object 11 and rebinds `y`; `x` still points to 10
    print(f"x={x}, y={y}")  ## Shows that immutables can't be changed through an alias
    a = [1, 2, 3]  ## A list object, bound to `a`
    b = a  ## `b` is an alias for the same list
    b.append(4)  ## Mutates that single list in place
    print(f"a={a}, b={b}, same object? {a is b}")  ## Both names see the change; `is` confirms one object
    nums = [1, 2]  ## Another list
    before = id(nums)  ## Record its identity
    nums += [3]  ## For lists, += calls __iadd__, which extends IN PLACE
    print(f"list += keeps identity: {id(nums) == before}")  ## True: still the same object
    t = (1, 2)  ## A tuple
    before = id(t)  ## Record its identity
    t += (3,)  ## Tuples have no __iadd__, so Python builds a new tuple and rebinds `t`
    print(f"tuple += keeps identity: {id(t) == before}")  ## False: a different object


if __name__ == "__main__":
    main()""",
            "under": "Each scope has a namespace mapping names to object references. `y = x` copies a reference and bumps the object's reference count. `a += b` first tries `a.__iadd__(b)`; if the type doesn't define it, Python falls back to `a = a.__add__(b)`. That is why `+=` mutates lists but rebinds tuples, strings and ints.",
            "gotchas": [
                {
                    "title": "The shared baseline config",
                    "note": "The helper returns the same dict every time, so all three names end up showing channel 44 and the baseline itself is corrupted. Copy before you modify.",
                    "wrong": """BASE_CONFIG = {"band": "5G", "channel": 36, "ssids": ["lab-open"]}

def make_test_config(channel):
    cfg = BASE_CONFIG
    cfg["channel"] = channel
    return cfg

t1 = make_test_config(149)
t2 = make_test_config(44)
print(t1["channel"], t2["channel"], BASE_CONFIG["channel"])""",
                    "fixed": """import copy

BASE_CONFIG = {"band": "5G", "channel": 36, "ssids": ["lab-open"]}

def make_test_config(channel):
    cfg = copy.deepcopy(BASE_CONFIG)
    cfg["channel"] = channel
    return cfg

t1 = make_test_config(149)
t2 = make_test_config(44)
print(t1["channel"], t2["channel"], BASE_CONFIG["channel"])""",
                },
                {
                    "title": "+= on a list inside a tuple",
                    "note": "The list's __iadd__ succeeds and mutates the list; then storing the result back into the tuple fails. You get an exception AND a modified object.",
                    "wrong": """t = ([1, 2], 3)
try:
    t[0] += [4]
except TypeError as e:
    print("Error:", e)
print(t)""",
                    "fixed": """t = ([1, 2], 3)
t[0].extend([4])
print(t)""",
                },
            ],
            "best": "Treat shared module-level data as read-only. Build fresh objects inside functions, or copy deliberately. For configs that must never change, use `types.MappingProxyType` (a read-only view) or a frozen dataclass (Module 3.6).",
        },
        {
            "title": "Shallow copy vs deep copy",
            "concept": "A **shallow copy** creates a new outer container whose items still point to the same objects. A **deep copy** recursively copies everything so nothing is shared. They behave the same for containers of immutable items and differ as soon as nested mutable objects are involved.",
            "why": "Test configs are nested (radios -> bands -> SSID lists). A shallow copy looks safe, but nested edits leak back into the original.",
            "syntax": "import copy\ns = copy.copy(x)       # shallow; also x.copy(), list(x), dict(x), x[:]\nd = copy.deepcopy(x)   # deep, recursive",
            "code": """import copy  ## Standard-library copy and deepcopy


def main() -> None:
    base = {"band": "5G", "channel": 36, "ssids": ["lab-open"]}  ## A dict with an immutable str, an int and a MUTABLE list
    alias = base  ## A second name, no copy at all
    shallow = copy.copy(base)  ## New dict, but its values are the same objects
    deep = copy.deepcopy(base)  ## New dict AND a new list inside it
    shallow["channel"] = 149  ## Rebinding a top-level key only affects the shallow copy
    shallow["ssids"].append("lab-wpa3")  ## Mutates the list that `base` also points to: the leak
    deep["ssids"].append("lab-owe")  ## Mutates deep's private list; `base` is unaffected
    print("base   :", base)  ## Shows the leaked SSID
    print("shallow:", shallow)  ## Own channel, shared SSID list
    print("deep   :", deep)  ## Fully independent
    print("alias is base:", alias is base)  ## The alias is literally the same object
    print("shared nested list (shallow):", shallow["ssids"] is base["ssids"])  ## True: shared
    print("shared nested list (deep):   ", deep["ssids"] is base["ssids"])  ## False: separate


if __name__ == "__main__":
    main()""",
            "under": "`deepcopy` walks the object graph recursively and keeps a `memo` dict of objects it has already copied, which handles self-references and shared sub-objects without infinite recursion. It uses a class's `__deepcopy__` if defined, otherwise the pickle protocol (`__reduce_ex__`). Immutable atoms such as ints and strings are not copied at all, because sharing them is safe.",
            "gotchas": [
                {
                    "title": "The [[0]*3]*3 trap",
                    "note": "Multiplying a list of lists repeats the reference to ONE inner list.",
                    "wrong": """bad = [[0] * 3] * 3
bad[0][0] = 1
print(bad)""",
                    "fixed": """good = [[0] * 3 for _ in range(3)]
good[0][0] = 1
print(good)""",
                },
                {
                    "title": "Deep-copying live resources",
                    "note": "Locks, sockets, SSH sessions and serial ports can't be copied. Deep-copy the data, never the device objects.",
                    "wrong": """import copy, threading
copy.deepcopy({"lock": threading.Lock()})""",
                    "fixed": """import copy, threading
config = {"band": "5G", "ssids": ["lab"]}
lock = threading.Lock()
snapshot = copy.deepcopy(config)
print(snapshot, lock.locked())""",
                },
            ],
            "best": "Use `deepcopy` for nested configs and data. Keep configuration (plain data) separate from connections (resources) so copying config is always safe. For very large or performance-sensitive structures, construct new objects explicitly.",
        },
        {
            "title": "is vs ==",
            "concept": "`==` asks **do these have equal values?** and calls `__eq__`. `is` asks **are these the very same object?** and compares identity. Use `is` only for singletons (`None`, `True`, `False`, sentinel objects) or when you intentionally test identity.",
            "why": "`if result is None` is correct and idiomatic. `if count is 1000` is a bug that may pass on one machine and fail on another.",
            "syntax": "a == b       # value equality -> a.__eq__(b)\na is b       # identity       -> id(a) == id(b)\nx is None    # the correct None check",
            "code": """def main() -> None:
    a = [1, 2, 3]  ## One list
    b = [1, 2, 3]  ## A second list with equal contents
    c = a  ## An alias of the first
    print(a == b, a is b)  ## Equal values, different objects: True False
    print(a == c, a is c)  ## Same object, so trivially equal too: True True
    result = None  ## A 'no value yet' marker
    print(result is None)  ## None exists exactly once, so identity is the right test
    print(int("256") is int("256"))  ## True: CPython caches ints from -5 to 256
    print(int("1000") is int("1000"))  ## False: outside the cache each call builds a new object
    s1 = "wlan0"  ## A literal, interned by the compiler
    s2 = "".join(["wlan", "0"])  ## Built at runtime: equal text, different object
    print(s1 == s2, s1 is s2)  ## True False
    nan = float("nan")  ## IEEE 754 Not-a-Number
    print(nan == nan, [nan] == [nan])  ## NaN is never equal to itself, but list comparison checks identity first


if __name__ == "__main__":
    main()""",
            "under": "`is` compares two pointers and can't be overridden. `==` dispatches to `__eq__`, which your classes can define (Module 3.5). The small-int cache and string interning are CPython implementation details, not language guarantees. Python 3.8+ emits a SyntaxWarning for `x is 1000` written with a literal. Container comparisons use an identity shortcut before `==`, which is why `[nan] == [nan]` is True.",
            "gotchas": [
                {
                    "title": "Using is with numbers or strings",
                    "note": "It only works by accident (caching or interning). Use == for values, and is only for None and other singletons.",
                    "wrong": """rssi = int("-70")
status = "".join(["conn", "ected"])
print(status is "connected", rssi is -70)""",
                    "fixed": """rssi = int("-70")
status = "".join(["conn", "ected"])
reply = None
print(status == "connected", rssi == -70, reply is None)""",
                }
            ],
            "best": "Use `is` only for None, True/False and sentinel objects; use `==` everywhere else. Turn on the linter rule that flags `is` with literals (ruff F632) in CI.",
        },
        {
            "title": "Truthiness",
            "concept": "Every object has a truth value in `if`, `while`, `and`, `or` and `not`. Empty containers, numeric zeros and None are **falsy**; almost everything else is **truthy**. Python calls `__bool__`, falls back to `__len__`, and otherwise treats the object as true.\n\nFalsy: `None`, `False`, `0`, `0.0`, `0j`, `Decimal(0)`, `Fraction(0)`, `\"\"`, `b\"\"`, `()`, `[]`, `{}`, `set()`, `range(0)`.",
            "why": "`if not stations:` is idiomatic for \"the list is empty\". But truthiness treats 0, 0.0 and \"\" as missing, and in a lab 0 dB attenuation and 0 Mbps throughput are real measurements.",
            "syntax": "if value: ...        # truthy branch\nif not value: ...    # falsy branch\nbool(value)          # explicit truth value\nif value is None: ...  # 'missing', with 0 still allowed",
            "code": """def describe(value: object) -> str:  ## Accepts any object
    return "truthy" if value else "falsy"  ## Uses the value's truthiness directly


class ScanResult:  ## preview: classes are taught in Module 3.1
    def __init__(self, bssids: list[str]) -> None:  ## Stores the BSSIDs found
        self.bssids = bssids  ## Attribute on the object

    def __len__(self) -> int:  ## Makes len(scan) work...
        return len(self.bssids)  ## ...and Python also uses it for truthiness


def main() -> None:
    for v in [0, 0.0, "", "0", [], [0], {}, None, False, " ", -1]:  ## Falsy values and tricky truthy ones
        print(f"{v!r:>6} -> {describe(v)}")  ## repr() so strings show their quotes; right-aligned in 6 columns
    print(bool(ScanResult([])), bool(ScanResult(["aa:bb:cc:dd:ee:ff"])))  ## Empty scan is falsy, non-empty is truthy


if __name__ == "__main__":
    main()""",
            "under": "`bool(x)` calls `type(x).__bool__(x)` if it exists; otherwise `__len__(x)` and treats 0 as False; otherwise returns True. That is why every custom object is truthy unless its class says otherwise.",
            "gotchas": [
                {
                    "title": "0 dB is a real value",
                    "note": "`not db` is True for 0, so an explicit request for 0 dB is replaced by the default.",
                    "wrong": """def set_attenuation(db=None):
    if not db:
        return "using default 30 dB"
    return f"setting {db} dB"

print(set_attenuation(0))""",
                    "fixed": """def set_attenuation(db=None):
    if db is None:
        return "using default 30 dB"
    return f"setting {db} dB"

print(set_attenuation(0), "|", set_attenuation())""",
                }
            ],
            "best": "Use `if not items:` for \"is this container empty?\" (PEP 8 style). Use `if x is None:` whenever 0, \"\" or False are legitimate values, which covers most measurements, offsets and attenuation levels.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Predict the output: `a = [1, 2]; b = a; a = a + [3]; print(a, b)`.",
            "solution": "`[1, 2, 3] [1, 2]`. `a + [3]` builds a new list and rebinds only `a`. With `a += [3]` both would print `[1, 2, 3]`.",
            "solution_code": "a = [1, 2]\nb = a\na = a + [3]\nprint(a, b)",
        },
        {
            "level": "Medium",
            "prompt": "Write `merge_config(base, override)` that merges nested dicts recursively into a NEW dict without modifying either input.",
            "solution": "Deep-copy the base, recurse where both sides hold dicts, and deep-copy any value taken from the override so nothing is shared.",
            "solution_code": """import copy


def merge_config(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


defaults = {"country": "IN", "radios": {"5G": {"channel": 36, "width": 80}, "6G": {"channel": 37, "width": 320}}}
override = {"radios": {"5G": {"channel": 149}}}
print(merge_config(defaults, override))
print(defaults["radios"]["5G"])""",
        },
        {
            "level": "Hard",
            "prompt": "A matrix builder returns 4 rows that all say channel 149, width 160. Find the bug and fix it.\n\n`row = {...}` is created once before the loops and appended on every iteration.",
            "solution": "There is only ONE row dict. Each append adds another reference to it, and each iteration overwrites it. Create a new dict inside the loop.",
            "solution_code": """def build_matrix(channels, widths):
    matrix = []
    for ch in channels:
        for w in widths:
            matrix.append({"channel": ch, "width": w, "result": None})
    return matrix


m = build_matrix([36, 149], [80, 160])
print(m)
print(len(set(map(id, m))) == len(m))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Is Python pass-by-value or pass-by-reference?", "a": "Neither: it is pass-by-object-reference (pass-by-assignment). The parameter becomes a new name bound to the same object. If the function mutates a mutable argument, the caller sees it; if it rebinds the parameter, the caller does not.", "follow": "How do you protect the caller's list? (Copy it inside the function, or accept a tuple.)"},
        {"level": "Intermediate", "q": "What is the difference between a shallow and a deep copy?", "a": "A shallow copy makes a new container whose items are the same objects. A deep copy recursively duplicates nested objects. They differ only when the container holds mutable objects.", "follow": "Why can deepcopy fail? (Objects holding OS resources such as locks and sockets can't be copied; classes may also define __deepcopy__.)"},
        {"level": "Beginner", "q": "What does [[0]*3]*3 produce, and why is it dangerous?", "a": "Three references to the same inner list, so writing one row changes all rows. Use `[[0]*3 for _ in range(3)]`.", "follow": "Is [0]*3 itself safe? (Yes, because ints are immutable.)"},
        {"level": "Intermediate", "q": "When should you use is instead of ==?", "a": "Only for identity: None, True/False and sentinel objects. Using is with literals relies on CPython caching (ints -5..256, interned strings), which is an implementation detail.", "follow": "Why is [nan] == [nan] True? (List comparison checks identity before calling __eq__.)"},
        {"level": "Intermediate", "q": "What makes an object falsy? Give a case where `if not x` is a bug.", "a": "Python calls __bool__, then __len__, and defaults to True. The bug: `if not attenuation_db:` treats 0 dB as missing; use `if attenuation_db is None:`.", "follow": "How do you make your own class falsy when empty? (Define __len__ or __bool__.)"},
        {"level": "Advanced", "q": "Why does `t[0] += [4]` both raise TypeError and modify the tuple's list?", "a": "`+=` runs in two steps: `list.__iadd__` mutates the list in place (succeeds), then Python tries `t[0] = result`, and tuple item assignment fails. The mutation has already happened.", "follow": "How would you write it safely? (`t[0].extend([4])`, which never assigns into the tuple.)"},
    ],
    "quiz": [
        {"q": "After `x = [1]; y = x; y = y + [2]`, what is x?", "options": ["[1]", "[1, 2]", "[2]", "None"], "answer": 0, "why": "y + [2] builds a new list and rebinds y only."},
        {"q": "A shallow copy shares which objects with the original?", "options": ["None", "The outer container", "The nested (inner) objects", "Only strings"], "answer": 2, "why": "It creates a new container holding the same item objects."},
        {"q": "Why is `if count is 1000:` unreliable?", "options": ["It is a SyntaxError", "Identity of ints depends on CPython caching", "is is slower", "It always raises"], "answer": 1, "why": "Only -5..256 are cached; other equal ints may be different objects."},
        {"q": "Which value is truthy?", "options": ["0.0", "''", "'0'", "[]"], "answer": 2, "why": "A non-empty string is truthy, even '0'."},
        {"q": "What does `[[0]*2]*2` become after `m[0][0] = 9`?", "options": ["[[9, 0], [0, 0]]", "[[9, 0], [9, 0]]", "[[9, 9], [0, 0]]", "Error"], "answer": 1, "why": "Both rows are the same list."},
    ],
    "cards": [
        {"front": "Mutable built-ins", "back": "list, dict, set, bytearray (plus most class instances)"},
        {"front": "Shallow vs deep copy", "back": "New container, shared items vs fully independent recursive copy."},
        {"front": "[[0]*3]*3", "back": "Three references to ONE inner list. Use a comprehension."},
        {"front": "When to use `is`", "back": "None, True/False and sentinels only."},
        {"front": "bool(x) lookup order", "back": "__bool__, then __len__, else True."},
        {"front": "`if not db:` bug", "back": "Treats 0 as missing. Use `if db is None:`."},
    ],
}
