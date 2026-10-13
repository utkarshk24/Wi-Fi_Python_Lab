"""Phase 9 content: modules 9.6-9.10 (security, packaging, docs, versioning, AI/reading code)."""

from net_support import needs

BUILD = needs("build hatchling") + " and runs the build tool in a subprocess"
DOCTEST = "runs doctest in a subprocess, which the in-browser runner can't do"
SUBPROC = "runs programs through subprocess, which the in-browser runner can't do"
YAML = needs("pyyaml")
EXEC_REQ = "builds a module that imports requests, which the in-browser runner doesn't include"

M_9_6 = {
    "id": "9.6",
    "title": "Security Basics",
    "hours": 1.5,
    "summary": "Everyday security for automation code: safe subprocess and shell handling, avoiding injection, safe deserialization (no pickle/yaml.load of untrusted data), verifying TLS, and scanning dependencies.",
    "concepts": [
        {
            "title": "Running commands safely",
            "local_only": SUBPROC,
            "concept": "Pass commands to `subprocess` as a **list**, not a string with `shell=True`: the list form hands arguments straight to the program, so a bench name or SSID containing spaces, `;` or `$(...)` can't start a second command. When you must build a shell string, quote every piece with `shlex.quote`. The same idea protects any command you assemble from device output or user input.",
            "why": "Automation glues together ssh, iperf3, iw and vendor tools, often with arguments that come from inventory files or device output. One AP named `; rm -rf results` is enough to ruin a run if commands are built as shell strings.",
            "syntax": "subprocess.run([\"ssh\", host, \"iw\", \"dev\", iface, \"link\"], timeout=10, check=True)\n# if a shell is unavoidable:\nsubprocess.run(shlex.quote(user_value), shell=True)",
            "code": """import shlex  ## Shell-safe quoting
import subprocess  ## Running programs

SSID = "Lab 6E; rm -rf results"  ## A hostile (or just awkward) value from inventory


def list_form(ssid):  ## The safe way: arguments as a list
    proc = subprocess.run(["printf", "%s\\n", f"connecting to {ssid}"], capture_output=True, text=True)  ## printf stands in for a real tool
    return proc.stdout.strip()  ## The ssid is a single argument, metacharacters and all


print(list_form(SSID))  ## The whole string is one argument; nothing is executed

shell_cmd = f"printf 'connecting to {SSID}'"  ## The dangerous way: a shell string
print("would run:", shell_cmd)  ## The ; starts a second command under a real shell
safe_cmd = f"printf 'connecting to %s\\n' {shlex.quote(SSID)}"  ## If a shell is unavoidable, quote the value
print("quoted arg:", shlex.quote(SSID))  ## Wrapped so the shell treats it as one token
print(subprocess.run(safe_cmd, shell=True, capture_output=True, text=True).stdout.strip())  ## Now safe even with shell=True

cmd = ["ssh", "admin@10.10.30.7", "iw", "dev", "wlan0", "link"]  ## A typical remote command, as a list
print("ssh argv:", cmd)  ## Each element is passed verbatim; no shell parsing of the SSID or host""",
            "under": "With a list, `subprocess` calls `execve` directly with those exact arguments; no shell is involved, so there is nothing to inject into. `shell=True` runs `(/bin/sh -c \"<string>\")`, which interprets `;`, `|`, `$()`, `&&`, globbing and quoting, which is exactly what you don't want around untrusted values. `shlex.quote` wraps a value in single quotes and escapes embedded quotes so the shell sees one token.",
            "gotchas": [
                {
                    "title": "shell=True with an interpolated value",
                    "local_only": SUBPROC,
                    "note": "Interpolating a value into a `shell=True` command lets that value run arbitrary commands. Here a crafted 'channel' would delete files on a real shell. Use the list form; the injected command becomes a (harmless, nonsensical) argument instead.",
                    "wrong": """import subprocess

channel = "36; echo PWNED"
out = subprocess.run(f"echo set channel {channel}", shell=True, capture_output=True, text=True).stdout
print(out.strip())""",
                    "fixed": """import subprocess

channel = "36; echo PWNED"
out = subprocess.run(["echo", "set", "channel", channel], capture_output=True, text=True).stdout
print(out.strip())""",
                },
            ],
            "best": "Default to the list form without `shell=True`, validate values you put into commands (a channel should be an int), use `shlex.quote` only when a shell is truly required, never build SQL/HTML/shell strings by concatenation, and set timeouts on every subprocess.",
        },
        {
            "title": "Deserialization, TLS and dependency scanning",
            "concept": "Three recurring footguns: **pickle** and **`yaml.load`** execute arbitrary code when loading untrusted data, so use `json` or `yaml.safe_load` for anything you didn't create; **TLS verification** must stay on (`verify=True`) for any real endpoint, with a proper CA bundle rather than `verify=False`; and **dependencies** carry known vulnerabilities, so `pip-audit` (or `safety`) in CI flags them. The example shows safe vs unsafe loading and a tiny vulnerability check against an advisory list.",
            "why": "A bench config or test-data file from a shared drive, a results blob from another tool, a cloud controller's API: each is untrusted input. And an automation box often has broad lab network access, so a compromised dependency or a man-in-the-middle on a 'convenient' `verify=False` call is a real risk.",
            "syntax": "yaml.safe_load(text)        # not yaml.load / not pickle.loads\nrequests.get(url, verify=True, timeout=5)\n# CI: pip-audit -r requirements.lock",
            "code": """import json  ## Safe structured data
import pickle  ## UNSAFE for untrusted input; shown to contrast


class Tripwire:  ## A class whose unpickling has a side effect
    def __reduce__(self):  ## pickle calls this to decide how to rebuild the object
        return (print, ("side effect during unpickling!",))  ## An attacker could run anything here


payload = pickle.dumps(Tripwire())  ## A malicious file would contain bytes like these
print("unpickling runs code:")  ## Demonstrate the danger
pickle.loads(payload)  ## Executes print(...) just by loading, no attribute access needed

config_text = '{"bench": "lab-07", "channel": 36}'  ## The same data as JSON
print("json is data-only:", json.loads(config_text))  ## json can only build basic types; no code runs

INSTALLED = {"requests": "2.31.0", "pyyaml": "6.0.1", "jinja2": "3.1.2", "urllib3": "2.0.3"}  ## From the lock file
ADVISORIES = [  ## A tiny stand-in for the pip-audit / OSV database
    ("jinja2", "<3.1.4", "CVE-2024-34064: xmlattr injection", "3.1.4"),  ## Fixed in 3.1.4
    ("urllib3", "<2.0.7", "CVE-2023-45803: request body leak on redirect", "2.0.7"),  ## Fixed in 2.0.7
]  ## End of advisories


def version_tuple(v):  ## "2.0.3" -> (2, 0, 3) for comparison
    return tuple(int(p) for p in v.split("."))  ## Simple, works for clean versions


for pkg, spec, desc, fixed in ADVISORIES:  ## Compare installed against each advisory
    bound = version_tuple(spec[1:])  ## The version in "<X.Y.Z"
    if pkg in INSTALLED and version_tuple(INSTALLED[pkg]) < bound:  ## Vulnerable range
        print(f"VULNERABLE {pkg} {INSTALLED[pkg]}: {desc} -> upgrade to {fixed}")  ## Actionable finding""",
            "under": "`pickle` is a serialization format that stores instructions for rebuilding objects, including calling arbitrary callables (`__reduce__`), so loading a pickle is equivalent to running code; the same is true of PyYAML's full loader. `requests` verifies TLS by default; `verify=False` disables certificate checking (and only silences the warning), which defeats the point of HTTPS. Real tools like `pip-audit` query the Python advisory database and understand full version specifiers.",
            "gotchas": [],
            "best": "Use `json` or `yaml.safe_load` for any data you didn't produce, never unpickle untrusted bytes, keep TLS verification on with a real CA bundle (install an internal CA properly instead of `verify=False`), pin dependencies in a lock file and run `pip-audit` in CI, and give automation accounts least privilege.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write `safe_ssh(host, *args)` that builds an ssh command as a list, rejecting any argument containing a shell metacharacter as defensive validation, and show it refuses a crafted channel.",
            "solution": "The list form is already safe; the validation is belt-and-braces and documents intent.",
            "solution_code": """BAD = set(";|&$`<>\\n")


def safe_ssh(host, *args):
    for a in args:
        if BAD & set(str(a)):
            raise ValueError(f"refusing suspicious argument: {a!r}")
    return ["ssh", host, *map(str, args)]


print(safe_ssh("admin@10.10.30.7", "iw", "dev", "wlan0", "link"))
try:
    safe_ssh("admin@10.10.30.7", "set", "channel", "36; rm -rf /")
except ValueError as e:
    print(e)""",
        },
        {
            "level": "Medium",
            "local_only": YAML,
            "prompt": "Load a bench config from YAML-like text with safe_load and reject it if it isn't a flat mapping of str to (str|int|bool), to catch unexpected structures (and anything full-load would have built).",
            "solution": "safe_load only builds basic types; add a schema check for the shape you expect.",
            "solution_code": """import yaml

TEXT = '''bench: lab-07
channel: 36
dfs: true
notes: "6 GHz capable"'''


def load_bench(text):
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("expected a mapping")
    for k, v in data.items():
        if not isinstance(k, str) or not isinstance(v, (str, int, bool)):
            raise ValueError(f"bad entry {k!r}: {type(v).__name__}")
    return data


print(load_bench(TEXT))
try:
    load_bench("benches:\\n  - lab-07\\n  - lab-08")
except ValueError as e:
    print(e)""",
        },
        {
            "level": "Hard",
            "prompt": "Parse requirements with pinned versions and compare against advisories expressed as `(package, '>=min,<fixed', id)`; report vulnerable packages and the version to upgrade to.",
            "solution": "Split the spec on commas, compare version tuples against each bound.",
            "solution_code": """def vt(v):
    return tuple(int(x) for x in v.split("."))


def vulnerable(installed, lo, hi):
    return vt(lo) <= vt(installed) < vt(hi)


REQS = {"requests": "2.31.0", "cryptography": "41.0.3", "jinja2": "3.1.2"}
ADVISORIES = [("cryptography", "41.0.0", "41.0.4", "EXAMPLE-0001 (illustrative advisory)"),
              ("jinja2", "3.0.0", "3.1.4", "CVE-2024-34064"),
              ("requests", "2.0.0", "2.31.0", "already fixed in installed")]
for pkg, lo, hi, advisory in ADVISORIES:
    if pkg in REQS and vulnerable(REQS[pkg], lo, hi):
        print(f"{pkg} {REQS[pkg]}: {advisory} -> upgrade to >= {hi}")""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Why avoid shell=True in subprocess?", "a": "It runs the command through a shell that interprets metacharacters, so any untrusted value (hostname, SSID, filename) can inject extra commands. The list form passes arguments directly to the program with no shell, eliminating that class of bug.", "follow": "When is a shell needed? (Pipes, redirection, globbing; then quote every value with shlex.quote.)"},
        {"level": "Intermediate", "q": "Why is pickle dangerous?", "a": "Unpickling can execute arbitrary code (via __reduce__), so loading a pickle from an untrusted source is remote code execution. Use json or yaml.safe_load for data; reserve pickle for trusted, same-version internal caches.", "follow": "Same issue with YAML? (Yes: yaml.load is unsafe; use safe_load.)"},
        {"level": "Intermediate", "q": "How do you handle TLS for internal lab services with private CAs?", "a": "Install the internal CA into the trust store (or pass verify=/path/to/ca-bundle.pem), never verify=False, which disables all verification and enables MITM. Automate CA distribution to bench images.", "follow": "What does verify=False actually do? (Skips certificate validation; the connection is still encrypted but unauthenticated.)"},
        {"level": "Advanced", "q": "How do you manage dependency security in a test framework?", "a": "Pin everything in a hash-locked file, run pip-audit/safety in CI and fail on known-vulnerable packages, update regularly (Dependabot/Renovate), minimise the dependency surface, and build images from pinned bases scanned by the registry.", "follow": "Why hashes in the lock file? (To detect tampered or substituted packages.)"},
    ],
    "quiz": [
        {"q": "Safest way to run a command with untrusted args:", "options": ["shell=True with quotes", "A list, shell=False", "os.system", "eval"], "answer": 1, "why": "No shell to inject into."},
        {"q": "Load untrusted config with...", "options": ["pickle.loads", "yaml.load", "yaml.safe_load / json.loads", "eval"], "answer": 2, "why": "Data-only parsers."},
        {"q": "`requests.get(url, verify=False)`...", "options": ["Is more secure", "Disables TLS certificate checks", "Uses a proxy", "Adds a timeout"], "answer": 1, "why": "Allows MITM."},
        {"q": "`shlex.quote('a; b')` returns...", "options": ["a; b", "'a; b'", "a b", "Error"], "answer": 1, "why": "One safe shell token."},
        {"q": "Find vulnerable dependencies in CI:", "options": ["ruff", "pip-audit", "mypy", "black"], "answer": 1, "why": "Advisory database check."},
    ],
    "cards": [
        {"front": "Safe subprocess", "back": "`subprocess.run([prog, arg1, arg2], timeout=..., check=True)` (no shell=True)"},
        {"front": "Shell quoting", "back": "`shlex.quote(value)` when a shell is unavoidable"},
        {"front": "Safe loading", "back": "`json.loads` / `yaml.safe_load`; never pickle/yaml.load untrusted data"},
        {"front": "TLS", "back": "Keep `verify=True`; install the internal CA, never verify=False"},
        {"front": "Dependency scan", "back": "`pip-audit -r requirements.lock` in CI; hash-pinned lock file"},
    ],
}


M_9_7 = {
    "id": "9.7",
    "title": "Packaging & Private Package Indexes",
    "hours": 1.5,
    "summary": "Turn the framework into an installable package: pyproject.toml with a build backend, a src layout, entry-point commands, dependency pinning, building wheels, and publishing to a private index.",
    "concepts": [
        {
            "title": "pyproject.toml, src layout and entry points",
            "runner": "none",
            "lang": "TOML",
            "filename": "pyproject.toml",
            "concept": "A modern Python package is described entirely by `pyproject.toml`: a `[build-system]` naming the build backend (hatchling, setuptools, flit), a `[project]` table with metadata, dependencies and `requires-python`, optional-dependency groups for extras (`[project.optional-dependencies]`), and `[project.scripts]` that become command-line tools on install. A **src layout** (`src/wifilab/`) stops the un-built package from shadowing the installed one during tests.",
            "why": "`pip install wifilab` on every bench, a pinned version per firmware train, and a `wifilab` command for engineers beats copying a folder and setting PYTHONPATH. It also makes the framework a dependency other repos can declare.",
            "syntax": "[build-system]\nrequires = [\"hatchling\"]\nbuild-backend = \"hatchling.build\"\n[project]\nname = \"wifilab\"\n[project.scripts]\nwifilab = \"wifilab.cli:main\"",
            "code": """[build-system]  ## How to build the package
requires = ["hatchling>=1.24"]  ## Build-time dependency (installed in an isolated env)
build-backend = "hatchling.build"  ## The backend pip/build calls to produce the wheel

[project]  ## Package metadata (PEP 621)
name = "wifilab"  ## Import and install name
version = "1.4.1"  ## Single source of truth for the version
description = "Wi-Fi test automation framework"  ## One line, shown on the index
requires-python = ">=3.11"  ## Refuses to install on older Python
readme = "README.md"  ## Long description for the index page
license = "MIT"  ## SPDX identifier
authors = [{ name = "WLAN Test Team" }]  ## Shown on the index
dependencies = [  ## Runtime dependencies with lower bounds
    "requests>=2.31",  ## HTTP client
    "paramiko>=3.4",  ## SSH
    "pydantic>=2.6",  ## Config validation
]  ## End of dependencies

[project.optional-dependencies]  ## Extras: pip install wifilab[dev]
dev = ["pytest>=8", "ruff", "mypy"]  ## Development tools
rf = ["scapy>=2.5", "pyshark>=0.6"]  ## Only needed on benches that capture packets

[project.scripts]  ## Console commands created on install
wifilab = "wifilab.cli:main"  ## `wifilab` runs wifilab/cli.py's main()
wifilab-report = "wifilab.report:main"  ## A second command

[tool.hatch.build.targets.wheel]  ## Backend-specific: where the code lives
packages = ["src/wifilab"]  ## src layout: the package is under src/""",
            "under": "On `pip install`, the build backend reads this file, produces a wheel, and pip installs it; the `[project.scripts]` entries become small executables on PATH that import the module and call the named function (the same `entry_points` mechanism pytest plugins use). With a src layout, `import wifilab` during tests resolves to the installed package, not the working copy, so tests exercise what users actually get. `requires-python` and dependency specifiers are enforced by pip at install time.",
            "gotchas": [],
            "best": "One `pyproject.toml`, a src layout, a single version source, lower-bound runtime deps plus a hash-pinned lock file for reproducible installs, extras for optional features, entry-point commands instead of loose scripts, and a README that renders on the index.",
        },
        {
            "title": "Building and publishing to a private index",
            "local_only": BUILD,
            "concept": "`python -m build` produces two artifacts in `dist/`: a **wheel** (`.whl`, the installable built form) and an **sdist** (`.tar.gz`, the source). `twine upload --repository-url <private index>` publishes them to an internal index (devpi, Artifactory, a cloud artifact registry), and benches install with `pip install wifilab --index-url <private index>`. The example builds a real package in a temp dir and inspects the wheel.",
            "why": "A private index is how a team ships the framework internally with versioning and access control, without putting Wi-Fi test code on public PyPI. CI builds and uploads on every tagged release.",
            "syntax": "python -m build\ntwine upload --repository-url https://pkgs.lab/simple dist/*\npip install wifilab==1.4.1 --index-url https://pkgs.lab/simple",
            "code": """import subprocess  ## Run the build tool
import sys  ## Same interpreter
import tempfile  ## Scratch project
import zipfile  ## A wheel is a zip
from pathlib import Path  ## Paths

project = Path(tempfile.mkdtemp())  ## A throwaway package to build
(project / "src" / "wifilab").mkdir(parents=True)  ## src layout
(project / "src" / "wifilab" / "__init__.py").write_text('__version__ = "1.4.1"\\n')  ## Package marker with a version
(project / "src" / "wifilab" / "cli.py").write_text("def main():\\n    print('wifilab 1.4.1')\\n")  ## The entry point
(project / "README.md").write_text("# wifilab\\n")  ## Long description
(project / "pyproject.toml").write_text(\"\"\"[build-system]
requires = ["hatchling>=1.24"]
build-backend = "hatchling.build"
[project]
name = "wifilab"
version = "1.4.1"
requires-python = ">=3.11"
dependencies = ["requests>=2.31"]
[project.scripts]
wifilab = "wifilab.cli:main"
[tool.hatch.build.targets.wheel]
packages = ["src/wifilab"]
\"\"\")  ## The metadata from the previous concept

result = subprocess.run([sys.executable, "-m", "build", "--wheel", "--no-isolation", str(project)], capture_output=True, text=True)  ## Build just the wheel
print("built:", "Successfully built" in result.stdout)  ## Did it work?

wheel = next((project / "dist").glob("*.whl"))  ## The produced wheel
print("artifact:", wheel.name)  ## wifilab-1.4.1-py3-none-any.whl: name-version-pytag-abi-platform
with zipfile.ZipFile(wheel) as zf:  ## A wheel is just a zip archive
    names = zf.namelist()  ## What's inside
    print("modules:", sorted(n for n in names if n.endswith(".py")))  ## The packaged code
    metadata = zf.read("wifilab-1.4.1.dist-info/METADATA").decode()  ## The metadata pip reads
for line in metadata.splitlines():  ## Show the key metadata
    if line.startswith(("Name:", "Version:", "Requires-Python:", "Requires-Dist:")):  ## The fields pip enforces
        print(line)  ## Name, version, python bound, dependencies
print("# twine upload --repository-url https://pkgs.lab/simple dist/*  (then pip install wifilab --index-url ...)")  ## How it reaches benches""",
            "under": "A wheel filename encodes compatibility: `wifilab-1.4.1-py3-none-any.whl` means pure Python 3, any ABI, any platform, so it installs everywhere. The `.dist-info/METADATA` file holds the same `[project]` fields pip uses to resolve dependencies and check `requires-python`. `--no-isolation` here reuses the already-installed backend; a normal `python -m build` creates an isolated environment and downloads the backend, which the workspace's network would block.",
            "gotchas": [],
            "best": "Build in CI on tagged releases, upload wheel and sdist to the private index with credentials from the secret store, install from the private index on benches with a pinned version, keep the version in one place (or derive it from the git tag), and test the built wheel (install it in a clean env) before publishing.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Parse a wheel filename into its components (distribution, version, python tag, abi tag, platform tag).",
            "solution": "Strip `.whl` and split on `-`; the last three fields are the compatibility tags.",
            "solution_code": """def parse_wheel(name):
    dist, version, py, abi, platform = name.removesuffix(".whl").split("-")
    return {"dist": dist, "version": version, "python": py, "abi": abi, "platform": platform}


print(parse_wheel("wifilab-1.4.1-py3-none-any.whl"))
print(parse_wheel("numpy-2.1.0-cp312-cp312-manylinux_2_17_x86_64.whl"))""",
        },
        {
            "level": "Medium",
            "prompt": "Check whether an installed set of packages satisfies a list of dependency specifiers like `requests>=2.31` and `pydantic>=2.6,<3`.",
            "solution": "Parse each specifier into (name, bounds); compare version tuples. (packaging.specifiers does this properly in real code.)",
            "solution_code": """import re


def vt(v):
    return tuple(int(x) for x in re.findall(r"\\d+", v))


def satisfies(installed, spec):
    name = re.match(r"[A-Za-z0-9_.-]+", spec)[0]
    have = installed.get(name)
    if have is None:
        return False
    for op, ver in re.findall(r"(>=|<=|==|<|>)\\s*([0-9.]+)", spec):
        ok = {">=": vt(have) >= vt(ver), "<=": vt(have) <= vt(ver), "==": vt(have) == vt(ver),
              "<": vt(have) < vt(ver), ">": vt(have) > vt(ver)}[op]
        if not ok:
            return False
    return True


INSTALLED = {"requests": "2.31.0", "pydantic": "2.6.4"}
for spec in ["requests>=2.31", "pydantic>=2.6,<3", "paramiko>=3.4"]:
    print(spec, "->", satisfies(INSTALLED, spec))""",
        },
        {
            "level": "Hard",
            "local_only": BUILD,
            "prompt": "Build a package that declares a `wifilab` console script, install the wheel into a fresh venv, and prove the command runs.",
            "solution": "Build the wheel, create a venv, pip install the wheel into it, then run the installed console script.",
            "solution_code": """import subprocess
import sys
import tempfile
import venv
from pathlib import Path

proj = Path(tempfile.mkdtemp())
(proj / "src" / "wifilab").mkdir(parents=True)
(proj / "src" / "wifilab" / "__init__.py").write_text("")
(proj / "src" / "wifilab" / "cli.py").write_text("def main():\\n    print('wifilab ready')\\n")
(proj / "pyproject.toml").write_text('''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
[project]
name = "wifilab"
version = "0.1.0"
[project.scripts]
wifilab = "wifilab.cli:main"
[tool.hatch.build.targets.wheel]
packages = ["src/wifilab"]
''')
subprocess.run([sys.executable, "-m", "build", "--wheel", "--no-isolation", str(proj)], capture_output=True, check=True)
wheel = next((proj / "dist").glob("*.whl"))
env = proj / "venv"
venv.create(env, with_pip=True)
pip = env / "bin" / "pip"
subprocess.run([pip, "install", "-q", str(wheel)], check=True)
print(subprocess.run([env / "bin" / "wifilab"], capture_output=True, text=True).stdout.strip())""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What does pyproject.toml replace?", "a": "setup.py/setup.cfg for metadata and build configuration; it declares the build backend ([build-system]) and project metadata, dependencies and entry points ([project]) in a standard, tool-agnostic way.", "follow": "What are entry-point scripts? ([project.scripts] that become CLI commands on install.)"},
        {"level": "Intermediate", "q": "Why a src layout?", "a": "It prevents the working-directory package from shadowing the installed one, so tests run against the installed package and import errors from missing packaging are caught early.", "follow": "Wheel vs sdist? (Wheel is the built, installable artifact; sdist is the source fallback.)"},
        {"level": "Intermediate", "q": "How do you distribute an internal framework?", "a": "Build wheels in CI on tagged releases, upload to a private index (devpi, Artifactory, cloud artifact registry) with credentials from a secret store, and install on benches with a pinned version from that index.", "follow": "How do you ensure reproducible installs? (A hash-pinned lock file plus --require-hashes.)"},
    ],
    "quiz": [
        {"q": "Declares the build backend:", "options": ["[project]", "[build-system]", "[tool.pytest]", "[metadata]"], "answer": 1, "why": "requires + build-backend."},
        {"q": "Create a CLI command on install:", "options": ["[project.scripts]", "[console]", "bin/", "setup.py scripts"], "answer": 0, "why": "Entry points."},
        {"q": "`pip install wifilab[rf]` installs...", "options": ["A file named rf", "The rf optional-dependency group", "Nothing extra", "A plugin"], "answer": 1, "why": "Extras."},
        {"q": "The installable built artifact is the...", "options": ["sdist", "wheel", "egg", "tarball"], "answer": 1, "why": ".whl."},
        {"q": "`py3-none-any` in a wheel name means...", "options": ["Python 3, any ABI, any platform", "Python 3 only on Linux", "No Python", "CPython 3.9"], "answer": 0, "why": "Pure-Python, universal."},
    ],
    "cards": [
        {"front": "Build backend", "back": "`[build-system] requires=['hatchling'] build-backend='hatchling.build'`"},
        {"front": "CLI command", "back": "`[project.scripts] wifilab = 'wifilab.cli:main'`"},
        {"front": "Build artifacts", "back": "`python -m build` → dist/*.whl and *.tar.gz"},
        {"front": "Publish", "back": "`twine upload --repository-url <private index> dist/*`"},
        {"front": "Install pinned", "back": "`pip install wifilab==1.4.1 --index-url <private index>`"},
    ],
}


M_9_8 = {
    "id": "9.8",
    "title": "Documentation",
    "hours": 1.5,
    "summary": "Docstrings that help, type hints as documentation, executable examples with doctest, and the shape of good README and runbook docs for a test framework.",
    "concepts": [
        {
            "title": "Docstrings and executable examples with doctest",
            "local_only": DOCTEST,
            "files": {"wifi_calc.py": '''"""Wi-Fi channel and throughput helpers."""


def channel_to_freq(channel: int, band: str = "5G") -> int:
    """Return the center frequency in MHz for a channel.

    >>> channel_to_freq(36)
    5180
    >>> channel_to_freq(1, band="2G")
    2412
    >>> channel_to_freq(37, band="6G")
    6135
    >>> channel_to_freq(200)
    Traceback (most recent call last):
        ...
    ValueError: channel 200 is not valid for 5G
    """
    if band == "2G":
        return 2407 + channel * 5 if channel < 14 else 2484
    if band == "5G":
        if not 36 <= channel <= 165:
            raise ValueError(f"channel {channel} is not valid for 5G")
        return 5000 + channel * 5
    if band == "6G":
        return 5950 + channel * 5
    raise ValueError(f"unknown band {band}")


def meets_kpi(mbps: float, kpi: float) -> bool:
    """True if a measurement meets its KPI.

    >>> meets_kpi(912.4, 850)
    True
    >>> meets_kpi(135.9, 150)
    False
    """
    return mbps >= kpi
'''},
            "concept": "A good docstring says what a function does, its parameters and return, and what it raises, not how it works. **Type hints** document the types so the docstring doesn't repeat them. Examples written in the docstring as interactive-prompt sessions are run by **doctest** (`python -m doctest -v file.py` or a pytest option), so they can never drift from the code: if the behaviour changes, the example fails.",
            "why": "Examples are the first thing people read and the first thing that goes stale. doctest keeps them correct, and running them is a free extra test of the simplest cases, including the error cases.",
            "syntax": "def f(x: int) -> int:\n    \"\"\"...\n    >>> f(2)\n    4\n    \"\"\"\n\npython -m doctest -v file.py\npytest --doctest-modules",
            "code": """import doctest  ## Standard-library example runner

import wifi_calc  ## The module with documented functions (see supporting files)

results = doctest.testmod(wifi_calc, verbose=False)  ## Run every >>> example in the module
print(f"doctest: {results.attempted} examples, {results.failed} failed")  ## All should pass

print(channel := wifi_calc.channel_to_freq.__doc__.splitlines()[0])  ## The one-line summary a reader sees first
print("6G ch37:", wifi_calc.channel_to_freq(37, band="6G"))  ## Using the documented function

broken = (  ## A docstring example that disagrees with the code (1.2, not 1.1); built up to avoid nested triple quotes
    "def add_margin(mbps):\\n"  ## Function header
    '    \"\"\"Add a 10% margin.\\n\\n'
    "    >>> add_margin(100)\\n"
    "    110.0\\n"
    '    \"\"\"\\n'
    "    return mbps * 1.2\\n"  ## The code: 20%, not 10%
)  ## The example says 110.0 but the code multiplies by 1.2
import types  ## Build a module from the broken source to test it
mod = types.ModuleType("broken")  ## Fresh module
exec(broken, mod.__dict__)  ## Define add_margin in it
r = doctest.testmod(mod, verbose=False)  ## Run its doctest
print(f"broken module: {r.failed} failed of {r.attempted} (the example and code disagree)")  ## Caught the drift""",
            "under": "doctest compares the text after each `>>>` block against the printed output exactly (whitespace matters; `...` continues a statement, and a traceback example matches on the exception line with `...` for the frames). `testmod` returns a `TestResults(attempted, failed)` namedtuple. `pytest --doctest-modules` collects these as normal tests, so documentation examples run in CI alongside everything else.",
            "gotchas": [],
            "best": "Write a one-line summary first, document parameters/returns/raises (or rely on type hints plus a short note), include a runnable example for anything non-obvious, keep examples small and deterministic, and run them in CI with `--doctest-modules` so they can't rot.",
        },
        {
            "title": "READMEs, runbooks and API docs",
            "runner": "none",
            "lang": "Markdown",
            "filename": "README.md",
            "concept": "Different docs answer different questions. A **README** gets someone productive fast: what it is, install, a minimal working example, where to go next. A **runbook** is for operators: exact steps to run the nightly suite, reserve a bench, and what to do when common failures happen. **API docs** (generated from docstrings by Sphinx or MkDocs) are reference material. The example is a README for the framework; the under-the-hood note covers the others.",
            "why": "A test framework is used by people who didn't write it, often at 2 a.m. when a nightly run broke. Docs that are task-oriented (how do I...) and kept next to the code are what make a framework adoptable instead of a bus-factor-of-one.",
            "syntax": "# Project\nWhat it is.\n## Install\n## Quickstart\n## Running the suite\n## Troubleshooting",
            "code": """# wifilab  ## Project name as the H1

Wi-Fi test automation for enterprise APs: rate-vs-range, roaming,  ## What it is...
interop and power, on real benches or simulators in CI.  ## ...and where it runs

## Install  ## First thing a reader needs

```  ## Code fence: shell commands
pip install wifilab --index-url https://pkgs.lab/simple  ## From the private index (9.7)
pip install "wifilab[rf]"  ## With the packet-capture extras
```  ## End of fence

## Quickstart  ## A minimal example that actually works

```python  ## Code fence with syntax highlighting
from wifilab import Bench  ## The facade (9.3)
bench = Bench.from_config("benches/lab-07.yaml")  ## Instruments built from bench config
result = bench.rate_vs_range(band="6G", start=0, stop=60, step=6)  ## One high-level call
result.to_csv("rvr.csv")  ## Raw data first
print(result.verdict(kpi=2000))  ## PASS / FAIL
```  ## End of fence

## Running the nightly suite  ## The most common task

```  ## Code fence
wifilab run --suite rvr --bench lab-07 --firmware 7.4.2-b003  ## The entry-point command from pyproject.toml
```  ## End of fence

Results go to `results/` as JUnit XML and an Allure report.  ## Where output lands

## Troubleshooting  ## Short list; the runbook has the long version

- `BenchBusyError`: another job holds the bench; see `docs/runbook.md#bench-locks`.  ## The most common error, with where to read more
- No 6 GHz radio: check the bench's `caps` in its config file.  ## Second most common, with the fix

## Links  ## Where to go next

- Full API reference: generated from docstrings (`mkdocs serve`)  ## Reference material, one source with doctest
- Runbook for operators: `docs/runbook.md`  ## Procedures and failure handling
- Contributing and dev setup: `CONTRIBUTING.md`  ## For people changing the framework""",
            "under": "This is written as Markdown; a documentation site generator (MkDocs with the mkdocstrings plugin, or Sphinx with autodoc) turns the same docstrings used by doctest into an API reference, so documentation has one source. A runbook differs from a README by being procedural and failure-oriented (numbered steps, exact commands, 'if X then Y'), which is the Phase 8/operations style applied to running the suite.",
            "gotchas": [],
            "best": "Keep docs in the repo next to the code, lead the README with install + a working example, write runbooks as numbered steps with real commands and failure handling, generate API reference from docstrings so it stays current, and treat broken examples (doctest/CI) as failures.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "local_only": DOCTEST,
            "prompt": "Write a function with a doctest that covers a normal case and an error case, and run doctest on it.",
            "solution": "A traceback example matches the exception line; run with doctest.run_docstring_examples or testmod.",
            "solution_code": """import doctest


def width_for(band):
    '''Max channel width (MHz) for a band.

    >>> width_for("6G")
    320
    >>> width_for("2G")
    40
    >>> width_for("7G")
    Traceback (most recent call last):
        ...
    KeyError: '7G'
    '''
    return {"2G": 40, "5G": 160, "6G": 320}[band]


runner = doctest.DocTestRunner()
for test in doctest.DocTestFinder().find(width_for, globs={"width_for": width_for}):
    runner.run(test)
print(runner.summarize(verbose=False))""",
        },
        {
            "level": "Medium",
            "prompt": "Generate a simple Markdown API table from a module's functions using introspection: name, signature and the first docstring line.",
            "solution": "inspect.signature and inspect.getdoc give the pieces; format as a Markdown table.",
            "solution_code": """import inspect


def band_freq(channel: int, band: str = "5G") -> int:
    \"\"\"Center frequency in MHz.\"\"\"
    return 5000 + channel * 5


def meets_kpi(mbps: float, kpi: float) -> bool:
    \"\"\"Whether a measurement meets its KPI.\"\"\"
    return mbps >= kpi


print("| Function | Signature | Summary |")
print("|---|---|---|")
for fn in (band_freq, meets_kpi):
    summary = (inspect.getdoc(fn) or "").splitlines()[0]
    print(f"| `{fn.__name__}` | `{fn.__name__}{inspect.signature(fn)}` | {summary} |")""",
        },
        {
            "level": "Hard",
            "prompt": "Write a doc-coverage check: given a module source, report public functions (not starting with _) that have no docstring, using ast.",
            "solution": "ast.get_docstring returns None when there's no docstring; filter public FunctionDefs.",
            "solution_code": """import ast

SRC = '''
def channel_to_freq(ch, band="5G"):
    \"\"\"Documented.\"\"\"
    return 5000 + ch * 5

def _helper(x):
    return x

def meets_kpi(mbps, kpi):
    return mbps >= kpi
'''
tree = ast.parse(SRC)
missing = [n.name for n in tree.body
           if isinstance(n, ast.FunctionDef) and not n.name.startswith("_") and ast.get_docstring(n) is None]
print("public functions without docstrings:", missing)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What makes a good docstring?", "a": "A one-line summary of what the function does, then parameters, return value and exceptions raised; it describes behaviour and contract, not implementation, and type hints carry the types. A runnable example helps for anything non-obvious.", "follow": "What's doctest? (Runs the examples in docstrings so they stay correct.)"},
        {"level": "Intermediate", "q": "How do you keep documentation examples from going stale?", "a": "Write them as doctests and run them in CI (pytest --doctest-modules), and generate API reference from the same docstrings (mkdocstrings/Sphinx autodoc) so there's one source of truth.", "follow": "Why run doctests in CI? (A behaviour change breaks the example, forcing an update.)"},
        {"level": "Intermediate", "q": "README vs runbook vs API reference?", "a": "README: get started fast (what, install, minimal example). Runbook: operator procedures and failure handling. API reference: generated per-function detail. Each answers a different question for a different reader.", "follow": "Where do runbooks matter most? (Operating nightly suites and incident response.)"},
    ],
    "quiz": [
        {"q": "doctest compares output...", "options": ["Approximately", "Exactly (whitespace matters)", "By type", "Ignoring order"], "answer": 1, "why": "Textual match."},
        {"q": "Run module docstrings as tests in pytest:", "options": ["--doctest-modules", "--docs", "--examples", "-k doctest"], "answer": 0, "why": "Collects >>> examples."},
        {"q": "Type hints in docstrings should be...", "options": ["Repeated in prose", "Carried by annotations instead", "Omitted entirely", "In comments"], "answer": 1, "why": "Avoid duplication/drift."},
        {"q": "A README should lead with...", "options": ["Architecture", "Install + a working example", "License", "Changelog"], "answer": 1, "why": "Get productive fast."},
        {"q": "`ast.get_docstring(node)` returns None when...", "options": ["Always", "There is no docstring", "The function is private", "It's a class"], "answer": 1, "why": "Doc-coverage check."},
    ],
    "cards": [
        {"front": "Docstring shape", "back": "Summary line; args; returns; raises (types via hints)"},
        {"front": "Executable example", "back": "`>>> f(2)` then expected output; run with doctest"},
        {"front": "Doctests in CI", "back": "`pytest --doctest-modules`"},
        {"front": "README order", "back": "What · Install · Quickstart · Running · Troubleshooting · Links"},
        {"front": "API docs from docstrings", "back": "MkDocs + mkdocstrings, or Sphinx autodoc"},
    ],
}


M_9_9 = {
    "id": "9.9",
    "title": "Versioning & Changelogs",
    "hours": 0.5,
    "summary": "Semantic versioning for a framework, Conventional Commits that drive the next version, and a Keep a Changelog file people actually read.",
    "concepts": [
        {
            "title": "SemVer, Conventional Commits and the changelog",
            "concept": "**Semantic Versioning** (MAJOR.MINOR.PATCH) encodes compatibility: bump PATCH for backward-compatible fixes, MINOR for backward-compatible features, MAJOR for breaking changes. **Conventional Commits** (`feat:`, `fix:`, `refactor:`, a `!` or `BREAKING CHANGE:` for incompatibilities) make the required bump computable from history, and let tools generate the **changelog** (grouped by type, newest first). The code derives the next version and a changelog section from a list of commits.",
            "why": "Benches pin the framework per firmware train, so 'is this upgrade safe?' must be answerable from the version. Automating the bump and changelog from commit messages removes the error-prone manual step and keeps release notes honest.",
            "syntax": "fix: ...      -> PATCH\nfeat: ...     -> MINOR\nfeat!: ...    -> MAJOR (or 'BREAKING CHANGE:' in the body)",
            "code": """import re  ## Parse commit subjects

COMMITS = [  ## git log --format=%s%n%b since the last tag, newest first
    ("feat(rvr): add 6 GHz 320 MHz sweep support", ""),  ## New feature -> MINOR
    ("fix(attenuator): snap set point to 0.25 dB grid", ""),  ## Fix -> PATCH
    ("refactor(core): extract Verdict dataclass", ""),  ## No version impact
    ("feat(api)!: rename Bench.run to Bench.run_suite", "BREAKING CHANGE: Bench.run is gone"),  ## Breaking -> MAJOR
    ("docs: expand roaming runbook", ""),  ## No version impact
    ("chore: bump ruff", ""),  ## No version impact
]  ## End of commits
CURRENT = (1, 4, 1)  ## Last released version


def classify(subject, body):  ## One commit -> "major" | "minor" | "patch" | None
    type_, bang = re.match(r"(\\w+)(?:\\([^)]*\\))?(!)?:", subject).group(1, 2) if ":" in subject else ("", "")  ## feat, fix, ...
    if bang or "BREAKING CHANGE" in body:  ## ! or a breaking-change footer
        return "major"  ## Incompatible
    if type_ == "feat":  ## New feature
        return "minor"  ## Backward-compatible addition
    if type_ == "fix":  ## Bug fix
        return "patch"  ## Backward-compatible fix
    return None  ## docs/refactor/chore/test: no release needed


bumps = [classify(s, b) for s, b in COMMITS]  ## Impact of each commit
level = "major" if "major" in bumps else "minor" if "minor" in bumps else "patch" if "patch" in bumps else None  ## Highest wins
major, minor, patch = CURRENT  ## Unpack
nxt = {"major": (major + 1, 0, 0), "minor": (major, minor + 1, 0), "patch": (major, minor, patch + 1), None: CURRENT}[level]  ## Apply the rule
print(f"{'.'.join(map(str, CURRENT))} -> {'.'.join(map(str, nxt))}  ({level or 'no release'})")  ## The computed next version

GROUPS = {"feat": "Added", "fix": "Fixed"}  ## Conventional type -> Keep a Changelog heading
sections = {}  ## heading -> list of lines
for subject, body in COMMITS:  ## Build the changelog
    m = re.match(r"(\\w+)(?:\\(([^)]*)\\))?(!)?:\\s*(.*)", subject)  ## type, scope, !, description
    heading = "Changed" if (m.group(3) or "BREAKING CHANGE" in body) else GROUPS.get(m.group(1))  ## Where it goes
    if heading:  ## Skip docs/chore/refactor
        scope = f"**{m.group(2)}**: " if m.group(2) else ""  ## Show the scope in bold
        sections.setdefault(heading, []).append(f"- {scope}{m.group(4)}")  ## One bullet

print(f"\\n## [{'.'.join(map(str, nxt))}] - 2026-10-13")  ## Changelog header for the release
for heading in ("Added", "Changed", "Fixed"):  ## Fixed order, most important first
    if heading in sections:  ## Only non-empty sections
        print(f"### {heading}")  ## Subsection
        print("\\n".join(sections[heading]))  ## Its bullets""",
            "under": "The highest-impact commit sets the release level (one breaking change forces a MAJOR bump regardless of how many fixes there are). Below version 1.0.0 the rules are often relaxed (breaking changes bump MINOR), which is why frameworks reach 1.0.0 deliberately. Tools like `python-semantic-release`, `commitizen` and `release-please` implement exactly this, plus tagging and publishing.",
            "gotchas": [],
            "best": "Adopt Conventional Commits, derive the version and changelog automatically in CI, keep a human-readable CHANGELOG.md (Keep a Changelog format: Added/Changed/Deprecated/Removed/Fixed/Security, newest first), tag releases, and call out breaking changes prominently with a migration note.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Compare two SemVer strings and report whether upgrading from a to b is a patch, minor, major, downgrade or same.",
            "solution": "Compare tuples field by field.",
            "solution_code": """def classify_upgrade(a, b):
    ta, tb = tuple(map(int, a.split("."))), tuple(map(int, b.split(".")))
    if tb < ta:
        return "downgrade"
    if tb == ta:
        return "same"
    if tb[0] != ta[0]:
        return "major"
    if tb[1] != ta[1]:
        return "minor"
    return "patch"


for a, b in [("1.4.1", "1.4.2"), ("1.4.1", "1.5.0"), ("1.4.1", "2.0.0"), ("1.4.1", "1.4.1"), ("2.0.0", "1.9.9")]:
    print(a, "->", b, ":", classify_upgrade(a, b))""",
        },
        {
            "level": "Medium",
            "prompt": "Given Conventional Commit subjects, count commits by type and decide the next version from 2.3.4.",
            "solution": "Tally types; apply the highest bump.",
            "solution_code": """import re
from collections import Counter

commits = ["fix: handle missing radiotap", "feat: add MLO tests", "fix: retry flaky roam",
           "docs: update readme", "feat: parse wpa_cli status"]
counts = Counter(re.match(r"(\\w+)", c)[1] for c in commits)
level = "minor" if counts["feat"] else "patch" if counts["fix"] else None
major, minor, patch = 2, 3, 4
nxt = {"minor": (major, minor + 1, 0), "patch": (major, minor, patch + 1), None: (major, minor, patch)}[level]
print(dict(counts), "->", ".".join(map(str, nxt)))""",
        },
        {
            "level": "Hard",
            "prompt": "Parse a Keep a Changelog file and extract the list of versions with their dates and the count of entries per section.",
            "solution": "Regex the `## [x.y.z] - date` headers and `### Section` subheaders, counting `- ` bullets between them.",
            "solution_code": """import re

CHANGELOG = '''# Changelog

## [1.5.0] - 2026-10-13
### Added
- 6 GHz 320 MHz sweep
- MLO link-switch test
### Fixed
- attenuator grid snapping

## [1.4.1] - 2026-09-20
### Fixed
- radiotap signal parsing
'''
version = None
out = {}
for line in CHANGELOG.splitlines():
    if m := re.match(r"## \\[([\\d.]+)\\] - (\\S+)", line):
        version = m[1]
        out[version] = {"date": m[2], "sections": {}}
    elif m := re.match(r"### (\\w+)", line):
        section = m[1]
        out[version]["sections"][section] = 0
    elif line.startswith("- ") and version:
        out[version]["sections"][section] += 1
for v, info in out.items():
    print(v, info)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What does each part of SemVer mean?", "a": "MAJOR: incompatible API changes. MINOR: backward-compatible new features. PATCH: backward-compatible bug fixes. Pre-1.0.0, anything may change. Consumers pin ranges based on this contract.", "follow": "How do you signal a breaking change in a commit? (feat!: or a BREAKING CHANGE: footer.)"},
        {"level": "Intermediate", "q": "How can versioning be automated?", "a": "Conventional Commits make the bump computable: tools scan commits since the last tag, pick the highest impact (fix→patch, feat→minor, breaking→major), bump the version, generate the changelog, tag and publish, all in CI.", "follow": "What format for the changelog? (Keep a Changelog: grouped sections, newest first, human-readable.)"},
    ],
    "quiz": [
        {"q": "A backward-compatible new feature bumps...", "options": ["MAJOR", "MINOR", "PATCH", "Nothing"], "answer": 1, "why": "feat → MINOR."},
        {"q": "`feat!:` or 'BREAKING CHANGE:' means...", "options": ["PATCH", "MINOR", "MAJOR", "No release"], "answer": 2, "why": "Incompatible."},
        {"q": "`fix:` commits bump...", "options": ["MAJOR", "MINOR", "PATCH", "Nothing"], "answer": 2, "why": "Backward-compatible fix."},
        {"q": "`docs:`/`chore:` commits...", "options": ["Bump PATCH", "Bump MINOR", "Trigger no release", "Bump MAJOR"], "answer": 2, "why": "No version impact."},
        {"q": "Keep a Changelog orders versions...", "options": ["Oldest first", "Newest first", "Alphabetically", "By size"], "answer": 1, "why": "Most recent at the top."},
    ],
    "cards": [
        {"front": "SemVer", "back": "MAJOR.MINOR.PATCH = breaking / feature / fix"},
        {"front": "Conventional Commits", "back": "`feat:`→minor, `fix:`→patch, `feat!:`/BREAKING→major"},
        {"front": "Next version", "back": "Highest-impact commit since the last tag decides the bump"},
        {"front": "Changelog format", "back": "Keep a Changelog: Added/Changed/Deprecated/Removed/Fixed/Security, newest first"},
        {"front": "Automation", "back": "commitizen / semantic-release / release-please in CI"},
    ],
}


M_9_10 = {
    "id": "9.10",
    "title": "AI Assistants & Reading Others' Code",
    "hours": 1.5,
    "summary": "Use AI assistants effectively and safely for test-automation work, and build the skill of reading unfamiliar code: mapping a module, tracing a call, and summarising an API from the outside.",
    "concepts": [
        {
            "title": "Reading unfamiliar code: map, trace, summarise",
            "local_only": EXEC_REQ,
            "concept": "You inherit far more code than you write. A repeatable approach: **map** the surface with `ast` (public functions, classes and their methods) to see what a module offers; **trace** who calls what by finding call sites; and **summarise** an object's usable API with `inspect` (signatures and one-line docs) without reading every line. The example does all three on a small driver module.",
            "why": "Debugging a failing nightly run in a framework someone else wrote, or deciding whether a vendor library does what you need, is a reading task first. Tools make it fast and accurate instead of scrolling and guessing.",
            "syntax": "ast.parse(src) -> FunctionDef / ClassDef nodes\ninspect.signature(obj), inspect.getmembers(obj), inspect.getsource(obj)",
            "code": """import ast  ## Static structure without running the code

SRC = '''
"Attenuator drivers."
import requests


class Attenuator:
    "Base interface."
    def set_db(self, db: float) -> None: ...
    def get_db(self) -> float: ...


class HttpAttenuator(Attenuator):
    "Talks to an HTTP attenuator."
    def __init__(self, base_url: str, step: float = 0.25):
        self.base_url, self.step = base_url, step

    def set_db(self, db):
        self._send(f"SETATT={db}")

    def get_db(self):
        return float(self._send("ATT?"))

    def _send(self, cmd):
        return requests.get(f"{self.base_url}/{cmd}", timeout=5).text


def make(url):
    return HttpAttenuator(url)
'''  ## A module you've just been handed

tree = ast.parse(SRC)  ## Parse once


def surface(tree):  ## Map public classes, their methods, and module-level functions
    for node in tree.body:  ## Top-level only
        if isinstance(node, ast.ClassDef):  ## A class
            bases = [b.id for b in node.bases if isinstance(b, ast.Name)]  ## What it extends
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]  ## Public methods
            print(f"class {node.name}({', '.join(bases)}): {methods}")  ## One line per class
        elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):  ## Module-level function
            args = [a.arg for a in node.args.args]  ## Parameter names
            print(f"def {node.name}({', '.join(args)})")  ## Its signature


surface(tree)  ## The module's public surface at a glance


def calls_to(tree, name):  ## Trace: where is `name` called?
    found = []  ## (line, enclosing function)
    for node in ast.walk(tree):  ## Whole tree
        if isinstance(node, ast.Call):  ## A call expression
            called = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)  ## requests.get -> get
            if called == name:  ## Match
                found.append(node.lineno)  ## Record the line
    return found  ## Line numbers


