"""Phase 9 content: modules 9.1-9.5 (debugging, SQL, patterns, clean code, review)."""

from net_support import needs

PDB = "drives pdb in a subprocess with scripted commands, which the in-browser runner can't do"
SQLITE = "uses sqlite3, which this in-browser runner doesn't bundle"
SQLA = needs("sqlalchemy")

M_9_1 = {
    "id": "9.1",
    "title": "Debugging",
    "hours": 2,
    "summary": "Find bugs quickly: read tracebacks properly, chain and annotate exceptions, capture context with the traceback module, and step through code with pdb and breakpoint().",
    "concepts": [
        {
            "title": "Tracebacks, exception chaining and notes",
            "concept": "A traceback lists the call stack from the outermost call (top) to where the exception was raised (bottom); read it **bottom-up**: last line is the exception, the frame above is where it happened. When you catch an exception and raise a clearer one, use `raise NewError(...) from err` so both appear (\"The above exception was the direct cause...\"). `err.add_note(...)` (Python 3.11+) attaches context such as the bench or AP name without changing the exception type. The `traceback` module formats all of this as text for logs and reports.",
            "why": "A failure at 3 a.m. in a nightly run is debugged from its log alone. 'KeyError: channel' tells you nothing; 'ConfigError: ap-lab-07 radio 6G has no channel' with the original KeyError chained below tells you exactly where to look.",
            "syntax": "try:\n    ...\nexcept KeyError as err:\n    err.add_note(f\"while configuring {ap}\")\n    raise ConfigError(\"...\") from err\n\ntraceback.format_exception(exc)",
            "code": """import traceback  ## Format exceptions as text


class ConfigError(Exception):  ## Domain-specific error type
    pass  ## No extra behaviour needed


def radio_channel(cfg, band):  ## Low-level lookup
    return cfg["radios"][band]["channel"]  ## KeyError if anything is missing


def configure(ap, cfg):  ## Higher-level operation
    try:  ## Translate low-level errors into meaningful ones
        return {band: radio_channel(cfg, band) for band in ("5G", "6G")}  ## Look up both radios
    except KeyError as err:  ## Something missing in the config
        err.add_note(f"bench config for {ap}")  ## Extra context on the original exception
        raise ConfigError(f"{ap}: radio config incomplete (missing {err})") from err  ## Clear message, original chained


CFG = {"radios": {"5G": {"channel": 36}, "6G": {"width": 160}}}  ## 6G entry has no channel

try:  ## Simulate the test framework catching a failure
    configure("ap-lab-07", CFG)  ## Raises ConfigError
except ConfigError as exc:  ## What a runner or report would do
    text = "".join(traceback.format_exception(exc))  ## Full chained traceback as one string
    lines = [ln for ln in text.splitlines() if ln and not ln[0].isspace() and not ln.startswith("Traceback")]  ## Drop stack frames for a compact view
    print("\\n".join(lines))  ## Original error, its note, the link sentence, then the new error
    print("cause:", repr(exc.__cause__))  ## The chained exception object is available too""",
            "under": "`raise ... from err` sets `__cause__` on the new exception; printing then shows the cause first, followed by 'The above exception was the direct cause of the following exception'. Without `from`, Python still records the context (`__context__`) but labels it 'During handling of the above exception, another exception occurred', which reads like a second bug. Notes are stored in `err.__notes__` and printed after the exception message.",
            "gotchas": [
                {
                    "title": "Swallowing exceptions",
                    "note": "`except Exception: pass` (or returning None) hides the failure: the test continues with bad data and fails later somewhere unrelated, or worse, passes. If you can't handle an error, let it propagate, or at least log it with its traceback (`log.exception`) before re-raising.",
                    "wrong": """def read_rssi(raw):
    try:
        return int(raw.split("=")[1])
    except Exception:
        return None


rssi = read_rssi("RSSI:-52")
print("rssi ok?", rssi is not None and rssi > -70)""",
                    "fixed": """import logging

logging.basicConfig(format="%(levelname)s %(message)s")
log = logging.getLogger("rssi")


def read_rssi(raw):
    try:
        return int(raw.split("=")[1])
    except (IndexError, ValueError):
        log.error("unparseable signal_poll line: %r", raw)
        raise


try:
    read_rssi("RSSI:-52")
except IndexError:
    print("the parse failure is visible, with the raw input in the log")""",
                },
            ],
            "best": "Read tracebacks bottom-up, catch the narrowest exception you can actually handle, raise domain errors with `from err`, add notes with identifying context (device, bench, firmware), and log `traceback.format_exception` text in reports.",
        },
        {
            "title": "Stepping through code with pdb",
            "local_only": PDB,
            "files": {"roam_calc.py": '''def roam_gap_ms(events):
    last_old = max(t for t, bssid in events if bssid == "A")
    first_new = min(t for t, bssid in events if bssid == "B")
    gap = first_new - last_old
    return gap * 1000


EVENTS = [(10.000, "A"), (10.020, "A"), (10.095, "B"), (10.115, "B")]
breakpoint()
print("gap:", round(roam_gap_ms(EVENTS), 1), "ms")
'''},
            "concept": "`breakpoint()` (or `python -m pdb script.py`) stops the program and opens the debugger. Key commands: `n` next line, `s` step into a call, `p expr` print, `pp` pretty-print, `l` list source, `w` where (stack), `u`/`d` move up/down the stack, `b file:line` set a breakpoint, `c` continue, `q` quit. `python -m pdb -c continue script.py` runs until a crash and then stops **post-mortem** at the failing line. The example feeds pdb a list of commands so you can see a real session.",
            "why": "Print-debugging a parser that fails on one AP model's output means re-running a 10-minute setup for each print you add. Stopping at the failing line with all variables inspectable is usually one run.",
            "syntax": "breakpoint()            # in code\npython -m pdb script.py\npython -m pdb -c continue script.py   # post-mortem on crash\npytest --pdb            # debugger on test failure",
            "code": """import subprocess  ## Run pdb as a separate process
import sys  ## Same interpreter

COMMANDS = "\\n".join([  ## What you'd type at the (Pdb) prompt
    "n",  ## Python 3.13 pauses on the breakpoint() line itself: move to the print line
    "s",  ## Step into the roam_gap_ms() call that the print line makes (stops at --Call--)
    "n",  ## Move to the first line of the body
    "n",  ## Run the line computing last_old
    "n",  ## Run the line computing first_new
    "p last_old, first_new",  ## Inspect two variables
    "w",  ## Show where we are in the call stack
    "c",  ## Continue to the end
]) + "\\n"  ## Final newline submits the last command

result = subprocess.run([sys.executable, "roam_calc.py"], input=COMMANDS, capture_output=True, text=True, env={"PYTHONBREAKPOINT": "pdb.set_trace", "PATH": ""})  ## breakpoint() -> pdb, commands from stdin
for line in result.stdout.splitlines():  ## The debugger session transcript
    if line.strip() and "<frozen" not in line and "bdb.py" not in line:  ## Skip interpreter-internal frames
        print(line.replace("(Pdb) ", "(Pdb) ").rstrip())  ## Prompt, location lines, printed values""",
            "under": "`breakpoint()` calls `sys.breakpointhook()`, which reads the `PYTHONBREAKPOINT` environment variable: unset means pdb, `0` disables every breakpoint (useful in CI), and a dotted name selects another debugger (`ipdb.set_trace`, or an IDE's). pdb reads commands from stdin, which is why piping them works; in a terminal you type them interactively. Lines starting with `>` show the current file, line and function; `->` marks the line about to run.",
            "gotchas": [],
            "best": "Use `breakpoint()` (never commit it: a pre-commit hook can block it), `pytest --pdb` or `-x --pdb` to stop at the first failure, `PYTHONBREAKPOINT=0` in CI, and post-mortem (`pdb.pm()` or `-c continue`) for crashes. IDE debuggers (VS Code, PyCharm) use the same concepts with a UI.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Catch a ValueError from int(\"6G\"), and re-raise it as a `ParseError` with `from`, then print the cause's type and message.",
            "solution": "`from err` stores the original in `__cause__`.",
            "solution_code": """class ParseError(Exception):
    pass


try:
    try:
        int("6G")
    except ValueError as err:
        raise ParseError("band field is not a channel number") from err
except ParseError as e:
    print(e, "| caused by", type(e.__cause__).__name__, "-", e.__cause__)""",
        },
        {
            "level": "Medium",
            "prompt": "Write a context manager `debug_context(**info)` that adds a note with the given key/values to any exception raised inside it, so failures carry bench/test context automatically.",
            "solution": "contextlib.contextmanager with try/except that calls add_note and re-raises.",
            "solution_code": """from contextlib import contextmanager


@contextmanager
def debug_context(**info):
    try:
        yield
    except Exception as err:
        err.add_note(", ".join(f"{k}={v}" for k, v in info.items()))
        raise


try:
    with debug_context(bench="lab-07", band="6G", firmware="7.4.2-b003"):
        {"5G": 36}["6G"]
except KeyError as e:
    print(repr(e), e.__notes__)""",
        },
        {
            "level": "Hard",
            "prompt": "Write a decorator that, when the wrapped function raises, records the local variables of the frame where the exception happened (from the traceback) into a dict for the test report.",
            "solution": "Walk `err.__traceback__` to the last frame (`tb_next` until None) and copy `tb_frame.f_locals`, filtering out large or private values.",
            "solution_code": """import functools

REPORT = {}


def capture_locals(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as err:
            tb = err.__traceback__
            while tb.tb_next:
                tb = tb.tb_next
            REPORT[fn.__name__] = {k: repr(v)[:60] for k, v in tb.tb_frame.f_locals.items() if not k.startswith("_")}
            raise
    return wrapper


@capture_locals
def check_throughput(band, samples, kpi):
    median = sorted(samples)[len(samples) // 2]
    assert median >= kpi, f"{band}: {median} < {kpi}"


try:
    check_throughput("6G", [1880.0, 1902.5, 1871.3], 2000)
except AssertionError:
    print(REPORT)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "How do you read a Python traceback?", "a": "Bottom-up: the last line is the exception type and message; the frame just above it is where it was raised; earlier frames show the call path. With chained exceptions, read each block, starting from the one marked as the direct cause.", "follow": "What does 'During handling of the above exception' mean? (A new exception happened inside an except block, without explicit chaining.)"},
        {"level": "Intermediate", "q": "When do you use `raise ... from err`?", "a": "When translating a low-level exception into a domain-specific one: the new message explains the problem in your terms, while the original is preserved as __cause__ for debugging. Use `from None` only when the original adds nothing.", "follow": "What's add_note for? (Adding context, like device or test parameters, without changing the exception type.)"},
        {"level": "Intermediate", "q": "How do you debug a failing pytest test?", "a": "Re-run just that test (-k or node id) with -x --pdb to drop into the debugger at the failure, or add breakpoint() before the suspect line; use -l to show locals in tracebacks and -s to see prints.", "follow": "How do you disable stray breakpoints in CI? (PYTHONBREAKPOINT=0.)"},
    ],
    "quiz": [
        {"q": "Read a traceback starting from...", "options": ["The top", "The bottom", "The middle", "Any frame"], "answer": 1, "why": "Exception and raising frame are last."},
        {"q": "`raise X from err` sets...", "options": ["__context__ only", "__cause__", "__notes__", "Nothing"], "answer": 1, "why": "Explicit cause."},
        {"q": "pdb: step INTO a function call", "options": ["n", "s", "c", "u"], "answer": 1, "why": "s = step."},
        {"q": "Disable all breakpoint() calls:", "options": ["PYTHONBREAKPOINT=0", "python -O", "pdb off", "-X nobreak"], "answer": 0, "why": "Env var read by sys.breakpointhook."},
        {"q": "Drop into the debugger on test failure:", "options": ["pytest --debug", "pytest --pdb", "pytest -v", "pytest --trace-failures"], "answer": 1, "why": "--pdb."},
    ],
    "cards": [
        {"front": "Chain exceptions", "back": "`raise DomainError('...') from err`"},
        {"front": "Add context", "back": "`err.add_note('bench=lab-07')` (3.11+)"},
        {"front": "Traceback as text", "back": "`''.join(traceback.format_exception(exc))`"},
        {"front": "pdb essentials", "back": "n, s, p expr, pp, l, w, u/d, b, c, q"},
        {"front": "Debug a test", "back": "`pytest path::test -x --pdb` / `breakpoint()`"},
    ],
}


M_9_2 = {
    "id": "9.2",
    "title": "SQLite & SQLAlchemy for Test Results",
    "hours": 2.5,
    "summary": "Store every result in a database instead of scattered files: a schema for runs and results, parameterised inserts and queries with sqlite3, and the same model with SQLAlchemy 2.0's ORM.",
    "concepts": [
        {
            "title": "A results database with sqlite3",
            "local_only": SQLITE,
            "concept": "`sqlite3` is in the standard library: a full SQL database in a single file, no server. Create tables with `CREATE TABLE`, insert with `executemany` and `?` placeholders (never string formatting), and query with `SELECT ... GROUP BY`. A simple schema for test automation: **runs** (one per nightly run: firmware, bench, start time) and **results** (one per test per run: outcome, duration, measured value). Using the connection as a context manager wraps writes in a transaction.",
            "why": "Trends, flaky-test detection, duration estimates for the nightly planner and 'when did this start failing?' are all one SQL query away once results are in a database, and impossible when they live in 3,000 JUnit files.",
            "syntax": "con = sqlite3.connect(\"results.db\")\nwith con:\n    con.executemany(\"INSERT INTO results VALUES (?, ?, ?)\", rows)\nfor row in con.execute(\"SELECT ... WHERE fw = ?\", (fw,)): ...",
            "code": """import sqlite3  ## Standard-library SQL database

con = sqlite3.connect(":memory:")  ## A file path like results.db in real use
con.row_factory = sqlite3.Row  ## Rows behave like dicts: row["column"]
con.executescript(\"\"\"
CREATE TABLE runs (id INTEGER PRIMARY KEY, night TEXT, firmware TEXT, bench TEXT);
CREATE TABLE results (run_id INTEGER REFERENCES runs(id), test TEXT, outcome TEXT, seconds REAL, mbps REAL);
CREATE INDEX idx_results_test ON results(test);
\"\"\")  ## Schema: one row per run, one row per test result

RUNS = [(1, "2026-10-10", "7.4.1", "lab-07"), (2, "2026-10-11", "7.4.2-b002", "lab-07"), (3, "2026-10-12", "7.4.2-b003", "lab-07")]  ## Three nights
RESULTS = [  ## (run_id, test, outcome, seconds, mbps)
    (1, "rvr[5G-42dB]", "pass", 61.0, 168.2), (1, "roam_11r", "pass", 30.2, None), (1, "dfs_ch52", "fail", 120.0, None),  ## Night 1
    (2, "rvr[5G-42dB]", "fail", 60.4, 141.0), (2, "roam_11r", "pass", 29.8, None), (2, "dfs_ch52", "fail", 121.3, None),  ## Night 2
    (3, "rvr[5G-42dB]", "fail", 60.9, 135.9), (3, "roam_11r", "fail", 45.1, None), (3, "dfs_ch52", "fail", 119.5, None),  ## Night 3
]  ## End of results
with con:  ## One transaction: all rows or none
    con.executemany("INSERT INTO runs VALUES (?, ?, ?, ?)", RUNS)  ## ? placeholders, values passed separately
    con.executemany("INSERT INTO results VALUES (?, ?, ?, ?, ?)", RESULTS)  ## Fast bulk insert

q = \"\"\"SELECT r.night, r.firmware, ROUND(100.0 * SUM(x.outcome = 'pass') / COUNT(*), 1) AS pass_rate
FROM runs r JOIN results x ON x.run_id = r.id GROUP BY r.id ORDER BY r.night\"\"\"  ## Pass rate per night
for row in con.execute(q):  ## Iterate the result rows
    print(row["night"], row["firmware"], f"{row['pass_rate']}%")  ## Column access by name

test = "rvr[5G-42dB]"  ## Value from user input or a report link
q = \"\"\"SELECT r.firmware, x.mbps FROM results x JOIN runs r ON r.id = x.run_id
WHERE x.test = ? ORDER BY r.night\"\"\"  ## Throughput history of one test
print(test, [(row["firmware"], row["mbps"]) for row in con.execute(q, (test,))])  ## Parameter tuple, never an f-string

q = \"\"\"SELECT test, MIN(r.firmware) AS first_bad_fw FROM results x JOIN runs r ON r.id = x.run_id
WHERE outcome = 'fail' AND test NOT IN (SELECT test FROM results WHERE run_id = 1 AND outcome = 'fail')
GROUP BY test ORDER BY test\"\"\"  ## Tests that passed on night 1 but fail now, with the first failing build
print([tuple(row) for row in con.execute(q)])  ## New regressions""",
            "under": "With `?` placeholders the values are sent to SQLite separately from the SQL text, so a test name containing a quote can never change the query's meaning, and statements can be reused. `with con:` commits on success and rolls back on an exception. In SQLite a comparison like `x.outcome = 'pass'` evaluates to 1 or 0, so `SUM()` counts passes. `row_factory = sqlite3.Row` allows access by column name.",
            "gotchas": [
                {
                    "title": "Building SQL with f-strings",
                    "local_only": SQLITE,
                    "note": "Interpolating values into SQL breaks as soon as a value contains a quote (parametrized test ids often do), and lets crafted input change the query. Always pass values as parameters.",
                    "wrong": """import sqlite3

con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE results (test TEXT, outcome TEXT)")
con.execute("INSERT INTO results VALUES (?, ?)", ("test_ssid[O'Brien's AP]", "fail"))
name = "test_ssid[O'Brien's AP]"
try:
    print(con.execute(f"SELECT outcome FROM results WHERE test = '{name}'").fetchall())
except sqlite3.OperationalError as e:
    print("OperationalError:", e)""",
                    "fixed": """import sqlite3

con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE results (test TEXT, outcome TEXT)")
con.execute("INSERT INTO results VALUES (?, ?)", ("test_ssid[O'Brien's AP]", "fail"))
name = "test_ssid[O'Brien's AP]"
print(con.execute("SELECT outcome FROM results WHERE test = ?", (name,)).fetchall())""",
                },
            ],
            "best": "Design the schema around questions you'll ask (by test, by firmware, by bench, over time), always use parameters, insert in transactions with executemany, add indexes for frequent filters, and back up the file (or move to PostgreSQL when several writers need it).",
        },
        {
            "title": "The same model with SQLAlchemy 2.0",
            "local_only": SQLA,
            "concept": "SQLAlchemy's ORM maps Python classes to tables: `Mapped[...]` type hints with `mapped_column()` define columns, `relationship()` links runs to their results, and a `Session` tracks objects and writes them in a transaction. Queries are built with `select()` and run with `session.scalars()` or `session.execute()`. The same code runs on SQLite for a laptop and PostgreSQL for the shared lab server, by changing only the URL.",
            "why": "Once a results dashboard (FastAPI, 6.2) and several writers (benches) share the database, you want typed models, relationships and portability across databases, without hand-writing SQL for every insert.",
            "syntax": "class Run(Base):\n    __tablename__ = \"runs\"\n    id: Mapped[int] = mapped_column(primary_key=True)\n    results: Mapped[list[\"Result\"]] = relationship(back_populates=\"run\")\n\nwith Session(engine) as s:\n    s.add(run); s.commit()\n    s.scalars(select(Result).where(Result.outcome == \"fail\"))",
            "code": """from sqlalchemy import ForeignKey, create_engine, func, select  ## pip install sqlalchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship  ## ORM building blocks


class Base(DeclarativeBase):  ## Common base for all models
    pass  ## Holds the metadata (table definitions)


class Run(Base):  ## One nightly run
    __tablename__ = "runs"  ## Table name
    id: Mapped[int] = mapped_column(primary_key=True)  ## Auto-increment key
    firmware: Mapped[str]  ## NOT NULL text column (type from the hint)
    bench: Mapped[str]  ## Bench name
    results: Mapped[list["Result"]] = relationship(back_populates="run", cascade="all, delete-orphan")  ## One-to-many


class Result(Base):  ## One test outcome
    __tablename__ = "results"  ## Table name
    id: Mapped[int] = mapped_column(primary_key=True)  ## Key
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))  ## Link to the run
    test: Mapped[str] = mapped_column(index=True)  ## Indexed for history queries
    outcome: Mapped[str]  ## pass / fail / skip
    mbps: Mapped[float | None]  ## Optional measurement (nullable because of `| None`)
    run: Mapped[Run] = relationship(back_populates="results")  ## Many-to-one back reference


engine = create_engine("sqlite://")  ## In-memory SQLite; e.g. postgresql+psycopg://user@db/results in the lab
Base.metadata.create_all(engine)  ## CREATE TABLE for every model

with Session(engine) as s:  ## Unit of work
    for fw, outcomes in [("7.4.1", ["pass", "pass", "fail"]), ("7.4.2-b003", ["fail", "fail", "fail"])]:  ## Two runs
        run = Run(firmware=fw, bench="lab-07")  ## A Python object, not yet in the database
        run.results = [Result(test=t, outcome=o, mbps=m) for t, o, m in zip(["rvr[5G-42dB]", "roam_11r", "dfs_ch52"], outcomes, [168.2, None, None])]  ## Children via the relationship
        s.add(run)  ## Cascade adds the results too
    s.commit()  ## One transaction: INSERTs for runs and results

    stmt = (select(Run.firmware, func.count().label("fails"))  ## Columns to return
            .join(Run.results).where(Result.outcome == "fail")  ## Only failures
            .group_by(Run.id).order_by(Run.firmware))  ## Per run
    print(s.execute(stmt).all())  ## Failures per firmware
    newest = s.scalars(select(Run).order_by(Run.id.desc())).first()  ## A Run object
    print(newest.firmware, [(r.test, r.outcome) for r in newest.results])  ## Navigate the relationship
    print(str(select(Result.test).where(Result.outcome == "fail")).replace("\\n", " "))  ## The SQL SQLAlchemy generates""",
            "under": "The `Session` keeps an identity map of loaded objects and a list of pending changes, flushing them as INSERT/UPDATE statements in dependency order (runs before results, so foreign keys exist) on `commit()`. `Mapped[float | None]` makes the column nullable; a plain `Mapped[str]` is NOT NULL. Comparisons like `Result.outcome == \"fail\"` don't evaluate to booleans: they build SQL expression objects with bound parameters, so values are never pasted into the SQL text.",
            "gotchas": [],
            "best": "Use SQLAlchemy 2.0 style (`Mapped`, `select()`), one Session per unit of work (per request or per run), migrations with Alembic once the schema is shared, PostgreSQL for multi-writer setups, and keep raw measurement data alongside verdicts.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "local_only": SQLITE,
            "prompt": "Store five durations for a suite and compute min, average and max with one SQL query.",
            "solution": "Aggregate functions in SQL; parameters for inserts.",
            "solution_code": """import sqlite3

con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE durations (suite TEXT, minutes REAL)")
con.executemany("INSERT INTO durations VALUES ('rvr-6g', ?)", [(m,) for m in (198, 205, 260, 201, 199)])
print(con.execute("SELECT MIN(minutes), ROUND(AVG(minutes), 1), MAX(minutes) FROM durations WHERE suite = ?", ("rvr-6g",)).fetchone())""",
        },
        {
            "level": "Medium",
            "local_only": SQLITE,
            "prompt": "Find flaky tests in SQL: tests with both passes and failures across runs, with their pass rate.",
            "solution": "GROUP BY test HAVING the count of distinct outcomes is 2.",
            "solution_code": """import sqlite3

con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE results (run INTEGER, test TEXT, outcome TEXT)")
rows = [(r, "roam_11r", o) for r, o in enumerate("PFPPFPFPPF")] + [(r, "assoc_wpa3", "P") for r in range(10)] + \\
       [(r, "dfs_ch52", "F") for r in range(10)]
con.executemany("INSERT INTO results VALUES (?, ?, ?)", rows)
q = '''SELECT test, ROUND(100.0 * SUM(outcome = 'P') / COUNT(*)) AS pass_pct FROM results
GROUP BY test HAVING COUNT(DISTINCT outcome) = 2'''
print(con.execute(q).fetchall())""",
        },
        {
            "level": "Hard",
            "local_only": SQLITE,
            "prompt": "Use a window function to show, for one test, each night's throughput and the change from the previous night (LAG).",
            "solution": "`LAG(mbps) OVER (ORDER BY night)` gives the previous row's value within the ordering.",
            "solution_code": """import sqlite3

con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE tput (night TEXT, test TEXT, mbps REAL)")
con.executemany("INSERT INTO tput VALUES (?, 'rvr[6G-30dB]', ?)",
                [("2026-10-09", 1210.4), ("2026-10-10", 1205.0), ("2026-10-11", 1098.7), ("2026-10-12", 1101.2)])
q = '''SELECT night, mbps, ROUND(mbps - LAG(mbps) OVER (ORDER BY night), 1) AS delta FROM tput ORDER BY night'''
for row in con.execute(q):
    print(row)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Why store test results in a database?", "a": "To query across runs: trends, pass rates per firmware, flaky tests, first failing build, duration history for scheduling, and dashboards, none of which scale with loose files.", "follow": "What's a minimal schema? (runs and results tables, linked by run id.)"},
        {"level": "Intermediate", "q": "Why use parameterised queries?", "a": "Values are passed separately from SQL text, so quotes or crafted strings can't alter the query, statements can be reused, and types are handled correctly.", "follow": "What's the placeholder in sqlite3? (? or :name.)"},
        {"level": "Intermediate", "q": "SQLite vs PostgreSQL for lab results?", "a": "SQLite: zero setup, single file, great for one writer or local analysis. PostgreSQL: concurrent writers from many benches, network access, roles, better concurrency and tooling. SQLAlchemy lets the same code target both.", "follow": "How do you evolve the schema? (Migrations with Alembic.)"},
    ],
    "quiz": [
        {"q": "sqlite3 placeholder:", "options": ["%s", "?", "{}", "$1"], "answer": 1, "why": "? (or :name)."},
        {"q": "`with con:` around inserts...", "options": ["Closes the DB", "Commits or rolls back as a transaction", "Locks the file forever", "Nothing"], "answer": 1, "why": "Transaction context."},
        {"q": "Nullable column in SQLAlchemy 2.0 typing:", "options": ["Mapped[str]", "Mapped[str | None]", "Optional() call", "nullable=False"], "answer": 1, "why": "| None."},
        {"q": "Previous row's value in SQL:", "options": ["PREV()", "LAG() OVER (...)", "SHIFT()", "LEAD()"], "answer": 1, "why": "Window function."},
        {"q": "Write pending ORM objects:", "options": ["s.save()", "s.commit()", "engine.write()", "Base.flush()"], "answer": 1, "why": "Commit the unit of work."},
    ],
    "cards": [
        {"front": "Bulk insert", "back": "`with con: con.executemany('INSERT ... VALUES (?, ?)', rows)`"},
        {"front": "Dict-like rows", "back": "`con.row_factory = sqlite3.Row`"},
        {"front": "Pass rate SQL", "back": "`100.0 * SUM(outcome = 'pass') / COUNT(*)` with GROUP BY"},
        {"front": "ORM model", "back": "`class Run(Base): __tablename__; id: Mapped[int] = mapped_column(primary_key=True)`"},
        {"front": "ORM query", "back": "`s.scalars(select(Result).where(Result.outcome == 'fail'))`"},
    ],
}


M_9_3 = {
    "id": "9.3",
    "title": "Design Patterns for Device Drivers",
    "hours": 2.5,
    "summary": "The handful of patterns that keep lab code maintainable: Protocol interfaces, factories, adapters, facades, decorators for retries and timing, and composition over inheritance.",
    "concepts": [
        {
            "title": "Protocol, Factory and Adapter",
            "concept": "A `typing.Protocol` describes what a driver must offer (methods and signatures) without forcing inheritance: any class with matching methods fits (structural typing), and mypy checks it. A **factory** (here a registry dict filled by a decorator) creates the right driver from a config string. An **adapter** wraps an existing vendor SDK whose API doesn't match your interface, translating calls instead of rewriting the SDK.",
            "why": "Your attenuator code must work with a Mini-Circuits box today, an Adaura box on another bench and a simulator in CI. Tests ask for 'an attenuator' and get whichever the bench config names.",
            "syntax": "class Attenuator(Protocol):\n    def set_db(self, db: float) -> None: ...\n\nDRIVERS: dict[str, type] = {}\ndef register(name): ...\n\ndef make(cfg) -> Attenuator: return DRIVERS[cfg[\"type\"]](**cfg[\"args\"])",
            "code": """from typing import Protocol  ## Structural interfaces


class Attenuator(Protocol):  ## What tests are allowed to rely on
    def set_db(self, db: float) -> None: ...  ## Set attenuation
    def get_db(self) -> float: ...  ## Read it back


DRIVERS: dict[str, type] = {}  ## Registry: config name -> class


def register(name):  ## Class decorator that fills the registry
    def wrap(cls):  ## Receives the class being defined
        DRIVERS[name] = cls  ## Remember it under the config name
        return cls  ## Leave the class unchanged
    return wrap  ## The actual decorator


@register("sim")  ## Available as type: sim
class SimAttenuator:  ## No inheritance from Attenuator needed
    def __init__(self, max_db=95):  ## Simulator settings
        self.max_db, self.db = max_db, 0.0  ## State

    def set_db(self, db):  ## Same signature as the Protocol
        self.db = min(db, self.max_db)  ## Clamp like hardware would

    def get_db(self):  ## Read back
        return self.db  ## Current value


class VendorSdk:  ## Imagine a vendor's library with its own naming and units
    def SetAttenuation(self, channel: int, tenths_of_db: int) -> int:  ## Different names, tenths of dB, status codes
        self._value = tenths_of_db  ## Store
        return 0  ## 0 = OK in this SDK

    def QueryAttenuation(self, channel: int) -> int:  ## Returns tenths of dB
        return self._value  ## Stored value


@register("vendor")  ## Available as type: vendor
class VendorAdapter:  ## Adapter: our interface on top of their SDK
    def __init__(self, channel=1):  ## Wraps one SDK instance
        self.sdk, self.channel = VendorSdk(), channel  ## Composition, not inheritance

    def set_db(self, db):  ## Translate the call...
        if self.sdk.SetAttenuation(self.channel, round(db * 10)) != 0:  ## ...units and error convention
            raise RuntimeError("vendor SDK rejected the value")  ## Exceptions instead of status codes

    def get_db(self):  ## Translate the result
        return self.sdk.QueryAttenuation(self.channel) / 10  ## Back to dB


def make(cfg) -> Attenuator:  ## Factory: config -> object
    return DRIVERS[cfg["type"]](**cfg.get("args", {}))  ## KeyError names an unknown type


for cfg in ({"type": "sim", "args": {"max_db": 63}}, {"type": "vendor", "args": {"channel": 2}}):  ## Two benches
    att = make(cfg)  ## The test doesn't care which class this is
    att.set_db(70.5)  ## Same calls for both
    print(cfg["type"], type(att).__name__, att.get_db())  ## Simulator clamps at 63; vendor stores 70.5
print("registered:", sorted(DRIVERS))  ## What the bench config may name""",
            "under": "Protocols are checked statically by mypy (assigning a `SimAttenuator` where an `Attenuator` is expected type-checks because the methods match); add `@runtime_checkable` to also allow `isinstance` checks of method presence. The registry decorator runs at class-definition time, so importing a driver module is enough to make it available, which is also how pytest plugins and many frameworks register things.",
            "gotchas": [],
            "best": "Define small Protocols for each instrument role, keep drivers thin, adapt vendor SDKs rather than leaking their APIs into tests, create objects through one factory from bench config, and give every driver a simulator implementation for CI.",
        },
        {
            "title": "Decorators for retries and timing, and a Facade",
            "concept": "Cross-cutting behaviour (retry on transient errors, timing, logging) belongs in **decorators**, written once and applied with `@retry(...)`, rather than copied into every driver method. A **facade** gives tests one simple object (`bench.set_distance(30)`, `bench.measure()`) that coordinates several instruments behind the scenes. Both rely on **composition**: objects that hold other objects, not deep inheritance trees.",
            "why": "Every SSH call, REST call and instrument command in a lab occasionally fails transiently, and every measurement needs timing in the report. Decorators keep that policy consistent; a facade keeps tests readable when a 'simple' action involves three devices.",
            "syntax": "def retry(times, on=(Exception,)):\n    def deco(fn):\n        @functools.wraps(fn)\n        def wrapper(*a, **kw): ...\n        return wrapper\n    return deco",
            "code": """import functools  ## wraps() keeps function metadata
import time  ## Timing


def retry(times=3, on=(ConnectionError, TimeoutError), log=print):  ## Decorator factory: settings first
    def deco(fn):  ## The decorator itself
        @functools.wraps(fn)  ## Keep fn's name and docstring on the wrapper
        def wrapper(*args, **kwargs):  ## Replaces fn
            for attempt in range(1, times + 1):  ## 1-based attempts
                try:  ## Try the real call
                    return fn(*args, **kwargs)  ## Success: return immediately
                except on as err:  ## Only the transient error types
                    if attempt == times:  ## Out of attempts
                        raise  ## Re-raise the last error unchanged
                    log(f"{fn.__name__}: attempt {attempt} failed ({err}), retrying")  ## Visible in logs
        return wrapper  ## Decorated function
    return deco  ## Applied by @retry(...)


def timed(fn):  ## Simple decorator without settings
    @functools.wraps(fn)  ## Keep metadata
    def wrapper(*args, **kwargs):  ## Measure every call
        t0 = time.perf_counter()  ## Start
        try:  ## Time even failing calls
            return fn(*args, **kwargs)  ## The real work
        finally:  ## Always record
            wrapper.last_ms = round((time.perf_counter() - t0) * 1000)  ## Stored on the wrapper for reports
    return wrapper  ## Decorated function


class FlakyTraffic:  ## A traffic generator that fails once, then works
    def __init__(self):  ## Track calls
        self.calls = 0  ## Counter

    @timed  ## Outer: times the whole call including retries
    @retry(times=3)  ## Inner: retries transient failures
    def run(self, seconds):  ## Decorators work on methods too
        self.calls += 1  ## Count real attempts
        if self.calls == 1:  ## First attempt fails
            raise ConnectionError("LANforge API reset")  ## Transient
        return 912.4  ## Mbps


class Bench:  ## Facade: one simple object for tests
    def __init__(self, attenuator, traffic):  ## Composition: built from parts
        self.att, self.traffic = attenuator, traffic  ## Collaborators

    def throughput_at(self, db):  ## One high-level operation
        self.att.append(db)  ## Stand-in for att.set_db(db)
        return self.traffic.run(seconds=10)  ## Measure


bench = Bench(attenuator=[], traffic=FlakyTraffic())  ## A list stands in for an attenuator here
print(bench.throughput_at(30), "Mbps")  ## Retried transparently
print("attempts:", bench.traffic.calls, "| name kept:", FlakyTraffic.run.__name__, "| timed:", isinstance(FlakyTraffic.run.last_ms, int))  ## Metadata and timing""",
            "under": "Stacked decorators apply bottom-up: `run = timed(retry(times=3)(run))`, so `timed` wraps the retrying function and measures all attempts. `functools.wraps` copies `__name__`, `__doc__`, `__qualname__` and sets `__wrapped__`, which is what pytest, logging and debuggers display. Attributes set on the wrapper function (like `last_ms`) are shared by all instances, which is fine for a demo; per-instance metrics belong in a results object.",
            "gotchas": [
                {
                    "title": "A decorator without functools.wraps",
                    "note": "Without `wraps`, every decorated function is called `wrapper` and loses its docstring: logs, tracebacks, pytest ids and API docs all show the wrong name, and introspection-based tools (fixtures, typer commands) can break.",
                    "wrong": """def timed(fn):
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper


@timed
def set_channel(band, channel):
    \"\"\"Set the AP radio channel.\"\"\"


print(set_channel.__name__, "|", set_channel.__doc__)""",
                    "fixed": """import functools


def timed(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper


@timed
def set_channel(band, channel):
    \"\"\"Set the AP radio channel.\"\"\"


print(set_channel.__name__, "|", set_channel.__doc__)""",
                },
            ],
            "best": "Use decorators for policy (retry, timing, logging, permission checks), always with `functools.wraps`, retry only transient and idempotent operations, build facades from injected parts so they can be tested with fakes, and prefer composition over inheritance for drivers.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Define a `PowerSwitch` Protocol (`on(outlet)`, `off(outlet)`, `state(outlet) -> bool`) and a simulator class that satisfies it; power-cycle outlet 3 and print its states.",
            "solution": "Protocol for the contract, plain class for the simulator; no inheritance needed.",
            "solution_code": """from typing import Protocol


class PowerSwitch(Protocol):
    def on(self, outlet: int) -> None: ...
    def off(self, outlet: int) -> None: ...
    def state(self, outlet: int) -> bool: ...


class SimPdu:
    def __init__(self, outlets=8):
        self.states = {o: True for o in range(1, outlets + 1)}

    def on(self, outlet):
        self.states[outlet] = True

    def off(self, outlet):
        self.states[outlet] = False

    def state(self, outlet):
        return self.states[outlet]


def power_cycle(pdu: PowerSwitch, outlet: int) -> list[bool]:
    seen = [pdu.state(outlet)]
    pdu.off(outlet)
    seen.append(pdu.state(outlet))
    pdu.on(outlet)
    seen.append(pdu.state(outlet))
    return seen


print(power_cycle(SimPdu(), 3))""",
        },
        {
            "level": "Medium",
            "prompt": "Add exponential backoff with an injectable sleep to the retry decorator (delays 1, 2, 4 ... seconds) and show the requested delays for a function that fails three times then succeeds.",
            "solution": "Compute `base * 2 ** (attempt - 1)` and call the injected sleep between attempts.",
            "solution_code": """import functools


def retry(times=4, base=1.0, on=(ConnectionError,), sleep=None):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            for attempt in range(1, times + 1):
                try:
                    return fn(*a, **kw)
                except on:
                    if attempt == times:
                        raise
                    sleep(base * 2 ** (attempt - 1))
        return wrapper
    return deco


delays, calls = [], {"n": 0}


@retry(times=5, sleep=delays.append)
def reboot_ap():
    calls["n"] += 1
    if calls["n"] < 4:
        raise ConnectionError("ssh refused")
    return "rebooted"


print(reboot_ap(), delays)""",
        },
        {
            "level": "Hard",
            "prompt": "Write an Observer: a `LinkMonitor` that notifies subscribed callbacks on state changes (up/down), with unsubscribe support; subscribe a logger and a counter and feed it a sequence of link states.",
            "solution": "Store callbacks in a list, notify only on transitions, return an unsubscribe function from subscribe.",
            "solution_code": """class LinkMonitor:
    def __init__(self):
        self._subs, self._state = [], None

    def subscribe(self, fn):
        self._subs.append(fn)
        return lambda: self._subs.remove(fn)

    def update(self, state):
        if state != self._state:
            old, self._state = self._state, state
            for fn in list(self._subs):
                fn(old, state)


mon = LinkMonitor()
events = []
mon.subscribe(lambda old, new: print(f"link {old} -> {new}"))
stop_counting = mon.subscribe(lambda old, new: events.append(new))
for s in ["up", "up", "down", "up"]:
    mon.update(s)
stop_counting()
mon.update("down")
print("counted:", events)""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "Protocol vs ABC for driver interfaces?", "a": "ABC: nominal typing, classes must inherit and implement abstract methods, errors at instantiation. Protocol: structural typing, any class with matching methods fits, checked by type checkers; great for adapting third-party classes you can't change.", "follow": "Can you isinstance-check a Protocol? (Only with @runtime_checkable, and it checks method presence, not signatures.)"},
        {"level": "Intermediate", "q": "Which design patterns do you use in test frameworks?", "a": "Factory/registry for drivers from config, Adapter for vendor SDKs, Facade for multi-instrument benches, Strategy for interchangeable algorithms (traffic profiles), Decorator for retries/timing, Observer for event monitoring, Page Object for UIs, and context managers for resource lifetime.", "follow": "Which one would you avoid overusing? (Deep inheritance; prefer composition.)"},
        {"level": "Advanced", "q": "Why prefer composition over inheritance for device drivers?", "a": "Drivers combine capabilities (SSH + REST + serial, retries, logging) that don't form a clean hierarchy; inheritance couples them tightly and creates fragile base classes. Composition assembles behaviour from small parts that can be swapped and tested independently.", "follow": "How do you share behaviour then? (Helper objects, decorators, mixins sparingly.)"},
    ],
    "quiz": [
        {"q": "Structural interface in typing:", "options": ["ABC", "Protocol", "TypedDict", "NamedTuple"], "answer": 1, "why": "Matching methods suffice."},
        {"q": "Wrap a vendor SDK to match your interface:", "options": ["Facade", "Adapter", "Singleton", "Observer"], "answer": 1, "why": "Translate the API."},
        {"q": "`@timed @retry def f` applies...", "options": ["timed first", "retry first, then timed wraps it", "Both at once", "Neither"], "answer": 1, "why": "Bottom-up."},
        {"q": "Keep a decorated function's name:", "options": ["functools.wraps", "copy.copy", "staticmethod", "nonlocal"], "answer": 0, "why": "Copies metadata."},
        {"q": "One simple object coordinating several instruments:", "options": ["Adapter", "Facade", "Factory", "Proxy"], "answer": 1, "why": "Facade."},
    ],
    "cards": [
        {"front": "Driver interface", "back": "`class Attenuator(Protocol): def set_db(self, db: float) -> None: ...`"},
        {"front": "Registry factory", "back": "`@register('sim') class Sim...`; `DRIVERS[cfg['type']](**args)`"},
        {"front": "Adapter", "back": "Wrap the vendor object; translate names, units, error codes"},
        {"front": "Decorator with args", "back": "`def retry(times): def deco(fn): @wraps(fn) def wrapper(...)`"},
        {"front": "Facade", "back": "`bench.throughput_at(db)` hides attenuator + traffic + DUT calls"},
    ],
}


MESSY = '''def run(ip, b, x, flag=False):
    import time, subprocess
    if b == 1:
        band = "2G"
    elif b == 2:
        band = "5G"
    else:
        band = "6G"
    subprocess.run(["ssh", ip, f"set radio {band} channel {x}"])
    time.sleep(30)
    out = subprocess.run(["iperf3", "-c", ip, "-J"], capture_output=True, text=True).stdout
    import json
    r = json.loads(out)["end"]["sum_received"]["bits_per_second"] / 1e6
    if flag:
        print(r)
    if band == "6G" and r > 2000 or band == "5G" and r > 850 or band == "2G" and r > 120:
        return True
    return False
'''

M_9_4 = {
    "id": "9.4",
    "title": "SOLID & Clean Code",
    "hours": 1.5,
    "summary": "Refactor a typical 'works on my bench' function into clean, testable pieces, guided by the SOLID principles that actually matter in automation code.",
    "concepts": [
        {
            "title": "From one tangled function to small testable parts",
            "files": {"messy.py": MESSY},
            "concept": "The function in `messy.py` (supporting files) configures a radio, waits, measures and judges, all at once, with magic numbers, a cryptic band code, a boolean flag and hidden dependencies (ssh, iperf3, sleep). The refactor applies **SRP** (one reason to change per unit), **DIP** (depend on injected abstractions, not on subprocess and time directly) and **OCP** (new bands via data, not new if-branches), plus naming and constants. The result runs in microseconds with fakes, so every rule can be tested.",
            "why": "The messy version can only be tested on a real bench, takes 30+ seconds per call, and every KPI change means editing control flow. Most test-automation maintenance pain comes from exactly this shape of code.",
            "syntax": "@dataclass(frozen=True) class Kpi: ...\nKPI_MBPS = {Band.G6: 2000, ...}\ndef check(band, mbps, kpis=KPI_MBPS) -> Verdict: ...\nclass Runner: def __init__(self, dut, traffic, sleep): ...",
            "code": """from dataclasses import dataclass  ## Small, explicit value types
from enum import Enum  ## Named bands instead of 1/2/3


class Band(Enum):  ## Replaces the cryptic b == 1/2/3 code
    G2 = "2G"  ## 2.4 GHz
    G5 = "5G"  ## 5 GHz
    G6 = "6G"  ## 6 GHz


KPI_MBPS = {Band.G2: 120, Band.G5: 850, Band.G6: 2000}  ## OCP: a new band or KPI is a data change
SETTLE_S = 30  ## Named constant instead of a magic sleep(30)


@dataclass(frozen=True)  ## Immutable result object instead of a bare True/False
class Verdict:  ## What the measurement means
    band: Band  ## Which band
    mbps: float  ## What was measured
    kpi: float  ## What was required

    @property  ## Derived, never stored separately
    def passed(self) -> bool:  ## Single source of truth for pass/fail
        return self.mbps >= self.kpi  ## Note: >= (the messy version used >, a hidden off-by-one)


def judge(band: Band, mbps: float, kpis=KPI_MBPS) -> Verdict:  ## SRP: pure decision logic, trivially testable
    return Verdict(band, mbps, kpis[band])  ## No I/O at all


class ThroughputCheck:  ## SRP: orchestration only
    def __init__(self, dut, traffic, sleep):  ## DIP: collaborators injected, not imported inside
        self.dut, self.traffic, self.sleep = dut, traffic, sleep  ## Real ones on the bench, fakes in tests

    def run(self, band: Band, channel: int) -> Verdict:  ## Clear name and typed parameters
        self.dut.set_channel(band, channel)  ## Configure (SSH details live in the dut driver)
        self.sleep(SETTLE_S)  ## Wait for the link to settle
        return judge(band, self.traffic.downlink_mbps())  ## Measure, then decide


class FakeDut:  ## Test double for the AP
    def __init__(self):  ## Record calls
        self.calls = []  ## What was configured

    def set_channel(self, band, channel):  ## Same interface as the real driver
        self.calls.append((band.value, channel))  ## Remember it


class FakeTraffic:  ## Test double for iperf3
    def __init__(self, mbps):  ## Canned measurement
        self.mbps = mbps  ## Value to return

    def downlink_mbps(self):  ## Same interface as the real traffic driver
        return self.mbps  ## No network


slept = []  ## Captured sleep requests
check = ThroughputCheck(FakeDut(), FakeTraffic(2000.0), sleep=slept.append)  ## Everything injected
v = check.run(Band.G6, 37)  ## Runs instantly
print(v, "passed:", v.passed)  ## Exactly at the KPI: passes now
print("configured:", check.dut.calls, "| slept:", slept)  ## Interactions are observable
print([judge(b, 900.0).passed for b in Band])  ## The rules, tested in one line""",
            "under": "Each piece now has one reason to change: KPIs (data), the pass rule (`Verdict.passed`), orchestration (`ThroughputCheck`), device commands (the dut driver), measurement (the traffic driver). Injecting `sleep` and the drivers is dependency inversion in its simplest form: high-level code depends on what it needs (an object with `set_channel`), not on `subprocess` and `time`. Writing the tests for `judge` revealed the boundary bug (`>` vs `>=`) that the original hid.",
            "gotchas": [
                {
                    "title": "Boolean flag arguments",
                    "note": "`run(ip, 2, 36, True)` is unreadable at the call site, and a flag usually means the function does two things. Prefer separate functions, keyword-only parameters, or returning data and letting the caller decide (print, log, report).",
                    "wrong": """def measure(band, channel, flag=False):
    mbps = 912.4
    if flag:
        print(mbps)
    return mbps > 850


print(measure("5G", 36, True))""",
                    "fixed": """def measure(band, channel):
    return 912.4


def meets_kpi(mbps, *, kpi):
    return mbps >= kpi


mbps = measure("5G", channel=36)
print(mbps, meets_kpi(mbps, kpi=850))""",
                },
            ],
            "best": "Small functions with intention-revealing names, enums instead of codes, named constants instead of magic numbers, data-driven rules, dependencies injected through constructors, pure decision logic separated from I/O, and a unit test for every rule you extract.",
        },
        {
            "title": "Interface segregation and Liskov in practice",
            "concept": "**ISP**: clients shouldn't depend on methods they don't use. A test that only needs `get_rssi()` shouldn't require a full controller object with 40 methods; give it a narrow Protocol. **LSP**: a subtype must be usable wherever its base type is expected: a `SimAp` that silently ignores `set_channel` for DFS channels, or raises a different exception type, breaks tests that work with the real AP.",
            "why": "Narrow interfaces make fakes tiny and tests focused. Substitutability is what makes simulators trustworthy: if the simulator behaves differently in edge cases, CI passes and the lab fails.",
            "syntax": "class RssiSource(Protocol):\n    def get_rssi(self, sta: str) -> int: ...\n\ndef weakest(src: RssiSource, stas): ...",
            "code": """from typing import Protocol  ## Narrow, structural interfaces


class RssiSource(Protocol):  ## ISP: exactly what the roaming check needs
    def get_rssi(self, sta: str) -> int: ...  ## One method


def needs_roam(src: RssiSource, sta: str, threshold: int = -70) -> bool:  ## Depends only on RssiSource
    return src.get_rssi(sta) < threshold  ## Business rule


class Controller:  ## The real thing has dozens of methods...
    def get_rssi(self, sta):  ## ...but only this one matters to needs_roam
        return {"02:00:00:00:01:00": -74}.get(sta, -50)  ## Stand-in for an API call

    def reboot_ap(self, ap):  ## Irrelevant to the check
        raise RuntimeError("never called by needs_roam")  ## Proves it's not used


print(needs_roam(Controller(), "02:00:00:00:01:00"))  ## Real-ish object works
print(needs_roam(type("Fake", (), {"get_rssi": lambda self, sta: -60})(), "any"))  ## A one-line fake works too


class Ap:  ## Base behaviour the tests rely on
    DFS = range(52, 145)  ## Radar channels need a CAC wait

    def set_channel(self, ch):  ## Contract: returns seconds to wait, raises ValueError for invalid channels
        if ch not in (36, 40, 44, 48, *self.DFS, 149, 153, 157, 161, 165):  ## Valid 5 GHz channels (simplified)
            raise ValueError(f"invalid channel {ch}")  ## Documented exception
        return 60 if ch in self.DFS else 0  ## DFS channels need 60 s channel availability check


class BadSimAp(Ap):  ## Violates LSP: different behaviour for the same inputs
    def set_channel(self, ch):  ## Overrides the contract
        return 0  ## Never waits, never validates


class GoodSimAp(Ap):  ## Honours the contract, just faster
    def __init__(self):  ## Records requested waits instead of sleeping
        self.cac_waits = []  ## For assertions

    def set_channel(self, ch):  ## Same validation and return value as the base
        wait = super().set_channel(ch)  ## Reuse the real rules
        self.cac_waits.append(wait)  ## Observable, not slept
        return wait  ## Same contract


for ap in (Ap(), BadSimAp(), GoodSimAp()):  ## The same test against each
    try:  ## Expect: 60 s for ch 52, ValueError for ch 14
        print(type(ap).__name__, ap.set_channel(52), end=" ")  ## DFS wait
        ap.set_channel(14)  ## Invalid in 5 GHz
        print("-> accepted ch 14 (contract broken)")  ## Only the bad simulator gets here
    except ValueError as e:  ## The documented behaviour
        print("->", e)  ## Real AP and good simulator agree""",
            "under": "`type(\"Fake\", (), {...})()` creates a class on the fly: handy for showing how small a fake can be when the interface is narrow (in real tests, write a tiny named class). Contract tests (the same test suite run against the real driver and the simulator) are the practical way to enforce LSP for simulators.",
            "gotchas": [],
            "best": "Define the narrowest interface each consumer needs, write contract tests that run against every implementation (real, simulator, fake), keep simulators faithful on validation and errors, and document contracts in docstrings (returns, raises).",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Replace this magic-number code with an Enum and a constants table: `if mode == 3: timeout = 45` (3 means WPA3-SAE, which needs a longer join timeout than open (1) or WPA2 (2), 15 s each).",
            "solution": "An Enum names the modes; a dict maps each to its timeout.",
            "solution_code": """from enum import Enum


class Security(Enum):
    OPEN = 1
    WPA2 = 2
    WPA3_SAE = 3


JOIN_TIMEOUT_S = {Security.OPEN: 15, Security.WPA2: 15, Security.WPA3_SAE: 45}
for mode in Security:
    print(mode.name, JOIN_TIMEOUT_S[mode])
print(Security(3), JOIN_TIMEOUT_S[Security(3)])""",
        },
        {
            "level": "Medium",
            "prompt": "Write contract tests as a function that takes any attenuator implementation and checks: set/get round-trip, clamping above max, and ValueError for negative values. Run it on a good and a bad implementation.",
            "solution": "One function of assertions, run against every implementation; failures name the broken rule.",
            "solution_code": """def contract(att):
    problems = []
    att.set_db(30)
    if att.get_db() != 30:
        problems.append("round-trip")
    att.set_db(200)
    if att.get_db() != att.max_db:
        problems.append("clamp")
    try:
        att.set_db(-1)
        problems.append("negative accepted")
    except ValueError:
        pass
    return problems or ["ok"]


class Good:
    max_db = 95

    def __init__(self):
        self.db = 0

    def set_db(self, db):
        if db < 0:
            raise ValueError(db)
        self.db = min(db, self.max_db)

    def get_db(self):
        return self.db


class Bad(Good):
    def set_db(self, db):
        self.db = db


print("Good:", contract(Good()))
print("Bad:", contract(Bad()))""",
        },
        {
            "level": "Hard",
            "prompt": "Refactor a function that parses `iw link` output AND decides if the link is good AND prints a report into three functions; keep the original behaviour for a sample input and show each part is testable alone.",
            "solution": "parse (text → dict), assess (dict → verdict), report (verdict → string). The orchestrator just chains them.",
            "solution_code": """import re

SAMPLE = '''Connected to 3c:84:6a:12:34:60 (on wlan0)
\\tsignal: -52 dBm
\\ttx bitrate: 2401.9 MBit/s 160MHz HE-MCS 11 HE-NSS 2'''


def parse(text):
    return {"signal": int(re.search(r"signal: (-?\\d+)", text)[1]),
            "tx_mbps": float(re.search(r"tx bitrate: ([\\d.]+)", text)[1]),
            "nss": int(re.search(r"NSS (\\d+)", text)[1])}


def assess(link, min_signal=-67, min_nss=2):
    issues = []
    if link["signal"] < min_signal:
        issues.append("weak signal")
    if link["nss"] < min_nss:
        issues.append("fewer spatial streams")
    return issues


def report(link, issues):
    return f"{link['tx_mbps']} Mbps, {link['signal']} dBm: " + (", ".join(issues) or "good")


link = parse(SAMPLE)
print(report(link, assess(link)))
print(assess({"signal": -75, "tx_mbps": 300.0, "nss": 1}))""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "Explain SOLID briefly with test-automation examples.", "a": "S: a driver talks to the device, a separate module judges KPIs. O: add bands/KPIs via data or new driver classes, not edits to core logic. L: simulators behave like real devices for the same inputs. I: tests depend on narrow interfaces (RssiSource), not giant controllers. D: high-level code receives drivers/clock/sleep via injection, so it runs with fakes.", "follow": "Which matters most day to day? (SRP and DIP: they make code testable.)"},
        {"level": "Intermediate", "q": "What makes test code hard to maintain?", "a": "Logic mixed with I/O, magic numbers, copy-pasted setup, boolean flags, hidden sleeps, hard-coded IPs, and tests asserting on everything at once. Refactor into named helpers, data-driven rules and injected dependencies.", "follow": "How do you refactor safely? (Characterisation tests first, then small steps.)"},
        {"level": "Advanced", "q": "How do you keep simulators honest?", "a": "Contract tests run against both the simulator and the real device (on the bench, nightly), covering validation, errors and timing contracts; simulator bugs found in the lab become new contract tests.", "follow": "What's the risk of an inaccurate simulator? (Green CI and red lab: false confidence.)"},
    ],
    "quiz": [
        {"q": "A function that configures, measures, judges and prints violates...", "options": ["LSP", "SRP", "ISP", "Nothing"], "answer": 1, "why": "Many reasons to change."},
        {"q": "Injecting `sleep` and drivers is an example of...", "options": ["DIP", "OCP", "LSP", "YAGNI"], "answer": 0, "why": "Depend on abstractions."},
        {"q": "Adding a band by editing a dict, not if-branches:", "options": ["OCP", "LSP", "DRY", "KISS"], "answer": 0, "why": "Open for extension."},
        {"q": "A simulator accepting invalid channels the real AP rejects breaks...", "options": ["SRP", "LSP", "ISP", "DIP"], "answer": 1, "why": "Not substitutable."},
        {"q": "Better than `run(ip, 2, 36, True)`:", "options": ["More flags", "Enums, keyword-only args, separate functions", "Global variables", "Comments"], "answer": 1, "why": "Readable call sites."},
    ],
    "cards": [
        {"front": "SRP in tests", "back": "Separate: device I/O, measurement, judgement (pure), reporting"},
        {"front": "DIP", "back": "Inject drivers, clock, sleep through constructors"},
        {"front": "OCP", "back": "New bands/KPIs/drivers via data or registry, not if-chains"},
        {"front": "LSP for simulators", "back": "Same validation, errors and return contract; enforce with contract tests"},
        {"front": "ISP", "back": "Narrow Protocols: depend only on what you call"},
    ],
}


DIFF = '''diff --git a/tests/test_roam.py b/tests/test_roam.py
--- a/tests/test_roam.py
+++ b/tests/test_roam.py
@@ -1,6 +1,18 @@
 import time
+import requests
+
+AP_IP = "10.10.30.7"

 def test_roam_11r(bench):
-    bench.roam(to="ap-2")
-    assert bench.roam_time_ms() < 50
+    try:
+        bench.roam(to="ap-2")
+    except:
+        pass
+    time.sleep(10)
+    r = requests.get(f"http://{AP_IP}/api/status")
+    print(r.json())
+    assert True
+
+def test_dfs_channel(bench):
+    bench.set_channel(52)
'''

M_9_5 = {
    "id": "9.5",
    "title": "Code Review Checklist",
    "hours": 1,
    "summary": "What to look for when reviewing test-automation code, and how to automate the mechanical part: a diff checker for common smells and an AST check that every test actually asserts something.",
    "concepts": [
        {
            "title": "Automating the mechanical review checks",
            "concept": "Good reviews spend human attention on intent, coverage and design. The mechanical smells can be flagged automatically from the diff: bare `except`, `time.sleep` in tests, hard-coded IPs, `print` instead of logging, HTTP calls without `timeout`, `assert True`. A small script that reads `git diff` output and reports only **added** lines with file and line number makes those comments unnecessary.",
            "why": "Reviewers who write 'please add a timeout' for the 30th time stop noticing the subtle problems. Bots catch the boring things consistently, so people can focus on 'does this test actually prove the feature works?'.",
            "syntax": "git diff origin/main...HEAD | python review_bot.py\n# parse '+++ b/<file>' and '@@ -a,b +c,d @@' to track line numbers",
            "code": """import re  ## Pattern checks

from diff_sample import DIFF  ## A pull request's unified diff (see supporting files)

CHECKS = [  ## (regex on an added line, message)
    (r"except\\s*:", "bare except hides failures; catch specific exceptions"),  ## E722-style
    (r"\\btime\\.sleep\\(", "fixed sleep in a test; poll for the condition with a deadline"),  ## Flaky timing
    (r"\\b\\d{1,3}(\\.\\d{1,3}){3}\\b", "hard-coded IP; take it from the bench config"),  ## Environment coupling
    (r"^\\s*print\\(", "print in test code; use logging or record_property"),  ## Lost output in CI
    (r"requests\\.(get|post|put|patch|delete)\\((?!.*timeout=)", "HTTP call without timeout"),  ## Can hang forever
    (r"assert\\s+True\\b", "assert True checks nothing"),  ## Fake assertion
]  ## End of checks


def review(diff):  ## Yield (file, line number, message) for added lines
    path, line_no = None, 0  ## Current file and line in the NEW version
    for raw in diff.splitlines():  ## Walk the diff
        if raw.startswith("+++ b/"):  ## New file section
            path = raw[6:]  ## Path after b/
        elif m := re.match(r"@@ -\\d+(?:,\\d+)? \\+(\\d+)", raw):  ## Hunk header: where the new lines start
            line_no = int(m[1]) - 1  ## Next line will be this number
        elif raw.startswith("+") and not raw.startswith("+++"):  ## Added line
            line_no += 1  ## It exists in the new file
            for pattern, message in CHECKS:  ## Run every check
                if re.search(pattern, raw[1:]):  ## Without the leading +
                    yield path, line_no, message  ## One finding
        elif not raw.startswith("-"):  ## Context line: present in both versions
            line_no += 1  ## Advance the new-file counter (removed lines don't)


for path, line, msg in review(DIFF):  ## Report like a review bot comment
    print(f"{path}:{line}: {msg}")  ## Clickable in most CI UIs""",
            "files": {"diff_sample.py": "DIFF = '''" + DIFF.replace("\\", "\\\\") + "'''\n"},
            "local_only": "imports a supporting file, which the in-browser runner doesn't provide",
            "under": "In a unified diff, lines starting with `+` exist only in the new version, `-` only in the old, and a space in both. The hunk header `@@ -1,6 +1,18 @@` says the new-file section starts at line 1, so counting `+` and context lines from there gives the real line numbers to comment on. Regex checks are heuristics: they produce some false positives, which is why bots should comment, not block, for style-level findings.",
            "gotchas": [],
            "best": "Automate the mechanical checks (linters, type checks, a small bot for team rules), keep human review for test intent, coverage of edge cases, failure messages and cleanup, review tests as carefully as product code, and keep PRs small enough to review well.",
        },
        {
            "title": "Checking that tests really assert: an AST check",
            "concept": "Python's `ast` module parses source code into a tree you can walk. A review helper can find test functions (`def test_*`) that contain no `assert`, no `pytest.raises`, and no call to an assertion helper: such tests pass whenever the code doesn't crash, which proves very little. The same technique finds other structural smells: tests with no failure message, or tests calling `sleep`.",
            "why": "'Tests that can't fail' are surprisingly common in automation suites (a helper swallowed the assertion, a refactor dropped it, `assert True` as a placeholder). They inflate pass rates and hide regressions.",
            "syntax": "tree = ast.parse(source)\nfor node in ast.walk(tree):\n    if isinstance(node, ast.FunctionDef) and node.name.startswith(\"test_\"): ...",
            "code": """import ast  ## Parse Python into a syntax tree

SOURCE = \"\"\"
import pytest

def test_rvr_6g(bench):
    mbps = bench.measure("6G")
    assert mbps >= 2000, f"{mbps} Mbps"

def test_roam(bench):
    bench.roam(to="ap-2")
    bench.log_roam_time()

def test_invalid_channel(bench):
    with pytest.raises(ValueError):
        bench.set_channel(14)

def test_placeholder():
    assert True

def test_uses_helper(bench):
    check_kpi(bench.measure("5G"), 850)
\"\"\"  ## Tests from a pull request
HELPERS = {"check_kpi"}  ## Team assertion helpers that count as checks


def verdict(fn: ast.FunctionDef) -> str:  ## Classify one test function
    asserts = [n for n in ast.walk(fn) if isinstance(n, ast.Assert)]  ## All assert statements, nested or not
    if any(isinstance(a.test, ast.Constant) and a.test.value is True for a in asserts):  ## assert True
        return "asserts a constant (always passes)"  ## Placeholder
    if asserts:  ## Real asserts present
        return "ok"  ## Fine
    for n in ast.walk(fn):  ## Other ways of checking
        if isinstance(n, ast.Call):  ## Function calls
            name = n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")  ## pytest.raises -> raises
            if name == "raises" or name in HELPERS:  ## Counts as an assertion
                return "ok"  ## Fine
    return "no assertion (passes unless it crashes)"  ## The smell we're looking for


tree = ast.parse(SOURCE)  ## Whole module
for node in tree.body:  ## Top-level statements
    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):  ## Test functions only
        print(f"line {node.lineno:>2} {node.name:<22} {verdict(node)}")  ## One line per test""",
            "under": "`ast.parse` produces nodes like `FunctionDef`, `Assert`, `Call`, `Attribute` and `Constant` with line numbers; `ast.walk` visits every node below a given one. Because the code is only parsed, never executed, this is safe to run on any pull request. pytest itself rewrites `assert` statements using the same AST machinery.",
            "gotchas": [],
            "best": "Review checklist for test code: Does it fail when the feature is broken? Is the failure message useful? Are waits condition-based with timeouts? Is cleanup guaranteed? Are bench details from config? Is it independent of other tests? Is it in the right suite/marker? Automate whatever can be detected structurally.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Count added and removed lines per file in a small unified diff.",
            "solution": "Track the current file from `+++ b/` lines; count lines starting with + or - (excluding the headers).",
            "solution_code": """from collections import Counter

DIFF = '''--- a/src/lab/att.py
+++ b/src/lab/att.py
@@ -1,3 +1,4 @@
-def set(db):
+def set_db(db):
+    check(db)
     send(db)
--- a/tests/test_att.py
+++ b/tests/test_att.py
@@ -2,2 +2,2 @@
-    set(30)
+    set_db(30)'''
added, removed, path = Counter(), Counter(), None
for line in DIFF.splitlines():
    if line.startswith("+++ b/"):
        path = line[6:]
    elif line.startswith("+") and not line.startswith("+++"):
        added[path] += 1
    elif line.startswith("-") and not line.startswith("---"):
        removed[path] += 1
for p in added:
    print(p, f"+{added[p]} -{removed[p]}")""",
        },
        {
            "level": "Medium",
            "prompt": "With `ast`, list every `assert` in a test module that has no failure message (`assert x >= y` instead of `assert x >= y, \"...\"`), with line numbers.",
            "solution": "ast.Assert has a `msg` attribute that is None when no message was given.",
            "solution_code": """import ast

SRC = '''def test_a(b):
    assert b.measure() >= 850
def test_b(b):
    assert b.roam_ms() < 50, f"roam took {b.roam_ms()} ms"
    assert b.connected
'''
for node in ast.walk(ast.parse(SRC)):
    if isinstance(node, ast.Assert) and node.msg is None:
        print(f"line {node.lineno}: assert without message: {ast.unparse(node.test)}")""",
        },
        {
            "level": "Hard",
            "prompt": "Find tests that depend on each other through module-level state: functions named test_* that assign to a global (via `global` statement) or mutate a module-level list/dict (`RESULTS.append(...)`).",
            "solution": "Collect module-level names, then look inside each test for `global` declarations or method calls on those names.",
            "solution_code": """import ast

SRC = '''RESULTS = []
CONFIG = {"band": "5G"}
def test_one():
    RESULTS.append(1)
def test_two():
    global CONFIG
    CONFIG = {"band": "6G"}
def test_three():
    local = []
    local.append(3)
    assert local
'''
tree = ast.parse(SRC)
module_names = {t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
for fn in (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")):
    issues = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Global):
            issues += [f"rebinds global {n}" for n in node.names]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and \\
                isinstance(node.func.value, ast.Name) and node.func.value.id in module_names:
            issues.append(f"mutates {node.func.value.id}.{node.func.attr}()")
    print(fn.name, issues or "independent")""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "What do you look for when reviewing a test?", "a": "That it fails when the feature is broken (meaningful assertions), clear failure messages, deterministic waits with timeouts, guaranteed cleanup, configuration instead of hard-coded bench details, independence from other tests, correct markers/suite placement, and readable intent.", "follow": "How do you check 'it fails when broken'? (Temporarily break the feature, or mutation testing.)"},
        {"level": "Intermediate", "q": "What should be automated in code review?", "a": "Formatting, linting, type checking, secret scanning, team-specific smells (sleeps, missing timeouts, hard-coded IPs), test-has-assertion checks and coverage reports, so reviewers focus on design and intent.", "follow": "Why comment instead of block for heuristic checks? (False positives; humans decide.)"},
        {"level": "Advanced", "q": "How would you detect tests that can never fail?", "a": "AST checks for tests without assertions or with constant assertions, helper allow-lists, and mutation testing (mutmut/cosmic-ray) which changes product code and verifies tests notice.", "follow": "Why can mutation testing be impractical for hardware tests? (Each run is slow; apply it to framework and parser code.)"},
    ],
    "quiz": [
        {"q": "In a unified diff, a line starting with a space is...", "options": ["Added", "Removed", "Context in both versions", "A header"], "answer": 2, "why": "Unchanged context."},
        {"q": "`@@ -1,6 +1,18 @@` means new-file lines start at...", "options": ["6", "1", "18", "0"], "answer": 1, "why": "+start,count."},
        {"q": "Find all asserts in a module safely:", "options": ["exec the code", "ast.parse + ast.walk", "grep 'assert'", "pytest --collect-only"], "answer": 1, "why": "Parse, don't run."},
        {"q": "A test with no assertion passes when...", "options": ["Never", "The code doesn't raise", "Only on CI", "Always fails"], "answer": 1, "why": "Proves little."},
        {"q": "Review bots for heuristic smells should...", "options": ["Block merges always", "Comment; humans decide", "Rewrite code", "Be avoided"], "answer": 1, "why": "False positives exist."},
    ],
    "cards": [
        {"front": "Diff line kinds", "back": "'+' added, '-' removed, ' ' context; '@@ -a,b +c,d @@' positions"},
        {"front": "Test review checklist", "back": "Can fail? Message? Timeouts? Cleanup? Config not constants? Independent?"},
        {"front": "AST walk", "back": "`for n in ast.walk(ast.parse(src)): isinstance(n, ast.Assert)`"},
        {"front": "Assert without message", "back": "`ast.Assert.msg is None`"},
        {"front": "Smells to flag", "back": "bare except, time.sleep, hard-coded IP, print, no timeout, assert True"},
    ],
}
