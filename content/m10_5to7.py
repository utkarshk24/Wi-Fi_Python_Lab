"""Phase 10 capstones 10.5-10.7: pcap analyzer, results dashboard, full CI pipeline."""

from auto_support import needs


def plain(code: str) -> str:
    """The annotated example code without its '  ## ' explanations, for use as a supporting file."""
    return "\n".join(line.split("  ## ")[0].rstrip() for line in code.split("\n")) + "\n"


SCAPY = needs("scapy") + " (frames are built and parsed offline, never sent)"
DASH = needs("fastapi httpx sqlalchemy jinja2")
DASH_SHOT = needs("fastapi httpx sqlalchemy jinja2 playwright") + " plus `playwright install chromium`"


# --------------------------------------------------------------------------- 10.5
CAPTURE = r'''"""make_capture: write a small, realistic 802.11 capture: joins, a roam, a failed join, retries."""  ## Fixture generator
from scapy.all import (BOOTP, DHCP, EAPOL, IP, LLC, SNAP, UDP, Dot11, Dot11AssoReq, Dot11AssoResp,  ## Frame layers
                       Dot11Auth, Dot11Deauth, Dot11ReassoReq, Dot11ReassoResp, RadioTap, Raw, rdpcap, wrpcap)  ## ...and file I/O

AP1, AP2 = "3c:84:6a:00:00:01", "3c:84:6a:00:00:02"  ## Two APs (BSSIDs) on the same SSID
PHONE, LAPTOP = "a4:5e:60:11:22:33", "f0:18:98:44:55:66"  ## Two client stations
GW = "00:00:5e:00:01:01"  ## Router / DHCP server MAC on the wired side
EPOCH = 1760000000.0  ## Capture start time (seconds since 1970)
TO_DS, FROM_DS, RETRY = 0x01, 0x02, 0x08  ## Frame Control flag bits
ACK, MIC, SECURE, INSTALL = 0x0080, 0x0100, 0x0200, 0x0040  ## EAPOL-Key "key information" bits
KEY_INFO = {1: ACK, 2: MIC, 3: ACK | MIC | INSTALL | SECURE, 4: MIC | SECURE}  ## Which bits each 4-way message sets


def mgmt(src, dst, bssid, body):  ## Management frame (auth, assoc, deauth...)
    return RadioTap() / Dot11(addr1=dst, addr2=src, addr3=bssid) / body  ## scapy fills type/subtype from the body layer


def data(sta, bssid, payload, uplink, retry=False):  ## Data frame between client and AP
    flags = (TO_DS if uplink else FROM_DS) | (RETRY if retry else 0)  ## Direction + retransmission flag
    addrs = dict(addr1=bssid, addr2=sta) if uplink else dict(addr1=sta, addr2=bssid)  ## Receiver / transmitter
    return RadioTap() / Dot11(type=2, FCfield=flags, addr3=GW, **addrs) / LLC() / SNAP() / payload  ## LLC/SNAP carries the EtherType


def eapol(n):  ## 4-way handshake message n (1-4)
    body = bytes([2]) + KEY_INFO[n].to_bytes(2, "big") + bytes(92)  ## Descriptor type, key info, zeroed rest
    return EAPOL(version=2, type=3) / Raw(body)  ## type 3 = EAPOL-Key


def dhcp(kind, sta):  ## DHCP message for a client
    return IP(src="0.0.0.0", dst="255.255.255.255") / UDP(sport=68, dport=67) / BOOTP(chaddr=bytes.fromhex(sta.replace(":", ""))) / DHCP(options=[("message-type", kind), "end"])  ## Addresses kept simple


def stamp(t0, timeline):  ## Give frames absolute timestamps
    frames = []  ## Result
    for dt, frame in timeline:  ## (offset seconds, frame)
        frame.time = EPOCH + t0 + dt  ## pcap timestamp
        frames.append(frame)  ## Keep order
    return frames  ## Timestamped frames


def handshake(sta, ap, start, gap=0.004):  ## The four EAPOL-Key messages
    return [(start + i * gap, data(sta, ap, eapol(n), uplink=n % 2 == 0)) for i, n in enumerate((1, 2, 3, 4))]  ## Odd = AP->client


def join(sta, ap, t0, dhcp_too=True):  ## Open auth, association, 4-way, then DHCP
    timeline = [  ## Offsets in seconds
        (0.000, mgmt(sta, ap, ap, Dot11Auth(algo=0, seqnum=1))),  ## Client: authentication request
        (0.002, mgmt(ap, sta, ap, Dot11Auth(algo=0, seqnum=2, status=0))),  ## AP: success
        (0.004, mgmt(sta, ap, ap, Dot11AssoReq())),  ## Client: association request
        (0.006, mgmt(ap, sta, ap, Dot11AssoResp(status=0, AID=1))),  ## AP: associated
        *handshake(sta, ap, 0.010),  ## Keys: 10, 14, 18, 22 ms... (M4 at 22 ms)
    ]  ## Join without DHCP
    if dhcp_too:  ## New client needs an address
        timeline += [(0.050, data(sta, ap, dhcp("discover", sta), True)), (0.120, data(sta, ap, dhcp("offer", sta), False)),  ## Discover / offer
                     (0.125, data(sta, ap, dhcp("request", sta), True)), (0.180, data(sta, ap, dhcp("ack", sta), False))]  ## Request / ack
    return stamp(t0, timeline)  ## Timestamped


def build():  ## The whole scenario, in time order
    frames = join(PHONE, AP1, 0.0)  ## Phone joins AP1: 180 ms to DHCP ACK
    traffic = IP(src="10.0.0.1", dst="10.0.0.23") / UDP(sport=5201, dport=5201) / Raw(b"x" * 100)  ## iperf-like payload
    frames += stamp(1.0, [(i * 0.025, data(PHONE, AP1, traffic.copy(), False, retry=i % 7 == 3)) for i in range(40)])  ## 40 frames, 6 retries
    frames += stamp(2.0, [(0.000, mgmt(LAPTOP, AP1, AP1, Dot11Auth(algo=0, seqnum=1))),  ## Laptop with a wrong passphrase
                          (0.002, mgmt(AP1, LAPTOP, AP1, Dot11Auth(algo=0, seqnum=2, status=0))),  ## Auth OK (open system)
                          (0.004, mgmt(LAPTOP, AP1, AP1, Dot11AssoReq())), (0.006, mgmt(AP1, LAPTOP, AP1, Dot11AssoResp(status=0, AID=2))),  ## Associated
                          *handshake(LAPTOP, AP1, 0.010)[:2], *handshake(LAPTOP, AP1, 1.010)[:2],  ## M1, M2 (bad MIC), retried once
                          (2.020, mgmt(AP1, LAPTOP, AP1, Dot11Deauth(reason=15)))])  ## AP gives up: reason 15 = 4-way handshake timeout
    frames += stamp(5.0, [(0.000, mgmt(PHONE, AP2, AP2, Dot11ReassoReq(current_AP=AP1))),  ## Phone roams to AP2
                          (0.003, mgmt(AP2, PHONE, AP2, Dot11ReassoResp(status=0, AID=1))),  ## Reassociated
                          *handshake(PHONE, AP2, 0.007)])  ## Fresh keys: M4 at 19 ms
    frames += stamp(8.0, [(0.0, mgmt(PHONE, AP2, AP2, Dot11Deauth(reason=3)))])  ## Phone leaves: reason 3 = station leaving
    return frames  ## Everything


def write(path):  ## Save as a pcap file
    frames = build()  ## Generate
    wrpcap(str(path), frames)  ## RadioTap link type, like a monitor-mode capture
    return len(frames)  ## Frame count


if __name__ == "__main__":  ## Demo: write and peek at the file
    print(write("lab.pcap"), "frames written")  ## Create
    for pkt in rdpcap("lab.pcap")[:6]:  ## Read back the first few
        print(f"{pkt.time - EPOCH:6.3f}s", pkt[Dot11].summary())  ## Offset and scapy's one-line summary'''

