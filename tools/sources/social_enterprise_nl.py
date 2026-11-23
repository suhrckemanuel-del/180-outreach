"""Social Enterprise NL members into targets.yaml. Zero LLM tokens.

Source: the public WordPress API https://social-enterprise.nl/wp-json/wp/v2/lid lists every member
(name, member page); each member page https://social-enterprise.nl/lid/<slug>/ shows the website
("Kijk op de website") and "Vestigingsplaats". robots.txt allows /lid/ and /wp-json/ (only /wp-admin/
and /?s= are closed); the terms reserve copyright on their texts and images, which we do not copy:
we keep name, website and city only. No size figure in the source.

One member page per 1.5 s; pages are cached, so a re-run only fetches new members.

    python tools/sources/social_enterprise_nl.py [--dry-run] [--limit N]
"""

from __future__ import annotations

import argparse
import html
import json
import re

import _common as c

API = "https://social-enterprise.nl/wp-json/wp/v2/lid?per_page=100&page={page}&_fields=slug,link,title"
SOCIAL = re.compile(r"(facebook|instagram|linkedin|twitter|x\.com|youtube|tiktok|social-enterprise\.nl|"
                    r"wa\.me|whatsapp|mailto:|tel:|google\.)", re.I)


def members() -> list[dict]:
    out, page = [], 1
    while True:
        try:
            batch = json.loads(c.fetch(API.format(page=page), delay=1.0).decode("utf-8"))
        except Exception as exc:  # WordPress answers 400 past the last page
            if "400" in str(exc):
                break
            raise
        if not batch:
            break
        out += batch
        page += 1
    return out


def parse(page: str) -> tuple[str, str]:
    site = ""
    m = re.search(r'href="(https?://[^"]+)"[^>]*>\s*<span[^>]*>\s*Kijk op de website', page)
    if m:
        site = m.group(1)
    else:  # fallback: first outside link in the member block that is not social media
        body = page.split("Vestigingsplaats", 1)[0][-20000:]
        for link in re.findall(r'href="(https?://[^"]+)"', body):
            if not SOCIAL.search(link) and "wp-content" not in link:
                site = link
                break
    city = ""
    m = re.search(r"Vestigingsplaats</h3>.*?inner-wrap\">([^<]*)</span>", page, flags=re.S)
    if m:
        city = html.unescape(m.group(1)).strip()
    return site, city


def rows(limit: int | None) -> list[dict]:
    out = []
    for i, mbr in enumerate(members()):
        if limit and i >= limit:
            break
        slug = mbr["slug"]
        page = c.fetch(mbr["link"], f"senl/{slug}.html", delay=1.5).decode("utf-8", "replace")
        site, city = parse(page)
        out.append({"name": html.unescape(mbr["title"]["rendered"]), "website": site, "city": city,
                    "country": "NL", "segment": "social_enterprise", "size_hint": "unknown"})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, help="only the first N members (testing)")
    a = ap.parse_args()
    c.report("social_enterprise_nl", c.add_rows(rows(a.limit), "social_enterprise_nl", a.dry_run), a.dry_run)


if __name__ == "__main__":
    main()
