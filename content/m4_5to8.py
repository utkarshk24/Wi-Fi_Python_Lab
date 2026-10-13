"""Phase 4 content: modules 4.5-4.8."""

SIGNAL_NOTE = "sends a real OS signal to its own process, which the in-browser runner can't do"
SCHEDULE_NOTE = "needs the schedule package (pip install schedule)"

M_4_5 = {
    "id": "4.5",
    "title": "logging",
    "hours": 2.5,
    "summary": "Loggers, handlers, levels and formatters; per-module loggers and propagation; logging exceptions; rotating files, dictConfig and structured JSON logs.",
    "concepts": [
        {
            "title": "Loggers, handlers, levels and formatters",
            "concept": "A **logger** (`logging.getLogger(__name__)`) creates records; **handlers** send them somewhere (console, file, network); **formatters** decide what a line looks like; **levels** (DEBUG < INFO < WARNING < ERROR < CRITICAL) filter at both the logger and the handler. Loggers form a dotted hierarchy, `wifitest.drivers.ap` is a child of `wifitest`, and records **propagate** up to parent handlers. Pass values as arguments (`log.info(\"ch %s\", ch)`) so formatting only happens if the record is emitted. `log.exception(...)` inside `except` adds the traceback.",
            "why": "A 3 a.m. failure is debuggable only if the log shows what was sent to the DUT and what came back. Console at INFO keeps Jenkins output readable while a DEBUG file keeps every command for later.",
            "syntax": "log = logging.getLogger(__name__)\nlog.debug(\"sent %r to %s\", cmd, ap)\nlog.warning(\"retrying %s\", ap)\ntry: ...\nexcept Exception:\n    log.exception(\"push failed\")\n\nhandler.setLevel(logging.INFO)\nhandler.setFormatter(logging.Formatter(\"%(levelname)s %(name)s: %(message)s\"))",
            "code": """import io  ## StringIO stands in for a log file so we can print its contents
import logging  ## The standard logging framework
import sys  ## sys.stdout for the console handler


def setup_logging() -> io.StringIO:  ## Configure once, at program start
    root = logging.getLogger("wifitest")  ## Top of our package's logger tree
    root.setLevel(logging.DEBUG)  ## Let everything through at the logger level...
    console = logging.StreamHandler(sys.stdout)  ## ...the console handler shows INFO and above
    console.setLevel(logging.INFO)  ## Readable CI output
    console.setFormatter(logging.Formatter("%(levelname)-7s %(name)s: %(message)s"))  ## No timestamps here so the demo output is stable
    file_buf = io.StringIO()  ## A real program would use logging.FileHandler("run.log")
    file_handler = logging.StreamHandler(file_buf)  ## Second destination
    file_handler.setLevel(logging.DEBUG)  ## The file keeps everything
    file_handler.setFormatter(logging.Formatter("%(levelname)s|%(name)s|%(funcName)s|%(message)s"))  ## More detail per line
    root.addHandler(console)  ## Attach both handlers to the package logger
    root.addHandler(file_handler)  ## Child loggers propagate to these
    return file_buf  ## So the demo can print the 'file'


log = logging.getLogger("wifitest.drivers.ap")  ## In a real module: logging.getLogger(__name__)


def set_channel(ap: str, ch: int) -> int:  ## A driver function that logs
    log.debug("sending 'set radio channel %s' to %s", ch, ap)  ## Lazy %-style arguments: formatted only if emitted
    if ch == 14:  ## A suspicious value
        log.warning("%s: channel 14 is only allowed in Japan", ap)  ## Shown on the console and in the file
    return ch  ## Pretend the device accepted it


def main() -> None:
    buf = setup_logging()  ## Configure handlers
    set_channel("ap-1", 36)  ## DEBUG only: file but not console
    set_channel("ap-1", 14)  ## Also a WARNING: both destinations
    try:  ## An error with a traceback
        {}["radio0"]  ## KeyError
    except KeyError:  ## Inside except, log.exception adds the traceback
        log.error("config lookup failed: radio0 missing", exc_info=False)  ## Message only (log.exception would append the full traceback)
    print("--- file log ---")  ## Show what the file received
    print(buf.getvalue(), end="")  ## Every level, with function names


if __name__ == "__main__":
    main()""",
            "under": "A call such as `log.debug(...)` first checks the logger's effective level (cheap), then builds a `LogRecord` and passes it to the logger's handlers, then to each ancestor's handlers while `propagate` is true. Each handler applies its own level and filters, then formats the record. If no handler is configured anywhere, a last-resort handler prints WARNING and above to stderr, which is why INFO messages seem to vanish in unconfigured scripts.",
            "gotchas": [
                {
                    "title": "Logging before configuring",
                    "note": "With no configuration only WARNING and above appear (through the last-resort handler, on stderr). Configure logging once at startup.",
                    "wrong": """import logging
log = logging.getLogger("wifitest")
log.info("starting sweep")
log.warning("attenuator slow to respond")""",
                    "fixed": """import logging, sys
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s", stream=sys.stdout)
log = logging.getLogger("wifitest")
log.info("starting sweep")
log.warning("attenuator slow to respond")""",
                },
                {
                    "title": "f-strings in log calls",
                    "note": "The f-string is built even when DEBUG is disabled, so an expensive repr runs for nothing. Pass arguments and let logging format lazily.",
                    "wrong": """import logging
logging.basicConfig(level=logging.INFO)
calls = {"n": 0}
class Dump:
    def __repr__(self):
        calls["n"] += 1
        return "<huge capture dump>"
for _ in range(1000):
    logging.debug(f"frame {Dump()!r}")
print("expensive reprs built:", calls["n"])""",
                    "fixed": """import logging
logging.basicConfig(level=logging.INFO)
calls = {"n": 0}
class Dump:
    def __repr__(self):
        calls["n"] += 1
        return "<huge capture dump>"
for _ in range(1000):
    logging.debug("frame %r", Dump())
print("expensive reprs built:", calls["n"])""",
                },
            ],
            "best": "Use `logging.getLogger(__name__)` in every module and configure handlers only in the entry point. Log commands sent and responses received at DEBUG, decisions at INFO, recoverable problems at WARNING and failures at ERROR (with `log.exception` inside except blocks). Never print in library code.",
        },
        {
            "title": "Rotating files, dictConfig and JSON logs",
            "concept": "`RotatingFileHandler(maxBytes=..., backupCount=...)` caps file size by rolling `run.log` to `run.log.1`, `run.log.2`, ...; `TimedRotatingFileHandler` rolls by time. `logging.config.dictConfig` defines all loggers, handlers and formatters in one dictionary (often loaded from YAML). A custom `Formatter.format` can emit **JSON**, and `extra={...}` attaches structured fields (bench, test, DUT build) to a record for searching in log tools.",
            "why": "A week-long soak test must not fill the disk; nightly logs shipped to a search tool are far more useful when every line carries `test`, `bench` and `build` fields you can filter on.",
            "syntax": "RotatingFileHandler(\"soak.log\", maxBytes=10_000_000, backupCount=5)\nlogging.config.dictConfig({\"version\": 1, \"handlers\": {...}, \"loggers\": {...}})\nlog.info(\"tput ok\", extra={\"ctx\": {\"test\": \"tput_6g\", \"mbps\": 2841}})",
            "code": """import json  ## For the JSON formatter
import logging  ## Core logging
import logging.config  ## dictConfig
import tempfile  ## Scratch directory for the rotating files
from pathlib import Path  ## Listing the files


class JsonFormatter(logging.Formatter):  ## One JSON object per line
    def format(self, record: logging.LogRecord) -> str:  ## Called once per emitted record
        payload = {"level": record.levelname, "logger": record.name, "msg": record.getMessage()}  ## Core fields
        payload.update(getattr(record, "ctx", {}))  ## Structured fields passed with extra={"ctx": {...}}
        return json.dumps(payload)  ## A single line


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:  ## Logs go here
        log_path = Path(tmp) / "soak.log"  ## The active log file
        logging.config.dictConfig({  ## The whole setup as data
            "version": 1,  ## Required schema version
            "formatters": {"json": {"()": JsonFormatter}},  ## "()" names a factory for a custom class
            "handlers": {  ## Where records go
                "rotating": {"class": "logging.handlers.RotatingFileHandler", "filename": str(log_path), "maxBytes": 300, "backupCount": 2, "formatter": "json"},  ## Tiny limit to force rotation
            },
            "loggers": {"wifitest": {"level": "INFO", "handlers": ["rotating"], "propagate": False}},  ## Our package only
        })
        log = logging.getLogger("wifitest.soak")  ## A child of the configured logger
        for minute in range(8):  ## Simulate a long run writing many lines
            log.info("sample", extra={"ctx": {"bench": "bench07", "minute": minute, "mbps": 900 + minute}})  ## Structured fields
        logging.shutdown()  ## Flush and close the files
        print(sorted(p.name for p in Path(tmp).iterdir()))  ## Active file plus at most 2 backups
        print(log_path.read_text().splitlines()[-1])  ## The newest record, as JSON


if __name__ == "__main__":
    main()""",
            "under": "Before each write, RotatingFileHandler checks whether the record would push the file past `maxBytes`; if so it renames `soak.log.1` to `soak.log.2` (deleting the oldest beyond `backupCount`), renames `soak.log` to `soak.log.1`, and opens a fresh `soak.log`. `extra` keys become attributes on the LogRecord, which is why the formatter reads `record.ctx`. dictConfig replaces existing configuration unless `incremental` or `disable_existing_loggers: False` is used.",
            "gotchas": [
                {
                    "title": "Adding handlers more than once",
                    "note": "Calling a setup function per test adds another handler each time, so every line is duplicated. Configure once, or check for existing handlers.",
                    "wrong": """import logging, sys
def setup():
    log = logging.getLogger("lab")
    log.addHandler(logging.StreamHandler(sys.stdout))
    log.setLevel(logging.INFO)
    return log
for _ in range(3):
    log = setup()
log.info("ping ok")""",
                    "fixed": """import logging, sys
def setup():
    log = logging.getLogger("lab")
    if not log.handlers:
        log.addHandler(logging.StreamHandler(sys.stdout))
        log.setLevel(logging.INFO)
    return log
for _ in range(3):
    log = setup()
log.info("ping ok")""",
                }
            ],
            "best": "Keep logging configuration in one dictConfig (YAML in the repo), rotate long-running logs by size or time, and add structured context (bench, test, build, DUT) to every record. Write a separate log file per test case so each failure's evidence is self-contained.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Configure basicConfig to print `LEVEL: message` at DEBUG to stdout, then log one message at each of DEBUG, INFO and ERROR.",
            "solution": "basicConfig with level, format and stream.",
            "solution_code": """import logging, sys

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s", stream=sys.stdout)
logging.debug("raw: RSSI=-54")
logging.info("station associated")
logging.error("iperf3 failed")""",
        },
        {
            "level": "Medium",
            "prompt": "Create a logging.Filter that redacts any occurrence of a secret password from messages before they're written.",
            "solution": "A filter can modify the record; return True to keep it.",
            "solution_code": """import logging, sys


class Redact(logging.Filter):
    def __init__(self, secret):
        super().__init__()
        self.secret = secret

    def filter(self, record):
        record.msg = str(record.getMessage()).replace(self.secret, "****")
        record.args = ()
        return True


handler = logging.StreamHandler(sys.stdout)
handler.addFilter(Redact("Lab@1234"))
log = logging.getLogger("lab.ssh")
log.addHandler(handler)
log.setLevel(logging.INFO)
log.info("login admin/%s on %s", "Lab@1234", "10.0.0.11")""",
        },
        {
            "level": "Hard",
            "prompt": "Write a context manager `test_log(name, folder)` that attaches a FileHandler writing `<name>.log` to the 'wifitest' logger for the duration of a test and removes it afterwards. Show that only messages from inside the block land in the file.",
            "solution": "Add the handler on enter, remove and close it in finally.",
            "solution_code": """import logging, tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def test_log(name, folder):
    handler = logging.FileHandler(Path(folder) / f"{name}.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger = logging.getLogger("wifitest")
    logger.addHandler(handler)
    try:
        yield
    finally:
        logger.removeHandler(handler)
        handler.close()


log = logging.getLogger("wifitest.case")
logging.getLogger("wifitest").setLevel(logging.INFO)
with tempfile.TemporaryDirectory() as tmp:
    log.info("before the test")
    with test_log("roam_11r", tmp):
        log.info("roam started")
        log.warning("latency 72 ms")
    log.info("after the test")
    print((Path(tmp) / "roam_11r.log").read_text(), end="")""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Why use logging instead of print?", "a": "Levels let you filter noise, handlers send output to several destinations (console, files, log servers), formatters add timestamps and context, and libraries can log without deciding where output goes. print can't be filtered or redirected per module.", "follow": "Where should logging be configured? (Once, in the application's entry point; libraries only call getLogger.)"},
        {"level": "Intermediate", "q": "How does the logger hierarchy work?", "a": "Logger names are dotted paths; 'wifitest.drivers.ap' is a child of 'wifitest.drivers' and 'wifitest'. Records propagate to ancestor handlers unless propagate is False, and a logger without its own level inherits its parent's effective level.", "follow": "Why does a message appear twice? (Handlers on both the child and an ancestor, or a handler added twice.)"},
        {"level": "Intermediate", "q": "Why pass arguments instead of f-strings to log calls?", "a": "Logging formats the message only if the record is actually emitted, so disabled DEBUG calls cost almost nothing. f-strings are evaluated every time, including expensive reprs.", "follow": "When is the difference significant? (In hot loops or with expensive object representations.)"},
        {"level": "Advanced", "q": "How would you make logs searchable across many nightly runs?", "a": "Emit structured JSON lines with consistent fields (timestamp, level, logger, test, bench, build, DUT) using a custom formatter and extra context, ship them to a log store, and keep per-test files as CI artifacts. Then you can query by test or build across runs.", "follow": "How do you stop secrets leaking? (A redacting filter plus never logging credentials in the first place.)"},
    ],
    "quiz": [
        {"q": "Which level is lowest?", "options": ["INFO", "DEBUG", "WARNING", "ERROR"], "answer": 1, "why": "DEBUG < INFO < WARNING < ERROR < CRITICAL."},
        {"q": "Without any configuration, log.info('x')...", "options": ["Prints to stdout", "Prints nothing", "Raises", "Writes a file"], "answer": 1, "why": "The last-resort handler shows WARNING+ only."},
        {"q": "What does log.exception() add?", "options": ["A timestamp", "The current traceback", "A new handler", "Colour"], "answer": 1, "why": "It logs at ERROR with exc_info."},
        {"q": "Recommended logger name in a module?", "options": ["'root'", "__name__", "'logger'", "The file path"], "answer": 1, "why": "Mirrors the package hierarchy."},
        {"q": "Which handler caps file size?", "options": ["FileHandler", "StreamHandler", "RotatingFileHandler", "NullHandler"], "answer": 2, "why": "maxBytes + backupCount."},
    ],
    "cards": [
        {"front": "Module logger", "back": "`log = logging.getLogger(__name__)`"},
        {"front": "Lazy log formatting", "back": "`log.info('ch %s on %s', ch, ap)`"},
        {"front": "Log with traceback", "back": "`log.exception('msg')` inside except"},
        {"front": "Size-capped log", "back": "`RotatingFileHandler(path, maxBytes=..., backupCount=...)`"},
        {"front": "Structured fields", "back": "`log.info('msg', extra={...})` + a custom Formatter"},
    ],
}


M_4_6 = {
    "id": "4.6",
    "title": "Retry/Backoff & Signal Handling",
    "hours": 2,
    "summary": "Retrying transient failures with exponential backoff and jitter, making retries testable, idempotency, and cleaning up when Jenkins aborts a job.",
    "concepts": [
        {
            "title": "Exponential backoff with jitter",
            "concept": "A good retry policy waits longer after each failure (**exponential backoff**: 0.5 s, 1 s, 2 s, 4 s...), caps the wait, adds randomness (**jitter**) so many clients don't retry in lockstep, retries only **transient** errors (timeouts, refused connections) and gives up after a bounded number of attempts, re-raising the last error. Injecting the `sleep` function makes the policy testable without real waiting. The `tenacity` library offers the same policies as decorators.",
            "why": "After a reboot an AP refuses SSH for 30–90 seconds. Backoff rides that out without hammering the device, while a hard cap still fails the test in bounded time if the AP never comes back.",
            "syntax": "delay = min(cap, base * factor ** attempt) * random.uniform(0.5, 1.0)\n\n# tenacity equivalent\n@retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(initial=0.5, max=8),\n       retry=retry_if_exception_type(ConnectionError))",
            "code": """import random  ## Jitter
from typing import Callable  ## Type hints for the injected functions


def backoff_delays(attempts: int, base: float = 0.5, factor: float = 2.0, cap: float = 8.0, rng: random.Random | None = None) -> list[float]:  ## The wait before each retry
    rng = rng or random.Random()  ## Injectable RNG so tests are reproducible
    return [round(min(cap, base * factor ** n) * rng.uniform(0.5, 1.0), 2) for n in range(attempts)]  ## Exponential, capped, jittered


def call_with_retry(func: Callable[[], str], attempts: int, retry_on: tuple, sleep: Callable[[float], None], rng: random.Random) -> str:  ## sleep is injected
    delays = backoff_delays(attempts - 1, rng=rng)  ## One delay between each pair of attempts
    for attempt in range(1, attempts + 1):  ## Bounded number of tries
        try:  ## Try the operation
            return func()  ## Success ends the loop
        except retry_on as err:  ## Only transient errors are retried
            if attempt == attempts:  ## Out of attempts
                raise  ## Re-raise the last error unchanged
            print(f"attempt {attempt} failed ({err}); waiting {delays[attempt - 1]} s")  ## Visible in the log
            sleep(delays[attempt - 1])  ## Real code passes time.sleep; tests pass a recorder


def main() -> None:
    print(backoff_delays(6, rng=random.Random(7)))  ## Grows roughly x2 per step, capped at 8 s, with jitter
    state = {"calls": 0}  ## Counts connection attempts
    def ssh_connect() -> str:  ## The AP refuses the first three connections (still booting)
        state["calls"] += 1  ## Count this attempt
        if state["calls"] <= 3:  ## Still booting
            raise ConnectionRefusedError("port 22 refused")  ## A transient error
        return "connected"  ## Booted
    slept: list[float] = []  ## Records the waits instead of sleeping
    print(call_with_retry(ssh_connect, attempts=5, retry_on=(ConnectionError,), sleep=slept.append, rng=random.Random(7)))  ## Succeeds on try 4
    print("total wait:", round(sum(slept), 2), "s over", len(slept), "retries")  ## Instant in tests, real waits in production
    try:  ## A non-transient error is NOT retried
        call_with_retry(lambda: int("not-a-number"), attempts=5, retry_on=(ConnectionError,), sleep=slept.append, rng=random.Random(7))  ## ValueError
    except ValueError as err:  ## Raised on the first attempt
        print("not retried:", err)  ## Bugs fail fast


if __name__ == "__main__":
    main()""",
            "under": "Without jitter, many clients that failed at the same moment retry at exactly the same moments too, recreating the overload (the \"thundering herd\"). Multiplying by a random factor spreads them out. `ConnectionRefusedError` is a subclass of `ConnectionError`, which is itself an `OSError`, so catching the base class covers refused, reset and aborted connections.",
            "gotchas": [
                {
                    "title": "Retrying an operation that isn't idempotent",
                    "note": "The command actually succeeded but the reply was lost, so the retry adds the VLAN a second time. Make operations idempotent (set state, don't append) or check before retrying.",
                    "wrong": """vlans = []
lost_reply = {"first": True}
def add_vlan(v):
    vlans.append(v)
    if lost_reply.pop("first", False):
        raise TimeoutError("reply lost")
for attempt in range(2):
    try:
        add_vlan(100)
        break
    except TimeoutError:
        pass
print(vlans)""",
                    "fixed": """vlans = set()
lost_reply = {"first": True}
def ensure_vlan(v):
    vlans.add(v)
    if lost_reply.pop("first", False):
        raise TimeoutError("reply lost")
for attempt in range(2):
    try:
        ensure_vlan(100)
        break
    except TimeoutError:
        pass
print(sorted(vlans))""",
                }
            ],
            "best": "Retry only operations that are safe to repeat, only for transient exception types, with exponential backoff, a cap, jitter and a bounded total time. Log every retry. Inject `sleep` and the RNG so unit tests run instantly and deterministically.",
        },
        {
            "title": "Signals, Ctrl+C and guaranteed cleanup",
            "local_only": SIGNAL_NOTE,
            "concept": "When Jenkins aborts a job or someone presses Ctrl+C, your process receives a **signal**: SIGINT becomes `KeyboardInterrupt`; SIGTERM, by default, kills the process **without** running `finally` blocks. Installing a handler with `signal.signal(signal.SIGTERM, handler)` that raises an exception turns termination into normal unwinding, so `finally` blocks and context managers restore lab state. `atexit.register(func)` runs func at normal interpreter exit.",
            "why": "An aborted nightly run must still reset attenuators, stop captures and release the bench lock; otherwise the next job starts on a bench left at 60 dB with a capture filling the disk.",
            "syntax": "class Aborted(Exception): ...\ndef on_term(signum, frame):\n    raise Aborted(signal.Signals(signum).name)\nsignal.signal(signal.SIGTERM, on_term)\n\natexit.register(release_bench_lock)",
            "code": """import atexit  ## Run functions at interpreter exit
import os  ## os.kill to send ourselves a signal (simulating a Jenkins abort)
import signal  ## Signal handling (POSIX)


class JobAborted(Exception):  ## Our own exception for "stop now, but clean up"
    pass  ## No extra behaviour needed


def on_terminate(signum: int, frame) -> None:  ## Signal handler: runs in the main thread between bytecodes
    raise JobAborted(signal.Signals(signum).name)  ## Convert the signal into an exception so finally blocks run


def main() -> None:
    signal.signal(signal.SIGTERM, on_terminate)  ## Install the handler (the default would kill us without cleanup)
    atexit.register(lambda: print("atexit: bench lock released"))  ## Runs when the interpreter exits normally
    attenuator = {"db": 0}  ## Lab state to protect
    try:  ## The long-running test
        attenuator["db"] = 60  ## Change lab state
        for step in range(1000):  ## A long sweep
            if step == 3:  ## Simulate Jenkins aborting the job mid-sweep
                os.kill(os.getpid(), signal.SIGTERM)  ## Send SIGTERM to ourselves
    except JobAborted as err:  ## The handler's exception unwinds normally
        print("aborted by", err, "at step", step)  ## Know where we stopped
    finally:  ## Always runs now
        attenuator["db"] = 0  ## Restore the bench
        print("attenuator restored to", attenuator["db"], "dB")  ## Evidence of cleanup
    try:  ## KeyboardInterrupt is a BaseException, not an Exception
        try:  ## Inner handler that catches "everything"
            raise KeyboardInterrupt  ## As if Ctrl+C were pressed
        except Exception:  ## Does NOT catch KeyboardInterrupt
            print("never printed")  ## Skipped
    except KeyboardInterrupt:  ## Caught here instead
        print("Ctrl+C still stops the program")  ## Users can always interrupt


if __name__ == "__main__":
    main()""",
            "under": "Python's C-level signal handler only sets a flag; the Python-level handler runs in the main thread at the next bytecode boundary, which is why raising from it is safe. Jenkins sends SIGTERM first and SIGKILL after a grace period (SIGKILL can't be caught), so cleanup must be quick. `atexit` functions don't run on SIGKILL or `os._exit()`.",
            "gotchas": [
                {
                    "title": "Swallowing Ctrl+C with a bare except",
                    "local_only": SIGNAL_NOTE,
                    "note": "A bare except catches KeyboardInterrupt, so a polling loop can't be interrupted. `except Exception` lets it through.",
                    "wrong": """import os, signal
caught = []
for attempt in range(3):
    try:
        os.kill(os.getpid(), signal.SIGINT)
    except:
        caught.append(attempt)
print("Ctrl+C swallowed", len(caught), "times; loop kept running")""",
                    "fixed": """import os, signal
caught = []
try:
    for attempt in range(3):
        try:
            os.kill(os.getpid(), signal.SIGINT)
        except Exception:
            caught.append(attempt)
except KeyboardInterrupt:
    print("Ctrl+C stopped the loop after", len(caught), "swallowed attempts")""",
                }
            ],
            "best": "Install a SIGTERM handler at startup that raises a dedicated exception, put all lab-state restoration in finally blocks or context managers, keep cleanup fast enough to finish within the CI's kill timeout, and never catch BaseException or use a bare except.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Print the un-jittered backoff schedule for 6 attempts with base 1 s, factor 2 and cap 10 s.",
            "solution": "min(cap, base * factor ** n) for n in range(6).",
            "solution_code": """print([min(10, 1 * 2 ** n) for n in range(6)])""",
        },
        {
            "level": "Medium",
            "prompt": "Write a `@retry(times, on)` decorator that records sleeps through an injectable `sleep` argument, and test that a function failing twice succeeds on the third call with two recorded sleeps.",
            "solution": "Combine the decorator factory from Module 3.8 with dependency injection.",
            "solution_code": """import functools


def retry(times, on, sleep, delay=1.0):
    def deco(func):
        @functools.wraps(func)
        def wrapper(*a, **kw):
            for attempt in range(1, times + 1):
                try:
                    return func(*a, **kw)
                except on:
                    if attempt == times:
                        raise
                    sleep(delay * 2 ** (attempt - 1))
        return wrapper
    return deco


waits, calls = [], {"n": 0}


@retry(times=4, on=(TimeoutError,), sleep=waits.append)
def get_uptime():
    calls["n"] += 1
    if calls["n"] < 3:
        raise TimeoutError
    return "up 3 min"


print(get_uptime(), waits)""",
        },
        {
            "level": "Hard",
            "local_only": SIGNAL_NOTE,
            "prompt": "Use signal.alarm (POSIX) as a whole-test watchdog: raise a custom exception if a 'hung' operation runs longer than 1 second, and cancel the alarm in finally.",
            "solution": "signal.alarm schedules SIGALRM; the handler raises; alarm(0) cancels it.",
            "solution_code": """import signal, time


class Watchdog(Exception):
    pass


def on_alarm(signum, frame):
    raise Watchdog("test exceeded 1 s")


signal.signal(signal.SIGALRM, on_alarm)
signal.alarm(1)
try:
    time.sleep(5)
except Watchdog as err:
    print("Watchdog:", err)
finally:
    signal.alarm(0)
print("alarm cancelled, continuing")""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "Describe a good retry policy.", "a": "Retry only transient, idempotent operations; use exponential backoff with a cap and jitter; bound attempts or total time; log each retry; re-raise the last error at the end. Never retry assertion failures or programming errors.", "follow": "Why jitter? (To avoid synchronised retries from many clients overloading a recovering service.)"},
        {"level": "Intermediate", "q": "What does idempotent mean, and why does it matter for retries?", "a": "An operation is idempotent if doing it twice has the same effect as once ('set channel 36' vs 'add VLAN'). A retry after a lost reply re-executes the operation, so non-idempotent operations can be applied twice.", "follow": "How do you make 'add VLAN' safe? (Check-then-create or an 'ensure present' operation.)"},
        {"level": "Advanced", "q": "How do you clean up when Jenkins aborts a Python job?", "a": "Jenkins sends SIGTERM (then SIGKILL after a timeout). Install a SIGTERM handler that raises an exception, so finally blocks and context managers run; keep cleanup quick; and design the next run to detect and recover any state left by a SIGKILL.", "follow": "Can you catch SIGKILL? (No.)"},
        {"level": "Beginner", "q": "Why doesn't except Exception catch KeyboardInterrupt?", "a": "KeyboardInterrupt and SystemExit derive from BaseException, not Exception, precisely so that broad handlers don't stop users or sys.exit from ending the program.", "follow": "What does a bare except catch? (Everything, including those.)"},
    ],
    "quiz": [
        {"q": "Why inject the sleep function into retry code?", "options": ["Speed in production", "Instant, deterministic tests", "Thread safety", "Required by tenacity"], "answer": 1, "why": "Tests record waits instead of sleeping."},
        {"q": "Which errors should be retried?", "options": ["AssertionError", "ValueError from bad input", "ConnectionRefusedError while a device boots", "SyntaxError"], "answer": 2, "why": "Transient failures only."},
        {"q": "By default, SIGTERM in Python...", "options": ["Raises KeyboardInterrupt", "Terminates without running finally", "Is ignored", "Raises SystemExit"], "answer": 1, "why": "Install a handler to unwind cleanly."},
        {"q": "KeyboardInterrupt inherits from...", "options": ["Exception", "BaseException", "RuntimeError", "OSError"], "answer": 1, "why": "So except Exception lets it through."},
        {"q": "What does jitter prevent?", "options": ["Long waits", "Synchronised retries (thundering herd)", "Exceptions", "Logging noise"], "answer": 1, "why": "It spreads retries out."},
    ],
    "cards": [
        {"front": "Backoff formula", "back": "min(cap, base * factor**n) * random.uniform(0.5, 1)"},
        {"front": "What to retry", "back": "Transient + idempotent operations only."},
        {"front": "Clean up on Jenkins abort", "back": "SIGTERM handler that raises → finally blocks run."},
        {"front": "atexit", "back": "Runs at normal exit; not on SIGKILL or os._exit."},
    ],
}


