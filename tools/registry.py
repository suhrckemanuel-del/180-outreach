"""The branch's shared contact registry: is anyone already talking to this organisation? Zero LLM tokens.

Keyed on the organisation's website domain, never its name. Backend from tenant.yaml registry.backend:
  local   state/registry.local.yaml (works today, only this kit sees it)
  monday  a monday.com board every branch member can see and log contacts on (docs/setup.md)

A domain is BLOCKED for us when another owner has it and either its status is in hold_statuses
(client, in_talks, call_booked) or its blocked_until date has not passed. With the monday backend
an unreachable API counts as blocked: the sender fails closed.

Usage:
    python tools/registry.py check stichting-x.nl
    python tools/registry.py claim stichting-x.nl --org "Stichting X" --status researching
    python tools/registry.py test-monday          # one read against the board, prints what it found
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.request

import tenant

API = "https://api.monday.com/v2"


class RegistryError(RuntimeError):
    pass


def _cfg():
    return (tenant.config() or {}).get("registry", {}) or {}


# ---------- local backend ----------

def _local_all() -> dict:
    return tenant.load(tenant.REGISTRY_LOCAL, {}) or {}


def _local_get(domain):
    return _local_all().get(domain)


def _local_put(domain, row):
    data = _local_all()
    data[domain] = row
    tenant.save(tenant.REGISTRY_LOCAL, data)


# ---------- monday backend ----------

def _token():
    m = _cfg().get("monday", {})
    tok = os.environ.get(m.get("token_env", "MONDAY_API_TOKEN"))
    path = tenant.PRIVATE / "monday_token.txt"
    if not tok and path.exists():
        tok = path.read_text(encoding="utf-8").strip()
    if not tok:
        raise RegistryError("no monday token (env MONDAY_API_TOKEN or private/monday_token.txt)")
    return tok


def _gql(query, variables):
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": _token(), "Content-Type": "application/json", "API-Version": "2024-10"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            out = json.loads(r.read().decode())
    except Exception as exc:
        raise RegistryError(f"monday unreachable: {exc}") from exc
    if out.get("errors"):
        raise RegistryError(f"monday error: {out['errors']}")
    return out["data"]


def _cols():
    m = _cfg().get("monday", {})
    cols = m.get("columns", {})
    if str(m.get("board_id", "TODO")) == "TODO" or any(str(c.get("id")) == "TODO" for c in cols.values()):
        raise RegistryError("monday board_id or column IDs still TODO in tenant.yaml")
    return str(m["board_id"]), cols


def _monday_get(domain):
    board, cols = _cols()
    q = """query ($board: ID!, $col: String!, $val: String!) {
      items_page_by_column_values(board_id: $board, limit: 5,
        columns: [{column_id: $col, column_values: [$val]}]) {
        items { id name column_values { id text } } } }"""
    items = _gql(q, {"board": board, "col": cols["domain"]["id"], "val": domain})[
        "items_page_by_column_values"]["items"]
    if not items:
        return None
    item = items[0]
    by_id = {c["id"]: c.get("text") or "" for c in item["column_values"]}
    row = {key: by_id.get(spec["id"], "") for key, spec in cols.items()}
    row.update({"org": item["name"], "_item_id": item["id"]})
    return row


def _monday_value(spec, value):
    return {"date": value} if spec.get("type") == "date" else value


def _monday_put(domain, row):
    board, cols = _cols()
    vals = {spec["id"]: _monday_value(spec, str(row.get(key, ""))) for key, spec in cols.items() if row.get(key)}
    existing = _monday_get(domain)
    if existing:
        q = """mutation ($board: ID!, $item: ID!, $vals: JSON!) {
          change_multiple_column_values(board_id: $board, item_id: $item, column_values: $vals) { id } }"""
        _gql(q, {"board": board, "item": existing["_item_id"], "vals": json.dumps(vals)})
    else:
        q = """mutation ($board: ID!, $name: String!, $vals: JSON!) {
          create_item(board_id: $board, item_name: $name, column_values: $vals) { id } }"""
        _gql(q, {"board": board, "name": row.get("org") or domain, "vals": json.dumps(vals)})


# ---------- public ----------

def lookup(domain: str):
    domain = tenant.domain_of(domain)
    return _monday_get(domain) if _cfg().get("backend") == "monday" else _local_get(domain)


def blocked_reason(domain: str, today: dt.date | None = None) -> str | None:
    """Why we may not contact this domain, or None. Raises RegistryError if the registry can't be read."""
    today = today or dt.date.today()
    row = lookup(domain)
    if not row:
        return None
    ours = (tenant.config() or {}).get("owner_tag")
    owner = str(row.get("owner") or "")
    if owner == ours:
        return None
    status = str(row.get("status") or "").lower()
    if status in [s.lower() for s in _cfg().get("hold_statuses", [])]:
        return f"registry: {owner or 'someone'} has {domain} as {status}"
    until = str(row.get("blocked_until") or "")[:10]
    if until and until >= today.isoformat():
        return f"registry: {owner or 'someone'} contacted {domain}, blocked until {until}"
    return None


def claim(domain: str, org: str, status: str, today: dt.date | None = None) -> None:
    today = today or dt.date.today()
    days = int(_cfg().get("block_days", 90))
    row = {
        "org": org,
        "domain": tenant.domain_of(domain),
        "owner": (tenant.config() or {}).get("owner_tag"),
        "status": status,
        "last_contact": today.isoformat(),
        "blocked_until": (today + dt.timedelta(days=days)).isoformat(),
    }
    if _cfg().get("backend") == "monday":
        _monday_put(row["domain"], row)
    else:
        _local_put(row["domain"], row)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("domain")
    cl = sub.add_parser("claim")
    cl.add_argument("domain")
    cl.add_argument("--org", required=True)
    cl.add_argument("--status", default="researching")
    sub.add_parser("test-monday")
    args = ap.parse_args()
    try:
        if args.cmd == "check":
            why = blocked_reason(args.domain)
            print(why or f"free: {tenant.domain_of(args.domain)}")
            sys.exit(2 if why else 0)
        elif args.cmd == "claim":
            claim(args.domain, args.org, args.status)
            print(f"claimed {tenant.domain_of(args.domain)} as {args.status}")
        else:
            board = str(_cfg().get("monday", {}).get("board_id", "TODO"))
            if board == "TODO":
                raise RegistryError("set registry.monday.board_id in tenant.yaml first")
            data = _gql("query ($b: [ID!]) { boards(ids: $b) { name columns { id title type } } }", {"b": [board]})
            print(json.dumps(data, indent=2))
    except RegistryError as exc:
        print(f"REGISTRY ERROR: {exc}")
        sys.exit(3)


if __name__ == "__main__":
    main()
