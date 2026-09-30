#!/usr/bin/env python3
"""Audit helper: check v0.7.1 records against the shipped v0.7 schema.

Usage:
  python3 check_v071_current_schema_mismatch.py /path/to/outputs/proofnet_v071_boundary_lens
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError as exc:
    raise SystemExit("Install jsonschema first: pip install jsonschema") from exc


def read_jsonl(path: Path):
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            yield line_no, json.loads(line)


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    schema_path = root / "schemas" / "proofnet_lens_trace_step_schema_v0_7.json"
    trace_path = root / "data" / "actual_lean_boundary_lens_trace_steps.jsonl"
    failure_path = root / "data" / "actual_lean_failure_branches.jsonl"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for kind, path in [("trace", trace_path), ("failure", failure_path)]:
        for line_no, rec in read_jsonl(path):
            rec_errors = sorted(validator.iter_errors(rec), key=lambda e: list(e.path))
            if rec_errors:
                errors.append({
                    "kind": kind,
                    "line": line_no,
                    "schema_version": rec.get("schema_version"),
                    "record_type": rec.get("record_type"),
                    "first_error": rec_errors[0].message,
                })
    print(json.dumps({
        "schema": str(schema_path),
        "trace_path": str(trace_path),
        "failure_path": str(failure_path),
        "num_errors": len(errors),
        "examples": errors[:20],
    }, indent=2, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
