"""Phase 10 capstones 10.1-10.4: complete, runnable reference projects."""

from lab_support import LAB_PY
from net_support import needs, sim


def plain(code: str) -> str:
    """The annotated example code without its '  ## ' explanations, for use as a supporting file."""
    return "\n".join(line.split("  ## ")[0].rstrip() for line in code.split("\n")) + "\n"


ASYNCSSH = needs("asyncssh") + " and starts simulated SSH devices on localhost"
RVR = needs("requests matplotlib") + " and starts simulated lab equipment on localhost"
REPORT = needs("jinja2 playwright") + " plus `playwright install chromium`"


LOGSCAN = '''"""logscan: summarise AP syslog files and fail CI on serious events."""  ## Module docstring = --help description
import argparse  ## Command-line parsing
import io  ## In-memory text for the demo
import json  ## Machine-readable output
import re  ## Line and event patterns
import sys  ## stdin/stdout
from collections import Counter  ## Tallies

LINE = re.compile(r"(?P<ts>\\S+) (?P<host>\\S+) (?P<proc>[\\w.-]+)(?:\\[\\d+\\])?: (?P<msg>.*)")  ## timestamp host process[pid]: message
RULES = [  ## (event kind, pattern, severity); first match wins
    ("fw_crash", re.compile(r"firmware crashed|FW crash"), "critical"),  ## Radio firmware crash
    ("kernel_warn", re.compile(r"WARNING: CPU: \\d+"), "error"),  ## Kernel warning with backtrace
    ("radar", re.compile(r"DFS radar detected on channel (?P<ch>\\d+)"), "warning"),  ## Channel change forced by radar
    ("deauth", re.compile(r"deauthenticated .*reason (?P<reason>\\d+)"), "info"),  ## Client left or was kicked
    ("auth_fail", re.compile(r"SAE: .*(fail|mismatch)", re.I), "warning"),  ## Wrong password / SAE problem
]  ## End of rules
SEVERITY = {"info": 0, "warning": 1, "error": 2, "critical": 3}  ## Ordering for filters and exit codes


def parse(stream):  ## Yield one event dict per interesting line
    for raw in stream:  ## Works on files, stdin, StringIO
        m = LINE.match(raw.strip())  ## Split the syslog line
        if not m:  ## Unrecognised format
            continue  ## Skip quietly (could count these too)
        for kind, pattern, severity in RULES:  ## Classify
            if hit := pattern.search(m["msg"]):  ## First matching rule
                yield {**m.groupdict(), "kind": kind, "severity": severity, **{k: v for k, v in hit.groupdict().items() if v}}  ## Line fields + event + captured details
                break  ## One event per line


def build_parser():  ## Separate so tests can inspect it
    p = argparse.ArgumentParser(prog="logscan", description=__doc__)  ## Help text from the docstring
    p.add_argument("--min-severity", choices=SEVERITY, default="info", help="hide events below this level")  ## Filter
    p.add_argument("--host", help="only events from this host")  ## Filter
    p.add_argument("--json", action="store_true", help="machine-readable output")  ## Output format
    p.add_argument("--fail-on", choices=SEVERITY, default="critical", help="exit 1 if any event is at least this severe")  ## CI gate
    return p  ## Configured parser


def main(argv=None, stdin=None, stdout=None):  ## Testable entry point
    args = build_parser().parse_args(argv)  ## argv=None means sys.argv[1:]
    out = stdout or sys.stdout  ## Where to print
    events = [e for e in parse(stdin or sys.stdin)  ## All events...
              if SEVERITY[e["severity"]] >= SEVERITY[args.min_severity] and args.host in (None, e["host"])]  ## ...that pass the filters
    if args.json:  ## Machine-readable
        json.dump({"events": len(events), "by_kind": Counter(e["kind"] for e in events)}, out, sort_keys=True)  ## Summary object
        out.write("\\n")  ## Newline after JSON
    else:  ## Human-readable table
        for (host, kind), n in sorted(Counter((e["host"], e["kind"]) for e in events).items()):  ## Count per host and kind
            out.write(f"{host:<10} {kind:<12} {n}\\n")  ## Aligned row
    worst = max((SEVERITY[e["severity"]] for e in events), default=-1)  ## Most severe event shown
    return 1 if worst >= SEVERITY[args.fail_on] else 0  ## Non-zero fails the CI step


SAMPLE = """2026-10-12T01:14:07 ap-lab-07 hostapd: wlan1: STA 02:00:00:00:01:00 IEEE 802.11: deauthenticated due to local deauth request (reason 3)
2026-10-12T01:20:44 ap-lab-07 kernel: [8123.4] ath12k_pci 0000:01:00.0: DFS radar detected on channel 52
2026-10-12T01:20:45 ap-lab-07 hostapd: wlan1: STA 02:00:00:00:02:00 IEEE 802.11: deauthenticated due to inactivity (reason 4)
2026-10-12T02:03:10 ap-lab-08 hostapd: wlan2: SAE: commit mismatch for 02:00:00:00:03:00
2026-10-12T02:31:59 ap-lab-08 kernel: [9001.2] ath12k_pci 0000:01:00.0: firmware crashed: MHI_CB_EE_RDDM
2026-10-12T02:32:00 ap-lab-08 kernel: WARNING: CPU: 2 PID: 911 at drivers/net/wireless/ath/ath12k/mac.c:1234
garbage line without the expected format"""  ## A night of logs from two APs

if __name__ == "__main__":  ## Demo when run directly (tests import the module instead)
    print("exit:", main(["--min-severity", "warning"], io.StringIO(SAMPLE)))  ## Table of warning+ events; crash -> exit 1
    print("exit:", main(["--host", "ap-lab-07", "--json"], io.StringIO(SAMPLE)))  ## JSON for one host; nothing critical -> 0'''

LOGSCAN_TESTS = '''import io
import json

import pytest

from logscan import SAMPLE, build_parser, main, parse


def run(*argv):
    out = io.StringIO()
    code = main(list(argv), io.StringIO(SAMPLE), out)
    return code, out.getvalue()


def test_parse_classifies_and_extracts_details():
    events = list(parse(io.StringIO(SAMPLE)))
    kinds = [e["kind"] for e in events]
    assert kinds == ["deauth", "radar", "deauth", "auth_fail", "fw_crash", "kernel_warn"]
    assert events[1]["ch"] == "52" and events[0]["reason"] == "3"


def test_crash_fails_the_run():
    code, _ = run("--json")
    assert code == 1


def test_host_filter_and_json_shape():
    code, text = run("--host", "ap-lab-07", "--json")
    data = json.loads(text)
    assert code == 0
    assert data == {"by_kind": {"deauth": 2, "radar": 1}, "events": 3}


@pytest.mark.parametrize("level,expected_rows", [("info", 5), ("warning", 4), ("critical", 1)])
def test_min_severity(level, expected_rows):
    _, text = run("--min-severity", level, "--fail-on", "critical")
    assert len(text.splitlines()) == expected_rows


def test_invalid_choice_is_a_usage_error():
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--min-severity", "loud"])
    assert exc.value.code == 2
'''

