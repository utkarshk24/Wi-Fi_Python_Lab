"""Phase 1 content: modules 1.7-1.9."""

M_1_7 = {
    "id": "1.7",
    "title": "Lists & Slicing",
    "hours": 2,
    "summary": "The mutable, ordered workhorse: adding and removing items, sorting, unpacking, slicing windows and computing percentiles.",
    "concepts": [
        {
            "title": "List operations",
            "concept": "A `list` is a **mutable, ordered** sequence that can hold any objects. `append` adds one item, `extend` adds every item from an iterable, `insert` places an item at a position, `pop` removes by index (last by default) and `remove` deletes the first matching value. `list.sort()` sorts **in place and returns None**; `sorted()` returns a new list.",
            "why": "Throughput samples, station lists and failure collections are lists. Knowing which operations are cheap (append, pop from the end) and which are slow (pop(0), insert(0), `in`) matters once a soak test produces millions of samples.",
            "syntax": "xs.append(x)        # add one item at the end, O(1)\nxs.extend(iterable) # add many items\nxs.insert(i, x)     # O(n)\nxs.pop()            # remove and return last, O(1)\nxs.pop(0)           # O(n)\nxs.remove(value)    # first match, O(n)\nxs.sort(key=..., reverse=...)  # in place, returns None\nsorted(xs)          # new list",
            "code": """def main() -> None:
    samples = [910.2, 905.7, 899.1]  ## Throughput samples in Mbps
    samples.append(912.4)  ## Adds one item at the end
    samples.extend([887.0, 901.3])  ## Adds each item of the iterable
    samples.insert(0, 0.0)  ## Inserts at index 0, shifting everything right (warm-up sample)
    print(samples, len(samples))  ## 7 items now
    first = samples.pop(0)  ## Removes and returns the item at index 0
    print(first, samples)  ## The warm-up sample is gone
    samples.remove(887.0)  ## Removes the first item equal to 887.0 (ValueError if absent)
    print(samples)  ## 5 items remain
    print(sorted(samples), samples)  ## sorted() returns a NEW list; the original order is unchanged
    samples.sort(reverse=True)  ## Sorts in place, largest first, and returns None
    print(samples)  ## Now sorted descending
    print(samples.index(905.7), 999.0 in samples)  ## Position of a value, and a membership test (linear scan)
    best, *rest, worst = samples  ## Star-unpacking: first item, everything in the middle, last item
    print(best, rest, worst)  ## rest is always a list


if __name__ == "__main__":
    main()""",
            "under": "A CPython list is a dynamic array of pointers to objects. It over-allocates capacity, so `append` is amortised O(1). Inserting or removing at the front shifts every pointer, which is O(n). `in` and `index()` compare items one by one. Python's sort is **Timsort**: stable (equal keys keep their order) and fast on partly ordered data such as samples that are already nearly sorted.",
            "gotchas": [
                {
                    "title": "append() vs extend()",
                    "note": "`append` adds its argument as one item, so appending a list nests it.",
                    "wrong": """stas = ["sta1"]
stas.append(["sta2", "sta3"])
print(stas, len(stas))""",
                    "fixed": """stas = ["sta1"]
stas.extend(["sta2", "sta3"])
print(stas, len(stas))""",
                },
                {
                    "title": "Assigning the result of sort()",
                    "note": "`list.sort()` returns None, so this throws your data away.",
                    "wrong": """samples = [3, 1, 2]
samples = samples.sort()
print(samples)""",
                    "fixed": """samples = [3, 1, 2]
samples.sort()
print(samples, sorted([9, 7, 8]))""",
                },
            ],
            "best": "Use `sorted()` when you need to keep the original order, and `.sort()` when you don't. Append at the end and pop from the end; if you need fast removal at both ends, use `collections.deque` (Module 2.11). Use star-unpacking instead of manual index arithmetic.",
        },
        {
            "title": "Slicing, windows and percentiles",
            "concept": "Slicing `xs[start:stop:step]` returns a **new list** (a shallow copy) of the selected items. Negative indices count from the end (`xs[-1]` is the last item). Omitted parts default to the whole range, so `xs[:]` copies the whole list and `xs[::-1]` reverses it. Slice **assignment** (`xs[2:4] = [...]`) replaces a range in place.",
            "why": "Rolling windows over throughput samples, dropping warm-up samples, taking the last N RSSI readings and computing median and P5 values are slicing and sorting problems that come up in every performance test.",
            "syntax": "xs[0], xs[-1]     # first, last\nxs[2:5]           # items 2, 3, 4\nxs[:3], xs[-3:]   # first three, last three\nxs[::2]           # every second item\nxs[::-1]          # reversed copy\nxs[a:b] = []      # delete a range in place",
            "code": """def percentile(values: list[float], pct: float) -> float:  ## Linear-interpolation percentile (the same method as numpy's default)
    ordered = sorted(values)  ## Work on a sorted copy; the caller's list is untouched
    k = (len(ordered) - 1) * pct / 100  ## Fractional position of the percentile in the sorted list
    lower = int(k)  ## Index just below that position
    upper = min(lower + 1, len(ordered) - 1)  ## Index just above it, clamped to the last element
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (k - lower)  ## Interpolate between the two neighbours


def main() -> None:
    mbps = [880, 902, 915, 897, 640, 910, 905, 899, 912, 908]  ## 10 one-second samples with one dip (640)
    print(mbps[0], mbps[-1])  ## First and last sample
    print(mbps[2:5], mbps[:3], mbps[-3:])  ## A middle range, the first three and the last three
    print(mbps[::2], mbps[::-1])  ## Every second sample, and a reversed copy
    window = mbps[-5:]  ## The last five samples as a new list
    print(sum(window) / len(window))  ## Mean of that window
    print(f"median={percentile(mbps, 50):.1f} p5={percentile(mbps, 5):.1f}")  ## The median ignores the dip; P5 exposes it
    mbps[4:5] = []  ## Slice assignment: delete the dip in place
    print(mbps, len(mbps))  ## One sample shorter


if __name__ == "__main__":
    main()""",
            "under": "A slice creates a new list object and copies the **references** to the selected items; the items themselves are not copied (that matters for lists of dicts, Module 1.10). Out-of-range slice bounds are clamped, so `xs[5:100]` never raises, unlike `xs[100]`. `xs[a:b] = other` can change the list's length.",
            "gotchas": [
                {
                    "title": "Index errors vs forgiving slices",
                    "note": "Indexing past the end raises IndexError, but slicing past the end silently returns fewer items. Check lengths when you expect a full window.",
                    "wrong": """samples = [900, 905]
last_five = samples[-5:]
print(sum(last_five) / 5)""",
                    "fixed": """samples = [900, 905]
last_five = samples[-5:]
if len(last_five) < 5:
    print(f"only {len(last_five)} samples, need 5")
else:
    print(sum(last_five) / 5)""",
                },
            ],
            "best": "Name your windows (`warmup = 3`, `steady = samples[warmup:]`) instead of using bare numbers. Report median and low percentiles alongside the mean, because a single stall barely moves the mean but is exactly what users feel. For heavy numeric work use the `statistics` module or numpy.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Drop the first 3 warm-up samples and the last 2 cool-down samples from a list of 12 samples using one slice.",
            "solution": "`samples[3:-2]` keeps the middle.",
            "solution_code": """samples = list(range(100, 112))
steady = samples[3:-2]
print(steady, len(steady))""",
        },
        {
            "level": "Medium",
            "prompt": "Compute a 3-sample moving average over a list of RSSI readings.",
            "solution": "Slide a window with slicing from each start index.",
            "solution_code": """rssi = [-52, -55, -61, -58, -66, -70]
averages = []
for i in range(len(rssi) - 2):
    window = rssi[i:i + 3]
    averages.append(round(sum(window) / 3, 1))
print(averages)""",
        },
        {
            "level": "Hard",
            "prompt": "Sort scan results `(bssid, band, rssi)` by band ascending and then by RSSI strongest first, without writing your own sort.",
            "solution": "Use a key that returns a tuple; negate RSSI so stronger (less negative) values come first.",
            "solution_code": """scan = [("ap-3", "6G", -61), ("ap-1", "5G", -48), ("ap-2", "5G", -70), ("ap-4", "6G", -52)]
scan.sort(key=lambda item: (item[1], -item[2]))
for row in scan:
    print(row)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What is the difference between append() and extend()?", "a": "`append(x)` adds x as a single item, so appending a list nests it. `extend(iterable)` adds each element of the iterable. `xs += other` behaves like extend.", "follow": "What does `xs.append(xs)` create? (A self-referencing list, printed as `[...]`.)"},
        {"level": "Beginner", "q": "sort() vs sorted()?", "a": "`list.sort()` sorts the list in place and returns None. `sorted(iterable)` works on any iterable and returns a new list. Both accept `key` and `reverse`, and both are stable.", "follow": "What does 'stable' mean, and why is it useful? (Equal keys keep their order, so you can sort by several keys in passes.)"},
        {"level": "Intermediate", "q": "What is the time complexity of common list operations?", "a": "Index access and append: O(1) (append is amortised). pop() from the end: O(1). insert(0) and pop(0): O(n). `in`, index() and remove(): O(n). Sorting: O(n log n).", "follow": "What would you use for a FIFO queue? (`collections.deque`, which has O(1) operations at both ends.)"},
        {"level": "Intermediate", "q": "Does slicing copy the list?", "a": "It creates a new list, but a **shallow** one: the new list holds references to the same item objects. Mutating a nested object through the slice affects the original.", "follow": "How do you copy a list of dicts safely? (`copy.deepcopy`, Module 1.10.)"},
        {"level": "Advanced", "q": "How does Python's list grow, and why is append amortised O(1)?", "a": "The list over-allocates its pointer array, growing by roughly 1/8 plus a constant each time it fills. Most appends just write into spare capacity; the occasional resize copies everything, but spread over many appends the cost per append is constant.", "follow": "How could you pre-size a list? (`[None] * n`, though usually unnecessary.)"},
    ],
    "quiz": [
        {"q": "What is `[1, 2, 3, 4, 5][1:4]`?", "options": ["[1, 2, 3, 4]", "[2, 3, 4]", "[2, 3, 4, 5]", "[1, 2, 3]"], "answer": 1, "why": "Start index 1 included, stop index 4 excluded."},
        {"q": "What does `xs.sort()` return?", "options": ["The sorted list", "None", "A copy", "True"], "answer": 1, "why": "It sorts in place."},
        {"q": "What is `[1, 2, 3][::-1]`?", "options": ["[3, 2, 1]", "[1, 2, 3]", "[3]", "Error"], "answer": 0, "why": "Step -1 walks backwards."},
        {"q": "Which operation is O(n)?", "options": ["xs.append(x)", "xs.pop()", "xs.pop(0)", "xs[-1]"], "answer": 2, "why": "Removing the first item shifts every other pointer."},
        {"q": "After `a, *b, c = [1, 2, 3, 4]`, what is b?", "options": ["2", "[2, 3]", "(2, 3)", "[2]"], "answer": 1, "why": "The starred name always gets a list."},
    ],
    "cards": [
        {"front": "append vs extend", "back": "One item (possibly a nested list) vs every item of an iterable."},
        {"front": "list.sort() return value", "back": "None (it sorts in place)."},
        {"front": "Reverse a list copy", "back": "`xs[::-1]` or `list(reversed(xs))`"},
        {"front": "pop(0) complexity", "back": "O(n). Use collections.deque for FIFO."},
        {"front": "Slicing past the end", "back": "No error; the slice is simply shorter."},
    ],
}


M_1_8 = {
    "id": "1.8",
    "title": "Tuples & Sets",
    "hours": 1.5,
    "summary": "Immutable records with unpacking, tuples as composite keys, and set algebra for comparing channel lists and scans.",
    "concepts": [
        {
            "title": "Tuples: immutable records",
            "concept": "A `tuple` is an **immutable, ordered** sequence. It is the natural type for a fixed record such as `(mac, channel, rssi)`. Tuples support **unpacking** into separate names and, when all their items are hashable, can be used as dict keys and set members. The comma makes the tuple, not the parentheses, so a one-item tuple needs a trailing comma: `(36,)`.",
            "why": "A test matrix entry `(band, width)` is a perfect composite dict key. Functions that return several values return a tuple, and unpacking it keeps call sites readable.",
            "syntax": "t = (\"aa:01\", 149, -54)\nmac, ch, rssi = t      # unpacking\nsingle = (36,)         # one-item tuple\nresults[(\"6G\", 320)] = 2840.0  # tuple as a dict key\na, b = b, a            # swap via tuple packing",
            "code": """def main() -> None:
    link = ("aa:bb:cc:00:00:01", 149, -54)  ## A fixed record: (MAC, channel, RSSI)
    mac, channel, rssi = link  ## Unpacking: the number of names must match the number of items
    print(mac, channel, rssi)  ## Three separate values
    single = (36,)  ## The trailing comma makes this a tuple
    not_a_tuple = (36)  ## Without a comma these are just grouping parentheses
    print(type(single).__name__, type(not_a_tuple).__name__)  ## tuple int
    try:  ## preview: try/except is taught in Module 2.5
        link[1] = 36  ## Tuples are immutable, so item assignment fails
    except TypeError as err:  ## Catch the error to show its message
        print("TypeError:", err)  ## 'tuple' object does not support item assignment
    results = {("5G", 80): 912.4, ("6G", 320): 2840.0}  ## Tuples as composite keys: (band, width) -> Mbps
    print(results[("6G", 320)])  ## Look up one combination
    a, b = 1, 2  ## Packing on the right, unpacking on the left
    a, b = b, a  ## Swap without a temporary variable
    print(a, b)  ## 2 1
    print(link.count(149), link.index(-54))  ## Tuples have only two methods: count and index


if __name__ == "__main__":
    main()""",
            "under": "A tuple stores a fixed-size array of references, so it is slightly smaller than an equivalent list and cheaper to create. A tuple's hash is computed from its items' hashes, which is why a tuple that contains a list is unhashable. CPython reuses the empty tuple and keeps free lists of small tuples to make creating them fast.",
            "gotchas": [
                {
                    "title": "A stray comma creates a tuple",
                    "note": "A trailing comma at the end of an assignment silently turns the value into a one-item tuple. Comparisons against an int then fail.",
                    "wrong": """channel = 36,
print(channel == 36, channel)""",
                    "fixed": """channel = 36
print(channel == 36, channel)""",
                },
                {
                    "title": "Immutable tuple, mutable contents",
                    "note": "The tuple can't change which objects it holds, but a list inside it can still be mutated, and such a tuple is unhashable.",
                    "wrong": """config = ("ap-1", ["ssid-a"])
config[1].append("ssid-b")
print(config)
print({config: "x"})""",
                    "fixed": """config = ("ap-1", ("ssid-a", "ssid-b"))
print(config, {config: "ok"}[config])""",
                },
            ],
            "best": "Use tuples for fixed-shape records and composite keys; use lists for collections that grow. When a record has more than three fields, give the fields names with `namedtuple` (Module 2.11) or a dataclass (Module 3.6).",
        },
        {
            "title": "Sets: membership and set algebra",
            "concept": "A `set` is an **unordered** collection of **unique, hashable** items with average O(1) membership tests. The operators `&` (intersection), `|` (union), `-` (difference) and `^` (symmetric difference) compare whole collections in one expression. `frozenset` is the immutable, hashable version. `{}` is an empty **dict**; an empty set is `set()`.",
            "why": "Which channels do the AP and STA both support? Which BSSIDs disappeared between two scans? Which tests failed in both runs? Each is one line of set algebra instead of a nested loop.",
            "syntax": "a & b   # in both\na | b   # in either\na - b   # in a but not b\na ^ b   # in exactly one\nx in s  # average O(1)\na <= b  # a is a subset of b",
            "code": """def main() -> None:
    ap_channels = {36, 40, 44, 48, 149, 153, 157, 161}  ## Channels the AP supports
    sta_channels = {36, 40, 44, 48, 52, 56}  ## Channels the STA supports
    print(sorted(ap_channels & sta_channels))  ## Common channels; sorted() for stable, readable output
    print(sorted(ap_channels - sta_channels))  ## AP-only channels
    print(sorted(ap_channels | sta_channels))  ## Every channel either side supports
    print(sorted(ap_channels ^ sta_channels))  ## Channels supported by exactly one side
    scan1 = {"aa:01", "aa:02", "aa:03"}  ## BSSIDs seen in the first scan
    scan2 = {"aa:02", "aa:03", "aa:04"}  ## BSSIDs seen in the second scan
    print("disappeared:", scan1 - scan2, "new:", scan2 - scan1)  ## Differences in both directions
    print(36 in ap_channels, {36, 40} <= ap_channels)  ## Membership test and subset test
    empty = set()  ## The only way to write an empty set
    print(type({}).__name__, type(empty).__name__)  ## {} is a dict, set() is a set
    frozen = frozenset({"WPA3", "SAE"})  ## Immutable and hashable, so it can be a dict key
    print({frozen: "ok"}[frozenset({"SAE", "WPA3"})])  ## Order doesn't matter for set equality or hashing


if __name__ == "__main__":
    main()""",
            "under": "A set is a hash table without values. Looking up `x in s` hashes x, jumps to a slot and compares only the few items in that slot, so it takes about the same time whether the set holds 10 or 10 million items. The trade-off is memory, plus the rule that items must be hashable and must not change while they are in the set. Iteration order depends on hash values and, for strings, varies between runs.",
            "gotchas": [
                {
                    "title": "Relying on set order",
                    "note": "Set iteration order is not insertion order, and for strings it can change between runs. Sort before printing or comparing output.",
                    "wrong": """failed = {"roam_11r", "throughput_6g", "assoc_wpa3"}
print(list(failed))""",
                    "fixed": """failed = {"roam_11r", "throughput_6g", "assoc_wpa3"}
print(sorted(failed))""",
                },
                {
                    "title": "Putting unhashable items in a set",
                    "note": "Lists and dicts can't be set members. Convert to tuples or frozensets first.",
                    "wrong": """pairs = {[36, 80], [149, 160]}""",
                    "fixed": """pairs = {(36, 80), (149, 160)}
print((36, 80) in pairs)""",
                },
            ],
            "best": "Convert to a set when you need many membership tests or a comparison between collections, then convert back with `sorted()` for output. To remove duplicates while keeping order, use `list(dict.fromkeys(items))` instead of `list(set(items))`.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Find the tests that failed in both of two nightly runs.",
            "solution": "Intersection of the two failure sets.",
            "solution_code": """night1 = {"roam_11r", "throughput_6g", "assoc_wpa3", "dfs_cac"}
night2 = {"throughput_6g", "dfs_cac", "mlo_link_switch"}
print(sorted(night1 & night2))""",
        },
        {
            "level": "Medium",
            "prompt": "Remove duplicate BSSIDs from a scan list while keeping the order in which they were first seen.",
            "solution": "dict keys keep insertion order and are unique.",
            "solution_code": """seen = ["aa:02", "aa:01", "aa:02", "aa:03", "aa:01"]
print(list(dict.fromkeys(seen)))""",
        },
        {
            "level": "Hard",
            "prompt": "Classify tests between two runs as fixed (failed then passed), new failures (passed then failed) and still failing.",
            "solution": "Three set differences and one intersection on the failure sets.",
            "solution_code": """before = {"roam_11r", "dfs_cac", "assoc_wpa3"}
after = {"dfs_cac", "mlo_link_switch"}
print("fixed:", sorted(before - after))
print("new failures:", sorted(after - before))
print("still failing:", sorted(before & after))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What is the difference between a list and a tuple?", "a": "Lists are mutable and meant for collections that change; tuples are immutable and meant for fixed records. Tuples of hashable items are hashable (usable as dict keys or set members), slightly smaller and faster to create.", "follow": "Is a tuple containing a list hashable? (No.)"},
        {"level": "Beginner", "q": "How do you create an empty set?", "a": "`set()`. `{}` creates an empty dict.", "follow": "And a one-item tuple? (`(x,)`, because the comma makes the tuple.)"},
        {"level": "Intermediate", "q": "Why is `x in some_set` fast but `x in some_list` slow?", "a": "A set is a hash table, so membership is average O(1): hash, jump to a slot, compare a few items. A list must compare items one by one, which is O(n).", "follow": "What is the worst case for a set lookup? (O(n) with many hash collisions, which is rare in practice.)"},
        {"level": "Intermediate", "q": "How do you deduplicate a list but keep the original order?", "a": "`list(dict.fromkeys(items))`. Dict keys are unique and keep insertion order (guaranteed since 3.7). `list(set(items))` loses the order.", "follow": "What if the items are unhashable? (Track seen keys yourself, e.g. using a tuple of the fields.)"},
        {"level": "Advanced", "q": "What is a frozenset, and when do you need one?", "a": "An immutable, hashable set. Use it when a set must itself be a dict key or a member of another set, such as caching results per set of enabled features.", "follow": "Is frozenset({1, 2}) == {1, 2}? (Yes; equality compares contents.)"},
    ],
    "quiz": [
        {"q": "What is `type((5))`?", "options": ["tuple", "int", "list", "set"], "answer": 1, "why": "Without a comma the parentheses only group."},
        {"q": "What is `{1, 2, 3} - {2, 3, 4}`?", "options": ["{1}", "{4}", "{1, 4}", "{2, 3}"], "answer": 0, "why": "Items in the first set but not the second."},
        {"q": "Which can be a dict key?", "options": ["[1, 2]", "{1, 2}", "(1, 2)", "{'a': 1}"], "answer": 2, "why": "Only the tuple of ints is hashable."},
        {"q": "What does `type({})` return?", "options": ["set", "dict", "frozenset", "tuple"], "answer": 1, "why": "Empty braces make a dict."},
        {"q": "What is `{1, 2} <= {1, 2, 3}`?", "options": ["True", "False", "{1, 2}", "TypeError"], "answer": 0, "why": "<= is the subset test."},
    ],
    "cards": [
        {"front": "One-item tuple", "back": "`(x,)`, because the comma makes the tuple."},
        {"front": "Empty set", "back": "`set()` (`{}` is a dict)."},
        {"front": "Set operators", "back": "& intersection, | union, - difference, ^ symmetric difference"},
        {"front": "Ordered dedupe", "back": "`list(dict.fromkeys(items))`"},
        {"front": "Hashable set", "back": "`frozenset`"},
    ],
}


M_1_9 = {
    "id": "1.9",
    "title": "Dictionaries",
    "hours": 2,
    "summary": "Key-value lookups, safe access with get(), updating and merging, grouping with setdefault, nested configs and how hashing works.",
    "concepts": [
        {
            "title": "Dictionary basics",
            "concept": "A `dict` maps **unique, hashable keys** to values with average O(1) lookups. `d[key]` raises `KeyError` for a missing key; `d.get(key, default)` returns a default instead. Dicts **keep insertion order** (guaranteed since Python 3.7). `update()` and the merge operator `|` (3.9+) combine dicts, with later values winning.",
            "why": "Station tables keyed by MAC, results keyed by test name, configs keyed by setting: dicts are the core data structure of every test framework.",
            "syntax": "d[key]                 # KeyError if missing\nd.get(key, default)    # default if missing\nd[key] = value         # insert or overwrite\nd.pop(key)             # remove and return\nfor k, v in d.items(): ...\nmerged = base | override  # 3.9+",
            "code": """def main() -> None:
    sta = {"mac": "aa:bb:cc:00:00:01", "rssi": -54, "band": "5G"}  ## A station record: keys map to values
    print(sta["rssi"], sta.get("nss"), sta.get("nss", 1))  ## [] for keys that must exist; get() returns None or your default
    sta["nss"] = 2  ## Assigning to a new key inserts it
    sta.update(rssi=-57, mcs=9)  ## Overwrites rssi and adds mcs in one call
    print(sta)  ## Keys stay in insertion order
    removed = sta.pop("mcs")  ## Removes the key and returns its value
    print(removed, "mcs" in sta)  ## `in` tests KEYS, not values
    for key, value in sta.items():  ## items() yields (key, value) pairs
        print(f"{key:>5}: {value}")  ## Aligned key/value listing
    defaults = {"band": "5G", "width": 80, "channel": 36}  ## Baseline settings
    override = {"channel": 149, "width": 160}  ## Per-test changes
    print(defaults | override)  ## A new merged dict; values from the right side win
    try:  ## preview: try/except is taught in Module 2.5
        sta["snr"]  ## Missing key with [] ...
    except KeyError as err:  ## ... raises KeyError
        print("KeyError:", err)  ## The message is the missing key


if __name__ == "__main__":
    main()""",
            "under": "A dict is a hash table. CPython keeps a compact array of entries in insertion order plus a sparse index table of hash slots, which is why iteration follows insertion order. A lookup hashes the key, probes the index table, then confirms with `==`. That is why keys must be hashable and must never change while they are in a dict.",
            "gotchas": [
                {
                    "title": "Changing a dict's size while iterating over it",
                    "note": "Adding or removing keys during iteration raises RuntimeError. Iterate over a snapshot of the keys instead.",
                    "wrong": """rssi = {"sta1": -50, "sta2": -82, "sta3": -90}
for mac in rssi:
    if rssi[mac] < -80:
        del rssi[mac]""",
                    "fixed": """rssi = {"sta1": -50, "sta2": -82, "sta3": -90}
for mac in list(rssi):
    if rssi[mac] < -80:
        del rssi[mac]
print(rssi)""",
                },
                {
                    "title": "dict.fromkeys() with a mutable default",
                    "note": "Every key shares the same list object.",
                    "wrong": """per_ap = dict.fromkeys(["ap-1", "ap-2"], [])
per_ap["ap-1"].append("sta1")
print(per_ap)""",
                    "fixed": """per_ap = {ap: [] for ap in ["ap-1", "ap-2"]}
per_ap["ap-1"].append("sta1")
print(per_ap)""",
                },
            ],
            "best": "Use `d[key]` when a missing key is a bug (fail loudly) and `d.get(key, default)` when absence is normal. Merge config layers with `|` so the originals stay untouched. Iterate with `.items()` rather than looking each key up again.",
        },
        {
            "title": "Grouping, counting and nested dicts",
            "concept": "`setdefault(key, default)` returns the existing value or inserts the default first, which makes **grouping** a one-liner: `groups.setdefault(k, []).append(x)`. `d[k] = d.get(k, 0) + 1` is the classic counter. Dicts can nest to represent structured configs, and chained indexing (`radios[\"6G\"][\"channel\"]`) reaches inner values.",
            "why": "Grouping stations by AP, counting disconnect reasons and keeping per-band radio configs are everyday tasks. Phase 2 introduces `defaultdict` and `Counter`, which make these even shorter, but they are built on exactly these patterns.",
            "syntax": "groups.setdefault(key, []).append(item)  # group\ncounts[key] = counts.get(key, 0) + 1     # count\ncfg[\"6G\"][\"channel\"] = 69                # nested update\nlist(d)  # list of keys",
            "code": """def main() -> None:
    log = [  ## (station MAC, AP name, RSSI) observations from a run
        ("aa:01", "ap-1", -50),  ## sta aa:01 seen on ap-1
        ("aa:02", "ap-1", -67),  ## sta aa:02 seen on ap-1
        ("aa:01", "ap-2", -58),  ## aa:01 has roamed to ap-2
        ("aa:03", "ap-2", -72),  ## aa:03 seen on ap-2
    ]
    by_ap: dict[str, list[str]] = {}  ## The type hint documents the shape: AP name -> list of MACs
    latest_rssi: dict[str, int] = {}  ## MAC -> most recent RSSI
    reasons = ["15", "3", "15", "8", "15"]  ## Deauth reason codes as text, as they come from a log
    for mac, ap, rssi in log:  ## Unpack each observation
        by_ap.setdefault(ap, []).append(mac)  ## Create the list on first sight of an AP, then append
        latest_rssi[mac] = rssi  ## Later observations overwrite earlier ones
    print(by_ap)  ## Stations grouped per AP
    print(latest_rssi)  ## aa:01 shows its value from ap-2
    counts: dict[str, int] = {}  ## reason -> occurrences
    for reason in reasons:  ## Count each reason code
        counts[reason] = counts.get(reason, 0) + 1  ## get() supplies 0 the first time
    print(counts)  ## Reason 15 (4-way handshake timeout) dominates
    radios = {"5G": {"channel": 36, "width": 80}, "6G": {"channel": 37, "width": 320}}  ## Nested per-band config
    radios["6G"]["channel"] = 69  ## Chained indexing reaches the inner dict
    print(radios["6G"], list(radios))  ## The inner dict, and the outer keys


if __name__ == "__main__":
    main()""",
            "under": "`setdefault` does one hash lookup and only inserts when the key is missing. Note that its default argument is evaluated every time the line runs, so `setdefault(k, [])` builds a throwaway empty list on each call even when the key already exists. That is harmless here, and `defaultdict` avoids it. Nested dicts are dicts holding references to other dict objects, so copying the outer dict does not copy the inner ones (Module 1.10).",
            "gotchas": [
                {
                    "title": "Nested lookups on missing keys",
                    "note": "Chained `[]` raises KeyError at the first missing level. Use get() with an empty-dict default for optional levels.",
                    "wrong": """radios = {"5G": {"channel": 36}}
print(radios["6G"]["channel"])""",
                    "fixed": """radios = {"5G": {"channel": 36}}
print(radios.get("6G", {}).get("channel", "not configured"))""",
                },
            ],
            "best": "For grouping and counting, write the pattern once with setdefault/get here, then switch to `defaultdict(list)` and `Counter` once you know them (Module 2.11). Keep nested configs shallow, and validate their shape when you load them (pydantic, Module 4.4).",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Invert `{'ap-1': '5G', 'ap-2': '6G', 'ap-3': '5G'}` into band -> list of APs.",
            "solution": "Group with setdefault.",
            "solution_code": """band_of = {"ap-1": "5G", "ap-2": "6G", "ap-3": "5G"}
aps_by_band = {}
for ap, band in band_of.items():
    aps_by_band.setdefault(band, []).append(ap)
print(aps_by_band)""",
        },
        {
            "level": "Medium",
            "prompt": "From a list of (test, verdict) results, build a summary dict with counts of PASS, FAIL and SKIP, including zeros for verdicts that never appear.",
            "solution": "Start from a dict with all keys at zero, then increment.",
            "solution_code": """results = [("t1", "PASS"), ("t2", "FAIL"), ("t3", "PASS"), ("t4", "PASS")]
summary = {"PASS": 0, "FAIL": 0, "SKIP": 0}
for _, verdict in results:
    summary[verdict] += 1
print(summary)""",
        },
        {
            "level": "Hard",
            "prompt": "Find the stations that roamed: build MAC -> list of APs in the order seen, and print only MACs that appear on more than one distinct AP, with their path.",
            "solution": "Group APs per MAC, skipping consecutive duplicates, then filter by length.",
            "solution_code": """log = [("aa:01", "ap-1"), ("aa:02", "ap-1"), ("aa:01", "ap-1"), ("aa:01", "ap-2"), ("aa:03", "ap-3"), ("aa:01", "ap-3")]
path = {}
for mac, ap in log:
    hops = path.setdefault(mac, [])
    if not hops or hops[-1] != ap:
        hops.append(ap)
for mac, hops in path.items():
    if len(hops) > 1:
        print(mac, " -> ".join(hops))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "d[key] vs d.get(key)?", "a": "`d[key]` raises KeyError if the key is missing. `d.get(key, default)` returns the default (None if not given). Use [] when the key must exist and get() when absence is normal.", "follow": "Does get() insert the key? (No; setdefault() does.)"},
        {"level": "Beginner", "q": "Are dictionaries ordered?", "a": "Yes. Since Python 3.7, dicts preserve insertion order as a language guarantee (it was a CPython 3.6 implementation detail before that). Updating an existing key keeps its original position.", "follow": "Is OrderedDict still useful? (For move_to_end() and order-sensitive equality.)"},
        {"level": "Intermediate", "q": "How does a dict lookup work, and why must keys be hashable?", "a": "Python computes `hash(key)`, uses it to find a slot in the hash table, then confirms the match with `==`. If a key's hash could change (as a mutable list's would), it would be stored in the wrong slot and become unfindable, so only hashable types are allowed.", "follow": "What must be true of __eq__ and __hash__? (Objects that compare equal must have equal hashes.)"},
        {"level": "Intermediate", "q": "How do you merge two dicts?", "a": "`merged = a | b` (3.9+) creates a new dict where b's values win. `a |= b` or `a.update(b)` updates in place. Before 3.9: `{**a, **b}`. None of these merge nested dicts recursively.", "follow": "How would you deep-merge configs? (A recursive function using deepcopy, as in Module 1.10.)"},
        {"level": "Advanced", "q": "Why does modifying a dict during iteration raise RuntimeError?", "a": "Inserting or deleting keys can resize or reorganise the hash table, which would invalidate the iterator's position. CPython detects the size change and raises `RuntimeError: dictionary changed size during iteration`. Iterate over `list(d)` or build a new dict instead.", "follow": "Is changing a value (not a key) during iteration allowed? (Yes; the size does not change.)"},
    ],
    "quiz": [
        {"q": "What does `{'a': 1}.get('b')` return?", "options": ["KeyError", "None", "0", "''"], "answer": 1, "why": "get() returns None by default."},
        {"q": "What is `{'a': 1, 'b': 2} | {'b': 3}`?", "options": ["{'a': 1, 'b': 2}", "{'a': 1, 'b': 3}", "{'b': 3}", "TypeError"], "answer": 1, "why": "The right side wins for shared keys."},
        {"q": "What does `'x' in d` test?", "options": ["Values", "Keys", "Both", "Items"], "answer": 1, "why": "Membership on a dict tests keys."},
        {"q": "Which cannot be a dict key?", "options": ["'ap-1'", "36", "('5G', 80)", "['5G', 80]"], "answer": 3, "why": "Lists are unhashable."},
        {"q": "What does `d.setdefault('k', []).append(1)` do when 'k' is missing?", "options": ["Raises KeyError", "Inserts [] for 'k', then appends 1", "Returns None", "Appends to a temporary list only"], "answer": 1, "why": "setdefault inserts the default and returns it."},
    ],
    "cards": [
        {"front": "d[k] vs d.get(k, default)", "back": "KeyError if missing vs default if missing."},
        {"front": "Dict order", "back": "Insertion order, guaranteed since Python 3.7."},
        {"front": "Group items by key", "back": "`groups.setdefault(key, []).append(item)`"},
        {"front": "Count occurrences", "back": "`counts[k] = counts.get(k, 0) + 1`"},
        {"front": "Merge dicts (3.9+)", "back": "`base | override` (right side wins)"},
    ],
}
