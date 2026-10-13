"""Phase 1 content: modules 1.4-1.6."""

M_1_4 = {
    "id": "1.4",
    "title": "Input & Output",
    "hours": 1,
    "summary": "print() options, stdout vs stderr, flushing for live progress in CI logs, and converting input() text safely.",
    "concepts": [
        {
            "title": "print(), stdout, stderr and flushing",
            "concept": "`print()` writes text to **stdout** by default. Its keyword arguments control the output: `sep` (between values), `end` (after the last value, default newline), `file` (where to write, e.g. `sys.stderr`) and `flush` (push the text out immediately). `input()` reads a line from the user and **always returns a str**.",
            "why": "Jenkins and other CI systems read stdout and stderr separately and often buffer output. Errors on stderr and flushed progress lines are what make a long attenuation sweep observable while it runs.",
            "syntax": "print(a, b, sep=\" | \")        # custom separator\nprint(\"x\", end=\"\")            # no newline\nprint(msg, file=sys.stderr)   # error stream\nprint(\".\", end=\"\", flush=True)  # show immediately\ntext = input(\"Channel? \")      # always a str",
            "code": """import sys  ## Gives access to sys.stdout and sys.stderr
import time  ## For a short sleep to simulate work


def main() -> None:
    print("AP", "STA", "channel 36", sep=" | ")  ## sep replaces the default single space between values
    print("Sweeping", end="")  ## end="" suppresses the newline, so the dots continue on this line
    for db in range(0, 40, 10):  ## Four steps: 0, 10, 20, 30 dB (range is covered in Module 1.6)
        print(".", end="", flush=True)  ## flush=True pushes each dot out immediately instead of waiting for the buffer
        time.sleep(0.05)  ## Simulates the time a real attenuation step takes
    print(" done")  ## Finishes the progress line with a newline
    print("warning: bench07 attenuator slow", file=sys.stderr)  ## Diagnostics go to stderr so they can be separated from results
    reply = "36"  ## Stands in for input("Channel? "), which always returns a str
    channel = int(reply)  ## Convert text to a number before doing arithmetic
    print(channel + 4)  ## 40: next 20 MHz channel up


if __name__ == "__main__":
    main()""",
            "under": "`sys.stdout` is a buffered text stream. In an interactive terminal it is **line-buffered** (flushed at each newline). When output goes to a pipe or a file, which is what happens in CI, it is **block-buffered**: nothing appears until about 8 KB accumulate or the program exits. `sys.stderr` is always line-buffered. `python -u` or the environment variable `PYTHONUNBUFFERED=1` disables stdout buffering for the whole process.",
            "gotchas": [
                {
                    "title": "input() returns text",
                    "note": "Arithmetic on the raw reply fails. Convert explicitly, and validate.",
                    "wrong": """reply = "36"
print(reply + 4)""",
                    "fixed": """reply = "36"
print(int(reply) + 4)""",
                },
                {
                    "title": "int() rejects decimal strings",
                    "note": "`int(\" 36 \")` works (whitespace is stripped) but `int(\"36.0\")` raises ValueError. Parse via float if the source may include decimals.",
                    "wrong": """print(int("36.0"))""",
                    "fixed": """print(int(float("36.0")), int(" 36 "))""",
                },
            ],
            "best": "Send results to stdout and diagnostics to stderr (better still, use `logging`, covered in Module 4.5). Run CI jobs with `PYTHONUNBUFFERED=1` so logs stream live. Convert and validate user input immediately after reading it.",
        }
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Print `5G|80|36` from three separate values using a single print() call and no f-string.",
            "solution": "Use the sep argument.",
            "solution_code": """print("5G", 80, 36, sep="|")""",
        },
        {
            "level": "Medium",
            "prompt": "Print a progress bar that grows by one `#` per step for 10 steps on a single line, then prints `100%`.",
            "solution": "Use end='' and flush=True for each step, then a final print.",
            "solution_code": """import time

for step in range(10):
    print("#", end="", flush=True)
    time.sleep(0.02)
print(" 100%")""",
        },
        {
            "level": "Hard",
            "prompt": "Write `parse_channel(text)` that accepts '36', ' 36 ' and '36.0', rejects '36.5' and 'abc' with a clear message, and returns an int.",
            "solution": "Convert via float, check it is a whole number, then convert to int. ValueError covers non-numeric text.",
            "solution_code": """def parse_channel(text: str) -> int:
    try:
        value = float(text)
    except ValueError:
        raise ValueError(f"not a number: {text!r}") from None
    if not value.is_integer():
        raise ValueError(f"channel must be a whole number: {text!r}")
    return int(value)


for t in ["36", " 36 ", "36.0", "36.5", "abc"]:
    try:
        print(repr(t), "->", parse_channel(t))
    except ValueError as err:
        print(repr(t), "->", err)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What is the difference between stdout and stderr?", "a": "Two separate output streams. stdout carries normal results; stderr carries errors and diagnostics. They can be redirected independently (`2>errors.log`), so tools and CI systems can separate them.", "follow": "Where does an uncaught exception's traceback go? (stderr.)"},
        {"level": "Intermediate", "q": "Why does my script's output appear only at the end in Jenkins?", "a": "When stdout is a pipe, Python block-buffers it. Fix it with `print(..., flush=True)`, `python -u`, or `PYTHONUNBUFFERED=1` in the job environment.", "follow": "Why does it look fine in a terminal? (Terminals get line buffering.)"},
        {"level": "Beginner", "q": "What type does input() return?", "a": "Always `str`. Convert with `int()` or `float()` and handle `ValueError` for bad input.", "follow": "What does int(' 42 ') return? (42; surrounding whitespace is allowed.)"},
        {"level": "Intermediate", "q": "How would you print a live, single-line progress indicator?", "a": "Use `end=''` (or a leading `\\r` to overwrite the line) together with `flush=True`. In CI logs `\\r` often renders poorly, so periodic full lines may be better.", "follow": "How would you avoid this in production code? (Use logging with a progress log line every N steps.)"},
    ],
    "quiz": [
        {"q": "What does `print('a', 'b', sep='-', end='!')` output?", "options": ["a b!", "a-b!", "a-b\\n!", "a-b"], "answer": 1, "why": "sep joins the values and end replaces the newline."},
        {"q": "Which makes CI logs stream live?", "options": ["print(..., end='')", "PYTHONUNBUFFERED=1", "sys.exit(0)", "print(..., sep='')"], "answer": 1, "why": "It disables block buffering of stdout."},
        {"q": "What does `int('36.0')` do?", "options": ["Returns 36", "Returns 36.0", "Raises ValueError", "Raises TypeError"], "answer": 2, "why": "int() does not parse decimal strings."},
        {"q": "Where should warnings go in a script whose stdout is parsed by another tool?", "options": ["stdout", "stderr", "A comment", "Nowhere"], "answer": 1, "why": "Keep stdout clean for the data the other tool reads."},
        {"q": "What does input() return when the user types 5?", "options": ["5", "'5'", "5.0", "None"], "answer": 1, "why": "Always a str."},
    ],
    "cards": [
        {"front": "print() keyword arguments", "back": "`sep`, `end`, `file`, `flush`"},
        {"front": "Why output is delayed in CI", "back": "stdout is block-buffered when piped. Use flush=True, -u or PYTHONUNBUFFERED=1."},
        {"front": "input() return type", "back": "Always str."},
        {"front": "Print to stderr", "back": "`print(msg, file=sys.stderr)`"},
    ],
}


M_1_5 = {
    "id": "1.5",
    "title": "Conditionals & match-case",
    "hours": 2,
    "summary": "if/elif/else chains, the conditional expression, the walrus operator, and structural pattern matching for event dispatch.",
    "concepts": [
        {
            "title": "if, elif, else, the ternary and :=",
            "concept": "`if` / `elif` / `else` run the **first** branch whose condition is truthy, so the order of the branches matters. The conditional expression `a if cond else b` picks a value in one line. The walrus operator `:=` assigns a value inside an expression, so you can compute, test and keep a value at once.",
            "why": "Classifying RSSI into quality bands, choosing a channel width per band, or deciding whether a sample is an outlier are all ordered decisions. Getting the order wrong silently mislabels data.",
            "syntax": "if cond1:\n    ...\nelif cond2:\n    ...\nelse:\n    ...\n\nvalue = a if cond else b\nif (n := len(items)) > 10:\n    print(n)",
            "code": """def classify_rssi(rssi: int) -> str:  ## preview: functions are taught in Module 2.1
    if rssi >= -50:  ## Strongest band first: the first true branch wins
        return "excellent"  ## return exits the function immediately
    elif rssi >= -65:  ## Only reached when rssi < -50
        return "good"  ## -65 to -51
    elif rssi >= -75:  ## Only reached when rssi < -65
        return "fair"  ## -75 to -66
    else:  ## Everything weaker than -75 dBm
        return "poor"  ## Catch-all branch


def main() -> None:
    for value in [-42, -63, -70, -88]:  ## One sample per band
        print(value, classify_rssi(value))  ## Shows how each value is labelled
    band = "6G"  ## Band under test
    width = 320 if band == "6G" else 80  ## Conditional expression: one value or the other
    print(band, width)  ## 6G 320
    samples = [910.2, 905.7, 0.0, 899.1]  ## Throughput samples with one zero (a stall)
    if (zeros := samples.count(0.0)) > 0:  ## Walrus: assign the count and test it in one step
        print(f"{zeros} zero-throughput sample(s) found")  ## The assigned value is still available here


if __name__ == "__main__":
    main()""",
            "under": "Python evaluates each condition with `bool()` semantics (Module 1.10), and stops at the first truthy one. `elif` is just `else: if` without the extra indentation. The walrus operator was added in Python 3.8. It binds the name in the enclosing scope, so `zeros` stays defined after the `if`.",
            "gotchas": [
                {
                    "title": "`x == a or b` is always true",
                    "note": "It parses as `(x == a) or b`, and a non-empty string is truthy. Compare each value, or use `in`.",
                    "wrong": """band = "2G"
if band == "5G" or "6G":
    print("high band test")""",
                    "fixed": """band = "2G"
if band in ("5G", "6G"):
    print("high band test")
else:
    print("skipping: low band")""",
                },
                {
                    "title": "Branches in the wrong order",
                    "note": "The broader condition placed first swallows the narrower one.",
                    "wrong": """rssi = -45
if rssi >= -75:
    print("fair")
elif rssi >= -50:
    print("excellent")""",
                    "fixed": """rssi = -45
if rssi >= -50:
    print("excellent")
elif rssi >= -75:
    print("fair")""",
                },
            ],
            "best": "Order range checks from most to least restrictive, use `in` with a tuple for membership, and keep each condition simple enough to read aloud. Use the conditional expression only for simple value choices, never for side effects.",
        },
        {
            "title": "Structural pattern matching (match-case)",
            "concept": "`match` compares a value against **patterns** in order and runs the first one that matches. Patterns can match literals, sequences, mappings (dicts) and classes, and they can **capture** parts into names. A `case ... if guard` adds an extra condition. `case _` is the catch-all. There is no fall-through between cases.",
            "why": "Event streams from logs or controllers (associations, roams, deauths) are naturally dict-shaped. Pattern matching dispatches on their structure and pulls out the fields you need in one readable statement.",
            "syntax": "match value:\n    case 0 | 1:                    # literal alternatives\n        ...\n    case [\"set\", \"channel\", ch]:     # sequence pattern, captures ch\n        ...\n    case {\"type\": \"roam\", \"to\": t}:  # mapping pattern\n        ...\n    case int(n) if n > 0:            # class pattern + guard\n        ...\n    case _:                          # anything else\n        ...",
            "code": """def handle(event: dict) -> str:  ## Turns one parsed event dict into a message
    match event:  ## Try each case pattern in order against the dict
        case {"type": "assoc", "sta": sta, "bssid": bssid}:  ## Mapping pattern: needs these keys; captures two values
            return f"{sta} associated to {bssid}"  ## Captured names are ordinary local variables
        case {"type": "roam", "sta": sta, "from": old, "to": new} if old != new:  ## Guard: only a real roam matches
            return f"{sta} roamed {old} -> {new}"  ## Uses all three captured values
        case {"type": "deauth", "reason": 3 | 8 as code}:  ## `3 | 8` matches either literal; `as` captures the matched value
            return f"leaving (reason {code})"  ## 3 and 8 mean the sender is leaving the BSS/ESS
        case {"type": "deauth", "reason": int(code)}:  ## Class pattern: any int reason, captured as code
            return f"deauth reason {code}"  ## Every other reason code
        case _:  ## Wildcard: matches anything that fell through
            return "unknown event"  ## Safe default


def main() -> None:
    events = [  ## A small event stream, as a log parser might produce it
        {"type": "assoc", "sta": "sta1", "bssid": "ap-1", "rssi": -52},  ## Extra keys such as rssi are ignored by mapping patterns
        {"type": "roam", "sta": "sta1", "from": "ap-1", "to": "ap-2"},  ## A genuine roam
        {"type": "roam", "sta": "sta1", "from": "ap-2", "to": "ap-2"},  ## Same AP on both sides: the guard rejects it
        {"type": "deauth", "sta": "sta1", "reason": 8},  ## Matches the 3 | 8 case
        {"type": "deauth", "sta": "sta1", "reason": 15},  ## 15: 4-way handshake timeout
    ]
    for event in events:  ## Dispatch each event
        print(handle(event))  ## Show which case handled it


if __name__ == "__main__":
    main()""",
            "under": "The compiler turns `match` into a series of structural checks: type checks for class patterns, `len` and indexing for sequence patterns, and key lookups for mapping patterns. Mapping patterns only require the listed keys to exist; extra keys are fine. Sequence patterns never match `str`, `bytes` or `bytearray`, so a string is not treated as a sequence of characters. Available since Python 3.10.",
            "gotchas": [
                {
                    "title": "A bare name in a case is a capture, not a constant",
                    "note": "`case DEAUTH:` does not compare against the variable DEAUTH. It matches **anything** and rebinds the name. Use a literal or a dotted name such as `EventType.DEAUTH`.",
                    "wrong": """DEAUTH = "deauth"

def kind(event_type):
    match event_type:
        case DEAUTH:
            return "deauth!"

print(kind("assoc"))""",
                    "fixed": """def kind(event_type):
    match event_type:
        case "deauth":
            return "deauth!"
        case _:
            return "other"

print(kind("assoc"), "|", kind("deauth"))""",
                }
            ],
            "best": "Reach for `match` when you dispatch on the **shape** of data. For simple value comparisons an `if` chain or a dict lookup is clearer. Always end with `case _` so unexpected input is handled on purpose.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write `width_for(band)` returning 40 for '2G', 80 for '5G', 320 for '6G' and raising ValueError otherwise.",
            "solution": "A simple if/elif chain (or match) with an explicit failure for unknown bands.",
            "solution_code": """def width_for(band: str) -> int:
    if band == "2G":
        return 40
    elif band == "5G":
        return 80
    elif band == "6G":
        return 320
    raise ValueError(f"unknown band: {band}")


print(width_for("2G"), width_for("5G"), width_for("6G"))""",
        },
        {
            "level": "Medium",
            "prompt": "Parse lab commands with match: `set channel 149`, `set width 160`, `scan`, and anything else as 'unknown'. Convert numeric arguments to int.",
            "solution": "Split the command into a list and use sequence patterns with captures.",
            "solution_code": """def run(cmd: str) -> str:
    match cmd.split():
        case ["set", "channel", ch]:
            return f"channel -> {int(ch)}"
        case ["set", "width", w]:
            return f"width -> {int(w)} MHz"
        case ["scan"]:
            return "scanning"
        case _:
            return f"unknown: {cmd!r}"


for c in ["set channel 149", "set width 160", "scan", "reboot now"]:
    print(run(c))""",
        },
        {
            "level": "Hard",
            "prompt": "Count events by kind from a list of dicts using match: assoc, real roam (from != to), deauth with reason 15 ('handshake timeout'), other deauth, other.",
            "solution": "Use mapping patterns with a guard, and a dict to hold counters.",
            "solution_code": """events = [
    {"type": "assoc"}, {"type": "roam", "from": "a", "to": "b"},
    {"type": "roam", "from": "a", "to": "a"}, {"type": "deauth", "reason": 15},
    {"type": "deauth", "reason": 3}, {"type": "probe"},
]
counts = {}
for e in events:
    match e:
        case {"type": "assoc"}:
            k = "assoc"
        case {"type": "roam", "from": a, "to": b} if a != b:
            k = "roam"
        case {"type": "deauth", "reason": 15}:
            k = "handshake timeout"
        case {"type": "deauth"}:
            k = "other deauth"
        case _:
            k = "other"
    counts[k] = counts.get(k, 0) + 1
print(counts)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Why is `if band == '5G' or '6G':` a bug?", "a": "It evaluates as `(band == '5G') or '6G'`. A non-empty string is truthy, so the condition is always true. Write `band in ('5G', '6G')`.", "follow": "Why a tuple rather than a list? (Either works; a tuple or set signals a fixed collection.)"},
        {"level": "Intermediate", "q": "Is match-case just a switch statement?", "a": "No. It does structural pattern matching: it can destructure sequences, mappings and objects, capture values into names, combine alternatives with `|` and add guards. There is no fall-through, and the first matching case wins.", "follow": "What does a bare name in a case pattern do? (It captures, matching anything.)"},
        {"level": "Intermediate", "q": "What does the walrus operator do, and when is it useful?", "a": "`name := expr` assigns and returns the value inside an expression. It avoids computing something twice, e.g. `while (line := f.readline()):` or `if (m := pattern.search(s)):`.", "follow": "Which Python version introduced it? (3.8.)"},
        {"level": "Advanced", "q": "Does a mapping pattern require an exact dict match?", "a": "No. It only requires the listed keys to be present (and their sub-patterns to match). Extra keys are ignored; use `**rest` to capture them.", "follow": "Does a sequence pattern match a string? (No; str, bytes and bytearray are excluded.)"},
    ],
    "quiz": [
        {"q": "With `rssi = -60`, which branch runs? `if rssi >= -75: A elif rssi >= -50: B else: C`", "options": ["A", "B", "C", "A and B"], "answer": 0, "why": "-60 >= -75 is true and the first true branch wins."},
        {"q": "What does `case x:` (bare name) match?", "options": ["Only the value in variable x", "Anything, capturing it as x", "Nothing", "It is a SyntaxError"], "answer": 1, "why": "Bare names are capture patterns."},
        {"q": "What is `'yes' if 0 else 'no'`?", "options": ["'yes'", "'no'", "0", "None"], "answer": 1, "why": "0 is falsy."},
        {"q": "Which Python version introduced match-case?", "options": ["3.6", "3.8", "3.10", "3.12"], "answer": 2, "why": "PEP 634, Python 3.10."},
        {"q": "Does `case {'type': 'roam'}` match `{'type': 'roam', 'sta': 'x'}`?", "options": ["Yes", "No", "Only with a guard", "Only with **rest"], "answer": 0, "why": "Extra keys are ignored by mapping patterns."},
    ],
    "cards": [
        {"front": "`x == a or b` bug", "back": "Parses as `(x == a) or b`; use `x in (a, b)`."},
        {"front": "Conditional expression syntax", "back": "`value_if_true if condition else value_if_false`"},
        {"front": "Walrus operator", "back": "`name := expr` assigns inside an expression (3.8+)."},
        {"front": "Bare name in a case pattern", "back": "A capture: it matches anything. Use literals or dotted names for constants."},
        {"front": "Catch-all case", "back": "`case _:`"},
    ],
}


