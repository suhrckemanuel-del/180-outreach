"""Aedes members (woningcorporaties), Rotterdam region only, into targets.yaml. Zero LLM tokens.

Source: the member map on https://aedes.nl/vereniging/de-woningcorporaties-die-lid-zijn-van-aedes
reads its pins from https://aedes.nl/kaarten?map=372 (GeoJSON: name, address, website). robots.txt
allows it (crawl-delay 5; this is one request). No size figure in the source.

    python tools/sources/aedes.py [--all-nl] [--dry-run] [--refresh]
"""

from __future__ import annotations

import argparse
import json
import re

import _common as c

URL = "https://aedes.nl/kaarten?map=372"


def rows(all_nl: bool, refresh: bool) -> list[dict]:
    cache = None if refresh else "aedes-map-372.json"
    feats = json.loads(c.fetch(URL, cache).decode("utf-8")).get("features", [])
    out = []
    for f in feats:
        p = f.get("properties", {})
        lines = [re.sub(r"<[^>]+>", "", x).strip() for x in re.split(r"<br\s*/?>", p.get("description", ""))]
        city = ""
        for ln in lines:
            m = re.match(r"^\d{4}\s?[A-Z]{2}\s+(.+)$", ln)
            if m:
                city = m.group(1).strip()
                break
        if not all_nl and c.region_rank(city) > 1:
            continue
        out.append({"name": p.get("name", ""), "website": p.get("field_link") or "", "city": city,
                    "country": "NL", "segment": "woningcorporatie", "size_hint": "unknown"})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--all-nl", action="store_true", help="every member, not only the Rotterdam region")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="ignore the cached download")
    a = ap.parse_args()
    c.report("aedes", c.add_rows(rows(a.all_nl, a.refresh), "aedes", a.dry_run), a.dry_run)


if __name__ == "__main__":
    main()
