"""Phase 5 content: modules 5.6-5.10 (pytest)."""

from lab_support import LAB_PY

MARKERS_INI = """[pytest]
addopts = --strict-markers
markers =
    smoke: quick checks that run on every commit
    hw: needs a real access point on the bench
    band(name): radio band the test targets
"""

M_5_6 = {
    "id": "5.6",
    "title": "Markers",
    "hours": 2,
    "summary": "Tag tests with built-in and custom markers, register them so typos fail loudly, select with -m, and read marker arguments from fixtures.",
    "concepts": [
        {
            "title": "skip, skipif, xfail and custom markers",
            "runner": "pytest",
            "filename": "test_markers.py",
            "files": {"lab.py": LAB_PY, "pytest.ini": MARKERS_INI},
            "args": ["-v", "-m", "smoke and not hw", "-rxs"],
            "concept": "A marker is a label attached to a test with `@pytest.mark.<name>`. Built-ins change how a test runs: `skip` and `skipif(condition, reason=...)` don't run it, `xfail(reason=..., raises=..., strict=...)` runs it and expects a failure. Custom markers (`smoke`, `hw`) only label tests; you register them in `pytest.ini` and select with `-m \"smoke and not hw\"`. With `--strict-markers` an unregistered marker is an error instead of a silent no-op.",
            "why": "A Wi-Fi suite mixes 10-second smoke checks, hour-long soak tests and tests that need a real AP. Markers let one codebase serve every pipeline stage: `-m smoke` on each commit, `-m \"not hw\"` in the cloud, everything on the nightly bench.",
            "syntax": "@pytest.mark.smoke\n@pytest.mark.skipif(cond, reason=\"...\")\n@pytest.mark.xfail(reason=\"BUG-1\", raises=ValueError, strict=True)\n\n$ pytest -m \"smoke and not hw\"",
            "code": """import sys  ## Used in a skipif condition

import pytest  ## Markers live under pytest.mark

from lab import FakeAP  ## Simulated access point


@pytest.mark.smoke  ## Custom marker, registered in pytest.ini
def test_ap_has_three_radios():  ## Selected by -m smoke
    assert FakeAP("ap-1").bands == {"2G", "5G", "6G"}  ## Fast, no hardware


@pytest.mark.hw  ## Needs a real AP, so "not hw" deselects it
def test_real_reboot():  ## Would talk to hardware
    raise RuntimeError("no hardware in CI")  ## Never runs in this selection


@pytest.mark.smoke  ## Markers stack: this test is smoke...
@pytest.mark.skipif(sys.platform == "linux", reason="demo: skipped on Linux")  ## ...and skipped when the condition is true
def test_windows_driver_version():  ## Would check a Windows-only driver
    assert True  ## Not reached on Linux


@pytest.mark.smoke  ## Also part of the smoke set
@pytest.mark.xfail(reason="BUG-2211: 5G-only SKU rejects 6G config", raises=ValueError, strict=True)  ## Known bug, must fail with ValueError
def test_6g_on_5g_only_sku():  ## Documents a known issue
    FakeAP("ap-2", bands=("5G",)).set_channel("6G", 37)  ## Raises ValueError, so the result is XFAIL""",
            "under": "Markers are stored on the collected item (`item.iter_markers()`), and `-m` evaluates a boolean expression over marker names. `skipif` conditions are evaluated during collection; an `xfail` test still runs, and its outcome becomes XFAIL (failed as expected) or XPASS (passed unexpectedly). With `strict=True` an XPASS is reported as a failure, so a fixed bug forces you to remove the marker. `-rxs` adds xfail and skip reasons to the short summary.",
            "gotchas": [
                {
                    "title": "A typo in a marker name",
                    "runner": "pytest",
                    "files": {"pytest.ini": MARKERS_INI},
                    "note": "Without `--strict-markers`, `@pytest.mark.smok` just creates a new, unused marker, and `-m smoke` silently skips the test. With it (set in addopts above), collection fails with a clear message.",
                    "wrong": """import pytest


@pytest.mark.smok
def test_beacon_interval():
    assert 100 == 100""",
                    "fixed": """import pytest


@pytest.mark.smoke
def test_beacon_interval():
    assert 100 == 100""",
                },
                {
                    "title": "Non-strict xfail hides a fixed bug",
                    "runner": "pytest",
                    "args": ["-q", "-rX"],
                    "note": "A non-strict xfail that starts passing is reported as XPASS and the run stays green, so nobody notices the bug was fixed (or that the test no longer tests anything). Make xfails strict, per marker or with `xfail_strict = true` in pytest.ini.",
                    "wrong": """import pytest


@pytest.mark.xfail(reason="BUG-1180: 160 MHz drops to 80")
def test_160mhz_width():
    assert 160 == 160""",
                    "fixed": """import pytest


@pytest.mark.xfail(reason="BUG-1180: 160 MHz drops to 80", strict=True)
def test_160mhz_width():
    assert 160 == 160""",
                },
            ],
            "best": "Register every custom marker with a description, enable `--strict-markers` and `xfail_strict = true`, always give a reason that names a bug id, and pass `raises=` to xfail so an unrelated crash isn't mistaken for the known bug.",
        },
        {
            "title": "Markers with arguments, read by fixtures",
            "runner": "pytest",
            "filename": "test_band_marker.py",
            "files": {"lab.py": LAB_PY, "pytest.ini": MARKERS_INI},
            "args": ["-v", "-s"],
            "concept": "A marker can carry arguments: `@pytest.mark.band(\"6G\")`. A fixture reads them through `request.node.get_closest_marker(\"band\")`, which returns the nearest marker (function, then class, then module) or None. `pytestmark = pytest.mark.band(\"5G\")` at module level marks every test in the file, and a function-level marker overrides it.",
            "why": "It's a clean way to declare what a test needs (a band, a security mode, a firmware feature) while one shared fixture does the setup. Tests stay declarative and the bench logic lives in one place.",
            "syntax": "pytestmark = pytest.mark.band(\"5G\")\n\nmarker = request.node.get_closest_marker(\"band\")\nband = marker.args[0] if marker else default",
            "code": """import pytest  ## For marks and fixtures

from lab import FakeAP  ## Simulated AP

pytestmark = pytest.mark.band("5G")  ## Module-level: every test here defaults to 5G
DEFAULT_CHANNEL = {"2G": 6, "5G": 36, "6G": 37}  ## Primary channel per band


@pytest.fixture  ## Shared setup that adapts to the marker
def radio(request):  ## request gives access to the test item
    marker = request.node.get_closest_marker("band")  ## Nearest band marker (function beats module)
    band = marker.args[0]  ## Positional argument of the marker
    ap = FakeAP("ap-1")  ## Fresh AP
    ap.set_channel(band, DEFAULT_CHANNEL[band])  ## Configure the requested band
    print(f"configured {band} ch{ap.channels[band]}", end=" ")  ## Visible with -s
    return band, ap  ## The test gets both


def test_uses_module_default(radio):  ## Inherits pytestmark
    assert radio[0] == "5G"  ## Module default applied


@pytest.mark.band("6G")  ## Function-level marker wins
def test_overrides_band(radio):  ## Closest marker is the function's
    band, ap = radio  ## Unpack the fixture value
    assert ap.channels[band] == 37  ## 6 GHz primary channel""",
            "under": "Markers accumulate from module to class to function on each item. `get_closest_marker` walks from the item outwards, while `iter_markers(name)` yields all of them closest first. The marker object exposes `.name`, `.args` and `.kwargs`.",
            "gotchas": [],
            "best": "Use marker arguments for what a test needs and fixtures for how to provide it. Give the fixture a sensible default when the marker is absent, and validate the arguments (unknown band → `pytest.fail`) so mistakes surface clearly.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "runner": "pytest",
            "files": {"pytest.ini": "[pytest]\naddopts = --strict-markers\nmarkers =\n    regression: tests for fixed bugs\n"},
            "args": ["-v", "-m", "regression"],
            "prompt": "Register a `regression` marker in pytest.ini, mark one of two tests with it, and run only regression tests.",
            "solution": "Register the marker under `markers =`, decorate one test, and select it with `-m regression`; the other is deselected.",
            "solution_code": """import pytest


@pytest.mark.regression
def test_bug_1042_dfs_channel_kept_after_reboot():
    assert 52 in range(52, 145)


def test_new_feature():
    assert True""",
        },
        {
            "level": "Medium",
            "runner": "pytest",
            "args": ["-q", "-rs"],
            "prompt": "Skip every test in a module when an optional vendor library (`lanforge_api`) isn't installed.",
            "solution": "`pytest.importorskip` at module level skips the whole module during collection if the import fails, and returns the module if it succeeds.",
            "solution_code": """import pytest

lanforge = pytest.importorskip("lanforge_api")


def test_create_station():
    assert lanforge.create_station("sta1")""",
        },
        {
            "level": "Hard",
            "runner": "pytest",
            "files": {"lab.py": LAB_PY, "pytest.ini": "[pytest]\naddopts = --strict-markers\nmarkers =\n    requires(band): test needs this radio band\n"},
            "args": ["-v", "-rs"],
            "prompt": "Write an autouse fixture that skips any test marked `@pytest.mark.requires(band=...)` when the bench AP doesn't have that band. The bench AP is 2G/5G only.",
            "solution": "Read the marker's kwargs in an autouse fixture and call `pytest.skip` with a reason when the band is missing.",
            "solution_code": """import pytest
from lab import FakeAP

BENCH_AP = FakeAP("bench-ap", bands=("2G", "5G"))


@pytest.fixture(autouse=True)
def _check_band(request):
    marker = request.node.get_closest_marker("requires")
    if marker and marker.kwargs["band"] not in BENCH_AP.bands:
        pytest.skip(f"bench AP has no {marker.kwargs['band']} radio")


@pytest.mark.requires(band="5G")
def test_5g_channel():
    BENCH_AP.set_channel("5G", 149)


@pytest.mark.requires(band="6G")
def test_6g_channel():
    BENCH_AP.set_channel("6G", 37)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What's the difference between skip and xfail?", "a": "skip doesn't run the test (environment not suitable). xfail runs it and expects failure (known bug). XFAIL is the expected outcome; XPASS means it unexpectedly passed, which fails the run if strict=True.", "follow": "When would you use skipif instead of skip? (When the condition is known at collection time, e.g. platform or library version.)"},
        {"level": "Intermediate", "q": "Why use --strict-markers?", "a": "Unregistered markers become collection errors, so typos like `smok` can't silently drop tests out of a `-m smoke` selection. Registering also documents markers in `pytest --markers`.", "follow": "Where do you register markers? (pytest.ini/pyproject markers list, or config.addinivalue_line in pytest_configure.)"},
        {"level": "Intermediate", "q": "How does a fixture read a marker's arguments?", "a": "`request.node.get_closest_marker('name')` returns the marker or None; use `.args` and `.kwargs`. Module-level `pytestmark` and class markers are included, closest first.", "follow": "How would you apply a marker to every test in a file? (pytestmark = ... at module level.)"},
        {"level": "Advanced", "q": "How would you organise markers for a Wi-Fi regression suite across CI stages?", "a": "Speed markers (smoke, slow, soak), resource markers (hw, attenuator, sniffer) and scope markers (band, security). Commit pipeline: `-m \"smoke and not hw\"`; nightly bench: `-m \"not soak\"`; weekly: everything. Resource markers also let a scheduler route tests to benches that have the hardware.", "follow": "How would you enforce that every test has exactly one speed marker? (A pytest_collection_modifyitems hook that errors on violations.)"},
    ],
    "quiz": [
        {"q": "`-m \"smoke and not hw\"` selects...", "options": ["All smoke tests", "Smoke tests that aren't marked hw", "Tests named smoke", "hw tests only"], "answer": 1, "why": "A boolean expression over marker names."},
        {"q": "A strict xfail test passes. The result is...", "options": ["XPASS, run green", "FAILED", "SKIPPED", "PASSED"], "answer": 1, "why": "strict=True turns XPASS into a failure."},
        {"q": "What does --strict-markers change?", "options": ["Runs markers in order", "Unregistered markers are errors", "Skips unmarked tests", "Makes xfail strict"], "answer": 1, "why": "It catches typos and undocumented markers."},
        {"q": "Which call reads the nearest marker?", "options": ["request.marker", "request.node.get_closest_marker(name)", "pytest.get_marker(name)", "item.marks[0]"], "answer": 1, "why": "Function beats class beats module."},
        {"q": "`pytest.importorskip('x')` when x is missing...", "options": ["Raises ImportError", "Skips the module/test", "Installs x", "Marks xfail"], "answer": 1, "why": "It skips, with the import error as the reason."},
    ],
    "cards": [
        {"front": "skip vs xfail", "back": "skip: don't run. xfail: run and expect failure (XFAIL/XPASS)"},
        {"front": "Register markers", "back": "pytest.ini `markers =` list + `--strict-markers`"},
        {"front": "Mark a whole module", "back": "`pytestmark = pytest.mark.name` at top level"},
        {"front": "Read marker args", "back": "`request.node.get_closest_marker('band').args`"},
        {"front": "Show skip/xfail reasons", "back": "`-rsx` (or -ra for all)"},
    ],
}


ADDOPT_CONFTEST = """import os

import pytest


def pytest_addoption(parser):
    group = parser.getgroup("wifi bench")
    group.addoption("--dut-ip", default=os.environ.get("DUT_IP", "192.0.2.1"),
                    help="management IP of the device under test")
    group.addoption("--band", choices=["2G", "5G", "6G"], default="5G", help="band to test")
    group.addoption("--soak-minutes", type=int, default=0, help="run soak tests for N minutes")


@pytest.fixture(scope="session")
def bench(request):
    cfg = request.config
    return {
        "dut_ip": cfg.getoption("--dut-ip"),
        "band": cfg.getoption("band"),
        "soak": cfg.getoption("soak_minutes"),
    }
"""

M_5_7 = {
    "id": "5.7",
    "title": "Configuration & pytest_addoption",
    "hours": 2,
    "summary": "Configure pytest with pytest.ini or pyproject.toml, add your own command-line options and ini settings, and feed them to tests through fixtures.",
    "concepts": [
        {
            "title": "pytest.ini, pyproject.toml and the rootdir",
            "runner": "pytest",
            "filename": "tests/check_dfs.py",
            "files": {"pytest.ini": """[pytest]
testpaths = tests
python_files = test_*.py check_*.py
addopts = -ra --strict-markers
xfail_strict = true
markers =
    dfs: radar-detection channels
filterwarnings =
    error::DeprecationWarning
"""},
            "args": ["-v"],
            "concept": "pytest reads one config file: the first of `pytest.ini`, `pyproject.toml` (`[tool.pytest.ini_options]`), `tox.ini` or `setup.cfg` it finds walking up from the test paths. Its directory becomes the **rootdir**, which anchors node ids. Common settings: `testpaths` (where to look when no path is given), `python_files` (extra file patterns), `addopts` (options always applied), `markers`, `xfail_strict` and `filterwarnings`.",
            "why": "Every engineer and every CI job should run the suite the same way. Putting the options in the config file instead of a README means `pytest` alone does the right thing.",
            "syntax": "# pytest.ini\n[pytest]\ntestpaths = tests\naddopts = -ra --strict-markers\n\n# pyproject.toml\n[tool.pytest.ini_options]\ntestpaths = [\"tests\"]",
            "code": """import pytest  ## For the marker

DFS_CHANNELS = range(52, 145)  ## 5 GHz channels that need radar detection


@pytest.mark.dfs  ## Registered in pytest.ini, so --strict-markers accepts it
def test_52_is_dfs():  ## Collected because python_files includes check_*.py
    assert 52 in DFS_CHANNELS  ## Passes


def test_36_is_not_dfs():  ## Lives in tests/, found through testpaths
    assert 36 not in DFS_CHANNELS  ## Passes""",
            "under": "The header line `configfile: pytest.ini` and `testpaths: tests` confirm which file was used. `addopts` is prepended to the command line, so `-ra` (short summary of all non-passing outcomes) is always on. `filterwarnings = error::DeprecationWarning` turns deprecation warnings into test failures, which catches library upgrades early. `-o key=value` overrides an ini value for one run.",
            "gotchas": [],
            "best": "Keep exactly one config file (prefer `[tool.pytest.ini_options]` in pyproject.toml for packaged projects), set `testpaths`, `--strict-markers`, `xfail_strict` and warning filters there, and check the header's `configfile:` line when something behaves unexpectedly.",
        },
        {
            "title": "Custom command-line options with pytest_addoption",
            "runner": "pytest",
            "filename": "tests/test_bench.py",
            "files": {"conftest.py": ADDOPT_CONFTEST},
            "args": ["-q", "-s", "--dut-ip", "192.0.2.10", "--band", "6G"],
            "concept": "The `pytest_addoption(parser)` hook in the root conftest.py adds options with the same API as argparse (`default`, `choices`, `type`, `help`). Read them with `request.config.getoption(\"--name\")` (or the dest name, `band`, `soak_minutes`). Wrap them in a session fixture so tests depend on a `bench` object, not on the command line.",
            "why": "The same suite runs against different DUTs, bands and durations. Options make that explicit: `pytest --dut-ip 10.1.1.5 --band 6G`, documented in `pytest --help` under your own group.",
            "syntax": "def pytest_addoption(parser):\n    parser.addoption(\"--band\", choices=[...], default=\"5G\")\n\nrequest.config.getoption(\"band\")",
            "code": """def test_bench_settings(bench):  ## Uses the session fixture from conftest.py
    print(f"\\nDUT {bench['dut_ip']} on {bench['band']}, soak {bench['soak']} min")  ## Shows the parsed values
    assert bench["band"] in {"2G", "5G", "6G"}  ## choices already guarantees this


def test_soak_disabled_by_default(bench):  ## --soak-minutes wasn't given
    assert bench["soak"] == 0  ## The int default""",
            "under": "Option hooks must live in the root conftest.py or a plugin, because pytest parses the command line before it walks into subdirectories. The default here falls back to the `DUT_IP` environment variable, a common pattern for CI secrets and bench assignments. `type=int` converts the value, and an invalid choice stops the run with a usage error (exit code 4).",
            "gotchas": [
                {
                    "title": "Defining pytest_addoption in a sub-directory conftest",
                    "runner": "pytest",
                    "filename": "tests/radio/test_band.py",
                    "files": {"tests/radio/conftest.py": "def pytest_addoption(parser):\n    parser.addoption(\"--band\", default=\"5G\")\n"},
                    "fixed_files": {"conftest.py": "def pytest_addoption(parser):\n    parser.addoption(\"--band\", default=\"5G\")\n"},
                    "args": ["-q", "--band", "6G"],
                    "note": "Run from the project root, pytest parses `--band` before it has loaded `tests/radio/conftest.py`, so the option is unknown. Move the hook to the root conftest.py (or a plugin).",
                    "wrong": """def test_band(request):
    assert request.config.getoption("band") == "6G\"""",
                    "fixed": """# conftest.py moved to the project root
def test_band(request):
    assert request.config.getoption("band") == "6G\"""",
                },
            ],
            "best": "Put options in a named group, give every option a default and help text, fall back to environment variables for CI, expose them through one session fixture, and validate early (`choices`, `type`) so a typo fails before any hardware is touched.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "runner": "pytest",
            "filename": "tests/test_smoke.py",
            "files": {"pyproject.toml": "[project]\nname = \"wifi-tests\"\nversion = \"0.1.0\"\n\n[tool.pytest.ini_options]\ntestpaths = [\"tests\"]\naddopts = \"-ra\"\n"},
            "args": ["-v"],
            "prompt": "Configure pytest through pyproject.toml so it only looks in `tests/` and always shows the short summary.",
            "solution": "`[tool.pytest.ini_options]` with `testpaths` and `addopts`; the header confirms `configfile: pyproject.toml`.",
            "solution_code": """def test_ssid_length():
    assert len("lab-6g") <= 32""",
        },
        {
            "level": "Medium",
            "runner": "pytest",
            "files": {"conftest.py": """import pytest


def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", help="also run slow tests")


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: long-running test")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        return
    skip_slow = pytest.mark.skip(reason="needs --runslow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
"""},
            "args": ["-v", "-rs"],
            "prompt": "Add a `--runslow` flag: tests marked `slow` are skipped unless it's given.",
            "solution": "Register the option and marker, then in pytest_collection_modifyitems add a skip marker to slow items when the flag is off.",
            "solution_code": """import pytest


def test_quick():
    assert True


@pytest.mark.slow
def test_overnight_soak():
    assert True""",
        },
        {
            "level": "Hard",
            "runner": "pytest",
            "files": {
                "conftest.py": """import pytest


def pytest_addoption(parser):
    parser.addini("bench_ap", help="name of the bench access point", default="ap-1")


@pytest.fixture
def bench_ap(request):
    return request.config.getini("bench_ap")
""",
                "pytest.ini": "[pytest]\nbench_ap = ap-lab-07\n",
            },
            "args": ["-q", "-s", "-o", "bench_ap=ap-hotdesk-2"],
            "prompt": "Add an ini setting `bench_ap` (set in pytest.ini) read by a fixture, then override it for one run from the command line.",
            "solution": "`parser.addini` declares it, `config.getini` reads it, and `-o bench_ap=...` overrides the file's value without editing it.",
            "solution_code": """def test_bench_name(bench_ap):
    print(f"\\nusing {bench_ap}")
    assert bench_ap.startswith("ap-")""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Where can pytest configuration live?", "a": "pytest.ini, pyproject.toml under [tool.pytest.ini_options], tox.ini or setup.cfg under [tool:pytest]. The first one found determines the rootdir. pytest.ini wins even if empty.", "follow": "What is the rootdir used for? (Node ids, conftest discovery anchor, cache dir location.)"},
        {"level": "Intermediate", "q": "How do you add a custom command-line option?", "a": "Implement pytest_addoption(parser) in the root conftest.py or a plugin, call parser.addoption with argparse-style arguments, and read it via request.config.getoption in a fixture.", "follow": "Why must it be in the root conftest? (Options are parsed before sub-directory conftests are loaded.)"},
        {"level": "Intermediate", "q": "What does addopts do and what's a risk?", "a": "It prepends options to every run. Risk: options that need a plugin (like -n for xdist) break environments without it, and surprising defaults confuse newcomers. Keep it to universally safe options like -ra and --strict-markers.", "follow": "How do you override an ini value once? (-o name=value.)"},
        {"level": "Advanced", "q": "How would you pass secrets like device passwords to a test suite?", "a": "Never in config files or options that end up in logs. Read from environment variables injected by the CI secret store (or a vault client) in a session fixture, mask them in reports, and fail fast with a clear message if missing.", "follow": "How would you keep them out of failure tracebacks? (Wrap in a small class whose __repr__ hides the value.)"},
    ],
    "quiz": [
        {"q": "Which file wins if both pytest.ini and pyproject.toml exist in the same dir?", "options": ["pyproject.toml", "pytest.ini", "Both merged", "Neither"], "answer": 1, "why": "pytest.ini has precedence."},
        {"q": "`testpaths = tests` means...", "options": ["Only tests/ can contain tests", "Search tests/ when no path is given", "Ignore tests/", "Run tests/ twice"], "answer": 1, "why": "It's the default search path."},
        {"q": "Where must pytest_addoption be defined?", "options": ["Any conftest", "Root conftest or a plugin", "A test file", "pytest.ini"], "answer": 1, "why": "Options are parsed early."},
        {"q": "Reading an ini value declared with parser.addini:", "options": ["config.getoption", "config.getini", "os.environ", "request.param"], "answer": 1, "why": "getini for ini settings."},
        {"q": "Exit code for an invalid --band choice?", "options": ["1", "2", "4", "5"], "answer": 2, "why": "Usage errors return 4."},
    ],
    "cards": [
        {"front": "pyproject pytest section", "back": "`[tool.pytest.ini_options]`"},
        {"front": "Add a CLI option", "back": "`pytest_addoption(parser)` in root conftest → `config.getoption`"},
        {"front": "Add an ini setting", "back": "`parser.addini(name, help, default)` → `config.getini(name)`"},
        {"front": "Override ini once", "back": "`pytest -o name=value`"},
        {"front": "Turn warnings into errors", "back": "`filterwarnings = error::DeprecationWarning`"},
    ],
}


HOOKS_CONFTEST = """import pytest

RESULTS = []


def pytest_report_header(config):
    return ["bench: lab-07 (simulated)", "firmware: 7.4.1"]


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "soak" in item.name:
            item.add_marker(pytest.mark.slow)
    items.sort(key=lambda item: item.get_closest_marker("smoke") is None)


def pytest_configure(config):
    config.addinivalue_line("markers", "smoke: fast checks")
    config.addinivalue_line("markers", "slow: long-running")
"""

REPORT_CONFTEST = """import pytest

RESULTS = []


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    report = yield
    setattr(item, "rep_" + report.when, report)
    return report


@pytest.fixture(autouse=True)
def logs_on_failure(request):
    yield
    report = getattr(request.node, "rep_call", None)
    if report is not None and report.failed:
        print(f"\\n  [teardown] collecting AP logs for {request.node.name}")


@pytest.fixture
def record_tput():
    def record(case, mbps):
        RESULTS.append((case, mbps))
    return record


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    terminalreporter.write_sep("-", "throughput results")
    for case, mbps in RESULTS:
        terminalreporter.write_line(f"{case:<10} {mbps:>8.1f} Mbps")
"""

M_5_8 = {
    "id": "5.8",
    "title": "Hooks",
    "hours": 2.5,
    "summary": "Extend pytest itself: change the collected items, add header lines, inspect each test's report, and print your own summary at the end.",
    "concepts": [
        {
            "title": "Collection hooks: reorder and auto-mark",
            "runner": "pytest",
            "filename": "test_suite.py",
            "files": {"conftest.py": HOOKS_CONFTEST},
            "args": ["-v", "-m", "not slow"],
            "concept": "Hooks are functions with reserved names (`pytest_*`) that pytest calls at defined points. Put them in conftest.py or a plugin. `pytest_configure` runs at startup (register markers), `pytest_report_header` adds lines to the header, and `pytest_collection_modifyitems(config, items)` receives the full list of collected tests, which you can reorder, filter or mark in place.",
            "why": "Suite-wide policy belongs in one place: run smoke tests first so a broken build fails in seconds, tag anything named `soak` as slow automatically, print which bench and firmware were used so every log is self-describing.",
            "syntax": "def pytest_collection_modifyitems(config, items):\n    items.sort(key=...)\n    item.add_marker(pytest.mark.slow)",
            "code": """import pytest  ## For the smoke marker


def test_throughput_6g():  ## Collected first in the file, runs after smoke tests
    assert True  ## Placeholder


def test_soak_24h():  ## Name contains "soak", so the hook marks it slow
    assert True  ## Deselected by -m "not slow"


@pytest.mark.smoke  ## The hook moves smoke tests to the front
def test_ap_boots():  ## Runs first despite being defined last
    assert True  ## Placeholder""",
            "under": "pytest's plugin manager (pluggy) collects every `pytest_*` function from conftest files and plugins and calls them all for each hook. Markers added in `pytest_collection_modifyitems` are visible to `-m` because deselection runs after it. Sorting with a boolean key works because False sorts before True and `sort` is stable, so the original order is kept within each group.",
            "gotchas": [
                {
                    "title": "Misspelling a hook name",
                    "runner": "pytest",
                    "files": {"conftest.py": "def pytest_collection_modifyitem(config, items):\n    items.reverse()\n"},
                    "fixed_files": {"conftest.py": "def pytest_collection_modifyitems(config, items):\n    items.reverse()\n"},
                    "note": "pytest validates `pytest_*` function names in conftest files and plugins: a name that isn't a known hook is an error at startup, not a silently ignored function. Read the message, it names the bad hook.",
                    "wrong": """def test_a():
    pass""",
                    "fixed": """def test_a():
    pass""",
                },
            ],
            "best": "Keep hooks small and in the root conftest (or a plugin), use `pytest_configure` to register markers you add, and prefer marking or sorting over silently dropping tests. If you must remove items, report them through `config.hook.pytest_deselected(items=...)` so the summary counts them.",
        },
        {
            "title": "Reporting hooks: per-test reports and a custom summary",
            "runner": "pytest",
            "filename": "test_tput.py",
            "files": {"conftest.py": REPORT_CONFTEST, "lab.py": LAB_PY},
            "args": ["-q", "-s"],
            "concept": "For every test pytest builds three reports (setup, call, teardown) through `pytest_runtest_makereport`. A **wrapper** hook (`@pytest.hookimpl(wrapper=True)`) runs around the other implementations: code before `yield` runs first, `yield` returns the report, and you return it. Storing it on the item (`item.rep_call`) lets a fixture's teardown know whether the test failed. `pytest_terminal_summary` prints your own section at the end.",
            "why": "On a bench you want logs, captures and screenshots only for failures (they're large), and a summary table of measured throughput in the console that people actually read. These two hooks are the standard way to do both.",
            "syntax": "@pytest.hookimpl(wrapper=True)\ndef pytest_runtest_makereport(item, call):\n    report = yield\n    item.rep_call = report  # when == 'call'\n    return report",
            "code": """from lab import throughput_mbps  ## Simulated measurement


def test_5g_80(record_tput):  ## record_tput comes from conftest.py
    mbps = throughput_mbps("5G", 80)  ## 900.0
    record_tput("5G/80", mbps)  ## Stored for the summary table
    assert mbps >= 850  ## Passes, so no logs are collected


def test_6g_320_weak(record_tput):  ## Weak signal case
    mbps = throughput_mbps("6G", 320, rssi=-72)  ## 4800 with a 44% penalty
    record_tput("6G/320", mbps)  ## Recorded even though the test fails
    assert mbps >= 3000, f"{mbps} Mbps"  ## Fails, so teardown collects logs""",
            "under": "`report.when` is `\"setup\"`, `\"call\"` or `\"teardown\"`, and `report.outcome` is passed, failed or skipped. The autouse fixture's code after `yield` runs in the teardown phase, after the call report exists. `tryfirst=True` makes our wrapper run before other plugins' wrappers. `terminalreporter.write_sep` draws a titled separator like pytest's own sections.",
            "gotchas": [],
            "best": "Use the new-style `wrapper=True` (pytest 8+) instead of `hookwrapper=True`, always return the report, attach artifacts only on failure, and put summary data into `config.stash` or a plugin object rather than module globals when the suite runs in parallel.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "runner": "pytest",
            "files": {"conftest.py": "def pytest_report_header(config):\n    return \"DUT firmware: 7.4.1 (build 2219)\"\n"},
            "args": [],
            "prompt": "Add the DUT firmware version to pytest's header.",
            "solution": "`pytest_report_header` returns a string or list of strings, shown under rootdir (not shown with -q).",
            "solution_code": """def test_firmware_string():
    assert "7.4.1".count(".") == 2""",
        },
        {
            "level": "Medium",
            "runner": "pytest",
            "files": {"conftest.py": """def pytest_collection_modifyitems(config, items):
    selected, deselected = [], []
    for item in items:
        (deselected if "legacy" in item.nodeid else selected).append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected
"""},
            "args": ["-v"],
            "prompt": "Deselect every test whose node id contains `legacy`, and make sure the summary reports them as deselected.",
            "solution": "Split the items, call the pytest_deselected hook for the removed ones, and replace the list contents in place with `items[:]`.",
            "solution_code": """def test_wpa3_sae():
    assert True


def test_legacy_wep():
    assert True""",
        },
        {
            "level": "Hard",
            "runner": "pytest",
            "files": {"conftest.py": """import collections

import pytest

FAILS = collections.Counter()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    if report.when == "call" and report.failed:
        FAILS[item.callspec.params.get("band", "?")] += 1
    return report


def pytest_terminal_summary(terminalreporter):
    terminalreporter.write_sep("-", "failures per band")
    for band in sorted(FAILS):
        terminalreporter.write_line(f"{band}: {FAILS[band]}")
"""},
            "args": ["-q", "--tb=no"],
            "prompt": "Count failures per band for a parametrized test and print them in a custom summary section.",
            "solution": "In a makereport wrapper, read the band from `item.callspec.params` for failed call reports; print the counter in pytest_terminal_summary.",
            "solution_code": """import pytest


@pytest.mark.parametrize("band", ["2G", "5G", "6G"])
@pytest.mark.parametrize("trial", range(2))
def test_associate(band, trial):
    failing = {("6G", 0), ("6G", 1), ("2G", 1)}
    assert (band, trial) not in failing""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "What is a pytest hook and where do you implement it?", "a": "A function with a reserved pytest_* name that pytest calls at a defined point (configure, collection, run, report). Implement it in conftest.py or a plugin; pluggy calls every implementation.", "follow": "How do you control the order of implementations? (tryfirst/trylast, or wrapper hooks.)"},
        {"level": "Intermediate", "q": "How would you collect logs only when a test fails?", "a": "A makereport wrapper stores each phase's report on the item (item.rep_call). An autouse fixture checks request.node.rep_call.failed after yield and collects logs then.", "follow": "Why not do it inside the hook? (Fixtures have access to the test's resources and run in the right teardown order.)"},
        {"level": "Advanced", "q": "What's the difference between hookwrapper=True and wrapper=True?", "a": "Old-style hookwrapper yields an outcome object (outcome.get_result(), force_result). New-style wrapper=True (pluggy 1.2+/pytest 8) yields the actual result, can raise, and must return the result, which reads like normal code.", "follow": "What happens if a wrapper forgets to return the report? (The hook's result becomes None and reporting breaks.)"},
        {"level": "Advanced", "q": "Name hooks in the order they're called for a simple run.", "a": "pytest_addoption → pytest_configure → pytest_sessionstart → pytest_collection_modifyitems → pytest_runtest_protocol (setup/call/teardown with pytest_runtest_makereport and pytest_runtest_logreport) → pytest_sessionfinish → pytest_terminal_summary → pytest_unconfigure.", "follow": "Which hook would you use to upload results to a dashboard? (pytest_sessionfinish or pytest_terminal_summary.)"},
    ],
    "quiz": [
        {"q": "Which hook can reorder tests?", "options": ["pytest_configure", "pytest_collection_modifyitems", "pytest_runtest_call", "pytest_sessionfinish"], "answer": 1, "why": "It receives the items list."},
        {"q": "How many reports per test does makereport produce?", "options": ["1", "2", "3", "Depends on fixtures"], "answer": 2, "why": "setup, call, teardown."},
        {"q": "A wrapper=True hook must...", "options": ["Return nothing", "Yield and return the result", "Call pytest.exit", "Be in a test file"], "answer": 1, "why": "It returns the (possibly modified) result."},
        {"q": "Misspelled pytest_ hook in conftest:", "options": ["Ignored", "Error at startup", "Warning only", "Runs anyway"], "answer": 1, "why": "Unknown hooks are validation errors."},
        {"q": "Best place to register markers added by a hook?", "options": ["pytest_configure", "pytest_sessionfinish", "a test", "pytest_report_header"], "answer": 0, "why": "config.addinivalue_line('markers', ...) at configure time."},
    ],
    "cards": [
        {"front": "Reorder/mark/filter tests", "back": "`pytest_collection_modifyitems(config, items)`"},
        {"front": "Know if a test failed in teardown", "back": "makereport wrapper → `item.rep_call.failed`"},
        {"front": "Custom end-of-run section", "back": "`pytest_terminal_summary(terminalreporter)`"},
        {"front": "Extra header lines", "back": "`pytest_report_header(config)`"},
        {"front": "Report removed tests", "back": "`config.hook.pytest_deselected(items=removed)`"},
    ],
}


PLUGIN_SRC = """import pytest


def pytest_addoption(parser):
    parser.addoption("--bench", default="lab-07", help="bench to run on")


def pytest_configure(config):
    config.addinivalue_line("markers", "bench_only: needs a physical bench")


def pytest_report_header(config):
    return f"bench plugin: {config.getoption('bench')}"


@pytest.fixture(scope="session")
def bench(request):
    return {"name": request.config.getoption("bench"), "aps": ["ap-1", "ap-2"]}
"""

M_5_9 = {
    "id": "5.9",
    "title": "Writing a Custom Plugin",
    "hours": 2,
    "summary": "Move conftest code into a reusable plugin module, load it with pytest_plugins or an entry point, and test the plugin itself with pytester.",
    "concepts": [
        {
            "title": "A plugin is a module with hooks and fixtures",
            "runner": "pytest",
            "filename": "tests/test_uses_plugin.py",
            "files": {"pytest_bench.py": PLUGIN_SRC, "conftest.py": "pytest_plugins = [\"pytest_bench\"]\n"},
            "args": ["-v", "--bench", "lab-12"],
            "concept": "A pytest plugin is just an importable module containing hooks and fixtures, the same things you'd put in conftest.py. Load it with `pytest_plugins = [\"module\"]` in the root conftest, with `-p module` on the command line, or automatically by installing a package that declares a `pytest11` entry point. Every repo that installs it gets the same options, markers and fixtures.",
            "why": "Five test repos (AP firmware, client drivers, controller, cloud API, factory) all need the same `bench` fixture and `--bench` option. Copy-pasted conftest files drift; a versioned plugin package doesn't.",
            "syntax": "# conftest.py\npytest_plugins = [\"pytest_bench\"]\n\n# pyproject.toml of the plugin package\n[project.entry-points.pytest11]\nbench = \"pytest_bench\"",
            "code": """import pytest  ## For the marker


def test_bench_from_plugin(bench):  ## Fixture defined in pytest_bench.py
    assert bench["name"] == "lab-12"  ## Value from --bench, an option the plugin added


@pytest.mark.bench_only  ## Marker registered by the plugin's pytest_configure
def test_two_aps(bench):  ## Same fixture, session-scoped
    assert len(bench["aps"]) == 2  ## Plugin data""",
            "under": "At startup pytest loads built-in plugins, then `pytest11` entry points of installed packages (that's how pytest-xdist and pytest-timeout appear in the header), then `-p` modules, then conftest files and their `pytest_plugins`. `pytest_plugins` is only allowed in the root conftest. A plugin's `pytest_addoption` works because it's loaded before the command line is parsed.",
            "gotchas": [
                {
                    "title": "Using a plugin's fixture without loading the plugin",
                    "runner": "pytest",
                    "files": {"pytest_bench.py": PLUGIN_SRC},
                    "fixed_files": {"pytest_bench.py": PLUGIN_SRC, "conftest.py": "pytest_plugins = [\"pytest_bench\"]\n"},
                    "note": "The module exists, but nothing registers it, so pytest reports `fixture 'bench' not found` and lists the fixtures it does know. Register it in the root conftest (or install the package with its entry point).",
                    "wrong": """def test_bench(bench):
    assert bench["name"]""",
                    "fixed": """# conftest.py now contains: pytest_plugins = ["pytest_bench"]
def test_bench(bench):
    assert bench["name"]""",
                    "args": ["-q", "--tb=line"],
                },
            ],
            "best": "Start in conftest.py; promote to a plugin once a second repo needs it. Name the package `pytest-<thing>`, register markers in `pytest_configure`, namespace options (`--bench-*`), version it, and keep its own test suite with pytester.",
        },
        {
            "title": "Testing a plugin with pytester",
            "runner": "pytest",
            "filename": "test_plugin.py",
            "files": {"pytest_bench.py": PLUGIN_SRC, "conftest.py": "pytest_plugins = [\"pytester\"]\n"},
            "args": ["-v"],
            "concept": "The built-in `pytester` plugin gives a fixture that creates a throwaway project (`makepyfile`, `makeconftest`, `makeini`), runs pytest inside it (`runpytest`) and returns a result you can assert on: `assert_outcomes(passed=1)`, `result.ret`, and `result.stdout.fnmatch_lines([...])` with glob patterns.",
            "why": "A plugin is code that other teams depend on. pytester lets you test it the way users run it: real pytest runs, real output, without touching your own test session.",
            "syntax": "pytest_plugins = [\"pytester\"]\n\ndef test_x(pytester):\n    pytester.makepyfile(\"def test_a(): pass\")\n    result = pytester.runpytest()\n    result.assert_outcomes(passed=1)",
            "code": """from pathlib import Path  ## To read the plugin source

PLUGIN = Path(__file__).with_name("pytest_bench.py").read_text()  ## The plugin under test


def test_option_and_fixture(pytester):  ## pytester builds an isolated project
    pytester.syspathinsert()  ## Make the temp project importable, so -p can find the plugin
    pytester.makepyfile(pytest_bench=PLUGIN)  ## Write the plugin into the temp project
    pytester.makepyfile(test_x="def test_name(bench):\\n    assert bench['name'] == 'lab-99'\\n")  ## A user's test
    result = pytester.runpytest("-p", "pytest_bench", "--bench", "lab-99")  ## Run pytest with the plugin loaded
    result.assert_outcomes(passed=1)  ## Exactly one test passed


def test_header_line(pytester):  ## Check user-visible output too
    pytester.syspathinsert()  ## Needed in every pytester test that uses -p
    pytester.makepyfile(pytest_bench=PLUGIN)  ## Same plugin
    pytester.makepyfile(test_y="def test_ok():\\n    pass\\n")  ## Trivial test
    result = pytester.runpytest("-p", "pytest_bench")  ## Default bench
    result.stdout.fnmatch_lines(["bench plugin: lab-07"])  ## Glob-matched line in the header""",
            "under": "pytester changes into a fresh temporary directory per test and runs pytest in-process (`runpytest_subprocess` runs it in a child process for full isolation). Files are written relative to that directory; `syspathinsert()` puts it on sys.path so `-p` can import modules you created there (without it, `-p` could silently pick up a same-named module from your real project). `fnmatch_lines` checks the lines appear in order, allowing `*` wildcards.",
            "gotchas": [],
            "best": "Cover each hook and option with a pytester test, assert on outcomes and on the exact user-facing text, and test misuse too (bad option values should fail with a clear message).",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "runner": "pytest",
            "files": {"pytest_ssid.py": "import pytest\n\n\n@pytest.fixture\ndef ssid():\n    return \"lab-6g\"\n", "conftest.py": "pytest_plugins = [\"pytest_ssid\"]\n"},
            "prompt": "Move an `ssid` fixture into a plugin module `pytest_ssid.py` and load it from the root conftest.",
            "solution": "The plugin module defines the fixture; `pytest_plugins` in the root conftest registers it.",
            "solution_code": """def test_ssid(ssid):
    assert ssid == "lab-6g\"""",
        },
        {
            "level": "Medium",
            "runner": "pytest",
            "files": {"conftest.py": "pytest_plugins = [\"pytester\"]\n"},
            "args": ["-q"],
            "prompt": "Use pytester to check that a failing test makes pytest exit with code 1 and reports 1 failed.",
            "solution": "`result.ret` is the exit code (an ExitCode enum, equal to 1) and assert_outcomes checks the counts.",
            "solution_code": """import pytest


def test_failure_exit_code(pytester):
    pytester.makepyfile("def test_bad():\\n    assert 880 >= 900\\n")
    result = pytester.runpytest()
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    result.assert_outcomes(failed=1)""",
        },
        {
            "level": "Hard",
            "runner": "pytest",
            "files": {"conftest.py": "pytest_plugins = [\"pytester\"]\n"},
            "args": ["-q"],
            "prompt": "Write a plugin that registers a `sniffer` marker in pytest_configure, and prove with pytester that `--strict-markers` accepts it when the plugin is loaded and rejects it when it isn't.",
            "solution": "Run pytester twice: with `-p` the marker is known; without it collection fails (exit code 2, interrupted) and the error mentions the marker. The second run uses `runpytest_subprocess`: in-process runs share pytest's global marker cache, which still remembers `sniffer` from the first run, so only a fresh interpreter proves the negative case.",
            "solution_code": """PLUGIN = '''
def pytest_configure(config):
    config.addinivalue_line("markers", "sniffer: needs a monitor-mode capture")
'''
TEST = '''
import pytest

@pytest.mark.sniffer
def test_capture():
    pass
'''


def test_marker_registered(pytester):
    pytester.syspathinsert()
    pytester.makepyfile(pytest_sniffer=PLUGIN, test_cap=TEST)
    pytester.runpytest("-p", "pytest_sniffer", "--strict-markers").assert_outcomes(passed=1)


def test_marker_missing_without_plugin(pytester):
    pytester.makepyfile(test_cap=TEST)
    result = pytester.runpytest_subprocess("--strict-markers")
    assert result.ret == 2
    result.stdout.fnmatch_lines(["*'sniffer' not found in `markers`*"])""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "How is a pytest plugin different from conftest.py?", "a": "Technically the same contents (hooks, fixtures). conftest.py is local and directory-scoped; a plugin is an importable module or installed package loaded by pytest_plugins, -p or a pytest11 entry point, so it can be shared and versioned across repos.", "follow": "Where is pytest_plugins allowed? (Only the root conftest, since pytest 4.)"},
        {"level": "Intermediate", "q": "How do you test a pytest plugin?", "a": "With the pytester fixture: create files in a temp project, run pytest in-process or as a subprocess, and assert outcomes, exit code and output lines.", "follow": "When would you use runpytest_subprocess? (When the plugin changes global state or needs a clean interpreter.)"},
        {"level": "Advanced", "q": "How does an installed package register itself with pytest?", "a": "An entry point in the `pytest11` group, e.g. `[project.entry-points.pytest11] bench = \"pytest_bench\"`. pytest loads all such entry points at startup unless disabled with -p no:name or PYTEST_DISABLE_PLUGIN_AUTOLOAD.", "follow": "Why might you disable autoload in CI? (Reproducibility and speed: only explicitly listed plugins run.)"},
    ],
    "quiz": [
        {"q": "Entry-point group for pytest plugins?", "options": ["pytest", "pytest11", "pytest_plugins", "plugins"], "answer": 1, "why": "pytest11."},
        {"q": "Where can `pytest_plugins = [...]` go?", "options": ["Any conftest", "Root conftest only", "Test files", "pytest.ini"], "answer": 1, "why": "Non-root use is an error."},
        {"q": "pytester.runpytest() returns...", "options": ["An exit code", "A RunResult with ret, outcomes, stdout", "A list of reports", "None"], "answer": 1, "why": "RunResult."},
        {"q": "fnmatch_lines patterns use...", "options": ["Regex", "Shell-style globs", "Exact strings only", "XPath"], "answer": 1, "why": "fnmatch glob patterns."},
        {"q": "Disable an auto-loaded plugin for one run:", "options": ["--no-plugin x", "-p no:x", "-k not x", "--disable x"], "answer": 1, "why": "-p no:name."},
    ],
    "cards": [
        {"front": "Load a local plugin", "back": "`pytest_plugins = ['mod']` in root conftest, or `-p mod`"},
        {"front": "Ship a plugin", "back": "`[project.entry-points.pytest11] name = 'module'`"},
        {"front": "Test a plugin", "back": "`pytest_plugins=['pytester']` → pytester.makepyfile/runpytest"},
        {"front": "Assert outcome counts", "back": "`result.assert_outcomes(passed=1, failed=0)`"},
        {"front": "Disable a plugin", "back": "`-p no:name`"},
    ],
}


SURVEY_FILES = {
    "devices.py": """def get_rssi(iface):
    # Real version would run `iw dev <iface> link` and parse it.
    raise RuntimeError(f"tried to read real radio {iface}")
""",
    "survey.py": """from devices import get_rssi


def best_iface(ifaces):
    return max(ifaces, key=get_rssi)
""",
}

M_5_10 = {
    "id": "5.10",
    "title": "Mocking",
    "hours": 2.5,
    "summary": "Replace slow or unavailable dependencies (devices, SSH sessions, clocks) with Mocks: return values, side effects, call assertions, specs, and patching in the right place.",
    "concepts": [
        {
            "title": "Mock, MagicMock, return_value and side_effect",
            "concept": "`unittest.mock.Mock` creates an object that accepts any attribute access or call and records it. Set `return_value` for what a call returns and `side_effect` for a sequence of results, an exception to raise, or a function to run. Afterwards assert on the interaction: `assert_called_once_with(...)`, `call_count`, `call_args_list`. `Mock(spec=RealClass)` restricts the mock to the real class's attributes.",
            "why": "A config-push function talks to a switch over SSH. In a unit test you want to check what it sent and how it handles a timeout, in milliseconds, without a switch.",
            "syntax": "m = Mock(spec=Client)\nm.send.return_value = \"ok\"\nm.send.side_effect = [TimeoutError, \"ok\"]\nm.send.assert_called_once_with(\"cmd\")",
            "code": """from unittest.mock import Mock, call  ## Standard library, no install needed


class SshClient:  ## Real interface (would wrap Netmiko/Paramiko)
    def send_command(self, cmd: str) -> str:  ## Would talk to a device
        raise NotImplementedError  ## Never called in the test


def push_vlan(client, vlan: int) -> bool:  ## Code under test
    for attempt in range(3):  ## Up to three tries
        try:  ## Timeouts are retried
            out = client.send_command(f"vlan {vlan}")  ## The interaction we want to check
            return "error" not in out.lower()  ## Success if the device didn't complain
        except TimeoutError:  ## Device didn't answer in time
            continue  ## Try again
    return False  ## Gave up


client = Mock(spec=SshClient)  ## Only SshClient's attributes are allowed
client.send_command.side_effect = [TimeoutError(), "VLAN 30 created"]  ## First call times out, second succeeds
print(push_vlan(client, 30))  ## Retried once, then succeeded
print(client.send_command.call_count)  ## Two calls recorded
print(client.send_command.call_args_list == [call("vlan 30"), call("vlan 30")])  ## Exact arguments of each call

client.reset_mock(side_effect=True)  ## Clear recorded calls and the side effect
client.send_command.return_value = "% Error: invalid VLAN"  ## Every call returns this now
print(push_vlan(client, 5000))  ## The error text makes it return False
client.send_command.assert_called_once_with("vlan 5000")  ## Raises AssertionError if not exactly one matching call
print("assertions passed")  ## Reached only if the assertion held""",
            "under": "Accessing any attribute on a Mock creates a child Mock on the fly and caches it, which is why `client.send_command` works without setup. Calls are recorded as `call(...)` objects. When `side_effect` is an iterable, each call takes the next item, and an exception instance or class in it is raised. `MagicMock` additionally supports magic methods (`len()`, `with`, iteration).",
            "gotchas": [
                {
                    "title": "Mocks without a spec accept typos",
                    "note": "A plain Mock happily records `send_comand` (one m), so the test passes even though the real class has no such method. With `spec=` the typo raises AttributeError immediately.",
                    "wrong": """from unittest.mock import Mock


class SshClient:
    def send_command(self, cmd):
        ...


client = Mock()
client.send_comand("show version")
print("test passed?", client.send_comand.called)""",
                    "fixed": """from unittest.mock import Mock


class SshClient:
    def send_command(self, cmd):
        ...


client = Mock(spec=SshClient)
try:
    client.send_comand("show version")
except AttributeError as e:
    print("caught:", e)""",
                },
            ],
            "best": "Always use `spec=` or `create_autospec` so mocks match the real interface (including method signatures), assert on the calls that matter, not on every call, and mock at the boundary (device client, HTTP session, clock), never the code you're testing.",
        },
        {
            "title": "Patch where the name is looked up; monkeypatch",
            "runner": "pytest",
            "filename": "test_survey.py",
            "files": SURVEY_FILES,
            "args": ["-v"],
            "concept": "`unittest.mock.patch(\"module.name\")` temporarily replaces an attribute and restores it afterwards. The key rule: patch the name **where it's used**, not where it's defined. `survey.py` did `from devices import get_rssi`, so it holds its own reference: patch `survey.get_rssi`. pytest's `monkeypatch` fixture does the same with `setattr`, `setenv` and `delenv`, undone automatically after the test.",
            "why": "Most mocking bugs in real suites are patches that don't take effect, so the test silently hits real hardware or the network. Knowing the lookup rule saves hours.",
            "syntax": "with patch(\"survey.get_rssi\", side_effect=f):\n    ...\n\ndef test_x(monkeypatch):\n    monkeypatch.setattr(survey, \"get_rssi\", f)\n    monkeypatch.setenv(\"DUT_IP\", \"192.0.2.1\")",
            "code": """import os  ## For the environment check
from unittest.mock import patch  ## Context manager / decorator

import survey  ## Module under test

FAKE_RSSI = {"wlan0": -67, "wlan1": -48, "wlan2": -71}  ## Simulated signal per interface


def test_best_iface_with_patch():  ## Using unittest.mock.patch
    with patch("survey.get_rssi", side_effect=FAKE_RSSI.get) as fake:  ## Replace the name survey uses
        assert survey.best_iface(["wlan0", "wlan1", "wlan2"]) == "wlan1"  ## Strongest signal wins
    assert fake.call_count == 3  ## One reading per interface


def test_best_iface_with_monkeypatch(monkeypatch):  ## pytest's built-in fixture
    monkeypatch.setattr(survey, "get_rssi", FAKE_RSSI.get)  ## Same patch, undone after the test
    monkeypatch.setenv("SURVEY_BAND", "6G")  ## Environment changes are undone too
    assert survey.best_iface(["wlan0", "wlan2"]) == "wlan0"  ## -67 beats -71
    assert os.environ["SURVEY_BAND"] == "6G"  ## Visible inside the test only""",
            "under": "`from devices import get_rssi` copies a reference into `survey`'s namespace at import time. Patching `devices.get_rssi` rebinds the name in `devices`, but `survey.get_rssi` still points at the original function. `patch` uses `importlib` to find the target by its dotted path, swaps the attribute, and restores it in `__exit__` even if the test fails.",
            "gotchas": [
                {
                    "title": "Patching where the function is defined",
                    "runner": "pytest",
                    "files": SURVEY_FILES,
                    "args": ["-q", "--tb=line"],
                    "note": "`survey` imported `get_rssi` by name, so replacing `devices.get_rssi` doesn't change what `survey` calls: the real function runs and tries to touch a radio.",
                    "wrong": """from unittest.mock import patch

import survey


def test_best():
    with patch("devices.get_rssi", side_effect={"a": -60, "b": -40}.get):
        assert survey.best_iface(["a", "b"]) == "b\"""",
                    "fixed": """from unittest.mock import patch

import survey


def test_best():
    with patch("survey.get_rssi", side_effect={"a": -60, "b": -40}.get):
        assert survey.best_iface(["a", "b"]) == "b\"""",
                },
            ],
            "best": "Patch the name in the module under test, prefer `monkeypatch` in pytest (no decorators, auto-undo), use `autospec=True` with patch so signatures are enforced, and if you patch the same thing in many tests, make it a fixture.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "A `ping(host)` dependency fails twice with TimeoutError and then returns 12.5 (ms). Use a Mock with side_effect to test a `wait_until_reachable(ping, host, tries)` function, and check how many calls it made.",
            "solution": "A list side_effect returns or raises the next item on each call; `call_count` confirms three attempts.",
            "solution_code": """from unittest.mock import Mock


def wait_until_reachable(ping, host, tries=5):
    for _ in range(tries):
        try:
            return ping(host)
        except TimeoutError:
            pass
    raise TimeoutError(f"{host} unreachable")


ping = Mock(side_effect=[TimeoutError, TimeoutError, 12.5])
print(wait_until_reachable(ping, "192.0.2.1"))
print(ping.call_count)
ping.assert_called_with("192.0.2.1")
print("ok")""",
        },
        {
            "level": "Medium",
            "runner": "pytest",
            "files": {"poller.py": """import time


def wait_for_link(read_state, timeout=30, interval=5):
    waited = 0
    while waited <= timeout:
        if read_state() == "up":
            return waited
        time.sleep(interval)
        waited += interval
    raise TimeoutError("link stayed down")
"""},
            "args": ["-v"],
            "prompt": "`wait_for_link` sleeps between polls. Test it in milliseconds by replacing `time.sleep` with monkeypatch, and record the requested sleeps.",
            "solution": "poller uses `time.sleep` via the module attribute, so patching `poller.time.sleep` (or `time.sleep`) works; collect the arguments in a list.",
            "solution_code": """import poller


def test_link_comes_up_on_third_poll(monkeypatch):
    sleeps = []
    monkeypatch.setattr(poller.time, "sleep", sleeps.append)
    states = iter(["down", "down", "up"])
    assert poller.wait_for_link(lambda: next(states)) == 10
    assert sleeps == [5, 5]""",
        },
        {
            "level": "Hard",
            "runner": "pytest",
            "files": {"config_loader.py": """import json


class Device:
    def push(self, hostname, config):
        raise RuntimeError("real device")


def deploy(path, device):
    with open(path) as fh:
        data = json.load(fh)
    for host, cfg in sorted(data.items()):
        device.push(host, cfg)
    return len(data)
"""},
            "args": ["-v"],
            "prompt": "Test `deploy` without a file or a device: use `mock_open` for the JSON file and `create_autospec(Device)` for the device, then assert the push calls in order.",
            "solution": "Patch `builtins.open` with mock_open(read_data=...) and pass an autospecced Device; autospec also enforces push's signature.",
            "solution_code": """from unittest.mock import call, create_autospec, mock_open, patch

import config_loader

DATA = '{"sw-2": {"vlan": 20}, "sw-1": {"vlan": 10}}'


def test_deploy_pushes_in_order():
    device = create_autospec(config_loader.Device, instance=True)
    with patch("builtins.open", mock_open(read_data=DATA)) as fake_open:
        assert config_loader.deploy("inventory.json", device) == 2
    fake_open.assert_called_once_with("inventory.json")
    assert device.push.call_args_list == [call("sw-1", {"vlan": 10}), call("sw-2", {"vlan": 20})]""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What's the difference between return_value and side_effect?", "a": "return_value is what every call returns. side_effect overrides it: an exception is raised, an iterable yields one result per call, a function is called with the same arguments and its result returned.", "follow": "How do you raise on the second call only? (side_effect=[value, Exception()].)"},
        {"level": "Intermediate", "q": "Why does patching sometimes have no effect?", "a": "You patched where the object is defined, but the code under test imported it by name and holds its own reference. Patch the name in the module that uses it (`survey.get_rssi`, not `devices.get_rssi`).", "follow": "When would patching the definition work? (If the code calls it as `devices.get_rssi(...)` through the module.)"},
        {"level": "Intermediate", "q": "Mock vs MagicMock vs create_autospec?", "a": "Mock records calls and attributes; MagicMock also implements magic methods (__len__, __iter__, __enter__). create_autospec builds a mock from a real object, enforcing attributes and call signatures, so API drift breaks the test.", "follow": "Why is autospec slower? (It introspects the real object recursively.)"},
        {"level": "Advanced", "q": "When is mocking the wrong choice?", "a": "When it tests implementation rather than behaviour (asserting every internal call), when the mocked contract is complex enough that a fake or a real lightweight dependency (SQLite, a local HTTP server, a simulator) is more faithful, and for integration tests whose point is the real interaction.", "follow": "What's a fake vs a mock? (A fake is a working simplified implementation; a mock records and verifies interactions.)"},
    ],
    "quiz": [
        {"q": "`m.side_effect = [1, ValueError()]`: second call...", "options": ["Returns 1", "Raises ValueError", "Returns None", "Raises StopIteration"], "answer": 1, "why": "Each call takes the next item; exceptions are raised."},
        {"q": "survey.py does `from devices import get_rssi`. Patch...", "options": ["devices.get_rssi", "survey.get_rssi", "builtins.get_rssi", "Either works"], "answer": 1, "why": "Patch where it's looked up."},
        {"q": "`Mock(spec=Cls).typo()` gives...", "options": ["A Mock", "AttributeError", "None", "TypeError"], "answer": 1, "why": "spec restricts attributes."},
        {"q": "monkeypatch changes are undone...", "options": ["Never", "At the end of the test", "At session end", "Only on failure"], "answer": 1, "why": "Function-scoped fixture teardown."},
        {"q": "Mocking file reads:", "options": ["mock_open", "MagicMock(file)", "patch('io')", "tmp_path only"], "answer": 0, "why": "mock_open(read_data=...) with patch('builtins.open')."},
    ],
    "cards": [
        {"front": "Sequence of results / errors", "back": "`m.side_effect = [TimeoutError(), 'ok']`"},
        {"front": "Patch rule", "back": "Patch where the name is looked up, not where it's defined"},
        {"front": "Enforce real signatures", "back": "`create_autospec(Cls, instance=True)` or `patch(..., autospec=True)`"},
        {"front": "pytest patching", "back": "`monkeypatch.setattr / setenv / delenv`, auto-undone"},
        {"front": "Check exact calls", "back": "`m.assert_called_once_with(...)`, `m.call_args_list`"},
    ],
}
