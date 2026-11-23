"""Add organisations, contacts and touches to the tenant pipeline without hand-editing YAML. Zero LLM tokens.

Every command takes the writer lock for the moment of the write. Arms are assigned here, by
alternating over first emails in draft order, so nobody picks an arm per organisation.

Usage:
    python tools/pipeline.py add-org --id stichting-x --name "Stichting X" --domain stichtingx.nl \
        --city Rotterdam --country NL --segment nonprofit --tier 1 --card cards/stichting-x.md
    python tools/pipeline.py add-contact --org stichting-x --id stichting-x-jan --name "Jan de Vries" \
        --title Directeur --email jan@stichtingx.nl --source https://stichtingx.nl/over-ons/team
    python tools/pipeline.py add-touch --org stichting-x --contact stichting-x-jan --kind first         --workflows "matching volunteers to shifts" "the monthly funder report"
        -> prints the touch id, its arm and the draft file to write (drafts/<touch>.txt)
    python tools/pipeline.py set --org stichting-x --status closed|paused|active [--outcome call|proposal|signed|no]
    python tools/pipeline.py show --org stichting-x
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

import registry
import tenant
from writer_lock import locked


def _org(pipeline, org_id):
    org = next((o for o in pipeline.get("orgs", []) if o["id"] == org_id), None)
    if org is None:
        sys.exit(f"org {org_id} not in the pipeline")
    return org


def next_arm(pipeline) -> str:
    firsts = [t for o in pipeline.get("orgs", []) for t in o.get("touches", []) if t.get("kind") == "first"]
    return "A" if len(firsts) % 2 == 0 else "B"


def add_org(a):
    domain = tenant.domain_of(a.domain)
    try:
        why = registry.blocked_reason(domain)
    except registry.RegistryError as exc:
        sys.exit(f"registry unreachable, not adding: {exc}")
    if why:
        sys.exit(f"not adding: {why}")
    supp = tenant.load(tenant.SUPPRESSION, {}) or {}
    if domain in (supp.get("domains") or {}):
        sys.exit(f"not adding: {domain} is on the suppression list")
    lang = "de" if a.country.upper() in (tenant.config().get("languages", {}).get("de_countries") or []) else "en"
    with locked("claude"):
        p = tenant.load(tenant.PIPELINE, {"orgs": []})
        p.setdefault("orgs", [])
        if any(o["id"] == a.id or o.get("domain") == domain for o in p["orgs"]):
            sys.exit(f"{a.id} / {domain} already in the pipeline")
        p["orgs"].append({
            "id": a.id, "name": a.name, "domain": domain, "city": a.city, "country": a.country.upper(),
            "segment": a.segment, "lang": lang, "tier": a.tier, "status": "active", "card": a.card,
            "added": dt.date.today().isoformat(), "contacts": [], "touches": [],
        })
        tenant.save(tenant.PIPELINE, p)
    try:
        registry.claim(domain, a.name, "researching")
    except registry.RegistryError as exc:
        print(f"warn  registry claim failed: {exc}")
    print(f"added {a.id} ({domain}, {lang}, tier {a.tier})")


def add_contact(a):
    if not a.source.startswith("http"):
        sys.exit("--source must be the URL where the address is published")
    if tenant.domain_of(a.email) != tenant.domain_of(a.source) and not a.allow_other_domain:
        sys.exit("address and source page are on different domains; check it, then pass --allow-other-domain")
    supp = tenant.load(tenant.SUPPRESSION, {}) or {}
    if a.email.lower() in (supp.get("addresses") or {}):
        sys.exit(f"{a.email} is on the suppression list")
    with locked("claude"):
        p = tenant.load(tenant.PIPELINE, {})
        org = _org(p, a.org)
        if any(c["id"] == a.id for c in org["contacts"]):
            sys.exit(f"contact {a.id} exists")
        org["contacts"].append({"id": a.id, "name": a.name, "title": a.title})
        tenant.save(tenant.PIPELINE, p)
        contacts = tenant.load(tenant.CONTACTS, {}) or {}
        contacts[a.id] = {"email": a.email.strip(), "source": a.source, "name": a.name}
        tenant.save(tenant.CONTACTS, contacts)
    print(f"contact {a.id} added to {a.org}")


def add_touch(a):
    with locked("claude"):
        p = tenant.load(tenant.PIPELINE, {})
        org = _org(p, a.org)
        if a.contact not in {c["id"] for c in org["contacts"]}:
            sys.exit(f"contact {a.contact} is not at {a.org}")
        n = sum(1 for t in org["touches"] if t.get("contact") == a.contact)
        suffix = {"first": "1", "chain": "1", "follow_up": "fu"}[a.kind]
        tid = f"{a.contact}-{suffix}" if n == 0 or a.kind == "follow_up" else f"{a.contact}-{n + 1}"
        if any(t["id"] == tid for t in org["touches"]):
            sys.exit(f"touch {tid} exists")
        if a.kind == "first":
            arm = next_arm(p)
        else:
            prev = next((t for t in org["touches"] if t.get("kind") in ("first", "chain")), None)
            arm = (prev or {}).get("arm", next_arm(p))
        touch = {"id": tid, "contact": a.contact, "kind": a.kind, "arm": arm, "status": "planned",
                 "body": f"drafts/{tid}.txt"}
        workflows = [w.strip() for w in (getattr(a, "workflows", None) or []) if w.strip()]
        if a.kind in ("first", "chain"):
            if len(workflows) != 2:
                sys.exit("--workflows needs the two workflows the email names, in their words "
                         "(tools/followups.py writes the follow-up question from them)")
            touch["workflows"] = workflows
        if a.kind == "chain":
            touch["after"] = next((t["id"] for t in org["touches"] if t.get("kind") == "first"), None)
        org["touches"].append(touch)
        tenant.save(tenant.PIPELINE, p)
    (tenant.DIR / "drafts").mkdir(exist_ok=True)
    tpl = {"first": f"first-{arm}", "chain": "chain", "follow_up": "follow"}[a.kind]
    print(f"touch {tid}  arm {arm}  lang {org['lang']}  write: tenants/{tenant.NAME}/drafts/{tid}.txt  "
          f"template: templates/{tpl}.{org['lang']}.md")


def set_org(a):
    with locked("claude"):
        p = tenant.load(tenant.PIPELINE, {})
        org = _org(p, a.org)
        if a.status:
            org["status"] = a.status
        if a.outcome:
            org["outcome"] = a.outcome
        tenant.save(tenant.PIPELINE, p)
    if a.outcome in ("call", "proposal", "signed"):
        status = {"call": "call_booked", "proposal": "in_talks", "signed": "client"}[a.outcome]
        try:
            registry.claim(org["domain"], org["name"], status)
        except registry.RegistryError as exc:
            print(f"warn  registry not updated: {exc}")
    print(f"{a.org}: status {org.get('status')}, outcome {org.get('outcome', '-')}")


def show(a):
    import yaml
    p = tenant.load(tenant.PIPELINE, {})
    print(yaml.safe_dump(_org(p, a.org), sort_keys=False, allow_unicode=True))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("add-org")
    for f in ("id", "name", "domain", "city", "country", "card"):
        o.add_argument(f"--{f}", required=f != "card")
    o.add_argument("--segment", required=True, choices=["nonprofit", "social_enterprise", "woningcorporatie"])
    o.add_argument("--tier", type=int, required=True, choices=[1, 2])
    c = sub.add_parser("add-contact")
    for f in ("org", "id", "name", "title", "email", "source"):
        c.add_argument(f"--{f}", required=True)
    c.add_argument("--allow-other-domain", action="store_true")
    t = sub.add_parser("add-touch")
    t.add_argument("--org", required=True)
    t.add_argument("--contact", required=True)
    t.add_argument("--kind", required=True, choices=["first", "follow_up", "chain"])
    t.add_argument("--workflows", nargs="+", help="first/chain: the two workflows the email names, in their words")
    s = sub.add_parser("set")
    s.add_argument("--org", required=True)
    s.add_argument("--status", choices=["active", "paused", "closed"])
    s.add_argument("--outcome", choices=["call", "proposal", "signed", "no"])
    sh = sub.add_parser("show")
    sh.add_argument("--org", required=True)
    a = ap.parse_args()
    {"add-org": add_org, "add-contact": add_contact, "add-touch": add_touch, "set": set_org, "show": show}[a.cmd](a)


if __name__ == "__main__":
    main()
