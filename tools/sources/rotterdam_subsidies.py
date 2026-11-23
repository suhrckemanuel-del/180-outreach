"""Mark targets that Gemeente Rotterdam subsidised in 2024. Zero LLM tokens. Adds no rows.

Source: the subsidy list in Rotterdam's published annual accounts,
https://www.watdoetdegemeente.rotterdam.nl/jaarstukken-2024/jaarverslag-paragrafen/subsidies/
(about 1,400 rows: recipient and amount paid in 2024, grouped by programme). It has no websites, so it
cannot add candidates; it is matched on the organisation's name to rows already in targets.yaml and
writes the amount into size_hint. That gives the two things the ANBI file lacks: a size signal and a
known funding source (decision 5 in docs/build-spec.md). Rows it marks sort first within their city.

Delft publishes no comparable list (checked 2026-11-21, see docs/sources.md).

    python tools/sources/rotterdam_subsidies.py [--dry-run]
"""

from __future__ import annotations

import argparse
import html
import re
from collections import defaultdict

import _common as c

URL = "https://www.watdoetdegemeente.rotterdam.nl/jaarstukken-2024/jaarverslag-paragrafen/subsidies/"
DROP = re.compile(r"\b(stichting|st\.|vereniging|foundation|the|de|het)\b", re.I)


def key(name: str) -> str:
    s = html.unescape(name or "").lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = DROP.sub(" ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def amounts() -> dict[str, int]:
    page = c.fetch(URL, "rotterdam-subsidies-2024.html").decode("utf-8", "replace")
    total: dict[str, int] = defaultdict(int)
    for tr in re.findall(r'<tr[^>]*normal-table-row[^>]*>(.*?)</tr>', page, flags=re.S):
        cells = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
        if len(cells) < 2 or not cells[0]:
            continue
        try:
            total[key(cells[0])] += int(cells[1].replace(".", "").replace("−", "-"))
        except ValueError:
            continue
    total.pop("", None)
    return total


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    paid = amounts()
    data = c.tenant.load(c.TARGETS, {}) or {}
    cands = data.get("candidates") or []
    marked = 0
    for cand in cands:  # undo an earlier run first, so a re-run never stacks or keeps a stale match
        cand["size_hint"] = re.sub(r"^Rotterdam subsidy 2024: EUR [\d,]+", "unknown", cand.get("size_hint") or "unknown")
    for cand in cands:
        if (cand.get("city") or "").strip().lower() != "rotterdam":  # name matches elsewhere are too often a namesake
            continue
        eur = paid.get(key(cand.get("name", "")))
        hint = cand.get("size_hint") or "unknown"
        if not eur or eur <= 0 or not hint.startswith("unknown"):
            continue
        rest = hint[len("unknown"):]
        cand["size_hint"] = f"Rotterdam subsidy 2024: EUR {eur:,}{rest}"
        marked += 1
    if not a.dry_run:
        c.save_candidates(cands)
    print(f"rotterdam_subsidies: {len(paid)} recipients in the list, {marked} targets marked"
          + (" (dry run)" if a.dry_run else ""))


if __name__ == "__main__":
    main()
