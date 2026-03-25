#!/usr/bin/env python3
"""Standalone script to validate a dataset against the Copilot Studio ObjectModel
and optionally export it as an OM-conformant eval test set.

Usage:
    python scripts/om_validate.py data/policy_advisor_3_9
    python scripts/om_validate.py data/policy_advisor_3_9 --export eval-results/policy_advisor_om.json
    python scripts/om_validate.py --schema EvaluationSet
    python scripts/om_validate.py --search "Eval*"
    python scripts/om_validate.py --analytics analytics_results_mr_policy_advisor_3_9.json --export eval-results/analytics_om.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ObjectModel integration for the marketplace framework"
    )
    parser.add_argument(
        "dataset_dir",
        nargs="?",
        help="Path to dataset directory to validate and/or export",
    )
    parser.add_argument(
        "--export",
        help="Path to write OM-conformant eval test set JSON",
    )
    parser.add_argument(
        "--analytics",
        help="Path to analytics JSON to convert to OM eval cases",
    )
    parser.add_argument(
        "--schema",
        help="Get schema for a named OM type",
    )
    parser.add_argument(
        "--search",
        help="Search OM types by wildcard pattern",
    )
    parser.add_argument(
        "--list-types",
        action="store_true",
        help="List all concrete OM types",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Print count of concrete OM types",
    )

    args = parser.parse_args()

    # Lazy import so the script works even without the full package installed
    try:
        from magentic_marketplace.om_schema.client import OMClient
        from magentic_marketplace.om_schema.eval_export import (
            export_analytics_as_eval_cases,
            export_eval_test_set,
        )
    except ImportError:
        # Add the package src to path for standalone execution
        pkg_src = Path(__file__).resolve().parent.parent / "packages" / "magentic-marketplace" / "src"
        sys.path.insert(0, str(pkg_src))
        from magentic_marketplace.om_schema.client import OMClient
        from magentic_marketplace.om_schema.eval_export import (
            export_analytics_as_eval_cases,
            export_eval_test_set,
        )

    # Schema queries
    if args.schema:
        result = OMClient.schema(args.schema)
        print(json.dumps(result, indent=2))
        return 0

    if args.search:
        results = OMClient.search(args.search)
        print(json.dumps(results, indent=2))
        return 0

    if args.list_types:
        types = OMClient.list_types()
        for t in types:
            print(f"  {t['name']:45s} base={t.get('baseType', '-')}")
        print(f"\n  {len(types)} concrete types")
        return 0

    if args.count:
        print(OMClient.type_count())
        return 0

    # Analytics export
    if args.analytics:
        analytics_path = Path(args.analytics)
        if not analytics_path.exists():
            print(f"ERROR: analytics file not found: {analytics_path}", file=sys.stderr)
            return 1
        payload = export_analytics_as_eval_cases(
            analytics_path,
            output_path=args.export,
        )
        meta = payload["metadata"]
        print(f"Exported {meta['caseCount']} analytics eval cases")
        if args.export:
            print(f"  Output: {args.export}")
        return 0

    # Dataset export
    if args.dataset_dir:
        dataset_path = Path(args.dataset_dir)
        if not dataset_path.exists():
            print(f"ERROR: dataset directory not found: {dataset_path}", file=sys.stderr)
            return 1

        payload = export_eval_test_set(
            dataset_path,
            output_path=args.export,
        )
        meta = payload["metadata"]
        print(f"Dataset: {meta['source']}")
        print(f"  Customers: {meta['customerCount']}")
        print(f"  Eval cases: {meta['caseCount']}")
        print(f"  EvaluationSet: {payload['evaluationSet']['displayName']}")
        print(f"  TestCaseComponents: {len(payload['testCaseComponents'])}")
        if args.export:
            print(f"  Output: {args.export}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
