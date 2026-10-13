"""Phase 8 content: modules 8.7-8.11 (reports, GitHub/GitLab CI, secrets, nightly design, triage)."""

from net_support import needs, sim

PYTEST_SUB = "runs pytest in a subprocess, which the in-browser runner can't do"
ALLURE = needs("pytest allure-pytest") + " and runs pytest in a subprocess"
YAML = needs("pyyaml")
VAULT = needs("requests") + " and starts a simulated Vault server on localhost"
SQLITE = "uses sqlite3, which this in-browser runner doesn't bundle"
MPL = needs("matplotlib")

SHARD_TESTS = {
    "tests/test_rvr.py": '''import pytest


@pytest.mark.parametrize("band,mbps,kpi", [("5G", 912.4, 850), ("6G", 1890.0, 2000)])
def test_rvr(record_property, band, mbps, kpi):
    record_property("throughput_mbps", mbps)
    assert mbps >= kpi, f"{band}: {mbps} < {kpi}"
''',
    "tests/test_roam.py": '''import pytest


def test_11r_roam_time():
    assert 38 <= 50


@pytest.mark.skip(reason="no second AP on this bench")
def test_11k_neighbor_report():
    pass
''',
    "pytest.ini": "[pytest]\njunit_family = xunit1\n",
}