M_10_1 = {
    "id": "10.1",
    "title": "Log Analyzer CLI",
    "hours": 4,
    "summary": "Capstone: a complete command-line tool that parses AP syslogs into classified events, filters them, prints a table or JSON, and returns an exit code CI can gate on; plus its test suite.",
    "concepts": [
        {
            "title": "The tool: parse, classify, filter, report, exit code",
            "filename": "logscan.py",
            "concept": "**Brief:** nightly runs leave megabytes of AP logs nobody reads. Build `logscan`: read syslog lines (file or stdin), classify interesting ones with ordered regex rules (firmware crash, kernel warning, DFS radar, deauth with reason, SAE failure), filter by severity and host, print a summary table or JSON, and exit non-zero when anything at or above `--fail-on` appears. **Skills used:** regex with named groups (2.x), generators, argparse with a testable `main(argv)` (4.1), Counter, JSON, exit codes.",
            "why": "A firmware crash in the AP log during an RvR run explains a throughput dip that otherwise looks like an RF problem. A tool that turns logs into a 6-line summary and fails the pipeline on crashes makes that link automatic.",
            "syntax": "logscan --min-severity warning < ap.log\nlogscan --host ap-lab-07 --json ap.log\nlogscan --fail-on error ap.log || echo \"serious events found\"",
            "code": LOGSCAN,
            "under": "Rules are checked in order and the first match wins, so more specific or more severe patterns go first. The `parse` generator streams line by line, so a 2 GB log never sits in memory. `main(argv, stdin, stdout)` takes its inputs as parameters (defaulting to the real ones), which is what makes the CLI testable without subprocesses, and the `if __name__ == \"__main__\"` guard keeps the demo from running when tests import the module. An installed tool would call `sys.exit(main())` from a `[project.scripts]` entry point.",
            "gotchas": [],
            "best": "Keep rules as data (and eventually in a config file the team can extend), stream input, make output modes explicit (table for humans, JSON for machines), choose exit codes deliberately (0 clean, 1 findings, 2 usage error from argparse), and ship the tool with tests from day one.",
        },
        {
            "title": "The test suite",
            "runner": "pytest",
            "filename": "tests/test_logscan.py",
            "files": {"logscan.py": plain(LOGSCAN), "pytest.ini": "[pytest]\npythonpath = .\n"},
            "args": ["-v"],
            "concept": "The tests exercise every layer through public functions: classification and detail extraction (`parse`), the exit-code contract, filters and the exact JSON shape, a parametrized severity table, and the usage-error path from argparse (`SystemExit` with code 2). Because `main` accepts streams, tests pass `StringIO` objects instead of files and capture output without touching the console.",
            "why": "Log formats drift with firmware versions. When a new firmware changes a message, a failing test with the sample line tells you exactly which rule to update, before the nightly pipeline silently stops catching crashes.",
            "syntax": "def run(*argv):\n    out = io.StringIO()\n    return main(list(argv), io.StringIO(SAMPLE), out), out.getvalue()",
            "code": LOGSCAN_TESTS.replace("import io\n", "import io  ## In-memory input and output\n", 1).replace("import json\n", "import json  ## Check the JSON output\n", 1).replace("\nimport pytest\n", "\nimport pytest  ## Test framework\n", 1).replace("from logscan import SAMPLE, build_parser, main, parse\n", "from logscan import SAMPLE, build_parser, main, parse  ## The tool under test\n", 1).replace('''def run(*argv):
    out = io.StringIO()
    code = main(list(argv), io.StringIO(SAMPLE), out)
    return code, out.getvalue()''', '''def run(*argv):  ## Helper: run the CLI on the sample, return (exit code, output)
    out = io.StringIO()  ## Capture stdout
    code = main(list(argv), io.StringIO(SAMPLE), out)  ## Same entry point the console script calls
    return code, out.getvalue()  ## Both results''').replace('''def test_parse_classifies_and_extracts_details():
    events = list(parse(io.StringIO(SAMPLE)))
    kinds = [e["kind"] for e in events]
    assert kinds == ["deauth", "radar", "deauth", "auth_fail", "fw_crash", "kernel_warn"]
    assert events[1]["ch"] == "52" and events[0]["reason"] == "3"''', '''def test_parse_classifies_and_extracts_details():  ## Unit test of the parser
    events = list(parse(io.StringIO(SAMPLE)))  ## Generator -> list
    kinds = [e["kind"] for e in events]  ## Classification only
    assert kinds == ["deauth", "radar", "deauth", "auth_fail", "fw_crash", "kernel_warn"]  ## Garbage line skipped, order kept
    assert events[1]["ch"] == "52" and events[0]["reason"] == "3"  ## Named groups captured''').replace('''def test_crash_fails_the_run():
    code, _ = run("--json")
    assert code == 1''', '''def test_crash_fails_the_run():  ## The CI contract
    code, _ = run("--json")  ## Default --fail-on critical
    assert code == 1  ## Firmware crash present''').replace('''def test_host_filter_and_json_shape():
    code, text = run("--host", "ap-lab-07", "--json")
    data = json.loads(text)
    assert code == 0
    assert data == {"by_kind": {"deauth": 2, "radar": 1}, "events": 3}''', '''def test_host_filter_and_json_shape():  ## Output contract for machines
    code, text = run("--host", "ap-lab-07", "--json")  ## One host
    data = json.loads(text)  ## Must be valid JSON
    assert code == 0  ## Nothing critical on this host
    assert data == {"by_kind": {"deauth": 2, "radar": 1}, "events": 3}  ## Exact shape''').replace('''@pytest.mark.parametrize("level,expected_rows", [("info", 5), ("warning", 4), ("critical", 1)])
def test_min_severity(level, expected_rows):
    _, text = run("--min-severity", level, "--fail-on", "critical")
    assert len(text.splitlines()) == expected_rows''', '''@pytest.mark.parametrize("level,expected_rows", [("info", 5), ("warning", 4), ("critical", 1)])  ## Table-driven
def test_min_severity(level, expected_rows):  ## One test, three cases
    _, text = run("--min-severity", level, "--fail-on", "critical")  ## Table output
    assert len(text.splitlines()) == expected_rows  ## One row per (host, kind)''').replace('''def test_invalid_choice_is_a_usage_error():
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--min-severity", "loud"])
    assert exc.value.code == 2''', '''def test_invalid_choice_is_a_usage_error():  ## argparse's error path
    with pytest.raises(SystemExit) as exc:  ## argparse exits instead of raising ValueError
        build_parser().parse_args(["--min-severity", "loud"])  ## Not a valid choice
    assert exc.value.code == 2  ## Usage errors exit with 2'''),
            "under": "`pytest.raises(SystemExit)` catches argparse's exit so the test can check the code (argparse also prints a usage message to stderr, which pytest captures). `pythonpath = .` in pytest.ini lets tests in `tests/` import `logscan.py` from the project root. Each test checks one contract, so a failure message points straight at what broke.",
            "gotchas": [],
            "best": "Test the parser, the CLI contract (exit codes, output shape) and error paths separately, keep sample log lines as fixtures (one per firmware version you support), and run the suite in CI on every change to the rules.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Extension: add a rule for `beacon loss` messages (severity warning) and report counts per AP for just that kind.",
            "solution": "Add a rule tuple; the rest of the tool picks it up because rules are data.",
            "solution_code": """import re
from collections import Counter

RULES = [("beacon_loss", re.compile(r"beacon loss", re.I), "warning")]
LOG = '''2026-10-12T03:00:01 ap-lab-07 kernel: wlan0: beacon loss from 3c:84:6a:12:34:80
2026-10-12T03:00:09 ap-lab-07 kernel: wlan0: Beacon loss from 3c:84:6a:12:34:80
2026-10-12T03:01:12 ap-lab-08 kernel: wlan1: beacon loss from 3c:84:6a:12:34:60'''
counts = Counter(line.split()[1] for line in LOG.splitlines() for kind, pat, sev in RULES if pat.search(line))
print(dict(counts))""",
        },
        {
            "level": "Medium",
            "prompt": "Extension: add a `--since` option (ISO timestamp) that drops events before it, comparing timestamps as datetimes, not strings.",
            "solution": "datetime.fromisoformat parses the log timestamps; compare objects.",
            "solution_code": """from datetime import datetime

events = [{"ts": "2026-10-12T01:14:07", "kind": "deauth"}, {"ts": "2026-10-12T02:31:59", "kind": "fw_crash"},
          {"ts": "2026-10-12T02:32:00", "kind": "kernel_warn"}]
since = datetime.fromisoformat("2026-10-12T02:00:00")
print([e["kind"] for e in events if datetime.fromisoformat(e["ts"]) >= since])""",
        },
        {
            "level": "Hard",
            "prompt": "Extension: correlate events: report any firmware crash on an AP that was preceded within 60 s by a DFS radar event on the same AP (a common real-world crash trigger).",
            "solution": "Group events by host, sort by time, and for each crash look back for a radar event inside the window.",
            "solution_code": """from datetime import datetime, timedelta

events = [("ap-lab-07", "2026-10-12T01:20:44", "radar"), ("ap-lab-07", "2026-10-12T01:21:20", "fw_crash"),
          ("ap-lab-08", "2026-10-12T02:31:59", "fw_crash"), ("ap-lab-08", "2026-10-12T01:00:00", "radar")]
window = timedelta(seconds=60)
for host, ts, kind in sorted(events, key=lambda e: (e[0], e[1])):
    if kind != "fw_crash":
        continue
    t = datetime.fromisoformat(ts)
    radar = [r for h, r, k in events if h == host and k == "radar" and timedelta(0) <= t - datetime.fromisoformat(r) <= window]
    print(host, ts, "after radar at " + radar[0] if radar else "no radar trigger")""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "Walk me through how you'd design a log analysis CLI for CI.", "a": "Streaming parser with ordered, data-driven classification rules; filters; human table and JSON outputs; deliberate exit codes (0 clean, 1 findings, 2 usage); a testable main(argv, stdin, stdout); tests per rule with real sample lines; packaged as a console script.", "follow": "How do you keep rules maintainable? (Data file with owners, tests per rule, a sample line for each.)"},
        {"level": "Intermediate", "q": "Why stream with a generator instead of reading the file?", "a": "Memory stays constant for multi-gigabyte logs, processing starts immediately, and the same function works for files, stdin pipes and sockets.", "follow": "What breaks streaming? (Sorting or correlating across the whole file; use bounded windows or a database.)"},
    ],
    "quiz": [
        {"q": "argparse invalid choice exits with code...", "options": ["0", "1", "2", "127"], "answer": 2, "why": "Usage error."},
        {"q": "Why does main() take stdin/stdout parameters?", "options": ["Speed", "Testability without subprocesses", "Required by argparse", "Unicode"], "answer": 1, "why": "Inject streams in tests."},
        {"q": "Rule order matters because...", "options": ["Regex is slow", "First match wins", "Python sorts dicts", "It doesn't"], "answer": 1, "why": "Specific/severe first."},
    ],
    "cards": [
        {"front": "CLI exit codes", "back": "0 clean, 1 findings, 2 usage error"},
        {"front": "Testable CLI", "back": "`main(argv=None, stdin=None, stdout=None)` + `if __name__ == '__main__'`"},
        {"front": "Streaming parse", "back": "Generator over lines; regex with named groups"},
    ],
}


HEALTH = '''import asyncio  ## Concurrency
import json  ## Machine-readable report
import re  ## Parsing show output
import socket  ## Reserve a dead port for the demo

import asyncssh  ## pip install asyncssh

from fake_device import start  ## Simulated controllers and switches (see supporting files)

COMMANDS = {"version": "show version", "ifaces": "show ip interface brief", "aps": "show ap summary"}  ## What a health check collects


def analyse(outputs):  ## Pure function: raw outputs -> (status, reasons)
    reasons = []  ## Problems found
    version = re.search(r"Version (\\S+)", outputs["version"])  ## Software version
    if not version or version[1] != "17.9.4a":  ## Policy: approved release
        reasons.append(f"version {version[1] if version else '?'} not approved")  ## Non-compliant
    for line in outputs["ifaces"].splitlines()[1:]:  ## Skip the header
        parts = line.split()  ## Columns
        if len(parts) >= 6 and parts[-2] == "down" and "administratively" not in line:  ## Down but not shut on purpose
            reasons.append(f"{parts[0]} down")  ## Unexpected outage
    stuck = [l.split()[0] for l in outputs["aps"].splitlines() if l.startswith("ap-") and not l.rstrip().endswith("Registered")]  ## APs not joined
    if stuck:  ## Some APs aren't registered
        reasons.append(f"APs not registered: {stuck}")  ## Name them
    return ("ok" if not reasons else "warn"), reasons  ## Verdict


async def check(name, port, password, sem, timeout=3.0):  ## One device, never raises
    async with sem:  ## Bound concurrent sessions
        try:  ## Classify failures
            async with asyncio.timeout(timeout):  ## Whole-device deadline
                async with asyncssh.connect("127.0.0.1", port=port, username="admin", password=password, known_hosts=None) as conn:  ## Simulator: no host key check
                    outputs = {k: (await conn.run(cmd)).stdout for k, cmd in COMMANDS.items()}  ## Run each command
            status, reasons = analyse(outputs)  ## Decide
        except asyncssh.PermissionDenied:  ## Credentials
            status, reasons = "fail", ["authentication failed"]  ## Inventory/vault problem
        except TimeoutError:  ## Too slow
            status, reasons = "fail", ["timeout"]  ## Device hung or overloaded
        except OSError as e:  ## Refused / unreachable
            status, reasons = "fail", [f"unreachable ({type(e).__name__})"]  ## Device down
    return {"device": name, "status": status, "reasons": reasons}  ## Report row


async def run_all(inventory, limit=10):  ## Whole fleet
    sem = asyncio.Semaphore(limit)  ## Shared limiter
    return await asyncio.gather(*(check(n, p, pw, sem) for n, (p, pw) in inventory.items()))  ## Input order preserved


dead = socket.socket()  ## A port with nothing listening
dead.bind(("127.0.0.1", 0))  ## Reserved, not listening
INVENTORY = {"wlc-1": (start("wlc-1", 1), "lab123"), "wlc-2": (start("wlc-2", 2), "lab123"),  ## Healthy controllers (with one AP downloading)
             "wlc-3": (start("wlc-3", 3), "old-pass"), "wlc-4": (dead.getsockname()[1], "lab123")}  ## Bad credentials; down

if __name__ == "__main__":  ## Demo
    rows = asyncio.run(run_all(INVENTORY, limit=2))  ## Check the fleet
    for r in rows:  ## Human-readable
        print(f"{r['device']:<6} {r['status']:<5} {'; '.join(r['reasons'])}")  ## One line per device
    summary = {s: sum(r["status"] == s for r in rows) for s in ("ok", "warn", "fail")}  ## Totals
    print(json.dumps(summary))  ## For dashboards
    print("exit code:", 1 if summary["fail"] else 0)  ## Fail CI only on unreachable/auth problems'''

M_10_2 = {
    "id": "10.2",
    "title": "Async Multi-Device Health Checker",
    "hours": 5,
    "summary": "Capstone: check a fleet of controllers/switches concurrently over SSH before a test run: version compliance, unexpected interface outages, unregistered APs, with failures classified per device; then detect what changed since the last run.",
    "concepts": [
        {
            "title": "The checker: collect concurrently, analyse purely, classify failures",
            "files": sim("fake_device.py"),
            "local_only": ASYNCSSH,
            "filename": "healthcheck.py",
            "concept": "**Brief:** before every nightly run, verify the lab: each controller runs the approved release, no interface is unexpectedly down, all APs are registered. Devices are checked concurrently over SSH with a session limit and a per-device timeout; analysis is a **pure function** of the collected outputs, so it's testable without devices; and every device ends with a status (ok / warn / fail) and reasons, never an exception. **Skills used:** asyncssh, Semaphore, asyncio.timeout (7.5), parsing (2.x, 7.9), JSON, exit codes.",
            "why": "A nightly run that starts while an AP is still downloading firmware, or with a controller on the wrong release, wastes the whole night and produces misleading failures. A 10-second pre-flight catches it.",
            "syntax": "status, reasons = analyse(outputs)   # pure\nrows = await asyncio.gather(*(check(...) for ...))",
            "code": HEALTH,
            "under": "Splitting I/O (`check`) from decisions (`analyse`) is the key design choice: the fiddly part, parsing and policy, can be unit-tested with captured outputs, while the I/O part only needs a few integration tests. Administratively-down interfaces are excluded on purpose: they're configured that way and alerting on them would train people to ignore the report. Only `fail` statuses fail the CI step; `warn` is reported but lets the run proceed.",
            "gotchas": [],
            "best": "Separate collection from analysis, bound concurrency, time out per device, classify every failure, keep policy (approved versions, exclusions) as data, and make the exit-code policy explicit (which statuses block the run).",
        },
        {
            "title": "What changed since last time",
            "concept": "A health report is most useful as a **diff**: what's newly broken, what recovered, what's still broken. Store each run's results as JSON, and compare the new results with the previous ones by device and reason. New problems go at the top of the notification; long-standing ones are summarised.",
            "why": "If wlc-3's password has been wrong for a week, repeating it every night is noise; the AP that stopped registering an hour ago is the news. Change detection is what keeps people reading the report.",
            "syntax": "new = now_set - before_set\nresolved = before_set - now_set\nstill = now_set & before_set",
            "code": """import json  ## Results are stored as JSON between runs

PREVIOUS = json.loads('[{"device": "wlc-1", "status": "ok", "reasons": []}, {"device": "wlc-2", "status": "warn", "reasons": ["APs not registered: [\\'ap-lab-09\\']"]}, {"device": "wlc-3", "status": "fail", "reasons": ["authentication failed"]}]')  ## Last night's report
CURRENT = [  ## Tonight's report (from the checker)
    {"device": "wlc-1", "status": "warn", "reasons": ["Gi0/0/0 down"]},  ## Newly broken
    {"device": "wlc-2", "status": "ok", "reasons": []},  ## Recovered
    {"device": "wlc-3", "status": "fail", "reasons": ["authentication failed"]},  ## Still broken
    {"device": "wlc-4", "status": "fail", "reasons": ["unreachable (ConnectionRefusedError)"]},  ## New device, broken
]  ## End of current


def problems(report):  ## Set of (device, reason) pairs
    return {(row["device"], reason) for row in report for reason in row["reasons"]}  ## Flatten


before, now = problems(PREVIOUS), problems(CURRENT)  ## Two sets
for label, items in (("NEW", now - before), ("RESOLVED", before - now), ("STILL BROKEN", now & before)):  ## Set algebra
    for device, reason in sorted(items):  ## Stable order
        print(f"{label:<13} {device}: {reason}")  ## Notification lines""",
            "under": "Representing problems as `(device, reason)` tuples makes the comparison three set operations. Reasons must be stable strings for this to work (no timestamps or counters inside them), the same normalisation idea as failure signatures in 8.11.",
            "gotchas": [],
            "best": "Persist every run's results, compare against the previous run (or a longer window), notify on NEW and RESOLVED, summarise STILL BROKEN, and keep reasons free of volatile details.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Unit-test `analyse()` without any device: feed it captured outputs for a healthy controller and one with an unexpected down interface.",
            "solution": "Because analyse is pure, a test is just inputs and expected outputs.",
            "solution_code": """import re


def analyse(outputs):
    reasons = []
    for line in outputs["ifaces"].splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 6 and parts[-2] == "down" and "administratively" not in line:
            reasons.append(f"{parts[0]} down")
    return ("ok" if not reasons else "warn"), reasons


HEADER = "Interface  IP-Address  OK? Method Status Protocol"
healthy = {"ifaces": HEADER + "\\nGi0/0/0 10.0.0.1 YES NVRAM up up\\nGi0/0/1 unassigned YES unset administratively down down"}
broken = {"ifaces": HEADER + "\\nGi0/0/0 10.0.0.1 YES NVRAM down down"}
assert analyse(healthy) == ("ok", [])
assert analyse(broken) == ("warn", ["Gi0/0/0 down"])
print("analyse() tests passed")""",
        },
        {
            "level": "Medium",
            "prompt": "Add a retry pass: devices that failed with `timeout` or `unreachable` are re-checked once after a delay, and the final report notes which ones recovered on retry.",
            "solution": "Filter retryable failures, re-run only those, and merge results with a flag.",
            "solution_code": """import asyncio

ATTEMPTS = {"wlc-4": 0}


async def check(name):
    if name == "wlc-4":
        ATTEMPTS[name] += 1
        if ATTEMPTS[name] == 1:
            return {"device": name, "status": "fail", "reasons": ["timeout"]}
    return {"device": name, "status": "ok", "reasons": []}


async def main(devices):
    rows = {r["device"]: r for r in await asyncio.gather(*(check(d) for d in devices))}
    retry = [d for d, r in rows.items() if r["status"] == "fail" and any(x.startswith(("timeout", "unreachable")) for x in r["reasons"])]
    await asyncio.sleep(0.01)
    for r in await asyncio.gather(*(check(d) for d in retry)):
        r["recovered_on_retry"] = r["status"] != "fail"
        rows[r["device"]] = r
    return list(rows.values())

print(asyncio.run(main(["wlc-1", "wlc-4"])))""",
        },
        {
            "level": "Hard",
            "prompt": "Render the report as a Slack Block Kit payload: header with counts, one section per NEW problem, and a context line with still-broken totals.",
            "solution": "Reuse the payload pattern from 6.6, driven by the change-detection sets.",
            "solution_code": """import json

new = [("wlc-1", "Gi0/0/0 down"), ("wlc-4", "unreachable (ConnectionRefusedError)")]
still = [("wlc-3", "authentication failed")]
payload = {
    "text": f"Lab health: {len(new)} new problem(s)",
    "blocks": [{"type": "header", "text": {"type": "plain_text", "text": f"Lab health: {len(new)} new, {len(still)} ongoing"}}]
    + [{"type": "section", "text": {"type": "mrkdwn", "text": f"*{d}*: {r}"}} for d, r in new]
    + [{"type": "context", "elements": [{"type": "mrkdwn", "text": f"Still broken: {', '.join(d for d, _ in still)}"}]}],
}
print(json.dumps(payload, indent=1)[:400])""",
        },
    ],
    "interview": [
        {"level": "Advanced", "q": "Design a pre-flight health check for a 300-AP lab.", "a": "Inventory-driven async collection (asyncssh/APIs) with bounded concurrency and per-device timeouts; pure analysis functions with policy as data (approved versions, expected states, exclusions); per-device status and reasons; persisted results with change detection; notifications on NEW/RESOLVED; CI exit policy blocking runs only on critical failures.", "follow": "How do you test it? (Unit tests on analyse with captured outputs; a few integration tests against simulators.)"},
        {"level": "Intermediate", "q": "Why should a fleet checker never raise per device?", "a": "One bad device would abort or hide the results for the others. Each task catches and classifies its own failures, so the report is always complete.", "follow": "Which failures do you retry? (Transient ones: timeouts and connection refused, not auth failures.)"},
    ],
    "quiz": [
        {"q": "Which part of the checker should be pure?", "options": ["SSH connect", "analyse(outputs)", "asyncio.gather", "The semaphore"], "answer": 1, "why": "Testable without devices."},
        {"q": "Administratively down interfaces are...", "options": ["Always alerts", "Excluded: configured on purpose", "Treated as up", "Errors"], "answer": 1, "why": "Avoid noise."},
        {"q": "Newly broken problems = ", "options": ["before - now", "now - before", "now & before", "now | before"], "answer": 1, "why": "Set difference."},
    ],
    "cards": [
        {"front": "Health check structure", "back": "collect (async I/O) → analyse (pure) → classify → report → diff"},
        {"front": "Change detection", "back": "NEW = now − before; RESOLVED = before − now; STILL = now ∩ before"},
        {"front": "Exit policy", "back": "Fail CI on fail statuses; report warn without blocking"},
    ],
}


