"""Phase 7 content: modules 7.5-7.8 (asyncssh, Nornir/NAPALM, NETCONF/RESTCONF/gNMI, SNMP)."""

from net_support import needs, sim

ASYNCSSH = needs("asyncssh") + " and starts simulated SSH devices on localhost"
NORNIR = needs("nornir nornir-netmiko nornir-utils") + " and starts simulated SSH devices on localhost"
NCCLIENT = needs("ncclient") + " and starts a simulated NETCONF device on localhost"
RESTCONF = needs("requests") + " and starts a simulated RESTCONF server on localhost"
PYSNMP = needs("pysnmp scapy") + " and starts a simulated SNMP agent on localhost"
TIMING = "measures real elapsed time with blocking sleeps, which the in-browser runner can't reproduce"
DEV = sim("fake_device.py")

INVENTORY = {
    "inventory/hosts.yaml": """---
wlc-1:
  hostname: 127.0.0.1
  groups: [ios]
  data: {site: lab-7, role: controller}
sw-1:
  hostname: 127.0.0.1
  groups: [ios]
  data: {site: lab-7, role: access}
sw-2:
  hostname: 127.0.0.1
  groups: [ios]
  data: {site: lab-9, role: access}
""",
    "inventory/groups.yaml": """---
ios:
  platform: cisco_ios
""",
    "inventory/defaults.yaml": """---
username: admin
password: lab123
""",
}

