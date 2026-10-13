"""Phase 5 content: modules 5.1-5.5 (pytest)."""

from lab_support import LAB_PY

M_5_1 = {
    "id": "5.1",
    "title": "Test Discovery & Assertions",
    "hours": 2,
    "summary": "How pytest finds tests, plain assert with rich failure messages, pytest.approx for measurements, pytest.raises for expected errors, and selecting which tests to run.",
    "concepts": [
        {
            "title": "Discovery and assertions",
            "runner": "pytest",
            "filename": "test_throughput.py",
            "files": {"lab.py": LAB_PY},
            "concept": "pytest collects files named `test_*.py` (or `*_test.py`), functions named `test_*`, and methods named `test_*` inside classes named `Test*` (without an `__init__`). A test is just a function that uses plain `assert`; pytest rewrites assertions so failures show the actual values. `pytest.approx` compares floats with a tolerance, and `pytest.raises(Error, match=...)` asserts that a block raises. Exit code 0 means all passed, 1 means failures.",
            "why": "Throughput results are floats with noise, invalid configurations must raise, and when a check fails at 3 a.m. the report must say what the value was. pytest gives all three with almost no boilerplate.",
            "syntax": "def test_name():\n    assert actual == expected\n    assert measured == pytest.approx(900, rel=0.05)\n    with pytest.raises(ValueError, match=\"not allowed\"):\n        do_bad_thing()\n\n$ pytest -q",
            "code": """import pytest  ## The test framework

from lab import throughput_mbps  ## The code under test (a simulated measurement)


def test_5g_80mhz_at_close_range():  ## Collected because the name starts with test_
    assert throughput_mbps("5G", 80) == 900.0  ## Plain assert: no special assertEqual methods


def test_6g_within_five_percent_of_target():  ## Measurements need tolerances
    assert throughput_mbps("6G", 320, rssi=-51) == pytest.approx(4800, rel=0.05)  ## Passes if within 5% of the target


def test_width_not_allowed_on_2g():  ## Expected errors are part of the contract
    with pytest.raises(ValueError, match="not allowed on 2G"):  ## Fails unless this exact error is raised
        throughput_mbps("2G", 80)  ## 80 MHz isn't valid on 2.4 GHz


def test_weak_signal_still_meets_floor():  ## This one fails on purpose, to show the report
    measured = throughput_mbps("5G", 80, rssi=-70)  ## Weak signal: about 540 Mbps
    assert measured >= 600, f"5G/80 at -70 dBm gave {measured} Mbps"  ## The message appears in the failure


class TestDfs:  ## Grouping tests in a class (no __init__ allowed)
    def test_channel_52_is_dfs(self):  ## Methods named test_* are collected too
        assert 52 in range(52, 145)  ## DFS range in 5 GHz""",
            "under": "When pytest imports a test module, its import hook rewrites every `assert` statement into code that records the sub-expressions (here `measured`, the comparison operands) so the failure message can show them. That's why test files must be imported by pytest itself, and why helper modules that should get rich asserts too need `pytest.register_assert_rewrite`. Collection results are a tree: session → module → class → function items.",
            "gotchas": [
                {
                    "title": "A test file name pytest doesn't collect",
                    "runner": "pytest",
                    "filename": "check_radio.py",
                    "note": "pytest only collects test_*.py and *_test.py by default, so this file is silently ignored: 'no tests ran', exit code 5.",
                    "wrong": """def test_channel_is_valid():
    assert 36 in range(36, 166)""",
                    "fixed": """# Same code, saved as test_radio.py (or add python_files = check_*.py to pytest.ini)
def test_channel_is_valid():
    assert 36 in range(36, 166)""",
                    "fixed_filename": "test_radio.py",
                },
                {
                    "title": "Comparing measured floats with ==",
                    "runner": "pytest",
                    "note": "Measured values are never exactly equal to a target. Compare with approx (relative or absolute tolerance).",
                    "wrong": """def test_aggregate():
    streams = [452.1, 461.9, 447.3]
    assert sum(streams) / 3 == 453.77""",
                    "fixed": """import pytest

def test_aggregate():
    streams = [452.1, 461.9, 447.3]
    assert sum(streams) / 3 == pytest.approx(453.77, abs=0.01)""",
                },
            ],
            "best": "Name test files and functions after the behaviour they check (`test_6g_within_five_percent_of_target`), keep one behaviour per test, use approx for every measured value and `pytest.raises(..., match=...)` for error paths, and add a message to asserts whose numbers need context.",
        },
        {
            "title": "Selecting tests to run",
            "runner": "pytest",
            "filename": "test_suite.py",
            "args": ["-v", "-k", "6g and not slow"],
            "concept": "You rarely run everything. `-k \"expr\"` selects tests whose names (and classes and markers) match a boolean expression; a **node id** such as `test_suite.py::TestRoam::test_11r` runs exactly one test; `-x` stops at the first failure; `-v` lists each test with its result; `--co` (collect-only) shows what would run. Exit code 5 means nothing was collected.",
            "why": "While debugging one roaming failure you want to rerun just that test in seconds, and a sanity job wants only the 6 GHz subset. Selection is how one suite serves both.",
            "syntax": "pytest -k \"6g and not slow\"\npytest tests/test_suite.py::TestRoam::test_11r\npytest -x -v\npytest --co -q",
            "code": """def test_6g_association():  ## Name contains "6g"
    assert True  ## Placeholder test body


def test_6g_throughput_slow():  ## Contains "6g" but also "slow": excluded by the -k expression
    assert True  ## Placeholder


def test_5g_association():  ## Doesn't match "6g"
    assert True  ## Placeholder


class TestRoam6g:  ## -k also matches class names
    def test_11r_fast_transition(self):  ## Selected because its class name contains "6g"
        assert True  ## Placeholder""",
            "under": "`-k` is evaluated against each item's keywords: its name, its parent names (class, module) and its markers, case-insensitively. Deselected items are counted in the summary. Node ids are `path::Class::function[param-id]`, which is also what pytest prints in failure reports, so you can copy one straight onto the command line.",
            "gotchas": [],
            "best": "Name tests so that `-k` selections fall out naturally (band, feature, speed), print node ids in CI reports for copy-paste reruns, and use `-x` with `-v` while debugging locally.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "runner": "pytest",
            "files": {"lab.py": LAB_PY},
            "prompt": "Write two tests for throughput_mbps: 6 GHz 160 MHz at close range is 2400 Mbps, and 5 GHz 320 MHz raises ValueError.",
            "solution": "One equality (exact here, because the simulation is deterministic) and one pytest.raises.",
            "solution_code": """import pytest
from lab import throughput_mbps


def test_6g_160():
    assert throughput_mbps("6G", 160) == 2400.0


def test_5g_320_rejected():
    with pytest.raises(ValueError, match="320 MHz"):
        throughput_mbps("5G", 320)""",
        },
        {
            "level": "Medium",
            "runner": "pytest",
            "files": {"lab.py": LAB_PY},
            "prompt": "Test that throughput drops monotonically as RSSI weakens from -50 to -80 dBm in 5 dB steps on 5G/80.",
            "solution": "Compute the series and assert each value is less than or equal to the previous one.",
            "solution_code": """from lab import throughput_mbps


def test_monotonic_with_rssi():
    series = [throughput_mbps("5G", 80, rssi=r) for r in range(-50, -81, -5)]
    assert all(b <= a for a, b in zip(series, series[1:])), series""",
        },
        {
            "level": "Hard",
            "runner": "pytest",
            "args": ["-x", "-q"],
            "prompt": "Show what -x does: write three tests where the second fails, and run with -x so the third never runs.",
            "solution": "With -x pytest stops after the first failure; the summary shows 1 failed, 1 passed.",
            "solution_code": """def test_first():
    assert True


def test_second_fails():
    assert 880 >= 900, "below threshold"


def test_third_never_runs():
    assert True""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Why pytest over unittest?", "a": "Plain functions and assert instead of classes and assertEqual methods, rich failure introspection, fixtures for setup and teardown, parametrization, markers and a large plugin ecosystem. pytest also runs existing unittest tests.", "follow": "How does pytest show the values in a failed assert? (Assertion rewriting at import time.)"},
        {"level": "Beginner", "q": "How do you test that code raises an exception?", "a": "`with pytest.raises(ValueError, match='regex'):` around the call. The test fails if nothing is raised or a different type is raised; match checks the message.", "follow": "How do you inspect the exception? (`with pytest.raises(E) as excinfo:` then excinfo.value.)"},
        {"level": "Intermediate", "q": "How do you compare floating-point measurements?", "a": "pytest.approx(expected, rel=..., abs=...), which works for numbers, lists and dicts of numbers. Pick a tolerance that reflects measurement noise, e.g. rel=0.05 for throughput.", "follow": "What's the default tolerance? (rel=1e-6, abs=1e-12.)"},
        {"level": "Intermediate", "q": "What do pytest's exit codes mean?", "a": "0 all passed, 1 some tests failed, 2 interrupted, 3 internal error, 4 usage error, 5 no tests collected. CI should treat 5 as a failure too, because it usually means a misconfigured path or selection.", "follow": "How do you rerun one test? (Pass its node id: file::Class::test.)"},
    ],
    "quiz": [
        {"q": "Which file does pytest collect by default?", "options": ["radio_checks.py", "test_radio.py", "radio.py", "tests.py"], "answer": 1, "why": "test_*.py or *_test.py."},
        {"q": "`pytest.approx(900, rel=0.05)` accepts...", "options": ["Only 900", "855 to 945", "0 to 900", "Any int"], "answer": 1, "why": "±5% of 900."},
        {"q": "Exit code when no tests are collected?", "options": ["0", "1", "4", "5"], "answer": 3, "why": "5 means nothing ran."},
        {"q": "`-k \"6g and not slow\"` selects...", "options": ["All tests", "Tests matching 6g but not slow", "Only slow tests", "Marked tests only"], "answer": 1, "why": "A boolean keyword expression."},
        {"q": "What does -x do?", "options": ["Runs in parallel", "Stops at the first failure", "Excludes slow tests", "Shows extra output"], "answer": 1, "why": "Exit on first failure."},
    ],
    "cards": [
        {"front": "pytest discovery rules", "back": "test_*.py files, test_* functions, Test* classes (no __init__)"},
        {"front": "Float comparison in tests", "back": "`assert x == pytest.approx(y, rel=0.05)`"},
        {"front": "Expected exception", "back": "`with pytest.raises(E, match='...'):`"},
        {"front": "Run one test", "back": "`pytest path::Class::test_name`"},
        {"front": "pytest exit codes", "back": "0 pass, 1 fail, 2 interrupted, 4 usage, 5 nothing collected"},
    ],
}


M_5_2 = {
    "id": "5.2",
    "title": "Fixtures: Fundamentals",
    "hours": 2.5,
    "summary": "Fixtures as dependency injection, yield-based setup and teardown, scopes from function to session, fixtures that use fixtures, and errors vs failures.",
    "concepts": [
        {
            "title": "Fixtures, yield teardown and scope",
            "runner": "pytest",
            "filename": "test_bench.py",
            "args": ["-q", "-s"],
            "files": {"lab.py": LAB_PY},
            "concept": "A **fixture** is a function decorated with `@pytest.fixture` that prepares something a test needs; a test asks for it by naming it as a parameter. Code before `yield` is setup, the yielded value is what the test receives, and code after `yield` is teardown, which runs even if the test fails. **Scope** controls how often a fixture is created: `function` (default, per test), `class`, `module`, `package` or `session` (once per run).",
            "why": "Connecting to a testbed is slow and should happen once per session; applying a baseline AP config can happen once per module; each test still needs a freshly connected station. Scopes express exactly that, and yield teardown guarantees the station is disconnected even after a failure.",
            "syntax": "@pytest.fixture(scope=\"session\")\ndef testbed():\n    tb = connect()\n    yield tb          # tests run here\n    tb.close()        # teardown, always\n\ndef test_x(testbed): ...",
            "code": """import pytest  ## Fixtures live in pytest

from lab import FakeAP, FakeStation  ## Simulated devices


@pytest.fixture(scope="session")  ## Created once for the whole run
def ap():  ## Tests receive whatever this yields
    print("\\n[session] connect to ap-1")  ## Setup (slow in real life)
    device = FakeAP("ap-1")  ## The resource
    yield device  ## Hand it to every test that asks for it
    print("[session] disconnect ap-1")  ## Teardown: once, after the last test


@pytest.fixture  ## Default scope "function": a fresh one per test
def sta(ap):  ## Fixtures can request other fixtures
    print("  [test] associate sta1")  ## Per-test setup
    station = FakeStation("aa:01")  ## A new station object every time
    station.associate(ap, rssi=-52)  ## Uses the session-scoped AP
    yield station  ## The test runs now
    station.disconnect()  ## Teardown runs even if the test failed
    print("  [test] disconnected sta1")  ## Visible teardown


def test_associated_to_ap1(sta, ap):  ## Ask for fixtures by parameter name
    assert sta.ap is ap  ## Same AP object as the fixture's


def test_rssi_is_strong(sta):  ## A second test gets a NEW sta, but the SAME ap
    assert sta.rssi > -60  ## Fresh state per test""",
            "under": "pytest builds a dependency graph from parameter names, creates each fixture once per its scope, and caches the value for the rest of that scope. Teardown runs in the reverse order of setup when the scope ends. Yield fixtures are generators: pytest calls `next()` for setup and `next()` again (expecting StopIteration) for teardown, so the code after yield runs even when the test raised.",
            "gotchas": [
                {
                    "title": "Mutating a broad-scoped fixture",
                    "runner": "pytest",
                    "files": {"lab.py": LAB_PY},
                    "note": "A session-scoped AP is shared, so one test's channel change leaks into the next. Reset state in a function-scoped fixture, or don't mutate shared objects.",
                    "wrong": """import pytest
from lab import FakeAP

@pytest.fixture(scope="session")
def ap():
    return FakeAP("ap-1")

def test_change_channel(ap):
    ap.set_channel("5G", 149)

def test_default_channel_is_unset(ap):
    assert "5G" not in ap.channels""",
                    "fixed": """import pytest
from lab import FakeAP

@pytest.fixture(scope="session")
def ap():
    return FakeAP("ap-1")

@pytest.fixture
def clean_ap(ap):
    ap.channels.clear()
    yield ap
    ap.channels.clear()

def test_change_channel(clean_ap):
    clean_ap.set_channel("5G", 149)

def test_default_channel_is_unset(clean_ap):
    assert "5G" not in clean_ap.channels""",
                }
            ],
            "best": "Give expensive, read-mostly resources (testbed connections) session scope and cheap, mutable ones function scope. Put teardown after `yield` so it always runs, and keep fixtures small and composable.",
        },
        {
            "title": "Errors vs failures, and addfinalizer",
            "runner": "pytest",
            "filename": "test_setup_errors.py",
            "args": ["-q", "-rfE"],
            "concept": "pytest distinguishes a **failure** (an assert in the test body failed: `F`) from an **error** (an exception during fixture setup or teardown: `E`). An error usually means the lab or environment is broken, not the DUT. If setup raises before `yield`, the teardown part of that fixture doesn't run, so allocate one resource per fixture. `request.addfinalizer(func)` registers cleanup from inside a fixture, useful when you create resources in a loop.",
            "why": "Separating \"the bench couldn't be reached\" (error) from \"the DUT behaved wrongly\" (failure) is the first step of every nightly triage, and decides whether to file a bug or fix the lab.",
            "syntax": "@pytest.fixture\ndef captures(request):\n    started = []\n    for iface in [\"mon0\", \"mon1\"]:\n        started.append(start(iface))\n        request.addfinalizer(lambda i=iface: stop(i))\n    return started\n\n$ pytest -rfE   # summary of failures and errors",
            "code": """import pytest  ## Fixtures and markers


@pytest.fixture  ## Setup that fails: the lab is broken
def attenuator():  ## e.g. the attenuator's HTTP API is down
    raise ConnectionError("attenuator 10.0.0.50 unreachable")  ## Raised during SETUP


@pytest.fixture  ## Several resources, each with its own cleanup
def captures(request):  ## `request` describes the requesting test
    started = []  ## What we've started so far
    for iface in ["mon0", "mon1"]:  ## Start one capture per monitor interface
        started.append(iface)  ## Pretend start succeeded
        request.addfinalizer(lambda i=iface: print(f"stopped capture on {i}"))  ## Registered cleanups run in reverse order
    return started  ## No yield needed when using addfinalizer


def test_rate_vs_range(attenuator):  ## Never runs: its fixture errored
    assert attenuator  ## Unreached


def test_dut_throughput():  ## A real product failure
    assert 880 >= 900, "throughput below threshold"  ## F, not E


def test_with_captures(captures):  ## Uses the multi-resource fixture
    assert captures == ["mon0", "mon1"]  ## Passes; finalizers print afterwards (shown with -s)""",
            "under": "Each test has three phases: setup, call and teardown, each producing its own report. An exception in setup or teardown is reported as an error for that test; an exception in the call phase is a failure. `-rfE` adds a short summary of failures (f) and errors (E); `-r` accepts other letters too (s skipped, x xfailed, A all).",
            "gotchas": [],
            "best": "Treat errors as \"fix the lab or the framework\" and failures as \"investigate the DUT\" in your triage process. Keep one resource per fixture so a failed setup never leaves half-built state, and use addfinalizer when creating a variable number of resources.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "runner": "pytest",
            "args": ["-q", "-s"],
            "prompt": "Write a function-scoped yield fixture `scan_results` that returns a list of BSSIDs and prints 'cleared' in teardown; use it in two tests.",
            "solution": "Each test gets its own list, and teardown prints after each test.",
            "solution_code": """import pytest


@pytest.fixture
def scan_results():
    results = ["ap-1", "ap-2"]
    yield results
    results.clear()
    print("cleared")


def test_two_bssids(scan_results):
    assert len(scan_results) == 2


def test_can_modify(scan_results):
    scan_results.append("ap-3")
    assert "ap-3" in scan_results""",
        },
        {
            "level": "Medium",
            "runner": "pytest",
            "args": ["-q", "-s"],
            "prompt": "Show module scope: a module-scoped fixture prints 'apply baseline config' once, even though three tests use it.",
            "solution": "scope='module' creates the fixture once per test module.",
            "solution_code": """import pytest


@pytest.fixture(scope="module")
def baseline():
    print("\\napply baseline config")
    yield {"country": "IN", "channel": 36}
    print("\\nrestore factory config")


def test_country(baseline):
    assert baseline["country"] == "IN"


def test_channel(baseline):
    assert baseline["channel"] == 36


def test_keys(baseline):
    assert set(baseline) == {"country", "channel"}""",
        },
        {
            "level": "Hard",
            "runner": "pytest",
            "args": ["-q", "-rE"],
            "prompt": "Write a fixture whose TEARDOWN fails (after yield) and show that the test passes but pytest reports an error for it.",
            "solution": "An exception after yield is a teardown error, reported separately from the test result.",
            "solution_code": """import pytest


@pytest.fixture
def bench_lock():
    yield "bench07"
    raise RuntimeError("could not release bench07 lock")


def test_uses_bench(bench_lock):
    assert bench_lock == "bench07\"""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What is a fixture?", "a": "A function marked @pytest.fixture that provides setup (and teardown via yield) for tests. Tests request fixtures by naming them as parameters; pytest creates them, caches them per scope and tears them down in reverse order.", "follow": "How is that better than setup_method? (Explicit, composable, scoped and reusable across files.)"},
        {"level": "Intermediate", "q": "Explain fixture scopes.", "a": "function (default, per test), class, module, package and session. Broader scopes are created once and shared, which saves time for expensive resources but means tests must not leave them modified.", "follow": "Can a session fixture use a function-scoped one? (No: ScopeMismatch error.)"},
        {"level": "Intermediate", "q": "What does yield do in a fixture?", "a": "Everything before yield is setup; the yielded value goes to the test; everything after yield is teardown and runs after the test, even if it failed. If setup raises before yield, teardown doesn't run.", "follow": "Alternative for dynamic cleanups? (request.addfinalizer.)"},
        {"level": "Intermediate", "q": "What's the difference between an error and a failure in pytest?", "a": "A failure is an assertion or exception in the test function itself. An error is an exception in fixture setup or teardown. In lab terms: failures point at the DUT, errors usually at the lab or framework.", "follow": "How do you list both in the summary? (pytest -rfE.)"},
    ],
    "quiz": [
        {"q": "Default fixture scope?", "options": ["session", "module", "function", "class"], "answer": 2, "why": "One per test."},
        {"q": "Code after yield in a fixture runs...", "options": ["Before the test", "After the test, even on failure", "Only on success", "Never"], "answer": 1, "why": "That's teardown."},
        {"q": "An exception in fixture setup is reported as...", "options": ["F (failed)", "E (error)", "s (skipped)", "x (xfail)"], "answer": 1, "why": "Setup/teardown problems are errors."},
        {"q": "How does a test request a fixture?", "options": ["@uses(fixture)", "By naming it as a parameter", "Importing it", "Calling it"], "answer": 1, "why": "Dependency injection by name."},
        {"q": "Which scope suits a slow testbed connection?", "options": ["function", "session", "class", "None"], "answer": 1, "why": "Create it once per run."},
    ],
    "cards": [
        {"front": "Yield fixture", "back": "setup → yield value → teardown (always runs)"},
        {"front": "Fixture scopes", "back": "function, class, module, package, session"},
        {"front": "Error vs failure", "back": "Fixture setup/teardown exception vs test-body failure"},
        {"front": "Dynamic cleanup", "back": "`request.addfinalizer(func)`"},
    ],
}


M_5_3 = {
    "id": "5.3",
    "title": "Fixtures: Advanced",
    "hours": 2.5,
    "summary": "Factory fixtures, parametrized fixtures with request.param, autouse fixtures, overriding fixtures, and usefixtures.",
    "concepts": [
        {
            "title": "Factory and parametrized fixtures",
            "runner": "pytest",
            "filename": "test_security_modes.py",
            "args": ["-v"],
            "files": {"lab.py": LAB_PY},
            "concept": "A **factory fixture** returns a function, so a test can create as many configured objects as it needs, while the fixture still tracks and cleans them up. A **parametrized fixture** (`@pytest.fixture(params=[...])`) runs every test that uses it once per parameter, with the current value in `request.param`; `ids=` gives readable names. Together they turn one test into a matrix.",
            "why": "A roaming test needs two or three stations; a security test must run under WPA2, WPA3-SAE and OWE. A factory and a parametrized fixture express both without duplicating test code.",
            "syntax": "@pytest.fixture\ndef make_sta():\n    made = []\n    def _make(mac, **kw): ...; made.append(s); return s\n    yield _make\n    for s in made: s.disconnect()\n\n@pytest.fixture(params=[\"wpa2\", \"wpa3-sae\", \"owe\"])\ndef security(request):\n    return request.param",
            "code": """import pytest  ## Fixtures

from lab import FakeAP, FakeStation  ## Simulated devices


@pytest.fixture  ## A factory fixture: the test gets a function
def make_sta():  ## Tracks everything it creates
    created = []  ## Stations made during this test
    def _make(mac: str, ap: FakeAP, rssi: int = -55) -> FakeStation:  ## The factory the test calls
        sta = FakeStation(mac)  ## Create...
        sta.associate(ap, rssi=rssi)  ## ...and configure
        created.append(sta)  ## Remember for cleanup
        return sta  ## Give it to the test
    yield _make  ## The test can call make_sta(...) any number of times
    for sta in created:  ## Teardown: clean up every station created
        sta.disconnect()  ## Leave no state behind


@pytest.fixture(params=["wpa2-psk", "wpa3-sae", "owe"], ids=["WPA2", "WPA3", "OWE"])  ## Every test using it runs 3 times
def security(request):  ## request.param holds the current parameter
    return request.param  ## e.g. "wpa3-sae"


def test_two_clients_on_one_ap(make_sta):  ## Uses the factory twice
    ap = FakeAP("ap-1")  ## One AP
    a, b = make_sta("aa:01", ap), make_sta("aa:02", ap, rssi=-70)  ## Two configured stations
    assert a.ap is b.ap is ap and b.rssi == -70  ## Both associated to the same AP


def test_security_mode_is_known(security):  ## Runs once per security mode
    assert security in {"wpa2-psk", "wpa3-sae", "owe"}  ## The ids show up in the test names""",
            "under": "A parametrized fixture splits each dependent test into one item per parameter at collection time, so `-v` lists `test_security_mode_is_known[WPA3]` and friends. If a test uses two parametrized fixtures, it runs for the Cartesian product. The fixture is created separately for each parameter, and its teardown runs before the next parameter's setup when the scope allows.",
            "gotchas": [
                {
                    "title": "Returning a single object when tests need several",
                    "runner": "pytest",
                    "files": {"lab.py": LAB_PY},
                    "note": "A plain fixture gives the same object to every request in a test, so 'two stations' are really one. Use a factory fixture.",
                    "wrong": """import pytest
from lab import FakeAP, FakeStation

@pytest.fixture
def sta():
    return FakeStation("aa:01")

def test_two_clients(sta):
    first, second = sta, sta
    first.associate(FakeAP("ap-1")); second.associate(FakeAP("ap-2"))
    assert first.ap.name != second.ap.name""",
                    "fixed": """import pytest
from lab import FakeAP, FakeStation

@pytest.fixture
def make_sta():
    return lambda mac: FakeStation(mac)

def test_two_clients(make_sta):
    first, second = make_sta("aa:01"), make_sta("aa:02")
    first.associate(FakeAP("ap-1")); second.associate(FakeAP("ap-2"))
    assert first.ap.name != second.ap.name""",
                }
            ],
            "best": "Use factory fixtures whenever a test needs a variable number of similar resources, and parametrized fixtures when every test in a group must run under each configuration (security mode, band, bench). Always give parameters readable ids.",
        },
        {
            "title": "autouse, overriding and usefixtures",
            "runner": "pytest",
            "filename": "test_autouse.py",
            "args": ["-q", "-s"],
            "concept": "`autouse=True` makes a fixture run for every test in its scope without being requested, which suits cross-cutting chores such as collecting logs after each test. A fixture defined closer to a test (in the test module, or a deeper conftest) **overrides** one with the same name further out, and can request the outer version by the same name. `@pytest.mark.usefixtures(\"name\")` activates a fixture for a test that doesn't need its value.",
            "why": "Every test should leave behind the AP log and a pcap for triage, without each test author remembering to ask; a roaming module may need a different `ap` fixture (two APs) than the rest of the suite.",
            "syntax": "@pytest.fixture(autouse=True)\ndef collect_logs(request): ...\n\n@pytest.fixture\ndef channel(): return 36      # outer\n# in a test module:\n@pytest.fixture\ndef channel(): return 149     # overrides for this module\n\n@pytest.mark.usefixtures(\"clean_bench\")",
            "code": """import pytest  ## Fixtures and markers


@pytest.fixture(autouse=True)  ## Runs around EVERY test in this module automatically
def collect_artifacts(request):  ## request.node is the test item
    yield  ## The test runs here
    print(f"\\n  saved logs for {request.node.name}")  ## A real version would copy AP logs and pcaps


@pytest.fixture  ## Imagine this came from conftest.py
def channel():  ## The suite-wide default
    return 36  ## UNII-1


@pytest.fixture  ## Activated with usefixtures: no value needed
def clean_bench():  ## e.g. reset attenuators and power-cycle nothing
    print("\\n  bench reset")  ## Side effect only


def test_default_channel(channel):  ## Gets 36
    assert channel == 36  ## Suite default


@pytest.mark.usefixtures("clean_bench")  ## Run clean_bench first; the test doesn't use its value
def test_after_reset():  ## No parameter needed
    assert True  ## Placeholder test""",
            "under": "Autouse fixtures are added to every test's fixture closure within their scope (module here; a conftest makes them apply to its whole directory). Fixture lookup for a name starts at the test's own module, then each conftest from the closest directory outwards, then plugins. That precedence is what makes overriding work.",
            "gotchas": [],
            "best": "Reserve autouse for genuinely universal chores (artifact collection, log markers) and keep them cheap. Override fixtures deliberately in the narrowest conftest or module that needs different behaviour, and prefer usefixtures to unused parameters.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "runner": "pytest",
            "args": ["-v"],
            "prompt": "Write a parametrized fixture `band` over 2G, 5G and 6G and a test asserting each band string ends with 'G'.",
            "solution": "params plus request.param; -v shows one result per band.",
            "solution_code": """import pytest


@pytest.fixture(params=["2G", "5G", "6G"])
def band(request):
    return request.param


def test_band_format(band):
    assert band.endswith("G")""",
        },
        {
            "level": "Medium",
            "runner": "pytest",
            "args": ["-q", "-s"],
            "prompt": "Write a factory fixture `make_capture(iface)` that records started interfaces and prints each one it stops in teardown. Use it for three interfaces in one test.",
            "solution": "Track creations in a list inside the fixture and clean them all up after yield.",
            "solution_code": """import pytest


@pytest.fixture
def make_capture():
    running = []
    def _start(iface):
        running.append(iface)
        return f"capture:{iface}"
    yield _start
    for iface in reversed(running):
        print(f"stop {iface}")


def test_three_captures(make_capture):
    handles = [make_capture(i) for i in ["mon0", "mon1", "mon2"]]
    assert handles[-1] == "capture:mon2\"""",
        },
        {
            "level": "Hard",
            "runner": "pytest",
            "args": ["-v"],
            "prompt": "Combine two parametrized fixtures (band × security) so one test runs for every combination, but make OWE on 2G show a readable id.",
            "solution": "Two parametrized fixtures give the Cartesian product; ids keep names readable.",
            "solution_code": """import pytest


@pytest.fixture(params=["2G", "6G"])
def band(request):
    return request.param


@pytest.fixture(params=["wpa3-sae", "owe"], ids=["SAE", "OWE"])
def security(request):
    return request.param


def test_profile(band, security):
    profile = f"{band}/{security}"
    assert "/" in profile""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "What is a factory fixture and when do you need one?", "a": "A fixture that returns a function which creates objects. Use it when a test needs several similar resources (multiple stations) with different arguments, while the fixture still tracks and cleans up everything it created.", "follow": "How does it clean up? (It keeps a list and tears them all down after yield.)"},
        {"level": "Intermediate", "q": "Parametrized fixture vs @pytest.mark.parametrize?", "a": "A parametrized fixture applies to every test that uses it (and can do setup per parameter, like configuring the AP per security mode). mark.parametrize is per test and passes plain values. Use fixtures for configuration environments, parametrize for data.", "follow": "What happens with two parametrized fixtures? (Cartesian product of their params.)"},
        {"level": "Intermediate", "q": "When is autouse appropriate?", "a": "For cross-cutting work every test in a scope needs, such as artifact collection, log markers or resetting a shared resource. Avoid it for heavy setup most tests don't need, because it's invisible to test readers.", "follow": "Where should autouse fixtures live? (In the conftest of the directory they apply to.)"},
        {"level": "Advanced", "q": "How does fixture overriding work?", "a": "pytest resolves a fixture name from the test module outward through conftest files to plugins; the closest definition wins. An overriding fixture can request the outer one by the same name to extend it.", "follow": "Can a test override a fixture via parametrize? (Yes, parametrizing an argument with the fixture's name overrides it for that test.)"},
    ],
    "quiz": [
        {"q": "Where is the current parameter in a parametrized fixture?", "options": ["request.value", "request.param", "fixture.param", "self.param"], "answer": 1, "why": "request.param."},
        {"q": "A test using fixtures with 2 and 3 params runs how many times?", "options": ["2", "3", "5", "6"], "answer": 3, "why": "Cartesian product."},
        {"q": "What does autouse=True do?", "options": ["Runs the fixture for every test in scope", "Caches forever", "Runs in parallel", "Skips teardown"], "answer": 0, "why": "No request needed."},
        {"q": "How do you use a fixture only for its side effect?", "options": ["@pytest.mark.usefixtures('name')", "import it", "global it", "autouse=False"], "answer": 0, "why": "No unused parameter needed."},
        {"q": "Which definition wins for the same fixture name?", "options": ["The outermost conftest", "The closest to the test", "Alphabetical", "The first imported"], "answer": 1, "why": "Closest scope overrides."},
    ],
    "cards": [
        {"front": "Factory fixture", "back": "Yields a function that creates objects; cleans them all up after yield."},
        {"front": "Parametrized fixture", "back": "`@pytest.fixture(params=[...], ids=[...])` + `request.param`"},
        {"front": "autouse", "back": "Fixture runs for every test in its scope automatically."},
        {"front": "Side-effect-only fixture", "back": "`@pytest.mark.usefixtures('name')`"},
    ],
}


M_5_4 = {
    "id": "5.4",
    "title": "conftest.py Hierarchy",
    "hours": 1.5,
    "summary": "How conftest.py files share fixtures and hooks by directory, overriding per directory, and what belongs in a root conftest versus a plugin.",
    "concepts": [
        {
            "title": "Directory-scoped fixtures with conftest.py",
            "runner": "pytest",
            "filename": "tests/roaming/test_roam.py",
            "args": ["-v"],
            "files": {
                "lab.py": LAB_PY,
                "conftest.py": "import sys, pathlib\nsys.path.insert(0, str(pathlib.Path(__file__).parent))\n\nimport pytest\nfrom lab import FakeAP\n\n\n@pytest.fixture(scope=\"session\")\ndef testbed():\n    return {\"name\": \"bench07\", \"country\": \"IN\"}\n\n\n@pytest.fixture\ndef aps():\n    return [FakeAP(\"ap-1\")]\n",
                "tests/roaming/conftest.py": "import pytest\nfrom lab import FakeAP\n\n\n@pytest.fixture\ndef aps():\n    return [FakeAP(\"ap-1\"), FakeAP(\"ap-2\")]\n",
                "tests/throughput/test_tput.py": "def test_single_ap(aps, testbed):\n    assert len(aps) == 1 and testbed[\"name\"] == \"bench07\"\n",
            },
            "concept": "A `conftest.py` file provides fixtures and hooks to every test in its directory and below, with no imports needed. pytest loads conftest files from the root down to each test's directory, and a deeper conftest can **override** a fixture from a higher one. Put suite-wide fixtures (testbed, logging) in the root conftest, and area-specific ones (multi-AP setups for roaming, traffic generators for throughput) in that area's conftest.",
            "why": "A suite with hundreds of tests stays organised when shared setup lives in a predictable place: the roaming folder automatically gets two APs while throughput tests keep one, and nobody copies fixtures between files.",
            "syntax": "conftest.py                     # testbed, session-wide fixtures\ntests/roaming/conftest.py       # aps -> two APs\ntests/roaming/test_roam.py\ntests/throughput/test_tput.py   # sees the root aps (one AP)",
            "code": """def test_roam_between_two_aps(aps, testbed):  ## aps comes from tests/roaming/conftest.py; testbed from the root conftest
    names = [ap.name for ap in aps]  ## The roaming conftest overrides aps with two APs
    assert names == ["ap-1", "ap-2"]  ## The closest definition wins
    assert testbed["country"] == "IN"  ## Root fixtures are visible everywhere below the root


def test_roaming_needs_two(aps):  ## Same override applies to every test in this folder
    assert len(aps) >= 2  ## Meanwhile tests/throughput still sees one AP""",
            "under": "During collection pytest walks from the rootdir to each test file's directory and imports every `conftest.py` on the way (registering each as a plugin). Fixture lookup then searches from the test's module through those conftests, closest first. Because the files are registered as plugins, they can also implement hooks (Module 5.8), which apply to their directory's tests.",
            "gotchas": [],
            "best": "Keep the root conftest small (testbed, CLI options, artifact collection), put area-specific fixtures in area conftests, and never import from conftest.py in test files. When the same conftest content is needed across repositories, turn it into a plugin (Module 5.9).",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "runner": "pytest",
            "files": {"conftest.py": "import pytest\n\n\n@pytest.fixture\ndef country():\n    return \"IN\"\n"},
            "prompt": "Use a fixture defined in conftest.py from a test file without importing it.",
            "solution": "conftest fixtures are available automatically.",
            "solution_code": """def test_country_code(country):
    assert country == "IN\"""",
        },
        {
            "level": "Medium",
            "runner": "pytest",
            "filename": "tests/dfs/test_dfs.py",
            "args": ["-q"],
            "files": {"conftest.py": "import pytest\n\n\n@pytest.fixture\ndef channel():\n    return 36\n", "tests/dfs/conftest.py": "import pytest\n\n\n@pytest.fixture\ndef channel(channel):\n    return channel + 16\n"},
            "prompt": "Override a root `channel` fixture (36) in tests/dfs/conftest.py so DFS tests get 52, by EXTENDING the outer fixture rather than replacing its value blindly.",
            "solution": "An overriding fixture can request the outer fixture of the same name.",
            "solution_code": """def test_dfs_channel(channel):
    assert channel == 52""",
        },
        {
            "level": "Hard",
            "runner": "pytest",
            "args": ["-q", "-s"],
            "filename": "tests/test_marker_count.py",
            "files": {"conftest.py": "def pytest_collection_finish(session):\n    print(f\"\\ncollected {len(session.items)} tests across the suite\")\n", "tests/test_other.py": "def test_a():\n    pass\n\ndef test_b():\n    pass\n"},
            "prompt": "Implement a hook in the root conftest that prints how many tests were collected across the whole suite.",
            "solution": "pytest_collection_finish receives the session after collection.",
            "solution_code": """def test_c():
    pass""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What is conftest.py?", "a": "A file pytest loads automatically that provides fixtures and hooks to all tests in its directory and subdirectories. No import is needed in test files.", "follow": "Should tests import from conftest? (No; rely on fixture injection.)"},
        {"level": "Intermediate", "q": "How do fixtures get shared across files?", "a": "Define them in a conftest.py at the level of the directory that needs them; every test below can request them by name. Deeper conftests can override them for their subtree.", "follow": "And across repositories? (Package them as a plugin.)"},
        {"level": "Intermediate", "q": "What belongs in the root conftest?", "a": "Truly global items: command-line options, testbed and configuration fixtures, artifact collection and reporting hooks. Area-specific setup belongs in that area's conftest to keep the root small.", "follow": "Why keep it small? (Every test loads it; complexity there affects the whole suite.)"},
    ],
    "quiz": [
        {"q": "Which tests can use a fixture in tests/roaming/conftest.py?", "options": ["All tests", "Tests under tests/roaming/", "Only test_roam.py", "None without import"], "answer": 1, "why": "Its directory and below."},
        {"q": "If root and tests/roaming conftests both define `aps`, a roaming test gets...", "options": ["The root one", "The roaming one", "An error", "Both"], "answer": 1, "why": "Closest wins."},
        {"q": "How do test files access conftest fixtures?", "options": ["import conftest", "By parameter name", "@use_conftest", "They can't"], "answer": 1, "why": "Injection by name."},
        {"q": "Can conftest.py contain hooks?", "options": ["Yes", "No", "Only in plugins", "Only pytest.ini"], "answer": 0, "why": "It's registered as a local plugin."},
    ],
    "cards": [
        {"front": "conftest.py reach", "back": "Its directory and every subdirectory."},
        {"front": "Overriding a fixture by directory", "back": "Define the same name in a deeper conftest."},
        {"front": "Extend an outer fixture", "back": "Request the same name inside the override."},
    ],
}


M_5_5 = {
    "id": "5.5",
    "title": "parametrize",
    "hours": 2.5,
    "summary": "Data-driven tests with @pytest.mark.parametrize, readable ids, per-case marks, stacked parameters for matrices, indirect parametrization and generating cases from data files.",
    "concepts": [
        {
            "title": "@pytest.mark.parametrize, ids and per-case marks",
            "runner": "pytest",
            "filename": "test_matrix.py",
            "args": ["-v", "-rx"],
            "files": {"lab.py": LAB_PY},
            "concept": "`@pytest.mark.parametrize(\"name1,name2\", [(v1, v2), ...])` runs a test once per tuple. `ids=` (or `pytest.param(..., id=\"...\")`) names each case; `pytest.param(..., marks=pytest.mark.xfail(reason=...))` attaches marks to one case. **Stacking** two parametrize decorators produces the Cartesian product, ideal for band × width matrices.",
            "why": "One throughput test body covers every band, width and expected value in a readable table, and known-bad combinations are documented as xfail with a reason rather than deleted.",
            "syntax": "@pytest.mark.parametrize(\"band,width,expected\", [\n    (\"5G\", 80, 900.0),\n    pytest.param(\"6G\", 320, 4800.0, id=\"6G-320MHz\"),\n    pytest.param(\"2G\", 80, 0, marks=pytest.mark.xfail(reason=\"...\")),\n])\n\n@pytest.mark.parametrize(\"band\", [\"5G\", \"6G\"])\n@pytest.mark.parametrize(\"rssi\", [-50, -70])   # 4 cases",
            "code": """import pytest  ## Markers and pytest.param

from lab import throughput_mbps  ## Simulated measurement

CASES = [  ## The test table: one row per case
    pytest.param("5G", 80, 900.0, id="5G-80MHz"),  ## Readable id shown in -v output and reports
    pytest.param("5G", 160, 1800.0, id="5G-160MHz"),  ## Another row
    pytest.param("6G", 320, 4800.0, id="6G-320MHz"),  ## Wi-Fi 7 wide channel
    pytest.param("2G", 80, 600.0, id="2G-80MHz", marks=pytest.mark.xfail(raises=ValueError, reason="80 MHz is not allowed on 2.4 GHz")),  ## Documented known-invalid case
]  ## End of table


@pytest.mark.parametrize("band,width,expected", CASES)  ## Argument names, then the rows
def test_peak_throughput(band, width, expected):  ## Runs once per row
    assert throughput_mbps(band, width) == pytest.approx(expected, rel=0.01)  ## Same check for every case


@pytest.mark.parametrize("rssi", [-50, -65], ids=lambda r: f"rssi{r}")  ## ids can be a function of the value
@pytest.mark.parametrize("band", ["5G", "6G"])  ## Stacked: 2 x 2 = 4 cases
def test_signal_matrix(band, rssi):  ## Cartesian product of both decorators
    assert throughput_mbps(band, 80, rssi=rssi) > 0  ## Placeholder check""",
            "under": "Parametrization happens during collection: each parameter set becomes its own test item with an id in brackets, e.g. `test_peak_throughput[6G-320MHz]`. Values are passed as-is (not copied), so mutable parameters are shared between cases. With stacked decorators, the ids combine in decorator order: `test_signal_matrix[5G-rssi-50]`.",
            "gotchas": [
                {
                    "title": "Looping inside one test instead of parametrizing",
                    "runner": "pytest",
                    "files": {"lab.py": LAB_PY},
                    "note": "The loop stops at the first failing case, hides the others, and reports one opaque test. Parametrize to see every case's result.",
                    "wrong": """from lab import throughput_mbps

def test_all_bands():
    for band, width, floor in [("5G", 80, 950), ("6G", 320, 4000), ("2G", 40, 250)]:
        assert throughput_mbps(band, width) >= floor""",
                    "fixed": """import pytest
from lab import throughput_mbps

@pytest.mark.parametrize("band,width,floor", [("5G", 80, 950), ("6G", 320, 4000), ("2G", 40, 250)])
def test_band(band, width, floor):
    assert throughput_mbps(band, width) >= floor""",
                }
            ],
            "best": "Keep the case table at the top of the module (or in a data file), give every case an id that reads like a report line (`6G-320MHz`), mark known-bad cases xfail with a reason instead of deleting them, and use stacking for full matrices.",
        },
        {
            "title": "indirect parametrization and generating cases from data",
            "runner": "pytest",
            "filename": "test_from_data.py",
            "args": ["-v"],
            "files": {
                "lab.py": LAB_PY,
                "matrix.json": "[\n  {\"id\": \"5G-80\", \"band\": \"5G\", \"width\": 80, \"min_mbps\": 850},\n  {\"id\": \"6G-160\", \"band\": \"6G\", \"width\": 160, \"min_mbps\": 2300},\n  {\"id\": \"6G-320\", \"band\": \"6G\", \"width\": 320, \"min_mbps\": 4600}\n]\n",
                "conftest.py": "import json, pathlib\n\n\ndef pytest_generate_tests(metafunc):\n    if \"case\" in metafunc.fixturenames:\n        rows = json.loads((pathlib.Path(__file__).parent / \"matrix.json\").read_text())\n        metafunc.parametrize(\"case\", rows, ids=[r[\"id\"] for r in rows])\n",
            },
            "concept": "With `indirect=True`, parametrize passes each value to a **fixture** of that name (as `request.param`) instead of straight to the test, so the fixture can do per-case setup (configure the AP for this band). The `pytest_generate_tests(metafunc)` hook generates parameters programmatically, for example from a JSON or YAML matrix file, so non-programmers can add cases without touching Python.",
            "why": "The test matrix for a release usually lives in a file the whole team edits. Generating tests from it, and letting a fixture configure the AP per case, keeps test code tiny while the matrix grows.",
            "syntax": "@pytest.mark.parametrize(\"configured_ap\", [\"5G\", \"6G\"], indirect=True)\ndef test_x(configured_ap): ...\n\ndef pytest_generate_tests(metafunc):          # in conftest.py\n    if \"case\" in metafunc.fixturenames:\n        metafunc.parametrize(\"case\", rows, ids=[r[\"id\"] for r in rows])",
            "code": """import pytest  ## Fixtures and markers

from lab import FakeAP, throughput_mbps  ## Simulated devices


@pytest.fixture  ## Receives each parametrize value via request.param (indirect)
def configured_ap(request):  ## Per-case setup lives here, not in the test
    ap = FakeAP("ap-1")  ## Fresh AP per case
    ap.set_channel(request.param, {"5G": 36, "6G": 37}[request.param])  ## Configure for this band
    return ap  ## The test receives the configured AP


@pytest.mark.parametrize("configured_ap", ["5G", "6G"], indirect=True)  ## Values go to the fixture, not the test
def test_ap_configured(configured_ap):  ## Gets a ready AP for each band
    assert len(configured_ap.channels) == 1  ## Exactly one radio configured


def test_matrix_row(case):  ## `case` is generated by pytest_generate_tests from matrix.json
    assert throughput_mbps(case["band"], case["width"]) >= case["min_mbps"]  ## One test per row in the file""",
            "under": "`pytest_generate_tests` is called once per test function during collection with a `metafunc` describing that function's arguments; calling `metafunc.parametrize` adds parameter sets just like the decorator. With indirect parametrization, pytest marks the argument as coming from a fixture and supplies the value on `request.param` when it builds that fixture for each case.",
            "gotchas": [],
            "best": "Generate tests from a version-controlled matrix file for anything the team edits often, put per-case device configuration in indirect fixtures, and validate the matrix file's format (pydantic, Module 4.4) in the hook so a typo fails collection clearly.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "runner": "pytest",
            "args": ["-v"],
            "prompt": "Parametrize a test over channels 36, 52 and 149 asserting `is_dfs(ch)` matches an expected flag.",
            "solution": "Pairs of (channel, expected).",
            "solution_code": """import pytest


def is_dfs(ch):
    return 52 <= ch <= 144


@pytest.mark.parametrize("ch,expected", [(36, False), (52, True), (149, False)])
def test_is_dfs(ch, expected):
    assert is_dfs(ch) is expected""",
        },
        {
            "level": "Medium",
            "runner": "pytest",
            "args": ["-v"],
            "prompt": "Build a 2 × 3 matrix (band 5G/6G × width 80/160/320) with stacked parametrize, and skip the 5G-320 combination with pytest.skip inside the test.",
            "solution": "Stacking gives 6 cases; skip the invalid one explicitly.",
            "solution_code": """import pytest


@pytest.mark.parametrize("width", [80, 160, 320])
@pytest.mark.parametrize("band", ["5G", "6G"])
def test_width_supported(band, width):
    if band == "5G" and width == 320:
        pytest.skip("320 MHz exists only in 6 GHz")
    assert width <= 320""",
        },
        {
            "level": "Hard",
            "runner": "pytest",
            "args": ["-v"],
            "prompt": "Write test cases with pytest.param where one case is marked xfail(strict=True) for a known DUT bug, and show what happens when the bug is fixed (the case unexpectedly passes).",
            "solution": "A strict xfail that passes becomes a FAILED test ('XPASS(strict)'), prompting you to remove the mark.",
            "solution_code": """import pytest


def roam_latency_ms(mode):
    return {"11r": 18, "11k": 42, "legacy": 95}[mode]


@pytest.mark.parametrize("mode,limit", [
    pytest.param("11r", 50, id="11r"),
    pytest.param("11k", 50, id="11k", marks=pytest.mark.xfail(strict=True, reason="BUG-1234: 11k roams slow")),
    pytest.param("legacy", 100, id="legacy"),
])
def test_roam_latency(mode, limit):
    assert roam_latency_ms(mode) <= limit""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Parametrize vs a loop inside the test?", "a": "Parametrize creates one test per case: every case runs and reports independently, failures name the case, and you can select or rerun one case by id. A loop stops at the first failure and hides the rest.", "follow": "How do you give cases readable names? (ids= or pytest.param(..., id=...).)"},
        {"level": "Intermediate", "q": "What does indirect=True do?", "a": "It routes each parameter value to the fixture with the same name (as request.param) instead of passing it to the test directly, so the fixture can perform per-case setup and teardown.", "follow": "Can you make only some arguments indirect? (Yes: indirect=['arg1'].)"},
        {"level": "Intermediate", "q": "How do you mark one parametrized case as expected to fail?", "a": "pytest.param(values, marks=pytest.mark.xfail(reason='BUG-123', strict=True)). With strict=True, an unexpected pass fails the run, so the mark is removed when the bug is fixed.", "follow": "Why strict? (To avoid stale xfails hiding fixed bugs.)"},
        {"level": "Advanced", "q": "How would you drive tests from a YAML matrix maintained by test planners?", "a": "Implement pytest_generate_tests in conftest: load and validate the YAML, then metafunc.parametrize the relevant argument with ids built from each row. Per-case device setup goes in indirect fixtures.", "follow": "How do you keep it fast? (Load the file once, e.g. cached at module level or in pytest_configure.)"},
    ],
    "quiz": [
        {"q": "Stacking @parametrize('a', [1,2]) and @parametrize('b', [3,4,5]) gives...", "options": ["2 tests", "5 tests", "6 tests", "1 test"], "answer": 2, "why": "2 × 3."},
        {"q": "How do you attach xfail to one case?", "options": ["@xfail on the test", "pytest.param(..., marks=pytest.mark.xfail)", "ids='xfail'", "skip=True"], "answer": 1, "why": "Per-case marks via pytest.param."},
        {"q": "With indirect=True the value goes to...", "options": ["The test", "The fixture of that name", "conftest", "The hook"], "answer": 1, "why": "As request.param."},
        {"q": "Which hook generates parameters programmatically?", "options": ["pytest_configure", "pytest_generate_tests", "pytest_runtest_call", "pytest_addoption"], "answer": 1, "why": "Called per test function at collection."},
        {"q": "What does XPASS(strict) cause?", "options": ["Nothing", "The test is reported as failed", "A skip", "A warning only"], "answer": 1, "why": "Strict xfails must fail."},
    ],
    "cards": [
        {"front": "Table-driven test", "back": "`@pytest.mark.parametrize('a,b', [(1, 2), ...])`"},
        {"front": "Readable case id", "back": "`pytest.param(..., id='6G-320MHz')`"},
        {"front": "Per-case mark", "back": "`pytest.param(..., marks=pytest.mark.xfail(reason=...))`"},
        {"front": "Per-case fixture setup", "back": "`indirect=True`"},
        {"front": "Cases from a data file", "back": "`pytest_generate_tests(metafunc)` + `metafunc.parametrize`"},
    ],
}
