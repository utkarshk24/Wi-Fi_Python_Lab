"""Build the course data: parse annotated code, run every snippet, inject into the HTML template."""
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "content"))

import importlib  # noqa: E402
from outline import CHEATSHEET, PHASES  # noqa: E402

def _key(mid: str) -> tuple[int, int]:
    major, minor = mid.split(".")
    return int(major), int(minor)


MODULES = sorted(
    (obj for f in sorted((HERE / "content").glob("m*.py"))
     for name, obj in vars(importlib.import_module(f.stem)).items() if name.startswith("M_")),
    key=lambda m: _key(m["id"]),
)

AUTO = {
    "def main() -> None:": "Entry point: keeps the demo code out of the module's global scope",
    'if __name__ == "__main__":': "True only when this file is run directly, not when it is imported",
    "main()": "Run the demo",
    "async def main() -> None:": "The top-level coroutine that asyncio.run() drives",
}
CLOSERS = {"]": "Closes the list", "}": "Closes the dict", ")": "Closes the call"}

errors: list[str] = []


def triple_quotes(code: str) -> int:
    return code.count('"""') + code.count("'''")


def parse_annotated(src: str, where: str) -> tuple[str, list[list[str]]]:
    lines = []
    in_string = False
    for raw in src.split("\n"):
        if "  ## " in raw:
            code, expl = raw.split("  ## ", 1)
            code = code.rstrip()
        else:
            code, expl = raw.rstrip(), ""
        stripped = code.strip()
        opens = triple_quotes(code) % 2 == 1
        if stripped and not expl and in_string:
            expl = "Part of the multi-line string (sample data)"
        elif stripped and not expl and opens:
            expl = "Starts a multi-line string holding sample data"
        if opens:
            in_string = not in_string
        if stripped and not expl:
            expl = AUTO.get(stripped) or CLOSERS.get(stripped, "")
            if not expl and re.fullmatch(r"[\]\)\}]+[,)\]}]*", stripped):
                expl = "Closes the structure opened above"
            if not expl:
                errors.append(f"{where}: unexplained line: {code!r}")
        lines.append([code, expl])
    return "\n".join(c for c, _ in lines), lines


CAPTURED: dict = {}


def run(code: str, runner: str | None = None, files: dict | None = None, args: list | None = None,
        filename: str = "snippet.py", extra_env: dict | None = None, capture: str | None = None) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in (files or {}).items():
            target = Path(tmp) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
            if name.startswith("bin/"):
                target.chmod(0o755)  # fake command-line tools, put on PATH below
        path = Path(tmp) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code)
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONHASHSEED="0", COLUMNS="100", NO_COLOR="1", **(extra_env or {}))
        if (Path(tmp) / "bin").is_dir():
            env["PATH"] = str(Path(tmp) / "bin") + os.pathsep + env["PATH"]
        if runner == "pytest":
            cmd = [sys.executable, "-I", "-u", "-m", "pytest", "-p", "no:cacheprovider", *(["-q"] if args is None else args)]
        else:
            flags = ["-E", "-s"] if files else ["-I"]  # with supporting files the script dir must be importable
            cmd = [sys.executable, *flags, "-u", str(path), *(args or [])]
        proc = subprocess.run(cmd, cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                              timeout=120, env=env)
        out = proc.stdout.replace(str(path), filename).replace(tmp + "/", "").replace(tmp, ".")
        CAPTURED.clear()
        if capture and (Path(tmp) / capture).exists():
            CAPTURED["image"] = "data:image/png;base64," + base64.b64encode((Path(tmp) / capture).read_bytes()).decode()
    if runner == "pytest":
        out = re.sub(r" in \d+(?:\.\d+)?s(?: \(\d+:\d+:\d+\))?", "", out)
        out = re.sub(r"^plugins: .*\n", "", out, flags=re.M)
        out = re.sub(r" -- /\S*python\S*$", "", out, flags=re.M)
        out = re.sub(r" at 0x[0-9a-f]+>", ">", out)
        lines = out.splitlines()
        internal = [ln for ln in lines if ln.startswith("INTERNALERROR>")]
        if len(internal) > 3:
            first = lines.index(internal[0])
            rest = [ln for ln in lines if not ln.startswith("INTERNALERROR>")]
            out = "\n".join(rest[:first] + ["INTERNALERROR> Traceback (most recent call last):",
                                             "INTERNALERROR>   ... (pytest internals trimmed)", internal[-1]] + rest[first:])
        return out.strip("\n")
    marker = "Traceback (most recent call last):"
    if marker in out:
        head = out[: out.index(marker)]
        last = out.rstrip("\n").splitlines()[-1]
        out = head + marker + "\n  ...\n" + last
    return out.rstrip("\n")


