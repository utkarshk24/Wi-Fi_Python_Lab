"""Phase 2 content: modules 2.10-2.12."""

M_2_10 = {
    "id": "2.10",
    "title": "JSON, YAML, CSV & XML",
    "hours": 2.5,
    "summary": "Reading iperf3 JSON, writing results as JSON and CSV, parsing JUnit XML reports, and the YAML pitfalls that bite testbed files.",
    "concepts": [
        {
            "title": "JSON and CSV",
            "concept": "`json.loads` / `json.load` turn JSON text or a file into dicts, lists, strings, numbers, True/False and None; `json.dumps` / `json.dump` go the other way (`indent=` for humans, `sort_keys=` for stable diffs). The `csv` module handles quoting and commas inside fields correctly: `DictWriter` writes rows from dicts and `DictReader` reads rows back as dicts. CSV has no types, so **every value reads back as a string**.",
            "why": "`iperf3 -J` produces JSON; controllers' REST APIs return JSON; results go to CSV for spreadsheets and dashboards. These two formats carry most lab data.",
            "syntax": "data = json.loads(text)          # or json.load(f)\ntext = json.dumps(obj, indent=2) # or json.dump(obj, f)\n\nw = csv.DictWriter(f, fieldnames=[...]); w.writeheader(); w.writerow(row)\nfor row in csv.DictReader(f): ...   # values are str",
            "code": """import csv  ## Correct CSV reading and writing, including quoting
import io  ## StringIO: an in-memory text file, so the demo needs no disk
import json  ## JSON encoding and decoding

IPERF_JSON = \"\"\"{"start": {"test_start": {"protocol": "TCP", "num_streams": 4, "duration": 10}},
 "end": {"sum_sent": {"bits_per_second": 1823000000.0, "retransmits": 12},
         "sum_received": {"bits_per_second": 1811500000.0}}}\"\"\"  ## A trimmed iperf3 -J result


def main() -> None:
    data = json.loads(IPERF_JSON)  ## Text -> nested dicts and lists
    rx_mbps = data["end"]["sum_received"]["bits_per_second"] / 1e6  ## Navigate with keys; bits/s -> Mbit/s
    print(data["start"]["test_start"]["protocol"], f"{rx_mbps:.1f} Mbps", data["end"]["sum_sent"]["retransmits"])  ## Protocol, receiver throughput, TCP retransmits
    result = {"test": "tput_6g_320", "mbps": round(rx_mbps, 1), "passed": rx_mbps > 1500, "notes": None}  ## A result record in Python types
    print(json.dumps(result))  ## Compact JSON: True -> true, None -> null
    print(json.dumps(result, indent=2, sort_keys=True))  ## Readable and diff-friendly
    buf = io.StringIO()  ## Stands in for open("results.csv", "w", newline="")
    writer = csv.DictWriter(buf, fieldnames=["test", "mbps", "passed"], lineterminator="\\n")  ## Column order comes from fieldnames
    writer.writeheader()  ## The header row
    writer.writerow({"test": "tput_6g_320", "mbps": 1811.5, "passed": True})  ## One row per dict
    writer.writerow({"test": "tput_5g_80, retry", "mbps": 902.3, "passed": True})  ## A comma inside a value gets quoted automatically
    print(buf.getvalue(), end="")  ## The CSV text that would be in the file
    rows = list(csv.DictReader(io.StringIO(buf.getvalue())))  ## Read it back as dicts keyed by the header
    print(rows[1]["test"], type(rows[1]["mbps"]).__name__)  ## Quoting round-trips; but every value is a str


if __name__ == "__main__":
    main()""",
            "under": "JSON maps to Python as: object → dict, array → list, string → str, number → int or float, true/false → True/False, null → None. Tuples become arrays and dict keys are always strings in JSON, so some values don't round-trip exactly. The csv writer's default line ending is `\\r\\n` (the CSV standard); when writing to a real file, open it with `newline=\"\"` so Python doesn't add a second newline translation on Windows.",
            "gotchas": [
                {
                    "title": "JSON doesn't round-trip every Python type",
                    "note": "Int keys come back as strings and tuples come back as lists.",
                    "wrong": """import json
widths = {36: (80, 160)}
again = json.loads(json.dumps(widths))
print(again, again == widths)""",
                    "fixed": """import json
widths = {36: (80, 160)}
again = {int(k): tuple(v) for k, v in json.loads(json.dumps(widths)).items()}
print(again, again == widths)""",
                },
                {
                    "title": "Splitting CSV lines by hand",
                    "note": "A quoted field containing a comma splits into two. Let the csv module parse quoting.",
                    "wrong": """line = '"tput_5g_80, retry",902.3,True'
print(line.split(","))""",
                    "fixed": """import csv
line = '"tput_5g_80, retry",902.3,True'
print(next(csv.reader([line])))""",
                },
            ],
            "best": "Parse JSON into dicts at the boundary and convert to your own types (dataclasses, Module 3.6) right away. Write JSON with `indent=2, sort_keys=True` for files people diff. Always use the csv module, open CSV files with `newline=\"\"`, and convert numeric columns explicitly after reading.",
        },
        {
            "title": "XML reports and YAML testbeds",
            "concept": "`xml.etree.ElementTree` parses XML into a tree of elements: `.tag`, `.attrib` / `.get()`, `.text`, `find()` for the first child, `findall()` for direct children and `iter()` for every matching descendant. JUnit XML, the report format every CI server reads, is XML. **YAML** is the usual format for testbed and config files; it needs the third-party `PyYAML` package, and you should always load it with `yaml.safe_load`.",
            "why": "Summarising a nightly JUnit report (failures, slowest tests) and reading testbed definitions such as AP IPs, attenuator ports and country codes are the two places these formats show up in a test framework.",
            "syntax": "root = ET.fromstring(text)     # or ET.parse(path).getroot()\nfor case in root.iter(\"testcase\"):\n    case.get(\"name\"), case.find(\"failure\")\n\nimport yaml                     # pip install pyyaml\ncfg = yaml.safe_load(f)         # never yaml.load on untrusted input",
            "code": """import xml.etree.ElementTree as ET  ## The standard-library XML parser, under its usual short name

JUNIT = \"\"\"<testsuite name="nightly" tests="3" failures="1">
  <testcase classname="roaming" name="test_11r_roam" time="42.1">
    <failure message="roam latency 180 ms &gt; 50 ms"/>
  </testcase>
  <testcase classname="throughput" name="test_tput_6g_320" time="31.0"/>
  <testcase classname="throughput" name="test_tput_5g_80" time="30.4"/>
</testsuite>\"\"\"  ## A small JUnit report as pytest --junitxml would produce it


def main() -> None:
    suite = ET.fromstring(JUNIT)  ## Parse text into the root element
    print(suite.tag, suite.get("name"), suite.attrib["failures"])  ## Element name and attributes (always strings)
    for case in suite.iter("testcase"):  ## Every <testcase> element in the tree
        failure = case.find("failure")  ## The first <failure> child, or None
        verdict = "FAIL" if failure is not None else "PASS"  ## Elements can be falsy, so compare with None explicitly
        line = f"{case.get('name'):<20} {verdict} {float(case.get('time')):5.1f}s"  ## Fixed-width summary line
        print(line + (f"  {failure.get('message')}" if failure is not None else ""))  ## &gt; in the XML has been decoded to >
    total = sum(float(c.get("time")) for c in suite.findall("testcase"))  ## findall: the direct children named testcase
    print(f"total {total:.1f}s")  ## Suite duration


if __name__ == "__main__":
    main()""",
            "under": "ElementTree builds the whole document in memory, which is fine for reports; `ET.iterparse` streams very large files. An element with no children is **falsy**, which is why `if failure:` would be a bug and `is not None` is required. For XML from untrusted sources, use the `defusedxml` package to block entity-expansion attacks. PyYAML implements YAML 1.1, where unquoted `NO`, `yes`, `on` and `off` are booleans and numbers with a leading zero are octal.",
            "gotchas": [
                {
                    "title": "YAML's surprising types (needs PyYAML)",
                    "note": "In YAML 1.1 the country code NO becomes False and channel 036 becomes 30 (octal). Quote values that must stay strings. (PyYAML isn't in the in-browser runner, so run this on your machine.)",
                    "local_only": "needs the PyYAML package (pip install pyyaml)",
                    "wrong": """import yaml
print(yaml.safe_load("country: NO\\nchannel: 036\\nradio: on"))""",
                    "fixed": """import yaml
print(yaml.safe_load('country: "NO"\\nchannel: 36\\nradio: "on"'))""",
                },
                {
                    "title": "Testing an element's truthiness",
                    "note": "A `<failure/>` element with no children is falsy, so `if failure:` reports a failed test as passed. Python 3.12+ also warns that this test will change meaning in the future.",
                    "wrong": """import xml.etree.ElementTree as ET
case = ET.fromstring('<testcase name="t"><failure message="boom"/></testcase>')
failure = case.find("failure")
print("FAIL" if failure else "PASS")""",
                    "fixed": """import xml.etree.ElementTree as ET
case = ET.fromstring('<testcase name="t"><failure message="boom"/></testcase>')
failure = case.find("failure")
print("FAIL" if failure is not None else "PASS")""",
                },
            ],
            "best": "Parse JUnit XML with ElementTree and compare found elements with `is not None`. Keep testbed files in YAML, load them only with `safe_load`, quote country codes and anything that looks like a boolean or a number with leading zeros, and validate the loaded data (Module 4.4).",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Load `'{\"ssid\": \"lab-wpa3\", \"channels\": [36, 149], \"hidden\": false}'` and print the SSID, the number of channels and the type of `hidden`.",
            "solution": "JSON false becomes Python False (a bool).",
            "solution_code": """import json
cfg = json.loads('{"ssid": "lab-wpa3", "channels": [36, 149], "hidden": false}')
print(cfg["ssid"], len(cfg["channels"]), type(cfg["hidden"]).__name__)""",
        },
        {
            "level": "Medium",
            "prompt": "Read a CSV of results from text, convert `mbps` to float, and print the average per band.",
            "solution": "DictReader, explicit float conversion, then group with setdefault.",
            "solution_code": """import csv, io
text = "test,band,mbps\\nt1,5G,912.4\\nt2,6G,2841.0\\nt3,5G,887.6\\nt4,6G,2790.2\\n"
by_band = {}
for row in csv.DictReader(io.StringIO(text)):
    by_band.setdefault(row["band"], []).append(float(row["mbps"]))
for band, values in sorted(by_band.items()):
    print(band, round(sum(values) / len(values), 1))""",
        },
        {
            "level": "Hard",
            "prompt": "Turn a JUnit report into a JSON summary: total tests, failures, the failed test names with their messages, and the slowest test.",
            "solution": "Collect data while iterating the testcases, then dump the dict with indent.",
            "solution_code": """import json
import xml.etree.ElementTree as ET
xml = '''<testsuite name="nightly">
  <testcase name="test_11r_roam" time="42.1"><failure message="latency 180 ms"/></testcase>
  <testcase name="test_tput_6g_320" time="31.0"/>
  <testcase name="test_dfs_cac" time="65.3"><failure message="CAC not honoured"/></testcase>
</testsuite>'''
cases = ET.fromstring(xml).findall("testcase")
failed = {c.get("name"): c.find("failure").get("message") for c in cases if c.find("failure") is not None}
slowest = max(cases, key=lambda c: float(c.get("time")))
print(json.dumps({"total": len(cases), "failures": len(failed), "failed": failed, "slowest": slowest.get("name")}, indent=2))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What's the difference between json.load and json.loads?", "a": "`load` reads from a file object; `loads` parses a string (the s is for string). Likewise `dump` writes to a file and `dumps` returns a string.", "follow": "How do you make JSON output stable for diffs? (`sort_keys=True, indent=2`.)"},
        {"level": "Intermediate", "q": "Why use yaml.safe_load instead of yaml.load?", "a": "Full loading can construct arbitrary Python objects from tags in the document, which is dangerous with untrusted files. safe_load only builds plain types (dicts, lists, strings, numbers, booleans, None). PyYAML 6 requires an explicit Loader for load() for this reason.", "follow": "Name a YAML type surprise. (Unquoted NO or off becomes False; 036 is octal 30 in YAML 1.1.)"},
        {"level": "Intermediate", "q": "Why not parse CSV with split(',')?", "a": "Fields may be quoted and contain commas, quotes or newlines. The csv module implements the quoting rules; split breaks on the first quoted comma.", "follow": "What type are values from DictReader? (Always str; convert explicitly.)"},
        {"level": "Advanced", "q": "How would you summarise JUnit XML from many CI runs?", "a": "Parse each file with ElementTree, iterate testcase elements, treat a child failure or error element (checked with `is not None`) as a failure, extract name, classname, time and message, and store rows in a database or CSV for trends. For huge files use iterparse.", "follow": "Why is defusedxml recommended? (Standard parsers can be attacked with entity-expansion payloads in untrusted XML.)"},
    ],
    "quiz": [
        {"q": "JSON null becomes which Python value?", "options": ["0", "''", "None", "False"], "answer": 2, "why": "null maps to None."},
        {"q": "What type is a value read by csv.DictReader?", "options": ["Inferred", "str", "bytes", "float"], "answer": 1, "why": "CSV has no types."},
        {"q": "`json.loads(json.dumps({1: 'a'}))` returns?", "options": ["{1: 'a'}", "{'1': 'a'}", "['a']", "Error"], "answer": 1, "why": "JSON object keys are always strings."},
        {"q": "How should you test that `case.find('failure')` found something?", "options": ["if failure:", "if failure is not None:", "if len(failure):", "if failure.text:"], "answer": 1, "why": "Elements without children are falsy."},
        {"q": "Which loads YAML safely?", "options": ["yaml.load(f)", "yaml.safe_load(f)", "eval(f.read())", "json.load(f)"], "answer": 1, "why": "safe_load builds only plain types."},
    ],
    "cards": [
        {"front": "json.load vs json.loads", "back": "From a file vs from a string."},
        {"front": "CSV values after reading", "back": "Always strings; convert explicitly."},
        {"front": "Open a CSV file for writing", "back": "`open(p, 'w', newline='')`"},
        {"front": "ElementTree element found?", "back": "Compare with `is not None` (empty elements are falsy)."},
        {"front": "Loading YAML", "back": "`yaml.safe_load`; quote NO, on/off and leading-zero numbers."},
    ],
}


M_2_11 = {
    "id": "2.11",
    "title": "collections Module",
    "hours": 2,
    "summary": "Counter for frequencies, defaultdict for grouping, deque for rolling windows and queues, namedtuple for light records, and ChainMap for layered config.",
    "concepts": [
        {
            "title": "Counter, defaultdict and deque",
            "concept": "`Counter` counts hashable items and answers \"most common\" in one call; missing keys count as 0. `defaultdict(factory)` creates a default value the first time a missing key is read, which makes grouping a one-liner. `deque` is a double-ended queue with O(1) appends and pops at **both** ends; `deque(maxlen=n)` keeps only the last n items, a ready-made rolling window.",
            "why": "Top disconnect reasons, stations grouped per AP, and the last N RSSI samples for a moving average are the patterns from Module 1.9 and 1.7, written with the right container instead of by hand.",
            "syntax": "Counter(items).most_common(3)\ngroups = defaultdict(list); groups[key].append(x)\nwindow = deque(maxlen=10); window.append(x)\nq = deque(); q.append(x); q.popleft()",
            "code": """from collections import Counter, defaultdict, deque  ## Three specialised containers


def main() -> None:
    reasons = ["15", "3", "15", "8", "15", "3", "2"]  ## Deauth reason codes from a night of logs
    counts = Counter(reasons)  ## Counts every item in one pass
    print(counts.most_common(2), counts["15"], counts["99"])  ## Top two; a missing key counts as 0 (no KeyError)
    counts.update(["15", "8"])  ## Add more observations
    print(counts.most_common(1), sum(counts.values()))  ## Still reason 15; total observations
    log = [("aa:01", "ap-1"), ("aa:02", "ap-1"), ("aa:01", "ap-2")]  ## (station, AP) sightings
    by_ap = defaultdict(list)  ## Missing keys get a fresh empty list
    for mac, ap in log:  ## Group without setdefault
        by_ap[ap].append(mac)  ## The first access to a new AP creates its list
    print(dict(by_ap))  ## Convert to a plain dict for display
    window = deque(maxlen=3)  ## Keeps only the 3 newest items
    for rssi in [-52, -55, -61, -58, -66]:  ## A stream of RSSI samples
        window.append(rssi)  ## Older samples fall off the left end automatically
    print(list(window), round(sum(window) / len(window), 1))  ## Rolling average of the last 3
    q = deque(["sta1", "sta2", "sta3"])  ## A round-robin queue of stations to test
    q.rotate(-1)  ## Rotate left by one: sta2 is now first
    print(q.popleft(), list(q))  ## O(1) removal from the front, unlike list.pop(0)


if __name__ == "__main__":
    main()""",
            "under": "`Counter` and `defaultdict` are both dict subclasses. `defaultdict` overrides `__missing__`, which `dict.__getitem__` calls on a missing key: it builds `factory()`, stores it and returns it. `deque` is implemented as a doubly linked list of fixed-size blocks, which gives O(1) at both ends but O(n) indexing in the middle.",
            "gotchas": [
                {
                    "title": "Reading a defaultdict inserts keys",
                    "note": "Just looking up a missing key creates it, so 'is ap-9 in the table?' changes the answer. Use `in` or `.get()` to check.",
                    "wrong": """from collections import defaultdict
by_ap = defaultdict(list, {"ap-1": ["aa:01"]})
print(len(by_ap["ap-9"]), "ap-9" in by_ap)""",
                    "fixed": """from collections import defaultdict
by_ap = defaultdict(list, {"ap-1": ["aa:01"]})
print(len(by_ap.get("ap-9", [])), "ap-9" in by_ap)""",
                },
                {
                    "title": "Using a list as a queue",
                    "note": "`list.pop(0)` shifts every remaining item, which is O(n) per pop. For queues use deque.popleft().",
                    "wrong": """import time
q = list(range(100_000))
t0 = time.perf_counter()
while q:
    q.pop(0)
print("list drained:", time.perf_counter() - t0 > 0)""",
                    "fixed": """import time
from collections import deque
q = deque(range(100_000))
t0 = time.perf_counter()
while q:
    q.popleft()
print("deque drained:", time.perf_counter() - t0 > 0)""",
                },
            ],
            "best": "Reach for Counter whenever you write `counts[k] = counts.get(k, 0) + 1`, defaultdict for grouping, and deque for FIFO queues and fixed-size windows. Convert a defaultdict to a plain dict before returning it from a function, so callers can't create keys by accident.",
        },
        {
            "title": "namedtuple, ChainMap and OrderedDict",
            "concept": "`namedtuple` creates a lightweight, immutable record type whose fields can be read by name or by position. `ChainMap` searches several dicts in order without copying them, which models layered configuration (CLI over bench file over defaults). `OrderedDict` is mostly superseded by ordinary dicts, but still offers `move_to_end()` and order-sensitive equality, which is handy for small LRU caches.",
            "why": "A `Sample(t, rssi, mcs)` record reads far better than `sample[1]`. Layered config is how a single suite runs on any bench: defaults, overridden by the bench file, overridden by Jenkins parameters.",
            "syntax": "Sample = namedtuple(\"Sample\", [\"t\", \"rssi\", \"mcs\"])\ns = Sample(1.0, -54, 11); s.rssi; s._replace(mcs=9)\n\ncfg = ChainMap(cli, bench, defaults)   # first match wins\nod.move_to_end(key); od.popitem(last=False)",
            "code": """from collections import ChainMap, OrderedDict, namedtuple  ## Records, layered lookups, ordered dict

Sample = namedtuple("Sample", ["t", "rssi", "mcs"])  ## Creates a new class named Sample with three fields


def main() -> None:
    s = Sample(t=1.0, rssi=-54, mcs=11)  ## Construct like a function call, by keyword or position
    print(s, s.rssi, s[2])  ## Readable repr; access by name or by index
    t, rssi, mcs = s  ## It is still a tuple, so it unpacks
    print(s._replace(mcs=9), s._asdict())  ## Immutable: _replace returns a modified copy; _asdict gives a dict
    defaults = {"band": "5G", "width": 80, "channel": 36}  ## Framework defaults
    bench = {"channel": 149}  ## From the bench's config file
    cli = {"width": 160}  ## From the command line or Jenkins parameters
    cfg = ChainMap(cli, bench, defaults)  ## Lookups search cli, then bench, then defaults
    print(cfg["band"], cfg["width"], cfg["channel"], dict(cfg))  ## Each key comes from the first layer that has it
    cache = OrderedDict(a=1, b=2, c=3)  ## Insertion-ordered dict with extra methods
    cache.move_to_end("a")  ## Mark 'a' as most recently used
    cache.popitem(last=False)  ## Evict the least recently used item (now 'b')
    print(list(cache))  ## c, a


if __name__ == "__main__":
    main()""",
            "under": "`namedtuple` generates a tuple subclass with read-only properties for each field and no per-instance `__dict__`, so instances are as small as plain tuples. `ChainMap` holds a list of the underlying mappings (`.maps`) and searches them on every lookup; writes go only to the first mapping. Since Python 3.7 plain dicts preserve insertion order, so OrderedDict is needed only for its extra methods.",
            "gotchas": [
                {
                    "title": "namedtuple fields can't be assigned",
                    "note": "Records are immutable. Use _replace to get a changed copy, or a dataclass (Module 3.6) when you need mutation.",
                    "wrong": """from collections import namedtuple
Sample = namedtuple("Sample", "t rssi mcs")
s = Sample(1.0, -54, 11)
s.rssi = -60""",
                    "fixed": """from collections import namedtuple
Sample = namedtuple("Sample", "t rssi mcs")
s = Sample(1.0, -54, 11)
s = s._replace(rssi=-60)
print(s)""",
                }
            ],
            "best": "Use namedtuple for small, immutable records passed between functions and dataclasses for anything richer. Build runtime config as a ChainMap of layers and keep each layer as its own dict, so you can always report which layer a value came from.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Find the three most common channels in a scan list using Counter.",
            "solution": "Counter(...).most_common(3).",
            "solution_code": """from collections import Counter
seen = [36, 149, 36, 1, 6, 36, 149, 11, 1, 36]
print(Counter(seen).most_common(3))""",
        },
        {
            "level": "Medium",
            "prompt": "Detect a sustained RSSI drop: keep a 4-sample rolling window and print the sample index when the window average first falls below -70 dBm.",
            "solution": "deque(maxlen=4) and check only once the window is full.",
            "solution_code": """from collections import deque
rssi = [-55, -58, -62, -66, -70, -73, -75, -79]
window = deque(maxlen=4)
for i, r in enumerate(rssi):
    window.append(r)
    if len(window) == 4 and sum(window) / 4 < -70:
        print("sustained drop at sample", i, list(window))
        break""",
        },
        {
            "level": "Hard",
            "prompt": "Build layered config with ChainMap (defaults, bench, cli) and write a function that reports, for every key, its value and which layer it came from.",
            "solution": "Search cfg.maps in order and stop at the first layer that contains the key.",
            "solution_code": """from collections import ChainMap
layers = {"cli": {"width": 160}, "bench": {"channel": 149, "country": "IN"}, "defaults": {"band": "5G", "width": 80, "channel": 36}}
cfg = ChainMap(*layers.values())


def source_of(key):
    for name, layer in layers.items():
        if key in layer:
            return name


for key in sorted(cfg):
    print(f"{key:<8} = {cfg[key]!r:<6} from {source_of(key)}")""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "How would you count word or event frequencies?", "a": "`collections.Counter(items)`, then `.most_common(n)`. Missing keys count as 0, Counters can be added and subtracted, and `update()` adds more observations.", "follow": "What happens to counts that drop to zero or below after subtraction with -? (They are removed.)"},
        {"level": "Intermediate", "q": "defaultdict vs dict.setdefault?", "a": "Both create a default for missing keys. defaultdict does it automatically on every read through `[]`, which is concise but can insert keys by accident; setdefault is explicit per call and works on a normal dict.", "follow": "How does defaultdict work internally? (It implements __missing__.)"},
        {"level": "Intermediate", "q": "Why use deque instead of list for a queue?", "a": "deque has O(1) append and pop at both ends; list.pop(0) and insert(0) are O(n) because every element shifts. `deque(maxlen=n)` also gives a bounded buffer for free.", "follow": "Is deque thread-safe? (append and popleft are atomic in CPython; for producer/consumer patterns use queue.Queue.)"},
        {"level": "Advanced", "q": "namedtuple vs dataclass?", "a": "namedtuple is an immutable tuple subclass: small, hashable, unpackable and positional. A dataclass is a regular class: mutable by default (frozen optional), supports defaults, methods and type hints more naturally, and isn't a tuple. Use namedtuple for simple records, dataclasses for domain objects.", "follow": "And typing.NamedTuple? (The same as namedtuple, with class syntax and type hints.)"},
    ],
    "quiz": [
        {"q": "`Counter('aab')['z']` returns?", "options": ["KeyError", "0", "None", "''"], "answer": 1, "why": "Missing keys count as 0."},
        {"q": "What does `deque(maxlen=3)` do when a 4th item is appended?", "options": ["Raises", "Drops the oldest item", "Grows", "Drops the new item"], "answer": 1, "why": "It discards from the opposite end."},
        {"q": "`defaultdict(int)['x']` returns?", "options": ["KeyError", "0", "None", "'x'"], "answer": 1, "why": "int() is 0, and the key is inserted."},
        {"q": "ChainMap(a, b)['k'] uses which mapping first?", "options": ["a", "b", "The larger one", "Both merged"], "answer": 0, "why": "Mappings are searched in order."},
        {"q": "How do you change a field of a namedtuple?", "options": ["s.f = 1", "s._replace(f=1)", "s.set('f', 1)", "You can't get a changed copy"], "answer": 1, "why": "_replace returns a new instance."},
    ],
    "cards": [
        {"front": "Most common items", "back": "`Counter(items).most_common(n)`"},
        {"front": "Group without setdefault", "back": "`d = defaultdict(list); d[k].append(x)`"},
        {"front": "Rolling window", "back": "`deque(maxlen=n)`"},
        {"front": "O(1) pop from the front", "back": "`deque.popleft()`"},
        {"front": "Layered config", "back": "`ChainMap(cli, bench, defaults)`"},
    ],
}


