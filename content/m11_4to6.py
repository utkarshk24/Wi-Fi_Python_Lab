"""Phase 11 final interview round, part 2: system design, behavioral (STAR), mock interview."""


# --------------------------------------------------------------------------- 11.4
CAPACITY = '''import math  ## Rounding up

suite = {"smoke": (40, 1.5), "regression": (600, 4.0), "rvr": (24, 35.0)}  ## Tests and average minutes per test
benches, nightly_window_h, setup_min = 6, 8, 20  ## Benches, hours available overnight, flash + preflight per bench
utilisation = 0.75  ## Realistic: failures, retries, bench outages


def bench_hours(names):  ## Total bench time for the chosen suites
    return sum(suite[n][0] * suite[n][1] for n in names) / 60  ## minutes -> hours


need = bench_hours(["regression", "rvr"])  ## The nightly plan
have = benches * (nightly_window_h - setup_min / 60) * utilisation  ## Usable bench-hours tonight
print(f"nightly needs {need:.1f} bench-hours; {have:.1f} available")  ## The headline numbers
print("fits" if need <= have else f"short by {need - have:.1f} h -> need {math.ceil(need / ((nightly_window_h - setup_min / 60) * utilisation))} benches")  ## Verdict
pcap_mb_per_test, runs_per_year = 150, 365  ## Captures kept per regression test
storage_tb = suite["regression"][0] * pcap_mb_per_test * runs_per_year / 1e6  ## MB -> TB
print(f"pcap storage: {storage_tb:.1f} TB/year -> keep failures only, or 30-day retention")  ## Drives the retention design
rows = sum(n for n, _ in suite.values()) * runs_per_year * 5  ## Result rows: 5 branches tested nightly
print(f"results DB: {rows / 1e6:.2f} M rows/year (one Postgres table with indexes is plenty)")  ## Not a big-data problem'''

SCHEDULER = '''import heapq  ## Priority queue

jobs = [  ## (arrival minute, priority, name, duration minutes); lower priority number = more urgent
    (0, 2, "nightly-shard-1", 120), (0, 2, "nightly-shard-2", 120), (0, 2, "nightly-shard-3", 120),  ## Big nightly shards
    (10, 0, "PR-981 smoke", 15), (25, 0, "PR-984 smoke", 15), (30, 1, "release-candidate", 60),  ## Urgent work arriving later
]  ## Workload


def simulate(n_benches, jobs):  ## Non-preemptive priority scheduling on identical benches
    free_at = [0] * n_benches  ## When each bench becomes free
    pending, waits, t, i = [], {}, 0, 0  ## Ready queue, results, clock, next arrival
    jobs = sorted(jobs)  ## By arrival
    while i < len(jobs) or pending:  ## Until everything ran
        t = max(t, min(free_at))  ## Advance to the next free bench...
        if not pending and i < len(jobs):  ## ...or to the next arrival if nothing is waiting
            t = max(t, jobs[i][0])  ## Jump the clock
        while i < len(jobs) and jobs[i][0] <= t:  ## Everything that has arrived
            arrival, prio, name, dur = jobs[i]  ## Unpack
            heapq.heappush(pending, (prio, arrival, name, dur))  ## Most urgent first, then oldest
            i += 1  ## Next
        bench = free_at.index(min(free_at))  ## Earliest free bench
        if pending and free_at[bench] <= t:  ## A bench is free and work is waiting
            prio, arrival, name, dur = heapq.heappop(pending)  ## Pick
            waits[name] = t - arrival  ## Minutes spent queued
            free_at[bench] = t + dur  ## Busy until
        else:  ## Nothing to do yet
            t += 1  ## Tick
    return waits  ## Per-job queue time


for n in (3, 4):  ## Compare two lab sizes
    w = simulate(n, jobs)  ## Run
    print(f"{n} benches:", {k: v for k, v in w.items() if "nightly" not in k})  ## How long urgent work waited'''

