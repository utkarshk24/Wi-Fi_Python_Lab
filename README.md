# Learn Practical Python

A single-page, browser-based Python course: 11 phases, 127 lessons, with runnable
examples (Pyodide), pytest suites, simulated lab equipment, CI/CD pipelines and a final
interview round.

## Build

    python3 build.py        # writes build/index.html (single file, open in a browser)

`build.py` parses the annotated lesson code in `content/`, runs every snippet with
CPython 3.13 to capture its real output, and injects the data into `app.html`.

## Layout

- `app.html` - the UI template (no framework, no build step beyond `build.py`)
- `build.py` - course builder and snippet runner
- `content/m*.py` - lesson modules; `content/outline.py` - phases, modules, cheat sheets
- `content/sim/` - simulators used by the lab lessons (attenuator, device, SNMP, ...)