FW_FILES = {
    "lab.py": LAB_PY,
    "pytest.ini": """[pytest]
testpaths = tests
pythonpath = .
addopts = --strict-markers
xfail_strict = true
junit_family = xunit1
markers =
    smoke: fast checks run on every change
    rf: needs RF path (attenuator, traffic)
    band(name): radio band the test needs
""",
    "framework/__init__.py": "",
    "framework/bench.py": '''"""Bench facade: one object that owns the instruments for a test session."""
from dataclasses import dataclass, field

from lab import FakeAP, FakeStation, throughput_mbps

BENCHES = {
    "lab-07": {"bands": ("2G", "5G", "6G"), "attenuator": True},
    "lab-12": {"bands": ("2G", "5G"), "attenuator": False},
}


@dataclass
class Bench:
    name: str
    bands: tuple
    has_attenuator: bool
    ap: FakeAP = field(init=False)
    atten_db: float = 0.0

    def __post_init__(self):
        self.ap = FakeAP(f"{self.name}-ap", bands=self.bands)

    @classmethod
    def from_name(cls, name):
        cfg = BENCHES[name]
        return cls(name, cfg["bands"], cfg["attenuator"])

    def set_attenuation(self, db):
        if not self.has_attenuator:
            raise RuntimeError(f"{self.name} has no attenuator")
        self.atten_db = db

    def associate(self, mac="02:00:00:00:01:00"):
        sta = FakeStation(mac)
        sta.associate(self.ap, rssi=-50 - round(self.atten_db))
        return sta

    def throughput(self, band, width, sta):
        return throughput_mbps(band, width, rssi=sta.rssi)

    def reset(self):
        self.ap.reboot()
        self.atten_db = 0.0
''',
    "framework/kpi.py": '''"""KPI table and verdicts, kept as data."""
KPI_MBPS = {("5G", 80, 0): 850, ("5G", 80, 20): 400, ("6G", 160, 0): 2200, ("6G", 160, 20): 1000, ("2G", 40, 0): 280}


def floor(band, width, atten):
    return KPI_MBPS[(band, width, atten)]
''',
    "tests/test_config.py": '''import pytest


@pytest.mark.smoke
def test_ap_has_bench_bands(bench):
    assert bench.ap.bands == set(bench.bands)


@pytest.mark.smoke
@pytest.mark.band("6G")
def test_6g_channel_37(bench):
    bench.ap.set_channel("6G", 37)
    assert bench.ap.channels["6G"] == 37
''',
}