ANALYZER = r'''"""pcapkpi: turn an 802.11 capture into per-client join/roam/retry KPIs and a CI verdict."""  ## Module docstring
import json  ## JSON report
import sys  ## argv / exit code
from collections import defaultdict  ## Per-client accumulators

from scapy.all import (DHCP, EAPOL, Dot11, Dot11AssoResp, Dot11Auth, Dot11Deauth, Dot11ReassoReq,  ## Layers we look for
                       Dot11ReassoResp, rdpcap)  ## ...and the reader

ACK, MIC, SECURE, INSTALL = 0x0080, 0x0100, 0x0200, 0x0040  ## EAPOL-Key info bits
RETRY = 0x08  ## Frame Control retry bit
LIMITS = {"join_ms": 500, "roam_ms": 50, "retry_pct": 10, "min_frames": 20}  ## Pass/fail policy (as data)


def roles(d):  ## (client MAC, BSSID) for any frame
    ds = int(d.FCfield) & 0x3  ## 0 mgmt/ad-hoc, 1 to-DS, 2 from-DS
    bssid = {1: d.addr1, 2: d.addr2}.get(ds, d.addr3)  ## Where the BSSID sits depends on direction
    return (d.addr2 if d.addr1 == bssid else d.addr1), bssid  ## The client is the other address


def key_message(pkt):  ## Which 4-way message (1-4) this EAPOL-Key frame is
    info = int.from_bytes(bytes(pkt[EAPOL].payload)[1:3], "big")  ## Bytes 1-2 after the descriptor type
    if info & ACK:  ## Sent by the AP
        return 3 if info & INSTALL else 1  ## M3 installs the key
    return 4 if info & SECURE else 2  ## Client: M4 is "secure"


def dhcp_type(pkt):  ## DHCP message type number (5 = ACK)
    return dict(o for o in pkt[DHCP].options if isinstance(o, tuple)).get("message-type")  ## Options are (name, value) tuples


def ms(seconds):  ## Seconds -> milliseconds, rounded
    return round(seconds * 1000, 1)  ## 0.1 ms is plenty for pcap timestamps


def analyse(packets):  ## The core: one pass, one small state machine per client
    clients = defaultdict(lambda: {"joins": [], "roams": [], "failed": [], "deauths": [], "data_frames": 0, "retries": 0})  ## Per-client results
    pending, serving = {}, {}  ## Connection attempt in progress / AP currently serving the client
    for pkt in sorted(packets, key=lambda p: p.time):  ## Captures can be slightly out of order
        if not pkt.haslayer(Dot11):  ## Not 802.11
            continue  ## Ignore
        d, t = pkt[Dot11], float(pkt.time)  ## Header and timestamp
        sta, bssid = roles(d)  ## Who's who
        c = clients[sta]  ## This client's record
        if d.type == 2:  ## Data frame
            c["data_frames"] += 1  ## Count
            c["retries"] += bool(int(d.FCfield) & RETRY)  ## Retransmission?
        if pkt.haslayer(Dot11Auth) and pkt[Dot11Auth].seqnum == 1:  ## A new join starts
            pending[sta] = {"kind": "join", "bssid": bssid, "start": t, "stage": "auth"}  ## Start the clock
        elif pkt.haslayer(Dot11ReassoReq):  ## A roam starts
            pending[sta] = {"kind": "roam", "bssid": bssid, "start": t, "stage": "reassoc", "from": serving.get(sta)}  ## Remember the old AP
        elif (pkt.haslayer(Dot11AssoResp) or pkt.haslayer(Dot11ReassoResp)) and sta in pending:  ## (Re)association answered
            pending[sta]["stage"] = "assoc"  ## Progress
        elif pkt.haslayer(EAPOL) and pkt[EAPOL].type == 3 and sta in pending:  ## A 4-way handshake message
            p = pending[sta]  ## The attempt
            p["stage"] = "4-way"  ## Progress
            p.setdefault("m1", t)  ## First M1 starts the handshake clock
            if key_message(pkt) == 4:  ## Handshake complete
                serving[sta] = bssid  ## Now connected here
                if p["kind"] == "roam":  ## Roams are done at M4 (same subnet, no DHCP)
                    c["roams"].append({"from": p["from"], "to": bssid, "roam_ms": ms(t - pending.pop(sta)["start"])})  ## Record
                else:  ## Joins still need an address
                    p.update(stage="dhcp", handshake_ms=ms(t - p["m1"]))  ## Keep waiting
        elif pkt.haslayer(DHCP) and dhcp_type(pkt) == 5 and sta in pending:  ## DHCP ACK: the client can talk
            p = pending.pop(sta)  ## Attempt finished
            c["joins"].append({"bssid": p["bssid"], "join_ms": ms(t - p["start"]), "handshake_ms": p["handshake_ms"]})  ## Record
        elif pkt.haslayer(Dot11Deauth):  ## Kicked or leaving
            reason = pkt[Dot11Deauth].reason  ## IEEE reason code
            if sta in pending:  ## Mid-connection: a failed join/roam
                p = pending.pop(sta)  ## Close it
                c["failed"].append({"bssid": p["bssid"], "stage": p["stage"], "reason": reason})  ## Where it died
            else:  ## Ordinary disconnect
                c["deauths"].append({"bssid": bssid, "reason": reason})  ## Record
            serving.pop(sta, None)  ## No longer connected
    for sta, p in pending.items():  ## Capture ended mid-connection
        clients[sta]["failed"].append({"bssid": p["bssid"], "stage": p["stage"], "reason": None})  ## Unknown reason
    for c in clients.values():  ## Derived KPI
        c["retry_pct"] = round(100 * c["retries"] / c["data_frames"], 1) if c["data_frames"] else 0.0  ## Retry rate
    return dict(sorted(clients.items()))  ## Stable order for JSON and tests


def verdict(report, limits=LIMITS):  ## Turn KPIs into a list of problems (empty = pass)
    problems = []  ## Human-readable findings
    for sta, c in report.items():  ## Per client
        problems += [f"{sta}: join to {j['bssid']} took {j['join_ms']} ms" for j in c["joins"] if j["join_ms"] > limits["join_ms"]]  ## Slow joins
        problems += [f"{sta}: roam to {r['to']} took {r['roam_ms']} ms" for r in c["roams"] if r["roam_ms"] > limits["roam_ms"]]  ## Slow roams
        problems += [f"{sta}: join to {f['bssid']} failed at {f['stage']} (reason {f['reason']})" for f in c["failed"]]  ## Failures
        if c["data_frames"] >= limits["min_frames"] and c["retry_pct"] > limits["retry_pct"]:  ## Enough traffic to judge
            problems.append(f"{sta}: retry rate {c['retry_pct']}% over {c['data_frames']} frames")  ## Poor link
    return problems  ## Possibly empty


def main(argv=None):  ## CLI: pcapkpi capture.pcap
    path = (argv if argv is not None else sys.argv[1:])[0]  ## First argument
    report = analyse(rdpcap(path))  ## Read and analyse
    print(json.dumps(report, indent=1))  ## Machine-readable KPIs (archive this)
    problems = verdict(report)  ## Judge
    for line in problems:  ## Human summary
        print("FAIL", line)  ## One per problem
    return 1 if problems else 0  ## CI exit code


if __name__ == "__main__":  ## Demo on a generated capture
    import make_capture  ## The fixture generator from the previous concept
    make_capture.write("lab.pcap")  ## Produce the input
    print("exit code:", main(["lab.pcap"]))  ## Run like the CLI would'''

PCAP_TESTS = r'''import pytest  ## Test framework
from scapy.all import rdpcap  ## Read the generated file

import make_capture as cap  ## Fixture generator (known scenario)
from pcapkpi import LIMITS, analyse, verdict  ## Code under test


@pytest.fixture(scope="module")  ## Build the capture once for all tests
def report(tmp_path_factory):  ## Module-scoped temp dir
    path = tmp_path_factory.mktemp("cap") / "lab.pcap"  ## Fresh location
    cap.write(path)  ## Known input
    return analyse(rdpcap(str(path)))  ## Through the real file format


def test_phone_join_and_roam_timings(report):  ## Happy path, exact numbers
    phone = report[cap.PHONE]  ## One client
    assert phone["joins"] == [{"bssid": cap.AP1, "join_ms": 180.0, "handshake_ms": 12.0}]  ## Auth -> DHCP ACK, M1 -> M4
    assert phone["roams"] == [{"from": cap.AP1, "to": cap.AP2, "roam_ms": 19.0}]  ## Reassoc -> M4
    assert phone["deauths"] == [{"bssid": cap.AP2, "reason": 3}]  ## Clean leave isn't a failure


def test_wrong_passphrase_fails_in_the_4way(report):  ## The classic support ticket
    assert report[cap.LAPTOP]["failed"] == [{"bssid": cap.AP1, "stage": "4-way", "reason": 15}]  ## Stage + reason code
    assert report[cap.LAPTOP]["joins"] == []  ## Never got an address


def test_retry_rate(report):  ## 6 retries in 40 data frames, plus handshake/DHCP frames
    assert report[cap.PHONE]["retries"] == 6  ## Retry bit counted
    assert report[cap.PHONE]["retry_pct"] == pytest.approx(100 * 6 / report[cap.PHONE]["data_frames"], abs=0.05)  ## Derived correctly


@pytest.mark.parametrize("limit,expected", [(5, 1), (20, 0)])  ## Policy is data: test both sides
def test_retry_limit_is_configurable(report, limit, expected):  ## No hard-coded thresholds
    problems = verdict(report, {**LIMITS, "retry_pct": limit})  ## Override one limit
    assert sum("retry rate" in p for p in problems) == expected  ## Flagged or not


def test_capture_ending_mid_join_is_reported():  ## Edge case built in memory, no file needed
    frames = cap.join(cap.LAPTOP, cap.AP2, 0.0, dhcp_too=False)  ## Keys done, no DHCP
    report = analyse(frames)  ## Same entry point
    assert report[cap.LAPTOP]["failed"] == [{"bssid": cap.AP2, "stage": "dhcp", "reason": None}]  ## Stuck waiting for an address'''

