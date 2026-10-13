"""Phase 7 content: modules 7.9-7.12 (parsing, config templating, Scapy)."""

from net_support import needs

TEXTFSM = needs("textfsm ntc-templates")
TTP = needs("ttp")
JINJA = needs("jinja2")
SCAPY = needs("scapy") + " (packets are only built and parsed offline here, never sent)"

AP_SUMMARY = """Number of APs: 3

AP Name       Slots  AP Model          Ethernet MAC    Radio MAC       Location   IP Address     State
--------------------------------------------------------------------------------------------------------
ap-lab-07     3      CW9166I-B         3c84.6a12.3456  3c84.6a12.3460  lab-7      10.10.30.7     Registered
ap-lab-08     3      CW9166I-B         3c84.6a12.3478  3c84.6a12.3480  lab-8      10.10.30.8     Registered
ap-lab-09     2      C9120AXI-B        3c84.6a12.34a0  3c84.6a12.34b0  lab-9      10.10.30.9     Downloading
"""

IP_BRIEF = """Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0/0   10.10.20.5      YES NVRAM  up                    up
GigabitEthernet0/0/1   unassigned      YES unset  administratively down down
Vlan100                192.168.100.5   YES NVRAM  up                    up
"""

RUNNING = """hostname ap-lab-07
!
interface GigabitEthernet0
 description uplink to sw-1 Gi1/0/7
 ip address 10.10.30.7 255.255.255.0
!
interface Dot11Radio1
 description 5 GHz radio
 channel 36
 power local 17
!
interface Dot11Radio2
 description 6 GHz radio
 channel 37
 shutdown
!
"""