FW_CONFTEST = '''import pytest  ## Hooks and fixtures

from framework.bench import BENCHES, Bench  ## The facade and bench inventory


def pytest_addoption(parser):  ## Command-line options (root conftest only)
    parser.addoption("--bench", default="lab-07", choices=sorted(BENCHES), help="bench to run on")  ## Validated choice


def pytest_report_header(config):  ## Shown at the top of every run
    return f"bench: {config.getoption('bench')} {BENCHES[config.getoption('bench')]}"  ## Self-describing logs


def pytest_collection_modifyitems(config, items):  ## Skip what the bench can't do, before running anything
    bench = BENCHES[config.getoption("bench")]  ## Capabilities
    for item in items:  ## Every collected test
        band = item.get_closest_marker("band")  ## @pytest.mark.band("6G")
        if band and band.args[0] not in bench["bands"]:  ## Bench lacks the radio
            item.add_marker(pytest.mark.skip(reason=f"bench has no {band.args[0]} radio"))  ## Clear reason
        if item.get_closest_marker("rf") and not bench["attenuator"]:  ## RF tests need an attenuator
            item.add_marker(pytest.mark.skip(reason="bench has no attenuator"))  ## Clear reason


@pytest.fixture(scope="session")  ## One bench object for the whole run
def bench(pytestconfig):  ## Built from the --bench option
    b = Bench.from_name(pytestconfig.getoption("bench"))  ## Facade over instruments
    yield b  ## Tests run here
    b.reset()  ## Always leave the bench clean


@pytest.fixture(autouse=True)  ## Every test
def clean_attenuation(bench):  ## Isolation between tests
    yield  ## Test body
    if bench.has_attenuator:  ## Only where it exists
        bench.set_attenuation(0)  ## Back to a known state


@pytest.fixture  ## Function scope
def sta(bench):  ## An associated client for throughput tests
    return bench.associate()  ## Uses the current attenuation'''