M_10_5 = {
    "id": "10.5",
    "title": "Pcap Analyzer",
    "hours": 6,
    "summary": "Capstone: generate a realistic 802.11 capture (joins, a roam, a wrong-passphrase failure, retries), then build a one-pass analyzer that turns it into per-client KPIs (join time, handshake time, roam time, failure stage and reason, retry rate) with a policy-driven CI verdict and tests.",
    "concepts": [
        {
            "title": "A known capture to develop against",
            "filename": "make_capture.py",
            "local_only": SCAPY,
            "concept": "**Brief:** \"the phone takes ages to connect\" and \"the laptop can't join\" arrive as pcaps. Before writing an analyzer you need input whose right answers you already know. `make_capture.py` builds one with scapy: a phone that joins AP1 (open auth, association, the WPA2 4-way handshake, DHCP), streams traffic with some retransmissions, roams to AP2 and leaves; and a laptop with a wrong passphrase whose handshake stalls at message 2 until the AP sends a deauthentication with reason 15. **Skills used:** scapy layers (7.x), bit flags, list building, timestamps.",
            "why": "A generated capture is a test fixture: every timing and failure in it was put there on purpose, so when the analyzer reports a 180 ms join or a reason-15 failure you can check it is right. Real captures come later, once the logic is trusted.",
            "syntax": "frame = RadioTap() / Dot11(addr1=dst, addr2=src, addr3=bssid) / Dot11Auth(seqnum=1)\nframe.time = epoch + offset\nwrpcap(\"lab.pcap\", frames)",
            "code": CAPTURE,
            "under": "In 802.11 the meaning of the three address fields depends on the To-DS/From-DS bits: for management frames addr3 is the BSSID; for data going to the AP (To-DS) addr1 is the BSSID; for data from the AP (From-DS) addr2 is. EAPOL-Key frames say which handshake message they are through the key-information bits: the AP's messages set ACK (M3 also sets Install), and the client's M4 sets Secure while M2 doesn't. A wrong passphrase shows up as M1 and M2 repeating with no M3, because the AP can't verify M2's MIC.",
            "gotchas": [],
            "best": "Keep a library of small synthetic captures, one per scenario (good join, slow DHCP, wrong passphrase, failed roam), alongside a few real ones from the lab. Make every timing in a synthetic capture a deliberate round number so the expected KPIs are obvious.",
        },
        {
            "title": "The analyzer: one pass, a state machine per client",
            "filename": "pcapkpi.py",
            "local_only": SCAPY,
            "files": {"make_capture.py": plain(CAPTURE)},
            "concept": "`analyse()` walks the frames once in time order. For each frame it works out the client and BSSID from the address fields, counts data frames and retries, and advances a small per-client state machine: authentication or reassociation starts an attempt, the 4-way handshake progresses it, M4 completes a roam, DHCP ACK completes a join, and a deauthentication before completion records a failure with the stage it reached and the reason code. `verdict()` applies limits kept as data and returns a list of problems; the CLI prints JSON, the problems, and exits 1 if there are any.",
            "why": "Join time, roam time and failure stage are the KPIs Wi-Fi teams argue about, and they are tedious to read off Wireshark by hand for every client in every run. With the analyzer in the pipeline, a capture becomes a JSON artifact and a pass/fail line, and \"slow join\" becomes \"DHCP took 130 of the 180 ms\".",
            "syntax": "report = analyse(rdpcap(\"lab.pcap\"))\nproblems = verdict(report, {**LIMITS, \"roam_ms\": 30})",
            "code": ANALYZER,
            "under": "Keeping state per client in `pending` (attempt in progress) and `serving` (current AP) is what lets one pass handle many interleaved clients. Every attempt ends in exactly one place: a join, a roam, a failure, or \"capture ended\". That's how you avoid the classic analyzer bug of silently dropping attempts that never finished. The retry rate is only judged with enough traffic (`min_frames`), because 1 retry in 3 frames is 33% and means nothing.",
            "gotchas": [],
            "best": "Separate parsing (frames to events), analysis (events to KPIs) and policy (KPIs to verdict), keep thresholds in data, emit JSON that can be archived and compared between builds, and make the exit code the CI contract. For multi-gigabyte captures, swap `rdpcap` for `PcapReader` to stream, or pre-filter with tshark.",
        },
        {
            "title": "Tests against the known scenario",
            "runner": "pytest",
            "filename": "tests/test_pcapkpi.py",
            "local_only": SCAPY,
            "files": {"make_capture.py": plain(CAPTURE), "pcapkpi.py": plain(ANALYZER), "pytest.ini": "[pytest]\npythonpath = .\n"},
            "args": ["-v"],
            "concept": "A module-scoped fixture writes the capture once to a temporary directory and analyses it through the real pcap format; the tests then check exact numbers for the happy path, the wrong-passphrase failure (stage and reason code), the retry count and rate, that the policy is configurable (parametrized over both sides of the threshold), and an edge case built in memory: a capture that ends while the client is still waiting for DHCP.",
            "why": "The state machine has many paths, and each Wi-Fi bug report adds one. Exact-number tests on a known capture mean that when you add support for FT roaming or SAE, you find out immediately if join timings for the old cases changed.",
            "syntax": "@pytest.fixture(scope=\"module\")\ndef report(tmp_path_factory):\n    path = tmp_path_factory.mktemp(\"cap\") / \"lab.pcap\"",
            "code": PCAP_TESTS,
            "under": "`tmp_path_factory` is the session-level way to get a temporary directory, needed because `tmp_path` is function-scoped and can't be used by a module-scoped fixture. Passing frames straight to `analyse()` in the last test works because the analyzer only needs packet objects with `.time`: the file format is just one way to get them.",
            "gotchas": [],
            "best": "Write one test per scenario with exact expected values, at least one test through the real file format, and parametrize policy tests over both sides of each threshold. When a real-world capture reveals a bug, shrink it into a new synthetic scenario and add a test.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Fleet summary: given the analyzer's JSON for several clients, print the median and worst join time, the worst roam time, and the number of failed joins.",
            "solution": "Flatten the per-client lists, then use `statistics.median` and `max`.",
            "solution_code": """import statistics

report = {
    "a4:5e:60:11:22:33": {"joins": [{"join_ms": 180.0}], "roams": [{"roam_ms": 19.0}, {"roam_ms": 42.5}], "failed": []},
    "f0:18:98:44:55:66": {"joins": [], "roams": [], "failed": [{"stage": "4-way", "reason": 15}]},
    "70:3a:cb:00:00:09": {"joins": [{"join_ms": 95.2}, {"join_ms": 410.0}], "roams": [], "failed": []},
}
joins = [j["join_ms"] for c in report.values() for j in c["joins"]]
roams = [r["roam_ms"] for c in report.values() for r in c["roams"]]
print(f"joins: median {statistics.median(joins)} ms, worst {max(joins)} ms")
print(f"worst roam: {max(roams)} ms")
print("failed joins:", sum(len(c["failed"]) for c in report.values()))""",
        },
        {
            "level": "Medium",
            "prompt": "Make failures readable: map IEEE 802.11 deauthentication reason codes to text and add a likely-cause hint per failure stage (e.g. a 4-way failure with reason 15 usually means a wrong passphrase).",
            "solution": "Two lookup tables (reason text and stage hints) and a formatter; keep unknown codes visible rather than hiding them.",
            "solution_code": """REASONS = {1: "unspecified", 2: "previous authentication no longer valid", 3: "station leaving",
           4: "inactivity", 8: "station leaving BSS", 14: "MIC failure", 15: "4-way handshake timeout",
           16: "group key handshake timeout", 23: "802.1X authentication failed"}
HINTS = {"4-way": "check the passphrase / PMK on both sides", "dhcp": "check the DHCP server and VLAN",
         "assoc": "check capabilities (security mode, PMF, band)", "auth": "check MAC filters and auth mode"}
failures = [{"sta": "f0:18:98:44:55:66", "stage": "4-way", "reason": 15},
            {"sta": "70:3a:cb:00:00:09", "stage": "dhcp", "reason": None},
            {"sta": "02:11:22:33:44:55", "stage": "assoc", "reason": 99}]
for f in failures:
    why = REASONS.get(f["reason"], f"reason {f['reason']}") if f["reason"] is not None else "capture ended"
    print(f"{f['sta']}: failed at {f['stage']} ({why}); hint: {HINTS.get(f['stage'], 'n/a')}")""",
        },
        {
            "level": "Hard",
            "prompt": "Detect retry bursts: from a time-ordered list of (time, retry flag) for one client, report windows of 10 consecutive frames where more than half were retries (a burst usually lines up with interference or a rate-adaptation problem, which an average retry rate hides).",
            "solution": "Slide a fixed-size window with a deque, keep a running count, and merge overlapping hot windows into one burst.",
            "solution_code": """from collections import deque

frames = [(round(i * 0.01, 2), i in range(30, 42) and i % 3 != 0) for i in range(80)]
window, hot, bursts = deque(), 0, []
for t, retry in frames:
    window.append((t, retry))
    hot += retry
    if len(window) > 10:
        hot -= window.popleft()[1]
    if len(window) == 10 and hot > 5:
        start = window[0][0]
        if bursts and start <= bursts[-1][1]:
            bursts[-1][1] = t
        else:
            bursts.append([start, t])
print("average retry rate:", f"{sum(r for _, r in frames) / len(frames):.0%}")
for start, end in bursts:
    print(f"retry burst from {start:.2f}s to {end:.2f}s")""",
        },
    ],
    "interview": [
        {"level": "Advanced", "q": "How would you measure client join time from a capture, and what can make the number wrong?", "a": "Track each client from the first authentication request through association, the 4-way handshake (M1 to M4) and DHCP ACK, keeping a per-client state machine. Errors come from missed frames in monitor mode (capture on the right channel, close to the client), multiple attempts interleaving, clock jumps, roams being counted as joins, and attempts that never finish being silently dropped.", "follow": "How would you handle FT (802.11r) roams? (No 4-way: the keys come with the FT auth/reassoc exchange, so the roam ends at reassociation response.)"},
        {"level": "Intermediate", "q": "A client can't connect and the capture shows M1/M2 repeating then deauth reason 15. What's going on?", "a": "The 4-way handshake times out: the AP can't validate M2's MIC, which almost always means the client and AP derived different PMKs, i.e. a wrong passphrase (or a mismatched PSK/SAE configuration).", "follow": "What would an SAE failure look like instead? (Failing SAE commit/confirm in the authentication frames, before association.)"},
    ],
    "quiz": [
        {"q": "In a To-DS data frame the BSSID is in...", "options": ["addr1", "addr2", "addr3", "addr4"], "answer": 0, "why": "To-DS: receiver is the AP."},
        {"q": "Which 4-way message sets ACK and Install?", "options": ["M1", "M2", "M3", "M4"], "answer": 2, "why": "M3 tells the client to install the key."},
        {"q": "Why judge retry rate only above a minimum frame count?", "options": ["Speed", "Small samples give meaningless percentages", "pcap limits", "Required by scapy"], "answer": 1, "why": "1 of 3 is 33%."},
    ],
    "cards": [
        {"front": "Join time", "back": "Auth req → assoc → M1..M4 → DHCP ACK; per-client state machine"},
        {"front": "Deauth reason 15", "back": "4-way handshake timeout: usually a wrong passphrase"},
        {"front": "Analyzer layering", "back": "Frames → events → KPIs → verdict (policy as data)"},
    ],
}


