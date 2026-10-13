"""Phase 3 content: modules 3.1-3.5."""

M_3_1 = {
    "id": "3.1",
    "title": "Classes & Objects",
    "hours": 2.5,
    "summary": "Defining classes, __init__ and self, instance attributes and methods, __repr__ vs __str__, class attributes and the name-mangling convention.",
    "concepts": [
        {
            "title": "Classes, __init__, self and methods",
            "concept": "A `class` is a blueprint; calling it creates an **instance** (an object). `__init__` runs right after the object is created and sets its **instance attributes**. Every method receives the instance as its first parameter, called `self` by convention, so `ap.set_channel(\"5G\", 149)` is really `AccessPoint.set_channel(ap, \"5G\", 149)`. `__repr__` gives an unambiguous developer view (used in lists, logs and the REPL); `__str__` gives a friendly one (used by `print` and f-strings).",
            "why": "Lab entities (APs, radios, stations, attenuators) each carry state plus the operations that act on it. A class keeps the two together, so `ap.set_channel(...)` replaces a loose dict and five helper functions that must all agree on its keys.",
            "syntax": "class AccessPoint:\n    def __init__(self, name: str) -> None:\n        self.name = name\n\n    def method(self, arg): ...\n\n    def __repr__(self) -> str:\n        return f\"AccessPoint({self.name!r})\"\n\nap = AccessPoint(\"ap-1\")",
            "code": """class AccessPoint:  ## A blueprint for lab access points
    \"\"\"A lab access point under test.\"\"\"  ## Class docstring

    def __init__(self, name: str, model: str, mgmt_ip: str) -> None:  ## Runs for every new instance; self is that new object
        self.name = name  ## Instance attributes: stored on this particular object
        self.model = model  ## Each AP gets its own copy of these values
        self.mgmt_ip = mgmt_ip  ## Management address used by drivers later
        self.radios: dict[str, int] = {}  ## A NEW dict per instance (band -> channel)

    def set_channel(self, band: str, channel: int) -> None:  ## A method: a function that receives the instance as self
        self.radios[band] = channel  ## Changes this AP's state only

    def describe(self) -> str:  ## Methods can read any attribute through self
        chans = ", ".join(f"{b}=ch{c}" for b, c in sorted(self.radios.items()))  ## Format the configured radios
        return f"{self.name} ({self.model}) {chans or 'no radios configured'}"  ## Fallback text for an empty dict

    def __repr__(self) -> str:  ## Developer view: ideally looks like the code to recreate the object
        return f"AccessPoint({self.name!r}, {self.model!r}, {self.mgmt_ip!r})"  ## !r adds quotes around the strings

    def __str__(self) -> str:  ## Friendly view used by print() and str()
        return f"{self.name} @ {self.mgmt_ip}"  ## Short and human-readable


def main() -> None:
    ap1 = AccessPoint("ap-1", "WAP-7E", "10.0.0.11")  ## Calling the class creates an instance and runs __init__
    ap2 = AccessPoint("ap-2", "WAP-6E", "10.0.0.12")  ## A second, independent instance
    ap1.set_channel("5G", 149)  ## Same as AccessPoint.set_channel(ap1, "5G", 149)
    ap1.set_channel("6G", 37)  ## ap1 now has two radios
    print(ap1.describe())  ## Uses ap1's state
    print(ap2.describe())  ## ap2's radios dict is still empty
    print(repr(ap1))  ## __repr__
    print(str(ap1))  ## __str__
    print([ap1, ap2])  ## Containers always show their items' __repr__
    print(type(ap1).__name__, isinstance(ap1, AccessPoint), ap1 is ap2)  ## Two separate objects of the same class
    print(sorted(vars(ap2)))  ## vars() shows the instance's attribute dict


if __name__ == "__main__":
    main()""",
            "under": "Calling `AccessPoint(...)` first runs `__new__` to allocate the object, then `__init__` to fill it in. Instance attributes live in a per-object dict, `obj.__dict__` (what `vars()` returns). Methods live once, on the class. Looking up `ap1.set_channel` finds the function on the class and returns a **bound method** that remembers `ap1`, which is how `self` gets passed automatically.",
            "gotchas": [
                {
                    "title": "Forgetting self",
                    "note": "Python always passes the instance as the first argument, so a method without a parameter for it fails when called.",
                    "wrong": """class Bench:
    def describe():
        return "bench07"

print(Bench().describe())""",
                    "fixed": """class Bench:
    def describe(self):
        return "bench07"

print(Bench().describe())""",
                },
                {
                    "title": "No __repr__: unreadable logs",
                    "note": "Without __repr__, objects print as their class name and a memory address. Logs and failure messages become useless.",
                    "wrong": """class Radio:
    def __init__(self, band, channel):
        self.band, self.channel = band, channel

print(repr(Radio("5G", 36)).startswith("<__main__.Radio object at"))""",
                    "fixed": """class Radio:
    def __init__(self, band, channel):
        self.band, self.channel = band, channel

    def __repr__(self):
        return f"Radio(band={self.band!r}, channel={self.channel})"

print([Radio("5G", 36), Radio("6G", 37)])""",
                },
            ],
            "best": "Set every instance attribute in `__init__` so an object's shape is obvious from one place. Always define `__repr__` for classes that appear in logs or test failures. Keep methods small; if a method doesn't use `self`, it may belong outside the class or as a static method (Module 3.2).",
        },
        {
            "title": "Class attributes, conventions and name mangling",
            "concept": "Attributes assigned in the class body are **class attributes**, shared by every instance. Reading `obj.attr` checks the instance first, then the class. **Assigning** `obj.attr = ...` always creates or changes an instance attribute, which then shadows the class one. A single leading underscore (`_last_rssi`) means \"internal, please don't touch\". Two leading underscores (`__secret`) trigger **name mangling**: Python renames it to `_ClassName__secret` to avoid clashes in subclasses. Neither is real privacy.",
            "why": "Class attributes suit constants such as valid channel ranges and counters shared by all instances. A mutable class attribute, though, is the object-oriented version of the mutable-default trap from Module 2.1.",
            "syntax": "class Station:\n    count = 0            # class attribute, shared\n    def __init__(self):\n        self._cache = None   # internal by convention\n        self.__key = \"x\"     # stored as _Station__key\n        Station.count += 1",
            "code": """class Station:  ## A Wi-Fi client
    count = 0  ## Class attribute: one value shared by the class and all instances
    default_band = "5G"  ## Another class attribute, used as a default

    def __init__(self, mac: str) -> None:  ## Per-instance setup
        self.mac = mac  ## Instance attribute
        self.band = Station.default_band  ## Copy the class default into the instance
        self._last_rssi: int | None = None  ## Leading underscore: internal by convention only
        self.__psk = "lab-secret"  ## Two underscores: Python renames this to _Station__psk
        Station.count += 1  ## Update the shared counter through the class


def main() -> None:
    a = Station("aa:01")  ## count becomes 1
    b = Station("aa:02")  ## count becomes 2
    print(Station.count, a.count)  ## Reading through the instance falls back to the class attribute
    a.default_band = "6G"  ## Assignment creates an INSTANCE attribute on a only
    print(a.default_band, b.default_band, Station.default_band)  ## a's own value shadows the class; b and the class are unchanged
    print(sorted(vars(a)))  ## Note the mangled name _Station__psk
    try:  ## The original name doesn't exist outside the class
        a.__psk  ## Outside the class body no mangling happens, so Python looks for '__psk'
    except AttributeError as err:  ## And doesn't find it
        print("AttributeError:", err)  ## Message names the missing attribute
    print(a._Station__psk)  ## Still reachable: mangling avoids accidents, it isn't security


if __name__ == "__main__":
    main()""",
            "under": "Attribute lookup on an instance checks the instance `__dict__`, then the class, then its base classes (and data descriptors such as properties take priority, Module 3.10). `Station.count += 1` reads and rebinds the class attribute, while `self.count += 1` would read the class value and then create an instance attribute: a common counter bug. Name mangling is a compile-time rewrite of `__name` inside the class body.",
            "gotchas": [
                {
                    "title": "A mutable class attribute is shared by everyone",
                    "note": "Every bench appends to the same list object, which lives on the class.",
                    "wrong": """class Bench:
    devices = []

    def add(self, device):
        self.devices.append(device)

b1, b2 = Bench(), Bench()
b1.add("ap-1")
print(b2.devices)""",
                    "fixed": """class Bench:
    def __init__(self):
        self.devices = []

    def add(self, device):
        self.devices.append(device)

b1, b2 = Bench(), Bench()
b1.add("ap-1")
print(b1.devices, b2.devices)""",
                },
                {
                    "title": "self.count += 1 doesn't update the class counter",
                    "note": "It reads the class value but writes a new instance attribute, so the class counter never moves.",
                    "wrong": """class Station:
    count = 0
    def __init__(self):
        self.count += 1

Station(); Station()
print(Station.count)""",
                    "fixed": """class Station:
    count = 0
    def __init__(self):
        Station.count += 1

Station(); Station()
print(Station.count)""",
                },
            ],
            "best": "Use class attributes only for constants and deliberately shared state, and always update them through the class name. Create every mutable attribute in `__init__`. Mark internals with a single underscore; reserve double underscores for the rare case of avoiding name clashes in subclasses.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write a `Radio` class with band, channel and width, a `__repr__`, and a method `label()` returning e.g. `\"5G ch149/80MHz\"`.",
            "solution": "Store the three values in __init__ and build strings from them.",
            "solution_code": """class Radio:
    def __init__(self, band, channel, width=20):
        self.band = band
        self.channel = channel
        self.width = width

    def label(self):
        return f"{self.band} ch{self.channel}/{self.width}MHz"

    def __repr__(self):
        return f"Radio({self.band!r}, {self.channel}, {self.width})"


r = Radio("5G", 149, 80)
print(r.label(), [r])""",
        },
        {
            "level": "Medium",
            "prompt": "Give `Station` a `record(rssi)` method that stores samples and a `mean_rssi()` method that returns None when there are no samples. Make sure two stations never share samples.",
            "solution": "Create the list in __init__ and guard the empty case.",
            "solution_code": """class Station:
    def __init__(self, mac):
        self.mac = mac
        self.samples = []

    def record(self, rssi):
        self.samples.append(rssi)

    def mean_rssi(self):
        if not self.samples:
            return None
        return round(sum(self.samples) / len(self.samples), 1)


a, b = Station("aa:01"), Station("aa:02")
for r in [-52, -55, -61]:
    a.record(r)
print(a.mean_rssi(), b.mean_rssi(), a.samples is b.samples)""",
        },
        {
            "level": "Hard",
            "prompt": "Write a `Testbed` class that assigns each new AP a unique management IP from 10.0.0.11 upwards (a class-level counter), and keeps its own list of APs per testbed instance.",
            "solution": "A class attribute holds the next host number; each instance has its own list.",
            "solution_code": """class Testbed:
    _next_host = 11

    def __init__(self, name):
        self.name = name
        self.aps = []

    def add_ap(self, ap_name):
        ip = f"10.0.0.{Testbed._next_host}"
        Testbed._next_host += 1
        self.aps.append((ap_name, ip))
        return ip


bench7, bench8 = Testbed("bench07"), Testbed("bench08")
bench7.add_ap("ap-1"); bench8.add_ap("ap-1"); bench7.add_ap("ap-2")
print(bench7.aps, bench8.aps)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What is self?", "a": "The instance the method was called on. `obj.method(x)` is equivalent to `Class.method(obj, x)`, and Python passes obj as the first parameter, which is named self by convention.", "follow": "Is self a keyword? (No, just a convention; any name works, but never use another.)"},
        {"level": "Beginner", "q": "What is the difference between __repr__ and __str__?", "a": "__repr__ is the unambiguous developer representation, used by repr(), containers, the REPL and debuggers. __str__ is the readable one used by print() and str(); if it's missing, Python falls back to __repr__.", "follow": "Which should you always define? (__repr__.)"},
        {"level": "Intermediate", "q": "Class attribute vs instance attribute?", "a": "A class attribute lives on the class and is shared by all instances; an instance attribute lives in each object's __dict__. Reading falls back from the instance to the class, but assigning through an instance always creates an instance attribute.", "follow": "Why is a list as a class attribute dangerous? (All instances mutate the same list.)"},
        {"level": "Intermediate", "q": "Does Python have private attributes?", "a": "No. A single underscore is a convention meaning internal. A double underscore triggers name mangling to _ClassName__attr, which prevents accidental clashes in subclasses but can still be accessed.", "follow": "When would you use the double underscore? (Rarely: in base classes meant to be subclassed by others.)"},
        {"level": "Advanced", "q": "What happens when you call a class?", "a": "type.__call__ runs: it calls __new__ to create the object, then __init__ on it if __new__ returned an instance of the class. __init__ must return None.", "follow": "When would you override __new__? (Immutable types, singletons, caching instances.)"},
    ],
    "quiz": [
        {"q": "What does print(obj) use first?", "options": ["__repr__", "__str__", "__name__", "__doc__"], "answer": 1, "why": "print uses __str__, falling back to __repr__."},
        {"q": "`a.x = 5` when x is a class attribute does what?", "options": ["Changes the class attribute", "Creates an instance attribute on a", "Raises AttributeError", "Changes all instances"], "answer": 1, "why": "Assignment through an instance creates an instance attribute."},
        {"q": "Inside class Station, `self.__key` is stored as...", "options": ["__key", "_key", "_Station__key", "Station.__key"], "answer": 2, "why": "Name mangling adds _ClassName."},
        {"q": "What does `[obj]` display?", "options": ["obj.__str__()", "obj.__repr__()", "The address only", "obj.__dict__"], "answer": 1, "why": "Containers show their items' repr."},
        {"q": "Where should mutable per-object state be created?", "options": ["As a class attribute", "In __init__", "In __repr__", "At module level"], "answer": 1, "why": "So each instance gets its own object."},
    ],
    "cards": [
        {"front": "`obj.method(x)` is the same as...", "back": "`Class.method(obj, x)`"},
        {"front": "__repr__ vs __str__", "back": "Developer view (containers, logs) vs friendly view (print)."},
        {"front": "Class attribute read vs write via instance", "back": "Read falls back to the class; write creates an instance attribute."},
        {"front": "`_x` vs `__x`", "back": "Internal by convention vs name-mangled to _Class__x."},
        {"front": "vars(obj)", "back": "The instance's attribute dict (obj.__dict__)."},
    ],
}


M_3_2 = {
    "id": "3.2",
    "title": "Methods & Properties",
    "hours": 2,
    "summary": "Instance, class and static methods, alternate constructors, and properties that validate input or compute values on the fly.",
    "concepts": [
        {
            "title": "Instance, class and static methods",
            "concept": "An **instance method** receives the object (`self`) and works with its state. A **class method** (`@classmethod`) receives the class (`cls`); its main use is an **alternate constructor** such as `Radio.from_string(\"6G/37/320MHz\")`, which also works correctly for subclasses. A **static method** (`@staticmethod`) receives neither; it's a plain function that lives in the class's namespace because it belongs with it conceptually.",
            "why": "Configs arrive in many forms: a CLI string, a YAML dict, a row from a CSV. One alternate constructor per format keeps parsing out of `__init__`, and a static frequency helper documents the channel arithmetic right next to the class that uses it.",
            "syntax": "class Radio:\n    def freq(self): ...                  # instance\n\n    @classmethod\n    def from_string(cls, text): return cls(...)\n\n    @staticmethod\n    def center_freq_mhz(band, ch): ...",
            "code": """class Radio:  ## One radio of an AP
    BASE_MHZ = {"2G": 2407, "5G": 5000, "6G": 5950}  ## Channel-numbering origin per band

    def __init__(self, band: str, channel: int, width: int = 20) -> None:  ## The primary constructor takes typed values
        self.band = band  ## e.g. "6G"
        self.channel = channel  ## e.g. 37
        self.width = width  ## Channel width in MHz

    @classmethod  ## Receives the class, not an instance
    def from_string(cls, text: str) -> "Radio":  ## Alternate constructor for "6G/37/320MHz"
        band, ch, width = text.split("/")  ## Split into three fields
        return cls(band, int(ch), int(width.removesuffix("MHz")))  ## cls(...) builds an instance of whichever class was used

    @staticmethod  ## Receives neither the class nor an instance
    def center_freq_mhz(band: str, channel: int) -> int:  ## Pure arithmetic that belongs with Radio
        return Radio.BASE_MHZ[band] + 5 * channel  ## e.g. 5 GHz ch36 = 5000 + 180 = 5180 MHz (2.4 GHz ch14 is a special case)

    def freq(self) -> int:  ## Instance method: uses this radio's state
        return self.center_freq_mhz(self.band, self.channel)  ## Static methods are callable through self too

    def __repr__(self) -> str:  ## Readable output
        return f"Radio({self.band!r}, {self.channel}, {self.width})"  ## Mirrors the constructor call


def main() -> None:
    r = Radio.from_string("6G/37/320MHz")  ## Called on the class
    print(r, r.freq())  ## 6 GHz channel 37 is centred at 6135 MHz
    print(Radio.center_freq_mhz("5G", 36), Radio.center_freq_mhz("2G", 6))  ## No instance needed
    radios = [Radio.from_string(s) for s in ["5G/149/80MHz", "2G/1/20MHz"]]  ## Parse a list of config strings
    print(radios, [x.freq() for x in radios])  ## 5745 MHz and 2412 MHz


if __name__ == "__main__":
    main()""",
            "under": "`@classmethod` and `@staticmethod` are descriptors (Module 3.10) that change what the method receives when looked up. A classmethod binds to the class even when called on an instance; a staticmethod doesn't bind at all. Because `from_string` calls `cls(...)` rather than `Radio(...)`, a subclass such as `WifiSevenRadio.from_string(...)` returns a WifiSevenRadio.",
            "gotchas": [
                {
                    "title": "Hard-coding the class in an alternate constructor",
                    "note": "Writing Radio(...) inside the classmethod means subclasses get a plain Radio back.",
                    "wrong": """class Radio:
    def __init__(self, band, channel):
        self.band, self.channel = band, channel

    @classmethod
    def from_string(cls, text):
        band, ch = text.split("/")
        return Radio(band, int(ch))

class EhtRadio(Radio):
    pass

print(type(EhtRadio.from_string("6G/37")).__name__)""",
                    "fixed": """class Radio:
    def __init__(self, band, channel):
        self.band, self.channel = band, channel

    @classmethod
    def from_string(cls, text):
        band, ch = text.split("/")
        return cls(band, int(ch))

class EhtRadio(Radio):
    pass

print(type(EhtRadio.from_string("6G/37")).__name__)""",
                }
            ],
            "best": "Keep `__init__` simple and typed, add one `from_xxx` classmethod per input format, and always return `cls(...)`. Use static methods sparingly, for helpers tightly tied to the class; a module-level function is often just as good.",
        },
        {
            "title": "Properties: validation and computed attributes",
            "concept": "`@property` turns a method into an attribute you read without parentheses. Adding `@name.setter` lets you run code, typically validation, whenever the attribute is assigned. A property without a setter is **read-only**. The value itself is stored in an internal attribute such as `self._db`. Because the syntax stays `obj.db`, you can start with a plain attribute and add validation later without changing any caller.",
            "why": "An attenuator must reject 120 dB before the command reaches the hardware, and a radio's \"path loss label\" or frequency should always reflect its current settings rather than a stale stored copy.",
            "syntax": "class Attenuator:\n    @property\n    def db(self) -> int:\n        return self._db\n\n    @db.setter\n    def db(self, value: int) -> None:\n        if not 0 <= value <= 95:\n            raise ValueError(...)\n        self._db = value",
            "code": """class Attenuator:  ## A programmable attenuator channel
    MAX_DB = 95  ## Hardware limit

    def __init__(self, name: str, db: int = 0) -> None:  ## Initial setting
        self.name = name  ## Label used in error messages
        self.db = db  ## Goes through the setter, so the initial value is validated too

    @property  ## Reading a.db calls this method
    def db(self) -> int:  ## The getter
        return self._db  ## The real value lives in an internal attribute

    @db.setter  ## Assigning a.db = x calls this method
    def db(self, value: int) -> None:  ## The setter
        if not 0 <= value <= self.MAX_DB:  ## Validate before storing
            raise ValueError(f"{self.name}: {value} dB outside 0..{self.MAX_DB}")  ## Clear error that names the device
        self._db = value  ## Store in the internal attribute, NOT self.db

    @property  ## A computed, read-only attribute (no setter)
    def path_loss_label(self) -> str:  ## Derived from the current value every time
        return "near" if self._db < 30 else "mid" if self._db < 60 else "far"  ## Chained conditional expression


def main() -> None:
    att = Attenuator("att-1")  ## Starts at 0 dB
    att.db = 42  ## Looks like an attribute assignment, but validation runs
    print(att.db, att.path_loss_label)  ## Reading needs no parentheses
    try:  ## An out-of-range value
        att.db = 120  ## The setter raises
    except ValueError as err:  ## Bad values never reach the device
        print("ValueError:", err)  ## Names the attenuator and the limits
    try:  ## A read-only property
        att.path_loss_label = "near"  ## There is no setter
    except AttributeError as err:  ## So assignment is refused
        print("AttributeError:", err)  ## Explains which property has no setter
    print(att.db)  ## The failed assignment left the value unchanged


if __name__ == "__main__":
    main()""",
            "under": "`property` is a data descriptor stored on the class. When you read `att.db`, Python finds it on the class and calls its getter, before even looking in the instance dict; assignment calls the setter. The `@db.setter` line creates a new property object that has both functions and rebinds the name `db` to it, which is why the getter and setter must have the same name.",
            "gotchas": [
                {
                    "title": "Infinite recursion in a setter",
                    "note": "Assigning self.db inside the db setter calls the setter again, forever. Store into the underscore attribute.",
                    "wrong": """class Attenuator:
    @property
    def db(self):
        return self._db

    @db.setter
    def db(self, value):
        self.db = value

a = Attenuator()
a.db = 10""",
                    "fixed": """class Attenuator:
    @property
    def db(self):
        return self._db

    @db.setter
    def db(self, value):
        self._db = value

a = Attenuator()
a.db = 10
print(a.db)""",
                },
                {
                    "title": "Calling a property like a method",
                    "note": "The property already returns the value; adding () tries to call that int.",
                    "wrong": """class Radio:
    @property
    def freq(self):
        return 5180

print(Radio().freq())""",
                    "fixed": """class Radio:
    @property
    def freq(self):
        return 5180

print(Radio().freq)""",
                },
            ],
            "best": "Start with plain attributes; switch to a property only when you need validation, a computed value or read-only access. Keep getters cheap and side-effect free, because readers expect attribute access to be fast. Never perform slow device I/O inside a property; make that an explicit method.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Add a read-only property `is_dfs` to a 5 GHz Radio that's True for channels 52–144.",
            "solution": "A property without a setter that computes from channel.",
            "solution_code": """class Radio:
    def __init__(self, channel):
        self.channel = channel

    @property
    def is_dfs(self):
        return 52 <= self.channel <= 144


print([(ch, Radio(ch).is_dfs) for ch in [36, 52, 100, 149]])""",
        },
        {
            "level": "Medium",
            "prompt": "Write `Station.from_iw_line(line)` that parses `\"aa:bb:cc:00:00:01 -54 dBm\"` into a Station with mac and rssi.",
            "solution": "A classmethod that splits the line and returns cls(...).",
            "solution_code": """class Station:
    def __init__(self, mac, rssi):
        self.mac, self.rssi = mac, rssi

    @classmethod
    def from_iw_line(cls, line):
        mac, rssi, _unit = line.split()
        return cls(mac, int(rssi))

    def __repr__(self):
        return f"Station({self.mac!r}, {self.rssi})"


print(Station.from_iw_line("aa:bb:cc:00:00:01 -54 dBm"))""",
        },
        {
            "level": "Hard",
            "prompt": "Give a `TxPower` class a `dbm` property validated to 0–30 and a `mw` property with BOTH a getter and a setter that converts to and from dBm, so setting mw=100 makes dbm 20.",
            "solution": "Store only dBm; mw reads and writes through the conversion.",
            "solution_code": """import math


class TxPower:
    def __init__(self, dbm=10):
        self.dbm = dbm

    @property
    def dbm(self):
        return self._dbm

    @dbm.setter
    def dbm(self, value):
        if not 0 <= value <= 30:
            raise ValueError(f"{value} dBm out of range 0..30")
        self._dbm = value

    @property
    def mw(self):
        return round(10 ** (self._dbm / 10), 3)

    @mw.setter
    def mw(self, value):
        self.dbm = round(10 * math.log10(value), 2)


p = TxPower()
p.mw = 100
print(p.dbm, p.mw)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "classmethod vs staticmethod?", "a": "A classmethod receives the class as cls and is typically used for alternate constructors that should also work for subclasses. A staticmethod receives nothing extra; it's a regular function namespaced inside the class.", "follow": "Why return cls(...) rather than ClassName(...)? (So subclasses get instances of themselves.)"},
        {"level": "Intermediate", "q": "Why use properties instead of getter/setter methods?", "a": "They keep the simple attribute syntax (`a.db = 42`) while allowing validation or computation. You can start with a public attribute and convert it to a property later without changing callers, which is why Python code rarely needs get_x()/set_x().", "follow": "How do you make an attribute read-only? (A property with no setter.)"},
        {"level": "Intermediate", "q": "What causes RecursionError in a property setter?", "a": "Assigning to the property's own name inside its setter (`self.db = value`) calls the setter again. Store the value in a different internal attribute such as `self._db`.", "follow": "What about the getter returning self.db? (Same problem.)"},
        {"level": "Advanced", "q": "How does @property work internally?", "a": "property is a data descriptor with __get__, __set__ and __delete__. Because it's a data descriptor on the class, it takes priority over the instance __dict__ during attribute lookup. @x.setter returns a copy of the property with the setter added.", "follow": "What's functools.cached_property? (A non-data descriptor that computes once and stores the result in the instance dict.)"},
    ],
    "quiz": [
        {"q": "What does a classmethod receive first?", "options": ["self", "cls", "Nothing", "The module"], "answer": 1, "why": "The class it was called on."},
        {"q": "How do you read a property `freq`?", "options": ["obj.freq()", "obj.freq", "obj.get_freq()", "obj['freq']"], "answer": 1, "why": "Properties are read like attributes."},
        {"q": "Assigning to a property with no setter raises...", "options": ["ValueError", "TypeError", "AttributeError", "Nothing"], "answer": 2, "why": "The property has no setter."},
        {"q": "Which builds the right subclass in an alternate constructor?", "options": ["return Radio(...)", "return cls(...)", "return self(...)", "return super()"], "answer": 1, "why": "cls is the class it was called on."},
        {"q": "Where should a property setter store the value?", "options": ["self.<same name>", "An internal attribute like self._db", "A global", "The class"], "answer": 1, "why": "Using the same name recurses."},
    ],
    "cards": [
        {"front": "Alternate constructor", "back": "`@classmethod def from_x(cls, ...): return cls(...)`"},
        {"front": "staticmethod", "back": "A plain function in the class namespace; no self or cls."},
        {"front": "Validated attribute", "back": "@property getter + @name.setter that checks, storing in self._name."},
        {"front": "Read-only attribute", "back": "A property without a setter."},
    ],
}


