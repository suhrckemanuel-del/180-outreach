"""Code-only enrichment and score gate for one organisation's own website. Zero LLM tokens.

    python tools/enrich.py <domain> [--json]      facts record (YAML) + digest for one organisation
    python tools/enrich.py score <domain>         score from the saved facts record
    python tools/enrich.py calibrate              score the 28 batch-1 cards, report recall on the fits
    python tools/enrich.py batch --pick N [--segment S]   enrich + score the next N 'new' rows, ranked table

What it reads: the homepage, robots.txt, sitemap.xml and up to 8 more pages of the organisation's own
site, chosen by words in the URL. It obeys robots.txt, caches every page for 7 days in
state/sources/enrich/, and never builds or guesses an address: an address is only reported when it is
printed on a page (mailto link or text, "[at]" decoded) on the organisation's own domain.
Every value in the facts record carries the URL of the page it came from.

Writes state/enrich/<domain>.facts.yaml and <domain>.digest.md (state/ is never committed). It changes
nothing in targets.yaml or pipeline.yaml.

SCORE CALIBRATION (2026-11-24, `python tools/enrich.py calibrate`, 28 batch-1 cards, threshold 3)
  Weights = the 12 priors in docs/scoping-2026-11-24/03-enrichment.md section 6, unchanged. Two code changes
  were needed to meet the target, not weight changes: a contact form (name/email/message) does not count as a
  workflow form, and an address printed on a sister TLD of the same name counts as on-domain (Equal
  Recruitment prints info@equalrecruitment.nl on equalrecruitment.com).
  Result: 11/11 fits clear the threshold; 7/17 rejects skipped (9/17 if D1 = yes, which adds the cultural -3
  and housing -2). The rejects that still pass have a form or a funder on the page but no workflow a person
  would call repetitive, so the model verdict stays the judge; this gate only removes the clear misses.
  Re-fit with logistic regression after ~100 model verdicts (doc section 6).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from html import unescape
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tenant  # noqa: E402

UA = "Mozilla/5.0 (compatible; 180dc-enrich/1.0; one request at a time, obeys robots.txt)"
ROBOT_UA = "180dc-enrich"   # the token robots.txt groups are matched on
HTML_CAP = 300_000          # characters handed to the regexes, bounds worst-case backtracking
CACHE_DIR = tenant.STATE / "sources" / "enrich"
OUT_DIR = tenant.STATE / "enrich"
CACHE_DAYS = 7
MAX_PAGES = 8          # beside the homepage
MAX_BYTES = 800_000
PAUSE = 0.4            # seconds between requests to one host
FETCH_BUDGET = 16      # hard cap on requests per organisation (robots, sitemaps, home, pages)

# ----------------------------------------------------------------------------------------- fetching


class Site:
    """One organisation's website: polite, cached, robots-aware fetching with a request budget."""

    def __init__(self, domain: str, fetcher=None):
        d = domain.strip().lower()
        d = d.split("://", 1)[-1].split("/")[0].removeprefix("www.")
        self.domain = d
        self.root = f"https://{d}/"
        self.fetcher = fetcher or self._http
        self.budget = FETCH_BUDGET
        self.robots = None
        self.robots_text = ""
        self.blocked: list[str] = []
        self.last = 0.0
        self.notes_robots = ""

    def _cache_file(self, url: str) -> Path:
        return CACHE_DIR / self.domain / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".json")

    def _http(self, url: str):
        wait = PAUSE - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        self.last = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "nl,en;q=0.8"})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                ctype = resp.headers.get("Content-Type", "")
                raw = resp.read(MAX_BYTES)
                try:
                    body = raw.decode(resp.headers.get_content_charset() or "utf-8", errors="replace")
                except LookupError:  # a bogus charset name in the header
                    body = raw.decode("utf-8", errors="replace")
                return {"body": body[:MAX_BYTES], "final": resp.geturl(), "ctype": ctype, "status": 200}
        except urllib.error.HTTPError as exc:
            return {"body": "", "final": url, "ctype": "", "status": exc.code}
        except Exception:  # noqa: BLE001 - timeouts, resets, bad status lines: one site must not stop the run
            return None

    def get(self, url: str, check_robots: bool = True):
        """Return {'body','final','ctype'} or None. Cached 7 days; never exceeds the request budget."""
        url = url.split("#")[0]
        if check_robots and self.robots is not None and not self.robots.can_fetch(ROBOT_UA, url):
            self.blocked.append(url)
            return None
        cf = self._cache_file(url)
        if cf.exists() and time.time() - cf.stat().st_mtime < CACHE_DAYS * 86400:
            try:
                return json.loads(cf.read_text(encoding="utf-8")) or None
            except (ValueError, OSError):  # a truncated cache file is a miss, not a crash
                pass
        if self.budget <= 0:
            return None
        self.budget -= 1
        got = self.fetcher(url)
        if got is None or got.get("status", 200) >= 400:
            return None  # failures are never cached: one timeout must not hide a site for a week
        final = got.get("final") or url
        if check_robots and final.split("#")[0] != url:
            # a redirect: the target must be on this site and allowed by robots.txt too
            if not same_site(final, self.domain) or (self.robots is not None and not self.robots.can_fetch(ROBOT_UA, final)):
                self.blocked.append(final)
                return None
        cf.parent.mkdir(parents=True, exist_ok=True)
        tmp = cf.with_suffix(".tmp")
        tmp.write_text(json.dumps(got), encoding="utf-8")
        tmp.replace(cf)
        return got

    def load_robots(self):
        rp = urllib.robotparser.RobotFileParser()
        url = urllib.parse.urljoin(self.root, "robots.txt")
        cf = self._cache_file(url)
        got = None
        if cf.exists() and time.time() - cf.stat().st_mtime < CACHE_DAYS * 86400:
            try:
                got = json.loads(cf.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                got = None
        if got is None:
            self.budget -= 1
            got = self.fetcher(url)
            if got and got.get("status", 200) < 400:
                cf.parent.mkdir(parents=True, exist_ok=True)
                cf.write_text(json.dumps(got), encoding="utf-8")
        if got is None or got.get("status", 200) >= 500:
            # RFC 9309: an unreachable robots.txt means do not crawl. Nothing is cached, so the next run retries.
            rp.parse(["User-agent: *", "Disallow: /"])
            self.notes_robots = "robots.txt unreachable: nothing fetched"
        elif got.get("status", 200) >= 400:
            rp.parse([])  # no robots.txt: everything allowed
        else:
            self.robots_text = got.get("body", "") if "html" not in got.get("ctype", "").lower() else ""
            rp.parse(self.robots_text.splitlines())
        self.robots = rp


def strip_blocks(html: str) -> str:
    """Drop <script>, <style>, <noscript>, <svg> and comments in one linear pass (no regex backtracking), so
    the size cap bites on visible markup and not on the megabytes of inline JavaScript a site builder adds."""
    low = html.lower()
    out, i = [], 0
    while i < len(html):
        hits = [(low.find(t, i), t) for t in ("<script", "<style", "<noscript", "<svg", "<!--")]
        hits = [(k, t) for k, t in hits if k != -1]
        if not hits:
            out.append(html[i:])
            break
        k, t = min(hits)
        out.append(html[i:k])
        end_tag = {"<script": "</script>", "<style": "</style>", "<noscript": "</noscript>", "<svg": "</svg>", "<!--": "-->"}[t]
        e = low.find(end_tag, k)
        i = len(html) if e == -1 else e + len(end_tag)
    return "".join(out)


def _is_html(got: dict) -> bool:
    ct = (got.get("ctype") or "").lower()
    return "html" in ct or (not ct and got.get("body", "").lstrip()[:1] == "<")


def same_site(url: str, domain: str) -> bool:
    host = urllib.parse.urlsplit(url).netloc.lower().split(":")[0].removeprefix("www.")
    return host == domain


SECOND_LEVEL = {"co", "org", "com", "net", "gov", "ac"}


def reg_domain(host: str) -> str:
    parts = host.lower().removeprefix("www.").split(".")
    if len(parts) >= 3 and parts[-2] in SECOND_LEVEL and len(parts[-1]) == 2:  # x.co.uk, x.com.au
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host.lower()


def stem(host: str) -> str:
    return reg_domain(host).split(".")[0]


# ------------------------------------------------------------------------------- page selection

CATEGORIES = [  # (name, url/anchor words, max pages)
    ("contact", r"contact|kontakt|bereik", 1),
    ("about", r"over-ons|over-|about|wie-zijn|organisatie|ons-verhaal|missie", 1),
    ("team", r"team|bestuur|medewerkers|mensen|colofon|board", 1),
    ("vacancies", r"vacature|werken-bij|werk-bij|jobs|careers|werkenbij|solliciteren", 1),
    ("annual", r"anbi|jaarverslag|jaarrekening|transparant", 1),
    ("funding", r"partners|financiering|fondsen|sponsor|steun|subsidie|donateur|samenwerking", 1),
    ("workflow", r"aanmeld|inschrijv|intake|verwijz|vrijwilliger|bestel|offerte|aanvragen|aanvraag|registr|word-lid|meld", 2),
]
SKIP_URL = re.compile(r"\.(pdf|jpe?g|png|gif|svg|webp|zip|docx?|xlsx?|mp[34])(\?|$)|/(wp-json|feed|tag|category|author|cart|winkelwagen|privacy|cookie)", re.I)


def link_candidates(html: str, base: str, domain: str) -> list[tuple[str, str]]:
    out = []
    for href, label in re.findall(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html):
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        link = urllib.parse.urljoin(base, href).split("#")[0]
        if same_site(link, domain) and not SKIP_URL.search(link):
            out.append((link, re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", unescape(label))).strip()))
    return out


def sitemap_urls(site: Site) -> list[str]:
    """URLs from sitemap.xml (one level of sitemap index, at most 2 extra files)."""
    urls: list[str] = []
    seeds = [urllib.parse.urljoin(site.root, "sitemap.xml")]
    for m in re.findall(r"(?im)^\s*sitemap:\s*(\S+)", site.robots_text):
        if same_site(m, site.domain) and m not in seeds:
            seeds.append(m)
    seen = 0
    for sm in seeds[:2]:
        got = site.get(sm, check_robots=False)
        if not got or "<loc" not in got["body"]:
            continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", got["body"])
        subs = [u for u in locs if u.endswith(".xml")]
        urls += [u for u in locs if not u.endswith(".xml")]
        for sub in subs[:2]:
            if seen >= 2:
                break
            seen += 1
            g2 = site.get(sub, check_robots=False)
            if g2:
                urls += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", g2["body"])
    return [u for u in urls if same_site(u, site.domain) and not SKIP_URL.search(u)]


def choose_pages(home_final: str, home_html: str, site: Site, sitemap: list[str]) -> list[str]:
    cands: dict[str, str] = {}
    for u in sitemap:
        cands.setdefault(u, "")
    for u, label in link_candidates(home_html, home_final, site.domain):
        cands[u] = label or cands.get(u, "")
    chosen: list[str] = []
    used = {home_final.rstrip("/"), site.root.rstrip("/")}
    for name, words, cap in CATEGORIES:
        rx = re.compile(words, re.I)
        scored = []
        for u, label in cands.items():
            if u.rstrip("/") in used or u in chosen:
                continue
            path = urllib.parse.urlsplit(u).path
            hit = len(rx.findall(path)) * 2 + len(rx.findall(label))
            if hit:
                scored.append((hit, -len(path), u))  # more hits first, shorter path first
        for _, _, u in sorted(scored, reverse=True)[:cap]:
            chosen.append(u)
            used.add(u.rstrip("/"))
        if len(chosen) >= MAX_PAGES:
            break
    return chosen[:MAX_PAGES]


# ------------------------------------------------------------------------------------ extraction

try:
    import trafilatura  # noqa: E402
except ImportError:  # pragma: no cover - requirements.txt lists it
    trafilatura = None


def page_text(html: str) -> str:
    if trafilatura is not None:
        try:
            t = trafilatura.extract(html, include_tables=True, favor_recall=True, no_fallback=False)
            if t:
                return t
        except Exception:  # noqa: BLE001 - fall back to plain text below
            pass
    html = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|section|article)>|<br\s*/?>", "\n", html)
    t = unescape(re.sub(r"(?s)<[^>]+>", " ", html))
    return "\n".join(l for l in (re.sub(r"[ \t]+", " ", x).strip() for x in t.split("\n")) if l)


def raw_lines(html: str) -> list[str]:
    """Visible text in block-sized lines (keeps address and name on their own lines)."""
    html = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<(h[1-6])\b[^>]*>(.*?)</\1>", lambda m: "\n" + re.sub(r"(?s)<[^>]+>", " ", m.group(2)) + "\n", html)
    html = re.sub(r"(?i)</(p|div|li|tr|td|section|article|dt|dd|address)>|<br\s*/?>", "\n", html)
    t = unescape(re.sub(r"(?s)<[^>]+>", " ", html))
    return [l for l in (re.sub(r"\s+", " ", x).strip() for x in t.split("\n")) if 2 <= len(l) <= 400]


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+\s*(?:@|\(at\)|\[at\])\s*[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")
SKIP_EMAIL = re.compile(r"\.(png|jpe?g|gif|svg|webp|css|js)$|example\.|sentry|wixpress|@2x|yourdomain|domain\.", re.I)
NAME_RE = re.compile(r"^(?:(?:Dr|Prof|Mr|Mw|Drs|Ir)\.\s+)*[A-ZÄÖÜ][\w'’.-]+(?:\s+(?:von|van|de|der|den|ter|te|di|la)?\s*[A-ZÄÖÜ][\w'’.-]+){1,3}$")
NAME_BEFORE = re.compile(r"((?:[A-ZÄÖÜ][\w'’.-]+)(?:\s+(?:van|de|der|den|ter|von)?\s*[A-ZÄÖÜ][\w'’.-]+){1,3})\s*[-–:|,/]\s*$")
NOT_A_NAME = re.compile(r"(?i)\b(stichting|team|contact|info|bestuur|directie|kantoor|aanmelden|administratie|vrijwilligers|voor|naar|mail|e-?mail|telefoon|adres|over|ons|onze|home|werken)\b")


def normalise_email(raw: str) -> str:
    t = re.sub(r"\s+", "", raw)
    t = re.sub(r"\(at\)|\[at\]", "@", t, flags=re.I)
    return t.strip(".").lower()


ROLE_NEVER = {"noreply", "no-reply", "donotreply", "do-not-reply", "postmaster", "webmaster", "hostmaster", "mailer-daemon"}
ROLE_LEGAL = {"privacy", "gdpr", "legal", "dpo", "abuse", "security", "klachten", "klacht"}
ROLE_RECRUIT = {"careers", "jobs", "hr", "talent", "recruitment", "karriere", "werken", "solliciteren", "vacatures", "sollicitaties"}
ROLE_GENERIC = {"info", "hello", "hallo", "contact", "sales", "marketing", "press", "pers", "media", "team", "welkom", "mail", "post", "kantoor", "secretariaat", "receptie"}
ROLE_WORKFLOW = [  # (workflow word in the address, why it is useful), most specific first
    "aanmelden", "aanmelding", "inschrijven", "inschrijving", "intake", "verwijzen", "meldingen",
    "vrijwilliger", "vrijwilligers", "bestellen", "bestelling", "orders", "offerte", "planning",
    "administratie", "boekhouding", "financien", "financiën", "klantenservice", "service", "coordinator", "coördinator",
]


def role_kind(addr: str, name: str | None) -> str:
    """person | role | recruit | legal | never | other. Ported from BDR-pipeline's email_finder (role sets
    only; its pattern guessing is deliberately not ported)."""
    local = addr.split("@")[0].lower()
    base = re.split(r"[._+-]", local)[0] if local not in ROLE_NEVER else local
    if local in ROLE_NEVER or base in ROLE_NEVER:
        return "never"
    if local in ROLE_LEGAL or base in ROLE_LEGAL:
        return "legal"
    if local in ROLE_RECRUIT or base in ROLE_RECRUIT:
        return "recruit"
    if name:
        return "person"
    if local in ROLE_GENERIC or any(w in local for w in ROLE_WORKFLOW):
        return "role"
    return "other"


def extract_emails(html: str, url: str, domain: str) -> list[dict]:
    """On-domain addresses printed on this page. Off-domain and asset-like strings are dropped."""
    found: dict[str, dict] = {}

    def keep(raw):
        a = normalise_email(raw)
        if "@" not in a or SKIP_EMAIL.search(a):
            return None
        host = a.split("@")[-1]
        # same registered name, or the same name on another TLD (equalrecruitment.nl printed on .com)
        if reg_domain(host) == reg_domain(domain):
            return a
        return a if stem(host) == stem(domain) and len(stem(domain)) >= 6 else None

    for href in re.findall(r'(?i)href=["\']mailto:([^"\'?]+)', html):
        m = EMAIL_RE.search(unescape(urllib.parse.unquote(href)))
        a = keep(m.group(0)) if m else None
        if a:
            found.setdefault(a, {"address": a, "url": url, "name": None})
    lines = raw_lines(html)
    for i, line in enumerate(lines):
        for raw in EMAIL_RE.findall(line):
            a = keep(raw)
            if not a:
                continue
            ent = found.setdefault(a, {"address": a, "url": url, "name": None})
            if ent["name"]:
                continue
            before = line.split(raw)[0]
            m = NAME_BEFORE.search(before)
            cand = m.group(1) if m else None
            if not cand:
                for prev in lines[max(0, i - 1):i]:
                    if NAME_RE.match(prev) and not NOT_A_NAME.search(prev):
                        cand = prev
                        break
            if cand and not NOT_A_NAME.search(cand):
                ent["name"] = cand
    return list(found.values())


FORM_RE = re.compile(r"(?is)<form\b(.*?)>(.*?)</form>")
NEWSLETTER = re.compile(r"nieuwsbrief|newsletter|mailchimp|inschrijven op de|abonneer|subscribe", re.I)


def extract_forms(html: str, url: str) -> list[dict]:
    forms = []
    for attrs, inner in FORM_RE.findall(html):
        if re.search(r'(?i)type=["\']search|role=["\']search|name=["\']s["\']|zoeken|search', attrs + inner[:300]) and len(re.findall(r"(?i)<input", inner)) <= 2:
            continue
        labels = [re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", unescape(x))).strip(" *:") for x in re.findall(r"(?is)<label[^>]*>(.*?)</label>", inner)]
        labels += [unescape(x).strip(" *:") for x in re.findall(r'(?i)placeholder=["\']([^"\']+)', inner)]
        for tag in re.findall(r"(?is)<(?:select|textarea)\b[^>]*>", inner):
            m = re.search(r'(?i)(?:aria-label|name)=["\']([^"\']+)', tag)
            if m:
                labels.append(m.group(1).replace("_", " ").replace("-", " ").strip())
        seen, uniq = set(), []
        for l in labels:
            k = l.lower()
            if l and len(l) < 80 and k not in seen and not re.search(r"(?i)mens bent|human|honeypot|captcha|leeg", l):
                seen.add(k)
                uniq.append(l)
        n_inputs = len(re.findall(r'(?i)<(?:input|select|textarea)\b(?![^>]*type=["\'](?:hidden|submit|button))', inner))
        if not uniq and not n_inputs:
            continue
        kind = "newsletter" if NEWSLETTER.search(attrs + inner) and len(uniq) <= 2 else "form"
        forms.append({"url": url, "fields": uniq[:15], "n_inputs": n_inputs, "kind": kind})
    return forms


def dedupe_forms(forms: list[dict]) -> list[dict]:
    """The same newsletter box in every page footer is one form, reported once at its first page."""
    seen, out = set(), []
    for f in forms:
        k = (tuple(x.lower() for x in f["fields"]), f["kind"])
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


FUNDERS = re.compile(
    r"\b(Gemeente (?:Rotterdam|Delft|Schiedam|Den Haag|Vlaardingen)|Oranje Fonds|VSBfonds|Fonds 1818|Stichting DOEN|Kansfonds|"
    r"Skanfonds|(?:Nationale )?Postcode ?Loterij|BankGiro Loterij|Rabobank (?:Stichting|Foundation|Fonds)|Instituut Gak|"
    r"ZonMw|Mondriaan Fonds|Fonds Cultuurparticipatie|Prins Bernhard Cultuurfonds|Ministerie van [A-Z]\w+(?: [A-Z]\w+)*|"
    r"Europese Unie|Europees Sociaal Fonds|Droomfonds|Fonds Sluyterman|Stichting Dioraphte|Haëlla|Janivo|"
    r"Van Leer Foundation|Fonds Slachtofferhulp|Cordaid|Stichting Gratis|Het Rotterdams Leescollectief|Jeugdwet|Wlz\b|Wmo\b|Zvw\b)", re.I)
FUND_PHRASE = re.compile(r"(?i)(?:gesteund|gefinancierd|mogelijk gemaakt|gesubsidieerd|subsidie|bijdrage|steun)\s+(?:door|van)\s+(?:het |de )?([A-Z][\w&'’ .-]{3,45}?)(?=[.,;:)\n]| en |$)")
STAFF_RE = re.compile(r"(?i)\b(\d{1,4})\s*(fte|medewerkers|collega'?s|professionals|werknemers|vrijwilligers|employees|staff|volunteers)\b")
# "500 medewerkers" on a partners page is the partner's size, not the organisation's. A figure counts
# only on a page about the organisation itself (over-ons, team, wie-zijn-wij), never on a page that
# lists partners, clients or funders.
STAFF_OK = re.compile(r"(?i)over[-_ ]?ons|overons|about|wie[-_ ]?zijn|organisatie|ons[-_ ]?verhaal|missie|"
                      r"team|bestuur|medewerkers|mensen|colofon|staff|board|directie")
STAFF_NO = re.compile(r"(?i)partner|klant|opdrachtgever|fondsen|fonds|sponsor|steun|donateur|samenwerking|"
                      r"netwerk|leverancier|deelnemer")


def staff_page_ok(url: str, text: str, pos: int) -> bool:
    """May the figure at text[pos] be read as this organisation's own staff count?"""
    path = urllib.parse.urlsplit(url).path.lower().rstrip("/")
    if STAFF_NO.search(path):
        return False
    if STAFF_OK.search(path):
        return True
    before = text[max(0, pos - 240):pos]
    for line in before.split("\n")[-3:]:  # a heading just above the figure marks the block
        if len(line) <= 80 and STAFF_OK.search(line) and not STAFF_NO.search(line):
            return True
    if STAFF_NO.search(before):
        return False
    return path == ""  # an unlabelled homepage figure is the organisation's own
JOB_WORDS = re.compile(r"(?i)\b(medewerker|co[oö]rdinator|manager|adviseur|assistent|assistant|specialist|analist|analyst|developer|ontwikkelaar|"
                       r"begeleider|consultant|stagiair|vrijwilliger|planner|administrateur|secretaresse|directeur|controller|officer|engineer|"
                       r"projectleider|teamleider|beleidsmedewerker|consulent|trainee|stage)\b")
ADMIN_ROLE = re.compile(r"(?i)\b(administra|office|planning|planner|backoffice|back office|bedrijfsvoering|secretar|data\b|\bai\b|"
                        r"automati|digital|\bict\b|\bit\b|crm|systeem|informatie|procesm|finan|co[oö]rdinator vrijwilligers|vrijwilligerscoördinator|"
                        r"kwaliteit|support|klantenservice)")
PAIN = re.compile(r"(?i)\b(werkdruk|administratieve last|administratielast|administratiedruk|wachtlijst|wachtlijsten|handmatig|handmatige|excel|"
                  r"digitalisering|digitaliseren|digitale transformatie|automatiseren|automatisering|\bAI\b|kunstmatige intelligentie|"
                  r"papierwerk|dubbel werk|inefficiënt|tijdrovend|tekort aan)\b")
NAV_WORKFLOW = re.compile(r"(?i)aanmeld|inschrijv|intake|verwijz|aanvragen|aanvraag|word[- ]lid|vrijwilliger[- ]worden|word[- ]vrijwilliger|bestel|offerte|reserver")
CONTACT_FIELD = re.compile(r"(?i)^(naam|name|voornaam|achternaam|e-?mail(adres)?|telefoon(nummer)?|phone|tel|bericht|message|vraag|onderwerp|subject|opmerkingen?|toelichting|.*akkoord.*|privacy.*)$")
WORKFLOW_WORDS = re.compile(r"(?i)aanmeld|inschrijv|intake|verwijz|vrijwilliger|bestel|offerte|aanvragen|webshop|abonnement|donatie|doneer|lid worden|word lid|rapportage|planning|reserver|boeken|contact opnemen")
PORTAL = re.compile(r"(?i)\b(mijn[\w-]*|inloggen|login|log in|dashboard|klantenportaal|portal|ouderportaal|app)\b")
TICKETS = re.compile(r"(?i)\b(tickets?|kaarten kopen|kaartverkoop|programma|agenda|voorstelling|exposities?)\b")
STOP = {
    "nl": re.compile(r"(?i)\b(de|het|een|en|van|voor|met|is|niet|wij|ons|onze|bij|om|ook|naar)\b"),
    "en": re.compile(r"(?i)\b(the|and|of|for|with|is|to|our|we|you|your|from|that)\b"),
    "de": re.compile(r"(?i)\b(der|die|das|und|nicht|ist|wir|mit|für|von|zu|ein|eine)\b"),
}


def detect_language(text: str) -> str:
    sample = text[:6000]
    counts = {k: len(rx.findall(sample)) for k, rx in STOP.items()}
    return max(counts, key=counts.get) if sum(counts.values()) else "unknown"


def sentence_around(text: str, m: re.Match, width: int = 140) -> str:
    s = max(0, m.start() - width)
    e = min(len(text), m.end() + width)
    return re.sub(r"\s+", " ", text[s:e]).strip()


# ------------------------------------------------------------------------------------- the record


def enrich(domain: str, fetcher=None, mx_check: bool = True, texts_out: dict | None = None) -> dict:
    site = Site(domain, fetcher)
    facts: dict = {
        "domain": site.domain, "site": site.root, "fetched": datetime.now().isoformat(timespec="seconds"),
        "alive": False, "pages": [], "js_needed": [], "robots_blocked": [], "emails": [], "forms": [],
        "funders": [], "staff": [], "vacancies": [], "pain": [], "workflow_words": [], "portal": [],
        "ticket_words": [], "language": "unknown", "role_match": None, "mx_problem": None, "notes": [],
    }
    site.load_robots()
    if site.notes_robots:
        facts["notes"].append(site.notes_robots)
    home = site.get(site.root)
    if not home or not _is_html(home):
        # try the www host once before calling the site down
        home = site.get(f"https://www.{site.domain}/")
    if not home or not home.get("body") or not _is_html(home):
        facts["notes"].append("site unreachable or empty")
        facts["robots_blocked"] = site.blocked[:10]
        return facts
    facts["alive"] = True
    final = home["final"]
    if not same_site(final, site.domain) and reg_domain(urllib.parse.urlsplit(final).netloc) != reg_domain(site.domain):
        facts["notes"].append(f"homepage redirects off-domain to {final}")
    sm = sitemap_urls(site)
    pages = [(final, home["body"])]
    for u in choose_pages(final, home["body"], site, sm):
        got = site.get(u)
        if got and _is_html(got):
            pages.append((got["final"], got["body"]))
    texts: dict[str, str] = {}
    all_emails: dict[str, dict] = {}
    for url, html in pages:
        html = strip_blocks(html)[:HTML_CAP]
        facts["pages"].append(url)
        text = page_text(html)
        texts[url] = text
        if texts_out is not None:
            texts_out[url] = text
        if len(text) < 250 and len(html) > 4000:
            facts["js_needed"].append(url)
        for e in extract_emails(html, url, site.domain):
            cur = all_emails.get(e["address"])
            if not cur or (e["name"] and not cur["name"]):
                all_emails[e["address"]] = e
        facts["forms"] += extract_forms(html, url)
        for m in FUNDERS.finditer(text):
            facts["funders"].append({"name": m.group(1), "url": url, "quote": sentence_around(text, m, 80)})
        for m in FUND_PHRASE.finditer(text):
            facts["funders"].append({"name": m.group(1).strip(), "url": url, "quote": sentence_around(text, m, 80)})
        for m in STAFF_RE.finditer(text):
            if not staff_page_ok(url, text, m.start()):
                continue
            facts["staff"].append({"n": int(m.group(1)), "unit": m.group(2).lower(), "url": url, "quote": sentence_around(text, m, 60)})
        for m in PAIN.finditer(text):
            facts["pain"].append({"word": m.group(1).lower(), "url": url, "quote": sentence_around(text, m, 110)})
        if re.search(r"vacature|werken-bij|werk-bij|jobs|careers|werkenbij|solliciteren", url, re.I):
            for line in raw_lines(html):
                if len(line) <= 90 and JOB_WORDS.search(line):
                    facts["vacancies"].append({"title": line, "admin": bool(ADMIN_ROLE.search(line)), "url": url})
        for m in NAV_WORKFLOW.finditer(urllib.parse.urlsplit(url).path):
            facts["workflow_words"].append({"word": m.group(0).lower(), "url": url})
        for m in PORTAL.finditer(text if url == final else ""):
            facts["portal"].append({"word": m.group(1).lower(), "url": url})
        for m in TICKETS.finditer(text if url == final else ""):
            facts["ticket_words"].append({"word": m.group(1).lower(), "url": url})
    # nav words on the homepage count as workflow signals too
    for link, label in link_candidates(home["body"], final, site.domain):
        if NAV_WORKFLOW.search(label + " " + urllib.parse.urlsplit(link).path):
            facts["workflow_words"].append({"word": (label or link)[:40].lower(), "url": final})
    seen_t = set()
    facts["vacancies"] = [v for v in facts["vacancies"] if not (v["title"] in seen_t or seen_t.add(v["title"]))][:15]
    facts["funders"] = _dedupe(facts["funders"], "name")
    facts["pain"] = _dedupe(facts["pain"], "word")
    facts["staff"] = facts["staff"][:6]
    facts["forms"] = dedupe_forms(facts["forms"])
    for key in ("workflow_words", "portal", "ticket_words"):
        seen_w = set()
        facts[key] = [x for x in facts[key] if not ((x["word"], x["url"]) in seen_w or seen_w.add((x["word"], x["url"])))][:12]
    facts["language"] = detect_language(texts.get(final, "") + " " + " ".join(texts.values())[:4000])
    facts["robots_blocked"] = site.blocked[:10]
    for a, e in all_emails.items():
        e["kind"] = role_kind(a, e["name"])
        facts["emails"].append(e)
    facts["role_match"] = suggest_address(facts["emails"])
    if mx_check and facts["emails"]:
        import pipeline  # reuses its DNS check; no second implementation
        facts["mx_problem"] = pipeline.mx_problem(reg_domain(facts["emails"][0]["address"].split("@")[1]))
    return facts


def _dedupe(rows: list[dict], key: str) -> list[dict]:
    seen, out = set(), []
    for r in rows:
        k = r[key].lower()
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out[:8]


def suggest_address(emails: list[dict]) -> dict | None:
    """Prefer a printed functional address that matches a workflow (aanmelden@, administratie@) over
    info@. Only ever picks an address that is already in the list, so nothing is built or guessed."""
    usable = [e for e in emails if e["kind"] in ("person", "role", "other")]
    for word in ROLE_WORKFLOW:
        for e in usable:
            if word in e["address"].split("@")[0].lower():
                return {"address": e["address"], "why": f"printed address matches the workflow word '{word}'", "url": e["url"]}
    for e in usable:
        if e["kind"] == "person":
            return {"address": e["address"], "why": f"personal address printed beside {e['name']}", "url": e["url"]}
    for e in usable:
        return {"address": e["address"], "why": "only a general address is printed", "url": e["url"]}
    return None


# ------------------------------------------------------------------------------------------ digest


def digest(facts: dict, texts: dict[str, str] | None = None, max_words: int = 600) -> str:
    """5 fact lines and the 3 best passages, every line with its URL, at most ~600 words."""
    d = facts["domain"]
    lines = [f"# {d} ({facts['language']}, {len(facts['pages'])} pages read)"]
    f = facts["forms"]
    real = [x for x in f if x["kind"] == "form"]
    lines.append("FORMS: " + ("; ".join(f"{', '.join(x['fields'][:6]) or str(x['n_inputs']) + ' inputs'} [{x['url']}]" for x in real[:2])
                              if real else ("newsletter form only" if f else "no form found") + f" [{facts['site']}]"))
    lines.append("FUNDERS: " + ("; ".join(f"{x['name']} [{x['url']}]" for x in facts["funders"][:4]) or f"none named on the pages read [{facts['site']}]"))
    st = facts["staff"]
    lines.append("STAFF: " + ("; ".join(f"{x['n']} {x['unit']} [{x['url']}]" for x in st[:3]) or f"no size stated [{facts['site']}]"))
    vac = facts["vacancies"]
    lines.append("HIRING: " + ("; ".join(f"{v['title']}{' (admin/data/AI)' if v['admin'] else ''} [{v['url']}]" for v in vac[:4]) or f"no vacancies found [{facts['site']}]"))
    em = facts["emails"]
    rm = facts["role_match"]
    lines.append("ADDRESS: " + (f"{rm['address']}, {rm['why']} [{rm['url']}]" + (f"; also printed: {', '.join(e['address'] for e in em if e['address'] != rm['address'])[:120]}" if len(em) > 1 else "")
                                if rm else "no on-domain address printed"))
    if texts:
        scored = []
        for url, text in texts.items():
            for para in re.split(r"\n+", text):
                para = para.strip()
                if 80 <= len(para) <= 420:
                    s = 2 * len(WORKFLOW_WORDS.findall(para)) + 2 * len(PAIN.findall(para)) + len(FUNDERS.findall(para))
                    if s:
                        scored.append((s, url, para))
        used = set()
        n = 0
        for s, url, para in sorted(scored, key=lambda x: -x[0]):
            if para[:40] in used or n >= 3:
                continue
            used.add(para[:40])
            lines.append(f'PASSAGE {n + 1}: "{para}" [{url}]')
            n += 1
    out = "\n".join(lines)
    words = out.split()
    return out if len(words) <= max_words else " ".join(words[:max_words]) + " …"


# --------------------------------------------------------------------------------------- the score
# Calibration is written here by `calibrate` (see CALIBRATION below the weights).

W = {
    "segment_social_enterprise": 3,
    "sector_words": 1,
    "cultural_name": -3,        # D1 only
    "form_or_workflow_nav": 3,
    "portal": 2,
    "newsletter_or_tickets_only": -2,
    "funder_or_subsidy": 2,
    "staff_8_100": 1,
    "staff_over_150": -3,
    "admin_vacancy": 2,
    "name_beside_address": 1,
    "housing": -2,              # D1 only
}
THRESHOLD = 3
CULTURAL = re.compile(r"(?i)theater|theatre|museum|festival|muziek|orkest|poppodium|galerie|gallery|monument|poezie|poetry|bioscoop|filmhuis|opera|dans\b")
HOUSING = re.compile(r"(?i)woningcorporatie|woonstad|havensteder|vestia|woonbron|woningbouw|\bwonen\b|aedes|woonstichting|wooncompagnie")
SECTOR = re.compile(r"(?i)zorg|jeugd|welzijn|onderwijs|vrijwilliger|wijk|kinder|school|gezin|ouderen|schuld|armoede|inclusi|talent|werkgelegenheid|re-integratie|participatie")


def decision_yes(key: str) -> bool:
    """Read a decision's answer from docs/decisions-*.md. Blank or anything not starting with 'yes' is no."""
    docs = Path(__file__).resolve().parents[1] / "docs"
    for f in sorted(docs.glob("decisions-*.md")):
        txt = f.read_text(encoding="utf-8")
        m = re.search(rf"\*\*{key}\.[^\n]*?\n(?:.*?\n)*?Answer[^:\n]*:[ \t]*([^\n]*)", txt)
        if m and m.group(1).strip().lower().startswith("yes"):
            return True
    return False


def gate(facts: dict, suppressed: set[str] | None = None, registry_blocked: str | None = None) -> str | None:
    if not facts.get("alive"):
        return "site down"
    if not facts.get("emails"):
        return "no on-domain address"
    if registry_blocked:
        return registry_blocked
    sup = suppressed or set()
    stems = {stem(x) for x in sup if "@" not in x} | {stem(x.split("@")[1]) for x in sup if "@" in x}
    if facts["domain"] in sup or stem(facts["domain"]) in stems or any(e["address"] in sup for e in facts["emails"]):
        return "suppressed"
    if facts.get("mx_problem") and "no mail server" in facts["mx_problem"]:
        return "no mail server"
    return None


def score(facts: dict, row: dict | None = None, d1: bool | None = None, weights: dict | None = None,
          suppressed: set[str] | None = None, registry_blocked: str | None = None) -> dict:
    row = row or {}
    w = weights or W
    d1 = decision_yes("D1") if d1 is None else d1
    skip = gate(facts, suppressed, registry_blocked)
    parts: list[tuple[str, int]] = []
    name = row.get("name") or ""
    if row.get("segment") == "social_enterprise":
        parts.append(("segment social_enterprise", w["segment_social_enterprise"]))
    sector_text = name + " " + " ".join(p.get("quote", "") for p in facts.get("pain", []))
    if SECTOR.search(name) or (row.get("segment") == "nonprofit" and SECTOR.search((row.get("size_hint") or "") + " " + facts.get("site", ""))):
        parts.append(("social/care/youth/education words", w["sector_words"]))
    if d1 and CULTURAL.search(name):
        parts.append(("cultural name (D1)", w["cultural_name"]))
    if d1 and (HOUSING.search(name) or row.get("segment") == "woningcorporatie"):
        parts.append(("housing association (D1)", w["housing"]))
    forms = [f for f in facts.get("forms", []) if f["kind"] == "form"]
    # a contact form (name, email, message) is not a workflow: count only fields beyond those
    real = [f for f in forms if len([x for x in f["fields"] if not CONTACT_FIELD.match(x)]) >= 3]
    if real or facts.get("workflow_words"):
        parts.append(("form with 3+ fields or aanmelden/inschrijven/intake in nav", w["form_or_workflow_nav"]))
    if facts.get("portal"):
        parts.append(("portal / login / dashboard", w["portal"]))
    if (facts.get("forms") and not forms or facts.get("ticket_words")) and not forms:
        parts.append(("newsletter form or ticket shop only", w["newsletter_or_tickets_only"]))
    if facts.get("funders") or _subsidy_ok(row.get("size_hint") or ""):
        parts.append(("named funder or Rotterdam subsidy 50k-1M", w["funder_or_subsidy"]))
    staff = [s["n"] for s in facts.get("staff", []) if s["unit"] in ("fte", "medewerkers", "collega's", "collega’s", "professionals", "werknemers", "employees", "staff")]
    if staff:
        top = max(staff)
        if top > 150:
            parts.append(("staff above ~150", w["staff_over_150"]))
        elif 8 <= top <= 100:
            parts.append(("staff about 8-100", w["staff_8_100"]))
    if any(v["admin"] for v in facts.get("vacancies", [])):
        parts.append(("admin/data/AI vacancy on own site", w["admin_vacancy"]))
    if any(e["name"] for e in facts.get("emails", [])):
        parts.append(("a person's name beside a printed address", w["name_beside_address"]))
    total = sum(p for _, p in parts)
    return {"score": total, "skip": skip, "go": skip is None and total >= THRESHOLD, "parts": parts}


def _subsidy_ok(hint: str) -> bool:
    m = re.search(r"EUR\s*([\d.,]+)", hint or "")
    if not m:
        return False
    try:
        v = int(re.sub(r"[.,]", "", m.group(1)))
    except ValueError:
        return False
    return 50_000 <= v <= 1_000_000


# --------------------------------------------------------------------------------------------- I/O


def save(facts: dict, dig: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-z0-9.-]", "_", facts["domain"]).strip(".")
    (OUT_DIR / f"{safe}.facts.yaml").write_text(yaml.safe_dump(facts, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
    (OUT_DIR / f"{safe}.digest.md").write_text(dig + "\n", encoding="utf-8")


def load_facts(domain: str) -> dict:
    p = OUT_DIR / f"{re.sub(r'[^a-z0-9.-]', '_', domain.removeprefix('www.').lower())}.facts.yaml"
    if not p.exists():
        sys.exit(f"no facts for {domain}: run  python tools/enrich.py {domain}  first")
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def run_one(domain: str, fetcher=None) -> tuple[dict, str]:
    site_texts: dict[str, str] = {}
    facts = enrich(domain, fetcher, texts_out=site_texts)
    dig = digest(facts, site_texts)
    save(facts, dig)
    return facts, dig


def targets() -> list[dict]:
    return (tenant.load(tenant.DIR / "targets.yaml", {}) or {}).get("candidates") or []


def row_for(domain: str) -> dict:
    for r in targets():
        if tenant.domain_of(r.get("website", "")) == domain:
            return r
    return {}


def suppressed_set() -> set[str]:
    s = tenant.load(tenant.SUPPRESSION, {}) or {}
    return {str(x).lower() for x in (list(s.get("addresses") or {}) + list(s.get("domains") or []))}


def registry_block(domain: str) -> str | None:
    try:
        import registry
        return registry.blocked_reason(domain)
    except Exception:  # noqa: BLE001 - a registry that cannot be read is reported by send.py, not here
        return None


def pick_rows(n: int, segment: str | None, cities=("delft", "rotterdam")) -> list[dict]:
    """The next 'new' rows by the rule in tools/sources/mark.py --pick: Delft and Rotterdam only, file
    order, nonprofits alternating social and cultural."""
    rows = [x for x in targets() if x.get("status") == "new" and x.get("city", "").lower() in cities
            and (not segment or x.get("segment") == segment)]
    if segment in (None, "nonprofit"):
        npf = [x for x in rows if x.get("segment") == "nonprofit"]
        cult = [x for x in npf if "culturele ANBI" in (x.get("size_hint") or "")]
        soc = [x for x in npf if x not in cult]
        mixed = [x for pair in zip(soc, cult) for x in pair] + soc[len(cult):] + cult[len(soc):]
        rows = [x for x in rows if x.get("segment") != "nonprofit"] + mixed if segment is None else mixed
    return rows[:n]


def cmd_batch(a):
    seen_d, rows = set(), []
    for r in pick_rows(a.pick, a.segment):  # one row per host, so threads never hit the same site together
        d = tenant.domain_of(r.get("website") or "")
        if d and d not in seen_d:
            seen_d.add(d)
            rows.append(r)
    t0 = time.time()
    sup = suppressed_set()

    def work(r):
        d = tenant.domain_of(r.get("website") or "")
        try:
            facts, _ = run_one(d)
        except Exception as exc:  # noqa: BLE001 - one bad site must not stop the batch
            return r, None, f"error: {exc}"
        return r, facts, None

    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(work, rows))
    table, js_pages, all_pages = [], 0, 0
    for r, facts, err in results:
        d = tenant.domain_of(r.get("website") or "")
        if not facts:
            table.append((-99, d, r.get("name") or d, "ERROR", err))
            continue
        js_pages += len(facts["js_needed"])
        all_pages += len(facts["pages"])
        sc = score(facts, r, suppressed=sup, registry_blocked=registry_block(d))
        table.append((sc["score"], d, r.get("name") or d, "skip: " + sc["skip"] if sc["skip"] else ("GO" if sc["go"] else "below"),
                      "; ".join(f"{p:+d} {n}" for n, p in sc["parts"])[:110]))
    table.sort(key=lambda x: -x[0])
    for s, d, name, verdict, why in table:
        print(f"{s:>3}  {verdict:<26} {d:<34} {name[:34]:<34} {why}")
    go = sum(1 for t in table if t[3] == "GO")
    print(f"\n{len(table)} organisations, {go} go to the model, {time.time() - t0:.0f}s, "
          f"js_needed on {js_pages}/{all_pages} pages ({100 * js_pages / max(all_pages, 1):.0f}%)")


CARD_LINE = re.compile(r"^ORG:.*?(https?://\S+)", re.M)


def batch1_cards() -> list[tuple[str, str, str]]:
    """(domain, card name, 'fit'|'reject') for every card in cards/."""
    out = []
    for p in sorted((tenant.DIR / "cards").glob("*.md")):
        txt = p.read_text(encoding="utf-8")
        m = CARD_LINE.search(txt)
        v = re.search(r"^VERDICT:\s*(FIT|REJECT)", txt, re.M)
        if m and v:
            out.append((tenant.domain_of(m.group(1)), p.stem, v.group(1).lower()))
    return out


def cmd_calibrate(a):
    cards = batch1_cards()
    sup = suppressed_set()
    d1 = True if a.d1 else None  # calibrate as if D1 = yes only when asked

    def work(c):
        d, stem, verdict = c
        try:
            facts = load_facts(d) if a.cached else run_one(d)[0]
        except Exception:  # SystemExit is not an Exception: a missing record raises it, handled below
            facts = run_one(d)[0]
        except SystemExit:
            facts = run_one(d)[0]
        return c, facts

    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(work, cards))
    fits_ok, rejects_skipped, rows = 0, 0, []
    n_fit = sum(1 for c in cards if c[2] == "fit")
    for (d, stem, verdict), facts in res:
        sc = score(facts, row_for(d) or {"name": stem}, d1=d1, suppressed=sup)
        passed = sc["go"]
        if verdict == "fit" and passed:
            fits_ok += 1
        if verdict == "reject" and not passed:
            rejects_skipped += 1
        rows.append((verdict, passed, sc["score"], stem, sc["skip"], "; ".join(f"{p:+d} {n}" for n, p in sc["parts"])))
    for r in sorted(rows, key=lambda x: (x[0], -x[2])):
        print(f"{r[0]:<7} {'GO ' if r[1] else 'no '} {r[2]:>3}  {r[3]:<24} {('skip: ' + r[4]) if r[4] else '':<24} {r[5][:100]}")
    n_rej = len(cards) - n_fit
    print(f"\nthreshold {THRESHOLD}: {fits_ok}/{n_fit} fits clear it; {rejects_skipped}/{n_rej} rejects would have been skipped")


def main():
    argv = sys.argv[1:]
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if argv and argv[0] == "batch":
        ap = argparse.ArgumentParser(prog="enrich.py batch")
        ap.add_argument("--pick", type=int, required=True)
        ap.add_argument("--segment")
        return cmd_batch(ap.parse_args(argv[1:]))
    if argv and argv[0] == "calibrate":
        ap = argparse.ArgumentParser(prog="enrich.py calibrate")
        ap.add_argument("--cached", action="store_true", help="reuse saved facts instead of fetching")
        ap.add_argument("--d1", action="store_true", help="score as if decision D1 were yes")
        return cmd_calibrate(ap.parse_args(argv[1:]))
    if argv and argv[0] == "score":
        ap = argparse.ArgumentParser(prog="enrich.py score")
        ap.add_argument("domain")
        a = ap.parse_args(argv[1:])
        d = tenant.domain_of(a.domain)
        sc = score(load_facts(d), row_for(d), suppressed=suppressed_set(), registry_blocked=registry_block(d))
        print(json.dumps(sc, indent=1, ensure_ascii=False))
        return None
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("domain")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    facts, dig = run_one(a.domain)
    print(json.dumps(facts, ensure_ascii=False, indent=1) if a.json else yaml.safe_dump(facts, sort_keys=False, allow_unicode=True, width=120))
    print("\n--- digest ---\n" + dig)
    return None


if __name__ == "__main__":
    main()
