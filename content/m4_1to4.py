"""Phase 4 content: modules 4.1-4.4."""

PROC_NOTE = "starts other processes, which the in-browser runner can't do"
TYPER_NOTE = "needs the typer package (pip install typer)"
PYDANTIC_NOTE = "needs pydantic and pydantic-settings (pip install pydantic-settings)"

M_4_1 = {
    "id": "4.1",
    "title": "Command-Line Interfaces: argparse to typer",
    "hours": 2.5,
    "summary": "Turning scripts into self-documenting lab tools: positional and optional arguments, types and choices, flags, subcommands, exit codes, and the same CLI in typer.",
    "concepts": [
        {
            "title": "argparse: arguments, subcommands and exit codes",
            "concept": "`argparse` (standard library) turns `sys.argv` into a namespace of typed values. `add_argument` defines positionals and options with `type=`, `choices=`, `default=`, `required=` and `action=\"store_true\"` for flags. **Subcommands** (`add_subparsers`) give one tool several verbs, like `git`. Bad input makes argparse print usage and exit with code **2**. Write `main(argv=None) -> int` so the parser can be tested with a list, and end scripts with `sys.exit(main())` so the exit code reaches the shell.",
            "why": "A sweep that is driven by `wifitool sweep --band 5G --channels 36,149 --att-stop 60` can be run by hand, from cron and from Jenkins with exactly the same code, and `--help` documents itself. CI decides pass or fail purely from the exit code.",
            "syntax": "parser = argparse.ArgumentParser(prog=\"wifitool\")\nparser.add_argument(\"--band\", choices=[\"2G\", \"5G\", \"6G\"], required=True)\nparser.add_argument(\"--step\", type=int, default=3)\nparser.add_argument(\"-v\", \"--verbose\", action=\"store_true\")\nsub = parser.add_subparsers(dest=\"command\", required=True)\nargs = parser.parse_args(argv)\n\nif __name__ == \"__main__\":\n    sys.exit(main())",
            "code": """import argparse  ## Standard-library argument parser


def channel_list(text: str) -> list[int]:  ## A custom type: "36,149" -> [36, 149]
    return [int(c) for c in text.split(",")]  ## Raising ValueError here makes argparse report a clean error


def build_parser() -> argparse.ArgumentParser:  ## Build the parser in a function so tests can reuse it
    parser = argparse.ArgumentParser(prog="wifitool", description="Lab Wi-Fi helper")  ## prog fixes the name shown in usage
    parser.add_argument("-v", "--verbose", action="store_true", help="more logging")  ## A flag: False unless given
    sub = parser.add_subparsers(dest="command", required=True)  ## One verb is mandatory
    sweep = sub.add_parser("sweep", help="run an attenuation sweep")  ## Subcommand 1
    sweep.add_argument("--band", choices=["2G", "5G", "6G"], required=True)  ## Only these values are accepted
    sweep.add_argument("--channels", type=channel_list, default=[36])  ## Converted by our custom type
    sweep.add_argument("--att-start", type=int, default=0)  ## Dashes become underscores: args.att_start
    sweep.add_argument("--att-stop", type=int, default=60)  ## Upper bound in dB
    sweep.add_argument("--step", type=int, default=3)  ## Step size in dB
    scan = sub.add_parser("scan", help="scan and list BSSIDs")  ## Subcommand 2
    fmt = scan.add_mutually_exclusive_group()  ## At most one of the following
    fmt.add_argument("--json", action="store_true")  ## Machine-readable output
    fmt.add_argument("--csv", action="store_true")  ## Spreadsheet output
    return parser  ## Ready to parse


def main(argv: list[str] | None = None) -> int:  ## argv=None means "use sys.argv"; tests pass a list
    args = build_parser().parse_args(argv)  ## Parse and validate (exits with code 2 on bad input)
    if args.command == "sweep":  ## Dispatch on the subcommand
        steps = list(range(args.att_start, args.att_stop + 1, args.step))  ## Inclusive sweep points
        print(f"sweep {args.band} channels={args.channels} steps={steps} verbose={args.verbose}")  ## Show the parsed values
    else:  ## The scan subcommand
        print(f"scan format={'json' if args.json else 'csv' if args.csv else 'table'}")  ## Default is a table
    return 0  ## Exit code 0 = success


if __name__ == "__main__":  ## In a real tool: sys.exit(main())
    print(main(["-v", "sweep", "--band", "5G", "--channels", "36,149", "--att-stop", "30", "--step", "10"]))  ## A full sweep command
    print(main(["scan", "--json"]))  ## The other subcommand
    try:  ## Invalid input
        main(["sweep", "--band", "7G"])  ## Not one of the choices
    except SystemExit as exc:  ## argparse printed usage and an error, then exited
        print("exit code:", exc.code)  ## 2 = command-line usage error""",
            "under": "`parse_args` walks the argument list, matches option strings, runs each `type` callable on the text, checks `choices` and required options, and builds an `argparse.Namespace`. On error it writes usage plus a message to **stderr** and calls `sys.exit(2)`, which raises `SystemExit`. Python itself maps an uncaught exception to exit code 1 and `sys.exit(n)` to n, which is what Jenkins, cron and shells read.",
            "gotchas": [
                {
                    "title": "Throwing away the exit code",
                    "local_only": PROC_NOTE,
                    "note": "The script returns 1 from main() but never passes it to sys.exit, so the shell (and Jenkins) sees success.",
                    "wrong": """import subprocess, sys
script = "def main():\\n    print('2 tests failed')\\n    return 1\\nmain()\\n"
r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
print(r.stdout.strip(), "| exit code seen by CI:", r.returncode)""",
                    "fixed": """import subprocess, sys
script = "import sys\\ndef main():\\n    print('2 tests failed')\\n    return 1\\nsys.exit(main())\\n"
r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
print(r.stdout.strip(), "| exit code seen by CI:", r.returncode)""",
                }
            ],
            "best": "Give every tool `main(argv=None) -> int` and finish with `sys.exit(main())`. Validate as much as possible in the parser (types, choices, mutually exclusive groups) so bad input fails before any lab equipment is touched. Use exit code 0 for success, 1 for test failures and 2 for usage errors.",
        },
        {
            "title": "The same CLI with typer",
            "local_only": TYPER_NOTE,
            "concept": "`typer` builds a CLI from ordinary functions and their **type hints**: parameters become options or arguments, `int` hints convert input, `bool` becomes a `--flag/--no-flag` pair, and docstrings become help text. Each decorated function is a subcommand. `typer.testing.CliRunner` invokes the CLI in-process for tests. It's built on click, so `typer.Exit(code=...)` sets the exit code.",
            "why": "Lab tools tend to grow a dozen subcommands. With typer, adding one is writing a typed function; help text, conversion and validation come for free, and CliRunner makes each command unit-testable.",
            "syntax": "app = typer.Typer()\n\n@app.command()\ndef sweep(band: Band, step: int = 3, verbose: bool = False):\n    \"\"\"Run an attenuation sweep.\"\"\"\n\nif __name__ == \"__main__\":\n    app()",
            "code": """from enum import Enum  ## Choices as an enum

import typer  ## Third-party: pip install typer
from typer.testing import CliRunner  ## Run commands in-process for tests

app = typer.Typer(help="Lab Wi-Fi helper")  ## The CLI application


class Band(str, Enum):  ## typer turns an Enum parameter into a fixed set of choices
    G2 = "2G"  ## 2.4 GHz
    G5 = "5G"  ## 5 GHz
    G6 = "6G"  ## 6 GHz


@app.command()  ## Registers `sweep` as a subcommand
def sweep(band: Band = typer.Option(..., help="Band under test"), att_stop: int = 60, step: int = 3, verbose: bool = False) -> None:  ## Options from type hints
    \"\"\"Run an attenuation sweep.\"\"\"  ## Becomes the command's help text
    steps = list(range(0, att_stop + 1, step))  ## The sweep points
    typer.echo(f"sweep {band.value}: {len(steps)} steps verbose={verbose}")  ## echo works well with CliRunner


@app.command()  ## A second subcommand
def scan(json_output: bool = typer.Option(False, "--json", help="JSON output")) -> None:  ## Custom option name
    \"\"\"Scan and list BSSIDs.\"\"\"  ## Help text
    typer.echo("scan as json" if json_output else "scan as table")  ## Output


def main() -> None:
    runner = CliRunner()  ## Simulates the command line without starting a process
    for args in (["sweep", "--band", "6G", "--att-stop", "30", "--step", "10", "--verbose"], ["scan", "--json"], ["sweep", "--band", "7G"]):  ## Three invocations
        result = runner.invoke(app, args)  ## Run the CLI with these arguments
        first_line = result.output.strip().splitlines()[0] if result.exit_code == 0 else "usage error"  ## Keep the demo output short
        print(" ".join(args), "->", first_line, "| exit", result.exit_code)  ## Exit 2 for the invalid band


if __name__ == "__main__":
    main()""",
            "under": "typer inspects each function's signature with `inspect` and `typing.get_type_hints`, builds click `Option` and `Argument` objects from the parameters, and wraps them in click commands. Parameter `att_stop` becomes `--att-stop`. Invalid values raise click's `BadParameter`, which prints a usage error and exits with code 2, just like argparse.",
            "gotchas": [],
            "best": "Choose argparse for small tools and zero dependencies, typer for larger tool suites. Either way, keep the business logic in plain functions that the CLI layer calls, so pytest can test the logic without going through the command line.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write a parser with a required `--dut-ip` and an optional `--retries` (int, default 3), and parse `['--dut-ip', '10.0.0.11']`.",
            "solution": "Two add_argument calls; dashes become underscores in the namespace.",
            "solution_code": """import argparse

p = argparse.ArgumentParser(prog="health")
p.add_argument("--dut-ip", required=True)
p.add_argument("--retries", type=int, default=3)
args = p.parse_args(["--dut-ip", "10.0.0.11"])
print(args.dut_ip, args.retries)""",
        },
        {
            "level": "Medium",
            "prompt": "Add a custom type `attenuation(text)` that accepts 0–95 and raises `argparse.ArgumentTypeError` otherwise; show the error exit code for '120'.",
            "solution": "ArgumentTypeError messages are shown in the usage error.",
            "solution_code": """import argparse


def attenuation(text):
    value = int(text)
    if not 0 <= value <= 95:
        raise argparse.ArgumentTypeError(f"{value} dB is outside 0..95")
    return value


p = argparse.ArgumentParser(prog="att")
p.add_argument("--db", type=attenuation, required=True)
print(p.parse_args(["--db", "40"]).db)
try:
    p.parse_args(["--db", "120"])
except SystemExit as exc:
    print("exit code:", exc.code)""",
        },
        {
            "level": "Hard",
            "prompt": "Write `main(argv)` for a tool with subcommands `reboot <ap>` and `status <ap>... [--json]` that returns 0, or 1 if any AP name doesn't start with 'ap-'. Call it with three argument lists.",
            "solution": "nargs='+' collects one or more positionals; return codes carry the result.",
            "solution_code": """import argparse
import json


def main(argv=None):
    p = argparse.ArgumentParser(prog="aptool")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("reboot").add_argument("ap")
    st = sub.add_parser("status")
    st.add_argument("aps", nargs="+")
    st.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    names = [args.ap] if args.cmd == "reboot" else args.aps
    bad = [n for n in names if not n.startswith("ap-")]
    if args.cmd == "status" and args.json:
        print(json.dumps({n: "up" for n in names}))
    else:
        print(args.cmd, names)
    return 1 if bad else 0


print(main(["reboot", "ap-1"]), main(["status", "ap-1", "ap-2", "--json"]), main(["status", "switch-1"]))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "How does a Python script report failure to Jenkins?", "a": "Through its process exit code: 0 means success, anything else failure. Use sys.exit(main()) with main returning an int; an uncaught exception also exits with 1.", "follow": "What exit code does argparse use for bad arguments? (2.)"},
        {"level": "Intermediate", "q": "Why write main(argv=None) instead of reading sys.argv directly?", "a": "So tests can call main(['sweep', '--band', '5G']) with a list and assert on the return code and output, without spawning a process. argparse uses sys.argv[1:] when argv is None.", "follow": "How do you test that bad input is rejected? (Catch SystemExit and check its code.)"},
        {"level": "Intermediate", "q": "argparse vs click/typer?", "a": "argparse is in the standard library and fine for small tools. click and typer make large multi-command CLIs easier: decorators or type hints define options, they handle help, colours and prompts, and include test runners. typer builds on click using type hints.", "follow": "How does typer know an option is an int? (From the parameter's type hint.)"},
        {"level": "Beginner", "q": "What does action='store_true' do?", "a": "Creates a flag that is False by default and True when present on the command line; it takes no value.", "follow": "How do you make two options mutually exclusive? (add_mutually_exclusive_group.)"},
    ],
    "quiz": [
        {"q": "argparse turns `--att-stop` into which attribute?", "options": ["args.att-stop", "args.att_stop", "args.attStop", "args['att-stop']"], "answer": 1, "why": "Dashes become underscores."},
        {"q": "Exit code for an argparse usage error?", "options": ["0", "1", "2", "-1"], "answer": 2, "why": "argparse calls sys.exit(2)."},
        {"q": "How should a script end so CI sees main()'s result?", "options": ["main()", "print(main())", "sys.exit(main())", "return main()"], "answer": 2, "why": "sys.exit passes the code to the OS."},
        {"q": "typer derives option types from...", "options": ["Docstrings", "Type hints", "Default values only", "A YAML file"], "answer": 1, "why": "Signature introspection."},
        {"q": "Which restricts --band to fixed values?", "options": ["type=str", "choices=[...]", "nargs='?'", "metavar"], "answer": 1, "why": "choices validates the value."},
    ],
    "cards": [
        {"front": "Testable CLI entry point", "back": "`def main(argv=None) -> int` + `sys.exit(main())`"},
        {"front": "Boolean flag in argparse", "back": "`action='store_true'`"},
        {"front": "Subcommands", "back": "`sub = parser.add_subparsers(dest='cmd', required=True)`"},
        {"front": "Exit codes", "back": "0 success, 1 failure, 2 usage error"},
    ],
}


M_4_2 = {
    "id": "4.2",
    "title": "subprocess",
    "hours": 2.5,
    "summary": "Running external tools safely: run() with captured output, check and timeout, argument lists instead of shell strings, and Popen for streaming output and stopping hung processes.",
    "concepts": [
        {
            "title": "subprocess.run: output, errors and timeouts",
            "local_only": PROC_NOTE,
            "concept": "`subprocess.run(args, ...)` starts a program, waits for it and returns a `CompletedProcess` with `returncode`, `stdout` and `stderr`. Pass the command as a **list** of arguments. `capture_output=True` collects the output; `text=True` decodes it to str. `check=True` raises `CalledProcessError` on a non-zero exit; `timeout=` kills the child and raises `TimeoutExpired` if it runs too long. `shlex.split` and `shlex.join` convert safely between a command string and a list.",
            "why": "iperf3, tcpdump, wpa_cli, hostapd_cli, iw and tshark are all command-line tools. A thin, safe wrapper around them, with a timeout on every call, is the core of most lab automation.",
            "syntax": "r = subprocess.run([\"iperf3\", \"-c\", host, \"-J\"], capture_output=True, text=True,\n                   timeout=60, check=True)\nr.returncode, r.stdout, r.stderr\nshlex.split(\"iperf3 -c 10.0.0.2 -t 30\")",
            "code": """import shlex  ## Safe splitting and joining of shell-style command lines
import subprocess  ## Run other programs
import sys  ## sys.executable: the current Python, available on every machine

PY = sys.executable  ## We run small Python one-liners so the demo works without iperf3 installed


def main() -> None:
    r = subprocess.run([PY, "-c", "print('iperf 3.16')"], capture_output=True, text=True)  ## List of args; capture and decode output
    print(r.returncode, repr(r.stdout.strip()), repr(r.stderr))  ## 0, the text, and an empty stderr
    r = subprocess.run([PY, "-c", "import sys; print('connect failed: no route', file=sys.stderr); sys.exit(1)"], capture_output=True, text=True)  ## A failing tool
    print(r.returncode, r.stderr.strip())  ## Without check=True, failure is just a return code you must inspect
    try:  ## check=True turns a non-zero exit into an exception
        subprocess.run([PY, "-c", "import sys; sys.exit(3)"], check=True)  ## Exits with 3
    except subprocess.CalledProcessError as err:  ## Raised by check=True
        print("CalledProcessError: exit", err.returncode)  ## The child's exit code
    try:  ## A hung tool
        subprocess.run([PY, "-c", "import time; time.sleep(5)"], timeout=0.5)  ## Would run 5 s
    except subprocess.TimeoutExpired as err:  ## run() kills the child, then raises
        print("TimeoutExpired after", err.timeout, "s")  ## The limit we set
    cmd = "iperf3 -c 192.168.1.10 -t 30 -J --logfile 'run 1.json'"  ## A command line from a config file
    print(shlex.split(cmd))  ## Quotes are honoured: 'run 1.json' stays one argument
    print(shlex.join(["wpa_cli", "-i", "wlan0", "set_network", "0", "ssid", '"lab wpa3"']))  ## Quote a list for logging or copy-paste


if __name__ == "__main__":
    main()""",
            "under": "With a list, Python executes the program directly (fork/exec on Linux, CreateProcess on Windows) and each list item arrives as exactly one argument; no shell parses it. `shell=True` instead hands one string to `/bin/sh -c`, which interprets spaces, quotes, `;`, `|`, `$()` and globbing. `run()` reads both pipes concurrently with `communicate()`, so a chatty child can't deadlock by filling a pipe buffer.",
            "gotchas": [
                {
                    "title": "shell=True with outside input",
                    "local_only": PROC_NOTE,
                    "note": "The shell interprets the `;` in an SSID taken from a config file and runs a second command. With an argument list the text is passed through literally.",
                    "wrong": """import subprocess
ssid = "lab; echo SECOND COMMAND RAN"
print(subprocess.run(f"echo {ssid}", shell=True, capture_output=True, text=True).stdout, end="")""",
                    "fixed": """import subprocess
ssid = "lab; echo SECOND COMMAND RAN"
print(subprocess.run(["echo", ssid], capture_output=True, text=True).stdout, end="")""",
                },
                {
                    "title": "Forgetting text=True",
                    "local_only": PROC_NOTE,
                    "note": "Without it, stdout is bytes, so string operations fail or compare wrongly.",
                    "wrong": """import subprocess, sys
out = subprocess.run([sys.executable, "-c", "print('940 Mbits/sec')"], capture_output=True).stdout
print(out, "Mbits" in str(out), out.startswith(b"940"))""",
                    "fixed": """import subprocess, sys
out = subprocess.run([sys.executable, "-c", "print('940 Mbits/sec')"], capture_output=True, text=True).stdout
print(repr(out.strip()), "Mbits" in out)""",
                },
            ],
            "best": "Always pass a list, always set a timeout, use `check=True` (or inspect `returncode`) so failures can't pass silently, log the command with `shlex.join`, and keep stderr: it usually explains the failure. Never use `shell=True` with values from configs, users or devices.",
        },
        {
            "title": "Popen: streaming output and stopping processes",
            "local_only": PROC_NOTE,
            "concept": "`subprocess.Popen` starts a process **without waiting**, so you can read its output line by line while it runs, do other work, and decide when to stop it. Iterate `proc.stdout` for live lines, `proc.wait(timeout=...)` to wait with a limit, and `terminate()` (SIGTERM) or `kill()` (SIGKILL) to stop it. Use it as a context manager so pipes are closed and the process is waited on.",
            "why": "A packet capture or an iperf3 server runs for the length of a test and must be stopped afterwards; a long iperf3 client run should stream per-second results into the log rather than appear all at once at the end.",
            "syntax": "with subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True) as proc:\n    for line in proc.stdout:\n        handle(line)\nproc.returncode\n\nproc.terminate(); proc.wait(timeout=5)   # then proc.kill() if needed",
            "code": """import subprocess  ## Popen and friends
import sys  ## sys.executable

CHILD = "import time\\nfor i in range(3):\\n    print(f'[{i}-{i + 1} sec] 940 Mbits/sec', flush=True)\\n    time.sleep(0.1)\\n"  ## Imitates iperf3's per-second lines


def main() -> None:
    with subprocess.Popen([sys.executable, "-c", CHILD], stdout=subprocess.PIPE, text=True) as proc:  ## Starts and returns immediately
        for line in proc.stdout:  ## Each line arrives as soon as the child flushes it
            print("live:", line.rstrip())  ## Stream into our own log
    print("exit code:", proc.returncode)  ## The with block waited for the process
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])  ## Like a capture that runs until stopped
    try:  ## Give it a short grace period
        proc.wait(timeout=0.3)  ## Raises TimeoutExpired: it's still running
    except subprocess.TimeoutExpired:  ## Time to stop it
        proc.terminate()  ## Polite stop: SIGTERM on Linux/macOS
        proc.wait(timeout=5)  ## Reap it; escalate to proc.kill() if this times out
    print("stopped, returncode", proc.returncode)  ## Negative = killed by that signal number on POSIX (-15 = SIGTERM)


if __name__ == "__main__":
    main()""",
            "under": "Popen returns as soon as the child has started. Reading `proc.stdout` blocks until the child writes and flushes a line; programs that buffer their output (most C tools when stdout isn't a terminal) appear to stall, which is why tools like tcpdump have `-l` (line-buffered) options. If you read only stdout while stderr is also a full pipe, the child can block forever; merge them with `stderr=subprocess.STDOUT` or use `communicate()`.",
            "gotchas": [
                {
                    "title": "Leaving a background process running",
                    "local_only": PROC_NOTE,
                    "note": "If the test crashes before stopping the capture, it keeps running (and filling the disk). Stop it in finally, or use a context manager that does.",
                    "wrong": """import subprocess, sys
proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
try:
    raise RuntimeError("test failed mid-run")
except RuntimeError:
    pass
print("capture still running:", proc.poll() is None)
proc.kill(); proc.wait()""",
                    "fixed": """import subprocess, sys
proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
try:
    try:
        raise RuntimeError("test failed mid-run")
    finally:
        proc.terminate()
        proc.wait(timeout=5)
except RuntimeError:
    pass
print("capture still running:", proc.poll() is None)""",
                }
            ],
            "best": "Wrap long-running tools (captures, iperf3 servers) in a context manager (Module 3.9) that terminates them in `__exit__`, escalating to `kill()` after a timeout. Stream output line by line into logging, and merge stderr into stdout unless you need them separate.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "local_only": PROC_NOTE,
            "prompt": "Run `python -c \"print(6 * 7)\"` with subprocess.run, capture the output as text and convert it to an int.",
            "solution": "capture_output=True, text=True, then int(stdout).",
            "solution_code": """import subprocess, sys

r = subprocess.run([sys.executable, "-c", "print(6 * 7)"], capture_output=True, text=True, check=True)
print(int(r.stdout) + 1)""",
        },
        {
            "level": "Medium",
            "local_only": PROC_NOTE,
            "prompt": "Write `run_tool(args, timeout=10)` that returns (ok, output) where ok is False on a non-zero exit or a timeout, and the output includes stderr.",
            "solution": "Merge stderr into stdout and catch TimeoutExpired.",
            "solution_code": """import subprocess, sys


def run_tool(args, timeout=10):
    try:
        r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    return r.returncode == 0, r.stdout.strip()


print(run_tool([sys.executable, "-c", "print('ok')"]))
print(run_tool([sys.executable, "-c", "import sys; sys.exit('no such interface: wlan9')"]))
print(run_tool([sys.executable, "-c", "import time; time.sleep(3)"], timeout=0.3))""",
        },
        {
            "level": "Hard",
            "local_only": PROC_NOTE,
            "prompt": "Stream a child that prints 5 throughput lines and stop it as soon as a line reports under 500 Mbits/sec, printing how many lines were read.",
            "solution": "Read lines from Popen and terminate when the condition is met.",
            "solution_code": """import re, subprocess, sys

child = "import time\\nfor v in [941, 938, 412, 939, 940]:\\n    print(f'{v} Mbits/sec', flush=True)\\n    time.sleep(0.05)\\n"
read = 0
with subprocess.Popen([sys.executable, "-c", child], stdout=subprocess.PIPE, text=True) as proc:
    for line in proc.stdout:
        read += 1
        mbps = int(re.match(r"(\\d+)", line).group(1))
        if mbps < 500:
            print("throughput dropped to", mbps, "- stopping")
            proc.terminate()
            break
print("lines read:", read)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "subprocess.run vs Popen?", "a": "run starts the process, waits for it and returns a CompletedProcess: ideal for short commands. Popen starts it and returns immediately, for streaming output, interacting, or stopping long-running processes yourself.", "follow": "What does run use internally? (Popen plus communicate.)"},
        {"level": "Intermediate", "q": "Why is shell=True dangerous?", "a": "The command string goes through /bin/sh, so characters like ; | $() and backticks in any interpolated value run extra commands (command injection), and quoting bugs break arguments with spaces. Passing a list avoids the shell entirely.", "follow": "When is shell=True acceptable? (Fixed, trusted command strings that need shell features like pipes, and even then prefer doing the pipe in Python.)"},
        {"level": "Intermediate", "q": "How do you handle a hung child process?", "a": "Always pass timeout. With run(), TimeoutExpired is raised after the child is killed. With Popen, wait(timeout=...), then terminate(), wait again, and kill() if it still doesn't exit.", "follow": "What does a negative returncode mean? (The process was killed by that signal, on POSIX.)"},
        {"level": "Advanced", "q": "Why can reading a child's stdout hang even though it's printing?", "a": "Buffering: many programs block-buffer output when stdout is a pipe, so lines arrive in large chunks or only at exit. Use the tool's line-buffering option, PYTHONUNBUFFERED for Python children, or a pseudo-terminal (pexpect, Module 6.8).", "follow": "And a deadlock? (Reading only one of two full pipes; use communicate() or merge stderr.)"},
    ],
    "quiz": [
        {"q": "What does check=True do?", "options": ["Validates arguments", "Raises CalledProcessError on non-zero exit", "Checks the tool exists", "Adds a timeout"], "answer": 1, "why": "Failures become exceptions."},
        {"q": "`shlex.split(\"a 'b c'\")` returns?", "options": ["['a', \"'b\", \"c'\"]", "['a', 'b c']", "['a b c']", "Error"], "answer": 1, "why": "Quotes keep 'b c' together."},
        {"q": "Without text=True, stdout is...", "options": ["str", "bytes", "None", "list"], "answer": 1, "why": "Raw bytes."},
        {"q": "Which starts a process without waiting?", "options": ["subprocess.run", "subprocess.call", "subprocess.Popen", "os.system"], "answer": 2, "why": "Popen returns immediately."},
        {"q": "What happens when run()'s timeout expires?", "options": ["Returns code 0", "Kills the child and raises TimeoutExpired", "Waits forever", "Detaches"], "answer": 1, "why": "That's the documented behaviour."},
    ],
    "cards": [
        {"front": "Safe run", "back": "`subprocess.run([...], capture_output=True, text=True, timeout=60, check=True)`"},
        {"front": "String <-> argument list", "back": "`shlex.split(s)` / `shlex.join(args)`"},
        {"front": "Stream output live", "back": "`with Popen(cmd, stdout=PIPE, text=True) as p: for line in p.stdout: ...`"},
        {"front": "Stop a process", "back": "terminate(), wait(timeout), then kill()"},
        {"front": "Never with outside input", "back": "`shell=True`"},
    ],
}