M_3_3 = {
    "id": "3.3",
    "title": "Inheritance, MRO, super() & Composition",
    "hours": 3,
    "summary": "Subclassing and overriding, super() and cooperative multiple inheritance, the method resolution order, mixins, and when composition beats inheritance.",
    "concepts": [
        {
            "title": "Inheritance, overriding and super()",
            "concept": "A subclass (`class VendorBAP(BaseAP)`) inherits every method and attribute of its base class and can **override** any of them by defining a method with the same name. `super()` reaches the next class's version, so an override can extend behaviour instead of replacing it, most often `super().__init__(...)`. Code written against the base class works with any subclass, which is **polymorphism**.",
            "why": "Every vendor's AP is managed differently but your tests want one interface: `ap.connect()`, `ap.show_clients_cmd()`. A base driver holds the shared logic and each vendor subclass overrides just the parts that differ.",
            "syntax": "class BaseAP:\n    def __init__(self, name): self.name = name\n    def connect(self): ...\n\nclass VendorBAP(BaseAP):\n    def __init__(self, name, port=22):\n        super().__init__(name)   # run the base setup\n        self.port = port\n    def connect(self):            # override\n        return super().connect() + \"...\"",
            "code": """class BaseAP:  ## Shared behaviour for every vendor's AP
    def __init__(self, name: str, ip: str) -> None:  ## Common state
        self.name = name  ## Every AP has a name...
        self.ip = ip  ## ...and a management IP

    def connect(self) -> str:  ## Default connection command
        return f"ssh admin@{self.ip}"  ## Subclasses may extend this

    def show_clients_cmd(self) -> str:  ## Each vendor must provide this
        raise NotImplementedError(f"{type(self).__name__} must implement show_clients_cmd")  ## Fails loudly if forgotten

    def describe(self) -> str:  ## Written once, against the base interface
        return f"{type(self).__name__} {self.name}: {self.show_clients_cmd()}"  ## Calls whichever override the instance has


class VendorAAP(BaseAP):  ## Inherits __init__, connect and describe
    def show_clients_cmd(self) -> str:  ## Overrides only what differs
        return "show wireless clients"  ## Vendor A's CLI command


class VendorBAP(BaseAP):  ## A vendor that needs extra state
    def __init__(self, name: str, ip: str, port: int = 22) -> None:  ## Extends the constructor
        super().__init__(name, ip)  ## Let the base class set name and ip
        self.port = port  ## Then add our own attribute

    def connect(self) -> str:  ## Extends rather than replaces
        return super().connect() + f" -p {self.port}"  ## Reuse the base command and add the port

    def show_clients_cmd(self) -> str:  ## Vendor B's command
        return "iwinfo wlan0 assoclist"  ## OpenWrt-style tooling


def main() -> None:
    aps = [VendorAAP("ap-1", "10.0.0.11"), VendorBAP("ap-2", "10.0.0.12", port=2222)]  ## Different classes, one interface
    for ap in aps:  ## Polymorphism: the same calls work for every subclass
        print(ap.describe(), "|", ap.connect())  ## Each object runs its own overrides
    print(isinstance(aps[1], BaseAP), issubclass(VendorBAP, BaseAP))  ## A VendorBAP IS a BaseAP
    try:  ## The base class on its own is incomplete
        BaseAP("ap-x", "10.0.0.99").describe()  ## show_clients_cmd isn't implemented here
    except NotImplementedError as err:  ## Explicit failure instead of silent nonsense
        print("NotImplementedError:", err)  ## Module 3.4 shows how ABCs catch this earlier


if __name__ == "__main__":
    main()""",
            "under": "When you call `ap.describe()`, Python looks for `describe` on the instance's class, then on each base class in the **method resolution order** (MRO), and uses the first one found. Inside `describe`, `self.show_clients_cmd()` starts that search again from the instance's actual class, which is why the base class can call methods that only subclasses define. `super()` without arguments works out the class and instance from the method's context.",
            "gotchas": [
                {
                    "title": "Forgetting super().__init__()",
                    "note": "The subclass's __init__ replaces the base one, so attributes the base would have set never exist.",
                    "wrong": """class BaseAP:
    def __init__(self, name):
        self.name = name

class VendorBAP(BaseAP):
    def __init__(self, name, port):
        self.port = port

ap = VendorBAP("ap-2", 2222)
print(ap.name)""",
                    "fixed": """class BaseAP:
    def __init__(self, name):
        self.name = name

class VendorBAP(BaseAP):
    def __init__(self, name, port):
        super().__init__(name)
        self.port = port

ap = VendorBAP("ap-2", 2222)
print(ap.name, ap.port)""",
                }
            ],
            "best": "Keep base classes small and focused on a shared interface. Call `super().__init__()` in every subclass constructor. Override to extend with `super()` where possible, and raise `NotImplementedError` (or use an ABC) for methods subclasses must provide.",
        },
        {
            "title": "Multiple inheritance, MRO, mixins and composition",
            "concept": "A class can inherit from several bases. Python linearises the hierarchy into one **MRO** (C3 linearization), visible as `Cls.__mro__`; every base appears once, after all its subclasses. `super()` means \"the next class in the MRO of this object\", not \"my parent\", so in a diamond each class's method runs exactly once when they all call `super()`. **Mixins** are small classes that add one capability. **Composition** means an object *has* other objects (an AP has radios) instead of *being* one; it's usually more flexible than inheritance.",
            "why": "Lab devices often need several capabilities (rebootable, monitored, loggable). Mixins add them without copying code. And an AP with a dict of Radio objects models reality better than an AP that inherits from Radio.",
            "syntax": "class LabAP(Rebootable, Monitored): ...\nLabAP.__mro__        # the lookup order\nsuper().setup()      # next class in the MRO\n\nclass AccessPoint:   # composition\n    def __init__(self, radios):\n        self.radios = {r.band: r for r in radios}",
            "code": """class Device:  ## The common root
    def setup(self) -> list[str]:  ## Each class contributes a setup step
        return ["Device"]  ## The last step in the chain


class Rebootable(Device):  ## A capability
    def setup(self) -> list[str]:  ## Adds its step, then defers to the next class in the MRO
        return ["Rebootable"] + super().setup()  ## super() here may NOT be Device (see output)


class Monitored(Device):  ## Another capability
    def setup(self) -> list[str]:  ## Same cooperative pattern
        return ["Monitored"] + super().setup()  ## Continues along the MRO


class LabAP(Rebootable, Monitored):  ## Diamond: both bases inherit from Device
    def setup(self) -> list[str]:  ## Starts the chain
        return ["LabAP"] + super().setup()  ## Next in the MRO is Rebootable


class Radio:  ## Composition: a part, not a parent
    def __init__(self, band: str, channel: int) -> None:  ## Its own state
        self.band, self.channel = band, channel  ## Tuple assignment of two attributes


class AccessPoint:  ## HAS radios rather than IS a radio
    def __init__(self, name: str, radios: list[Radio]) -> None:  ## Receives its parts
        self.name = name  ## Own state
        self.radios = {r.band: r for r in radios}  ## Holds the parts, keyed by band

    def channels(self) -> dict[str, int]:  ## Delegates to its parts
        return {band: r.channel for band, r in self.radios.items()}  ## Reads from each Radio


def main() -> None:
    print(LabAP().setup())  ## Every class runs exactly once, Device last
    print([cls.__name__ for cls in LabAP.__mro__])  ## The C3 linearization Python computed
    ap = AccessPoint("ap-1", [Radio("5G", 149), Radio("6G", 37)])  ## Assemble from parts
    print(ap.channels())  ## Delegation through composition
    ap.radios["6G"] = Radio("6G", 69)  ## Swap a part at runtime: hard to do with inheritance
    print(ap.channels())  ## Reflects the new radio


if __name__ == "__main__":
    main()""",
            "under": "C3 linearization builds the MRO so that each class comes before its bases and the left-to-right order of bases in the class statement is respected. For `LabAP(Rebootable, Monitored)` that gives LabAP → Rebootable → Monitored → Device → object. Inside `Rebootable.setup`, `super()` resolves to the class after Rebootable in **the instance's** MRO, which is Monitored, even though Rebootable only lists Device as its base.",
            "gotchas": [
                {
                    "title": "Calling a parent class directly in a diamond",
                    "note": "Hard-coding Device.setup(self) instead of super() skips Monitored entirely, so one capability never initialises.",
                    "wrong": """class Device:
    def setup(self): return ["Device"]
class Rebootable(Device):
    def setup(self): return ["Rebootable"] + Device.setup(self)
class Monitored(Device):
    def setup(self): return ["Monitored"] + Device.setup(self)
class LabAP(Rebootable, Monitored):
    def setup(self): return ["LabAP"] + Rebootable.setup(self)
print(LabAP().setup())""",
                    "fixed": """class Device:
    def setup(self): return ["Device"]
class Rebootable(Device):
    def setup(self): return ["Rebootable"] + super().setup()
class Monitored(Device):
    def setup(self): return ["Monitored"] + super().setup()
class LabAP(Rebootable, Monitored):
    def setup(self): return ["LabAP"] + super().setup()
print(LabAP().setup())""",
                }
            ],
            "best": "Prefer composition: give objects the parts they use and delegate to them. Use inheritance for genuine \"is-a\" relationships with a shared interface, and mixins for small, independent capabilities. In any hierarchy that might use multiple inheritance, call `super()` consistently rather than naming parent classes.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Create `BaseStation` with `connect()` returning `\"wpa_cli reconnect\"`, and `WindowsStation` overriding it to return `\"netsh wlan connect name=lab\"`. Call connect() on both through a loop.",
            "solution": "Override the method in the subclass; the loop doesn't need to know which is which.",
            "solution_code": """class BaseStation:
    def connect(self):
        return "wpa_cli reconnect"


class WindowsStation(BaseStation):
    def connect(self):
        return "netsh wlan connect name=lab"


for sta in [BaseStation(), WindowsStation()]:
    print(type(sta).__name__, "->", sta.connect())""",
        },
        {
            "level": "Medium",
            "prompt": "Write a `LoggingMixin` with `log(msg)` that appends to `self.events`, and use it in an `AccessPoint` class that logs every channel change. Make sure events is per instance.",
            "solution": "The mixin relies on the host class creating self.events in __init__.",
            "solution_code": """class LoggingMixin:
    def log(self, msg):
        self.events.append(f"[{self.name}] {msg}")


class AccessPoint(LoggingMixin):
    def __init__(self, name):
        self.name = name
        self.events = []
        self.channel = None

    def set_channel(self, ch):
        self.log(f"channel {self.channel} -> {ch}")
        self.channel = ch


a, b = AccessPoint("ap-1"), AccessPoint("ap-2")
a.set_channel(36); a.set_channel(149); b.set_channel(1)
print(a.events, b.events)""",
        },
        {
            "level": "Hard",
            "prompt": "Predict, then print, the MRO of `class D(B, C)` where B(A) and C(A) all define `who()` returning their name plus super().who() (A returns ['A']).",
            "solution": "C3 gives D, B, C, A, object; cooperative super visits each class once.",
            "solution_code": """class A:
    def who(self): return ["A"]
class B(A):
    def who(self): return ["B"] + super().who()
class C(A):
    def who(self): return ["C"] + super().who()
class D(B, C):
    def who(self): return ["D"] + super().who()

print(D().who(), [k.__name__ for k in D.__mro__])""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What does super() do?", "a": "It returns a proxy that finds methods on the next class in the instance's MRO. It's most often used as super().__init__(...) in a subclass constructor, and to extend an overridden method instead of copying it.", "follow": "Is the 'next class' always the parent? (No; in multiple inheritance it can be a sibling.)"},
        {"level": "Intermediate", "q": "What is the MRO and how is it computed?", "a": "The method resolution order is the linear order in which Python searches classes for an attribute. It's computed with C3 linearization: each class precedes its bases, and the order of bases in the class statement is preserved. See it with Cls.__mro__ or Cls.mro().", "follow": "What happens if no consistent order exists? (TypeError when the class is defined.)"},
        {"level": "Intermediate", "q": "Composition vs inheritance: when to use which?", "a": "Inheritance models 'is-a' with a shared interface (VendorAAP is a BaseAP). Composition models 'has-a' (an AP has radios) and is more flexible: parts can be swapped at runtime, tested separately and combined freely. Prefer composition unless polymorphism through a common base is the point.", "follow": "Give a sign that inheritance was the wrong choice. (Subclasses overriding methods just to disable them.)"},
        {"level": "Advanced", "q": "Explain the diamond problem in Python.", "a": "When D inherits from B and C, which both inherit from A, a naive scheme could run A's methods twice. Python's C3 MRO lists A once, after B and C, and cooperative super() calls visit each class exactly once. That only works if every class in the hierarchy uses super() consistently.", "follow": "What's a mixin? (A small class adding one capability, intended to be combined with others.)"},
    ],
    "quiz": [
        {"q": "MRO of `class D(B, C)` with B(A), C(A)?", "options": ["D B A C", "D B C A", "D C B A", "D A B C"], "answer": 1, "why": "C3 keeps A after both B and C."},
        {"q": "Forgetting super().__init__() in a subclass leads to...", "options": ["SyntaxError", "Missing base-class attributes", "Infinite recursion", "Nothing"], "answer": 1, "why": "The base initialiser never runs."},
        {"q": "Which relationship suits composition?", "options": ["Station is a Device", "AP has Radios", "VendorAAP is a BaseAP", "bool is an int"], "answer": 1, "why": "'Has-a' means composition."},
        {"q": "`isinstance(VendorBAP(...), BaseAP)` is...", "options": ["True", "False", "Error", "Depends on super()"], "answer": 0, "why": "Subclass instances are instances of the base."},
        {"q": "Where do you see the lookup order?", "options": ["Cls.__bases__", "Cls.__mro__", "Cls.__dict__", "dir(Cls)"], "answer": 1, "why": "__bases__ lists only direct parents."},
    ],
    "cards": [
        {"front": "super()", "back": "The next class in the instance's MRO."},
        {"front": "See the MRO", "back": "`Cls.__mro__` or `Cls.mro()`"},
        {"front": "Composition", "back": "Has-a: an object holds and delegates to its parts."},
        {"front": "Mixin", "back": "A small class adding one capability via multiple inheritance."},
        {"front": "Override vs extend", "back": "Replace a method, or call super().method() and add to it."},
    ],
}


M_3_4 = {
    "id": "3.4",
    "title": "Abstract Base Classes & Protocols",
    "hours": 2.5,
    "summary": "Enforcing driver interfaces with abc.ABC, template methods, structural typing with typing.Protocol, and what runtime_checkable can and can't check.",
    "concepts": [
        {
            "title": "Abstract base classes",
            "concept": "Inheriting from `abc.ABC` and marking methods with `@abstractmethod` makes a class **abstract**: it can't be instantiated, and neither can any subclass that leaves an abstract method unimplemented. The error appears when the object is **created**, not later when the missing method is finally called. An ABC can also provide concrete methods built on the abstract ones, the **template method** pattern.",
            "why": "A framework that supports iperf3, LANforge and a vendor traffic tool needs every driver to provide `start()` and `result_mbps()`. An ABC turns a forgotten method into an immediate, explicit error at setup time instead of an AttributeError two hours into a nightly run.",
            "syntax": "from abc import ABC, abstractmethod\n\nclass TrafficGenerator(ABC):\n    @abstractmethod\n    def start(self, duration_s: int) -> None: ...\n\n    def run(self, duration_s=10):   # concrete, uses the abstract ones\n        self.start(duration_s)\n        return self.result_mbps()",
            "code": """from abc import ABC, abstractmethod  ## The tools for defining abstract base classes


class TrafficGenerator(ABC):  ## The interface every traffic tool driver must follow
    @abstractmethod  ## Subclasses MUST implement this
    def start(self, duration_s: int) -> None:  ## Begin generating traffic
        ...  ## No body needed; the ellipsis is a placeholder

    @abstractmethod  ## Also required
    def result_mbps(self) -> float:  ## Return the measured throughput
        ...  ## Placeholder

    def run(self, duration_s: int = 10) -> float:  ## Template method: shared logic built on the abstract steps
        self.start(duration_s)  ## Calls whichever implementation the subclass provides
        return self.result_mbps()  ## Same here


class FakeIperf(TrafficGenerator):  ## A complete implementation (a test double)
    def __init__(self, mbps: float) -> None:  ## Canned result
        self.mbps = mbps  ## What result_mbps will report
        self.duration_s = None  ## Set by start()

    def start(self, duration_s: int) -> None:  ## Implements the first abstract method
        self.duration_s = duration_s  ## A real driver would launch iperf3 here

    def result_mbps(self) -> float:  ## Implements the second
        return self.mbps  ## A real driver would parse JSON output


class HalfDoneDriver(TrafficGenerator):  ## Forgot result_mbps
    def start(self, duration_s: int) -> None:  ## Only one of the two
        pass  ## Does nothing


def main() -> None:
    gen = FakeIperf(912.4)  ## Allowed: everything is implemented
    print(gen.run(30), gen.duration_s)  ## The template method drove both steps
    for cls in (TrafficGenerator, HalfDoneDriver):  ## Two classes that can't be instantiated
        try:  ## Creating the object is where the check happens
            cls()  ## Fails immediately
        except TypeError as err:  ## Python lists the missing methods
            print("TypeError:", err)  ## Clear, early failure
    print(isinstance(gen, TrafficGenerator), sorted(TrafficGenerator.__abstractmethods__))  ## The required names (a frozenset, sorted for stable output)


if __name__ == "__main__":
    main()""",
            "under": "`ABC` uses the metaclass `ABCMeta`. When a class is created, ABCMeta collects every method still marked abstract into `__abstractmethods__`; `object.__new__` refuses to instantiate a class whose set isn't empty. Abstract methods can have a body, which subclasses may call through `super()`. ABCs can also be combined with `@property` and `@classmethod` (put `@abstractmethod` innermost).",
            "gotchas": [
                {
                    "title": "Without an ABC the error comes late",
                    "note": "A plain base class lets you build an incomplete driver, and you only find out when the missing method is finally called, possibly hours into a run.",
                    "wrong": """class TrafficGenerator:
    def run(self):
        self.start()
        return self.result_mbps()

class HalfDoneDriver(TrafficGenerator):
    def start(self):
        print("traffic started")

driver = HalfDoneDriver()
print("driver created fine...")
driver.run()""",
                    "fixed": """from abc import ABC, abstractmethod

class TrafficGenerator(ABC):
    @abstractmethod
    def start(self): ...
    @abstractmethod
    def result_mbps(self): ...

class HalfDoneDriver(TrafficGenerator):
    def start(self):
        print("traffic started")

try:
    HalfDoneDriver()
except TypeError as err:
    print("caught at setup:", err)""",
                }
            ],
            "best": "Define one ABC per kind of device or tool your framework drives, keep it small (the methods tests actually call), and put shared workflow in concrete template methods. Write a fake implementation of each ABC for unit tests and offline `--sim` runs.",
        },
        {
            "title": "Protocols and duck typing",
            "concept": "Python is **duck-typed**: code works with any object that has the right methods, whatever its class. `typing.Protocol` writes that expectation down as a type: any class with matching methods **is** a structural subtype, with no inheritance needed. Static checkers such as mypy enforce it (Module 3.11). Adding `@runtime_checkable` allows `isinstance()` checks, but those only test that the method **names** exist, not their signatures.",
            "why": "Attenuators from three vendors, written by three teams, may never share a base class. A Protocol lets your sweep function accept any of them, and mypy tells you in CI if one is missing `get_db`.",
            "syntax": "from typing import Protocol, runtime_checkable\n\n@runtime_checkable\nclass Attenuator(Protocol):\n    def set_db(self, db: int) -> None: ...\n    def get_db(self) -> int: ...\n\ndef sweep(att: Attenuator, steps): ...",
            "code": """from typing import Protocol, runtime_checkable  ## Structural typing tools


@runtime_checkable  ## Also allow isinstance() checks at runtime
class Attenuator(Protocol):  ## Describes WHAT an attenuator can do, not what it inherits from
    def set_db(self, db: int) -> None: ...  ## Required method 1
    def get_db(self) -> int: ...  ## Required method 2


class VendorXAttenuator:  ## No base class at all
    def __init__(self) -> None:  ## Starts at 0 dB
        self._db = 0  ## Internal state

    def set_db(self, db: int) -> None:  ## Matches the protocol by name and signature
        self._db = db  ## A real driver sends a command

    def get_db(self) -> int:  ## Second method of the protocol
        return self._db  ## Reads back the value


class Thermometer:  ## Something unrelated
    def read(self) -> float:  ## Different methods entirely
        return 24.5  ## Degrees Celsius


def sweep(att: Attenuator, steps: range) -> list[int]:  ## Accepts anything that fits the protocol
    readings = []  ## Readback after each step
    for db in steps:  ## Each attenuation step
        att.set_db(db)  ## Duck typing: just call the method
        readings.append(att.get_db())  ## Verify by reading back
    return readings  ## The values actually set


def main() -> None:
    att = VendorXAttenuator()  ## Never mentions Attenuator in its class statement
    print(sweep(att, range(0, 31, 10)))  ## Works because it has the right methods
    print(isinstance(att, Attenuator), isinstance(Thermometer(), Attenuator))  ## Structural check: True, False
    print(Attenuator in type(att).__mro__)  ## Not a real base class


if __name__ == "__main__":
    main()""",
            "under": "A Protocol class is a special ABC whose `__subclasshook__` reports any class with the required members as a subclass. With `@runtime_checkable`, `isinstance()` just checks that each member exists (via `hasattr`), which is why it can't detect a wrong signature. Static checkers compare full signatures, which is where Protocols really pay off.",
            "gotchas": [
                {
                    "title": "runtime_checkable only checks names",
                    "note": "A class with set_db() taking no argument passes the isinstance check and then fails at the call. Rely on mypy for signature checks.",
                    "wrong": """from typing import Protocol, runtime_checkable

@runtime_checkable
class Attenuator(Protocol):
    def set_db(self, db: int) -> None: ...

class BadDriver:
    def set_db(self):
        pass

drv = BadDriver()
print(isinstance(drv, Attenuator))
drv.set_db(30)""",
                    "fixed": """from typing import Protocol, runtime_checkable

@runtime_checkable
class Attenuator(Protocol):
    def set_db(self, db: int) -> None: ...

class GoodDriver:
    def set_db(self, db: int) -> None:
        self.db = db

drv = GoodDriver()
print(isinstance(drv, Attenuator))
drv.set_db(30)
print(drv.db)""",
                }
            ],
            "best": "Use an ABC when you own the hierarchy and want shared template methods; use a Protocol when implementations come from elsewhere or you just want to describe what a function needs. Keep protocols tiny (one to three methods) and run mypy in CI so signature mismatches are caught.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Define an ABC `PowerSwitch` with abstract `on(outlet)` and `off(outlet)`, and a `FakePDU` that records actions in a list.",
            "solution": "Implement both abstract methods in the subclass.",
            "solution_code": """from abc import ABC, abstractmethod


class PowerSwitch(ABC):
    @abstractmethod
    def on(self, outlet): ...
    @abstractmethod
    def off(self, outlet): ...


class FakePDU(PowerSwitch):
    def __init__(self):
        self.actions = []
    def on(self, outlet):
        self.actions.append(("on", outlet))
    def off(self, outlet):
        self.actions.append(("off", outlet))


pdu = FakePDU()
pdu.off(3); pdu.on(3)
print(pdu.actions)""",
        },
        {
            "level": "Medium",
            "prompt": "Add a concrete `power_cycle(outlet)` template method to the PowerSwitch ABC that calls off() then on(), and show it works for FakePDU without FakePDU defining it.",
            "solution": "Concrete methods on an ABC are inherited like any other method.",
            "solution_code": """from abc import ABC, abstractmethod


class PowerSwitch(ABC):
    @abstractmethod
    def on(self, outlet): ...
    @abstractmethod
    def off(self, outlet): ...

    def power_cycle(self, outlet):
        self.off(outlet)
        self.on(outlet)
        return f"outlet {outlet} cycled"


class FakePDU(PowerSwitch):
    def __init__(self):
        self.actions = []
    def on(self, outlet):
        self.actions.append(f"on {outlet}")
    def off(self, outlet):
        self.actions.append(f"off {outlet}")


pdu = FakePDU()
print(pdu.power_cycle(5), pdu.actions)""",
        },
        {
            "level": "Hard",
            "prompt": "Define a Protocol `HasRssi` with an `rssi` attribute (as a property) and write `strongest(items)` that works with both a Station class and a ScanEntry dataclass-like class that share no base.",
            "solution": "Protocols can declare attributes; any object exposing rssi fits.",
            "solution_code": """from typing import Protocol


class HasRssi(Protocol):
    @property
    def rssi(self) -> int: ...


class Station:
    def __init__(self, mac, rssi):
        self.mac, self.rssi = mac, rssi
    def __repr__(self):
        return f"Station({self.mac})"


class ScanEntry:
    def __init__(self, bssid, rssi):
        self.bssid, self.rssi = bssid, rssi
    def __repr__(self):
        return f"ScanEntry({self.bssid})"


def strongest(items: list[HasRssi]) -> HasRssi:
    return max(items, key=lambda x: x.rssi)


print(strongest([Station("aa:01", -60), ScanEntry("ap-2", -48), Station("aa:02", -52)]))""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "What does an abstract base class give you?", "a": "A declared interface plus early enforcement: a subclass that misses an abstract method can't be instantiated, so the error appears at creation time. It can also provide shared concrete methods (template methods) built on the abstract ones.", "follow": "Can an abstract method have a body? (Yes; subclasses can call it with super().)"},
        {"level": "Intermediate", "q": "ABC vs Protocol?", "a": "An ABC is nominal: classes must inherit from it. A Protocol is structural: any class with matching members qualifies, no inheritance needed. Use ABCs for hierarchies you own with shared code; Protocols to describe what a function needs from objects you may not control.", "follow": "Which one do static type checkers use more? (Both, but Protocols are designed for static duck typing.)"},
        {"level": "Beginner", "q": "What is duck typing?", "a": "Using objects based on what they can do rather than their type: if it has set_db() and get_db(), treat it as an attenuator. Python checks for the method when you call it.", "follow": "What's the risk? (Errors appear late, at call time; Protocols plus mypy move them earlier.)"},
        {"level": "Advanced", "q": "What are the limits of @runtime_checkable?", "a": "isinstance() against a runtime-checkable Protocol only verifies that the members exist; it doesn't check signatures, return types or attribute types. It's also slower than a nominal isinstance. Treat it as a coarse guard and rely on static checking for correctness.", "follow": "How does isinstance work with ABCs that you don't inherit from? (Via __subclasshook__ or ABC.register().)"},
    ],
    "quiz": [
        {"q": "When does an ABC report a missing abstract method?", "options": ["At import", "When the object is created", "When the method is called", "Never"], "answer": 1, "why": "Instantiation fails with TypeError."},
        {"q": "Does a class need to inherit from a Protocol to satisfy it?", "options": ["Yes", "No", "Only with runtime_checkable", "Only for properties"], "answer": 1, "why": "Protocols are structural."},
        {"q": "What does isinstance(obj, RuntimeCheckableProto) check?", "options": ["Full signatures", "Only that member names exist", "Return types", "Docstrings"], "answer": 1, "why": "It checks presence, not signatures."},
        {"q": "A concrete method on an ABC that calls abstract ones is a...", "options": ["Mixin", "Template method", "Descriptor", "Factory"], "answer": 1, "why": "The template method pattern."},
        {"q": "Which decorator marks a required method?", "options": ["@required", "@abstractmethod", "@interface", "@override"], "answer": 1, "why": "From the abc module."},
    ],
    "cards": [
        {"front": "Abstract class", "back": "Inherits ABC; @abstractmethod methods must be implemented before instantiation."},
        {"front": "Template method", "back": "A concrete base method built from abstract steps."},
        {"front": "typing.Protocol", "back": "Structural interface: matching members is enough, no inheritance."},
        {"front": "@runtime_checkable limit", "back": "isinstance checks member names only."},
    ],
}


