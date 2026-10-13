"""Phase 8 content: modules 8.1-8.6 (git, code quality, Docker, compose, Jenkins)."""

from net_support import needs, sim

GIT = "runs the git command-line tool through subprocess, which the in-browser runner can't do"
TOOLS = "runs ruff and mypy through subprocess (pip install ruff mypy)"
YAML = needs("pyyaml")
JENKINS = needs("requests") + " and starts a simulated Jenkins API on localhost"
FILES = "imports a supporting file, which the in-browser runner doesn't provide"

GIT_SETUP = '''import os  ## Environment for git
import subprocess  ## Run git
import tempfile  ## Scratch repository

REPO = tempfile.mkdtemp()  ## A throwaway repo for the demo
ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",  ## Ignore personal git settings
       "GIT_AUTHOR_NAME": "Lab CI", "GIT_AUTHOR_EMAIL": "ci@lab.example",  ## Fixed author
       "GIT_COMMITTER_NAME": "Lab CI", "GIT_COMMITTER_EMAIL": "ci@lab.example",  ## Fixed committer
       "GIT_AUTHOR_DATE": "2026-10-12T09:00:00+0530", "GIT_COMMITTER_DATE": "2026-10-12T09:00:00+0530"}  ## Fixed dates: identical commit hashes on every run


def git(*args):  ## Run one git command in the demo repo
    return subprocess.run(["git", *args], cwd=REPO, env=ENV, capture_output=True, text=True, check=True).stdout.strip()  ## Raise if git fails


def commit(path, text, message):  ## Change a file and commit it
    with open(os.path.join(REPO, path), "a") as f:  ## Append so every commit changes something
        f.write(text + "\\n")  ## One new line
    git("add", path)  ## Stage it
    git("commit", "-q", "-m", message)  ## Record it
'''

