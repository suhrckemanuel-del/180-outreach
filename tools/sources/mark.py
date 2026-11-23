"""Set the status of candidates in targets.yaml, matched on the website domain. Zero LLM tokens.

    python tools/sources/mark.py <domain> --status researched|rejected|new [--why "reason"]
    python tools/sources/mark.py --pick nonprofit=13 social_enterprise=12 woningcorporatie=3 [--cities Delft Rotterdam]

--pick prints the next 'new' candidates per segment in file order (Delft and Rotterdam first, then a
Rotterdam subsidy of EUR 50k-1M, then unknown size, then larger), nonprofits alternating cultural and
social, which is the batch rule in docs/tickets/08-batch-loop.md. It changes nothing.
"""

from __future__ import annotations

import argparse
import sys

import _common as c


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("domain", nargs="?")
    ap.add_argument("--status", choices=["new", "researched", "rejected"])
    ap.add_argument("--why", default="")
    ap.add_argument("--pick", nargs="+", metavar="SEGMENT=N")
    ap.add_argument("--cities", nargs="+", default=["Delft", "Rotterdam"])
    a = ap.parse_args()
    cands = (c.tenant.load(c.TARGETS, {}) or {}).get("candidates") or []

    if a.pick:
        cities = {x.lower() for x in a.cities}
        for spec in a.pick:
            seg, n = spec.split("=")
            rows = [x for x in cands if x.get("status") == "new" and x.get("segment") == seg
                    and x.get("city", "").lower() in cities]
            if seg == "nonprofit":  # alternate cultural and social nonprofits so one kind does not fill the batch
                cult = [x for x in rows if "culturele ANBI" in (x.get("size_hint") or "")]
                soc = [x for x in rows if x not in cult]
                rows = [x for pair in zip(soc, cult) for x in pair] + soc[len(cult):] + cult[len(soc):]
            rows = rows[: int(n)]
            for x in rows:
                print(f"{seg}\t{c.domain(x['website'])}\t{x['city']}\t{x['name']}\t{x.get('size_hint')}")
        return

    if not a.domain or not a.status:
        sys.exit("give a domain and --status, or --pick")
    d = c.domain(a.domain)
    hit = [x for x in cands if c.domain(x.get("website", "")) == d]
    if not hit:
        sys.exit(f"{d} is not in targets.yaml")
    for x in hit:
        x["status"] = a.status
        if a.why:
            x["why"] = a.why
        elif "why" in x and a.status == "new":
            del x["why"]
    c.save_candidates(cands)
    print(f"{d}: {a.status}" + (f" ({a.why})" if a.why else ""))


if __name__ == "__main__":
    main()