M_11_4 = {
    "id": "11.4",
    "title": "System Design for Test Automation",
    "hours": 2,
    "summary": "How to answer \"design a test system\" questions: a repeatable structure, back-of-the-envelope capacity estimates in code, a scheduling trade-off you can quantify, and six full design questions with model answers.",
    "concepts": [
        {
            "title": "Estimate before you design",
            "concept": "Design answers improve when they start from numbers. Estimate bench-hours needed against bench-hours available (with a realistic utilisation factor), storage for captures and logs, and the size of the results database. The block does this for a nightly plan: 600 regression tests plus 24 long RvR tests on 6 benches.",
            "why": "Numbers turn opinions into decisions: \"we need two more benches or we cut RvR to weekly\", \"keeping every pcap is 33 TB a year, so we keep failures only\", \"a million rows a year doesn't need a data lake\". Interviewers look for exactly this grounding.",
            "syntax": "need = tests * minutes / 60\nhave = benches * hours * utilisation",
            "code": CAPACITY,
            "under": "The utilisation factor (0.6 to 0.8 in real labs) covers flaky equipment, reruns and maintenance; planning at 100% guarantees missed nightly windows. Storage estimates usually decide retention policy before any technology choice does.",
            "gotchas": [],
            "best": "Say your assumptions out loud, round generously, compute the two or three numbers that drive the design, and let them pick the architecture (and say which assumption would change the answer).",
        },
        {
            "title": "Quantify a trade-off: scheduling shared benches",
            "concept": "Shared hardware is the heart of most test-system designs. This simulation runs non-preemptive priority scheduling: long nightly shards are already running when urgent PR smoke tests and a release candidate arrive. It prints how long the urgent jobs waited with 3 and with 4 benches.",
            "why": "\"Should we reserve a bench for PR smoke tests?\" is a classic design follow-up. A ten-line simulation answers it with numbers: with every bench busy on two-hour shards, a 15-minute smoke test waits the better part of two hours unless a bench is kept free or long jobs are split.",
            "syntax": "heapq.heappush(pending, (priority, arrival, name, duration))",
            "code": SCHEDULER,
            "under": "Priority only decides who goes *next*; with non-preemptive jobs, urgent work still waits for a bench to free up. The fixes are structural: reserve capacity for short jobs, shard long suites into smaller pieces so benches free up often, or allow preemption at test boundaries (checkpointing).",
            "gotchas": [],
            "best": "In a design answer, name the resource that is scarce (benches, RF chambers, sniffers), then the policy for sharing it (locks, priorities, reservations, shard size) and the metric you'd watch (queue time per priority class).",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Each RvR point produces a 40 MB capture and 2 MB of logs; a run has 22 points × 3 iterations; you run it on 4 firmware branches nightly. Estimate storage per month and choose a retention rule that keeps it under 2 TB.",
            "solution": "Compute monthly volume, then the retention window that fits (or keep captures only for failing points).",
            "solution_code": """per_run_mb = 22 * 3 * (40 + 2)
monthly_tb = per_run_mb * 4 * 30 / 1e6
print(f"{per_run_mb / 1000:.2f} GB per run, {monthly_tb:.2f} TB per month")
days = int(2 / (per_run_mb * 4 / 1e6))
print(f"keep everything for {days} days, or keep logs always and captures only for failing points")""",
        },
        {
            "level": "Medium",
            "prompt": "A suite has 400 tests; each fails spuriously with probability 0.2% (flakiness). What is the chance a full run is green with no real bugs? How does one automatic rerun of failed tests change it?",
            "solution": "Independent tests: P(green) = (1 - p)^n. With one rerun, a test fails only if it fails twice: p².",
            "solution_code": """p, n = 0.002, 400
print(f"no reruns: {(1 - p) ** n:.1%} of clean runs are green")
print(f"one rerun: {(1 - p * p) ** n:.2%} green")
print(f"expected spurious failures per run: {p * n:.2f}")""",
        },
        {
            "level": "Hard",
            "prompt": "Design question: \"Design a flaky-test management system.\" Write a structured answer (requirements, data, detection, workflow, metrics).",
            "solution": "**Requirements:** detect flaky tests automatically, keep them visible without blocking merges, and drive them to a fix.\n\n**Data:** per-test outcome history from the results service (10.6), with build, bench, duration and failure signature.\n\n**Detection:** flip rate across recent runs on the same build; pass-on-rerun events; failures that correlate with a bench rather than a build.\n\n**Workflow:** auto-quarantine (a marker that runs the test but doesn't fail the build), auto-file a ticket with the history, owner from CODEOWNERS, an SLA to fix or delete, and un-quarantine after N clean runs.\n\n**Metrics:** number of quarantined tests and their age, flake rate per area, bench-correlated failures (which point to hardware), and time to fix.",
        },
    ],
    "interview": [
        {"level": "Advanced", "q": "Design an automated Wi-Fi regression system for 300 APs across 6 benches.", "a": "Clarify scale (tests, duration, branches, nightly window). Components: inventory and bench model (capabilities per bench); a scheduler with locks, priorities and sharding by duration; a pytest-based framework with bench-aware fixtures, markers and capability skips; equipment drivers with verify and reset; pre-flight health checks; results service with JUnit plus KPIs and raw artifacts; dashboards and triage summaries; CI integration (PR smoke, nightly regression, weekly RvR). Non-functional: reliability (reset to a known state, timeouts everywhere), observability (structured logs, console capture), security (vaulted credentials). Back it with a capacity estimate.", "follow": "What breaks first as you scale to 30 benches? (Scheduling and bench health: you need automatic bench quarantine and utilisation metrics.)"},
        {"level": "Advanced", "q": "Design the results pipeline from test run to dashboard.", "a": "Tests emit JUnit plus a structured KPI JSON with full metadata; a CI post step uploads both to a results API (validated, idempotent on run id); a relational store for runs/results/KPIs with indexes on build and test, object storage for logs and captures with retention; summaries computed in SQL; dashboards for pass rate per build, KPI trends against baselines, flakiness; notifications for new failures only.", "follow": "How do you compare KPIs fairly across benches? (Store bench calibration and compare like with like; baselines per bench.)"},
        {"level": "Advanced", "q": "How would you design a lab reservation system?", "a": "Resources with capabilities and health state; reservations with time windows and owners; automatic leases for CI with heartbeats and expiry so crashed jobs release benches; priorities and reserved capacity for short PR jobs; an API plus Jenkins lock integration; audit log; and utilisation and queue-time metrics.", "follow": "How do you avoid deadlock when a job needs two resources? (Acquire in a global order or atomically, with timeouts.)"},
        {"level": "Advanced", "q": "Design firmware upgrade testing for a fleet of APs.", "a": "Matrix of upgrade paths (n-1 to n, n-2 to n, downgrade) and configurations; automate flash plus verify (version, config preserved, radios up, clients rejoin, KPIs within tolerance); test interrupted upgrades (power loss, network drop) and rollback; staged rollout with health gates in the field; capture console logs for every upgrade.", "follow": "What's the riskiest case? (Interrupted upgrade: test power-cut at different points with a controllable PDU.)"},
        {"level": "Intermediate", "q": "How do you structure any system design answer?", "a": "Clarify requirements and scale; estimate the key numbers; draw the main components and data flow; go deep on the hardest part (usually shared hardware or data volume); cover failure handling, observability and security; finish with trade-offs and what you'd do next.", "follow": "How long on each part in 30 minutes? (5 clarify/estimate, 10 components, 10 deep dive, 5 trade-offs.)"},
        {"level": "Advanced", "q": "Design log collection for a 6-bench lab.", "a": "Every device and test host ships logs (syslog, console via serial servers, test logs) to a central collector with bench and device tags and UTC timestamps; per-test time windows let the framework attach the relevant slice to each failure; retention tiers; parsers (like 10.1) turn crash and radar events into structured events that can fail tests or annotate results.", "follow": "How do you correlate an AP crash with the test that triggered it? (Synchronised clocks via NTP/PTP and test start/stop markers written into the logs.)"},
    ],
    "quiz": [
        {"q": "The first step in a design answer is...", "options": ["Draw boxes", "Pick a database", "Clarify requirements and scale", "Write code"], "answer": 2, "why": "Then estimate."},
        {"q": "Why plan bench capacity at ~75% utilisation?", "options": ["Licensing", "Failures, reruns and maintenance eat time", "Power", "It's a standard"], "answer": 1, "why": "100% plans always slip."},
        {"q": "Priority scheduling alone doesn't help urgent jobs when...", "options": ["Jobs are short", "Long non-preemptive jobs hold every bench", "There are many benches", "Never"], "answer": 1, "why": "Reserve capacity or shard."},
    ],
    "cards": [
        {"front": "Design answer shape", "back": "Clarify → estimate → components → deep dive → failures/observability/security → trade-offs"},
        {"front": "Scarce resource", "back": "Benches/chambers: locks, priorities, reserved capacity, shard size, queue-time metric"},
        {"front": "Flake math", "back": "P(green) = (1-p)^n; one rerun → (1-p²)^n"},
    ],
}