# --------------------------------------------------------------------------- 10.6
DASHBOARD = r'''"""dashboard: store test runs and show pass rates and KPI trends per firmware build."""  ## Module docstring
import os  ## Database URL from the environment
from datetime import datetime, timezone  ## Run timestamps
from typing import Literal  ## Restricted string values

from fastapi import Depends, FastAPI, HTTPException  ## pip install fastapi
from fastapi.responses import HTMLResponse  ## The dashboard page
from jinja2 import Environment  ## HTML templating
from pydantic import BaseModel, Field  ## Request validation
from sqlalchemy import ForeignKey, case, create_engine, func, select  ## pip install sqlalchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker  ## 2.0-style ORM
from sqlalchemy.pool import StaticPool  ## One shared connection for in-memory SQLite


class Base(DeclarativeBase):  ## Base class for the ORM models
    pass  ## Nothing to add


class Run(Base):  ## One pipeline run on one bench
    __tablename__ = "runs"  ## Table name
    id: Mapped[int] = mapped_column(primary_key=True)  ## Auto-increment key
    build: Mapped[str] = mapped_column(index=True)  ## Firmware under test
    bench: Mapped[str]  ## Which bench ran it
    started: Mapped[datetime]  ## When
    results: Mapped[list["Result"]] = relationship(back_populates="run", cascade="all, delete-orphan")  ## Its test results


class Result(Base):  ## One test outcome inside a run
    __tablename__ = "results"  ## Table name
    id: Mapped[int] = mapped_column(primary_key=True)  ## Key
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)  ## Parent run
    test: Mapped[str] = mapped_column(index=True)  ## Test node id or name
    outcome: Mapped[str]  ## passed / failed / skipped
    value: Mapped[float | None]  ## Optional KPI measurement, e.g. Mbps
    run: Mapped[Run] = relationship(back_populates="results")  ## Back-reference


engine = create_engine(os.environ.get("RESULTS_DB", "sqlite://"), connect_args={"check_same_thread": False}, poolclass=StaticPool)  ## Real use: sqlite:///results.db or Postgres
SessionLocal = sessionmaker(engine)  ## Session factory
Base.metadata.create_all(engine)  ## Create tables if missing (use Alembic migrations in production)


def get_db():  ## Dependency: one session per request
    with SessionLocal() as db:  ## Closed after the response
        yield db  ## Handed to the route


class ResultIn(BaseModel):  ## Incoming result
    test: str = Field(min_length=1)  ## Non-empty
    outcome: Literal["passed", "failed", "skipped"]  ## Anything else is a 422
    value: float | None = None  ## Optional measurement


class RunIn(BaseModel):  ## Incoming run (what CI posts)
    build: str = Field(pattern=r"^\d+\.\d+\.\d+(-b\d+)?$")  ## e.g. 7.4.2 or 7.4.2-b003
    bench: str  ## Bench name
    results: list[ResultIn] = Field(min_length=1)  ## At least one result


app = FastAPI(title="Wi-Fi results")  ## The application


@app.post("/api/runs", status_code=201)  ## CI uploads here
def create_run(body: RunIn, db: Session = Depends(get_db)) -> dict:  ## Validated body + session
    run = Run(build=body.build, bench=body.bench, started=datetime.now(timezone.utc),  ## Parent row
              results=[Result(**r.model_dump()) for r in body.results])  ## Children via the relationship
    db.add(run)  ## Stage
    db.commit()  ## Write (one transaction for the run and all its results)
    return {"id": run.id, "results": len(run.results)}  ## What was stored


def build_summary(db: Session) -> list[dict]:  ## Pass rate per build, oldest first
    executed = func.sum(case((Result.outcome != "skipped", 1), else_=0))  ## Skips don't count
    passed = func.sum(case((Result.outcome == "passed", 1), else_=0))  ## Passes
    rows = db.execute(select(Run.build, executed, passed).join(Run.results).group_by(Run.build).order_by(func.min(Run.id)))  ## One SQL query
    return [{"build": b, "executed": e, "passed": p, "pass_rate": round(100 * p / e, 1) if e else None} for b, e, p in rows]  ## Plain dicts


@app.get("/api/builds")  ## JSON for other tools
def builds(db: Session = Depends(get_db)) -> list[dict]:  ## Session injected
    return build_summary(db)  ## Same data the page shows


@app.get("/api/tests/{test}/trend")  ## One KPI across builds
def trend(test: str, db: Session = Depends(get_db)) -> list[dict]:  ## Path parameter
    rows = db.execute(select(Run.build, Result.outcome, Result.value).join(Result.run).where(Result.test == test).order_by(Run.id)).all()  ## Chronological
    if not rows:  ## Unknown test
        raise HTTPException(404, f"no results for {test!r}")  ## Clear error
    return [{"build": b, "outcome": o, "value": v} for b, o, v in rows]  ## Series


PAGE = Environment(autoescape=True).from_string("""<!doctype html><title>Wi-Fi results</title>
<style>body{font:14px system-ui;margin:20px;color:#1d2433} table{border-collapse:collapse} td,th{padding:4px 10px;border-bottom:1px solid #e3e6ec;text-align:left}
.bar{background:#e3e6ec;width:160px;height:10px;border-radius:5px} .bar i{display:block;height:10px;border-radius:5px;background:#2f855a} .low i{background:#c53030}</style>
<h2>Pass rate by firmware build</h2><table><tr><th>Build</th><th>Executed</th><th>Passed</th><th>Pass rate</th><th></th></tr>
{% for r in rows %}<tr><td>{{ r.build }}</td><td>{{ r.executed }}</td><td>{{ r.passed }}</td><td>{{ r.pass_rate }}%</td>
<td><div class="bar {{ 'low' if r.pass_rate < 90 }}"><i style="width:{{ r.pass_rate }}%"></i></div></td></tr>{% endfor %}</table>
<h3>Failing in {{ latest }}</h3><ul>{% for t in failing %}<li>{{ t }}</li>{% else %}<li>none</li>{% endfor %}</ul>""")  ## Template (autoescaped)


@app.get("/", response_class=HTMLResponse)  ## The page people open
def page(db: Session = Depends(get_db)) -> str:  ## Returns HTML text
    rows = build_summary(db)  ## Table data
    latest = rows[-1]["build"] if rows else "-"  ## Newest build
    failing = db.scalars(select(Result.test).join(Result.run).where(Run.build == latest, Result.outcome == "failed").distinct()).all()  ## What broke
    return PAGE.render(rows=rows, latest=latest, failing=failing)  ## Fill the template


if __name__ == "__main__":  ## Demo: in-process client, no server needed (real use: uvicorn dashboard:app)
    from fastapi.testclient import TestClient  ## pip install httpx
    from playwright.sync_api import sync_playwright  ## Screenshot of the page
    client = TestClient(app)  ## Calls the app directly
    for build, fails in [("7.4.0", []), ("7.4.1", ["test_roam_ft"]), ("7.4.2-b003", ["test_roam_ft", "test_rvr_5g_42db"])]:  ## Three nightly runs
        tests = ["test_join_wpa3", "test_roam_ft", "test_rvr_5g_42db", "test_dfs_switch"]  ## Same suite each night
        results = [{"test": t, "outcome": "failed" if t in fails else "passed", "value": 171.2 - 18 * len(fails) if "rvr" in t else None} for t in tests]  ## Fake outcomes
        results.append({"test": "test_6g_psc", "outcome": "skipped"})  ## Bench without 6 GHz
        print(client.post("/api/runs", json={"build": build, "bench": "lab-07", "results": results}).json())  ## Upload
    print(client.get("/api/builds").json())  ## Summary
    print(client.get("/api/tests/test_rvr_5g_42db/trend").json())  ## One KPI over time
    bad = client.post("/api/runs", json={"build": "nightly", "bench": "lab-07", "results": []})  ## Two invalid fields
    print(bad.status_code, [e["loc"][-1] for e in bad.json()["detail"]])  ## 422 with one error per field
    with sync_playwright() as p:  ## Render the HTML page to an image
        tab = p.chromium.launch().new_page(viewport={"width": 640, "height": 330})  ## Small viewport
        tab.set_content(client.get("/").text)  ## The real page
        tab.screenshot(path="dashboard.png")  ## Shown below'''

