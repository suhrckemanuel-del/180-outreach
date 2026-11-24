"""Provider-agnostic test bench for a cheap model on the verdict job (job A). Zero model calls itself.

It reads the digests in tenants/<t>/state/enrich/*.digest.md, builds the verdict prompt from
docs/prompts/cheap-model-context.md, asks a function the user supplies, checks the JSON shape, and
compares the verdict with the answer key in tenants/<t>/cards/*.md (`VERDICT: FIT|REJECT ...`).

The model is never called from this repo's code: point VERDICT_MODEL at a Python file outside the repo
(so no key or endpoint is committed) that defines:

    def model(prompt: str) -> str: ...

Usage:
    VERDICT_MODEL=/path/to/model.py python tools/verdict_harness.py
    python tools/verdict_harness.py --model /path/to/model.py --limit 5
    python tools/verdict_harness.py --digests DIR --cards DIR --context FILE   (a fixture run)

Every record must be {"domain","verdict":"fit"|"reject","tier":1..3,"reason":<=25 words,
"evidence_url"} and `evidence_url` must be a substring of that digest.
Exit code 1 only when a record was unusable (bad JSON or failed validation); a wrong verdict is data.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tenant  # noqa: E402

REPO = Path(__file__).resolve().parents[1]  # the shared docs live with the code, not with a tenant's state
DIGESTS = tenant.STATE / "enrich"
CARDS = tenant.DIR / "cards"
CONTEXT = REPO / "docs" / "prompts" / "cheap-model-context.md"
VERDICTS = ("fit", "reject")


def context_text(path: Path | None = None) -> str:
    p = Path(path) if path else CONTEXT
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        sys.exit(f"cannot read the context file: {p}")


def build_prompt(context: str, digest_text: str) -> str:
    """The job-A instructions from the shared context file, then the digest. Nothing else."""
    try:
        job = context[context.index("A. **Verdict.**"):context.index("B. **Two ideas.**")].strip()
        rules = context[context.index("## Never"):context.index("## Privacy")].strip()
    except ValueError:  # a rewritten context file: fall back to the whole thing rather than guessing
        job, rules = "", context.strip()
    return "\n\n".join(x for x in (
        job, rules, "Return only that one JSON object: no prose, no code fence.",
        "DIGEST:\n" + digest_text.strip()) if x) + "\n"


def parse_json(raw: str) -> tuple[dict | None, str]:
    """The first JSON object in the reply. A code fence around it is tolerated, prose is not."""
    if not isinstance(raw, str) or not raw.strip():
        return None, "empty reply"
    text = re.sub(r"^\s*```[a-z]*\s*|\s*```\s*$", "", raw.strip(), flags=re.I)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None, "no JSON object in the reply"
    try:
        rec = json.loads(text[start:end + 1])
    except ValueError as exc:
        return None, f"JSON does not parse: {exc}"
    return (rec, "") if isinstance(rec, dict) else (None, "the reply is not a JSON object")


def validate(rec: dict, digest_text: str) -> list[str]:
    """Every rule the brief sets for a job-A record."""
    problems = []
    domain = rec.get("domain")
    if not isinstance(domain, str) or not domain.strip():
        problems.append("domain missing")
    elif domain.strip().lower() not in digest_text.lower():
        problems.append(f"domain {domain!r} is not in the digest")
    verdict = rec.get("verdict")
    if verdict not in VERDICTS:
        problems.append(f"verdict must be fit|reject, not {verdict!r}")
    tier = rec.get("tier")
    if not isinstance(tier, int) or isinstance(tier, bool) or tier not in (1, 2, 3):
        problems.append(f"tier must be 1, 2 or 3, not {tier!r}")
    reason = rec.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        problems.append("reason missing")
    elif len(reason.split()) > 25:
        problems.append(f"reason is {len(reason.split())} words (max 25)")
    url = rec.get("evidence_url")
    if not isinstance(url, str) or not url.strip():
        problems.append("evidence_url missing")
    elif url.strip() not in digest_text:
        problems.append("evidence_url is not a substring of the digest")
    return problems


def answer_key(cards_dir: Path | None = None) -> dict[str, str]:
    """domain -> 'fit'|'reject' from every card's ORG: line and VERDICT: line."""
    out: dict[str, str] = {}
    for p in sorted((Path(cards_dir) if cards_dir else CARDS).glob("*.md")):
        txt = p.read_text(encoding="utf-8")
        m = re.search(r"^ORG:.*?(https?://\S+)", txt, re.M)
        v = re.search(r"^VERDICT:\s*(FIT|REJECT)", txt, re.M)
        if not m or not v:
            continue
        out[tenant.domain_of(m.group(1)) or p.stem] = v.group(1).lower()
    return out