M_3_5 = {
    "id": "3.5",
    "title": "Dunder (Magic) Methods",
    "hours": 2.5,
    "summary": "Making objects behave like built-ins: equality and hashing, ordering, the container protocol, arithmetic operators, truthiness and callables.",
    "concepts": [
        {
            "title": "Equality, hashing and ordering",
            "concept": "Operators call **dunder methods**: `a == b` calls `a.__eq__(b)`, `a < b` calls `a.__lt__(b)`, `hash(a)` calls `a.__hash__()`. By default `==` means identity. If you define `__eq__`, Python sets `__hash__` to None (unhashable) unless you also define it, because **objects that compare equal must have equal hashes**. Returning `NotImplemented` for unsupported types lets Python try the other operand. `functools.total_ordering` fills in `<=`, `>` and `>=` from `__eq__` and `__lt__`.",
            "why": "MAC addresses arrive in three formats. A `MacAddress` value type that compares and hashes by value lets you put them in sets, use them as dict keys and sort them, whatever format each tool printed.",
            "syntax": "def __eq__(self, other):\n    if not isinstance(other, MacAddress):\n        return NotImplemented\n    return self.value == other.value\n\ndef __hash__(self): return hash(self.value)\ndef __lt__(self, other): ...",
            "code": """from functools import total_ordering  ## Generates the remaining comparison methods


@total_ordering  ## From __eq__ and __lt__ it adds __le__, __gt__ and __ge__
class MacAddress:  ## A value type: two objects with the same address are equal
    def __init__(self, text: str) -> None:  ## Accepts any common format
        digits = text.replace("-", "").replace(":", "").replace(".", "").lower()  ## Strip separators
        if len(digits) != 12 or any(c not in "0123456789abcdef" for c in digits):  ## Validate
            raise ValueError(f"not a MAC address: {text!r}")  ## Reject garbage early
        self.value = int(digits, 16)  ## Store one canonical form: a 48-bit integer

    def __str__(self) -> str:  ## Canonical lower-case colon format
        h = f"{self.value:012x}"  ## 12 hex digits with leading zeros
        return ":".join(h[i:i + 2] for i in range(0, 12, 2))  ## Insert colons every two digits

    def __repr__(self) -> str:  ## Developer view
        return f"MacAddress({str(self)!r})"  ## Reuses __str__

    def __eq__(self, other: object) -> bool:  ## Called for ==
        if not isinstance(other, MacAddress):  ## Unknown type
            return NotImplemented  ## Let Python try the other side (then fall back to identity: False)
        return self.value == other.value  ## Equal when the 48-bit values match

    def __hash__(self) -> int:  ## Required for sets and dict keys once __eq__ is defined
        return hash(self.value)  ## Equal objects -> equal hashes

    def __lt__(self, other: "MacAddress") -> bool:  ## Called for <, and used by sorted()
        if not isinstance(other, MacAddress):  ## Same rule as __eq__
            return NotImplemented  ## Python will raise TypeError if neither side supports it
        return self.value < other.value  ## Numeric order of the addresses


def main() -> None:
    a = MacAddress("AA-BB-CC-00-00-01")  ## Windows-style format
    b = MacAddress("aa:bb:cc:00:00:01")  ## Linux-style format
    print(a == b, a is b, len({a, b}))  ## Equal values, different objects, one set member
    seen = {a: "ap-1"}  ## Hashable, so usable as a dict key
    print(seen[MacAddress("aabb.cc00.0001")])  ## Lookup with yet another format
    print(sorted([MacAddress("aa:bb:cc:00:00:09"), a, MacAddress("00:11:22:33:44:55")]))  ## Uses __lt__
    print(a >= b, a == "aa:bb:cc:00:00:01")  ## >= comes from total_ordering; comparing with a str is simply False


if __name__ == "__main__":
    main()""",
            "under": "For `a == b`, Python calls `a.__eq__(b)`; if that returns NotImplemented it tries `b.__eq__(a)`; if both decline, `==` falls back to identity. Sets and dicts first compare hashes, then confirm with `__eq__`, which is why the hash/equality contract matters. A hashable object's hash must never change while it's in a set or dict, so value types should be effectively immutable.",
            "gotchas": [
                {
                    "title": "Defining __eq__ without __hash__",
                    "note": "Python makes the class unhashable, so it can't go in sets or be a dict key.",
                    "wrong": """class Mac:
    def __init__(self, v): self.v = v.lower()
    def __eq__(self, other): return self.v == other.v

print({Mac("AA:01"), Mac("aa:01")})""",
                    "fixed": """class Mac:
    def __init__(self, v): self.v = v.lower()
    def __eq__(self, other): return self.v == other.v
    def __hash__(self): return hash(self.v)

print(len({Mac("AA:01"), Mac("aa:01")}))""",
                }
            ],
            "best": "For value types, define `__eq__` and `__hash__` from the same canonical fields, return `NotImplemented` for foreign types, and don't mutate those fields after creation. Use `@total_ordering` or, simpler still, `@dataclass(frozen=True, order=True)` (Module 3.6), which generates all of this for you.",
        },
        {
            "title": "Containers, operators, truthiness and __call__",
            "concept": "Implementing a few dunders makes your object work with built-in syntax: `__len__` (len), `__iter__` (for loops), `__contains__` (`in`), `__getitem__` (indexing and slicing), `__bool__` (truthiness), `__add__` (`+`) and `__call__` (calling the object like a function). Python's built-ins and your own code then treat it like a native container.",
            "why": "A `ScanResult` that supports `len(scan)`, `\"ap-2\" in scan`, `scan[0]` and `scan1 + scan2` reads like plain Python in test code, and a callable threshold object can be passed anywhere a filter function is expected.",
            "syntax": "__len__ -> len(x)        __iter__ -> for v in x\n__contains__ -> v in x   __getitem__ -> x[i], x[a:b]\n__bool__ -> if x         __add__ -> x + y\n__call__ -> x(arg)",
            "code": """class ScanResult:  ## A container of (bssid, rssi) pairs, strongest first
    def __init__(self, entries: list[tuple[str, int]]) -> None:  ## Accept raw pairs
        self._entries = sorted(entries, key=lambda e: e[1], reverse=True)  ## Keep them sorted by signal strength

    def __len__(self) -> int:  ## len(scan); also used for truthiness when there's no __bool__
        return len(self._entries)  ## Delegate to the list

    def __iter__(self):  ## for bssid, rssi in scan
        return iter(self._entries)  ## Hand out the list's iterator

    def __contains__(self, bssid: str) -> bool:  ## "ap-2" in scan
        return any(b == bssid for b, _ in self._entries)  ## Membership by BSSID, not by tuple

    def __getitem__(self, index):  ## scan[0], scan[-1], scan[:2]
        return self._entries[index]  ## Lists already handle ints and slices

    def __add__(self, other: "ScanResult") -> "ScanResult":  ## scan1 + scan2
        return ScanResult(self._entries + other._entries)  ## A new merged, re-sorted result

    def __repr__(self) -> str:  ## Readable output
        return f"ScanResult({len(self)} BSSIDs)"  ## Summary rather than the whole list


class RssiThreshold:  ## A configurable filter
    def __init__(self, limit: int) -> None:  ## The threshold in dBm
        self.limit = limit  ## Stored for later calls

    def __call__(self, rssi: int) -> bool:  ## Makes instances callable: strong(-60)
        return rssi >= self.limit  ## The filtering rule


def main() -> None:
    s1 = ScanResult([("ap-1", -61), ("ap-2", -48), ("ap-3", -77)])  ## First scan
    s2 = ScanResult([("ap-4", -55)])  ## Second scan
    print(len(s1), "ap-2" in s1, "ap-9" in s1, s1[0], s1[-1])  ## Built-in syntax on our class
    for bssid, rssi in s1:  ## Iteration via __iter__
        print(f"  {bssid}: {rssi} dBm")  ## Strongest first
    merged = s1 + s2  ## __add__
    print(merged, merged[:2], bool(ScanResult([])))  ## Slicing works too; an empty scan is falsy via __len__
    strong = RssiThreshold(-65)  ## An object...
    print(strong(-60), [b for b, r in merged if strong(r)])  ## ...used exactly like a function


if __name__ == "__main__":
    main()""",
            "under": "Python looks up dunder methods on the **type**, not the instance, so assigning `obj.__len__ = ...` has no effect on `len(obj)`. If `__contains__` is missing, `in` falls back to iterating; if `__iter__` is missing, iteration falls back to calling `__getitem__` with 0, 1, 2... until IndexError. A class with `__call__` is a natural way to bundle a function with configuration.",
            "gotchas": [
                {
                    "title": "Returning the wrong type from __len__",
                    "note": "__len__ must return a non-negative int; len() refuses anything else.",
                    "wrong": """class Samples:
    def __init__(self, xs): self.xs = xs
    def __len__(self): return float(len(self.xs))

print(len(Samples([1, 2])))""",
                    "fixed": """class Samples:
    def __init__(self, xs): self.xs = xs
    def __len__(self): return len(self.xs)

print(len(Samples([1, 2])))""",
                }
            ],
            "best": "Implement only the dunders that make the object's natural operations read better, and make them behave like their built-in counterparts (`+` returns a new object, `len` is cheap, iteration doesn't mutate). If your class is really a sequence or mapping, inherit from `collections.abc.Sequence` or `Mapping` to get the rest for free.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Give a `Channel` class (band, number) `__eq__` and `__hash__` so that duplicates collapse in a set.",
            "solution": "Compare and hash the same tuple of fields.",
            "solution_code": """class Channel:
    def __init__(self, band, number):
        self.band, self.number = band, number
    def __eq__(self, other):
        if not isinstance(other, Channel):
            return NotImplemented
        return (self.band, self.number) == (other.band, other.number)
    def __hash__(self):
        return hash((self.band, self.number))
    def __repr__(self):
        return f"{self.band}/{self.number}"


print(sorted({Channel("5G", 36), Channel("5G", 36), Channel("6G", 37)}, key=repr))""",
        },
        {
            "level": "Medium",
            "prompt": "Write a `Throughput` value class (Mbps) supporting `+` with another Throughput, comparison with `<`, and a readable `__repr__`. Sum a list of them with sum() using a start value.",
            "solution": "__add__ returns a new instance; sum() needs a Throughput(0) start.",
            "solution_code": """from functools import total_ordering


@total_ordering
class Throughput:
    def __init__(self, mbps):
        self.mbps = mbps
    def __add__(self, other):
        return Throughput(self.mbps + other.mbps)
    def __eq__(self, other):
        return isinstance(other, Throughput) and self.mbps == other.mbps
    def __lt__(self, other):
        return self.mbps < other.mbps
    def __repr__(self):
        return f"{self.mbps:.1f} Mbps"


streams = [Throughput(452.1), Throughput(461.9), Throughput(447.3)]
print(sum(streams, Throughput(0)), max(streams), Throughput(1) < Throughput(2))""",
        },
        {
            "level": "Hard",
            "prompt": "Make a `RingLog` that keeps the last N log lines, supports len(), iteration, `in` (substring search over lines) and indexing, and is falsy when empty.",
            "solution": "Wrap a deque(maxlen=N) and implement the container dunders.",
            "solution_code": """from collections import deque


class RingLog:
    def __init__(self, size):
        self._lines = deque(maxlen=size)
    def add(self, line):
        self._lines.append(line)
    def __len__(self):
        return len(self._lines)
    def __iter__(self):
        return iter(self._lines)
    def __contains__(self, text):
        return any(text in line for line in self._lines)
    def __getitem__(self, i):
        return self._lines[i]


log = RingLog(3)
print(bool(log))
for line in ["assoc aa:01", "deauth reason=15", "assoc aa:02", "roam aa:01"]:
    log.add(line)
print(len(log), "deauth" in log, "roam" in log, log[-1], list(log))""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "If you override __eq__, what happens to __hash__?", "a": "Python sets __hash__ to None, making instances unhashable, because the default identity hash would break the rule that equal objects have equal hashes. Define __hash__ from the same fields used in __eq__, or don't make the object hashable.", "follow": "Why must the hashed fields not change? (The object would be stored under a stale hash and become unfindable in sets and dicts.)"},
        {"level": "Intermediate", "q": "Why return NotImplemented instead of False from __eq__?", "a": "NotImplemented tells Python to try the reflected operation on the other operand (b.__eq__(a)), which lets other types define comparisons with yours. Returning False shuts that down. For ordering operators, if both sides return NotImplemented, Python raises TypeError.", "follow": "What does == do if both sides return NotImplemented? (Falls back to identity.)"},
        {"level": "Beginner", "q": "What does __call__ do?", "a": "It makes instances callable like functions: obj(args) runs obj.__call__(args). Useful for configurable callables such as thresholds, validators or strategies that keep state.", "follow": "How is that different from a closure? (Same idea; a class is clearer when there's more state or several methods.)"},
        {"level": "Advanced", "q": "Why does assigning obj.__len__ on an instance not affect len(obj)?", "a": "Implicit special-method lookup goes through the type, skipping the instance dictionary, for speed and correctness. Define dunders on the class.", "follow": "What else gets looked up on the type? (All operator dunders, __enter__/__exit__, __iter__ and others.)"},
    ],
    "quiz": [
        {"q": "Which method does `x in obj` call first?", "options": ["__iter__", "__contains__", "__getitem__", "__eq__"], "answer": 1, "why": "It falls back to iteration only if __contains__ is missing."},
        {"q": "A class with __eq__ but no __hash__ is...", "options": ["Hashable by id", "Unhashable", "Hashable by value", "An error at definition"], "answer": 1, "why": "Python sets __hash__ to None."},
        {"q": "What does @total_ordering need?", "options": ["Only __lt__", "__eq__ and one of __lt__/__le__/__gt__/__ge__", "All six", "__hash__"], "answer": 1, "why": "It derives the rest."},
        {"q": "Without __bool__, truthiness uses...", "options": ["__len__", "__repr__", "__eq__", "Always True"], "answer": 0, "why": "__len__ == 0 means falsy."},
        {"q": "`obj(5)` calls...", "options": ["obj.__init__(5)", "obj.__call__(5)", "obj.__new__(5)", "obj.__getitem__(5)"], "answer": 1, "why": "Callable instances use __call__."},
    ],
    "cards": [
        {"front": "Equality/hash contract", "back": "a == b must imply hash(a) == hash(b)."},
        {"front": "Unsupported operand type in __eq__", "back": "Return NotImplemented."},
        {"front": "@total_ordering", "back": "Provide __eq__ + __lt__, get the rest."},
        {"front": "Container dunders", "back": "__len__, __iter__, __contains__, __getitem__"},
        {"front": "Callable object", "back": "Define __call__."},
    ],
}