DASH_TESTS = r'''import pytest  ## Test framework
from fastapi.testclient import TestClient  ## In-process HTTP client
from sqlalchemy import create_engine  ## Fresh database per test
from sqlalchemy.orm import sessionmaker  ## Session factory
from sqlalchemy.pool import StaticPool  ## Keep the in-memory DB alive across connections

from dashboard import Base, app, get_db  ## App and the dependency to replace


@pytest.fixture  ## New, empty database for every test
def client():  ## Yields a TestClient
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)  ## In-memory
    Base.metadata.create_all(engine)  ## Tables
    TestSession = sessionmaker(engine)  ## Bound to this engine

    def override():  ## Replacement for get_db
        with TestSession() as db:  ## Same shape as the real dependency
            yield db  ## Handed to routes

    app.dependency_overrides[get_db] = override  ## Swap it in
    yield TestClient(app)  ## Test runs here
    app.dependency_overrides.clear()  ## Undo, so tests stay independent


def upload(client, build, outcomes):  ## Helper: post one run
    results = [{"test": t, "outcome": o} for t, o in outcomes.items()]  ## Body
    response = client.post("/api/runs", json={"build": build, "bench": "lab-07", "results": results})  ## Call
    assert response.status_code == 201, response.text  ## Show the body if it fails
    return response.json()  ## Stored ids


def test_pass_rate_ignores_skips(client):  ## Business rule
    upload(client, "7.4.1", {"a": "passed", "b": "failed", "c": "skipped", "d": "passed"})  ## 2 of 3 executed
    assert client.get("/api/builds").json() == [{"build": "7.4.1", "executed": 3, "passed": 2, "pass_rate": 66.7}]  ## Exact


def test_builds_are_listed_oldest_first(client):  ## Ordering contract
    for build in ("7.4.0", "7.4.1", "7.4.2-b003"):  ## Uploaded in this order
        upload(client, build, {"a": "passed"})  ## One test each
    assert [r["build"] for r in client.get("/api/builds").json()] == ["7.4.0", "7.4.1", "7.4.2-b003"]  ## Same order


@pytest.mark.parametrize("body,field", [  ## Validation table
    ({"build": "nightly", "bench": "x", "results": [{"test": "a", "outcome": "passed"}]}, "build"),  ## Bad version string
    ({"build": "7.4.1", "bench": "x", "results": []}, "results"),  ## No results
    ({"build": "7.4.1", "bench": "x", "results": [{"test": "a", "outcome": "flaky"}]}, "outcome"),  ## Unknown outcome
])  ## Three cases
def test_invalid_uploads_are_rejected(client, body, field):  ## 422 names the field
    response = client.post("/api/runs", json=body)  ## Call
    assert response.status_code == 422  ## Validation error
    assert field in [e["loc"][-1] for e in response.json()["detail"]]  ## Pinpoints the problem


def test_unknown_test_trend_is_404(client):  ## Error path
    assert client.get("/api/tests/nope/trend").status_code == 404  ## Not a 500


def test_page_escapes_test_names(client):  ## Security: test names come from CI input
    upload(client, "7.4.1", {"<script>alert(1)</script>": "failed"})  ## Hostile name
    html = client.get("/").text  ## Rendered page
    assert "<script>alert" not in html and "&lt;script&gt;" in html  ## Autoescaped'''

