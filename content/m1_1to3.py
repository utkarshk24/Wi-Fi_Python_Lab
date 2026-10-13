"""Phase 1 content: modules 1.1-1.3.

Annotated code uses `  ## ` to separate the code from its explanation.
Standard lines (def main, the __main__ guard) are annotated automatically by build.py.
"""

M_1_1 = {
    "id": "1.1",
    "title": "Objects, Variables & References",
    "hours": 2,
    "summary": "Names point to objects. Every object has an identity, a type and a value, and assignment never copies.",
    "concepts": [
        {
            "title": "Names, objects and identity",
            "concept": "In Python a variable is a **name bound to an object**. The object lives in memory and carries three things: an **identity** (`id()`), a **type** (`type()`) and a **value**. Assignment (`=`) makes a name point to an object; it never copies the object. Rebinding a name to another object leaves every other name alone.",
            "why": "Test frameworks pass the same config dicts, station lists and device objects around constantly. Knowing that two names can share one object is the difference between a clean suite and one where a test silently corrupts the next test's setup.",
            "syntax": "name = expression      # bind name to the object the expression produces\nid(obj)                # identity: an int unique while obj is alive\ntype(obj)              # the object's class\nother = name           # second name for the SAME object",
            "code": """def main() -> None:
    rssi = -54  ## Binds the name `rssi` to an int object whose value is -54
    print(type(rssi), id(rssi) > 0)  ## Every object has a type (`int`) and an identity (a positive integer in CPython)
    alias = rssi  ## A second name for the same object; nothing is copied
    print(alias is rssi)  ## `is` compares identity, so this is True: one object, two names
    rssi = -60  ## Rebinding: `rssi` now points to a different object; `alias` still points to -54
    print(rssi, alias)  ## Shows the two names now refer to different objects
    ap_name = "lab-ap-01"  ## Strings are objects too, with their own type
    print(isinstance(ap_name, str), type(ap_name).__name__)  ## isinstance() checks the type; `__name__` gives the class name as text
    value = 42  ## `value` points to an int
    value = "forty-two"  ## Dynamic typing: the same name can later point to an object of another type
    print(type(value).__name__)  ## The type belongs to the object, not to the name


if __name__ == "__main__":
    main()""",
            "under": "In CPython every object is a C struct (`PyObject`) holding a **reference count** and a pointer to its type. A namespace (module globals, function locals) maps names to object pointers. `x = y` copies a pointer and increments the object's reference count. When the count reaches zero the object is freed. `id()` in CPython is the object's memory address, which is why an id can be reused after an object is destroyed.",
            "gotchas": [
                {
                    "title": "Shadowing a built-in name",
                    "note": "Naming a variable `list`, `str`, `id` or `type` hides the built-in for the rest of that scope. The error appears far away from the line that caused it.",
                    "wrong": """list = ["aa:01", "aa:02"]
print(list("abc"))""",
                    "fixed": """stations = ["aa:01", "aa:02"]
print(list("abc"))""",
                }
            ],
            "best": "Choose descriptive names (`stations`, `rssi_dbm`, `base_config`) and never reuse built-in names. Use `is` only to test identity, and think of `=` as attaching a label to an object.",
        },
        {
            "title": "Dynamic and strong typing; type() vs isinstance()",
            "concept": "Python is **dynamically typed**: types are checked at runtime and belong to objects, not names. It is also **strongly typed**: it refuses to silently mix incompatible types (`\"ch\" + 36` raises `TypeError`). `type(x)` returns the exact class. `isinstance(x, cls)` also accepts subclasses, which is usually what you want.",
            "why": "Parsed log values arrive as strings. Mixing them with ints raises errors that you must fix with explicit conversion. Validating inputs (channels, attenuation values) means knowing when `isinstance` is too permissive.",
            "syntax": "type(x) is int          # exact type only\nisinstance(x, int)      # int or any subclass of int (bool included!)\nisinstance(x, (int, float))  # any of several types",
            "code": """def main() -> None:
    channel = 36  ## An int that we want to put into a label
    try:  ## preview: try/except is taught in Module 2.5; it catches the error so the script continues
        label = "ch" + channel  ## str + int is not allowed: Python is strongly typed
    except TypeError as err:  ## Catches the TypeError and binds it to `err`
        print("TypeError:", err)  ## Prints Python's explanation of the problem
    label = "ch" + str(channel)  ## Explicit conversion with str() makes the types compatible
    print(label)  ## ch36
    print(type(True) is int, isinstance(True, int))  ## bool is a subclass of int: exact type differs, isinstance says yes
    for v in [36, 36.0, "36", None]:  ## Four values that all "look like" 36 in a log
        print(f"{v!r:>6} -> {type(v).__name__}")  ## `!r` shows repr (quotes on strings); `>6` right-aligns in 6 columns


if __name__ == "__main__":
    main()""",
            "under": "Each object stores a pointer to its type object, and operators look up methods on that type at runtime. `\"ch\" + 36` calls `str.__add__(\"ch\", 36)`, which returns `NotImplemented` for an int. Python then tries `int.__radd__`, which also refuses, so it raises `TypeError`. `isinstance` walks the class's method resolution order (MRO), which for `bool` is `bool -> int -> object`.",
            "gotchas": [
                {
                    "title": "bool sneaks through isinstance(x, int)",
                    "note": "A config parser that validates channels with `isinstance(value, int)` accepts `True` as channel 1. Exclude bool explicitly when it matters.",
                    "wrong": """def valid_channel(value):
    return isinstance(value, int) and value > 0

print(valid_channel(True))""",
                    "fixed": """def valid_channel(value):
    return type(value) is int and value > 0

print(valid_channel(True), valid_channel(36))""",
                }
            ],
            "best": "Prefer `isinstance` for normal type checks because it respects inheritance. Use `type(x) is T` only when subclasses must be rejected, such as bool vs int. Convert parsed strings explicitly (`int()`, `float()`) at the boundary where data enters your program.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Predict the output, then run it.",
            "code": "a = 5\nb = a\na = a + 1\nprint(a, b)",
            "solution": "`6 5`. Ints are immutable, so `a + 1` creates a new object and rebinds only `a`. `b` still points to `5`.",
            "solution_code": "a = 5\nb = a\na = a + 1\nprint(a, b)",
        },
        {
            "level": "Medium",
            "prompt": "Write `is_real_int(value)` that returns True only for genuine ints. It must reject bool, float and numeric strings.",
            "solution": "Use an exact type check, because `isinstance(True, int)` is True.",
            "solution_code": """def is_real_int(value: object) -> bool:
    return type(value) is int


for v in [36, True, 36.0, "36", -3]:
    print(repr(v), is_real_int(v))""",
        },
        {
            "level": "Hard",
            "prompt": "Predict all prints and explain them using identity: `stations = ['sta1']`, `backup = stations`, `stations = stations + ['sta2']`, `backup.append('sta3')`.",
            "solution": "`stations + ['sta2']` builds a **new** list and rebinds `stations`, so `backup` keeps the original list. `backup.append` then mutates that original list only. The identities differ after the rebinding.",
            "solution_code": """stations = ["sta1"]
backup = stations
print(stations is backup)
stations = stations + ["sta2"]
backup.append("sta3")
print(stations, backup, stations is backup)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What is a variable in Python?", "a": "A name bound to an object. The object holds the type and value; the name is only a reference. Assignment binds a name and never copies the object.", "follow": "What happens to the object when no names refer to it? (Its reference count reaches zero and CPython frees it.)"},
        {"level": "Beginner", "q": "Is Python statically or dynamically typed? Strongly or weakly?", "a": "Dynamically typed: types are attached to objects and checked at runtime. Strongly typed: it does not silently coerce incompatible types, so `\"1\" + 1` raises `TypeError` instead of producing `\"11\"` or `2`.", "follow": "How do type hints change this? (They don't. Hints are for tools like mypy and have no runtime effect.)"},
        {"level": "Intermediate", "q": "What is the difference between type() and isinstance()?", "a": "`type(x)` returns the exact class. `isinstance(x, C)` returns True for C or any subclass. Use `isinstance` normally; use `type(x) is C` when subclasses must be excluded, such as rejecting bool where an int is required.", "follow": "Why is isinstance(True, int) True? (bool subclasses int.)"},
        {"level": "Intermediate", "q": "What does id() return, and can two objects have the same id?", "a": "An integer unique to the object **while it is alive**; in CPython it is the memory address. Two objects that exist at the same time never share an id, but an id can be reused after an object is freed.", "follow": "Why can `id([]) == id([])` print True? (The first list is freed before the second is created, so the address is reused.)"},
        {"level": "Advanced", "q": "Is everything in Python an object?", "a": "Yes. Ints, functions, classes, modules and even types are objects with identity, type and value. That is why functions can be stored in dicts, passed as arguments and returned from other functions.", "follow": "What is the type of a class? (`type`, the default metaclass.)"},
    ],
    "quiz": [
        {"q": "After `x = 10; y = x; x = 20`, what is `y`?", "options": ["10", "20", "None", "It raises NameError"], "answer": 0, "why": "`x = 20` rebinds `x` only. `y` still points to the object 10."},
        {"q": "Which call returns True?", "options": ["type(True) is int", "isinstance(True, int)", "isinstance(1.0, int)", "type('1') is int"], "answer": 1, "why": "bool is a subclass of int, so isinstance accepts it while the exact type check does not."},
        {"q": "What does `\"ch\" + 36` do?", "options": ["Returns 'ch36'", "Returns 'ch 36'", "Raises TypeError", "Returns None"], "answer": 2, "why": "Python is strongly typed and refuses to add str and int. Use `\"ch\" + str(36)`."},
        {"q": "What does `=` do in `b = a`?", "options": ["Copies the value of a into b", "Binds b to the same object as a", "Creates a deep copy", "Compares a and b"], "answer": 1, "why": "Assignment binds a name to an object; no copy is made."},
        {"q": "Why is `list = [1, 2]` a bad idea?", "options": ["It is a SyntaxError", "It hides the built-in list() in that scope", "Lists can't be assigned to names", "It makes the list immutable"], "answer": 1, "why": "Shadowing built-ins breaks later calls such as `list('abc')`."},
    ],
    "cards": [
        {"front": "What three things does every Python object have?", "back": "An identity (`id()`), a type (`type()`) and a value."},
        {"front": "Does `b = a` copy the object?", "back": "No. It binds `b` to the same object as `a`."},
        {"front": "Dynamic vs strong typing in Python", "back": "Dynamic: types live on objects and are checked at runtime. Strong: no silent coercion between incompatible types."},
        {"front": "type(x) is C vs isinstance(x, C)", "back": "Exact class only vs class or any subclass."},
        {"front": "What is id(x) in CPython?", "back": "The object's memory address; unique only while the object is alive."},
    ],
}


M_1_2 = {
    "id": "1.2",
    "title": "Numbers, bool, None & Operators",
    "hours": 2,
    "summary": "Integer and float arithmetic, floor division, float precision, bool and None, short-circuit logic and bitwise field decoding.",
    "concepts": [
        {
            "title": "Numbers and arithmetic",
            "concept": "`int` has **arbitrary precision**, so it never overflows. `float` is an IEEE 754 double with about 15–17 significant digits, which means many decimal fractions (0.1, 0.2) cannot be stored exactly. `/` always returns a float. `//` is **floor** division (it rounds toward minus infinity) and `%` is the matching remainder. `round()` uses banker's rounding (ties go to the even neighbour).",
            "why": "Throughput thresholds, percentage deltas and timing maths all use floats. Comparing floats with `==` produces flaky pass/fail decisions. Floor division with negative values (dBm, offsets) surprises people who expect truncation.",
            "syntax": "a / b    # true division -> float\na // b   # floor division\na % b    # remainder (same sign as b)\ndivmod(a, b)  # (a // b, a % b)\na ** b   # power\nmath.isclose(x, y)  # safe float comparison",
            "code": """import math  ## Standard-library maths functions, including isclose()
from decimal import Decimal  ## Exact decimal arithmetic for money-like values


def main() -> None:
    print(2 ** 100)  ## ints grow as needed, no overflow
    print(7 / 2, 7 // 2, 7 % 2)  ## true division, floor division and remainder
    print(-7 // 2, -7 % 2)  ## floor goes toward minus infinity: -3.5 floors to -4, remainder is 1
    print(divmod(125, 60))  ## quotient and remainder in one call: 125 s is 2 min 5 s
    print(0.1 + 0.2, 0.1 + 0.2 == 0.3)  ## binary floats can't hold 0.1 exactly, so == fails
    print(math.isclose(0.1 + 0.2, 0.3))  ## compares within a relative tolerance (1e-09 by default)
    print(Decimal("0.1") + Decimal("0.2"))  ## Decimal built from strings is exact
    print(round(2.5), round(3.5), round(2.675, 2))  ## ties go to even; 2.675 is really 2.67499... in binary
    print(10 > 5 > 1, 1 < 3 < 2)  ## chained comparisons mean (10 > 5) and (5 > 1)


if __name__ == "__main__":
    main()""",
            "under": "Small ints are stored in a single machine word; larger ones switch to an array of 30-bit digits, which is why `2 ** 100` just works. A float is 64 bits: 1 sign bit, 11 exponent bits and 52 fraction bits. 0.1 in binary is a repeating fraction, so it is rounded to the nearest representable value. `0.1 + 0.2` lands one step above the double closest to 0.3.",
            "gotchas": [
                {
                    "title": "Comparing floats with ==",
                    "note": "A throughput check written with `==` against a computed value will fail randomly. Compare with a tolerance.",
                    "wrong": """measured = 0.1 * 3
print(measured == 0.3)""",
                    "fixed": """import math

measured = 0.1 * 3
print(math.isclose(measured, 0.3))""",
                },
                {
                    "title": "int() truncates, // floors",
                    "note": "They agree for positive numbers and disagree for negative ones, which matters for dBm and offsets.",
                    "wrong": """print(int(-3.5), -7 // 2)""",
                    "fixed": """import math

print(math.trunc(-3.5), math.floor(-3.5), -7 // 2)""",
                },
            ],
            "best": "Never compare computed floats with `==`; use `math.isclose` or an explicit tolerance such as `abs(a - b) <= 0.05 * baseline`. Use `Decimal` (built from strings) when exact decimal results matter. Format floats for display with f-strings rather than `round()`.",
        },
        {
            "title": "bool, None, logic and bitwise operators",
            "concept": "`bool` is a subclass of `int` (`True == 1`). `None` is a singleton meaning \"no value\". `and` / `or` **short-circuit** and return one of their operands, not necessarily a bool. Bitwise operators (`&`, `|`, `^`, `~`, `<<`, `>>`) act on the binary form of ints, which is exactly what you need to decode protocol fields.",
            "why": "802.11 frames are full of bit fields. The Frame Control field holds the frame type and subtype, and the Capability Information field is a 16-bit flag set. Decoding them with shifts and masks is a common interview task for Wi-Fi roles. dBm and mW conversion is everyday RF maths.",
            "syntax": "x & mask        # keep only the bits set in mask\nx | flag        # set a bit\n(x >> n) & 0b11 # extract a 2-bit field starting at bit n\n1 << k          # value with only bit k set\nf\"{x:08b}\"      # show x as 8 binary digits",
            "code": """import math  ## Needed for log10 in the mW -> dBm conversion


def dbm_to_mw(dbm: float) -> float:  ## preview: functions are taught in Module 2.1
    return 10 ** (dbm / 10)  ## P(mW) = 10^(dBm / 10)


def mw_to_dbm(mw: float) -> float:  ## The inverse conversion
    return 10 * math.log10(mw)  ## P(dBm) = 10 * log10(P in mW)


ESS = 1 << 0  ## Capability Information bit 0: the sender is an AP in an infrastructure BSS
PRIVACY = 1 << 4  ## Bit 4: encryption required
SHORT_SLOT = 1 << 10  ## Bit 10: short slot time in use
RADIO_MEASUREMENT = 1 << 12  ## Bit 12: 802.11k radio measurement supported


def main() -> None:
    fc_byte = 0x88  ## First Frame Control byte of a QoS Data frame
    frame_type = (fc_byte >> 2) & 0b11  ## Type lives in bits 2-3: shift right 2, keep 2 bits
    subtype = (fc_byte >> 4) & 0b1111  ## Subtype lives in bits 4-7: shift right 4, keep 4 bits
    print(f"type={frame_type} subtype={subtype} bits={fc_byte:08b}")  ## type 2 = Data, subtype 8 = QoS Data

    cap = 0x1411  ## A capability field with bits 0, 4, 10 and 12 set
    print("privacy on:", bool(cap & PRIVACY))  ## AND with the mask leaves a non-zero value only if the bit is set
    print("short slot:", bool(cap & SHORT_SLOT))  ## Same test for bit 10
    print("IBSS bit:", bool(cap & (1 << 1)))  ## Bit 1 (IBSS) is not set, so the result is 0, which is False

    print(f"{dbm_to_mw(20):.1f} mW, {dbm_to_mw(-30):.4f} mW")  ## 20 dBm is 100 mW; -30 dBm is 1 microwatt
    print(f"{mw_to_dbm(100):.1f} dBm")  ## Round trip back to 20 dBm

    print(True + True, None is None, bool(None))  ## bool is an int subclass; None is a singleton and is falsy
    timeout = 0  ## Imagine a user explicitly asked for a timeout of 0
    print(timeout or 30, 5 and 7, 0 and 7)  ## `or` returns the first truthy operand; `and` returns the first falsy one, else the last


if __name__ == "__main__":
    main()""",
            "under": "`and` evaluates its left operand and returns it immediately if it is falsy; otherwise it returns the right operand. `or` returns the left operand if it is truthy, otherwise the right one. This is short-circuit evaluation, so the right side may never run. Python ints behave as if they had infinite two's-complement sign extension, which is why `~5` is `-6`.",
            "gotchas": [
                {
                    "title": "`x or default` swallows legitimate zeros",
                    "note": "`or` treats 0, 0.0 and \"\" as missing. A 0 dB attenuation or a 0 s delay would silently be replaced by the default.",
                    "wrong": """attenuation_db = 0
print(attenuation_db or 30)""",
                    "fixed": """attenuation_db = 0
value = 30 if attenuation_db is None else attenuation_db
print(value)""",
                },
                {
                    "title": "Using `not` where you meant bitwise `~`, or the reverse",
                    "note": "`not` is logical negation and returns a bool. `~` flips every bit of an int. Clearing a flag needs `~` combined with `&`.",
                    "wrong": """cap = 0x1411
PRIVACY = 1 << 4
print(hex(cap & (not PRIVACY)))""",
                    "fixed": """cap = 0x1411
PRIVACY = 1 << 4
print(hex(cap & ~PRIVACY))""",
                },
            ],
            "best": "Name your bit masks as constants (`PRIVACY = 1 << 4`) instead of scattering magic numbers. Test a flag with `bool(value & MASK)`, set it with `value | MASK` and clear it with `value & ~MASK`. Use `is None` rather than `or` when 0 is a valid value.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Convert 125 seconds and 3725 seconds to `m:ss` and `h:mm:ss` using divmod.",
            "solution": "divmod gives the quotient and remainder in one step. Apply it twice for hours.",
            "solution_code": """total = 125
minutes, seconds = divmod(total, 60)
print(f"{minutes}:{seconds:02d}")

total = 3725
hours, rest = divmod(total, 3600)
minutes, seconds = divmod(rest, 60)
print(f"{hours}:{minutes:02d}:{seconds:02d}")""",
        },
        {
            "level": "Medium",
            "prompt": "Decode the first Frame Control byte 0x80 (a beacon) into protocol version, type and subtype.",
            "solution": "Version is bits 0-1, type bits 2-3, subtype bits 4-7. A beacon is type 0 (Management), subtype 8.",
            "solution_code": """fc_byte = 0x80
version = fc_byte & 0b11
frame_type = (fc_byte >> 2) & 0b11
subtype = (fc_byte >> 4) & 0b1111
print(version, frame_type, subtype)""",
        },
        {
            "level": "Hard",
            "prompt": "Two radios each transmit 17 dBm into the same combiner. What is the combined power in dBm? (Power in mW adds; dBm values don't.)",
            "solution": "Convert to mW, add, convert back. Doubling power adds about 3.01 dB.",
            "solution_code": """import math

total_mw = 2 * 10 ** (17 / 10)
print(f"{total_mw:.2f} mW = {10 * math.log10(total_mw):.2f} dBm")""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Why is 0.1 + 0.2 != 0.3 in Python?", "a": "Floats are IEEE 754 binary doubles. 0.1 and 0.2 are repeating fractions in binary, so they are stored as close approximations, and their sum is 0.30000000000000004. Compare with `math.isclose()` or use `Decimal` for exact decimal maths.", "follow": "How would you compare a measured throughput against a baseline? (With a relative tolerance, e.g. within 5%.)"},
        {"level": "Beginner", "q": "What is the difference between / and //?", "a": "`/` is true division and always returns a float. `//` is floor division: it rounds toward minus infinity, so `-7 // 2` is `-4`, not `-3`.", "follow": "What does -7 % 2 return? (1, because the remainder takes the sign of the divisor.)"},
        {"level": "Intermediate", "q": "What do `and` and `or` return?", "a": "One of their operands, not necessarily a bool. `a or b` returns `a` if it is truthy, otherwise `b`. `a and b` returns `a` if it is falsy, otherwise `b`. Both short-circuit, so the right side may never be evaluated.", "follow": "Why is `timeout or 30` risky? (A legitimate 0 is replaced by 30.)"},
        {"level": "Intermediate", "q": "How do you check whether bit 4 is set in an integer, set it and clear it?", "a": "Test with `bool(x & (1 << 4))`, set with `x | (1 << 4)`, clear with `x & ~(1 << 4)`. Naming the mask as a constant makes protocol code readable.", "follow": "How would you extract a 4-bit field starting at bit 4? (`(x >> 4) & 0xF`.)"},
        {"level": "Advanced", "q": "Why does round(2.5) return 2?", "a": "Python 3 uses round-half-to-even (banker's rounding), which avoids a systematic upward bias when many values are rounded. Separately, `round(2.675, 2)` gives 2.67 because 2.675 is stored as 2.67499999… in binary.", "follow": "How would you always round half up? (`Decimal(...).quantize(..., rounding=ROUND_HALF_UP)`.)"},
    ],
    "quiz": [
        {"q": "What is `-7 // 2`?", "options": ["-3", "-4", "-3.5", "3"], "answer": 1, "why": "Floor division rounds toward minus infinity."},
        {"q": "What does `0 or 'default'` evaluate to?", "options": ["0", "False", "'default'", "True"], "answer": 2, "why": "`or` returns the first truthy operand."},
        {"q": "Which expression tests whether bit 4 of `cap` is set?", "options": ["cap and 4", "cap & (1 << 4)", "cap | 16", "cap >> 4 == 1"], "answer": 1, "why": "AND with a mask that has only bit 4 set."},
        {"q": "What is `round(3.5)`?", "options": ["3", "4", "3.0", "4.0"], "answer": 1, "why": "Ties go to the even neighbour: 4 is even."},
        {"q": "Approximately what is 20 dBm in mW?", "options": ["2 mW", "20 mW", "100 mW", "1000 mW"], "answer": 2, "why": "10^(20/10) = 100 mW."},
    ],
    "cards": [
        {"front": "/ vs //", "back": "True division (float) vs floor division (rounds toward minus infinity)."},
        {"front": "How to compare floats safely", "back": "`math.isclose(a, b)` or an explicit tolerance."},
        {"front": "What do `and` / `or` return?", "back": "One of their operands; both short-circuit."},
        {"front": "Test, set and clear bit k", "back": "`x & (1<<k)`, `x | (1<<k)`, `x & ~(1<<k)`"},
        {"front": "dBm to mW", "back": "mW = 10 ** (dBm / 10); dBm = 10 * log10(mW)"},
        {"front": "round(2.5)", "back": "2. Python uses round-half-to-even."},
    ],
}


M_1_3 = {
    "id": "1.3",
    "title": "Strings & f-strings",
    "hours": 2.5,
    "summary": "Immutable text, the string methods you use to parse logs, f-string formatting for clean reports, and str vs bytes.",
    "concepts": [
        {
            "title": "String methods for parsing",
            "concept": "A `str` is an **immutable** sequence of Unicode characters. Every method returns a new string and leaves the original unchanged. The workhorses for parsing are `strip()`, `split()`, `partition()`, `startswith()`, `replace()`, `lower()` and `join()`.",
            "why": "Most lab data starts life as text: `iw` output, AP CLI output, syslog lines, iperf summaries. Clean, method-based parsing is faster to write and easier to read than regex for simple formats.",
            "syntax": "s.strip()            # remove surrounding whitespace\ns.split()            # split on runs of whitespace\ns.split(\"=\", 1)      # split on '=' at most once\nhead, sep, tail = s.partition(\":\")\n\":\".join(parts)      # glue a list of strings together",
            "code": """def main() -> None:
    line = "  wlan0: RSSI=-54 dBm  MCS=11  NSS=2  "  ## A raw line, with stray whitespace, as it might come from a tool
    clean = line.strip()  ## New string without leading or trailing whitespace
    print(repr(clean))  ## repr() shows the quotes, so you can see exactly where the string starts and ends
    iface, _, rest = clean.partition(":")  ## Splits at the first ':' into 3 parts; `_` is a throwaway name for the separator
    print(iface)  ## wlan0
    fields = rest.split()  ## No argument: split on any run of whitespace and drop empty pieces
    print(fields)  ## A list of the tokens after the colon
    stats = {}  ## preview: dicts are taught in Module 1.9
    for field in fields:  ## Go through each token
        if "=" in field:  ## `in` on strings tests for a substring
            key, value = field.split("=", 1)  ## maxsplit=1 keeps any later '=' inside the value
            stats[key] = value  ## Store the pair, still as text
    print(stats)  ## The parsed key/value pairs
    print(clean.startswith("wlan"), "MCS" in clean, clean.count("="))  ## Prefix test, substring test and occurrence count
    mac = "AA-BB-CC-11-22-33"  ## A MAC address in a vendor's dash format
    print(mac.replace("-", ":").lower())  ## Normalise to the common lower-case colon format
    print(":".join(["aa", "bb", "cc"]))  ## join() is called on the separator and takes an iterable of strings


if __name__ == "__main__":
    main()""",
            "under": "Because strings are immutable they can be hashed (used as dict keys) and safely shared between names. CPython stores each string in the most compact of three layouts (1, 2 or 4 bytes per character) depending on its widest character. Small identifier-like literals are often **interned** (stored once), which is an optimisation you must never rely on.",
            "gotchas": [
                {
                    "title": "split(\" \") is not split()",
                    "note": "With an explicit single-space separator, runs of spaces produce empty strings. Tool output is often aligned with multiple spaces.",
                    "wrong": """print("MCS=11  NSS=2".split(" "))""",
                    "fixed": """print("MCS=11  NSS=2".split())""",
                },
                {
                    "title": "Trying to change a string in place",
                    "note": "Strings are immutable. Build a new string instead.",
                    "wrong": """iface = "wlan0"
iface[0] = "W\"""",
                    "fixed": """iface = "wlan0"
iface = "W" + iface[1:]
print(iface)""",
                },
                {
                    "title": "Building big strings with += in a loop",
                    "note": "Each `+=` may create a new string, which is O(n²) in the worst case. Collect pieces in a list and join once.",
                    "wrong": """report = ""
for ch in [36, 40, 44]:
    report += f"ch{ch} ok\\n"
print(report, end="")""",
                    "fixed": """lines = [f"ch{ch} ok" for ch in [36, 40, 44]]
print("\\n".join(lines))""",
                },
            ],
            "best": "Strip input at the boundary, prefer `split()` over `split(\" \")`, use `partition` when you need exactly one split, and normalise identifiers (MACs, interface names) immediately to one canonical format. Build multi-line output with a list and one `join`.",
        },
        {
            "title": "f-strings, formatting and str vs bytes",
            "concept": "f-strings (`f\"...{expr}...\"`) embed expressions in text. After a colon you can add a **format spec**: width, alignment (`<` `>` `^`), precision (`.2f`), base (`b`, `x`), percentages (`%`) and more. `{expr=}` prints the expression and its value, which is handy for debugging. `str` holds text; `bytes` holds raw octets. You convert between them with `.encode()` and `.decode()`.",
            "why": "Aligned station tables and test summaries make Jenkins logs readable at 3 a.m. Sockets, serial consoles and pcaps deliver bytes, so you must decode them deliberately.",
            "syntax": "f\"{value:>8}\"      # right-align in 8 columns\nf\"{rate:9.1f}\"     # width 9, 1 decimal place\nf\"{n:08b}\"         # binary, zero-padded to 8 digits\nf\"{n:#06x}\"        # hex with 0x prefix, width 6\nf\"{ratio:.1%}\"     # percentage\nf\"{channel=}\"      # 'channel=149'",
            "code": """def main() -> None:
    stations = [("aa:bb:cc:00:00:01", -48, 1201.0), ("aa:bb:cc:00:00:02", -71, 288.24)]  ## (MAC, RSSI, rate) tuples; tuples are covered in Module 1.8
    print(f"{'MAC':<17} | {'RSSI':>5} | {'Rate':>9}")  ## Header: left-align MAC in 17 columns, right-align numbers
    print("-" * 37)  ## A string times an int repeats it; 17 + 3 + 5 + 3 + 9 = 37 columns
    for mac, rssi, rate in stations:  ## Unpacks each tuple into three names
        print(f"{mac:<17} | {rssi:>5} | {rate:>9.1f}")  ## Same widths as the header, rate with one decimal
    channel = 149  ## A value to debug-print
    print(f"{channel=}")  ## Prints the expression text and its value
    print(f"{0x88:08b} {255:x} {255:#06x} {0.8734:.1%}")  ## Binary, hex, hex with prefix and padding, percentage
    raw = "wlan0".encode("utf-8")  ## str -> bytes using UTF-8
    print(raw, type(raw).__name__, raw.decode())  ## bytes show a b'' prefix; decode() turns them back into str
    print(len("café"), len("café".encode()))  ## 4 characters, but 5 bytes, because é takes 2 bytes in UTF-8


if __name__ == "__main__":
    main()""",
            "under": "An f-string is compiled into code that evaluates each expression and calls `format(value, spec)`, which delegates to the object's `__format__` method. That is why dates, Decimals and your own classes can define their own format specs. Text sent over a socket or serial port must become bytes. UTF-8 uses 1–4 bytes per character, so character count and byte count differ for non-ASCII text.",
            "gotchas": [
                {
                    "title": "Mixing str and bytes",
                    "note": "Data from sockets, serial ports and `subprocess` (without text=True) is bytes. Decode it once at the boundary.",
                    "wrong": """chunk = b"RSSI=-54"
print(chunk.startswith("RSSI"))""",
                    "fixed": """chunk = b"RSSI=-54"
text = chunk.decode("utf-8", errors="replace")
print(text.startswith("RSSI"))""",
                },
            ],
            "best": "Use f-strings for all formatting. Keep column widths in one place when you print tables. Decode bytes to str as soon as they enter your program, with an explicit encoding and an `errors=` policy for noisy serial consoles.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Normalise these MAC addresses to lower-case colon format: `AA-BB-CC-00-11-22`, `aabb.cc00.1122`, `AA:BB:CC:00:11:22`.",
            "solution": "Remove every separator, lower-case, then re-insert a colon every 2 characters.",
            "solution_code": """def normalise_mac(mac: str) -> str:
    hex_digits = mac.replace("-", "").replace(":", "").replace(".", "").lower()
    return ":".join(hex_digits[i:i + 2] for i in range(0, 12, 2))


for m in ["AA-BB-CC-00-11-22", "aabb.cc00.1122", "AA:BB:CC:00:11:22"]:
    print(normalise_mac(m))""",
        },
        {
            "level": "Medium",
            "prompt": "Parse `\"tx bitrate: 1200.9 MBit/s 160MHz HE-MCS 11 HE-NSS 2\"` into rate (float), width (int), MCS (int) and NSS (int) using only string methods.",
            "solution": "Split into tokens, then read the value that follows each label.",
            "solution_code": """line = "tx bitrate: 1200.9 MBit/s 160MHz HE-MCS 11 HE-NSS 2"
tokens = line.split()
rate = float(tokens[2])
width = int(tokens[4].removesuffix("MHz"))
mcs = int(tokens[tokens.index("HE-MCS") + 1])
nss = int(tokens[tokens.index("HE-NSS") + 1])
print(rate, width, mcs, nss)""",
        },
        {
            "level": "Hard",
            "prompt": "Print a test summary table with columns Test (left, 22), Result (centred, 6) and Mbps (right, 8, one decimal), with a total row.",
            "solution": "Fix the widths once, use the same spec for every row, and compute the total with sum().",
            "solution_code": """rows = [("throughput_5g_80", "PASS", 912.44), ("throughput_6g_320", "PASS", 2841.0), ("roam_11r", "FAIL", 0.0)]
print(f"{'Test':<22}{'Result':^6}{'Mbps':>8}")
for name, result, mbps in rows:
    print(f"{name:<22}{result:^6}{mbps:>8.1f}")
print(f"{'TOTAL':<22}{'':^6}{sum(r[2] for r in rows):>8.1f}")""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Why are Python strings immutable?", "a": "Immutability lets strings be hashed (dict keys, set members), shared safely between names and threads, and cached or interned. Any 'modification' creates a new string.", "follow": "How do you efficiently build a long string? (Collect parts in a list and call `''.join(parts)`.)"},
        {"level": "Beginner", "q": "What is the difference between split() and split(' ')?", "a": "`split()` splits on runs of any whitespace and discards empty strings. `split(' ')` splits on every single space, so consecutive spaces produce empty strings.", "follow": "How do you split only on the first '='? (`s.split('=', 1)` or `s.partition('=')`.)"},
        {"level": "Intermediate", "q": "What is the difference between str and bytes?", "a": "`str` is a sequence of Unicode code points (text). `bytes` is a sequence of integers 0–255 (raw data). Convert with `encode()` and `decode()` and an explicit encoding. Sockets, serial ports and files opened in binary mode give you bytes.", "follow": "Why can len() differ between the two? (UTF-8 uses multiple bytes for non-ASCII characters.)"},
        {"level": "Intermediate", "q": "What does f\"{x=}\" do?", "a": "It prints the expression text, an equals sign and the value's repr, e.g. `x=149`. Available since Python 3.8; useful for quick debug output.", "follow": "Can you add a format spec? (Yes: `f\"{rate=:.1f}\"`.)"},
        {"level": "Advanced", "q": "What is string interning, and should you rely on it?", "a": "Interning stores one copy of a string so equal strings can share an object. CPython interns many identifier-like literals automatically, but it's an implementation detail. Always compare strings with `==`, never `is`.", "follow": "When might you intern manually? (`sys.intern()` for many repeated keys to save memory.)"},
    ],
    "quiz": [
        {"q": "What does `'a  b'.split(' ')` return?", "options": ["['a', 'b']", "['a', '', 'b']", "['a  b']", "['a', ' ', 'b']"], "answer": 1, "why": "Two consecutive spaces with an explicit separator produce an empty string."},
        {"q": "Which f-string right-aligns `x` in 8 columns with 2 decimals?", "options": ["f'{x:<8.2f}'", "f'{x:>8.2f}'", "f'{x:8.2}'", "f'{x:^8.2f}'"], "answer": 1, "why": "`>` aligns right, 8 is the width, `.2f` is two decimals."},
        {"q": "What is `len('café'.encode())`?", "options": ["4", "5", "6", "8"], "answer": 1, "why": "é takes two bytes in UTF-8."},
        {"q": "What does `'k=v=w'.split('=', 1)` return?", "options": ["['k', 'v', 'w']", "['k', 'v=w']", "['k=v', 'w']", "('k', '=', 'v=w')"], "answer": 1, "why": "maxsplit=1 stops after the first separator."},
        {"q": "What happens with `s = 'abc'; s[0] = 'x'`?", "options": ["s becomes 'xbc'", "TypeError", "s becomes 'x'", "IndexError"], "answer": 1, "why": "Strings are immutable."},
    ],
    "cards": [
        {"front": "split() vs split(' ')", "back": "Any whitespace run (no empties) vs every single space (empties possible)."},
        {"front": "Fast way to build a long string", "back": "Append parts to a list, then `''.join(parts)`."},
        {"front": "f-string debug form", "back": "`f\"{x=}\"` prints `x=<repr of x>`."},
        {"front": "str -> bytes and back", "back": "`s.encode('utf-8')` and `b.decode('utf-8')`"},
        {"front": "partition() returns", "back": "A 3-tuple: (head, separator, tail). The separator is '' if not found."},
    ],
}
