"""Phase 7 content: modules 7.13-7.18 (pcap analysis, iperf3, Wi-Fi CLIs, LANforge, attenuators, RvR)."""

from net_support import needs, sim

TSHARK = needs("scapy") + " and the tshark command-line tool (apt install tshark / Wireshark installer)"
PYSHARK = needs("scapy pyshark") + " and tshark"
IPERF = "needs the iperf3 tool (apt install iperf3 / brew install iperf3); runs a real server and client on localhost"
TOOLS = "runs simulated wpa_cli/iw/hostapd_cli executables (see supporting files) through subprocess"
LANFORGE = needs("requests") + " and starts a simulated LANforge-style API on localhost"
ATTEN = needs("requests") + " and starts a simulated attenuator on localhost"
RVR = needs("requests matplotlib") + " and starts simulated lab equipment on localhost"
RVR_PYTEST = needs("pytest requests") + " and starts simulated lab equipment on localhost"

MAKE_DNS_PCAP = '''"""Writes dns.pcap: three DNS lookups from a Wi-Fi client, one of which fails (NXDOMAIN)."""
from scapy.all import DNS, DNSQR, DNSRR, IP, UDP, Ether, wrpcap

STA, DNS_SRV = "192.168.100.57", "10.0.0.53"
pkts = []
for i, name in enumerate(["ap-lab-07.lab.example", "ntp.lab.example", "nosuch.lab.example"]):
    q = Ether(src="02:00:00:00:01:00", dst="3c:84:6a:12:34:60") / IP(src=STA, dst=DNS_SRV) / UDP(sport=50000 + i, dport=53) / DNS(id=i, rd=1, qd=DNSQR(qname=name))
    q.time = 1760263400 + i * 0.1
    bad = name.startswith("nosuch")
    r = Ether(src="3c:84:6a:12:34:60", dst="02:00:00:00:01:00") / IP(src=DNS_SRV, dst=STA) / UDP(sport=53, dport=50000 + i) / DNS(
        id=i, qr=1, rd=1, ra=1, rcode=3 if bad else 0, qd=DNSQR(qname=name), an=None if bad else DNSRR(rrname=name, rdata=f"10.10.30.{7 + i}"))
    r.time = q.time + 0.004 * (i + 1)
    pkts += [q, r]
wrpcap("dns.pcap", pkts)
'''

