"""Phase 6 content: modules 6.6-6.10 (general automation)."""

from auto_support import FAKE_CLI, FAKE_CONSOLE, needs

SERIAL = needs("pyserial") + " and a pseudo-terminal (Linux/macOS)"
PEXPECT = needs("pexpect") + " and a pseudo-terminal (Linux/macOS; on Windows use wexpect or Paramiko)"
WATCHDOG = needs("watchdog") + " and a background observer thread"
JINJA = needs("jinja2")
JINJA_PW = needs("jinja2 playwright")
CONSOLE_FILES = {"fake_console.py": FAKE_CONSOLE}
CLI_FILES = {"fake_cli.py": FAKE_CLI}

M_6_6 = {
    "id": "6.6",
    "title": "Email, Slack & Teams Notifications",
    "hours": 1.5,
    "summary": "Send results where people will see them: multipart emails with attachments, Slack and Teams webhook messages, with secrets from the environment and senders you can test.",
    "concepts": [
        {
            "title": "Building and sending email with EmailMessage",
            "concept": "`email.message.EmailMessage` builds a correct MIME message: headers by item assignment, `set_content()` for the plain-text body, `add_alternative(..., subtype=\"html\")` for an HTML version, `add_attachment()` for files. `smtplib.SMTP(host, 587)` with `starttls()` and `login()` sends it. Keep building and sending separate, and pass the SMTP class in, so tests can use a fake.",
            "why": "The nightly run's summary email is often the only report managers read. A plain-text fallback, an HTML table and the CSV attached cover every mail client and every reader.",
            "syntax": "msg = EmailMessage()\nmsg[\"Subject\"] = \"...\"\nmsg.set_content(text)\nmsg.add_alternative(html, subtype=\"html\")\nmsg.add_attachment(data, maintype=\"text\", subtype=\"csv\", filename=\"r.csv\")\nwith smtplib.SMTP(host, 587) as s: s.starttls(); s.login(u, p); s.send_message(msg)",
            "code": """import os  ## Credentials come from the environment
import smtplib  ## Standard-library SMTP client
from email.message import EmailMessage  ## Modern email API


def build_report(passed, failed, csv_bytes):  ## Pure function: easy to test
    msg = EmailMessage()  ## Starts as a simple text message
    msg["Subject"] = f"[nightly] Wi-Fi regression: {failed} failed of {passed + failed}"  ## Headline in the subject
    msg["From"] = "wifi-ci@example.com"  ## Sender
    msg["To"] = ", ".join(["qa-team@example.com", "fw-leads@example.com"])  ## Several recipients
    msg.set_content(f"Passed: {passed}\\nFailed: {failed}\\nResults attached.")  ## Plain-text body (fallback)
    msg.add_alternative(f"<h2>Nightly run</h2><p><b>{failed}</b> failed of {passed + failed}</p>", subtype="html")  ## HTML version
    msg.add_attachment(csv_bytes, maintype="text", subtype="csv", filename="results.csv")  ## The CSV file
    return msg  ## Built, not sent


def send(msg, host="smtp.example.com", port=587, smtp_class=smtplib.SMTP):  ## smtp_class is injectable
    with smtp_class(host, port, timeout=10) as smtp:  ## Connect (closed by the with block)
        smtp.starttls()  ## Upgrade to TLS before sending credentials
        smtp.login(os.environ.get("SMTP_USER", "wifi-ci"), os.environ.get("SMTP_PASSWORD", ""))  ## Never hard-code passwords
        smtp.send_message(msg)  ## Reads From/To from the headers


class FakeSMTP:  ## Test double with the same interface
    log = []  ## Shared record of calls

    def __init__(self, host, port, timeout):  ## Same signature as smtplib.SMTP
        self.log.append(f"connect {host}:{port}")  ## Record the connection

    def __enter__(self):  ## Context manager support
        return self  ## The "connection"

    def __exit__(self, *exc):  ## Nothing to close
        return False  ## Don't swallow exceptions

    def starttls(self):  ## Record TLS
        self.log.append("starttls")  ## Order matters: TLS before login

    def login(self, user, password):  ## Record the login (not the password)
        self.log.append(f"login {user}")  ## Username only

    def send_message(self, msg):  ## Record what would be sent
        self.log.append(f"send to {msg['To']}")  ## Recipients


msg = build_report(41, 2, b"test,result\\nrvr_5g,fail\\n")  ## Build once
print(msg["Subject"])  ## Header access
print([part.get_content_type() for part in msg.walk()])  ## The MIME tree
send(msg, smtp_class=FakeSMTP)  ## Exercise the sending code without a server
print(FakeSMTP.log)  ## What it did, in order""",
            "under": "Adding an alternative turns the message into `multipart/alternative` (text and HTML versions of the same content); adding an attachment wraps everything in `multipart/mixed`. `msg.walk()` iterates the tree depth-first. `send_message` derives the envelope sender and recipients from the From/To/Cc headers. Port 587 is submission with STARTTLS; 465 is implicit TLS (`smtplib.SMTP_SSL`).",
            "gotchas": [
                {
                    "title": "A webhook URL or password in the source",
                    "note": "Webhook URLs are bearer secrets: anyone who has one can post to your channel. Committed to git (or printed in CI logs) they leak. Read them from the environment (set by the CI secret store) and skip notifications cleanly when absent.",
                    "wrong": """SLACK_WEBHOOK = "https://hooks.slack.com/services/T000/B000/XXXXXXXXXXXX"


def notify(text):
    print(f"posting {text!r} to {SLACK_WEBHOOK}")


notify("nightly: 2 failed")""",
                    "fixed": """import os


def notify(text):
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        print("SLACK_WEBHOOK_URL not set; skipping notification")
        return
    print(f"posting {text!r} to Slack")


notify("nightly: 2 failed")""",
                },
            ],
            "best": "Build messages in pure functions and test them, inject the transport, take credentials from the environment, include a plain-text part, keep attachments small (link to large artifacts instead), and never let a notification failure fail the test run.",
        },
        {
            "title": "Slack and Teams webhooks",
            "concept": "Incoming webhooks accept an HTTP POST with a JSON body. Slack uses **Block Kit** (`text` as a fallback plus `blocks`: header, section fields, action buttons); Microsoft Teams (Workflows/Power Automate webhooks) accepts an **Adaptive Card** inside a message `attachments` list. Build the payload in one function per service and send it with one small `post_json` helper whose HTTP opener can be swapped in tests.",
            "why": "A red message in the team channel 2 minutes after a nightly failure, with a button to the report, gets acted on. An email at 6 a.m. often doesn't.",
            "syntax": "payload = {\"text\": \"...\", \"blocks\": [...]}\nreq = urllib.request.Request(url, data=json.dumps(payload).encode(),\n    headers={\"Content-Type\": \"application/json\"}, method=\"POST\")\nurllib.request.urlopen(req, timeout=10)",
            "code": """import json  ## Payloads are JSON
import urllib.request  ## Standard-library HTTP (requests.post(url, json=...) works the same)

RUN = {"suite": "nightly-rvr", "passed": 41, "failed": 2, "url": "https://ci.example.com/runs/812"}  ## Results to announce


def slack_payload(run):  ## Slack Block Kit message
    icon = ":white_check_mark:" if run["failed"] == 0 else ":x:"  ## Emoji shortcode by outcome
    return {  ## The JSON body
        "text": f"{icon} {run['suite']}: {run['failed']} failed",  ## Fallback for notifications and old clients
        "blocks": [  ## Rich layout
            {"type": "header", "text": {"type": "plain_text", "text": f"{run['suite']} finished"}},  ## Title
            {"type": "section", "fields": [{"type": "mrkdwn", "text": f"*Passed:* {run['passed']}"}, {"type": "mrkdwn", "text": f"*Failed:* {run['failed']}"}]},  ## Two-column facts
            {"type": "actions", "elements": [{"type": "button", "text": {"type": "plain_text", "text": "Open report"}, "url": run["url"]}]},  ## Link button
        ],  ## End of blocks
    }  ## End of payload


def teams_payload(run):  ## Adaptive Card for Microsoft Teams
    card = {"type": "AdaptiveCard", "version": "1.4", "body": [  ## Card schema
        {"type": "TextBlock", "text": f"{run['suite']}: {run['failed']} failed", "weight": "Bolder", "color": "Attention" if run["failed"] else "Good"},  ## Coloured headline
        {"type": "FactSet", "facts": [{"title": "Passed", "value": str(run["passed"])}, {"title": "Failed", "value": str(run["failed"])}]},  ## Key/value facts
    ], "actions": [{"type": "Action.OpenUrl", "title": "Open report", "url": run["url"]}]}  ## Button
    return {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": card}]}  ## Teams envelope


def post_json(url, payload, opener=urllib.request.urlopen):  ## One sender for every webhook
    body = json.dumps(payload).encode()  ## Serialise to bytes
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")  ## Build the request
    with opener(req, timeout=10) as resp:  ## Real network call in production
        return resp.status  ## 200 on success


class FakeResponse:  ## What a fake opener returns
    status = 200  ## Pretend success

    def __enter__(self):  ## Context manager protocol
        return self  ## The response

    def __exit__(self, *exc):  ## Nothing to close
        return False  ## Propagate errors


sent = []  ## Captured requests


def fake_opener(req, timeout):  ## Same signature as urlopen
    sent.append((req.get_method(), req.get_header("Content-type"), json.loads(req.data)))  ## Record method, header and body
    return FakeResponse()  ## No network


print(slack_payload(RUN)["text"], "|", len(slack_payload(RUN)["blocks"]), "blocks")  ## Slack summary
print(post_json("https://hooks.example/slack", slack_payload(RUN), opener=fake_opener))  ## 200 from the fake
print(post_json("https://hooks.example/teams", teams_payload(RUN), opener=fake_opener))  ## Same helper, different payload
print([(m, h, list(b)) for m, h, b in sent])  ## What would have gone over the wire""",
            "under": "`urllib.request.Request` with `data=` and `method=\"POST\"` sends the bytes as the body; `get_header` uses the capitalised form `Content-type` because urllib normalises header names. Slack shows `text` in push notifications even when `blocks` render in the channel. Webhooks are rate-limited (Slack: about one message per second per webhook), so batch rather than posting per test.",
            "gotchas": [],
            "best": "Notify on state changes (green → red, red → green) rather than every run, include the one link people need, keep payload builders pure and unit-tested, time out quickly, and swallow (but log) notification errors so they never mask test results.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Build an EmailMessage for a single failed test with a subject, From, To and a two-line body, and print it as text.",
            "solution": "`str(msg)` (or `msg.as_string()`) shows the headers and body exactly as they'd be sent.",
            "solution_code": """from email.message import EmailMessage

msg = EmailMessage()
msg["Subject"] = "FAIL test_rvr_6g on lab-07"
msg["From"] = "wifi-ci@example.com"
msg["To"] = "qa-team@example.com"
msg.set_content("6G/160 at 42 dB: 1890 Mbps (KPI 2000)\\nhttps://ci.example.com/runs/812")
print(msg.as_string())""",
        },
        {
            "level": "Medium",
            "prompt": "Only notify when the suite's status changes. Keep the previous status in a small JSON state file and return the message to send (or None).",
            "solution": "Read the old state (default unknown), compare, write the new state, and produce a message only on change.",
            "solution_code": """import json
from pathlib import Path

STATE = Path("notify_state.json")


def on_result(suite, failed):
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    status = "red" if failed else "green"
    previous = state.get(suite)
    state[suite] = status
    STATE.write_text(json.dumps(state))
    if previous == status:
        return None
    return f"{suite} is now {status.upper()} (was {previous or 'unknown'})"


for failed in [0, 0, 3, 2, 0]:
    print(on_result("nightly-rvr", failed))""",
        },
        {
            "level": "Hard",
            "prompt": "Make `post_json` retry up to 3 times on `urllib.error.URLError` with a delay (injectable sleep), and give up quietly (return None and log) if every attempt fails. Test it with an opener that fails twice.",
            "solution": "Wrap the opener call in a loop that catches URLError, sleeps between attempts and returns the status on success.",
            "solution_code": """import json
import urllib.error
import urllib.request


def post_json(url, payload, opener=urllib.request.urlopen, attempts=3, delay=2.0, sleep=None, log=print):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    for i in range(1, attempts + 1):
        try:
            with opener(req, timeout=10) as resp:
                return resp.status
        except urllib.error.URLError as e:
            log(f"attempt {i} failed: {e.reason}")
            if i < attempts and sleep:
                sleep(delay)
    log("giving up; notification not sent")
    return None


class OK:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *a): return False


calls = {"n": 0}


def flaky_opener(req, timeout):
    calls["n"] += 1
    if calls["n"] < 3:
        raise urllib.error.URLError("connection reset")
    return OK()


waits = []
print(post_json("https://hooks.example/x", {"text": "hi"}, opener=flaky_opener, sleep=waits.append))
print("slept:", waits)
print(post_json("https://hooks.example/x", {"text": "hi"}, opener=lambda r, timeout: (_ for _ in ()).throw(urllib.error.URLError("down")), sleep=waits.append))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "How do you send an email with an attachment in Python?", "a": "Build an email.message.EmailMessage (headers, set_content, add_attachment with maintype/subtype/filename) and send it with smtplib.SMTP using starttls() and login(), credentials from environment variables.", "follow": "Port 587 vs 465? (STARTTLS submission vs implicit TLS with SMTP_SSL.)"},
        {"level": "Intermediate", "q": "How would you avoid alert fatigue from CI notifications?", "a": "Notify on status transitions, aggregate per run instead of per test, route by ownership (the failing area's channel), include the essential numbers and one link, and keep noise (known flaky tests) out with quarantine.", "follow": "Where do you store the previous status? (A small state file/artifact, the CI API, or a DB.)"},
        {"level": "Intermediate", "q": "How do you test code that sends notifications?", "a": "Separate payload building (pure, unit-tested by asserting on the dict) from sending (inject the SMTP class or HTTP opener and use a fake that records calls). Optionally one integration test against a sandbox channel.", "follow": "Why not mock smtplib globally? (Injection is explicit and doesn't depend on import paths.)"},
    ],
    "quiz": [
        {"q": "Add an HTML version to an EmailMessage:", "options": ["msg.html = ...", "msg.add_alternative(html, subtype='html')", "msg.set_content(html)", "msg.attach_html()"], "answer": 1, "why": "Creates multipart/alternative."},
        {"q": "A Slack webhook URL should be stored...", "options": ["In the code", "In the README", "In a CI secret / env var", "In the test name"], "answer": 2, "why": "It's a bearer secret."},
        {"q": "Teams rich message format:", "options": ["Block Kit", "Adaptive Card", "Markdown only", "HTML email"], "answer": 1, "why": "Adaptive Cards."},
        {"q": "`smtp.starttls()` should be called...", "options": ["After login", "Before login", "After send", "Never"], "answer": 1, "why": "Encrypt before sending credentials."},
        {"q": "Best trigger for a team-channel alert:", "options": ["Every test result", "Every run", "Status changes", "Only on Mondays"], "answer": 2, "why": "Reduces noise."},
    ],
    "cards": [
        {"front": "Multipart email", "back": "`set_content(text)` + `add_alternative(html, subtype='html')` + `add_attachment(...)`"},
        {"front": "Send email", "back": "`with smtplib.SMTP(host, 587) as s: s.starttls(); s.login(u, p); s.send_message(msg)`"},
        {"front": "Slack webhook body", "back": "`{'text': fallback, 'blocks': [header, section, actions]}`"},
        {"front": "POST JSON (stdlib)", "back": "`Request(url, data=json.dumps(p).encode(), headers=..., method='POST')`"},
        {"front": "Testable sender", "back": "Inject `smtp_class` / `opener`; fake records calls"},
    ],
}


M_6_7 = {
    "id": "6.7",
    "title": "pyserial for DUT UART Consoles",
    "hours": 2,
    "summary": "Talk to a device's serial console: open the port, capture the boot log, interrupt the bootloader, run commands, strip echoes and prompts, and wait for patterns with deadlines.",
    "concepts": [
        {
            "title": "Open, boot, wait for the prompt, run a command",
            "files": CONSOLE_FILES,
            "local_only": SERIAL,
            "concept": "`serial.Serial(port, baudrate, timeout=...)` opens a UART (`/dev/ttyUSB0`, `COM3`). The port works in **bytes**: `write(b\"cmd\\r\")`, `read_until(b\"# \")` reads until the expected terminator or the timeout. A console echoes what you type, so a command's output starts with the command itself and ends with the next prompt; strip both. Here a simulated DUT on a pseudo-terminal stands in for real hardware, and `power_on()` plays the role of the PDU outlet.",
            "why": "The serial console is the one interface that works when the network doesn't: during boot, after a bad firmware flash, or when the Wi-Fi driver crashes. Capturing boot logs and recovering devices over UART is everyday lab automation.",
            "syntax": "with serial.Serial(\"/dev/ttyUSB0\", 115200, timeout=5) as ser:\n    ser.write(b\"uname -a\\r\")\n    out = ser.read_until(b\"# \").decode(errors=\"replace\")",
            "code": """import serial  ## pip install pyserial

from fake_console import power_on, start  ## Simulated DUT console (see supporting files)

PROMPT = b"root@ap-lab-07:~# "  ## Shell prompt as bytes
port = start()  ## Path like /dev/pts/3; on a real bench, /dev/ttyUSB0 or COM3


def run_cmd(ser, cmd):  ## Send one command and return just its output
    ser.reset_input_buffer()  ## Drop anything left over from earlier
    ser.write(cmd.encode() + b"\\r")  ## Strings must be encoded; consoles expect carriage return
    raw = ser.read_until(PROMPT).decode(errors="replace")  ## Everything up to the next prompt
    if not raw.endswith(PROMPT.decode()):  ## read_until returns early on timeout
        raise TimeoutError(f"no prompt after {cmd!r}: {raw[-60:]!r}")  ## Say what we did get
    lines = raw.replace("\\r\\n", "\\n").split("\\n")  ## Normalise line endings
    return "\\n".join(lines[1:-1])  ## Drop the echoed command and the prompt line


with serial.Serial(port, baudrate=115200, timeout=5) as ser:  ## 115200 8N1 is the common default
    power_on()  ## Start the boot after the port is open, so nothing is missed
    boot = ser.read_until(PROMPT).decode(errors="replace")  ## Capture the whole boot log
    print(f"boot log: {len(boot.splitlines())} lines, wifi fw line:", [ln for ln in boot.splitlines() if "ath12k" in ln])  ## Check for the driver
    print(run_cmd(ser, "uname -a"))  ## A simple command
    print(run_cmd(ser, "iw dev wlan0 info"))  ## Multi-line output
    print(repr(run_cmd(ser, "iwinfo")))  ## Command missing on this image""",
            "under": "`read_until` reads byte by byte into a buffer until it ends with the terminator or `timeout` seconds pass without completing, then returns whatever it has, so a short result means a timeout, not an error. Serial data can contain garbage at the wrong baud rate or during boot, hence `errors=\"replace\"`. pyserial clears the receive buffer when it opens the port, which is why boot output that arrives before `open` is lost on real hardware too.",
            "gotchas": [
                {
                    "title": "Writing str instead of bytes",
                    "local_only": needs("pyserial"),
                    "note": "Serial ports carry bytes. Passing a str raises TypeError. Encode explicitly (and add the line ending the device expects). `loop://` is pyserial's built-in loopback port: what you write comes back.",
                    "wrong": """import serial

ser = serial.serial_for_url("loop://", timeout=1)
ser.write("show version\\r")""",
                    "fixed": """import serial

ser = serial.serial_for_url("loop://", timeout=1)
ser.write("show version\\r".encode())
print(ser.read_until(b"\\r"))""",
                },
            ],
            "best": "Always set a timeout, treat a missing terminator as a failure with the partial output in the message, encode/decode at the edges, reset the input buffer before each command, log every byte to a per-test console log file, and release the port in `finally` (or `with`) so the next test can open it.",
        },
        {
            "title": "Interrupting the bootloader and logging the console",
            "files": CONSOLE_FILES,
            "local_only": SERIAL,
            "concept": "To recover or reflash a device you stop U-Boot's autoboot countdown by sending a key as soon as `Hit any key to stop autoboot` appears, then run bootloader commands at the `=> ` prompt. A small `expect(ser, pattern, timeout)` helper reads in chunks until a regex matches or a deadline passes, and appends everything to a console log, which becomes the most valuable artifact when a boot fails.",
            "why": "Factory reset, TFTP firmware recovery, reading the bootloader environment and boot-time benchmarks all start at the bootloader prompt, and the window to catch it is often 1–3 seconds.",
            "syntax": "m = expect(ser, rb\"autoboot\", timeout=30)\nser.write(b\"\\r\")\nexpect(ser, rb\"=> \", timeout=5)",
            "code": """import re  ## Pattern matching on console output
import time  ## Deadlines

import serial  ## pip install pyserial

from fake_console import power_on, start  ## Simulated DUT console


def expect(ser, pattern, timeout, log):  ## Read until a regex matches or the deadline passes
    deadline = time.monotonic() + timeout  ## Monotonic clock for deadlines
    buf = b""  ## Everything read during this call
    while time.monotonic() < deadline:  ## Keep reading until time is up
        chunk = ser.read(ser.in_waiting or 1)  ## Whatever has arrived (blocks up to ser.timeout for 1 byte)
        buf += chunk  ## Accumulate
        log.write(chunk)  ## Console log keeps every byte
        if m := re.search(pattern, buf):  ## Match anywhere in what we have so far
            return m, buf  ## Caller gets the match and the text
    raise TimeoutError(f"{pattern!r} not seen in {timeout}s; last bytes: {buf[-80:]!r}")  ## Useful failure message


with serial.Serial(start(), 115200, timeout=0.1) as ser, open("console.log", "wb") as log:  ## Short read timeout, our own deadlines
    power_on()  ## PDU on
    t0 = time.monotonic()  ## Boot timing starts
    expect(ser, rb"Hit any key to stop autoboot", timeout=10, log=log)  ## Wait for the countdown banner
    ser.write(b"\\r")  ## Any key stops autoboot
    expect(ser, rb"=> $", timeout=5, log=log)  ## U-Boot prompt at the very end of the output
    print("reached U-Boot within 2 s:", time.monotonic() - t0 < 2)  ## Boot-to-bootloader time check
    ser.write(b"printenv bootdelay\\r")  ## A bootloader command
    m, text = expect(ser, rb"bootdelay=(\\d+)", timeout=5, log=log)  ## Capture the value with a group
    print("bootdelay is", int(m.group(1)))  ## Parsed integer

print(open("console.log", "rb").read().decode().splitlines()[:3])  ## The log starts with the boot banner""",
            "under": "`ser.in_waiting` is the number of bytes already received; reading that many (or 1, blocking for up to the port timeout) keeps the loop responsive without busy-waiting. Searching the accumulated buffer, not just the last chunk, handles patterns split across reads. The `with` statement manages both the port and the log file, closing them even on errors.",
            "gotchas": [],
            "best": "Use short port timeouts plus explicit deadlines per step, regexes anchored to what's unique (`=> $`), one console log per test attached to the report, and never assume a fixed boot time: wait for the pattern. For many devices, pexpect's `fdpexpect` gives the same expect API over a serial file descriptor.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "local_only": needs("pyserial"),
            "prompt": "Use pyserial's `loop://` port to write a line and read it back with `readline()`.",
            "solution": "`readline()` reads up to and including `\\n`. Writes and reads are bytes.",
            "solution_code": """import serial

with serial.serial_for_url("loop://", timeout=1) as ser:
    ser.write(b"AT+VERSION?\\n")
    print(ser.readline())
    print(ser.in_waiting, "bytes left")""",
        },
        {
            "level": "Medium",
            "files": CONSOLE_FILES,
            "local_only": SERIAL,
            "prompt": "Boot the simulated DUT, wait for the shell prompt, then run `cat /etc/openwrt_release` and extract the release number with a regex.",
            "solution": "Reuse the read-until-prompt approach, then `re.search(r\"'([\\d.]+)'\", out)`.",
            "solution_code": """import re
import serial
from fake_console import power_on, start

PROMPT = b"# "
with serial.Serial(start(), 115200, timeout=5) as ser:
    power_on()
    ser.read_until(PROMPT)
    ser.write(b"cat /etc/openwrt_release\\r")
    out = ser.read_until(PROMPT).decode()
    print(re.search(r"'([\\d.]+)'", out).group(1))""",
        },
        {
            "level": "Hard",
            "files": CONSOLE_FILES,
            "local_only": SERIAL,
            "prompt": "Scan the boot log for problems: return the first line matching any of `panic`, `Oops`, `firmware crashed`, or `error`, or report a clean boot. Also report how many kernel log lines (`[ ... ]`) appeared.",
            "solution": "Read until the prompt, split lines, search with one combined case-insensitive regex.",
            "solution_code": """import re
import serial
from fake_console import power_on, start

BAD = re.compile(r"panic|Oops|firmware crashed|error", re.IGNORECASE)
with serial.Serial(start(), 115200, timeout=5) as ser:
    power_on()
    lines = ser.read_until(b"# ").decode(errors="replace").splitlines()
kernel = [ln for ln in lines if ln.startswith("[")]
problem = next((ln for ln in lines if BAD.search(ln)), None)
print("kernel lines:", len(kernel))
print(f"problem: {problem}" if problem else "clean boot")""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What settings do you need to open a serial console?", "a": "Port name, baud rate (often 115200), data bits/parity/stop bits (usually 8N1), flow control (usually none) and a timeout. Wrong baud rate shows as garbage characters.", "follow": "How do you find the port? (ls /dev/ttyUSB*, dmesg, or serial.tools.list_ports.)"},
        {"level": "Intermediate", "q": "How do you reliably catch the U-Boot prompt?", "a": "Open the port before powering the device (via a PDU), read in small chunks and search for the 'Hit any key' banner, send a key immediately, then wait for the bootloader prompt with a deadline. Log everything.", "follow": "What if you miss the window? (Power-cycle and retry, or set bootdelay higher via fw_setenv.)"},
        {"level": "Intermediate", "q": "Why does command output include the command itself?", "a": "The device echoes received characters back. Strip the first line (the echo) and the trailing prompt; or disable echo (stty -echo) on Linux consoles.", "follow": "Why might lines end with \\r\\n? (Terminal line discipline converts \\n to \\r\\n.)"},
    ],
    "quiz": [
        {"q": "`ser.write('ls')` raises...", "options": ["Nothing", "TypeError", "SerialException", "UnicodeError"], "answer": 1, "why": "Needs bytes."},
        {"q": "`read_until(b'# ')` returns early when...", "options": ["Never", "The timeout expires", "A newline arrives", "The buffer is full"], "answer": 1, "why": "Returns what it has on timeout."},
        {"q": "pyserial loopback URL:", "options": ["serial://", "loop://", "tty://loop", "mem://"], "answer": 1, "why": "serial_for_url('loop://')."},
        {"q": "Typical console baud rate:", "options": ["9600", "57600", "115200", "1000000"], "answer": 2, "why": "Most embedded Linux boards."},
        {"q": "Boot output sent before the port was opened is...", "options": ["Buffered forever", "Lost", "Replayed", "Logged by the kernel"], "answer": 1, "why": "Open the port first, then power on."},
    ],
    "cards": [
        {"front": "Open a serial port", "back": "`serial.Serial('/dev/ttyUSB0', 115200, timeout=5)`"},
        {"front": "Send a command", "back": "`ser.write(cmd.encode() + b'\\r')`"},
        {"front": "Read to a prompt", "back": "`ser.read_until(b'# ')` (check it really ends with the prompt)"},
        {"front": "List ports", "back": "`python -m serial.tools.list_ports`"},
        {"front": "Catch U-Boot", "back": "Open port → power on → wait 'Hit any key' → send '\\r' → wait '=> '"},
    ],
}


M_6_8 = {
    "id": "6.8",
    "title": "pexpect for Interactive CLIs",
    "hours": 2,
    "summary": "Automate programs that expect a human at a terminal: logins, prompts, confirmations, mode changes, timeouts and alternative outcomes, with pexpect.",
    "concepts": [
        {
            "title": "spawn, expect, sendline, before",
            "files": CLI_FILES,
            "local_only": PEXPECT,
            "concept": "`pexpect.spawn(cmd, args)` runs a program in a pseudo-terminal, so it behaves exactly as if a person were typing. `expect(pattern)` waits until the output matches a regex, `sendline(text)` types a line, and after a match `child.before` holds everything between the previous match and this one: the command's output. `expect_exact` matches a literal string. Use `encoding=\"utf-8\"` to work with str.",
            "why": "Some device CLIs, vendor tools and installers only work interactively: they ask for passwords, show `[y/N]` confirmations and switch prompts between modes. pexpect scripts them reliably, and the same patterns apply to SSH sessions via `pexpect.pxssh`.",
            "syntax": "child = pexpect.spawn(\"ssh\", [\"admin@ap\"], encoding=\"utf-8\", timeout=10)\nchild.expect(\"Password: \")\nchild.sendline(password)\nchild.expect(r\"ap-1> \")\noutput = child.before",
            "code": """import sys  ## To run the simulated CLI with this Python

import pexpect  ## pip install pexpect (Linux/macOS)

child = pexpect.spawn(sys.executable, ["fake_cli.py"], encoding="utf-8", timeout=5)  ## Start the program in a pseudo-terminal
child.expect("Username: ")  ## Wait for the login prompt
child.sendline("admin")  ## Type and press Enter
child.expect("Password: ")  ## Password prompt (input isn't echoed)
child.sendline("lab123")  ## Credentials would come from a vault or env var
child.expect("ap-1> ")  ## Logged in when the CLI prompt appears
print(child.before.strip())  ## Text printed between the password and the prompt: the banner

child.sendline("show radio 5g")  ## Run a command
child.expect("ap-1> ")  ## Wait for the prompt to return
out = child.before.splitlines()  ## The echo of our command, then its output
print(out[0], "=>", out[1])  ## First line is the echo, second the result

child.sendline("enable")  ## Switch to privileged mode
child.expect_exact("[admin@ap-1]# ")  ## The prompt changes; brackets are literal here
child.sendline("reload")  ## Dangerous command that asks for confirmation
child.expect_exact("[y/N] ")  ## Wait for the question
child.sendline("y")  ## Confirm
child.expect(pexpect.EOF)  ## The program exits
print(child.before.strip().splitlines()[-1])  ## Last thing it printed
child.close()  ## Reap the process and collect its exit status
print("exit status:", child.exitstatus)  ## 0 for a clean exit""",
            "under": "A pseudo-terminal (pty) makes the child think it's attached to a terminal, so it prompts, echoes input and line-buffers output as it would for a person. pexpect reads the pty's output into a buffer and runs your regex against it; on a match, `before`, `after` and `match` are set and the buffer is trimmed. Terminals send `\\r\\n` line endings, which is why output is best split with `splitlines()`.",
            "gotchas": [
                {
                    "title": "Regex special characters in a prompt",
                    "files": CLI_FILES,
                    "local_only": PEXPECT,
                    "note": "`expect()` takes a regular expression, and `[admin@ap-1]` is a character class (with an invalid range `p-1`). Use `expect_exact()` for literal prompts or `re.escape()` the text.",
                    "wrong": """import sys
import pexpect

child = pexpect.spawn(sys.executable, ["fake_cli.py"], encoding="utf-8", timeout=5)
for prompt, answer in [("Username: ", "admin"), ("Password: ", "lab123"), ("ap-1> ", "enable")]:
    child.expect(prompt)
    child.sendline(answer)
try:
    child.expect("[admin@ap-1]# ")
except Exception as e:
    print(type(e).__name__, e)""",
                    "fixed": """import sys
import pexpect

child = pexpect.spawn(sys.executable, ["fake_cli.py"], encoding="utf-8", timeout=5)
for prompt, answer in [("Username: ", "admin"), ("Password: ", "lab123"), ("ap-1> ", "enable")]:
    child.expect(prompt)
    child.sendline(answer)
child.expect_exact("[admin@ap-1]# ")
print("privileged prompt reached")""",
                },
            ],
            "best": "Match prompts as specifically as possible (anchor on the hostname), use `expect_exact` for literals, set a timeout on every spawn, and always `close()` the child so it doesn't linger. For SSH to network devices prefer Netmiko or Paramiko (Phase 7); use pexpect for local interactive tools and odd CLIs.",
        },
        {
            "title": "Alternatives, timeouts and session logs",
            "files": CLI_FILES,
            "local_only": PEXPECT,
            "concept": "`expect([p0, p1, pexpect.TIMEOUT, pexpect.EOF])` waits for whichever comes first and returns its **index**, so one call handles success, a wrong password, a hang and an unexpected exit. Without TIMEOUT/EOF in the list, they raise exceptions. Setting `child.logfile_read` to a file records everything the program printed, for the test report.",
            "why": "Real sessions branch: the device may ask to change the default password, reject credentials, or hang during a firmware upgrade. Handling every branch explicitly is what separates a robust script from one that fails mysteriously at 3 a.m.",
            "syntax": "i = child.expect([\"ap-1> \", \"Login incorrect\", pexpect.TIMEOUT, pexpect.EOF])\nif i == 0: ... elif i == 1: ...",
            "code": """import io  ## In-memory log for the example (a real one would be a file)
import sys  ## Python path for the simulated CLI

import pexpect  ## pip install pexpect


def login(password, log):  ## Returns a logged-in child or raises with a clear reason
    child = pexpect.spawn(sys.executable, ["fake_cli.py"], encoding="utf-8", timeout=3)  ## Start the CLI
    child.logfile_read = log  ## Everything the CLI prints goes to the log
    child.expect("Username: ")  ## First prompt
    child.sendline("admin")  ## User
    child.expect("Password: ")  ## Second prompt
    child.sendline(password)  ## Password under test
    i = child.expect(["ap-1> ", "Login incorrect", pexpect.TIMEOUT, pexpect.EOF])  ## Four possible outcomes
    if i == 0:  ## Prompt appeared
        return child  ## Success
    reason = ["", "bad credentials", "timed out waiting for prompt", "CLI exited unexpectedly"][i]  ## Map index to a message
    child.close(force=True)  ## Clean up the process
    raise RuntimeError(f"login failed: {reason}")  ## One clear error for the caller


log = io.StringIO()  ## Collects the session transcript
try:  ## Wrong password first
    login("letmein", log)  ## Will be rejected
except RuntimeError as e:  ## The branch we mapped
    print(e)  ## login failed: bad credentials

child = login("lab123", log)  ## Correct password
child.sendline("show versoin")  ## Typo on purpose
child.expect("ap-1> ")  ## Prompt comes back either way
print(child.before.splitlines()[-1])  ## The CLI's error message
child.sendline("exit")  ## Leave cleanly
child.expect(pexpect.EOF)  ## Wait for the process to end
print("log lines:", len(log.getvalue().splitlines()), "| has banner:", "AP-OS 7.4.1" in log.getvalue())  ## The transcript for the report""",
            "under": "With a list, pexpect compiles all patterns and returns the index of the one that matches earliest in the output stream. `pexpect.TIMEOUT` in the list turns the timeout from an exception into a branch; same for `EOF`. `logfile_read` receives only what the child writes (`logfile_send` gets what you send, `logfile` both), which keeps passwords out of the log because they're never echoed.",
            "gotchas": [],
            "best": "List every expected outcome (including TIMEOUT and EOF) at decision points, convert indexes into named reasons, keep a transcript per session, never log what you send when it includes secrets, and close children with `force=True` in error paths.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "local_only": PEXPECT,
            "prompt": "Use `pexpect.run` to run `python -c \"print('wlan0 up')\"` and capture its output and exit status in one call.",
            "solution": "`pexpect.run(cmd, withexitstatus=True)` returns the output (bytes unless encoding is set) and the status.",
            "solution_code": """import sys
import pexpect

cmd = f'{sys.executable} -c "print(\\'wlan0 up\\')"'
output, status = pexpect.run(cmd, withexitstatus=True, encoding="utf-8")
print(repr(output), status)""",
        },
        {
            "level": "Medium",
            "files": CLI_FILES,
            "local_only": PEXPECT,
            "prompt": "Log in and run a list of show commands, returning a dict of command → output (without the echoed command).",
            "solution": "Loop over commands: sendline, expect the prompt, drop the first line of `before`.",
            "solution_code": """import sys
import pexpect

child = pexpect.spawn(sys.executable, ["fake_cli.py"], encoding="utf-8", timeout=5)
for prompt, answer in [("Username: ", "admin"), ("Password: ", "lab123")]:
    child.expect(prompt)
    child.sendline(answer)
child.expect("ap-1> ")
results = {}
for cmd in ["show version", "show radio 5g"]:
    child.sendline(cmd)
    child.expect("ap-1> ")
    results[cmd] = "\\n".join(child.before.splitlines()[1:])
child.sendline("exit")
child.expect(pexpect.EOF)
for cmd, out in results.items():
    print(f"{cmd!r}: {out}")""",
        },
        {
            "level": "Hard",
            "files": CLI_FILES,
            "local_only": PEXPECT,
            "prompt": "Answer `reload`'s confirmation with **N** and verify the CLI stays at the privileged prompt; then show what happens with a 1-second timeout when you wait for text that never comes.",
            "solution": "Expect the confirmation, send N, expect the prompt again. For the timeout, put pexpect.TIMEOUT in the list and check the index.",
            "solution_code": """import sys
import pexpect

child = pexpect.spawn(sys.executable, ["fake_cli.py"], encoding="utf-8", timeout=5)
for prompt, answer in [("Username: ", "admin"), ("Password: ", "lab123"), ("ap-1> ", "enable")]:
    child.expect(prompt)
    child.sendline(answer)
child.expect_exact("[admin@ap-1]# ")
child.sendline("reload")
child.expect_exact("[y/N] ")
child.sendline("N")
child.expect_exact("[admin@ap-1]# ")
print("still running:", child.isalive())
child.sendline("show version")
i = child.expect_exact(["Upgrade complete", pexpect.TIMEOUT], timeout=1)
print("index:", i, "(1 means TIMEOUT)")
child.close(force=True)""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "What does pexpect do that subprocess can't?", "a": "It runs the program in a pseudo-terminal and lets you wait for output patterns and respond, so programs that prompt interactively (passwords via the tty, confirmations, curses-like CLIs) can be automated. subprocess pipes aren't terminals, so many programs behave differently or refuse to prompt.", "follow": "What about Windows? (wexpect, or pexpect.popen_spawn without a pty.)"},
        {"level": "Intermediate", "q": "How do you handle multiple possible responses?", "a": "Pass a list to expect, including pexpect.TIMEOUT and pexpect.EOF, and branch on the returned index.", "follow": "What do before and after contain? (Text before the match, and the matched text.)"},
        {"level": "Advanced", "q": "Why are prompt regexes a common source of bugs?", "a": "Prompts contain regex metacharacters ($, #, [, ], .), can appear inside command output, and change with modes. Use expect_exact or re.escape, anchor to the hostname, and update the expected prompt after mode changes.", "follow": "How do you deal with paging (--More--)? (Disable paging, e.g. 'terminal length 0', or expect --More-- and send a space.)"},
    ],
    "quiz": [
        {"q": "`child.before` after a match holds...", "options": ["The matched text", "Output before the match", "Everything ever printed", "Your last input"], "answer": 1, "why": "Text up to the match."},
        {"q": "Match a literal prompt `[admin@ap]#`:", "options": ["expect()", "expect_exact()", "sendline()", "read()"], "answer": 1, "why": "No regex interpretation."},
        {"q": "`expect([a, b, pexpect.TIMEOUT])` on timeout returns...", "options": ["Raises", "0", "2", "None"], "answer": 2, "why": "Index of TIMEOUT."},
        {"q": "Record what the child prints:", "options": ["child.logfile_send", "child.logfile_read", "child.stdout", "print(child)"], "answer": 1, "why": "logfile_read."},
        {"q": "pexpect runs children in a...", "options": ["Pipe", "Pseudo-terminal", "Thread", "Container"], "answer": 1, "why": "pty."},
    ],
    "cards": [
        {"front": "Start interactive program", "back": "`pexpect.spawn(cmd, args, encoding='utf-8', timeout=10)`"},
        {"front": "Wait and respond", "back": "`child.expect('Password: '); child.sendline(pw)`"},
        {"front": "Branch on outcome", "back": "`i = child.expect([ok, 'incorrect', pexpect.TIMEOUT, pexpect.EOF])`"},
        {"front": "Literal prompt", "back": "`child.expect_exact('[admin@ap-1]# ')`"},
        {"front": "Session transcript", "back": "`child.logfile_read = open('session.log', 'w')`"},
    ],
}


M_6_9 = {
    "id": "6.9",
    "title": "File Watchers",
    "hours": 1,
    "summary": "React to new files (captures, logs, results) by polling directory snapshots or with watchdog's event-based observer, and avoid processing half-written files.",
    "concepts": [
        {
            "title": "Polling with directory snapshots",
            "concept": "The simplest watcher takes a snapshot of a directory (name → modification time and size) and compares it with the previous one: new names are created files, missing names are deleted, changed stats are modified. Call it every few seconds. It needs only the standard library and works on network shares where OS events don't.",
            "why": "A sniffer drops `.pcap` files into a folder, a tool writes results files, a colleague uploads firmware: something should pick each one up and process it automatically.",
            "syntax": "snap = {e.name: (e.stat().st_mtime_ns, e.stat().st_size) for e in os.scandir(d)}\nnew = snap.keys() - old.keys()",
            "code": """import os  ## scandir for fast directory listing
import tempfile  ## A scratch directory for the example
from pathlib import Path  ## Path helpers


def snapshot(folder, suffix=".pcap"):  ## name -> (mtime, size) for matching files
    return {e.name: (e.stat().st_mtime_ns, e.stat().st_size) for e in os.scandir(folder) if e.is_file() and e.name.endswith(suffix)}  ## One stat per entry


def diff(old, new):  ## Compare two snapshots
    created = sorted(new.keys() - old.keys())  ## In new only
    deleted = sorted(old.keys() - new.keys())  ## In old only
    modified = sorted(n for n in new.keys() & old.keys() if new[n] != old[n])  ## In both, but changed
    return created, modified, deleted  ## Three lists


with tempfile.TemporaryDirectory() as d:  ## Stand-in for the capture folder
    folder = Path(d)  ## Path object for convenience
    before = snapshot(folder)  ## Empty at first
    (folder / "assoc.pcap").write_bytes(b"\\xd4\\xc3\\xb2\\xa1" + b"\\0" * 20)  ## A capture arrives
    (folder / "roam.pcap").write_bytes(b"\\xd4\\xc3\\xb2\\xa1")  ## Another one
    (folder / "notes.txt").write_text("ignored")  ## Not a pcap, filtered out
    after = snapshot(folder)  ## Second poll
    print(diff(before, after))  ## Two created files
    (folder / "roam.pcap").write_bytes(b"\\xd4\\xc3\\xb2\\xa1" + b"\\0" * 100)  ## Capture grows
    (folder / "assoc.pcap").unlink()  ## Capture removed
    print(diff(after, snapshot(folder)))  ## One modified, one deleted""",
            "under": "`os.scandir` returns directory entries with cached type information, and `entry.stat()` is one system call per file. Comparing (mtime in nanoseconds, size) catches almost all changes; a file rewritten within the same timestamp tick with the same size would be missed, which is why some tools add a content hash. Set operations on dict keys (`-`, `&`) make the diff one line each.",
            "gotchas": [
                {
                    "title": "Processing a file that's still being written",
                    "note": "A watcher sees the file as soon as it's created, often before the writer has finished. Have writers write to a temporary name and `os.replace` it into place (atomic on the same filesystem), and have the watcher ignore temporary names.",
                    "wrong": """import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as d:
    path = Path(d) / "results.json"
    f = open(path, "w")
    f.write('{"suite": "rvr", "passed": 4')
    f.flush()
    print("watcher reads:", path.read_text())
    f.write(', "failed": 1}')
    f.close()""",
                    "fixed": """import os
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as d:
    final, tmp = Path(d) / "results.json", Path(d) / "results.json.tmp"
    with open(tmp, "w") as f:
        f.write('{"suite": "rvr", "passed": 4')
        f.write(', "failed": 1}')
    os.replace(tmp, final)
    visible = [p.name for p in Path(d).iterdir() if not p.name.endswith(".tmp")]
    print("watcher sees:", visible, "->", final.read_text())""",
                },
            ],
            "best": "Write-then-rename on the producer side, ignore temp suffixes on the consumer side, process each file once (track handled names or move processed files to `done/`), and make processing idempotent so a restart that sees the same file twice is harmless.",
        },
        {
            "title": "Event-driven watching with watchdog",
            "local_only": WATCHDOG,
            "concept": "`watchdog` uses the OS's change notifications (inotify on Linux, FSEvents on macOS, ReadDirectoryChangesW on Windows). Subclass `FileSystemEventHandler` (or `PatternMatchingEventHandler`) and implement `on_created`, `on_modified`, `on_moved`, `on_deleted`; schedule it on a path with an `Observer`, which runs in a background thread.",
            "why": "Events arrive within milliseconds without polling, which matters for live log tailing or kicking off analysis the moment a capture lands, and scales to large directory trees.",
            "syntax": "class H(FileSystemEventHandler):\n    def on_created(self, event): ...\nobs = Observer(); obs.schedule(H(), path, recursive=True); obs.start()\n...\nobs.stop(); obs.join()",
            "code": """import os  ## For the atomic rename
import queue  ## Hand events from the observer thread to the main thread
import tempfile  ## Scratch directory
from pathlib import Path  ## Paths

from watchdog.events import FileSystemEventHandler  ## pip install watchdog
from watchdog.observers import Observer  ## Background thread using OS notifications

events = queue.Queue()  ## Thread-safe channel


class PcapHandler(FileSystemEventHandler):  ## React only to finished .pcap files
    def on_created(self, event):  ## A new file appeared
        if not event.is_directory and event.src_path.endswith(".pcap"):  ## Written directly under its final name
            events.put(("created", Path(event.src_path).name))  ## Don't do heavy work in the observer thread

    def on_moved(self, event):  ## Renames: how write-then-rename files arrive
        if event.dest_path.endswith(".pcap"):  ## Final name is a pcap
            events.put(("ready", Path(event.dest_path).name))  ## Safe to process now


with tempfile.TemporaryDirectory() as d:  ## Watched folder
    observer = Observer()  ## Picks the best backend for this OS
    observer.schedule(PcapHandler(), d, recursive=False)  ## Watch one folder
    observer.start()  ## Starts the background thread
    try:  ## Always stop the observer
        Path(d, "roam.pcap.part").write_bytes(b"\\xd4\\xc3\\xb2\\xa1")  ## Producer writes a temp name
        os.replace(Path(d, "roam.pcap.part"), Path(d, "roam.pcap"))  ## Then renames atomically
        Path(d, "notes.txt").write_text("ignored")  ## Filtered out by the handler
        got = events.get(timeout=5)  ## Wait for the first relevant event
        print(got)  ## ('ready', 'roam.pcap')
    finally:  ## Even if the wait times out
        observer.stop()  ## Ask the thread to finish
        observer.join()  ## Wait for it""",
            "under": "On Linux, watchdog's inotify backend receives a stream of kernel events; a rename within the watched folder arrives as one moved event with both paths. Handlers run on the observer's thread, so they should only enqueue work; the main thread (or a worker pool) does the processing. Editors and tools often produce several events per save (create, modify, modify), which is another reason to react to renames or debounce.",
            "gotchas": [],
            "best": "Use watchdog for local disks and responsiveness, polling for network shares and simplicity. Keep handlers tiny (enqueue), debounce bursts of modified events, and always stop and join the observer.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write `new_files(folder, seen)` that returns sorted names of `.json` files not in the `seen` set, and adds them to it. Call it twice with a file added in between.",
            "solution": "Compare the current listing with the set, update the set, return the difference.",
            "solution_code": """import tempfile
from pathlib import Path


def new_files(folder, seen):
    current = {p.name for p in Path(folder).glob("*.json")}
    fresh = sorted(current - seen)
    seen.update(fresh)
    return fresh


with tempfile.TemporaryDirectory() as d:
    seen = set()
    Path(d, "run1.json").write_text("{}")
    print(new_files(d, seen))
    Path(d, "run2.json").write_text("{}")
    print(new_files(d, seen))
    print(new_files(d, seen))""",
        },
        {
            "level": "Medium",
            "prompt": "Write a processor that moves each handled file into a `done/` subfolder, so a restarted watcher never handles it twice. Show that a second pass finds nothing.",
            "solution": "Process, then `Path.rename` into done/ (same filesystem, so it's atomic).",
            "solution_code": """import json
import tempfile
from pathlib import Path


def process_inbox(inbox):
    done = Path(inbox, "done")
    done.mkdir(exist_ok=True)
    handled = []
    for path in sorted(Path(inbox).glob("*.json")):
        data = json.loads(path.read_text())
        handled.append(f"{path.name}: {data['failed']} failed")
        path.rename(done / path.name)
    return handled


with tempfile.TemporaryDirectory() as d:
    Path(d, "a.json").write_text('{"failed": 0}')
    Path(d, "b.json").write_text('{"failed": 2}')
    print(process_inbox(d))
    print(process_inbox(d))
    print(sorted(p.name for p in Path(d, "done").iterdir()))""",
        },
        {
            "level": "Hard",
            "prompt": "Debounce: given a stream of (time, filename) modification events, emit each file only once it has been quiet for 2 seconds. Implement it as a pure function over a list of events plus a final 'now'.",
            "solution": "Track the last event time per file; a file is ready when now minus its last event is at least the quiet period. Pure functions like this are easy to test without real files or threads.",
            "solution_code": """def ready_files(events, now, quiet=2.0):
    last = {}
    for t, name in events:
        last[name] = max(t, last.get(name, t))
    return sorted(name for name, t in last.items() if now - t >= quiet)


stream = [(0.0, "a.log"), (0.5, "a.log"), (1.0, "b.log"), (2.9, "a.log"), (3.0, "c.log")]
print(ready_files(stream, now=3.5))
print(ready_files(stream, now=5.0))""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "Polling vs OS notifications for watching files?", "a": "Polling: simple, portable, works on NFS/SMB shares, but has latency and costs a directory scan per interval. Notifications (inotify/FSEvents via watchdog): immediate and efficient, but can miss events on network filesystems, have watch limits, and deliver bursts of events.", "follow": "What's the inotify watch limit? (fs.inotify.max_user_watches.)"},
        {"level": "Intermediate", "q": "How do you avoid reading half-written files?", "a": "Producers write to a temp name and atomically rename (os.replace) on the same filesystem; consumers ignore temp names or react to rename events. Alternatives: a sentinel .done file, or waiting until size is stable.", "follow": "Is rename atomic across filesystems? (No; it becomes copy + delete.)"},
        {"level": "Advanced", "q": "Design a service that processes every capture dropped into a share exactly once.", "a": "Poll or watch for completed files, claim each by atomically moving it into a processing/ folder, process idempotently, move to done/ or failed/ with an error file, and on restart re-scan processing/ for crashed work. Record checksums to detect duplicates.", "follow": "How would you scale to multiple workers? (The atomic move is the lock; only one worker's rename succeeds.)"},
    ],
    "quiz": [
        {"q": "Atomic way to publish a finished file:", "options": ["shutil.copy", "os.replace(tmp, final)", "open(final, 'a')", "Path.touch"], "answer": 1, "why": "Rename on the same filesystem."},
        {"q": "watchdog handlers run on...", "options": ["The main thread", "The observer's thread", "A new process", "The kernel"], "answer": 1, "why": "Keep them light; enqueue work."},
        {"q": "Linux backend used by watchdog:", "options": ["FSEvents", "inotify", "kqueue", "ReadDirectoryChangesW"], "answer": 1, "why": "inotify."},
        {"q": "Best for SMB/NFS shares:", "options": ["inotify", "Polling", "Signals", "select()"], "answer": 1, "why": "Notifications are unreliable there."},
        {"q": "`new.keys() - old.keys()` gives...", "options": ["Deleted files", "Created files", "Modified files", "Error"], "answer": 1, "why": "Names only in the new snapshot."},
    ],
    "cards": [
        {"front": "Directory snapshot", "back": "`{e.name: (e.stat().st_mtime_ns, e.stat().st_size) for e in os.scandir(d)}`"},
        {"front": "Safe file hand-off", "back": "Write `x.tmp`, then `os.replace('x.tmp', 'x')`"},
        {"front": "watchdog setup", "back": "Handler subclass + `Observer().schedule(h, path)`, `start()`, `stop()`, `join()`"},
        {"front": "Process once", "back": "Move handled files to `done/` (rename = claim)"},
        {"front": "Debounce", "back": "Emit when quiet for N seconds since the last event"},
    ],
}


REPORT_DATA = """RUN = {
    "suite": "nightly-rvr", "dut": "ap-lab-07", "firmware": "7.4.1", "date": "2026-10-11",
    "results": [
        {"test": "rvr_5g_80", "band": "5G", "mbps": 912.4, "kpi": 850, "ssid": "lab-5g"},
        {"test": "rvr_6g_160", "band": "6G", "mbps": 1890.0, "kpi": 2000, "ssid": "lab-6g"},
        {"test": "rvr_2g_20", "band": "2G", "mbps": 141.7, "kpi": 120, "ssid": "<b>guest</b>"},
    ],
}
"""

M_6_10 = {
    "id": "6.10",
    "title": "HTML/PDF Reports with Jinja2",
    "hours": 2,
    "summary": "Generate HTML reports from data with Jinja2 templates (loops, conditionals, filters, macros, inheritance, autoescaping), then turn the HTML into a PDF.",
    "concepts": [
        {
            "title": "Templates, loops, filters and autoescaping",
            "files": {"report_data.py": REPORT_DATA},
            "local_only": JINJA,
            "concept": "Jinja2 renders text from a template and data. `{{ expr }}` outputs a value, `{% for %}` / `{% if %}` control flow, filters transform values (`{{ x|round(1) }}`, `{{ items|length }}`), and you can register your own filters. Create an `Environment` with `autoescape=True` for HTML so that values like SSIDs containing `<` are escaped, not injected into the page.",
            "why": "A self-contained HTML report (summary, pass/fail table, KPI colours, links) attached to every run is far more useful than a console log, and templates keep the presentation out of the test code.",
            "syntax": "env = Environment(loader=..., autoescape=True)\nenv.filters[\"mbps\"] = lambda v: f\"{v:,.1f} Mbps\"\nhtml = env.get_template(\"report.html\").render(run=run)",
            "code": """from jinja2 import DictLoader, Environment  ## pip install jinja2

from report_data import RUN  ## Results to render (see supporting files)

TEMPLATE = \"\"\"<h1>{{ run.suite }} on {{ run.dut }} (fw {{ run.firmware }})</h1>
<p>{{ failed|length }} of {{ run.results|length }} failed</p>
<table>
{% for r in run.results %}
  <tr class="{{ 'fail' if r.mbps < r.kpi else 'pass' }}">
    <td>{{ r.test }}</td><td>{{ r.ssid }}</td><td>{{ r.mbps|mbps }}</td><td>{{ r.kpi|mbps }}</td>
  </tr>
{% endfor %}
</table>
{% if failed %}<p>Investigate: {{ failed|map(attribute='test')|join(', ') }}</p>{% endif %}\"\"\"  ## The page layout, separate from the data

env = Environment(loader=DictLoader({"report.html": TEMPLATE}), autoescape=True, trim_blocks=True, lstrip_blocks=True)  ## autoescape for HTML; trim_* tidy whitespace
env.filters["mbps"] = lambda v: f"{v:,.1f} Mbps"  ## Custom filter used as {{ x|mbps }}

failed = [r for r in RUN["results"] if r["mbps"] < r["kpi"]]  ## Computed in Python, passed in
html = env.get_template("report.html").render(run=RUN, failed=failed)  ## Data in, text out
print(html)  ## Look at the result: the SSID's <b> is escaped""",
            "under": "Jinja compiles each template to Python code once and caches it, so rendering many reports is fast. Attribute access `r.test` works on dicts too (it tries the attribute, then the key). With autoescaping on, every `{{ }}` output is HTML-escaped unless marked safe (`|safe` or `Markup`), which protects reports from SSIDs, hostnames or log lines that contain markup.",
            "gotchas": [
                {
                    "title": "Rendering HTML without autoescape",
                    "local_only": JINJA,
                    "note": "`Template(...)` and a plain `Environment()` don't escape by default. An SSID, hostname or log line containing markup (or a script) is injected into the report and runs when someone opens it. Turn autoescaping on for HTML.",
                    "wrong": """from jinja2 import Template

ssid = '<script>alert("pwned")</script>'
print(Template("<td>{{ ssid }}</td>").render(ssid=ssid))""",
                    "fixed": """from jinja2 import Environment

env = Environment(autoescape=True)
ssid = '<script>alert("pwned")</script>'
print(env.from_string("<td>{{ ssid }}</td>").render(ssid=ssid))""",
                },
            ],
            "best": "Compute data (pass/fail, aggregates) in Python and keep templates for presentation, enable autoescape (`select_autoescape([\"html\", \"xml\"])` with a FileSystemLoader), use `StrictUndefined` so a typo in a variable name fails loudly, and keep templates in files next to the code.",
        },
        {
            "title": "Template inheritance, then HTML to PDF",
            "files": {"report_data.py": REPORT_DATA},
            "local_only": JINJA_PW,
            "capture": "report.png",
            "image_alt": "Rendered HTML test report with a header, a summary line and a table with one failing row highlighted in red",
            "concept": "A base template defines the page skeleton with `{% block %}` placeholders; child templates `{% extends \"base.html\" %}` and fill the blocks, so every report shares one header, footer and stylesheet. Macros (`{% macro %}`) are reusable template functions, like a status badge. To get a PDF, open the HTML in headless Chromium with Playwright and call `page.pdf()`.",
            "why": "Several report types (RvR, roaming, soak) should look like one product. And some audiences (customers, compliance, release sign-off) want a PDF they can file.",
            "syntax": "{# base.html #} <html>...{% block content %}{% endblock %}</html>\n{# rvr.html #} {% extends \"base.html\" %}{% block content %}...{% endblock %}\n\npage.set_content(html); page.pdf(path=\"report.pdf\", format=\"A4\")",
            "code": """from pathlib import Path  ## To check the files written

from jinja2 import DictLoader, Environment, StrictUndefined  ## Template engine
from playwright.sync_api import sync_playwright  ## Headless Chromium for PDF and PNG

from report_data import RUN  ## Same results data

TEMPLATES = {  ## Normally files in a templates/ folder
    "base.html": \"\"\"<html><head><style>
body{font-family:sans-serif;margin:24px} table{border-collapse:collapse} td,th{border:1px solid #ccc;padding:4px 10px}
.fail{background:#fde2e1} .badge{padding:1px 8px;border-radius:8px;color:#fff;font-size:12px}
</style></head><body><header><b>Wi-Fi Test Lab</b> | {{ run.date }}</header>
{% block content %}{% endblock %}<footer><small>Generated by wifi-ci</small></footer></body></html>\"\"\",  ## Shared skeleton with a block
    "rvr.html": \"\"\"{% extends "base.html" %}
{% macro badge(ok) %}<span class="badge" style="background:{{ '#15803d' if ok else '#b91c1c' }}">{{ 'PASS' if ok else 'FAIL' }}</span>{% endmacro %}
{% block content %}<h2>Rate vs range: {{ run.dut }} fw {{ run.firmware }}</h2>
<table><tr><th>Test</th><th>SSID</th><th>Mbps</th><th>KPI</th><th></th></tr>
{% for r in run.results %}<tr class="{{ '' if r.mbps >= r.kpi else 'fail' }}"><td>{{ r.test }}</td><td>{{ r.ssid }}</td>
<td>{{ r.mbps }}</td><td>{{ r.kpi }}</td><td>{{ badge(r.mbps >= r.kpi) }}</td></tr>{% endfor %}</table>{% endblock %}\"\"\",  ## Child fills the block and uses a macro
}  ## End of the template dict

env = Environment(loader=DictLoader(TEMPLATES), autoescape=True, undefined=StrictUndefined)  ## Typos in variable names raise errors
html = env.get_template("rvr.html").render(run=RUN)  ## Child + base rendered together
Path("report.html").write_text(html)  ## The HTML report artifact

with sync_playwright() as p:  ## Headless browser to print the page
    page = p.chromium.launch().new_page(viewport={"width": 720, "height": 300})  ## Size for the preview image
    page.set_content(html)  ## Load the rendered HTML
    page.pdf(path="report.pdf", format="A4", print_background=True)  ## Print to PDF, keeping row colours
    page.screenshot(path="report.png")  ## PNG preview (shown below)

pdf = Path("report.pdf").read_bytes()  ## Inspect the PDF
print("PDF header:", pdf[:5], "| pages:", pdf.count(b"/Type /Page") - pdf.count(b"/Type /Pages"))  ## %PDF- and one page
print("FAIL badges:", html.count(">FAIL<"), "| escaped SSID:", "&lt;b&gt;guest" in html)  ## Content checks""",
            "under": "`extends` makes the child render the parent, replacing each `block` with the child's version (`{{ super() }}` keeps the parent's content). Macros compile to functions that return markup, so their output isn't escaped twice. Chromium's print-to-PDF uses the print stylesheet and page size; `print_background=True` keeps background colours, which browsers drop when printing by default.",
            "gotchas": [],
            "best": "One base template per brand, a child template per report type, macros for repeated widgets, `StrictUndefined` everywhere, CSS inline (reports are emailed and archived, so external files get lost), and PDF only where it's actually required: HTML is searchable and easier to diff.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "local_only": JINJA,
            "prompt": "Render a plain-text summary (not HTML) of three results with a for loop and a conditional PASS/FAIL marker.",
            "solution": "Text output doesn't need autoescape; `trim_blocks` keeps the loop from adding blank lines.",
            "solution_code": """from jinja2 import Environment

env = Environment(trim_blocks=True, lstrip_blocks=True)
tpl = env.from_string('''{% for r in results %}
{{ "%-12s"|format(r.test) }} {{ "PASS" if r.ok else "FAIL" }}
{% endfor %}''')
print(tpl.render(results=[{"test": "assoc_wpa3", "ok": True}, {"test": "roam_11r", "ok": False}, {"test": "dfs_52", "ok": True}]))""",
        },
        {
            "level": "Medium",
            "local_only": JINJA,
            "prompt": "Show what `StrictUndefined` changes: render `{{ run.firmwre }}` (typo) with the default and with StrictUndefined.",
            "solution": "The default renders an empty string silently; StrictUndefined raises UndefinedError naming the missing attribute.",
            "solution_code": """from jinja2 import Environment, StrictUndefined
from jinja2.exceptions import UndefinedError

run = {"firmware": "7.4.1"}
print(repr(Environment().from_string("fw={{ run.firmwre }}").render(run=run)))
try:
    Environment(undefined=StrictUndefined).from_string("fw={{ run.firmwre }}").render(run=run)
except UndefinedError as e:
    print("UndefinedError:", e)""",
        },
        {
            "level": "Hard",
            "local_only": JINJA,
            "prompt": "Write a macro `kpi_cell(value, kpi, unit)` that renders a table cell coloured green or red with the margin in percent, import it from a separate `macros.html`, and render two cells.",
            "solution": "`{% import \"macros.html\" as m %}` makes macros available as `m.kpi_cell(...)`.",
            "solution_code": """from jinja2 import DictLoader, Environment

env = Environment(autoescape=True, loader=DictLoader({
    "macros.html": '''{% macro kpi_cell(value, kpi, unit) -%}
<td style="color:{{ 'green' if value >= kpi else 'red' }}">{{ value }} {{ unit }} ({{ '%+.1f'|format((value - kpi) / kpi * 100) }}%)</td>
{%- endmacro %}''',
    "row.html": '''{% import "macros.html" as m %}<tr>{{ m.kpi_cell(912.4, 850, "Mbps") }}{{ m.kpi_cell(1890, 2000, "Mbps") }}</tr>''',
}))
print(env.get_template("row.html").render())""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What's Jinja2 and why use it for reports?", "a": "A template engine: templates with placeholders, loops, conditionals and filters render text from data. It separates presentation from logic, and the same engine drives Ansible, Flask and config generation.", "follow": "Where else is it used in network automation? (Device config templating, Phase 7.)"},
        {"level": "Intermediate", "q": "Why enable autoescape?", "a": "So values are HTML-escaped by default, preventing markup or scripts from data (SSIDs, hostnames, logs) being injected into reports viewed in a browser.", "follow": "How do you output trusted HTML? (|safe or markupsafe.Markup, sparingly.)"},
        {"level": "Intermediate", "q": "How does template inheritance work?", "a": "A base template defines blocks; child templates extend it and override blocks. Rendering the child produces the base with the child's blocks filled; super() includes the parent's block content.", "follow": "Macros vs includes? (Macros take arguments; include inserts another template with the current context.)"},
        {"level": "Advanced", "q": "How would you produce PDF reports in a Linux CI job?", "a": "Render HTML with Jinja2, then print it with headless Chromium (Playwright page.pdf) or WeasyPrint. Embed CSS and images (data URIs) so the HTML is self-contained, archive both HTML and PDF as artifacts.", "follow": "Trade-off between the two? (Chromium matches browser rendering exactly; WeasyPrint is lighter and has better paged-media CSS.)"},
    ],
    "quiz": [
        {"q": "Output an expression in Jinja:", "options": ["{% x %}", "{{ x }}", "{# x #}", "${x}"], "answer": 1, "why": "Double braces."},
        {"q": "Default autoescape for `Template(...)`:", "options": ["On", "Off", "Depends on file extension", "Always XML"], "answer": 1, "why": "Off unless configured."},
        {"q": "Fail on undefined variables:", "options": ["strict=True", "undefined=StrictUndefined", "check=True", "autoescape=True"], "answer": 1, "why": "StrictUndefined."},
        {"q": "Child template syntax:", "options": ["{% include %}", "{% extends 'base.html' %}", "{% import %}", "{% inherit %}"], "answer": 1, "why": "extends."},
        {"q": "Keep background colours in a Chromium PDF:", "options": ["format='A4'", "print_background=True", "scale=2", "landscape=True"], "answer": 1, "why": "Backgrounds are dropped by default."},
    ],
    "cards": [
        {"front": "Jinja syntax", "back": "`{{ expr }}`, `{% for/if %}`, `{# comment #}`, `x|filter`"},
        {"front": "Safe HTML env", "back": "`Environment(loader=..., autoescape=True, undefined=StrictUndefined)`"},
        {"front": "Custom filter", "back": "`env.filters['mbps'] = lambda v: f'{v:.1f} Mbps'`"},
        {"front": "Inheritance", "back": "base: `{% block content %}{% endblock %}`; child: `{% extends 'base.html' %}`"},
        {"front": "HTML → PDF", "back": "Playwright `page.set_content(html); page.pdf(path=..., print_background=True)`"},
    ],
}
