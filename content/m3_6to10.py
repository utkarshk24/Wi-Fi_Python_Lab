"""Phase 3 content: modules 3.6-3.10."""

M_3_6 = {
    "id": "3.6",
    "title": "dataclasses, enums & __slots__",
    "hours": 2.5,
    "summary": "Removing boilerplate with dataclasses, frozen and ordered value types, enums for fixed sets of values and flags, and __slots__ for lean objects.",
    "concepts": [
        {
            "title": "dataclasses",
            "concept": "`@dataclass` reads the class's type-annotated fields and generates `__init__`, `__repr__` and `__eq__` for you. Mutable defaults need `field(default_factory=list)`. `__post_init__` runs after the generated `__init__` for validation or derived fields (`field(init=False)`). `frozen=True` makes instances immutable and hashable; `order=True` adds comparison operators based on field order. `asdict()` converts to a plain dict, ready for JSON.",
            "why": "Test results, scan entries and testbed definitions are records with a few typed fields. A dataclass gives them a readable repr in failure messages, value equality for assertions and one-line JSON export, without writing any of that by hand.",
            "syntax": "@dataclass\nclass Result:\n    test: str\n    mbps: float\n    samples: list[float] = field(default_factory=list)\n\n@dataclass(frozen=True, order=True, slots=True, kw_only=False)\nclass Channel: ...",
            "code": """from dataclasses import FrozenInstanceError, asdict, dataclass, field  ## The dataclass toolkit

THRESHOLD_MBPS = {"5G": 850, "6G": 2400}  ## Pass thresholds per band


@dataclass  ## Generates __init__, __repr__ and __eq__ from the annotated fields below
class ThroughputResult:  ## One throughput test result
    test: str  ## Required field (no default)
    band: str  ## Required field
    mbps: float  ## Required field
    samples: list[float] = field(default_factory=list)  ## Mutable default: a NEW list per instance
    passed: bool = field(init=False)  ## Not an __init__ parameter; computed in __post_init__

    def __post_init__(self) -> None:  ## Runs right after the generated __init__
        self.passed = self.mbps >= THRESHOLD_MBPS.get(self.band, 0)  ## Derived field


@dataclass(frozen=True, order=True)  ## Immutable, hashable, and comparable field by field
class Channel:  ## A value type
    band: str  ## Compared first
    number: int  ## Compared second


def main() -> None:
    r = ThroughputResult("tput_5g_80", "5G", 912.4, [910.2, 905.7])  ## Positional arguments in field order
    print(r)  ## The generated __repr__ shows every field
    print(r.passed, asdict(r))  ## Derived field; asdict() gives a JSON-ready dict
    print(r == ThroughputResult("tput_5g_80", "5G", 912.4, [910.2, 905.7]))  ## Generated __eq__ compares field values
    chans = {Channel("5G", 36), Channel("5G", 36), Channel("6G", 37)}  ## frozen=True makes them hashable
    print(sorted(chans))  ## order=True compares (band, number) tuples
    try:  ## Frozen instances can't be changed
        Channel("5G", 36).number = 40  ## Attempted mutation
    except FrozenInstanceError as err:  ## A dedicated exception type
        print("FrozenInstanceError:", err)  ## Names the field


if __name__ == "__main__":
    main()""",
            "under": "The decorator inspects `__annotations__` in definition order and writes the methods as real Python source, which it compiles and attaches to the class. That's why there's no runtime cost compared with hand-written methods. With `frozen=True`, the generated `__setattr__` raises; with `eq=True` and `frozen=True`, a `__hash__` based on the fields is generated as well. Type hints on fields are not enforced at runtime.",
            "gotchas": [
                {
                    "title": "A mutable default value",
                    "note": "dataclasses refuse a plain list default (it would be shared, as in Module 2.1). Use default_factory.",
                    "wrong": """from dataclasses import dataclass

@dataclass
class Result:
    test: str
    samples: list = []""",
                    "fixed": """from dataclasses import dataclass, field

@dataclass
class Result:
    test: str
    samples: list = field(default_factory=list)

a, b = Result("t1"), Result("t2")
a.samples.append(1)
print(a, b)""",
                }
            ],
            "best": "Make result and config records dataclasses; make value types `frozen=True` so they can be dict keys and can't change underneath you. Validate in `__post_init__`, convert with `asdict()` at the JSON boundary, and add `slots=True` (3.10+) for records you create by the million.",
        },
        {
            "title": "Enums and Flags",
            "concept": "An `Enum` defines a fixed set of named members: `Verdict.PASS`. Members are singletons, compared with `is` or `==`, iterable, and convertible from values (`Band(\"6G\")`) or names (`Verdict[\"FAIL\"]`); invalid values raise `ValueError`. `StrEnum` (3.11+) and `IntEnum` members also behave as plain strings and ints. `Flag` members combine with `|` into sets of options and are tested with `in`. `auto()` assigns values for you.",
            "why": "Bands, verdicts, security modes and deauth reason codes are closed sets. An enum catches a typo such as `\"6g\"` or `\"PASSED\"` at the boundary instead of letting it silently miss every comparison, and a Flag models capability bit sets such as HT | VHT | HE | EHT.",
            "syntax": "class Band(StrEnum):\n    G5 = \"5G\"\n    G6 = \"6G\"\n\nclass Verdict(Enum):\n    PASS = auto()\n\nclass Cap(Flag):\n    HE = auto(); EHT = auto()\nCap.HE | Cap.EHT",
            "code": """from enum import Enum, Flag, IntEnum, StrEnum, auto  ## The enum toolbox


class Band(StrEnum):  ## Members are also str, so they print and compare as text
    G2 = "2G"  ## 2.4 GHz
    G5 = "5G"  ## 5 GHz
    G6 = "6G"  ## 6 GHz


class Verdict(Enum):  ## A plain enum: members are NOT equal to their values
    PASS = auto()  ## auto() picks 1, 2, 3...
    FAIL = auto()  ## ...so we never maintain numbers by hand
    SKIP = auto()  ## Third member


class Capability(Flag):  ## Members are powers of two that combine with |
    HT = auto()  ## 802.11n
    VHT = auto()  ## 802.11ac
    HE = auto()  ## 802.11ax
    EHT = auto()  ## 802.11be


class ReasonCode(IntEnum):  ## Members are also ints: handy for codes parsed from logs
    UNSPECIFIED = 1  ## Unspecified reason
    DEAUTH_LEAVING = 3  ## Deauthenticated because the sender is leaving
    DISASSOC_LEAVING = 8  ## Disassociated because the sender is leaving the BSS
    FOURWAY_TIMEOUT = 15  ## 4-way handshake timeout


def main() -> None:
    band = Band("6G")  ## Look a member up by value, e.g. from a config file
    print(band, band is Band.G6, band == "6G", [b.value for b in Band])  ## StrEnum compares equal to its string; enums are iterable
    print(Verdict.PASS, Verdict.PASS.name, Verdict["FAIL"], Verdict.PASS == 1)  ## By name with []; plain Enum != its value
    caps = Capability.HE | Capability.EHT  ## A combined flag value
    print(caps, Capability.EHT in caps, Capability.VHT in caps)  ## Membership tests on flags
    print(ReasonCode(15).name, ReasonCode.FOURWAY_TIMEOUT == 15)  ## Decode a numeric code from a log
    try:  ## Values outside the set are rejected
        Band("7G")  ## Not a member
    except ValueError as err:  ## Typos fail loudly at the boundary
        print("ValueError:", err)  ## Says which value was invalid


if __name__ == "__main__":
    main()""",
            "under": "Enum classes are built by the `EnumType` metaclass, which turns each class attribute into a singleton member and blocks creating new ones or reassigning existing ones. `Band(\"6G\")` looks the value up in an internal value-to-member map. A Flag value is backed by an int, so `HE | EHT` is a new pseudo-member whose bits are both set. `IntEnum` and `StrEnum` subclass int and str, which is convenient but means they lose some type safety.",
            "gotchas": [
                {
                    "title": "Comparing a plain Enum with its value",
                    "note": "Verdict.PASS is not equal to 1 or 'PASS'. Convert raw values into members first, then compare members.",
                    "wrong": """from enum import Enum

class Verdict(Enum):
    PASS = "PASS"
    FAIL = "FAIL"

raw = "PASS"
print(raw == Verdict.PASS)""",
                    "fixed": """from enum import Enum

class Verdict(Enum):
    PASS = "PASS"
    FAIL = "FAIL"

raw = "PASS"
print(Verdict(raw) is Verdict.PASS)""",
                }
            ],
            "best": "Convert strings from logs, CLIs and config files into enum members at the boundary, then use members everywhere inside. Use StrEnum or IntEnum when the values must interoperate with text or numbers (JSON, logs), plain Enum otherwise, and Flag for capability sets.",
        },
        {
            "title": "__slots__",
            "concept": "Normally every instance carries its own attribute dict. Declaring `__slots__` (or `@dataclass(slots=True)`) replaces it with fixed storage for exactly the named attributes. Instances use noticeably less memory and attribute access is a little faster, but you can no longer add attributes that aren't listed, which also catches typos.",
            "why": "A 12-hour soak test might hold millions of RSSI samples as objects. Slots shrink each one, and a typo like `sample.rsi = -60` raises instead of silently creating a new attribute.",
            "syntax": "class Sample:\n    __slots__ = (\"t\", \"rssi\")\n\n@dataclass(slots=True)\nclass Sample:\n    t: float\n    rssi: int",
            "code": """import sys  ## getsizeof for a rough size comparison
from dataclasses import dataclass  ## dataclass can generate __slots__ for us


@dataclass  ## Regular instances: each has a __dict__
class SampleDict:  ## One RSSI sample
    t: float  ## Seconds since start
    rssi: int  ## dBm


@dataclass(slots=True)  ## 3.10+: generates __slots__ = ("t", "rssi")
class SampleSlots:  ## Same fields, fixed storage
    t: float  ## Seconds since start
    rssi: int  ## dBm


def main() -> None:
    a, b = SampleDict(1.0, -54), SampleSlots(1.0, -54)  ## One of each
    print(hasattr(a, "__dict__"), hasattr(b, "__dict__"))  ## Only the regular one has a per-instance dict
    print(sys.getsizeof(a) + sys.getsizeof(a.__dict__) > sys.getsizeof(b))  ## Object + dict vs one compact object
    a.rsi = -60  ## Typo: silently creates a NEW attribute on a regular object
    print(sorted(vars(a)))  ## The typo is now part of the object
    try:  ## The slotted class rejects unknown attributes
        b.rsi = -60  ## Same typo
    except AttributeError as err:  ## Caught immediately
        print("AttributeError:", err)  ## Names the class and the bad attribute


if __name__ == "__main__":
    main()""",
            "under": "Each name in `__slots__` becomes a member descriptor on the class that reads and writes a fixed offset inside the instance, so no dict is allocated. Subclasses get a `__dict__` again unless they also define `__slots__`. Slotted classes can't use `cached_property`, which stores its result in the instance dict.",
            "gotchas": [
                {
                    "title": "Typos create attributes on normal objects",
                    "note": "Without slots, a misspelled attribute silently becomes a new one and the real field keeps its old value.",
                    "wrong": """class Sample:
    def __init__(self, rssi):
        self.rssi = rssi

s = Sample(-54)
s.rsi = -60
print(s.rssi)""",
                    "fixed": """class Sample:
    __slots__ = ("rssi",)
    def __init__(self, rssi):
        self.rssi = rssi

s = Sample(-54)
try:
    s.rsi = -60
except AttributeError as err:
    print("caught:", err)""",
                }
            ],
            "best": "Add `slots=True` to dataclasses that are created in large numbers or whose attributes should be fixed. Leave them off for classes that need dynamic attributes or cached_property.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write a `ScanEntry` dataclass (bssid, channel, rssi) and sort a list of entries by rssi, strongest first.",
            "solution": "Plain dataclass plus sorted() with a key.",
            "solution_code": """from dataclasses import dataclass


@dataclass
class ScanEntry:
    bssid: str
    channel: int
    rssi: int


scan = [ScanEntry("ap-1", 36, -61), ScanEntry("ap-2", 149, -48), ScanEntry("ap-3", 1, -70)]
for e in sorted(scan, key=lambda e: e.rssi, reverse=True):
    print(e)""",
        },
        {
            "level": "Medium",
            "prompt": "Create a `Security` StrEnum (OPEN, WPA2, WPA3, OWE) and a frozen dataclass `SsidProfile(name, security)` whose __post_init__ converts a plain string to the enum and rejects unknown values.",
            "solution": "Frozen dataclasses need object.__setattr__ to adjust a field in __post_init__.",
            "solution_code": """from dataclasses import dataclass
from enum import StrEnum


class Security(StrEnum):
    OPEN = "open"
    WPA2 = "wpa2"
    WPA3 = "wpa3"
    OWE = "owe"


@dataclass(frozen=True)
class SsidProfile:
    name: str
    security: Security

    def __post_init__(self):
        object.__setattr__(self, "security", Security(self.security))


print(SsidProfile("lab-wpa3", "wpa3"))
try:
    SsidProfile("lab-wep", "wep")
except ValueError as err:
    print("ValueError:", err)""",
        },
        {
            "level": "Hard",
            "prompt": "Parse capability strings like `\"HT,VHT,HE\"` into a Capability Flag, then report which test suites a DUT can run, where the 802.11be suite needs EHT and the MU-MIMO suite needs VHT or HE.",
            "solution": "Combine members with | via functools.reduce, then test with in.",
            "solution_code": """from enum import Flag, auto
from functools import reduce
from operator import or_


class Cap(Flag):
    HT = auto()
    VHT = auto()
    HE = auto()
    EHT = auto()


def parse_caps(text):
    return reduce(or_, (Cap[name] for name in text.split(",")), Cap(0))


for dut, caps in [("ap-wifi6", "HT,VHT,HE"), ("ap-wifi7", "HT,VHT,HE,EHT"), ("ap-n-only", "HT")]:
    c = parse_caps(caps)
    suites = [s for s, ok in [("be_suite", Cap.EHT in c), ("mu_mimo_suite", bool(c & (Cap.VHT | Cap.HE)))] if ok]
    print(dut, suites)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What does @dataclass generate?", "a": "By default __init__, __repr__ and __eq__ from the annotated fields. Options add ordering (order=True), immutability plus hashing (frozen=True), __slots__ (slots=True) and keyword-only parameters (kw_only=True).", "follow": "Are field types enforced? (No; they are hints only.)"},
        {"level": "Intermediate", "q": "Why can't you write `samples: list = []` in a dataclass?", "a": "The default would be one list shared by every instance, the mutable-default bug, so dataclasses raise ValueError. Use field(default_factory=list).", "follow": "When does __post_init__ run? (Right after the generated __init__.)"},
        {"level": "Intermediate", "q": "Enum vs constants such as BAND_5G = '5G'?", "a": "Enums form a closed, iterable set, reject invalid values when converting, print meaningful names, and let type checkers verify you pass a Band rather than any string. Plain constants allow any string to slip through.", "follow": "When use StrEnum? (When values must also act as strings, e.g. in JSON or CLI output.)"},
        {"level": "Advanced", "q": "What are __slots__ for, and what do they cost?", "a": "They replace the per-instance __dict__ with fixed storage for named attributes, saving memory and preventing new attributes. The costs: no dynamic attributes, no cached_property, extra care with multiple inheritance and subclasses (which regain a __dict__ unless they declare __slots__ too).", "follow": "How do you get slots with a dataclass? (@dataclass(slots=True) in 3.10+.)"},
    ],
    "quiz": [
        {"q": "Which option makes a dataclass hashable and immutable?", "options": ["order=True", "frozen=True", "slots=True", "eq=False"], "answer": 1, "why": "frozen with eq generates __hash__."},
        {"q": "How do you give a dataclass field a fresh list each time?", "options": ["= []", "= list", "= field(default_factory=list)", "= None"], "answer": 2, "why": "default_factory is called per instance."},
        {"q": "`Band('7G')` for a Band enum without that value raises...", "options": ["KeyError", "ValueError", "TypeError", "Nothing"], "answer": 1, "why": "Lookup by value raises ValueError."},
        {"q": "Which enum type combines members with |?", "options": ["Enum", "IntEnum", "Flag", "StrEnum"], "answer": 2, "why": "Flags are bit sets."},
        {"q": "Assigning an unlisted attribute on a slotted instance...", "options": ["Works", "Raises AttributeError", "Is ignored", "Adds to __dict__"], "answer": 1, "why": "There's no __dict__ to hold it."},
    ],
    "cards": [
        {"front": "@dataclass generates", "back": "__init__, __repr__, __eq__ (plus ordering/hash/slots with options)"},
        {"front": "Mutable default in a dataclass", "back": "`field(default_factory=list)`"},
        {"front": "Value type dataclass", "back": "`@dataclass(frozen=True)`"},
        {"front": "Enum lookup", "back": "By value `Band('6G')`, by name `Verdict['FAIL']`"},
        {"front": "Flag membership", "back": "`Cap.EHT in caps`"},
        {"front": "__slots__ benefit", "back": "Less memory, no accidental new attributes."},
    ],
}


M_3_7 = {
    "id": "3.7",
    "title": "Iterators & Generators",
    "hours": 3,
    "summary": "The iterator protocol behind every for loop, generator functions with yield, lazy processing pipelines, yield from, and infinite streams.",
    "concepts": [
        {
            "title": "The iterator protocol and generator functions",
            "concept": "An **iterable** is anything `iter()` accepts; an **iterator** is the object `iter()` returns, which produces values with `next()` until it raises `StopIteration`. You can write an iterator class with `__iter__` and `__next__`, but a **generator function** (any function containing `yield`) is far simpler: calling it returns a generator without running the body; each `next()` runs until the next `yield`, hands out that value and pauses with all local state kept.",
            "why": "Attenuation sweeps, channel plans and sample streams are sequences you produce step by step. A generator describes them in a few lines, and because values are produced on demand, a sweep can stop early without computing the steps it never reaches.",
            "syntax": "it = iter(xs); next(it); next(it, default)\n\ndef steps(start, stop, step):\n    db = start\n    while db <= stop:\n        yield db\n        db += step",
            "code": """class Countdown:  ## An iterator written by hand
    def __init__(self, start: int) -> None:  ## Where to begin
        self.current = start  ## State kept between next() calls

    def __iter__(self):  ## Iterators return themselves from __iter__
        return self  ## So they work in for loops

    def __next__(self) -> int:  ## Produce the next value
        if self.current <= 0:  ## Nothing left
            raise StopIteration  ## The signal that ends a for loop
        self.current -= 1  ## Advance the state
        return self.current + 1  ## The value for this step


def attenuation_steps(start: int, stop: int, step: int):  ## The same idea as a generator function
    db = start  ## Local state survives between yields
    while db <= stop:  ## Inclusive upper bound
        yield db  ## Hand out a value and pause here
        db += step  ## Resumes from this line on the next next()


def main() -> None:
    it = iter([36, 40])  ## A list is iterable; iter() gives an iterator over it
    print(next(it), next(it), next(it, "done"))  ## next() with a default returns it instead of raising StopIteration
    print(list(Countdown(3)))  ## list() drives the protocol until StopIteration
    gen = attenuation_steps(0, 20, 10)  ## Calling it runs NOTHING yet; it returns a generator object
    print(type(gen).__name__, next(gen), list(gen), list(gen))  ## First value, then the rest, then nothing: single use
    for db in attenuation_steps(0, 60, 30):  ## Generators work anywhere an iterable does
        print("set", db, "dB")  ## 0, 30, 60


if __name__ == "__main__":
    main()""",
            "under": "A generator object owns a suspended **frame**: its local variables and the position of the last `yield`. `next()` resumes that frame; when the function returns, Python raises `StopIteration` for you. Since PEP 479 (Python 3.7), a `StopIteration` that escapes from inside a generator body is turned into `RuntimeError`, so a stray `next()` can't silently end a loop early.",
            "gotchas": [
                {
                    "title": "Calling a generator function doesn't run it",
                    "note": "The body only starts when something asks for the first value, so side effects (like 'start traffic') don't happen at the call.",
                    "wrong": """def start_traffic():
    print("traffic started")
    yield "running"

start_traffic()
print("did it start?")""",
                    "fixed": """def start_traffic():
    print("traffic started")
    yield "running"

gen = start_traffic()
print(next(gen))""",
                },
                {
                    "title": "A bare next() inside a generator",
                    "note": "When the inner iterator is exhausted, the StopIteration becomes RuntimeError (PEP 479). Pass a default to next(), or loop instead.",
                    "wrong": """def first_two_pairs(xs):
    it = iter(xs)
    while True:
        yield next(it), next(it)

print(list(first_two_pairs([1, 2, 3])))""",
                    "fixed": """def pairs(xs):
    it = iter(xs)
    for a in it:
        b = next(it, None)
        yield a, b

print(list(pairs([1, 2, 3])))""",
                },
            ],
            "best": "Write generators instead of iterator classes unless you need extra methods. Use them for any sequence that is large, expensive or open-ended, and remember they're single-use: convert to a list if you need several passes.",
        },
        {
            "title": "Pipelines, yield from and infinite generators",
            "concept": "Chaining generators builds a **pipeline**: each stage takes an iterable, yields transformed items and pulls from the previous stage only when it needs the next item. Memory stays constant however large the input, and stopping early stops every stage. `yield from other` delegates to another iterable, yielding all its values. A generator can also be **infinite** (`while True: yield ...`); take what you need with `itertools.islice` or `break`.",
            "why": "Finding roam events for one station in a multi-gigabyte capture log is a pipeline: read lines → filter by MAC → parse → detect roams. Each stage is a tiny, testable function, and only one line is in memory at a time.",
            "syntax": "def stage(items):\n    for item in items:\n        if keep(item):\n            yield transform(item)\n\npipeline = stage3(stage2(stage1(source)))\n\ndef merged(*logs):\n    for log in logs:\n        yield from log",
            "code": """from itertools import islice  ## Take a bounded slice of any iterator

LOG = [  ## Pretend these lines stream from a huge file
    "0.0 aa:01 assoc ap-1",  ## Station aa:01 joins ap-1
    "1.2 aa:02 assoc ap-1",  ## A different station
    "5.7 aa:01 roam ap-2",  ## aa:01 roams
    "6.1 aa:02 deauth reason=3",  ## aa:02 leaves
    "9.4 aa:01 roam ap-3",  ## aa:01 roams again
]


def read_lines(lines):  ## Stage 1: the source (a file object would go here)
    for n, line in enumerate(lines, start=1):  ## One line at a time
        print(f"    read line {n}")  ## Shows WHEN each line is pulled through the pipeline
        yield line  ## Pass it downstream


def only_station(lines, mac: str):  ## Stage 2: filter
    for line in lines:  ## Pulls from stage 1 on demand
        if f" {mac} " in line:  ## Keep only this station's lines
            yield line  ## Others are dropped


def parse(lines):  ## Stage 3: transform text into tuples
    for line in lines:  ## Pulls from stage 2
        t, mac, event, detail = line.split(maxsplit=3)  ## Four fields
        yield float(t), event, detail  ## Structured output


def roams(events):  ## Stage 4: detect what we care about
    for t, event, detail in events:  ## Pulls from stage 3
        if event == "roam":  ## Only roam events
            yield f"t={t}s -> {detail}"  ## A human-readable result


def merged(*logs):  ## yield from: delegate to several iterables in turn
    for log in logs:  ## Each log source
        yield from log  ## Same as: for x in log: yield x


def sample_ids():  ## An infinite generator
    n = 0  ## Counter state
    while True:  ## Never ends on its own
        yield n  ## Next id
        n += 1  ## Advance


def main() -> None:
    pipeline = roams(parse(only_station(read_lines(LOG), "aa:01")))  ## Builds the chain; nothing has run yet
    print("first roam:", next(pipeline))  ## Pulls just enough lines to produce one result (lines 1-3)
    print("rest:", list(pipeline))  ## Continues where it stopped
    print(list(merged(["a", "b"], ("c",))))  ## Flattens two iterables
    print(list(islice(sample_ids(), 5)))  ## Take only the first five of an endless stream


if __name__ == "__main__":
    main()""",
            "under": "Each stage holds a reference to the previous stage's generator. `next()` on the last stage resumes it, which calls `next()` on the one before, and so on back to the source; values then flow forward one at a time. Nothing is buffered between stages, which is why memory use doesn't grow with input size. `yield from` also forwards `send()` and `throw()` calls and returns the sub-generator's return value.",
            "gotchas": [
                {
                    "title": "Materialising every stage",
                    "note": "Building a full list at each stage multiplies memory use and does all the work up front, even if you only need the first result.",
                    "wrong": """lines = [f"{i} aa:01 roam ap-{i % 3}" for i in range(100_000)]
roams = [parts for parts in [ln.split() for ln in lines] if parts[2] == "roam"]
print(roams[0], len(roams))""",
                    "fixed": """lines = (f"{i} aa:01 roam ap-{i % 3}" for i in range(100_000))
roams = (parts for parts in (ln.split() for ln in lines) if parts[2] == "roam")
print(next(roams))""",
                }
            ],
            "best": "Build log and capture processing as a chain of small generator stages, each with one job and its own unit test. Keep the source stage responsible for opening and closing the file (with a `with` block inside the generator). Use `islice` or `break` to bound infinite generators.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write a generator `channels(band)` that yields the 20 MHz 5 GHz UNII-1 and UNII-3 channels (36–48 and 149–165, step 4).",
            "solution": "Two loops with yield, or yield from two ranges.",
            "solution_code": """def channels():
    yield from range(36, 49, 4)
    yield from range(149, 166, 4)


print(list(channels()))""",
        },
        {
            "level": "Medium",
            "prompt": "Write a generator `moving_average(values, n)` that yields the average of each full window of n values.",
            "solution": "Keep a deque(maxlen=n) inside the generator.",
            "solution_code": """from collections import deque


def moving_average(values, n):
    window = deque(maxlen=n)
    for v in values:
        window.append(v)
        if len(window) == n:
            yield round(sum(window) / n, 1)


print(list(moving_average([-52, -55, -61, -58, -66, -70], 3)))""",
        },
        {
            "level": "Hard",
            "prompt": "Build a pipeline that streams a log written to a temp file, keeps deauth lines, extracts the reason code and yields running counts per reason, printing only the final counts.",
            "solution": "The source stage opens the file inside the generator with with, so it's closed when the pipeline finishes.",
            "solution_code": """import re
import tempfile
from pathlib import Path


def read(path):
    with open(path, encoding="utf-8") as f:
        yield from f


def deauths(lines):
    for line in lines:
        if "deauth" in line:
            yield line


def reasons(lines):
    for line in lines:
        m = re.search(r"reason=(\\d+)", line)
        if m:
            yield int(m.group(1))


with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp) / "ap.log"
    p.write_text("assoc aa:01\\ndeauth aa:01 reason=15\\ndeauth aa:02 reason=3\\nassoc aa:03\\ndeauth aa:03 reason=15\\n")
    counts = {}
    for r in reasons(deauths(read(p))):
        counts[r] = counts.get(r, 0) + 1
    print(counts)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What's the difference between an iterable and an iterator?", "a": "An iterable can produce an iterator via iter() (lists, dicts, files, generators). An iterator has __next__ and remembers its position; it is consumed as you go and is itself iterable (iter(it) returns it).", "follow": "Is a list an iterator? (No; it's an iterable. iter(list) gives a list_iterator.)"},
        {"level": "Intermediate", "q": "What happens when you call a generator function?", "a": "Nothing in the body runs; you get a generator object. Each next() runs the body until the next yield, returns that value and suspends with local state intact. When the function returns, StopIteration is raised.", "follow": "What does PEP 479 change? (A StopIteration raised inside a generator becomes RuntimeError.)"},
        {"level": "Intermediate", "q": "Why do generator pipelines use so little memory?", "a": "Each stage pulls one item at a time from the previous one and yields it onward, so only the current item is alive at each stage. Nothing is collected into intermediate lists.", "follow": "What if a stage needs to look at all items, like sorting? (That stage must buffer; keep it as late as possible.)"},
        {"level": "Advanced", "q": "What does yield from do beyond a loop?", "a": "It yields every value of a sub-iterator, but also forwards send() and throw() calls to a sub-generator and evaluates to the sub-generator's return value. It's the basis of how coroutines were composed before async/await.", "follow": "What is generator.send(x)? (Resumes the generator, making the paused yield expression evaluate to x.)"},
    ],
    "quiz": [
        {"q": "What does `next(iter([]), 'empty')` return?", "options": ["None", "'empty'", "StopIteration", "[]"], "answer": 1, "why": "The default is returned instead of raising."},
        {"q": "A function containing yield returns...", "options": ["Its first yielded value", "A generator object", "A list", "None"], "answer": 1, "why": "Calling it creates a generator."},
        {"q": "Which ends a for loop over a custom iterator?", "options": ["return None", "raise StopIteration", "break inside __next__", "raise IndexError"], "answer": 1, "why": "StopIteration signals exhaustion."},
        {"q": "`list(islice(itertools.count(), 3))` gives?", "options": ["[1, 2, 3]", "[0, 1, 2]", "Infinite loop", "[0, 1, 2, 3]"], "answer": 1, "why": "islice takes the first 3."},
        {"q": "`yield from xs` is roughly...", "options": ["return xs", "for x in xs: yield x", "yield list(xs)", "xs.yield()"], "answer": 1, "why": "Plus forwarding of send/throw."},
    ],
    "cards": [
        {"front": "Iterator protocol", "back": "__iter__ returns self; __next__ returns values then raises StopIteration."},
        {"front": "Generator function", "back": "Any function with yield; calling it returns a lazy generator."},
        {"front": "Generator pipeline", "back": "Chained stages pulling one item at a time: constant memory."},
        {"front": "yield from", "back": "Delegate to another iterable (and sub-generator)."},
        {"front": "Bound an infinite generator", "back": "`itertools.islice(gen, n)` or break"},
    ],
}


