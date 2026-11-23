"""Check a client-outreach email before it becomes a Gmail draft. Zero LLM tokens.

The draft carries two kinds of tags, both stripped by --clean:
  [claim:ID]   after every sentence about us; ID must be in the tenant ledger with usable: true
  [src:URL]    after every fact about the recipient; a first email needs at least one

Exit code 1 on any ERROR. tools/send.py runs this again before every send.

Usage:
    python tools/lint_email.py drafts/stichting-x-1.txt --clean drafts/stichting-x-1.clean.txt
    python tools/lint_email.py drafts/stichting-x-fu.txt --followup --clean drafts/stichting-x-fu.clean.txt
    python tools/lint_email.py drafts/verein-y-1.txt --lang de
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import tenant

BANNED = [
    # filler and sales cliché
    "hope this finds you well", "hope you're doing well", "hope you are doing well", "just following up",
    "just checking in", "circling back", "touching base", "passionate", "leverage", "delve", "synergy",
    "caught my attention", "caught my eye", "i came across", "i wanted to reach out", "reaching out because",
    "thrilled", "excited to", "game-changer", "game changer", "cutting-edge", "in today's fast-paced",
    "looking forward to hearing from you", "quick question", "no strings attached", "limited time",
    # AI-pitch cliché
    "ai-powered", "revolutionise", "revolutionize", "unlock", "streamline", "harness the power",
    "transform your", "supercharge", "seamless", "next-generation",
    # German
    "ich hoffe, es geht ihnen gut", "mit großem interesse", "revolutionieren", "nahtlos",
    # spam-filter words
    "free!!!", "act now", "100% free", "risk-free", "guarantee",
]
SLOT = re.compile(r"\{[^}]{2,}\}|\bTODO\b|\bTR-\.\.\.")


def ledger():
    data = tenant.load(tenant.LEDGER, {}) or {}
    return {c["id"]: c for c in data.get("claims", [])}


def lint(raw: str, *, followup: bool, lang: str | None) -> tuple[list[str], list[str], str]:
    claims = re.findall(r"\[claim:([A-Za-z0-9-]+)\]", raw)
    sources = re.findall(r"\[src:([^\]\s]+)\]", raw)
    body = re.sub(r"\s*\[(claim|src):[^\]]+\]", "", raw)
    body = re.sub(r"[ \t]+\n", "\n", body)
    low = body.lower()
    errors, warns = [], []

    text_only = re.sub(r"(?im)^(subject|betreff):.*$", "", body)
    words = len(re.findall(r"\b[\wÀ-ÿ'-]+\b", re.sub(r"https?://\S+", "", text_only)))
    limit = 60 if followup else 125
    (errors if words > limit + 15 else warns if words > limit else []).append(f"{words} words (target <= {limit})")

    if SLOT.search(body):
        errors.append(f"unfilled template slot: {SLOT.search(body).group(0)}")
    if re.search(r"[—–]", body):
        errors.append("em/en dash: use a comma or a full stop")
    for phrase in BANNED:
        if phrase in low:
            errors.append(f"banned phrase: '{phrase}'")
    q = re.sub(r"https?://\S+", "", text_only).count("?")
    if q != 1:
        errors.append(f"{q} question marks: exactly one ask")
    if re.search(r"(?im)^\s*--\s*$|not relevant\? reply|kein interesse\?", body):
        errors.append("footer or opt-out written into the body: gmail_draft.py adds it")
    if re.search(r"\b(attached|attachment|anbei|im anhang)\b", low):
        errors.append("mentions an attachment: first-touch emails carry none")

    booking = str((tenant.config() or {}).get("booking_link") or "")
    links = re.findall(r"https?://\S+", body)
    others = [u for u in links if not (booking and booking != "TODO" and u.rstrip(".,)").startswith(booking))]
    if others:
        errors.append(f"link other than the booking link: {others[0]}")
    if not followup and booking and booking != "TODO" and booking not in body:
        warns.append("booking link missing")
    if re.search(r"\b\d+\s?%|\b\d+\s?(hours|stunden|uur) (a|per|pro) (week|woche)", low):
        errors.append("usage or time-saving number: never in outreach")

    if not followup and not sources:
        errors.append("no [src:URL] tag: every fact about the recipient needs its page")
    for url in sources:
        if not url.startswith("http"):
            errors.append(f"[src:] is not a URL: {url}")

    known = ledger()
    if not known:
        warns.append("tenant ledger missing: claim IDs not checked")
    for cid in claims:
        c = known.get(cid)
        if known and c is None:
            errors.append(f"claim ID not in ledger: {cid}")
        elif c is not None and not c.get("usable"):
            errors.append(f"claim {cid} is not usable yet: {c.get('note', '')}")

    german = bool(re.search(r"\b(ich|und|nicht|wäre|grüßen|ihre)\b", low))
    if lang == "de" and not german:
        errors.append("--lang de but the email is not in German")
    if lang == "en" and german:
        errors.append("--lang en but the email reads as German")
    if german:
        du = re.search(r"\b(du|dich|dir|dein\w*|euch|euer\w*)\b", low)
        if du:
            errors.append("German emails use Sie, not du")
    return errors, warns, body.strip() + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file")
    ap.add_argument("--followup", action="store_true", help="follow-up in the same thread: 60 words, no [src:] needed")
    ap.add_argument("--lang", choices=["en", "de"])
    ap.add_argument("--clean", help="write the email with tags removed to this file")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    errors, warns, clean = lint(Path(args.file).read_text(encoding="utf-8"), followup=args.followup, lang=args.lang)
    for e in errors:
        print("ERROR ", e)
    for w in warns:
        print("warn  ", w)
    if not errors and not warns:
        print("ok")
    if args.clean:
        Path(args.clean).write_text(clean, encoding="utf-8")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