FW_TEST_RVR = '''import pytest  ## Test framework

from framework.kpi import floor  ## KPIs come from data, not the test

POINTS = [("5G", 80, 0), ("5G", 80, 20), ("6G", 160, 0), ("6G", 160, 20), ("2G", 40, 0)]  ## (band, width, attenuation)


@pytest.mark.rf  ## Needs an attenuator
@pytest.mark.parametrize("band,width,atten", [pytest.param(*p, marks=pytest.mark.band(p[0]), id=f"{p[0]}-{p[1]}MHz-{p[2]}dB") for p in POINTS])  ## Each point marked with its band
def test_throughput_meets_kpi(bench, record_property, band, width, atten):  ## One item per point
    bench.set_attenuation(atten)  ## Distance
    sta = bench.associate()  ## Client at that distance
    mbps = bench.throughput(band, width, sta)  ## Measurement (simulated)
    record_property("throughput_mbps", mbps)  ## Into JUnit XML
    kpi = floor(band, width, atten)  ## Required value
    assert mbps >= kpi, f"{band}/{width} at {atten} dB: {mbps} Mbps < {kpi}"  ## Clear failure message'''

M_10_3 = {
    "id": "10.3",
    "title": "pytest Wi-Fi Test Framework",
    "hours": 10,
    "summary": "Capstone: a small but complete pytest framework: bench selection by option, capability-based skipping via markers and hooks, session fixtures with cleanup, KPIs as data, JUnit properties; run against two bench profiles.",
    "concepts": [
        {
            "title": "The framework core: conftest.py",
            "runner": "pytest",
            "filename": "conftest.py",
            "files": {**FW_FILES, "tests/test_rvr.py": plain(FW_TEST_RVR)},
            "args": ["-v", "-rs", "--bench", "lab-07"],
            "concept": "**Brief:** one test suite must run on any bench, doing what each bench can and skipping (with reasons) what it can't. The root `conftest.py` is the framework's core: a validated `--bench` option, a report header naming the bench, a **collection hook** that skips tests whose `band`/`rf` markers the bench can't satisfy, a session-scoped `bench` fixture (facade from 9.3) with cleanup, an autouse fixture restoring attenuation after every test, and a `sta` fixture. Supporting files hold the facade, KPI table, pytest.ini with registered markers, and two test modules. **Skills used:** everything in Phase 5, plus 9.3/9.4 design.",
            "why": "This is the shape of real lab frameworks. Getting the skeleton right (options, capability-aware collection, fixtures with guaranteed cleanup, KPIs as data) is what lets dozens of engineers add tests without breaking each other's benches.",
            "syntax": "pytest --bench lab-07 -m smoke\npytest --bench lab-12 -m 'rf' -rs\npytest --junitxml=results/lab-07.xml",
            "code": FW_CONFTEST,
            "under": "Skipping at collection time (in `pytest_collection_modifyitems`) means unsupported tests never acquire hardware or run setup, and the skip reason appears in the summary (`-rs`). The session `bench` fixture's code after `yield` runs once at the end; the autouse fixture's runs after every test, so one test's attenuation can't leak into the next. One 6 GHz point fails its KPI here: the simulated throughput at 20 dB on 6 GHz is below the floor, which is exactly the kind of finding the framework exists to surface.",
            "gotchas": [],
            "best": "Root conftest for options/hooks/core fixtures, capabilities in a bench inventory, markers registered with --strict-markers, skip with reasons at collection, session fixtures for instruments with teardown resets, autouse fixtures for per-test isolation, KPIs in data, and record_property for every measurement.",
        },
        {
            "title": "Same suite, different bench",
            "runner": "pytest",
            "filename": "tests/test_rvr.py",
            "files": {**FW_FILES, "conftest.py": plain(FW_CONFTEST)},
            "args": ["-q", "-rs", "--bench", "lab-12"],
            "concept": "The RvR test module is pure intent: points as data, each parametrized case marked with its band, measurement through the facade, KPI from the table, value recorded for reports. Run against `lab-12` (no 6 GHz radio, no attenuator), the framework skips what can't run and says why, without a single `if bench == ...` in any test.",
            "why": "Tests that encode bench differences in `if` statements rot quickly. Declaring needs with markers and letting the framework decide keeps tests readable and makes adding a bench a one-line inventory change.",
            "syntax": "pytest.param(*point, marks=pytest.mark.band(band), id=...)\n@pytest.mark.rf",
            "code": FW_TEST_RVR,
            "under": "`pytest.param(..., marks=...)` attaches a marker to one parametrized case, which the collection hook then reads. With `-q -rs` the output is a compact progress line plus one summary line per skip reason (identical reasons are grouped with a count).",
            "gotchas": [],
            "best": "Write tests as intent plus data, declare requirements with markers, let one hook enforce capabilities, and run the same suite on every bench profile in CI (simulators included) to keep it honest.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Add a bench `lab-15` with only 6 GHz and an attenuator to the inventory, and list which of the five RvR points would run on it.",
            "solution": "The capability rule is just a membership check on the band.",
            "solution_code": """BENCHES = {"lab-07": {"bands": ("2G", "5G", "6G"), "attenuator": True},
           "lab-12": {"bands": ("2G", "5G"), "attenuator": False},
           "lab-15": {"bands": ("6G",), "attenuator": True}}
POINTS = [("5G", 80, 0), ("5G", 80, 20), ("6G", 160, 0), ("6G", 160, 20), ("2G", 40, 0)]
b = BENCHES["lab-15"]
print([p for p in POINTS if p[0] in b["bands"] and b["attenuator"]])""",
        },
        {
            "level": "Medium",
            "runner": "pytest",
            "files": {**FW_FILES, "conftest.py": plain(FW_CONFTEST)},
            "args": ["-q", "-m", "smoke", "--bench", "lab-12", "-rs"],
            "filename": "tests/test_extra.py",
            "prompt": "Add a smoke test that every band on the bench accepts a default channel, and run only smoke tests on lab-12.",
            "solution": "Loop over the bench's bands inside one smoke test; `-m smoke` selects it plus the config smoke tests.",
            "solution_code": """import pytest

DEFAULT = {"2G": 6, "5G": 36, "6G": 37}


@pytest.mark.smoke
def test_default_channels(bench):
    for band in bench.bands:
        bench.ap.set_channel(band, DEFAULT[band])
    assert set(bench.ap.channels) == set(bench.bands)""",
        },
        {
            "level": "Hard",
            "runner": "pytest",
            "files": {**FW_FILES, "conftest.py": plain(FW_CONFTEST) + '''

import sqlite3

RESULTS = sqlite3.connect(":memory:")
RESULTS.execute("CREATE TABLE results (test TEXT, outcome TEXT, mbps REAL)")


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    if report.when == "call":
        mbps = dict(report.user_properties).get("throughput_mbps")
        RESULTS.execute("INSERT INTO results VALUES (?, ?, ?)", (item.name, report.outcome, mbps))
    return report


def pytest_terminal_summary(terminalreporter):
    terminalreporter.write_sep("-", "stored results")
    for row in RESULTS.execute("SELECT outcome, COUNT(*), ROUND(AVG(mbps), 1) FROM results GROUP BY outcome ORDER BY outcome"):
        terminalreporter.write_line(str(row))
'''},
            "args": ["-q", "--bench", "lab-07", "--tb=no"],
            "filename": "tests/test_rvr.py",
            "prompt": "Store every call result (test, outcome, recorded throughput) in a SQLite table via a makereport hook, and print an aggregate in the terminal summary.",
            "solution": "`report.user_properties` holds what record_property stored; a wrapper hook writes a row per call phase, and pytest_terminal_summary queries it.",
            "solution_code": plain(FW_TEST_RVR),
        },
    ],
    "interview": [
        {"level": "Advanced", "q": "Describe the architecture of a pytest-based Wi-Fi framework you'd build.", "a": "Root conftest with bench option, report header and a capability-aware collection hook; bench inventory as data; facade over instrument drivers (Protocols + registry, simulators for CI); session fixtures with teardown resets, autouse isolation fixtures; markers (smoke, rf, band) registered strictly; KPIs as data; record_property + JUnit/Allure + results DB; same suite on every bench profile.", "follow": "Where do retries live? (Drivers, for transport errors; never around assertions.)"},
        {"level": "Intermediate", "q": "Why skip in pytest_collection_modifyitems instead of inside tests?", "a": "Tests don't need bench-specific ifs, no setup or hardware is acquired for tests that can't run, and skip reasons are consistent and visible in reports.", "follow": "How would you route tests to capable benches automatically? (Scheduler using the same markers + inventory, 8.10.)"},
    ],
    "quiz": [
        {"q": "Attach a marker to one parametrized case:", "options": ["@pytest.mark on the function", "pytest.param(..., marks=...)", "ids=", "conftest"], "answer": 1, "why": "Per-case marks."},
        {"q": "Session fixture teardown runs...", "options": ["After each test", "Once at the end of the run", "Never", "Before each test"], "answer": 1, "why": "Scope = session."},
        {"q": "Show skip reasons in the summary:", "options": ["-v", "-rs", "-x", "-s"], "answer": 1, "why": "-r with s."},
    ],
    "cards": [
        {"front": "Capability skip", "back": "pytest_collection_modifyitems + markers + bench inventory"},
        {"front": "Per-test isolation", "back": "autouse fixture resetting state after yield"},
        {"front": "Results to DB", "back": "makereport wrapper → report.user_properties → INSERT"},
    ],
}


