"""Phase 7 content: modules 7.1-7.4 (sockets, ipaddress, Paramiko, Netmiko)."""

from net_support import needs, sim

SOCK = "uses real sockets and a server thread, which the in-browser runner can't do"
PARAMIKO = needs("paramiko") + " and starts a simulated SSH device on localhost"
NETMIKO = needs("netmiko") + " and starts simulated SSH devices on localhost"
DEV = sim("fake_device.py")

BENCH_SERVER = '''"""A tiny line-based bench-control server (think: attenuator or relay box with a TCP port)."""
import socketserver
import threading

STATE = {"att": 0}


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        for raw in self.rfile:
            cmd = raw.decode().strip()
            if cmd == "ATT?":
                reply = f"ATT {STATE['att']}"
            elif cmd.startswith("ATT "):
                try:
                    STATE["att"] = int(cmd.split()[1])
                    reply = f"OK {STATE['att']}"
                except ValueError:
                    reply = "ERR bad value"
            elif cmd == "BURST":
                self.wfile.write(b"READY\\n")
                reply = "DONE"
            elif cmd == "QUIT":
                self.wfile.write(b"BYE\\n")
                return
            else:
                reply = f"ERR unknown command {cmd!r}"
            self.wfile.write((reply + "\\n").encode())


def start():
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server.server_address[1]
'''

