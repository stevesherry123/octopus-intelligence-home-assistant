from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import Settings
from .history import DEFAULT_HISTORY_URL, download_history
from .pipeline import run_pipeline
from .scheduler import run_scheduler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="octopus-intelligence")
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download-history")
    download.add_argument("--output", default="data/agile-history.json")
    download.add_argument("--url", default=DEFAULT_HISTORY_URL)
    run = commands.add_parser("run")
    run.add_argument("--feed-file", type=Path)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--no-ai", action="store_true")
    run.add_argument(
        "--no-announce",
        action="store_true",
        help="Publish the analysis sensor without updating the announcement helper",
    )
    schedule = commands.add_parser("schedule")
    schedule.add_argument("--interval-hours", type=float, default=3)
    schedule.add_argument("--no-ai", action="store_true")
    schedule.add_argument("--no-announce", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "download-history":
        print(download_history(args.output, url=args.url))
    elif args.command == "run":
        feed = args.feed_file.read_text(encoding="utf-8") if args.feed_file else None
        analysis = run_pipeline(
            Settings.from_environment(),
            feed_text=feed,
            dry_run=args.dry_run,
            use_ai=not args.no_ai,
            publish_announcement=not args.no_announce,
        )
        print(json.dumps(analysis, indent=2))
    elif args.command == "schedule":
        run_scheduler(
            Settings.from_environment(),
            interval_hours=args.interval_hours,
            use_ai=not args.no_ai,
            publish_announcement=not args.no_announce,
        )


if __name__ == "__main__":
    main()