RVR_CAPSTONE = '''import json  ## Results file
import statistics  ## Median per point
import time  ## Settle/sample delays

import matplotlib  ## pip install matplotlib

matplotlib.use("Agg")  ## Headless
import matplotlib.pyplot as plt  ## Chart
import requests  ## Instrument APIs

import fake_attenuator  ## Simulated attenuator
import fake_lanforge  ## Simulated traffic generator

ATT, LF = fake_attenuator.start(), fake_lanforge.start()  ## From the bench config in real life
PLAN = {"points": list(range(0, 61, 6)), "bands": ["5G", "6G"], "iterations": 3, "settle_s": 0.01, "samples": 3}  ## The test plan as data
s = requests.Session()  ## Shared HTTP session


def set_att(db):  ## Set and verify
    assert s.get(f"{ATT}/SETATT={db:g}", timeout=5).text == "1", f"attenuator rejected {db}"  ## Reply check
    return float(s.get(f"{ATT}/ATT?", timeout=5).text)  ## Read back


def measure(band, samples):  ## One traffic run: median of a few samples
    cx = f"rvr-{band}"  ## Cross-connect name
    s.post(f"{LF}/cli-json/add_cx", json={"alias": cx, "band": band}, timeout=5)  ## Define
    s.post(f"{LF}/cli-json/set_cx_state", json={"cx_name": cx, "cx_state": "RUNNING"}, timeout=5)  ## Start
    try:  ## Always stop
        vals = []  ## Samples
        for _ in range(samples):  ## Sampling loop
            time.sleep(0.005)  ## Interval
            vals.append(s.get(f"{LF}/cx/{cx}", timeout=5).json()[cx]["bps rx b"] / 1e6)  ## Mbps
        return statistics.median(vals)  ## Robust value
    finally:  ## Cleanup
        s.post(f"{LF}/cli-json/set_cx_state", json={"cx_name": cx, "cx_state": "STOPPED"}, timeout=5)  ## Stop


def sweep(plan):  ## The whole run -> list of result rows
    rows = []  ## Results
    try:  ## Guarantee the reset
        for db in plan["points"]:  ## Each distance
            applied = set_att(db)  ## Verified attenuation
            time.sleep(plan["settle_s"])  ## Settle
            for band in plan["bands"]:  ## Each band
                runs = [measure(band, plan["samples"]) for _ in range(plan["iterations"])]  ## Repeat
                rows.append({"atten_db": applied, "band": band, "median_mbps": round(statistics.median(runs), 1), "min_mbps": round(min(runs), 1)})  ## Median and worst
    finally:  ## Bench back to safe state
        set_att(0)  ## Reset
    return rows  ## Raw results


rows = sweep(PLAN)  ## Run it
meta = {"dut": "ap-lab-07", "firmware": "7.4.2-b003", "bench": "lab-07", **PLAN}  ## Context saved with the data
with open("rvr_results.json", "w") as f:  ## Raw data first
    json.dump({"meta": meta, "rows": rows}, f, indent=1)  ## Everything needed to re-judge later

fig, ax = plt.subplots(figsize=(7, 3.8))  ## Chart
for band, marker in zip(PLAN["bands"], "os"):  ## One series per band
    pts = [r for r in rows if r["band"] == band]  ## This band
    ax.plot([r["atten_db"] for r in pts], [r["median_mbps"] for r in pts], marker=marker, label=f"{band} median")  ## Median curve
    ax.fill_between([r["atten_db"] for r in pts], [r["min_mbps"] for r in pts], [r["median_mbps"] for r in pts], alpha=0.15)  ## Spread down to the worst run
ax.set(xlabel="Attenuation (dB)", ylabel="Throughput (Mbps)", title=f"RvR {meta['dut']} fw {meta['firmware']} ({PLAN['iterations']} iterations)")  ## Labels with context
ax.grid(alpha=0.3)  ## Grid
ax.legend()  ## Legend
fig.savefig("rvr_capstone.png", dpi=90, bbox_inches="tight")  ## For the report
plt.close(fig)  ## Free memory
print(len(rows), "rows saved; bench reset to", s.get(f"{ATT}/ATT?", timeout=5).text, "dB")  ## Confirmation'''