M_3_8 = {
    "id": "3.8",
    "title": "Closures & Decorators",
    "hours": 3.5,
    "summary": "Decorators as functions that wrap functions, preserving metadata with functools.wraps, decorators with arguments such as retry, stacking order and skip-if-unsupported guards.",
    "concepts": [
        {
            "title": "Writing a decorator",
            "concept": "A **decorator** is a function that takes a function and returns a replacement, usually a **wrapper** closure that does something before and after calling the original. `@log_calls` above a `def` is shorthand for `func = log_calls(func)`. The wrapper accepts `*args, **kwargs` so it works with any signature. `@functools.wraps(func)` copies the original's name, docstring and other metadata onto the wrapper and stores the original as `__wrapped__`.",
            "why": "Logging every device command, timing every test step and counting calls are cross-cutting concerns. A decorator adds them in one line without touching the functions themselves.",
            "syntax": "def deco(func):\n    @functools.wraps(func)\n    def wrapper(*args, **kwargs):\n        ...  # before\n        result = func(*args, **kwargs)\n        ...  # after\n        return result\n    return wrapper\n\n@deco\ndef f(): ...",
            "code": """import functools  ## For functools.wraps


def log_calls(func):  ## A decorator: receives the function being decorated
    @functools.wraps(func)  ## Copy func's __name__, __doc__ etc. onto wrapper
    def wrapper(*args, **kwargs):  ## Accepts any arguments, whatever func's signature
        arg_text = ", ".join([repr(a) for a in args] + [f"{k}={v!r}" for k, v in kwargs.items()])  ## Render the call
        print(f"-> {func.__name__}({arg_text})")  ## Before the call
        result = func(*args, **kwargs)  ## Call the original with the same arguments
        print(f"<- {func.__name__} returned {result!r}")  ## After the call
        return result  ## Always return the original's result
    return wrapper  ## The replacement function


@log_calls  ## Same as: set_channel = log_calls(set_channel)
def set_channel(ap: str, channel: int, width: int = 20) -> str:  ## The function being decorated
    \"\"\"Configure one radio channel.\"\"\"  ## Preserved by wraps
    return f"{ap}: ch{channel}/{width}MHz"  ## What the call returns


def reboot(ap: str) -> str:  ## Decorated manually below, without the @ syntax
    return f"{ap} rebooting"  ## Plain function


def main() -> None:
    set_channel("ap-1", 149, width=80)  ## The wrapper prints before and after
    print(set_channel.__name__, "|", set_channel.__doc__)  ## Thanks to wraps, the metadata is the original's
    print(set_channel.__wrapped__("ap-2", 36))  ## The undecorated original is still reachable (no logging)
    logged_reboot = log_calls(reboot)  ## Decorating is just calling the decorator
    logged_reboot("ap-3")  ## Behaves exactly like @log_calls would


if __name__ == "__main__":
    main()""",
            "under": "When Python executes `@log_calls def set_channel...`, it creates the function object, calls `log_calls` with it, and binds the name to whatever comes back. The wrapper is a closure: it keeps a reference to `func` in a cell (Module 2.2). Decorators therefore run **once, at definition time**; the wrapper runs on every call.",
            "gotchas": [
                {
                    "title": "Forgetting functools.wraps",
                    "note": "Every decorated function shows up as 'wrapper' in logs, tracebacks and pytest output, and its docstring is lost.",
                    "wrong": """def log_calls(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@log_calls
def test_roam_11r():
    \"\"\"802.11r fast transition.\"\"\"

print(test_roam_11r.__name__, test_roam_11r.__doc__)""",
                    "fixed": """import functools

def log_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@log_calls
def test_roam_11r():
    \"\"\"802.11r fast transition.\"\"\"

print(test_roam_11r.__name__, test_roam_11r.__doc__)""",
                },
                {
                    "title": "Not returning the result",
                    "note": "A wrapper that calls func but forgets to return its value turns every decorated function into one that returns None.",
                    "wrong": """import functools

def log_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func(*args, **kwargs)
    return wrapper

@log_calls
def rssi():
    return -54

print(rssi())""",
                    "fixed": """import functools

def log_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@log_calls
def rssi():
    return -54

print(rssi())""",
                },
            ],
            "best": "Always use `@functools.wraps`, always accept `*args, **kwargs` and always return the wrapped result. Keep decorators focused on one concern, and give them tests of their own with simple dummy functions.",
        },
        {
            "title": "Decorators with arguments and stacking",
            "concept": "A decorator that takes options, like `@retry(times=3)`, is a **decorator factory**: a function that returns a decorator, which returns a wrapper. That's three nested functions. When several decorators are stacked, the one **nearest the `def` is applied first**, so the outermost one runs first at call time. A decorator can also decide not to call the function at all, for example to skip a test the DUT can't support.",
            "why": "`@retry(times=3, on=(ConnectionError,))` around SSH connects absorbs a rebooting AP; `@requires_band(\"6G\")` turns \"DUT has no 6 GHz radio\" into a clean skip instead of a confusing failure.",
            "syntax": "def retry(times=3, on=(Exception,)):   # factory: takes options\n    def decorator(func):                # decorator: takes func\n        @functools.wraps(func)\n        def wrapper(*args, **kwargs):   # wrapper: runs per call\n            ...\n        return wrapper\n    return decorator\n\n@outer\n@inner      # applied first\ndef f(): ...",
            "code": """import functools  ## wraps
import time  ## sleep between attempts


def retry(times: int = 3, delay: float = 0.0, on: tuple = (ConnectionError,)):  ## Factory: called with the options
    def decorator(func):  ## The real decorator, receiving the function
        @functools.wraps(func)  ## Keep the metadata
        def wrapper(*args, **kwargs):  ## Runs on every call
            for attempt in range(1, times + 1):  ## Up to `times` attempts
                try:  ## Try the call
                    return func(*args, **kwargs)  ## Success: return immediately
                except on as err:  ## Only the listed exception types are retried
                    print(f"  attempt {attempt}/{times} failed: {err}")  ## Make retries visible in logs
                    if attempt == times:  ## Out of attempts
                        raise  ## Re-raise the last error unchanged
                    time.sleep(delay)  ## Back off before trying again
        return wrapper  ## Give back the wrapper
    return decorator  ## Give back the decorator


def requires_band(band: str):  ## A guard decorator factory
    def decorator(func):  ## Receives the test function
        @functools.wraps(func)  ## Keep the test's name for reports
        def wrapper(dut: dict, *args, **kwargs):  ## The first argument is the DUT description
            if band not in dut["bands"]:  ## Unsupported: don't even run the test
                return f"SKIP {func.__name__}: {dut['name']} has no {band} radio"  ## A clean, explained skip
            return func(dut, *args, **kwargs)  ## Supported: run it
        return wrapper  ## Replacement function
    return decorator  ## Configured decorator


attempts = {"n": 0}  ## Shared counter so the fake connect can fail twice


@retry(times=3)  ## retry(times=3) runs first and returns the decorator that wraps ssh_connect
def ssh_connect(host: str) -> str:  ## Simulates an AP that is still booting
    attempts["n"] += 1  ## Count the calls
    if attempts["n"] < 3:  ## The first two attempts fail
        raise ConnectionError(f"{host} refused")  ## Like a real SSH refusal
    return f"connected to {host}"  ## Third attempt succeeds


@requires_band("6G")  ## Applied second: wraps the retrying function
@retry(times=2)  ## Applied first (nearest the def)
def test_6g_throughput(dut: dict) -> str:  ## A test that needs 6 GHz
    return f"PASS on {dut['name']}"  ## Placeholder test body


def main() -> None:
    print(ssh_connect("10.0.0.11"))  ## Two retries, then success
    print(test_6g_throughput({"name": "ap-1", "bands": ["5G", "6G"]}))  ## Supported DUT: runs
    print(test_6g_throughput({"name": "ap-old", "bands": ["2G", "5G"]}))  ## Unsupported DUT: skipped without calling the test
    print(test_6g_throughput.__name__)  ## wraps at every level keeps the original name


if __name__ == "__main__":
    main()""",
            "under": "`@retry(times=3)` evaluates `retry(times=3)` first, at definition time, producing a decorator that has `times` in its closure; that decorator is then applied to the function. With stacking, `@a @b def f` means `f = a(b(f))`: `b` wraps first, `a` wraps the result, so at call time `a`'s wrapper runs first and `b`'s runs inside it. That's why the band guard here prevents any retries on unsupported DUTs.",
            "gotchas": [
                {
                    "title": "Using a decorator factory without parentheses",
                    "note": "`@retry` without () passes the function as `times`, and calling the 'decorated' function returns a wrapper instead of a result.",
                    "wrong": """import functools

def retry(times=3):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

@retry
def ping(host):
    return f"{host} up"

result = ping("ap-1")
print(type(result).__name__)""",
                    "fixed": """import functools

def retry(times=3):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

@retry()
def ping(host):
    return f"{host} up"

print(ping("ap-1"))""",
                }
            ],
            "best": "Retry only specific, transient exception types and log each failed attempt; never retry assertion failures. Put guard decorators (skips, preconditions) outermost so they short-circuit before anything else runs. In pytest code, prefer the built-in markers and fixtures (Phase 5) for skips and setup; use decorators for device-level concerns.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write a `count_calls` decorator that stores the number of calls on `wrapper.calls`.",
            "solution": "Functions are objects, so the wrapper can carry an attribute.",
            "solution_code": """import functools


def count_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.calls += 1
        return func(*args, **kwargs)
    wrapper.calls = 0
    return wrapper


@count_calls
def poll_rssi():
    return -54


for _ in range(4):
    poll_rssi()
print(poll_rssi.calls)""",
        },
        {
            "level": "Medium",
            "prompt": "Write `@timed` that records the duration of each call in milliseconds in a list `wrapper.durations`, without printing the (non-deterministic) values. Show that 3 calls give 3 positive durations.",
            "solution": "perf_counter before and after, in a finally so failures are timed too.",
            "solution_code": """import functools
import time


def timed(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            wrapper.durations.append((time.perf_counter() - t0) * 1000)
    wrapper.durations = []
    return wrapper


@timed
def step():
    return sum(range(10_000))


for _ in range(3):
    step()
print(len(step.durations), all(d > 0 for d in step.durations))""",
        },
        {
            "level": "Hard",
            "prompt": "Write `@validate_range(**limits)` that checks keyword arguments against (low, high) limits before calling the function, e.g. `@validate_range(channel=(1, 233), tx_power=(0, 30))`.",
            "solution": "A factory capturing the limits dict; the wrapper checks each named kwarg present in the call.",
            "solution_code": """import functools


def validate_range(**limits):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for name, (low, high) in limits.items():
                if name in kwargs and not low <= kwargs[name] <= high:
                    raise ValueError(f"{func.__name__}: {name}={kwargs[name]} outside {low}..{high}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


@validate_range(channel=(1, 233), tx_power=(0, 30))
def configure(ap, *, channel, tx_power):
    return f"{ap}: ch{channel} {tx_power} dBm"


print(configure("ap-1", channel=37, tx_power=23))
try:
    configure("ap-1", channel=37, tx_power=36)
except ValueError as err:
    print("ValueError:", err)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What is a decorator?", "a": "A callable that takes a function and returns a replacement. `@deco` above `def f` means `f = deco(f)`. Usually the replacement is a wrapper closure that adds behaviour before and after calling the original.", "follow": "When does the decorator itself run? (Once, when the def statement executes.)"},
        {"level": "Intermediate", "q": "Why use functools.wraps?", "a": "Without it the wrapper's __name__, __doc__, __module__ and signature metadata replace the original's, which breaks logs, tracebacks, help() and tools like pytest. wraps copies them over and adds __wrapped__.", "follow": "How do you call the undecorated function? (func.__wrapped__.)"},
        {"level": "Intermediate", "q": "Write a decorator that takes arguments.", "a": "Three levels: a factory that receives the options and returns a decorator, which receives the function and returns a wrapper, which runs per call. Use it as @retry(times=3), with parentheses.", "follow": "How could one decorator work both with and without parentheses? (Check whether the first argument is callable.)"},
        {"level": "Intermediate", "q": "In what order are stacked decorators applied?", "a": "Bottom-up: the one closest to the def is applied first, so @a @b def f is a(b(f)). At call time a's wrapper runs first and calls into b's.", "follow": "Why put a skip guard outermost? (So nothing else, like retries or timing, runs for a skipped test.)"},
        {"level": "Advanced", "q": "How would you write a retry decorator safely?", "a": "Accept the attempt count, delay/backoff and the exception types to retry; catch only those; log each failure; re-raise the last error unchanged (bare raise) when attempts run out; use functools.wraps. Never retry on AssertionError, which would hide real test failures.", "follow": "Why exponential backoff with jitter? (So many clients retrying together don't hammer a recovering device in sync.)"},
    ],
    "quiz": [
        {"q": "`@d` above `def f` is equivalent to...", "options": ["f = d", "f = d(f)", "d = f(d)", "f = d()"], "answer": 1, "why": "The decorator is called with the function."},
        {"q": "Stacked `@a` then `@b` above def f gives...", "options": ["b(a(f))", "a(b(f))", "a(f) and b(f)", "f(a, b)"], "answer": 1, "why": "The nearest decorator is applied first."},
        {"q": "What does functools.wraps preserve?", "options": ["Performance", "Name, docstring and metadata", "Arguments", "Return value"], "answer": 1, "why": "It copies metadata and sets __wrapped__."},
        {"q": "A decorator with arguments has how many nested levels?", "options": ["1", "2", "3", "4"], "answer": 2, "why": "Factory, decorator, wrapper."},
        {"q": "When does the decorator function itself execute?", "options": ["Every call", "At definition time", "At import of callers", "Never"], "answer": 1, "why": "The wrapper is what runs per call."},
    ],
    "cards": [
        {"front": "Decorator skeleton", "back": "def d(func): @wraps(func) def wrapper(*a, **kw): return func(*a, **kw); return wrapper"},
        {"front": "Decorator with options", "back": "Factory → decorator → wrapper (3 levels); use with ()."},
        {"front": "Stack order", "back": "@a @b def f  ==  a(b(f))"},
        {"front": "Get the original function", "back": "`func.__wrapped__`"},
    ],
}


M_3_9 = {
    "id": "3.9",
    "title": "Context Managers",
    "hours": 2.5,
    "summary": "Guaranteed setup and teardown with with: writing __enter__/__exit__, exception handling and suppression, @contextmanager, ExitStack and suppress.",
    "concepts": [
        {
            "title": "__enter__ and __exit__",
            "concept": "A **context manager** is any object with `__enter__` and `__exit__`. `with cm as x:` calls `__enter__` (its return value becomes `x`), runs the block, and then **always** calls `__exit__(exc_type, exc, traceback)`, whether the block finished, returned early or raised. If the block raised, `__exit__` sees the exception; returning `True` **suppresses** it, while returning `False` or `None` lets it propagate.",
            "why": "Lab state must be restored even when a test crashes: attenuators back to their baseline, captures stopped, SSH sessions closed, bench locks released. A context manager turns that into a single `with` line instead of try/finally blocks copied into every test.",
            "syntax": "class Attenuation:\n    def __enter__(self):\n        ...           # setup\n        return thing  # bound by 'as'\n    def __exit__(self, exc_type, exc, tb):\n        ...           # teardown, always runs\n        return False  # don't suppress\n\nwith Attenuation(att, 40) as a: ...",
            "code": """class FakeAttenuator:  ## Stands in for a real attenuator driver
    def __init__(self) -> None:  ## Starts at the baseline
        self.db = 10  ## Current attenuation


class Attenuation:  ## Temporarily set attenuation, then always restore it
    def __init__(self, att: FakeAttenuator, db: int) -> None:  ## Configuration only; nothing happens yet
        self.att = att  ## The device to control
        self.db = db  ## Target value inside the block
        self.saved: int | None = None  ## The value to restore

    def __enter__(self) -> FakeAttenuator:  ## Runs at the start of the with block
        self.saved = self.att.db  ## Remember the current state
        self.att.db = self.db  ## Apply the temporary setting
        print(f"  set {self.db} dB (was {self.saved})")  ## Visible setup
        return self.att  ## Becomes the `as` target

    def __exit__(self, exc_type, exc, tb) -> bool:  ## Runs at the end of the block, ALWAYS
        self.att.db = self.saved  ## Restore, whatever happened
        print(f"  restored {self.saved} dB ({exc_type.__name__ if exc_type else 'no error'})")  ## Shows what ended the block
        return False  ## Don't suppress exceptions: failures still propagate


class IgnoreTimeouts:  ## A context manager that DOES suppress one exception type
    def __enter__(self):  ## Nothing to set up
        return self  ## Convention when there's nothing else useful to return

    def __exit__(self, exc_type, exc, tb) -> bool:  ## Decides whether to swallow the error
        if exc_type is not None and issubclass(exc_type, TimeoutError):  ## Only timeouts
            print(f"  ignored: {exc}")  ## Record that we swallowed it
            return True  ## True means: the exception is handled, continue after the with block
        return False  ## Everything else propagates


def main() -> None:
    att = FakeAttenuator()  ## Baseline 10 dB
    with Attenuation(att, 40) as a:  ## __enter__ runs here
        print("  measuring at", a.db, "dB")  ## The block sees the temporary value
    print("after block:", att.db)  ## Back to baseline
    try:  ## Now a block that fails
        with Attenuation(att, 60):  ## Setup runs
            raise RuntimeError("iperf3 crashed")  ## The test blows up mid-measurement
    except RuntimeError as err:  ## The error still reaches us...
        print("caught:", err, "| attenuator at", att.db, "dB")  ## ...and the attenuator was restored first
    with IgnoreTimeouts():  ## A suppressing manager
        raise TimeoutError("ping timed out")  ## Swallowed by __exit__
    print("continued after the timeout")  ## Execution carries on


if __name__ == "__main__":
    main()""",
            "under": "`with A() as x: body` behaves like: `mgr = A(); x = mgr.__enter__(); try: body; except BaseException: if not mgr.__exit__(*sys.exc_info()): raise; else: mgr.__exit__(None, None, None)`. The `as` target is whatever `__enter__` returns, not the manager itself (files return themselves, which is why `with open(...) as f` gives you the file). Python looks up `__enter__` and `__exit__` on the type.",
            "gotchas": [
                {
                    "title": "Accidentally suppressing every exception",
                    "note": "An __exit__ that returns True unconditionally hides real test failures: the assertion error below vanishes.",
                    "wrong": """class Capture:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        print("capture stopped")
        return True

with Capture():
    assert 880 >= 900, "throughput below threshold"
print("test reported as passed!")""",
                    "fixed": """class Capture:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        print("capture stopped")
        return False

try:
    with Capture():
        assert 880 >= 900, "throughput below threshold"
except AssertionError as err:
    print("test failed:", err)""",
                }
            ],
            "best": "Make __exit__ restore state unconditionally and return False unless suppression is the explicit purpose. Keep __init__ free of side effects so creating the manager doesn't change the lab; do the work in __enter__.",
        },
        {
            "title": "@contextmanager, ExitStack and suppress",
            "concept": "`contextlib.contextmanager` turns a generator into a context manager: code before `yield` is the setup, the yielded value is the `as` target, and code after it is the teardown. Wrap the `yield` in `try/finally` so teardown runs even when the block raises. `ExitStack` manages a **variable number** of context managers and closes them in reverse order. `suppress(SomeError)` ignores one exception type in a block.",
            "why": "Starting packet captures on however many monitor interfaces a bench has, then stopping all of them in reverse order whatever happens, is exactly what ExitStack is for. @contextmanager makes each capture manager a few lines long.",
            "syntax": "@contextmanager\ndef capture(iface):\n    start(iface)\n    try:\n        yield handle\n    finally:\n        stop(iface)\n\nwith ExitStack() as stack:\n    caps = [stack.enter_context(capture(i)) for i in ifaces]\n\nwith suppress(FileNotFoundError): ...",
            "code": """from contextlib import ExitStack, contextmanager, suppress  ## Context manager helpers


@contextmanager  ## Turns this generator into a context manager
def packet_capture(iface: str):  ## Start a capture, hand back the frame list, always stop it
    print(f"  start capture on {iface}")  ## Setup: before yield
    frames: list[str] = []  ## Stands in for a pcap handle
    try:  ## Protect the teardown
        yield frames  ## The with block runs here; frames becomes the `as` target
    finally:  ## Runs on success AND on exceptions
        print(f"  stop capture on {iface}: {len(frames)} frames")  ## Teardown: after yield


def main() -> None:
    with packet_capture("mon0") as frames:  ## Setup runs
        frames.extend(["beacon", "probe-req", "auth"])  ## Use the yielded object
    with ExitStack() as stack:  ## Manages any number of context managers
        caps = [stack.enter_context(packet_capture(i)) for i in ["mon0", "mon1"]]  ## Enter each; ExitStack remembers them
        caps[0].append("beacon")  ## Work with all of them
        print("  both captures running")  ## Inside the combined block
    with suppress(FileNotFoundError):  ## Ignore exactly this exception type
        open("/nonexistent/ap.log")  ## Raises FileNotFoundError, which is suppressed
    print("continued after suppress")  ## Execution continues normally
    try:  ## The finally in packet_capture also runs on errors
        with packet_capture("mon2") as frames:  ## Setup
            frames.append("assoc-req")  ## Some work
            raise ValueError("bad frame")  ## The block fails
    except ValueError as err:  ## Propagated after the capture was stopped
        print("caught:", err)  ## Teardown already printed


if __name__ == "__main__":
    main()""",
            "under": "The decorator wraps the generator in a `_GeneratorContextManager`: `__enter__` calls `next()` to run up to the `yield`; `__exit__` either calls `next()` again (normal exit) or **throws** the block's exception into the generator at the `yield`, which is why a `try/finally` around it sees the error. ExitStack keeps a stack of exit callbacks and unwinds them last-in, first-out, so later resources are released before earlier ones.",
            "gotchas": [
                {
                    "title": "No try/finally around yield",
                    "note": "If the block raises, the exception is thrown in at the yield and the teardown after it is skipped: the capture never stops.",
                    "wrong": """from contextlib import contextmanager

@contextmanager
def capture(iface):
    print("start", iface)
    yield
    print("stop", iface)

try:
    with capture("mon0"):
        raise RuntimeError("test failed")
except RuntimeError:
    print("did the capture stop?")""",
                    "fixed": """from contextlib import contextmanager

@contextmanager
def capture(iface):
    print("start", iface)
    try:
        yield
    finally:
        print("stop", iface)

try:
    with capture("mon0"):
        raise RuntimeError("test failed")
except RuntimeError:
    print("capture stopped first")""",
                }
            ],
            "best": "Write small resource managers with @contextmanager and always put the yield inside try/finally. Use ExitStack whenever the number of resources is decided at runtime (benches, interfaces, devices). Use suppress only for errors that genuinely don't matter, never as a blanket.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write a class-based context manager `Channel(ap, ch)` that sets `ap['channel']` on enter and restores the previous channel on exit.",
            "solution": "Save in __enter__, restore in __exit__, return False.",
            "solution_code": """class Channel:
    def __init__(self, ap, ch):
        self.ap, self.ch = ap, ch
    def __enter__(self):
        self.saved = self.ap["channel"]
        self.ap["channel"] = self.ch
        return self.ap
    def __exit__(self, *exc):
        self.ap["channel"] = self.saved
        return False


ap = {"name": "ap-1", "channel": 36}
with Channel(ap, 149) as a:
    print("inside:", a["channel"])
print("after:", ap["channel"])""",
        },
        {
            "level": "Medium",
            "prompt": "Write `@contextmanager bench_lock(name, locks)` that adds the bench to a `locks` set on entry, refuses (RuntimeError) if it's already locked, and always removes it on exit.",
            "solution": "Check before yield, clean up in finally.",
            "solution_code": """from contextlib import contextmanager


@contextmanager
def bench_lock(name, locks):
    if name in locks:
        raise RuntimeError(f"{name} is already in use")
    locks.add(name)
    try:
        yield name
    finally:
        locks.discard(name)


locks = set()
with bench_lock("bench07", locks):
    print("locked:", sorted(locks))
    try:
        with bench_lock("bench07", locks):
            pass
    except RuntimeError as err:
        print("RuntimeError:", err)
print("after:", sorted(locks))""",
        },
        {
            "level": "Hard",
            "prompt": "Use ExitStack to lock every bench named in a list, then show that when one lock fails part-way, the locks already taken are released.",
            "solution": "If entering a later context raises, ExitStack unwinds the ones already entered.",
            "solution_code": """from contextlib import ExitStack, contextmanager


@contextmanager
def bench_lock(name, locks):
    if name in locks:
        raise RuntimeError(f"{name} busy")
    locks.add(name)
    try:
        yield name
    finally:
        locks.discard(name)


locks = {"bench09"}
try:
    with ExitStack() as stack:
        for bench in ["bench07", "bench08", "bench09"]:
            stack.enter_context(bench_lock(bench, locks))
        print("all locked")
except RuntimeError as err:
    print("RuntimeError:", err)
print("locks held now:", sorted(locks))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What does a with statement guarantee?", "a": "That the context manager's __exit__ runs when the block ends, however it ends: normally, via return or break, or via an exception. That's what makes it ideal for cleanup.", "follow": "What is bound by 'as'? (Whatever __enter__ returns.)"},
        {"level": "Intermediate", "q": "What do __exit__'s arguments and return value mean?", "a": "It receives the exception type, value and traceback (all None if the block succeeded). Returning a truthy value suppresses the exception; returning False or None lets it propagate.", "follow": "When is suppression appropriate? (Rarely: e.g. contextlib.suppress for an expected, harmless error.)"},
        {"level": "Intermediate", "q": "How do you write a context manager with contextlib?", "a": "Decorate a generator with @contextmanager: setup before yield, the yielded value becomes the as-target, teardown after it. Put the yield inside try/finally so teardown runs on exceptions too.", "follow": "Why is finally necessary? (The block's exception is thrown into the generator at the yield.)"},
        {"level": "Advanced", "q": "What is ExitStack for?", "a": "Managing a dynamic number of context managers or cleanup callbacks in one with block. It unwinds them in reverse order, including when entering a later one fails, and can transfer ownership with pop_all().", "follow": "How would you open N files safely? (stack.enter_context(open(p)) in a loop.)"},
    ],
    "quiz": [
        {"q": "When does __exit__ run?", "options": ["Only on success", "Only on exceptions", "Always", "Only with as"], "answer": 2, "why": "That's the guarantee."},
        {"q": "Returning True from __exit__...", "options": ["Re-raises", "Suppresses the exception", "Restarts the block", "Has no effect"], "answer": 1, "why": "Truthy means handled."},
        {"q": "In @contextmanager, the as-target is...", "options": ["The generator", "The yielded value", "None", "The function"], "answer": 1, "why": "Whatever is yielded."},
        {"q": "ExitStack closes resources in which order?", "options": ["Same as entered", "Reverse of entering", "Random", "Alphabetical"], "answer": 1, "why": "Last in, first out."},
        {"q": "`with suppress(KeyError): d['x']` when x is missing...", "options": ["Raises KeyError", "Continues silently", "Returns None", "Logs a warning"], "answer": 1, "why": "suppress swallows that type."},
    ],
    "cards": [
        {"front": "Context manager protocol", "back": "__enter__ (setup, returns as-target) and __exit__(type, value, tb)"},
        {"front": "__exit__ returns True", "back": "The exception is suppressed."},
        {"front": "Generator-based manager", "back": "@contextmanager with yield inside try/finally"},
        {"front": "Dynamic number of resources", "back": "contextlib.ExitStack"},
        {"front": "Ignore one exception type", "back": "`with contextlib.suppress(Err):`"},
    ],
}


M_3_10 = {
    "id": "3.10",
    "title": "Descriptors & Metaclasses",
    "hours": 2,
    "summary": "How properties really work: descriptors with __get__/__set__/__set_name__, reusable validated fields, class registries with __init_subclass__, and what metaclasses are (and when not to use them).",
    "concepts": [
        {
            "title": "Descriptors",
            "concept": "A **descriptor** is an object stored as a **class attribute** that defines `__get__`, and optionally `__set__` and `__delete__`. When you access that attribute on an instance, Python calls those methods instead of reading the instance dict. `__set_name__` tells the descriptor the attribute name it was assigned to. Properties, methods, classmethods and `__slots__` are all built on descriptors. Writing your own lets you reuse one validation rule across many fields and classes.",
            "why": "TX power, channel, attenuation and MCS index all need range validation. One `RangeValidated` descriptor replaces a dozen nearly identical property getter/setter pairs.",
            "syntax": "class Field:\n    def __set_name__(self, owner, name): self.private = \"_\" + name\n    def __get__(self, obj, objtype=None):\n        return self if obj is None else getattr(obj, self.private)\n    def __set__(self, obj, value): ...\n\nclass RadioConfig:\n    tx_power = Field()",
            "code": """class RangeValidated:  ## A reusable validated-attribute descriptor
    def __init__(self, low: int, high: int, unit: str = "") -> None:  ## The rule for this field
        self.low, self.high, self.unit = low, high, unit  ## Stored on the descriptor (shared config, not data)

    def __set_name__(self, owner: type, name: str) -> None:  ## Called once, when the owning class is created
        self.public = name  ## e.g. "tx_power"
        self.private = "_" + name  ## Where each INSTANCE's value will live

    def __get__(self, obj, objtype=None):  ## Called for instance.tx_power (and Class.tx_power)
        if obj is None:  ## Accessed on the class itself
            return self  ## Return the descriptor so tools can inspect it
        return getattr(obj, self.private)  ## Read this instance's own value

    def __set__(self, obj, value: int) -> None:  ## Called for instance.tx_power = value
        if not self.low <= value <= self.high:  ## The shared validation rule
            raise ValueError(f"{self.public}={value}{self.unit} outside {self.low}..{self.high}{self.unit}")  ## Names the field
        setattr(obj, self.private, value)  ## Store on the instance, not on the descriptor


class RadioConfig:  ## Uses the descriptor for two fields
    tx_power = RangeValidated(0, 30, " dBm")  ## Class attribute holding a descriptor instance
    channel = RangeValidated(1, 233)  ## Same rule type, different limits

    def __init__(self, channel: int, tx_power: int) -> None:  ## Ordinary constructor
        self.channel = channel  ## Goes through RangeValidated.__set__
        self.tx_power = tx_power  ## Validated too


def main() -> None:
    cfg = RadioConfig(37, 23)  ## Valid values
    other = RadioConfig(149, 17)  ## A second instance with its own values
    print(cfg.channel, cfg.tx_power, other.tx_power, vars(cfg))  ## Values live in each instance's dict under _name
    try:  ## An invalid assignment
        cfg.tx_power = 36  ## Rejected by __set__
    except ValueError as err:  ## Same message format for every field
        print("ValueError:", err)  ## Names the field and limits
    print(type(RadioConfig.__dict__["tx_power"]).__name__, RadioConfig.tx_power.public)  ## On the class: the descriptor itself


if __name__ == "__main__":
    main()""",
            "under": "For `obj.attr`, `object.__getattribute__` checks the type's MRO first: a **data descriptor** (one with `__set__` or `__delete__`) found there wins over the instance dict; otherwise the instance dict wins; then **non-data descriptors** (only `__get__`, like plain functions) apply. That precedence is why a property can't be bypassed by writing to `obj.__dict__`, and why `cached_property` (a non-data descriptor) can store its result in the instance dict and be skipped on later reads.",
            "gotchas": [
                {
                    "title": "Storing the value on the descriptor",
                    "note": "There's one descriptor per class, shared by all instances, so storing data on self makes every instance see the last value set.",
                    "wrong": """class Field:
    def __get__(self, obj, objtype=None):
        return self.value
    def __set__(self, obj, value):
        self.value = value

class Radio:
    channel = Field()

a, b = Radio(), Radio()
a.channel = 36
b.channel = 149
print(a.channel, b.channel)""",
                    "fixed": """class Field:
    def __set_name__(self, owner, name):
        self.private = "_" + name
    def __get__(self, obj, objtype=None):
        return getattr(obj, self.private)
    def __set__(self, obj, value):
        setattr(obj, self.private, value)

class Radio:
    channel = Field()

a, b = Radio(), Radio()
a.channel = 36
b.channel = 149
print(a.channel, b.channel)""",
                }
            ],
            "best": "Reach for a custom descriptor only when the same attribute logic repeats across many fields; for one or two fields a property is clearer. Keep per-instance data on the instance (via `__set_name__`) and configuration on the descriptor. Consider pydantic or attrs, which provide validated fields out of the box.",
        },
        {
            "title": "__init_subclass__ and metaclasses",
            "concept": "Classes are objects too, created by a **metaclass**; the default is `type`. A custom metaclass can intercept class creation, but most real needs are covered by the simpler `__init_subclass__` hook, which runs on the base class every time a subclass is defined and can receive keyword arguments from the class statement. A common use is an automatic **plugin registry**: every driver subclass registers itself under a vendor name.",
            "why": "A framework that picks a driver by the `vendor:` field in a testbed file needs a name → class map. With `__init_subclass__`, adding a new vendor is just writing the subclass; no central list to forget to update.",
            "syntax": "class Driver:\n    registry = {}\n    def __init_subclass__(cls, vendor, **kw):\n        super().__init_subclass__(**kw)\n        Driver.registry[vendor] = cls\n\nclass VendorA(Driver, vendor=\"vendor-a\"): ...\n\nclass Meta(type):\n    def __new__(mcls, name, bases, ns): ...",
            "code": """class Driver:  ## Base class that keeps a registry of all subclasses
    registry: dict[str, type] = {}  ## vendor name -> driver class

    def __init_subclass__(cls, vendor: str, **kwargs) -> None:  ## Runs whenever a subclass is DEFINED
        super().__init_subclass__(**kwargs)  ## Keep cooperative inheritance working
        cls.vendor = vendor  ## Record the vendor on the subclass
        Driver.registry[vendor] = cls  ## Register it under that name

    @classmethod  ## Factory that picks the right subclass
    def for_vendor(cls, vendor: str) -> "Driver":  ## e.g. from the testbed file
        return cls.registry[vendor]()  ## Look up and instantiate


class VendorADriver(Driver, vendor="vendor-a"):  ## Keyword arguments in the class statement go to __init_subclass__
    def clients_cmd(self) -> str:  ## Vendor-specific behaviour
        return "show wireless clients"  ## Vendor A's CLI


class VendorBDriver(Driver, vendor="vendor-b"):  ## Registers itself just by being defined
    def clients_cmd(self) -> str:  ## Vendor B's behaviour
        return "iwinfo wlan0 assoclist"  ## OpenWrt-style


class TracingMeta(type):  ## A metaclass: the class of a class
    def __new__(mcls, name, bases, namespace):  ## Runs when a class using this metaclass is created
        cls = super().__new__(mcls, name, bases, namespace)  ## Build the class normally
        print(f"metaclass built {name} with {sorted(k for k in namespace if not k.startswith('__'))}")  ## Inspect the class body
        return cls  ## Return the new class


class Plugin(metaclass=TracingMeta):  ## Creating this class runs TracingMeta.__new__
    def run(self) -> str:  ## A method in the class body
        return "plugin ran"  ## Behaviour


def main() -> None:
    print(sorted(Driver.registry))  ## Both vendors registered automatically
    drv = Driver.for_vendor("vendor-b")  ## Chosen by name, as a config file would
    print(type(drv).__name__, drv.vendor, drv.clients_cmd())  ## The right class was instantiated
    print(type(Plugin).__name__, type(Driver).__name__, type(type).__name__)  ## Classes are instances of metaclasses


if __name__ == "__main__":
    main()""",
            "under": "A class statement collects the body into a namespace dict, then calls `metaclass(name, bases, namespace)`. `type.__new__` builds the class, calls `__set_name__` on descriptors, and then calls the parent's `__init_subclass__`. ABCs (`ABCMeta`) and enums (`EnumType`) are examples of standard-library metaclasses; that's also why combining two different metaclasses in one class can raise a metaclass conflict.",
            "gotchas": [
                {
                    "title": "Forgetting the class keyword argument",
                    "note": "When __init_subclass__ requires vendor=, a subclass without it fails at definition time, which is actually useful: the mistake surfaces immediately.",
                    "wrong": """class Driver:
    registry = {}
    def __init_subclass__(cls, vendor, **kwargs):
        super().__init_subclass__(**kwargs)
        Driver.registry[vendor] = cls

class ForgotVendor(Driver):
    pass""",
                    "fixed": """class Driver:
    registry = {}
    def __init_subclass__(cls, vendor, **kwargs):
        super().__init_subclass__(**kwargs)
        Driver.registry[vendor] = cls

class NewVendor(Driver, vendor="vendor-c"):
    pass

print(Driver.registry)""",
                }
            ],
            "best": "Use `__init_subclass__` for registries and subclass validation; it covers the large majority of what people used metaclasses for. Write a real metaclass only when you must change how the class object itself is built, and say why in a comment. Most framework code never needs one.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Add a `mcs = RangeValidated(0, 13)` field to a class and show that 11 is accepted and 14 rejected.",
            "solution": "Reuse the descriptor; only the limits change.",
            "solution_code": """class RangeValidated:
    def __init__(self, low, high):
        self.low, self.high = low, high
    def __set_name__(self, owner, name):
        self.name, self.private = name, "_" + name
    def __get__(self, obj, objtype=None):
        return self if obj is None else getattr(obj, self.private)
    def __set__(self, obj, value):
        if not self.low <= value <= self.high:
            raise ValueError(f"{self.name}={value} outside {self.low}..{self.high}")
        setattr(obj, self.private, value)


class Rate:
    mcs = RangeValidated(0, 13)


r = Rate()
r.mcs = 11
print(r.mcs)
try:
    r.mcs = 14
except ValueError as err:
    print("ValueError:", err)""",
        },
        {
            "level": "Medium",
            "prompt": "Write a `Typed(kind)` descriptor that only accepts values of a given type, and use it for `ssid: str` and `hidden: bool` on an SsidProfile class.",
            "solution": "Check isinstance in __set__ and raise TypeError.",
            "solution_code": """class Typed:
    def __init__(self, kind):
        self.kind = kind
    def __set_name__(self, owner, name):
        self.name, self.private = name, "_" + name
    def __get__(self, obj, objtype=None):
        return self if obj is None else getattr(obj, self.private)
    def __set__(self, obj, value):
        if not isinstance(value, self.kind):
            raise TypeError(f"{self.name} must be {self.kind.__name__}, got {type(value).__name__}")
        setattr(obj, self.private, value)


class SsidProfile:
    ssid = Typed(str)
    hidden = Typed(bool)
    def __init__(self, ssid, hidden=False):
        self.ssid, self.hidden = ssid, hidden


print(vars(SsidProfile("lab-wpa3")))
try:
    SsidProfile("lab", hidden="yes")
except TypeError as err:
    print("TypeError:", err)""",
        },
        {
            "level": "Hard",
            "prompt": "Extend the Driver registry so `__init_subclass__` also verifies that every subclass defines `clients_cmd`, raising TypeError at class-definition time if not.",
            "solution": "Inspect the new class inside __init_subclass__ before registering it.",
            "solution_code": """class Driver:
    registry = {}
    def __init_subclass__(cls, vendor, **kwargs):
        super().__init_subclass__(**kwargs)
        if "clients_cmd" not in vars(cls):
            raise TypeError(f"{cls.__name__} must define clients_cmd()")
        Driver.registry[vendor] = cls


class GoodDriver(Driver, vendor="good"):
    def clients_cmd(self):
        return "show clients"


try:
    class LazyDriver(Driver, vendor="lazy"):
        pass
except TypeError as err:
    print("TypeError:", err)
print(sorted(Driver.registry))""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "What is a descriptor?", "a": "An object stored as a class attribute that defines __get__ (and optionally __set__/__delete__), so attribute access on instances calls those methods. property, methods, classmethod, staticmethod and __slots__ are all descriptors.", "follow": "Data vs non-data descriptor? (Data descriptors define __set__ or __delete__ and take precedence over the instance dict.)"},
        {"level": "Intermediate", "q": "What does __set_name__ do?", "a": "Python calls it on each descriptor when the owning class is created, passing the class and the attribute name. It lets the descriptor know its own name for storage and error messages, without repeating it.", "follow": "Which Python version added it? (3.6.)"},
        {"level": "Advanced", "q": "What is a metaclass, and have you needed one?", "a": "The class of a class: it controls how class objects are created (type is the default). Most needs are better met by __init_subclass__, class decorators or descriptors. Honest answer for most automation code: rarely or never; ABCMeta and EnumType are the ones you use indirectly.", "follow": "What is a metaclass conflict? (Combining bases whose metaclasses aren't compatible.)"},
        {"level": "Advanced", "q": "How would you build a plugin registry?", "a": "Use __init_subclass__ on a base class to record each subclass in a dict when it's defined, keyed by a name passed in the class statement. A classmethod factory then looks classes up by name from config. Alternatives: entry points for plugins in other packages (as pytest does).", "follow": "How does the registry learn about plugins in another package? (They must be imported, e.g. via importlib or packaging entry points.)"},
    ],
    "quiz": [
        {"q": "Where must a descriptor live to work?", "options": ["Instance dict", "As a class attribute", "In a module global", "In __slots__ only"], "answer": 1, "why": "Descriptors are found on the type."},
        {"q": "Which takes precedence over the instance dict?", "options": ["Non-data descriptor", "Data descriptor", "Neither", "Both"], "answer": 1, "why": "Data descriptors win; non-data ones lose to the instance dict."},
        {"q": "`type(type)` is...", "options": ["object", "type", "class", "metaclass"], "answer": 1, "why": "type is its own metaclass."},
        {"q": "When does __init_subclass__ run?", "options": ["At each instantiation", "When a subclass is defined", "At import of the base", "Never automatically"], "answer": 1, "why": "Class creation time."},
        {"q": "Which is built on descriptors?", "options": ["property", "list", "dict", "tuple"], "answer": 0, "why": "property is a data descriptor."},
    ],
    "cards": [
        {"front": "Descriptor methods", "back": "__get__, __set__, __delete__, plus __set_name__"},
        {"front": "Data descriptor precedence", "back": "Wins over the instance __dict__."},
        {"front": "Simplest class registry", "back": "__init_subclass__ on the base class"},
        {"front": "Metaclass", "back": "The class of a class; type by default."},
    ],
}