M_7_5 = {
    "id": "7.5",
    "title": "asyncssh for Parallel Devices",
    "hours": 2,
    "summary": "SSH to many devices at once with asyncio and asyncssh: gather, bounded concurrency, per-device timeouts, and error isolation.",
    "concepts": [
        {
            "title": "asyncssh.connect and gather",
            "files": DEV,
            "local_only": ASYNCSSH,
            "concept": "asyncssh is an SSH client (and server) built on asyncio. `async with asyncssh.connect(host, port=..., username=..., password=..., known_hosts=...)` opens a connection; `await conn.run(cmd)` returns a result with `.stdout`, `.stderr` and `.exit_status`. Because waiting on the network doesn't block the event loop, `asyncio.gather` runs hundreds of sessions concurrently in one thread.",
            "why": "Collecting `show tech` from 300 APs one by one takes an hour. Concurrently, it takes about as long as the slowest device. asyncssh is the go-to for that scale when you don't need Netmiko's per-vendor CLI handling.",
            "syntax": "async with asyncssh.connect(h, username=u, password=p, known_hosts=kh) as conn:\n    r = await conn.run(\"show version\", check=True)\n\nresults = await asyncio.gather(*(one(h) for h in hosts))",
            "code": """import asyncio  ## Event loop
import time  ## Measure wall-clock time

import asyncssh  ## pip install asyncssh

from fake_device import start  ## Simulated devices (see supporting files)

PORTS = {f"ap-{i}": start(f"ap-{i}", i) for i in range(1, 6)}  ## Five devices; "show tech" takes 1 s on each


async def collect(name, port):  ## One device's work
    async with asyncssh.connect("127.0.0.1", port=port, username="admin", password="lab123", known_hosts=None) as conn:  ## known_hosts=None only for the simulator
        result = await conn.run("show tech-support wireless", check=False)  ## Slow command; awaiting frees the loop
        return name, result.exit_status, len(result.stdout.splitlines())  ## Summary


async def sequential():  ## One after another
    return [await collect(n, p) for n, p in PORTS.items()]  ## Each await finishes before the next starts


async def concurrent():  ## All at once
    return await asyncio.gather(*(collect(n, p) for n, p in PORTS.items()))  ## Results in the same order as the inputs


for runner in (sequential, concurrent):  ## Compare the two
    t0 = time.perf_counter()  ## Start timer
    results = asyncio.run(runner())  ## Run on a fresh event loop
    print(runner.__name__, results[0], f"~{round(time.perf_counter() - t0)} s")  ## About 5 s vs about 1 s""",
            "under": "Each `await` on network I/O hands control back to the event loop, which runs whatever other coroutine has data ready. asyncssh implements the SSH protocol itself on asyncio streams (it doesn't use Paramiko). `gather` wraps each coroutine in a Task and waits for all; its result list keeps the input order. With `check=True`, a non-zero exit status raises `ProcessError`.",
            "gotchas": [
                {
                    "title": "A blocking call inside a coroutine",
                    "local_only": TIMING,
                    "note": "`time.sleep()`, `requests.get()` or a Paramiko call inside `async def` blocks the whole event loop, so 'concurrent' tasks run one at a time. Use the async version (`asyncio.sleep`, httpx.AsyncClient, asyncssh) or push blocking code to a thread with `asyncio.to_thread`.",
                    "wrong": """import asyncio
import time


async def poll(ap):
    time.sleep(0.5)
    return ap


async def main():
    t0 = time.perf_counter()
    await asyncio.gather(*(poll(f"ap-{i}") for i in range(4)))
    print(f"took ~{round(time.perf_counter() - t0, 1)} s")

asyncio.run(main())""",
                    "fixed": """import asyncio
import time


async def poll(ap):
    await asyncio.sleep(0.5)
    return ap


async def main():
    t0 = time.perf_counter()
    await asyncio.gather(*(poll(f"ap-{i}") for i in range(4)))
    print(f"took ~{round(time.perf_counter() - t0, 1)} s")

asyncio.run(main())""",
                },
            ],
            "best": "Use asyncssh when you need hundreds of sessions or long-running parallel collection; verify host keys with a known_hosts file you manage; keep everything inside coroutines non-blocking; and wrap blocking libraries with `asyncio.to_thread`.",
        },
        {
            "title": "Bounded concurrency, timeouts and per-device errors",
            "files": DEV,
            "local_only": ASYNCSSH,
            "concept": "Real fleets need limits and resilience: an `asyncio.Semaphore(n)` caps how many sessions are open at once, `asyncio.timeout(s)` (Python 3.11+) or `asyncio.wait_for` bounds each device, and `gather(..., return_exceptions=True)` (or a try/except per task) keeps one broken device from cancelling the rest. Classify failures (auth, refused, timeout) for the report.",
            "why": "Out of 300 APs, a few are always rebooting, unreachable or misconfigured. The run must finish, report exactly which ones failed and why, and not overload the controller or jump host with 300 simultaneous logins.",
            "syntax": "sem = asyncio.Semaphore(20)\nasync with sem:\n    async with asyncio.timeout(30):\n        ...\nawait asyncio.gather(*tasks, return_exceptions=True)",
            "code": """import asyncio  ## Event loop, Semaphore, timeout
import socket  ## To get a port that nothing listens on

import asyncssh  ## pip install asyncssh

from fake_device import start  ## Simulated devices

closed = socket.socket()  ## Reserve a port, then don't listen on it
closed.bind(("127.0.0.1", 0))  ## The OS picks a free port
FLEET = {  ## name -> (port, password)
    "ap-1": (start("ap-1", 1), "lab123"),  ## Healthy
    "ap-2": (start("ap-2", 2), "lab123"),  ## Healthy
    "ap-3": (start("ap-3", 3), "wrong"),  ## Bad credentials in the inventory
    "ap-4": (closed.getsockname()[1], "lab123"),  ## Device down: connection refused
    "ap-5": (start("ap-5", 5), "lab123"),  ## Slow command exceeds the per-device timeout
}  ## End of fleet
sem = asyncio.Semaphore(2)  ## At most two sessions at a time


async def check(name):  ## Never raises: always returns (name, status)
    port, password = FLEET[name]  ## Inventory lookup
    cmd = "show tech-support wireless" if name == "ap-5" else "show clock"  ## ap-5 gets the slow command
    async with sem:  ## Waits here while two sessions are already open
        try:  ## Classify every failure
            async with asyncio.timeout(0.8):  ## Whole connect+command budget for this device
                async with asyncssh.connect("127.0.0.1", port=port, username="admin", password=password, known_hosts=None) as conn:  ## Simulator: no host key check
                    out = (await conn.run(cmd, check=True)).stdout  ## check=True raises on non-zero exit
                    return name, "ok: " + out.split()[0]  ## First word of the output
        except asyncssh.PermissionDenied:  ## Authentication failed
            return name, "auth failed"  ## Fix the inventory
        except TimeoutError:  ## asyncio.timeout expired (check before OSError: TimeoutError is a subclass)
            return name, "timeout"  ## Too slow
        except OSError as e:  ## Nothing listening / unreachable (ConnectionRefusedError is an OSError)
            return name, f"unreachable ({type(e).__name__})"  ## Device down


async def main():  ## Run the whole fleet
    results = await asyncio.gather(*(check(n) for n in FLEET))  ## Each task handles its own errors
    for name, status in results:  ## Report
        print(f"{name}: {status}")  ## One line per device

asyncio.run(main())  ## Start the event loop""",
            "under": "A Semaphore holds a counter: `async with sem` decrements it or waits until another task releases. `asyncio.timeout()` cancels the code inside its block when the deadline passes and converts the cancellation into `TimeoutError` at the block's exit, closing the SSH connection on the way out. Handling errors inside each task means `gather` never sees an exception.",
            "gotchas": [],
            "best": "Bound concurrency to what devices and jump hosts tolerate, give every device a timeout, return a status per device instead of raising, separate auth/unreachable/timeout in reports, and retry only the unreachable ones in a second pass.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "files": DEV,
            "local_only": ASYNCSSH,
            "prompt": "Run `show version` on three simulated devices concurrently with asyncssh and print each device's software version line.",
            "solution": "gather over a coroutine per device; pick the line containing 'Version'.",
            "solution_code": """import asyncio
import asyncssh
from fake_device import start

PORTS = {f"sw-{i}": start(f"sw-{i}", i) for i in (1, 2, 3)}


async def version(name, port):
    async with asyncssh.connect("127.0.0.1", port=port, username="admin", password="lab123", known_hosts=None) as c:
        out = (await c.run("show version")).stdout
        return name, next(line for line in out.splitlines() if "Version" in line).split("Version ")[1]


async def main():
    for name, v in await asyncio.gather(*(version(n, p) for n, p in PORTS.items())):
        print(name, v)

asyncio.run(main())""",
        },
        {
            "level": "Medium",
            "local_only": TIMING,
            "prompt": "Show that a Semaphore(2) limits concurrency: run 6 tasks that each sleep 0.3 s and record the maximum number running at once.",
            "solution": "Increment a counter on entry and decrement on exit inside `async with sem`; track the max.",
            "solution_code": """import asyncio

running = {"now": 0, "max": 0}


async def job(i, sem):
    async with sem:
        running["now"] += 1
        running["max"] = max(running["max"], running["now"])
        await asyncio.sleep(0.3)
        running["now"] -= 1


async def main():
    sem = asyncio.Semaphore(2)
    await asyncio.gather(*(job(i, sem) for i in range(6)))
    print("max concurrent:", running["max"])

asyncio.run(main())""",
        },
        {
            "level": "Hard",
            "files": DEV,
            "local_only": ASYNCSSH,
            "prompt": "Process results as they finish (fastest first) using `asyncio.as_completed`, with one device that's much slower than the others.",
            "solution": "as_completed yields awaitables in completion order, ideal for live progress output.",
            "solution_code": """import asyncio
import asyncssh
from fake_device import start

JOBS = {"sw-1": "show clock", "sw-2": "show tech-support wireless", "sw-3": "show clock"}
PORTS = {n: start(n, i) for i, n in enumerate(JOBS, 1)}


async def run(name):
    async with asyncssh.connect("127.0.0.1", port=PORTS[name], username="admin", password="lab123", known_hosts=None) as c:
        await c.run(JOBS[name])
        return name


async def main():
    for fut in asyncio.as_completed([run(n) for n in JOBS]):
        print("done:", await fut)

asyncio.run(main())""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "Threads vs asyncio for SSH to many devices?", "a": "Both overlap network waits. Threads work with blocking libraries (Paramiko, Netmiko) and are fine up to tens or low hundreds of devices. asyncio with asyncssh scales to thousands of sessions in one thread with less memory, but everything must be async-aware.", "follow": "How do you use a blocking library from asyncio? (asyncio.to_thread or run_in_executor.)"},
        {"level": "Intermediate", "q": "How do you stop one failing device from breaking the batch?", "a": "Catch exceptions per task and return a status (or gather with return_exceptions=True and inspect), so other tasks complete and the report lists each failure.", "follow": "What's the default gather behaviour on exception? (The first exception propagates; others keep running unless cancelled.)"},
        {"level": "Advanced", "q": "How do you limit load on devices and jump hosts?", "a": "asyncio.Semaphore around each session, connection pooling where supported, per-device timeouts, and possibly rate limits per site. Measure what the platform tolerates (AAA servers often rate-limit logins).", "follow": "Where should the semaphore be: around connect or around the whole job? (Around the whole session.)"},
    ],
    "quiz": [
        {"q": "`time.sleep(1)` inside async def...", "options": ["Yields to the loop", "Blocks the whole loop", "Raises", "Is skipped"], "answer": 1, "why": "Use asyncio.sleep."},
        {"q": "Limit concurrent sessions to 20:", "options": ["asyncio.Lock()", "asyncio.Semaphore(20)", "gather(limit=20)", "ThreadPool(20)"], "answer": 1, "why": "Semaphore."},
        {"q": "`asyncio.timeout(5)` on expiry raises...", "options": ["CancelledError outside", "TimeoutError", "asyncssh.Error", "Nothing"], "answer": 1, "why": "Converted to TimeoutError."},
        {"q": "Results in completion order:", "options": ["gather", "as_completed", "wait_for", "shield"], "answer": 1, "why": "as_completed yields as they finish."},
        {"q": "asyncssh auth failure exception:", "options": ["PermissionDenied", "AuthError", "ValueError", "KeyError"], "answer": 0, "why": "asyncssh.PermissionDenied."},
    ],
    "cards": [
        {"front": "asyncssh run", "back": "`async with asyncssh.connect(h, ...) as c: r = await c.run(cmd)`"},
        {"front": "Fan out", "back": "`await asyncio.gather(*(job(d) for d in devices))`"},
        {"front": "Bound concurrency", "back": "`sem = asyncio.Semaphore(20)`; `async with sem:`"},
        {"front": "Per-device deadline", "back": "`async with asyncio.timeout(30):` (3.11+)"},
        {"front": "Blocking lib in async", "back": "`await asyncio.to_thread(blocking_fn, args)`"},
    ],
}


M_7_6 = {
    "id": "7.6",
    "title": "NAPALM, Nornir & Vendor APIs",
    "hours": 2.5,
    "summary": "Nornir for inventory-driven, multi-threaded automation; the NAPALM idea of vendor-neutral getters; and wrapping vendor APIs behind one interface.",
    "concepts": [
        {
            "title": "Nornir: inventory, filters, tasks and results",
            "files": {**DEV, **INVENTORY},
            "local_only": NORNIR,
            "concept": "Nornir is a pure-Python automation framework. `InitNornir` loads an **inventory** (hosts, groups, defaults; here from YAML files) and a **runner** (threaded with N workers). `nr.filter(...)` selects hosts by attributes or data (`F(data__role=\"access\")`). `nr.run(task=...)` runs a task function on every selected host in parallel and returns an `AggregatedResult`: per-host results, `failed` flags and `failed_hosts`. Plugins provide tasks such as `netmiko_send_command`.",
            "why": "Once you have more than a handful of devices, you need inventory, grouping, parallelism and per-host results everywhere. Nornir gives you those as plain Python, so tests and tools stay debuggable and composable.",
            "syntax": "nr = InitNornir(config_file=\"config.yaml\")\naccess = nr.filter(F(data__role=\"access\"))\nr = access.run(task=netmiko_send_command, command_string=\"show version\")\nprint_result(r)",
            "code": """from nornir import InitNornir  ## pip install nornir nornir-netmiko nornir-utils
from nornir.core.filter import F  ## Filter objects for complex queries
from nornir_netmiko.tasks import netmiko_send_command  ## Task plugin wrapping Netmiko

from fake_device import start  ## Simulated devices

nr = InitNornir(  ## Load inventory and runner settings
    runner={"plugin": "threaded", "options": {"num_workers": 10}},  ## Up to 10 hosts in parallel
    inventory={"plugin": "SimpleInventory", "options": {"host_file": "inventory/hosts.yaml", "group_file": "inventory/groups.yaml", "defaults_file": "inventory/defaults.yaml"}},  ## YAML inventory (see supporting files)
    logging={"enabled": False},  ## Keep the example output clean
)  ## End of InitNornir
for i, host in enumerate(nr.inventory.hosts.values(), start=1):  ## Lab only: point hosts at the simulators
    host.port = start(host.name, i)  ## A real inventory just has the device addresses

print({name: (h.platform, h["site"]) for name, h in nr.inventory.hosts.items()})  ## platform from the group, site from host data
access = nr.filter(F(data__role="access"))  ## Only access switches
print("access:", list(access.inventory.hosts))  ## Filter result


def interfaces_up(task):  ## A custom task: runs once per host, in a worker thread
    rows = task.run(task=netmiko_send_command, command_string="show ip interface brief", use_textfsm=True).result  ## Sub-task, parsed output
    return [r["interface"] for r in rows if r["status"] == "up"]  ## Becomes this host's result


results = nr.run(task=interfaces_up)  ## All hosts in parallel
for name, multi in results.items():  ## One MultiResult per host
    print(name, "failed" if multi.failed else multi[0].result)  ## multi[0] is the top-level task's result
print("failed hosts:", list(results.failed_hosts))  ## Empty when everything worked""",
            "under": "Inventory attributes resolve host → groups → defaults, so `platform` set on the `ios` group and credentials in defaults apply to every host. Each task call receives a `Task` object with `task.host`; calling `task.run()` nests sub-tasks and records their results. Netmiko connections are opened on first use per host and cached in the host's connection pool until `nr.close_connections()`.",
            "gotchas": [],
            "best": "Keep inventory in version control (or generate it from your source of truth such as NetBox), put credentials in defaults from environment variables, write small custom tasks that return data, and always report `failed_hosts`.",
        },
        {
            "title": "Vendor-neutral getters (the NAPALM idea)",
            "concept": "NAPALM (`get_network_driver(\"ios\")(host, user, pw)`) exposes the **same methods with the same return schema** on every platform: `get_facts()`, `get_interfaces()`, `get_lldp_neighbors()`, plus config replace/merge with diff and rollback. The pattern is worth copying for anything vendor-specific in your lab, Wi-Fi controllers included: one abstract interface, one driver per vendor translating its API into the common schema, and tests that only use the interface.",
            "why": "Test suites that call vendor A's REST API directly have to be rewritten for vendor B. With a driver layer, adding a vendor is one class, and compliance checks (\"every AP runs the approved firmware\") work across the whole lab.",
            "syntax": "driver = napalm.get_network_driver(\"ios\")\nwith driver(host, user, pw) as dev:\n    facts = dev.get_facts()\n    dev.load_merge_candidate(config=cfg); print(dev.compare_config()); dev.commit_config()",
            "code": """from abc import ABC, abstractmethod  ## Interface definition


class WlcDriver(ABC):  ## The common interface, like NAPALM's NetworkDriver
    @abstractmethod  ## Every driver must implement it
    def get_aps(self) -> list[dict]:  ## Schema: name, model, firmware, clients
        ...  ## No body in the interface


class VendorA(WlcDriver):  ## Imagine: CLI over SSH
    RAW = "ap-lab-07 CW9166I 17.9.4 12\\nap-lab-08 CW9166I 17.9.3 4"  ## What its CLI returns

    def get_aps(self):  ## Translate vendor text into the common schema
        rows = [line.split() for line in self.RAW.splitlines()]  ## Whitespace columns
        return [{"name": n, "model": m, "firmware": f, "clients": int(c)} for n, m, f, c in rows]  ## Normalised dicts


class VendorB(WlcDriver):  ## Imagine: a cloud REST API returning JSON
    RAW = {"devices": [{"apName": "ap-lab-09", "hw": "AP-635", "sw": {"version": "10.6.0.2"}, "stats": {"clientCount": 7}}]}  ## Different field names and nesting

    def get_aps(self):  ## Same output schema as VendorA
        return [{"name": d["apName"], "model": d["hw"], "firmware": d["sw"]["version"], "clients": d["stats"]["clientCount"]} for d in self.RAW["devices"]]  ## Map fields


APPROVED = {"CW9166I": "17.9.4", "AP-635": "10.6.0.2"}  ## Firmware policy per model


def compliance(drivers):  ## Works with any driver: only uses the interface
    report = {}  ## name -> problem or "ok"
    for drv in drivers:  ## Every controller, any vendor
        for ap in drv.get_aps():  ## Common schema
            want = APPROVED.get(ap["model"])  ## Policy lookup
            report[ap["name"]] = "ok" if ap["firmware"] == want else f"runs {ap['firmware']}, want {want}"  ## Verdict
    return report  ## Plain data, easy to test and print


for name, verdict in compliance([VendorA(), VendorB()]).items():  ## Mixed-vendor lab
    print(f"{name}: {verdict}")  ## One line per AP""",
            "under": "NAPALM drivers do exactly this translation: the IOS driver runs show commands (via Netmiko) and parses them, the Junos driver uses NETCONF, the EOS driver uses eAPI, and all return the documented getter schema. NAPALM's `compliance_report(validation_file)` compares getter output with a YAML of expected values, which is the same idea as `compliance()` above.",
            "gotchas": [],
            "best": "Define the schema first (TypedDict or pydantic), keep drivers thin translators, test each driver against recorded real output, and when NAPALM supports your platform, use it rather than writing your own.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "files": {**DEV, **INVENTORY},
            "local_only": NORNIR,
            "prompt": "With the same inventory, filter hosts at site lab-7 and print their names, roles and platforms (no device connections needed).",
            "solution": "Filtering only reads the inventory; `F(data__site=...)` or `nr.filter(site=...)` both work.",
            "solution_code": """from nornir import InitNornir
from nornir.core.filter import F

nr = InitNornir(inventory={"plugin": "SimpleInventory", "options": {
    "host_file": "inventory/hosts.yaml", "group_file": "inventory/groups.yaml", "defaults_file": "inventory/defaults.yaml"}},
    logging={"enabled": False})
for name, h in nr.filter(F(data__site="lab-7")).inventory.hosts.items():
    print(name, h["role"], h.platform)""",
        },
        {
            "level": "Medium",
            "files": {**DEV, **INVENTORY},
            "local_only": NORNIR,
            "prompt": "Write a Nornir task that returns the clock line from each device, and make one host fail (wrong password) to see how failures are reported.",
            "solution": "Set the bad password on one host object; the task's exception is captured in the results and the other hosts succeed. Nornir also logs the full traceback of failed tasks, which is silenced here to keep the output short (in real runs, keep it in the log file).",
            "solution_code": """import logging

from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_command
from fake_device import start

logging.getLogger("nornir").setLevel(logging.CRITICAL)

nr = InitNornir(runner={"plugin": "threaded", "options": {"num_workers": 5}},
                inventory={"plugin": "SimpleInventory", "options": {
                    "host_file": "inventory/hosts.yaml", "group_file": "inventory/groups.yaml",
                    "defaults_file": "inventory/defaults.yaml"}}, logging={"enabled": False})
for i, h in enumerate(nr.inventory.hosts.values(), 1):
    h.port = start(h.name, i)
nr.inventory.hosts["sw-2"].password = "wrong"

r = nr.run(task=netmiko_send_command, command_string="show clock")
for name, multi in r.items():
    print(name, "FAILED: " + type(multi[0].exception).__name__ if multi.failed else multi[0].result.strip())
print(sorted(r.failed_hosts))""",
        },
        {
            "level": "Hard",
            "prompt": "Add a third driver `VendorC` whose API returns APs as a CSV string (`name;model;fw;clients`) and run the compliance check across all three without touching `compliance()`.",
            "solution": "A new driver class is the only change; that's the point of the interface.",
            "solution_code": """from abc import ABC, abstractmethod


class WlcDriver(ABC):
    @abstractmethod
    def get_aps(self) -> list[dict]: ...


class VendorC(WlcDriver):
    RAW = "ap-lab-10;U6-Enterprise;6.6.55;3\\nap-lab-11;U6-Enterprise;6.6.41;0"

    def get_aps(self):
        return [dict(zip(("name", "model", "firmware", "clients"), (n, m, f, int(c))))
                for n, m, f, c in (line.split(";") for line in self.RAW.splitlines())]


APPROVED = {"U6-Enterprise": "6.6.55"}


def compliance(drivers):
    return {ap["name"]: "ok" if ap["firmware"] == APPROVED.get(ap["model"]) else f"runs {ap['firmware']}"
            for d in drivers for ap in d.get_aps()}


print(compliance([VendorC()]))""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "What problems does Nornir solve compared to a script with a for loop?", "a": "Inventory with groups/defaults/data, filtering, threaded execution with per-host results and failure tracking, connection management via plugins, and composable tasks, all in plain Python you can debug and test.", "follow": "Nornir vs Ansible? (Nornir is Python code, faster and easier to debug; Ansible is YAML playbooks with a large module ecosystem.)"},
        {"level": "Intermediate", "q": "What does NAPALM provide?", "a": "A vendor-neutral API: identical getters (get_facts, get_interfaces, get_bgp_neighbors...) returning a documented schema, config merge/replace with compare_config and rollback, and compliance reports, implemented per platform with the best transport (NETCONF, eAPI, SSH).", "follow": "What's the difference between merge and replace? (Merge adds lines; replace makes the candidate the whole config.)"},
        {"level": "Advanced", "q": "How would you support three Wi-Fi controller vendors in one test framework?", "a": "Define a controller interface (get_aps, get_clients, set_wlan, get_radio_config) with a schema, one driver per vendor translating their CLI/API, contract tests that each driver must pass using recorded outputs, and tests that only depend on the interface.", "follow": "How do you handle vendor-only features? (Optional capabilities with explicit feature flags; tests skip when unsupported.)"},
    ],
    "quiz": [
        {"q": "Nornir inventory attribute precedence:", "options": ["defaults → groups → host", "host → groups → defaults", "groups only", "random"], "answer": 1, "why": "Most specific wins."},
        {"q": "Select hosts by data field in Nornir:", "options": ["nr.where()", "nr.filter(F(data__role='access'))", "nr.select()", "nr.hosts['x']"], "answer": 1, "why": "F objects."},
        {"q": "Hosts whose task failed:", "options": ["results.errors", "results.failed_hosts", "nr.failed", "results.exceptions"], "answer": 1, "why": "AggregatedResult.failed_hosts."},
        {"q": "NAPALM's core idea:", "options": ["Faster SSH", "Same getters and schema across vendors", "GUI", "SNMP polling"], "answer": 1, "why": "Vendor-neutral API."},
        {"q": "Adding a vendor with a driver interface means...", "options": ["Rewriting tests", "One new driver class", "Changing the schema", "Forking the framework"], "answer": 1, "why": "Tests depend on the interface."},
    ],
    "cards": [
        {"front": "Nornir init", "back": "`InitNornir(runner={...}, inventory={'plugin': 'SimpleInventory', ...})`"},
        {"front": "Nornir filter", "back": "`nr.filter(F(data__role='access') & F(site='lab-7'))`"},
        {"front": "Run a task", "back": "`r = nr.run(task=fn)`; `r[host][0].result`; `r.failed_hosts`"},
        {"front": "NAPALM getters", "back": "`get_facts()`, `get_interfaces()`, `get_lldp_neighbors()`, ..."},
        {"front": "Driver pattern", "back": "ABC interface + one translator class per vendor + common schema"},
    ],
}


M_7_7 = {
    "id": "7.7",
    "title": "NETCONF, RESTCONF & gNMI",
    "hours": 2.5,
    "summary": "Model-driven management: NETCONF with ncclient (capabilities, filters, edit-config), RESTCONF with plain HTTP and YANG-JSON, and the shape of gNMI telemetry.",
    "concepts": [
        {
            "title": "NETCONF with ncclient",
            "files": DEV,
            "local_only": NCCLIENT,
            "concept": "NETCONF is an XML RPC protocol over SSH (port 830). On connect, client and server exchange **capabilities** (supported features and YANG models). `get_config(source=\"running\", filter=(\"subtree\", xml))` returns configuration matching a subtree filter; `get()` adds operational state; `edit_config(target=..., config=xml)` changes it. Replies are XML: parse them with namespaces using lxml/ElementTree.",
            "why": "Structured, schema-validated data instead of screen-scraping, with transactions on platforms that support candidate configs. Most modern routers, switches and many Wi-Fi controllers expose NETCONF with YANG models.",
            "syntax": "with manager.connect(host=h, port=830, username=u, password=p, hostkey_verify=True) as m:\n    reply = m.get_config(source=\"running\", filter=(\"subtree\", FILTER))\n    m.edit_config(target=\"running\", config=CONFIG)",
            "code": """from lxml import etree  ## XML parsing with namespaces
from ncclient import manager  ## pip install ncclient

from fake_device import start  ## Simulated device with a NETCONF subsystem

NS = {"if": "urn:ietf:params:xml:ns:yang:ietf-interfaces"}  ## Prefix -> namespace map for XPath
FILTER = \"\"\"<interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
  <interface><name>GigabitEthernet2</name></interface>
</interfaces>\"\"\"  ## Subtree filter: only this interface
CONFIG = \"\"\"<config><interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
  <interface><name>GigabitEthernet3</name><description>ap-lab-09</description></interface>
</interfaces></config>\"\"\"  ## Change set for edit-config

with manager.connect(host="127.0.0.1", port=start("csr-1"), username="admin", password="lab123",  ## Port 830 on real devices
                     hostkey_verify=False, allow_agent=False, look_for_keys=False, timeout=10) as m:  ## hostkey_verify=False only for the simulator
    for cap in m.server_capabilities:  ## What the device advertised in its hello
        print("cap:", cap.split("?")[0])  ## Drop the module/revision query part
    reply = m.get_config(source="running", filter=("subtree", FILTER))  ## Filtered read
    root = etree.fromstring(reply.data_xml.encode())  ## Parse the <data> element
    for iface in root.xpath("//if:interface", namespaces=NS):  ## Namespace-aware XPath
        print(iface.findtext("if:name", namespaces=NS), "|", iface.findtext("if:description", namespaces=NS))  ## Fields by tag
    print("edit ok:", m.edit_config(target="running", config=CONFIG).ok)  ## <ok/> in the reply
    after = etree.fromstring(m.get_config(source="running").data_xml.encode())  ## Read everything back
    print([d.text for d in after.xpath("//if:description", namespaces=NS)])  ## Description changed on Gi3""",
            "under": "NETCONF messages are framed with `]]>]]>` (base 1.0) or chunked framing (base 1.1). ncclient handles the SSH `netconf` subsystem, hello exchange, framing and message-ids, and returns an `RPCReply` whose `.ok`, `.errors` and `.data_xml` you inspect. YANG models define the XML structure; the namespace URI identifies the model, which is why XPath needs the namespace map.",
            "gotchas": [],
            "best": "Check capabilities before using a feature (candidate, confirmed-commit), use subtree or XPath filters to fetch only what you need, prefer candidate + validate + commit where supported, and parse with namespaces rather than string searching.",
        },
        {
            "title": "RESTCONF: the same models over HTTP",
            "files": sim("fake_restconf.py"),
            "local_only": RESTCONF,
            "concept": "RESTCONF (RFC 8040) maps YANG data to URLs under `/restconf/data/`, with list keys in the path (`interface=GigabitEthernet2`). Use `Accept: application/yang-data+json` for JSON bodies whose top-level keys are prefixed with the module name (`ietf-interfaces:interfaces`). GET reads, PATCH merges, PUT replaces, DELETE removes; success for writes is often `204 No Content`.",
            "why": "It's ordinary HTTPS and JSON, so `requests` (Phase 6) is all you need: ideal for quick checks and for tools that already speak REST.",
            "syntax": "s.headers.update({\"Accept\": \"application/yang-data+json\", \"Content-Type\": \"application/yang-data+json\"})\nr = s.get(f\"{base}/restconf/data/ietf-interfaces:interfaces/interface=Gi2\")",
            "code": """import requests  ## pip install requests

from fake_restconf import start  ## Simulated RESTCONF server (see supporting files)

BASE = start() + "/restconf/data/ietf-interfaces:interfaces"  ## Data resource for the ietf-interfaces model
MEDIA = "application/yang-data+json"  ## RESTCONF's JSON media type

s = requests.Session()  ## Shared settings
s.auth = ("admin", "lab123")  ## HTTP basic auth (HTTPS on real devices)
s.headers.update({"Accept": MEDIA, "Content-Type": MEDIA})  ## Ask for and send YANG-JSON

r = s.get(BASE, timeout=5)  ## Whole list
for iface in r.json()["ietf-interfaces:interfaces"]["interface"]:  ## Module-prefixed top-level key
    print(iface["name"], iface["enabled"], repr(iface["description"]))  ## Typed JSON values

change = {"ietf-interfaces:interface": [{"name": "GigabitEthernet3", "description": "ap-lab-09", "enabled": True}]}  ## Body for one list entry
r = s.patch(f"{BASE}/interface=GigabitEthernet3", json=change, timeout=5)  ## Merge into the existing entry
print("PATCH", r.status_code)  ## 204 No Content on success

r = s.get(f"{BASE}/interface=GigabitEthernet3", timeout=5)  ## Read one entry back by key
print(r.json()["ietf-interfaces:interface"][0])  ## Updated

r = requests.get(BASE, auth=("admin", "lab123"), headers={"Accept": "application/json"}, timeout=5)  ## Wrong media type
print("plain JSON Accept:", r.status_code)  ## 406 Not Acceptable on strict servers""",
            "under": "A RESTCONF URL is the YANG path: `module:container/list=key/leaf`. Keys with special characters (like `/` in `GigabitEthernet1/0/1`) must be percent-encoded (`%2F`). PATCH is a merge (only the fields sent change), PUT replaces the target resource entirely.",
            "gotchas": [],
            "best": "Use HTTPS with certificate verification, a Session with the right media types, percent-encode keys, prefer PATCH for small changes, and read back after writing. Use NETCONF when you need transactions (candidate/commit) or locks.",
        },
        {
            "title": "gNMI paths and telemetry updates",
            "concept": "gNMI (gRPC Network Management Interface) uses the same YANG models with a compact path syntax, `/interfaces/interface[name=eth1]/state/counters/in-octets`, and **streaming telemetry**: devices push updates every N seconds or on change. Clients like `gnmic` or `pygnmi` subscribe and receive notifications with a timestamp, a prefix and updates (path + value). The code parses paths into elements and keys and turns notifications (as gnmic prints them in JSON) into rates.",
            "why": "Polling SNMP counters every 5 minutes misses the 10-second throughput collapse during a roam. Streaming telemetry at 1–10 s intervals is how modern labs and NOCs watch devices.",
            "syntax": "gnmic -a ap:57400 subscribe --path \"/interfaces/interface[name=wlan0]/state/counters\" --sample-interval 1s\n\nelem[name=key]/elem/leaf",
            "code": """import json  ## Notifications arrive as JSON from gnmic
import re  ## Path parsing


def parse_path(path):  ## "/a/b[k=v]/c" -> [("a", {}), ("b", {"k": "v"}), ("c", {})]
    elems = []  ## Result
    for part in path.strip("/").split("/"):  ## Split on slashes (keys here contain none)
        name = part.split("[", 1)[0]  ## Element name before any key
        keys = dict(re.findall(r"\\[(\\w[\\w-]*)=([^\\]]+)\\]", part))  ## All [key=value] pairs
        elems.append((name, keys))  ## Keep order
    return elems  ## Structured path


print(parse_path("/interfaces/interface[name=wlan0]/state/counters/in-octets"))  ## Elements with keys

NOTIFICATIONS = [  ## Two samples, 10 s apart (timestamps in ns)
    {"timestamp": 1760262900000000000, "prefix": "interfaces/interface[name=wlan0]/state/counters", "updates": [{"Path": "in-octets", "values": {"in-octets": "52344112"}}, {"Path": "out-octets", "values": {"out-octets": "11200345"}}]},  ## First sample
    {"timestamp": 1760262910000000000, "prefix": "interfaces/interface[name=wlan0]/state/counters", "updates": [{"Path": "in-octets", "values": {"in-octets": "1177344112"}}, {"Path": "out-octets", "values": {"out-octets": "36200345"}}]},  ## Second sample
]  ## End of samples

samples = {}  ## (interface, leaf) -> list of (time_s, value)
for n in json.loads(json.dumps(NOTIFICATIONS)):  ## Round-trip through JSON, as if read from gnmic
    iface = parse_path(n["prefix"])[1][1]["name"]  ## Key of the interface element
    for u in n["updates"]:  ## Each leaf in this notification
        value = int(next(iter(u["values"].values())))  ## Counters arrive as strings
        samples.setdefault((iface, u["Path"]), []).append((n["timestamp"] / 1e9, value))  ## Seconds, value

for (iface, leaf), pts in samples.items():  ## Rate from the last two samples
    (t0, v0), (t1, v1) = pts[-2:]  ## Previous and latest
    print(f"{iface} {leaf}: {(v1 - v0) * 8 / (t1 - t0) / 1e6:.1f} Mbps")  ## Bytes -> bits per second -> Mbps""",
            "under": "On the wire gNMI uses protobuf over gRPC (HTTP/2, usually TLS on port 57400 or 9339), and paths are structured messages (`PathElem` with name and key map); the string form is for humans and tools. Subscriptions can be SAMPLE (periodic), ON_CHANGE or TARGET_DEFINED. Counters are uint64 in the model, which is why they're sent as strings in JSON encodings.",
            "gotchas": [],
            "best": "Subscribe to exactly the paths you need at the interval you need, store raw counters with timestamps (compute rates later), handle counter resets after reboots, and use gnmic for exploration before writing code.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "files": DEV,
            "local_only": NCCLIENT,
            "prompt": "Connect with ncclient and print whether the device supports the candidate datastore.",
            "solution": "Look for the candidate capability in `m.server_capabilities` (ncclient also exposes a shortcut, `':candidate' in m.server_capabilities`).",
            "solution_code": """from ncclient import manager
from fake_device import start

with manager.connect(host="127.0.0.1", port=start(), username="admin", password="lab123",
                     hostkey_verify=False, allow_agent=False, look_for_keys=False) as m:
    print("candidate:", ":candidate" in m.server_capabilities)
    print("confirmed-commit:", ":confirmed-commit" in m.server_capabilities)""",
        },
        {
            "level": "Medium",
            "prompt": "Parse this NETCONF reply with ElementTree (standard library) and print each interface name with its enabled flag as a bool.",
            "code": """REPLY = '''<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101"><data>
<interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
<interface><name>Gi1</name><enabled>true</enabled></interface>
<interface><name>Gi3</name><enabled>false</enabled></interface>
</interfaces></data></rpc-reply>'''""",
            "solution": "Use a namespace map with findall; convert the text 'true'/'false' explicitly.",
            "solution_code": """import xml.etree.ElementTree as ET

REPLY = '''<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="101"><data>
<interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
<interface><name>Gi1</name><enabled>true</enabled></interface>
<interface><name>Gi3</name><enabled>false</enabled></interface>
</interfaces></data></rpc-reply>'''
NS = {"if": "urn:ietf:params:xml:ns:yang:ietf-interfaces"}
root = ET.fromstring(REPLY)
for iface in root.findall(".//if:interface", NS):
    print(iface.findtext("if:name", namespaces=NS), iface.findtext("if:enabled", namespaces=NS) == "true")""",
        },
        {
            "level": "Hard",
            "files": sim("fake_restconf.py"),
            "local_only": RESTCONF,
            "prompt": "Write `set_description(name, text)` for the RESTCONF server that percent-encodes the key, PATCHes, verifies by reading back, and raises if the read-back differs. Try it on `GigabitEthernet1` and on a missing interface.",
            "solution": "`urllib.parse.quote(name, safe='')` encodes the key; non-2xx statuses become exceptions with the server's error-tag.",
            "solution_code": """from urllib.parse import quote

import requests
from fake_restconf import start

BASE = start() + "/restconf/data/ietf-interfaces:interfaces"
s = requests.Session()
s.auth = ("admin", "lab123")
s.headers.update({"Accept": "application/yang-data+json", "Content-Type": "application/yang-data+json"})


def set_description(name, text):
    url = f"{BASE}/interface={quote(name, safe='')}"
    r = s.patch(url, json={"ietf-interfaces:interface": [{"name": name, "description": text}]}, timeout=5)
    if r.status_code != 204:
        tag = r.json()["ietf-restconf:errors"]["error"][0]["error-tag"]
        raise RuntimeError(f"{name}: HTTP {r.status_code} {tag}")
    got = s.get(url, timeout=5).json()["ietf-interfaces:interface"][0]["description"]
    if got != text:
        raise RuntimeError(f"{name}: read back {got!r}")
    return got


print(set_description("GigabitEthernet1", "uplink to core-2"))
try:
    set_description("GigabitEthernet9", "x")
except RuntimeError as e:
    print(e)""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "NETCONF vs RESTCONF vs gNMI?", "a": "All use YANG models. NETCONF: XML RPCs over SSH, rich operations (candidate, commit, lock, validate). RESTCONF: HTTP verbs on YANG paths with JSON/XML, simple to use, fewer transactional features. gNMI: gRPC/protobuf, efficient, built for streaming telemetry plus get/set.", "follow": "Which would you use for 1-second interface counters? (gNMI subscribe.)"},
        {"level": "Intermediate", "q": "What are NETCONF capabilities?", "a": "Strings exchanged in the hello message listing protocol versions, optional features (:candidate, :confirmed-commit, :validate, :xpath) and supported YANG modules with revisions. Clients check them before using a feature.", "follow": "What's the candidate datastore? (A scratch config you edit, validate and commit atomically.)"},
        {"level": "Advanced", "q": "Why use model-driven APIs instead of CLI scraping in tests?", "a": "Structured, typed data with stable schemas (no regex breakage when CLI output changes), atomic changes with validation and rollback, and telemetry streaming. The cost: learning YANG and platform model coverage gaps.", "follow": "How do you explore a device's models? (Capabilities, get-schema, pyang, YANG Suite, gnmic capabilities.)"},
    ],
    "quiz": [
        {"q": "NETCONF default port:", "options": ["22", "443", "830", "57400"], "answer": 2, "why": "830 over SSH."},
        {"q": "RESTCONF JSON media type:", "options": ["application/json", "application/yang-data+json", "text/yang", "application/netconf"], "answer": 1, "why": "yang-data+json."},
        {"q": "RESTCONF partial update method:", "options": ["PUT", "PATCH", "POST", "OPTIONS"], "answer": 1, "why": "PATCH merges."},
        {"q": "Streaming telemetry protocol:", "options": ["SNMP", "gNMI", "Syslog", "TFTP"], "answer": 1, "why": "gNMI subscribe."},
        {"q": "XPath on NETCONF XML needs...", "options": ["Nothing special", "A namespace map", "JSON conversion", "A DTD"], "answer": 1, "why": "Elements are namespaced."},
    ],
    "cards": [
        {"front": "ncclient read", "back": "`m.get_config(source='running', filter=('subtree', xml)).data_xml`"},
        {"front": "ncclient write", "back": "`m.edit_config(target='candidate', config=xml); m.commit()`"},
        {"front": "RESTCONF URL", "back": "`/restconf/data/module:container/list=key`"},
        {"front": "RESTCONF headers", "back": "`Accept/Content-Type: application/yang-data+json`"},
        {"front": "gNMI path", "back": "`/interfaces/interface[name=eth1]/state/counters/in-octets`"},
    ],
}


SNMP_FILES = sim("fake_snmp.py")

M_7_8 = {
    "id": "7.8",
    "title": "SNMP with pysnmp",
    "hours": 1.5,
    "summary": "Read device data over SNMP: OIDs and MIBs, GET and WALK with pysnmp's asyncio API, building tables from columns, counter rates with wrap handling, and common failure modes.",
    "concepts": [
        {
            "title": "GET with pysnmp",
            "files": SNMP_FILES,
            "local_only": PYSNMP,
            "concept": "SNMP addresses each value by an **OID** (`1.3.6.1.2.1.1.5.0` is sysName). MIBs give OIDs names (`SNMPv2-MIB::sysName.0`). pysnmp 7's API is asyncio-based: `get_cmd(engine, CommunityData(\"public\"), target, ContextData(), ObjectType(ObjectIdentity(...)))` returns `(error_indication, error_status, error_index, var_binds)`. Check the first two before using the values. The agent here is a small simulator on a local UDP port.",
            "why": "Almost every AP, switch, PDU and UPS speaks SNMP, and many labs still use it for inventory, uptime and interface counters, especially on older or simpler devices.",
            "syntax": "target = await UdpTransportTarget.create((host, 161), timeout=2, retries=1)\nerr_ind, err_stat, err_idx, binds = await get_cmd(\n    SnmpEngine(), CommunityData(\"public\"), target, ContextData(),\n    ObjectType(ObjectIdentity(\"SNMPv2-MIB\", \"sysName\", 0)))",
            "code": """import asyncio  ## pysnmp 7 is asyncio-based

from pysnmp.hlapi.v3arch.asyncio import (CommunityData, ContextData, ObjectIdentity, ObjectType,  ## pip install pysnmp
                                         SnmpEngine, UdpTransportTarget, get_cmd)  ## High-level API

from fake_snmp import start  ## Simulated SNMP agent (see supporting files)

PORT = start()  ## UDP port; real agents listen on 161


async def get(*objects):  ## GET one or more variables
    engine = SnmpEngine()  ## Holds SNMP state (one per program is fine)
    target = await UdpTransportTarget.create(("127.0.0.1", PORT), timeout=1, retries=1)  ## Where and how patiently
    err_ind, err_stat, err_idx, binds = await get_cmd(engine, CommunityData("public", mpModel=1),  ## mpModel=1 means SNMPv2c
                                                      target, ContextData(), *objects)  ## One ObjectType per variable
    engine.close_dispatcher()  ## Release the UDP socket
    if err_ind:  ## Transport problem: timeout, unknown host...
        raise RuntimeError(str(err_ind))  ## No answer at all
    if err_stat:  ## The agent answered with an error
        raise RuntimeError(f"{err_stat.prettyPrint()} at {binds[int(err_idx) - 1][0]}")  ## Which variable failed
    return [(oid.prettyPrint(), val.prettyPrint()) for oid, val in binds]  ## Names and values as text


rows = asyncio.run(get(  ## Several variables in one request
    ObjectType(ObjectIdentity("SNMPv2-MIB", "sysName", 0)),  ## By MIB name (bundled MIB)
    ObjectType(ObjectIdentity("SNMPv2-MIB", "sysDescr", 0)),  ## Description
    ObjectType(ObjectIdentity("1.3.6.1.2.1.1.3.0")),  ## By numeric OID: sysUpTime
))  ## End of the call
for name, value in rows:  ## Print them
    print(name, "=", value)  ## MIB-resolved names
ticks = int(rows[2][1])  ## TimeTicks are hundredths of a second
print(f"uptime: {ticks // 8_640_000} days {ticks % 8_640_000 // 360_000} h")  ## Human-readable""",
            "under": "A GET is one UDP datagram with a BER-encoded PDU containing the community string and variable bindings; the agent replies with the same OIDs and their values. SNMPv2c sends the community in clear text; SNMPv3 (`UsmUserData`) adds authentication and encryption. pysnmp resolves names like `SNMPv2-MIB::sysName` using compiled MIB modules; numeric OIDs always work, even for MIBs you haven't compiled.",
            "gotchas": [
                {
                    "title": "A wrong community string looks like a timeout",
                    "files": SNMP_FILES,
                    "local_only": PYSNMP,
                    "note": "Agents silently drop requests with an unknown community (that's by design), so the client just times out. When SNMP 'times out' on a reachable device, check community, ACLs and SNMP version before blaming the network.",
                    "wrong": """import asyncio
from pysnmp.hlapi.v3arch.asyncio import *
from fake_snmp import start

port = start()


async def main():
    engine = SnmpEngine()
    target = await UdpTransportTarget.create(("127.0.0.1", port), timeout=0.5, retries=0)
    err_ind, *_ = await get_cmd(engine, CommunityData("pubic"), target, ContextData(),
                                ObjectType(ObjectIdentity("1.3.6.1.2.1.1.5.0")))
    engine.close_dispatcher()
    print("error:", err_ind)

asyncio.run(main())""",
                    "fixed": """import asyncio
from pysnmp.hlapi.v3arch.asyncio import *
from fake_snmp import start

port = start()


async def main():
    engine = SnmpEngine()
    target = await UdpTransportTarget.create(("127.0.0.1", port), timeout=0.5, retries=0)
    err_ind, _, _, binds = await get_cmd(engine, CommunityData("public"), target, ContextData(),
                                         ObjectType(ObjectIdentity("1.3.6.1.2.1.1.5.0")))
    engine.close_dispatcher()
    print("error:", err_ind, "| value:", binds[0][1].prettyPrint())

asyncio.run(main())""",
                },
            ],
            "best": "Use SNMPv3 with authPriv where possible, short timeouts with one retry, numeric OIDs in code (with a comment naming them), check error_indication and error_status on every call, and prefer streaming telemetry or APIs for high-frequency data.",
        },
        {
            "title": "WALK a table and compute rates from counters",
            "files": SNMP_FILES,
            "local_only": PYSNMP,
            "concept": "Tables like ifTable are columns of OIDs indexed by row: `ifDescr.2`, `ifOperStatus.2` and `ifInOctets.2` all describe interface 2. `walk_cmd(...)` (GETNEXT) or `bulk_walk_cmd(...)` (GETBULK, fewer round trips) iterate a subtree; with `lexicographicMode=False` they stop at the end of the requested column. Build rows by index, then turn Counter32 values into rates using deltas, handling the 2³² wrap.",
            "why": "Interface utilisation on the AP uplink during a throughput test, or radio interface state across 50 APs, are table walks plus a little arithmetic.",
            "syntax": "async for err_ind, err_stat, err_idx, binds in walk_cmd(engine, community, target, ContextData(),\n        ObjectType(ObjectIdentity(\"1.3.6.1.2.1.2.2.1.2\")), lexicographicMode=False):\n    ...",
            "code": """import asyncio  ## asyncio API

from pysnmp.hlapi.v3arch.asyncio import (CommunityData, ContextData, ObjectIdentity, ObjectType,  ## pip install pysnmp
                                         SnmpEngine, UdpTransportTarget, walk_cmd)  ## GETNEXT-based walk

from fake_snmp import start  ## Simulated agent

PORT = start()  ## Agent's UDP port
COLUMNS = {"descr": "1.3.6.1.2.1.2.2.1.2", "oper": "1.3.6.1.2.1.2.2.1.8", "in_octets": "1.3.6.1.2.1.2.2.1.10"}  ## ifTable columns by numeric OID


async def walk_table(engine, target):  ## Returns {ifIndex: {column: value}}
    table = {}  ## Rows keyed by interface index
    for col, oid in COLUMNS.items():  ## One walk per column
        async for err_ind, err_stat, _, binds in walk_cmd(engine, CommunityData("public"), target, ContextData(),  ## Async iterator
                                                          ObjectType(ObjectIdentity(oid)), lexicographicMode=False):  ## Stop at the end of this column
            if err_ind or err_stat:  ## Stop on any error
                raise RuntimeError(str(err_ind or err_stat.prettyPrint()))  ## Report it
            for name, value in binds:  ## Usually one per step
                index = int(name.prettyPrint().rsplit(".", 1)[1])  ## Last sub-identifier is the row index
                table.setdefault(index, {})[col] = value.prettyPrint() if col == "descr" else int(value)  ## Text or number
    return table  ## Complete table


def delta32(old, new):  ## Counter32 difference, allowing for one wrap past 2**32
    return new - old if new >= old else new + 2**32 - old  ## A wrap looks like a decrease


async def main():  ## Two polls, as a monitor would do
    engine = SnmpEngine()  ## Shared engine
    target = await UdpTransportTarget.create(("127.0.0.1", PORT), timeout=1, retries=1)  ## Agent address
    first = await walk_table(engine, target)  ## Poll 1
    second = await walk_table(engine, target)  ## Poll 2 (the simulator advances counters per poll)
    engine.close_dispatcher()  ## Release the socket
    interval = 10  ## Seconds between polls in production (fixed here for a reproducible example)
    for idx, row in sorted(second.items()):  ## One line per interface
        state = {1: "up", 2: "down"}.get(row["oper"], row["oper"])  ## ifOperStatus enum
        mbps = delta32(first[idx]["in_octets"], row["in_octets"]) * 8 / interval / 1e6  ## Bytes -> bits per second -> Mbps
        print(f"{idx} {row['descr']:<6} {state:<5} {mbps:6.1f} Mbps in")  ## Aligned columns

asyncio.run(main())  ## Run it""",
            "under": "GETNEXT returns the next OID in lexicographic order after the one requested, so walking from a column OID visits each row in index order; without `lexicographicMode=False` the walk would continue into the next column and beyond. wlan0's counter in the simulator starts just below 2³² and wraps between polls, which is why the naive `new - old` would be negative. For fast links, use the 64-bit ifHCInOctets (Counter64) to avoid frequent wraps.",
            "gotchas": [],
            "best": "Walk only the columns you need, prefer GETBULK on SNMPv2c/v3, use 64-bit HC counters on anything faster than 100 Mbps, handle wraps and counter resets (sysUpTime going backwards means a reboot), and store raw counters with timestamps.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Convert SNMP TimeTicks (hundredths of a second) to a `days, hh:mm:ss` string, and check it on 26784300.",
            "solution": "divmod chain on seconds.",
            "solution_code": """def ticks_to_text(ticks):
    seconds = ticks // 100
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{days} days, {hours:02}:{minutes:02}:{seconds:02}"


print(ticks_to_text(26784300))
print(ticks_to_text(99))""",
        },
        {
            "level": "Medium",
            "prompt": "Utilisation: an interface's ifSpeed is 1 Gbps. Two ifInOctets samples 300 s apart are 4294900000 and 120000000 (it wrapped). Compute the average utilisation in percent.",
            "solution": "Wrap-aware delta × 8 / interval / speed × 100.",
            "solution_code": """def delta32(old, new):
    return new - old if new >= old else new + 2**32 - old


old, new, interval, speed = 4294900000, 120000000, 300, 1_000_000_000
bits = delta32(old, new) * 8
print(f"delta {delta32(old, new)} bytes, utilisation {bits / interval / speed * 100:.2f} %")""",
        },
        {
            "level": "Hard",
            "files": SNMP_FILES,
            "local_only": PYSNMP,
            "prompt": "Use `bulk_walk_cmd` (GETBULK) to fetch the whole system group (`1.3.6.1.2.1.1`) and print each OID's name and value.",
            "solution": "bulk_walk_cmd takes nonRepeaters and maxRepetitions; lexicographicMode=False stops at the end of the subtree.",
            "solution_code": """import asyncio
from pysnmp.hlapi.v3arch.asyncio import *
from fake_snmp import start

port = start()


async def main():
    engine = SnmpEngine()
    target = await UdpTransportTarget.create(("127.0.0.1", port), timeout=1, retries=1)
    async for err_ind, err_stat, _, binds in bulk_walk_cmd(engine, CommunityData("public"), target, ContextData(),
                                                          0, 10, ObjectType(ObjectIdentity("1.3.6.1.2.1.1")),
                                                          lexicographicMode=False):
        if err_ind or err_stat:
            print("error", err_ind or err_stat)
            break
        for oid, val in binds:
            print(oid.prettyPrint(), "=", val.prettyPrint())
    engine.close_dispatcher()

asyncio.run(main())""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "SNMP v2c vs v3?", "a": "v2c authenticates with a plain-text community string; v3 adds users with authentication (SHA) and privacy (AES encryption) and access control. Use v3 authPriv anywhere outside an isolated lab.", "follow": "Which port do traps use? (UDP 162; polling uses 161.)"},
        {"level": "Intermediate", "q": "GET vs GETNEXT vs GETBULK?", "a": "GET reads exact OIDs. GETNEXT returns the next OID lexicographically, used to walk tables. GETBULK (v2c+) returns many next values per request, reducing round trips for large tables.", "follow": "Why can walks be slow on big devices? (Thousands of rows; use bulk and only needed columns.)"},
        {"level": "Intermediate", "q": "How do you compute interface throughput from SNMP?", "a": "Poll ifHCInOctets/ifHCOutOctets at known intervals, take wrap-aware deltas, multiply by 8 and divide by elapsed seconds; compare with ifHighSpeed for utilisation. Detect reboots via sysUpTime.", "follow": "Why prefer HC counters? (32-bit counters wrap every ~34 s at 1 Gbps.)"},
    ],
    "quiz": [
        {"q": "SNMP polling port:", "options": ["UDP 161", "TCP 161", "UDP 162", "TCP 22"], "answer": 0, "why": "Traps use 162."},
        {"q": "Wrong community on v2c usually gives...", "options": ["authError", "A timeout", "noSuchName", "A crash"], "answer": 1, "why": "Agents drop it silently."},
        {"q": "Stop a walk at the end of the column:", "options": ["maxRows=1", "lexicographicMode=False", "strict=True", "bulk=True"], "answer": 1, "why": "Otherwise it continues."},
        {"q": "TimeTicks unit:", "options": ["Milliseconds", "Hundredths of a second", "Seconds", "Microseconds"], "answer": 1, "why": "1/100 s."},
        {"q": "Counter32 at 1 Gbps wraps roughly every...", "options": ["34 s", "5 min", "1 h", "Never"], "answer": 0, "why": "2^32 bytes × 8 / 1e9 ≈ 34 s."},
    ],
    "cards": [
        {"front": "sysName / sysUpTime OIDs", "back": "1.3.6.1.2.1.1.5.0 / 1.3.6.1.2.1.1.3.0"},
        {"front": "ifTable columns", "back": "ifDescr .2.2.1.2, ifOperStatus .2.2.1.8, ifInOctets .2.2.1.10"},
        {"front": "pysnmp GET", "back": "`await get_cmd(SnmpEngine(), CommunityData('public'), target, ContextData(), ObjectType(...))`"},
        {"front": "Check results", "back": "error_indication (transport) and error_status (agent) before values"},
        {"front": "Counter wrap", "back": "`new - old if new >= old else new + 2**32 - old`"},
    ],
}
