"""One writer for the tenant's pipeline.yaml at a time. Zero LLM tokens.

The job kit's lock was held for a whole session, and an interactive session once overlapped the
daily run. Here every write takes the lock for seconds only (`with locked("sender"): ...`), and a
lock older than STALE_MINUTES is treated as abandoned by a crashed run.

Usage from the shell (for a session that edits pipeline.yaml by hand):
    python tools/writer_lock.py status
    python tools/writer_lock.py acquire --seat claude
    python tools/writer_lock.py release --seat claude
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import sys
import time

import yaml

import tenant

SEATS = ("claude", "manuel", "sender", "sync")
STALE_MINUTES = 30


def read_lock():
    return tenant.load(tenant.LOCK)


def _stale(data) -> bool:
    try:
        since = dt.datetime.fromisoformat(str(data.get("since")))
    except (TypeError, ValueError):
        return True
    return (dt.datetime.now().astimezone() - since).total_seconds() > STALE_MINUTES * 60


def acquire(seat: str, wait_seconds: int = 0) -> None:
    deadline = time.time() + wait_seconds
    while True:
        current = read_lock()
        if not current or current.get("seat") == seat or _stale(current):
            break
        if time.time() >= deadline:
            sys.exit(f"writer lock held by {current.get('seat')} since {current.get('since')}")
        time.sleep(2)
    payload = {"seat": seat, "since": dt.datetime.now().astimezone().isoformat(timespec="seconds")}
    tenant.LOCK.parent.mkdir(parents=True, exist_ok=True)
    tenant.LOCK.write_text(yaml.safe_dump(payload), encoding="utf-8")


def release(seat: str) -> None:
    current = read_lock()
    if current and current.get("seat") != seat and not _stale(current):
        sys.exit(f"writer lock held by {current.get('seat')}; {seat} cannot release it")
    if tenant.LOCK.exists():
        tenant.LOCK.unlink()


@contextlib.contextmanager
def locked(seat: str, wait_seconds: int = 60):
    acquire(seat, wait_seconds)
    try:
        yield
    finally:
        release(seat)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    for name in ("acquire", "release"):
        p = sub.add_parser(name)
        p.add_argument("--seat", required=True, choices=SEATS)
    args = ap.parse_args()
    if args.cmd == "status":
        data = read_lock()
        print("writer lock: free" if not data else f"writer lock: {data.get('seat')} since {data.get('since')}"
              + (" (stale)" if _stale(data) else ""))
    elif args.cmd == "acquire":
        acquire(args.seat)
        print(f"writer lock: {args.seat}")
    else:
        release(args.seat)
        print("writer lock: free")


if __name__ == "__main__":
    main()