M_4_3 = {
    "id": "4.3",
    "title": "os, shutil, glob & Environment Variables",
    "hours": 1.5,
    "summary": "Reading configuration from environment variables, finding tools on PATH, and copying, moving, archiving and deleting result directories.",
    "concepts": [
        {
            "title": "Environment variables and file operations",
            "concept": "`os.environ` is a dict-like mapping of the process's environment; `os.getenv(name, default)` reads one safely. Every value is a **string**, so convert explicitly. Children started with subprocess inherit it. `shutil` handles whole-file and whole-tree operations: `copy2` (with metadata), `copytree`, `move`, `rmtree`, `make_archive` (zip or tar) and `which` (find an executable on PATH). `os.walk` walks a directory tree.",
            "why": "CI passes the bench name, DUT build and credentials as environment variables. At the end of a run, logs and pcaps are zipped into one artifact for Jenkins, and the scratch tree is removed. A pre-flight `shutil.which(\"iperf3\")` fails fast instead of crashing mid-test.",
            "syntax": "os.getenv(\"LAB_BENCH\", \"bench00\")\nint(os.getenv(\"LAB_RETRIES\", \"3\"))\nshutil.which(\"iperf3\")            # path or None\nshutil.copytree(src, dst)\nshutil.make_archive(base, \"zip\", root_dir=folder)\nshutil.rmtree(folder)",
            "code": """import os  ## Environment and directory walking
import shutil  ## High-level file operations
import tempfile  ## Scratch space for the demo
from pathlib import Path  ## Paths


def main() -> None:
    os.environ["LAB_BENCH"] = "bench07"  ## Normally set by Jenkins or your shell; values must be str
    print(os.environ.get("LAB_BENCH"), os.getenv("LAB_TOKEN", "<not set>"))  ## Safe reads with a default
    retries = int(os.getenv("LAB_RETRIES", "3"))  ## Everything is text: convert explicitly
    print(retries + 1)  ## Now arithmetic works
    print("tool found:", shutil.which("definitely-not-a-lab-tool") is not None)  ## which() returns a path or None
    with tempfile.TemporaryDirectory() as tmp:  ## Work in a scratch directory
        run = Path(tmp) / "build-4.32.1" / "throughput_6g"  ## A results folder
        run.mkdir(parents=True)  ## Create it
        for name in ["ap.log", "sta1.pcap", "iperf.json"]:  ## Typical artifacts
            (run / name).write_text(f"contents of {name}\\n")  ## Small placeholder files
        archive = shutil.make_archive(str(Path(tmp) / "artifacts"), "zip", root_dir=run.parent)  ## Zip the whole build folder
        print(Path(archive).name, Path(archive).stat().st_size > 0)  ## artifacts.zip, non-empty
        backup = shutil.copytree(run, Path(tmp) / "backup")  ## Copy an entire tree
        print(sorted(p.name for p in backup.iterdir()))  ## Same files in the copy
        shutil.move(str(backup / "sta1.pcap"), str(Path(tmp) / "keep.pcap"))  ## Move (rename) a file
        shutil.rmtree(run.parent)  ## Delete the original tree, contents included
        print(run.exists(), (Path(tmp) / "keep.pcap").exists())  ## Gone, and the moved file survived
        for dirpath, dirnames, filenames in os.walk(tmp):  ## Walk what's left, top-down
            print(Path(dirpath).relative_to(tmp).as_posix() or ".", sorted(dirnames), sorted(filenames))  ## One line per directory


if __name__ == "__main__":
    main()""",
            "under": "`os.environ` is loaded once at startup from the process environment; assigning to it calls `putenv` so child processes see the change, but the parent shell never does. `shutil.which` searches the directories in PATH (and PATHEXT extensions on Windows). `rmtree` removes files bottom-up; on Windows, read-only files need an `onexc` handler to clear the flag first.",
            "gotchas": [
                {
                    "title": "Treating environment values as numbers",
                    "note": "Environment variables are always strings (or missing).",
                    "wrong": """import os
os.environ["LAB_RETRIES"] = "3"
print(os.getenv("LAB_RETRIES") + 1)""",
                    "fixed": """import os
os.environ["LAB_RETRIES"] = "3"
print(int(os.getenv("LAB_RETRIES", "3")) + 1)""",
                },
                {
                    "title": "Assigning a non-string",
                    "note": "os.environ only stores strings; convert numbers and booleans yourself.",
                    "wrong": """import os
os.environ["LAB_CHANNEL"] = 149""",
                    "fixed": """import os
os.environ["LAB_CHANNEL"] = str(149)
print(repr(os.environ["LAB_CHANNEL"]))""",
                },
            ],
            "best": "Read the environment in one config function, convert and validate every value there, and pass typed values to the rest of the code. Check required tools with `shutil.which` at startup. Archive results with `make_archive` for CI, and delete scratch trees only after the archive succeeds.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Read `LAB_DEBUG` and treat '1', 'true', 'yes' (any case) as True and anything else, including unset, as False.",
            "solution": "Normalise the string and test membership.",
            "solution_code": """import os


def env_flag(name):
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes"}


os.environ["LAB_DEBUG"] = "True"
print(env_flag("LAB_DEBUG"), env_flag("LAB_UNSET_FLAG"))""",
        },
        {
            "level": "Medium",
            "local_only": "looks up programs on your machine's PATH",
            "prompt": "Write `require_tools(names)` that raises RuntimeError listing every missing tool. Test it with the running Python (always present) and a made-up tool name.",
            "solution": "Collect the names for which shutil.which returns None, then raise once with all of them.",
            "solution_code": """import shutil, sys


def require_tools(names):
    missing = [n for n in names if shutil.which(n) is None]
    if missing:
        raise RuntimeError(f"missing tools: {', '.join(missing)}")
    return True


print(require_tools([sys.executable]))
try:
    require_tools([sys.executable, "lab-attenuator-cli-9000"])
except RuntimeError as err:
    print("RuntimeError:", err)""",
        },
        {
            "level": "Hard",
            "prompt": "Keep only the 3 newest build folders under results/ (by name order of build numbers) and delete the rest with shutil.rmtree.",
            "solution": "Sort folder names by the numeric version, slice off the newest three, delete the others.",
            "solution_code": """import shutil, tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    results = Path(tmp) / "results"
    for b in ["4.30.0", "4.31.2", "4.32.0", "4.32.1", "4.9.9"]:
        (results / b).mkdir(parents=True)
    builds = sorted(results.iterdir(), key=lambda p: tuple(int(x) for x in p.name.split(".")))
    for old in builds[:-3]:
        shutil.rmtree(old)
    print(sorted(p.name for p in results.iterdir()))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What type are environment variable values?", "a": "Always strings (or absent). Convert with int(), float() or an explicit boolean parser, and provide defaults with os.getenv(name, default).", "follow": "Does changing os.environ affect the parent shell? (No; only this process and its children.)"},
        {"level": "Intermediate", "q": "How do you pass secrets to a test job?", "a": "Through the CI system's secret store injected as environment variables (or a secrets manager), read once at startup and never logged. Never commit them to the repository or config files.", "follow": "How do you stop them appearing in logs? (Masking in CI plus a log filter that redacts known secret values.)"},
        {"level": "Beginner", "q": "How do you check a tool is installed before using it?", "a": "shutil.which('iperf3') returns its full path or None, searching PATH like the shell does.", "follow": "Why check up front? (Fail fast with a clear message instead of a FileNotFoundError mid-test.)"},
        {"level": "Intermediate", "q": "copy vs copy2 vs copytree?", "a": "copy copies content and permission bits, copy2 also preserves timestamps and other metadata, copytree copies a whole directory tree (using copy2 by default).", "follow": "How do you archive a folder? (shutil.make_archive(base, 'zip', root_dir).)"},
    ],
    "quiz": [
        {"q": "`os.getenv('NOT_SET')` returns?", "options": ["''", "None", "KeyError", "False"], "answer": 1, "why": "None unless a default is given."},
        {"q": "What does shutil.which return for a missing tool?", "options": ["''", "None", "False", "Raises"], "answer": 1, "why": "None."},
        {"q": "Which deletes a directory with its contents?", "options": ["os.remove", "os.rmdir", "shutil.rmtree", "Path.unlink"], "answer": 2, "why": "rmdir needs an empty directory."},
        {"q": "`os.environ['X'] = 5` ...", "options": ["Stores 5", "Stores '5'", "Raises TypeError", "Is ignored"], "answer": 2, "why": "Values must be str."},
        {"q": "Which creates a zip of a folder?", "options": ["shutil.make_archive", "os.zip", "zipfile.open", "Path.zip"], "answer": 0, "why": "make_archive(base, 'zip', root_dir)."},
    ],
    "cards": [
        {"front": "Read an env var with default", "back": "`os.getenv('NAME', 'default')` (always a str)"},
        {"front": "Find a tool on PATH", "back": "`shutil.which('iperf3')`"},
        {"front": "Copy / delete a tree", "back": "`shutil.copytree` / `shutil.rmtree`"},
        {"front": "Zip a results folder", "back": "`shutil.make_archive(base, 'zip', root_dir=folder)`"},
    ],
}


M_4_4 = {
    "id": "4.4",
    "title": "Configuration Management",
    "hours": 2,
    "summary": "Layered configuration (defaults, testbed file, environment, CLI), typed and validated config objects, and validation with pydantic and pydantic-settings.",
    "concepts": [
        {
            "title": "Layered, typed configuration",
            "concept": "Real tools combine several configuration **layers**, each overriding the one before: built-in defaults → a testbed file → environment variables → command-line options. Merge the layers once, then **convert and validate** into a typed, immutable object (a frozen dataclass), so the rest of the code never handles raw strings or missing keys. Fail fast with a clear message on invalid values.",
            "why": "The same suite runs on any bench by swapping one testbed file, Jenkins can override the channel with an environment variable, and an engineer can override it again on the command line, all without editing code.",
            "syntax": "merged = {**DEFAULTS, **file_layer, **env_layer, **cli_layer}  # later wins\n\n@dataclass(frozen=True)\nclass Testbed:\n    name: str\n    channel: int = 36\n    def __post_init__(self): ...   # validate",
            "code": """import json  ## The testbed file format for this demo (YAML works the same way)
import tempfile  ## Scratch file
from dataclasses import dataclass, fields  ## Typed config object and its field list
from pathlib import Path  ## File handling

DEFAULTS = {"band": "5G", "channel": 36, "attenuator_port": 1}  ## Built-in defaults: the lowest layer


@dataclass(frozen=True)  ## Immutable once built: nothing can change config mid-run
class Testbed:  ## The validated configuration the rest of the code uses
    name: str  ## Bench name
    ap_ip: str  ## AP management address
    band: str  ## Band under test
    channel: int  ## Channel number
    attenuator_port: int  ## Attenuator output used for this AP

    def __post_init__(self) -> None:  ## Validation runs once, at creation
        if self.band not in {"2G", "5G", "6G"}:  ## Closed set of bands
            raise ValueError(f"band must be 2G, 5G or 6G, got {self.band!r}")  ## Clear error
        if not 1 <= self.channel <= 233:  ## Broad sanity range
            raise ValueError(f"channel {self.channel} out of range")  ## Clear error


def load_testbed(path: Path, env: dict[str, str], cli: dict[str, object]) -> Testbed:  ## Merge layers, convert, validate
    file_layer = json.loads(path.read_text(encoding="utf-8"))  ## Second layer: the testbed file
    env_layer = {f.name: env[f"LAB_{f.name.upper()}"] for f in fields(Testbed) if f"LAB_{f.name.upper()}" in env}  ## LAB_CHANNEL -> channel
    merged = {**DEFAULTS, **file_layer, **env_layer, **cli}  ## Later layers override earlier ones
    types = {f.name: f.type for f in fields(Testbed)}  ## Field name -> declared type
    typed = {k: int(v) if types[k] is int else v for k, v in merged.items()}  ## Env values arrive as text: convert ints
    return Testbed(**typed)  ## __post_init__ validates the final values


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:  ## Write a sample testbed file
        path = Path(tmp) / "bench07.json"  ## One file per bench
        path.write_text(json.dumps({"name": "bench07", "ap_ip": "10.0.0.11", "channel": 149}))  ## Overrides the default channel
        tb = load_testbed(path, env={}, cli={})  ## Defaults + file
        print(tb)  ## channel 149 from the file
        tb = load_testbed(path, env={"LAB_CHANNEL": "157"}, cli={})  ## The environment overrides the file
        print(tb.channel, type(tb.channel).__name__)  ## Converted to int
        tb = load_testbed(path, env={"LAB_CHANNEL": "157"}, cli={"channel": 165, "band": "5G"})  ## CLI overrides everything
        print(tb.channel)  ## 165
        try:  ## A bad value from any layer is caught once, centrally
            load_testbed(path, env={"LAB_BAND": "7G"}, cli={})  ## Typo in a Jenkins parameter
        except ValueError as err:  ## Raised by __post_init__
            print("ValueError:", err)  ## Fails before any device is touched


if __name__ == "__main__":
    main()""",
            "under": "`{**a, **b}` builds a new dict where keys from b replace keys from a; it's a shallow merge, so nested sections need a recursive merge (Module 1.10's `merge_config`). `dataclasses.fields()` exposes each field's name and declared type, which lets one function map environment names and convert values generically.",
            "gotchas": [
                {
                    "title": "Secrets in the testbed file",
                    "note": "Passwords committed with the testbed end up in git history and CI logs. Keep only a reference in the file and read the secret from the environment.",
                    "wrong": """import json
testbed = json.loads('{"ap_ip": "10.0.0.11", "ap_password": "Lab@1234"}')
print("connecting with", testbed["ap_password"])""",
                    "fixed": """import json, os
os.environ.setdefault("LAB_AP_PASSWORD", "from-ci-secret-store")
testbed = json.loads('{"ap_ip": "10.0.0.11", "ap_password_env": "LAB_AP_PASSWORD"}')
password = os.environ[testbed["ap_password_env"]]
print("password loaded:", bool(password), "| length hidden from logs")""",
                }
            ],
            "best": "Load configuration in one place at startup, merge the layers in a documented order, convert and validate into a frozen object, and log the final values (minus secrets) at the start of every run so failures can be reproduced.",
        },
        {
            "title": "Validation with pydantic and pydantic-settings",
            "local_only": PYDANTIC_NOTE,
            "concept": "`pydantic` models declare fields with type hints and constraints (`Field(ge=1, le=233)`, `Literal[...]`, IP address types, nested models and lists). `Model.model_validate(data)` converts compatible input (\"149\" → 149) and raises one `ValidationError` listing **every** problem with its location. `pydantic-settings`' `BaseSettings` reads fields from environment variables (with a prefix such as `LAB_`) and `.env` files automatically.",
            "why": "A testbed YAML with three typos should report all three at once, with their paths (`radios.1.channel`), before the nightly run starts, not one at a time across three failed jobs.",
            "syntax": "class Radio(BaseModel):\n    band: Literal[\"2G\", \"5G\", \"6G\"]\n    channel: int = Field(ge=1, le=233)\n\nTestbed.model_validate(yaml.safe_load(f))\n\nclass Settings(BaseSettings):\n    model_config = SettingsConfigDict(env_prefix=\"LAB_\")\n    bench: str = \"bench00\"",
            "code": """import os  ## To simulate environment variables
from ipaddress import IPv4Address  ## pydantic validates and converts IP addresses
from typing import Literal  ## Closed sets of values

from pydantic import BaseModel, Field, ValidationError  ## Third-party: pip install pydantic
from pydantic_settings import BaseSettings, SettingsConfigDict  ## Third-party: pip install pydantic-settings


class Radio(BaseModel):  ## One radio section of the testbed
    band: Literal["2G", "5G", "6G"]  ## Only these strings
    channel: int = Field(ge=1, le=233)  ## Integer with bounds
    width: Literal[20, 40, 80, 160, 320] = 80  ## Allowed widths, with a default


class Testbed(BaseModel):  ## The whole testbed file
    name: str  ## Bench name
    ap_ip: IPv4Address  ## "10.0.0.11" becomes an IPv4Address object
    radios: list[Radio]  ## Nested models are validated too


class Settings(BaseSettings):  ## Values from the environment
    model_config = SettingsConfigDict(env_prefix="LAB_")  ## LAB_BENCH -> bench, LAB_RETRIES -> retries
    bench: str = "bench00"  ## Default when unset
    retries: int = 3  ## Converted from text


def main() -> None:
    tb = Testbed.model_validate({"name": "bench07", "ap_ip": "10.0.0.11", "radios": [{"band": "6G", "channel": "37", "width": 320}]})  ## "37" converts to 37
    print(tb.ap_ip, type(tb.ap_ip).__name__, tb.radios[0])  ## Typed values
    bad = {"name": "bench08", "ap_ip": "10.0.0.300", "radios": [{"band": "5G", "channel": 36}, {"band": "7G", "channel": 999}]}  ## Three mistakes
    try:  ## Validate the bad file
        Testbed.model_validate(bad)  ## Collects every error
    except ValidationError as err:  ## One exception, all problems
        print(err.error_count(), "errors:")  ## How many
        for e in err.errors():  ## Each problem with its location
            print("  ", ".".join(str(p) for p in e["loc"]), "->", e["type"])  ## e.g. radios.1.band -> literal_error
    os.environ["LAB_BENCH"], os.environ["LAB_RETRIES"] = "bench07", "5"  ## As Jenkins would set them
    print(Settings())  ## Reads and converts the environment


if __name__ == "__main__":
    main()""",
            "under": "pydantic compiles each model into a validator (written in Rust in pydantic 2) that walks the input, coerces compatible types in lax mode, checks constraints and accumulates errors with their paths instead of stopping at the first one. BaseSettings builds its input dict from several sources (init arguments, environment, `.env` files, secrets directories) in a defined priority order before validating.",
            "gotchas": [],
            "best": "Describe the testbed file with pydantic models, validate it at startup, and print every error with its location. Use BaseSettings for environment-driven options and keep secrets in `SecretStr` fields so they don't print.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Merge defaults `{'band': '5G', 'width': 80}`, a bench layer `{'width': 160}` and a CLI layer `{'band': '6G'}`, and print the result.",
            "solution": "Later dicts override earlier ones in `{**a, **b, **c}`.",
            "solution_code": """defaults = {"band": "5G", "width": 80}
bench = {"width": 160}
cli = {"band": "6G"}
print({**defaults, **bench, **cli})""",
        },
        {
            "level": "Medium",
            "prompt": "Write `env_int(name, default, low, high)` that reads an int from the environment and raises ValueError with a clear message for non-numbers or out-of-range values.",
            "solution": "Convert inside try, then range-check.",
            "solution_code": """import os


def env_int(name, default, low, high):
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name}={raw!r} is not an integer") from None
    if not low <= value <= high:
        raise ValueError(f"{name}={value} outside {low}..{high}")
    return value


os.environ["LAB_ATT_STEP"] = "3"
print(env_int("LAB_ATT_STEP", 2, 1, 10))
for bad in ["three", "40"]:
    os.environ["LAB_ATT_STEP"] = bad
    try:
        env_int("LAB_ATT_STEP", 2, 1, 10)
    except ValueError as err:
        print("ValueError:", err)""",
        },
        {
            "level": "Hard",
            "local_only": PYDANTIC_NOTE,
            "prompt": "Add a pydantic model validator to Testbed that rejects two radios on the same band, and show the error.",
            "solution": "model_validator(mode='after') runs once all fields are valid.",
            "solution_code": """from typing import Literal
from pydantic import BaseModel, ValidationError, model_validator


class Radio(BaseModel):
    band: Literal["2G", "5G", "6G"]
    channel: int


class Testbed(BaseModel):
    name: str
    radios: list[Radio]

    @model_validator(mode="after")
    def unique_bands(self):
        bands = [r.band for r in self.radios]
        if len(bands) != len(set(bands)):
            raise ValueError(f"duplicate band in {bands}")
        return self


try:
    Testbed(name="bench07", radios=[{"band": "5G", "channel": 36}, {"band": "5G", "channel": 149}])
except ValidationError as err:
    print(err.errors()[0]["msg"])""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "How do you manage configuration for many benches?", "a": "One testbed file per bench (YAML/JSON) for hardware details, layered over framework defaults, with environment variables and CLI options for per-run overrides. Merge in one place, validate into typed objects, keep secrets out of the files, and log the effective config at startup.", "follow": "Where do secrets come from? (The CI secret store or a vault, via environment variables.)"},
        {"level": "Intermediate", "q": "Why validate configuration at startup?", "a": "So a typo fails in seconds with a precise message instead of hours later as a confusing device error, and so every later function can trust the types it receives.", "follow": "What does pydantic add over hand-written checks? (Declarative constraints, coercion, nested models and all errors reported at once with locations.)"},
        {"level": "Beginner", "q": "In {**a, **b}, which value wins for a shared key?", "a": "The one from b: later unpackings override earlier ones. It's a shallow merge; nested dicts are replaced, not merged.", "follow": "How do you deep-merge? (A recursive function.)"},
        {"level": "Advanced", "q": "What is BaseSettings in pydantic-settings?", "a": "A model whose fields are filled from environment variables (optionally with a prefix and nested delimiter), .env files and secret directories, then validated like any pydantic model. It centralises environment-driven configuration with types.", "follow": "Which source wins when both an env var and an init argument exist? (Init arguments by default.)"},
    ],
    "quiz": [
        {"q": "Which layer usually has the highest priority?", "options": ["Defaults", "Testbed file", "Environment", "Command line"], "answer": 3, "why": "The most specific, most recent intent wins."},
        {"q": "Why freeze the config object?", "options": ["Speed", "So nothing changes it mid-run", "pydantic requires it", "JSON needs it"], "answer": 1, "why": "Immutability prevents surprises."},
        {"q": "pydantic's ValidationError reports...", "options": ["Only the first error", "Every error with its location", "Only type errors", "Nothing useful"], "answer": 1, "why": "Errors are accumulated."},
        {"q": "Where should an AP password live?", "options": ["In the testbed YAML", "In the code", "In a CI secret / environment variable", "In the log"], "answer": 2, "why": "Never in the repo."},
        {"q": "`Field(ge=1, le=233)` means...", "options": ["1 < x < 233", "1 <= x <= 233", "A default of 1", "A list length"], "answer": 1, "why": "Greater-or-equal and less-or-equal."},
    ],
    "cards": [
        {"front": "Config layer order", "back": "defaults → testbed file → environment → CLI"},
        {"front": "Typed config object", "back": "Frozen dataclass or pydantic model, validated once."},
        {"front": "pydantic validate", "back": "`Model.model_validate(data)`; ValidationError lists all problems."},
        {"front": "Env-driven settings", "back": "`BaseSettings` with `env_prefix='LAB_'`"},
    ],
}
