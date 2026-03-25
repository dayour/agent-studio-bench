"""Export marketplace experiment data as OM-valid evaluation artifacts.

Converts the bench YAML customer/business datasets into Copilot Studio
ObjectModel-conformant TestCaseComponent and SimpleEvaluationCase structures.
These can be validated with om-cli validate and pushed to Copilot Studio
via the Island Gateway testcomponent API.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _customer_to_eval_case(customer: dict[str, Any]) -> dict[str, Any]:
    """Convert a marketplace customer YAML into a SimpleEvaluationCase."""
    request_text = customer.get("request", "")
    items = customer.get("menu_features", {})
    amenities = customer.get("amenity_features", [])

    # Build a rich input string that includes the full request context
    input_parts = [request_text]
    if items:
        item_names = ", ".join(items.keys())
        input_parts.append(f"Required topics: {item_names}")
    if amenities:
        amenity_names = ", ".join(amenities) if isinstance(amenities, list) else ", ".join(amenities.keys())
        input_parts.append(f"Required connected systems: {amenity_names}")

    return {
        "$kind": "SimpleEvaluationCase",
        "input": " | ".join(input_parts),
        "source": "Generated",
        "diagnostics": [],
    }


def _build_test_case_component(
    display_name: str,
    cases: list[dict[str, Any]],
    *,
    description: str = "",
    parent_bot_component_id: str | None = None,
) -> dict[str, Any]:
    """Build a TestCaseComponent wrapping EvaluationData rows."""
    schema_name = f"mspva_{uuid.uuid4()}"
    component: dict[str, Any] = {
        "$kind": "TestCaseComponent",
        "schemaName": schema_name,
        "definition": {
            "$kind": "EvaluationData",
            "rows": cases,
            "diagnostics": [],
            "extensionData": {
                "displayOrder": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
            },
        },
        "displayName": display_name,
        "description": description or display_name,
        "category": "Testing",
        "state": "Active",
    }
    if parent_bot_component_id:
        component["parentBotComponentId"] = parent_bot_component_id
    return component


def _build_evaluation_set(
    display_name: str,
    *,
    description: str = "",
) -> dict[str, Any]:
    """Build an EvaluationSet (the parent container for test cases)."""
    return {
        "$kind": "TestCaseComponent",
        "schemaName": f"mspva_{uuid.uuid4()}",
        "definition": {
            "$kind": "EvaluationSet",
            "graders": [
                {"$kind": "GeneralQualityGrader", "diagnostics": []},
            ],
            "diagnostics": [],
        },
        "displayName": display_name,
        "description": description or display_name,
        "category": "Testing",
        "state": "Active",
    }


def export_eval_test_set(
    dataset_dir: str | Path,
    *,
    output_path: str | Path | None = None,
    set_name: str | None = None,
) -> dict[str, Any]:
    """Export a marketplace dataset as an OM-valid evaluation test set.

    Args:
        dataset_dir: Path to a dataset directory (e.g. data/policy_advisor_3_9).
        output_path: Optional path to write the JSON output.
        set_name: Display name for the evaluation set. Defaults to directory name.

    Returns:
        A dict containing the full OM-conformant test set payload ready for
        the testcomponent API, plus metadata about what was exported.
    """
    dataset_path = Path(dataset_dir)
    customers_dir = dataset_path / "customers"

    if not customers_dir.exists():
        raise FileNotFoundError(f"No customers directory at {customers_dir}")

    set_display_name = set_name or f"Evaluate {dataset_path.name}"
    eval_set = _build_evaluation_set(set_display_name, description=f"Generated from {dataset_path.name}")

    cases = []
    customer_files = sorted(customers_dir.glob("*.yaml"))
    for cf in customer_files:
        customer = _load_yaml(cf)
        case = _customer_to_eval_case(customer)
        cases.append(case)

    test_case_components = []
    for i, case in enumerate(cases):
        component = _build_test_case_component(
            display_name=case["input"][:100],
            cases=[case],
            description=f"Test case {i + 1} from {dataset_path.name}",
        )
        test_case_components.append(component)

    payload = {
        "metadata": {
            "source": str(dataset_path),
            "exportedAt": datetime.now(timezone.utc).isoformat(),
            "customerCount": len(customer_files),
            "caseCount": len(cases),
        },
        "evaluationSet": eval_set,
        "testCaseComponents": test_case_components,
    }

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)

    return payload


def export_analytics_as_eval_cases(
    analytics_json: str | Path,
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Convert marketplace analytics results into OM eval cases.

    Each customer transaction becomes a SimpleEvaluationCase with the
    customer request as input and the actual purchase outcome as
    expectedOutput. This enables regression testing of marketplace behavior.
    """
    with open(analytics_json, encoding="utf-8") as f:
        analytics = json.load(f)

    cases = []
    # Support both analytics JSON shapes
    customer_list = analytics.get("customer_summaries", analytics.get("customers", []))
    for customer in customer_list:
        # Analytics JSON may use 'request' (full) or 'customer_name' (summary)
        request_text = customer.get("request", "")
        if not request_text:
            name = customer.get("customer_name", customer.get("name", "unknown"))
            cid = customer.get("customer_id", "")
            request_text = f"Customer {name} ({cid})" if cid else f"Customer {name}"

        payments = customer.get("payments", [])
        payments_made = customer.get("payments_made", 0)
        needs_met = customer.get("needs_met", False)
        utility = customer.get("utility", 0)

        expected = "needs_met=True" if needs_met else "needs_met=False"
        expected += f" | utility={utility}"
        if payments:
            paid_to = payments[0].get("business_name", "unknown")
            amount = payments[0].get("amount", 0)
            expected += f" | paid={amount} to {paid_to}"
        elif payments_made:
            expected += f" | payments_made={payments_made}"

        case = {
            "$kind": "SimpleEvaluationCase",
            "input": request_text,
            "source": "Generated",
            "expectedOutput": expected,
            "diagnostics": [],
        }
        cases.append(case)

    set_name = f"Evaluate {Path(analytics_json).stem}"
    eval_set = _build_evaluation_set(set_name)

    components = []
    for i, case in enumerate(cases):
        comp = _build_test_case_component(
            display_name=case["input"][:100],
            cases=[case],
            description=f"Analytics case {i + 1}",
        )
        components.append(comp)

    payload = {
        "metadata": {
            "source": str(analytics_json),
            "exportedAt": datetime.now(timezone.utc).isoformat(),
            "caseCount": len(cases),
        },
        "evaluationSet": eval_set,
        "testCaseComponents": components,
    }

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)

    return payload