# --------------------------------------------------------------------------- 11.5
STAR_CHECK = '''import re  ## Word and number detection

answer = {  ## An EXAMPLE answer to adapt; replace every detail with your own experience
    "situation": "Our nightly Wi-Fi regression on six benches was failing about a third of runs, and the team had stopped trusting red builds.",  ## Context: brief, specific
    "task": "I was asked to make the nightly results trustworthy again before the 7.4 release, about four weeks out.",  ## Your responsibility
    "action": "I pulled three months of JUnit results, grouped failures by signature, and found most came from two benches with an attenuator that dropped commands. "  ## What YOU did, step by step...
              "I added a pre-flight check that verified every attenuator and took bad benches out of the pool, replaced fixed sleeps with polling, and quarantined five flaky tests with tickets.",  ## ...concrete actions, not adjectives
    "result": "Spurious failures fell from 31% of runs to under 3% within two weeks, the team went back to treating red as real, and the pre-flight check became part of every pipeline.",  ## Measurable outcome + lasting change
}  ## Situation, Task, Action, Result


def review(star):  ## Quick self-check of an answer's shape
    words = {k: len(v.split()) for k, v in star.items()}  ## Length per part
    total = sum(words.values())  ## About 140 words is ~1 minute spoken; aim for 1.5-2 minutes
    action_share = words["action"] / total  ## Most of the answer should be what YOU did
    i_count = len(re.findall(r"\\bI\\b", star["action"]))  ## Ownership
    we_count = len(re.findall(r"\\b[Ww]e\\b", star["action"]))  ## Team credit (fine, but not instead of "I")
    has_number = bool(re.search(r"\\d", star["result"]))  ## A measurable outcome
    print("words per part:", words, "total:", total)  ## Balance
    print(f"action share: {action_share:.0%} (aim for 50-60%)")  ## The part interviewers score
    print(f"'I' vs 'we' in action: {i_count} vs {we_count}")  ## Make your contribution clear
    print("result has a number:", has_number)  ## Quantified impact
    return action_share >= 0.4 and has_number and i_count >= we_count  ## Simple pass/fail


print("ready to use:", review(answer))  ## Run this on your own stories'''

