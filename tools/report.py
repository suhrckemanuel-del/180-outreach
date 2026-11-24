"""Build out/report.html: one self-contained status page for this outreach kit. Zero LLM tokens.

    python tools/report.py            writes out/report.html and prints its path
    python tools/report.py --out X    writes somewhere else

Read-only. It reads the tenant's pipeline.yaml, targets.yaml and cards/, state/sent.log and
state/calls.yaml, out/shortlist.csv and docs/decisions-2026-11-25.md, plus the hand-edited
docs/next-10-days.md.

It never prints a contact person's name or an email address: cards are reduced to the organisation,
the verdict and the reason line, and any name or address that slips into free text is scrubbed
against the people the pipeline and the cards name.

No server and no external CSS, JS, fonts or images: the file opens by double-click.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tenant  # noqa: E402

ROOT = tenant.ROOT
SEND_END = dt.date(2026, 12, 22)          # limits.yaml last_send_date
GOAL_SIGNED = "2-3 signed projects by mid-January 2027"
EMAIL_GOAL = 1000                          # about 1,000 emails by 22 Dec
DECISIONS = "docs/decisions-2026-11-25.md"
NEXT_DAYS = "docs/next-10-days.md"
SHORTLIST = "out/shortlist.csv"

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]*")  # also catches a bare "management@"
ORG_LINE = re.compile(r"^ORG:\s*([^|\n]+?)\s*\|.*?(https?://\S+)", re.M)
ORG_LINE_PLAIN = re.compile(r"^ORG:\s*(.*?)\s+(https?://\S+)", re.M)
VERDICT_LINE = re.compile(r"^VERDICT:\s*(FIT|REJECT)\s*[:.\-]?\s*(.*)$", re.M | re.I)
PEOPLE_LINE = re.compile(r"^PEOPLE:\s*(.+)$", re.M)
DECISION_LINE = re.compile(r"\*\*(D\d+)\.\s*(.*?)\*\*", re.S)
ANSWER_LINE = re.compile(r"(?im)^Answer[^:\n]*:[ \t]*([^\n]*)$")
HEADING = re.compile(r"(?m)^##\s+(.+)$")

UNLOCKS = {
    1: "childcare, youth-care and welzijn leads, and the cultural/housing penalty in the gate",
    2: "one more official childcare source for targets.yaml",
    3: "the 'hiring for AI or admin' signal from job boards",
    4: "a Maps fallback if the free registers run short",
    5: "company-size enrichment, low value",
    6: "three member lists by email, drafted for Manuel to send",
    7: "the changemakers leftover from batch 1",
    8: "the socialdebt subject line",
    9: "the ledger wording ticket",
    10: "the January volume wave and the 1,000-email goal",
    11: "a second inbox for the January volume",
    12: "Postmaster Tools and DMARC reports",
    13: "the project-shaped ask in the ledger",
    14: "the legal team's answer before volume rises",
    15: "Manuel's cold-call hours and weekly number",
    16: "LinkedIn notes for the top leads",
    17: "a commit at the end of each session",
}


# ------------------------------------------------------------------------------- read-only inputs


def _load(path: Path, default):
    if not path.exists():
        return default
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return default
    return default if data is None else data


def read_targets() -> list[dict]:
    return (_load(tenant.DIR / "targets.yaml", {}) or {}).get("candidates") or []


def read_pipeline() -> list[dict]:
    return (_load(tenant.PIPELINE, {}) or {}).get("orgs") or []


def read_sent() -> list[list[str]]:
    if not tenant.SENT_LOG.exists():
        return []
    rows = []
    for line in tenant.SENT_LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(line.split("\t"))
    return rows


def read_calls() -> list[dict]:
    return (_load(tenant.STATE / "calls.yaml", {}) or {}).get("calls") or []


def read_shortlist() -> list[dict]:
    path = ROOT / SHORTLIST
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return [r for r in csv.DictReader(fh) if (r.get("domain") or "").strip()]


def read_cards() -> tuple[list[dict], set[str]]:
    """(cards, people). People are only ever used to scrub free text, never printed."""
    cards, people = [], set()
    for path in sorted((tenant.DIR / "cards").glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        m = ORG_LINE.search(text) or ORG_LINE_PLAIN.search(text)
        v = VERDICT_LINE.search(text)
        if not m or not v:
            continue
        for line in PEOPLE_LINE.findall(text):
            for part in line.split(";"):
                name = part.split(",")[0].strip()
                if len(name) > 2:
                    people.add(name)
        cards.append({
            "name": m.group(1).strip(),
            "domain": tenant.domain_of(m.group(2)),
            "verdict": v.group(1).upper(),
            "why": (v.group(2).strip() or "(no reason given)").rstrip("."),
        })
    return cards, people


def read_decisions() -> list[dict]:
    path = ROOT / DECISIONS
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    marks = list(DECISION_LINE.finditer(text))
    out = []
    for i, m in enumerate(marks):
        block = text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        ans = ANSWER_LINE.search(block)
        section = ""
        for h in HEADING.finditer(text[: m.start()]):
            section = h.group(1).strip()
        out.append({
            "id": int(m.group(1)[1:]),
            "code": m.group(1),
            "title": m.group(2).strip().rstrip("."),
            "answer": ans.group(1).strip() if ans else "",
            "section": section,
        })
    return out


def read_next_days() -> str:
    path = ROOT / NEXT_DAYS
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


# ---------------------------------------------------------------------------------------- numbers


def funnel_numbers(targets, cards, pipeline, shortlist) -> list[tuple[str, int | None, str]]:
    touches = [t for org in pipeline for t in (org.get("touches") or [])]
    gate = sum(1 for r in shortlist if (r.get("verdict") or "").upper() == "GO") if shortlist else None
    return [
        ("Candidates in the list", len(targets), "every row in targets.yaml"),
        ("Passed the gate", gate, "GO rows in out/shortlist.csv" if gate is not None
         else "not measured yet: run enrich.py batch --csv"),
        ("Researched (a card exists)", len(cards), "one card per organisation"),
        ("Fit", sum(1 for c in cards if c["verdict"] == "FIT"), "cards whose verdict is FIT"),
        ("Drafted", sum(1 for t in touches if t.get("body")), "touches with a written body"),
        ("Approved", sum(1 for t in touches if t.get("approved")), "touches Manuel approved"),
        ("Sent", sum(1 for t in touches if t.get("sent")), "touches with a send time"),
        ("Replied", sum(1 for t in touches if t.get("status") == "replied"), "touches whose thread has a reply"),
        ("Calls", sum(1 for o in pipeline if o.get("outcome") in ("call", "proposal", "signed")),
         "organisations with outcome call or better"),
        ("Signed", sum(1 for o in pipeline if o.get("outcome") == "signed"), "organisations with outcome signed"),
    ]


def biggest_drop(stages) -> int | None:
    """Index of the stage ending the largest fall between two measured stages."""
    best, idx = 0, None
    for i in range(1, len(stages)):
        a, b = stages[i - 1][1], stages[i][1]
        if isinstance(a, int) and isinstance(b, int) and a > 0 and b - a < best:
            best, idx = b - a, i
    return idx


def status_of(org: dict | None) -> str:
    if not org:
        return "not in the pipeline"
    if org.get("outcome"):
        return f"outcome: {org['outcome']}"
    touches = org.get("touches") or []
    if not touches:
        return org.get("status") or "in the pipeline"
    t = touches[-1]
    bits = []
    if t.get("sent"):
        bits.append("sent " + str(t["sent"])[:10])
    if t.get("status") not in (None, "", "sent"):
        bits.append(str(t["status"]))
    return " · ".join(bits) or str(t.get("status") or "in the pipeline")


# ------------------------------------------------------------------------------------------- html


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def scrub(text: str, people: set[str]) -> str:
    """Remove every email address and every known person's name from one piece of plain text.

    Word boundaries and a three-character minimum matter: a test contact called S must never rewrite
    the s in a CSS class, and a person called Max must not rewrite max-width. That is also why this
    runs on the values that go into the page, never on the assembled HTML.
    """
    text = EMAIL_RE.sub("(address removed)", text or "")
    for name in sorted((n for n in people if len(n) >= 3), key=len, reverse=True):
        text = re.sub(r"(?<!\w)" + re.escape(name) + r"(?!\w)", "(name removed)", text, flags=re.I)
    return text


def render_funnel(stages, mark) -> str:
    top = max([v for _, v, _ in stages if isinstance(v, int)] or [1]) or 1
    rows = []
    for i, (label, value, note) in enumerate(stages):
        width = 0 if not isinstance(value, int) else max(2, round(100 * value / top))
        shown = "—" if value is None else f"{value:,}"
        rows.append(
            f'<tr class="{"drop" if i == mark else ""}">'
            f'<th scope="row">{esc(label)}</th>'
            f'<td class="num">{shown}</td>'
            f'<td class="bar"><span style="width:{width}%"></span></td>'
            f'<td class="note">{esc(note)}{" <b class=\"tag\">biggest drop</b>" if i == mark else ""}</td>'
            f"</tr>"
        )
    return f'<table class="funnel"><tbody>{"".join(rows)}</tbody></table>'


def render_batch(cards, pipeline, people) -> str:
    if not cards:
        return "<p class=\"meta\">No research cards yet.</p>"
    by_domain = {o.get("domain"): o for o in pipeline}
    ordered = sorted(cards, key=lambda c: (c["verdict"] != "FIT", c["name"].lower()))
    rows = "".join(
        f'<tr><td>{esc(c["name"])}</td>'
        f'<td class="v {c["verdict"].lower()}">{esc(c["verdict"])}</td>'
        f'<td>{esc(scrub(c["why"], people))}</td>'
        f'<td>{esc(status_of(by_domain.get(c["domain"])))}</td></tr>'
        for c in ordered
    )
    return ('<table class="batch"><thead><tr><th>Organisation</th><th>Verdict</th>'
            f'<th>Why, in one line</th><th>Live status</th></tr></thead><tbody>{rows}</tbody></table>')


def render_shortlist(shortlist) -> str:
    if not shortlist:
        return '<p class="meta">run enrich.py batch --csv first</p>'
    def score(r):
        try:
            return int(r.get("score") or 0)
        except ValueError:
            return 0
    top = sorted(shortlist, key=score, reverse=True)[:40]
    rows = "".join(
        f'<tr><td class="num">{i}</td><td class="num">{esc(r.get("score"))}</td>'
        f'<td>{esc(r.get("name"))}</td><td>{esc(r.get("city"))}</td>'
        f'<td>{esc(r.get("segment"))}</td>'
        f'<td class="v {"go" if (r.get("verdict") or "").upper() == "GO" else ""}">{esc(r.get("verdict"))}</td>'
        f'<td class="note">{esc(", ".join((r.get("reasons") or "").split(";")[:2]))}</td></tr>'
        for i, r in enumerate(top, 1)
    )
    return ('<table class="shortlist"><thead><tr><th>#</th><th>Score</th><th>Organisation</th>'
            f'<th>City</th><th>Segment</th><th>Verdict</th><th>Signals</th></tr></thead><tbody>{rows}</tbody></table>')


def render_blocked(decisions, people) -> str:
    if not decisions:
        return f'<p class="meta">{esc(DECISIONS)} was not found, so this list is empty.</p>'
    blanks = [d for d in decisions if d["id"] != 0 and not d["answer"]]
    if not blanks:
        return "<p>Nothing is blocked: every decision has an answer.</p>"
    rows = "".join(
        f'<tr><td><b>{esc(d["code"])}</b></td><td>{esc(scrub(d["title"], people))}</td>'
        f'<td>{esc(scrub(UNLOCKS.get(d["id"], ""), people))}</td></tr>'
        for d in blanks
    )
    open_n = len([d for d in decisions if d["id"] != 0])
    return ('<table class="blocked"><thead><tr><th>Decision</th><th>What is waiting</th>'
            f'<th>What answering it unlocks</th></tr></thead><tbody>{rows}</tbody></table>'
            f'<p class="meta">{len(blanks)} of {open_n} still blank. A blank answer means the sessions skip that part.</p>')


def render_next_days(text: str, people) -> str:
    if not text.strip():
        return f'<p class="meta">{esc(NEXT_DAYS)} has not been written yet.</p>'
    out, in_list = [], False
    for line in text.splitlines():
        t = line.strip()
        if not t:
            continue
        if t.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3>{esc(scrub(t[3:], people))}</h3>")
        elif t.startswith("- "):
            if not in_list:
                out.append('<ul class="days">')
                in_list = True
            out.append(f"<li>{esc(scrub(t[2:], people))}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<p>{esc(scrub(t, people))}</p>")
    if in_list:
        out.append("</ul>")
    return "".join(out)


CSS = """
:root { color-scheme: light; --bg:#fbfaf7; --card:#ffffff; --fg:#1b1b1b; --muted:#5f5f5f;
        --line:#e2ded6; --accent:#1f5c4a; --warn:#8a3b2a; --soft:#f1eee7; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
       font:15px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width:64rem; margin:0 auto; padding:1.6rem 1.2rem 4rem; }
