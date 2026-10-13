"""Phase 5 content: modules 5.11-5.14 (pytest)."""

from lab_support import LAB_PY

M_5_11 = {
    "id": "5.11",
    "title": "Built-in Fixtures",
    "hours": 1.5,
    "summary": "The fixtures pytest gives you for free: tmp_path for files, capsys and caplog for output and logs, pytest.warns, request, pytestconfig and record_property.",
    "concepts": [
        {
            "title": "tmp_path, capsys and caplog",
            "runner": "pytest",
            "filename": "test_builtins.py",
            "args": ["-v"],
            "concept": "`tmp_path` is a fresh `pathlib.Path` directory per test (`tmp_path_factory` for session-wide dirs). `capsys` captures what the code prints: `capsys.readouterr()` returns `.out` and `.err` and resets the buffer (`capfd` does the same at file-descriptor level, for subprocesses and C extensions). `caplog` captures log records: `caplog.records`, `caplog.messages`, `caplog.text`, and `caplog.set_level(...)` to lower the threshold.",
            "why": "Automation code writes captures and reports to disk, prints progress and logs warnings. These fixtures let you test all three without touching your real filesystem or console, and they clean up after themselves.",
            "syntax": "def test_x(tmp_path, capsys, caplog):\n    caplog.set_level(logging.INFO)\n    out, err = capsys.readouterr()\n    assert \"msg\" in caplog.messages",
            "code": """import json  ## The code under test writes JSON
import logging  ## And logs

log = logging.getLogger("survey")  ## Module-level logger, as in real code


def save_survey(folder, readings):  ## Code under test
    path = folder / "survey.json"  ## Output file inside the given folder
    path.write_text(json.dumps(readings))  ## Write the results
    print(f"saved {len(readings)} readings")  ## Progress message on stdout
    weak = [ssid for ssid, rssi in readings.items() if rssi < -75]  ## Weak networks
    if weak:  ## Only warn when needed
        log.warning("weak signal: %s", ", ".join(weak))  ## Becomes a log record
    log.info("survey done")  ## INFO is below the default WARNING threshold
    return path  ## Caller gets the file


def test_writes_file(tmp_path):  ## A new empty directory for this test only
    path = save_survey(tmp_path, {"lab-5g": -52})  ## Write into it
    assert json.loads(path.read_text()) == {"lab-5g": -52}  ## Read back and compare


def test_prints_progress(tmp_path, capsys):  ## capsys captures stdout/stderr
    save_survey(tmp_path, {"a": -50, "b": -60})  ## Prints one line
    assert capsys.readouterr().out == "saved 2 readings\\n"  ## Exact text, newline included


def test_logs_weak_networks(tmp_path, caplog):  ## caplog captures log records
    caplog.set_level(logging.INFO, logger="survey")  ## Also capture INFO from this logger
    save_survey(tmp_path, {"guest": -81, "lab": -49})  ## One weak network
    assert caplog.messages == ["weak signal: guest", "survey done"]  ## Formatted messages in order
    assert caplog.records[0].levelname == "WARNING"  ## Each record keeps its level""",
            "under": "pytest creates `tmp_path` under a per-session base directory and keeps the last three sessions for inspection. capsys swaps `sys.stdout`/`sys.stderr` for in-memory buffers while the test runs. caplog installs a handler on the root logger, but a record only reaches a handler if the logger's effective level allows it, which is why INFO needs `set_level`.",
            "gotchas": [
                {
                    "title": "Expecting caplog to see INFO without set_level",
                    "runner": "pytest",
                    "args": ["-q", "--tb=short"],
                    "note": "The root logger's default level is WARNING, so `log.info` records are dropped before caplog's handler sees them. Lower the level in the test with `caplog.set_level` (or `log_level` in pytest.ini).",
                    "wrong": """import logging

log = logging.getLogger("roam")


def test_roam_logged(caplog):
    log.info("roamed to ap-2")
    assert "roamed to ap-2" in caplog.messages""",
                    "fixed": """import logging

log = logging.getLogger("roam")


def test_roam_logged(caplog):
    caplog.set_level(logging.INFO)
    log.info("roamed to ap-2")
    assert "roamed to ap-2" in caplog.messages""",
                },
            ],
            "best": "Never write test files to the repo or `/tmp` by hand: use `tmp_path`. Assert on `caplog.messages` or records rather than on formatted text with timestamps, and call `readouterr()` right after the code you're checking, because it consumes the buffer.",
        },
        {
            "title": "pytest.warns, request, pytestconfig and record_property",
            "runner": "pytest",
            "filename": "test_meta.py",
            "args": ["-v", "--junitxml=report.xml", "-o", "junit_family=xunit1"],
            "concept": "`pytest.warns(Warning, match=...)` asserts that code emits a warning. `request` is the fixture-of-fixtures: `request.node` (the test item, its name and markers), `request.param` in parametrized fixtures, `request.addfinalizer`, `request.getfixturevalue`. `pytestconfig` is the config object (options, ini values, rootpath). `record_property(name, value)` attaches data to the test in the JUnit XML report, where CI dashboards can read it.",
            "why": "Deprecations in your bench library should be tested like any other behaviour, fixtures often need to know which test they serve, and measured values (throughput, firmware version) belong in the machine-readable report, not only in the console.",
            "syntax": "with pytest.warns(DeprecationWarning, match=\"use x\"):\n    old_api()\n\nrequest.node.name\npytestconfig.getoption(\"verbose\")\nrecord_property(\"mbps\", 941.2)",
            "code": """import warnings  ## To emit a warning

import pytest  ## For pytest.warns


def set_channel_legacy(ch):  ## Old API kept for compatibility
    warnings.warn("use set_channel(band, ch)", DeprecationWarning, stacklevel=2)  ## Tell callers to migrate
    return ch  ## Still works


def test_legacy_api_warns():  ## The warning is part of the contract
    with pytest.warns(DeprecationWarning, match="set_channel\\\\(band"):  ## Fails if no matching warning
        assert set_channel_legacy(36) == 36  ## And the value is still right


def test_knows_its_name(request, pytestconfig):  ## Introspection fixtures
    assert request.node.name == "test_knows_its_name"  ## The current test item
    assert pytestconfig.getoption("verbose") == 1  ## -v was passed once


def test_records_measurement(record_property):  ## Data for the JUnit report
    record_property("throughput_mbps", 941.2)  ## Becomes <property name=... value=...>
    record_property("firmware", "7.4.1")  ## Any string or number
    assert 941.2 > 900  ## The check itself""",
            "under": "pytest.warns installs a `warnings.catch_warnings(record=True)` context and checks the recorded list on exit. With `--junitxml=report.xml` pytest writes one `<testcase>` per test, and `record_property` adds `<properties>` to it. The report line at the end (`generated xml file`) confirms where it went. The default report format, `xunit2`, has no per-test properties, so `record_property` needs `junit_family=xunit1` (set it in pytest.ini); otherwise pytest warns and drops them.",
            "gotchas": [],
            "best": "Turn DeprecationWarnings into errors in CI (`filterwarnings = error::DeprecationWarning`) and test intentional warnings with pytest.warns. Use record_property for every measured KPI so dashboards don't have to scrape logs.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "runner": "pytest",
            "args": ["-v"],
            "prompt": "Test a function that writes a hostapd config to a file: check the file exists and contains `channel=36`.",
            "solution": "Pass `tmp_path` to the code under test and read the file back.",
            "solution_code": """def write_hostapd(folder, ssid, channel):
    path = folder / "hostapd.conf"
    path.write_text(f"ssid={ssid}\\nchannel={channel}\\nhw_mode=a\\n")
    return path


def test_hostapd_conf(tmp_path):
    path = write_hostapd(tmp_path, "lab-5g", 36)
    assert path.exists()
    assert "channel=36" in path.read_text().splitlines()""",
        },
        {
            "level": "Medium",
            "runner": "pytest",
            "args": ["-v"],
            "prompt": "A CLI prints errors to stderr. Use capsys to check that an invalid band prints `error: unknown band 7G` to stderr and nothing to stdout.",
            "solution": "readouterr() returns both streams; check each.",
            "solution_code": """import sys


def cli(band):
    if band not in {"2G", "5G", "6G"}:
        print(f"error: unknown band {band}", file=sys.stderr)
        return 2
    print(f"ok {band}")
    return 0


def test_invalid_band(capsys):
    assert cli("7G") == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.strip() == "error: unknown band 7G\"""",
        },
        {
            "level": "Hard",
            "runner": "pytest",
            "args": ["-q", "-s"],
            "prompt": "Use `tmp_path_factory` in a session fixture to create one shared capture directory, and have each test write a file named after itself (via `request.node.name`). Print the sorted file names at the end of the last test.",
            "solution": "tmp_path_factory.mktemp gives a session-wide directory; request.node.name names each file.",
            "solution_code": """import pytest


@pytest.fixture(scope="session")
def capture_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("captures")


@pytest.fixture
def capture_file(capture_dir, request):
    return capture_dir / f"{request.node.name}.pcap"


def test_assoc(capture_file):
    capture_file.write_bytes(b"\\xd4\\xc3\\xb2\\xa1")


def test_roam(capture_file, capture_dir):
    capture_file.write_bytes(b"\\xd4\\xc3\\xb2\\xa1")
    print(sorted(p.name for p in capture_dir.iterdir()))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "How do you test code that writes files?", "a": "Use the tmp_path fixture, a unique pathlib.Path directory per test that pytest creates and cleans up (keeping the last few runs for debugging). tmp_path_factory creates directories for broader scopes.", "follow": "What's the older equivalent? (tmpdir, which returns a py.path object.)"},
        {"level": "Intermediate", "q": "capsys vs capfd?", "a": "capsys replaces sys.stdout/sys.stderr Python objects; capfd redirects file descriptors 1 and 2, so it also captures output from subprocesses and C libraries.", "follow": "How do you see output while debugging? (-s or capsys.disabled().)"},
        {"level": "Intermediate", "q": "Why might caplog not capture a log line?", "a": "The logger's effective level filters it out before it reaches caplog's handler (default WARNING), or the logger has propagate=False. Fix with caplog.set_level(level, logger=name).", "follow": "Where else can you set it? (log_level in pytest.ini.)"},
        {"level": "Intermediate", "q": "What's record_property for?", "a": "Adding key/value data to a test's entry in the JUnit XML report, e.g. measured throughput or firmware version, so CI tools and dashboards can display or trend it.", "follow": "Is it compatible with xdist? (Yes; record_testsuite_property is for suite-level values.)"},
    ],
    "quiz": [
        {"q": "tmp_path is...", "options": ["Shared by all tests", "A unique pathlib.Path per test", "The repo root", "/tmp itself"], "answer": 1, "why": "One fresh directory per test."},
        {"q": "capsys.readouterr() returns...", "options": ["A string", "(out, err) and resets the buffers", "A list of lines", "Log records"], "answer": 1, "why": "A namedtuple; buffers reset."},
        {"q": "INFO logs missing in caplog. Fix:", "options": ["Use capsys", "caplog.set_level(logging.INFO)", "print instead", "-v"], "answer": 1, "why": "Lower the threshold."},
        {"q": "Assert a warning is emitted:", "options": ["pytest.raises(Warning)", "pytest.warns(Warning)", "recwarn.assert()", "warnings.assert_emitted"], "answer": 1, "why": "pytest.warns."},
        {"q": "Data in JUnit XML per test:", "options": ["print()", "record_property", "caplog", "request.param"], "answer": 1, "why": "Adds <property> elements."},
    ],
    "cards": [
        {"front": "Temp files in tests", "back": "`tmp_path` (per test), `tmp_path_factory.mktemp()` (wider scopes)"},
        {"front": "Check printed output", "back": "`out, err = capsys.readouterr()`"},
        {"front": "Check logs", "back": "`caplog.set_level(INFO)`; `caplog.messages`, `caplog.records`"},
        {"front": "Current test inside a fixture", "back": "`request.node` (.name, markers)"},
        {"front": "KPI into JUnit XML", "back": "`record_property('mbps', 941.2)`"},
    ],
}


M_5_12 = {
    "id": "5.12",
    "title": "Plugin Ecosystem",
    "hours": 1.5,
    "summary": "The plugins most automation teams install: pytest-xdist for parallel runs, pytest-rerunfailures, pytest-timeout, plus pytest-cov, pytest-html, pytest-mock and friends.",
    "concepts": [
        {
            "title": "xdist, rerunfailures and timeout",
            "runner": "pytest",
            "filename": "test_plugins.py",
            "args": ["-q", "-n", "2", "--tb=line", "--show-capture=no"],
            "concept": "**pytest-xdist** runs tests in parallel worker processes: `-n 4` or `-n auto`, with `--dist loadscope` to keep a module or class on one worker. **pytest-rerunfailures** retries failing tests: `--reruns 2 --reruns-delay 5` or `@pytest.mark.flaky(reruns=2)` on one test. **pytest-timeout** fails a test that runs too long: `--timeout 60` or `@pytest.mark.timeout(5)`, so a hung SSH session can't block the pipeline forever.",
            "why": "A 2-hour regression run on 4 workers takes about 30 minutes, a hung device read no longer stalls CI overnight, and an occasional RF glitch gets one retry (while still being reported).",
            "syntax": "pip install pytest-xdist pytest-rerunfailures pytest-timeout\n\npytest -n auto --dist loadscope --reruns 1 --timeout 300",
            "code": """import os  ## For the worker id
import time  ## To simulate a hang

import pytest  ## For markers

ATTEMPTS = {"count": 0}  ## Module state survives reruns within one worker process


def test_runs_on_a_worker():  ## Every test runs in some worker process
    assert os.environ["PYTEST_XDIST_WORKER"] in {"gw0", "gw1"}  ## xdist sets this variable


@pytest.mark.flaky(reruns=1)  ## pytest-rerunfailures: retry this test once if it fails
def test_flaky_association():  ## Fails the first time only
    ATTEMPTS["count"] += 1  ## Count tries in this process
    assert ATTEMPTS["count"] > 1, "association timed out"  ## First attempt fails, rerun passes


@pytest.mark.timeout(1)  ## This test may run at most 1 second
def test_hung_ssh_read():  ## Simulates a read that never returns
    time.sleep(3)  ## Killed after 1 s by pytest-timeout


@pytest.mark.parametrize("band", ["2G", "5G", "6G"])  ## Spread across workers
def test_band(band):  ## Three quick tests
    assert band.endswith("G")  ## Placeholder""",
            "under": "xdist starts N worker processes (gw0, gw1, ...); each collects the whole suite and the controller hands out test ids. Session fixtures run once **per worker**, not once overall, so shared hardware needs a lock (a file lock or a bench reservation service). Reruns re-execute the test with fresh function fixtures and are counted separately (`R` in the progress line, `1 rerun` in the summary). The timeout here uses the signal method, which raises inside the test, so the run continues.",
            "gotchas": [],
            "best": "Use xdist only for tests that don't share hardware, or group hardware tests with `--dist loadgroup` and `@pytest.mark.xdist_group(\"bench7\")`. Treat reruns as a temporary bandage: apply them per test with the flaky marker rather than globally (a global `--reruns` also reruns timed-out tests, and the timeout isn't reliably re-armed for the rerun), report rerun counts and fix the root cause. Set a global `--timeout` in CI as a safety net and shorter per-test timeouts where you know the bound.",
        },
        {
            "title": "The rest of the toolbox",
            "concept": "Other widely used plugins: **pytest-cov** (`--cov=pkg --cov-report=term-missing`, coverage with branch data), **pytest-html** (`--html=report.html --self-contained-html`), **pytest-mock** (`mocker` fixture wrapping unittest.mock with auto-undo), **pytest-randomly** (shuffles test order, reseeds random, exposes order dependencies), **pytest-benchmark** (`benchmark(fn)` with statistics), **pytest-bdd** (Gherkin feature files), **pytest-asyncio** or **anyio** (async tests), **pytest-repeat** (`--count 100` to hunt flakes). This example checks which ones are installed, the way a CI preflight might.",
            "why": "Knowing the ecosystem stops you from rebuilding coverage, HTML reports or parallelism by hand, and interviewers often ask which plugins you've used and why.",
            "syntax": "from importlib import metadata\nmetadata.version(\"pytest-xdist\")",
            "code": """from importlib import metadata  ## Reads installed package metadata

WANTED = ["pytest", "pytest-xdist", "pytest-rerunfailures", "pytest-timeout", "pytest-cov", "pytest-html"]  ## A team's standard set

for dist in WANTED:  ## Check each package
    try:  ## version() raises if the package isn't installed
        metadata.version(dist)  ## Look up the installed version
        status = "installed"  ## Found
    except metadata.PackageNotFoundError:  ## Not installed in this environment
        status = "missing  -> pip install " + dist  ## How to fix it
    print(f"{dist:<22} {status}")  ## One aligned line per package""",
            "local_only": "the output depends on which packages are installed; in the browser every package shows as missing",
            "under": "`importlib.metadata` reads the `*.dist-info` folders that pip writes, so it works for any installed distribution without importing it. Plugins that pytest auto-loads are listed in the header's `plugins:` line. The output shown is from the machine that built this course (pytest-cov and pytest-html not installed there).",
            "gotchas": [],
            "best": "Pin plugin versions in your requirements or lock file next to pytest itself, because plugins break across pytest major versions. Add a preflight like this to CI images, and prefer one well-maintained plugin over a pile of small ones.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "runner": "pytest",
            "args": ["-q", "--reruns", "2"],
            "prompt": "A test fails twice and passes on the third attempt. Run it with `--reruns 2` and read the summary.",
            "solution": "Two reruns are recorded (`RR.`), and the final outcome is passed.",
            "solution_code": """TRIES = []


def test_dhcp_lease():
    TRIES.append(1)
    assert len(TRIES) == 3, f"attempt {len(TRIES)}: no DHCP offer\"""",
        },
        {
            "level": "Medium",
            "runner": "pytest",
            "args": ["-v", "-n", "2", "--dist", "loadgroup"],
            "prompt": "Two tests use the same physical bench. Make sure xdist always runs them on the same worker (so never at the same time), while other tests spread out.",
            "solution": "`@pytest.mark.xdist_group(\"bench7\")` with `--dist loadgroup` pins a group to one worker; the node ids get an `@bench7` suffix.",
            "solution_code": """import pytest


@pytest.mark.xdist_group("bench7")
def test_rvr_5g():
    assert True


@pytest.mark.xdist_group("bench7")
def test_rvr_6g():
    assert True


def test_parser():
    assert True""",
        },
        {
            "level": "Hard",
            "runner": "pytest",
            "args": ["-q", "-p", "no:rerunfailures", "--tb=line", "--show-capture=no"],
            "prompt": "Write a test that waits for a device banner, with a per-test timeout of 1 second, and show how pytest-timeout reports a hang.",
            "solution": "`@pytest.mark.timeout(1)` turns an endless wait into a clear failure: `Failed: Timeout (>1.0s) from pytest-timeout`.",
            "solution_code": """import time

import pytest


def read_banner():
    while True:
        time.sleep(0.1)


@pytest.mark.timeout(1)
def test_banner():
    assert "login:" in read_banner()""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "What do you need to watch for when running hardware tests with xdist?", "a": "Each worker is a separate process with its own session fixtures, so shared devices can be configured concurrently. Group hardware tests with xdist_group/loadgroup, or use a reservation lock, and keep pure-software tests fully parallel.", "follow": "How would you share one expensive setup across workers? (A file lock plus a cached result in tmp_path_factory.getbasetemp().parent.)"},
        {"level": "Intermediate", "q": "Is retrying failed tests a good idea?", "a": "As a short-term mitigation for known-noisy RF or network conditions, yes, if reruns are visible in reports and tracked. As a permanent fix, no: it hides real intermittent bugs (e.g. a race in roaming).", "follow": "How would you track flakiness? (Store per-test rerun counts in a dashboard and alert on trends.)"},
        {"level": "Beginner", "q": "How do you measure test coverage?", "a": "pytest-cov: `pytest --cov=mypkg --cov-branch --cov-report=term-missing`, and enforce a floor with `--cov-fail-under=85` in CI.", "follow": "What doesn't coverage tell you? (Whether the assertions are meaningful.)"},
    ],
    "quiz": [
        {"q": "`-n auto` does what?", "options": ["Retries", "Runs workers = CPU count", "Auto-marks tests", "Sets timeouts"], "answer": 1, "why": "xdist worker count from CPUs."},
        {"q": "Session fixtures under xdist run...", "options": ["Once total", "Once per worker", "Once per test", "Never"], "answer": 1, "why": "Each worker has its own session."},
        {"q": "`R` in the progress line means...", "options": ["Running", "Rerun", "Random", "Report"], "answer": 1, "why": "pytest-rerunfailures."},
        {"q": "Plugin providing the `mocker` fixture:", "options": ["pytest-mock", "pytest-cov", "pytest-xdist", "pytest-bdd"], "answer": 0, "why": "pytest-mock."},
        {"q": "Exposes test-order dependencies:", "options": ["pytest-randomly", "pytest-timeout", "pytest-html", "pytest-cov"], "answer": 0, "why": "It shuffles order each run."},
    ],
    "cards": [
        {"front": "Parallel tests", "back": "pytest-xdist: `-n auto`, `--dist loadscope|loadgroup`"},
        {"front": "Retry flaky tests", "back": "pytest-rerunfailures: `--reruns 2 --reruns-delay 5`"},
        {"front": "Kill hung tests", "back": "pytest-timeout: `--timeout 300`, `@pytest.mark.timeout(5)`"},
        {"front": "Coverage", "back": "pytest-cov: `--cov=pkg --cov-branch --cov-fail-under=85`"},
        {"front": "HTML report", "back": "pytest-html: `--html=report.html --self-contained-html`"},
    ],
}


GOLDEN_PARSER = """def parse_iw_link(text):
    info = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Connected to"):
            info["bssid"] = line.split()[2]
        elif line.startswith("SSID:"):
            info["ssid"] = line.split(":", 1)[1].strip()
        elif line.startswith("freq:"):
            info["freq_mhz"] = int(float(line.split()[1]))
        elif line.startswith("signal:"):
            info["signal_dbm"] = int(line.split()[1])
        elif line.startswith("tx bitrate:"):
            info["tx_mbps"] = float(line.split()[2])
    return info
"""

GOLDEN_CONFTEST = """import json

import pytest


def pytest_addoption(parser):
    parser.addoption("--update-golden", action="store_true", help="rewrite golden files")


@pytest.fixture
def golden(request):
    update = request.config.getoption("--update-golden")
    folder = request.path.parent / "golden"

    def check(name, actual):
        path = folder / f"{name}.json"
        if update or not path.exists():
            path.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\\n")
            pytest.skip(f"golden file {path.name} written")
        assert actual == json.loads(path.read_text())

    return check
"""

M_5_13 = {
    "id": "5.13",
    "title": "Flaky Tests & Test Data",
    "hours": 2,
    "summary": "Why tests flake (time, order, shared state, randomness, real RF) and how to fix each cause; managing test data with data files, builders and golden files.",
    "concepts": [
        {
            "title": "Replace sleeps with polling, and control time and randomness",
            "concept": "Most flaky tests come from a few causes: fixed `sleep()`s that are sometimes too short, depending on wall-clock time, unseeded randomness, tests that depend on order or leftover state, and real-world noise. The fixes: poll a condition with a deadline instead of sleeping, inject the clock so tests can control it, seed random generators and log the seed, and give every test its own state.",
            "why": "A suite that fails 2% of the time for no reason trains people to ignore red builds, and then real regressions slip through. Deterministic tests are worth a lot of engineering effort.",
            "syntax": "def wait_until(pred, timeout, interval, clock=time.monotonic, sleep=time.sleep): ...\n\nrng = random.Random(seed)",
            "code": """import random  ## For a seeded generator
import time  ## Real clock and sleep (the defaults)


def wait_until(predicate, timeout=30.0, interval=0.5, clock=time.monotonic, sleep=time.sleep):  ## Clock and sleep are injectable
    deadline = clock() + timeout  ## monotonic: immune to NTP clock jumps
    while True:  ## Poll until success or deadline
        if predicate():  ## Condition met
            return True  ## Return as soon as it's true, no wasted waiting
        if clock() >= deadline:  ## Out of time
            return False  ## Caller decides how to fail
        sleep(interval)  ## Short pause between polls


class FakeClock:  ## Test double: time only moves when sleep is called
    def __init__(self):  ## Starts at zero
        self.now = 0.0  ## Simulated seconds

    def __call__(self):  ## Used as clock()
        return self.now  ## Current simulated time

    def sleep(self, seconds):  ## Used as sleep()
        self.now += seconds  ## Advance instantly


clock = FakeClock()  ## One fake clock for the example
states = iter(["down", "down", "down", "up"])  ## Link comes up on the fourth poll
print(wait_until(lambda: next(states) == "up", timeout=10, interval=2, clock=clock, sleep=clock.sleep))  ## True
print(clock.now)  ## 6.0 simulated seconds, ~0 real seconds

clock = FakeClock()  ## Fresh clock
print(wait_until(lambda: False, timeout=5, interval=2, clock=clock, sleep=clock.sleep), clock.now)  ## Gives up at the deadline

seed = 1234  ## In CI, generate one and print it so failures can be replayed
rng = random.Random(seed)  ## Private generator, doesn't touch the global one
print([rng.choice([1, 6, 11]) for _ in range(5)])  ## Same channel sequence every run with this seed""",
            "under": "`time.monotonic()` never goes backwards, unlike `time.time()`, which jumps when NTP corrects the clock. Passing `clock` and `sleep` as parameters (dependency injection) is what makes the loop testable in microseconds. `random.Random(seed)` creates an independent generator, so other code calling `random.random()` can't change your sequence.",
            "gotchas": [
                {
                    "title": "A fixed sleep instead of waiting for a condition",
                    "note": "A fixed sleep is either too short on a slow day (flaky failure) or too long every day (slow suite). The simulated link here takes a random 1–4 s to come up, so the `sleep(2)` version passes or fails depending on luck. Polling with a deadline always waits just long enough.",
                    "wrong": """import random

random.seed(2)
link_up_after = random.uniform(1, 4)
waited = 2.0
print("link up?", waited >= link_up_after)""",
                    "fixed": """import random

random.seed(2)
link_up_after = random.uniform(1, 4)
waited, interval, timeout = 0.0, 0.25, 10.0
while waited < link_up_after and waited < timeout:
    waited += interval
print("link up?", waited >= link_up_after, "after", waited, "s")""",
                },
            ],
            "best": "Ban bare `sleep()` in tests except inside a polling helper, use `time.monotonic` for deadlines, inject clocks, seed and log randomness (`pytest-randomly` prints its seed), run new tests 50–100 times (`pytest-repeat --count`) before merging, and quarantine flaky tests with a marker and a ticket rather than deleting or ignoring them.",
        },
        {
            "title": "Test data: data files and golden files",
            "runner": "pytest",
            "filename": "tests/test_parse_iw.py",
            "files": {
                "iwparse.py": GOLDEN_PARSER,
                "tests/conftest.py": GOLDEN_CONFTEST,
                "pytest.ini": "[pytest]\npythonpath = .\n",
                "tests/data/iw_link_5g.txt": "Connected to 3c:84:6a:12:34:56 (on wlan0)\n\tSSID: lab-5g\n\tfreq: 5180.0\n\tsignal: -52 dBm\n\ttx bitrate: 1200.9 MBit/s 80MHz HE-MCS 11 HE-NSS 2\n",
                "tests/data/iw_link_6g.txt": "Connected to 3c:84:6a:12:34:57 (on wlan1)\n\tSSID: lab-6g\n\tfreq: 5975\n\tsignal: -61 dBm\n\ttx bitrate: 2401.9 MBit/s 160MHz HE-MCS 11 HE-NSS 2\n",
                "tests/golden/iw_link_5g.json": "{\n  \"bssid\": \"3c:84:6a:12:34:56\",\n  \"freq_mhz\": 5180,\n  \"signal_dbm\": -52,\n  \"ssid\": \"lab-5g\",\n  \"tx_mbps\": 1200.9\n}\n",
            },
            "args": ["-v", "-rs"],
            "concept": "Keep realistic input samples (CLI output, API responses, pcaps) as files under `tests/data/` and parametrize over them. A **golden file** (snapshot) stores the expected parsed result; the test compares against it, and an `--update-golden` option regenerates it after a deliberate change, which you then review in the diff. Here the 6 GHz sample has no golden file yet, so the fixture writes one and skips.",
            "why": "Parsers for `iw`, `wpa_cli` or vendor CLIs break when firmware changes the output format. A folder of real captured outputs plus golden results catches that instantly, and adding a new firmware's output is a one-file change.",
            "syntax": "SAMPLES = sorted((Path(__file__).parent / \"data\").glob(\"*.txt\"))\n\n@pytest.mark.parametrize(\"sample\", SAMPLES, ids=lambda p: p.stem)\ndef test_x(sample, golden): ...",
            "code": """from pathlib import Path  ## Locate data files relative to this test

import pytest  ## For parametrize

from iwparse import parse_iw_link  ## Parser under test

SAMPLES = sorted((Path(__file__).parent / "data").glob("iw_link_*.txt"))  ## Every captured sample


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda p: p.stem)  ## One test per file, named after it
def test_parse_matches_golden(sample, golden):  ## golden is the snapshot fixture from conftest.py
    golden(sample.stem, parse_iw_link(sample.read_text()))  ## Compare with tests/golden/<stem>.json


def test_handles_missing_fields():  ## Edge cases are written inline
    assert parse_iw_link("Not connected.") == {}  ## Disconnected output gives an empty dict""",
            "under": "`pythonpath = .` in pytest.ini puts the project root on sys.path, so tests in `tests/` can import `iwparse.py` (without it, pytest only adds the test file's own folder and the import fails). Paths are built from `__file__`, never from the current directory, so the tests work wherever pytest is started. `ids=lambda p: p.stem` gives readable node ids (`[iw_link_5g]`). The golden JSON is written with `sort_keys=True` and a trailing newline so regenerated files produce minimal, reviewable diffs.",
            "gotchas": [],
            "best": "Capture samples from real devices (scrubbing serials and MACs if needed), name them by firmware and scenario, keep golden files small and sorted, and never run `--update-golden` in CI. Use builders (small functions or dataclasses with defaults) for structured inputs instead of copying big literals between tests.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write `retry_until(fn, attempts, delay, sleep=time.sleep)` that calls fn until it returns truthy, and test it with a fake sleep that records delays.",
            "solution": "Injecting sleep makes the test instant, and the recorded delays prove it waited between attempts but not after the last one.",
            "solution_code": """import time


def retry_until(fn, attempts=5, delay=1.0, sleep=time.sleep):
    for i in range(attempts):
        result = fn()
        if result:
            return result
        if i < attempts - 1:
            sleep(delay)
    return None


slept = []
answers = iter([None, None, "192.0.2.77"])
print(retry_until(lambda: next(answers), delay=2, sleep=slept.append))
print(slept)""",
        },
        {
            "level": "Medium",
            "runner": "pytest",
            "args": ["-q", "-p", "no:randomly"],
            "prompt": "These two tests pass in file order but the second fails when run alone, because it relies on state the first left behind. Fix it with a fixture that gives each test its own state.",
            "solution": "Shared module state creates order dependency. A function-scoped fixture builds fresh state for every test, so each passes in any order or alone.",
            "solution_code": """import pytest


@pytest.fixture
def ap_config():
    return {"ssid": "lab", "channels": [36]}


def test_add_channel(ap_config):
    ap_config["channels"].append(149)
    assert ap_config["channels"] == [36, 149]


def test_default_channels(ap_config):
    assert ap_config["channels"] == [36]""",
        },
        {
            "level": "Hard",
            "runner": "pytest",
            "files": {"conftest.py": """import os
import random

import pytest


def pytest_report_header(config):
    seed = int(os.environ.get("TEST_SEED", "0")) or random.SystemRandom().randrange(10**6)
    config.stash[SEED_KEY] = seed
    return f"test seed: {seed} (replay with TEST_SEED={seed})"


SEED_KEY = pytest.StashKey[int]()


@pytest.fixture
def rng(pytestconfig):
    return random.Random(pytestconfig.stash[SEED_KEY])
"""},
            "args": [],
            "env": {"TEST_SEED": "4242"},
            "prompt": "Generate a random seed per run (or take `TEST_SEED` from the environment), print it in the header, and give tests a seeded `rng` fixture so any failure can be replayed exactly.",
            "solution": "Store the seed in `config.stash` from pytest_report_header and build a Random from it in a fixture. The run shown used `TEST_SEED=4242`, so the header is reproducible.",
            "solution_code": """def test_random_channel_plan(rng):
    plan = [rng.choice([36, 52, 100, 149]) for _ in range(4)]
    assert all(ch in {36, 52, 100, 149} for ch in plan)""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "What are the most common causes of flaky tests?", "a": "Timing (fixed sleeps, timeouts too tight), order dependence and shared state, unseeded randomness, wall-clock/timezone assumptions, resource leaks between tests, concurrency races, and in hardware testing real RF/network variability.", "follow": "How do you find order dependence? (pytest-randomly or -p random-order; run the test alone.)"},
        {"level": "Intermediate", "q": "How do you replace a sleep in a test?", "a": "Poll the actual condition with a deadline (time.monotonic) and short interval, returning as soon as it's true; fail with a descriptive message on timeout. In unit tests, inject the clock/sleep so no real time passes.", "follow": "Why monotonic? (It can't jump backwards with NTP adjustments.)"},
        {"level": "Advanced", "q": "Your nightly Wi-Fi suite has a 3% random failure rate. What's your plan?", "a": "Measure first: collect per-test failure and rerun history. Classify: product bug (race in roaming), test bug (sleep, shared state), or environment (RF interference, bench contention). Fix test bugs, file product bugs with logs and pcaps, stabilise the environment (shielded boxes, attenuators, bench locks), and quarantine with tickets meanwhile, keeping them visible.", "follow": "How would you prove a test is fixed? (Run it 100+ times with pytest-repeat and compare failure rate.)"},
        {"level": "Intermediate", "q": "What's a golden file test and its risk?", "a": "Comparing output to a stored expected file (snapshot). Risk: people regenerate goldens without reviewing, baking bugs in. Mitigate with small, sorted, reviewable files and never auto-updating in CI.", "follow": "When are goldens a bad fit? (Outputs with timestamps or nondeterminism, unless normalised.)"},
    ],
    "quiz": [
        {"q": "Best replacement for `time.sleep(5)` before checking a link:", "options": ["sleep(10)", "Poll with a deadline", "Rerun on failure", "Skip the test"], "answer": 1, "why": "Wait just as long as needed, bounded."},
        {"q": "Clock to use for deadlines:", "options": ["time.time()", "time.monotonic()", "datetime.now()", "time.process_time()"], "answer": 1, "why": "Monotonic never jumps."},
        {"q": "A test passes in the suite but fails alone. Likely cause:", "options": ["Slow CPU", "Order dependence on shared state", "Wrong Python", "Missing marker"], "answer": 1, "why": "It relies on another test's side effects."},
        {"q": "`random.Random(seed)` vs `random.seed(seed)`:", "options": ["Same thing", "Private generator vs global state", "Random is faster", "seed is deprecated"], "answer": 1, "why": "Independent generator isn't affected by other code."},
        {"q": "Where should test data paths be anchored?", "options": ["os.getcwd()", "Path(__file__).parent", "/tmp", "$HOME"], "answer": 1, "why": "Works from any working directory."},
    ],
    "cards": [
        {"front": "Fix a flaky sleep", "back": "Poll the condition with a monotonic deadline"},
        {"front": "Make time testable", "back": "Inject `clock` and `sleep` parameters; use a FakeClock"},
        {"front": "Reproducible randomness", "back": "`rng = random.Random(seed)`; print the seed"},
        {"front": "Golden file workflow", "back": "Compare to stored JSON; `--update-golden` + review diff"},
        {"front": "Hunt flakes", "back": "`pytest --count 100 test_x.py` (pytest-repeat), pytest-randomly"},
    ],
}


FW_FILES = {
    "framework/__init__.py": "",
    "framework/dut.py": """from abc import ABC, abstractmethod


class Dut(ABC):
    \"\"\"What every device driver must provide. Tests only use this interface.\"\"\"

    @abstractmethod
    def set_channel(self, band: str, channel: int) -> None: ...

    @abstractmethod
    def throughput(self, band: str, width: int) -> float: ...


class SimDut(Dut):
    def __init__(self, name: str):
        from lab import FakeAP, throughput_mbps
        self.ap, self._tput = FakeAP(name), throughput_mbps

    def set_channel(self, band, channel):
        self.ap.set_channel(band, channel)

    def throughput(self, band, width):
        return self._tput(band, width)


DRIVERS = {"sim": SimDut}
""",
    "framework/testbed.py": """import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Testbed:
    name: str
    dut_type: str
    dut_name: str
    kpi_floor_mbps: dict


def load(path: Path) -> Testbed:
    data = json.loads(path.read_text())
    return Testbed(**data)
""",
    "testbeds/sim-lab.json": "{\n  \"name\": \"sim-lab\",\n  \"dut_type\": \"sim\",\n  \"dut_name\": \"ap-sim-1\",\n  \"kpi_floor_mbps\": {\"5G/80\": 850, \"6G/160\": 2200}\n}\n",
    "lab.py": LAB_PY,
    "conftest.py": """from pathlib import Path

import pytest

from framework import dut, testbed


def pytest_addoption(parser):
    parser.addoption("--testbed", default="sim-lab", help="testbed file name in testbeds/")


def pytest_report_header(config):
    return f"testbed: {config.getoption('testbed')}"


@pytest.fixture(scope="session")
def bed(pytestconfig):
    return testbed.load(Path(__file__).parent / "testbeds" / f"{pytestconfig.getoption('testbed')}.json")


@pytest.fixture(scope="session")
def device(bed):
    return dut.DRIVERS[bed.dut_type](bed.dut_name)
""",
}

M_5_14 = {
    "id": "5.14",
    "title": "Framework Architecture",
    "hours": 3,
    "summary": "Put it all together: a layered test framework (tests → fixtures → drivers → testbed config), and JUnit XML reports that CI and dashboards consume.",
    "concepts": [
        {
            "title": "Layers: tests, fixtures, drivers, testbed config",
            "runner": "pytest",
            "filename": "tests/test_kpi.py",
            "files": FW_FILES,
            "args": ["-v", "--testbed", "sim-lab"],
            "concept": "A maintainable automation framework separates four layers. **Tests** state intent and KPIs only. **Fixtures** (conftest.py) build and clean up resources. **Drivers** wrap devices behind an abstract interface (`Dut`), so a simulator, a vendor A AP and a vendor B AP are interchangeable. **Testbed files** (JSON/YAML) describe the physical setup: which DUT, addresses, KPI floors. Selecting `--testbed` swaps the whole environment without touching a test.",
            "why": "Without layers, IPs, SSH calls and thresholds end up copy-pasted in hundreds of tests, and moving to a new bench or AP model means editing all of them. With layers it's one new driver class and one testbed file.",
            "syntax": "framework/\n  dut.py        # Dut ABC + drivers\n  testbed.py    # load testbed config\ntestbeds/\n  sim-lab.json\nconftest.py     # options + fixtures\ntests/\n  test_kpi.py   # intent + KPIs only",
            "code": """import pytest  ## For parametrize

CASES = [("5G", 36, 80), ("6G", 37, 160)]  ## band, channel, width under test


@pytest.mark.parametrize("band,channel,width", CASES, ids=lambda v: str(v))  ## Readable ids
def test_throughput_meets_kpi(device, bed, band, channel, width):  ## Fixtures supply the DUT and testbed
    device.set_channel(band, channel)  ## Driver call through the Dut interface
    measured = device.throughput(band, width)  ## Measurement via the driver
    floor = bed.kpi_floor_mbps[f"{band}/{width}"]  ## Threshold comes from the testbed file, not the test
    assert measured >= floor, f"{band}/{width}: {measured} < {floor} Mbps"  ## Clear failure message""",
            "under": "`Dut` is an abstract base class: instantiating a driver that forgets a method fails immediately with TypeError, so incomplete drivers can't reach the lab. The `DRIVERS` registry maps the testbed's `dut_type` to a class (a simple factory). Session-scoped fixtures create the device once per run; in a real framework the device fixture would also connect, check health and collect logs on teardown.",
            "gotchas": [],
            "best": "Tests never import drivers, IP addresses or thresholds directly. Keep drivers thin and typed, put retries and timeouts in the driver layer, validate testbed files at load time (pydantic is a good fit), and add a simulator driver so the framework itself runs in CI on every commit.",
        },
        {
            "title": "JUnit XML: the report CI understands",
            "concept": "`pytest --junitxml=report.xml` writes one `<testcase>` per test with its time and, for failures, a `<failure>` element with the message. Jenkins, GitLab, GitHub Actions (via a reporter action) and Azure DevOps all display it. Values from `record_property` appear as `<property>` elements. Here a script reads such a report (embedded as a string) and builds the summary a nightly email or dashboard would show.",
            "why": "Console logs are for humans debugging one run. JUnit XML is how results reach CI tabs, trend graphs, flaky-test trackers and KPI dashboards across thousands of runs.",
            "syntax": "pytest --junitxml=report.xml -o junit_family=xunit1\n\nroot = ET.fromstring(xml)\nfor case in root.iter(\"testcase\"): ...",
            "code": """import xml.etree.ElementTree as ET  ## Standard-library XML parser

REPORT = \"\"\"<testsuites><testsuite name="pytest" tests="3" failures="1" errors="0" skipped="0" time="12.4">
<testcase classname="tests.test_kpi" name="test_tput[5G]" time="4.1">
  <properties><property name="throughput_mbps" value="912.4"/></properties></testcase>
<testcase classname="tests.test_kpi" name="test_tput[6G]" time="5.2">
  <properties><property name="throughput_mbps" value="2010.7"/></properties>
  <failure message="AssertionError: 6G/160: 2010.7 &lt; 2200 Mbps">...</failure></testcase>
<testcase classname="tests.test_roam" name="test_11r" time="3.1"/>
</testsuite></testsuites>\"\"\"  ## A trimmed real-world report

root = ET.fromstring(REPORT)  ## Parse the whole document
suite = root.find("testsuite")  ## pytest writes one suite inside <testsuites>
print(f"{suite.get('tests')} tests, {suite.get('failures')} failed, {suite.get('time')} s")  ## Totals from attributes

for case in root.iter("testcase"):  ## Every test case, at any depth
    props = {p.get("name"): p.get("value") for p in case.iter("property")}  ## record_property values
    failure = case.find("failure")  ## None if the test passed
    status = "FAIL" if failure is not None else "pass"  ## Outcome
    tput = props.get("throughput_mbps", "-")  ## Missing for non-KPI tests
    print(f"{status:<4} {case.get('name'):<16} {tput:>8}")  ## One row per test
    if failure is not None:  ## Show why it failed
        print("     ", failure.get("message"))  ## Entities like &lt; are decoded by the parser""",
            "under": "ElementTree decodes XML entities (`&lt;` becomes `<`). `iter()` walks the whole tree, `find()` returns the first direct child match. For untrusted XML from outside your CI, use `defusedxml`, which blocks entity-expansion attacks; reports your own pipeline produced are fine with the standard library.",
            "gotchas": [],
            "best": "Always produce JUnit XML in CI (plus an HTML report for humans), set `junit_family=xunit1` in pytest.ini if you use record_property, record KPIs with `record_property`, archive reports as build artifacts, and push the parsed numbers to a time-series store so regressions show up as trends, not surprises.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Define a `Dut` abstract base class with `reboot()` and show that a driver which forgets to implement it can't be instantiated.",
            "solution": "ABC plus @abstractmethod make Python refuse to create incomplete drivers.",
            "solution_code": """from abc import ABC, abstractmethod


class Dut(ABC):
    @abstractmethod
    def reboot(self) -> None: ...


class BrokenDriver(Dut):
    pass


class GoodDriver(Dut):
    def reboot(self):
        print("rebooting")


GoodDriver().reboot()
try:
    BrokenDriver()
except TypeError as e:
    print("TypeError:", e)""",
        },
        {
            "level": "Medium",
            "prompt": "Validate a testbed dict before use: required keys `name`, `dut_type`, `kpi_floor_mbps`, dut_type must be one of the known drivers, and every KPI floor must be a positive number. Collect all problems instead of stopping at the first.",
            "solution": "Accumulate error strings and raise once with all of them, so a misconfigured bench is fixed in one round.",
            "solution_code": """DRIVERS = {"sim", "vendor_a", "vendor_b"}


def validate(bed):
    errors = [f"missing key: {k}" for k in ("name", "dut_type", "kpi_floor_mbps") if k not in bed]
    if "dut_type" in bed and bed["dut_type"] not in DRIVERS:
        errors.append(f"unknown dut_type {bed['dut_type']!r}")
    for kpi, floor in bed.get("kpi_floor_mbps", {}).items():
        if not isinstance(floor, (int, float)) or floor <= 0:
            errors.append(f"bad floor for {kpi}: {floor!r}")
    if errors:
        raise ValueError("; ".join(errors))
    return bed


print(validate({"name": "lab7", "dut_type": "sim", "kpi_floor_mbps": {"5G/80": 850}})["name"])
try:
    validate({"dut_type": "vendor_c", "kpi_floor_mbps": {"6G/160": -1}})
except ValueError as e:
    print(e)""",
        },
        {
            "level": "Hard",
            "runner": "pytest",
            "args": ["-q", "--junitxml=out/report.xml", "-o", "junit_family=xunit1"],
            "files": {"conftest.py": """import xml.etree.ElementTree as ET
from pathlib import Path


def pytest_sessionfinish(session, exitstatus):
    path = Path(session.config.option.xmlpath or "")
    print("\\nreport written:", path.name)


def pytest_unconfigure(config):
    path = Path("out/report.xml")
    if path.exists():
        root = ET.parse(path).getroot()
        names = [c.get("name") for c in root.iter("testcase")]
        props = [p.get("value") for p in root.iter("property")]
        print("junit testcases:", names, "properties:", props)
"""},
            "prompt": "Run tests with `--junitxml`, record a throughput property, and after the run (in `pytest_unconfigure`, when the XML has been written) parse the report and print the test names and recorded values.",
            "solution": "The junitxml plugin writes the file at session finish, so read it in `pytest_unconfigure`. record_property values appear as `<property>` elements.",
            "solution_code": """def test_tput_5g(record_property):
    record_property("throughput_mbps", 912.4)


def test_tput_6g(record_property):
    record_property("throughput_mbps", 2401.0)""",
        },
    ],
    "interview": [
        {"level": "Advanced", "q": "Describe the architecture of a test automation framework you'd build for Wi-Fi APs.", "a": "Layers: tests (intent and KPIs), fixtures in conftest (setup/teardown, logs on failure), a driver layer with an abstract Dut interface and per-vendor implementations (SSH/REST/serial), equipment drivers (attenuators, traffic generators, sniffers), testbed config files validated at load, and reporting (JUnit XML, HTML, KPIs to a time-series DB). A simulator driver lets the framework itself be tested in CI. Markers and options select band, testbed and suite level.", "follow": "Where do retries belong? (In drivers for transport errors, not in tests.)"},
        {"level": "Intermediate", "q": "Why put thresholds in testbed files instead of tests?", "a": "KPIs depend on the bench (antenna setup, attenuation, DUT model). Keeping them in configuration lets one test run on many benches with appropriate floors and lets KPI changes be reviewed separately from logic.", "follow": "How would you version them? (Same repo, reviewed via PRs, with history.)"},
        {"level": "Intermediate", "q": "What does a JUnit XML report contain and who consumes it?", "a": "testsuite totals, one testcase per test with classname, name and time, failure/error/skipped elements with messages, and optional properties. CI systems render it, and scripts feed dashboards and flaky trackers.", "follow": "How do you add custom data? (record_property / record_testsuite_property.)"},
        {"level": "Advanced", "q": "How would you make the framework itself trustworthy?", "a": "Unit tests for drivers against simulators and recorded outputs, pytester tests for plugins, type checking and linting in CI, a smoke run on a simulated testbed per commit, versioned releases of the framework package, and clear ownership of drivers.", "follow": "How do you roll out a framework change to many benches safely? (Canary benches first, then all.)"},
    ],
    "quiz": [
        {"q": "Which layer should know a DUT's IP address?", "options": ["Tests", "Testbed config", "Assertions", "Markers"], "answer": 1, "why": "Environment details live in config."},
        {"q": "An ABC driver missing an abstract method:", "options": ["Works until called", "TypeError on instantiation", "Warning", "Skipped"], "answer": 1, "why": "Python refuses to instantiate it."},
        {"q": "Flag to write a JUnit report:", "options": ["--junit", "--junitxml=path", "--xml", "--report"], "answer": 1, "why": "--junitxml."},
        {"q": "Where does record_property data appear?", "options": ["Console only", "<property> elements in JUnit XML", "pytest.ini", "Nowhere"], "answer": 1, "why": "Inside the testcase."},
        {"q": "Why include a simulator driver?", "options": ["Speed up the lab", "Test the framework in CI without hardware", "Replace real tests", "Licensing"], "answer": 1, "why": "Framework changes are verified on every commit."},
    ],
    "cards": [
        {"front": "Framework layers", "back": "tests → fixtures → drivers (Dut ABC) → testbed config → reports"},
        {"front": "Swap environments", "back": "`--testbed name` → load testbeds/name.json in a session fixture"},
        {"front": "Driver registry", "back": "`DRIVERS = {'sim': SimDut, ...}`; pick by testbed dut_type"},
        {"front": "JUnit XML", "back": "`pytest --junitxml=report.xml` (+ `junit_family=xunit1` for record_property)"},
        {"front": "Parse JUnit XML", "back": "`ET.parse(path).getroot().iter('testcase')`"},
    ],
}
