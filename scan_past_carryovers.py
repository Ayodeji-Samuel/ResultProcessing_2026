#!/usr/bin/env python3
"""
Management script: scan existing results and back-fill carryover records.

Usage:
    python scan_past_carryovers.py             # scan ALL sessions
    python scan_past_carryovers.py --session 1  # scan a specific session (by ID)

This is safe to run multiple times — duplicates are skipped automatically.
"""
import argparse
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.utils.grading import scan_and_create_past_carryovers


def main():
    parser = argparse.ArgumentParser(description='Scan results and create missing carryover records')
    parser.add_argument('--session', type=int, default=None,
                        help='Limit scan to a specific academic session ID. Omit to scan all.')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        print('Scanning existing results for carryovers ...')
        result = scan_and_create_past_carryovers(session_id=args.session)

        print(f"\nDone!")
        print(f"  Carryover records created from failures : {result['created_from_failures']}")
        print(f"  Carryovers auto-cleared (passed later)  : {result['cleared']}")
        print(f"  Results flagged as carryover (level diff): {result['flagged_carryover_results']}")


if __name__ == '__main__':
    main()