REPORT_CODE = '''import base64  ## Embed the chart in the HTML
import json  ## Read results
from pathlib import Path  ## Files

from jinja2 import Environment, StrictUndefined  ## pip install jinja2
from playwright.sync_api import sync_playwright  ## For the screenshot preview

CURRENT = {"meta": {"dut": "ap-lab-07", "firmware": "7.4.2-b003"}, "rows": [  ## Tonight (normally json.load from the sweep)
    {"atten_db": 0, "band": "5G", "median_mbps": 939.4}, {"atten_db": 30, "band": "5G", "median_mbps": 666.0}, {"atten_db": 42, "band": "5G", "median_mbps": 135.9},  ## 5 GHz
    {"atten_db": 0, "band": "6G", "median_mbps": 2410.0}, {"atten_db": 30, "band": "6G", "median_mbps": 1205.0}, {"atten_db": 42, "band": "6G", "median_mbps": 156.6}]}  ## 6 GHz
BASELINE = {"meta": {"firmware": "7.4.1"}, "rows": [  ## Last release's results for the same plan
    {"atten_db": 0, "band": "5G", "median_mbps": 941.0}, {"atten_db": 30, "band": "5G", "median_mbps": 702.5}, {"atten_db": 42, "band": "5G", "median_mbps": 171.2},  ## 5 GHz
    {"atten_db": 0, "band": "6G", "median_mbps": 2405.1}, {"atten_db": 30, "band": "6G", "median_mbps": 1198.3}, {"atten_db": 42, "band": "6G", "median_mbps": 160.0}]}  ## 6 GHz
KPI = {("5G", 0): 900, ("5G", 30): 600, ("5G", 42): 150, ("6G", 0): 2300, ("6G", 30): 1100, ("6G", 42): 120}  ## Floors
TOLERANCE = 0.05  ## A drop of more than 5% vs baseline is a regression

base = {(r["band"], r["atten_db"]): r["median_mbps"] for r in BASELINE["rows"]}  ## Lookup by point
table = []  ## One row per point for the report
for r in CURRENT["rows"]:  ## Judge every point two ways
    key = (r["band"], r["atten_db"])  ## Point id
    delta = (r["median_mbps"] - base[key]) / base[key]  ## Relative change vs baseline
    table.append({**r, "kpi": KPI[key], "baseline": base[key], "delta_pct": round(delta * 100, 1),  ## Numbers
                  "kpi_ok": r["median_mbps"] >= KPI[key], "regression": delta < -TOLERANCE})  ## Two independent verdicts

TEMPLATE = """<html><head><style>body{font-family:sans-serif;margin:20px} td,th{border:1px solid #ccc;padding:3px 8px}
table{border-collapse:collapse} .bad{background:#fde2e1} .warn{background:#fff4d6}</style></head><body>
<h2>RvR {{ meta.dut }}: fw {{ meta.firmware }} vs {{ baseline_fw }}</h2>
<p>{{ fails }} KPI failure(s), {{ regressions }} regression(s) beyond {{ tol }}%</p>
<table><tr><th>Band</th><th>dB</th><th>Mbps</th><th>KPI</th><th>Baseline</th><th>&Delta;%</th></tr>
{% for r in rows %}<tr class="{{ 'bad' if not r.kpi_ok else 'warn' if r.regression else '' }}"><td>{{ r.band }}</td><td>{{ r.atten_db }}</td>
<td>{{ r.median_mbps }}</td><td>{{ r.kpi }}</td><td>{{ r.baseline }}</td><td>{{ '%+.1f'|format(r.delta_pct) }}</td></tr>{% endfor %}
</table></body></html>"""  ## Report layout (Jinja2, autoescaped)

env = Environment(autoescape=True, undefined=StrictUndefined)  ## Safe HTML, strict variables
html = env.from_string(TEMPLATE).render(meta=CURRENT["meta"], baseline_fw=BASELINE["meta"]["firmware"], rows=table, tol=int(TOLERANCE * 100),  ## Fill it
                                        fails=sum(not r["kpi_ok"] for r in table), regressions=sum(r["regression"] for r in table))  ## Counts
Path("rvr_report.html").write_text(html)  ## The artifact people open

with sync_playwright() as p:  ## Preview image for chat/email
    page = p.chromium.launch().new_page(viewport={"width": 560, "height": 300})  ## Small viewport
    page.set_content(html)  ## Render the report
    page.screenshot(path="rvr_report.png")  ## Shown below

for r in table:  ## Console summary
    flags = ("KPI FAIL " if not r["kpi_ok"] else "") + ("REGRESSION" if r["regression"] else "")  ## What's wrong, if anything
    print(f"{r['band']} {r['atten_db']:>2} dB {r['median_mbps']:>7} Mbps ({r['delta_pct']:+.1f}% vs baseline) {flags}")  ## One line per point'''