header { border-bottom:3px solid var(--accent); padding-bottom:1rem; }
h1 { font-size:1.65rem; margin:.1rem 0 .35rem; letter-spacing:-.01em; }
h2 { font-size:1.12rem; margin:2.2rem 0 .6rem; padding-bottom:.3rem; border-bottom:1px solid var(--line); }
h3 { font-size:.98rem; margin:1.2rem 0 .4rem; }
p { margin:.4rem 0; }
.meta { color:var(--muted); font-size:.88rem; }
.lead { font-size:1rem; max-width:48rem; }
.grid { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:.7rem; margin:1.1rem 0 .4rem; }
.stat { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:.7rem .85rem; }
.stat b { display:block; font-size:1.7rem; line-height:1.2; }
.stat span { color:var(--muted); font-size:.8rem; text-transform:uppercase; letter-spacing:.04em; }
table { width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line);
        border-radius:8px; overflow:hidden; font-size:.89rem; }
th, td { text-align:left; padding:.45rem .6rem; border-bottom:1px solid var(--line); vertical-align:top; }
thead th { background:var(--soft); font-size:.78rem; text-transform:uppercase; letter-spacing:.04em; }
tbody tr:last-child td, tbody tr:last-child th { border-bottom:none; }
.num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
.note { color:var(--muted); }
.funnel th { width:14rem; font-weight:600; }
.funnel td.bar { width:9rem; padding-top:.65rem; }
.funnel td.bar span { display:block; height:.55rem; background:var(--accent); opacity:.35; border-radius:3px; }
.funnel tr.drop td, .funnel tr.drop th { background:#fdf3ef; }
.funnel tr.drop td.bar span { background:var(--warn); opacity:.7; }
.tag { color:var(--warn); font-size:.75rem; text-transform:uppercase; letter-spacing:.04em; }
.v { font-weight:600; font-size:.8rem; text-transform:uppercase; letter-spacing:.03em; }
.v.fit, .v.go { color:var(--accent); }
.v.reject { color:var(--muted); }
ul.days { margin:.3rem 0; padding-left:1.2rem; }
ul.days li { margin:.22rem 0; }
footer { margin-top:3rem; border-top:1px solid var(--line); padding-top:.8rem; color:var(--muted); font-size:.82rem; }
"""


def build() -> str:
    targets = read_targets()
    pipeline = read_pipeline()
    cards, people = read_cards()
    shortlist = read_shortlist()
    decisions = read_decisions()
    sent_rows = read_sent()
    calls = read_calls()

    for org in pipeline:
        for c in org.get("contacts") or []:
            name = (c.get("name") or "").strip()
            if len(name) >= 3:
                people.add(name)

    stages = funnel_numbers(targets, cards, pipeline, shortlist)
    mark = biggest_drop(stages)

    sent = len(sent_rows) if sent_rows else sum(1 for o in pipeline for t in (o.get("touches") or []) if t.get("sent"))
    replied = sum(1 for o in pipeline for t in (o.get("touches") or []) if t.get("status") == "replied")
    call_n = sum(1 for o in pipeline if o.get("outcome") in ("call", "proposal", "signed"))
    signed = sum(1 for o in pipeline if o.get("outcome") == "signed")
    planned_calls = sum(1 for c in calls if c.get("status") == "planned")
    days_left = max(0, (SEND_END - dt.date.today()).days)
    stamp = dt.datetime.now().isoformat(timespec="minutes")
    inputs = ", ".join([
        "tenants/" + tenant.NAME + "/pipeline.yaml",
        "tenants/" + tenant.NAME + "/targets.yaml",
        "tenants/" + tenant.NAME + "/cards/",
        "tenants/" + tenant.NAME + "/state/sent.log",
        "tenants/" + tenant.NAME + "/state/calls.yaml",
        SHORTLIST,
        DECISIONS,
        NEXT_DAYS,
    ])

    batch_section = render_batch(cards, pipeline, people)
    shortlist_section = render_shortlist(shortlist)
    blocked_section = render_blocked(decisions, people)
    next_section = render_next_days(read_next_days(), people)
    card_note = f"{len(cards)} researched, {sum(1 for c in cards if c['verdict'] == 'FIT')} fit"
    label = tenant.config().get("name") or tenant.NAME
    call_note = f"{planned_calls} planned in calls.yaml" if planned_calls else "none planned yet"

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Outreach status · {esc(label)}</title>
<style>{CSS}
</style></head>
<body><main>
<header>
<h1>Outreach status: {esc(label)}</h1>
<p class="lead">Goal: {esc(GOAL_SIGNED)}, and about {EMAIL_GOAL:,} emails by 22 December.
{days_left} days left to 22 December. {esc(card_note)}.</p>
</header>

<section>
<h2>Headline</h2>
<div class="grid">
<div class="stat"><b>{sent:,}</b><span>emails sent</span></div>
<div class="stat"><b>{replied:,}</b><span>replies</span></div>
<div class="stat"><b>{call_n:,}</b><span>calls or better</span></div>
<div class="stat"><b>{signed:,}</b><span>signed</span></div>
</div>
<p class="meta">Calls: {esc(call_note)}. Replies at 10 sends are noise: the first real read is around 40 to 50 sends.</p>
</section>

<section>
<h2>The funnel, and where it loses the most</h2>
{render_funnel(stages, mark)}
<p class="meta">Every stage counts real rows in the files above. The marked row is the largest fall between two measured stages.</p>
</section>

<section>
<h2>Batch 1: the researched organisations</h2>
{batch_section}
</section>

<section>
<h2>Shortlist: the next organisations to research</h2>
{shortlist_section}
</section>

<section>
<h2>Blocked on a decision</h2>
{blocked_section}
</section>

<section>
<h2>Next 10 days</h2>
{next_section}
</section>

<footer>
Generated {esc(stamp)} by tools/report.py. Read-only: no server, no external files, no contact data.
<br>Inputs: {esc(inputs)}.
</footer>
</main></body></html>
"""
    return page


def write_report(path: str | None = None) -> Path:
    target = Path(path) if path else ROOT / "out" / "report.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build(), encoding="utf-8", newline="")
    return target


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=None, help="write here instead of out/report.html")
    a = ap.parse_args()
    path = write_report(a.out)
    print(f"report: {path}  ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
