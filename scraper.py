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
    test_parser.add_argument("--offline", action="store_true", help="Run fast offline validation using fixture payload")

    # Command: test-all
    test_all_parser = subparsers.add_parser("test-all", help="Run canaries across all registered platforms")
    test_all_parser.add_argument("--json", action="store_true", help="Output results as JSON")
    test_all_parser.add_argument("--offline", action="store_true", help="Run fast offline validation using fixture payload")

    # Command: health
    health_parser = subparsers.add_parser("health", help="Display health summary table")
    health_parser.add_argument("--offline", action="store_true", help="Run fast offline validation using fixture payload")

    # Command: report
    report_parser = subparsers.add_parser("report", help="Display comprehensive health and schema report")
    report_parser.add_argument("--json", action="store_true", help="Output report as JSON")
    report_parser.add_argument("--offline", action="store_true", help="Run fast offline validation using fixture payload")

    # Command: history <platform>
    hist_parser = subparsers.add_parser("history", help="Display historical health and delta diagnosis")
    hist_parser.add_argument("platform", nargs="?", default=None, help="Target platform (optional)")
    hist_parser.add_argument("--json", action="store_true", help="Output delta as JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    runner = ScraperLabRunner()
    is_live = not getattr(args, "offline", False)

    if args.command == "test":
        res = runner.run_platform_test(args.platform, live_network=is_live)
        if not res:
            print(f"Error: Unknown platform '{args.platform}'. Available: {scraper_test_registry.list_platforms()}")
            sys.exit(1)
        if getattr(args, "json", False):
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(format_health_report([res]))

    elif args.command == "test-all":
        results = runner.run_all(live_network=is_live)
        if getattr(args, "json", False):
            print(json.dumps([r.to_dict() for r in results], indent=2))
        else:
            print(format_health_report(results))

    elif args.command == "health":
        results = runner.run_all(live_network=is_live)
        print(format_summary_table(results))

    elif args.command == "report":
        results = runner.run_all(live_network=is_live)
        if getattr(args, "json", False):
            print(json.dumps([r.to_dict() for r in results], indent=2))
        else:
            print(format_health_report(results))

    elif args.command == "history":
        platforms = [args.platform] if args.platform else scraper_test_registry.list_platforms()
        deltas = [runner.compute_historical_delta(p) for p in platforms]
        if getattr(args, "json", False):
            print(json.dumps(deltas, indent=2))
        else:
            for d in deltas:
                print(f"[{d['platform'].upper()}] {d['diagnosis']}")
                if d.get("has_history"):
                    print(f"  Status: {d['previous_status']} -> {d['current_status']}")
                    print(f"  Backend: {d['previous_backend']} -> {d['current_backend']}")
                    print(f"  Latency Delta: {d['latency_delta_ms']:+d} ms")
                    print(f"  Fallback Delta: {d['fallback_delta']:+d}")
                print()


if __name__ == "__main__":
    main()