STORY_BANK = '''themes = ["conflict", "failure", "deadline", "ownership", "influence", "ambiguity", "learning", "quality vs speed"]  ## What behavioral questions probe

stories = {  ## Your story bank: EXAMPLE titles; replace with your own experiences
    "Fixed flaky nightly runs": {"ownership", "quality vs speed", "influence"},  ## Each story can answer several themes
    "Missed a firmware regression": {"failure", "learning"},  ## A real mistake and what changed afterwards
    "Disagreed on test scope with dev lead": {"conflict", "influence"},  ## Disagreement handled well
    "Built RvR automation in 3 weeks": {"deadline", "ambiguity", "ownership"},  ## Pressure and unclear requirements
}  ## 4-6 strong stories usually cover everything

width = max(map(len, stories)) + 2  ## Column width for the table
print(" " * width + " ".join(t[:4] for t in themes))  ## Header row (abbreviated themes)
for title, covers in stories.items():  ## One row per story
    print(title.ljust(width) + " ".join(" X  " if t in covers else " .  " for t in themes))  ## Coverage marks
gaps = [t for t in themes if not any(t in covers for covers in stories.values())]  ## Themes with no story
print("gaps:", gaps or "none")  ## Prepare a story for each gap'''

BEHAVIORAL = [
    ("Tell me about a time you found a serious bug late in a release.", "**Example to adapt; use your own experience.** S: two days before a release, a nightly RvR run showed 5 GHz range down 6 dB on the release candidate. T: confirm it was real and get it to the right team fast enough to matter. A: I reran on a second bench to rule out the setup, bisected the firmware builds with an automated script, and narrowed it to a rate-control change; I sent the developer the comparison chart, the commit and a one-line reproduction. R: the fix landed the next day, the release went out on time, and RvR was added to the release-candidate gate so the gap couldn't recur."),
    ("Describe a disagreement with a developer or lead and how you resolved it.", "**Example to adapt.** S: a dev lead wanted to drop roaming tests from PR checks because they were slow. T: keep coverage without blocking developers. A: I measured the tests (12 minutes, 2 real catches in a quarter), proposed running a 2-minute roaming smoke on PRs and the full set nightly, and offered to own the change. R: we agreed on the split, PR time dropped by 10 minutes, and the nightly set caught the next roaming regression. The point is data, a compromise, and owning the follow-through."),
    ("Tell me about a mistake you made.", "**Example to adapt.** S: I merged a fixture change that silently skipped the 6 GHz tests on every bench. T: as the author, I had to own it. A: when a teammate noticed the drop in test count, I confirmed the cause, fixed it the same day, and added a check that fails the run if the collected-test count falls more than 10% below the last run. R: we lost two nights of 6 GHz coverage; the guard has since caught two similar problems. Show what you changed so it can't happen again."),
    ("Describe a time you automated something that saved the team time.", "**Example to adapt.** S: engineers spent an hour each morning reading logs from failed nightly runs. T: cut triage time. A: I wrote a summary tool that grouped failures by signature, attached the relevant AP log slice, and posted one message to chat. R: triage dropped to about 15 minutes and duplicate bug reports stopped. Quantify the before and after."),
    ("Tell me about working with unclear requirements.", "**Example to adapt.** S: I was asked to \"automate Wi-Fi 7 testing\" with no test plan. T: turn that into something deliverable. A: I listed candidate areas, ranked them with the PM by risk and customer impact, agreed on MLO throughput and roaming as phase one, and shipped those in three weeks with a review after each. R: phase one caught two MLO bugs before beta, and the ranking became the roadmap for phase two."),
    ("How do you handle being asked to cut testing to meet a deadline?", "**Example to adapt.** Make the risk explicit rather than refusing: show what each option covers (for example, a risk-based subset that keeps security, roaming and upgrade paths), state what is not covered and its likely impact, get the decision owner to choose consciously, and schedule the remaining tests right after release. It shows judgement, not obstruction."),
    ("Tell me about a time you influenced without authority.", "**Example to adapt.** S: other teams kept writing their own bench setup scripts. T: get them to adopt the shared framework. A: I made it easy (a quick-start guide, a template repo, office hours), migrated one team's suite myself as a showcase, and shared the reliability numbers. R: three teams moved within a quarter and bench-related failures dropped."),
    ("Why do you want this role?", "**Template.** Connect three things: what the role needs (from the job description), evidence you've done it (one specific achievement with a number), and what you want to learn or build next that this team offers. Keep it under a minute and specific to the company."),
]