M_7_9 = {
    "id": "7.9",
    "title": "Output Parsing: TextFSM, TTP & Genie",
    "hours": 2.5,
    "summary": "Turn CLI text into structured data: TextFSM state-machine templates (and the ntc-templates library), TTP templates that look like the output, and when to reach for Genie or plain regex.",
    "concepts": [
        {
            "title": "TextFSM templates and ntc-templates",
            "local_only": TEXTFSM,
            "concept": "A TextFSM template declares **Values** (named regex captures) and **States** with rules. Each line of output is matched against the current state's rules; `-> Record` stores the captured values as one row. `textfsm.TextFSM(template).ParseText(text)` returns rows as lists, and `header` names the columns. The **ntc-templates** package ships hundreds of community templates for common show commands, which Netmiko's `use_textfsm=True` uses.",
            "why": "Parsing tabular show output with ad-hoc `split()` breaks on the first column that contains a space or goes missing. A template is a small, testable spec of the output format that you can reuse across scripts and fix in one place.",
            "syntax": "Value NAME (\\S+)\nValue STATE (\\S+)\n\nStart\n  ^${NAME}\\s+\\d+\\s+.*\\s+${STATE}\\s*$$ -> Record",
            "code": """import io  ## TextFSM reads templates from file objects

import textfsm  ## pip install textfsm
from ntc_templates.parse import parse_output  ## pip install ntc-templates

AP_SUMMARY = open("ap_summary.txt").read()  ## Captured output (see supporting files)

TEMPLATE = r\"\"\"Value AP_NAME (\\S+)
Value SLOTS (\\d+)
Value MODEL (\\S+)
Value IP (\\d+\\.\\d+\\.\\d+\\.\\d+)
Value STATE (\\S+)

Start
  ^${AP_NAME}\\s+${SLOTS}\\s+${MODEL}\\s+\\S+\\s+\\S+\\s+\\S+\\s+${IP}\\s+${STATE}\\s*$$ -> Record
\"\"\"  ## Our own template for "show ap summary"

fsm = textfsm.TextFSM(io.StringIO(TEMPLATE))  ## Compile the template
rows = fsm.ParseText(AP_SUMMARY)  ## Run the state machine over every line
print(fsm.header)  ## Column names, in Value order
aps = [dict(zip(fsm.header, row)) for row in rows]  ## Rows as dicts
print(aps[2])  ## One AP
print("not registered:", [a["AP_NAME"] for a in aps if a["STATE"] != "Registered"])  ## Logic on structured data

parsed = parse_output(platform="cisco_ios", command="show ip interface brief", data=open("ip_brief.txt").read())  ## A community template
print(parsed[1])  ## Keys are lower-case in ntc-templates""",
            "files": {"ap_summary.txt": AP_SUMMARY, "ip_brief.txt": IP_BRIEF},
            "under": "Rules are tried in order for each input line; the first match wins and its action runs. `$$` is a literal end-of-line anchor (a single `$` would start a variable). Header and separator lines simply match no rule and are skipped. ntc-templates selects a template through an index file keyed by platform and command regex, which is why the command string must match what the template expects.",
            "gotchas": [
                {
                    "title": "A Value regex that's too strict drops rows silently",
                    "local_only": TEXTFSM,
                    "files": {"ip_brief.txt": IP_BRIEF},
                    "note": "If a row doesn't match the rule, it's not an error: the row just disappears. Here the IP Value only accepts dotted quads, so the `unassigned` interface vanishes, and a check like \"all interfaces up\" passes wrongly. Make Values match everything a column can contain, and assert on the row count.",
                    "wrong": """import io
import textfsm

T = r'''Value INTF (\\S+)
Value IP (\\d+\\.\\d+\\.\\d+\\.\\d+)
Value STATUS (up|down|administratively down)

Start
  ^${INTF}\\s+${IP}\\s+\\S+\\s+\\S+\\s+${STATUS}\\s+\\S+\\s*$$ -> Record
'''
rows = textfsm.TextFSM(io.StringIO(T)).ParseText(open("ip_brief.txt").read())
print(len(rows), "rows;", "all up:", all(r[2] == "up" for r in rows))""",
                    "fixed": """import io
import textfsm

T = r'''Value INTF (\\S+)
Value IP (\\S+)
Value STATUS (up|down|administratively down)

Start
  ^${INTF}\\s+${IP}\\s+\\S+\\s+\\S+\\s+${STATUS}\\s+\\S+\\s*$$ -> Record
'''
rows = textfsm.TextFSM(io.StringIO(T)).ParseText(open("ip_brief.txt").read())
print(len(rows), "rows;", "all up:", all(r[2] == "up" for r in rows))""",
                },
            ],
            "best": "Check ntc-templates before writing your own, keep custom templates in files with test fixtures (captured output → expected rows), assert row counts against the device's own totals (\"Number of APs: 3\"), and prefer APIs with structured output when the platform has them.",
        },
        {
            "title": "TTP: templates that look like the output",
            "local_only": TTP,
            "files": {"running.txt": RUNNING},
            "concept": "TTP (Template Text Parser) templates are a copy of the text with variables in `{{ }}`. A `<group>` matches a repeating block (like each `interface` section) and becomes a list of dicts. Variables can have functions: `{{ channel | to_int }}`, `{{ desc | ORPHRASE }}` (several words), `{{ shut | set(True) }}` (set a flag when a line is present). TTP shines on configuration files and hierarchical output.",
            "why": "Auditing configs (\"which radios are shut down?\", \"which APs exceed the power limit?\") means parsing nested, irregular text. A TTP template is usually readable at a glance by anyone who knows the config.",
            "syntax": "<group name=\"interfaces\">\ninterface {{ name }}\n description {{ desc | ORPHRASE }}\n channel {{ channel | to_int }}\n shutdown {{ disabled | set(True) }}\n</group>",
            "code": """import json  ## Pretty output

from ttp import ttp  ## pip install ttp

CONFIG = open("running.txt").read()  ## A device config (see supporting files)

TEMPLATE = \"\"\"<group name="interfaces">
interface {{ name }}
 description {{ desc | ORPHRASE }}
 ip address {{ ip }} {{ mask }}
 channel {{ channel | to_int }}
 power local {{ power | to_int }}
 shutdown {{ disabled | set(True) }}
</group>\"\"\"  ## Looks like the config itself

parser = ttp(data=CONFIG, template=TEMPLATE)  ## Data plus template
parser.parse()  ## Run it
interfaces = parser.result()[0][0]["interfaces"]  ## Results are nested per input and template
print(json.dumps(interfaces[1]))  ## One radio, typed values
radios = [i for i in interfaces if i["name"].startswith("Dot11Radio")]  ## Just the radios
print("shut down:", [r["name"] for r in radios if r.get("disabled")])  ## Flag set by set(True)
print("channels:", {r["name"]: r["channel"] for r in radios})  ## Integers, thanks to to_int""",
            "under": "TTP turns each template line into a regex, with variables becoming named groups (default pattern: a word without spaces; `ORPHRASE` allows several words). A group starts when its first line matches and collects following lines until the next start. Keys that never match are simply absent from that dict, hence `r.get(\"disabled\")`.",
            "gotchas": [],
            "best": "Use TTP for configs and nested output, TextFSM (ntc-templates) for tabular show commands, Genie parsers when you're in the Cisco pyATS ecosystem (`device.parse(\"show version\")` returns a validated schema), and regex only for one-off single-line extraction.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Without any library, parse `Number of APs: 3` from the summary and check it equals the number of data rows (lines starting with 'ap-').",
            "solution": "A regex with a named group for the total, a list comprehension for rows; comparing them catches parser drift.",
            "solution_code": """import re

AP_SUMMARY = '''Number of APs: 3

AP Name       Slots  AP Model
ap-lab-07     3      CW9166I-B
ap-lab-08     3      CW9166I-B
ap-lab-09     2      C9120AXI-B
'''
total = int(re.search(r"Number of APs:\\s+(?P<n>\\d+)", AP_SUMMARY)["n"])
rows = [line for line in AP_SUMMARY.splitlines() if line.startswith("ap-")]
print(total, len(rows), "consistent" if total == len(rows) else "MISMATCH")""",
        },
        {
            "level": "Medium",
            "local_only": TEXTFSM,
            "prompt": "Write a TextFSM template for `wpa_cli scan_results` (bssid, frequency, signal, flags, ssid; SSID may be empty) and list networks with WPA3.",
            "solution": "Tab-separated columns; SSID Value must allow empty with `(.*)`.",
            "solution_code": """import io
import textfsm

SCAN = '''bssid / frequency / signal level / flags / ssid
3c:84:6a:12:34:60\\t5975\\t-52\\t[WPA3-SAE-CCMP][ESS]\\tlab-6g
3c:84:6a:12:34:56\\t5180\\t-49\\t[WPA2-PSK-CCMP][WPA3-SAE-CCMP][ESS]\\tlab-5g
9e:11:22:33:44:55\\t5745\\t-78\\t[ESS]\\tguest
de:ad:be:ef:00:01\\t2412\\t-83\\t[WPA2-PSK-CCMP][ESS]\\t
'''
T = r'''Value BSSID ([0-9a-f:]{17})
Value FREQ (\\d+)
Value SIGNAL (-?\\d+)
Value FLAGS (\\S+)
Value SSID (.*)

Start
  ^${BSSID}\\t${FREQ}\\t${SIGNAL}\\t${FLAGS}\\t${SSID}$$ -> Record
'''
fsm = textfsm.TextFSM(io.StringIO(T))
rows = [dict(zip(fsm.header, r)) for r in fsm.ParseText(SCAN)]
print(len(rows), "networks")
print([(r["SSID"] or "<hidden>", r["FREQ"]) for r in rows if "WPA3" in r["FLAGS"]])""",
        },
        {
            "level": "Hard",
            "local_only": TTP,
            "files": {"running.txt": RUNNING},
            "prompt": "Audit the config with TTP: report every radio whose `power local` exceeds 15 dBm or that is shut down, plus the uplink description.",
            "solution": "One group template; filter the resulting dicts in Python.",
            "solution_code": """from ttp import ttp

T = '''<group name="ifs">
interface {{ name }}
 description {{ desc | ORPHRASE }}
 power local {{ power | to_int }}
 shutdown {{ shut | set(True) }}
</group>'''
p = ttp(data=open("running.txt").read(), template=T)
p.parse()
ifs = p.result()[0][0]["ifs"]
for i in ifs:
    issues = []
    if i.get("power", 0) > 15:
        issues.append(f"power {i['power']} dBm")
    if i.get("shut"):
        issues.append("shut down")
    if i["name"].startswith("Dot11") and issues:
        print(i["name"], issues)
print("uplink:", next(i["desc"] for i in ifs if i["name"] == "GigabitEthernet0"))""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "TextFSM vs TTP vs Genie vs regex?", "a": "TextFSM: state-machine templates, great for tabular show output; huge ntc-templates library. TTP: templates that mirror the text, great for configs and hierarchical output. Genie: Cisco pyATS parsers with strict schemas for many Cisco commands. Regex: fine for single values, painful for tables.", "follow": "Which does Netmiko support? (All three: use_textfsm, use_ttp, use_genie.)"},
        {"level": "Intermediate", "q": "How do you keep parsers from silently breaking after a firmware upgrade?", "a": "Store captured outputs per firmware as test fixtures with expected parsed results, assert row counts against totals the device prints, and run parser tests in CI whenever templates or fixtures change.", "follow": "What's the better long-term fix? (Use APIs with structured output.)"},
        {"level": "Advanced", "q": "Explain how a TextFSM template processes input.", "a": "Values define named regexes. Each line is tested against the current state's rules in order; on match, values are captured and actions run (Record, Clear, Continue, state transitions). Record appends the current values as a row. Filldown/Required options control carry-over and mandatory fields.", "follow": "What's Filldown for? (Carrying a value like a VRF name onto following rows.)"},
    ],
    "quiz": [
        {"q": "End-of-line anchor inside a TextFSM rule:", "options": ["$", "$$", "\\Z", "EOL"], "answer": 1, "why": "Single $ introduces a variable."},
        {"q": "A row that matches no rule in TextFSM...", "options": ["Raises", "Is skipped silently", "Becomes an empty row", "Stops parsing"], "answer": 1, "why": "Hence the row-count check."},
        {"q": "TTP function to capture several words:", "options": ["WORD", "ORPHRASE", "LINE", "MULTI"], "answer": 1, "why": "ORPHRASE."},
        {"q": "Community TextFSM template library:", "options": ["genie-parsers", "ntc-templates", "ttp-templates", "netdata"], "answer": 1, "why": "ntc-templates."},
        {"q": "Best tool for parsing a running config into nested data:", "options": ["split()", "TTP", "SNMP", "difflib"], "answer": 1, "why": "Group blocks map naturally."},
    ],
    "cards": [
        {"front": "TextFSM parse", "back": "`fsm = textfsm.TextFSM(open(t)); rows = fsm.ParseText(text); fsm.header`"},
        {"front": "ntc-templates", "back": "`parse_output(platform='cisco_ios', command='show ...', data=text)`"},
        {"front": "TTP parse", "back": "`p = ttp(data=text, template=t); p.parse(); p.result()`"},
        {"front": "TTP flag variable", "back": "`shutdown {{ disabled | set(True) }}`"},
        {"front": "Parser safety net", "back": "Assert parsed row count == device-reported total"},
    ],
}


SITE_DATA = '''SITE = {
    "hostname": "ap-lab-07",
    "mgmt": "10.10.30.7/24",
    "ntp": ["10.0.0.10", "10.0.0.11"],
    "wlans": [
        {"id": 1, "ssid": "lab-6g", "security": "wpa3-sae", "vlan": 600, "bands": ["6G"]},
        {"id": 2, "ssid": "lab-5g", "security": "wpa2-wpa3", "vlan": 500, "bands": ["5G", "2G"]},
        {"id": 3, "ssid": "guest", "security": "owe", "vlan": 900, "bands": ["5G"], "rate_limit_mbps": 20},
    ],
    "radios": {"2G": {"channel": 6, "power": 12}, "5G": {"channel": 36, "power": 17}, "6G": {"channel": 37, "power": 20}},
}
'''

M_7_10 = {
    "id": "7.10",
    "title": "Jinja2 Config Templating",
    "hours": 1.5,
    "summary": "Generate device configurations from data with Jinja2 (loops, conditionals, custom filters, whitespace control), and compare intended config against running config.",
    "concepts": [
        {
            "title": "Rendering configs from structured data",
            "local_only": JINJA,
            "files": {"site_data.py": SITE_DATA},
            "concept": "Keep **what** a device should look like in data (YAML/JSON or a source of truth like NetBox) and **how** the vendor syntax looks in a Jinja2 template. Loops generate repeated blocks (WLANs, VLANs), conditionals handle optional features, custom filters do conversions (prefix → netmask), and `trim_blocks`/`lstrip_blocks` keep the output free of stray blank lines and indentation. `StrictUndefined` makes a missing key an error instead of an empty string.",
            "why": "Twenty test benches need nearly identical AP configs with different SSIDs, channels and IPs. Templates make the configs consistent, reviewable (the data diff is small) and reproducible for every test run.",
            "syntax": "env = Environment(loader=FileSystemLoader(\"templates\"), trim_blocks=True, lstrip_blocks=True, undefined=StrictUndefined)\nenv.filters[\"netmask\"] = ...\nprint(env.get_template(\"ap.j2\").render(**site))",
            "code": """import ipaddress  ## For the netmask filter

from jinja2 import Environment, StrictUndefined  ## pip install jinja2

from site_data import SITE  ## Intent: what this AP should look like (see supporting files)

TEMPLATE = \"\"\"hostname {{ hostname }}
interface GigabitEthernet0
 ip address {{ mgmt | ip }} {{ mgmt | netmask }}
{% for server in ntp %}
ntp server {{ server }}
{% endfor %}
{% for w in wlans %}
wlan {{ w.ssid }} {{ w.id }}
 vlan {{ w.vlan }}
 security {{ w.security }}
 radio {{ w.bands | join(' ') | lower }}
{% if w.rate_limit_mbps is defined %}
 rate-limit {{ w.rate_limit_mbps * 1000 }} kbps
{% endif %}
 no shutdown
{% endfor %}
{% for band, r in radios | dictsort %}
radio {{ band | lower }} channel {{ r.channel }} power {{ r.power }}
{% endfor %}\"\"\"  ## Vendor syntax lives here, not in the data

env = Environment(trim_blocks=True, lstrip_blocks=True, undefined=StrictUndefined)  ## Clean whitespace; fail on missing keys
env.filters["ip"] = lambda cidr: str(ipaddress.ip_interface(cidr).ip)  ## "10.10.30.7/24" -> "10.10.30.7"
env.filters["netmask"] = lambda cidr: str(ipaddress.ip_interface(cidr).netmask)  ## -> "255.255.255.0"

config = env.from_string(TEMPLATE).render(**SITE)  ## Data in, config text out
print(config)  ## The generated configuration""",
            "under": "`trim_blocks` removes the newline after a block tag (`{% ... %}`), and `lstrip_blocks` strips spaces before it, so control lines leave no trace in the output. `dictsort` iterates a dict sorted by key for stable output. `is defined` tests whether an optional key exists; with StrictUndefined, simply using a missing key raises `UndefinedError` instead.",
            "gotchas": [
                {
                    "title": "Block tags leaving blank lines in the config",
                    "local_only": JINJA,
                    "note": "Without `trim_blocks`/`lstrip_blocks`, every `{% for %}` / `{% endfor %}` line leaves a newline (and its indentation) behind. Some devices reject or misread such configs, and diffs get noisy.",
                    "wrong": """from jinja2 import Environment

t = '''{% for v in vlans %}
vlan {{ v }}
{% endfor %}
end'''
print(repr(Environment().from_string(t).render(vlans=[500, 600])))""",
                    "fixed": """from jinja2 import Environment

t = '''{% for v in vlans %}
vlan {{ v }}
{% endfor %}
end'''
print(repr(Environment(trim_blocks=True, lstrip_blocks=True).from_string(t).render(vlans=[500, 600])))""",
                },
            ],
            "best": "Data in version control (or NetBox), one template per platform and role, StrictUndefined and whitespace control always on, custom filters for conversions instead of logic in templates, and rendered configs reviewed as diffs before they're pushed.",
        },
        {
            "title": "Intended vs running config: a diff",
            "concept": "Once configs are generated, compare them with what the device actually runs. `difflib.unified_diff` shows lines to add (`+`) and remove (`-`) like `git diff`. Normalising first (strip trailing spaces, drop comment/`!` lines, ignore volatile lines like timestamps) keeps the diff meaningful. An empty diff means the device is compliant.",
            "why": "Before a test run you want proof the bench is configured as intended. After someone 'just tweaks one thing' on a device, the diff shows exactly what drifted.",
            "syntax": "diff = difflib.unified_diff(running, intended, fromfile=\"running\", tofile=\"intended\", lineterm=\"\")",
            "code": """import difflib  ## Standard-library diff

INTENDED = \"\"\"hostname ap-lab-07
ntp server 10.0.0.10
ntp server 10.0.0.11
radio 5g channel 36 power 17
radio 6g channel 37 power 20\"\"\"  ## What the template rendered

RUNNING = \"\"\"! Last configuration change at 09:14:02 UTC Mon Oct 12 2026
hostname ap-lab-07
ntp server 10.0.0.10
radio 5g channel 149 power 17
radio 6g channel 37 power 20   \"\"\"  ## What the device reports (note the trailing spaces)


def normalise(text):  ## Make the comparison about meaning, not formatting
    return [line.rstrip() for line in text.splitlines() if line.strip() and not line.startswith("!")]  ## Drop comments, blanks, trailing spaces


diff = list(difflib.unified_diff(normalise(RUNNING), normalise(INTENDED), fromfile="running", tofile="intended", lineterm=""))  ## Running -> intended
print("\\n".join(diff) if diff else "compliant")  ## The changes needed, or a clean bill
missing = [d[1:] for d in diff if d.startswith("+") and not d.startswith("+++")]  ## Lines to push
print("to push:", missing)  ## Candidate remediation""",
            "under": "`unified_diff` finds the longest matching subsequences between the two line lists and reports the rest as changes with a few lines of context, each hunk introduced by `@@ -a,b +c,d @@`. `lineterm=\"\"` stops it adding newlines to lines that never had them. Changing a line shows up as a `-` and a `+`.",
            "gotchas": [],
            "best": "Normalise before diffing, compare whole sections (or parsed data) for hierarchical configs, store compliance results per device per run, and let a human review remediation for anything outside the test bench.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "local_only": JINJA,
            "prompt": "Render VLAN definitions from a list of dicts (`id`, `name`), skipping any VLAN marked `\"reserved\": True`.",
            "solution": "A for loop with an inline `if` filter clause.",
            "solution_code": """from jinja2 import Environment

t = '''{% for v in vlans if not v.reserved %}
vlan {{ v.id }}
 name {{ v.name }}
{% endfor %}'''
vlans = [{"id": 500, "name": "lab-5g", "reserved": False}, {"id": 1002, "name": "fddi", "reserved": True},
         {"id": 600, "name": "lab-6g", "reserved": False}]
print(Environment(trim_blocks=True, lstrip_blocks=True).from_string(t).render(vlans=vlans))""",
        },
        {
            "level": "Medium",
            "local_only": JINJA,
            "prompt": "Show `StrictUndefined` catching a typo (`w.vlna`) in a WLAN template, and print the error message.",
            "solution": "Rendering raises UndefinedError naming the missing attribute.",
            "solution_code": """from jinja2 import Environment, StrictUndefined
from jinja2.exceptions import UndefinedError

t = "wlan {{ w.ssid }}\\n vlan {{ w.vlna }}"
try:
    Environment(undefined=StrictUndefined).from_string(t).render(w={"ssid": "lab-6g", "vlan": 600})
except UndefinedError as e:
    print("UndefinedError:", e)""",
        },
        {
            "level": "Hard",
            "local_only": JINJA,
            "prompt": "Write a macro that renders a radio block and validates the channel for its band (raise an error from inside the template for 6 GHz channel 36), using a custom `fail` global.",
            "solution": "Templates can call Python functions registered in `env.globals`; raising from one aborts the render with a clear message.",
            "solution_code": """from jinja2 import Environment

VALID = {"2G": range(1, 14), "5G": range(36, 166), "6G": range(1, 234, 4)}


def fail(msg):
    raise ValueError(msg)


env = Environment(trim_blocks=True, lstrip_blocks=True)
env.globals.update(fail=fail, VALID=VALID)
t = env.from_string('''{% macro radio(band, ch) %}
{% if ch not in VALID[band] %}{{ fail("channel %d invalid for %s" % (ch, band)) }}{% endif %}
radio {{ band | lower }} channel {{ ch }}
{% endmacro %}
{{ radio("5G", 36) }}{{ radio("6G", 37) }}''')
print(t.render())
try:
    env.from_string('{% macro radio(band, ch) %}{% if ch not in VALID[band] %}{{ fail("channel %d invalid for %s" % (ch, band)) }}{% endif %}{% endmacro %}{{ radio("6G", 36) }}').render()
except ValueError as e:
    print("ValueError:", e)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "Why generate configs from templates?", "a": "Consistency and scale: intent lives in reviewed data, syntax lives in templates, and every device gets the same structure. Changes are small data diffs, and configs are reproducible.", "follow": "Where should the data come from? (A source of truth such as NetBox, or versioned YAML.)"},
        {"level": "Intermediate", "q": "How do you avoid logic creeping into templates?", "a": "Precompute in Python (or custom filters) and pass ready-to-render data; keep templates to loops, simple conditionals and formatting.", "follow": "When is a macro appropriate? (Repeated vendor syntax blocks, like a radio or interface stanza.)"},
        {"level": "Intermediate", "q": "How do you check a device is compliant with its intended config?", "a": "Render intended config, fetch running config, normalise both, diff (or compare parsed structures), and report or remediate the differences.", "follow": "Why parse instead of text-diff for some platforms? (Order-insensitive sections and defaults that aren't shown.)"},
    ],
    "quiz": [
        {"q": "Remove the newline after a block tag:", "options": ["lstrip_blocks", "trim_blocks", "autoescape", "keep_trailing_newline"], "answer": 1, "why": "trim_blocks."},
        {"q": "Iterate a dict in key order in Jinja:", "options": ["|sort", "|dictsort", "|items", "|keys"], "answer": 1, "why": "dictsort."},
        {"q": "Test an optional key exists:", "options": ["is defined", "is not none", "exists()", "has()"], "answer": 0, "why": "`is defined`."},
        {"q": "difflib lines starting with '+' are...", "options": ["In fromfile only", "In tofile only", "Unchanged", "Headers"], "answer": 1, "why": "Added in the target."},
        {"q": "Config templates should avoid...", "options": ["Loops", "Heavy business logic", "Filters", "Comments"], "answer": 1, "why": "Precompute in Python."},
    ],
    "cards": [
        {"front": "Config env", "back": "`Environment(trim_blocks=True, lstrip_blocks=True, undefined=StrictUndefined)`"},
        {"front": "Custom filter", "back": "`env.filters['netmask'] = lambda c: str(ip_interface(c).netmask)`"},
        {"front": "Loop with condition", "back": "`{% for v in vlans if not v.reserved %}`"},
        {"front": "Diff configs", "back": "`difflib.unified_diff(run, want, 'running', 'intended', lineterm='')`"},
        {"front": "Normalise before diff", "back": "Strip trailing spaces, drop comments/blank/volatile lines"},
    ],
}


M_7_11 = {
    "id": "7.11",
    "title": "Scapy Fundamentals",
    "hours": 2,
    "summary": "Build and dissect packets layer by layer with Scapy, convert to and from raw bytes, write and read pcap files, and summarise captures. Everything here is offline: nothing is sent.",
    "concepts": [
        {
            "title": "Layers, fields, bytes and dissection",
            "local_only": SCAPY,
            "concept": "Scapy builds packets by stacking layers with `/`: `Ether()/IP()/UDP()/DNS()`. Unset fields get sensible defaults, and lengths and checksums are computed when the packet is turned into bytes (`bytes(pkt)`). Going the other way, `Ether(raw_bytes)` dissects bytes into layers. Access a layer with `pkt[IP]`, a field with `pkt[IP].ttl`, test with `pkt.haslayer(DNS)`, and inspect with `summary()` and `show()`.",
            "why": "Test engineers use Scapy to craft exactly the packet a test needs (a malformed DHCP option, a specific DSCP mark), to decode captures programmatically, and to understand protocols byte by byte.",
            "syntax": "pkt = Ether(dst=...)/IP(dst=\"10.0.0.1\", tos=0xb8)/UDP(dport=5201)/Raw(b\"x\")\nraw = bytes(pkt)\nback = Ether(raw)\nback[IP].ttl",
            "code": """from scapy.all import DNS, DNSQR, IP, UDP, Ether, Raw, hexdump  ## pip install scapy

pkt = (Ether(src="02:00:00:00:01:00", dst="3c:84:6a:12:34:60")  ## Layer 2: explicit MACs keep the example deterministic
       / IP(src="192.168.100.57", dst="10.0.0.53", tos=0xB8)  ## Layer 3: DSCP EF (46) shifted into the ToS byte
       / UDP(sport=53111, dport=53)  ## Layer 4
       / DNS(id=0x1A2B, rd=1, qd=DNSQR(qname="ap-lab-07.lab.example")))  ## Application layer
print(pkt.summary())  ## One-line description
print(pkt[IP].chksum, pkt[IP].len)  ## None None: computed only when building bytes

raw = bytes(pkt)  ## Build: fills in lengths and checksums
print(len(raw), "bytes")  ## Size on the wire (without FCS)
hexdump(raw[:32])  ## First 32 bytes: Ethernet header then IP header

back = Ether(raw)  ## Dissect bytes into layers
print(back[IP].len, hex(back[IP].chksum), back[IP].tos >> 2)  ## Now computed; DSCP = ToS >> 2
print(back.haslayer(DNS), back[DNS].qd.qname.decode())  ## Layer test and a nested field
print([layer.__name__ for layer in back.layers()])  ## Layer classes in order
print(DNS in back, Raw in back, back[UDP].dport)  ## `in` tests for a layer; no Raw because DNS decoded the payload""",
            "under": "Each layer is a `Packet` with a list of field descriptors; `/` sets the lower layer's payload and Scapy binds protocol fields automatically (Ether.type becomes 0x0800 for IP, IP.proto 17 for UDP). `bytes()` calls each layer's `post_build`, which is where lengths and checksums are computed. Dissection walks the bytes, choosing the next layer class from those binding fields (EtherType, IP protocol, UDP port 53 → DNS).",
            "gotchas": [
                {
                    "title": "Reading computed fields before the packet is built",
                    "local_only": SCAPY,
                    "note": "Checksums and lengths stay `None` on a packet you constructed until it's turned into bytes. Build it (or rebuild from bytes) before checking them, or use `show2()` instead of `show()`.",
                    "wrong": """from scapy.all import IP, UDP

pkt = IP(src="192.168.100.57", dst="10.0.0.1") / UDP(dport=5201) / b"payload"
print("udp len:", pkt[UDP].len, "ip checksum:", pkt[IP].chksum)""",
                    "fixed": """from scapy.all import IP, UDP

pkt = IP(src="192.168.100.57", dst="10.0.0.1") / UDP(dport=5201) / b"payload"
built = IP(bytes(pkt))
print("udp len:", built[UDP].len, "ip checksum:", hex(built[IP].chksum))""",
                },
            ],
            "best": "Set addresses explicitly in tests, build to bytes before asserting on computed fields, use `haslayer`/`getlayer` rather than assuming a layer exists, and only ever send crafted packets on lab networks you're authorised to test (sending needs root and a capable interface).",
        },
        {
            "title": "Writing and reading pcap files",
            "local_only": SCAPY,
            "concept": "`wrpcap(path, packets)` writes a capture, `rdpcap(path)` reads it all into memory, and `PcapReader(path)` streams one packet at a time for large files. Each packet carries a `.time` timestamp. With `haslayer` and field access you can filter and aggregate: flows, retransmissions, DNS failures, DSCP marking, inter-packet gaps.",
            "why": "Captures are the ground truth in Wi-Fi and network testing. A script that summarises a pcap (who talked to whom, how much, how fast, any errors) turns a 200 MB file into a pass/fail check you can run after every test.",
            "syntax": "wrpcap(\"run.pcap\", pkts)\nfor pkt in PcapReader(\"run.pcap\"):\n    if pkt.haslayer(UDP): ...",
            "code": """from collections import Counter  ## Aggregation

from scapy.all import IP, TCP, UDP, Ether, PcapReader, wrpcap  ## pip install scapy

STA, SRV = "192.168.100.57", "10.0.0.20"  ## Wi-Fi client and test server
pkts = []  ## Synthetic capture: an iperf-like UDP stream plus a TCP handshake
for i in range(6):  ## Six UDP datagrams, one every 10 ms
    p = Ether() / IP(src=STA, dst=SRV, tos=0xB8 if i < 5 else 0) / UDP(sport=40000, dport=5201) / (b"x" * 1200)  ## Last one lost its DSCP mark
    p.time = 1760263200.000 + i * 0.010  ## Capture timestamp (epoch seconds)
    pkts.append(p)  ## Collect
for i, flags in enumerate(["S", "SA", "A"]):  ## TCP three-way handshake
    src, dst = (STA, SRV) if flags != "SA" else (SRV, STA)  ## Direction depends on the step
    p = Ether() / IP(src=src, dst=dst) / TCP(sport=51000 if src == STA else 22, dport=22 if src == STA else 51000, flags=flags)  ## SSH session start
    p.time = 1760263200.100 + i * 0.002  ## 2 ms apart
    pkts.append(p)  ## Collect
wrpcap("run.pcap", pkts)  ## Write a standard pcap file

flows, dscp, times = Counter(), Counter(), []  ## Accumulators
for pkt in PcapReader("run.pcap"):  ## Stream: one packet in memory at a time
    if not pkt.haslayer(IP):  ## Skip non-IP frames
        continue  ## Next packet
    proto = "UDP" if pkt.haslayer(UDP) else "TCP" if pkt.haslayer(TCP) else "other"  ## Transport protocol
    flows[(pkt[IP].src, pkt[IP].dst, proto)] += len(pkt)  ## Bytes per direction and protocol
    if pkt.haslayer(UDP) and pkt[UDP].dport == 5201:  ## The test stream only
        dscp[pkt[IP].tos >> 2] += 1  ## DSCP value counts
        times.append(float(pkt.time))  ## Timestamps for gap analysis

for (src, dst, proto), nbytes in sorted(flows.items()):  ## Flow table
    print(f"{src:>15} -> {dst:<15} {proto} {nbytes} bytes")  ## Aligned columns
print("DSCP counts:", dict(dscp))  ## 46 = EF; one packet arrived unmarked
gaps = [round((b - a) * 1000, 1) for a, b in zip(times, times[1:])]  ## Inter-packet gaps in ms
print("max gap:", max(gaps), "ms")  ## Jitter check""",
            "under": "pcap files store a global header (link type, snap length) then a record header (timestamp, captured length) per packet; Scapy restores `.time` from it. `rdpcap` returns a `PacketList` in memory, fine for small files; `PcapReader` is an iterator suitable for gigabytes. Default Ether() addresses resolve to broadcast/your interface when built, so real analysis should key on IP addresses, as here.",
            "gotchas": [],
            "best": "Stream large captures with PcapReader, filter as early as possible, key flows on (src, dst, proto, ports), compare timestamps as floats, and for heavy dissection of large files consider tshark/pyshark (next lessons) which are much faster at decoding.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "local_only": SCAPY,
            "prompt": "Build an ICMP echo request from 192.168.100.57 to 10.0.0.1 with id 7 and seq 1, convert it to bytes and dissect it again; print the ICMP type and the IP total length.",
            "solution": "IP()/ICMP() then IP(bytes(pkt)).",
            "solution_code": """from scapy.all import ICMP, IP

pkt = IP(src="192.168.100.57", dst="10.0.0.1") / ICMP(id=7, seq=1) / b"lab-ping"
back = IP(bytes(pkt))
print(back[ICMP].type, back[ICMP].id, back[ICMP].seq, back[IP].len)""",
        },
        {
            "level": "Medium",
            "local_only": SCAPY,
            "prompt": "Create a DHCP Discover (Ether/IP/UDP/BOOTP/DHCP) from MAC 02:00:00:00:01:00 and print the message type and the client hardware address as text.",
            "solution": "DHCP options are a list of tuples; BOOTP.chaddr holds the MAC bytes (padded to 16).",
            "solution_code": """from scapy.all import BOOTP, DHCP, IP, UDP, Ether

mac = "02:00:00:00:01:00"
pkt = (Ether(src=mac, dst="ff:ff:ff:ff:ff:ff") / IP(src="0.0.0.0", dst="255.255.255.255")
       / UDP(sport=68, dport=67) / BOOTP(chaddr=bytes.fromhex(mac.replace(":", "")), xid=0x1234)
       / DHCP(options=[("message-type", "discover"), ("hostname", b"sta-lab-1"), "end"]))
back = Ether(bytes(pkt))
opts = dict(o for o in back[DHCP].options if isinstance(o, tuple))
print(opts["message-type"], opts["hostname"], back[BOOTP].chaddr[:6].hex(":"))""",
        },
        {
            "level": "Hard",
            "local_only": SCAPY,
            "prompt": "Generate a TCP stream where one segment is retransmitted (same seq sent twice) and detect it from the pcap.",
            "solution": "Track (src, dst, sport, dport, seq) for segments with payload; a repeat is a retransmission.",
            "solution_code": """from scapy.all import IP, TCP, PcapReader, wrpcap

pkts = []
seq = 1000
for i, size in enumerate([1200, 1200, 1200, 1200]):
    pkts.append(IP(src="10.0.0.20", dst="192.168.100.57") / TCP(sport=5201, dport=50000, seq=seq, flags="A") / (b"d" * size))
    if i == 1:
        pkts.append(pkts[-1].copy())
    seq += size
wrpcap("tcp.pcap", pkts)

seen, retrans = set(), []
for p in PcapReader("tcp.pcap"):
    if p.haslayer(TCP) and len(p[TCP].payload):
        key = (p[IP].src, p[IP].dst, p[TCP].sport, p[TCP].dport, p[TCP].seq)
        if key in seen:
            retrans.append(p[TCP].seq)
        seen.add(key)
print("segments:", len(pkts), "retransmitted seq:", retrans)""",
        },
    ],
    "interview": [
        {"level": "Beginner", "q": "What is Scapy used for in test automation?", "a": "Crafting packets with exact field values (including malformed ones), sending/sniffing on lab interfaces, and dissecting/analysing pcap files programmatically. It covers Ethernet/IP/TCP/UDP, DHCP, DNS, 802.11, Radiotap and many more.", "follow": "What does sending require? (Root/CAP_NET_RAW and an interface on an authorised test network.)"},
        {"level": "Intermediate", "q": "Why is a checksum None after building a Scapy packet object?", "a": "Computed fields are filled in by post_build when the packet is serialised; until bytes(pkt) (or show2) is called they remain None so Scapy can compute them from the final content.", "follow": "How do you send a deliberately wrong checksum? (Set the field explicitly; Scapy won't overwrite it.)"},
        {"level": "Intermediate", "q": "rdpcap vs PcapReader?", "a": "rdpcap loads all packets into memory (simple, fine for small files). PcapReader iterates lazily, needed for large captures.", "follow": "What's faster for huge files? (tshark with field extraction, or dpkt.)"},
    ],
    "quiz": [
        {"q": "Stack layers in Scapy with...", "options": ["+", "/", "|", ">>"], "answer": 1, "why": "The / operator."},
        {"q": "Dissect raw Ethernet bytes:", "options": ["parse(raw)", "Ether(raw)", "Packet.load(raw)", "rdpcap(raw)"], "answer": 1, "why": "Call the layer class."},
        {"q": "DSCP from the IP ToS byte:", "options": ["tos & 0x3f", "tos >> 2", "tos << 2", "tos % 64"], "answer": 1, "why": "Top 6 bits."},
        {"q": "Stream a large pcap:", "options": ["rdpcap", "PcapReader", "wrpcap", "sniff"], "answer": 1, "why": "Iterator."},
        {"q": "Packet timestamp attribute:", "options": ["pkt.ts", "pkt.time", "pkt[IP].time", "pkt.stamp"], "answer": 1, "why": ".time (epoch seconds)."},
    ],
    "cards": [
        {"front": "Build a packet", "back": "`Ether()/IP(dst=...)/UDP(dport=...)/b'data'`"},
        {"front": "Computed fields", "back": "Only after `bytes(pkt)`; check with `IP(bytes(pkt))`"},
        {"front": "Layer access", "back": "`pkt[IP].src`, `pkt.haslayer(DNS)`, `DNS in pkt`"},
        {"front": "pcap I/O", "back": "`wrpcap(path, pkts)`, `rdpcap(path)`, `PcapReader(path)`"},
        {"front": "DSCP", "back": "`pkt[IP].tos >> 2` (EF = 46 = ToS 0xB8)"},
    ],
}


