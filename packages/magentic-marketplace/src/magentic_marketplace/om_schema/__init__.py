"""ObjectModel CLI integration for the marketplace framework.

Provides a Python wrapper around om-cli.exe (Copilot Studio ObjectModel CLI)
for schema validation, type lookup, eval test set generation, and composition
queries. The CLI binary lives at E:\\agent-studio\\tools\\om-cli\\om-cli.exe.
"""

from magentic_marketplace.om_schema.client import OMClient
from magentic_marketplace.om_schema.eval_export import export_eval_test_set

__all__ = ["OMClient", "export_eval_test_set"]