M_2_12 = {
    "id": "2.12",
    "title": "itertools & functools",
    "hours": 1.5,
    "summary": "Generating test matrices with product, chaining, slicing and batching iterators, grouping sorted data, and functools tools: partial, lru_cache, reduce and singledispatch.",
    "concepts": [
        {
            "title": "itertools: building and slicing iterators",
            "concept": "`itertools` provides fast, lazy building blocks. `product` gives the Cartesian product (every combination), `chain` joins iterables, `cycle` repeats forever, `islice` slices any iterator, `pairwise` (3.10+) yields neighbouring pairs, `batched` (3.12+) yields fixed-size chunks, `accumulate` yields running totals and `groupby` groups **consecutive** items with the same key, so the input must be sorted by that key first.",
            "why": "A band × width × security test matrix is one `product` call. Gaps between timestamps come from `pairwise`. Sending commands to a device in chunks of 8 is `batched`.",
            "syntax": "product(bands, widths, security)   # every combination\nchain(a, b)  islice(it, n)  cycle(xs)\npairwise(ts)        # (t0, t1), (t1, t2), ...\nbatched(xs, 3)      # (x0, x1, x2), (x3, x4, x5), ...\ngroupby(sorted(xs, key=k), key=k)",
            "code": """from itertools import accumulate, batched, chain, cycle, groupby, islice, pairwise, product  ## Lazy iterator tools


def main() -> None:
    matrix = list(product(["5G", "6G"], [80, 160], ["WPA3", "OWE"]))  ## 2 x 2 x 2 = every combination
    print(len(matrix), matrix[:3])  ## 8 test cases; the rightmost input varies fastest
    print(list(chain([36, 40], [149, 153])))  ## Join two channel lists without building an intermediate list
    print(list(islice(cycle(["ap-1", "ap-2", "ap-3"]), 7)))  ## Round-robin forever, sliced to the first 7
    ts = [0.0, 1.0, 2.0, 5.5, 6.5]  ## Sample timestamps in seconds
    gaps = [round(b - a, 1) for a, b in pairwise(ts)]  ## Each timestamp paired with the next
    print(gaps, max(gaps))  ## A 3.5 s gap: samples were lost
    print(list(batched(range(1, 8), 3)))  ## Chunks of 3; the last one may be shorter (3.12+)
    print(list(accumulate([120, 340, 90])))  ## Running totals, e.g. bytes transferred so far
    events = [("ap-1", "assoc"), ("ap-1", "roam"), ("ap-2", "assoc"), ("ap-1", "deauth")]  ## Unsorted events
    for ap, group in groupby(sorted(events), key=lambda e: e[0]):  ## Sort by the key first, then group
        print(ap, [e[1] for e in group])  ## Each group is an iterator over that AP's events


if __name__ == "__main__":
    main()""",
            "under": "Every itertools function returns an iterator that computes values on demand, so `product` of large inputs doesn't allocate the full matrix until you ask for it with `list()`. `groupby` only compares each item with the previous one; when the key changes it starts a new group. The group iterators share the underlying iterator, so consume each group before moving on to the next.",
            "gotchas": [
                {
                    "title": "groupby on unsorted data",
                    "note": "groupby groups consecutive equal keys only, so ap-1 appears twice. Sort by the same key first.",
                    "wrong": """from itertools import groupby
events = [("ap-1", "assoc"), ("ap-2", "assoc"), ("ap-1", "roam")]
print([(k, len(list(g))) for k, g in groupby(events, key=lambda e: e[0])])""",
                    "fixed": """from itertools import groupby
events = [("ap-1", "assoc"), ("ap-2", "assoc"), ("ap-1", "roam")]
def key(e):
    return e[0]
print([(k, len(list(g))) for k, g in groupby(sorted(events, key=key), key=key)])""",
                }
            ],
            "best": "Generate test matrices with `product` and filter out invalid combinations with a comprehension. Use `islice` to take a bounded number of items from any iterator, and always sort before `groupby` (or use a defaultdict when order doesn't matter).",
        },
        {
            "title": "functools: partial, lru_cache, reduce, singledispatch",
            "concept": "`partial(func, ...)` pre-fills some arguments and returns a new callable. `@lru_cache` (or `@cache`) memoises a function: repeated calls with the same hashable arguments return the stored result. `reduce` folds a sequence into one value. `@singledispatch` picks an implementation based on the type of the first argument. These use **decorator** syntax (`@name` above a def), which Module 3.8 explains in full.",
            "why": "`partial(ping, count=1, timeout=0.2)` gives a quick-ping helper; caching a slow DUT capability query saves seconds on every test; singledispatch formats channels, SSIDs and other values without an if/elif ladder.",
            "syntax": "quick = partial(ping, count=1)\n\n@lru_cache(maxsize=128)\ndef slow(model): ...\nslow.cache_info(); slow.cache_clear()\n\nreduce(lambda acc, x: acc | x, flags, 0)\n\n@singledispatch\ndef describe(v): ...\n@describe.register\ndef _(v: int): ...",
            "code": """import time  ## sleep() to make the cached function noticeably slow
from functools import lru_cache, partial, reduce, singledispatch  ## Higher-order function tools


def ping(host: str, count: int = 4, timeout: float = 1.0) -> str:  ## Builds a ping command line
    return f"ping -c {count} -W {timeout} {host}"  ## Returned, not run, to keep the demo self-contained


@lru_cache(maxsize=128)  ## preview: decorators are taught in Module 3.8; this wraps the function with a cache
def dut_capabilities(model: str) -> tuple[str, ...]:  ## Pretend this asks the DUT over SSH (slow)
    time.sleep(0.05)  ## Simulated network delay, paid only on a cache miss
    return ("HT", "VHT", "HE", "EHT") if model.endswith("7") else ("HT", "VHT", "HE")  ## Immutable result, safe to share


@singledispatch  ## The generic function: used when no type-specific version matches
def describe(value) -> str:  ## Fallback implementation
    return f"unknown: {value!r}"  ## Shown for floats here


@describe.register  ## Register a version chosen by the type hint of the first argument
def _(value: int) -> str:  ## Used for ints
    return f"channel {value}"  ## Ints are channels in this toy example


@describe.register  ## Another registration
def _(value: str) -> str:  ## Used for strings
    return f"ssid {value!r}"  ## Strings are SSIDs


def main() -> None:
    quick_ping = partial(ping, count=1, timeout=0.2)  ## A new callable with count and timeout pre-filled
    print(quick_ping("ap-1"))  ## Only the host is still needed
    for _ in range(3):  ## Three identical queries...
        dut_capabilities("wifi7")  ## ...only the first one is slow
    dut_capabilities("wifi6")  ## A different argument is a new cache entry
    print(dut_capabilities.cache_info())  ## 2 hits, 2 misses, 2 entries stored
    print(reduce(lambda acc, x: acc | x, [0b0001, 0b0100, 0b1000], 0))  ## Fold capability bits together with OR: 13
    print(describe(149), describe("lab-wpa3"), describe(3.5))  ## Dispatch on the argument's type


if __name__ == "__main__":
    main()""",
            "under": "`lru_cache` stores results in a dict keyed by the call's arguments, so every argument must be hashable; when the cache is full, the least recently used entry is evicted. The cache lives as long as the function, so cached data can go stale (call `cache_clear()` between tests if the DUT changes). `partial` objects keep `func`, `args` and `keywords` attributes, which makes them easier to inspect and debug than lambdas.",
            "gotchas": [
                {
                    "title": "lru_cache with unhashable arguments",
                    "note": "Lists can't be dictionary keys, so the cached function fails. Pass a tuple instead.",
                    "wrong": """from functools import lru_cache

@lru_cache
def total(samples):
    return sum(samples)

print(total([910.2, 905.7]))""",
                    "fixed": """from functools import lru_cache

@lru_cache
def total(samples):
    return sum(samples)

print(total((910.2, 905.7)), total.cache_info().misses)""",
                }
            ],
            "best": "Cache only pure functions whose results can't change during a run, or clear the cache when the device under test changes. Prefer `partial` over lambda for pre-filling arguments. Use `reduce` only when a built-in such as `sum`, `max`, `any` or `math.prod` doesn't already do the job.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Build every (channel, width) combination for channels [36, 149] and widths [80, 160] with product and print them.",
            "solution": "product of the two lists.",
            "solution_code": """from itertools import product
for ch, w in product([36, 149], [80, 160]):
    print(f"ch{ch}/{w}MHz")""",
        },
        {
            "level": "Medium",
            "prompt": "Split a list of 10 AP config commands into batches of 4 (the CLI accepts at most 4 lines per push) and print each batch.",
            "solution": "itertools.batched in 3.12+, or islice in a loop on older versions.",
            "solution_code": """from itertools import batched
commands = [f"set radio{i % 2} txpower {14 + i}" for i in range(10)]
for n, batch in enumerate(batched(commands, 4), start=1):
    print(n, list(batch))""",
        },
        {
            "level": "Hard",
            "prompt": "Find the longest stall in a throughput trace: report the start time and length of the longest run of consecutive zero samples, using groupby.",
            "solution": "groupby on 'is zero' gives runs of zero and non-zero samples; track the longest zero run and where it started.",
            "solution_code": """from itertools import groupby
trace = [(0, 910), (1, 905), (2, 0), (3, 0), (4, 899), (5, 0), (6, 0), (7, 0), (8, 912)]
best_len, best_start = 0, None
for is_zero, run in groupby(trace, key=lambda s: s[1] == 0):
    run = list(run)
    if is_zero and len(run) > best_len:
        best_len, best_start = len(run), run[0][0]
print(f"longest stall: {best_len} s starting at t={best_start}")""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "How do you generate every combination of several parameter lists?", "a": "`itertools.product(a, b, c)`, which yields tuples lazily with the last input varying fastest. Filter invalid combinations with a comprehension; `pytest.mark.parametrize` (Module 5.5) can take the result directly.", "follow": "How many cases does product(range(3), repeat=4) give? (3**4 = 81.)"},
        {"level": "Intermediate", "q": "What is the classic groupby mistake?", "a": "Using it on unsorted data. groupby only groups consecutive items with equal keys, so the same key can appear in several groups. Sort by the same key first, or use a defaultdict when you don't need ordering.", "follow": "Why must you consume each group before advancing? (The groups share one underlying iterator.)"},
        {"level": "Intermediate", "q": "What does functools.lru_cache do, and what are the risks?", "a": "It memoises results keyed by the arguments, so repeated calls skip the work. Arguments must be hashable, the cache holds references (memory), and cached results can go stale if the underlying data changes; clear it with cache_clear().", "follow": "What's the difference between cache and lru_cache? (cache is unbounded; lru_cache evicts the least recently used entry beyond maxsize.)"},
        {"level": "Advanced", "q": "partial vs lambda?", "a": "Both pre-fill arguments. partial binds values immediately (no late-binding surprises), exposes func, args and keywords for inspection, and pickles more easily, which matters for multiprocessing. A lambda is more flexible for reordering or transforming arguments.", "follow": "When would partial fail to pickle? (When the wrapped function itself can't be pickled, e.g. a lambda or a nested function.)"},
    ],
    "quiz": [
        {"q": "`len(list(product([1, 2], [3, 4, 5])))` is?", "options": ["5", "6", "2", "3"], "answer": 1, "why": "2 × 3 combinations."},
        {"q": "`list(pairwise([1, 2, 3]))` gives?", "options": ["[(1, 2), (2, 3)]", "[(1, 2), (3,)]", "[1, 2, 3]", "[(1, 3)]"], "answer": 0, "why": "Neighbouring pairs, overlapping."},
        {"q": "groupby requires its input to be...", "options": ["A list", "Sorted by the grouping key", "Unique", "Numeric"], "answer": 1, "why": "It groups consecutive equal keys."},
        {"q": "What does `partial(f, x=1)` return?", "options": ["f(1)", "A new callable", "None", "A tuple"], "answer": 1, "why": "A callable with x pre-filled."},
        {"q": "Calling an @lru_cache function with a list argument...", "options": ["Works", "Raises TypeError", "Returns None", "Caches by id"], "answer": 1, "why": "Cache keys must be hashable."},
    ],
    "cards": [
        {"front": "Every combination of lists", "back": "`itertools.product(a, b, c)`"},
        {"front": "Neighbouring pairs", "back": "`itertools.pairwise(xs)` (3.10+)"},
        {"front": "Fixed-size chunks", "back": "`itertools.batched(xs, n)` (3.12+)"},
        {"front": "groupby rule", "back": "Sort by the key first."},
        {"front": "Pre-fill arguments", "back": "`functools.partial(func, kw=value)`"},
        {"front": "Memoise a pure function", "back": "`@functools.lru_cache(maxsize=...)`"},
    ],
}