M_10_6 = {
    "id": "10.6",
    "title": "FastAPI Results Dashboard",
    "hours": 5,
    "summary": "Capstone: a results service CI uploads to: SQLAlchemy models for runs and results, validated FastAPI endpoints, pass-rate and KPI-trend queries done in SQL, an autoescaped HTML dashboard, and tests that swap in a fresh database per test with dependency overrides.",
    "concepts": [
        {
            "title": "The service: models, API, queries, page",
            "filename": "dashboard.py",
            "local_only": DASH_SHOT,
            "capture": "dashboard.png",
            "image_alt": "Results dashboard table showing pass rate per firmware build with green and red bars, and the failing tests in the newest build",
            "concept": "**Brief:** results live in hundreds of JUnit files on Jenkins and nobody can answer \"when did the 5 GHz range regress?\". Build a small service: CI posts each run as JSON; SQLAlchemy stores runs and results in two related tables; `/api/builds` returns pass rate per build (skips excluded) computed in one SQL query; `/api/tests/{test}/trend` returns one test's outcome and KPI across builds; `/` renders an HTML dashboard. **Skills used:** FastAPI routes and dependencies (6.x), pydantic validation, SQLAlchemy 2.0 ORM, Jinja2.",
            "why": "A dashboard turns per-run noise into trends: a pass rate dropping from 100% to 60% over three builds, or one KPI sliding a few Mbps per build, is obvious in a table and invisible in individual Jenkins runs. The JSON endpoints let the release checklist and chat bots ask the same questions.",
            "syntax": "@app.post(\"/api/runs\", status_code=201)\ndef create_run(body: RunIn, db: Session = Depends(get_db)) -> dict: ...\nselect(Run.build, func.sum(...)).join(Run.results).group_by(Run.build)",
            "code": DASHBOARD,
            "under": "`get_db` is a generator dependency: FastAPI runs it up to `yield` before the route and finishes it (closing the session) after the response, which is also what makes it swappable in tests. Aggregating with `func.sum(case(...))` lets the database do the counting instead of loading every result into Python. `StaticPool` is only needed for in-memory SQLite (every connection must be the same one or each would see an empty database); with a file or Postgres URL you'd use the default pool. Jinja's `autoescape=True` matters because test names and messages come from CI input.",
            "gotchas": [],
            "best": "Validate everything CI sends (pydantic patterns and literals), store raw results and compute summaries in queries, add indexes on the columns you filter by (build, test), use migrations (Alembic) once the schema is shared, and protect the upload endpoint with a token in a real deployment.",
        },
        {
            "title": "Testing it with a fresh database per test",
            "runner": "pytest",
            "filename": "tests/test_dashboard.py",
            "local_only": DASH,
            "files": {"dashboard.py": plain(DASHBOARD).split('\nif __name__ == "__main__":')[0] + "\n", "pytest.ini": "[pytest]\npythonpath = .\nfilterwarnings =\n    ignore:The anyio.abc.BlockingPortal alias:DeprecationWarning\n"},
            "args": ["-v"],
            "concept": "The `client` fixture creates an in-memory database, then uses `app.dependency_overrides[get_db]` to make every route use it, and clears the override afterwards. Each test therefore starts empty and can assert exact numbers. The tests cover the pass-rate rule (skips excluded), ordering, a parametrized table of invalid uploads that must return 422 naming the right field, the 404 path, and that hostile test names are escaped in the HTML.",
            "why": "The dashboard is what people use to decide whether a build ships. A bug in the pass-rate query (counting skips, say) quietly changes release decisions, so the business rules deserve exact tests, and the validation tests stop a broken CI job from filling the database with junk.",
            "syntax": "app.dependency_overrides[get_db] = override\nyield TestClient(app)\napp.dependency_overrides.clear()",
            "code": DASH_TESTS,
            "under": "Overriding the dependency rather than the global engine keeps the test isolated: nothing the test does touches the module's default database. `assert response.status_code == 201, response.text` puts the response body in the failure message, which saves a debugging round when a validation rule rejects the test's own data.",
            "gotchas": [],
            "best": "Give each test its own database (or a transaction rolled back at the end), assert exact JSON for business rules, cover each validation rule with a parametrized case, and include at least one security-flavoured test (escaping, auth) for anything rendered in a browser.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Using the summary rows the API returns, print each build whose pass rate dropped by more than 5 points compared with the previous build.",
            "solution": "Pair each row with the previous one using `zip(rows, rows[1:])`.",
            "solution_code": """rows = [{"build": "7.4.0", "pass_rate": 100.0}, {"build": "7.4.1", "pass_rate": 96.0},
        {"build": "7.4.2-b001", "pass_rate": 88.5}, {"build": "7.4.2-b003", "pass_rate": 90.0}]
for prev, cur in zip(rows, rows[1:]):
    drop = prev["pass_rate"] - cur["pass_rate"]
    if drop > 5:
        print(f"{cur['build']}: pass rate {cur['pass_rate']}% ({-drop:+.1f} points vs {prev['build']})")""",
        },
        {
            "level": "Medium",
            "prompt": "Write the CI side: convert a JUnit XML report into the JSON body `/api/runs` expects (passed/failed/skipped per test case, errors counted as failed).",
            "solution": "Parse with ElementTree; a testcase's outcome comes from whether it has a failure, error or skipped child.",
            "solution_code": """import json
import xml.etree.ElementTree as ET

JUNIT = '''<testsuite name="pytest" tests="4"><testcase classname="tests.test_join" name="test_join_wpa3"/>
<testcase classname="tests.test_roam" name="test_roam_ft"><failure message="roam took 81 ms"/></testcase>
<testcase classname="tests.test_rvr" name="test_rvr_5g_42db"><error message="attenuator timeout"/></testcase>
<testcase classname="tests.test_band" name="test_6g_psc"><skipped message="bench has no 6G radio"/></testcase></testsuite>'''

def outcome(case):
    if case.find("failure") is not None or case.find("error") is not None:
        return "failed"
    return "skipped" if case.find("skipped") is not None else "passed"

body = {"build": "7.4.2-b003", "bench": "lab-07",
        "results": [{"test": c.get("name"), "outcome": outcome(c)} for c in ET.fromstring(JUNIT).iter("testcase")]}
print(json.dumps(body, indent=1))""",
        },
        {
            "level": "Hard",
            "prompt": "Add flakiness detection: from the outcome history of each test across recent builds, flag tests that flip between passed and failed at least twice (a flip-rate signal) and separate them from tests that started failing and stayed failed (a regression).",
            "solution": "Count transitions between consecutive executed outcomes; a regression is a single pass-to-fail transition that persists to the latest build.",
            "solution_code": """history = {
    "test_join_wpa3": ["passed", "passed", "passed", "passed", "passed"],
    "test_roam_ft": ["passed", "failed", "passed", "failed", "passed"],
    "test_rvr_5g_42db": ["passed", "passed", "failed", "failed", "failed"],
    "test_dfs_switch": ["passed", "skipped", "failed", "passed", "failed"],
}
for test, outcomes in history.items():
    ran = [o for o in outcomes if o != "skipped"]
    flips = sum(a != b for a, b in zip(ran, ran[1:]))
    if flips >= 2:
        print(f"{test}: flaky ({flips} flips in {len(ran)} runs)")
    elif flips == 1 and ran[-1] == "failed":
        print(f"{test}: regression since run {len(ran) - ran[::-1].index('passed') + 1}")""",
        },
    ],
    "interview": [
        {"level": "Advanced", "q": "Design a test results service for a Wi-Fi team.", "a": "CI posts validated run documents (build, bench, environment, per-test outcome and KPIs) to an API; a relational schema with runs and results (indexed by build and test) plus raw artifacts in object storage; summaries computed in SQL; endpoints for pass rate per build, per-test history, KPI trends and flakiness; a simple HTML dashboard; auth on upload, retention policies, and migrations.", "follow": "How do you keep it fast as results grow? (Indexes, pre-aggregated tables per build, pagination, retention.)"},
        {"level": "Intermediate", "q": "How do you test a FastAPI app that uses a database?", "a": "Use TestClient in-process and override the session dependency with one bound to a fresh test database (in-memory SQLite or a transaction rolled back per test), so each test starts from a known state and asserts exact results.", "follow": "Why not mock the session? (You'd test your mocks, not your queries.)"},
    ],
    "quiz": [
        {"q": "What does `app.dependency_overrides[get_db] = f` do?", "options": ["Deletes get_db", "Routes use f instead of get_db", "Caches get_db", "Nothing in tests"], "answer": 1, "why": "Swap dependencies in tests."},
        {"q": "Why StaticPool with `sqlite://`?", "options": ["Speed", "Each new connection would get its own empty in-memory DB", "Thread safety only", "Required by FastAPI"], "answer": 1, "why": "One shared connection."},
        {"q": "A pydantic Literal field given an unknown value returns...", "options": ["200", "400", "422", "500"], "answer": 2, "why": "Validation error."},
    ],
    "cards": [
        {"front": "Generator dependency", "back": "Code before yield runs before the route; after yield runs after the response"},
        {"front": "Test DB isolation", "back": "dependency_overrides + fresh engine per test; clear overrides after"},
        {"front": "Aggregate in SQL", "back": "func.sum(case((cond, 1), else_=0)) with group_by"},
    ],
}