M_10_4 = {
    "id": "10.4",
    "title": "Rate-vs-Range Automation",
    "hours": 6,
    "summary": "Capstone: a production-style RvR run (test plan as data, verified attenuation, repeated iterations with median and worst case, raw JSON with metadata, chart with spread) and a report that judges KPIs and regressions against a baseline build.",
    "concepts": [
        {
            "title": "The sweep engine",
            "files": sim("fake_attenuator.py", "fake_lanforge.py"),
            "local_only": RVR,
            "capture": "rvr_capstone.png",
            "image_alt": "Rate-versus-range chart for 5 and 6 GHz with shaded spread between the median and worst of three iterations",
            "filename": "rvr_sweep.py",
            "concept": "**Brief:** extend 7.18 into something a lab would run nightly. The plan (points, bands, iterations, settle time, samples) is data; each point is measured several times and stored as median and minimum; raw results are written with metadata (DUT, firmware, bench, plan) before any judging; the chart shows the median with the spread down to the worst run; and the attenuator is reset whatever happens. **Skills used:** 6.5, 7.16-7.18, statistics, JSON.",
            "why": "Single measurements on real RF are noisy; reporting one number per point invites false alarms and missed regressions. Iterations, medians and a visible spread make the result trustworthy, and saved metadata makes it comparable months later.",
            "syntax": "PLAN = {\"points\": [...], \"bands\": [...], \"iterations\": 3}\nrows = sweep(PLAN)\njson.dump({\"meta\": meta, \"rows\": rows}, f)",
            "code": RVR_CAPSTONE,
            "under": "`fill_between` shades the area between two curves, here between the worst and the median of the iterations, so instability at a point is visible at a glance. The sweep's `finally` resets the attenuator even if a measurement raises. On real hardware the settle time and samples would be seconds and tens of samples; the structure is identical.",
            "gotchas": [],
            "best": "Plan as data (versioned), repeated measurements with median and min, metadata saved alongside results, raw data written before verdicts, cleanup in finally, and charts that show variability, not just a line.",
        },
        {
            "title": "The report: KPIs, baseline comparison, HTML",
            "local_only": REPORT,
            "capture": "rvr_report.png",
            "image_alt": "HTML report table comparing tonight's RvR results with the baseline firmware, failing and regressed rows highlighted",
            "filename": "rvr_report.py",
            "concept": "A result can be bad in two independent ways: below the **KPI** (absolute floor) or **regressed** against the baseline build (relative drop beyond a tolerance). The report computes both per point, renders an autoescaped Jinja2 HTML table with rows highlighted by verdict (6.10), and writes a PNG preview with Playwright for chats and emails. The console prints the same facts.",
            "why": "A point can pass its KPI and still be a 9% regression from last release (5 GHz at 30 dB here), which is exactly what firmware teams need to see before a release. KPIs alone miss slow degradation; baselines alone miss absolute requirements.",
            "syntax": "delta = (now - base) / base\nregression = delta < -TOLERANCE\nkpi_ok = now >= KPI[point]",
            "code": REPORT_CODE,
            "under": "The comparison is keyed by (band, attenuation), so the baseline must come from the same plan; storing the plan in each results file (previous concept) is what makes that check possible. Highlight priority is KPI failure (red) over regression (amber). The PNG below is the actual page Chromium rendered from the HTML this code wrote.",
            "gotchas": [],
            "best": "Judge against both absolute KPIs and a baseline with a tolerance based on measured run-to-run variance, key comparisons by plan point, show deltas with sign, and keep the HTML self-contained so it can be emailed or archived.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "From RvR rows, compute each band's 'range' at 100 Mbps (largest attenuation still ≥ 100 Mbps) and compare it with the baseline's range.",
            "solution": "Max over filtered rows per band; differences in dB are an intuitive headline metric.",
            "solution_code": """now = {"5G": [(36, 380.2), (42, 135.9), (48, 46.0)], "6G": [(36, 505.0), (42, 156.6), (48, 41.2)]}
base = {"5G": [(36, 401.3), (42, 171.2), (48, 104.5)], "6G": [(36, 498.1), (42, 160.0), (48, 39.9)]}


def reach(points, floor=100):
    return max((db for db, mbps in points if mbps >= floor), default=None)


for band in now:
    print(band, "range now", reach(now[band]), "dB vs baseline", reach(base[band]), "dB")""",
        },
        {
            "level": "Medium",
            "prompt": "Choose the regression tolerance from data: given 5 repeated runs per point of the baseline, use 3× the coefficient of variation (stdev/mean) per point, with a 3% minimum.",
            "solution": "Points with noisy measurements get wider tolerances; stable points get tight ones.",
            "solution_code": """import statistics

baseline_runs = {("5G", 30): [702.5, 698.0, 710.2, 695.4, 705.1], ("6G", 42): [160.0, 142.3, 171.8, 150.2, 166.4]}
for point, runs in baseline_runs.items():
    cv = statistics.stdev(runs) / statistics.mean(runs)
    tol = max(0.03, 3 * cv)
    print(point, f"cv={cv:.3f} tolerance={tol:.1%}")""",
        },
        {
            "level": "Hard",
            "prompt": "Detect non-monotonic points: throughput should not increase by more than 5% as attenuation rises; flag points that do (often a rate-adaptation or measurement problem worth investigating).",
            "solution": "Compare each point with the previous (lower attenuation) one per band.",
            "solution_code": """rows = {"5G": [(0, 939.4), (6, 938.1), (12, 930.0), (18, 990.2), (24, 870.0), (30, 666.0)],
        "6G": [(0, 2410.0), (6, 2398.0), (12, 2370.0), (18, 2290.0), (24, 1905.0), (30, 1205.0)]}
for band, pts in rows.items():
    for (d0, m0), (d1, m1) in zip(pts, pts[1:]):
        if m1 > m0 * 1.05:
            print(f"{band}: {m0} Mbps at {d0} dB -> {m1} Mbps at {d1} dB (+{(m1 / m0 - 1):.1%}) check this point")""",
        },
    ],
    "interview": [
        {"level": "Advanced", "q": "How would you make RvR results trustworthy enough to gate a release?", "a": "Controlled environment, verified attenuation, settle time, multiple iterations with median and worst case, raw data with full metadata, KPIs plus baseline comparison with tolerances derived from measured variance, and visible spread in charts; investigate non-monotonic points and outliers before trusting a verdict.", "follow": "What's the difference between a KPI failure and a regression? (Absolute floor vs relative drop from a reference build.)"},
    ],
    "quiz": [
        {"q": "Why store the test plan with the results?", "options": ["Size", "To compare like with like later", "Required by JSON", "Speed"], "answer": 1, "why": "Baselines need the same plan."},
        {"q": "A point at +2% vs baseline but below KPI is...", "options": ["Fine", "A KPI failure, not a regression", "A regression", "Noise"], "answer": 1, "why": "Two independent checks."},
    ],
    "cards": [
        {"front": "Trustworthy RvR", "back": "Iterations → median + min; metadata; raw data first; spread in chart"},
        {"front": "Two verdicts", "back": "KPI (absolute floor) and regression (relative to baseline ± tolerance)"},
    ],
}
