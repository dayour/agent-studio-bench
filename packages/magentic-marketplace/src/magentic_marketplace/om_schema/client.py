"""Python wrapper around om-cli.exe for ObjectModel schema operations.

All methods shell out to the .NET CLI and parse JSON responses. The binary
path is resolved from OM_CLI_PATH env var or defaults to the standard
location inside the agent-studio tools directory.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


_DEFAULT_OM_CLI = r"E:\agent-studio\tools\om-cli\om-cli.exe"


def _om_cli_path() -> str:
    return os.environ.get("OM_CLI_PATH", _DEFAULT_OM_CLI)


def _run(args: list[str], *, timeout: int = 30) -> dict[str, Any]:
    """Execute om-cli.exe with the given arguments and return parsed JSON."""
    cmd = [_om_cli_path()] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"om-cli failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return json.loads(result.stdout)


class OMClient:
    """Stateless wrapper for ObjectModel CLI operations."""

    # ------------------------------------------------------------------
    # Type catalog
    # ------------------------------------------------------------------

    @staticmethod
    def list_types(*, concrete_only: bool = True) -> list[dict[str, Any]]:
        """Return all OM types. Set concrete_only=False for abstract types too."""
        args = ["list"]
        if concrete_only:
            args.append("--concrete-only")
        data = _run(args)
        return data.get("types", [])

    @staticmethod
    def type_count(*, concrete_only: bool = True) -> int:
        data = _run(["list"] + (["--concrete-only"] if concrete_only else []))
        return data.get("totalTypes", 0)

    # ------------------------------------------------------------------
    # Schema inspection
    # ------------------------------------------------------------------

    @staticmethod
    def schema(type_name: str) -> dict[str, Any]:
        """Get full JSON Schema for a named type."""
        return _run(["schema", type_name])

    @staticmethod
    def search(pattern: str) -> list[dict[str, Any]]:
        """Wildcard search across type names and properties."""
        data = _run(["search", pattern])
        return data.get("results", [])

    @staticmethod
    def hierarchy(type_name: str, *, direction: str = "descendants") -> dict[str, Any]:
        """Get inheritance tree for a type."""
        return _run(["hierarchy", type_name, "-d", direction])

    @staticmethod
    def composition(type_name: str, *, depth: int = 2) -> dict[str, Any]:
        """Get property composition tree for a type."""
        return _run(["composition", type_name, "-d", str(depth)])

    @staticmethod
    def examples(type_name: str) -> dict[str, Any]:
        """Get example YAML for a type."""
        return _run(["examples", type_name])

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def validate_file(yaml_path: str | Path) -> dict[str, Any]:
        """Validate a YAML file against the ObjectModel schema.

        Returns dict with keys: valid (bool), diagnosticCount (int),
        diagnostics (list of dicts with Severity, Code, Message, Range).
        """
        return _run(["validate", "-f", str(yaml_path)])

    @staticmethod
    def is_valid(yaml_path: str | Path) -> bool:
        """Convenience: return True if the file passes OM validation."""
        result = OMClient.validate_file(yaml_path)
        return result.get("valid", False)

    # ------------------------------------------------------------------
    # Convenience queries
    # ------------------------------------------------------------------

    @staticmethod
    def eval_types() -> list[dict[str, Any]]:
        """Return all evaluation-related OM types."""
        return OMClient.search("Eval*")

    @staticmethod
    def grader_types() -> list[dict[str, Any]]:
        """Return all grader OM types."""
        return OMClient.search("*Grader*")

    @staticmethod
    def agent_types() -> list[dict[str, Any]]:
        """Return all agent-related OM types."""
        return OMClient.search("*Agent*")