def run_spec(spec: dict, code: str, prefix: str = "") -> str | None:
    if (spec.get(prefix + "runner") or spec.get("runner")) == "none":
        return None
    default = "test_example.py" if spec.get("runner") == "pytest" else "snippet.py"
    filename = spec.get(prefix + "filename") or spec.get("filename", default)
    files = spec.get(prefix + "files", spec.get("files"))
    out = run(code, spec.get(prefix + "runner") or spec.get("runner"), files, spec.get("args"), filename,
              spec.get("env"), None if prefix else spec.get("capture"))
    if "image" in CAPTURED and not prefix:
        spec["image"] = CAPTURED["image"]
    return out


PHASE_TITLES = {p["n"]: p["title"] for p in PHASES}
PYTEST_NOTE = "runs pytest, which the in-browser runner doesn't include"
CONFIG_NOTE = "is a configuration file for another tool, shown for reading rather than executed"


def build_module(m: dict) -> dict:
    mid = m["id"]
    m["phase"] = int(mid.split(".")[0])
    m["phaseTitle"] = PHASE_TITLES[m["phase"]]
    for spec in [*m["concepts"], *[g for c in m["concepts"] for g in c.get("gotchas", [])], *m["exercises"]]:
        if spec.get("runner") == "pytest" and not spec.get("local_only"):
            spec["local_only"] = PYTEST_NOTE
        if spec.get("runner") == "none":
            spec["local_only"] = CONFIG_NOTE
    for ci, c in enumerate(m["concepts"]):
        src, lines = parse_annotated(c["code"], f"{mid} concept {ci + 1}")
        c["code"] = src
        c["lines"] = lines
        c["output"] = run_spec(c, src)
        for g in c.get("gotchas", []):
            g["wrong_output"] = run_spec(g, g["wrong"], "wrong_")
            g["fixed_output"] = run_spec(g, g["fixed"], "fixed_")
    for e in m["exercises"]:
        if e.get("code") and not e.get("runner"):
            e["code_output"] = run(e["code"])
        if e.get("solution_code"):
            e["solution_output"] = run_spec(e, e["solution_code"])
    for q in m["quiz"]:
        assert 0 <= q["answer"] < len(q["options"]), (mid, q["q"])
    return m


def main() -> None:
    data = {
        "phases": [{"n": p["n"], "title": p["title"], "hours": p["hours"],
                    "modules": [{"id": i, "title": t, "hours": h} for i, t, h in p["modules"]]} for p in PHASES],
        "modules": [build_module(m) for m in MODULES],
        "cheatsheet": [{"phase": s["phase"], "title": s["title"], "rows": [list(r) for r in s["rows"]]} for s in CHEATSHEET],
        "pythonVersion": sys.version.split()[0],
    }
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    (HERE / "build").mkdir(exist_ok=True)
    (HERE / "build" / "data.json").write_text(json.dumps(data, indent=1))
    template = (HERE / "app.html").read_text()
    payload = json.dumps(data).replace("</", "<\\/")
    out = template.replace("/*__COURSE_DATA__*/null", payload)
    (HERE / "build" / "index.html").write_text(out)
    print("modules:", len(data["modules"]), "html bytes:", len(out))


if __name__ == "__main__":
    main()