M_8_7 = {
    "id": "8.7",
    "title": "JUnit & Allure Publishing",
    "hours": 1.5,
    "summary": "Produce machine-readable results: JUnit XML from pytest, merging shards from parallel stages, and Allure results with steps, attachments and labels for rich reports.",
    "concepts": [
        {
            "title": "JUnit XML: produce, merge, summarise",
            "files": SHARD_TESTS,
            "local_only": PYTEST_SUB,
            "concept": "`pytest --junitxml=path` writes a JUnit XML report: a `testsuite` with totals and one `testcase` per test, containing `failure`, `error` or `skipped` elements as needed. When a pipeline runs tests in parallel stages or shards, each writes its **own** file, and a small merge step combines them into one report with correct totals for publishing and dashboards.",
            "why": "Every CI system (Jenkins junit step, GitLab reports, GitHub test-reporter actions) and most dashboards consume JUnit XML. Getting it right, and merged, is what makes failures visible without anyone reading console logs.",
            "syntax": "pytest -m rf --junitxml=results/rf.xml\npytest -m 'not rf' --junitxml=results/sw.xml\n# merge results/*.xml -> results/all.xml",
            "code": """import subprocess  ## Run pytest like two parallel CI stages would
import sys  ## Same interpreter
import xml.etree.ElementTree as ET  ## Read and write XML
from pathlib import Path  ## Paths

for shard in ("rvr", "roam"):  ## Two shards, two files
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"tests/test_{shard}.py", f"--junitxml=results/{shard}.xml"], capture_output=True)  ## Failures don't stop us


def merge(paths, out):  ## Combine many JUnit files into one <testsuites>
    root = ET.Element("testsuites")  ## New top-level element
    totals = dict.fromkeys(("tests", "failures", "errors", "skipped"), 0)  ## Running totals
    for p in sorted(paths):  ## Stable order
        tree = ET.parse(p).getroot()  ## <testsuites> or <testsuite>
        for suite in tree.iter("testsuite"):  ## Each suite in that file
            suite.set("name", Path(p).stem)  ## Name it after the shard
            for key in totals:  ## Add up the counters
                totals[key] += int(suite.get(key, 0))  ## Missing attributes count as 0
            root.append(suite)  ## Move the suite into the merged tree
    for key, value in totals.items():  ## Totals on the root element
        root.set(key, str(value))  ## Attributes are strings
    ET.ElementTree(root).write(out, encoding="utf-8", xml_declaration=True)  ## Write the merged report
    return totals  ## For logging


print(merge(Path("results").glob("*.xml"), "results/all.xml"))  ## Combined totals
for case in ET.parse("results/all.xml").getroot().iter("testcase"):  ## Walk every test case
    outcome = next((child.tag for child in case if child.tag in ("failure", "error", "skipped")), "passed")  ## First outcome element, if any
    props = {p.get("name"): p.get("value") for p in case.iter("property")}  ## record_property values
    print(f"{outcome:<8} {case.get('classname')}.{case.get('name')}", props or "")  ## One line per test""",
            "under": "A passing testcase has no child elements; failure/error/skipped carry a `message` attribute and the traceback as text. `junit_family = xunit1` (set in pytest.ini here) keeps `<properties>` per test case; the default xunit2 drops them. Merging works by moving whole `<testsuite>` elements under a new `<testsuites>` root; most consumers accept that shape.",
            "gotchas": [
                {
                    "title": "Parallel stages writing the same JUnit file",
                    "files": SHARD_TESTS,
                    "local_only": PYTEST_SUB,
                    "note": "When both shards write `results/junit.xml`, the last one to finish overwrites the other, and the published report silently loses tests. Give every stage its own file name and publish with a glob.",
                    "wrong": """import subprocess, sys
import xml.etree.ElementTree as ET

for shard in ("rvr", "roam"):
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"tests/test_{shard}.py",
                    "--junitxml=results/junit.xml"], capture_output=True)
print("tests in published report:", sum(1 for _ in ET.parse("results/junit.xml").getroot().iter("testcase")))""",
                    "fixed": """import subprocess, sys
import xml.etree.ElementTree as ET
from pathlib import Path

for shard in ("rvr", "roam"):
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"tests/test_{shard}.py",
                    f"--junitxml=results/junit-{shard}.xml"], capture_output=True)
print("tests in published reports:", sum(1 for p in Path("results").glob("junit-*.xml") for _ in ET.parse(p).getroot().iter("testcase")))""",
                },
            ],
            "best": "One JUnit file per stage/shard/bench with a descriptive name, publish with a glob (`results/*.xml`), merge only when a tool needs a single file, keep `xunit1` if you use record_property, and archive the XML as an artifact alongside logs.",
        },
        {
            "title": "Allure: steps, attachments and labels",
            "local_only": ALLURE,
            "files": {"tests/test_allure_demo.py": '''import json

import allure


@allure.feature("Roaming")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("11r roam completes under 50 ms on 5 GHz")
def test_ft_roam():
    with allure.step("Associate client to ap-lab-07"):
        bssid = "3c:84:6a:12:34:60"
    with allure.step("Lower attenuation on ap-lab-08 to trigger roam"):
        roam_ms = 38
    allure.attach(json.dumps({"from": bssid, "to": "3c:84:6a:12:34:80", "roam_ms": roam_ms}),
                  name="roam-event", attachment_type=allure.attachment_type.JSON)
    assert roam_ms < 50


@allure.feature("Throughput")
def test_6g_rvr_point():
    with allure.step("Set attenuation 42 dB"):
        pass
    with allure.step("Run iperf3 downlink"):
        mbps = 135.9
    assert mbps >= 150, f"{mbps} Mbps < KPI 150"
'''},
            "concept": "Allure is a reporting framework: the `allure-pytest` plugin writes one JSON file per test (plus attachments) into `--alluredir`, and the Allure CLI turns a folder of results into an HTML report with history, categories and trends. In tests, `allure.step` records nested steps, `allure.attach` stores logs, JSON, pcaps or screenshots, and decorators add **labels** (feature, severity, owner) used for filtering.",
            "why": "A JUnit failure says 'assert 135.9 >= 150'. An Allure report shows the steps leading up to it, the attached iperf3 JSON and the RvR chart, grouped by feature, with the test's history across nights: what a firmware developer needs to start debugging.",
            "syntax": "pytest --alluredir=allure-results\nallure generate allure-results -o allure-report --clean\n\nwith allure.step(\"Set attenuation\"): ...\nallure.attach(body, name=..., attachment_type=allure.attachment_type.JSON)",
            "code": """import json  ## Allure result files are JSON
import subprocess  ## Run pytest
import sys  ## Same interpreter
from pathlib import Path  ## Paths

subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_allure_demo.py", "--alluredir=allure-results"], capture_output=True)  ## Writes allure-results/

results = sorted(Path("allure-results").glob("*-result.json"))  ## One file per test (names are UUIDs)
print("result files:", len(results), "| attachments:", len(list(Path("allure-results").glob("*-attachment*"))))  ## Plus attachment files
for path in results:  ## Inspect what the report will show
    r = json.loads(path.read_text())  ## The test's record
    labels = {lab["name"]: lab["value"] for lab in r["labels"] if lab["name"] in ("feature", "severity")}  ## Selected labels
    steps = [s["name"] for s in r.get("steps", [])]  ## Recorded steps, in order
    print(f"{r['status']:<7} {r['name']}")  ## Title from @allure.title or the test name
    print("        labels:", labels, "| steps:", steps)  ## What groups and explains the test
    if r["status"] != "passed":  ## Failure details
        print("        message:", r["statusDetails"]["message"].strip().splitlines()[0])  ## First line of the assertion""",
            "under": "Each `*-result.json` holds status, timing, labels, parameters, steps (each with its own status) and references to attachment files by source name. Report generation (`allure generate` or `allure serve`) needs the Allure command-line tool (Java), usually run by the Jenkins Allure plugin or a CI step; copying the previous report's `history` folder into the results folder before generating is what produces trend charts.",
            "gotchas": [],
            "best": "Use steps for the actions a human would describe, attach the evidence (iperf3 JSON, console logs, captures, charts) only on failure if size matters, label by feature and owner, keep JUnit for CI gating and Allure for humans, and preserve history between runs.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Parse a JUnit XML string and print pass/fail/skip counts computed from the test cases themselves (not the suite attributes).",
            "solution": "Look at each testcase's children: failure/error → failed, skipped → skipped, none → passed.",
            "solution_code": """import xml.etree.ElementTree as ET
from collections import Counter

XML = '''<testsuite tests="4"><testcase name="a"/><testcase name="b"><failure message="x"/></testcase>
<testcase name="c"><skipped message="no AP"/></testcase><testcase name="d"><error message="setup"/></testcase></testsuite>'''
kinds = Counter()
for case in ET.fromstring(XML).iter("testcase"):
    tags = {child.tag for child in case}
    kinds["failed" if tags & {"failure", "error"} else "skipped" if "skipped" in tags else "passed"] += 1
print(dict(kinds))""",
        },
        {
            "level": "Medium",
            "prompt": "Build a JUnit XML report from scratch for results that didn't come from pytest (e.g. an RvR script), so CI can publish them: one testcase per KPI point, failures with messages.",
            "solution": "Create testsuite/testcase elements with ElementTree and set totals; any producer can feed CI this way.",
            "solution_code": """import xml.etree.ElementTree as ET

points = [("5G@0dB", 939.5, 900), ("5G@42dB", 135.9, 150), ("6G@30dB", 1205.0, 1100)]
suite = ET.Element("testsuite", name="rvr", tests=str(len(points)))
failures = 0
for name, mbps, kpi in points:
    case = ET.SubElement(suite, "testcase", classname="rvr", name=name)
    if mbps < kpi:
        failures += 1
        ET.SubElement(case, "failure", message=f"{mbps} Mbps < KPI {kpi}")
suite.set("failures", str(failures))
ET.indent(suite)
print(ET.tostring(suite, encoding="unicode"))""",
        },
        {
            "level": "Hard",
            "prompt": "Compare two JUnit reports (last night vs tonight) and list new failures, fixed tests, and still-failing tests.",
            "solution": "Map test id → outcome for each report, then use set operations.",
            "solution_code": """import xml.etree.ElementTree as ET


def outcomes(xml):
    out = {}
    for c in ET.fromstring(xml).iter("testcase"):
        failed = any(child.tag in ("failure", "error") for child in c)
        out[f"{c.get('classname')}::{c.get('name')}"] = "fail" if failed else "pass"
    return out


LAST = '''<testsuite><testcase classname="rvr" name="5G"/><testcase classname="roam" name="11r"><failure/></testcase>
<testcase classname="dfs" name="ch52"><failure/></testcase></testsuite>'''
TONIGHT = '''<testsuite><testcase classname="rvr" name="5G"><failure/></testcase><testcase classname="roam" name="11r"/>
<testcase classname="dfs" name="ch52"><failure/></testcase></testsuite>'''
a, b = outcomes(LAST), outcomes(TONIGHT)
fails_a = {t for t, o in a.items() if o == "fail"}
fails_b = {t for t, o in b.items() if o == "fail"}
print("new failures:", sorted(fails_b - fails_a))
print("fixed:", sorted(fails_a - fails_b))
print("still failing:", sorted(fails_a & fails_b))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Why produce JUnit XML from pytest?", "a": "It's the common format CI systems and dashboards understand: per-test outcomes, durations, failure messages and properties, so results are published, trended and gated automatically.", "follow": "Which pytest option writes it? (--junitxml=path.)"},
        {"level": "Intermediate", "q": "JUnit vs Allure?", "a": "JUnit XML is a minimal interchange format for CI gating and counts. Allure is a rich human-facing report with steps, attachments, labels, categories and history. Many teams produce both from the same run.", "follow": "What does Allure need to show trends? (The previous report's history folder.)"},
        {"level": "Intermediate", "q": "How do you handle results from parallel shards?", "a": "Each shard writes a uniquely named file; the CI publish step takes a glob, or a merge script combines suites and totals. Never share one output path between parallel stages.", "follow": "What about pytest-xdist workers? (xdist merges into one --junitxml file itself.)"},
    ],
    "quiz": [
        {"q": "A passing testcase element contains...", "options": ["<passed/>", "No outcome child elements", "<success/>", "status='pass'"], "answer": 1, "why": "Only failures/errors/skips add children."},
        {"q": "Two stages write results/junit.xml in parallel...", "options": ["Merged automatically", "One overwrites the other", "CI errors out", "Both are kept"], "answer": 1, "why": "Use unique names."},
        {"q": "record_property needs junit_family...", "options": ["xunit2", "xunit1/legacy", "any", "allure"], "answer": 1, "why": "xunit2 drops per-test properties."},
        {"q": "Allure writes per-test results as...", "options": ["One XML file", "JSON files in --alluredir", "A SQLite DB", "HTML directly"], "answer": 1, "why": "*-result.json."},
        {"q": "Record a sub-action in an Allure report:", "options": ["allure.label", "with allure.step('...')", "print()", "logging.info"], "answer": 1, "why": "Steps."},
    ],
    "cards": [
        {"front": "JUnit from pytest", "back": "`pytest --junitxml=results/<stage>.xml` (+ `junit_family=xunit1` for properties)"},
        {"front": "Outcome of a testcase", "back": "child failure/error/skipped, or none = passed"},
        {"front": "Merge reports", "back": "Move each <testsuite> under a new <testsuites>, sum totals"},
        {"front": "Allure results", "back": "`pytest --alluredir=allure-results`; `allure generate ... -o report`"},
        {"front": "Allure in tests", "back": "`allure.step`, `allure.attach`, `@allure.feature`, `@allure.severity`"},
    ],
}


GH_WORKFLOW = '''name: wifi-tests
on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: "30 20 * * *"
concurrency:
  group: wifi-tests-${{ github.ref }}
  cancel-in-progress: true
jobs:
  lint:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install ruff mypy && ruff check . && mypy src
  unit:
    needs: lint
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-24.04, windows-2022]
        python: ["3.11", "3.12"]
        exclude:
          - {os: windows-2022, python: "3.11"}
        include:
          - {os: ubuntu-24.04, python: "3.13", experimental: true}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "${{ matrix.python }}", cache: pip}
      - run: pip install -r requirements.lock && pytest tests/unit --junitxml=results/unit.xml
  bench:
    needs: unit
    if: github.event_name == 'schedule'
    runs-on: [self-hosted, wifi-bench, 6ghz]
    timeout-minutes: 240
    environment: lab
    steps:
      - uses: actions/checkout@v4
      - run: pytest -m rvr --junitxml=results/rvr.xml
        env:
          LAB_PASSWORD: ${{ secrets.LAB_PASSWORD }}
      - uses: actions/upload-artifact@v4
        if: always()
        with: {name: rvr-results, path: results/}
'''

M_8_8 = {
    "id": "8.8",
    "title": "GitHub Actions & GitLab CI",
    "hours": 2,
    "summary": "The same pipeline ideas in hosted CI: GitHub Actions workflows (triggers, matrix, needs, self-hosted bench runners, secrets, artifacts) and GitLab CI (stages, rules, tags, JUnit reports), plus checking workflow files from Python.",
    "concepts": [
        {
            "title": "A GitHub Actions workflow",
            "runner": "none",
            "lang": "YAML",
            "filename": ".github/workflows/wifi-tests.yml",
            "concept": "A workflow file in `.github/workflows/` declares **triggers** (`on`: push, pull_request, schedule), **jobs** that run on runners (`runs-on`), dependencies between jobs (`needs`), a **matrix** that fans one job out over combinations, and **steps** that either run shell commands or use published actions (pinned by version). Lab hardware is reached through a **self-hosted runner** on a bench PC, selected by labels. Secrets come from the repository or environment settings.",
            "why": "If the test repo lives on GitHub, Actions gives PR checks and nightly bench runs with no separate CI server. The concepts map one-to-one to Jenkins: runs-on ≈ agent label, needs ≈ stage order, matrix ≈ matrix, secrets ≈ credentials.",
            "syntax": "on: {push: {branches: [main]}, schedule: [{cron: \"30 20 * * *\"}]}\njobs:\n  test:\n    runs-on: [self-hosted, wifi-bench]\n    steps: [{uses: actions/checkout@v4}, {run: pytest}]",
            "code": """name: wifi-tests  ## Shown in the Actions tab
on:  ## Triggers
  push:  ## On pushes...
    branches: [main]  ## ...to main only
  pull_request:  ## On every PR (any target branch)
  schedule:  ## Nightly
    - cron: "30 20 * * *"  ## 20:30 UTC = 02:00 IST
concurrency:  ## At most one run per branch
  group: wifi-tests-${{ github.ref }}  ## Runs on the same ref share a group
  cancel-in-progress: true  ## A new push cancels the outdated run
jobs:  ## Jobs run in parallel unless linked with needs
  lint:  ## Fast checks first
    runs-on: ubuntu-24.04  ## GitHub-hosted VM, pinned image
    steps:  ## Executed in order
      - uses: actions/checkout@v4  ## Clone the repo (pinned major version)
      - uses: actions/setup-python@v5  ## Install Python
        with: {python-version: "3.12"}  ## Inputs to the action
      - run: pip install ruff mypy && ruff check . && mypy src  ## Shell step; non-zero exit fails the job
  unit:  ## Hardware-free tests on several platforms
    needs: lint  ## Only after lint passes
    runs-on: ${{ matrix.os }}  ## Each matrix cell picks its OS
    strategy:  ## How to fan out
      fail-fast: false  ## Let other cells finish when one fails
      matrix:  ## Cartesian product of these lists
        os: [ubuntu-24.04, windows-2022]  ## 2 values
        python: ["3.11", "3.12"]  ## x 2 values = 4 cells
        exclude:  ## Remove combinations
          - {os: windows-2022, python: "3.11"}  ## -> 3 cells
        include:  ## Add or extend combinations
          - {os: ubuntu-24.04, python: "3.13", experimental: true}  ## -> 4 cells
    steps:  ## Same steps in every cell
      - uses: actions/checkout@v4  ## Clone
      - uses: actions/setup-python@v5  ## Python from the matrix
        with: {python-version: "${{ matrix.python }}", cache: pip}  ## Cache pip downloads between runs
      - run: pip install -r requirements.lock && pytest tests/unit --junitxml=results/unit.xml  ## Unit tests
  bench:  ## Real hardware
    needs: unit  ## After unit tests
    if: github.event_name == 'schedule'  ## Nightly only, not on every PR
    runs-on: [self-hosted, wifi-bench, 6ghz]  ## A bench PC registered as a runner with these labels
    timeout-minutes: 240  ## Hard limit for the job
    environment: lab  ## Environment with its own secrets and optional approvals
    steps:  ## On the bench PC
      - uses: actions/checkout@v4  ## Clone onto the bench PC
      - run: pytest -m rvr --junitxml=results/rvr.xml  ## The RF suite
        env:  ## Step-level environment
          LAB_PASSWORD: ${{ secrets.LAB_PASSWORD }}  ## Masked in logs
      - uses: actions/upload-artifact@v4  ## Keep results downloadable
        if: always()  ## Even if the tests failed
        with: {name: rvr-results, path: results/}  ## What to upload""",
            "under": "Each job gets a fresh runner (VM or self-hosted machine) and its own checkout; data passes between jobs only via artifacts or outputs. Step `if: always()` overrides the default 'only if previous steps succeeded', which is how results are uploaded after failures. Self-hosted runners execute untrusted PR code if you let them, so bench runners should only run trusted triggers (schedule, main), as the `if` above ensures.",
            "gotchas": [],
            "best": "Pin actions to versions (or SHAs), run fast jobs first with `needs`, use concurrency groups, restrict self-hosted bench runners to trusted events, keep secrets in environments with approvals for lab access, set `timeout-minutes`, and upload results with `if: always()`.",
        },
        {
            "title": "The same pipeline in GitLab CI",
            "runner": "none",
            "lang": "YAML",
            "filename": ".gitlab-ci.yml",
            "concept": "GitLab CI uses one `.gitlab-ci.yml`: **stages** define order, each job belongs to a stage, `rules` decide when a job runs (merge requests, schedules, branches), **tags** pick runners (a bench runner), `parallel:matrix` fans out, and `artifacts:reports:junit` makes GitLab show test results in merge requests. CI/CD variables (masked, protected) hold secrets.",
            "why": "Many embedded and networking teams host code on GitLab. Knowing both syntaxes, and that the concepts are identical, makes you productive in either.",
            "syntax": "stages: [lint, test, bench]\njob:\n  stage: test\n  tags: [wifi-bench]\n  rules: [{if: '$CI_PIPELINE_SOURCE == \"schedule\"'}]\n  artifacts: {reports: {junit: results/*.xml}}",
            "code": """stages: [lint, unit, bench]  ## Stage order; jobs in one stage run in parallel
default:  ## Settings for every job
  image: registry.lab/wifi-tests:1.4.1  ## The runner image from 8.3
  interrupt: true  ## A newer pipeline may cancel this one
lint:  ## Job name
  stage: lint  ## First stage
  script:  ## Shell commands
    - ruff check .  ## Lint
    - mypy src  ## Types
unit:  ## Software-only tests
  stage: unit  ## After lint
  parallel:  ## Fan out
    matrix:  ## One job per combination
      - PYTHON: ["3.11", "3.12"]  ## Variable values
  script:  ## Uses the matrix variable
    - uv run --python $PYTHON pytest tests/unit --junitxml=results/unit-$PYTHON.xml  ## Separate file per cell
  artifacts:  ## Keep and publish results
    when: always  ## Even on failure
    reports:  ## GitLab-understood report types
      junit: results/unit-*.xml  ## Shown in the merge request widget
bench:  ## Hardware tests
  stage: bench  ## Last
  tags: [wifi-bench, 6ghz]  ## Runs only on runners registered with these tags
  rules:  ## When to create this job
    - if: '$CI_PIPELINE_SOURCE == "schedule"'  ## Nightly schedules
    - if: '$CI_COMMIT_BRANCH == "main"'  ## And on main
      when: manual  ## ...but on main only when someone clicks Run
  resource_group: bench-lab-07  ## Only one job at a time uses this bench
  timeout: 4h  ## Job limit
  script:  ## The RF suite; LAB_PASSWORD is a masked, protected CI/CD variable
    - pytest -m rvr --junitxml=results/rvr.xml  ## Results file
  artifacts:  ## Publish
    when: always  ## Even on failure
    paths: [results/]  ## Downloadable files
    reports:  ## Test report
      junit: results/rvr.xml  ## Parsed by GitLab""",
            "under": "GitLab evaluates `rules` top to bottom when the pipeline is created; the first matching rule decides whether (and how) the job is added. `resource_group` is GitLab's built-in mutex: jobs sharing a group never run concurrently, a simple bench lock. Protected variables are only exposed to pipelines on protected branches, which keeps lab credentials away from arbitrary merge requests.",
            "gotchas": [],
            "best": "Mirror the same structure as Jenkins/Actions (lint → unit → bench), use tags for bench runners and resource_group for exclusive hardware, publish JUnit via reports, keep secrets as masked+protected variables, and validate the file with GitLab's CI Lint before merging.",
        },
        {
            "title": "Checking workflow files in Python",
            "local_only": YAML,
            "files": {"wifi-tests.yml": GH_WORKFLOW},
            "concept": "Workflow files are data, so a small script can expand what CI will actually run and enforce house rules: compute the **matrix** cells after `exclude`/`include` the way GitHub does, derive the job order from `needs`, and flag risky patterns (unpinned actions, self-hosted jobs that can run on pull requests, missing timeouts).",
            "why": "A typo in a matrix can silently drop a platform, and a self-hosted bench runner reachable from pull requests is a security hole. A 1-second lint in pre-commit or CI catches both.",
            "syntax": "wf = yaml.safe_load(open(path))\n# careful: YAML 1.1 parses the key `on` as boolean True",
            "code": """from graphlib import TopologicalSorter  ## Job order from needs
from itertools import product  ## Matrix expansion

import yaml  ## pip install pyyaml

wf = yaml.safe_load(open("wifi-tests.yml"))  ## The workflow (see supporting files)
triggers = wf.get("on", wf.get(True))  ## PyYAML reads the bare key `on` as True (YAML 1.1 booleans)
print("triggers:", sorted(triggers))  ## push, pull_request, schedule
jobs = wf["jobs"]  ## name -> job


def expand(matrix):  ## GitHub's rules: product of lists, minus exclude, plus include
    keys = [k for k in matrix if k not in ("include", "exclude")]  ## Axis names
    cells = [dict(zip(keys, combo)) for combo in product(*(matrix[k] for k in keys))]  ## Cartesian product
    cells = [c for c in cells if not any(all(c.get(k) == v for k, v in ex.items()) for ex in matrix.get("exclude", []))]  ## Drop excluded
    for inc in matrix.get("include", []):  ## Includes extend matching cells or add new ones
        matches = [c for c in cells if all(c.get(k) == v for k, v in inc.items() if k in keys)]  ## Cells matching on axis keys
        if matches and all(k not in keys or c.get(k) == inc[k] for c in matches for k in inc):  ## Same axis values: extend
            for c in matches:  ## Add the extra keys
                c.update(inc)  ## e.g. experimental: true
        else:  ## New combination
            cells.append(dict(inc))  ## Added as its own cell
    return cells  ## Final list


cells = expand(jobs["unit"]["strategy"]["matrix"])  ## The unit job's cells
print(len(cells), "unit cells:", [f"{c['os']}/py{c['python']}" for c in cells])  ## What actually runs
order = TopologicalSorter({name: set([job["needs"]] if isinstance(job.get("needs"), str) else job.get("needs", [])) for name, job in jobs.items()})  ## needs can be a string or a list
print("job order:", list(order.static_order()))  ## lint -> unit -> bench

for name, job in jobs.items():  ## House rules
    for step in job.get("steps", []):  ## Every step
        if "uses" in step and "@" not in step["uses"]:  ## Action without a version
            print(f"{name}: unpinned action {step['uses']}")  ## Supply-chain risk
    runs_on = job["runs-on"] if isinstance(job["runs-on"], list) else [job["runs-on"]]  ## Normalise to a list
    if "self-hosted" in runs_on and "schedule" not in str(job.get("if", "")):  ## Bench job not restricted to trusted triggers
        print(f"{name}: self-hosted runner reachable from pull requests")  ## Security risk
    if "self-hosted" in runs_on and "timeout-minutes" not in job:  ## Hardware jobs must time out
        print(f"{name}: no timeout")  ## Could hold the bench forever
print("checks done")  ## Silence above means the house rules pass""",
            "under": "In YAML 1.1 (which PyYAML implements), `on`, `off`, `yes` and `no` are booleans, so the workflow's `on:` key loads as `True`: a classic surprise when processing GitHub workflows in Python. The include semantics implemented here cover the common cases; GitHub's documentation describes the full algorithm (and `act` or the workflow run itself is the final word).",
            "gotchas": [],
            "best": "Lint workflows in CI (actionlint is excellent; a few Python checks add team rules), expand matrices to see exactly what runs, pin actions, and keep bench jobs on trusted triggers with timeouts.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "local_only": YAML,
            "prompt": "Show the YAML 1.1 boolean surprise: load `on: [push]`, `country: NO` and `enabled: yes` with PyYAML and print the resulting dict.",
            "solution": "PyYAML turns `on` into True, `NO` (Norway!) into False and `yes` into True. Quote such values in YAML you control.",
            "solution_code": """import yaml

print(yaml.safe_load("on: [push]\\ncountry: NO\\nenabled: yes\\nquoted: 'NO'"))""",
        },
        {
            "level": "Medium",
            "prompt": "Convert a cron line `30 20 * * 1-5` (UTC) into the local IST time and weekdays it runs, to check a nightly schedule doesn't start during working hours.",
            "solution": "Parse minute/hour/day-of-week fields; IST is UTC+5:30, which can roll over to the next day.",
            "solution_code": """from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def describe(cron):
    minute, hour, _, _, dow = cron.split()
    lo, hi = (int(x) for x in dow.split("-"))
    out = []
    for d in range(lo, hi + 1):
        utc = datetime(2026, 10, 11 + d, int(hour), int(minute), tzinfo=timezone.utc)
        ist = utc.astimezone(IST)
        out.append(f"{DAYS[ist.weekday()]} {ist:%H:%M} IST")
    return out


print(describe("30 20 * * 1-5"))""",
        },
        {
            "level": "Hard",
            "local_only": YAML,
            "prompt": "Write a GitLab rules evaluator for a simplified `if:` syntax (`$VAR == \"value\"` joined by `&&`), and decide whether the bench job runs for a schedule, a main push and a merge request.",
            "solution": "First matching rule wins; `when` defaults to on_success; no match means the job isn't created.",
            "solution_code": """import re

import yaml

RULES = yaml.safe_load('''
- if: '$CI_PIPELINE_SOURCE == "schedule"'
- if: '$CI_COMMIT_BRANCH == "main" && $CI_PIPELINE_SOURCE == "push"'
  when: manual
''')


def matches(expr, env):
    return all(env.get(var) == val for var, val in re.findall(r'\\$(\\w+) == "([^"]*)"', expr))


def decide(rules, env):
    for rule in rules:
        if matches(rule["if"], env):
            return rule.get("when", "on_success")
    return "not created"


for env in ({"CI_PIPELINE_SOURCE": "schedule"}, {"CI_PIPELINE_SOURCE": "push", "CI_COMMIT_BRANCH": "main"},
            {"CI_PIPELINE_SOURCE": "merge_request_event"}):
    print(env["CI_PIPELINE_SOURCE"], "->", decide(RULES, env))""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "How do you run hardware tests from GitHub Actions or GitLab CI?", "a": "Register self-hosted runners on bench PCs with labels/tags (wifi-bench, 6ghz), route hardware jobs to them, restrict them to trusted events (schedule, protected branches), serialise access (concurrency group / resource_group / external lock), and upload results as artifacts.", "follow": "Why not let PRs run on bench runners? (Untrusted code would execute on lab machines with lab credentials.)"},
        {"level": "Intermediate", "q": "Map Jenkins concepts to GitHub Actions.", "a": "Jenkinsfile → workflow YAML; agent label → runs-on labels; stages → jobs with needs (or steps); parallel/matrix → strategy.matrix; credentials → secrets; post always → if: always(); archiveArtifacts → upload-artifact; junit → a test-report action.", "follow": "And GitLab? (stages/jobs, tags, rules, artifacts:reports:junit, CI/CD variables.)"},
        {"level": "Advanced", "q": "What's tricky about matrix include/exclude?", "a": "exclude removes exact matches from the product; include either extends existing combinations that match all its original axis values or adds a new combination. Misunderstanding it silently drops or duplicates cells; expanding the matrix in a lint step makes it visible.", "follow": "How do you mark a cell as allowed to fail? (continue-on-error with a matrix flag like experimental.)"},
    ],
    "quiz": [
        {"q": "GitHub: run a step even after failures:", "options": ["continue: true", "if: always()", "needs: always", "fail-fast: false"], "answer": 1, "why": "Overrides success()."},
        {"q": "GitLab: run job on bench runners:", "options": ["runs-on", "tags", "agent", "pool"], "answer": 1, "why": "tags select runners."},
        {"q": "2 OS × 2 Python, exclude one, include one new =", "options": ["3", "4", "5", "6"], "answer": 1, "why": "4 − 1 + 1."},
        {"q": "PyYAML loads the key `on:` as...", "options": ["'on'", "True", "None", "Error"], "answer": 1, "why": "YAML 1.1 booleans."},
        {"q": "GitLab built-in mutex for a bench:", "options": ["lock:", "resource_group", "concurrency", "needs"], "answer": 1, "why": "resource_group."},
    ],
    "cards": [
        {"front": "GH Actions job on bench", "back": "`runs-on: [self-hosted, wifi-bench]` + `if: github.event_name == 'schedule'`"},
        {"front": "Upload results always", "back": "`uses: actions/upload-artifact@v4` with `if: always()`"},
        {"front": "GitLab JUnit", "back": "`artifacts: {when: always, reports: {junit: results/*.xml}}`"},
        {"front": "GitLab bench lock", "back": "`resource_group: bench-lab-07`"},
        {"front": "Cancel outdated runs", "back": "GH: `concurrency: {group: ..., cancel-in-progress: true}`; GitLab: `interrupt: true`"},
    ],
}


M_8_9 = {
    "id": "8.9",
    "title": "Secrets Management",
    "hours": 1,
    "summary": "Keep lab credentials out of code, logs and reports: environment variables and secret files, a Secret type that can't be printed, log redaction, and fetching secrets from Vault.",
    "concepts": [
        {
            "title": "Secrets in, never out: env vars, a Secret type, redacted logs",
            "concept": "Secrets enter the program at one place (environment variables injected by CI, or files mounted by Docker/Kubernetes), are validated at startup, and are wrapped in a small `Secret` type whose `repr`/`str` print `'***'`, so they can't leak through `print(config)`, tracebacks or reports. A `logging.Filter` adds a second line of defence by redacting known secret values from every log message.",
            "why": "Test logs, JUnit XML and Allure reports are widely shared (and archived for years). One `print(bench_config)` with an SSH password in it is enough to leak lab access to everyone who can open a CI build.",
            "syntax": "class Secret:\n    def __init__(self, v): self._v = v\n    def get(self): return self._v\n    def __repr__(self): return \"Secret('***')\"",
            "code": """import logging  ## Logging with a redaction filter
import os  ## Environment variables
from dataclasses import dataclass  ## Settings object

os.environ.setdefault("LAB_SSH_PASSWORD", "Wl@n-7-s3cret")  ## Demo only: CI would inject this
os.environ.setdefault("LAB_SNMP_COMMUNITY", "lab7-ro")  ## Demo only


class Secret:  ## A value that refuses to be displayed
    def __init__(self, value: str):  ## Wrap the raw string
        self._value = value  ## Stored privately

    def get(self) -> str:  ## Explicit access where it's really needed
        return self._value  ## e.g. passing to paramiko.connect

    def __repr__(self) -> str:  ## Used by print(obj), f"{obj!r}", tracebacks, dataclass repr
        return "Secret('***')"  ## Never the value

    __str__ = __repr__  ## Same for str() and f"{obj}"


def require(name: str) -> Secret:  ## Read a required secret at startup
    value = os.environ.get(name)  ## Injected by CI / env file
    if not value:  ## Missing or empty
        raise SystemExit(f"missing required secret {name}")  ## Fail fast, naming the variable only
    return Secret(value)  ## Wrapped immediately


@dataclass  ## Bench settings: secrets typed as Secret
class BenchConfig:  ## Everything a test run needs
    bench: str  ## Plain value
    ssh_user: str  ## Plain value
    ssh_password: Secret  ## Wrapped
    snmp_community: Secret  ## Wrapped


cfg = BenchConfig("lab-07", "admin", require("LAB_SSH_PASSWORD"), require("LAB_SNMP_COMMUNITY"))  ## Built once at startup
print(cfg)  ## Safe to print or put in a report
print("password length:", len(cfg.ssh_password.get()))  ## The real value is still usable


class RedactSecrets(logging.Filter):  ## Second line of defence for anything that slips through
    def __init__(self, secrets):  ## The values to hide
        super().__init__()  ## Initialise the base Filter
        self.values = [s.get() for s in secrets if s.get()]  ## Raw strings to look for

    def filter(self, record):  ## Called for every log record
        msg = record.getMessage()  ## Fully formatted message
        for v in self.values:  ## Each secret value
            msg = msg.replace(v, "***")  ## Redact it
        record.msg, record.args = msg, None  ## Replace the message
        return True  ## Keep the record


log = logging.getLogger("bench")  ## Module logger
handler = logging.StreamHandler()  ## To stderr
handler.addFilter(RedactSecrets([cfg.ssh_password, cfg.snmp_community]))  ## Every record passes through the filter
handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))  ## Simple format
log.addHandler(handler)  ## Attach
log.setLevel(logging.INFO)  ## Show INFO
log.info("snmpget -c %s 10.10.30.7 sysName.0", cfg.snmp_community.get())  ## A careless log line with the raw value
log.info("connecting to %s with %s", cfg.bench, cfg.ssh_password)  ## Logging the wrapper is safe anyway""",
            "under": "`print`, f-strings, logging's `%s`, dataclass reprs and traceback locals all go through `__repr__`/`__str__`, so overriding both covers nearly every accidental display. The filter is applied on the handler, so it sees the fully formatted message; filters on handlers run for records from any logger that reaches that handler.",
            "gotchas": [
                {
                    "title": "Dumping the config dict into a report",
                    "note": "A plain dict of settings looks harmless until it's printed in a debug line or attached to an Allure report. Wrap secrets at the boundary so every later display is safe by default.",
                    "wrong": """config = {"bench": "lab-07", "ssh_user": "admin", "ssh_password": "Wl@n-7-s3cret"}
print("run config:", config)""",
                    "fixed": """class Secret(str):
    def __repr__(self):
        return "'***'"


config = {"bench": "lab-07", "ssh_user": "admin", "ssh_password": Secret("Wl@n-7-s3cret")}
print("run config:", config)
print("still usable:", config["ssh_password"].startswith("Wl"))""",
                },
            ],
            "best": "Inject secrets via CI secret stores, env files or mounted files (never command-line arguments or the repo), validate at startup, wrap them immediately, log identities not credentials, add a redaction filter, rotate on any suspected leak, and scan the repo and CI logs for secrets.",
        },
        {
            "title": "Fetching secrets from Vault",
            "files": sim("fake_vault.py"),
            "local_only": VAULT,
            "concept": "A secrets manager (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault) stores credentials centrally with access policies, audit logs and rotation. With Vault's KV v2 engine, a client reads `GET /v1/secret/data/<path>` with an `X-Vault-Token` header and gets the key/value pairs under `data.data`. CI gets a short-lived, read-only token (often via OIDC/JWT login), never a long-lived one. The server here is a minimal simulation of that endpoint.",
            "why": "When 40 benches share credentials, rotating the AP admin password means editing 40 CI configs, unless they all read it from Vault at run time. Vault's audit log also shows exactly which job read which secret.",
            "syntax": "r = requests.get(f\"{VAULT}/v1/secret/data/lab/bench07\", headers={\"X-Vault-Token\": token}, timeout=5)\nsecrets = r.json()[\"data\"][\"data\"]",
            "code": """import os  ## Token comes from the environment
from functools import lru_cache  ## Read each path once per run

import requests  ## pip install requests (hvac is the official client library)

from fake_vault import start  ## Simulated Vault (see supporting files)

VAULT = start()  ## https://vault.lab.example:8200 in real life
os.environ.setdefault("VAULT_TOKEN", "hvs.lab-ci-readonly")  ## Demo only: CI logs in and exports a short-lived token


class VaultError(RuntimeError):  ## Clear, domain-specific failures
    pass  ## No extra behaviour


@lru_cache(maxsize=None)  ## Cache per path: secrets don't change during a test run
def read_secret(path: str) -> dict:  ## Read a KV v2 secret
    r = requests.get(f"{VAULT}/v1/secret/data/{path}", headers={"X-Vault-Token": os.environ["VAULT_TOKEN"]}, timeout=5)  ## Token in a header, never the URL
    if r.status_code == 403:  ## Policy doesn't allow this path (or token expired)
        raise VaultError(f"permission denied for {path}")  ## Path only, no token
    if r.status_code == 404:  ## No such secret
        raise VaultError(f"no secret at {path}")  ## Probably a typo in the bench config
    r.raise_for_status()  ## Anything else unexpected
    body = r.json()["data"]  ## KV v2 wraps data and metadata
    print(f"read {path} (version {body['metadata']['version']})")  ## Log the path and version, never values
    return body["data"]  ## The key/value pairs


bench = read_secret("lab/bench07")  ## Credentials for bench 07
print(sorted(bench))  ## Key names are fine to log
read_secret("lab/bench07")  ## Cached: no second request, no second log line
for path in ("lab/bench99", "prod/core-routers"):  ## A typo and a path outside our policy
    try:  ## Both should fail clearly
        read_secret(path)  ## Attempt
    except VaultError as e:  ## Our own error type
        print("VaultError:", e)  ## Actionable message
os.environ["VAULT_TOKEN"] = "hvs.expired"  ## Simulate an expired token
read_secret.cache_clear()  ## Forget cached values
try:  ## Now even the valid path fails
    read_secret("lab/bench07")  ## 403 with a bad token
except VaultError as e:  ## Reported the same way
    print("VaultError:", e)  ## Time to re-authenticate""",
            "under": "KV v2 keeps versions of each secret (the `metadata.version` field), so a rotation creates version 4 while running jobs that already read version 3 keep working until they finish. `lru_cache` keys on the function arguments; clearing it is how you force a re-read. A real CI integration usually authenticates with the CI system's OIDC token (`auth/jwt/login`) to get a token valid for minutes, scoped by policy to the lab paths.",
            "gotchas": [],
            "best": "Short-lived, least-privilege tokens per pipeline, read secrets at the start of the run, keep them in memory only (wrapped), log paths and versions not values, handle 403/404 with clear errors, and rotate centrally.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Load settings from a `.env`-style text (KEY=value lines, comments, quoted values) into a dict without any library, wrapping keys that end with `_PASSWORD` or `_TOKEN` in a masked type.",
            "solution": "Skip blanks and comments, split on the first '=', strip quotes, wrap by suffix.",
            "solution_code": """class Secret(str):
    def __repr__(self):
        return "'***'"


ENV_TEXT = '''# bench 07
BENCH=lab-07
LAB_SSH_PASSWORD="Wl@n-7-s3cret"
LANFORGE_TOKEN=lf-0f9e8d7c6b5a
ATTEN_URL=http://10.10.40.21
'''
settings = {}
for line in ENV_TEXT.splitlines():
    if not line.strip() or line.lstrip().startswith("#"):
        continue
    key, value = line.split("=", 1)
    value = value.strip().strip('"').strip("'")
    settings[key] = Secret(value) if key.endswith(("_PASSWORD", "_TOKEN")) else value
print(settings)""",
        },
        {
            "level": "Medium",
            "prompt": "Scan text (a log or a diff) for things that look like secrets: AWS-style keys, private key headers, `password=` assignments, and Vault tokens (`hvs.`), reporting line numbers without printing the values.",
            "solution": "A few regexes with names; report the rule and line only. (Real scanners like gitleaks add entropy checks and hundreds of rules.)",
            "solution_code": """import re

RULES = {
    "aws access key": r"AKIA[0-9A-Z]{16}",
    "private key": r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "password assignment": r"(?i)password\\s*[=:]\\s*\\S+",
    "vault token": r"hvs\\.[A-Za-z0-9_-]{10,}",
}
TEXT = '''connecting to ap-lab-07
ssh_password = Wl@n-7-s3cret
export VAULT_TOKEN=hvs.CAESIJ3k_example_token
-----BEGIN OPENSSH PRIVATE KEY-----
all good here'''
for n, line in enumerate(TEXT.splitlines(), 1):
    for name, pattern in RULES.items():
        if re.search(pattern, line):
            print(f"line {n}: possible {name}")""",
        },
        {
            "level": "Hard",
            "files": sim("fake_vault.py"),
            "local_only": VAULT,
            "prompt": "Write `get_credentials(bench)` that reads `lab/<bench>` from Vault and returns a dataclass with the password wrapped in a Secret, and prove the returned object is safe to print.",
            "solution": "Combine the Vault read with the Secret wrapper at the boundary.",
            "solution_code": """from dataclasses import dataclass

import requests
from fake_vault import TOKEN, start

VAULT = start()


class Secret:
    def __init__(self, v):
        self._v = v

    def get(self):
        return self._v

    def __repr__(self):
        return "Secret('***')"


@dataclass(frozen=True)
class Credentials:
    user: str
    password: Secret
    snmp: Secret


def get_credentials(bench):
    r = requests.get(f"{VAULT}/v1/secret/data/lab/{bench}", headers={"X-Vault-Token": TOKEN}, timeout=5)
    r.raise_for_status()
    d = r.json()["data"]["data"]
    return Credentials(d["ssh_user"], Secret(d["ssh_password"]), Secret(d["snmp_community"]))


creds = get_credentials("bench07")
print(creds)
print(creds.password.get() == "Wl@n-7-s3cret")""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Where should test credentials live?", "a": "In a secret store (CI credentials, Vault, cloud secret manager), injected at run time via environment variables or mounted files. Never in the repo, Dockerfiles, command lines, or logs.", "follow": "Why not command-line arguments? (Visible in process listings and CI logs.)"},
        {"level": "Intermediate", "q": "How do you stop secrets appearing in logs and reports?", "a": "Wrap them in a type with a masked repr at the boundary, log identities not credentials, add a redaction filter on log handlers, rely on CI masking, and scan artifacts.", "follow": "Is CI masking enough? (No: it misses transformed values, like base64 or URL-encoded secrets.)"},
        {"level": "Advanced", "q": "Design secret access for 40 lab benches in CI.", "a": "Vault (or similar) with per-bench paths, CI authenticates via OIDC/JWT to get short-lived tokens scoped by policy to lab paths, jobs read secrets at start and keep them in memory, rotation done centrally with versioned KV, and audit logs reviewed.", "follow": "What happens to running jobs during rotation? (They keep the version they read; new jobs get the new version.)"},
    ],
    "quiz": [
        {"q": "Override to make print(obj) safe:", "options": ["__eq__", "__repr__ (and __str__)", "__hash__", "__len__"], "answer": 1, "why": "Display paths use them."},
        {"q": "Vault KV v2 values are under...", "options": ["data", "data.data", "secret", "values"], "answer": 1, "why": "data.data, with data.metadata."},
        {"q": "Best CI token for Vault:", "options": ["Root token", "Short-lived, read-only, path-scoped", "Personal token", "No token"], "answer": 1, "why": "Least privilege."},
        {"q": "Redact secrets for every log record:", "options": ["print", "logging.Filter on the handler", "str.replace in each call", "logging.disable"], "answer": 1, "why": "Central and automatic."},
        {"q": "After a secret is pushed to git, first...", "options": ["Rewrite history", "Rotate the secret", "Delete the repo", "Ignore it"], "answer": 1, "why": "Assume it's compromised."},
    ],
    "cards": [
        {"front": "Secret wrapper", "back": "Class with `get()` and `__repr__ = __str__ = lambda: '***'`"},
        {"front": "Required secret", "back": "`os.environ.get(NAME)` → missing → exit naming the variable only"},
        {"front": "Log redaction", "back": "`logging.Filter` replacing secret values in `record.getMessage()`"},
        {"front": "Vault read", "back": "`GET /v1/secret/data/<path>` with `X-Vault-Token` → `data.data`"},
        {"front": "Leak response", "back": "Rotate first, then purge history, then add scanning"},
    ],
}


M_8_10 = {
    "id": "8.10",
    "title": "Nightly Regression Design & Lab Locking",
    "hours": 3,
    "summary": "Design the nightly run: exclusive bench reservations with leases that survive crashed jobs, and a scheduler that fits suites onto benches by capability, priority and the time window.",
    "concepts": [
        {
            "title": "Bench reservations with leases (SQLite)",
            "local_only": SQLITE,
            "concept": "A bench lock must be **exclusive** (two jobs never hold the same bench), **atomic** (no race between checking and taking), and **self-healing** (a job that crashes or is killed doesn't hold the bench forever). A lease does all three: acquiring is a single `UPDATE ... WHERE holder IS NULL OR lease_until < now` (atomic in the database), the holder renews the lease with heartbeats while it works, and an expired lease can be taken over. SQLite is enough for a single lab server; the same SQL works on PostgreSQL for a shared service.",
            "why": "Jenkins' lockable resources only protect jobs inside one Jenkins. Benches are also used by GitHub runners, manual debugging sessions and scripts. A small reservation service that everyone uses is how labs stop 'who reset my AP?' incidents.",
            "syntax": "UPDATE benches SET holder=?, lease_until=? WHERE name=? AND (holder IS NULL OR lease_until < ?)\n-- rowcount 1 = acquired, 0 = busy",
            "code": """import sqlite3  ## Standard-library database


class Clock:  ## Injectable time so the example is deterministic
    def __init__(self):  ## Start at t=0
        self.t = 0.0  ## Seconds

    def __call__(self):  ## Used as now()
        return self.t  ## Current fake time


class BenchLocks:  ## Reservation service backed by one table
    def __init__(self, db, now, lease=300):  ## lease = seconds a reservation lasts without renewal
        self.db, self.now, self.lease = db, now, lease  ## Dependencies
        db.execute("CREATE TABLE IF NOT EXISTS benches (name TEXT PRIMARY KEY, labels TEXT, holder TEXT, lease_until REAL)")  ## One row per bench

    def add(self, name, labels):  ## Register a bench with capability labels
        self.db.execute("INSERT INTO benches VALUES (?, ?, NULL, 0)", (name, ",".join(sorted(labels))))  ## Initially free

    def acquire(self, job, label):  ## Take any free bench with the label; None if all busy
        now = self.now()  ## One timestamp for the whole decision
        for (name,) in self.db.execute("SELECT name FROM benches WHERE ',' || labels || ',' LIKE ? ORDER BY name", (f"%,{label},%",)).fetchall():  ## Candidate benches
            cur = self.db.execute("UPDATE benches SET holder = ?, lease_until = ? WHERE name = ? AND (holder IS NULL OR lease_until < ?)",  ## Atomic check-and-take
                                  (job, now + self.lease, name, now))  ## Only succeeds if free or expired
            if cur.rowcount == 1:  ## We got it
                self.db.commit()  ## Make it visible to others
                return name  ## The reserved bench
        return None  ## Everything busy

    def renew(self, job, name):  ## Heartbeat from the running job
        cur = self.db.execute("UPDATE benches SET lease_until = ? WHERE name = ? AND holder = ?", (self.now() + self.lease, name, job))  ## Only the holder can renew
        self.db.commit()  ## Persist
        return cur.rowcount == 1  ## False means we lost the bench (lease expired and was taken)

    def release(self, job, name):  ## Give the bench back
        self.db.execute("UPDATE benches SET holder = NULL, lease_until = 0 WHERE name = ? AND holder = ?", (name, job))  ## Only the holder can release
        self.db.commit()  ## Persist


clock = Clock()  ## Fake time
locks = BenchLocks(sqlite3.connect(":memory:"), now=clock)  ## A file path like /srv/lab/locks.db in real use
locks.add("bench-03", {"5ghz", "6ghz"})  ## Two benches
locks.add("bench-07", {"6ghz"})  ## Only 6 GHz

print("rvr#101 ->", locks.acquire("rvr#101", "6ghz"))  ## First free 6 GHz bench
print("roam#102 ->", locks.acquire("roam#102", "6ghz"))  ## The other one
print("dfs#103 ->", locks.acquire("dfs#103", "6ghz"))  ## None: both busy
clock.t = 200  ## 200 s later rvr#101 sends a heartbeat...
print("rvr#101 renewed:", locks.renew("rvr#101", "bench-03"))  ## ...extending its lease to t=500
clock.t = 400  ## roam#102 crashed at t=0 and never renewed; its lease ended at t=300
print("dfs#103 ->", locks.acquire("dfs#103", "6ghz"))  ## Takes over the expired bench-07
print("roam#102 renew:", locks.renew("roam#102", "bench-07"))  ## The zombie job learns it lost the bench
locks.release("rvr#101", "bench-03")  ## Normal release
print("free now:", [n for (n,) in locks.db.execute("SELECT name FROM benches WHERE holder IS NULL")])  ## bench-03""",
            "under": "The conditional `UPDATE` is the whole trick: the database evaluates the `WHERE` and writes in one statement, so of two jobs racing for the same bench exactly one gets `rowcount == 1`. Renew and release include `holder = ?` so a job can never extend or free someone else's reservation. Lease length is a trade-off: long enough to survive a missed heartbeat or two, short enough that a crashed job's bench comes back quickly.",
            "gotchas": [
                {
                    "title": "A lock with no expiry",
                    "note": "If a job is killed (agent reboot, OOM, cancelled build) between acquire and release, a plain lock flag stays set forever and the bench silently drops out of every nightly run until someone notices. Leases make the system recover on its own.",
                    "wrong": """benches = {"bench-07": None}


def acquire(job):
    if benches["bench-07"] is None:
        benches["bench-07"] = job
        return True
    return False


acquire("roam#102")
print("next night, bench free?", acquire("rvr#201"))""",
                    "fixed": """LEASE = 300
benches = {"bench-07": (None, 0.0)}


def acquire(job, now):
    holder, until = benches["bench-07"]
    if holder is None or until < now:
        benches["bench-07"] = (job, now + LEASE)
        return True
    return False


acquire("roam#102", now=0)
print("next night, bench free?", acquire("rvr#201", now=86400))""",
                },
            ],
            "best": "One reservation service for all consumers (CI, runners, humans), atomic acquire, leases with heartbeats, holder-checked renew/release, a short grace period before takeover, an audit table of who held what when, and a bench health check right after acquiring.",
        },
        {
            "title": "Planning the night: suites onto benches",
            "concept": "A nightly plan assigns each suite (duration, required capabilities, priority) to a bench that has the capabilities and enough time left in the window. A simple, effective heuristic: sort by priority, then by duration (longest first), and put each suite on the capable bench that frees up earliest. Whatever doesn't fit is reported, so you can add benches, shorten suites or move them to the weekend.",
            "why": "A lab with 5 benches and 30 suites can't run everything every night. An explicit plan guarantees the critical suites (release-blocking RvR, roaming) always run, uses idle benches, and makes the trade-offs visible instead of accidental.",
            "syntax": "for suite in sorted(suites, key=lambda s: (s.priority, -s.minutes)):\n    bench = min(capable(suite), key=finish_time)",
            "code": """from dataclasses import dataclass, field  ## Plain data classes


@dataclass  ## One test suite
class Suite:  ## What has to run tonight
    name: str  ## Suite name
    minutes: int  ## Expected duration (from history)
    needs: set  ## Required capabilities
    priority: int  ## 1 = must run


@dataclass  ## One bench
class Bench:  ## Where suites can run
    name: str  ## Bench name
    caps: set  ## Capabilities
    busy_until: int = 0  ## Minutes after the window opens
    plan: list = field(default_factory=list)  ## Assigned (start, suite) pairs


WINDOW = 8 * 60  ## 22:00 to 06:00
SUITES = [Suite("rvr-6g", 210, {"6ghz", "attenuator"}, 1), Suite("rvr-5g", 180, {"attenuator"}, 1),  ## Release-blocking
          Suite("roam-11r", 120, {"two_ap"}, 1), Suite("interop-clients", 240, {"client_farm"}, 2),  ## Important
          Suite("dfs-radar", 150, {"5ghz", "radar_gen"}, 2), Suite("soak-24h-lite", 300, {"6ghz"}, 3),  ## Nice to have
          Suite("power-save", 90, {"power_meter"}, 3)]  ## No bench has a power meter tonight
BENCHES = [Bench("bench-03", {"5ghz", "6ghz", "attenuator", "two_ap"}), Bench("bench-05", {"5ghz", "radar_gen", "attenuator"}),  ## Bench capabilities
           Bench("bench-07", {"6ghz", "client_farm"})]  ## from the inventory

unscheduled = []  ## Suites that didn't fit
for s in sorted(SUITES, key=lambda s: (s.priority, -s.minutes)):  ## Priority first, then longest first
    capable = [b for b in BENCHES if s.needs <= b.caps and b.busy_until + s.minutes <= WINDOW]  ## Has capabilities and time
    if not capable:  ## Nowhere to put it
        unscheduled.append(s.name)  ## Report it
        continue  ## Next suite
    bench = min(capable, key=lambda b: b.busy_until)  ## Earliest available capable bench
    bench.plan.append((bench.busy_until, s.name))  ## Start time and suite
    bench.busy_until += s.minutes  ## Bench busy until then



def clock(offset):  ## Minutes after 22:00 -> "HH:MM"
    h, m = divmod(22 * 60 + offset, 60)  ## Absolute minutes -> hours, minutes
    return f"{h % 24:02d}:{m:02d}"  ## Wrap past midnight


for b in BENCHES:  ## The plan, per bench
    slots = ", ".join(f"{clock(start)} {name}" for start, name in b.plan)  ## Start time and suite
    print(f"{b.name}: {slots}  [{b.busy_until / WINDOW:.0%} used]")  ## Utilisation of the window
print("not scheduled:", unscheduled)  ## Visible trade-offs""",
            "under": "This is a greedy list-scheduling heuristic for a bin-packing-like problem: it isn't guaranteed optimal, but it's predictable, explains itself and is usually close enough. `s.needs <= b.caps` is a set subset test. Durations should come from history (median of recent runs plus a margin), which is one more reason to store results in a database (Phase 9).",
            "gotchas": [],
            "best": "Keep suite metadata (duration, capabilities, priority, owner) next to the tests, compute the plan before the window opens, publish it, alert when priority-1 suites don't fit, and feed actual durations back into the next plan.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Given suite durations (minutes) and an 8-hour window on one bench, return which suites fit when you add them in priority order, and the minutes left.",
            "solution": "Accumulate while the running total stays within the window; skip (don't stop at) a suite that doesn't fit, so smaller later ones can still run.",
            "solution_code": """suites = [("rvr-6g", 210), ("roam-11r", 120), ("interop", 240), ("dfs", 90), ("power", 45)]
window, used, planned = 480, 0, []
for name, minutes in suites:
    if used + minutes <= window:
        planned.append(name)
        used += minutes
print(planned, "| minutes left:", window - used)""",
        },
        {
            "level": "Medium",
            "local_only": SQLITE,
            "prompt": "Add an audit trail to reservations: every acquire/release inserts a row (bench, job, action, time), and print the bench-07 history.",
            "solution": "A second table written in the same transaction as the state change.",
            "solution_code": """import sqlite3

db = sqlite3.connect(":memory:")
db.executescript('''CREATE TABLE benches(name TEXT PRIMARY KEY, holder TEXT);
CREATE TABLE audit(bench TEXT, job TEXT, action TEXT, t REAL);
INSERT INTO benches VALUES ('bench-07', NULL);''')


def acquire(job, t):
    with db:
        ok = db.execute("UPDATE benches SET holder=? WHERE name='bench-07' AND holder IS NULL", (job,)).rowcount == 1
        db.execute("INSERT INTO audit VALUES ('bench-07', ?, ?, ?)", (job, "acquire" if ok else "denied", t))
    return ok


def release(job, t):
    with db:
        db.execute("UPDATE benches SET holder=NULL WHERE name='bench-07' AND holder=?", (job,))
        db.execute("INSERT INTO audit VALUES ('bench-07', ?, 'release', ?)", (job, t))


acquire("rvr#101", 0); acquire("manual:utkarsh", 60); release("rvr#101", 3600); acquire("manual:utkarsh", 3700)
for row in db.execute("SELECT t, job, action FROM audit ORDER BY t"):
    print(row)""",
        },
        {
            "level": "Hard",
            "prompt": "Estimate tonight's suite durations from history: use the median of the last 5 runs plus 15% margin, falling back to a default for suites with fewer than 3 runs.",
            "solution": "statistics.median for robustness against one slow outlier; explicit fallback for new suites.",
            "solution_code": """import statistics

HISTORY = {"rvr-6g": [198, 205, 260, 201, 199, 203], "roam-11r": [118, 121], "dfs": [140, 151, 149, 300, 146]}
DEFAULT = 180


def estimate(name):
    runs = HISTORY.get(name, [])[-5:]
    if len(runs) < 3:
        return DEFAULT, "default"
    return round(statistics.median(runs) * 1.15), f"median of {len(runs)}"


for suite in ("rvr-6g", "roam-11r", "dfs", "new-mlo"):
    print(suite, *estimate(suite))""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "How do you prevent two automation jobs from using the same bench?", "a": "A single reservation service used by every consumer, with atomic acquire (conditional update or a lock server), leases with heartbeats so crashed jobs don't hold benches forever, holder-checked release, and an audit log.", "follow": "Why not a file lock on the bench PC? (Other machines and CI systems can't see it reliably, and it dies with the host.)"},
        {"level": "Intermediate", "q": "How would you design a nightly regression for limited lab hardware?", "a": "Inventory benches with capabilities, give suites metadata (duration from history, needs, priority, owner), compute a plan that guarantees priority-1 suites, report what didn't fit, run with reservations and timeouts, publish results and a morning summary, and feed actual durations back.", "follow": "What do you do when priority-1 suites don't fit? (Alert, add capacity, split suites, or shorten via smarter test selection.)"},
        {"level": "Advanced", "q": "What can go wrong with leases?", "a": "Clock skew between hosts (use the DB's clock), pauses longer than the lease (GC, laptop sleep) causing a job to lose its bench without knowing (check renew results and stop), and takeovers of benches left in a bad state (health check and reset after acquiring).", "follow": "How do you choose the lease length? (Several heartbeat intervals; balance recovery speed against false takeovers.)"},
    ],
    "quiz": [
        {"q": "Atomic acquire in SQL:", "options": ["SELECT then UPDATE", "UPDATE ... WHERE holder IS NULL, check rowcount", "INSERT OR IGNORE only", "A Python lock"], "answer": 1, "why": "One statement decides."},
        {"q": "A crashed job's bench is recovered by...", "options": ["Manual cleanup only", "Lease expiry", "Restarting the DB", "Rebooting the bench"], "answer": 1, "why": "No heartbeat, lease ends."},
        {"q": "`renew` returning False means...", "options": ["DB error", "The job lost the reservation", "Lease extended", "Bench offline"], "answer": 1, "why": "Stop using the bench."},
        {"q": "Greedy plan ordering used here:", "options": ["Shortest first", "Priority, then longest first", "Alphabetical", "Random"], "answer": 1, "why": "Big important items placed first."},
        {"q": "`s.needs <= b.caps` tests...", "options": ["Numeric comparison", "Subset (bench has every needed capability)", "Equality", "Overlap"], "answer": 1, "why": "Set subset."},
    ],
    "cards": [
        {"front": "Atomic reservation", "back": "`UPDATE benches SET holder=?, lease_until=? WHERE name=? AND (holder IS NULL OR lease_until < now)`"},
        {"front": "Heartbeat", "back": "Renew lease periodically; renew fails → stop, you lost the bench"},
        {"front": "Safe release", "back": "`... WHERE name=? AND holder=?` (only the holder)"},
        {"front": "Nightly plan", "back": "Priority, longest first, earliest capable bench; report unscheduled"},
        {"front": "Duration estimate", "back": "Median of recent runs × margin; default for new suites"},
    ],
}


NIGHTS = '''HISTORY = {  # test -> outcomes for the last 10 nights, oldest first (P pass, F fail)
    "test_rvr[5G-42dB]":      "PPPPPPPPFF",
    "test_rvr[6G-30dB]":      "PPPPPPPPPP",
    "test_roam_11r":          "PFPPFPFPPF",
    "test_dfs_ch52":          "FFFFFFFFFF",
    "test_assoc_wpa3":        "PPPPPPPPPP",
    "test_mlo_link_switch":   "PPPPPPPPPF",
}
PASS_RATE = [96.2, 95.8, 97.1, 96.5, 95.4, 96.9, 95.5, 96.0, 91.3, 89.7]
'''

M_8_11 = {
    "id": "8.11",
    "title": "Automatic Triage & Dashboards",
    "hours": 2,
    "summary": "Turn hundreds of nightly failures into a short, actionable list: normalised failure signatures, known-issue matching, new-vs-flaky-vs-broken classification from history, and trend charts for dashboards.",
    "concepts": [
        {
            "title": "Failure signatures and known-issue matching",
            "concept": "Raw failure messages differ in every run (timestamps, MACs, IPs, measured numbers), so identical problems look unique. **Normalising** them (replace variable parts with placeholders) produces a **signature** that groups failures across tests and nights. Signatures are then matched against a table of **known issues** (regex → ticket and owner), so only genuinely new problems need a human.",
            "why": "A nightly run with 60 failures where 55 are the same known firmware bug and 4 are a lab DHCP outage should be reported as 3 lines, not 60. That's the difference between people reading the report and ignoring it.",
            "syntax": "sig = re.sub(r\"\\d+(\\.\\d+)?\", \"<N>\", re.sub(MAC, \"<MAC>\", msg))\nfor pattern, ticket in KNOWN: if re.search(pattern, sig): ...",
            "code": """import re  ## Normalisation and matching
from collections import defaultdict  ## Grouping

FAILURES = [  ## (test, message) from tonight's JUnit files
    ("test_rvr[5G-42dB]", "AssertionError: 5G at 42 dB: 135.9 Mbps < KPI 150"),  ## Throughput miss
    ("test_rvr[5G-48dB]", "AssertionError: 5G at 48 dB: 61.2 Mbps < KPI 80"),  ## Same problem, different numbers
    ("test_roam_11r", "TimeoutError: sta 02:00:00:00:01:00 did not reassociate to 3c:84:6a:12:34:80 within 5 s"),  ## Roam
    ("test_roam_11k", "TimeoutError: sta 02:00:00:00:02:00 did not reassociate to 3c:84:6a:12:34:80 within 5 s"),  ## Same signature
    ("test_assoc_wpa3", "ConnectionError: DHCP no offer on 192.168.100.0/24 after 30 s (2026-10-12 01:14:07)"),  ## Lab problem
    ("test_mlo_switch", "AssertionError: link switch took 412 ms (limit 100 ms)"),  ## Something new
]  ## End of failures

RULES = [  ## Variable parts -> placeholders (order matters: specific before generic)
    (r"\\b\\d{4}-\\d{2}-\\d{2}[ T]\\d{2}:\\d{2}:\\d{2}\\b", "<TIME>"),  ## Timestamps
    (r"\\b[0-9a-f]{2}(:[0-9a-f]{2}){5}\\b", "<MAC>"),  ## MAC addresses
    (r"\\b\\d{1,3}(\\.\\d{1,3}){3}(/\\d+)?\\b", "<IP>"),  ## IPv4 addresses and prefixes
    (r"\\b\\d+(\\.\\d+)?\\b", "<N>"),  ## Any other number
]  ## End of rules
KNOWN = [  ## Known issues: signature regex -> (ticket, category)
    (r"did not reassociate to <MAC> within", ("FW-2231", "product: 11r reassoc timeout")),  ## Firmware bug under investigation
    (r"DHCP no offer", ("LAB-118", "environment: lab DHCP")),  ## Lab infrastructure
]  ## End of known issues


def signature(msg):  ## Normalised message = the problem's fingerprint
    for pattern, placeholder in RULES:  ## Apply each rule
        msg = re.sub(pattern, placeholder, msg)  ## Replace variable parts
    return msg  ## Groupable key


groups = defaultdict(list)  ## signature -> tests
for test, msg in FAILURES:  ## Group tonight's failures
    groups[signature(msg)].append(test)  ## Same problem, same bucket, whichever test hit it

for sig, tests in groups.items():  ## One line per distinct problem
    known = next((info for pattern, info in KNOWN if re.search(pattern, sig)), None)  ## First matching known issue
    label = f"{known[0]} ({known[1]})" if known else "NEW: needs triage"  ## Ticket or call to action
    print(f"{len(tests)}x {label}: {sig}")  ## Count, label, signature
    print("    tests:", ", ".join(tests))  ## Which tests hit it""",
            "under": "Rule order matters: the timestamp rule must run before the generic number rule, or `2026-10-12` would become `<N>-<N>-<N>`. Grouping by signature alone puts the 11r and 11k roaming failures in one bucket, because they're the same underlying problem; teams that prefer to keep different tests apart add the test name (without parameter ids) to the key. Known-issue patterns match the normalised signature, so they're written once and stay valid as numbers change.",
            "gotchas": [
                {
                    "title": "Grouping by the raw failure message",
                    "note": "Every message contains a different MAC, measurement or timestamp, so grouping by raw text produces one 'unique' failure per test and the triage report is as long as the failure list. Normalise first.",
                    "wrong": """msgs = ["sta 02:00:00:00:01:00 did not reassociate within 5 s",
        "sta 02:00:00:00:02:00 did not reassociate within 5 s",
        "sta 02:00:00:00:03:00 did not reassociate within 5 s"]
print("distinct problems:", len(set(msgs)))""",
                    "fixed": """import re

msgs = ["sta 02:00:00:00:01:00 did not reassociate within 5 s",
        "sta 02:00:00:00:02:00 did not reassociate within 5 s",
        "sta 02:00:00:00:03:00 did not reassociate within 5 s"]
norm = {re.sub(r"\\b[0-9a-f]{2}(:[0-9a-f]{2}){5}\\b", "<MAC>", m) for m in msgs}
print("distinct problems:", len(norm), norm)""",
                },
            ],
            "best": "Normalise variable tokens (times, MACs, IPs, numbers, temp paths), group by signature, keep known issues as reviewed data with owners and tickets, separate product/environment/test-code categories, and put NEW signatures at the top of the morning report.",
        },
        {
            "title": "History, flakiness and trend charts",
            "files": {"history.py": NIGHTS},
            "local_only": MPL,
            "capture": "trend.png",
            "image_alt": "Line chart of nightly pass rate over ten nights with a dashed 95 percent target line; the last two nights fall below it",
            "concept": "Each test's outcomes over recent nights tell you what kind of failure it is: **new** (passed until recently, now fails), **flaky** (flips between pass and fail), **broken** (fails every night) or **healthy**. Counting flips is a simple flakiness score. Suite-level pass rate per night, plotted against a target, is the headline trend for a dashboard.",
            "why": "A new failure tonight is probably caused by tonight's firmware and is urgent; a flaky test needs test-code or lab work; a permanently broken test needs a decision (fix or quarantine). Treating all three the same wastes everyone's time.",
            "syntax": "flips = sum(a != b for a, b in zip(h, h[1:]))\nnew = h[-1] == \"F\" and h[:-2].count(\"F\") == 0",
            "code": """import matplotlib  ## pip install matplotlib

matplotlib.use("Agg")  ## Headless
import matplotlib.pyplot as plt  ## Chart

from history import HISTORY, PASS_RATE  ## Last 10 nights (see supporting files)


def classify(h):  ## h is a string like "PPPPPPPPFF", oldest first
    flips = sum(a != b for a, b in zip(h, h[1:]))  ## How often the outcome changed
    if "F" not in h:  ## Never failed
        return "healthy", flips  ## Nothing to do
    if set(h) == {"F"}:  ## Failed every night
        return "broken", flips  ## Needs a fix or quarantine decision
    if h.endswith("F") and flips <= 1:  ## Passed steadily, then switched to failing
        return "NEW", flips  ## Likely caused by a recent change: urgent
    return "flaky", flips  ## Flips back and forth


ORDER = {"NEW": 0, "flaky": 1, "broken": 2, "healthy": 3}  ## Report order: most urgent first
rows = sorted(((classify(h), test, h) for test, h in HISTORY.items()), key=lambda r: (ORDER[r[0][0]], r[1]))  ## Classify and sort
for (kind, flips), test, h in rows:  ## Triage table
    print(f"{kind:<8} {test:<22} {h}  flips={flips}  pass={h.count('P') * 10}%")  ## 10 nights -> % pass

nights = list(range(1, len(PASS_RATE) + 1))  ## Night index
fig, ax = plt.subplots(figsize=(6.5, 3))  ## Dashboard-sized chart
ax.plot(nights, PASS_RATE, marker="o", color="#0A6C8A", label="Pass rate")  ## The trend
ax.axhline(95, color="grey", linestyle="--", linewidth=1, label="Target 95%")  ## Target line
below = [(n, r) for n, r in zip(nights, PASS_RATE) if r < 95]  ## Nights under target
ax.scatter([n for n, _ in below], [r for _, r in below], color="#C2410C", zorder=3, label="Below target")  ## Highlight them
ax.set(xlabel="Night", ylabel="Pass rate (%)", title="Nightly regression pass rate", ylim=(85, 100))  ## Labels and range
ax.legend(loc="lower left")  ## Legend out of the way
fig.savefig("trend.png", dpi=90, bbox_inches="tight")  ## For the dashboard / report
plt.close(fig)  ## Free memory
print("nights below target:", [n for n, _ in below])  ## The same fact as text""",
            "under": "Flip counting is crude but robust; more careful flakiness scores weight recent nights or require a minimum number of runs. The 'NEW' rule (steady passes, then failing) catches regressions introduced by the latest builds, and the dip below target on the last two nights lines up with the two new failures. Dashboards (Grafana, Superset) usually read these numbers from a database rather than images, which is what Phase 9.2 sets up.",
            "gotchas": [],
            "best": "Store every result (test, build, bench, outcome, duration, signature) so history is a query away, classify failures before people look at them, quarantine flaky tests with tickets instead of retrying forever, report NEW failures first with the suspect builds, and chart the trend against a target.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Normalise these messages and count distinct signatures: two throughput misses with different numbers, and one timeout on a different port.",
            "solution": "Replacing numbers collapses the throughput messages; the timeout stays separate.",
            "solution_code": """import re

msgs = ["5G at 42 dB: 135.9 Mbps < KPI 150", "5G at 48 dB: 61.2 Mbps < KPI 80", "iperf3 timeout on port 5211"]
sigs = {re.sub(r"\\b\\d+(\\.\\d+)?\\b", "<N>", m) for m in msgs}
print(len(sigs))
for s in sorted(sigs):
    print(s)""",
        },
        {
            "level": "Medium",
            "prompt": "Find the first bad build for a NEW failure: given per-build outcomes for one test, report the build where it started failing and the last good build.",
            "solution": "Scan from the newest backwards until the first pass; the build after it is the first bad one.",
            "solution_code": """builds = [("7.4.1-b210", "P"), ("7.4.1-b211", "P"), ("7.4.2-b001", "P"), ("7.4.2-b002", "F"), ("7.4.2-b003", "F")]
last_good = None
for i in range(len(builds) - 1, -1, -1):
    if builds[i][1] == "P":
        last_good = i
        break
print("last good:", builds[last_good][0], "| first bad:", builds[last_good + 1][0])""",
        },
        {
            "level": "Hard",
            "prompt": "Emit tonight's per-suite metrics in InfluxDB line protocol (measurement, tags, fields, timestamp in ns) so Grafana can chart them, escaping spaces in tag values.",
            "solution": "`measurement,tag=v,tag2=v field=1,field2=2.5 1760300000000000000`; tag values escape spaces and commas with backslashes; integer fields end with `i`.",
            "solution_code": """def escape_tag(v):
    return str(v).replace(",", "\\\\,").replace(" ", "\\\\ ").replace("=", "\\\\=")


def line(measurement, tags, fields, ts_ns):
    tag_part = ",".join(f"{k}={escape_tag(v)}" for k, v in sorted(tags.items()))
    field_part = ",".join(f"{k}={v}i" if isinstance(v, int) else f"{k}={v}" for k, v in fields.items())
    return f"{measurement},{tag_part} {field_part} {ts_ns}"


TS = 1760300000 * 10**9
for suite, passed, failed, rate in [("rvr", 20, 2, 90.9), ("roaming suite", 14, 1, 93.3)]:
    print(line("nightly", {"suite": suite, "bench": "lab-07", "fw": "7.4.2-b003"},
               {"passed": passed, "failed": failed, "pass_rate": rate}, TS))""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "How do you reduce triage effort for a large nightly suite?", "a": "Normalise failure messages into signatures, group failures by signature, auto-match known issues to tickets, classify by history (new, flaky, broken), separate environment failures from product failures, and report only what's new and actionable first.", "follow": "Where do known-issue rules live? (Version-controlled data reviewed like code, with owners.)"},
        {"level": "Intermediate", "q": "How do you detect a flaky test?", "a": "From history: outcomes that flip between pass and fail on the same code and firmware, or pass on rerun. Count flips or reruns over a window; quarantine above a threshold with a ticket.", "follow": "Why not just retry automatically? (It hides real intermittent product bugs, e.g. roaming races.)"},
        {"level": "Advanced", "q": "What would your morning regression dashboard show?", "a": "Pass rate trend vs target, NEW failures with suspect builds, known issues by ticket with counts, environment problems by bench, flaky-test list, suite durations vs plan, and bench utilisation, all drilling down to logs and artifacts.", "follow": "What data model supports it? (Results table keyed by run, build, bench, test with outcome, duration, signature, then queries and views.)"},
    ],
    "quiz": [
        {"q": "Why normalise failure messages?", "options": ["Shorter logs", "Group identical problems with different numbers/MACs", "Encryption", "Faster tests"], "answer": 1, "why": "Signatures."},
        {"q": "History PPPPPPPPFF is most likely...", "options": ["Flaky", "NEW regression", "Broken", "Healthy"], "answer": 1, "why": "Steady, then failing."},
        {"q": "History PFPPFPFPPF is...", "options": ["NEW", "Flaky", "Broken", "Healthy"], "answer": 1, "why": "Many flips."},
        {"q": "Apply the timestamp rule before the number rule because...", "options": ["Speed", "Otherwise dates become <N>-<N>-<N>", "Alphabetical", "No reason"], "answer": 1, "why": "Specific before generic."},
        {"q": "Integer field in Influx line protocol:", "options": ["passed=20", "passed=20i", "passed:20", "passed='20'"], "answer": 1, "why": "Trailing i."},
    ],
    "cards": [
        {"front": "Failure signature", "back": "Message with times/MACs/IPs/numbers replaced by placeholders"},
        {"front": "Known issues", "back": "Regex on signature → ticket, category, owner"},
        {"front": "Classify by history", "back": "NEW (steady→fail), flaky (flips), broken (always fail), healthy"},
        {"front": "Flakiness score", "back": "`sum(a != b for a, b in zip(h, h[1:]))`"},
        {"front": "Dashboard feed", "back": "Influx line protocol / DB rows: suite, bench, fw, pass_rate"},
    ],
}
