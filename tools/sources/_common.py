"""Shared helpers for the candidate-list scripts in tools/sources/. Zero LLM tokens.

Each source script fetches a public list with plain HTTP, turns it into rows and calls add_rows().
add_rows() de-duplicates on the website domain against targets.yaml, the pipeline and the suppression
list, sorts Delft and Rotterdam first, and writes targets.yaml. Downloads are cached in
tenants/<t>/state/sources/ (gitignored) so a re-run does not hit the source again.

Row: {name, website, city, country, segment, source, size_hint, status: new}
"""

from __future__ import annotations

import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tenant  # noqa: E402

TARGETS = tenant.DIR / "targets.yaml"
CACHE = tenant.STATE / "sources"
UA = "Mozilla/5.0 (compatible; 180dc-candidate-list/1.0; plain HTTP, one request at a time)"

HOME = {"delft", "rotterdam"}
# Rijnmond plus Delft's neighbours: second in the sort order, and the Aedes region filter.
REGION = {
    "schiedam", "vlaardingen", "maassluis", "capelle aan den ijssel", "krimpen aan den ijssel",
    "barendrecht", "ridderkerk", "albrandswaard", "rhoon", "poortugaal", "lansingerland",
    "bergschenhoek", "berkel en rodenrijs", "bleiswijk", "nissewaard", "spijkenisse", "hellevoetsluis",
    "brielle", "voorne aan zee", "westvoorne", "zuidplas", "nieuwerkerk aan den ijssel", "hoogvliet",
    "rozenburg", "pernis", "rijswijk", "pijnacker-nootdorp", "pijnacker", "nootdorp", "midden-delfland",
    "schipluiden", "den hoorn", "westland", "naaldwijk", "zoetermeer", "den haag", "'s-gravenhage",
    "dordrecht", "zwijndrecht", "papendrecht", "gouda",
}

# Hosts that are not the organisation's own site: social media, link pages, shared ANBI platforms.
NOT_OWN_SITE = {
    "facebook.com", "m.facebook.com", "instagram.com", "linkedin.com", "nl.linkedin.com", "twitter.com",
    "x.com", "youtube.com", "google.com", "sites.google.com", "drive.google.com", "docs.google.com",
    "linktr.ee", "issuu.com", "dropbox.com", "kvk.nl", "belastingdienst.nl", "anbi.nl", "geefgratis.nl",
    "anbi.rkcn.nl", "rkcn.nl", "ngk.nl", "protestantsekerk.nl", "pkn.nl", "kerkbalans.nl",
    "cgk.nl", "gkv.nl", "hersteld-hervormd.nl", "nl.wikipedia.org", "wikipedia.org",
}


def domain(url: str) -> str:
    return tenant.domain_of(url or "").split(":", 1)[0].strip(".")


def own_site(url: str) -> bool:
    d = domain(url)
    if not d or "." not in d:
        return False
    return not any(d == h or d.endswith("." + h) for h in NOT_OWN_SITE)


def norm_city(city: str) -> str:
    return re.sub(r"\s+", " ", (city or "").strip())


def region_rank(city: str) -> int:
    c = (city or "").strip().lower()
    if c in HOME:
        return 0
    if c in REGION:
        return 1
    return 2


def fetch(url: str, cache_name: str | None = None, delay: float = 0.0, timeout: int = 60) -> bytes:
    """GET with a cache file. delay is slept before a real request (polite paging)."""
    if cache_name:
        path = CACHE / cache_name
        if path.exists() and path.stat().st_size > 0:
            return path.read_bytes()
    if delay:
        time.sleep(delay)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "nl,en"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    if cache_name:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return data


def known_domains() -> dict[str, str]:
    """domain -> where it already is (targets, pipeline, suppression)."""
    seen: dict[str, str] = {}
    for c in (tenant.load(TARGETS, {}) or {}).get("candidates") or []:
        seen[domain(c.get("website", ""))] = f"targets ({c.get('source')})"
    for o in (tenant.load(tenant.PIPELINE, {}) or {}).get("orgs") or []:
        seen[o.get("domain", "")] = "pipeline"
    supp = tenant.load(tenant.SUPPRESSION, {}) or {}
    for d in (supp.get("domains") or {}):
        seen[domain(d)] = "suppression"
    for a in (supp.get("addresses") or {}):
        seen.setdefault(domain(a), "suppression (address)")
    seen.pop("", None)
    return seen


def size_rank(hint: str) -> int:
    """0: a subsidy that fits a 20-100 staff organisation; 1: unknown or tiny; 2: likely too big."""
    m = re.search(r"EUR ([\d,]+)", hint or "")
    if not m:
        return 1
    eur = int(m.group(1).replace(",", ""))
    if eur > 1_000_000:
        return 2
    return 0 if eur >= 50_000 else 1


def sort_key(c: dict):
    # a municipal subsidy says nothing about a housing corporation's size, so only other segments use it
    size = size_rank(c.get("size_hint")) if c.get("segment") != "woningcorporatie" else 1
    return (0 if c.get("status") == "new" else 1, region_rank(c.get("city", "")), size)


def save_candidates(cands: list[dict]) -> None:
    cands.sort(key=sort_key)  # stable: within a group the order of adding is kept
    head = TARGETS.read_text(encoding="utf-8").split("candidates:", 1)[0] if TARGETS.exists() else ""
    tenant.save(TARGETS, {"candidates": cands})
    if head.strip():  # keep the explanatory comment block at the top of the file
        TARGETS.write_text(head + TARGETS.read_text(encoding="utf-8"), encoding="utf-8")


def add_rows(rows: list[dict], source: str, dry_run: bool = False) -> dict:
    """Append new rows; returns counts for the source script's report line."""
    data = tenant.load(TARGETS, {}) or {}
    cands = data.get("candidates") or []
    seen = known_domains()
    stats = {"offered": len(rows), "added": 0, "home": 0, "dup": 0, "no_site": 0}
    for r in rows:
        if not own_site(r.get("website", "")):
            stats["no_site"] += 1
            continue
        d = domain(r["website"])
        if d in seen:
            stats["dup"] += 1
            continue
        seen[d] = f"targets ({source})"
        cands.append({
            "name": r["name"].strip(), "website": r["website"].strip(), "city": norm_city(r.get("city", "")),
            "country": r.get("country", "NL"), "segment": r["segment"], "source": source,
            "size_hint": r.get("size_hint") or "unknown", "status": "new",
        })
        stats["added"] += 1
        stats["home"] += region_rank(r.get("city", "")) == 0
    if not dry_run:
        save_candidates(cands)
    return stats


def report(source: str, stats: dict, dry_run: bool) -> None:
    tag = " (dry run, nothing written)" if dry_run else ""
    print(f"{source}: {stats['offered']} offered, {stats['added']} added ({stats['home']} in Delft/Rotterdam), "
          f"{stats['dup']} duplicate domain, {stats['no_site']} no own website{tag}")