M_7_13 = {
    "id": "7.13",
    "title": "pyshark & tshark for pcap Analysis",
    "hours": 2,
    "summary": "Use Wireshark's dissectors from Python: tshark field extraction and statistics via subprocess, and pyshark for object-style access to the same decoded fields.",
    "concepts": [
        {
            "title": "tshark: display filters, field extraction, statistics",
            "files": {"make_dns_pcap.py": MAKE_DNS_PCAP},
            "local_only": TSHARK,
            "concept": "tshark is Wireshark's command-line twin with all of its protocol dissectors. `-r file` reads a capture, `-Y \"filter\"` applies a display filter, and `-T fields -e field ...` prints only the fields you name, one line per packet, which is trivial to parse. `-q -z conv,udp` (or `io,stat`, `expert`) prints statistics tables. From Python, run it with `subprocess.run` and parse stdout.",
            "why": "Wireshark decodes thousands of protocols (802.11 with every amendment, EAPOL, DHCP options, QUIC...) better than anything you'd write yourself. tshark makes that decoding scriptable and fast enough for large captures.",
            "syntax": "tshark -r run.pcap -Y \"dns.flags.response==1\" -T fields -e dns.qry.name -e dns.flags.rcode -E separator=,\ntshark -r run.pcap -q -z conv,udp",
            "code": """import csv  ## Parse tshark's comma-separated output
import io  ## Treat stdout as a file
import runpy  ## Run the helper that writes the capture
import subprocess  ## Call tshark

runpy.run_path("make_dns_pcap.py")  ## Creates dns.pcap (see supporting files)

FIELDS = ["frame.time_relative", "ip.dst", "dns.qry.name", "dns.flags.rcode", "dns.a", "dns.time"]  ## Wireshark field names
cmd = ["tshark", "-r", "dns.pcap", "-Y", "dns.flags.response == 1", "-T", "fields",  ## Responses only, selected fields
       *[arg for f in FIELDS for arg in ("-e", f)], "-E", "separator=,", "-E", "header=y"]  ## Comma-separated with a header row
out = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True).stdout  ## stderr kept separate (tshark prints notices there)

for row in csv.DictReader(io.StringIO(out)):  ## One dict per response
    status = "NXDOMAIN" if row["dns.flags.rcode"] == "3" else row["dns.a"]  ## rcode 3 = name doesn't exist
    print(f"{row['dns.qry.name']:<24} {status:<11} {float(row['dns.time']) * 1000:.0f} ms")  ## dns.time = response latency

stats = subprocess.run(["tshark", "-r", "dns.pcap", "-q", "-z", "conv,udp"], capture_output=True, text=True, timeout=60, check=True).stdout  ## Conversation table
print("\\n".join(line for line in stats.splitlines() if "<->" in line))  ## Just the conversation rows""",
            "under": "Field names (`dns.qry.name`, `wlan.ssid`, `wlan_radio.signal_dbm`) are the same ones Wireshark shows in its status bar when you click a field; `tshark -G fields` lists them all. Display filters run after full dissection, so they can use any field; capture filters (`-f`, BPF syntax) only apply when capturing live. Fields can repeat in one packet (several answers), in which case tshark joins them with commas, which is why a different separator is sometimes safer.",
            "gotchas": [],
            "best": "Extract only the fields you need with `-T fields` (much faster than full JSON), use `-E header=y` and a separator that can't appear in values, keep stderr separate, pin the tshark version in CI images, and develop filters interactively in Wireshark first.",
        },
        {
            "title": "pyshark: dissected packets as Python objects",
            "files": {"make_dns_pcap.py": MAKE_DNS_PCAP},
            "local_only": PYSHARK,
            "concept": "pyshark runs tshark in the background and gives you packets whose layers and fields are attributes: `pkt.dns.qry_name`, `pkt.ip.src`, `pkt.highest_layer`. `FileCapture(path, display_filter=...)` iterates a file (`LiveCapture` sniffs an interface). Field names use underscores where Wireshark uses dots. Use `keep_packets=False` for big files and always `close()` the capture.",
            "why": "When you need several fields from different layers with some logic between them, pyshark reads more naturally than parsing tshark text, while still using Wireshark's decoding.",
            "syntax": "cap = pyshark.FileCapture(\"run.pcap\", display_filter=\"dns\", keep_packets=False)\nfor pkt in cap:\n    print(pkt.dns.qry_name)\ncap.close()",
            "code": """import runpy  ## Run the capture helper

import pyshark  ## pip install pyshark (needs tshark installed)

runpy.run_path("make_dns_pcap.py")  ## Creates dns.pcap

cap = pyshark.FileCapture("dns.pcap", display_filter="dns", keep_packets=False)  ## Filtered by tshark; packets not kept in memory
latency, failures = [], []  ## Results
try:  ## Make sure tshark is stopped even on errors
    for pkt in cap:  ## Each item is a dissected packet
        if pkt.dns.flags_response == "True":  ## Field values arrive as strings
            latency.append(float(pkt.dns.time) * 1000)  ## Response time in ms
            if pkt.dns.flags_rcode != "0":  ## Not NOERROR
                failures.append(pkt.dns.qry_name)  ## Remember which name failed
        print(pkt.number, pkt.highest_layer, pkt.ip.src, "->", pkt.ip.dst, pkt.dns.qry_name)  ## Per-packet summary
finally:  ## Always
    cap.close()  ## Stops the tshark process

print(f"max DNS latency {max(latency):.0f} ms; failed lookups: {failures}")  ## Test-style verdict""",
            "under": "pyshark launches tshark with `-T pdml` (XML) or `-T ek` and parses its output into objects, so it's convenient but slower than `-T fields` extraction. Boolean fields come through as the strings `\"True\"`/`\"False\"` or `\"1\"`/`\"0\"` depending on the field and tshark version, which is why comparing against strings (or normalising) matters.",
            "gotchas": [
                {
                    "title": "Accessing a layer the packet doesn't have",
                    "files": {"make_dns_pcap.py": MAKE_DNS_PCAP},
                    "local_only": PYSHARK,
                    "note": "Without a filter, a capture contains all sorts of packets, and `pkt.dns` raises AttributeError on the first one without DNS (here, the answer field `a` is missing on the NXDOMAIN response). Filter in tshark, or check with `hasattr`/`in` before using a layer or optional field.",
                    "wrong": """import runpy
import pyshark

runpy.run_path("make_dns_pcap.py")
cap = pyshark.FileCapture("dns.pcap", display_filter="dns.flags.response == 1")
try:
    for pkt in cap:
        print(pkt.dns.qry_name, pkt.dns.a)
except AttributeError:
    print("AttributeError: no answer field in the response for", pkt.dns.qry_name)
finally:
    cap.close()""",
                    "fixed": """import runpy
import pyshark

runpy.run_path("make_dns_pcap.py")
cap = pyshark.FileCapture("dns.pcap", display_filter="dns.flags.response == 1")
try:
    for pkt in cap:
        print(pkt.dns.qry_name, getattr(pkt.dns, "a", "no answer"))
finally:
    cap.close()""",
                },
            ],
            "best": "Push filtering into tshark (`display_filter`), use `getattr(layer, field, default)` for optional fields, close captures in `finally`, and switch to `tshark -T fields` when performance matters.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "files": {"make_dns_pcap.py": MAKE_DNS_PCAP},
            "local_only": TSHARK,
            "prompt": "Use tshark to count packets per protocol (highest layer) in dns.pcap.",
            "solution": "`-T fields -e _ws.col.Protocol` prints the Protocol column; count with Counter.",
            "solution_code": """import runpy
import subprocess
from collections import Counter

runpy.run_path("make_dns_pcap.py")
out = subprocess.run(["tshark", "-r", "dns.pcap", "-T", "fields", "-e", "_ws.col.Protocol"],
                     capture_output=True, text=True, check=True).stdout
print(Counter(out.split()))""",
        },
        {
            "level": "Medium",
            "local_only": TSHARK,
            "prompt": "Create a beacon capture with Scapy and use tshark to extract SSID, channel and signal for each beacon (fields `wlan.ssid`, `wlan.ds.current_channel`, `wlan_radio.signal_dbm`).",
            "solution": "tshark understands Radiotap and 802.11 natively. Recent tshark versions print `wlan.ssid` in fields mode as hex bytes (an SSID isn't guaranteed to be text), so decode it yourself.",
            "solution_code": """import subprocess
from scapy.all import Dot11, Dot11Beacon, Dot11Elt, RadioTap, wrpcap

frames = []
for bssid, ssid, ch, freq, rssi in [("3c:84:6a:12:34:56", b"lab-5g", 36, 5180, -49), ("9e:11:22:33:44:55", b"guest", 149, 5745, -78)]:
    frames.append(RadioTap(present="Channel+dBm_AntSignal", ChannelFrequency=freq, ChannelFlags="OFDM+5GHz", dBm_AntSignal=rssi)
                  / Dot11(type=0, subtype=8, addr1="ff:ff:ff:ff:ff:ff", addr2=bssid, addr3=bssid)
                  / Dot11Beacon(cap="ESS") / Dot11Elt(ID="SSID", info=ssid) / Dot11Elt(ID="DSset", info=bytes([ch])))
wrpcap("beacons.pcap", frames)
out = subprocess.run(["tshark", "-r", "beacons.pcap", "-T", "fields", "-e", "wlan.bssid", "-e", "wlan.ssid",
                      "-e", "wlan.ds.current_channel", "-e", "wlan_radio.signal_dbm"],
                     capture_output=True, text=True, check=True).stdout
for line in out.splitlines():
    bssid, ssid_hex, channel, signal = line.split("\\t")
    print(bssid, bytes.fromhex(ssid_hex).decode(), "ch" + channel, signal, "dBm")""",
        },
        {
            "level": "Hard",
            "files": {"make_dns_pcap.py": MAKE_DNS_PCAP},
            "local_only": TSHARK,
            "prompt": "Get tshark's output as JSON (`-T json`) for DNS responses and extract query name and rcode from the nested structure.",
            "solution": "In `-T json`, each packet has `_source.layers`, and each layer is a dict of field name → value with nested trees for some fields. `-J dns` keeps only the DNS layer *including* its subtrees (lower-case `-j` keeps top-level fields only). JSON is complete but verbose: prefer `-T fields` when you can.",
            "solution_code": """import json
import runpy
import subprocess

runpy.run_path("make_dns_pcap.py")
out = subprocess.run(["tshark", "-r", "dns.pcap", "-Y", "dns.flags.response == 1", "-T", "json", "-J", "dns"],
                     capture_output=True, text=True, check=True).stdout
for pkt in json.loads(out):
    dns = pkt["_source"]["layers"]["dns"]
    query = next(iter(dns["Queries"].values()))
    print(query["dns.qry.name"], dns["dns.flags_tree"]["dns.flags.rcode"])""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "Scapy vs tshark/pyshark for analysing captures?", "a": "Scapy: pure Python, craft and edit packets, fine for moderate files and custom logic. tshark/pyshark: Wireshark's full dissectors (far broader and more accurate protocol support, especially 802.11), faster on large files with -T fields; pyshark adds object access at a speed cost.", "follow": "How would you process a 5 GB capture? (tshark with a display filter and -T fields, or editcap to split first.)"},
        {"level": "Intermediate", "q": "Display filter vs capture filter?", "a": "Capture filters (BPF, -f) decide what's recorded during live capture and can't see decoded fields. Display filters (-Y) run after dissection on any field (e.g. wlan.fc.type_subtype == 0x08).", "follow": "Give a filter for EAPOL frames. (eapol)"},
        {"level": "Advanced", "q": "How would you verify roaming performance automatically from sniffer captures?", "a": "Merge captures from sniffers on both channels (mergecap), extract the client's auth/reassoc/EAPOL/FT frames and data frames with tshark fields, compute the gap from last data on the old AP to first data on the new AP, and assert against the KPI per roam.", "follow": "How do you keep sniffer clocks aligned? (Same host/NTP/PTP, or capture both channels with one multi-radio sniffer.)"},
    ],
    "quiz": [
        {"q": "Print only chosen fields with tshark:", "options": ["-V", "-T fields -e ...", "-x", "-q"], "answer": 1, "why": "Field extraction mode."},
        {"q": "Apply a display filter in tshark:", "options": ["-f", "-Y", "-R only", "-F"], "answer": 1, "why": "-Y (single pass)."},
        {"q": "pyshark field for Wireshark's dns.qry.name:", "options": ["pkt.dns['qry.name']", "pkt.dns.qry_name", "pkt.qry_name", "pkt.dns.qry.name"], "answer": 1, "why": "Dots become underscores."},
        {"q": "Stop pyshark's tshark process:", "options": ["del cap", "cap.close()", "cap.stop()", "Nothing needed"], "answer": 1, "why": "close() it."},
        {"q": "List all tshark field names:", "options": ["tshark -L", "tshark -G fields", "tshark --fields", "tshark -D"], "answer": 1, "why": "-G fields."},
    ],
    "cards": [
        {"front": "tshark field extraction", "back": "`tshark -r f.pcap -Y filter -T fields -e a -e b -E separator=,`"},
        {"front": "tshark statistics", "back": "`tshark -r f.pcap -q -z conv,ip` / `io,stat,1` / `expert`"},
        {"front": "pyshark file", "back": "`cap = pyshark.FileCapture(p, display_filter=..., keep_packets=False)`; close()"},
        {"front": "Optional pyshark field", "back": "`getattr(pkt.dns, 'a', None)`"},
        {"front": "Wi-Fi signal field", "back": "`wlan_radio.signal_dbm` (Radiotap-derived)"},
    ],
}


M_7_14 = {
    "id": "7.14",
    "title": "iperf3 Automation",
    "hours": 1.5,
    "summary": "Drive iperf3 from Python: start a server, run TCP and UDP clients with JSON output, extract throughput, retransmits, jitter and loss, and handle errors properly.",
    "concepts": [
        {
            "title": "TCP throughput with JSON output",
            "local_only": IPERF,
            "concept": "`iperf3 -s` runs a server (`-1` = handle one test then exit, `-p` = port). `iperf3 -c HOST -t SECONDS -J` runs a client and prints a JSON report: `start` (connection info), `intervals` (per-second stats) and `end` (totals). Throughput is `end.sum_received.bits_per_second` (what actually arrived), TCP retransmissions are `end.sum_sent.retransmits`. Options you'll use: `-P` parallel streams, `-R` reverse direction (server sends), `-w` window size, `-O` omit the first seconds (TCP ramp-up).",
            "why": "iperf3 is the standard traffic generator for Wi-Fi throughput, rate-vs-range and regression testing. Wrapping it in Python means every measurement is parsed, checked against KPIs and stored, not copied from a terminal.",
            "syntax": "iperf3 -s -1 -p 5201\niperf3 -c 192.168.100.1 -p 5201 -t 10 -O 2 -P 4 -R -J",
            "code": """import json  ## iperf3 -J output
import subprocess  ## Run the tool
import time  ## Give the server a moment to start

PORT = "5211"  ## Pick a port per test bench to avoid clashes
server = subprocess.Popen(["iperf3", "-s", "-1", "-p", PORT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  ## One-shot server (on the far end in a real setup)
time.sleep(0.5)  ## Server needs a moment to listen

proc = subprocess.run(["iperf3", "-c", "127.0.0.1", "-p", PORT, "-t", "2", "-O", "1", "-J"],  ## 2 s test, first second omitted from totals
                      capture_output=True, text=True, timeout=30)  ## Never without a timeout
result = json.loads(proc.stdout)  ## The whole report
server.wait(timeout=10)  ## -1 makes the server exit after one test

print(sorted(result))  ## Top-level sections
end = result["end"]  ## Totals
mbps = end["sum_received"]["bits_per_second"] / 1e6  ## What actually arrived at the receiver
print("protocol:", result["start"]["test_start"]["protocol"], "| duration:", result["start"]["test_start"]["duration"], "s")  ## Test parameters echoed back
print("received over 1000 Mbps:", mbps > 1000)  ## Loopback is fast; a Wi-Fi link would be checked against its KPI
print("retransmits is an int:", isinstance(end["sum_sent"].get("retransmits"), int))  ## TCP retransmissions (Linux senders only)
print("intervals reported:", len(result["intervals"]))  ## Per-second samples (omitted seconds excluded)""",
            "under": "With `-J` iperf3 buffers everything and prints one JSON document at the end (`--json-stream` in newer versions emits one object per interval). `sum_sent` is measured at the sender (bytes written to the socket), `sum_received` at the receiver, which is the number to report. Retransmit counts come from the Linux kernel's TCP_INFO, so they're missing when the sender is macOS or Windows. Loopback numbers here only show the mechanics: they say nothing about Wi-Fi.",
            "gotchas": [
                {
                    "title": "Not checking for iperf3 errors",
                    "local_only": IPERF,
                    "note": "When the server isn't reachable (or is busy with another test), iperf3 still prints JSON, but with an `error` key and no `end.sum_received`, and exits with status 1. Code that goes straight for the numbers crashes with a confusing KeyError. Check the return code and the error field first.",
                    "wrong": """import json
import subprocess

proc = subprocess.run(["iperf3", "-c", "127.0.0.1", "-p", "5299", "-t", "1", "-J"], capture_output=True, text=True, timeout=30)
result = json.loads(proc.stdout)
print(result["end"]["sum_received"]["bits_per_second"])""",
                    "fixed": """import json
import subprocess

proc = subprocess.run(["iperf3", "-c", "127.0.0.1", "-p", "5299", "-t", "1", "-J"], capture_output=True, text=True, timeout=30)
result = json.loads(proc.stdout)
if proc.returncode != 0 or "error" in result:
    print("iperf3 failed:", result.get("error"))
else:
    print(result["end"]["sum_received"]["bits_per_second"])""",
                },
            ],
            "best": "Run the server on the wired side and the client on the Wi-Fi station (or reverse with `-R` for downlink), use `-O` to skip TCP slow start, run several iterations and report median and min, record the full JSON as an artifact, and always check `error`.",
        },
        {
            "title": "UDP: offered load, jitter and loss",
            "local_only": IPERF,
            "concept": "With `-u -b RATE` iperf3 sends UDP at a fixed offered rate. The receiver reports **jitter** (variation in packet delay, ms) and **loss** (`lost_packets`, `lost_percent`) in `end.sum`. UDP tests answer different questions from TCP: can the link carry 50 Mbps of video with under 1% loss and under 30 ms jitter? Use `-l` for datagram size and `--get-server-output` when you need the server's view.",
            "why": "Voice, video and real-time applications care about loss and jitter, not just peak throughput. UDP tests at fixed rates are the standard way to measure them, and to find the maximum rate a link sustains with acceptable loss.",
            "syntax": "iperf3 -c host -u -b 50M -l 1200 -t 10 -J",
            "code": """import json  ## Parse the report
import statistics  ## Median of intervals
import subprocess  ## Run the tool
import time  ## Server start-up

PORT = "5212"  ## Separate port from the TCP test


def iperf_udp(rate, seconds=2):  ## One UDP run against a fresh one-shot server
    srv = subprocess.Popen(["iperf3", "-s", "-1", "-p", PORT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  ## Server
    time.sleep(0.5)  ## Let it listen
    try:  ## Always reap the server process
        proc = subprocess.run(["iperf3", "-c", "127.0.0.1", "-p", PORT, "-u", "-b", rate, "-l", "1200", "-t", str(seconds), "-J"],  ## Fixed offered load
                              capture_output=True, text=True, timeout=30)  ## Bounded
        data = json.loads(proc.stdout)  ## Report
        if "error" in data:  ## Check before using numbers
            raise RuntimeError(data["error"])  ## Clear failure
        return data  ## Full report
    finally:  ## Even on errors
        srv.wait(timeout=10)  ## One-shot server exits after the test


report = iperf_udp("50M")  ## 50 Mbps offered
s = report["end"]["sum"]  ## UDP totals live in end.sum
print(f"offered 50 Mbps, delivered ~{round(s['bits_per_second'] / 1e6)} Mbps")  ## Close to the offered rate on a clean link
print("loss under 1%:", s["lost_percent"] < 1, "| jitter under 5 ms:", s["jitter_ms"] < 5)  ## The KPIs for real-time traffic
per_second = [i["sum"]["bits_per_second"] / 1e6 for i in report["intervals"]]  ## Interval series
print("intervals:", len(per_second), "| median within 10% of offered:", abs(statistics.median(per_second) - 50) < 5)  ## Stability check""",
            "under": "iperf3's UDP sender paces packets to hit the target bitrate; each datagram carries a sequence number and send timestamp, and the receiver counts gaps (loss) and computes jitter as the smoothed mean deviation of transit-time differences (RFC 3550). On a congested Wi-Fi link you'd see loss climb once the offered rate exceeds capacity.",
            "gotchas": [],
            "best": "Choose rates around the expected capacity and step up to find the knee, use realistic datagram sizes (`-l 1200` avoids IP fragmentation), report loss and jitter with the offered rate, and run UDP and TCP separately since they answer different questions.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Parse a saved iperf3 TCP JSON report (trimmed) and print received Mbps, retransmits and the minimum interval throughput.",
            "solution": "Navigate the nested dicts; intervals live under `intervals[i].sum`.",
            "solution_code": """import json

REPORT = '''{"start": {"test_start": {"protocol": "TCP", "duration": 3}},
 "intervals": [{"sum": {"bits_per_second": 941.2e6}}, {"sum": {"bits_per_second": 602.5e6}}, {"sum": {"bits_per_second": 938.0e6}}],
 "end": {"sum_sent": {"bits_per_second": 830.1e6, "retransmits": 37}, "sum_received": {"bits_per_second": 827.4e6}}}'''
r = json.loads(REPORT)
print(f"{r['end']['sum_received']['bits_per_second'] / 1e6:.1f} Mbps, retransmits {r['end']['sum_sent']['retransmits']}")
print(f"min interval {min(i['sum']['bits_per_second'] for i in r['intervals']) / 1e6:.1f} Mbps")""",
        },
        {
            "level": "Medium",
            "prompt": "Turn a list of iperf3 results (Mbps per iteration) into a verdict: pass if the median is at least the KPI and no single run is below 80% of it.",
            "solution": "Median protects against one outlier; the floor catches a severe dip.",
            "solution_code": """import statistics


def verdict(runs, kpi):
    med = statistics.median(runs)
    worst = min(runs)
    ok = med >= kpi and worst >= 0.8 * kpi
    return ok, round(med, 1), worst


print(verdict([912.4, 905.1, 921.7, 899.0, 910.3], kpi=850))
print(verdict([912.4, 905.1, 610.0, 899.0, 910.3], kpi=850))""",
        },
        {
            "level": "Hard",
            "local_only": IPERF,
            "prompt": "Run a 2-stream TCP test (`-P 2`) in reverse mode (`-R`) and print the number of streams in the report and whether the per-stream throughputs add up to the total (within 1%).",
            "solution": "Each stream appears in `end.streams`; `-R` makes the server send. Summing the receiver side should match `sum_received`.",
            "solution_code": """import json
import subprocess
import time

srv = subprocess.Popen(["iperf3", "-s", "-1", "-p", "5213"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.5)
proc = subprocess.run(["iperf3", "-c", "127.0.0.1", "-p", "5213", "-t", "1", "-P", "2", "-R", "-J"], capture_output=True, text=True, timeout=30)
srv.wait(timeout=10)
r = json.loads(proc.stdout)
streams = r["end"]["streams"]
total = r["end"]["sum_received"]["bits_per_second"]
parts = sum(s["receiver"]["bits_per_second"] for s in streams)
print("reverse:", bool(r["start"]["test_start"]["reverse"]), "| streams:", len(streams), "| adds up:", abs(parts - total) / total < 0.01)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "How do you measure downlink vs uplink throughput on a Wi-Fi client with iperf3?", "a": "Run the server on the wired side. From the client, a normal test measures uplink (client sends); -R measures downlink (server sends). Or swap where the server runs.", "follow": "What's --bidir? (Both directions at once.)"},
        {"level": "Intermediate", "q": "sum_sent vs sum_received?", "a": "sum_sent counts bytes the sender wrote; sum_received counts what the receiver got, which is the meaningful throughput. For TCP they're close; for UDP the difference is loss.", "follow": "Why use -O? (To exclude TCP slow start from the average.)"},
        {"level": "Intermediate", "q": "Why does TCP throughput on Wi-Fi vary run to run, and how do you report it?", "a": "Contention, interference, rate adaptation, retries and host CPU/scheduling. Run multiple iterations, report median and min (or percentiles), keep the environment controlled (shielded box, fixed attenuation), and store raw JSON.", "follow": "What would make TCP numbers misleading? (Too small windows, single stream on high-BDP links, CPU-bound clients.)"},
    ],
    "quiz": [
        {"q": "Machine-readable iperf3 output:", "options": ["-V", "-J", "-x", "--csv"], "answer": 1, "why": "JSON report."},
        {"q": "Measure the server→client direction:", "options": ["-u", "-R", "-P", "-O"], "answer": 1, "why": "Reverse mode."},
        {"q": "UDP loss and jitter are in...", "options": ["end.sum_sent", "end.sum", "start", "intervals[0]"], "answer": 1, "why": "UDP totals in end.sum."},
        {"q": "iperf3 failure in JSON mode shows up as...", "options": ["Empty output", "An 'error' key and exit code 1", "A Python exception", "Zero throughput"], "answer": 1, "why": "Check it."},
        {"q": "Skip the first 2 s of TCP ramp-up:", "options": ["-t 2", "-O 2", "-i 2", "-w 2"], "answer": 1, "why": "Omit."},
    ],
    "cards": [
        {"front": "One-shot server", "back": "`iperf3 -s -1 -p 5201`"},
        {"front": "TCP client JSON", "back": "`iperf3 -c host -t 10 -O 2 -J` → end.sum_received.bits_per_second"},
        {"front": "UDP at fixed rate", "back": "`iperf3 -c host -u -b 50M -l 1200 -J` → end.sum.lost_percent, jitter_ms"},
        {"front": "Downlink test", "back": "`-R` (server sends)"},
        {"front": "Error check", "back": "`if proc.returncode or 'error' in result:`"},
    ],
}


WIFI_TOOLS = sim("wpa_cli", "iw", "hostapd_cli")

M_7_15 = {
    "id": "7.15",
    "title": "wpa_cli, hostapd_cli & iw",
    "hours": 2,
    "summary": "Control and query Linux Wi-Fi from Python: wrap wpa_cli (station), hostapd_cli (AP) and iw (driver/nl80211) with subprocess, and parse their key=value, tabular and indented outputs.",
    "concepts": [
        {
            "title": "Wrapping wpa_cli",
            "files": WIFI_TOOLS,
            "local_only": TOOLS,
            "concept": "`wpa_cli -i wlan0 <command>` talks to wpa_supplicant, the station-side daemon. `status` and `signal_poll` print `key=value` lines (easy to turn into a dict); `scan_results` prints a tab-separated table; control commands (`reassociate`, `select_network 0`, `disconnect`) print `OK` or `FAIL`. A small wrapper class with one method per command, a timeout and parsing gives your tests a clean API. The tools used here are simulators placed on PATH, with the exact output format of the real ones.",
            "why": "Linux test clients (laptops, Raspberry Pis, LANforge stations) are controlled through wpa_supplicant. Connect, roam, check RSSI and link speed, verify WPA3 negotiated: all wpa_cli commands.",
            "syntax": "subprocess.run([\"wpa_cli\", \"-i\", iface, \"status\"], capture_output=True, text=True, timeout=10, check=True)\ndict(line.split(\"=\", 1) for line in out.splitlines() if \"=\" in line)",
            "code": """import subprocess  ## Run the CLI tools


class WpaCli:  ## Thin, typed wrapper around one interface
    def __init__(self, iface="wlan0", timeout=10):  ## One instance per test client interface
        self.iface, self.timeout = iface, timeout  ## Settings

    def _run(self, *args):  ## Every call goes through here
        proc = subprocess.run(["wpa_cli", "-i", self.iface, *args], capture_output=True, text=True, timeout=self.timeout)  ## Never hang
        if proc.returncode != 0:  ## Tool-level failure (e.g. unknown command, no daemon)
            raise RuntimeError(f"wpa_cli {' '.join(args)}: {proc.stdout.strip() or proc.stderr.strip()}")  ## Include its message
        return proc.stdout  ## Raw text

    def _kv(self, *args):  ## key=value output -> dict
        return dict(line.split("=", 1) for line in self._run(*args).splitlines() if "=" in line)  ## Split on the first '=' only

    def status(self):  ## Association state
        return self._kv("status")  ## wpa_state, ssid, bssid, freq, key_mgmt...

    def signal(self):  ## Current link quality
        s = self._kv("signal_poll")  ## RSSI, LINKSPEED, NOISE...
        return {"rssi": int(s["RSSI"]), "link_mbps": int(s["LINKSPEED"]), "snr": int(s["RSSI"]) - int(s["NOISE"]), "width": s["WIDTH"]}  ## Typed values

    def scan_results(self):  ## Tab-separated table after a header line
        rows = [line.split("\\t") for line in self._run("scan_results").splitlines()[1:]]  ## Skip the header
        return [{"bssid": r[0], "freq": int(r[1]), "signal": int(r[2]), "flags": r[3], "ssid": r[4] if len(r) > 4 else ""} for r in rows]  ## Hidden SSIDs are empty


sta = WpaCli("wlan0")  ## The test client
st = sta.status()  ## Is it connected?
print(st["wpa_state"], st["ssid"], st["bssid"], st["freq"], st["key_mgmt"])  ## COMPLETED, WPA3 (SAE) on 6 GHz
print(sta.signal())  ## Typed link metrics
best = max((n for n in sta.scan_results() if n["ssid"]), key=lambda n: n["signal"])  ## Strongest visible named network
print("strongest:", best["ssid"], best["signal"], "dBm |", "WPA3" if "SAE" in best["flags"] else "no WPA3")  ## Security from flags""",
            "under": "wpa_cli connects to wpa_supplicant's control socket (`/var/run/wpa_supplicant/wlan0`) and prints the daemon's reply verbatim, which is why outputs are simple text. For long-running monitoring, wpa_supplicant also emits events (`CTRL-EVENT-CONNECTED`, `CTRL-EVENT-DISCONNECTED reason=...`) that `wpa_cli -a script` or the control socket can deliver. `split(\"=\", 1)` matters because values like SSIDs can contain '='.",
            "gotchas": [
                {
                    "title": "Trusting the exit code of a control command",
                    "files": WIFI_TOOLS,
                    "local_only": TOOLS,
                    "note": "wpa_cli reports most command failures as the text `FAIL` with exit status 0. A wrapper that only checks the return code will think `select_network 9` (a network that doesn't exist) succeeded. Check for `OK`.",
                    "wrong": """import subprocess

proc = subprocess.run(["wpa_cli", "-i", "wlan0", "select_network", "9"], capture_output=True, text=True, timeout=10)
print("selected!" if proc.returncode == 0 else "failed")""",
                    "fixed": """import subprocess

proc = subprocess.run(["wpa_cli", "-i", "wlan0", "select_network", "9"], capture_output=True, text=True, timeout=10)
reply = proc.stdout.strip()
print("selected!" if proc.returncode == 0 and reply == "OK" else f"failed: {reply}")""",
                },
            ],
            "best": "One wrapper class per tool with typed return values, timeouts on every call, `OK`/`FAIL` checking for control commands, parsing in one place with tests built from captured real output, and the interface name always explicit (`-i`).",
        },
        {
            "title": "iw and hostapd_cli: link details and the AP's view",
            "files": WIFI_TOOLS,
            "local_only": TOOLS,
            "concept": "`iw dev wlan0 link` shows the station's current association (SSID, frequency, signal, TX/RX bitrate with MCS, NSS and channel width); `iw dev wlan0 station dump` adds counters like retries. Output is indented `key: value` text, parsed with regexes. On the AP side, `hostapd_cli -i wlan0 status` gives radio state (channel, width, SSID) and `all_sta` lists each associated client's MAC followed by its `key=value` details.",
            "why": "Rate-vs-range and interoperability tests need the negotiated PHY rate, MCS and NSS on both ends, not just throughput: \"the client connected at 2 spatial streams instead of 4\" is a finding iperf3 alone can't give you.",
            "syntax": "iw dev wlan0 link\niw dev wlan0 station dump\nhostapd_cli -i wlan0 status\nhostapd_cli -i wlan0 all_sta",
            "code": """import re  ## Pattern-based parsing
import subprocess  ## Run the tools


def run(*cmd):  ## Small helper: run, check, return stdout
    return subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True).stdout  ## check=True raises on failure


link = run("iw", "dev", "wlan0", "link")  ## Station view of the current link
if link.startswith("Not connected"):  ## iw's way of saying so
    raise SystemExit("not associated")  ## Stop early
rate = re.search(r"tx bitrate: ([\\d.]+) MBit/s (\\d+)MHz HE-MCS (\\d+) HE-NSS (\\d+)", link)  ## HE (Wi-Fi 6/6E) rate line
print("bssid:", re.search(r"Connected to (\\S+)", link)[1], "| ssid:", re.search(r"SSID: (.+)", link)[1])  ## Who we're connected to
print("signal:", int(re.search(r"signal: (-?\\d+) dBm", link)[1]), "dBm")  ## RSSI
print("tx: {} Mbps, {} MHz, MCS {}, NSS {}".format(*rate.groups()))  ## Negotiated PHY parameters

status = dict(line.split("=", 1) for line in run("hostapd_cli", "-i", "wlan0", "status").splitlines() if "=" in line)  ## AP radio state
print("AP:", status["ssid[0]"], "channel", status["channel"], "| clients:", status["num_sta[0]"])  ## Per-BSS keys are indexed [0], [1]...

stations, current = {}, None  ## all_sta: MAC line, then that station's key=value lines
for line in run("hostapd_cli", "-i", "wlan0", "all_sta").splitlines():  ## Walk the output
    if re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}", line):  ## A new station starts with its MAC
        current = stations.setdefault(line, {})  ## New dict for it
    elif "=" in line and current is not None:  ## A property of the current station
        key, value = line.split("=", 1)  ## Split once
        current[key] = value  ## Store
for mac, info in stations.items():  ## The AP's view of each client
    print(mac, "signal", info["signal"], "| rx", int(info["rx_rate_info"].split()[0]) / 10, "Mbps")  ## Rates are in 100 kbps units""",
            "under": "iw talks to the kernel through nl80211 (netlink), so its output reflects the driver's current state; the text format is meant for humans and can change between versions, which is why regexes should be anchored on labels, not columns. hostapd_cli, like wpa_cli, talks to the daemon's control socket. In hostapd's `rx_rate_info` the first number is in units of 100 kbps.",
            "gotchas": [],
            "best": "Parse by labels with tolerant regexes, keep captured outputs from each driver/firmware as test fixtures, collect both station and AP views for every throughput point, and consider `iw ... -j`-style JSON or nl80211 libraries (pyroute2) where available.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Parse this `wpa_cli status` output into a dict and print whether the client is connected with WPA3 on 6 GHz (freq between 5925 and 7125).",
            "solution": "Split each line on the first '='; check wpa_state, key_mgmt and freq.",
            "solution_code": """STATUS = '''bssid=3c:84:6a:12:34:60
freq=6135
ssid=lab-6g
key_mgmt=SAE
wpa_state=COMPLETED'''
s = dict(line.split("=", 1) for line in STATUS.splitlines())
print(s["wpa_state"] == "COMPLETED" and s["key_mgmt"].startswith("SAE") and 5925 <= int(s["freq"]) <= 7125)""",
        },
        {
            "level": "Medium",
            "prompt": "Convert a frequency in MHz to (band, channel) for 2.4, 5 and 6 GHz, and test it on 2437, 5180, 5745 and 5975.",
            "solution": "2.4 GHz: (f - 2407) / 5 (2484 is ch 14); 5 GHz: (f - 5000) / 5; 6 GHz: (f - 5950) / 5.",
            "solution_code": """def freq_to_channel(mhz):
    if mhz == 2484:
        return "2G", 14
    if 2412 <= mhz <= 2472:
        return "2G", (mhz - 2407) // 5
    if 5150 <= mhz <= 5895:
        return "5G", (mhz - 5000) // 5
    if 5955 <= mhz <= 7115:
        return "6G", (mhz - 5950) // 5
    raise ValueError(f"{mhz} MHz is not a Wi-Fi channel center")


for f in (2437, 5180, 5745, 5975, 6135):
    print(f, freq_to_channel(f))""",
        },
        {
            "level": "Hard",
            "files": WIFI_TOOLS,
            "local_only": TOOLS,
            "prompt": "Write `snapshot()` that collects station and AP views into one record (RSSI on both sides, TX/RX rates, MCS, NSS, width) for logging at each test point.",
            "solution": "Combine wpa_cli signal_poll, iw link and hostapd_cli all_sta (matching the station's MAC) into a flat dict.",
            "solution_code": """import re
import subprocess


def run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True).stdout


def kv(text):
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


def snapshot(sta_mac="02:00:00:00:01:00"):
    sig = kv(run("wpa_cli", "-i", "wlan0", "signal_poll"))
    link = run("iw", "dev", "wlan0", "link")
    tx = re.search(r"tx bitrate: ([\\d.]+) MBit/s (\\d+)MHz HE-MCS (\\d+) HE-NSS (\\d+)", link).groups()
    ap_view = run("hostapd_cli", "-i", "wlan0", "all_sta").split(sta_mac, 1)[1]
    return {"sta_rssi": int(sig["RSSI"]), "ap_rssi": int(kv(ap_view)["signal"]), "tx_mbps": float(tx[0]),
            "width_mhz": int(tx[1]), "mcs": int(tx[2]), "nss": int(tx[3])}


print(snapshot())""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "wpa_cli vs iw vs hostapd_cli?", "a": "wpa_cli controls/queries wpa_supplicant (station: connect, roam, status, signal_poll). hostapd_cli does the same for hostapd (AP: status, stations, deauth). iw talks to the kernel via nl80211 for driver-level info and config (link, station dump, scan, set channel, monitor mode).", "follow": "Which shows the negotiated MCS? (iw link/station dump; hostapd's rx/tx_rate_info.)"},
        {"level": "Intermediate", "q": "How do you make wrappers around CLI tools robust?", "a": "Timeouts, explicit interface arguments, checking both exit codes and textual OK/FAIL replies, label-anchored parsing, typed return values, and fixtures from each tool version to catch format changes.", "follow": "When would you use the control socket directly? (Event monitoring and lower overhead.)"},
        {"level": "Advanced", "q": "A client connects at NSS 1 instead of NSS 2. How do you investigate?", "a": "Compare station and AP views (iw station dump, hostapd all_sta), check the capabilities in association request/response (HE capabilities IE) in a capture, antenna configuration and SMPS power save, and chain mask settings on both sides.", "follow": "What's SMPS? (Spatial multiplexing power save: a client turns off chains to save power.)"},
    ],
    "quiz": [
        {"q": "wpa_cli command for RSSI and link speed:", "options": ["status", "signal_poll", "scan", "bss"], "answer": 1, "why": "signal_poll."},
        {"q": "wpa_cli control command failure is usually...", "options": ["Exit code 1", "The text FAIL with exit 0", "An exception", "No output"], "answer": 1, "why": "Check the reply."},
        {"q": "Frequency 6135 MHz is...", "options": ["5 GHz ch 227", "6 GHz ch 37", "6 GHz ch 5", "2.4 GHz ch 13"], "answer": 1, "why": "(6135 - 5950) / 5 = 37."},
        {"q": "Station counters including retries:", "options": ["iw dev wlan0 link", "iw dev wlan0 station dump", "iw list", "iw reg get"], "answer": 1, "why": "station dump."},
        {"q": "Split 'ssid=a=b' safely:", "options": ["split('=')", "split('=', 1)", "partition only", "rsplit('=')"], "answer": 1, "why": "Values can contain '='."},
    ],
    "cards": [
        {"front": "Station status", "back": "`wpa_cli -i wlan0 status` / `signal_poll` (key=value)"},
        {"front": "Scan table", "back": "`wpa_cli -i wlan0 scan_results` (tab-separated, header line)"},
        {"front": "Negotiated rate", "back": "`iw dev wlan0 link` → tx bitrate, MHz, MCS, NSS"},
        {"front": "AP's clients", "back": "`hostapd_cli -i wlan0 all_sta`"},
        {"front": "6 GHz channel", "back": "`(freq - 5950) // 5`"},
    ],
}


LF = sim("fake_lanforge.py")

M_7_16 = {
    "id": "7.16",
    "title": "LANforge API Scripting",
    "hours": 2,
    "summary": "Drive a traffic-generation system through its JSON API: create virtual stations, bring them up and wait for IP, create and run traffic, read rates, and always clean up.",
    "concepts": [
        {
            "title": "Stations: create, bring up, wait for association",
            "files": LF,
            "local_only": LANFORGE,
            "concept": "Candela LANforge exposes a JSON API (default port 8080): GET endpoints like `/port/1/1/sta0000` return object state, and POST commands under `/cli-json/` (`add_sta`, `set_port`, `add_cx`, `set_cx_state`) change it. A typical flow: create a virtual station with SSID and security, admin-up the port, then **poll** until it has an IP and a BSSID. The simulator here implements a small subset of that API with the same shape.",
            "why": "One LANforge chassis can emulate hundreds of Wi-Fi clients, and every serious Wi-Fi lab automates it: capacity tests, roaming with 50 stations, mixed-band throughput. The polling-with-deadline pattern is the same for any lab equipment API.",
            "syntax": "post(\"/cli-json/add_sta\", {\"resource\": 1, \"radio\": \"wiphy0\", \"sta_name\": \"sta0000\", \"ssid\": \"lab-6g\", ...})\nget(\"/port/1/1/sta0000\")[\"interface\"][\"ip\"]",
            "code": """import time  ## Polling deadline

import requests  ## pip install requests

from fake_lanforge import start  ## Simulated LANforge-style API (see supporting files)

BASE = start()  ## http://lanforge:8080 on a real bench
s = requests.Session()  ## Reused connection


def post(cmd, body):  ## Send a CLI-JSON command
    r = s.post(f"{BASE}/cli-json/{cmd}", json=body, timeout=10)  ## Commands are POSTs
    r.raise_for_status()  ## HTTP-level errors
    return r.json()  ## Small status object


def port(name):  ## Read one port's state
    r = s.get(f"{BASE}/port/1/1/{name}", timeout=10)  ## shelf 1, resource 1
    r.raise_for_status()  ## 404 if it doesn't exist
    return r.json()["interface"]  ## The interesting part


def wait_for(check, timeout=10.0, interval=0.1):  ## Poll until check() returns something truthy
    deadline = time.monotonic() + timeout  ## Monotonic deadline
    while time.monotonic() < deadline:  ## Keep trying
        if result := check():  ## Done?
            return result  ## Return what the check found
        time.sleep(interval)  ## Back off between polls
    raise TimeoutError(f"condition not met within {timeout}s")  ## Clear failure


post("add_sta", {"resource": 1, "radio": "wiphy0", "sta_name": "sta0000", "ssid": "lab-6g", "key": "lab-passphrase", "mode": "802.11ax"})  ## Create the virtual station
print("after create:", port("sta0000")["down"], port("sta0000")["ip"])  ## Exists but down, no IP
post("set_port", {"resource": 1, "port": "sta0000", "current_flags": 0, "interest": 8388610})  ## Admin up (flags/interest select which bits change)
t0 = time.monotonic()  ## Time the association
info = wait_for(lambda: (p := port("sta0000"))["ip"] != "0.0.0.0" and p)  ## Wait for DHCP to finish
print(f"associated to {info['ap']} with {info['ip']}, {info['signal']}, in {time.monotonic() - t0 < 2} under 2 s")  ## Ready for traffic""",
            "under": "LANforge objects are addressed as shelf.resource.name (`1.1.sta0000`); ports report `down` (admin state), `ip`, `ap` (BSSID) and `signal`. Commands are asynchronous: the POST returns as soon as the command is queued, so state must be polled. The walrus operator in the lambda reads the port once and returns the whole dict when the condition holds.",
            "gotchas": [],
            "best": "Wrap the API in a client class, poll with deadlines (never fixed sleeps), name stations and cross-connects with a test-run prefix so cleanup can find them, and log every command you send.",
        },
        {
            "title": "Traffic: cross-connects, rates and guaranteed cleanup",
            "files": LF,
            "local_only": LANFORGE,
            "concept": "A **cross-connect** (CX) is a traffic flow between two endpoints (A = station, B = upstream port). Create it with `add_cx`, start and stop it with `set_cx_state`, and read live rates from `/cx/<name>` (`bps rx a`, `bps rx b`). Because traffic keeps running until stopped, wrap it in a **context manager** so it stops even if the test fails halfway.",
            "why": "Leaving traffic running after a failed test poisons every later test on the bench (and someone's afternoon). Guaranteed cleanup is not optional in lab automation.",
            "syntax": "@contextmanager\ndef traffic(name):\n    start(name)\n    try:\n        yield\n    finally:\n        stop(name)",
            "code": """import statistics  ## Median of samples
import time  ## Sampling interval
from contextlib import contextmanager  ## Build a with-statement helper

import requests  ## pip install requests

from fake_lanforge import start  ## Simulated API

BASE = start()  ## API root
s = requests.Session()  ## HTTP session


def post(cmd, body):  ## CLI-JSON command helper
    s.post(f"{BASE}/cli-json/{cmd}", json=body, timeout=10).raise_for_status()  ## Raise on HTTP errors


def cx_state(name):  ## Read a cross-connect
    return s.get(f"{BASE}/cx/{name}", timeout=10).json()[name]  ## Keyed by name


@contextmanager  ## Turns the generator into a context manager
def traffic(name, band):  ## Create, run, always stop
    post("add_cx", {"alias": name, "test_mgr": "default_tm", "tx_endp": f"{name}-A", "rx_endp": f"{name}-B", "band": band})  ## Define the flow
    post("set_cx_state", {"test_mgr": "default_tm", "cx_name": name, "cx_state": "RUNNING"})  ## Start traffic
    try:  ## The test body runs at the yield
        yield name  ## Hand control to the with-block
    finally:  ## Runs on success, failure or exception
        post("set_cx_state", {"test_mgr": "default_tm", "cx_name": name, "cx_state": "STOPPED"})  ## Stop traffic no matter what


samples = []  ## Downlink rate samples (Mbps)
with traffic("run42-dl-6g", "6G") as cx:  ## Traffic runs only inside this block
    for _ in range(5):  ## Five samples
        time.sleep(0.05)  ## A real test samples every second for tens of seconds
        samples.append(cx_state(cx)["bps rx b"] / 1e6)  ## Rate received at endpoint B
print(f"median {statistics.median(samples):.1f} Mbps over {len(samples)} samples")  ## The measurement
print("state after block:", cx_state("run42-dl-6g")["state"])  ## Stopped by the finally clause

try:  ## Now a test that fails in the middle
    with traffic("run42-ul-5g", "5G") as cx:  ## Start traffic
        raise AssertionError("throughput below KPI")  ## Test failure while traffic is running
except AssertionError as e:  ## The failure still propagates to the test runner
    print("test failed:", e, "| traffic state:", cx_state("run42-ul-5g")["state"])  ## Yet traffic was stopped""",
            "under": "`@contextmanager` runs the generator up to `yield` on entering the `with` block and resumes it on exit; an exception inside the block is re-raised at the `yield`, so the `finally` clause runs and the exception continues outwards. In pytest, a yield fixture gives the same guarantee and is the natural home for this in a framework.",
            "gotchas": [
                {
                    "title": "Stopping traffic only on the happy path",
                    "files": LF,
                    "local_only": LANFORGE,
                    "note": "When the stop call comes after the assertions, any failure skips it and the traffic runs on into the next test. Put cleanup in `finally` (or a context manager or pytest fixture).",
                    "wrong": """import requests
from fake_lanforge import start

BASE = start()


def post(cmd, body):
    return requests.post(f"{BASE}/cli-json/{cmd}", json=body, timeout=10)
post("add_cx", {"alias": "cx1", "band": "5G"})
post("set_cx_state", {"cx_name": "cx1", "cx_state": "RUNNING"})
try:
    assert 500 > 900, "throughput below KPI"
    post("set_cx_state", {"cx_name": "cx1", "cx_state": "STOPPED"})
except AssertionError:
    pass
print("cx1 state:", requests.get(f"{BASE}/cx/cx1", timeout=10).json()["cx1"]["state"])""",
                    "fixed": """import requests
from fake_lanforge import start

BASE = start()


def post(cmd, body):
    return requests.post(f"{BASE}/cli-json/{cmd}", json=body, timeout=10)
post("add_cx", {"alias": "cx1", "band": "5G"})
post("set_cx_state", {"cx_name": "cx1", "cx_state": "RUNNING"})
try:
    assert 500 > 900, "throughput below KPI"
except AssertionError:
    pass
finally:
    post("set_cx_state", {"cx_name": "cx1", "cx_state": "STOPPED"})
print("cx1 state:", requests.get(f"{BASE}/cx/cx1", timeout=10).json()["cx1"]["state"])""",
                },
            ],
            "best": "Every resource you create (stations, CXs, attenuation changes) gets a matching cleanup in `finally` or a fixture; sample rates over time and report median and min; and delete test objects at the end of a run so benches start clean.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write `wait_for(check, timeout, interval, clock, sleep)` with injectable clock and sleep, and test it with a fake clock where the condition becomes true on the 4th poll.",
            "solution": "Same polling helper, but testable in microseconds.",
            "solution_code": """def wait_for(check, timeout, interval, clock, sleep):
    deadline = clock() + timeout
    while clock() < deadline:
        if (result := check()):
            return result
        sleep(interval)
    raise TimeoutError


t = [0.0]
polls = iter([None, None, None, "192.168.100.57"])
print(wait_for(lambda: next(polls), timeout=5, interval=0.5, clock=lambda: t[0],
               sleep=lambda dt: t.__setitem__(0, t[0] + dt)), "after", t[0], "s")""",
        },
        {
            "level": "Medium",
            "files": LF,
            "local_only": LANFORGE,
            "prompt": "Create three stations (sta0000-sta0002) on the simulated API, bring them all up, and wait until every one has an IP. Print the total time-to-ready as a boolean against 2 s.",
            "solution": "Issue all the up commands first, then wait on a condition over all stations (don't wait one by one).",
            "solution_code": """import time
import requests
from fake_lanforge import start

BASE = start()
s = requests.Session()
names = [f"sta{i:04}" for i in range(3)]
for n in names:
    s.post(f"{BASE}/cli-json/add_sta", json={"resource": 1, "radio": "wiphy0", "sta_name": n, "ssid": "lab-5g"}, timeout=10)
t0 = time.monotonic()
for n in names:
    s.post(f"{BASE}/cli-json/set_port", json={"resource": 1, "port": n, "current_flags": 0}, timeout=10)
while not all(s.get(f"{BASE}/port/1/1/{n}", timeout=10).json()["interface"]["ip"] != "0.0.0.0" for n in names):
    time.sleep(0.05)
print("all", len(names), "stations ready under 2 s:", time.monotonic() - t0 < 2)""",
        },
        {
            "level": "Hard",
            "files": LF,
            "local_only": LANFORGE,
            "prompt": "Turn the traffic context manager into a class `LfClient` with methods for stations and traffic, where `traffic()` is a method usable in a with-statement and `close()` stops anything still running.",
            "solution": "Track created CXs in the client; the context manager stops its own CX, and close() is a safety net for anything left over.",
            "solution_code": """from contextlib import contextmanager

import requests
from fake_lanforge import start


class LfClient:
    def __init__(self, base):
        self.base, self.s, self.running = base, requests.Session(), set()

    def _post(self, cmd, body):
        self.s.post(f"{self.base}/cli-json/{cmd}", json=body, timeout=10).raise_for_status()

    def state(self, cx):
        return self.s.get(f"{self.base}/cx/{cx}", timeout=10).json()[cx]["state"]

    @contextmanager
    def traffic(self, cx, band="5G"):
        self._post("add_cx", {"alias": cx, "band": band})
        self._post("set_cx_state", {"cx_name": cx, "cx_state": "RUNNING"})
        self.running.add(cx)
        try:
            yield cx
        finally:
            self._stop(cx)

    def _stop(self, cx):
        self._post("set_cx_state", {"cx_name": cx, "cx_state": "STOPPED"})
        self.running.discard(cx)

    def close(self):
        for cx in list(self.running):
            self._stop(cx)


lf = LfClient(start())
with lf.traffic("cx-a") as cx:
    print(cx, lf.state(cx))
lf._post("add_cx", {"alias": "cx-b", "band": "6G"})
lf._post("set_cx_state", {"cx_name": "cx-b", "cx_state": "RUNNING"})
lf.running.add("cx-b")
lf.close()
print("cx-a", lf.state("cx-a"), "| cx-b", lf.state("cx-b"))""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "How do you automate a capacity test with 64 emulated clients?", "a": "Create stations in bulk with a run-specific prefix, bring them up, poll until all are associated with IPs (with a deadline and a list of laggards), create traffic per station, ramp up, sample per-station and aggregate rates, then stop and delete everything in cleanup.", "follow": "What do you report? (Aggregate and per-client throughput distribution, association success rate, time to associate.)"},
        {"level": "Intermediate", "q": "Why poll with a deadline instead of sleeping a fixed time?", "a": "Association and DHCP time varies; fixed sleeps are either flaky or slow. Polling returns as soon as the condition holds and fails clearly when it doesn't.", "follow": "What interval would you use? (Short enough to be responsive, long enough not to hammer the API: 0.5–1 s.)"},
        {"level": "Advanced", "q": "How do you guarantee lab equipment is reset after failed tests?", "a": "Cleanup in finally/context managers/pytest yield fixtures for every created resource, idempotent teardown that tolerates partial setup, a run-level cleanup that deletes everything with the run's prefix, and a pre-test sanity check that resets the bench to a known state.", "follow": "Why both per-test and per-run cleanup? (Crashes and killed CI jobs skip per-test cleanup.)"},
    ],
    "quiz": [
        {"q": "API commands that return before the action completes are...", "options": ["Synchronous", "Asynchronous: poll for state", "Broken", "Idempotent"], "answer": 1, "why": "Queue then poll."},
        {"q": "Guarantee traffic stops on assertion failure:", "options": ["Call stop at the end", "finally / context manager", "atexit", "time.sleep"], "answer": 1, "why": "Runs on every exit path."},
        {"q": "`@contextmanager` code after yield runs...", "options": ["Before the block", "When the with-block exits", "Never", "Only on error"], "answer": 1, "why": "On exit, if wrapped in finally."},
        {"q": "LANforge object addressing:", "options": ["IP:port", "shelf.resource.name", "MAC", "UUID"], "answer": 1, "why": "e.g. 1.1.sta0000."},
        {"q": "Best name for test-created stations:", "options": ["sta1", "Random", "Run-specific prefix", "The tester's name"], "answer": 2, "why": "Cleanup can find them."},
    ],
    "cards": [
        {"front": "Poll with deadline", "back": "`while monotonic() < deadline: if check(): return; sleep(i)`"},
        {"front": "Create station", "back": "POST /cli-json/add_sta {resource, radio, sta_name, ssid, key}"},
        {"front": "Start/stop traffic", "back": "POST /cli-json/set_cx_state {cx_name, cx_state: RUNNING|STOPPED}"},
        {"front": "Read rate", "back": "GET /cx/<name> → 'bps rx a', 'bps rx b'"},
        {"front": "Guaranteed cleanup", "back": "`@contextmanager` with try/yield/finally (or a pytest yield fixture)"},
    ],
}


AT = sim("fake_attenuator.py")

M_7_17 = {
    "id": "7.17",
    "title": "Programmable Attenuator Control",
    "hours": 1,
    "summary": "Control a programmable RF attenuator over its HTTP API: validated set/get with read-back, step resolution, sweeps with settle time, and always restoring the bench.",
    "concepts": [
        {
            "title": "A validated attenuator client",
            "files": AT,
            "local_only": ATTEN,
            "concept": "Programmable attenuators sit in the RF path between AP and client to simulate distance. Many expose simple HTTP or Telnet commands: here `GET /SETATT=30.25` returns `1` (accepted) or `0` (rejected), `GET /ATT?` returns the current value and `GET /MN?` the model. A good client validates the range and step resolution (0.25 dB here) **before** sending, checks the reply, and reads the value back.",
            "why": "Rate-vs-range, roaming and sensitivity tests all hinge on attenuation being exactly what the test thinks it is. A silently rejected command means a whole test run measured the wrong distance.",
            "syntax": "requests.get(f\"{base}/SETATT={db}\", timeout=5).text == \"1\"\nfloat(requests.get(f\"{base}/ATT?\", timeout=5).text)",
            "code": """import requests  ## pip install requests

from fake_attenuator import start  ## Simulated attenuator (see supporting files)


class Attenuator:  ## Client for one attenuator channel
    MAX_DB, STEP = 95.0, 0.25  ## From the device's datasheet

    def __init__(self, base):  ## e.g. http://10.10.40.21
        self.base = base.rstrip("/")  ## Normalise the URL
        self.model = self._get("MN?").removeprefix("MN=")  ## Identify the device once

    def _get(self, cmd):  ## Every command is a GET
        r = requests.get(f"{self.base}/{cmd}", timeout=5)  ## Short timeout: it's on the lab LAN
        r.raise_for_status()  ## HTTP-level problems
        return r.text.strip()  ## Plain-text reply

    def set(self, db):  ## Validate, send, verify
        if not 0 <= db <= self.MAX_DB:  ## Range check
            raise ValueError(f"{db} dB outside 0-{self.MAX_DB}")  ## Never send it
        db = round(db / self.STEP) * self.STEP  ## Snap to the device's resolution
        if self._get(f"SETATT={db:g}") != "1":  ## 1 means accepted
            raise RuntimeError(f"attenuator rejected {db} dB")  ## Device said no
        actual = self.get()  ## Read back
        if abs(actual - db) > 1e-9:  ## Must match exactly after snapping
            raise RuntimeError(f"set {db} dB but device reports {actual} dB")  ## Mismatch
        return actual  ## What is really applied

    def get(self):  ## Current attenuation
        return float(self._get("ATT?"))  ## Text -> number


att = Attenuator(start())  ## Connect
print(att.model)  ## Model string
print(att.set(30.25), att.set(42.6), att.get())  ## 42.6 snaps to 42.5
try:  ## Out-of-range request
    att.set(120)  ## Above the maximum
except ValueError as e:  ## Caught before anything was sent
    print("ValueError:", e)  ## Clear message""",
            "under": "Snapping with `round(db / step) * step` maps any request onto the device's grid (42.6 → 170.4 steps → 170 → 42.5 dB). Formatting with `:g` sends `42.5` rather than `42.500000`. `requests` treats a trailing `?` as the start of an empty query string, so the device actually receives `/ATT`; this simulator accepts both forms. Values on a 0.25 grid are exactly representable in binary floating point, so comparing after snapping is safe; arbitrary decimals like 0.1 are not.",
            "gotchas": [
                {
                    "title": "Accumulating float steps",
                    "files": AT,
                    "local_only": ATTEN,
                    "note": "Building a sweep by repeatedly adding a decimal step accumulates binary rounding error (0.1 added ten times is 0.9999999999999999, not 1.0), so the device sees a value off its 0.25 dB grid and rejects it (reply `0`). Compute each point from integers, or snap to the device resolution.",
                    "wrong": """import requests
from fake_attenuator import start

base = start()
value = 0.0
for _ in range(10):
    value += 0.1
print(repr(value), "->", requests.get(f"{base}/SETATT={value}", timeout=5).text)""",
                    "fixed": """import requests
from fake_attenuator import start

base = start()
value = round(10 * 0.1 / 0.25) * 0.25
print(repr(value), "->", requests.get(f"{base}/SETATT={value:g}", timeout=5).text)""",
                },
            ],
            "best": "Validate and snap before sending, check every reply, read back after setting, log each change with a timestamp, and identify the device (model/serial) at the start of each run so reports say which hardware was used.",
        },
        {
            "title": "Sweeps with settle time and a guaranteed reset",
            "files": AT,
            "local_only": ATTEN,
            "concept": "A sweep generates attenuation points (start, stop, step), and after each change waits a **settle time** for the client's rate adaptation to stabilise before measuring. A generator yields each applied value to the test, and a `try/finally` puts the attenuator back to a safe value (usually 0 dB) at the end, even if the test fails.",
            "why": "Measuring immediately after a 6 dB jump captures the transition, not the steady state. And leaving 60 dB applied after a failed run makes every following test fail mysteriously: the client can't connect.",
            "syntax": "def sweep(att, start, stop, step, settle):\n    try:\n        for db in points:\n            att.set(db); time.sleep(settle); yield db\n    finally:\n        att.set(0)",
            "code": """import time  ## Settle delay

import requests  ## pip install requests

import fake_attenuator  ## Simulated attenuator (we also peek at its history for the demo)

BASE = fake_attenuator.start()  ## Device URL


def set_att(db):  ## Minimal client for this example
    if requests.get(f"{BASE}/SETATT={db:g}", timeout=5).text != "1":  ## Check the reply
        raise RuntimeError(f"rejected {db}")  ## Fail loudly


def sweep(start, stop, step, settle=0.02, reset_to=0.0):  ## Yields each applied attenuation
    n = int(round((stop - start) / step))  ## Number of steps, computed once from the floats
    try:  ## Guarantee the reset
        for i in range(n + 1):  ## Integer loop: no accumulated float error
            db = start + i * step  ## Each point computed directly
            set_att(db)  ## Apply
            time.sleep(settle)  ## Let rate adaptation settle (seconds in a real test)
            yield db  ## Hand the point to the test
    finally:  ## Runs when the loop ends, breaks, or the consumer fails
        set_att(reset_to)  ## Back to a safe value


measured = {}  ## attenuation -> fake measurement
for db in sweep(0, 30, 7.5):  ## 0, 7.5, 15, 22.5, 30
    measured[db] = round(940 - db * 9.5)  ## Stand-in for an iperf3 run at this point
print(measured)  ## Results per point
print("history:", fake_attenuator.STATE["history"])  ## Every value the device received, ending with the reset

try:  ## A test that fails mid-sweep
    for db in sweep(0, 60, 20):  ## 0, 20, 40, 60
        if db == 40:  ## Pretend the client disconnected here
            raise AssertionError("client lost association at 40 dB")  ## Test failure
except AssertionError as e:  ## Reported to the runner as usual
    print(e, "| attenuation now:", requests.get(f"{BASE}/ATT?", timeout=5).text, "dB")  ## Reset happened anyway""",
            "under": "When the consumer of a generator raises (or breaks out of the loop), Python closes the generator, raising `GeneratorExit` at the paused `yield`; the `finally` block runs then. That makes generator-based sweeps safe in plain loops too, as long as the generator object is closed promptly (CPython does this as soon as it's no longer referenced; `contextlib.closing` makes it explicit).",
            "gotchas": [],
            "best": "Compute sweep points from integer indexes, include settle time as a parameter (and in the report), sweep both down and up when hysteresis matters (roaming), reset in `finally`, and record the applied value next to every measurement.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write `snap(db, step=0.25, max_db=95)` that rejects out-of-range values and snaps to the grid; test 10.1, 10.13, 94.9 and 96.",
            "solution": "Range check then round to the nearest multiple of the step.",
            "solution_code": """def snap(db, step=0.25, max_db=95.0):
    if not 0 <= db <= max_db:
        raise ValueError(f"{db} out of range")
    return round(db / step) * step


for v in (10.1, 10.13, 94.9, 96):
    try:
        print(v, "->", snap(v))
    except ValueError as e:
        print(v, "->", e)""",
        },
        {
            "level": "Medium",
            "prompt": "Generate a down-and-up sweep 0 → 40 → 0 in 10 dB steps without repeating the turning point, using integer arithmetic.",
            "solution": "Build the ascending list once, then append its reverse without the first element.",
            "solution_code": """def round_trip(start, stop, step):
    n = round((stop - start) / step)
    up = [start + i * step for i in range(n + 1)]
    return up + up[-2::-1]


print(round_trip(0, 40, 10))
print(round_trip(0, 1.5, 0.25))""",
        },
        {
            "level": "Hard",
            "files": AT,
            "local_only": ATTEN,
            "prompt": "Implement a sweep that stops early once a measurement falls below a floor (the client is effectively out of range), still resetting the attenuator.",
            "solution": "Break out of the consumer loop; the generator is closed and its finally block runs.",
            "solution_code": """import requests
import fake_attenuator

BASE = fake_attenuator.start()


def sweep(points):
    try:
        for db in points:
            assert requests.get(f"{BASE}/SETATT={db:g}", timeout=5).text == "1"
            yield db
    finally:
        requests.get(f"{BASE}/SETATT=0", timeout=5)


def fake_tput(db):
    return max(0, 940 - db * 18)


results = []
gen = sweep([i * 6 for i in range(11)])
for db in gen:
    mbps = fake_tput(db)
    results.append((db, mbps))
    if mbps < 100:
        break
gen.close()
print(results)
print("attenuation after early stop:", requests.get(f"{BASE}/ATT?", timeout=5).text)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What does a programmable attenuator do in a Wi-Fi test?", "a": "It adds a controlled amount of RF path loss between devices in a conducted or shielded setup, emulating distance or obstacles repeatably, so tests like rate-vs-range, roaming triggers and sensitivity are reproducible.", "follow": "Why conducted/shielded? (To remove uncontrolled interference and multipath.)"},
        {"level": "Intermediate", "q": "Why include a settle time after changing attenuation?", "a": "Rate adaptation, MIMO mode and sometimes band steering react over hundreds of milliseconds to seconds; measuring too early captures transients. The settle time should be measured and recorded.", "follow": "How would you choose it? (Measure throughput vs time after a step and pick when it stabilises.)"},
        {"level": "Intermediate", "q": "How do you ensure the bench is left usable after a failed sweep?", "a": "Reset attenuation in a finally block or fixture teardown, and have a per-run setup check that sets known values before starting.", "follow": "What else should be reset? (Traffic, station state, AP config changes.)"},
    ],
    "quiz": [
        {"q": "`sum([0.1] * 10) == 1.0` in Python is...", "options": ["True", "False", "Error", "Depends on OS"], "answer": 1, "why": "Floating-point rounding: 0.9999999999999999."},
        {"q": "Snap 42.6 dB to a 0.25 dB grid:", "options": ["42.6", "42.5", "42.75", "43"], "answer": 1, "why": "round(170.4) = 170 → 42.5."},
        {"q": "When does a generator's finally run if the consumer breaks?", "options": ["Never", "When the generator is closed", "At program exit only", "Immediately at yield"], "answer": 1, "why": "GeneratorExit on close."},
        {"q": "After set(), a robust client should...", "options": ["Sleep 5 s", "Read the value back", "Reconnect", "Nothing"], "answer": 1, "why": "Verify."},
        {"q": "Format 42.5 without trailing zeros:", "options": ["f'{x:.6f}'", "f'{x:g}'", "str(int(x))", "repr(x)"], "answer": 1, "why": ":g."},
    ],
    "cards": [
        {"front": "Snap to device grid", "back": "`round(db / step) * step`"},
        {"front": "Float-safe sweep", "back": "`[start + i * step for i in range(n + 1)]` with integer i"},
        {"front": "Verify a set", "back": "Check the reply, then read back and compare"},
        {"front": "Always reset", "back": "Generator/fixture with `finally: att.set(0)`"},
        {"front": "Settle time", "back": "Wait after each change before measuring; record it"},
    ],
}


RVR_EQUIP = {**sim("fake_attenuator.py", "fake_lanforge.py")}

RVR_CONFTEST = '''import time

import pytest
import requests

import fake_attenuator
import fake_lanforge

KPI = {"5G": {0: 900, 30: 600, 42: 150}, "6G": {0: 2300, 30: 1100, 42: 120}}


@pytest.fixture(scope="session")
def attenuator():
    base = fake_attenuator.start()

    def set_db(db):
        assert requests.get(f"{base}/SETATT={db:g}", timeout=5).text == "1"

    yield set_db
    set_db(0)


@pytest.fixture(scope="session")
def lanforge():
    return fake_lanforge.start()


@pytest.fixture
def measure(lanforge):
    s = requests.Session()

    def run(band, samples=3):
        name = f"rvr-{band}"
        s.post(f"{lanforge}/cli-json/add_cx", json={"alias": name, "band": band}, timeout=5)
        s.post(f"{lanforge}/cli-json/set_cx_state", json={"cx_name": name, "cx_state": "RUNNING"}, timeout=5)
        try:
            values = []
            for _ in range(samples):
                time.sleep(0.01)
                values.append(s.get(f"{lanforge}/cx/{name}", timeout=5).json()[name]["bps rx b"] / 1e6)
            return sorted(values)[len(values) // 2]
        finally:
            s.post(f"{lanforge}/cli-json/set_cx_state", json={"cx_name": name, "cx_state": "STOPPED"}, timeout=5)

    return run
'''

M_7_18 = {
    "id": "7.18",
    "title": "End-to-End Rate-vs-Range Test",
    "hours": 2.5,
    "summary": "Combine the pieces into a real test: sweep attenuation, run traffic per band at each point, collect results to CSV, draw the RvR chart, judge against KPIs, and express it as a pytest test with fixtures.",
    "concepts": [
        {
            "title": "The RvR script: sweep, measure, store, plot, judge",
            "files": RVR_EQUIP,
            "local_only": RVR,
            "capture": "rvr_e2e.png",
            "image_alt": "Rate-versus-range chart from the simulated bench: 5 GHz and 6 GHz throughput falling with attenuation, with KPI markers",
            "concept": "A rate-vs-range run is a loop: for each attenuation point, set the attenuator, let the link settle, run traffic for each band, record the median throughput (plus the attenuation actually applied). Then write the raw results to CSV, draw the chart, and compare selected points against KPIs to produce a verdict. Every resource is cleaned up in `finally`. Both instruments here are the simulators from the previous lessons, and the simulated throughput depends on the simulated attenuation.",
            "why": "This is the canonical Wi-Fi performance test, and it exercises every skill from this phase: HTTP instrument control, traffic APIs, polling, cleanup, CSV, plotting and KPI logic. Once it's a script, it runs nightly on every firmware build.",
            "syntax": "for db in points:\n    att.set(db); sleep(settle)\n    for band in bands: results.append(measure(band))\nwrite_csv(); plot(); verdict()",
            "code": """import csv  ## Raw results file
import statistics  ## Median of samples
import time  ## Settle and sampling delays

import matplotlib  ## pip install matplotlib

matplotlib.use("Agg")  ## Headless plotting
import matplotlib.pyplot as plt  ## Chart
import requests  ## Instrument APIs

import fake_attenuator  ## Simulated attenuator
import fake_lanforge  ## Simulated traffic generator (its rates follow the attenuation)

ATT, LF = fake_attenuator.start(), fake_lanforge.start()  ## Instrument URLs (from the bench config in real life)
POINTS = [i * 6 for i in range(11)]  ## 0..60 dB in 6 dB steps
BANDS = ["5G", "6G"]  ## Bands under test
KPI = {"5G": {0: 900, 30: 600, 42: 150}, "6G": {0: 2300, 30: 1100, 42: 120}}  ## Minimum Mbps at chosen points
s = requests.Session()  ## Shared HTTP session


def set_att(db):  ## Apply attenuation and verify
    assert s.get(f"{ATT}/SETATT={db:g}", timeout=5).text == "1", f"attenuator rejected {db}"  ## Reply check
    return float(s.get(f"{ATT}/ATT?", timeout=5).text)  ## Read back what is really applied


def measure(band, samples=5):  ## Median downlink rate for one band
    cx = f"rvr-{band}"  ## Cross-connect name
    s.post(f"{LF}/cli-json/add_cx", json={"alias": cx, "band": band}, timeout=5)  ## Define the flow
    s.post(f"{LF}/cli-json/set_cx_state", json={"cx_name": cx, "cx_state": "RUNNING"}, timeout=5)  ## Start traffic
    try:  ## Always stop it
        values = []  ## Samples
        for _ in range(samples):  ## A real run samples for 20-60 s
            time.sleep(0.01)  ## Sampling interval
            values.append(s.get(f"{LF}/cx/{cx}", timeout=5).json()[cx]["bps rx b"] / 1e6)  ## Mbps at the receiver
        return statistics.median(values)  ## Robust against one odd sample
    finally:  ## Even if a request fails
        s.post(f"{LF}/cli-json/set_cx_state", json={"cx_name": cx, "cx_state": "STOPPED"}, timeout=5)  ## Stop traffic


rows = []  ## One row per (attenuation, band)
try:  ## The sweep
    for db in POINTS:  ## Each distance
        applied = set_att(db)  ## Set and verify
        time.sleep(0.02)  ## Settle (seconds on real hardware)
        for band in BANDS:  ## Each band at this distance
            rows.append({"atten_db": applied, "band": band, "mbps": round(measure(band), 1)})  ## Record the point
finally:  ## Bench back to a known state
    set_att(0)  ## Reset attenuation

with open("rvr.csv", "w", newline="") as f:  ## Raw data for later analysis
    writer = csv.DictWriter(f, fieldnames=["atten_db", "band", "mbps"])  ## Fixed columns
    writer.writeheader()  ## Header line
    writer.writerows(rows)  ## All points

fig, ax = plt.subplots(figsize=(7, 4))  ## The RvR chart
for band, marker in zip(BANDS, "os"):  ## One line per band
    pts = [r for r in rows if r["band"] == band]  ## This band's rows
    ax.plot([r["atten_db"] for r in pts], [r["mbps"] for r in pts], marker=marker, label=band)  ## Throughput vs attenuation
    ax.scatter(list(KPI[band]), list(KPI[band].values()), marker="_", s=300, color="black")  ## KPI floors as short bars
ax.set(xlabel="Attenuation (dB)", ylabel="Throughput (Mbps)", title="RvR (simulated bench)")  ## Labels
ax.grid(alpha=0.3)  ## Light grid
ax.legend()  ## Band labels
fig.savefig("rvr_e2e.png", dpi=90, bbox_inches="tight")  ## Chart for the report
plt.close(fig)  ## Free memory

lookup = {(r["band"], r["atten_db"]): r["mbps"] for r in rows}  ## Fast access by point
failures = [f"{b}@{db}dB: {lookup[(b, db)]} < {kpi}" for b in BANDS for db, kpi in KPI[b].items() if lookup[(b, db)] < kpi]  ## KPI checks
print(len(rows), "points written to rvr.csv")  ## Raw data summary
print("verdict:", "PASS" if not failures else "FAIL", failures)  ## The answer people want
print("attenuator left at", s.get(f"{ATT}/ATT?", timeout=5).text, "dB")  ## Bench reset confirmed""",
            "under": "The simulated LANforge computes each band's rate from the simulated attenuator's current value with a logistic fall-off, so the curve is shaped like a real one. The structure is what matters: instruments behind small functions, every start paired with a stop in `finally`, raw data saved before any judging, and the verdict computed from data, not from the chart. The chart below is the file this run wrote.",
            "gotchas": [],
            "best": "Save raw data first, then derive charts and verdicts from it (so you can re-judge with new KPIs without re-running), record firmware, bench and settle time in the output, run each point several times on real hardware, and put the instrument code in the framework layer so the test script stays this readable.",
        },
        {
            "title": "The same test as a pytest test",
            "runner": "pytest",
            "filename": "test_rvr.py",
            "files": {**RVR_EQUIP, "conftest.py": RVR_CONFTEST},
            "args": ["-v", "-rA"],
            "concept": "In a framework, the sweep becomes a parametrized test: one test case per (band, KPI point), so each check passes or fails on its own in the report. Session fixtures own the instruments (and reset the attenuator in teardown), a function fixture runs traffic with guaranteed stop, and `record_property` stores the measured value in the JUnit XML for dashboards.",
            "why": "A parametrized RvR test shows exactly which band failed at which distance, reruns a single point with `-k`, and plugs into the same CI reporting as every other test.",
            "syntax": "@pytest.mark.parametrize(\"band,db,kpi\", CASES, ids=...)\ndef test_rvr_point(attenuator, measure, record_property, band, db, kpi): ...",
            "code": """import pytest  ## Test framework

from conftest import KPI  ## KPI table shared with the fixtures

CASES = [(band, db, kpi) for band, points in KPI.items() for db, kpi in points.items()]  ## One case per KPI point


@pytest.mark.parametrize("band,db,kpi", CASES, ids=[f"{b}-{d}dB" for b, d, _ in CASES])  ## Readable test ids
def test_rvr_point(attenuator, measure, record_property, band, db, kpi):  ## Fixtures from conftest.py
    attenuator(db)  ## Set the distance (verified inside the fixture)
    mbps = measure(band)  ## Median throughput with guaranteed traffic stop
    record_property("throughput_mbps", round(mbps, 1))  ## Into the JUnit XML report
    assert mbps >= kpi, f"{band} at {db} dB: {mbps:.1f} Mbps < KPI {kpi}"  ## Clear failure message""",
            "under": "Parametrize expands the list into six independent test items; session-scoped fixtures start each simulator once and the attenuator fixture's code after `yield` resets it to 0 dB when the session ends. `-rA` adds a short summary line for every outcome. Because measurements are independent per item, a failed point doesn't stop the others.",
            "gotchas": [],
            "best": "Keep KPIs in data shared by tests and reports, one test item per checked point, instrument fixtures at session scope with teardown resets, `record_property` for every measurement, and the sweep-plus-chart script kept alongside for exploratory runs.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Given RvR rows (atten, band, mbps), find for each band the highest attenuation at which throughput is still at least 100 Mbps (its 'range').",
            "solution": "Filter by band and threshold, take the max attenuation.",
            "solution_code": """rows = [(0, "5G", 935), (12, "5G", 921), (24, "5G", 870), (36, "5G", 420), (48, "5G", 60),
        (0, "6G", 2410), (12, "6G", 2370), (24, "6G", 1950), (36, "6G", 620), (48, "6G", 30)]
for band in ("5G", "6G"):
    reach = max(db for db, b, mbps in rows if b == band and mbps >= 100)
    print(band, "range:", reach, "dB")""",
        },
        {
            "level": "Medium",
            "prompt": "Compare two firmware builds' RvR results point by point and flag any point where the new build is more than 10% slower.",
            "solution": "Join on (band, attenuation), compute the relative change, filter by threshold.",
            "solution_code": """old = {("5G", 0): 935, ("5G", 24): 870, ("5G", 36): 420, ("6G", 0): 2410, ("6G", 24): 1950, ("6G", 36): 620}
new = {("5G", 0): 940, ("5G", 24): 862, ("5G", 36): 351, ("6G", 0): 2398, ("6G", 24): 1720, ("6G", 36): 640}
for key in sorted(old):
    change = (new[key] - old[key]) / old[key] * 100
    flag = "REGRESSION" if change < -10 else ""
    print(f"{key[0]} {key[1]:>2} dB {old[key]:>5} -> {new[key]:>5} ({change:+.1f}%) {flag}")""",
        },
        {
            "level": "Hard",
            "prompt": "Interpolate: estimate the attenuation at which throughput crosses a threshold (500 Mbps) by linear interpolation between the two neighbouring measured points.",
            "solution": "Find the first pair where the curve goes from >= threshold to < threshold and interpolate linearly.",
            "solution_code": """def crossing(points, threshold):
    for (a0, t0), (a1, t1) in zip(points, points[1:]):
        if t0 >= threshold > t1:
            return a0 + (t0 - threshold) * (a1 - a0) / (t0 - t1)
    return None


five_g = [(0, 935), (12, 921), (24, 870), (36, 420), (48, 60)]
six_g = [(0, 2410), (12, 2370), (24, 1950), (36, 620), (48, 30)]
print("5G crosses 500 Mbps at", round(crossing(five_g, 500), 1), "dB")
print("6G crosses 500 Mbps at", round(crossing(six_g, 500), 1), "dB")""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "Walk through how you'd automate a rate-vs-range test.", "a": "Bench config (instruments, DUT, client) → reset to known state → for each attenuation point: set and verify, settle, run traffic per band/direction for N seconds and M iterations, record median/min plus PHY rate and RSSI from both ends → save raw CSV/JSON → chart → compare against KPIs and previous builds → cleanup in finally. Run nightly in CI with results to a dashboard.", "follow": "What extra data helps debug a bad curve? (RSSI, MCS/NSS per point, retries, captures at the knee.)"},
        {"level": "Intermediate", "q": "Why save raw results before judging?", "a": "So verdicts and charts can be recomputed with new KPIs or analysis without re-running hours of lab time, and failures can be investigated after the fact.", "follow": "What format? (CSV/JSON with metadata: firmware, bench, settle time, iteration count.)"},
        {"level": "Advanced", "q": "Your RvR results vary by 15% between nights. How do you make them trustworthy?", "a": "Control the environment (shielded enclosures, fixed cabling), verify attenuator read-back, warm up devices, increase samples and iterations, fix channel and bandwidth, check client CPU and drivers, track per-point variance, and compare against a golden reference build each night.", "follow": "How do you detect a real regression vs noise? (Statistical comparison over several runs, thresholds based on observed variance.)"},
    ],
    "quiz": [
        {"q": "After each attenuation change you should...", "options": ["Measure immediately", "Wait a settle time", "Reboot the client", "Change band"], "answer": 1, "why": "Let rate adaptation stabilise."},
        {"q": "Where should attenuator reset live?", "options": ["End of script", "finally / fixture teardown", "A comment", "Next test's setup only"], "answer": 1, "why": "Runs even on failure."},
        {"q": "Report throughput per point as...", "options": ["Single sample", "Median (and min) of several", "Max only", "Average of first and last"], "answer": 1, "why": "Robust and honest."},
        {"q": "One pytest item per KPI point gives...", "options": ["Slower tests", "Per-point pass/fail and reruns", "Fewer reports", "No benefit"], "answer": 1, "why": "Granular results."},
        {"q": "Measured values into JUnit XML:", "options": ["print", "record_property", "caplog", "assert message"], "answer": 1, "why": "Machine-readable."},
    ],
    "cards": [
        {"front": "RvR loop", "back": "set+verify attenuation → settle → traffic per band → record → reset in finally"},
        {"front": "Save first", "back": "Raw CSV/JSON, then chart and verdict from data"},
        {"front": "pytest RvR", "back": "parametrize (band, db, kpi); session fixtures for instruments; record_property"},
        {"front": "Range at threshold", "back": "Linear interpolation between neighbouring points"},
        {"front": "Regression check", "back": "Point-by-point vs previous build, flag drops beyond noise"},
    ],
}