M_7_12 = {
    "id": "7.12",
    "title": "Scapy for 802.11 & Radiotap",
    "hours": 2.5,
    "summary": "Wi-Fi frames in Scapy: Radiotap metadata, 802.11 management frames, information elements (SSID, channel, RSN), and analysing a connection sequence from a capture.",
    "concepts": [
        {
            "title": "Beacons, information elements and Radiotap",
            "local_only": SCAPY,
            "concept": "A monitor-mode capture frame is `RadioTap()/Dot11()/...`. **Radiotap** carries receive metadata (signal dBm, channel frequency, data rate). **Dot11** is the 802.11 MAC header: `type` (0 management, 1 control, 2 data), `subtype` (8 = beacon), and addresses `addr1` (receiver), `addr2` (transmitter), `addr3` (BSSID). Management frames carry **information elements** (`Dot11Elt`: ID, length, info): SSID (ID 0), DS Parameter Set (ID 3, the channel), RSN (ID 48, security). Iterate the Elt chain to read them.",
            "why": "Beacon analysis answers real test questions from captures: Is the AP advertising WPA3? On which channel? Is the beacon interval right? Is a hidden SSID really hidden? What RSSI did the sniffer see?",
            "syntax": "RadioTap(present=\"dBm_AntSignal+Channel\", dBm_AntSignal=-52, ChannelFrequency=5180)\n/ Dot11(type=0, subtype=8, addr1=BCAST, addr2=BSSID, addr3=BSSID)\n/ Dot11Beacon(cap=\"ESS+privacy\") / Dot11Elt(ID=\"SSID\", info=b\"lab-5g\")",
            "code": """from scapy.all import Dot11, Dot11Beacon, Dot11Elt, RadioTap, PcapReader, wrpcap  ## pip install scapy

BCAST = "ff:ff:ff:ff:ff:ff"  ## Beacons go to broadcast
RSN_SAE = bytes.fromhex("0100000fac040100000fac040100000fac08c000")  ## RSN IE body: CCMP, AKM 8 (SAE), MFP required


def beacon(bssid, ssid, channel, freq, rssi, rsn=None):  ## Build one beacon as a sniffer would capture it
    frame = (RadioTap(present="Rate+Channel+dBm_AntSignal", Rate=12, ChannelFrequency=freq, ChannelFlags="OFDM+5GHz", dBm_AntSignal=rssi)  ## Receive metadata
             / Dot11(type=0, subtype=8, addr1=BCAST, addr2=bssid, addr3=bssid)  ## Management/beacon header
             / Dot11Beacon(beacon_interval=100, cap="ESS+privacy" if rsn else "ESS")  ## Fixed beacon fields
             / Dot11Elt(ID="SSID", info=ssid.encode())  ## IE 0
             / Dot11Elt(ID="DSset", info=bytes([channel])))  ## IE 3: current channel
    return frame / Dot11Elt(ID="RSNinfo", info=rsn) if rsn else frame  ## IE 48 only for secured networks


wrpcap("beacons.pcap", [beacon("3c:84:6a:12:34:56", "lab-5g", 36, 5180, -49, RSN_SAE),  ## Secured network
                        beacon("3c:84:6a:12:34:57", "", 36, 5180, -50, RSN_SAE),  ## Hidden SSID (empty)
                        beacon("9e:11:22:33:44:55", "guest", 149, 5745, -78)])  ## Open network


def elements(pkt):  ## Walk the chain of information elements
    elt = pkt.getlayer(Dot11Elt)  ## First IE
    while elt is not None:  ## Until the end of the frame
        yield elt.ID, bytes(elt.info)  ## (id, raw value)
        elt = elt.payload.getlayer(Dot11Elt)  ## Next IE


for pkt in PcapReader("beacons.pcap"):  ## Read them back
    if not pkt.haslayer(Dot11Beacon):  ## Only beacons
        continue  ## Skip others
    ies = dict(elements(pkt))  ## IE id -> bytes
    ssid = ies[0].decode() or "<hidden>"  ## Empty SSID means hidden
    rsn = ies.get(48)  ## None for open networks
    akm = {b"\\x00\\x0f\\xac\\x02": "PSK", b"\\x00\\x0f\\xac\\x08": "SAE"}.get(rsn[14:18], "?") if rsn else "open"  ## AKM suite selector bytes
    print(f"{pkt[Dot11].addr3} {ssid:<9} ch{ies[3][0]:<4} {pkt[RadioTap].dBm_AntSignal} dBm {akm}")  ## One line per BSS""",
            "under": "The RSN element is binary: version (2 bytes), group cipher suite (4), pairwise count + suites, AKM count + suites, then capabilities. Suite selectors are the IEEE OUI `00-0F-AC` plus a type byte (4 = CCMP, 2 = PSK, 8 = SAE). Radiotap's `present` bitmap says which metadata fields follow; a field that isn't present reads as `None` in Scapy, so real code checks before using it.",
            "gotchas": [
                {
                    "title": "Assuming a Radiotap field is present",
                    "local_only": SCAPY,
                    "note": "Different drivers and sniffers include different Radiotap fields. In a capture without signal information, `dBm_AntSignal` is `None`, and arithmetic or comparisons on it blow up deep inside your analysis. Check for None (or the `present` flags) and handle the missing case explicitly.",
                    "wrong": """from scapy.all import Dot11, RadioTap

frame = RadioTap(present="Rate", Rate=12) / Dot11(type=0, subtype=8)
pkt = RadioTap(bytes(frame))
if pkt[RadioTap].dBm_AntSignal < -70:
    print("weak beacon")""",
                    "fixed": """from scapy.all import Dot11, RadioTap

frame = RadioTap(present="Rate", Rate=12) / Dot11(type=0, subtype=8)
pkt = RadioTap(bytes(frame))
signal = pkt[RadioTap].dBm_AntSignal
if signal is None:
    print("signal not captured by this sniffer")
elif signal < -70:
    print("weak beacon")""",
                },
            ],
            "best": "Parse IEs by walking the chain (they're optional and repeatable), decode binary IEs with struct and the spec, treat Radiotap fields as optional, and validate your parser against captures from real sniffers in the lab.",
        },
        {
            "title": "Analysing a connection sequence",
            "local_only": SCAPY,
            "concept": "A WPA3 client join looks like this in a capture: probe request/response, **authentication** (subtype 11, SAE commit/confirm), **association request/response** (subtypes 0/1, with a status code), the **EAPOL 4-way handshake** (four data frames carrying EAPOL-Key), then data. A deauthentication (subtype 12) carries a reason code. Classifying frames by type/subtype and timing the steps answers \"how long did it take to connect?\" and \"why did it disconnect?\".",
            "why": "Connection time and disconnect reasons are core Wi-Fi KPIs. Automating them from sniffer captures turns hours of manual Wireshark work into a test assertion: join time under 100 ms, no deauth with reason 15 (4-way handshake timeout).",
            "syntax": "MGMT = {0: \"assoc-req\", 1: \"assoc-resp\", 4: \"probe-req\", 5: \"probe-resp\", 8: \"beacon\", 11: \"auth\", 12: \"deauth\"}\n(pkt.type, pkt.subtype)",
            "code": """from scapy.all import EAPOL, LLC, SNAP, Dot11, Dot11AssoReq, Dot11AssoResp, Dot11Auth, Dot11Deauth, RadioTap, PcapReader, wrpcap  ## pip install scapy

AP, STA = "3c:84:6a:12:34:60", "02:00:00:00:01:00"  ## BSSID and client MAC
T0 = 1760263300.0  ## Capture start time


def frame(t, layer, src, dst, subtype=None, data=False):  ## Build one captured frame at time t (ms after T0)
    dot11 = Dot11(type=2 if data else 0, subtype=subtype or 0, addr1=dst, addr2=src, addr3=AP, FCfield="to_DS" if data and src == STA else 0)  ## MAC header
    pkt = RadioTap() / dot11 / layer  ## Minimal radiotap
    pkt.time = T0 + t / 1000  ## Timestamp
    return pkt  ## The frame


capture = [  ## A successful WPA3 join, then a disconnect 5 s later
    frame(0.0, Dot11Auth(algo=3, seqnum=1, status=0), STA, AP, subtype=11),  ## SAE commit
    frame(4.1, Dot11Auth(algo=3, seqnum=1, status=0), AP, STA, subtype=11),  ## SAE commit from AP
    frame(9.8, Dot11Auth(algo=3, seqnum=2, status=0), STA, AP, subtype=11),  ## SAE confirm
    frame(12.0, Dot11Auth(algo=3, seqnum=2, status=0), AP, STA, subtype=11),  ## SAE confirm from AP
    frame(15.3, Dot11AssoReq(cap=0x1111, listen_interval=10), STA, AP, subtype=0),  ## Association request
    frame(17.9, Dot11AssoResp(status=0, AID=7), AP, STA, subtype=1),  ## Association response: success, AID 7
    *[frame(20.0 + i * 3.5, LLC() / SNAP() / EAPOL(version=2, type=3), AP if i % 2 == 0 else STA, STA if i % 2 == 0 else AP, data=True) for i in range(4)],  ## EAPOL-Key messages 1-4
    frame(5032.0, Dot11Deauth(reason=3), STA, AP, subtype=12),  ## Client leaves (reason 3)
]  ## End of capture
wrpcap("join.pcap", capture)  ## Write it like a sniffer would

MGMT = {0: "assoc-req", 1: "assoc-resp", 11: "auth", 12: "deauth"}  ## Subtypes we care about
REASONS = {3: "STA leaving", 15: "4-way handshake timeout", 7: "class 3 frame from non-associated STA"}  ## A few deauth reason codes
events = []  ## (ms, label)
for pkt in PcapReader("join.pcap"):  ## Read back
    ms = round((float(pkt.time) - T0) * 1000, 1)  ## Relative time
    d = pkt[Dot11]  ## MAC header
    if d.type == 0 and d.subtype in MGMT:  ## Management frame of interest
        label = MGMT[d.subtype]  ## Name by subtype
        if pkt.haslayer(Dot11AssoResp):  ## Include the status code
            label += f" status={pkt[Dot11AssoResp].status} aid={pkt[Dot11AssoResp].AID}"  ## 0 = success
        if pkt.haslayer(Dot11Deauth):  ## Include the reason
            label += f" reason={pkt[Dot11Deauth].reason} ({REASONS.get(pkt[Dot11Deauth].reason, '?')})"  ## Human-readable
        events.append((ms, label))  ## Record
    elif pkt.haslayer(EAPOL):  ## Handshake message
        events.append((ms, "eapol"))  ## Record

for ms, label in events:  ## Timeline
    print(f"{ms:>8} ms  {label}")  ## Aligned
eapol_times = [ms for ms, label in events if label == "eapol"]  ## Handshake timestamps
print("join time:", eapol_times[-1] - events[0][0], "ms;", "4-way complete:", len(eapol_times) == 4)  ## First auth to EAPOL 4/4""",
            "under": "Management frame subtypes are 4-bit values in the Frame Control field; data frames with EAPOL are LLC/SNAP encapsulated with EtherType 0x888E. Authentication algorithm 3 is SAE (0 is open system), and SAE uses seqnum 1 for commit and 2 for confirm. Reason codes come from the 802.11 standard; a real analyser would include the full table.",
            "gotchas": [],
            "best": "Filter by BSSID and client MAC first, use a full reason/status code table, compute KPIs (auth→EAPOL 4/4, roam gap) as functions with tests on recorded captures, and remember that a single sniffer can miss frames: absence of a frame isn't proof it wasn't sent.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "local_only": SCAPY,
            "prompt": "Build a probe request for SSID `lab-6g` from client 02:00:00:00:01:00 and print its type, subtype and the SSID read back from the bytes.",
            "solution": "Management type 0, subtype 4; the SSID IE is the first Dot11Elt.",
            "solution_code": """from scapy.all import Dot11, Dot11Elt, Dot11ProbeReq, RadioTap

p = RadioTap() / Dot11(type=0, subtype=4, addr1="ff:ff:ff:ff:ff:ff", addr2="02:00:00:00:01:00",
                       addr3="ff:ff:ff:ff:ff:ff") / Dot11ProbeReq() / Dot11Elt(ID="SSID", info=b"lab-6g")
back = RadioTap(bytes(p))
print(back[Dot11].type, back[Dot11].subtype, back[Dot11Elt].info.decode())""",
        },
        {
            "level": "Medium",
            "prompt": "Parse an RSN information element body (hex given) with struct: print the group cipher, the pairwise cipher list and the AKM list as names.",
            "solution": "Little-endian counts, 4-byte suite selectors; map the last byte of OUI 00-0F-AC suites to names.",
            "solution_code": """import struct

CIPHER = {2: "TKIP", 4: "CCMP-128", 8: "GCMP-128", 9: "GCMP-256"}
AKM = {1: "802.1X", 2: "PSK", 8: "SAE", 18: "OWE", 24: "SAE-EXT-KEY"}


def parse_rsn(body):
    version, = struct.unpack_from("<H", body, 0)
    off = 2
    group = body[off + 3]; off += 4
    n, = struct.unpack_from("<H", body, off); off += 2
    pairwise = [CIPHER.get(body[off + 4 * i + 3]) for i in range(n)]; off += 4 * n
    m, = struct.unpack_from("<H", body, off); off += 2
    akms = [AKM.get(body[off + 4 * i + 3]) for i in range(m)]
    return version, CIPHER.get(group), pairwise, akms


print(parse_rsn(bytes.fromhex("0100000fac040100000fac040200000fac02000fac08c000")))""",
        },
        {
            "level": "Hard",
            "local_only": SCAPY,
            "prompt": "Detect a roam in a capture: the client's data frames switch from BSSID A to BSSID B. Report the gap in milliseconds between the last frame on A and the first on B.",
            "solution": "Track the BSSID (addr3 or the AP side address) of each client data frame over time; when it changes, compute the time difference.",
            "solution_code": """from scapy.all import Dot11, RadioTap, PcapReader, wrpcap

STA, A, B = "02:00:00:00:01:00", "3c:84:6a:12:34:60", "3c:84:6a:12:34:80"
frames = []
for i, (t, bssid) in enumerate([(0, A), (20, A), (40, A), (95, B), (115, B)]):
    p = RadioTap() / Dot11(type=2, subtype=0, FCfield="to_DS", addr1=bssid, addr2=STA, addr3=bssid) / b"data"
    p.time = 1000 + t / 1000
    frames.append(p)
wrpcap("roam.pcap", frames)

last_bssid, last_t = None, None
for p in PcapReader("roam.pcap"):
    d = p[Dot11]
    if d.type == 2 and d.addr2 == STA:
        if last_bssid and d.addr3 != last_bssid:
            print(f"roam {last_bssid} -> {d.addr3}: gap {round((float(p.time) - last_t) * 1000)} ms")
        last_bssid, last_t = d.addr3, float(p.time)""",
        },
    ],
    "interview": [
        {"level": "Intermediate", "q": "What's in a Radiotap header and why does it matter?", "a": "Per-frame receive (or transmit) metadata added by the capture driver: signal/noise dBm, channel frequency and flags, data rate or MCS/HE info, antenna, FCS flag. It's how you know the RSSI and rate of each frame, which matters for RF and rate-adaptation analysis.", "follow": "Is Radiotap transmitted over the air? (No, it's added by the sniffer.)"},
        {"level": "Intermediate", "q": "Walk through a WPA3-Personal connection in a capture.", "a": "Probe exchange (optional), SAE authentication (commit/commit, confirm/confirm, algo 3), association request/response (status 0, AID), EAPOL-Key 4-way handshake, then protected data. Deauth/disassoc frames carry reason codes on disconnect.", "follow": "How does WPA2-PSK differ? (Open System auth algo 0 instead of SAE; PSK used directly for PMK.)"},
        {"level": "Advanced", "q": "How would you measure roam time from captures?", "a": "Sniff both channels (or use a multi-radio sniffer), find the client's last data frame via the old BSSID and the first data frame via the new BSSID after reassociation/FT and the 4-way (or FT) handshake; report the gap and each phase's duration.", "follow": "What makes 802.11r faster? (Fast BSS Transition folds the key exchange into auth/reassoc frames, skipping the 4-way handshake.)"},
    ],
    "quiz": [
        {"q": "Beacon type/subtype:", "options": ["0/8", "2/0", "1/11", "0/4"], "answer": 0, "why": "Management, subtype 8."},
        {"q": "IE that carries the channel:", "options": ["SSID (0)", "DS Parameter Set (3)", "RSN (48)", "TIM (5)"], "answer": 1, "why": "DSset."},
        {"q": "addr3 in a beacon is...", "options": ["Receiver", "Transmitter", "BSSID", "Client"], "answer": 2, "why": "BSSID."},
        {"q": "SAE authentication algorithm number:", "options": ["0", "1", "3", "8"], "answer": 2, "why": "3 = SAE."},
        {"q": "Deauth reason 15 means...", "options": ["STA leaving", "4-way handshake timeout", "Unspecified", "Inactivity"], "answer": 1, "why": "Common in key/password issues."},
    ],
    "cards": [
        {"front": "802.11 frame in Scapy", "back": "`RadioTap()/Dot11(type, subtype, addr1, addr2, addr3)/...`"},
        {"front": "Key IEs", "back": "0 SSID, 3 DS (channel), 48 RSN, 221 vendor"},
        {"front": "Mgmt subtypes", "back": "0 assoc-req, 1 assoc-resp, 4 probe-req, 5 probe-resp, 8 beacon, 11 auth, 12 deauth"},
        {"front": "Walk IEs", "back": "`elt = pkt.getlayer(Dot11Elt)`; `elt = elt.payload.getlayer(Dot11Elt)`"},
        {"front": "Optional Radiotap field", "back": "`pkt[RadioTap].dBm_AntSignal` is None when not captured: check it"},
    ],
}
