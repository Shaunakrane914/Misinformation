#!/usr/bin/env python3
"""
Aegis Protocol — Scraper Laboratory CLI
=======================================
First-class testing, benchmarking, and schema-drift detection CLI for websites.
Tells the engineering team how outside websites are changing.

CRITICAL INVARIANT:
This script and the scrapers/ package are STRICTLY for laboratory testing,
canary checks, schema validation, and health reporting.
It MUST NOT be imported or invoked by production agents.

Usage:
  python scraper.py test <platform>    # e.g. reddit, x, youtube, github, web
  python scraper.py test-all           # run canaries across all platforms
  python scraper.py health             # output health summary table
  python scraper.py report             # full structured health report
"""

import argparse
import json
import sys
from typing import List

from scrapers import (
    ScraperLabRunner,
    format_health_report,
    format_summary_table,
    scraper_test_registry,
)


def main():
    parser = argparse.ArgumentParser(
        description="Aegis Protocol — Scraper Laboratory (Testing & Benchmarking Suite)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Laboratory command to run")

    # Command: test <platform>
    test_parser = subparsers.add_parser("test", help="Run canary test for a specific website/platform")
    test_parser.add_argument(
        "platform",
        type=str,
        help="Target platform (reddit, x, youtube, github, web, google_news, instagram, facebook, tiktok, linkedin, bilibili)",
    )
    test_parser.add_argument("--json", action="store_true", help="Output results as JSON")

    # Command: test-all
    test_all_parser = subparsers.add_parser("test-all", help="Run canaries across all registered platforms")
    test_all_parser.add_argument("--json", action="store_true", help="Output results as JSON")

    # Command: health
    subparsers.add_parser("health", help="Display health summary table")

    # Command: report
    report_parser = subparsers.add_parser("report", help="Display comprehensive health and schema report")
    report_parser.add_argument("--json", action="store_true", help="Output report as JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    runner = ScraperLabRunner()

    if args.command == "test":
        res = runner.run_platform_test(args.platform)
        if not res:
            print(f"Error: Unknown platform '{args.platform}'. Available: {scraper_test_registry.list_platforms()}")
            sys.exit(1)
        if getattr(args, "json", False):
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(format_health_report([res]))

    elif args.command == "test-all":
        results = runner.run_all()
        if getattr(args, "json", False):
            print(json.dumps([r.to_dict() for r in results], indent=2))
        else:
            print(format_health_report(results))

    elif args.command == "health":
        results = runner.run_all()
        print(format_summary_table(results))

    elif args.command == "report":
        results = runner.run_all()
        if getattr(args, "json", False):
            print(json.dumps([r.to_dict() for r in results], indent=2))
        else:
            print(format_health_report(results))


if __name__ == "__main__":
    main()