print("requests.get called at lines:", calls_to(tree, "get"))  ## The one network boundary in this module

import inspect  ## inspect works on live objects (built here by exec-ing the same source)
mod = {}  ## Namespace to exec into
exec(compile(tree, "attn.py", "exec"), mod)  ## Build the module
cls = mod["HttpAttenuator"]  ## The concrete driver
print("HttpAttenuator API:")  ## Summarise its usable methods
for name, member in inspect.getmembers(cls, inspect.isfunction):  ## Every method
    if not name.startswith("_") or name == "__init__":  ## Public plus the constructor
        print(f"  {name}{inspect.signature(member)}")  ## Name and signature""",
            "under": "`ast` reads structure without importing (safe for code you don't trust or can't run), while `inspect` works on live objects and gives real signatures, source (`getsource`), the defining module and MRO. For a whole codebase, the same ideas scale with tools: `grep`/ripgrep for call sites, `pyreverse` for class diagrams, an IDE's 'find usages' and call hierarchy, and the module's own tests as executable documentation of intended use.",
            "gotchas": [],
            "best": "Read the public surface and the tests first, trace one real path end to end rather than reading top to bottom, use tooling (find-usages, call hierarchy, ast/inspect) instead of scrolling, and write down a one-paragraph summary of what a module does once you understand it.",
        },
        {
            "title": "Using AI assistants well (and safely)",
            "concept": "AI assistants are good at boilerplate (parsers, fixtures, argparse, regexes), explaining unfamiliar code and errors, drafting tests, and refactoring, when given concrete context. They are unreliable on exact API details, recent library versions, and anything safety- or security-critical, and they can produce confident, wrong code. The discipline: give real context, verify every claim against docs and by running it, never paste secrets or proprietary code into external tools, and keep responsibility for the result. The code is a reviewer's checklist you can run over AI-generated snippets.",
            "why": "Assistants genuinely speed up test-automation work, which is full of boilerplate, but a plausible-looking wrong retry loop or an invented library flag that only fails on a real bench at 2 a.m. costs far more than it saved. The value is real; so is the need to verify.",
            "syntax": "# good prompt: concrete task + context + constraints + what to verify\n# then: run it, read it, check the API, test the edges",
            "code": """import re  ## Scan generated code for things to double-check

GENERATED = '''
import requests

def fetch_aps(controller, token):
    r = requests.get(f"https://{controller}/api/v1/aps",
                     headers={"Authorization": f"Bearer {token}"},
                     verify=False)
    return r.json()["aps"]

def retry(fn):
    for i in range(3):
        try:
            return fn()
        except:
            pass
'''  ## A snippet an assistant produced for "fetch APs with a retry"

CHECKS = [  ## (pattern, what to verify before trusting it)
    (r"verify\\s*=\\s*False", "TLS verification disabled: confirm this isn't shipped; use the lab CA instead"),  ## Security
    (r"requests\\.\\w+\\((?![^)]*timeout)", "HTTP call without a timeout: can hang a nightly run"),  ## Reliability
    (r"except\\s*:", "bare except: hides real failures; catch specific exceptions"),  ## Correctness
    (r'\\["\\w+"\\]', "indexes a response key directly: verify the real API shape, keys may differ"),  ## API accuracy
    (r"range\\(\\d+\\)", "fixed retry count with no backoff/delay: check against the API's rate limits"),  ## Behaviour
]  ## End of checks

findings = sorted((i, note) for pattern, note in CHECKS for i, line in enumerate(GENERATED.splitlines(), 1) if re.search(pattern, line))  ## Every (line, note) hit, in line order
print("review of AI-generated snippet:")  ## Run the human checklist, automated
for i, note in findings:  ## Each thing to verify
    print(f"  line {i}: {note}")  ## What to check before trusting it

print("\\nverify before use:")  ## The non-automatable part
for step in ["Does the controller API really return {'aps': [...]}? (check the docs or one real call)",  ## API shape
             "Is Bearer-token auth correct for this controller, or is it an API key header?",  ## Auth
             "Run it against the simulator and a real device; test the error paths",  ## Execution
             "No secrets or proprietary topology were pasted into an external tool"]:  ## Confidentiality
    print(f"  - {step}")  ## A checklist, not a guarantee""",
            "under": "The failure modes are systematic, not random: assistants interpolate from training data, so they invent plausible API shapes, default to patterns common online (`verify=False`, bare except), and can't know your library's current version or your private controller's real responses. Treating generated code exactly like a pull request from a new contributor, read, questioned, tested, is the right mental model. For confidentiality, check whether your organization permits a given tool and what may be shared before pasting anything.",
            "gotchas": [],
            "best": "Use assistants for boilerplate, explanations and first drafts with concrete context; verify every API detail against real docs or a real call; run and test the code, especially error paths; never paste secrets, credentials or proprietary code into tools your organization hasn't approved; and keep ownership of correctness, the assistant doesn't.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "List every function a module defines and whether it has a return type annotation, using ast.",
            "solution": "FunctionDef.returns is None when there's no return annotation.",
            "solution_code": """import ast

SRC = '''
def set_db(db: float) -> None: ...
def get_db(self): ...
def make(url: str) -> "Attenuator": ...
'''
for node in ast.parse(SRC).body:
    if isinstance(node, ast.FunctionDef):
        print(node.name, "annotated" if node.returns is not None else "NO return type")""",
        },
        {
            "level": "Medium",
            "prompt": "Summarise a class's public API at runtime: method names, signatures and first docstring line, with inspect.",
            "solution": "inspect.getmembers + isfunction, signature and getdoc.",
            "solution_code": """import inspect


class Bench:
    def rate_vs_range(self, band: str, start: int, stop: int) -> list:
        \"\"\"Run a rate-vs-range sweep.\"\"\"
        return []

    def reset(self) -> None:
        \"\"\"Return the bench to a known state.\"\"\"

    def _connect(self):
        \"\"\"Internal.\"\"\"


for name, m in inspect.getmembers(Bench, inspect.isfunction):
    if not name.startswith("_"):
        doc = (inspect.getdoc(m) or "").splitlines()[0]
        print(f"{name}{inspect.signature(m)} - {doc}")""",
        },
        {
            "level": "Hard",
            "prompt": "Build a tiny call graph from a module: for each top-level function, which other top-level functions it calls. Report it as an adjacency list.",
            "solution": "Collect top-level function names, then walk each function body for Call nodes whose name is in that set.",
            "solution_code": """import ast

SRC = '''
def measure(band):
    return raw_iperf(band)

def raw_iperf(band):
    return parse(run_cmd(band))

def parse(text):
    return 900.0

def run_cmd(band):
    return "..."

def report(band):
    m = measure(band)
    return format_line(m)

def format_line(m):
    return str(m)
'''
tree = ast.parse(SRC)
funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
graph = {}
for fn in (n for n in tree.body if isinstance(n, ast.FunctionDef)):
    calls = {c.func.id for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id in funcs}
    graph[fn.name] = sorted(calls)
for name, calls in graph.items():
    print(f"{name} -> {calls}")""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "How do you approach an unfamiliar codebase?", "a": "Read the README and tests first, map the public surface (modules, classes, entry points), trace one real path end to end, use find-usages/call-hierarchy and tools (ast/inspect, pyreverse) rather than reading linearly, and write a short summary as you go.", "follow": "Why read the tests? (They document intended usage and edge cases.)"},
        {"level": "Intermediate", "q": "Where do AI coding assistants help and where do they fail?", "a": "Help: boilerplate, explanations, first-draft tests, refactors, regexes, with concrete context. Fail: exact/recent API details, security-critical code, and anything needing real-world knowledge they don't have; they produce confident wrong code. Verify everything and run it.", "follow": "What's a safe workflow? (Treat output like a PR from a new contributor: read, question, test.)"},
        {"level": "Advanced", "q": "What are the risks of pasting work code into external AI tools?", "a": "Leaking secrets, proprietary topology, customer data or unreleased details; and relying on unverified output in safety- or compliance-sensitive contexts. Follow the organization's policy on approved tools and what may be shared, and never include credentials.", "follow": "How do you get the benefit safely? (Approved tools, sanitised context, local models where required, always verify.)"},
    ],
    "quiz": [
        {"q": "Read code structure without running it:", "options": ["inspect", "ast", "exec", "import"], "answer": 1, "why": "Static parse."},
        {"q": "Get a live function's signature:", "options": ["ast.signature", "inspect.signature", "func.args", "dir(func)"], "answer": 1, "why": "inspect."},
        {"q": "Best first things to read in a new codebase:", "options": ["Every file top to bottom", "README and tests", "The changelog", "Git blame"], "answer": 1, "why": "Fast orientation."},
        {"q": "AI-generated code should be treated like...", "options": ["Trusted and shipped", "A PR from a new contributor: reviewed and tested", "Documentation", "A linter"], "answer": 1, "why": "Verify and run it."},
        {"q": "Before pasting code into an external AI tool, check...", "options": ["Nothing", "Org policy and for secrets/proprietary data", "The font", "The time"], "answer": 1, "why": "Confidentiality."},
    ],
    "cards": [
        {"front": "Map a module", "back": "`ast.parse` → ClassDef/FunctionDef (surface without running)"},
        {"front": "Summarise an API", "back": "`inspect.signature`, `getmembers`, `getdoc`, `getsource`"},
        {"front": "Trace calls", "back": "find-usages / call hierarchy; ast.walk for Call nodes"},
        {"front": "AI assistants: good for", "back": "Boilerplate, explanations, first-draft tests, refactors (with context)"},
        {"front": "AI assistants: verify", "back": "API details, run it, test edges, no secrets/proprietary code"},
    ],
}