# --------------------------------------------------------------------------- 10.7
JENKINSFILE = r'''pipeline {  ## Declarative pipeline: the whole CI flow, versioned with the code
    agent none  ## Each stage chooses its own machine
    options {  ## Pipeline-wide settings
        timestamps()  ## Timestamp every log line
        timeout(time: 6, unit: 'HOURS')  ## Kill a hung nightly run
        buildDiscarder(logRotator(numToKeepStr: '30'))  ## Keep the last 30 builds
        disableConcurrentBuilds()  ## One run per branch at a time
    }
    parameters {  ## Shown on "Build with Parameters"
        choice(name: 'SUITE', choices: ['smoke', 'regression', 'rvr'], description: 'pytest marker to run')  ## Test selection
        string(name: 'FIRMWARE', defaultValue: 'latest', description: 'Firmware build under test')  ## DUT image
        booleanParam(name: 'FLASH', defaultValue: true, description: 'Flash the AP before testing')  ## Skip when re-running
    }
    triggers { cron(env.BRANCH_NAME == 'main' ? 'H 1 * * *' : '') }  ## Nightly on main only; H spreads the start minute
    stages {  ## In order; a failed stage stops the ones after it
        stage('Lint and unit tests') {  ## Fast feedback, no hardware
            agent { docker { image 'python:3.12-slim' } }  ## Clean, reproducible container
            steps {  ## Shell commands
                sh 'pip install -e ".[dev]"'  ## Project plus dev tools
                sh 'ruff check . && ruff format --check . && mypy src'  ## Style and type gates
                sh 'pytest tests/unit -q --junitxml=reports/unit.xml --cov=wifilab --cov-report=xml'  ## Unit tests with coverage
            }
            post { always { junit 'reports/unit.xml' } }  ## Publish results even when tests fail
        }
        stage('Select tests') {  ## Decide what the lab must run
            agent { docker { image 'python:3.12-slim' } }  ## No hardware needed
            steps {  ## Ask ci.py
                script {  ## Groovy logic
                    env.MARKERS = sh(script: "git diff --name-only origin/main...HEAD | python ci.py select --suite ${params.SUITE}", returnStdout: true).trim()  ## e.g. "smoke or rf"
                }
                echo "Lab markers: ${env.MARKERS}"  ## Visible in the log
            }
        }
        stage('Lab tests') {  ## Needs a real bench
            when { expression { env.MARKERS } }  ## Skip entirely for docs-only changes
            agent { label 'wifi-bench' }  ## Only machines wired to test equipment
            options { lock(label: 'bench', quantity: 1, variable: 'BENCH') }  ## Reserve one free bench (Lockable Resources plugin)
            steps {  ## The long part
                withCredentials([usernamePassword(credentialsId: 'ap-admin', usernameVariable: 'AP_USER', passwordVariable: 'AP_PASS')]) {  ## Secrets as masked env vars
                    sh 'python -m venv .venv && .venv/bin/pip install -q -e .'  ## Framework on the bench host
                    sh '.venv/bin/python ci.py preflight --bench "$BENCH"'  ## Health check (10.2): fail fast, not after 3 hours
                    script {  ## Conditional and exit-code logic
                        if (params.FLASH) { sh ".venv/bin/python ci.py flash --bench \"\$BENCH\" --firmware ${params.FIRMWARE}" }  ## Optional flashing
                        def rc = sh(returnStatus: true, script: '.venv/bin/pytest -m "$MARKERS" --bench "$BENCH" --junitxml=reports/lab.xml')  ## Don't abort on test failures
                        if (rc > 1) { error("pytest could not run properly (exit ${rc})") }  ## 1 = tests failed; 2-5 = interrupted, internal, usage or no tests
                    }
                }
            }
            post {  ## Runs after the stage, whatever happened
                always {  ## Every time
                    junit testResults: 'reports/lab.xml', allowEmptyResults: true  ## Failed tests mark the build UNSTABLE (yellow), not FAILED (red)
                    archiveArtifacts artifacts: 'reports/**, logs/**, captures/*.pcap', allowEmptyArchive: true  ## Keep evidence
                    sh '.venv/bin/python ci.py summary reports/lab.xml > summary.md || true'  ## Triage summary (never fails the post step)
                    sh '.venv/bin/python ci.py upload reports/lab.xml --build "$FIRMWARE" --bench "$BENCH" || true'  ## Results dashboard (10.6)
                }
                unstable { slackSend(channel: '#wifi-ci', color: 'warning', message: readFile('summary.md')) }  ## Test failures: tell the team
                failure { slackSend(channel: '#wifi-ci', color: 'danger', message: "Lab stage broke: ${env.BUILD_URL}") }  ## Infrastructure problem
            }
        }
    }
}'''

CI_PY = r'''"""ci.py: the Python side of the pipeline: test selection, JUnit merge, triage summary."""  ## Keep logic in Python, not Groovy
import re  ## Failure-message normalisation
import xml.etree.ElementTree as ET  ## JUnit XML
from collections import defaultdict  ## Grouping

AREAS = {"src/wifilab/rf/": "rf", "src/wifilab/roam/": "roam", "src/wifilab/security/": "security", "tests/lab/": "smoke"}  ## Path prefix -> pytest marker
NO_LAB = ("docs/", "README", ".github/", "tests/unit/")  ## Changes that don't need hardware


def select(changed, suite="smoke"):  ## Which markers the lab stage should run
    relevant = [f for f in changed if not f.startswith(NO_LAB)]  ## Ignore docs and unit-only changes
    if not relevant:  ## Nothing hardware-related changed
        return ""  ## Empty = skip the lab stage
    markers = {suite} | {m for f in relevant for prefix, m in AREAS.items() if f.startswith(prefix)}  ## Requested suite + affected areas
    return " or ".join(sorted(markers))  ## A pytest -m expression


def parse_junit(xml_text):  ## Counts and failures from one JUnit file
    root = ET.fromstring(xml_text)  ## <testsuites> or <testsuite>
    counts, failures = defaultdict(int), []  ## Results
    for case in root.iter("testcase"):  ## Every test
        name = f"{case.get('classname')}::{case.get('name')}"  ## Unique id
        problem = case.find("failure") if case.find("failure") is not None else case.find("error")  ## Failure or error element
        if problem is not None:  ## Did not pass
            counts["failed"] += 1  ## Count
            failures.append((name, problem.get("message", "")))  ## Keep the message for triage
        elif case.find("skipped") is not None:  ## Skipped
            counts["skipped"] += 1  ## Count
        else:  ## Passed
            counts["passed"] += 1  ## Count
    return counts, failures  ## Both


def signature(message):  ## Normalise so similar failures group together
    message = re.sub(r"0x[0-9a-f]+|\b[0-9a-f]{2}(:[0-9a-f]{2}){5}\b", "<id>", message.lower())  ## Addresses and MACs
    return re.sub(r"\d+(\.\d+)?", "N", message)[:80]  ## Numbers vary run to run


def summary(reports):  ## Markdown for chat, plus an exit code
    total, groups = defaultdict(int), defaultdict(list)  ## Merged counts / failures by signature
    for xml_text in reports:  ## Merge several JUnit files (shards, benches)
        counts, failures = parse_junit(xml_text)  ## One file
        for key, n in counts.items():  ## Add up
            total[key] += n  ## Merge
        for name, message in failures:  ## Group
            groups[signature(message)].append(name)  ## Same cause, same bucket
    lines = [f"**{total['passed']} passed, {total['failed']} failed, {total['skipped']} skipped**"]  ## Headline
    for sig, names in sorted(groups.items(), key=lambda kv: -len(kv[1])):  ## Biggest group first
        lines.append(f"- {len(names)} x `{sig}` e.g. {names[0]}")  ## One line per cause
    return "\n".join(lines), (1 if total["failed"] else 0)  ## Text and exit code


if __name__ == "__main__":  ## Demo with inline data (the pipeline passes real files)
    print("PR touching docs only ->", repr(select(["docs/roaming.md", "README.md"])))  ## Lab skipped
    print("PR touching roaming ->", repr(select(["src/wifilab/roam/ft.py", "docs/roaming.md"])))  ## smoke + roam
    print("nightly regression ->", repr(select(["src/wifilab/rf/rvr.py"], suite="regression")))  ## regression + rf
    shard1 = """<testsuite><testcase classname="tests.lab.test_roam" name="test_ft_roam[5G]"><failure message="roam took 81.4 ms (limit 50)"/></testcase>
<testcase classname="tests.lab.test_roam" name="test_ft_roam[6G]"><failure message="roam took 77.0 ms (limit 50)"/></testcase>
<testcase classname="tests.lab.test_join" name="test_join_wpa3"/></testsuite>"""  ## Bench 1 results
    shard2 = """<testsuite><testcase classname="tests.lab.test_rvr" name="test_rvr[5G-42dB]"><error message="attenuator at 0x7f3a timeout after 5 s"/></testcase>
<testcase classname="tests.lab.test_band" name="test_6g_psc"><skipped message="no 6G radio"/></testcase>
<testcase classname="tests.lab.test_join" name="test_join_wpa2"/></testsuite>"""  ## Bench 2 results
    text, code = summary([shard1, shard2])  ## Merge and triage
    print(text)  ## What goes to chat
    print("exit code:", code)  ## Non-zero when anything failed'''