M_4_7 = {
    "id": "4.7",
    "title": "Scheduling",
    "hours": 1,
    "summary": "Running lab jobs periodically: cron syntax and pitfalls, drift-free loops, the standard-library sched module, and the schedule library.",
    "concepts": [
        {
            "title": "Periodic jobs without drift",
            "concept": "**cron** runs commands on a calendar schedule (`minute hour day month weekday`) and suits jobs that start fresh each time. Inside a long-running Python process, a loop that sleeps a fixed interval **after** the work slowly drifts later, because the work itself takes time; scheduling against an absolute deadline (`next_run += interval`) doesn't drift. The standard-library `sched` module and the `schedule` package provide in-process schedulers.",
            "why": "A sanity check every hour, an RSSI sample every second for a 12-hour soak, and a nightly report at 06:00 all need reliable timing. A sampler that drifts by 50 ms per sample is off by ten minutes by morning.",
            "syntax": "# cron: m h dom mon dow   command\n45 5 * * 1-5  /opt/lab/venv/bin/python -m wifitool sanity >> /var/log/sanity.log 2>&1\n\nnext_run = time.monotonic()\nwhile True:\n    work()\n    next_run += interval\n    time.sleep(max(0, next_run - time.monotonic()))",
            "code": """import sched  ## Standard-library event scheduler
import time  ## Monotonic clock and sleep


def drifting_loop(samples: int, interval: float, work_s: float) -> float:  ## Sleep a fixed time after the work
    t0 = time.monotonic()  ## Start
    for _ in range(samples):  ## Each sample
        time.sleep(work_s)  ## The work takes time...
        time.sleep(interval)  ## ...and the full interval is added on top
    return time.monotonic() - t0  ## Total elapsed


def deadline_loop(samples: int, interval: float, work_s: float) -> float:  ## Schedule against absolute deadlines
    t0 = time.monotonic()  ## Start
    next_run = t0  ## First deadline is now
    for _ in range(samples):  ## Each sample
        time.sleep(work_s)  ## The same work
        next_run += interval  ## The next deadline, independent of how long the work took
        time.sleep(max(0.0, next_run - time.monotonic()))  ## Sleep only the remaining time
    return time.monotonic() - t0  ## Total elapsed


def main() -> None:
    drift = drifting_loop(samples=5, interval=0.05, work_s=0.02)  ## Ideal total: 5 x 0.05 = 0.25 s
    steady = deadline_loop(samples=5, interval=0.05, work_s=0.02)  ## Same work, deadline-based
    print("drifting loop over 0.33 s:", drift > 0.33, "| deadline loop under 0.3 s:", steady < 0.3)  ## The work time accumulates in the first only
    s = sched.scheduler(time.monotonic, time.sleep)  ## A scheduler using the monotonic clock
    log: list[str] = []  ## Record what ran, in order
    for delay, name in [(0.06, "report"), (0.02, "ping"), (0.04, "rssi")]:  ## Events registered out of order
        s.enter(delay, 1, lambda n=name: log.append(n))  ## Run after `delay` seconds (default arg captures the name)
    s.run()  ## Blocks until every event has run, in time order
    print(log)  ## ping, rssi, report


if __name__ == "__main__":
    main()""",
            "under": "`sched.scheduler` keeps a heap of (time, priority, action) events and repeatedly sleeps until the earliest one is due. Deadline-based loops still can't run faster than the work itself: if one iteration overruns, the next sleeps zero and the loop catches up. cron starts each job in a minimal environment (short PATH, no shell profile), which is why scripts that work in a terminal fail under cron.",
            "gotchas": [
                {
                    "title": "Cron's minimal environment",
                    "note": "cron doesn't load your shell profile, so tools on your interactive PATH aren't found. Use absolute paths (or set PATH in the crontab) and the venv's python. This demo runs a command with a cron-like PATH.",
                    "local_only": "starts a subprocess with a modified environment",
                    "wrong": """import subprocess
env = {"PATH": "/usr/bin:/bin"}
r = subprocess.run("lab-sanity-tool --quick", shell=True, env=env, capture_output=True, text=True)
print("exit", r.returncode, "|", "not found" in r.stderr)""",
                    "fixed": """import subprocess, sys
env = {"PATH": "/usr/bin:/bin"}
r = subprocess.run([sys.executable, "-c", "print('sanity ok')"], env=env, capture_output=True, text=True)
print("exit", r.returncode, "|", r.stdout.strip())""",
                }
            ],
            "best": "Use cron (or a CI scheduler) for jobs that start fresh, with absolute paths and output redirected to a log. Use deadline-based loops for in-process sampling. Prefer CI-scheduled jobs for anything whose results people need to see, so failures show up where the team looks.",
        },
        {
            "title": "The schedule library",
            "local_only": SCHEDULE_NOTE,
            "concept": "`schedule` expresses in-process schedules in readable Python: `schedule.every(10).seconds.do(job)`, `schedule.every().day.at(\"06:00\").do(report)`. Your loop calls `schedule.run_pending()` regularly, and `idle_seconds()` tells you how long to sleep. Jobs can be tagged and cancelled. It's simple and single-threaded: a slow job delays the others.",
            "why": "A small lab daemon that pings every DUT each minute and posts a summary each morning is a dozen lines with schedule, and needs no cron access on the bench machine.",
            "syntax": "schedule.every(1).minutes.do(ping_all)\nschedule.every().monday.at(\"06:00\").do(weekly_report)\nwhile True:\n    schedule.run_pending()\n    time.sleep(schedule.idle_seconds() or 1)",
            "code": """import time  ## Sleep between checks

import schedule  ## Third-party: pip install schedule


def main() -> None:
    ran: list[str] = []  ## What ran, in order
    schedule.every(0.05).seconds.do(lambda: ran.append("ping"))  ## Fractional seconds are allowed (handy for demos)
    schedule.every(0.12).seconds.do(lambda: ran.append("rssi")).tag("sampling")  ## Tag jobs to manage them as a group
    deadline = time.monotonic() + 0.3  ## Run the scheduler loop for 0.3 s
    while time.monotonic() < deadline:  ## The usual main loop
        schedule.run_pending()  ## Run every job that is due
        time.sleep(0.01)  ## Short nap between checks
    print("pings:", ran.count("ping") >= 4, "| rssi samples:", ran.count("rssi") >= 2)  ## Roughly 6 and 2; exact counts vary
    schedule.clear("sampling")  ## Cancel the tagged jobs
    print("jobs left:", len(schedule.get_jobs()))  ## Only the ping job remains
    schedule.clear()  ## Cancel everything


if __name__ == "__main__":
    main()""",
            "under": "Each Job stores its interval and `next_run` time. `run_pending()` runs every job whose `next_run` is in the past, in order, on the calling thread, and then computes its next run. That's why one slow job delays all others; long work belongs in a thread or a separate process.",
            "gotchas": [],
            "best": "Use schedule for small, single-purpose daemons; keep each job short and wrap it in try/except plus logging so one failure doesn't kill the loop. For anything critical or multi-host, use cron, systemd timers or CI schedules instead.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write the crontab line that runs `/opt/lab/venv/bin/python -m wifitool sanity` at 05:45 Monday to Friday and appends output and errors to /var/log/sanity.log. Print it.",
            "solution": "Fields: minute hour day-of-month month day-of-week.",
            "solution_code": """print("45 5 * * 1-5 /opt/lab/venv/bin/python -m wifitool sanity >> /var/log/sanity.log 2>&1")""",
        },
        {
            "level": "Medium",
            "prompt": "Write `sample_every(interval, count, read)` that calls `read()` on a deadline schedule and returns the list of offsets (rounded to 0.01 s) at which reads happened.",
            "solution": "Track next_run against the monotonic clock.",
            "solution_code": """import time


def sample_every(interval, count, read):
    t0 = time.monotonic()
    next_run = t0
    offsets = []
    for _ in range(count):
        read()
        offsets.append(round(time.monotonic() - t0, 2))
        next_run += interval
        time.sleep(max(0, next_run - time.monotonic()))
    return offsets


print(sample_every(0.05, 4, lambda: time.sleep(0.01)))""",
        },
        {
            "level": "Hard",
            "prompt": "Make a tiny job runner over sched that re-schedules itself every interval, catches and records exceptions from a flaky job without stopping, and stops after N runs.",
            "solution": "The action re-enters itself; try/except inside keeps the scheduler alive.",
            "solution_code": """import sched, time

s = sched.scheduler(time.monotonic, time.sleep)
results = []


def flaky_ping(run):
    if run == 2:
        raise TimeoutError("ap-3 no reply")
    return "ok"


def job(run, remaining):
    try:
        results.append(flaky_ping(run))
    except TimeoutError as err:
        results.append(f"error: {err}")
    if remaining > 1:
        s.enter(0.02, 1, job, (run + 1, remaining - 1))


s.enter(0, 1, job, (1, 4))
s.run()
print(results)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Read this cron expression: `0 2 * * *`.", "a": "Every day at 02:00. Fields are minute, hour, day of month, month and day of week.", "follow": "And `*/15 * * * *`? (Every 15 minutes.)"},
        {"level": "Intermediate", "q": "Why does a script work in your terminal but fail in cron?", "a": "cron uses a minimal environment: short PATH, no shell profile, different working directory, no virtualenv activation. Use absolute paths to the interpreter and tools, set any needed variables in the crontab, and log output to a file.", "follow": "How do you see why it failed? (Redirect stdout and stderr to a log: `>> log 2>&1`.)"},
        {"level": "Intermediate", "q": "How do you avoid drift in a periodic sampler?", "a": "Schedule against absolute deadlines on the monotonic clock (next_run += interval; sleep until next_run) instead of sleeping a fixed interval after each piece of work.", "follow": "What happens if the work takes longer than the interval? (The loop runs back-to-back until it catches up; consider skipping missed slots.)"},
        {"level": "Advanced", "q": "cron vs CI-scheduled jobs for nightly regression?", "a": "CI scheduling gives visibility (results and logs where the team looks), parameters, locking of lab resources, retries and notifications. cron is fine for simple host-local tasks like log rotation or a health ping.", "follow": "How do you prevent overlapping runs? (CI concurrency limits or locks; in cron, flock.)"},
    ],
    "quiz": [
        {"q": "`45 5 * * 1-5` runs...", "options": ["Every 45 minutes", "05:45 on weekdays", "45th day", "5 times an hour"], "answer": 1, "why": "Minute 45, hour 5, Monday–Friday."},
        {"q": "Which loop doesn't drift?", "options": ["sleep(interval) after work", "next_run += interval; sleep until next_run", "while True without sleep", "time.time() comparisons"], "answer": 1, "why": "Deadline-based scheduling."},
        {"q": "What does schedule.run_pending() do?", "options": ["Starts a thread", "Runs jobs that are due", "Sleeps until the next job", "Clears jobs"], "answer": 1, "why": "Your loop calls it regularly."},
        {"q": "Why do cron jobs often fail to find tools?", "options": ["cron is slow", "Minimal PATH/environment", "cron runs as Windows", "Tools need a GUI"], "answer": 1, "why": "No shell profile is loaded."},
    ],
    "cards": [
        {"front": "Cron fields", "back": "minute hour day-of-month month day-of-week"},
        {"front": "Drift-free loop", "back": "next_run += interval; sleep(max(0, next_run - monotonic()))"},
        {"front": "In-process scheduler (stdlib)", "back": "`sched.scheduler(time.monotonic, time.sleep)`"},
        {"front": "schedule library loop", "back": "`schedule.run_pending()` + short sleep"},
    ],
}


M_4_8 = {
    "id": "4.8",
    "title": "Packaging a Script as an Installable CLI",
    "hours": 2,
    "summary": "The src layout, pyproject.toml with [project.scripts] entry points, how installers turn them into commands, versions at runtime, and installing tools with pipx or uv.",
    "concepts": [
        {
            "title": "pyproject.toml and entry points",
            "concept": "A modern Python package is described by `pyproject.toml`: `[build-system]` names the build backend, `[project]` holds the name, version, Python requirement and dependencies, and `[project.scripts]` maps **command names** to `module:function` **entry points**. When the package is installed, the installer writes a small launcher (`wifitool`, or `wifitool.exe` on Windows) that imports the module and calls the function. The **src layout** (`src/wifitool/...`) ensures tests run against the installed package, not stray files.",
            "why": "Everyone on the team and every Jenkins agent gets the same `wifitool` command at the same version with one install command, instead of copying scripts around and fixing sys.path by hand.",
            "syntax": "[build-system]\nrequires = [\"hatchling\"]\nbuild-backend = \"hatchling.build\"\n\n[project]\nname = \"wifitool\"\nversion = \"1.4.0\"\nrequires-python = \">=3.11\"\ndependencies = [\"typer>=0.12\"]\n\n[project.scripts]\nwifitool = \"wifitool.cli:main\"\n\n$ pip install -e .     # or: uv tool install . / pipx install .",
            "code": """import importlib  ## Import a module by name, as the generated launcher does
import sys  ## sys.path for the temporary project
import tempfile  ## Scratch project directory
import tomllib  ## Standard-library TOML parser (3.11+)
from pathlib import Path  ## Writing the project files

PYPROJECT = '''[project]
name = "wifitool"
version = "1.4.0"
requires-python = ">=3.11"

[project.scripts]
wifitool = "wifitool.cli:main"
'''  ## A minimal pyproject.toml (build-system omitted for brevity)

CLI = '''def main() -> int:
    print("wifitool 1.4.0: sweep, scan, report")
    return 0
'''  ## src/wifitool/cli.py: the function the command runs


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:  ## A throwaway project
        root = Path(tmp)  ## Project root
        (root / "pyproject.toml").write_text(PYPROJECT)  ## Package metadata
        pkg = root / "src" / "wifitool"  ## src layout: code lives under src/
        pkg.mkdir(parents=True)  ## Create the package folder
        (pkg / "__init__.py").write_text('__version__ = "1.4.0"\\n')  ## Marks the package
        (pkg / "cli.py").write_text(CLI)  ## The entry-point module
        meta = tomllib.loads((root / "pyproject.toml").read_text())  ## Parse the TOML into dicts
        print(meta["project"]["name"], meta["project"]["version"], meta["project"]["requires-python"])  ## Core metadata
        scripts = meta["project"]["scripts"]  ## {"wifitool": "wifitool.cli:main"}
        sys.path.insert(0, str(root / "src"))  ## What an install effectively does: make the package importable
        try:  ## Resolve each entry point like the generated launcher
            for command, target in scripts.items():  ## command name -> "module:function"
                module_name, func_name = target.split(":")  ## Split the reference
                func = getattr(importlib.import_module(module_name), func_name)  ## Import the module and fetch the function
                print(f"$ {command}")  ## Pretend we typed the command
                print("exit code:", func())  ## The launcher calls sys.exit(func())
        finally:  ## Undo the import-path change
            sys.path.remove(str(root / "src"))  ## Clean up
            for name in [m for m in sys.modules if m.startswith("wifitool")]:  ## Forget the modules
                del sys.modules[name]  ## So nothing leaks into later code


if __name__ == "__main__":
    main()""",
            "under": "Installing a package (from a wheel, or in editable mode with `pip install -e .`) writes its metadata into `site-packages/<name>-<version>.dist-info/`, including `entry_points.txt`. For each console script the installer creates an executable wrapper in the environment's `bin/` (or `Scripts\\`) directory that runs `from wifitool.cli import main; sys.exit(main())`. `pipx` and `uv tool install` put each tool in its own isolated environment and link just the command onto your PATH.",
            "gotchas": [
                {
                    "title": "Flat layout tests pass by accident",
                    "note": "With the package next to the tests, Python imports the local folder even if packaging is broken (say, a missing file). The src layout forces tests to use the installed package. This shows which copy gets imported.",
                    "wrong": """import sys, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory() as tmp:
    (Path(tmp) / "wifitool").mkdir()
    (Path(tmp) / "wifitool" / "__init__.py").write_text("WHERE = 'local folder, not the installed package'\\n")
    sys.path.insert(0, tmp)
    import wifitool
    print(wifitool.WHERE)
    sys.path.remove(tmp); del sys.modules["wifitool"]""",
                    "fixed": """import sys, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory() as tmp:
    (Path(tmp) / "src" / "wifitool").mkdir(parents=True)
    (Path(tmp) / "src" / "wifitool" / "__init__.py").write_text("WHERE = 'src layout: only importable once installed'\\n")
    sys.path.insert(0, tmp)
    try:
        import wifitool
    except ModuleNotFoundError as err:
        print("not importable without installing:", err.name)
    sys.path.remove(tmp)""",
                }
            ],
            "best": "Use the src layout, one `pyproject.toml`, `[project.scripts]` for every CLI, and pinned versions. Install tools for daily use with `uv tool install` or `pipx`, and install the framework in editable mode (`pip install -e .`) while developing it.",
        },
        {
            "title": "Versions and metadata at runtime",
            "concept": "`importlib.metadata.version(\"name\")` reads the installed version of any distribution; it raises `PackageNotFoundError` if the package isn't installed (for example when running from a source checkout). Reporting the framework version, Python version and key dependency versions at the start of every run makes results reproducible. `packaging.version.Version` compares versions correctly (`4.10.0 > 4.9.9`), which plain string comparison doesn't.",
            "why": "When a nightly result differs from last week's, the first question is \"which framework and which library versions ran?\". A version banner in every log answers it immediately.",
            "syntax": "from importlib.metadata import version, PackageNotFoundError\ntry:\n    __version__ = version(\"wifitool\")\nexcept PackageNotFoundError:\n    __version__ = \"0+unknown\"",
            "code": """import platform  ## Python version
from importlib.metadata import PackageNotFoundError, version  ## Installed-distribution metadata


def dist_version(name: str) -> str:  ## Version of an installed package, or a marker if absent
    try:  ## Look it up in the installed metadata
        return version(name)  ## e.g. "2.13.5"
    except PackageNotFoundError:  ## Not installed (or running from a source tree)
        return "not installed"  ## Make the gap visible instead of crashing


def version_key(v: str) -> tuple[int, ...]:  ## Compare dotted versions numerically
    return tuple(int(part) for part in v.split("."))  ## "4.10.0" -> (4, 10, 0)


def main() -> None:
    print("python major version:", platform.python_version_tuple()[0])  ## A real banner prints the full version
    print("wifitool:", dist_version("wifitool-that-is-not-installed"))  ## Graceful fallback
    builds = ["4.9.9", "4.10.0", "4.32.1", "4.4.0"]  ## DUT firmware builds
    print(sorted(builds))  ## String sort: wrong, "4.10.0" sorts before "4.4.0"
    print(sorted(builds, key=version_key))  ## Numeric sort: correct
    print(max(builds, key=version_key))  ## The newest build


if __name__ == "__main__":
    main()""",
            "under": "`importlib.metadata` searches the `*.dist-info` and `*.egg-info` folders on `sys.path`, reads the `METADATA` file and returns the `Version` field. It works for any installed distribution, including ones installed in editable mode. Real-world version strings can contain pre-release and local parts (`4.32.1rc2+lab`), which is why the `packaging` library's `Version` class is the robust choice for comparisons.",
            "gotchas": [
                {
                    "title": "Comparing version strings directly",
                    "note": "String comparison goes character by character, so '4.10' is \"less\" than '4.9'. Convert to numeric tuples (or packaging.version.Version).",
                    "wrong": """print("4.10.0" > "4.9.9", max(["4.9.9", "4.10.0"]))""",
                    "fixed": """def key(v):
    return tuple(int(x) for x in v.split("."))
print(key("4.10.0") > key("4.9.9"), max(["4.9.9", "4.10.0"], key=key))""",
                }
            ],
            "best": "Single-source the version (in pyproject.toml, or from git tags with hatch-vcs/setuptools-scm), read it at runtime with importlib.metadata, print a version banner (framework, Python, key libraries, DUT build) at the start of every run, and compare versions numerically.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Parse a pyproject.toml string with tomllib and print its dependency list.",
            "solution": "tomllib.loads returns nested dicts.",
            "solution_code": """import tomllib

text = '''[project]
name = "wifitool"
version = "1.4.0"
dependencies = ["typer>=0.12", "pydantic>=2", "pyyaml"]
'''
print(tomllib.loads(text)["project"]["dependencies"])""",
        },
        {
            "level": "Medium",
            "prompt": "Write `parse_entry_point('wifitool.cli:main')` returning (module, attribute) and validating the format, raising ValueError for strings without exactly one colon.",
            "solution": "partition on ':' and check both sides are non-empty.",
            "solution_code": """def parse_entry_point(ref):
    module, sep, attr = ref.partition(":")
    if not sep or not module or not attr or ":" in attr:
        raise ValueError(f"bad entry point {ref!r}; expected 'module:function'")
    return module, attr


print(parse_entry_point("wifitool.cli:main"))
for bad in ["wifitool.cli.main", "a:b:c"]:
    try:
        parse_entry_point(bad)
    except ValueError as err:
        print("ValueError:", err)""",
        },
        {
            "level": "Hard",
            "prompt": "Write a version banner function returning a dict of Python version (major.minor) and the versions of a list of distributions, marking missing ones, then print it as sorted JSON.",
            "solution": "Combine sys.version_info and importlib.metadata with a fallback.",
            "solution_code": """import json, sys
from importlib.metadata import PackageNotFoundError, version


def banner(dists):
    out = {"python": f"{sys.version_info.major}.{sys.version_info.minor}"}
    for d in dists:
        try:
            out[d] = version(d)
        except PackageNotFoundError:
            out[d] = "missing"
    return out


info = banner(["surely-not-installed-lab-lib"])
print(json.dumps(info, sort_keys=True).replace(info["python"], "3.x"))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What is an entry point / console script?", "a": "A mapping in [project.scripts] from a command name to 'module:function'. On install, the installer creates an executable wrapper that imports the module, calls the function and exits with its return value.", "follow": "Where does the wrapper go? (The environment's bin/ or Scripts\\ directory.)"},
        {"level": "Intermediate", "q": "Why the src layout?", "a": "Code under src/ isn't importable from the project root by accident, so tests must run against the installed package; packaging mistakes (missing modules, data files) show up in CI instead of in users' environments.", "follow": "How do you develop against it? (pip install -e . for an editable install.)"},
        {"level": "Intermediate", "q": "wheel vs sdist?", "a": "A wheel is a built, ready-to-install archive (no build step at install time). An sdist is a source archive that must be built on the target machine. Publish both; installers prefer wheels.", "follow": "What does pyproject's [build-system] do? (Declares the backend, e.g. hatchling or setuptools, used to build them.)"},
        {"level": "Advanced", "q": "How do you make test runs reproducible across agents?", "a": "Pin dependencies with a lock file (uv.lock, pip-tools), install the framework as a versioned package, use the same Python version (container or uv-managed), and log a version banner at the start of each run.", "follow": "Why compare versions with packaging.version? (It handles pre-releases and numeric ordering correctly.)"},
    ],
    "quiz": [
        {"q": "Which table defines CLI commands in pyproject.toml?", "options": ["[tool.scripts]", "[project.scripts]", "[build-system]", "[project.cli]"], "answer": 1, "why": "Console script entry points."},
        {"q": "`'4.10.0' > '4.9.9'` as strings is...", "options": ["True", "False", "Error", "None"], "answer": 1, "why": "'1' < '9' character-wise."},
        {"q": "What does `pip install -e .` do?", "options": ["Encrypts the package", "Editable install pointing at your source", "Installs only dependencies", "Builds a wheel only"], "answer": 1, "why": "Changes to source take effect immediately."},
        {"q": "importlib.metadata.version raises what for a missing package?", "options": ["KeyError", "PackageNotFoundError", "ImportError", "Returns None"], "answer": 1, "why": "Catch it to fall back."},
        {"q": "Which installs a CLI tool into its own isolated environment?", "options": ["pip install --user", "pipx install / uv tool install", "python setup.py", "conda list"], "answer": 1, "why": "One environment per tool."},
    ],
    "cards": [
        {"front": "Console script", "back": "`[project.scripts] wifitool = 'wifitool.cli:main'`"},
        {"front": "src layout", "back": "Code in src/pkg so tests use the installed package."},
        {"front": "Installed version at runtime", "back": "`importlib.metadata.version('name')`"},
        {"front": "Compare versions", "back": "Numeric tuples or packaging.version.Version, never raw strings."},
    ],
}