M_7_1 = {
    "id": "7.1",
    "title": "Socket Programming",
    "hours": 2.5,
    "summary": "TCP and UDP from first principles: clients and servers, timeouts, framing a byte stream into messages, and packing binary protocol fields with struct.",
    "concepts": [
        {
            "title": "A TCP client for a line-based protocol",
            "files": {"bench_server.py": BENCH_SERVER},
            "local_only": SOCK,
            "concept": "`socket.create_connection((host, port), timeout=...)` opens a TCP connection. TCP is a **byte stream**: it delivers bytes in order, but doesn't preserve message boundaries, so the protocol must say where a message ends (here: a newline). `sock.makefile(\"rwb\")` wraps the socket in a buffered file so `readline()` returns exactly one line. Errors are exceptions: `ConnectionRefusedError` when nothing listens, `TimeoutError` (socket.timeout) when the peer is silent.",
            "why": "Lots of lab equipment speaks simple text protocols over TCP: attenuators, power relays, RF switches, signal generators (SCPI on port 5025). A dozen lines of socket code control them without any vendor library.",
            "syntax": "with socket.create_connection((host, port), timeout=3) as s:\n    f = s.makefile(\"rwb\")\n    f.write(b\"ATT 30\\n\"); f.flush()\n    reply = f.readline().decode().strip()",
            "code": """import socket  ## Standard-library sockets

from bench_server import start  ## Simulated bench box (see supporting files)

port = start()  ## Server listens on 127.0.0.1:<port>


def query(f, cmd):  ## Send one line, read one line back
    f.write(cmd.encode() + b"\\n")  ## Messages end with a newline
    f.flush()  ## Push the buffered bytes onto the network
    return f.readline().decode().strip()  ## Blocks until a full line arrives (or the timeout)


with socket.create_connection(("127.0.0.1", port), timeout=3) as sock:  ## TCP connect with a timeout
    f = sock.makefile("rwb")  ## Buffered reader/writer over the socket
    print(query(f, "ATT 30"))  ## Set attenuation
    print(query(f, "ATT?"))  ## Read it back
    print(query(f, "ATT thirty"))  ## Server-side validation
    print(query(f, "QUIT"))  ## Polite goodbye
    print(f.readline())  ## Server closed the connection: readline returns b'' at EOF

try:  ## Connecting to a port where nothing listens
    socket.create_connection(("127.0.0.1", 1), timeout=1)  ## Port 1 is closed here
except ConnectionRefusedError as e:  ## The OS answered with a TCP reset
    print("refused:", e.errno)  ## errno 111 on Linux (ECONNREFUSED)""",
            "under": "`create_connection` resolves the name, tries each address and applies the timeout to the connect and to every later blocking call on the socket. `makefile` builds a `BufferedRWPair` over the socket, so `readline` keeps reading chunks until it sees `\\n`. An empty read (`b''`) means the peer closed its side: it's the end-of-stream signal, not an error.",
            "gotchas": [
                {
                    "title": "Assuming one recv() is one message",
                    "files": {"bench_server.py": BENCH_SERVER},
                    "local_only": SOCK,
                    "note": "`recv(1024)` returns whatever bytes have arrived: part of a message, or two messages glued together. Here the server sends `READY` and `DONE` back to back and a single recv gets both. Frame messages (newline, length prefix) and read until a complete frame is in hand.",
                    "wrong": """import socket
import time
from bench_server import start

with socket.create_connection(("127.0.0.1", start()), timeout=3) as s:
    s.sendall(b"BURST\\n")
    time.sleep(0.2)
    print("one recv got:", s.recv(1024))""",
                    "fixed": """import socket
from bench_server import start

with socket.create_connection(("127.0.0.1", start()), timeout=3) as s:
    f = s.makefile("rwb")
    f.write(b"BURST\\n")
    f.flush()
    print("first message:", f.readline())
    print("second message:", f.readline())""",
                },
            ],
            "best": "Always set timeouts, use `sendall` (not `send`) and a framing rule for reads, wrap connections in `with`, handle `ConnectionRefusedError`, `TimeoutError` and EOF explicitly, and log the raw bytes when talking to a new instrument.",
        },
        {
            "title": "Binary protocols with struct and length-prefixed framing",
            "concept": "`struct.pack(fmt, ...)` turns numbers into bytes and `struct.unpack` turns them back, following a format string: `!` for network (big-endian) byte order, `B`/`H`/`I` for 1/2/4-byte unsigned ints, `h` signed short, `f` float, `6s` six raw bytes. Binary streams are usually framed with a length prefix: read the fixed-size header, then exactly that many payload bytes.",
            "why": "Telemetry from test equipment, custom DUT agents, pcap headers and Wi-Fi frame fields are all binary. struct is how Python reads and writes them precisely, byte for byte.",
            "syntax": "hdr = struct.pack(\"!HB\", length, msg_type)\nlength, msg_type = struct.unpack(\"!HB\", data[:3])\nstruct.calcsize(\"!HB\")  # 3",
            "code": """import struct  ## Pack and unpack binary data

TELEMETRY = struct.Struct("!IhH6s")  ## seq (uint32), rssi (int16), mbps (uint16), MAC (6 bytes); ! = network byte order
print(TELEMETRY.size, "bytes per record")  ## 4 + 2 + 2 + 6 = 14

mac = bytes.fromhex("3c846a123460")  ## A MAC address as 6 raw bytes
record = TELEMETRY.pack(1042, -52, 1201, mac)  ## Python values -> bytes
print(record.hex(" "))  ## How it looks on the wire
seq, rssi, mbps, raw_mac = TELEMETRY.unpack(record)  ## bytes -> Python values
print(seq, rssi, mbps, raw_mac.hex(":"))  ## Signed RSSI survives the round trip


def frame(payload: bytes) -> bytes:  ## Length-prefixed message
    return struct.pack("!H", len(payload)) + payload  ## 2-byte length, then the payload


class Deframer:  ## Rebuilds messages from arbitrary chunks of a stream
    def __init__(self):  ## Starts empty
        self.buf = b""  ## Bytes received but not yet consumed

    def feed(self, chunk: bytes):  ## Call with whatever recv() returned
        self.buf += chunk  ## Append new bytes
        while len(self.buf) >= 2:  ## Enough for a length header?
            (length,) = struct.unpack("!H", self.buf[:2])  ## Peek at the length
            if len(self.buf) < 2 + length:  ## Payload not complete yet
                break  ## Wait for more bytes
            yield self.buf[2:2 + length]  ## One complete message
            self.buf = self.buf[2 + length:]  ## Drop it from the buffer


stream = frame(record) + frame(TELEMETRY.pack(1043, -55, 1150, mac))  ## Two messages back to back
d = Deframer()  ## One deframer per connection
for chunk in (stream[:5], stream[5:20], stream[20:]):  ## Simulate TCP splitting the stream oddly
    for msg in d.feed(chunk):  ## Zero or more complete messages per chunk
        print("message:", TELEMETRY.unpack(msg)[:3])  ## seq, rssi, mbps""",
            "under": "Without a byte-order prefix struct uses the machine's native order and alignment padding, which differs between platforms, so protocols always specify one (`!` or `>` for big-endian). A precompiled `struct.Struct` parses the format once and is faster in loops. `bytes.hex(\" \")` and `hex(\":\")` add separators for readability.",
            "gotchas": [],
            "best": "Write the wire format down (field, size, signedness, byte order) next to a `struct.Struct` constant, always use an explicit byte order, validate lengths before unpacking, and keep a buffer per connection for framing.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "files": {"bench_server.py": BENCH_SERVER},
            "local_only": SOCK,
            "prompt": "Write `is_open(host, port, timeout=0.5)` using `connect_ex`, and check the bench server's port plus ports 1 and 9.",
            "solution": "`connect_ex` returns 0 on success or an errno instead of raising, which makes a compact port checker.",
            "solution_code": """import socket
from bench_server import start


def is_open(host, port, timeout=0.5):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


bench = start()
for port in (bench, 1, 9):
    label = "bench port" if port == bench else f"port {port}"
    print(label, is_open("127.0.0.1", port))""",
        },
        {
            "level": "Medium",
            "prompt": "The first two bytes of an 802.11 frame are the Frame Control field (little-endian). Unpack it from `b'\\x80\\x00'` (a beacon) and `b'\\x88\\x41'` (QoS data to the AP) and extract type, subtype and the To-DS/Protected flags.",
            "solution": "Unpack `<H`, then use shifts and masks: type is bits 2-3, subtype bits 4-7, flags in the second byte.",
            "solution_code": """import struct

TYPES = {0: "mgmt", 1: "ctrl", 2: "data"}


def frame_control(raw):
    (fc,) = struct.unpack("<H", raw)
    return {"type": TYPES[(fc >> 2) & 0b11], "subtype": (fc >> 4) & 0b1111,
            "to_ds": bool(fc & 0x0100), "protected": bool(fc & 0x4000)}


print(frame_control(b"\\x80\\x00"))
print(frame_control(b"\\x88\\x41"))""",
        },
        {
            "level": "Hard",
            "local_only": SOCK,
            "prompt": "Write a UDP request/response client with a timeout and retries. The server drops the first request it receives, so the client must retry.",
            "solution": "UDP has no delivery guarantee: set a socket timeout, resend on `TimeoutError`, give up after N attempts.",
            "solution_code": """import socket
import threading


def udp_server(sock):
    seen = 0
    while True:
        data, addr = sock.recvfrom(1024)
        seen += 1
        if seen == 1:
            continue
        sock.sendto(b"PONG " + data, addr)


srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
srv.bind(("127.0.0.1", 0))
threading.Thread(target=udp_server, args=(srv,), daemon=True).start()

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as c:
    c.settimeout(0.3)
    for attempt in range(1, 4):
        c.sendto(b"PING 7", srv.getsockname())
        try:
            reply, _ = c.recvfrom(1024)
            print(f"attempt {attempt}: {reply}")
            break
        except TimeoutError:
            print(f"attempt {attempt}: timeout, retrying")""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "TCP vs UDP?", "a": "TCP: connection-oriented, reliable, ordered byte stream with flow and congestion control. UDP: connectionless datagrams, no delivery or ordering guarantee, low overhead, message boundaries preserved. DNS, DHCP, SNMP, syslog and iperf -u use UDP; SSH, HTTP and NETCONF use TCP.", "follow": "Why does iperf have a UDP mode? (To measure loss and jitter at a fixed offered rate.)"},
        {"level": "Intermediate", "q": "Why can't you rely on recv() returning one message?", "a": "TCP is a byte stream; the kernel delivers whatever has arrived, split or merged arbitrarily. You need framing: delimiters, length prefixes or fixed sizes, and a buffer that accumulates until a full message is present.", "follow": "send vs sendall? (send may write only part; sendall loops until everything is sent.)"},
        {"level": "Intermediate", "q": "What does `!` mean in a struct format, and why does it matter?", "a": "Network (big-endian) byte order with no alignment padding. Native order differs across CPUs (x86 is little-endian), so wire formats must specify order explicitly.", "follow": "Which byte order do 802.11 headers use? (Little-endian, unlike most IP protocols.)"},
        {"level": "Advanced", "q": "How would you handle 500 concurrent device connections in Python?", "a": "asyncio streams (or asyncssh/aiohttp for higher-level protocols), or selectors for low-level work, instead of one thread per connection. Bound concurrency with semaphores, set timeouts everywhere, and batch results.", "follow": "When are threads still fine? (Tens of connections, blocking libraries.)"},
    ],
    "quiz": [
        {"q": "`recv()` returning b'' means...", "options": ["Timeout", "The peer closed the connection", "No data yet", "Error"], "answer": 1, "why": "EOF."},
        {"q": "Connecting to a closed local port raises...", "options": ["TimeoutError", "ConnectionRefusedError", "OSError 0", "Nothing"], "answer": 1, "why": "The OS sends a reset."},
        {"q": "`struct.calcsize('!IhH6s')`:", "options": ["12", "14", "16", "13"], "answer": 1, "why": "4+2+2+6."},
        {"q": "Which preserves message boundaries?", "options": ["TCP", "UDP", "Both", "Neither"], "answer": 1, "why": "Datagrams."},
        {"q": "Safest way to send all bytes on TCP:", "options": ["send", "sendall", "write", "sendto"], "answer": 1, "why": "Loops until done."},
    ],
    "cards": [
        {"front": "TCP client with timeout", "back": "`socket.create_connection((h, p), timeout=3)`"},
        {"front": "Line framing", "back": "`f = sock.makefile('rwb')`; `f.readline()`"},
        {"front": "Network byte order", "back": "`struct.pack('!H', n)` (big-endian, no padding)"},
        {"front": "Port check", "back": "`s.connect_ex((h, p)) == 0`"},
        {"front": "UDP reliability", "back": "Timeout + resend + max attempts (app does it)"},
    ],
}


M_7_2 = {
    "id": "7.2",
    "title": "The ipaddress Module",
    "hours": 1,
    "summary": "Validate, compare and plan IPv4/IPv6 addresses and subnets: membership, host ranges, subnetting a lab block, summarising and finding overlaps.",
    "concepts": [
        {
            "title": "Addresses, networks and interfaces",
            "concept": "`ipaddress.ip_address(\"10.1.1.5\")` validates and returns an IPv4Address or IPv6Address. `ip_network(\"10.1.1.0/24\")` is a subnet (host bits must be zero), `ip_interface(\"10.1.1.5/24\")` is an address plus its network, like an interface config. They support `in`, comparisons, sorting, arithmetic, `.hosts()`, `.subnets()`, `.supernet()` and properties such as `.is_private` and `.num_addresses`.",
            "why": "Inventory files, DHCP pools, ACLs and test configs are full of addresses. Validating and computing with real IP objects instead of string splitting prevents a whole class of bugs (and handles IPv6 for free).",
            "syntax": "ip_address(\"10.1.1.5\") in ip_network(\"10.1.1.0/24\")\nlist(net.subnets(new_prefix=26))\nip_interface(\"10.1.1.5/24\").network",
            "code": """import ipaddress  ## Standard library

mgmt = ipaddress.ip_network("10.20.30.0/24")  ## A subnet (host bits must be zero)
ap = ipaddress.ip_address("10.20.30.57")  ## A single address
print(ap in mgmt, mgmt.num_addresses, mgmt.netmask, mgmt.broadcast_address)  ## Membership and basic facts
hosts = list(mgmt.hosts())  ## Usable host addresses (network and broadcast excluded)
print(hosts[0], hosts[-1], len(hosts))  ## First, last, count
print(ap + 1, ap.is_private, ap.reverse_pointer)  ## Arithmetic, RFC 1918 check, PTR name

iface = ipaddress.ip_interface("10.20.30.57/24")  ## Address plus prefix, like an interface config
print(iface.ip, iface.network, iface.with_netmask)  ## Split it apart

v6 = ipaddress.ip_address("2001:db8:0:0:0:0:0:1")  ## IPv6 works the same way
print(v6.compressed, v6.version, ipaddress.ip_network("2001:db8::/64").num_addresses)  ## Short form and a big number

addrs = ["10.20.30.100", "10.20.30.9", "10.20.4.1"]  ## Strings sort wrongly
print(sorted(addrs))  ## Lexicographic: "10.20.30.100" before "10.20.30.9"
print([str(a) for a in sorted(map(ipaddress.ip_address, addrs))])  ## Numeric order""",
            "under": "IPv4Address is a 32-bit integer underneath (`int(ap)`), which is why comparison, sorting and `+ 1` work. `hosts()` is a generator, so iterating a huge IPv6 network doesn't build a list unless you ask. `ip_address()` picks v4 or v6 by parsing; the explicit classes (`IPv4Address`) reject the other family.",
            "gotchas": [
                {
                    "title": "Host bits set in a network",
                    "note": "`ip_network(\"10.1.1.5/24\")` is ambiguous: is that the network 10.1.1.0/24 or a typo? ipaddress refuses it. Use `strict=False` to mask the host bits, or `ip_interface` if you mean an address with its prefix.",
                    "wrong": """import ipaddress

print(ipaddress.ip_network("10.1.1.5/24"))""",
                    "fixed": """import ipaddress

print(ipaddress.ip_network("10.1.1.5/24", strict=False))
print(ipaddress.ip_interface("10.1.1.5/24").network)""",
                },
            ],
            "best": "Parse addresses at the boundary (config load, CLI args) into ipaddress objects, keep them as objects internally, convert to strings only for output, and use `ip_interface` for 'address/prefix' values from device configs.",
        },
        {
            "title": "Planning: subnetting, summarising, overlaps",
            "concept": "`net.subnets(new_prefix=26)` splits a block into equal subnets; `ipaddress.collapse_addresses()` merges adjacent or overlapping networks into the shortest list; `a.overlaps(b)` and `a.subnet_of(b)` compare networks; `net.address_exclude(sub)` carves a hole out of a block.",
            "why": "Lab networks get carved up by hand and conflicts cause baffling failures (two benches answering on the same subnet). A planning script that allocates per bench and checks the inventory for overlaps is a small, high-value tool.",
            "syntax": "list(block.subnets(new_prefix=26))\nlist(ipaddress.collapse_addresses(nets))\na.overlaps(b); a.subnet_of(b)",
            "code": """import ipaddress  ## Standard library

block = ipaddress.ip_network("10.50.0.0/22")  ## The lab's allocation: 1024 addresses
benches = list(block.subnets(new_prefix=26))  ## Sixteen /26s, 64 addresses each
plan = dict(zip([f"bench-{i:02}" for i in range(1, 5)], benches))  ## First four benches
for name, net in plan.items():  ## Show the plan
    hosts = list(net.hosts())  ## 62 usable addresses
    print(f"{name}: {net}  gw {hosts[0]}  dhcp {hosts[9]}-{hosts[-1]}")  ## Gateway first, DHCP pool after 9 reserved

routes = [ipaddress.ip_network(n) for n in ["10.50.0.0/26", "10.50.0.64/26", "10.50.0.128/25", "10.50.2.0/24"]]  ## From a routing table
print([str(n) for n in ipaddress.collapse_addresses(routes)])  ## Shortest equivalent list

inventory = {"bench-01": "10.50.0.0/26", "bench-07": "10.50.0.32/27", "guest": "10.60.0.0/24"}  ## Someone hand-edited this
nets = {k: ipaddress.ip_network(v) for k, v in inventory.items()}  ## Parse once
names = sorted(nets)  ## Stable pair order
clashes = [(a, b) for i, a in enumerate(names) for b in names[i + 1:] if nets[a].overlaps(nets[b])]  ## Every pair checked once
print("overlaps:", clashes)  ## bench-07 sits inside bench-01

free = list(block.address_exclude(ipaddress.ip_network("10.50.0.0/24")))  ## What's left after the first /24 is used
print(sorted(str(n) for n in free))  ## Remaining blocks""",
            "under": "`subnets()` and `address_exclude()` are generators. `collapse_addresses` sorts the networks and merges neighbours whose union is a valid larger prefix (two adjacent /26 make a /25, which merges with the next /25 into a /24). `overlaps` is true when either network contains the other's first address.",
            "gotchas": [],
            "best": "Keep the address plan in data (YAML/JSON) and generate configs from it, check overlaps in CI whenever the inventory changes, reserve the first addresses of each subnet for infrastructure, and document it all in the same file.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Validate a list of strings from a CSV and split them into valid IPv4, valid IPv6 and invalid entries.",
            "solution": "`ip_address` raises ValueError for anything invalid; `.version` tells the family.",
            "solution_code": """import ipaddress

raw = ["10.1.1.1", "10.1.1.256", "fe80::1", "ap-lab-07", "192.168.100.57", " 10.0.0.1"]
result = {"v4": [], "v6": [], "invalid": []}
for s in raw:
    try:
        ip = ipaddress.ip_address(s)
        result[f"v{ip.version}"].append(str(ip))
    except ValueError:
        result["invalid"].append(s)
print(result)""",
        },
        {
            "level": "Medium",
            "prompt": "Assign management IPs to 5 APs from `10.20.30.0/27`, skipping the gateway (first host) and anything listed as reserved.",
            "solution": "Iterate the hosts generator, filter out reserved addresses, and zip with the AP names.",
            "solution_code": """import ipaddress

net = ipaddress.ip_network("10.20.30.0/27")
reserved = {ipaddress.ip_address(a) for a in ["10.20.30.2", "10.20.30.5"]}
hosts = list(net.hosts())
gateway, candidates = hosts[0], [h for h in hosts[1:] if h not in reserved]
aps = [f"ap-lab-{i:02}" for i in range(7, 12)]
print("gw", gateway)
for ap, ip in zip(aps, candidates):
    print(ap, ip)""",
        },
        {
            "level": "Hard",
            "prompt": "Given an interface list from several devices (`device`, `interface`, `ip/prefix`), report any two interfaces on different devices that are configured in overlapping subnets but with different prefixes (a classic mask mismatch).",
            "solution": "Parse with ip_interface, compare every pair across devices, and flag overlapping networks whose prefix lengths differ.",
            "solution_code": """import ipaddress
from itertools import combinations

rows = [("core-sw", "Vlan100", "10.20.30.1/24"), ("wlc-1", "Gi0/0/1", "10.20.30.5/24"),
        ("ap-lab-07", "eth0", "10.20.30.57/26"), ("ap-lab-08", "eth0", "10.20.31.8/24")]
ifaces = [(d, i, ipaddress.ip_interface(a)) for d, i, a in rows]
for (d1, i1, a1), (d2, i2, a2) in combinations(ifaces, 2):
    if d1 != d2 and a1.network.overlaps(a2.network) and a1.network.prefixlen != a2.network.prefixlen:
        print(f"mask mismatch: {d1} {i1} {a1.with_prefixlen} vs {d2} {i2} {a2.with_prefixlen}")""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "ip_address vs ip_network vs ip_interface?", "a": "ip_address is one address; ip_network is a subnet (host bits zero, strict by default); ip_interface is an address with its prefix, exposing .ip and .network.", "follow": "What does strict=False do? (Masks host bits instead of raising.)"},
        {"level": "Intermediate", "q": "How do you find overlapping subnets in an inventory?", "a": "Parse each into ip_network and test pairs with .overlaps() (or sort by network address and compare neighbours for large lists). Report both owners.", "follow": "How would you scale to 100k prefixes? (Sort and sweep, or a radix tree like pytricia.)"},
        {"level": "Intermediate", "q": "Why sort IPs as objects instead of strings?", "a": "String sorting is lexicographic, so 10.0.0.100 sorts before 10.0.0.9. ipaddress objects compare numerically.", "follow": "How would you sort mixed v4/v6? (Key by (version, int(ip)).)"},
    ],
    "quiz": [
        {"q": "`ip_network('10.1.1.5/24')` gives...", "options": ["10.1.1.0/24", "ValueError", "10.1.1.5/32", "None"], "answer": 1, "why": "Host bits set; strict by default."},
        {"q": "Usable hosts in a /26:", "options": ["64", "62", "63", "30"], "answer": 1, "why": "64 minus network and broadcast."},
        {"q": "`collapse_addresses` on two adjacent /26s returns...", "options": ["Two /26s", "One /25", "A /24", "Error"], "answer": 1, "why": "Merged into the covering prefix."},
        {"q": "Address with its prefix, like interface config:", "options": ["ip_address", "ip_network", "ip_interface", "IPv4Mask"], "answer": 2, "why": "ip_interface."},
        {"q": "`sorted(['10.0.0.9', '10.0.0.10'])` as strings gives first...", "options": ["10.0.0.9", "10.0.0.10", "Error", "Random"], "answer": 1, "why": "'1' < '9'."},
    ],
    "cards": [
        {"front": "Membership test", "back": "`ip_address(a) in ip_network(n)`"},
        {"front": "Split a block", "back": "`list(net.subnets(new_prefix=26))`"},
        {"front": "Summarise routes", "back": "`ipaddress.collapse_addresses(nets)`"},
        {"front": "Overlap check", "back": "`a.overlaps(b)`, `a.subnet_of(b)`"},
        {"front": "Address + mask", "back": "`ip_interface('10.1.1.5/24').network`"},
    ],
}


M_7_3 = {
    "id": "7.3",
    "title": "Paramiko",
    "hours": 2,
    "summary": "SSH from Python with Paramiko: connect, run commands with exit codes, host key verification, and interactive shell sessions for devices that need one.",
    "concepts": [
        {
            "title": "SSHClient and exec_command",
            "files": DEV,
            "local_only": PARAMIKO,
            "concept": "`paramiko.SSHClient()` is the high-level SSH client. `connect(host, port, username, password, timeout=...)` authenticates; `exec_command(cmd)` opens a channel, runs one command and returns `stdin, stdout, stderr` file-like objects; `stdout.channel.recv_exit_status()` waits for and returns the exit code. A **host key policy** decides what happens with an unknown server key. The device here is a simulated switch with a real SSH server on localhost.",
            "why": "SSH is how you reach APs, controllers, Linux test clients and traffic generators. Paramiko is the foundation that Netmiko, NAPALM's IOS driver and many lab tools are built on, so understanding it pays off when the higher layers misbehave.",
            "syntax": "c = paramiko.SSHClient()\nc.load_system_host_keys()\nc.connect(host, username=u, password=p, timeout=10)\n_, out, err = c.exec_command(\"uname -a\", timeout=30)\nprint(out.read().decode(), out.channel.recv_exit_status())",
            "code": """import paramiko  ## pip install paramiko

from fake_device import start  ## Simulated device with a real SSH server (see supporting files)

port = start("wlc-1", 5)  ## On a real bench: port 22 on the device's management IP

client = paramiko.SSHClient()  ## High-level client
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  ## Lab simulator only; see the gotcha below
client.connect("127.0.0.1", port=port, username="admin", password="lab123", timeout=5, look_for_keys=False, allow_agent=False)  ## Password auth only


def run(cmd):  ## One command, one channel
    _, stdout, stderr = client.exec_command(cmd, timeout=10)  ## Returns immediately with file-like objects
    out = stdout.read().decode().replace("\\r\\n", "\\n")  ## Read until the remote side closes the channel
    status = stdout.channel.recv_exit_status()  ## Exit code (0 = success)
    return status, out  ## Both matter


status, out = run("show clock")  ## A simple command
print(status, out.strip())  ## 0 and the time
status, out = run("show ip interface brief")  ## Tabular output
print(status, out.splitlines()[1])  ## First data row
status, out = run("show wireless summry")  ## Typo: the device rejects it
print(status, out.strip().splitlines()[-1])  ## Non-zero status plus the device's error
transport = client.get_transport()  ## The underlying SSH connection
print(transport.is_active(), transport.remote_version)  ## Still connected; the server's version string
client.close()  ## Close the connection""",
            "under": "One SSH connection (a `Transport`) can carry many channels. `exec_command` opens a new channel per command, so commands don't share state: a `cd` in one doesn't affect the next. Reading stdout to EOF before calling `recv_exit_status()` avoids a deadlock when output fills the channel's window. Many network devices don't return meaningful exit codes, so also check the output for error markers like `% Invalid input`.",
            "gotchas": [
                {
                    "title": "Trusting every host key",
                    "files": DEV,
                    "local_only": PARAMIKO,
                    "note": "`AutoAddPolicy` accepts any server key, so a man-in-the-middle (or a re-imaged device with someone else's IP) is accepted silently and gets your password. Use `RejectPolicy` with a known_hosts file you manage, and pin keys when devices are provisioned.",
                    "wrong": """import paramiko
from fake_device import start

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=start(), username="admin", password="lab123", look_for_keys=False, allow_agent=False)
print("connected; server key was never checked")""",
                    "fixed": """import paramiko
from fake_device import HOST_KEY, start

port = start()
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.RejectPolicy())
try:
    c.connect("127.0.0.1", port=port, username="admin", password="lab123", look_for_keys=False, allow_agent=False)
except paramiko.SSHException as e:
    print("refused:", str(e).replace(str(port), "PORT"))
c.get_host_keys().add(f"[127.0.0.1]:{port}", HOST_KEY.get_name(), HOST_KEY)
c.connect("127.0.0.1", port=port, username="admin", password="lab123", look_for_keys=False, allow_agent=False)
print("connected with a pinned key")""",
                },
            ],
            "best": "Pin host keys (RejectPolicy + managed known_hosts), use key-based auth or a vault for passwords, set connect and command timeouts, read output to EOF before the exit status, and close clients in `finally`/`with`. For network devices, reach for Netmiko unless you need low-level control.",
        },
        {
            "title": "Interactive shells with invoke_shell",
            "files": DEV,
            "local_only": PARAMIKO,
            "concept": "Some tasks need one continuous session: entering configuration mode, changing context, answering prompts. `client.invoke_shell()` opens a channel with a pseudo-terminal, like an interactive login. You write commands with `send()` and read with `recv()` until the expected prompt shows up; a small `read_until(chan, prompt)` helper with a deadline does that job.",
            "why": "On many network devices exec channels run each command in isolation, so `configure terminal` followed by `interface ...` only works in a shell session. Understanding this is also what makes Netmiko's behaviour (and its timeouts) make sense.",
            "syntax": "chan = client.invoke_shell()\nchan.send(\"configure terminal\\n\")\nout = read_until(chan, b\"(config)#\")",
            "code": """import time  ## Deadlines

import paramiko  ## pip install paramiko

from fake_device import start  ## Simulated device

client = paramiko.SSHClient()  ## Same client as before
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  ## Simulator only
client.connect("127.0.0.1", port=start("core-sw-1", 1), username="admin", password="lab123", look_for_keys=False, allow_agent=False)  ## Log in


def read_until(chan, prompt: bytes, timeout=5.0):  ## Collect output until the prompt appears
    deadline, buf = time.monotonic() + timeout, b""  ## Our own deadline
    while not buf.endswith(prompt):  ## Prompts are at the very end of the output
        if time.monotonic() > deadline:  ## Took too long
            raise TimeoutError(f"no {prompt!r}; got {buf[-60:]!r}")  ## Show what arrived
        if chan.recv_ready():  ## Data waiting?
            buf += chan.recv(4096)  ## Read what's there
        else:  ## Nothing yet
            time.sleep(0.05)  ## Don't spin the CPU
    return buf.decode().replace("\\r\\n", "\\n")  ## Normalised text


chan = client.invoke_shell()  ## Interactive session with a pty
read_until(chan, b"core-sw-1#")  ## Wait for the first prompt
for cmd, prompt in [("configure terminal", b"(config)#"), ("interface Vlan300", b"(config-if)#"),  ## Each step changes the prompt
                    ("description lab-6g-clients", b"(config-if)#"), ("end", b"core-sw-1#")]:  ## Back to exec mode
    chan.send(cmd + "\\n")  ## Type the command
    out = read_until(chan, prompt)  ## Wait for the mode's prompt
    print(repr(out.splitlines()[-1]))  ## The prompt we landed on
chan.send("show running-config\\n")  ## Verify
print(read_until(chan, b"core-sw-1#").splitlines()[-4:-1])  ## Our interface is in the config
client.close()  ## Closes the shell too""",
            "under": "The shell channel's pty makes the device echo input and print prompts, exactly as for a human. `recv_ready()` checks whether data is buffered without blocking. Reading until the prompt **ends** the buffer avoids matching a prompt-like string inside output. This loop is essentially what Netmiko's `read_until_pattern` does, plus handling of paging, ANSI codes and timing quirks.",
            "gotchas": [],
            "best": "Match prompts that include the hostname and mode, keep a deadline per step, verify config changes by reading them back, and prefer Netmiko (which handles paging, prompt detection and vendor quirks) for real devices.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "files": DEV,
            "local_only": PARAMIKO,
            "prompt": "Connect to the simulated device and print the uptime line from `show version`, plus the exit status.",
            "solution": "exec_command, read stdout, find the line containing 'uptime'.",
            "solution_code": """import paramiko
from fake_device import start

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=start("ap-lab-07", 7), username="admin", password="lab123",
          look_for_keys=False, allow_agent=False, timeout=5)
_, out, _ = c.exec_command("show version", timeout=10)
text = out.read().decode()
print(next(line for line in text.splitlines() if "uptime" in line), out.channel.recv_exit_status())
c.close()""",
        },
        {
            "level": "Medium",
            "files": DEV,
            "local_only": PARAMIKO,
            "prompt": "Show what a wrong password does: catch `paramiko.AuthenticationException` and print a one-line message.",
            "solution": "Authentication failures raise AuthenticationException (a subclass of SSHException); report it without a traceback.",
            "solution_code": """import paramiko
from fake_device import start

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    c.connect("127.0.0.1", port=start(), username="admin", password="wrong",
              look_for_keys=False, allow_agent=False, timeout=5)
except paramiko.AuthenticationException as e:
    print("login failed:", e)
finally:
    c.close()""",
        },
        {
            "level": "Hard",
            "files": DEV,
            "local_only": PARAMIKO,
            "prompt": "Run the same three commands on three simulated devices concurrently with a ThreadPoolExecutor (one SSH client per device), and print a per-device summary.",
            "solution": "One client per thread (don't share), results collected with `as_completed` or `map`, connections closed in finally.",
            "solution_code": """from concurrent.futures import ThreadPoolExecutor

import paramiko
from fake_device import start

DEVICES = {f"ap-lab-0{i}": start(f"ap-lab-0{i}", i) for i in (7, 8, 9)}


def collect(name):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        c.connect("127.0.0.1", port=DEVICES[name], username="admin", password="lab123",
                  look_for_keys=False, allow_agent=False, timeout=5)
        statuses = []
        for cmd in ("show clock", "show version", "show ip interface brief"):
            _, out, _ = c.exec_command(cmd, timeout=10)
            out.read()
            statuses.append(out.channel.recv_exit_status())
        return name, statuses
    finally:
        c.close()


with ThreadPoolExecutor(max_workers=3) as pool:
    for name, statuses in pool.map(collect, DEVICES):
        print(name, "ok" if not any(statuses) else statuses)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "exec_command vs invoke_shell?", "a": "exec_command runs a single command on a new channel and returns its output and exit status; each call is independent. invoke_shell opens an interactive session with a pty, needed for mode changes and prompts, but you must detect prompts yourself.", "follow": "Why don't exit codes help much on network devices? (Many always return 0 or don't support exec; check output.)"},
        {"level": "Intermediate", "q": "What's the risk of AutoAddPolicy?", "a": "It accepts unknown host keys silently, so MITM attacks or IP reuse go unnoticed and credentials are sent to whoever answers. Use RejectPolicy with managed known_hosts, or verify fingerprints from your inventory.", "follow": "How do you handle devices re-imaged with new keys? (Update the inventory's pinned key through a controlled process.)"},
        {"level": "Intermediate", "q": "Can you share one SSHClient across threads?", "a": "A Transport supports multiple channels, but sharing a client across threads needs care; the simple, safe pattern is one client per device per worker, or use asyncssh for high concurrency.", "follow": "How many concurrent SSH sessions do network devices allow? (Often 5–16 VTY lines.)"},
    ],
    "quiz": [
        {"q": "Get a command's exit code:", "options": ["stdout.status", "stdout.channel.recv_exit_status()", "client.exit_code", "stderr.read()"], "answer": 1, "why": "On the channel."},
        {"q": "Safest host key policy for production:", "options": ["AutoAddPolicy", "WarningPolicy", "RejectPolicy + known hosts", "None"], "answer": 2, "why": "Unknown keys are refused."},
        {"q": "Config mode across several commands needs...", "options": ["exec_command each", "invoke_shell", "SFTP", "Port forwarding"], "answer": 1, "why": "One persistent session."},
        {"q": "Wrong password raises...", "options": ["TimeoutError", "AuthenticationException", "ValueError", "Nothing"], "answer": 1, "why": "paramiko.AuthenticationException."},
        {"q": "One SSH connection can carry...", "options": ["One command", "Many channels", "Only a shell", "Only SFTP"], "answer": 1, "why": "Multiplexed channels."},
    ],
    "cards": [
        {"front": "Paramiko connect", "back": "`c = SSHClient(); c.load_system_host_keys(); c.connect(h, username=u, password=p, timeout=10)`"},
        {"front": "Run a command", "back": "`_, out, err = c.exec_command(cmd); out.read(); out.channel.recv_exit_status()`"},
        {"front": "Interactive session", "back": "`chan = c.invoke_shell(); chan.send('cmd\\n'); read until prompt`"},
        {"front": "Host key safety", "back": "`RejectPolicy()` + managed known_hosts"},
        {"front": "Auth failure", "back": "`except paramiko.AuthenticationException`"},
    ],
}


M_7_4 = {
    "id": "7.4",
    "title": "Netmiko",
    "hours": 2.5,
    "summary": "Netmiko on top of Paramiko: device types, prompt handling, show commands parsed into structured data, configuration changes, saving, timeouts and many devices in parallel.",
    "concepts": [
        {
            "title": "ConnectHandler, send_command and TextFSM parsing",
            "files": DEV,
            "local_only": NETMIKO,
            "concept": "`ConnectHandler(**device)` connects and prepares the session for that `device_type` (disables paging, sets terminal width, finds the prompt). `send_command(cmd)` returns the output with the echo and prompt removed. With `use_textfsm=True` Netmiko parses known commands into a **list of dicts** using the ntc-templates library. Use it as a context manager so the session is always closed.",
            "why": "Netmiko handles the tedious, vendor-specific parts of CLI automation (prompts, paging, timing) for 100+ platforms. Structured output turns 'scrape and regex' scripts into reliable data checks.",
            "syntax": "dev = {\"device_type\": \"cisco_ios\", \"host\": h, \"username\": u, \"password\": p}\nwith ConnectHandler(**dev) as conn:\n    rows = conn.send_command(\"show ip interface brief\", use_textfsm=True)",
            "code": """from netmiko import ConnectHandler  ## pip install netmiko (pulls in paramiko and ntc-templates)

from fake_device import start  ## Simulated IOS-style controller (see supporting files)

device = {  ## Everything Netmiko needs to know about one device
    "device_type": "cisco_ios",  ## Selects prompts, paging command and quirks
    "host": "127.0.0.1",  ## Management IP on a real bench
    "port": start("wlc-1", 5),  ## SSH port (22 normally)
    "username": "admin",  ## From a vault or env var in real code
    "password": "lab123",  ## Same
}  ## End of the device dict

with ConnectHandler(**device) as conn:  ## Connects, disables paging, finds the prompt; disconnects at the end
    print(conn.find_prompt())  ## The detected prompt
    print(conn.send_command("show clock").strip())  ## Raw text, echo and prompt removed
    rows = conn.send_command("show ip interface brief", use_textfsm=True)  ## Parsed into a list of dicts
    print(rows[0])  ## One interface as a dict
    down = [r["interface"] for r in rows if r["status"] != "up"]  ## Real logic on structured data
    print("not up:", down)  ## Interfaces that need attention""",
            "under": "On connect, Netmiko's `session_preparation` for cisco_ios sends `terminal width 511` and `terminal length 0` and reads the prompt. `send_command` writes the command and reads until it sees the prompt again (or a pattern you pass with `expect_string`), then strips the echoed command and trailing prompt. `use_textfsm` looks up a template by platform and command in ntc-templates' index; if none matches, you get the raw string back.",
            "gotchas": [
                {
                    "title": "A slow command and the default read timeout",
                    "files": DEV,
                    "local_only": NETMIKO,
                    "note": "`send_command` gives up after `read_timeout` seconds (10 by default) if the prompt hasn't returned. Long commands (`show tech`, file copies, upgrades) need a larger value. Here a deliberately small timeout shows the failure on a command that takes 1 s.",
                    "wrong": """from netmiko import ConnectHandler
from netmiko.exceptions import ReadTimeout
from fake_device import start

dev = {"device_type": "cisco_ios", "host": "127.0.0.1", "port": start(), "username": "admin", "password": "lab123"}
with ConnectHandler(**dev) as conn:
    try:
        conn.send_command("show tech-support wireless", read_timeout=0.5)
    except ReadTimeout as e:
        print("ReadTimeout:", next(line for line in str(e).splitlines() if line.strip()))""",
                    "fixed": """from netmiko import ConnectHandler
from fake_device import start

dev = {"device_type": "cisco_ios", "host": "127.0.0.1", "port": start(), "username": "admin", "password": "lab123"}
with ConnectHandler(**dev) as conn:
    out = conn.send_command("show tech-support wireless", read_timeout=60)
    print(out.splitlines()[0])""",
                },
            ],
            "best": "Pick the exact `device_type`, use the context manager, prefer `use_textfsm=True` (or TTP/Genie) over regexes on raw text, set `read_timeout` per command for slow ones, and enable `session_log` when debugging a new platform.",
        },
        {
            "title": "Config changes, saving, and many devices in parallel",
            "files": DEV,
            "local_only": NETMIKO,
            "concept": "`send_config_set([...])` enters configuration mode, sends each line, and exits; it returns the full transcript so you can check for errors. `save_config()` runs the platform's save command (`write memory` on IOS). Verify the change by reading it back. To touch many devices, run one connection per device in a `ThreadPoolExecutor`, collecting results (and errors) per device.",
            "why": "Configuring a test VLAN on every switch port of the bench, or setting the same WLAN on 20 controllers before a run, is routine. Doing it in parallel with per-device error reporting turns minutes into seconds.",
            "syntax": "out = conn.send_config_set([\"interface Vlan200\", \"description guest\"])\nconn.save_config()\n\nwith ThreadPoolExecutor(max_workers=10) as pool:\n    results = list(pool.map(configure, devices))",
            "code": """import time  ## Timing the parallel run
from concurrent.futures import ThreadPoolExecutor  ## One worker per device

from netmiko import ConnectHandler  ## Netmiko

from fake_device import start  ## Simulated devices

DEVICES = [{"device_type": "cisco_ios", "host": "127.0.0.1", "port": start(f"sw-{i}", i),  ## Three simulated switches
            "username": "admin", "password": "lab123"} for i in (1, 2, 3)]  ## Same credentials
CHANGE = ["interface Vlan600", "description lab-6g-clients"]  ## The config lines to push


def configure(dev):  ## Runs in a worker thread, one device each
    try:  ## Report errors per device instead of crashing the batch
        with ConnectHandler(**dev) as conn:  ## Own connection per thread
            host = conn.find_prompt().rstrip("#")  ## Device name from the prompt
            transcript = conn.send_config_set(CHANGE)  ## Enter config mode, send, exit
            if "% Invalid" in transcript:  ## Devices report errors in the output, not as exceptions
                return host, "rejected"  ## Don't save a bad change
            conn.save_config()  ## write memory
            tech = conn.send_command("show tech-support wireless", read_timeout=30)  ## Slow command (1 s each)
            ok = "description lab-6g-clients" in conn.send_command("show running-config")  ## Verify by reading back
            return host, f"configured={ok} tech_lines={len(tech.splitlines())}"  ## Summary
    except Exception as e:  ## Connection or timeout problems
        return dev["port"], f"error: {type(e).__name__}"  ## Keep going with the others


t0 = time.monotonic()  ## Start timer
with ThreadPoolExecutor(max_workers=len(DEVICES)) as pool:  ## All devices at once
    for host, result in pool.map(configure, DEVICES):  ## Results in input order
        print(host, result)  ## One line per device
print("parallel run under 3 s:", time.monotonic() - t0 < 3)  ## Three 1-second commands overlapped""",
            "under": "Each thread blocks on network I/O most of the time, so threads overlap nicely despite the GIL. `pool.map` returns results in the order of the input list, regardless of which device finished first. `send_config_set` uses `config_mode()` / `exit_config_mode()` around the lines and checks the prompt after each one.",
            "gotchas": [],
            "best": "Make changes idempotent (safe to re-run), check transcripts for error markers, save only after verifying, cap `max_workers` to what your devices and jump hosts tolerate, and collect per-device results into a report rather than stopping at the first failure. For large fleets, use Nornir (7.6) which builds this pattern in.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "files": DEV,
            "local_only": NETMIKO,
            "prompt": "Connect with Netmiko and print the AP names and states from `show ap summary` (raw text; parse it yourself by skipping header lines).",
            "solution": "Lines after the dashed separator are data rows; split on whitespace.",
            "solution_code": """from netmiko import ConnectHandler
from fake_device import start

dev = {"device_type": "cisco_ios", "host": "127.0.0.1", "port": start("wlc-1"), "username": "admin", "password": "lab123"}
with ConnectHandler(**dev) as conn:
    out = conn.send_command("show ap summary")
lines = out.splitlines()
first = next(i for i, line in enumerate(lines) if line.startswith("---")) + 1
for line in lines[first:]:
    parts = line.split()
    print(parts[0], parts[-1])""",
        },
        {
            "level": "Medium",
            "files": DEV,
            "local_only": NETMIKO,
            "prompt": "Use `use_textfsm=True` on `show ip interface brief` from three devices and build one table of interfaces that are up, keyed by device.",
            "solution": "Loop devices, parse, filter on status.",
            "solution_code": """from netmiko import ConnectHandler
from fake_device import start

table = {}
for i in (1, 2, 3):
    dev = {"device_type": "cisco_ios", "host": "127.0.0.1", "port": start(f"sw-{i}", i),
           "username": "admin", "password": "lab123"}
    with ConnectHandler(**dev) as conn:
        rows = conn.send_command("show ip interface brief", use_textfsm=True)
        table[f"sw-{i}"] = [(r["interface"], r["ip_address"]) for r in rows if r["status"] == "up"]
for name, ups in table.items():
    print(name, ups)""",
        },
        {
            "level": "Hard",
            "files": DEV,
            "local_only": NETMIKO,
            "prompt": "Make a config push idempotent: only send lines that aren't already in the running config, and report 'no change' on the second run.",
            "solution": "Read the running config, compute missing lines (keeping the parent `interface` line when any child is missing), push only those.",
            "solution_code": """from netmiko import ConnectHandler
from fake_device import start

WANT = {"interface Vlan700": ["description iot-clients"]}
dev = {"device_type": "cisco_ios", "host": "127.0.0.1", "port": start("sw-9", 9), "username": "admin", "password": "lab123"}


def push(conn):
    running = conn.send_command("show running-config")
    lines = []
    for parent, children in WANT.items():
        missing = [c for c in children if f" {c}" not in running]
        if parent not in running or missing:
            lines += [parent] + (missing or children)
    if not lines:
        return "no change"
    conn.send_config_set(lines)
    return f"pushed {lines}"


with ConnectHandler(**dev) as conn:
    print(push(conn))
    print(push(conn))""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What does Netmiko add on top of Paramiko?", "a": "Per-platform session preparation (paging off, terminal width), prompt detection, send_command/send_config_set that wait for prompts and strip echoes, config mode handling, save_config, file transfer helpers and parsing integrations (TextFSM, TTP, Genie).", "follow": "What's device_type 'autodetect'? (SSHDetect guesses the platform.)"},
        {"level": "Intermediate", "q": "How do you get structured data from show commands?", "a": "use_textfsm=True (ntc-templates), use_ttp with a template, or use_genie=True (Cisco pyATS parsers); or the device's API (NETCONF/RESTCONF) which returns structured data natively.", "follow": "What if there's no template? (Write a TextFSM/TTP template, or use the API.)"},
        {"level": "Intermediate", "q": "How would you push a change to 200 switches safely?", "a": "Dry run (diff) first, canary a few devices, then parallel workers with a bounded pool, per-device verification and save, error collection and a rollback plan. Log session transcripts.", "follow": "How do you make the change idempotent? (Compare desired vs running and only send missing lines.)"},
        {"level": "Advanced", "q": "send_command hangs on a command that asks a question. What do you do?", "a": "Use send_command with expect_string matching the question, then send the answer (or send_command_timing), or use the platform's non-interactive flag. Increase read_timeout for long operations.", "follow": "What's send_command_timing? (Reads based on idle time instead of the prompt.)"},
    ],
    "quiz": [
        {"q": "Structured output from Netmiko:", "options": ["parse=True", "use_textfsm=True", "json=True", "structured()"], "answer": 1, "why": "Via ntc-templates."},
        {"q": "Push several config lines:", "options": ["send_command", "send_config_set", "write_channel", "save_config"], "answer": 1, "why": "Handles config mode."},
        {"q": "Long command fails with ReadTimeout. Fix:", "options": ["sleep(60)", "read_timeout=120", "fast_cli=True", "Reconnect"], "answer": 1, "why": "Raise the per-command timeout."},
        {"q": "Device errors like '% Invalid input' are...", "options": ["Exceptions", "In the returned text", "Logged only", "Ignored"], "answer": 1, "why": "Check the transcript."},
        {"q": "pool.map returns results in...", "options": ["Completion order", "Input order", "Random order", "Reverse order"], "answer": 1, "why": "Input order."},
    ],
    "cards": [
        {"front": "Netmiko connect", "back": "`with ConnectHandler(device_type='cisco_ios', host=..., username=..., password=...) as c:`"},
        {"front": "Parsed show output", "back": "`c.send_command(cmd, use_textfsm=True)` → list of dicts"},
        {"front": "Config change", "back": "`c.send_config_set(lines)`; check for '% Invalid'; `c.save_config()`"},
        {"front": "Slow command", "back": "`send_command(cmd, read_timeout=120)`"},
        {"front": "Many devices", "back": "ThreadPoolExecutor, one connection per device, results per device"},
    ],
}