M_1_6 = {
    "id": "1.6",
    "title": "Loops",
    "hours": 2.5,
    "summary": "for over any iterable, range/enumerate/zip/reversed, while loops with deadlines, break/continue and the loop else clause.",
    "concepts": [
        {
            "title": "for loops and the iteration helpers",
            "concept": "`for item in iterable:` walks any iterable (lists, strings, dicts, files, ranges). `range(start, stop, step)` produces numbers lazily and **excludes stop**. `enumerate()` adds a counter, `zip()` walks several iterables in step, `reversed()` walks backwards. `zip(..., strict=True)` raises an error if the lengths differ (Python 3.10+).",
            "why": "Channel lists, attenuation steps and test matrices are all loops. `zip(strict=True)` catches the classic bug of a channel list and an expected-result list falling out of step.",
            "syntax": "for x in items: ...\nfor i in range(0, 61, 20): ...      # 0, 20, 40, 60\nfor idx, x in enumerate(items, start=1): ...\nfor a, b in zip(xs, ys, strict=True): ...\nfor x in reversed(items): ...",
            "code": """def main() -> None:
    channels = [36, 40, 44, 48]  ## UNII-1 20 MHz channels
    for ch in channels:  ## Each pass binds `ch` to the next element
        print(ch, end=" ")  ## Print on one line
    print()  ## End the line
    for i in range(0, 61, 20):  ## start 0, stop 61 (excluded), step 20: 0, 20, 40, 60
        print(f"attenuation {i} dB")  ## One line per step
    for idx, ch in enumerate(channels, start=1):  ## enumerate yields (counter, item) pairs; start=1 for human numbering
        print(f"{idx}: ch{ch}")  ## Numbered list
    widths = [20, 40, 80, 160]  ## One width per channel
    for ch, w in zip(channels, widths):  ## zip pairs the first items, then the second items, and so on
        print(f"ch{ch}@{w}MHz", end="  ")  ## Paired output on one line
    print()  ## End the line
    try:  ## preview: try/except is taught in Module 2.5
        list(zip(channels, widths[:3], strict=True))  ## Lengths 4 and 3: strict=True raises instead of silently dropping data
    except ValueError as err:  ## Catch the mismatch error
        print("ValueError:", err)  ## Explains which argument was shorter
    for ch in reversed(channels):  ## Walk the list backwards without copying it
        print(ch, end=" ")  ## 48 44 40 36
    print()  ## End the line


if __name__ == "__main__":
    main()""",
            "under": "`for` calls `iter()` on the object to get an iterator, then calls `next()` on it repeatedly until `StopIteration` is raised. That protocol is why every container, file object and generator works in a for loop (Module 3.7). `range` objects store only start, stop and step, so `range(10**12)` uses almost no memory. `enumerate`, `zip` and `reversed` return lazy iterators too.",
            "gotchas": [
                {
                    "title": "Removing items while iterating",
                    "note": "Removing shifts later elements left, so the loop skips the next item. Iterate over a copy, or build a new list (comprehensions, Module 2.4).",
                    "wrong": """rssi = [-80, -82, -50, -90]
for r in rssi:
    if r < -75:
        rssi.remove(r)
print(rssi)""",
                    "fixed": """rssi = [-80, -82, -50, -90]
for r in rssi[:]:
    if r < -75:
        rssi.remove(r)
print(rssi)""",
                },
                {
                    "title": "range() excludes the stop value",
                    "note": "A sweep from 0 to 60 dB in 20 dB steps needs stop=61 (or 60 + step).",
                    "wrong": """print(list(range(0, 60, 20)))""",
                    "fixed": """print(list(range(0, 60 + 20, 20)))""",
                },
                {
                    "title": "zip() silently truncates",
                    "note": "Without strict=True the extra items are dropped with no warning.",
                    "wrong": """channels = [36, 40, 44]
expected = [900, 905]
print(list(zip(channels, expected)))""",
                    "fixed": """channels = [36, 40, 44]
expected = [900, 905]
try:
    print(list(zip(channels, expected, strict=True)))
except ValueError as err:
    print("ValueError:", err)""",
                },
            ],
            "best": "Loop over items directly, never `for i in range(len(items))` unless you really need the index; then use `enumerate`. Use `zip(strict=True)` whenever the lists are supposed to match. Never mutate a list while looping over it.",
        },
        {
            "title": "while, break, continue and loop-else",
            "concept": "`while cond:` repeats while the condition is truthy. `break` exits the loop immediately; `continue` skips to the next iteration. A loop's `else:` block runs only if the loop finished **without** `break`, which makes it a natural \"nothing was found / everything passed\" branch. Polling loops must always have a **deadline**, measured with `time.monotonic()`.",
            "why": "Waiting for a station to associate, for an AP to come back after reboot, or for a DHCP lease all need a poll-until-timeout loop. A loop without a deadline is how a nightly job hangs for 10 hours.",
            "syntax": "deadline = time.monotonic() + timeout\nwhile time.monotonic() < deadline:\n    if ready():\n        break\n    time.sleep(interval)\nelse:\n    raise TimeoutError(\"not ready\")",
            "code": """import time  ## monotonic() for deadlines, sleep() between polls


class FakeStation:  ## preview: classes are taught in Module 3.1; this one simulates a STA
    def __init__(self, connects_after: int) -> None:  ## Number of polls before it reports associated
        self.polls = 0  ## How many times we have asked so far
        self.connects_after = connects_after  ## Store the threshold on the object

    def is_associated(self) -> bool:  ## Each call counts as one poll
        self.polls += 1  ## Record the poll
        return self.polls >= self.connects_after  ## True once enough polls have happened


def wait_for_association(sta: FakeStation, timeout: float, interval: float) -> bool:  ## Generic poll-until-timeout helper
    deadline = time.monotonic() + timeout  ## monotonic() never jumps backwards, unlike time.time()
    while time.monotonic() < deadline:  ## Keep polling until the deadline passes
        if sta.is_associated():  ## Condition met?
            return True  ## Leave immediately with success
        time.sleep(interval)  ## Wait before the next poll so we don't hammer the device
    return False  ## Deadline reached without success


def main() -> None:
    print(wait_for_association(FakeStation(3), timeout=1.0, interval=0.05))  ## Connects on the 3rd poll: True
    print(wait_for_association(FakeStation(100), timeout=0.3, interval=0.05))  ## Would need 100 polls: times out, False

    results = {36: 910, 40: 0, 44: 905, 48: 899}  ## Channel -> measured Mbps (dicts: Module 1.9)
    for ch, mbps in results.items():  ## Walk the (channel, value) pairs
        if mbps == 0:  ## No traffic at all: skip this channel
            print(f"ch{ch}: no traffic, skipping")  ## Report the skip
            continue  ## Jump straight to the next channel
        if mbps < 850:  ## Below threshold: stop the whole check
            print(f"ch{ch}: below threshold, stop")  ## Report why we stop
            break  ## Leave the loop; the else block will NOT run
        print(f"ch{ch}: {mbps} Mbps ok")  ## Normal pass
    else:  ## Runs only because the loop finished without break
        print("all channels passed the threshold check")  ## Summary when nothing failed


if __name__ == "__main__":
    main()""",
            "under": "`time.time()` follows the wall clock, which NTP can step forwards or backwards, so durations measured with it can be wrong or even negative. `time.monotonic()` is guaranteed never to go backwards and is the correct clock for timeouts. The loop `else` clause compiles to a jump that `break` skips over; it has nothing to do with whether the loop body ever ran.",
            "gotchas": [
                {
                    "title": "Polling with no deadline",
                    "note": "If the device never becomes ready, the job hangs until someone kills it. Always bound the wait.",
                    "wrong": """import time

def wait_up(check):
    while not check():
        time.sleep(1)

print("this would hang forever if check() never returns True")""",
                    "fixed": """import time

def wait_up(check, timeout=2.0, interval=0.1):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(interval)
    return False

print(wait_up(lambda: False, timeout=0.3))""",
                },
                {
                    "title": "Misreading loop-else",
                    "note": "`else` runs when the loop ends without `break`, including when the iterable was empty. It is not an 'if the loop didn't run' branch.",
                    "wrong": """for ch in []:
    print("testing", ch)
else:
    print("else ran even though the list was empty")""",
                    "fixed": """channels = []
if not channels:
    print("no channels configured")
for ch in channels:
    print("testing", ch)""",
                },
            ],
            "best": "Write one reusable `wait_until(condition, timeout, interval)` helper and use it everywhere instead of `time.sleep(30)` after a reboot. Use loop-else only for search loops where 'not found' is the else case, and add a comment, because many readers misread it.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Print every 5 GHz UNII-3 channel from 149 to 165 inclusive (step 4) with its index starting at 1.",
            "solution": "range with stop 166 (exclusive) and enumerate(start=1).",
            "solution_code": """for idx, ch in enumerate(range(149, 166, 4), start=1):
    print(idx, ch)""",
        },
        {
            "level": "Medium",
            "prompt": "Given `channels` and `measured` lists, print PASS/FAIL per channel against a 900 Mbps threshold, refusing to run if the lists differ in length.",
            "solution": "zip(strict=True) turns a length mismatch into an error before any wrong verdict is printed.",
            "solution_code": """channels = [36, 40, 44, 48]
measured = [912.0, 887.5, 905.1, 930.2]
for ch, mbps in zip(channels, measured, strict=True):
    verdict = "PASS" if mbps >= 900 else "FAIL"
    print(f"ch{ch}: {mbps:7.1f} Mbps {verdict}")""",
        },
        {
            "level": "Hard",
            "prompt": "Search a scan list of (bssid, rssi) for the first BSSID stronger than -60 dBm. Use for-else to print 'no suitable AP' when none qualifies. Test with two lists.",
            "solution": "break on the first match; else handles the not-found case.",
            "solution_code": """def pick(scan):
    for bssid, rssi in scan:
        if rssi > -60:
            print("selected", bssid, rssi)
            break
    else:
        print("no suitable AP")


pick([("ap-1", -72), ("ap-2", -55), ("ap-3", -50)])
pick([("ap-1", -72), ("ap-2", -81)])""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "When does a for loop's else block run?", "a": "When the loop finishes without hitting `break`, including when the iterable is empty. It is useful for search loops where 'not found' goes in the else.", "follow": "Does while support else too? (Yes, with the same rule.)"},
        {"level": "Beginner", "q": "What does zip() do with lists of different lengths?", "a": "It stops at the shortest and silently drops the rest. In Python 3.10+ `zip(..., strict=True)` raises ValueError instead; `itertools.zip_longest` pads the shorter ones.", "follow": "Which would you use in a test that pairs expected and actual results? (strict=True.)"},
        {"level": "Intermediate", "q": "How do you wait for a device to come up without hanging forever?", "a": "Poll in a loop with a deadline measured by `time.monotonic()`, sleep between polls, and return or raise when the deadline passes. Wrap it in a reusable `wait_until()` helper.", "follow": "Why monotonic() rather than time()? (The wall clock can jump; monotonic can't go backwards.)"},
        {"level": "Intermediate", "q": "Why is `for i in range(len(items))` considered unpythonic?", "a": "It adds indexing noise and invites off-by-one errors. Iterate items directly, or use `enumerate()` when you need the index and `zip()` to walk several lists together.", "follow": "When is an index loop justified? (When you must modify items by position or look at neighbours, though `zip(items, items[1:])` often still works.)"},
        {"level": "Advanced", "q": "What actually happens when a for loop runs?", "a": "Python calls `iter(obj)` to get an iterator, then calls `next()` on it until `StopIteration` is raised, binding each result to the loop variable. Any object implementing `__iter__` (or the older `__getitem__` protocol) can be looped over.", "follow": "What is the difference between an iterable and an iterator? (An iterator also has `__next__` and is consumed once.)"},
    ],
    "quiz": [
        {"q": "What does `list(range(0, 10, 3))` return?", "options": ["[0, 3, 6, 9]", "[0, 3, 6]", "[3, 6, 9]", "[0, 3, 6, 9, 12]"], "answer": 0, "why": "Stop (10) is excluded; 9 < 10 is included."},
        {"q": "A for loop ends with break. Does its else block run?", "options": ["Yes", "No", "Only if the list was empty", "Only in Python 2"], "answer": 1, "why": "else runs only when the loop finishes without break."},
        {"q": "Which clock should a timeout loop use?", "options": ["time.time()", "time.monotonic()", "datetime.now()", "time.ctime()"], "answer": 1, "why": "monotonic never jumps backwards."},
        {"q": "What does `enumerate(['a', 'b'], start=1)` yield first?", "options": ["'a'", "(0, 'a')", "(1, 'a')", "1"], "answer": 2, "why": "It yields (counter, item) pairs starting at start."},
        {"q": "`zip([1, 2, 3], [4, 5])` produces how many pairs?", "options": ["2", "3", "It raises", "0"], "answer": 0, "why": "zip stops at the shortest unless strict=True."},
    ],
    "cards": [
        {"front": "range(start, stop, step)", "back": "Lazy sequence; stop is excluded."},
        {"front": "for-else", "back": "else runs if the loop ended without break."},
        {"front": "zip(strict=True)", "back": "Raises ValueError if lengths differ (3.10+)."},
        {"front": "Timeout loop clock", "back": "`time.monotonic()`"},
        {"front": "Remove items while looping?", "back": "Never mutate the list you iterate; loop over a copy or build a new list."},
    ],
}
