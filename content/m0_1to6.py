"""Phase 0 environment and tooling: Python install, venvs, editor and debugger, git, shell, Jupyter."""


# --------------------------------------------------------------------------- 0.1
CHECK_BASH = '''python3 --version  ## Which Python this shell finds first
which -a python3  ## Every python3 on the PATH, in lookup order
python3 -c "import sys; print(sys.executable)"  ## The exact binary this interpreter runs from'''

CHECK_PY = '''import sys  ## Access to the running interpreter's version
assert sys.version_info >= (3, 10), "Upgrade Python"  ## Fail loudly on an old interpreter
print("Python", sys.version_info.major, "is new enough")  ## Printed only if the check passed'''

M_0_1 = {
    "id": "0.1",
    "title": "Installing Python",
    "hours": 1,
    "summary": "Install a current Python on Windows, macOS or Linux, confirm which interpreter your shell actually runs, and check the version from code before you start the course.",
    "concepts": [
        {
            "title": "Install one Python and confirm which one runs",
            "runner": "none",
            "lang": "Bash",
            "filename": "check.sh",
            "concept": "**Brief:** the course needs Python 3.12 or newer. Most machines have several interpreters (the system one, one from python.org, one from Homebrew or your package manager), and the `python` command may point to a different one from `python3`. Install one current release from python.org, the Microsoft Store, Homebrew (`brew install python`) or your Linux package manager, then check which binary your terminal picks up. **Skills used:** the shell's PATH lookup, `python -c`, `sys.executable`.",
            "why": "Most \"it works on my machine\" problems start with two interpreters on the PATH. A library installed into one is invisible to the other, and tests that pass in your editor fail in CI. Knowing exactly which binary is running removes that whole class of bug.",
            "syntax": "python3 --version\nwhich -a python3",
            "code": CHECK_BASH,
            "under": "The shell searches the directories in `PATH` from left to right and runs the first match. `which -a` lists all matches in that order, so you can see which one wins. On Windows use `where.exe python` in PowerShell or Command Prompt for the same information. `sys.executable` is the ground truth: the interpreter that is actually running your code.",
            "gotchas": [],
            "best": "Use one Python per project (a virtual environment, next lesson), keep the system Python alone, and when a tool misbehaves, print `sys.executable` first.",
        },
        {
            "title": "Check the version from code",
            "concept": "The same check can live in your code. A script that depends on newer syntax or standard-library features should fail immediately with a clear message, not halfway through a test run. This snippet runs right here in the browser, so you can see the check pass.",
            "why": "A clear version assertion at the top of a script or test suite turns a confusing `SyntaxError` on a dict union or `match` statement into a one-line message that tells the next person what to install.",
            "syntax": "sys.version_info >= (3, 10)",
            "code": CHECK_PY,
            "under": "`sys.version_info` is a tuple-like object, so tuple comparison works: `(3, 12, 1) >= (3, 10)` is True because comparison goes element by element. The `assert` statement raises `AssertionError` with your message when the condition is false, and Python skips assertions entirely when run with `-O`, so use an explicit `if` and `raise` for checks that must always run in production code.",
            "gotchas": [],
            "best": "Declare the minimum version once in `pyproject.toml` (`requires-python`) and check it at startup in long-running tools, not in every module.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Find every Python on your machine and note which one `python3` runs. If `python` and `python3` differ, say which one the course should use and why.",
            "solution": "Run `which -a python3` (or `where.exe python` on Windows). The course should use the newest 3.12+ interpreter. Either command works if it points to that interpreter; the important part is consistency: use the same one in your terminal, your editor and your virtual environment.",
            "solution_code": "which -a python3  ## First line is what the shell runs",
            "runner": "none",
        },
        {
            "level": "Medium",
            "prompt": "Explain in two sentences why a script that uses `match` statements gives a `SyntaxError` on Python 3.9, and how the version check above prevents a confusing failure.",
            "solution": "`match` was added in Python 3.10, so an older interpreter cannot parse the file at all, and the error appears before any code runs. A version assertion at the top of the entry point reports the actual problem (\"Upgrade Python\") with the version found, instead of a parser error deep in a stack trace.",
        },
        {
            "level": "Hard",
            "prompt": "Write a function `require_python(minimum)` that raises `RuntimeError` with a message naming the found and required versions, then call it with (3, 10).",
            "solution": "Compare `sys.version_info[:2]` with the minimum tuple; use `raise` rather than `assert` so the check survives `python -O`.",
            "solution_code": """import sys

def require_python(minimum):
    if sys.version_info[:2] < minimum:
        found = ".".join(map(str, sys.version_info[:2]))
        need = ".".join(map(str, minimum))
        raise RuntimeError(f"Python {need}+ required, found {found}")

require_python((3, 10))
print("ok")""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "How do you tell which Python interpreter is running a script?", "a": "Print `sys.executable` and `sys.version` from inside the script, or run `which -a python3` in the shell to see the PATH order. Those two answers together explain most version confusion.", "follow": "Why can `pip install` succeed but the import still fail? (The pip and the interpreter that runs the code belong to different Pythons. Use `python -m pip` to tie them together.)"},
        {"level": "Beginner", "q": "What is the difference between `python` and `python3` on many systems?", "a": "They are separate commands on the PATH and can point to different installations. Virtual environments and `python -m pip` avoid the ambiguity because they name the interpreter explicitly.", "follow": "How do you pin the version for a project? (`requires-python` in `pyproject.toml`, plus a venv built from that interpreter.)"},
    ],
    "quiz": [
        {"q": "Which command shows every python3 on the PATH in lookup order (Linux/macOS)?", "options": ["which -a python3", "pip list", "python3 -m venv", "echo $PYTHON"], "answer": 0, "why": "`which -a` lists all matches."},
        {"q": "Why is an `assert` a weak check in production code?", "options": ["It is slow", "`python -O` removes assertions", "It only works on Windows", "It prints too much"], "answer": 1, "why": "Use `if` plus `raise` for checks that must always run."},
        {"q": "What does `sys.executable` tell you?", "options": ["The script's file name", "The interpreter binary running the code", "The pip version", "The OS name"], "answer": 1, "why": "It is the real interpreter path."},
    ],
    "cards": [
        {"front": "Which Python runs?", "back": "`which -a python3` (Linux/macOS), `where.exe python` (Windows), `sys.executable` in code"},
        {"front": "Version check", "back": "`sys.version_info >= (3, 10)`; use `raise` not `assert` for must-run checks"},
    ],
}


# --------------------------------------------------------------------------- 0.2
VENV_BASH = '''python3 -m venv .venv  ## Create an isolated environment in .venv/
source .venv/bin/activate  ## Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip  ## Use this pip, which belongs to the venv
python -m pip install "requests>=2.31,<3" pytest  ## Install with a version range, not "latest forever"
python -m pip freeze > requirements.txt  ## Record exact versions for the next person
deactivate  ## Leave the environment and return to the system shell'''

REQ_TXT = '''requests==2.32.3  ## Exact pin for reproducible installs
pytest==8.3.3  ## Test runner used by the course
pyyaml>=6,<7  ## A range, when any patch release is fine'''

M_0_2 = {
    "id": "0.2",
    "title": "Virtual Environments & Dependencies",
    "hours": 1.5,
    "summary": "Create a project virtual environment, install dependencies into it safely, record exact versions in requirements.txt, and recreate the environment from that file on another machine.",
    "concepts": [
        {
            "title": "Create, activate and fill a virtual environment",
            "runner": "none",
            "lang": "Bash",
            "filename": "setup.sh",
            "concept": "**Brief:** every project gets its own environment, so its libraries cannot clash with another project's or with the operating system's tools. `python -m venv` creates a folder with its own interpreter and `site-packages`. Activating it puts that interpreter first on the PATH. Install with `python -m pip` so the installer belongs to the same interpreter. **Skills used:** `venv`, `pip`, requirements files, version specifiers.",
            "why": "Installing everything globally works until two projects need different versions of the same library, or until an OS upgrade breaks a tool the system Python depends on. Environments make each project reproducible and keep your machine tidy.",
            "syntax": "python -m venv .venv\nsource .venv/bin/activate\npython -m pip install -r requirements.txt",
            "code": VENV_BASH,
            "under": "A venv does not copy the whole interpreter; it links to the base Python and gives you a private `site-packages`. Activation only changes your shell's PATH and prompt. The scripts in `.venv/bin` also work without activation if you call them by path, which is what editors and CI do. `pip freeze` writes exact versions of everything installed, including indirect dependencies, so keep the requirement lines you wrote by hand separate when you want a short file.",
            "gotchas": [],
            "best": "Put `.venv/` in `.gitignore`, never commit it, recreate it from `requirements.txt` when it breaks, and always run `python -m pip` rather than a bare `pip`.",
        },
        {
            "title": "Requirements files: pins versus ranges",
            "runner": "none",
            "lang": "Text",
            "filename": "requirements.txt",
            "concept": "A requirements file lists what the project needs. An exact pin (`==`) gives identical installs everywhere, which suits CI and benches. A range (`>=`, `<`) lets security patches through while avoiding breaking major releases, which suits libraries you depend on loosely. Real projects often pin in an application's lockfile and use ranges in the library's `pyproject.toml`.",
            "why": "The bench that ran last night and the laptop that runs tests today must agree on the library versions, or a result change is a mystery. Pins make that agreement explicit.",
            "syntax": "package==1.2.3  # exact\npackage>=1.2,<2  # range",
            "code": REQ_TXT,
            "under": "pip resolves all the constraints together and installs one version per package. When two lines conflict, the install fails with a resolver message, which is the signal to loosen one of them. Comments in requirements files start with `#` and are ignored by pip.",
            "gotchas": [],
            "best": "Pin exact versions for anything that runs tests or ships, use ranges for libraries you publish, and upgrade deliberately with a change that updates the pins and runs the full suite.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Create a venv called `.venv` in an empty folder, activate it, and show that `python` now points inside the folder.",
            "solution": "Run `python3 -m venv .venv`, activate it, then `which python` (or `where python` on Windows). The path should be inside `.venv`.",
            "solution_code": "python3 -m venv .venv  ## Create\nsource .venv/bin/activate  ## Activate\nwhich python  ## Should print .../.venv/bin/python",
            "runner": "none",
        },
        {
            "level": "Medium",
            "prompt": "Explain why `pip install requests` in a shell without an active venv can install into a different Python than the one your script runs under.",
            "solution": "`pip` is found by PATH, which may belong to another interpreter, while `python` in the script may be another binary. Using `python -m pip` runs pip from the same interpreter as `python`, so both refer to the same site-packages.",
        },
        {
            "level": "Hard",
            "prompt": "Write the commands to rebuild a broken environment from requirements.txt on a new machine, and a check that the installed `requests` version matches the pin.",
            "solution": "Delete `.venv`, create it again, install from the file, then compare the pinned version with `importlib.metadata.version(\"requests\")` inside the venv. The check below shows the comparison logic with a stand-in for the installed version.",
            "solution_code": """pins = {"requests": "2.32.3", "pytest": "8.3.3"}  ## Read these from requirements.txt
installed = {"requests": "2.32.3", "pytest": "8.2.0"}  ## Stand-in for importlib.metadata.version(name)
for name, pinned in pins.items():
    status = "match" if installed[name] == pinned else f"mismatch: have {installed[name]}"
    print(name, status)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Why use a virtual environment per project?", "a": "Each project gets its own interpreter packages, so versions cannot clash between projects or with the operating system, and the environment can be recreated from a requirements file.", "follow": "What do you commit to git? (requirements or pyproject lockfile, not the .venv folder.)"},
        {"level": "Intermediate", "q": "Pin versions or use ranges?", "a": "Pin exact versions for applications, CI and lab tooling so every run is identical; use ranges in libraries so downstream users can resolve compatible versions with their own dependencies.", "follow": "How do you upgrade safely? (Upgrade one dependency, run the full suite, commit the new pin with a note.)"},
    ],
    "quiz": [
        {"q": "Which command installs into the venv's own interpreter?", "options": ["pip install x", "python -m pip install x", "sudo pip install x", "venv install x"], "answer": 1, "why": "Same interpreter as python."},
        {"q": "What should `.gitignore` contain for a venv?", "options": [".venv/", "requirements.txt", "*.py", "pyproject.toml"], "answer": 0, "why": "Do not commit the environment."},
        {"q": "`requests>=2.31,<3` means...", "options": ["Exactly 2.31", "Any version from 2.31 up to but not including 3", "Any version", "Only 3.x"], "answer": 1, "why": "A range."},
    ],
    "cards": [
        {"front": "Create + activate", "back": "`python3 -m venv .venv` then `source .venv/bin/activate` (PowerShell: `.venv\\Scripts\\Activate.ps1`)"},
        {"front": "Record versions", "back": "`python -m pip freeze > requirements.txt`; rebuild with `-r requirements.txt`"},
    ],
}


# --------------------------------------------------------------------------- 0.3
LAUNCH_JSON = '''{  ## The whole file is one JSON object
  "version": "0.2.0",  ## Schema version of the debug configuration file
  "configurations": [  ## Each entry is one run or debug target
    {  ## One configuration
      "name": "Debug current file",  ## Shown in the Run and Debug panel
      "type": "debugpy",  ## The Python debugger extension
      "request": "launch",  ## Start the program under the debugger
      "program": "${file}",  ## The file currently open in the editor
      "console": "integratedTerminal",  ## Input and output appear in the terminal panel
      "justMyCode": true  ## Step over library code, stay in yours
    }
  ]
}'''

DEBUG_BASH = '''code .  ## Open the current folder in VS Code (macOS/Linux with the shell command installed)
python -m pdb script.py  ## Run a script under the built-in debugger from the terminal
python -X dev script.py  ## Extra runtime checks: warnings, resource and asyncio diagnostics
python -c "import code; code.interact()"  ## Start a plain interactive interpreter with no editor'''

M_0_3 = {
    "id": "0.3",
    "title": "VS Code, Debugger & REPL",
    "hours": 1.5,
    "summary": "Set up VS Code for Python with the interpreter and a debug configuration, step through code with breakpoints, and use the interactive interpreter to try ideas quickly.",
    "concepts": [
        {
            "title": "A debug configuration for VS Code",
            "runner": "none",
            "lang": "JSON",
            "filename": ".vscode/launch.json",
            "concept": "**Brief:** `print` debugging works until the bug lives three function calls deep. VS Code's Python extension (debugpy) runs your script under a debugger so you can set breakpoints, step into functions, and inspect variables. Select your venv interpreter first (Command Palette: \"Python: Select Interpreter\"), then add a launch configuration like this one so \"Run and Debug\" starts the current file with the right settings. **Skills used:** VS Code debugging, `launch.json`, interpreter selection.",
            "why": "Stepping through a real failing run shows the state at each line, which tells you the cause faster than adding ten prints and rerunning. Learning the debugger early saves hours in every later phase.",
            "syntax": "\"request\": \"launch\", \"program\": \"${file}\"",
            "code": LAUNCH_JSON,
            "under": "`${file}` is a VS Code variable replaced with the path of the open file when you press run. `justMyCode` stops the debugger from stepping into the standard library and third-party code, which keeps the stepping focused. The `integratedTerminal` console means `input()` works while debugging.",
            "gotchas": [],
            "best": "Set breakpoints by clicking the gutter, use conditional breakpoints for loops that run thousands of times, and keep one launch configuration per common entry point (CLI, tests, a service).",
        },
        {
            "title": "Terminal debugging, dev mode and the interactive interpreter",
            "runner": "none",
            "lang": "Bash",
            "filename": "terminal.sh",
            "concept": "When no editor is at hand, the same tools work in a terminal. `python -m pdb` runs a script under the standard debugger with commands like `n` (next line), `s` (step in), `p var` (print), and `c` (continue). `python -X dev` enables extra warnings and checks that catch real bugs early. `code.interact()` gives a plain interpreter. The REPL is covered by the same ideas as the interactive prompt you get from `python`.",
            "why": "Remote lab machines and CI runners rarely have an editor. Knowing pdb means you can debug a failing test on the bench over SSH.",
            "syntax": "python -m pdb script.py\n(Pdb) n",
            "code": DEBUG_BASH,
            "under": "pdb is part of the standard library: it reads commands from stdin and stops at the first line, or at a `breakpoint()` call in your code. `breakpoint()` (Python 3.7+) calls `pdb.set_trace()` by default, and the `PYTHONBREAKPOINT` environment variable can turn it off in CI. `-X dev` raises warnings to visible level, which surfaces deprecations early.",
            "gotchas": [],
            "best": "Leave no `breakpoint()` calls in committed code, add `PYTHONBREAKPOINT=0` to CI, and reproduce a failure in pdb before you change the code.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Set a breakpoint in a loop that sums numbers, run it under the debugger, and note the value of `total` after the third iteration.",
            "solution": "Click the gutter next to the `total += n` line, start Debug (F5), and use Continue until the third hit. Hover over `total` or read it in the Variables panel.",
        },
        {
            "level": "Medium",
            "prompt": "Find the bug in a function that should return the mean of a list but returns the wrong value for `[1, 2, 3]`. Use pdb rather than print statements.",
            "solution": "Typical bug: `sum(values) / len(values) + 1` or dividing by a fixed number. Step with `n` through the return line and print `sum(values)` and `len(values)` with `p` to see the wrong operand.",
        },
        {
            "level": "Hard",
            "prompt": "Write a conditional breakpoint to stop only when a loop variable equals 500 in a loop of 1000 iterations, then explain why this is faster than stepping.",
            "solution": "In VS Code, right-click the gutter and choose Add Conditional Breakpoint with `i == 500`. Stepping through 500 iterations manually takes many keypresses; the condition halts only on the one that matters.",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "How do you debug a Python script that gives the wrong result?", "a": "Reproduce it with a minimal input, set a breakpoint before the first wrong value, and step through while checking variables. Use prints only when the debugger is unavailable, such as on a remote machine where pdb still works.", "follow": "What is the difference between step over and step into? (Over runs the line as one unit; into enters the called function.)"},
        {"level": "Beginner", "q": "What does a REPL give you that a script does not?", "a": "Immediate feedback on expressions and objects: you can try a call, inspect its result and build up code interactively without rerunning everything from the start.", "follow": "When would you move code from the REPL into a file? (As soon as it is worth repeating or testing.)"},
    ],
    "quiz": [
        {"q": "In pdb, which command prints a variable?", "options": ["n", "c", "p name", "q"], "answer": 2, "why": "`p` prints an expression."},
        {"q": "`PYTHONBREAKPOINT=0` does what?", "options": ["Stops the interpreter", "Turns breakpoint() into a no-op", "Adds a breakpoint", "Sets the debugger port"], "answer": 1, "why": "Useful in CI."},
        {"q": "`justMyCode: true` in launch.json means...", "options": ["Only Python 3 code runs", "The debugger skips library code when stepping", "Code is formatted", "Tests are skipped"], "answer": 1, "why": "Focus stepping on your code."},
    ],
    "cards": [
        {"front": "pdb commands", "back": "n next, s step in, c continue, p expr print, q quit, l list source"},
        {"front": "Breakpoints", "back": "Gutter click; conditional via right-click; `breakpoint()` in code"},
    ],
}


# --------------------------------------------------------------------------- 0.4
GIT_BASH = '''git init  ## Start tracking this folder as a repository
git add .gitignore README.md src/  ## Stage specific files, not everything
git commit -m "Add project skeleton"  ## Record the staged snapshot with a message
git switch -c feature/rvr-report  ## Create and move to a new branch
git log --oneline --graph --decorate  ## Compact history with branches shown
git diff --staged  ## Review exactly what the next commit will contain
git push -u origin feature/rvr-report  ## Publish the branch and track it upstream'''

GITIGNORE = '''.venv/  ## The virtual environment is local, never shared
__pycache__/  ## Bytecode caches regenerate themselves
*.pyc  ## Compiled files
.pytest_cache/  ## Test runner cache
.env  ## Secrets and local settings stay out of git
reports/  ## Generated test outputs
*.pcap  ## Large captures belong in artifact storage'''

M_0_4 = {
    "id": "0.4",
    "title": "Git Essentials",
    "hours": 2,
    "summary": "Use git for the daily cycle of a Python project: initialise, stage deliberately, commit with clear messages, work on branches, review the diff and publish. Plus a .gitignore that keeps environments and secrets out.",
    "concepts": [
        {
            "title": "The daily cycle: stage, commit, branch, publish",
            "runner": "none",
            "lang": "Bash",
            "filename": "workflow.sh",
            "concept": "**Brief:** git records snapshots of your project. Three ideas cover almost all daily use: the working tree (your files), the staging area (what the next commit will contain), and commits (permanent snapshots). Stage specific files so unrelated edits do not end up together, review with `git diff --staged`, commit with a message that says why, and work on a branch so `main` stays releasable. **Skills used:** init, add, commit, branch, log, diff, push.",
            "why": "Test code changes constantly, and a clean history is how a team finds the commit that broke a KPI. Small, well-described commits make `git bisect` and code review practical.",
            "syntax": "git add <files>\ngit commit -m \"message\"",
            "code": GIT_BASH,
            "under": "`git add` moves changes into the index, which is the staging area. A commit captures the index, not the working tree, so a file you edited but did not stage is not in the commit. Branches are only pointers to commits, so creating one is cheap. `git log --graph` shows how branches diverge and merge.",
            "gotchas": [],
            "best": "Commit small logical changes, write the subject in the imperative (\"Add roam KPI\"), keep the subject under about 72 characters, and never commit directly to `main` in a shared repository.",
        },
        {
            "title": "A .gitignore for Python test projects",
            "runner": "none",
            "lang": "Text",
            "filename": ".gitignore",
            "concept": "A `.gitignore` file tells git which paths to leave untracked. Python projects generate caches, environments and reports that should never be committed, and secrets that must not leak at all. Add the file before your first commit so those files are never tracked.",
            "why": "A committed `.env` file with a lab password is a security incident, and a committed `.venv` bloats the repository and breaks on other machines. The `.gitignore` prevents both.",
            "syntax": "pattern/  # ignore a directory\n*.ext  # ignore by extension",
            "code": GITIGNORE,
            "under": "Patterns are matched relative to the file's folder. A trailing slash matches directories only. Files already tracked stay tracked even when you add them to `.gitignore`; run `git rm --cached <file>` to untrack them.",
            "gotchas": [],
            "best": "Start from GitHub's Python template, commit the `.gitignore` in the first commit, and add secret-scanning as a pre-commit hook for anything that looks like a key.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Create a repository, add a README, commit it, and show the one-line history.",
            "solution": "Run `git init`, create README.md, `git add README.md`, `git commit -m \"Add README\"`, then `git log --oneline`.",
            "solution_code": "git init  ## New repository\ngit add README.md  ## Stage the file\ngit commit -m \"Add README\"  ## First commit\ngit log --oneline  ## One line per commit",
            "runner": "none",
        },
        {
            "level": "Medium",
            "prompt": "You edited three files but only one is ready to commit. Show how to commit just that one, and check what was committed.",
            "solution": "Stage only the ready file with `git add path/to/file.py`, check with `git diff --staged`, commit, then `git status` shows the other two still modified.",
        },
        {
            "level": "Hard",
            "prompt": "A `.env` file with a password was committed last week. Remove it from future commits and explain why deleting it in a new commit is not enough.",
            "solution": "Add `.env` to `.gitignore`, run `git rm --cached .env`, commit. Deleting it in a new commit leaves the secret in history, so rotate the password and rewrite history with `git filter-repo` if the repository is shared.",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What is the difference between `git add` and `git commit`?", "a": "`git add` stages changes into the index, which prepares the next snapshot; `git commit` records that snapshot permanently in history with a message.", "follow": "How do you undo a staged file? (`git restore --staged <file>`.)"},
        {"level": "Intermediate", "q": "How do you find the commit that introduced a bug?", "a": "Use `git bisect` between a known good and a known bad commit, optionally with a script that returns an exit code, to binary-search the history.", "follow": "Why do small commits help? (Bisect and review both work on small, single-purpose changes.)"},
    ],
    "quiz": [
        {"q": "What does `git add` do?", "options": ["Creates a commit", "Stages changes for the next commit", "Pushes to the remote", "Creates a branch"], "answer": 1, "why": "Staging, then commit."},
        {"q": "Why ignore `.venv/`?", "options": ["It is slow to commit", "It is machine-specific and can be rebuilt", "Git cannot read it", "It contains tests"], "answer": 1, "why": "Recreate from requirements."},
        {"q": "What does `git switch -c name` do?", "options": ["Deletes a branch", "Creates and switches to a new branch", "Renames a commit", "Shows the log"], "answer": 1, "why": "Create plus switch."},
    ],
    "cards": [
        {"front": "Git's three areas", "back": "Working tree → staging (index) → commit"},
        {"front": "Secret leaked?", "back": "Rotate the secret first; deleting it in a new commit keeps it in history"},
    ],
}


# --------------------------------------------------------------------------- 0.5
SHELL_BASH = '''ls -lh logs/  ## Long listing with human-readable sizes
grep -R "ERROR" logs/ | head -n 5  ## Search every log for errors and show the first five
grep -c "ERROR" logs/ap-lab-07.log  ## Count matching lines in one file
cat logs/*.log | sort | uniq -c | sort -rn | head  ## Most frequent lines across all logs
echo "exit code of last command: $?"  ## 0 means success, anything else means failure
export LAB_BENCH=lab-07  ## Environment variable visible to child programs
python report.py --bench "$LAB_BENCH"  ## The script reads the variable from its environment
chmod +x scripts/run_nightly.sh  ## Make the script executable
crontab -e  ## Edit this user's scheduled jobs'''

SCRIPT_SH = '''#!/usr/bin/env bash  ## Run with bash, wherever bash lives
set -euo pipefail  ## Stop on errors, unset variables and failed pipe stages
BENCH="${1:?usage: run_nightly.sh <bench>}"  ## First argument, required
mkdir -p "reports/$BENCH"  ## Create the output folder if missing
python -m pytest -m smoke --bench "$BENCH" --junitxml="reports/$BENCH/junit.xml"  ## Run the tests and save results
echo "done: $BENCH"  ## Simple progress line for the log'''

M_0_5 = {
    "id": "0.5",
    "title": "Linux Shell for Automation",
    "hours": 1.5,
    "summary": "The shell skills automation relies on: finding and summarising text in logs, pipes and exit codes, environment variables, a safe bash script template, and scheduling with cron.",
    "concepts": [
        {
            "title": "Search, count and summarise logs with pipes",
            "runner": "none",
            "lang": "Bash",
            "filename": "logs.sh",
            "concept": "**Brief:** an overnight run leaves gigabytes of logs across six benches. The shell answers questions in seconds: where are the errors, how many, which lines repeat most. Small tools chained with pipes do the work: each reads text on stdin, transforms it and writes to stdout. **Skills used:** `ls`, `grep`, `head`, `sort`, `uniq`, `cat`, pipes, exit codes, environment variables, `chmod`, `crontab`.",
            "why": "Reading logs by hand does not scale, and a one-line pipeline you can rerun is more trustworthy than a memory of how you found the problem last time.",
            "syntax": "command | command | command",
            "code": SHELL_BASH,
            "under": "Each program in a pipeline runs at the same time, connected through a buffer, so `head` can stop the whole pipeline early. `uniq` only merges adjacent duplicates, which is why the pipeline sorts first. `$?` holds the exit status of the last command; zero means success. `export` puts a variable into the environment, so child programs such as Python see it, while a plain assignment does not.",
            "gotchas": [],
            "best": "Quote variables (`\"$VAR\"`), use `grep -F` for literal strings, pipe through `head` while exploring so output stays small, and turn a pipeline you reuse into a script.",
        },
        {
            "title": "A bash script template that fails loudly",
            "runner": "none",
            "lang": "Bash",
            "filename": "scripts/run_nightly.sh",
            "concept": "A shell script that keeps going after an error is a silent failure generator. The template opens with `set -euo pipefail`, which stops on the first failing command, on unset variables and on failures inside pipes. It checks its arguments and runs the Python tests with a results file, so the CI job can read what happened.",
            "why": "A nightly job that reports success after a failed step wastes a night of bench time and hides the failure from everyone. Fail-fast scripts make failures visible at the moment they happen.",
            "syntax": "set -euo pipefail",
            "code": SCRIPT_SH,
            "under": "`-e` exits on the first non-zero command, `-u` treats an unset variable as an error, and `pipefail` makes a pipeline fail when any stage fails, not only the last. `${1:?message}` aborts with the message when the argument is missing. `#!/usr/bin/env bash` finds bash on the PATH, which matters on systems where it is not in `/bin`.",
            "gotchas": [],
            "best": "Use `set -euo pipefail` in every script, use `shellcheck` to lint scripts, and keep logic that grows beyond about 50 lines in Python.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Count how many ERROR lines each log file has, sorted from most to least.",
            "solution": "Use `grep -c` per file or `grep -c ERROR logs/*.log | sort -t: -k2 -rn`.",
            "solution_code": "grep -c ERROR logs/*.log | sort -t: -k2 -rn  ## Count per file, most errors first",
            "runner": "none",
        },
        {
            "level": "Medium",
            "prompt": "Explain why `false | true; echo $?` prints 0 but the same line under `set -o pipefail` prints 1.",
            "solution": "Without pipefail, a pipeline's status is the status of its last command (`true`, 0). With pipefail, it is the rightmost non-zero status, here from `false`, so the status is 1.",
        },
        {
            "level": "Hard",
            "prompt": "Write a cron line that runs the nightly script at 01:30 every day and appends output to a log file, and explain each field.",
            "solution": "`30 1 * * * /home/lab/scripts/run_nightly.sh lab-07 >> /home/lab/logs/nightly.log 2>&1`. Fields are minute, hour, day of month, month, day of week. `2>&1` sends errors to the same log, and the absolute path avoids depending on the cron environment's PATH.",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What does `set -euo pipefail` do?", "a": "It makes the script exit on the first failing command, on unset variables and on failure of any stage in a pipeline, so errors are not silently ignored.", "follow": "Why is `-e` alone not enough? (It does not catch failures in the middle of a pipeline.)"},
        {"level": "Beginner", "q": "How do you find the most common error messages in a log?", "a": "Filter with `grep`, then `sort | uniq -c | sort -rn | head` to count and rank the repeated lines.", "follow": "Why must you sort before `uniq`? (`uniq` only merges adjacent duplicates.)"},
    ],
    "quiz": [
        {"q": "What does `$?` contain?", "options": ["The script name", "The exit status of the last command", "The PID", "The current directory"], "answer": 1, "why": "0 means success."},
        {"q": "Which command makes a file runnable?", "options": ["chmod +x", "chown", "ln -s", "touch"], "answer": 0, "why": "Adds the execute bit."},
        {"q": "`export VAR=1` differs from `VAR=1` because...", "options": ["It is faster", "Child programs see it", "It is saved to disk", "It is read-only"], "answer": 1, "why": "Environment variables are inherited."},
    ],
    "cards": [
        {"front": "Script header", "back": "`#!/usr/bin/env bash` + `set -euo pipefail`"},
        {"front": "Log triage", "back": "grep → sort → uniq -c → sort -rn → head"},
    ],
}


# --------------------------------------------------------------------------- 0.6
JUPYTER_TXT = '''pip install jupyterlab  ## Install the notebook interface into the active venv
jupyter lab  ## Start the server and open it in the browser
jupyter nbconvert --to script analysis.ipynb  ## Turn a notebook into a plain Python file'''

NOTEBOOK_CELL = '''# Cell 1: load the captured RSSI samples  ## Each cell runs in the same kernel state
samples = [-61, -64, -58, -70, -66]  ## Values in dBm, one per second
# Cell 2: summarise them  ## Uses the variable from cell 1
mean = sum(samples) / len(samples)  ## Average signal strength
print(round(mean, 1))  ## Output appears under the cell
# Cell 3: a magic command  ## Only valid inside Jupyter, not in a .py file
%timeit sorted(samples)  ## Times the expression over many runs'''

M_0_6 = {
    "id": "0.6",
    "title": "Jupyter for Experiments",
    "hours": 0.5,
    "summary": "Use Jupyter notebooks for quick experiments and data exploration, know their state pitfalls, and move finished code into scripts and tests.",
    "concepts": [
        {
            "title": "Install Jupyter and run a notebook",
            "runner": "none",
            "lang": "Bash",
            "filename": "jupyter.sh",
            "concept": "**Brief:** a notebook mixes code, output and prose in one document. It is ideal for trying a parser on a real capture, plotting an RvR curve, or checking a formula before you commit to it. Install JupyterLab into your project's virtual environment so the notebook uses the same libraries as your tests, then convert the notebook to a script when the code is worth keeping.",
            "why": "Exploring data in a notebook is faster than editing and rerunning a script. Keeping it in the project venv avoids the \"works in the notebook but not in pytest\" problem.",
            "syntax": "jupyter lab",
            "code": JUPYTER_TXT,
            "under": "Jupyter starts a local server and a kernel (the Python process) that runs your cells. The kernel is a separate process from the browser, so it keeps variables between cells until you restart it.",
            "gotchas": [],
            "best": "Install Jupyter in the same venv as the project, restart the kernel and run all cells before you share a notebook, and move any function you reuse into a module that tests import.",
        },
        {
            "title": "Cells share state: the hidden-order trap",
            "runner": "none",
            "lang": "Python",
            "filename": "analysis.ipynb",
            "concept": "Cells run in whatever order you click them, and they all share one kernel. A notebook can show results that come from a cell you have since edited or deleted. Keep cells in top-to-bottom order, and use \"Restart and Run All\" before you trust a result. The example below is three cells; the magic command `%timeit` only works in Jupyter.",
            "why": "The most common notebook bug is a number that cannot be reproduced because it depended on a deleted cell. Running everything from a clean kernel catches it.",
            "syntax": "# cell: code\n# output appears below the cell",
            "code": NOTEBOOK_CELL,
            "under": "Each cell is compiled and executed in the shared namespace, so a variable from cell 1 is visible in cell 2 for as long as the kernel lives. Magic commands like `%timeit` start with `%` and are handled by IPython, the interactive shell underneath Jupyter.",
            "gotchas": [],
            "best": "Keep one idea per cell, restart the kernel regularly, and when a result matters, move it into a script with a test.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Start JupyterLab from your project venv, create a notebook, and print the Python version it uses.",
            "solution": "Run `jupyter lab`, create a Python 3 notebook, and run `import sys; print(sys.executable)`. The path should be inside `.venv`.",
            "solution_code": "import sys  ## Standard library module\nprint(sys.executable)  ## Should be inside .venv",
            "runner": "none",
        },
        {
            "level": "Medium",
            "prompt": "Explain why a result in a notebook may not reproduce after a restart, and how to check that it does.",
            "solution": "Variables from cells that were run in a different order, or from deleted cells, persist in the kernel. Use Kernel → Restart and Run All; if the result changes, a hidden dependency existed.",
        },
        {
            "level": "Hard",
            "prompt": "Decide when a notebook should become a script with tests. List three signs.",
            "solution": "Move code when it is run more than a couple of times, when others need to run it, or when its result feeds a decision (a KPI, a release gate). The script should take inputs as arguments and have tests like any other module.",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What is the main risk of using notebooks?", "a": "Hidden state: cells run out of order keep variables alive, so results may not reproduce from a clean start. Restart and run all before trusting or sharing results.", "follow": "How do you test notebook code? (Move functions into a module and test the module with pytest.)"},
        {"level": "Beginner", "q": "When is a notebook the right tool?", "a": "For exploration, quick plots and checking a formula against real data, where fast feedback matters more than repeatability.", "follow": "What comes next once the exploration works? (A function in a module, a test and a script entry point.)"},
    ],
    "quiz": [
        {"q": "Which command converts a notebook to a script?", "options": ["jupyter nbconvert --to script", "jupyter export", "pip notebook", "python -m nb"], "answer": 0, "why": "nbconvert."},
        {"q": "Why does a cell see a variable defined in an earlier cell?", "options": ["Cells are files", "They share the kernel's namespace", "It is a bug", "Jupyter copies variables"], "answer": 1, "why": "Shared kernel state."},
        {"q": "Where should Jupyter be installed for a project?", "options": ["Only globally", "In the project's venv", "In the browser", "In /usr/bin"], "answer": 1, "why": "Same libraries as the tests."},
    ],
    "cards": [
        {"front": "Notebook hygiene", "back": "Restart kernel → Run All before trusting or sharing"},
        {"front": "Notebook → script", "back": "`jupyter nbconvert --to script file.ipynb`"},
    ],
}