M_11_5 = {
    "id": "11.5",
    "title": "Behavioral Answers (STAR)",
    "hours": 1.5,
    "summary": "The STAR structure (Situation, Task, Action, Result), a self-check for your answers, a story bank that covers the common themes, and eight common behavioral questions with example answers to adapt to your own experience.",
    "concepts": [
        {
            "title": "STAR and a quick self-check",
            "concept": "Behavioral questions (\"tell me about a time...\") are scored on structure and evidence. **S**ituation and **T**ask set context briefly; **A**ction (what *you* did) should be about half the answer; **R**esult should be measurable and include what you learned or changed. The block holds an example answer, clearly an example to adapt, and checks its shape: words per part, the share spent on action, \"I\" vs \"we\", and whether the result has a number.",
            "why": "Strong engineers often give weak behavioral answers: long situations, \"we\" everywhere, no result. Interviewers can't credit what you don't say, so the structure is how your real work gets counted.",
            "syntax": "S (1-2 sentences) → T (1 sentence) → A (most of it, \"I\") → R (numbers + lesson)",
            "code": STAR_CHECK,
            "under": "The checks are deliberately crude, but they catch the three most common problems: context that drags on, actions told in \"we\" so your part is invisible, and results without a measure. A spoken answer of 1.5 to 2 minutes is about 200 to 280 words.",
            "gotchas": [],
            "best": "Write your stories down, run them through a check like this, say them out loud with a timer, and use only true stories from your own experience: interviewers probe details, and the examples here are templates, not scripts.",
        },
        {
            "title": "A story bank that covers the themes",
            "concept": "Most behavioral questions probe a handful of themes: conflict, failure, deadlines, ownership, influence, ambiguity, learning, and quality vs speed. Four to six good stories, each able to answer several themes, cover nearly every question. The block prints a coverage matrix and lists themes with no story yet.",
            "why": "Under pressure people grab the first story that comes to mind, even if it fits badly. A prepared bank lets you pick the best story for the question and avoid telling the same one twice in a loop of interviews.",
            "syntax": "stories = {\"title\": {\"theme\", ...}}\ngaps = [t for t in themes if not any(t in s for s in stories.values())]",
            "code": STORY_BANK,
            "under": "The same story can be told from different angles: \"fixed flaky nightly runs\" answers ownership (you took it on), influence (you got others to change habits) and quality vs speed (you argued for reliability). Prepare the angle, not just the story.",
            "gotchas": [],
            "best": "Keep the bank in one document with a STAR outline per story, one number per result, and a note of which themes it covers; refresh it before each interview with the job description's priorities.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Write your own 30-second introduction: current role, two achievements relevant to this job (with numbers), and why this role. Read it aloud with a timer.",
            "solution": "Shape: \"I'm a [role] working on [area]. Recently I [achievement 1 with number] and [achievement 2 with number]. I'm looking for [what this role offers] because [genuine reason].\" About 70 to 80 words is 30 seconds spoken.",
        },
        {
            "level": "Medium",
            "prompt": "Turn one real experience of yours into a full STAR answer and run it through the checker from the first concept. Revise until the action share is at least half and the result has a number.",
            "solution": "Typical fixes: cut the situation to two sentences; split the action into three concrete steps starting with \"I\"; add a before/after measure to the result (time saved, failures reduced, bugs caught before release) and one sentence on what you changed afterwards.",
        },
        {
            "level": "Hard",
            "prompt": "Build your story bank: list five of your own stories, map each to the themes, and fill any gaps. Then prepare a 'failure' story whose result includes what you changed so it can't recur.",
            "solution": "A good failure story owns the mistake plainly, keeps the damage in proportion, spends most of the time on the recovery and the systemic fix (a check, a process change, a test), and ends with evidence the fix worked. Avoid fake failures (\"I work too hard\"); interviewers discount them.",
        },
    ],
    "interview": [{"level": "Intermediate", "q": q, "a": a} for q, a in BEHAVIORAL],
    "quiz": [
        {"q": "Which STAR part should take the most time?", "options": ["Situation", "Task", "Action", "Result"], "answer": 2, "why": "What you did."},
        {"q": "A strong result includes...", "options": ["Who was to blame", "A measure and what changed afterwards", "Only team credit", "Technical jargon"], "answer": 1, "why": "Quantified impact plus learning."},
        {"q": "How many prepared stories usually cover most questions?", "options": ["1", "4-6", "20", "50"], "answer": 1, "why": "Each covers several themes."},
    ],
    "cards": [
        {"front": "STAR", "back": "Situation (brief), Task, Action (~half, 'I'), Result (number + lesson)"},
        {"front": "Themes", "back": "Conflict, failure, deadline, ownership, influence, ambiguity, learning, quality vs speed"},
        {"front": "Failure story", "back": "Own it, keep it proportionate, focus on the recovery and the systemic fix"},
    ],
}