M_10_7 = {
    "id": "10.7",
    "title": "Full Jenkins Pipeline",
    "hours": 4,
    "summary": "Capstone: the pipeline that ties the capstones together: lint and unit tests in a container, change-based test selection, a bench reserved with a lock, pre-flight health check, optional flashing, lab tests with correct exit-code handling, JUnit publishing, artifacts, a triage summary to chat, and upload to the results dashboard.",
    "concepts": [
        {
            "title": "The Jenkinsfile",
            "runner": "none",
            "lang": "Groovy",
            "filename": "Jenkinsfile",
            "concept": "**Brief:** wire everything into one pipeline. Fast checks (ruff, mypy, unit tests) run in a throwaway Python container on every change. A selection stage asks `ci.py` which pytest markers the change needs, and docs-only changes skip the lab. The lab stage runs on a machine labelled `wifi-bench`, reserves a free bench with a lock, injects credentials, runs the pre-flight health check, optionally flashes firmware, and runs pytest with `returnStatus` so test failures mark the build unstable while infrastructure errors fail it. Post steps always publish JUnit, archive logs and captures, post a triage summary to chat and upload results to the dashboard. **Skills used:** Jenkins declarative syntax (8.x), pytest markers and exit codes, the 10.2, 10.3 and 10.6 capstones.",
            "why": "Bench time is the scarce resource. This layout spends it only when needed (selection), never on a broken bench (pre-flight), never on code that fails lint (stage order), and never loses the evidence of a failure (post always). Distinguishing unstable (tests found bugs) from failed (pipeline broke) tells people whether to look at the firmware or at the lab.",
            "syntax": "stage('Lab tests') {\n    agent { label 'wifi-bench' }\n    options { lock(label: 'bench', quantity: 1, variable: 'BENCH') }\n    steps { ... }\n    post { always { junit 'reports/lab.xml' } }\n}",
            "code": JENKINSFILE,
            "under": "With `agent none` at the top, each stage gets its own executor, so the lab node isn't held while lint runs in Docker. `lock(label:, quantity: 1, variable:)` from the Lockable Resources plugin waits until a resource with that label is free and puts its name in `BENCH`; the lock is released when the stage ends, even on failure. `sh(returnStatus: true)` returns pytest's exit code instead of throwing, which is what lets 1 (test failures) and 2-5 (interrupted, internal error, usage error, no tests collected) be handled differently. The `junit` step then marks the build UNSTABLE if any test failed. Keeping logic in `ci.py` rather than Groovy means it is testable with pytest and runnable on a laptop.",
            "gotchas": [],
            "best": "Order stages cheapest-first, keep the Jenkinsfile thin and the logic in Python, lock shared hardware, run a pre-flight check before long suites, use `post { always }` for results and artifacts, use credentials bindings (never echo secrets), and make nightly-only behaviour depend on the branch or trigger, not on a copied job.",
        },
        {
            "title": "ci.py: selection, merge and triage in testable Python",
            "filename": "ci.py",
            "concept": "`select()` maps changed paths to pytest markers (docs and unit-only changes need no lab), `parse_junit()` turns a JUnit file into counts and failure messages, and `summary()` merges several files (benches, shards), groups failures by a normalised signature (numbers, hex addresses and MACs replaced) and returns markdown for chat plus an exit code. The demo shows three selection decisions and a merged triage summary.",
            "why": "Twenty red tests with one root cause should read as one line in the morning, not twenty. Grouping by signature turns \"81.4 ms\" and \"77.0 ms\" roam failures into one bucket, so the person on triage duty knows there are two problems, not three.",
            "syntax": "git diff --name-only origin/main...HEAD | python ci.py select --suite smoke\npython ci.py summary reports/*.xml > summary.md",
            "code": CI_PY,
            "under": "The selection result is a pytest `-m` expression (`roam or smoke`), so it plugs straight into the marker system from 10.3; an empty string is the agreed signal to skip the stage. Signatures are lower-cased and truncated so trivial differences don't split groups. Errors (`<error>`, usually setup or infrastructure) and failures (`<failure>`, assertions) are both counted as failed here but keep their messages, so triage can still tell them apart.",
            "gotchas": [],
            "best": "Unit-test `ci.py` like any other module, keep the path-to-marker map next to the code it describes (or in CODEOWNERS-style config), always run a smoke subset even when selection finds nothing specific, and review the selection rules when a bug slips past them.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Map pytest exit codes to Jenkins outcomes: 0 → SUCCESS, 1 → UNSTABLE, 5 (no tests collected) → FAILURE with a hint about the marker expression, anything else → FAILURE.",
            "solution": "A small lookup with a default.",
            "solution_code": """MEANING = {0: ("SUCCESS", "all tests passed"), 1: ("UNSTABLE", "some tests failed"),
           2: ("FAILURE", "interrupted"), 3: ("FAILURE", "internal pytest error"),
           4: ("FAILURE", "usage error (bad option?)"), 5: ("FAILURE", "no tests collected: check the -m expression")}
for rc in (0, 1, 5, 137):
    result, why = MEANING.get(rc, ("FAILURE", f"killed or crashed (exit {rc})"))
    print(rc, result, "-", why)""",
        },
        {
            "level": "Medium",
            "prompt": "Shard a lab suite across benches: given test durations from the last run, split tests into N groups with roughly equal total time (greedy: longest first, into the currently shortest group).",
            "solution": "Sort by duration descending and always add to the group with the smallest total; a heap makes that O(n log k).",
            "solution_code": """import heapq

durations = {"test_rvr_5g": 1800, "test_rvr_6g": 1750, "test_roam_ft": 420, "test_roam_okc": 400,
             "test_dfs": 900, "test_join_wpa3": 60, "test_join_wpa2": 55, "test_band_steer": 300}
benches = 3
heap = [(0, i, []) for i in range(benches)]
for test, secs in sorted(durations.items(), key=lambda kv: -kv[1]):
    total, i, tests = heapq.heappop(heap)
    tests.append(test)
    heapq.heappush(heap, (total + secs, i, tests))
for total, i, tests in sorted(heap, key=lambda g: g[1]):
    print(f"bench {i}: {total / 60:.0f} min {tests}")""",
        },
        {
            "level": "Hard",
            "prompt": "Write pytest tests for `ci.select` and `ci.signature` (the functions are included in the test file so it runs standalone): docs-only changes skip the lab, area markers are added, and two roam failures with different numbers share a signature.",
            "runner": "pytest",
            "solution": "Parametrize the selection cases; assert signature equality for messages that differ only in numbers and inequality for different causes.",
            "solution_code": """import re

import pytest

AREAS = {"src/wifilab/rf/": "rf", "src/wifilab/roam/": "roam"}
NO_LAB = ("docs/", "README", "tests/unit/")


def select(changed, suite="smoke"):
    relevant = [f for f in changed if not f.startswith(NO_LAB)]
    if not relevant:
        return ""
    return " or ".join(sorted({suite} | {m for f in relevant for p, m in AREAS.items() if f.startswith(p)}))


def signature(message):
    message = re.sub(r"0x[0-9a-f]+", "<id>", message.lower())
    return re.sub(r"\\d+(\\.\\d+)?", "N", message)[:80]


@pytest.mark.parametrize("changed,expected", [
    (["docs/a.md", "README.md"], ""),
    (["src/wifilab/roam/ft.py"], "roam or smoke"),
    (["src/wifilab/rf/rvr.py", "src/wifilab/roam/ft.py"], "rf or roam or smoke"),
    (["setup.cfg"], "smoke"),
])
def test_select(changed, expected):
    assert select(changed) == expected


def test_same_cause_same_signature():
    assert signature("roam took 81.4 ms (limit 50)") == signature("Roam took 77 ms (limit 50)")


def test_different_cause_different_signature():
    assert signature("roam took 81 ms") != signature("attenuator at 0x7f timeout")""",
        },
    ],
    "interview": [
        {"level": "Advanced", "q": "Walk me through a CI pipeline for hardware-in-the-loop Wi-Fi testing.", "a": "Cheap checks first in containers (lint, types, unit tests); change-based test selection; lab stage on labelled bench agents with a lock per bench; pre-flight health check; firmware flash; pytest with markers and JUnit output, distinguishing test failures (unstable) from infrastructure failures (failed); post-always publishing of JUnit, logs and captures; triage summary to chat; results to a dashboard; nightly full regression on main via cron, PRs get smoke plus affected areas.", "follow": "How do you stop one broken bench from failing every run? (Pre-flight check, take the bench out of the lock pool automatically, retry on another bench.)"},
        {"level": "Intermediate", "q": "Why keep pipeline logic in Python scripts instead of the Jenkinsfile?", "a": "Python is testable with pytest, runnable locally, reviewable by the whole team, and portable to another CI system; Groovy in Jenkins is hard to test and runs in a sandbox with surprising restrictions.", "follow": "What stays in the Jenkinsfile? (Agents, stage order, credentials, locks, post actions: orchestration only.)"},
    ],
    "quiz": [
        {"q": "Failed tests should usually make the build...", "options": ["FAILED", "UNSTABLE", "ABORTED", "SUCCESS"], "answer": 1, "why": "junit marks unstable; red means the pipeline broke."},
        {"q": "`sh(returnStatus: true, ...)` returns...", "options": ["stdout", "The exit code instead of throwing", "Nothing", "A boolean"], "answer": 1, "why": "Lets you branch on pytest's code."},
        {"q": "pytest exit code 5 means...", "options": ["Tests failed", "Interrupted", "No tests collected", "Usage error"], "answer": 2, "why": "Often a wrong -m expression."},
    ],
    "cards": [
        {"front": "Stage order", "back": "Cheapest first: lint/unit → select → preflight → flash → lab → publish"},
        {"front": "lock(label:, quantity: 1, variable:)", "back": "Reserve one free bench; name in env var; released automatically"},
        {"front": "pytest exit codes", "back": "0 ok, 1 failures, 2 interrupted, 3 internal, 4 usage, 5 no tests"},
    ],
}
