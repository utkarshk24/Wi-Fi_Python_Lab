"""Supporting files (simulators) shared by the Phase 6 lessons. Not a lesson module."""


def needs(pkgs: str) -> str:
    return f"needs {pkgs}, which the in-browser runner doesn't include (pip install {pkgs})"


FAKE_API = '''"""A tiny simulated Wi-Fi controller REST API, served from a background thread."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

TOKEN = "lab-token"
APS = {
    "ap-1": {"name": "ap-1", "band": "5G", "channel": 36, "clients": 12},
    "ap-2": {"name": "ap-2", "band": "6G", "channel": 37, "clients": 4},
    "ap-3": {"name": "ap-3", "band": "5G", "channel": 149, "clients": 0},
}
CLIENTS = [{"mac": f"02:00:00:00:00:{i:02x}", "rssi": -40 - i} for i in range(7)]
STATE = {"flaky_calls": 0}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        parts = url.path.strip("/").split("/")
        if url.path == "/api/v1/aps":
            band = query.get("band", [None])[0]
            return self.reply(200, [ap for ap in APS.values() if band in (None, ap["band"])])
        if len(parts) == 4 and parts[:3] == ["api", "v1", "aps"]:
            ap = APS.get(parts[3])
            return self.reply(200, ap) if ap else self.reply(404, {"error": f"no AP named {parts[3]}"})
        if url.path == "/api/v1/clients":
            page = int(query.get("page", ["1"])[0])
            items = CLIENTS[(page - 1) * 3: page * 3]
            nxt = f"/api/v1/clients?page={page + 1}" if page * 3 < len(CLIENTS) else None
            return self.reply(200, {"items": items, "next": nxt})
        if url.path == "/api/v1/flaky":
            STATE["flaky_calls"] += 1
            if STATE["flaky_calls"] <= 2:
                return self.reply(503, {"error": "controller busy"})
            return self.reply(200, {"status": "ok", "attempt": STATE["flaky_calls"]})
        if url.path == "/api/v1/slow":
            time.sleep(2)
            return self.reply(200, {"status": "finally"})
        return self.reply(404, {"error": "unknown path"})

    def do_POST(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            return self.reply(401, {"error": "missing or bad token"})
        if self.headers.get("Content-Type") != "application/json":
            return self.reply(415, {"error": "send JSON"})
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if len(parts) == 5 and parts[4] == "channel" and parts[3] in APS:
            if body.get("channel") not in {1, 6, 11, 36, 37, 149, 165}:
                return self.reply(422, {"error": f"invalid channel {body.get('channel')}"})
            APS[parts[3]].update(band=body["band"], channel=body["channel"])
            return self.reply(200, APS[parts[3]])
        return self.reply(404, {"error": "unknown path"})


def start():
    """Start the server on a free port and return its base URL."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"
'''


FAKE_CONSOLE = '''"""A simulated DUT UART console on a pseudo-terminal, so pyserial has something to talk to."""
import os
import threading
import time
import tty

POWER = threading.Event()
BOOT = [
    "U-Boot 2023.04 (Mar 02 2026)",
    "DRAM:  512 MiB",
    "Hit any key to stop autoboot:  2",
]
LINUX = [
    "Starting kernel ...",
    "[    1.204] ath12k_pci 0000:01:00.0: fw 1.2.3",
    "[    2.881] br-lan: port 1(eth0) entered forwarding state",
    "",
    "OpenWrt 23.05 ap-lab-07 ttyS0",
    "",
]
COMMANDS = {
    "uname -a": "Linux ap-lab-07 6.6.30 #0 SMP aarch64 GNU/Linux",
    "iw dev wlan0 info": "Interface wlan0\\r\\n\\ttype AP\\r\\n\\tchannel 36 (5180 MHz), width: 80 MHz",
    "cat /etc/openwrt_release": "DISTRIB_RELEASE='23.05.3'",
    "printenv bootdelay": "bootdelay=2",
    "version": "U-Boot 2023.04 (Mar 02 2026)",
}


def _serve(fd):
    def say(text):
        os.write(fd, (text + "\\r\\n").encode())

    POWER.wait()
    for line in BOOT:
        say(line)
    time.sleep(0.5)
    try:
        interrupted = bool(os.read(fd, 64))
    except BlockingIOError:
        interrupted = False
    prompt = "=> " if interrupted else "root@ap-lab-07:~# "
    if not interrupted:
        for line in LINUX:
            say(line)
    os.write(fd, prompt.encode())
    buf = b""
    while True:
        try:
            chunk = os.read(fd, 256)
        except BlockingIOError:
            time.sleep(0.01)
            continue
        except OSError:
            return
        text = chunk.replace(b"\\r\\n", b"\\n").replace(b"\\r", b"\\n")
        os.write(fd, text.replace(b"\\n", b"\\r\\n"))
        buf += text
        while b"\\n" in buf:
            line, _, buf = buf.partition(b"\\n")
            cmd = line.decode().strip()
            if cmd:
                say(COMMANDS.get(cmd, f"-ash: {cmd.split()[0]}: not found"))
            os.write(fd, prompt.encode())


def start():
    """Create the fake console and return its device path (like /dev/ttyUSB0)."""
    controller, device = os.openpty()
    tty.setraw(device)
    os.set_blocking(controller, False)
    threading.Thread(target=_serve, args=(controller,), daemon=True).start()
    return os.ttyname(device)


def power_on():
    """Like switching the DUT's PDU outlet on: the boot log starts now."""
    POWER.set()
'''


FAKE_CLI = '''"""A simulated interactive AP command line (login, prompt, a few commands)."""
import getpass
import sys

user = input("Username: ")
password = getpass.getpass("Password: ")
if (user, password) != ("admin", "lab123"):
    print("Login incorrect")
    sys.exit(1)
print("Welcome to AP-OS 7.4.1")
mode = "ap-1> "
while True:
    try:
        cmd = input(mode).strip()
    except EOFError:
        break
    if cmd == "show version":
        print("AP-OS 7.4.1 build 2219, uptime 3 days")
    elif cmd == "show radio 5g":
        print("Radio 5G: channel 36, width 80 MHz, txpower 20 dBm, clients 12")
    elif cmd == "enable":
        mode = "[admin@ap-1]# "
    elif cmd == "reload":
        if input("Proceed with reload? [y/N] ").strip().lower() == "y":
            print("Reloading...")
            break
    elif cmd in {"exit", "quit"}:
        print("Bye")
        break
    elif cmd:
        print(f"% Unknown command: {cmd}")
'''
