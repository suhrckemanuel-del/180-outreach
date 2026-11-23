"""ANBI register (Belastingdienst open data, CC0) into targets.yaml. Zero LLM tokens.

Source: https://download.belastingdienst.nl/data/anbi/anbi.zip, linked from
https://belastingdienst.nl/wps/wcm/connect/bldcontentnl/themaoverstijgend/brochures_en_publicaties/open_data_anbi
One zip with anbi.xml (refreshed every Tuesday). Per ANBI: naam, vestigingsPlaats, webSite, dates.
No income, no staff count.

Filters, in code (the researcher still decides fit):
- ANBI status ended (eindDatum / intrekkingsDatum) -> out
- churches, parishes, mosques and other religious congregations -> out (no staff, no funder reporting)
- schools, universities, the municipality itself -> out
- "Vrienden van" / support foundations of another institution -> out (no own operation)
- website on a shared platform or social media -> out (not their own domain)
- cities: Delft and Rotterdam by default; --region adds Rijnmond and the Haaglanden neighbours

    python tools/sources/anbi.py [--region] [--dry-run] [--refresh]
"""

from __future__ import annotations

import argparse
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter

import _common as c

URL = "https://download.belastingdienst.nl/data/anbi/anbi.zip"

OUT_NAME = re.compile(
    r"\b(kerk\w*|parochie|diaconie|diaconaal|kerkrentmeester\w*|gemeente te|gemeente van|protestants\w*|"
    r"gereformeerd\w*|hervormd\w*|baptist\w*|evangeli\w*|luthers\w*|remonstrant\w*|doopsgezind\w*|"
    r"katholiek\w*|r\.?\s?k\.?|pinkster\w*|apostolisch\w*|christengemeente|christelijke gemeente|"
    r"moskee|islamitisch\w*|masjid|synagoge|joodse gemeente|hindoe\w*|mandir|tempel|gurdwara|boeddhist\w*|"
    r"zending\w*|missie|mission|ministries|ministry|congregatie|klooster|abdij|reformator\w*|jesus|jezus|"
    r"voorgangers|bijbel\w*|"
    r"school\w*|scholen\w*|basisschool|universiteit|university|hogeschool|lyceum|gymnasium|"
    r"vrienden van|vriendenkring|vriendenstichting|steunstichting|steunfonds)\b",
    re.I,
)
OUT_EXACT = {"gemeente rotterdam", "gemeente delft"}
PLATFORM_MIN = 5  # a host used by this many ANBIs nationally is a platform or umbrella, not one org's site


def load(refresh: bool) -> list[ET.Element]:
    raw = c.fetch(URL, None if refresh else "anbi.zip", timeout=180)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        xml = z.read("anbi.xml")
    return ET.fromstring(xml).findall(".//beschikking")


def rows(region: bool, refresh: bool) -> tuple[list[dict], Counter]:
    items = load(refresh)
    hosts = Counter(c.domain(b.findtext("webSite") or "") for b in items)
    why = Counter()
    out = []
    for b in items:
        name = (b.findtext("naam") or "").strip()
        city = (b.findtext("vestigingsPlaats") or "").strip()
        site = (b.findtext("webSite") or "").strip()
        rank = c.region_rank(city)
        if rank > (1 if region else 0):
            continue
        if b.find("eindDatum") is not None or b.find("intrekkingsDatum") is not None:
            why["ended"] += 1
            continue
        alias = (b.findtext("aliasNaam") or "").strip()
        if name.lower() in OUT_EXACT or OUT_NAME.search(name) or OUT_NAME.search(alias):
            why["religious, school or support foundation"] += 1
            continue
        if not site or not c.own_site(site):
            why["no own website"] += 1
            continue
        if hosts[c.domain(site)] >= PLATFORM_MIN:
            why["shared platform domain"] += 1
            continue
        cultural = b.find("ingangsDatumCultuur") is not None and b.find("eindDatumCultuur") is None
        out.append({"name": alias.title() if alias and len(name) > 60 else name, "website": site, "city": city,
                    "country": "NL", "segment": "nonprofit",
                    "size_hint": "unknown" + ("; culturele ANBI" if cultural else "")})
    return out, why


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--region", action="store_true", help="also Rijnmond and Haaglanden, not only Delft and Rotterdam")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="download the weekly file again")
    a = ap.parse_args()
    rs, why = rows(a.region, a.refresh)
    print("filtered out: " + ", ".join(f"{k} {v}" for k, v in why.most_common()))
    c.report("anbi", c.add_rows(rs, "anbi", a.dry_run), a.dry_run)


if __name__ == "__main__":
    main()
