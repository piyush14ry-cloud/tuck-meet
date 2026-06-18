#!/usr/bin/env python3
"""Standalone entry point for the daily matching job.

Schedule this to run every day at 5:00 PM. Two easy options:

  cron (Linux/macOS) - `crontab -e`:
      0 17 * * *  cd /path/to/tuck-meet && /path/to/.venv/bin/python scripts/run_matching.py

  Flask CLI equivalent:
      0 17 * * *  cd /path/to/tuck-meet && flask run-matching

On Windows, use Task Scheduler to run this script daily at 17:00.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.matching import run_matching  # noqa: E402


def main() -> None:
    app = create_app()
    with app.app_context():
        result = run_matching()
        print(f"Created {result.created} matches for {result.people_matched} people.")
        for line in result.details:
            print(f"  - {line}")


if __name__ == "__main__":
    main()
