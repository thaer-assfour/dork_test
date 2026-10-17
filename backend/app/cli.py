"""DorkHub command-line interface. Each module can be driven independently."""
from __future__ import annotations

import argparse
import json
import sys

from app.db.base import SessionLocal, init_db


def _cmd_initdb(_args) -> None:
    init_db()
    print("database initialized")


def _cmd_set_password(args) -> None:
    from app.security import hash_password

    h = hash_password(args.password)
    print("Add this to your .env:")
    print(f"DORKHUB_AUTH_PASSWORD_HASH={h}")


def _cmd_hash_password(args) -> None:
    """Print only the bcrypt hash. Password is read from stdin (never argv)."""
    from app.security import hash_password

    password = sys.stdin.readline().rstrip("\n")
    if not password:
        print("empty password", file=sys.stderr)
        sys.exit(1)
    print(hash_password(password))


def _cmd_gen_secret(_args) -> None:
    import secrets

    print(secrets.token_urlsafe(48))


def _cmd_import_dorks(_args) -> None:
    from app.dorks.importer import import_library

    init_db()
    db = SessionLocal()
    try:
        print(json.dumps(import_library(db)))
    finally:
        db.close()


def _cmd_discover(args) -> None:
    from app.discovery.sources import SOURCES

    if args.source not in SOURCES:
        print(f"unknown source. choose from: {', '.join(SOURCES)}", file=sys.stderr)
        sys.exit(1)
    rows = SOURCES[args.source](only_self_hosted=not args.all)
    print(json.dumps(rows[: args.limit], indent=2))


def _cmd_estimate(args) -> None:
    from app.engines.registry import get_engine
    from app.scanner.planner import build_plan

    init_db()
    db = SessionLocal()
    try:
        engine = get_engine(args.engine)
        plan = build_plan(db, args.targets, args.dorks, args.engine, float(engine.price_per_1000))
        print(json.dumps(plan.as_dict(), indent=2))
    finally:
        db.close()


def main() -> None:
    p = argparse.ArgumentParser(prog="dorkhub")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("initdb").set_defaults(func=_cmd_initdb)

    sp = sub.add_parser("set-password")
    sp.add_argument("password")
    sp.set_defaults(func=_cmd_set_password)

    sub.add_parser("hash-password").set_defaults(func=_cmd_hash_password)
    sub.add_parser("gen-secret").set_defaults(func=_cmd_gen_secret)

    sub.add_parser("import-dorks").set_defaults(func=_cmd_import_dorks)

    sd = sub.add_parser("discover")
    sd.add_argument("source")
    sd.add_argument("--all", action="store_true", help="include platform-hosted programs")
    sd.add_argument("--limit", type=int, default=20)
    sd.set_defaults(func=_cmd_discover)

    se = sub.add_parser("estimate")
    se.add_argument("--targets", type=int, nargs="+", required=True)
    se.add_argument("--dorks", type=int, nargs="+", required=True)
    se.add_argument("--engine", default="serper")
    se.set_defaults(func=_cmd_estimate)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