# --------------------------------------------------------------------------- 11.6
PLAN = '''import random  ## Seeded selection

BANK = {  ## A small question bank per section (extend it with your weak areas from the Interview page)
    "python": ["Mutable default arguments", "Generators vs lists", "Decorators with arguments", "GIL and concurrency", "Context managers"],  ## Language
    "pytest": ["Fixture scopes and teardown", "Parametrize vs fixtures", "conftest and hooks", "Mocking a device API", "Handling flaky tests"],  ## Testing
    "automation": ["Concurrent SSH to 200 devices", "Parsing CLI output safely", "Attenuator control with verification", "RvR methodology", "Join time from a pcap"],  ## Domain automation
    "cicd": ["Jenkins stage design for hardware", "pytest exit codes in CI", "Secrets in pipelines", "Speeding up a 10-hour suite"],  ## CI/CD
    "coding": ["Longest RSSI run above a floor", "Merge bench reservations", "LRU session cache", "Retry decorator with backoff", "Top-k error signatures"],  ## Coding problems (11.3)
    "design": ["Regression system for 300 APs", "Results pipeline", "Lab reservation system", "Flaky-test management"],  ## System design (11.4)
}  ## Sections
AGENDA = [("Intro and your background", 5, None), ("Rapid fire", 8, ("python", 3)), ("Testing deep dive", 8, ("pytest", 2)),  ## (block, minutes, (section, how many))
          ("Automation scenario", 7, ("automation", 1)), ("Coding", 15, ("coding", 1)), ("Design", 10, ("design", 1)),  ## Technical core
          ("CI/CD", 4, ("cicd", 1)), ("Your questions", 3, None)]  ## Wrap-up


def plan(seed):  ## A reproducible 60-minute mock
    rng = random.Random(seed)  ## Same seed -> same interview (useful to retry it later)
    clock = 0  ## Minutes elapsed
    for block, minutes, pick in AGENDA:  ## In order
        chosen = rng.sample(BANK[pick[0]], pick[1]) if pick else []  ## Draw questions without repeats
        print(f"{clock:02d}-{clock + minutes:02d} min  {block}" + (": " + "; ".join(chosen) if chosen else ""))  ## One agenda line
        clock += minutes  ## Advance
    print("total:", clock, "minutes")  ## Should be 60


plan(seed=11)  ## Change the seed for a fresh mock'''

RUBRIC = '''RUBRIC = {  ## Weight of each skill in the overall score
    "communication": 0.20, "python": 0.20, "testing": 0.20, "automation": 0.15, "problem_solving": 0.15, "design": 0.10,  ## Typical weighting for a test automation role
}  ## Weights sum to 1
SCALE = {1: "no hire", 2: "lean no", 3: "lean hire", 4: "hire", 5: "strong hire"}  ## Typical 1-5 scale

scores = {"communication": 4, "python": 4, "testing": 5, "automation": 4, "problem_solving": 3, "design": 2}  ## Your self-ratings after a mock
assert abs(sum(RUBRIC.values()) - 1) < 1e-9 and scores.keys() == RUBRIC.keys()  ## Sanity checks
overall = sum(RUBRIC[k] * scores[k] for k in RUBRIC)  ## Weighted average
print(f"overall: {overall:.2f} ({SCALE[round(overall)]})")  ## Headline
weakest = sorted(RUBRIC, key=lambda k: (scores[k], -RUBRIC[k]))[:2]  ## Lowest score first; ties -> heavier weight first
print("drill next:", weakest)  ## Where practice pays most
gain = {k: RUBRIC[k] * (5 - scores[k]) for k in RUBRIC}  ## Score points available per skill
print("biggest upside:", max(gain, key=gain.get), f"(+{max(gain.values()):.2f})")  ## Weight x room to improve'''