M_8_1 = {
    "id": "8.1",
    "title": "Git Branching Strategies",
    "hours": 1.5,
    "summary": "Branches, merges, tags and cherry-picks as a test-automation team uses them: short-lived feature branches into main, release branches for firmware trains, and hotfixes carried across.",
    "concepts": [
        {
            "title": "Feature branches and merges (trunk-based)",
            "local_only": GIT,
            "concept": "In **trunk-based development** everyone integrates into `main` frequently through short-lived branches (hours to a couple of days) reviewed as pull requests. `git switch -c` creates a branch, commits stay on it until merged, and `git merge --no-ff` records a merge commit so the feature remains visible in history (a squash merge would instead combine it into one commit). The example drives real git from Python with fixed author dates, so the commit hashes are the same every time you run it.",
            "why": "A test framework is shared by many people and run by CI against every firmware build. Small, frequently merged changes keep `main` always runnable; long-lived branches drift apart and produce painful merges right before a release.",
            "syntax": "git switch -c feature/rvr-6g\ngit commit -am \"Add 6 GHz to RvR test\"\ngit switch main && git merge --no-ff feature/rvr-6g\ngit log --oneline --graph --all",
            "code": GIT_SETUP + """

git("init", "-q", "-b", "main")  ## New repository whose default branch is main
commit("framework.py", "VERSION = '1.0'", "Add test framework skeleton")  ## First commit on main
git("switch", "-q", "-c", "feature/rvr-6g")  ## Create and switch to a short-lived feature branch
commit("test_rvr.py", "BANDS = ['5G', '6G']", "Add 6 GHz to RvR test")  ## Work on the branch
commit("test_rvr.py", "KPI_6G = 2200", "Add 6 GHz KPI")  ## More work on the branch
git("switch", "-q", "main")  ## Meanwhile, someone fixes main
commit("framework.py", "TIMEOUT = 30", "Fix: raise attenuator timeout")  ## main moved on
git("merge", "-q", "--no-ff", "feature/rvr-6g", "-m", "Merge feature/rvr-6g")  ## Merge commit with two parents
print(git("log", "--oneline", "--graph", "--all"))  ## The shape of history
git("branch", "-d", "feature/rvr-6g")  ## Delete the merged branch (safe: refuses if unmerged)
print(git("branch", "--list"))  ## Only main is left""",
            "under": "A commit's hash is a SHA-1 (SHA-256 in newer repos) of its content, parents, author, committer and timestamps, which is why fixing the dates and identity makes the output reproducible. A branch is just a movable name for a commit; `merge --no-ff` creates a commit with two parents even when a fast-forward would be possible. `--graph` draws those parent links.",
            "gotchas": [
                {
                    "title": "Committing captures, results and secrets",
                    "local_only": GIT,
                    "note": "`git add -A` stages everything: multi-gigabyte pcaps, result folders, `.env` files with passwords, bytecode. Once pushed, secrets are in history forever (removing them needs a history rewrite and a credential rotation). Add a `.gitignore` before the first commit.",
                    "wrong": """import os, subprocess, tempfile

repo = tempfile.mkdtemp()
for path, text in {"src/test_rvr.py": "pass", "results/run1.pcap": "\\xd4\\xc3", ".env": "SSH_PASSWORD=Wl@n7", "src/__pycache__/x.pyc": ""}.items():
    os.makedirs(os.path.join(repo, os.path.dirname(path)), exist_ok=True)
    open(os.path.join(repo, path), "w").write(text)
run = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True).stdout
run("init", "-q")
run("add", "-A")
print(run("status", "--porcelain"))""",
                    "fixed": """import os, subprocess, tempfile

repo = tempfile.mkdtemp()
files = {".gitignore": "results/\\n*.pcap\\n.env\\n__pycache__/\\n", "src/test_rvr.py": "pass",
         "results/run1.pcap": "\\xd4\\xc3", ".env": "SSH_PASSWORD=Wl@n7", "src/__pycache__/x.pyc": ""}
for path, text in files.items():
    os.makedirs(os.path.join(repo, os.path.dirname(path)), exist_ok=True)
    open(os.path.join(repo, path), "w").write(text)
run = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True).stdout
run("init", "-q")
run("add", "-A")
print(run("status", "--porcelain"))""",
                },
            ],
            "best": "Keep branches short-lived, rebase or merge `main` into them daily, require pull requests with CI green before merge, protect `main`, write commit messages that say why, and start every repo with a `.gitignore` (plus a pre-commit secret scanner, 8.2).",
        },
        {
            "title": "Tags, release branches and cherry-picks",
            "local_only": GIT,
            "concept": "An **annotated tag** (`git tag -a v1.4.0 -m ...`) marks a release permanently. A **release branch** (`release/1.4`) is cut from that tag when a firmware train needs its own test-suite version while `main` moves on. A fix made on `main` is carried to the release branch with `git cherry-pick -x`, which copies the change and records where it came from. `git describe --tags` names any commit relative to the latest tag.",
            "why": "Firmware 1.4 is in the field and tested with suite 1.4; main is already testing Wi-Fi 7 features for 1.5. When a bug in the RvR test is found, it must be fixed for both, without dragging 1.5's tests into the 1.4 suite.",
            "syntax": "git tag -a v1.4.0 -m \"Release 1.4.0\"\ngit switch -c release/1.4 v1.4.0\ngit cherry-pick -x <commit>\ngit describe --tags",
            "code": GIT_SETUP + """

git("init", "-q", "-b", "main")  ## Fresh repo
commit("suite.py", "SUITE = 'rvr+roam'", "Suite for firmware 1.4")  ## The state we release
git("tag", "-a", "v1.4.0", "-m", "Test suite 1.4.0")  ## Annotated tag: has its own message, author and date
git("switch", "-q", "-c", "release/1.4", "v1.4.0")  ## Release branch starting at the tag
git("switch", "-q", "main")  ## Back to main
commit("suite.py", "MLO = True", "Add Wi-Fi 7 MLO tests")  ## New feature: must NOT go to 1.4
commit("rvr.py", "SIGNAL = 'optional'", "Fix: handle missing Radiotap signal")  ## Bug fix: needed in 1.4 too
fix = git("rev-parse", "--short", "HEAD")  ## Hash of the fix
print("main is", git("describe", "--tags"))  ## tag-commits_since-g<hash>

git("switch", "-q", "release/1.4")  ## Go to the release branch
git("cherry-pick", "-x", fix)  ## Copy only the fix; -x appends "(cherry picked from commit ...)"
git("tag", "-a", "v1.4.1", "-m", "Test suite 1.4.1")  ## Patch release
print(git("log", "--oneline", "release/1.4"))  ## Release history: no MLO commit
print(git("log", "-1", "--format=%B").splitlines()[-1])  ## The provenance line from -x
print(git("tag", "--list"))  ## Both releases""",
            "under": "`git describe` finds the nearest annotated tag reachable from HEAD and appends the number of commits since it and the abbreviated hash (`v1.4.0-2-g<hash>`), a handy build identifier for CI artifacts. A cherry-pick creates a **new** commit with the same change but a different parent, so it gets a different hash than the original.",
            "gotchas": [],
            "best": "Use semantic version tags on the test framework, cut release branches only when a firmware train needs one, land fixes on `main` first and cherry-pick with `-x`, and stamp every CI result with `git describe` output so you always know which suite version produced it.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "local_only": GIT,
            "prompt": "Create a repo with two commits and print `git log --format='%h %an %s'` and the number of commits (`git rev-list --count HEAD`).",
            "solution": "Fixed identity and dates via environment variables make the hashes reproducible.",
            "solution_code": GIT_SETUP.replace("  ## ", "  # ") + """
git("init", "-q", "-b", "main")
commit("a.py", "x = 1", "First")
commit("a.py", "y = 2", "Second")
print(git("log", "--format=%h %an %s"))
print(git("rev-list", "--count", "HEAD"))""",
        },
        {
            "level": "Medium",
            "local_only": GIT,
            "prompt": "Show the difference between a fast-forward merge and `--no-ff`: merge two identical branches each way and count the commits on main.",
            "solution": "When main hasn't moved, a plain merge just moves the pointer (no new commit); --no-ff always creates a merge commit.",
            "solution_code": GIT_SETUP.replace("  ## ", "  # ") + """
git("init", "-q", "-b", "main")
commit("a.py", "base", "Base")
for name, flags in (("ff", []), ("noff", ["--no-ff", "-m", "Merge noff"])):
    git("switch", "-q", "-c", f"feature/{name}", "main")
    commit(f"{name}.py", name, f"Work on {name}")
    git("switch", "-q", "main")
    before = int(git("rev-list", "--count", "HEAD"))
    git("merge", "-q", *flags, f"feature/{name}")
    print(name, "added", int(git("rev-list", "--count", "HEAD")) - before, "commit(s) to main")""",
        },
        {
            "level": "Hard",
            "local_only": GIT,
            "prompt": "Find which commit broke a check using `git bisect run`: ten commits change a KPI value, and the check fails once KPI drops below 800.",
            "solution": "`git bisect run <cmd>` binary-searches history, using the command's exit code (0 good, 1 bad) to locate the first bad commit in about log2(n) steps.",
            "solution_code": GIT_SETUP.replace("  ## ", "  # ") + """
git("init", "-q", "-b", "main")
for i, kpi in enumerate([900, 890, 880, 870, 860, 850, 790, 780, 770, 760]):
    with open(os.path.join(REPO, "kpi.txt"), "w") as f:
        f.write(str(kpi))
    git("add", "kpi.txt")
    git("commit", "-q", "-m", f"Tune KPI to {kpi}")
expected = git("rev-parse", "HEAD~3")
git("bisect", "start", "HEAD", "HEAD~9")
check = ["python3", "-c", "import sys; sys.exit(0 if int(open('kpi.txt').read()) >= 800 else 1)"]
out = git("bisect", "run", *check)
first_bad = next(line for line in out.splitlines() if "is the first bad commit" in line).split()[0]
print("found the 7th commit:", first_bad == expected)
print(git("show", "-s", "--format=%s", "refs/bisect/bad"))
git("bisect", "reset")""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "merge vs rebase?", "a": "Merge combines histories with a merge commit (history shows what really happened). Rebase replays your commits on top of another branch, giving a linear history but rewriting commit hashes. Never rebase commits others have already pulled.", "follow": "What does squash merge do? (Combines a branch into one commit on main.)"},
        {"level": "Intermediate", "q": "Which branching strategy suits a test automation repo?", "a": "Trunk-based with short-lived feature branches and PR reviews, CI on every PR, and release branches only when a product release train needs a frozen suite. GitFlow's long-lived develop branch adds overhead without much benefit for test code.", "follow": "How do you keep a release branch's suite compatible with its firmware? (Cherry-pick fixes only; features stay on main.)"},
        {"level": "Intermediate", "q": "How do you find the commit that broke a test?", "a": "git bisect: mark a known good and bad commit, then test the midpoints, or automate with git bisect run and a script whose exit code says good or bad.", "follow": "What if some commits can't be tested? (Exit code 125 tells bisect to skip.)"},
        {"level": "Advanced", "q": "A password was committed and pushed. What do you do?", "a": "Rotate the credential immediately (assume it's compromised), then remove it from history (git filter-repo or BFG), force-push, ask everyone to re-clone, and add secret scanning (pre-commit hooks, server-side push protection) so it can't recur.", "follow": "Why rotate first? (History rewrite doesn't remove copies already cloned or cached.)"},
    ],
    "quiz": [
        {"q": "`git merge --no-ff` always...", "options": ["Rebases", "Creates a merge commit", "Squashes", "Fails on conflicts"], "answer": 1, "why": "Even when fast-forward is possible."},
        {"q": "Copy one fix to a release branch:", "options": ["git merge main", "git cherry-pick -x <sha>", "git rebase", "git revert"], "answer": 1, "why": "Only that change."},
        {"q": "`git describe --tags` output `v1.4.0-2-gabc123` means...", "options": ["Version 1.4.2", "2 commits after tag v1.4.0", "Tag on commit 2", "An error"], "answer": 1, "why": "tag-count-g<hash>."},
        {"q": "Commit hashes depend on...", "options": ["Content only", "Content, parents, author, committer, timestamps", "Branch name", "Remote URL"], "answer": 1, "why": "Hence reproducible with fixed env."},
        {"q": "Keep pcaps out of the repo:", "options": ["git rm later", ".gitignore before committing", "git stash", "git clean"], "answer": 1, "why": "Ignore first."},
    ],
    "cards": [
        {"front": "New branch", "back": "`git switch -c feature/x`"},
        {"front": "Merge keeping branch history", "back": "`git merge --no-ff feature/x`"},
        {"front": "Release tag", "back": "`git tag -a v1.4.0 -m 'msg'`; `git push --tags`"},
        {"front": "Carry a fix", "back": "`git cherry-pick -x <sha>`"},
        {"front": "Find the bad commit", "back": "`git bisect start BAD GOOD; git bisect run ./check.sh`"},
    ],
}


WIFI_UTILS = '''import os
import subprocess
from typing import Optional


def channel_to_freq(channel, band = "5G", cache={}):
    if band == None:
        return None
    if channel in cache: return cache[channel]
    try:
        freq = 5000 + 5*channel
    except:
        print(f"bad channel")
    cache[channel] = freq
    return freq
'''

BENCH_TYPED = '''from dataclasses import dataclass


@dataclass
class Radio:
    band: str
    channel: int
    width_mhz: int


def parse_width(text: str) -> int:
    return text.removesuffix(" MHz")


def find_radio(radios: list[Radio], band: str) -> Radio | None:
    for r in radios:
        if r.band == band:
            return r
    return None


def report(radios: list[Radio]) -> str:
    six = find_radio(radios, "6G")
    return f"6 GHz on channel {six.channel}"
'''

M_8_2 = {
    "id": "8.2",
    "title": "pre-commit, ruff, black & mypy",
    "hours": 1.5,
    "summary": "Automate code quality: ruff for linting and formatting (black-compatible), mypy for type checking, and pre-commit to run them before every commit and in CI.",
    "concepts": [
        {
            "title": "ruff: lint and format",
            "files": {"wifi_utils.py": WIFI_UTILS},
            "local_only": TOOLS,
            "concept": "**ruff** is a very fast Python linter (it implements the rules of flake8, pyflakes, pycodestyle, bugbear, pyupgrade and more) and formatter (black-compatible). `ruff check` reports problems with rule codes (F401 unused import, E711 comparison to None, E722 bare except, B006 mutable default argument...), `ruff check --fix` repairs the safe ones, and `ruff format` rewrites layout. The sample file in the supporting files contains classic bugs; the script runs ruff on it the way a CI job would.",
            "why": "Most of those 'style' findings are real bugs in test code: a mutable default shared between calls, a bare except that hides KeyboardInterrupt and real failures, a variable that's unset when the except branch runs. Catching them automatically frees code review for test logic.",
            "syntax": "ruff check --select E,F,B,UP .\nruff check --fix .\nruff format --diff .\n\n# pyproject.toml\n[tool.ruff]\nline-length = 110\n[tool.ruff.lint]\nselect = [\"E\", \"F\", \"B\", \"UP\", \"SIM\"]",
            "code": """import subprocess  ## Run the tools as a CI job would


def tool(*cmd):  ## Run a command, return (exit code, combined output)
    p = subprocess.run(cmd, capture_output=True, text=True)  ## Don't raise: non-zero just means findings
    return p.returncode, (p.stdout + p.stderr).strip()  ## Both streams


rc, out = tool("ruff", "check", "--no-cache", "--select", "E,F,B", "--output-format", "concise", "wifi_utils.py")  ## Lint with three rule families
print(out)  ## One finding per line: file:line:col: CODE message
print("ruff check exit code:", rc)  ## 1 = findings, which fails a CI step

rc, out = tool("ruff", "format", "--no-cache", "--diff", "wifi_utils.py")  ## What the formatter would change, without changing it
print("\\n".join(line for line in out.splitlines() if line.startswith(("-", "+")) and not line.startswith(("---", "+++"))))  ## Just the changed lines
print("ruff format exit code:", rc)  ## 1 = file would be reformatted""",
            "under": "ruff parses each file into a syntax tree once and runs all enabled rules over it, written in Rust, which is why it checks large repos in milliseconds. Rule codes keep the prefixes of the tools they came from (`F` pyflakes, `E`/`W` pycodestyle, `B` flake8-bugbear). The formatter's output is deterministic, so formatting debates disappear: whatever `ruff format` produces is the style.",
            "gotchas": [],
            "best": "Configure ruff in `pyproject.toml`, start with E, F, B, UP and SIM, fix or explicitly ignore (`# noqa: B006` with a reason) every finding, run `ruff format` instead of debating style, and run the same commands locally (pre-commit) and in CI so they never disagree.",
        },
        {
            "title": "mypy: catching bugs with type hints",
            "files": {"bench.py": BENCH_TYPED},
            "local_only": TOOLS,
            "concept": "mypy reads type hints and reports code that can't be right: returning `str` where `int` was promised, using a value that may be `None` without checking, calling methods that don't exist. It doesn't run your code. `--strict` turns on the full set of checks; most teams start with defaults plus `--check-untyped-defs` and tighten over time.",
            "why": "The bug in `report()` below (using a radio that may not exist) would crash a nightly run only on benches without a 6 GHz radio. mypy finds it on the laptop in a second.",
            "syntax": "mypy --strict src/\n\n# pyproject.toml\n[tool.mypy]\npython_version = \"3.12\"\nstrict = true",
            "code": """import subprocess  ## Run mypy like CI

p = subprocess.run(["mypy", "--no-incremental", "--strict", "bench.py"], capture_output=True, text=True)  ## No cache, all strict checks
for line in p.stdout.splitlines():  ## file:line: error: message [code]
    print(line)  ## Each finding
print("mypy exit code:", p.returncode)  ## 1 = type errors""",
            "under": "mypy builds a model of every name's type from annotations and inference (`six` is `Radio | None` because that's what `find_radio` returns), then checks each operation against it. The `[return-value]` and `[union-attr]` codes in brackets can be used to silence one specific error with `# type: ignore[code]`. Type hints have no effect at runtime unless a library (pydantic, typer) reads them.",
            "gotchas": [
                {
                    "title": "mypy silently skips functions without annotations",
                    "local_only": TOOLS,
                    "note": "By default mypy doesn't type-check the body of an unannotated function, so a fully unannotated module passes with 'no issues'. Add annotations, or at least enable `check_untyped_defs`.",
                    "wrong": """import pathlib
import subprocess

pathlib.Path("radio.py").write_text("def width(band):\\n    widths = {'5G': 80}\\n    return widths[band] + ' MHz'\\n")
print(subprocess.run(["mypy", "--no-incremental", "radio.py"], capture_output=True, text=True).stdout.strip())""",
                    "fixed": """import pathlib
import subprocess

pathlib.Path("radio.py").write_text("def width(band):\\n    widths = {'5G': 80}\\n    return widths[band] + ' MHz'\\n")
print(subprocess.run(["mypy", "--no-incremental", "--check-untyped-defs", "radio.py"], capture_output=True, text=True).stdout.strip())""",
                },
            ],
            "best": "Annotate public functions and framework APIs first, run mypy in CI, use `X | None` honestly and handle the None, avoid `Any` creeping in from untyped libraries (install their stubs), and ratchet strictness module by module.",
        },
        {
            "title": "pre-commit: the same checks on every commit",
            "runner": "none",
            "lang": "YAML",
            "filename": ".pre-commit-config.yaml",
            "concept": "pre-commit installs a git hook that runs configured checks on the files you're committing, each tool in its own pinned environment. `pre-commit install` once per clone; `pre-commit run --all-files` in CI. If a hook fails or modifies files, the commit is stopped so you can review. The config below wires up ruff (lint + format), mypy, and generic hooks that catch big files, merge-conflict markers and private keys.",
            "why": "Problems found before the commit never reach the PR, the CI queue, or the lab. And because the versions are pinned in the config, every engineer and the CI run exactly the same checks.",
            "syntax": "pip install pre-commit\npre-commit install\npre-commit run --all-files\npre-commit autoupdate",
            "code": """repos:  ## List of hook repositories
  - repo: https://github.com/astral-sh/ruff-pre-commit  ## Official ruff hooks
    rev: v0.6.9  ## Pinned version (pre-commit autoupdate bumps it)
    hooks:  ## Hooks from this repo
      - id: ruff  ## Lint
        args: [--fix]  ## Apply safe fixes; the commit stops so you can review them
      - id: ruff-format  ## Format (black-compatible)
  - repo: https://github.com/pre-commit/mirrors-mypy  ## mypy packaged for pre-commit
    rev: v1.11.2  ## Pinned
    hooks:  ## Hooks from this repo
      - id: mypy  ## Type check
        additional_dependencies: [types-requests, types-PyYAML]  ## Stubs mypy needs in its isolated env
  - repo: https://github.com/pre-commit/pre-commit-hooks  ## Generic hygiene hooks
    rev: v4.6.0  ## Pinned
    hooks:  ## Hooks from this repo
      - id: check-added-large-files  ## Blocks accidental pcaps and firmware images
        args: [--maxkb=2048]  ## Anything over 2 MB
      - id: check-merge-conflict  ## Leftover <<<<<<< markers
      - id: detect-private-key  ## SSH/TLS private keys
      - id: end-of-file-fixer  ## Newline at end of file
      - id: trailing-whitespace  ## Strip trailing spaces""",
            "under": "On `git commit`, the hook passes the staged file names to each hook whose file filter matches (Python hooks only see .py files). Each repository at its `rev` is cloned once and installed into a cached virtualenv under `~/.cache/pre-commit`, which is why hooks don't depend on what's installed in your project environment.",
            "gotchas": [],
            "best": "Keep hooks fast (under a few seconds), pin every `rev`, run `pre-commit run --all-files` in CI as well (hooks can be skipped locally with `--no-verify`), and add a secret scanner (gitleaks or detect-secrets) for lab credentials.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "local_only": TOOLS,
            "prompt": "Run `ruff check --fix` on a copy of the sample file and show how many findings remain afterwards (the ones that need a human).",
            "solution": "Safe fixes (unused imports, the f-string without placeholders) are applied automatically. `== None` → `is None` counts as an *unsafe* fix in ruff (it changes behaviour for objects with a custom `__eq__`), so it stays, along with the findings that need judgement: the mutable default, the one-line `if`, and the bare except.",
            "files": {"wifi_utils.py": WIFI_UTILS},
            "solution_code": """import subprocess

subprocess.run(["ruff", "check", "--no-cache", "--select", "E,F,B", "--fix", "--quiet", "wifi_utils.py"], capture_output=True)
out = subprocess.run(["ruff", "check", "--no-cache", "--select", "E,F,B", "--output-format", "concise", "wifi_utils.py"],
                     capture_output=True, text=True).stdout
print(out.strip())""",
        },
        {
            "level": "Medium",
            "local_only": TOOLS,
            "files": {"bench.py": BENCH_TYPED},
            "prompt": "Fix the two mypy errors in bench.py (convert the width to int; handle the missing radio) and show mypy --strict passes.",
            "solution": "Return `int(...)`, and check for None before using the radio. Writing the fixed module and re-running mypy proves it.",
            "solution_code": """import pathlib
import subprocess

src = pathlib.Path("bench.py").read_text()
src = src.replace('return text.removesuffix(" MHz")', 'return int(text.removesuffix(" MHz"))')
src = src.replace('    six = find_radio(radios, "6G")\\n    return f"6 GHz on channel {six.channel}"',
                  '    six = find_radio(radios, "6G")\\n    if six is None:\\n        return "no 6 GHz radio"\\n    return f"6 GHz on channel {six.channel}"')
pathlib.Path("bench.py").write_text(src)
print(subprocess.run(["mypy", "--no-incremental", "--strict", "bench.py"], capture_output=True, text=True).stdout.strip())""",
        },
        {
            "level": "Hard",
            "local_only": TOOLS,
            "files": {"wifi_utils.py": WIFI_UTILS, "bench.py": BENCH_TYPED},
            "prompt": "Write a quality-gate script that runs ruff check, ruff format --check and mypy, prints a one-line status per tool, and exits non-zero if any failed (so a CI step fails).",
            "solution": "Collect each tool's exit code, print a table, and `sys.exit(1)` if any is non-zero. The same script runs locally and in CI.",
            "solution_code": """import subprocess
import sys

CHECKS = {
    "ruff check": ["ruff", "check", "--no-cache", "--quiet", "."],
    "ruff format": ["ruff", "format", "--no-cache", "--check", "--quiet", "."],
    "mypy": ["mypy", "--no-incremental", "bench.py"],
}
failed = []
for name, cmd in CHECKS.items():
    rc = subprocess.run(cmd, capture_output=True, text=True).returncode
    print(f"{name:<12} {'PASS' if rc == 0 else 'FAIL'}")
    if rc:
        failed.append(name)
print("gate:", "FAILED " + ", ".join(failed) if failed else "passed")
sys.exit(1 if failed else 0)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What's the difference between a linter, a formatter and a type checker?", "a": "A linter (ruff, flake8) finds likely bugs and bad patterns; a formatter (ruff format, black) rewrites layout so style is consistent; a type checker (mypy, pyright) verifies type consistency using annotations. None of them run the code.", "follow": "Why automate formatting? (No style debates in reviews; diffs show only real changes.)"},
        {"level": "Intermediate", "q": "Why is a mutable default argument a bug?", "a": "The default object is created once when the function is defined and shared by every call, so state leaks between calls (e.g. a cache dict or a results list). Use None and create inside.", "follow": "Which ruff rule catches it? (B006.)"},
        {"level": "Intermediate", "q": "How do you introduce mypy into an existing untyped codebase?", "a": "Start with default settings plus check_untyped_defs, fix or ignore findings, annotate the framework's public API first, use per-module overrides to enforce strict on new or cleaned modules, and run it in CI so it can only get better.", "follow": "What are stub packages? (types-requests etc., type info for untyped libraries.)"},
    ],
    "quiz": [
        {"q": "ruff rule for a bare `except:`:", "options": ["F401", "E722", "B006", "E711"], "answer": 1, "why": "E722."},
        {"q": "`ruff format --check` exit code 1 means...", "options": ["Crash", "Files would be reformatted", "Lint errors", "Success"], "answer": 1, "why": "Use in CI."},
        {"q": "By default mypy checks unannotated function bodies?", "options": ["Yes", "No", "Only in --strict", "Only for classes"], "answer": 1, "why": "Enable check_untyped_defs."},
        {"q": "Install the git hook once per clone:", "options": ["pre-commit run", "pre-commit install", "git hook add", "pip install hooks"], "answer": 1, "why": "Writes .git/hooks/pre-commit."},
        {"q": "Run all hooks on all files in CI:", "options": ["pre-commit", "pre-commit run --all-files", "git commit", "ruff ."], "answer": 1, "why": "Not just staged files."},
    ],
    "cards": [
        {"front": "Lint + autofix", "back": "`ruff check --fix .`"},
        {"front": "Format check", "back": "`ruff format --check .` (or `black --check .`)"},
        {"front": "Type check", "back": "`mypy --strict src/`; handle `X | None`"},
        {"front": "pre-commit", "back": "`.pre-commit-config.yaml`; `pre-commit install`; `run --all-files` in CI"},
        {"front": "Classic bug rules", "back": "B006 mutable default, E722 bare except, F401 unused import, E711 == None"},
    ],
}


DOCKERFILE_BAD = '''FROM python:latest
ENV LAB_PASSWORD=Wl@n-7-s3cret
COPY . /app
RUN apt-get update && apt-get install -y tshark iperf3
RUN pip install -r /app/requirements.txt
CMD python -m pytest /app/tests
'''

M_8_3 = {
    "id": "8.3",
    "title": "Docker for Test Runners",
    "hours": 2.5,
    "summary": "Package the test framework and its tools (tshark, iperf3, SSH) into a reproducible image: a well-structured Dockerfile, layer caching, non-root users, and running containers against lab hardware.",
    "concepts": [
        {
            "title": "A Dockerfile for a Wi-Fi test runner",
            "runner": "none",
            "lang": "Dockerfile",
            "filename": "Dockerfile",
            "concept": "A Dockerfile is a recipe: each instruction creates a layer of the image. Start from a **pinned** slim Python base, install system tools in one `RUN` (cleaning apt lists in the same layer), copy the dependency lock file and install it **before** copying the source (so code changes don't invalidate the dependency layer), run as a **non-root** user, and use exec-form `ENTRYPOINT`/`CMD` so signals reach pytest.",
            "why": "\"Works on my machine\" disappears when every CI agent, bench PC and laptop runs the same image with the same tshark, iperf3 and Python packages. A rebuild after a test change takes seconds because only the last layers change.",
            "syntax": "docker build -t wifi-tests:1.4.1 .\ndocker run --rm -v \"$PWD/results:/results\" wifi-tests:1.4.1 -m smoke",
            "code": """# syntax=docker/dockerfile:1  ## Enables current BuildKit syntax features
FROM python:3.12-slim-bookworm  ## Pinned base: exact Python minor version and Debian release
ENV PYTHONDONTWRITEBYTECODE=1 \\  ## No .pyc files in the image
    PYTHONUNBUFFERED=1 \\  ## Logs appear immediately in CI output
    PIP_NO_CACHE_DIR=1 \\  ## Don't keep pip's download cache in a layer
    DEBIAN_FRONTEND=noninteractive  ## tshark's installer must not stop to ask questions
RUN apt-get update \\  ## Refresh package lists...
 && apt-get install -y --no-install-recommends tshark iperf3 openssh-client iw \\  ## ...install only what tests need...
 && rm -rf /var/lib/apt/lists/*  ## ...and drop the lists in the SAME layer, or they stay in the image
WORKDIR /opt/wifi-tests  ## All following paths are relative to this
COPY requirements.lock .  ## Dependencies first: this layer is reused until the lock file changes
RUN pip install --require-hashes -r requirements.lock  ## Exact, verified versions
COPY . .  ## Source last: editing a test only rebuilds from here
RUN useradd --create-home --uid 1000 tester && chown -R tester /opt/wifi-tests  ## Unprivileged account
USER tester  ## Everything from now on, including the tests, runs as non-root
ENTRYPOINT ["python", "-m", "pytest"]  ## Exec form: pytest is PID 1 and receives SIGTERM from CI
CMD ["-m", "smoke", "--junitxml=/results/junit.xml"]  ## Default arguments, replaced by anything after the image name""",
            "under": "Docker caches each layer keyed by the instruction and its inputs (for COPY, the files' content). The first changed layer and everything after it is rebuilt, which is why the order is: rarely changing (OS packages) → sometimes (Python deps) → often (source). With shell-form `CMD python -m pytest` the process runs under `/bin/sh -c`, which doesn't forward SIGTERM, so a cancelled CI job leaves pytest running until it's killed.",
            "gotchas": [
                {
                    "title": "Shipping the whole working directory as build context",
                    "note": "Without a `.dockerignore`, `docker build .` sends everything to the builder: `.git`, virtualenvs, gigabytes of captures from past runs. Builds get slow and secrets can end up in images. The script estimates the context size for a typical repo with and without ignore rules.",
                    "wrong": """from fnmatch import fnmatch

tree = {".git/objects/pack/p1.pack": 410, "venv/lib/site-packages.tar": 380, "results/2026-10-11/run.pcap": 2150,
        "src/framework.py": 0.1, "tests/test_rvr.py": 0.05, "requirements.lock": 0.01, ".env": 0.001}
ignore = []
sent = {p: mb for p, mb in tree.items() if not any(fnmatch(p, pat) for pat in ignore)}
print(f"context: {sum(sent.values()):.0f} MB, includes .env: {'.env' in sent}")""",
                    "fixed": """from fnmatch import fnmatch

tree = {".git/objects/pack/p1.pack": 410, "venv/lib/site-packages.tar": 380, "results/2026-10-11/run.pcap": 2150,
        "src/framework.py": 0.1, "tests/test_rvr.py": 0.05, "requirements.lock": 0.01, ".env": 0.001}
ignore = [".git/*", "venv/*", "results/*", "*.pcap", ".env"]
sent = {p: mb for p, mb in tree.items() if not any(fnmatch(p, pat) for pat in ignore)}
print(f"context: {sum(sent.values()):.2f} MB, includes .env: {'.env' in sent}")""",
                },
            ],
            "best": "Pin the base image (tag, ideally digest), order layers by change frequency, combine apt commands with cleanup, use a lock file with hashes, add `.dockerignore`, run as non-root, use exec-form ENTRYPOINT, never bake secrets into ENV/ARG, and tag images with the framework version and git hash.",
        },
        {
            "title": "Checking Dockerfiles and building run commands in Python",
            "concept": "Two small tools that teams end up writing: a **Dockerfile linter** that enforces house rules (pinned base, no secrets in ENV, apt cleanup, non-root USER, exec-form CMD) in CI, and a **run-command builder** that turns a bench description into the right `docker run` flags: host networking or device passthrough for lab hardware, an env file for secrets, a results volume, and capabilities for packet capture. `shlex.join` produces a command line that's safe to paste into a shell.",
            "why": "Hardware tests need privileges ordinary containers don't have (raw sockets for Scapy, serial devices, the lab VLAN), and getting those flags right by hand for each bench is error-prone. Generating them from the bench config makes them consistent and reviewable.",
            "syntax": "docker run --rm --network host --device /dev/ttyUSB0 --cap-add NET_RAW --env-file bench.env -v ./results:/results image args",
            "code": """import re  ## Pattern checks
import shlex  ## Shell-safe command lines

DOCKERFILE = \"\"\"FROM python:latest
ENV LAB_PASSWORD=Wl@n-7-s3cret
COPY . /app
RUN apt-get update && apt-get install -y tshark iperf3
RUN pip install -r /app/requirements.txt
CMD python -m pytest /app/tests\"\"\"  ## A Dockerfile that breaks most of the rules

RULES = [  ## (message, function that returns True when the rule is violated)
    ("base image not pinned", lambda t: re.search(r"^FROM \\S+:(latest)?\\s*$|^FROM [^:\\s]+\\s*$", t, re.M)),  ## :latest or no tag at all
    ("secret-looking ENV/ARG", lambda t: re.search(r"^(ENV|ARG) \\S*(PASSWORD|TOKEN|SECRET|KEY)\\S*=", t, re.M | re.I)),  ## Credentials baked into layers
    ("apt lists not cleaned", lambda t: "apt-get install" in t and "rm -rf /var/lib/apt/lists" not in t),  ## Bloated layer
    ("no non-root USER", lambda t: not re.search(r"^USER (?!root\\b)\\S+", t, re.M)),  ## Tests would run as root
    ("source copied before dependencies", lambda t: t.find("COPY . ") < t.find("pip install")),  ## Breaks layer caching
    ("shell-form CMD/ENTRYPOINT", lambda t: re.search(r"^(CMD|ENTRYPOINT) (?!\\[)", t, re.M)),  ## Signals won't reach the process
]  ## End of rules

problems = [msg for msg, violated in RULES if violated(DOCKERFILE)]  ## Run every rule
print(f"{len(problems)} problems:", *problems, sep="\\n  - ")  ## Report


def docker_run(bench, image, pytest_args):  ## Bench config -> docker run command
    cmd = ["docker", "run", "--rm", "--name", f"tests-{bench['name']}"]  ## Remove the container afterwards; predictable name
    if bench.get("lab_vlan"):  ## Tests must reach devices on the lab network
        cmd += ["--network", "host"]  ## Share the host's interfaces
    for dev in bench.get("serial", []):  ## DUT consoles
        cmd += ["--device", dev]  ## Pass the serial device through
    if bench.get("capture"):  ## Scapy/tshark need raw sockets
        cmd += ["--cap-add", "NET_RAW", "--cap-add", "NET_ADMIN"]  ## Just these capabilities, not --privileged
    cmd += ["--env-file", f"/etc/lab/{bench['name']}.env"]  ## Secrets from a root-only file, not the command line
    cmd += ["-v", f"/srv/results/{bench['name']}:/results"]  ## Results survive the container
    return shlex.join(cmd + [image, *pytest_args])  ## Quote everything safely


bench07 = {"name": "lab-07", "lab_vlan": True, "serial": ["/dev/ttyUSB0"], "capture": True}  ## From the bench inventory
print(docker_run(bench07, "registry.lab/wifi-tests:1.4.1", ["-m", "smoke and not slow", "--junitxml=/results/junit.xml"]))  ## Ready to run""",
            "under": "The linter works on raw text with multiline regexes (`re.M` makes `^` match at each line start); real tools like hadolint parse the Dockerfile properly and cover many more rules. `shlex.join` single-quotes any argument containing spaces or shell metacharacters (like the `-m` expression), so the printed command means exactly what the list means.",
            "gotchas": [],
            "best": "Run a Dockerfile linter (hadolint) in CI, prefer specific capabilities and devices over `--privileged`, pass secrets through env files or secret mounts (never on the command line, which shows up in `ps` and CI logs), and generate run commands from bench data.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Given a list of Dockerfile instructions, report the index of the first layer that a change to `tests/test_rvr.py` would invalidate (the first COPY that includes it).",
            "solution": "Layers before the first COPY of the changed file stay cached; that COPY and everything after rebuild.",
            "solution_code": """layers = ["FROM python:3.12-slim-bookworm", "RUN apt-get install -y tshark", "COPY requirements.lock .",
          "RUN pip install -r requirements.lock", "COPY . .", "USER tester"]
changed = "tests/test_rvr.py"
first = next(i for i, ins in enumerate(layers) if ins.startswith("COPY") and (ins.split()[1] in (".", changed)))
print("rebuild from layer", first, "->", layers[first:])
print("cached:", layers[:first])""",
        },
        {
            "level": "Medium",
            "prompt": "Extend the bench-to-command builder with a `cpus`/`memory` limit and a `--stop-timeout` so long-running suites get time to clean up, and print the command for a bench without serial devices.",
            "solution": "Optional settings become optional flags; shlex.join keeps quoting correct.",
            "solution_code": """import shlex


def docker_run(bench, image, args):
    cmd = ["docker", "run", "--rm"]
    if "cpus" in bench:
        cmd += ["--cpus", str(bench["cpus"])]
    if "memory" in bench:
        cmd += ["--memory", bench["memory"]]
    cmd += ["--stop-timeout", str(bench.get("stop_timeout", 60))]
    for dev in bench.get("serial", []):
        cmd += ["--device", dev]
    return shlex.join(cmd + [image, *args])


print(docker_run({"cpus": 4, "memory": "6g", "stop_timeout": 120}, "wifi-tests:1.4.1", ["-k", "rvr and 6g"]))""",
        },
        {
            "level": "Hard",
            "prompt": "Parse a multi-stage Dockerfile and list each stage with its base image and which earlier stages it copies from (`COPY --from=...`).",
            "solution": "Track the current stage on each FROM (with optional `AS name`) and record COPY --from references.",
            "solution_code": """import re

DOCKERFILE = '''FROM python:3.12-slim-bookworm AS deps
COPY requirements.lock .
RUN pip install --prefix=/install -r requirements.lock
FROM python:3.12-slim-bookworm AS runtime
COPY --from=deps /install /usr/local
COPY . /opt/wifi-tests
FROM runtime AS debug
RUN pip install ipdb'''

stages, current = {}, None
for line in DOCKERFILE.splitlines():
    if m := re.match(r"FROM (\\S+)(?: AS (\\S+))?", line, re.I):
        current = m[2] or f"stage{len(stages)}"
        stages[current] = {"base": m[1], "copies_from": []}
    elif m := re.match(r"COPY --from=(\\S+)", line):
        stages[current]["copies_from"].append(m[1])
for name, info in stages.items():
    print(name, info)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Why run tests in Docker?", "a": "Reproducible environments: the same Python, packages and tools (tshark, iperf3) on every CI agent, bench PC and laptop; easy rollback to a previous image; isolation between suites with conflicting dependencies.", "follow": "What's harder in containers for lab tests? (Hardware access: networks, serial devices, raw sockets.)"},
        {"level": "Intermediate", "q": "How do you make Docker builds fast?", "a": "Order layers by change frequency (system packages, then dependencies, then source), copy only the lock file before installing deps, use .dockerignore, use BuildKit cache mounts, and multi-stage builds to keep runtime images small.", "follow": "What invalidates a COPY layer? (Any change in the copied files' content.)"},
        {"level": "Intermediate", "q": "Container needs to capture packets and reach DUTs. What flags?", "a": "--network host (or a macvlan on the lab VLAN), --cap-add NET_RAW/NET_ADMIN for capture and raw sockets, --device for serial consoles, and avoid --privileged unless truly necessary.", "follow": "Why avoid --privileged? (It gives the container nearly full host access.)"},
        {"level": "Advanced", "q": "Exec form vs shell form for ENTRYPOINT?", "a": "Exec form runs the process directly as PID 1 so it receives signals (SIGTERM from docker stop/CI cancel) and can clean up; shell form wraps it in /bin/sh -c, which doesn't forward signals, so the process is killed after the timeout without cleanup.", "follow": "What about zombie processes? (Use --init or tini as PID 1 when the process spawns children.)"},
    ],
    "quiz": [
        {"q": "Put `COPY . .` ...", "options": ["First", "After dependency install", "Before FROM", "Never"], "answer": 1, "why": "Keeps the dependency layer cached."},
        {"q": "Clean apt lists in...", "options": ["A later RUN", "The same RUN as install", "The CMD", "docker-compose"], "answer": 1, "why": "Later layers can't shrink earlier ones."},
        {"q": "Signals reach pytest when CMD is...", "options": ["Shell form", "Exec form [\"...\"]", "Either", "Neither"], "answer": 1, "why": "No intermediate shell."},
        {"q": "Keep .git and pcaps out of the build:", "options": [".gitignore", ".dockerignore", "VOLUME", "WORKDIR"], "answer": 1, "why": "Build context filter."},
        {"q": "Raw-socket capture in a container needs...", "options": ["--privileged only", "--cap-add NET_RAW", "-p 80", "--rm"], "answer": 1, "why": "Specific capability."},
    ],
    "cards": [
        {"front": "Layer order", "back": "OS packages → lock file + deps → source → USER"},
        {"front": "apt in Docker", "back": "`apt-get update && apt-get install -y --no-install-recommends ... && rm -rf /var/lib/apt/lists/*`"},
        {"front": "Non-root", "back": "`RUN useradd ... && USER tester`"},
        {"front": "Lab hardware flags", "back": "`--network host --device /dev/ttyUSB0 --cap-add NET_RAW`"},
        {"front": "Shell-safe command", "back": "`shlex.join(cmd_list)`"},
    ],
}


COMPOSE = '''services:
  results-db:
    image: postgres:16.4
    environment:
      POSTGRES_DB: results
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets: [db_password]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d results"]
      interval: 5s
      retries: 10
    volumes: [db-data:/var/lib/postgresql/data]
  sim-devices:
    build: ./sim
    healthcheck:
      test: ["CMD", "python", "-c", "import socket; socket.create_connection(('localhost', 2222), 2)"]
      interval: 3s
  tests:
    build: .
    depends_on:
      results-db: {condition: service_healthy}
      sim-devices: {condition: service_healthy}
    environment:
      BENCH: ${BENCH:-lab-07}
      FIRMWARE: ${FIRMWARE:?set FIRMWARE to the build under test}
      DB_URL: postgresql://postgres@results-db/results
    volumes: ["./results:/results"]
  dashboard:
    image: grafana/grafana:11.2.0
    depends_on: [results-db]
    ports: ["3000:3000"]
    profiles: [ui]
volumes:
  db-data: {}
secrets:
  db_password:
    file: ./secrets/db_password.txt
'''

M_8_4 = {
    "id": "8.4",
    "title": "docker compose",
    "hours": 1.5,
    "summary": "Run the test runner together with its supporting services (results database, simulators, dashboard) using one compose file: dependencies with health checks, variables, secrets, volumes and profiles.",
    "concepts": [
        {
            "title": "A compose file for tests, simulators and results",
            "runner": "none",
            "lang": "YAML",
            "filename": "compose.yaml",
            "concept": "`compose.yaml` declares **services** (containers), how they depend on each other, their environment, volumes, secrets and ports. `depends_on` with `condition: service_healthy` makes the test runner wait until the database's **healthcheck** passes. `${VAR:-default}` and `${VAR:?message}` interpolate variables from the shell or an `.env` file, and **profiles** keep optional services (like a dashboard) out of normal runs.",
            "why": "A CI job, a developer laptop and a bench PC can all run `docker compose run tests` and get the same database, the same device simulators and the same runner, wired together correctly, with one command.",
            "syntax": "FIRMWARE=7.4.1 docker compose run --rm tests -m smoke\ndocker compose --profile ui up -d\ndocker compose down -v",
            "code": """services:  ## Each key below is one container
  results-db:  ## Stores test results
    image: postgres:16.4  ## Pinned image
    environment:  ## Container environment
      POSTGRES_DB: results  ## Database created on first start
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password  ## Password read from a mounted secret file
    secrets: [db_password]  ## Mount the secret defined at the bottom
    healthcheck:  ## How compose knows the DB is ready, not just started
      test: ["CMD-SHELL", "pg_isready -U postgres -d results"]  ## Exit code 0 = healthy
      interval: 5s  ## Check every 5 seconds
      retries: 10  ## Unhealthy after 10 failures
    volumes: [db-data:/var/lib/postgresql/data]  ## Named volume: data survives container restarts
  sim-devices:  ## The device simulators from Phase 7, as a service
    build: ./sim  ## Built from a local Dockerfile
    healthcheck:  ## Ready when the SSH port accepts connections
      test: ["CMD", "python", "-c", "import socket; socket.create_connection(('localhost', 2222), 2)"]  ## Exec form check
      interval: 3s  ## Check often
  tests:  ## The test runner image from 8.3
    build: .  ## Built from the repo's Dockerfile
    depends_on:  ## Start order AND readiness
      results-db: {condition: service_healthy}  ## Wait for the healthcheck, not just the container
      sim-devices: {condition: service_healthy}  ## Same for the simulators
    environment:  ## Settings for the run
      BENCH: ${BENCH:-lab-07}  ## Use $BENCH, or lab-07 if unset
      FIRMWARE: ${FIRMWARE:?set FIRMWARE to the build under test}  ## Refuse to start without it
      DB_URL: postgresql://postgres@results-db/results  ## Service names are DNS names on the compose network
    volumes: ["./results:/results"]  ## Bind mount: JUnit XML lands in the repo's results/
  dashboard:  ## Optional Grafana
    image: grafana/grafana:11.2.0  ## Pinned
    depends_on: [results-db]  ## Short form: start order only
    ports: ["3000:3000"]  ## Host port 3000 -> container port 3000
    profiles: [ui]  ## Only started with --profile ui
volumes:  ## Named volumes managed by Docker
  db-data: {}  ## Default settings
secrets:  ## Secrets mounted under /run/secrets/
  db_password:  ## Name used by services
    file: ./secrets/db_password.txt  ## Not committed (.gitignore)""",
            "under": "Compose creates one network per project, and each service is reachable by its name, which is why `results-db` works as a hostname. Without a condition, `depends_on` only orders container *starts*; a database container is 'started' seconds before it accepts connections. Secrets appear as files under `/run/secrets/` rather than environment variables, so they don't show up in `docker inspect` or process listings.",
            "gotchas": [],
            "best": "Health checks on every dependency, `service_healthy` conditions, required variables with `:?`, secrets as files, named volumes for data, profiles for optional tools, and `docker compose down -v` in CI cleanup so runs don't share state.",
        },
        {
            "title": "Reading the compose model from Python",
            "local_only": YAML,
            "files": {"compose.yaml": COMPOSE},
            "concept": "A compose file is plain YAML, so Python can check it in CI: compute the **start order** from `depends_on` with `graphlib.TopologicalSorter`, resolve `${VAR:-default}` / `${VAR:?msg}` interpolation the way compose does, and flag dependencies that only wait for start rather than health.",
            "why": "Catching a missing health condition or an unset required variable in a 2-second lint step beats discovering it as a flaky 'connection refused' 10 minutes into a nightly run.",
            "syntax": "spec = yaml.safe_load(open(\"compose.yaml\"))\nTopologicalSorter({svc: deps}).static_order()",
            "code": """import os  ## Environment for interpolation
import re  ## ${...} patterns
from graphlib import TopologicalSorter  ## Dependency ordering (standard library)

import yaml  ## pip install pyyaml

spec = yaml.safe_load(open("compose.yaml"))  ## The compose file as dicts and lists (see supporting files)
services = spec["services"]  ## name -> definition


def deps(svc):  ## depends_on comes in two shapes: list or mapping with conditions
    d = svc.get("depends_on", [])  ## Missing means none
    return {name: "service_started" for name in d} if isinstance(d, list) else {k: v["condition"] for k, v in d.items()}  ## Normalise


graph = {name: set(deps(svc)) for name, svc in services.items()}  ## service -> services it needs first
print("start order:", list(TopologicalSorter(graph).static_order()))  ## Dependencies before dependants
for name, svc in services.items():  ## Readiness check
    for dep, cond in deps(svc).items():  ## Each dependency
        if cond != "service_healthy":  ## Only waits for the container to start
            print(f"warning: {name} -> {dep} waits for start, not health")  ## Possible race


def interpolate(value, env):  ## Compose-style ${VAR}, ${VAR:-default}, ${VAR:?error}
    def sub(m):  ## Replace one ${...}
        name, op, arg = m.group(1), m.group(2), m.group(3)  ## Pieces of the expression
        if env.get(name):  ## Set and non-empty
            return env[name]  ## Use it
        if op == ":?":  ## Required
            raise ValueError(f"{name}: {arg}")  ## Same idea as compose's error
        return arg or ""  ## Default, or empty
    return re.sub(r"\\$\\{(\\w+)(?:(:-|:\\?)([^}]*))?\\}", sub, value)  ## Every ${...} in the string


env = {k: str(v) for k, v in services["tests"]["environment"].items()}  ## The runner's environment block
for shell_env in ({"FIRMWARE": "7.4.1"}, {}):  ## A CI job that sets FIRMWARE, and one that forgot
    try:  ## Resolve every variable
        print({k: interpolate(v, shell_env) for k, v in env.items()})  ## Effective environment
    except ValueError as e:  ## Required variable missing
        print("compose would refuse to start:", e)  ## Fail before any container starts""",
            "under": "`TopologicalSorter` raises `CycleError` if services depend on each other in a loop, which compose also rejects. `yaml.safe_load` only builds plain Python types (no arbitrary objects), which is the right choice for any config file. Compose itself also reads a `.env` file next to the compose file for interpolation; shell variables take precedence over it.",
            "gotchas": [
                {
                    "title": "depends_on without a health condition",
                    "note": "Plain `depends_on` starts the runner as soon as the database *container* starts, typically seconds before PostgreSQL accepts connections, so the first test fails with connection refused, sometimes. The timeline shows both behaviours.",
                    "wrong": """READY_AT = {"results-db": 8.0, "sim-devices": 3.0}
STARTED_AT = {"results-db": 0.5, "sim-devices": 0.4}
start_tests = max(STARTED_AT.values())
print(f"tests start at {start_tests}s; db ready: {start_tests >= READY_AT['results-db']}")""",
                    "fixed": """READY_AT = {"results-db": 8.0, "sim-devices": 3.0}
STARTED_AT = {"results-db": 0.5, "sim-devices": 0.4}
start_tests = max(READY_AT.values())
print(f"tests start at {start_tests}s; db ready: {start_tests >= READY_AT['results-db']}")""",
                },
            ],
            "best": "Lint compose files in CI (`docker compose config` validates and prints the resolved model; small Python checks add house rules), require health conditions for anything the tests connect to, and make the test runner itself retry its first connection briefly anyway.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Use graphlib to get a start order for: tests needs db and sims; sims needs license-server; dashboard needs db.",
            "solution": "A dict of service → dependencies; static_order yields a valid order.",
            "solution_code": """from graphlib import TopologicalSorter

graph = {"tests": {"db", "sims"}, "sims": {"license-server"}, "dashboard": {"db"}, "db": set(), "license-server": set()}
order = list(TopologicalSorter(graph).static_order())
print(order)
print(all(order.index(d) < order.index(s) for s, ds in graph.items() for d in ds))""",
        },
        {
            "level": "Medium",
            "prompt": "Show what happens with a dependency cycle (sims needs tests, tests needs sims).",
            "solution": "TopologicalSorter raises CycleError and reports the cycle.",
            "solution_code": """from graphlib import CycleError, TopologicalSorter

try:
    list(TopologicalSorter({"tests": {"sims"}, "sims": {"tests"}}).static_order())
except CycleError as e:
    print("CycleError:", e.args[1])""",
        },
        {
            "level": "Hard",
            "local_only": YAML,
            "files": {"compose.yaml": COMPOSE},
            "prompt": "Implement compose-style override merging: merge a `compose.override.yaml` (as a dict) into the base so mappings merge recursively, and lists like `ports` are replaced. Show the effective `tests` service.",
            "solution": "Recursive dict merge where the override wins for scalars and lists. (Real compose has a few special cases, e.g. some lists are merged; `docker compose config` shows the true result.)",
            "solution_code": """import yaml


def merge(base, over):
    out = dict(base)
    for k, v in over.items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


base = yaml.safe_load(open("compose.yaml"))
override = {"services": {"tests": {"environment": {"BENCH": "lab-12", "LOG_LEVEL": "DEBUG"},
                                   "volumes": ["./results-debug:/results"]}}}
eff = merge(base, override)["services"]["tests"]
print(eff["environment"])
print(eff["volumes"])""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What is docker compose for?", "a": "Defining and running multi-container setups declaratively: services, networks, volumes, secrets and dependencies in one YAML file, started and stopped together.", "follow": "How do containers find each other? (By service name on the project network.)"},
        {"level": "Intermediate", "q": "Why does depends_on not guarantee a service is ready?", "a": "By default it only orders container starts. Readiness requires a healthcheck on the dependency and condition: service_healthy (or the client retrying).", "follow": "What does a good healthcheck test? (The actual protocol: pg_isready, an HTTP /health endpoint, an SSH banner.)"},
        {"level": "Intermediate", "q": "How do you pass secrets to compose services?", "a": "Compose secrets mounted as files under /run/secrets, or env files that aren't committed. Avoid literal values in compose.yaml, and prefer *_FILE variables when images support them.", "follow": "Why files over environment variables? (Env vars leak via inspect, logs and child processes.)"},
    ],
    "quiz": [
        {"q": "Wait for a dependency's healthcheck:", "options": ["depends_on: [db]", "condition: service_healthy", "restart: always", "links"], "answer": 1, "why": "Readiness, not just start."},
        {"q": "`${FIRMWARE:?msg}` when unset...", "options": ["Empty string", "Error, compose won't start", "Default 'msg'", "Ignored"], "answer": 1, "why": "Required variable."},
        {"q": "Only start a service when asked:", "options": ["deploy", "profiles", "scale: 0", "extends"], "answer": 1, "why": "--profile name."},
        {"q": "Reach the DB from the tests container at...", "options": ["localhost", "results-db", "127.0.0.1:5432", "host.docker.internal"], "answer": 1, "why": "Service name DNS."},
        {"q": "Remove containers AND named volumes:", "options": ["docker compose stop", "docker compose down -v", "docker rm", "docker compose rm"], "answer": 1, "why": "-v removes volumes."},
    ],
    "cards": [
        {"front": "Run tests once", "back": "`docker compose run --rm tests -m smoke`"},
        {"front": "Readiness", "back": "healthcheck + `depends_on: {db: {condition: service_healthy}}`"},
        {"front": "Variables", "back": "`${VAR:-default}`, `${VAR:?required message}`, `.env` file"},
        {"front": "Optional services", "back": "`profiles: [ui]` → `--profile ui`"},
        {"front": "See resolved config", "back": "`docker compose config`"},
    ],
}


M_8_5 = {
    "id": "8.5",
    "title": "Jenkins Declarative Pipelines",
    "hours": 2.5,
    "summary": "A Jenkinsfile for a Wi-Fi test suite: agents and labels, parameters, stages, parallel branches, timeouts, credentials, always-publish post actions; and triggering and following Jenkins jobs from Python.",
    "concepts": [
        {
            "title": "A Jenkinsfile, line by line",
            "runner": "none",
            "lang": "Groovy",
            "filename": "Jenkinsfile",
            "concept": "A declarative pipeline lives in a `Jenkinsfile` in the repo. `agent { label ... }` picks where it runs (a bench-attached node), `parameters` become build inputs, `options` set timeouts and log timestamps, `environment` injects variables and credentials, `stages` run in order (with `parallel` branches inside), and `post` blocks run **after** the stages: `always` for publishing results and cleanup, `failure`/`unstable` for notifications.",
            "why": "The pipeline is the contract between the test framework and the lab: which bench, which firmware, which suite, how results get published. Kept in the repo, it's reviewed and versioned like the tests themselves.",
            "syntax": "pipeline {\n  agent { label 'wifi-bench' }\n  stages { stage('Test') { steps { sh 'pytest ...' } } }\n  post { always { junit 'results/*.xml' } }\n}",
            "code": """pipeline {  ## Declarative pipeline root
    agent { label 'wifi-bench && 6ghz' }  ## Run on a node that has BOTH labels (a 6 GHz-capable bench PC)
    parameters {  ## Shown as a form on "Build with Parameters"
        string(name: 'FIRMWARE', defaultValue: '7.4.1', description: 'AP build under test')  ## Text input
        choice(name: 'SUITE', choices: ['smoke', 'regression', 'rvr'], description: 'pytest marker to run')  ## Dropdown
    }  ## End of parameters
    options {  ## Pipeline-wide settings
        timeout(time: 3, unit: 'HOURS')  ## Kill the whole run if it hangs
        timestamps()  ## Prefix every console line with time
        buildDiscarder(logRotator(numToKeepStr: '60'))  ## Keep the last 60 builds
        disableConcurrentBuilds()  ## One run at a time on this job (one bench)
    }  ## End of options
    environment {  ## Variables for every step
        BENCH = 'lab-07'  ## Plain value
        LAB = credentials('lab07-ssh')  ## Username/password credential: sets LAB_USR and LAB_PSW, masked in logs
    }  ## End of environment
    stages {  ## Run in order; a failed stage skips the rest
        stage('Setup') {  ## Prepare a clean environment
            steps {  ## Commands in this stage
                sh 'python3 -m venv .venv && .venv/bin/pip install -q -r requirements.lock'  ## Isolated deps per build
            }  ## End of steps
        }  ## End of stage
        stage('Lint') {  ## Fast checks first: fail in seconds, not hours
            steps { sh '.venv/bin/ruff check . && .venv/bin/mypy src' }  ## Code quality gate
        }  ## End of stage
        stage('Flash & sanity') {  ## Put the firmware on the DUT
            steps { sh ".venv/bin/python -m lab.flash --bench ${BENCH} --firmware ${params.FIRMWARE}" }  ## Double quotes so Groovy interpolates
        }  ## End of stage
        stage('Tests') {  ## Independent groups in parallel
            parallel {  ## Branches run at the same time
                stage('Functional') {  ## Branch 1
                    steps { sh ".venv/bin/pytest -m '${params.SUITE} and not rf' --junitxml=results/functional.xml" }  ## Non-RF tests
                }  ## End of branch
                stage('Parsers') {  ## Branch 2
                    steps { sh '.venv/bin/pytest tests/unit --junitxml=results/unit.xml' }  ## No hardware needed
                }  ## End of branch
            }  ## End of parallel
        }  ## End of stage
    }  ## End of stages
    post {  ## Runs after the stages, whatever happened
        always {  ## Every time
            junit allowEmptyResults: true, testResults: 'results/*.xml'  ## Publish test results (failing tests mark the build UNSTABLE)
            archiveArtifacts artifacts: 'results/**, logs/**', allowEmptyArchive: true  ## Keep logs, pcaps, charts
            sh '.venv/bin/python -m lab.reset --bench ${BENCH} || true'  ## Leave the bench clean even if tests failed
        }  ## End of always
        failure { echo 'Infrastructure failure: check the Setup/Flash stages' }  ## Red build: pipeline itself broke
        unstable { echo 'Tests failed: see the Test Results page' }  ## Yellow build: tests ran, some failed
    }  ## End of post
}  ## End of pipeline""",
            "under": "Jenkins runs `sh` steps on the agent and fails the stage on a non-zero exit code; the `junit` step marks the build UNSTABLE (yellow) when the XML contains failures, which separates 'tests found bugs' from 'the pipeline broke' (FAILURE, red). Single-quoted Groovy strings are passed literally (the shell expands `${BENCH}` from the environment), double-quoted ones are interpolated by Groovy first, which matters for secrets: never interpolate credentials in Groovy strings.",
            "gotchas": [
                {
                    "title": "Publishing results only when tests pass",
                    "runner": "none",
                    "note": "If `junit` sits in the test stage after `sh 'pytest ...'`, a failing test makes `sh` return non-zero, the stage stops, and results are never published: you get a red build and no test report, exactly when you need it most. Publish in `post { always { ... } }`. (Some teams also run pytest with `|| true` and let `junit` decide the build status.)",
                    "wrong": """stage('Tests') {
    steps {
        sh 'pytest -m smoke --junitxml=results/junit.xml'
        junit 'results/junit.xml'
    }
}""",
                    "fixed": """stage('Tests') {
    steps {
        sh 'pytest -m smoke --junitxml=results/junit.xml'
    }
}
post {
    always {
        junit allowEmptyResults: true, testResults: 'results/junit.xml'
    }
}""",
                },
            ],
            "best": "Keep the Jenkinsfile thin (call Python entry points for real logic), fail fast with cheap stages first, set timeouts, use labels to target bench capabilities, publish results and artifacts in `post { always }`, reset the bench in `always`, and keep credentials in the credentials store with single-quoted `sh` strings.",
        },
        {
            "title": "Triggering and following Jenkins jobs from Python",
            "files": sim("fake_jenkins.py"),
            "local_only": JENKINS,
            "concept": "Jenkins has a REST API: `POST /job/<name>/buildWithParameters?FIRMWARE=...` queues a build and returns a **queue item** URL in the `Location` header; polling `<queue item>/api/json` reveals the build number once an executor picks it up; polling `/job/<name>/<n>/api/json` shows `building` and `result`; and `/testReport/api/json` returns the test results. Authenticate with a user and **API token** (HTTP basic auth). The server here simulates those endpoints.",
            "why": "Release tooling, a firmware build system or a nightly orchestrator often needs to start a test job on a specific bench and wait for its verdict. A small client with polling and timeouts does this reliably.",
            "syntax": "r = s.post(f\"{JENKINS}/job/{job}/buildWithParameters\", params=params)\nqueue_url = r.headers[\"Location\"]\nbuild = s.get(queue_url + \"api/json\").json()[\"executable\"]",
            "code": """import os  ## Credentials from the environment
import time  ## Polling

import requests  ## pip install requests

from fake_jenkins import start  ## Simulated Jenkins API (see supporting files)

JENKINS = start()  ## https://jenkins.lab.example in real life
s = requests.Session()  ## Reused connection
s.auth = (os.environ.get("JENKINS_USER", "ci-bot"), os.environ.get("JENKINS_TOKEN", "11a2b3c4d5e6f7a8b9c0"))  ## User + API token (never a password)


def poll(url, done, interval=0.05, timeout=30):  ## GET url until done(json) returns something truthy
    deadline = time.monotonic() + timeout  ## Monotonic deadline
    while time.monotonic() < deadline:  ## Keep polling
        data = s.get(url, timeout=10).json()  ## Current state
        if result := done(data):  ## Finished?
            return result  ## Whatever the check extracted
        time.sleep(interval)  ## Seconds to minutes in real life
    raise TimeoutError(url)  ## Give up clearly


r = s.post(f"{JENKINS}/job/wifi-regression/buildWithParameters", params={"FIRMWARE": "7.4.2-rc1", "SUITE": "rvr"}, timeout=10)  ## Queue a build
r.raise_for_status()  ## 201 Created
queue = r.headers["Location"]  ## Where to follow the queued item
print("queued:", queue.rsplit("/queue/", 1)[1])  ## e.g. item/101/

build = poll(queue + "api/json", lambda q: q["executable"])  ## Wait until an executor starts it
print("started build", build["number"])  ## The build number
info = poll(build["url"] + "api/json", lambda b: None if b["building"] else b)  ## Wait until it finishes
params = {p["name"]: p["value"] for p in info["actions"][0]["parameters"]}  ## What it ran with
print("result:", info["result"], "| params:", params, "| minutes:", info["duration"] // 60000)  ## Verdict

report = s.get(build["url"] + "testReport/api/json", timeout=10).json()  ## Test results
print(f"passed {report['passCount']}, failed {report['failCount']}, skipped {report['skipCount']}")  ## Summary
for case in report["suites"][0]["cases"]:  ## Failed cases with their messages
    if case["status"] in ("FAILED", "REGRESSION"):  ## REGRESSION = newly failing since last build
        print(f"  {case['name']}: {case['errorDetails']}")  ## What to look at""",
            "under": "A queued build has no number until an executor takes it, hence the two-step poll (queue item, then build). `REGRESSION` in Jenkins test reports means the test passed in the previous build and fails now; `FAILED` means it was already failing. With an API token, Jenkins doesn't require a CSRF crumb for POST requests.",
            "gotchas": [],
            "best": "Use API tokens from a secret store, poll with deadlines and back-off, record the build URL in your own logs, and use the test report API (or the JUnit XML artifact) rather than scraping console logs. The `python-jenkins` package wraps these endpoints if you prefer a library.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "runner": "none",
            "prompt": "Add a `retry(2)` around the flash step and a 20-minute timeout on just the Tests stage.",
            "solution": "`retry` and `timeout` are steps (inside `steps`) or stage options; stage-level `options { timeout(...) }` bounds the whole stage.",
            "solution_code": """stage('Flash & sanity') {
    steps {
        retry(2) {
            sh ".venv/bin/python -m lab.flash --bench ${BENCH} --firmware ${params.FIRMWARE}"
        }
    }
}
stage('Tests') {
    options { timeout(time: 20, unit: 'MINUTES') }
    steps {
        sh ".venv/bin/pytest -m '${params.SUITE}' --junitxml=results/tests.xml"
    }
}""",
        },
        {
            "level": "Medium",
            "prompt": "Write the Python side of a pipeline step: a CLI that reads a JUnit XML file and exits 0 if all passed, 1 if tests failed (build should go UNSTABLE), and 2 if the file is missing (infrastructure problem), printing a one-line summary.",
            "solution": "Distinct exit codes let the pipeline decide between UNSTABLE and FAILURE (e.g. `catchError` or `unstable()` on exit code 1).",
            "solution_code": """import sys
import xml.etree.ElementTree as ET
from pathlib import Path

Path("junit.xml").write_text('<testsuites><testsuite tests="3" failures="1" errors="0" skipped="0">'
                             '<testcase name="a"/><testcase name="b"><failure message="x"/></testcase><testcase name="c"/>'
                             '</testsuite></testsuites>')


def verdict(path):
    if not Path(path).exists():
        print(f"no results at {path}")
        return 2
    suites = ET.parse(path).getroot().iter("testsuite")
    tests = failed = 0
    for s in suites:
        tests += int(s.get("tests", 0))
        failed += int(s.get("failures", 0)) + int(s.get("errors", 0))
    print(f"{tests} tests, {failed} failed")
    return 1 if failed else 0


print("exit code:", verdict("junit.xml"))
print("exit code:", verdict("missing.xml"))""",
        },
        {
            "level": "Hard",
            "files": sim("fake_jenkins.py"),
            "local_only": JENKINS,
            "prompt": "Show what happens without valid credentials, then wrap trigger-and-wait in a function that returns (result, failed test names) and raises on HTTP errors.",
            "solution": "401 without auth; `raise_for_status` turns it into an exception. The wrapper composes the queue/build/report calls.",
            "solution_code": """import time

import requests
from fake_jenkins import start

J = start()
print("no auth:", requests.post(f"{J}/job/wifi-regression/buildWithParameters", timeout=5).status_code)


def run_job(job, params, auth=("ci-bot", "11a2b3c4d5e6f7a8b9c0")):
    s = requests.Session()
    s.auth = auth
    r = s.post(f"{J}/job/{job}/buildWithParameters", params=params, timeout=10)
    r.raise_for_status()
    q = r.headers["Location"] + "api/json"
    while not (exe := s.get(q, timeout=10).json()["executable"]):
        time.sleep(0.05)
    while (b := s.get(exe["url"] + "api/json", timeout=10).json())["building"]:
        time.sleep(0.05)
    cases = s.get(exe["url"] + "testReport/api/json", timeout=10).json()["suites"][0]["cases"]
    return b["result"], [c["name"] for c in cases if c["status"] in ("FAILED", "REGRESSION")]


print(run_job("wifi-regression", {"FIRMWARE": "7.4.2-rc1", "SUITE": "smoke"}))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Declarative vs scripted pipeline?", "a": "Declarative uses a fixed structure (pipeline/agent/stages/post) that's easier to read, validate and visualise; scripted is full Groovy with more flexibility. Most teams use declarative and put complex logic in shared libraries or Python scripts.", "follow": "Where should test logic live? (In Python, called by the pipeline.)"},
        {"level": "Intermediate", "q": "UNSTABLE vs FAILURE in Jenkins?", "a": "FAILURE (red) means a step failed: the pipeline couldn't complete (infra, flashing, setup). UNSTABLE (yellow) usually means tests ran and some failed, set by the junit step. Keeping them separate tells you whether to look at the product or the lab.", "follow": "How do you make a step mark UNSTABLE instead of FAILURE? (catchError(buildResult: 'UNSTABLE') or unstable().)"},
        {"level": "Intermediate", "q": "How do you handle credentials in Jenkins pipelines?", "a": "Store them in Jenkins credentials (or Vault via a plugin), bind with credentials() or withCredentials, use single-quoted sh strings so Groovy doesn't interpolate them, and rely on masking in logs. Never echo them.", "follow": "Why single quotes? (Groovy interpolation would put the secret in the command string Jenkins logs and warns about.)"},
        {"level": "Advanced", "q": "How would you trigger lab tests from a firmware build pipeline?", "a": "The firmware pipeline uploads the image, then triggers the test job with parameters (build job: 'wifi-regression', parameters: [...], wait: true/false) or via the REST API from an orchestrator; the test job reports results back (status, JUnit) and the firmware pipeline gates promotion on them.", "follow": "Why not run tests inside the firmware pipeline? (Different agents/benches, separate ownership, reuse for other builds.)"},
    ],
    "quiz": [
        {"q": "Always publish JUnit results in...", "options": ["The Test stage", "post { always }", "options", "environment"], "answer": 1, "why": "Runs even after failures."},
        {"q": "`agent { label 'wifi-bench && 6ghz' }` selects...", "options": ["Any node", "Nodes with both labels", "Either label", "The controller"], "answer": 1, "why": "Label expression."},
        {"q": "Build with failing tests (junit step) becomes...", "options": ["FAILURE", "UNSTABLE", "ABORTED", "SUCCESS"], "answer": 1, "why": "Yellow."},
        {"q": "After POST buildWithParameters, the Location header points to...", "options": ["The build", "A queue item", "The console", "The job"], "answer": 1, "why": "Build number comes later."},
        {"q": "Authenticate API calls with...", "options": ["Your password", "An API token", "A cookie", "No auth"], "answer": 1, "why": "Revocable, no CSRF crumb needed."},
    ],
    "cards": [
        {"front": "Pipeline skeleton", "back": "pipeline { agent; parameters; options; environment; stages; post }"},
        {"front": "Always publish", "back": "`post { always { junit 'results/*.xml'; archiveArtifacts ... } }`"},
        {"front": "Credentials", "back": "`LAB = credentials('id')` → LAB_USR / LAB_PSW, single-quoted sh"},
        {"front": "Trigger via REST", "back": "POST /job/X/buildWithParameters → Location: queue item → executable.number"},
        {"front": "Build status", "back": "GET /job/X/N/api/json → building, result; /testReport/api/json"},
    ],
}


SELECT_TESTS = '''"""Map changed files to the pytest marker expression a pipeline should run (test impact analysis)."""
import argparse
import fnmatch
import sys

RULES = [  # (glob, markers to run)
    ("src/lab/attenuator*.py", {"rvr", "roam"}),
    ("src/lab/traffic/*", {"rvr", "throughput"}),
    ("src/lab/parsers/*", {"unit"}),
    ("tests/test_roam*.py", {"roam"}),
    ("requirements.lock", {"smoke", "rvr", "roam", "throughput", "unit"}),
    ("docs/*", set()),
]


def select(changed):
    markers, unmatched = set(), []
    for path in changed:
        hits = [m for pattern, m in RULES if fnmatch.fnmatch(path, pattern)]
        if hits:
            markers.update(*hits)
        else:
            unmatched.append(path)
    if unmatched:
        markers.add("smoke")
    return " or ".join(sorted(markers)) if markers else None, unmatched


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("changed", nargs="*", help="changed file paths (e.g. from git diff --name-only)")
    args = p.parse_args(argv)
    expr, unmatched = select(args.changed)
    if expr is None:
        print("SKIP")
        return 0
    print(expr)
    if unmatched:
        print("unmapped:", ", ".join(unmatched), file=sys.stderr)
    return 0
'''

M_8_6 = {
    "id": "8.6",
    "title": "Advanced Jenkins",
    "hours": 3,
    "summary": "Pipelines that scale across benches: shared libraries, lockable bench resources, matrix builds over bands and firmware, stash/unstash, and moving decision logic into tested Python.",
    "concepts": [
        {
            "title": "Shared library step, bench locks and a matrix",
            "runner": "none",
            "lang": "Groovy",
            "filename": "Jenkinsfile + vars/wifiSuite.groovy",
            "concept": "A **shared library** (a separate repo loaded with `@Library`) holds reusable steps: `vars/wifiSuite.groovy` becomes a `wifiSuite(...)` step usable in every Jenkinsfile. The Lockable Resources plugin's `lock(label: ..., quantity: 1, variable: ...)` reserves one free bench from a pool for the duration of a block, so parallel jobs never share hardware. A `matrix` runs the same stages for every combination of axes (band × security), with `excludes` for impossible ones.",
            "why": "Twenty jobs across five benches need the same setup/test/publish sequence and must never collide on a bench. Shared steps remove copy-paste; locks remove collisions; matrices turn one stage definition into a full compatibility grid.",
            "syntax": "@Library('wifi-ci@v3') _\nlock(label: 'bench-6ghz', quantity: 1, variable: 'BENCH') { ... }\nmatrix { axes { axis { name 'BAND'; values '5G', '6G' } } stages { ... } }",
            "code": """// vars/wifiSuite.groovy (in the shared library repo)  ## File that defines the custom step
def call(Map cfg) {  ## Step entry point: wifiSuite(marker: ..., band: ...)
    lock(label: cfg.pool ?: 'wifi-bench', quantity: 1, variable: 'BENCH') {  ## Wait for one free bench from the pool, name it in env.BENCH
        try {  ## Always reset what we reserved
            sh ".venv/bin/python -m lab.prepare --bench ${env.BENCH} --band ${cfg.band}"  ## Configure the reserved bench
            sh ".venv/bin/pytest -m '${cfg.marker}' --band ${cfg.band} --junitxml=results/${cfg.band}-${cfg.security}.xml"  ## Run the suite
        } finally {  ## Even when tests fail
            sh ".venv/bin/python -m lab.reset --bench ${env.BENCH} || true"  ## Hand the bench back clean
        }  ## End of try/finally
    }  ## Lock released here
}  ## End of step

// Jenkinsfile (in the test repo)  ## The pipeline that uses the step
@Library('wifi-ci@v3') _  ## Load the library at a pinned tag
pipeline {  ## Declarative pipeline
    agent none  ## Each matrix cell picks its own agent
    stages {  ## Top-level stages
        stage('Compatibility grid') {  ## One stage, many cells
            matrix {  ## Cartesian product of the axes
                axes {  ## Dimensions
                    axis { name 'BAND'; values '2G', '5G', '6G' }  ## Bands
                    axis { name 'SECURITY'; values 'wpa2', 'wpa3', 'owe' }  ## Security modes
                }  ## End of axes
                excludes {  ## Impossible combinations
                    exclude {  ## 6 GHz forbids WPA2-only
                        axis { name 'BAND'; values '6G' }  ## When band is 6G...
                        axis { name 'SECURITY'; values 'wpa2' }  ## ...and security is WPA2
                    }  ## End of exclude
                }  ## End of excludes
                agent { label "wifi-runner && ${BAND == '6G' ? '6ghz' : 'any-band'}" }  ## Per-cell agent by capability
                stages {  ## What each cell runs
                    stage('Suite') {  ## Single stage per cell
                        steps { wifiSuite(marker: 'interop', band: BAND, security: SECURITY, pool: "bench-${BAND}") }  ## The shared step
                    }  ## End of stage
                }  ## End of stages
            }  ## End of matrix
        }  ## End of stage
    }  ## End of stages
    post { always { junit allowEmptyResults: true, testResults: 'results/*.xml' } }  ## Publish all cells' results
}  ## End of pipeline""",
            "under": "The library is fetched from SCM at the given version and its `vars/*.groovy` files become global steps. `lock` blocks queue in Jenkins (not on an executor-holding agent if placed before `agent`) until a resource with the label is free; the `variable` gets the resource's name. The matrix above yields 8 cells (3 × 3 minus one exclusion), each scheduled independently.",
            "gotchas": [
                {
                    "title": "Locking the bench for the whole pipeline",
                    "runner": "none",
                    "note": "A `lock` option at pipeline level holds the bench during checkout, venv setup, linting and result upload, often half the run time, while other jobs queue for it. Lock only the stages that touch hardware.",
                    "wrong": """pipeline {
    agent { label 'wifi-runner' }
    options { lock(label: 'bench-6ghz', quantity: 1, variable: 'BENCH') }
    stages {
        stage('Setup') { steps { sh 'python3 -m venv .venv && .venv/bin/pip install -r requirements.lock' } }
        stage('Lint')  { steps { sh '.venv/bin/ruff check .' } }
        stage('RF tests') { steps { sh '.venv/bin/pytest -m rvr --bench $BENCH' } }
    }
}""",
                    "fixed": """pipeline {
    agent { label 'wifi-runner' }
    stages {
        stage('Setup') { steps { sh 'python3 -m venv .venv && .venv/bin/pip install -r requirements.lock' } }
        stage('Lint')  { steps { sh '.venv/bin/ruff check .' } }
        stage('RF tests') {
            options { lock(label: 'bench-6ghz', quantity: 1, variable: 'BENCH') }
            steps { sh '.venv/bin/pytest -m rvr --bench $BENCH' }
        }
    }
}""",
                },
            ],
            "best": "Version the shared library and pin it in each Jenkinsfile, keep library steps small, lock only hardware stages with label-based pools, use matrix excludes for invalid combinations, and keep anything that needs logic or tests (selection, parsing, reporting) in Python.",
        },
        {
            "title": "Decision logic in Python, not Groovy",
            "files": {"select_tests.py": SELECT_TESTS},
            "local_only": FILES,
            "concept": "Pipelines often need decisions: which tests to run for this change, which bench fits this job, whether a result is a regression. Written in Groovy they're hard to test; written as a small Python CLI they get unit tests and run locally. Here `select_tests.py` (supporting files) maps changed file paths to a pytest marker expression; the pipeline would call it with `git diff --name-only origin/main...HEAD` and pass the result to `pytest -m`.",
            "why": "Running the 4-hour RF regression for a docs typo wastes bench time, and skipping it for an attenuator driver change misses regressions. A mapping that's reviewed and tested makes per-PR runs both fast and safe.",
            "syntax": "MARKERS = sh(script: \"python select_tests.py $(git diff --name-only origin/main...HEAD)\", returnStdout: true).trim()\nif (MARKERS != 'SKIP') { sh \"pytest -m '${MARKERS}'\" }",
            "code": """import contextlib  ## Capture what the CLI prints
import io  ## In-memory stdout/stderr

from select_tests import main, select  ## The pipeline helper (see supporting files)

CHANGES = {  ## Pull requests and the files they touched
    "PR 311 attenuator driver": ["src/lab/attenuator_rcdat.py"],  ## RF path code
    "PR 312 docs": ["docs/howto.md"],  ## Nothing to test
    "PR 313 new helper": ["src/lab/new_util.py", "src/lab/parsers/iw.py"],  ## One unmapped file
    "PR 314 dependency bump": ["requirements.lock"],  ## Everything could break
}  ## End of examples
for title, files in CHANGES.items():  ## Decide for each PR
    expr, unmatched = select(files)  ## Pure function: easy to unit-test
    print(f"{title:<26} -> {expr or 'SKIP'}" + (f"  (unmapped: {unmatched})" if unmatched else ""))  ## What the pipeline would run

out, err = io.StringIO(), io.StringIO()  ## Now call it exactly as Jenkins would, through main()
with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):  ## Capture both streams
    code = main(["src/lab/traffic/lanforge.py", "tests/test_roam_11r.py"])  ## argv without the program name
print(repr(out.getvalue().strip()), "| exit", code, "| stderr:", repr(err.getvalue()))  ## stdout is what returnStdout captures""",
            "under": "Unmapped files fall back to the smoke suite, a deliberately safe default: the mapping can be incomplete without silently skipping tests. `main(argv=None)` taking an explicit list is the pattern from Phase 4 that makes CLIs testable without subprocesses; Jenkins' `sh(returnStdout: true)` captures only stdout, which is why diagnostics go to stderr.",
            "gotchas": [],
            "best": "Keep pipeline decisions in small Python CLIs with tests, print machine-readable output on stdout and diagnostics on stderr, fail safe (run more, not less) when unsure, and review the mapping like code.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Expand a Jenkins-style matrix in Python: axes BAND (2G, 5G, 6G) × SECURITY (wpa2, wpa3, owe) minus the exclusion (6G, wpa2); print the cell count and the cells.",
            "solution": "itertools.product over the axes, filtered by the excludes.",
            "solution_code": """from itertools import product

axes = {"BAND": ["2G", "5G", "6G"], "SECURITY": ["wpa2", "wpa3", "owe"]}
excludes = [{"BAND": "6G", "SECURITY": "wpa2"}]
cells = [dict(zip(axes, combo)) for combo in product(*axes.values())]
cells = [c for c in cells if not any(all(c[k] == v for k, v in ex.items()) for ex in excludes)]
print(len(cells))
print([f"{c['BAND']}/{c['SECURITY']}" for c in cells])""",
        },
        {
            "level": "Medium",
            "prompt": "Simulate a lockable-resource pool: 3 jobs need a 6 GHz bench; the pool has bench-03 and bench-07. Show which job gets which bench and who waits, with acquire/release.",
            "solution": "A pool with acquire (first free matching resource or None) and release; jobs that get None wait in the queue.",
            "solution_code": """class Pool:
    def __init__(self, resources):
        self.free = dict(resources)
        self.busy = {}

    def acquire(self, label, job):
        for name, labels in self.free.items():
            if label in labels:
                self.busy[name] = (self.free.pop(name), job)
                return name
        return None

    def release(self, name):
        labels, job = self.busy.pop(name)
        self.free[name] = labels
        return job


pool = Pool({"bench-03": {"6ghz", "5ghz"}, "bench-05": {"5ghz"}, "bench-07": {"6ghz"}})
waiting = []
for job in ["rvr#101", "roam#102", "interop#103"]:
    got = pool.acquire("6ghz", job)
    print(job, "->", got or "waiting")
    if not got:
        waiting.append(job)
print("released by", pool.release("bench-03"))
print(waiting[0], "->", pool.acquire("6ghz", waiting[0]))""",
        },
        {
            "level": "Hard",
            "files": {"select_tests.py": SELECT_TESTS},
            "local_only": FILES,
            "prompt": "Write pytest-style checks (plain asserts are enough here) for `select()`: docs-only changes skip, unmapped files add smoke, the lock file selects everything, and results are deterministic (sorted).",
            "solution": "Because select is pure, its tests are one-liners. Run them on every change to the mapping.",
            "solution_code": """from select_tests import select

assert select(["docs/a.md"]) == (None, [])
expr, unmatched = select(["src/lab/x.py"])
assert expr == "smoke" and unmatched == ["src/lab/x.py"]
assert select(["requirements.lock"])[0] == "roam or rvr or smoke or throughput or unit"
assert select(["tests/test_roam_ft.py", "src/lab/parsers/iw.py"])[0] == "roam or unit"
print("all select() checks passed")""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "How do you stop two Jenkins jobs from using the same bench?", "a": "Lockable Resources: define benches as resources with capability labels, wrap hardware stages in lock(label:..., quantity:1, variable:...), so jobs queue until a matching bench is free; reset the bench in finally before releasing.", "follow": "What if a job crashes holding a lock? (Jenkins releases it when the build ends; add bench health checks on acquire.)"},
        {"level": "Intermediate", "q": "What goes in a shared library vs the Jenkinsfile?", "a": "Shared library: reusable steps (setup, bench reservation, publishing, notifications) versioned and tested once. Jenkinsfile: what this repo runs, with which parameters. Complex logic should be Python called from either.", "follow": "Why pin the library version? (So library changes don't break every pipeline at once.)"},
        {"level": "Advanced", "q": "How would you cut PR validation time on an RF test suite?", "a": "Test impact analysis mapping changed paths to markers, a fast always-run smoke set, running pure-software tests in parallel containers, reserving benches only for RF stages, and running the full RF regression nightly instead of per PR.", "follow": "How do you avoid missing regressions with selective runs? (Fail-safe defaults, nightly full runs, mapping reviews.)"},
    ],
    "quiz": [
        {"q": "`lock(label: 'bench-6ghz', quantity: 1, variable: 'BENCH')` gives...", "options": ["All 6 GHz benches", "One free bench, its name in env.BENCH", "A random node", "A mutex on the job"], "answer": 1, "why": "One resource from the labelled pool."},
        {"q": "Matrix with 3×3 axes and one exclude yields...", "options": ["9", "8", "6", "3"], "answer": 1, "why": "9 - 1."},
        {"q": "Shared library custom steps live in...", "options": ["src/", "vars/<name>.groovy", "resources/", "Jenkinsfile"], "answer": 1, "why": "vars/ defines global steps."},
        {"q": "`sh(returnStdout: true)` captures...", "options": ["stderr", "stdout only", "both", "exit code"], "answer": 1, "why": "Diagnostics belong on stderr."},
        {"q": "Best place for test-selection logic:", "options": ["Groovy in the Jenkinsfile", "A tested Python CLI", "Job config UI", "Shell one-liner"], "answer": 1, "why": "Testable and runnable locally."},
    ],
    "cards": [
        {"front": "Load shared library", "back": "`@Library('wifi-ci@v3') _`"},
        {"front": "Reserve a bench", "back": "`lock(label: 'bench-6ghz', quantity: 1, variable: 'BENCH') { ... }`"},
        {"front": "Matrix", "back": "`matrix { axes {...} excludes {...} stages {...} }`"},
        {"front": "Python from pipeline", "back": "`sh(script: 'python x.py ...', returnStdout: true).trim()`"},
        {"front": "Test impact analysis", "back": "Changed paths → markers; unmapped → smoke (fail safe)"},
    ],
}