def digests(digests_dir: Path | None = None) -> list[tuple[str, str]]:
    """(domain, text) for every digest file, in file-name order."""
    d = Path(digests_dir) if digests_dir else DIGESTS
    out = []
    for p in sorted(d.glob("*.digest.md")):
        out.append((p.name[:-len(".digest.md")], p.read_text(encoding="utf-8")))
    return out


def load_model(spec: str):
    """A `model(prompt) -> str` callable from a Python file the user points at. No key lives here."""
    path = Path(spec).expanduser()
    if not path.exists():
        sys.exit(f"VERDICT_MODEL / --model points at no file: {path}")
    mod_spec = importlib.util.spec_from_file_location("verdict_model", path)
    if not mod_spec or not mod_spec.loader:
        sys.exit(f"cannot load a Python file from {path}")
    module = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(module)
    fn = getattr(module, "model", None)
    if not callable(fn):
        sys.exit(f"{path} must define model(prompt) -> str")
    return fn


def compare(model, pairs: list[tuple[str, str]], key: dict[str, str], context: str,
            limit: int | None = None) -> list[dict]:
    rows = []
    for domain, text in pairs[:limit] if limit else pairs:
        row = {"domain": domain, "expected": key.get(domain), "record": None, "problems": [], "error": ""}
        try:
            raw = model(build_prompt(context, text))
        except Exception as exc:  # noqa: BLE001 - one bad reply must not stop the bench
            row["error"] = f"model raised {type(exc).__name__}: {exc}"
            rows.append(row)
            continue
        rec, why = parse_json(raw)
        if rec is None:
            row["error"] = why
        else:
            row["record"] = rec
            row["problems"] = validate(rec, text)
        rows.append(row)
    return rows


def summarise(rows: list[dict]) -> dict:
    graded = [r for r in rows if r["expected"]]
    matched = [r for r in graded if r["record"] and not r["problems"]
               and r["record"].get("verdict") == r["expected"]]
    return {"total": len(graded), "matched": len(matched),
            "mismatched": [r for r in graded if r not in matched],
            "invalid": [r for r in rows if r["error"] or r["problems"]]}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default=None, help="path to a Python file defining model(prompt); "
                                                  "defaults to the VERDICT_MODEL env var")
    ap.add_argument("--digests", type=Path, default=None)
    ap.add_argument("--cards", type=Path, default=None)
    ap.add_argument("--context", type=Path, default=None)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    spec = a.model or __import__("os").environ.get("VERDICT_MODEL", "")
    if not spec:
        sys.exit("no model: set VERDICT_MODEL to a Python file or pass --model")
    key = answer_key(a.cards)
    pairs = digests(a.digests)
    if not pairs:
        sys.exit("no digests found: run tools/enrich.py first")
    rows = compare(load_model(spec), pairs, key, context_text(a.context), a.limit)
    for r in rows:
        got = (r["record"] or {}).get("verdict") or "-"
        mark = "ok" if r["expected"] and r["record"] and not r["problems"] and got == r["expected"] else "  "
        print(f"{mark} {r['domain']:<34} expected {r['expected'] or '-':<7} got {got}")
        for p in r["problems"]:
            print(f"     invalid: {p}")
        if r["error"]:
            print(f"     error: {r['error']}")
    s = summarise(rows)
    rate = 100 * s["matched"] / s["total"] if s["total"] else 0.0
    print(f"\nmatch rate: {s['matched']}/{s['total']} ({rate:.0f}%) on the answer key")
    for r in s["mismatched"]:
        reason = (r["record"] or {}).get("reason") or r["error"] or "; ".join(r["problems"])
        print(f"mismatch: {r['domain']} expected {r['expected']}, got "
              f"{(r['record'] or {}).get('verdict', '-')} ({reason})")
    return 1 if any(r["error"] or r["problems"] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