MOCK = [
    ("Intermediate", "Walk me through how you'd automate a client roaming test end to end.", "Bench with two APs on a shared SSID and a programmable attenuator per AP path; a client (or traffic generator) associated to AP1; continuous traffic; ramp attenuation to push the client toward AP2; capture with a sniffer on both channels; measure roam time (reassociation to 4-way completion, or FT exchange), packet loss and throughput gap; repeat per security mode and band with iterations; pytest parametrization, KPIs as data, artifacts attached on failure."),
    ("Intermediate", "What happens when a fixture with `yield` raises during teardown?", "The test's own result is recorded, and the teardown error is reported separately as an error on that test, so cleanup failures are visible without hiding the test outcome. Keep teardown defensive (try/finally per resource) so one failure doesn't skip the rest."),
    ("Intermediate", "Your nightly run went from 2 to 40 failures. What do you do in the first 15 minutes?", "Look at the shape before the details: group failures by signature and by bench; check what changed (firmware, framework commit, lab infrastructure); look at the first failure in time order. Forty failures on one bench with the same timeout is infrastructure; spread across benches after a firmware change is a regression."),
    ("Advanced", "How would you test a Python library that talks to 5 different AP vendors?", "A common interface with a driver per vendor; unit tests for each driver against recorded responses (fixtures per firmware version); contract tests that run the same suite against every driver; a few integration tests per vendor on real hardware, marked and run nightly; simulators for error cases that are hard to produce on real devices."),
    ("Intermediate", "Explain async vs threads for polling 500 APs via REST.", "Both work for I/O-bound polling. asyncio with httpx/aiohttp scales to thousands of concurrent requests in one thread with low overhead and explicit cancellation and timeouts; threads are simpler with blocking libraries but heavier per connection. Bound concurrency either way (semaphore or pool size) to protect the controller."),
    ("Advanced", "How do you make an RvR result reproducible six months later?", "Store the test plan, raw per-iteration data, firmware and framework versions, bench id and calibration, attenuator and traffic-generator settings, environment (channel, width, power), and the code commit; keep the analysis as code that regenerates charts from raw data."),
    ("Beginner", "What does `pytest -k \"roam and not 6G\" -m smoke -x -v` do?", "Runs tests whose names match the keyword expression (contain roam, not 6G), restricted to the smoke marker, stopping at the first failure, with verbose per-test output."),
    ("Intermediate", "How would you review a teammate's test automation pull request?", "Correctness of what is asserted (does the test fail when the feature breaks?), determinism (no sleeps, isolated state), cleanup, clear names and failure messages, reuse of fixtures and helpers, markers and runtime, and whether the change is covered in CI."),
    ("Advanced", "A test passes alone but fails in the full suite. How do you debug it?", "It depends on order or shared state: run it after the preceding tests to reproduce (pytest-randomly or `-p no:randomly` to control order), bisect the set of preceding tests, look for module-level state, session fixtures that are mutated, leftover device configuration, environment variables, and monkeypatches that weren't undone."),
    ("Intermediate", "What metrics would you put on a Wi-Fi test dashboard?", "Pass rate per build and per area, new vs existing failures, flaky test count, KPI trends against baselines (throughput at key attenuations, join and roam time), bench utilisation and health, and suite duration."),
    ("Advanced", "How do you decide what to automate first?", "Rank by value over cost: frequency of execution, risk of the area, manual effort saved, stability of the feature and how deterministic the test can be. Release-gating smoke tests and high-churn areas first; rare, unstable or exploratory tests later or never."),
    ("Intermediate", "What questions should you ask the interviewer?", "About the work: what the lab looks like and how tests are scheduled, how results drive release decisions, what the biggest pain in the current framework is, how success in the first 90 days is measured, and how the team splits development and test ownership."),
]

