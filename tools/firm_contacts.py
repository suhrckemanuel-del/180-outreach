"""Pull the contact details a firm publishes on its own website. Zero LLM tokens.

Fetches the homepage plus the usual team / contact / Impressum / careers pages, follows same-site
links whose text looks like one of those, and prints compact JSON: published email addresses (with
the page each came from), whether the careers pages mention internships, and the pages it read.
Job-posting PDFs linked from those pages are read too (needs pypdf), because some firms only print
the application address inside the posting.

It only reports what the firm published. It never builds or guesses an address from a name
pattern; a person without a published address stays without one.

With --people it also prints a short digest of the team pages for a session LLM to read instead of
fetching them again: navigation and footer lines repeated across the site are dropped, and only the
lines around names, job titles and career-path phrases ("started as an intern") are kept.

Pages are cached in data/cache/<host>/ for 7 days, so a --people rerun costs no fetches. robots.txt
is respected.

Usage:
    python tools/firm_contacts.py hf-debt.com
    python tools/firm_contacts.py https://www.robuscap.com/en/ --max-pages 25
    python tools/firm_contacts.py b2venture.vc --people
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from collections import Counter
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
CACHE_DAYS = 7

PATH_GUESSES = [
    "", "team", "en/team", "de/team", "about/team", "people", "en/people", "ueber-uns", "about-us",
    "contact", "en/contact", "kontakt", "de/kontakt", "impressum", "imprint", "en/imprint",
    "legal-notice", "careers", "en/careers", "karriere", "jobs", "en/jobs",
    # Dutch nonprofit sites (180DC client outreach)
    "over-ons", "over-ons/team", "over-ons/organisatie", "organisatie", "ons-team", "wie-zijn-wij",
    "medewerkers", "bestuur", "colofon", "nl/contact", "contact-opnemen", "werken-bij", "vacatures",
]
LINK_WORDS = re.compile(
    r"team|people|member|partner|kontakt|contact|impressum|imprint|legal|karriere|career|jobs|about|ueber"
    r"|over-ons|organisatie|medewerkers|bestuur|colofon|wie-zijn|werken-bij|vacature",
    re.I)
PDF_WORDS = re.compile(r"career|karriere|job|stelle|intern|praktik|werkstudent|posting|ausschreibung", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+\s*(?:@|\(at\)|\[at\])\s*[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")
INTERN = re.compile(r"praktik|intern\b|internship|werkstudent|working student|trainee|off-cycle", re.I)
SKIP_EMAIL = re.compile(r"\.(png|jpe?g|gif|svg|webp)$|example\.|sentry|wixpress|@2x", re.I)
UA = "Mozilla/5.0 (compatible; firm-contacts/1.0)"

# --people digest
TEAM_PAGE = re.compile(r"team|people|member|partner|about|ueber|our-|unser|over-ons|organisatie|medewerkers|bestuur", re.I)
TITLE = re.compile(
    r"\b(partner|principal|associate|analyst|analystin|investment manager|director|managing|"
    r"gesch[aä]ftsf[uü]hrer\w*|vorstand|founder|gr[uü]nder\w*|ceo|cfo|coo|cto|vice president|vp|"
    r"head of|senior|junior|werkstudent\w*|working student|intern|praktikant\w*|trainee|advisor|berater\w*|"
    r"investor|venture|scout|operating|chief|leiter\w*|manager\w*|"
    r"directeur|directrice|bestuurder|bestuurslid|voorzitter|penningmeester|secretaris|co[oö]rdinator\w*|"
    r"bedrijfsvoering|operations|office manager|programma\w*|teamleider|projectleider|fondsenwerv\w*)\b", re.I)
PATH = re.compile(
    r"(started (as|at|his|her|their)|joined|began|since \d{4}|seit \d{4}|prior to|before joining|previously|"
    r"zuvor|vorher|angefangen|begann|als (praktikant|werkstudent)|as an? (intern|working student|analyst)|"
    r"internships? at|praktik\w* bei|studied|studierte|graduated|alumn)", re.I)
NAME = re.compile(r"^(?:(?:Dr|Prof)\.\s+)*[A-ZÄÖÜ][\w'’.-]+(?:\s+(?:von|van|de|der|zu|den|di|la)?\s*[A-ZÄÖÜ][\w'’.-]+){1,3}$")
BLOCK_END = re.compile(r"(?i)</(p|div|li|h[1-6]|tr|td|section|article|figcaption|dt|dd)>|<br\s*/?>")
HEADING = re.compile(r"(?is)<(h[1-6])\b[^>]*>(.*?)</\1>")


def _cache_path(url):
    host = urllib.parse.urlsplit(url).netloc.removeprefix("www.") or "unknown"
    return CACHE / host / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".json")


def fetch(url, timeout=12, use_cache=True, want_pdf=False):
    """Return (content, final_url, kind) where kind is 'html', 'pdf' or None."""
    cp = _cache_path(url)
    if use_cache and cp.exists() and time.time() - cp.stat().st_mtime < CACHE_DAYS * 86400:
        c = json.loads(cp.read_text(encoding="utf-8"))
        return c["content"], c["final"], c["kind"]
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "de,en;q=0.8"})
    content, final, kind = None, url, None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            final, ctype = resp.geturl(), resp.headers.get("Content-Type", "")
            if "html" in ctype:
                content, kind = resp.read(800_000).decode("utf-8", errors="replace"), "html"
            elif want_pdf and "pdf" in ctype:
                content, kind = pdf_text(resp.read(5_000_000)), "pdf"
    except (urllib.error.URLError, TimeoutError, ValueError, ConnectionError):
        pass
    if use_cache and content is not None:
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(json.dumps({"content": content, "final": final, "kind": kind}), encoding="utf-8")
    return content, final, kind


def pdf_text(data):
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages[:6])
    except Exception:  # noqa: BLE001 - a broken PDF is just skipped
        return None


def robots_for(root):
    rp = urllib.robotparser.RobotFileParser()
    try:
        req = urllib.request.Request(urllib.parse.urljoin(root, "robots.txt"), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=8) as resp:
            rp.parse(resp.read(200_000).decode("utf-8", errors="replace").splitlines())
    except Exception:  # noqa: BLE001 - no robots.txt means everything is allowed
        rp.parse([])
    return rp


def normalise_email(raw):
    text = re.sub(r"\s+", "", raw)
    text = re.sub(r"\(at\)|\[at\]", "@", text, flags=re.I)
    return text.strip(".").lower()


def visible_text(html):
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    return unescape(re.sub(r"(?s)<[^>]+>", " ", html))


def text_lines(html):
    """Visible text split at block boundaries, one cleaned line per block."""
    html = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", html)
    # a heading is one line even when it splits first and last name with <br> or <span>
    html = HEADING.sub(lambda m: "\n" + re.sub(r"(?s)<[^>]+>", " ", m.group(2)) + "\n", html)
    html = BLOCK_END.sub("\n", html)
    text = unescape(re.sub(r"(?s)<[^>]+>", " ", html))
    return [l for l in (re.sub(r"\s+", " ", x).strip() for x in text.split("\n")) if 2 <= len(l) <= 400]


def people_digest(page_lines, max_chars):
    """Keep name / title / path lines from team pages; drop lines repeated across the site."""
    n = len(page_lines)
    seen_on = Counter(l for lines in page_lines.values() for l in set(lines))
    boiler = {l for l, c in seen_on.items() if n >= 3 and c >= max(3, n // 2)}
    digest, used, kept = {}, 0, set()
    for url, lines in page_lines.items():
        lines = [l for l in lines if l not in boiler]
        if not TEAM_PAGE.search(url) and sum(bool(TITLE.search(l)) for l in lines) < 3:
            continue
        keep = []
        for i, line in enumerate(lines):
            short_title = TITLE.search(line) and len(line) <= 80
            if short_title or PATH.search(line):
                prev = lines[i - 1] if i else ""
                if prev and NAME.match(prev) and prev not in kept:
                    keep.append(prev)
                    kept.add(prev)
                if line not in kept:
                    keep.append(line[:300])
                    kept.add(line)
            elif NAME.match(line) and i + 1 < len(lines) and TITLE.search(lines[i + 1]) and line not in kept:
                keep.append(line)
                kept.add(line)
        if not keep:
            continue
        block = keep[:80]
        size = sum(len(l) + 1 for l in block)
        if used + size > max_chars:
            block = block[: max(0, (max_chars - used) // 60)]
            size = sum(len(l) + 1 for l in block)
        if block:
            digest[url] = block
            used += size
        if used >= max_chars:
            break
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("site")
    parser.add_argument("--max-pages", type=int, default=18)
    parser.add_argument("--people", action="store_true", help="add a team-page digest for a session LLM")
    parser.add_argument("--digest-chars", type=int, default=6000)
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    site = args.site if "://" in args.site else f"https://{args.site}"
    base = urllib.parse.urlsplit(site)
    root = f"{base.scheme}://{base.netloc}/"
    host = base.netloc.removeprefix("www.")
    robots = robots_for(root)
    use_cache = not args.no_cache

    queue = [urllib.parse.urljoin(root, p) for p in PATH_GUESSES]
    if site.rstrip("/") + "/" != root:
        queue.insert(0, site)
    seen, pages, emails, intern_pages = set(), [], {}, []
    pdfs, pdf_queue, blocked, page_lines = [], [], [], {}

    def take(text, final):
        for raw in EMAIL.findall(text):
            addr = normalise_email(raw)
            if "@" in addr and not SKIP_EMAIL.search(addr):
                emails.setdefault(addr, final)

    while queue and len(pages) < args.max_pages:
        url = queue.pop(0).split("#")[0]
        if url in seen:
            continue
        seen.add(url)
        if not robots.can_fetch(UA, url):
            blocked.append(url)
            continue
        html, final, kind = fetch(url, use_cache=use_cache)
        if kind != "html" or not html or final in pages:
            continue
        pages.append(final)

        for href in re.findall(r'(?i)href=["\']mailto:([^"\'?]+)', html):
            addr = normalise_email(urllib.parse.unquote(href))
            if not SKIP_EMAIL.search(addr):
                emails.setdefault(addr, final)
        text = visible_text(html)
        take(text, final)
        if INTERN.search(text) and LINK_WORDS.search(final):
            intern_pages.append(final)
        if args.people:
            page_lines[final] = text_lines(html)

        for href, label in re.findall(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html):
            link = urllib.parse.urljoin(final, href)
            parts = urllib.parse.urlsplit(link)
            if parts.netloc.removeprefix("www.") != host or link in seen:
                continue
            label_text = visible_text(label)
            if parts.path.lower().endswith(".pdf"):
                if (PDF_WORDS.search(parts.path) or PDF_WORDS.search(label_text)) and link not in pdf_queue:
                    pdf_queue.append(link)
            elif LINK_WORDS.search(parts.path) or LINK_WORDS.search(label_text):
                queue.append(link)

    for link in pdf_queue[:3]:
        if not robots.can_fetch(UA, link):
            blocked.append(link)
            continue
        text, final, kind = fetch(link, use_cache=use_cache, want_pdf=True)
        if kind == "pdf" and text:
            pdfs.append(final)
            take(text, final)
            if INTERN.search(text):
                intern_pages.append(final)

    stem = host.split(".")[0]  # hf-debt.com and hf-debt.de are the same firm
    own = {e: src for e, src in emails.items() if e.split("@")[-1].split(".")[0] == stem}
    out = {
        "site": root,
        "published_emails_on_domain": own,
        "other_emails": {e: s for e, s in emails.items() if e not in own},
        "pages_mentioning_internships": sorted(set(intern_pages)),
        "pages_read": len(pages),
    }
    if pdfs:
        out["pdfs_read"] = pdfs
    if blocked:
        out["blocked_by_robots"] = blocked[:10]
    if args.people:
        out["people_digest"] = people_digest(page_lines, args.digest_chars)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