M_11_6 = {
    "id": "11.6",
    "title": "Mock Interview",
    "hours": 1.5,
    "summary": "Run a realistic 60-minute mock: a reproducible plan generated from a question bank, a weighted scoring rubric that tells you what to drill next, and twelve mixed questions with model answers to finish the course.",
    "concepts": [
        {
            "title": "Generate a reproducible mock plan",
            "concept": "A mock only helps if it feels like the real thing: timed blocks, a mix of question types, and questions you didn't pick yourself. The generator draws questions per section from a bank with a seeded random generator, so the same seed reproduces the same mock for a retry after you've studied, and a new seed gives a fresh one. Run it, then do the interview out loud with a timer or with a friend asking the questions.",
            "why": "Most interview failures are about delivery under time pressure, not knowledge: rambling on an early question, freezing on the coding problem, or never getting to trade-offs in the design. Timed practice is the only fix.",
            "syntax": "rng = random.Random(seed)\nrng.sample(questions, k)",
            "code": PLAN,
            "under": "`random.Random(seed)` creates an independent generator, so the plan is reproducible and doesn't disturb the global random state. `sample` draws without replacement, so no question repeats within a section.",
            "gotchas": [],
            "best": "Do at least three full mocks before a real interview: one alone (recorded), one with a peer, and one on a seed you've retried after studying. Feed the weak questions into the Interview page's \"review again\" list.",
        },
        {
            "title": "Score yourself and pick what to drill",
            "concept": "Interviewers score against a rubric: communication, language skill, testing, domain automation, problem solving and design, each weighted. After a mock, rate yourself 1 to 5 per skill; the block computes the weighted score, the two weakest skills, and the skill with the biggest upside (weight times room to improve), which is where an hour of practice pays most.",
            "why": "Practising what you're already good at feels productive but moves the score least. A weighted rubric turns \"I should prepare more\" into \"spend tonight on design questions\".",
            "syntax": "overall = sum(weight[k] * score[k] for k in weight)\nupside = weight[k] * (5 - score[k])",
            "code": RUBRIC,
            "under": "Sorting by `(score, -weight)` breaks ties toward the more heavily weighted skill. The upside calculation is a simple expected-value argument: improving a low-weight skill by two points can matter less than a high-weight one by one point.",
            "gotchas": [],
            "best": "Rate yourself honestly right after each mock, ask your mock partner for the same ratings, track the numbers across mocks, and stop drilling a skill once it reaches 4.",
        },
    ],
    "exercises": [
        {
            "level": "Easy",
            "prompt": "Generate three different mock plans by changing the seed, pick one, and run it out loud with a 60-minute timer. Note every question where you paused for more than 10 seconds.",
            "solution": "The pauses are your study list. For each, write a three-sentence answer (result or claim, mechanism, example from your work) and retry the same seed after a few days.",
        },
        {
            "level": "Medium",
            "prompt": "Implement Leitner-box review for interview questions: answered correctly moves a question up a box (reviewed less often), wrong moves it back to box 1. Simulate 5 sessions and print which questions are due each session.",
            "solution": "Box n is reviewed every 2^(n-1) sessions; correct answers promote, wrong ones reset.",
            "solution_code": """import random

rng = random.Random(3)
boxes = {q: 1 for q in ["GIL", "fixtures", "RvR", "LRU", "roam time", "Jenkins locks"]}
skill = {"GIL": 0.9, "fixtures": 0.95, "RvR": 0.6, "LRU": 0.5, "roam time": 0.7, "Jenkins locks": 0.8}
for session in range(1, 6):
    due = [q for q, box in boxes.items() if (session - 1) % 2 ** (box - 1) == 0]
    for q in due:
        boxes[q] = min(boxes[q] + 1, 4) if rng.random() < skill[q] else 1
    print(f"session {session}: reviewed {due}")
print("final boxes:", boxes)""",
        },
        {
            "level": "Hard",
            "prompt": "Final project: run a full mock with a peer using a fresh seed, score yourself with the rubric, then write a one-page plan for the next week covering the two weakest skills, using specific modules of this course.",
            "solution": "A good plan names concrete modules and outputs, for example: design (11.4 questions out loud plus one estimate exercise per day), problem solving (two 11.3 problems per day with brute-force-then-optimise), a second mock at the end of the week on the same seed, and rescoring to confirm the improvement.",
        },
    ],
    "interview": [{"level": lvl, "q": q, "a": a} for lvl, q, a in MOCK],
    "quiz": [
        {"q": "Why seed the mock generator?", "options": ["Speed", "Reproduce the same mock for a retry", "Required by random", "Security"], "answer": 1, "why": "Same seed, same questions."},
        {"q": "Where does an hour of practice pay most?", "options": ["Your strongest skill", "Highest weight × room to improve", "Random topic", "Behavioral only"], "answer": 1, "why": "Expected gain."},
        {"q": "A test passes alone but fails in the suite: likely cause?", "options": ["Python version", "Shared state or order dependence", "Network only", "pytest bug"], "answer": 1, "why": "Bisect the preceding tests."},
    ],
    "cards": [
        {"front": "60-minute mock", "back": "5 intro, 8 rapid fire, 8 testing, 7 automation, 15 coding, 10 design, 4 CI/CD, 3 your questions"},
        {"front": "After each mock", "back": "Score with the rubric → drill the biggest upside → retry the same seed"},
        {"front": "Ask the interviewer", "back": "Lab and scheduling, how results drive releases, framework pain points, 90-day success"},
    ],
}
