#!/usr/bin/env python3
"""Validate YAML or JSON instances against a JSON Schema subset.

Supported keywords: type, enum, required, properties, additionalProperties,
items, minItems, maxItems, minLength, maxLength, pattern. That is enough
for the schemas in schemas/; unsupported keywords are rejected at load
time so schema drift fails loudly instead of passing silently.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common  # noqa: E402

TYPES = {"object", "array", "string", "integer", "number", "boolean", "null"}
KEYWORDS = {
    "type",
    "enum",
    "required",
    "properties",
    "additionalProperties",
    "items",
    "minItems",
    "maxItems",
    "minLength",
    "maxLength",
    "pattern",
    "title",
    "description",
    "$schema",
}


def _type_ok(value, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return value is None


def check_schema(schema, where: str = "$") -> list[str]:
    """Reject schemas that use anything outside the supported subset."""
    errors: list[str] = []
    if not isinstance(schema, dict):
        return [f"{where}: schema fragment must be an object"]
    for key in schema:
        if key not in KEYWORDS:
            errors.append(f"{where}: unsupported keyword {key!r}")
    if "type" in schema and isinstance(schema["type"], str):
        if schema["type"] not in TYPES:
            errors.append(f"{where}: unknown type {schema['type']!r}")
    for name, sub in schema.get("properties", {}).items():
        errors.extend(check_schema(sub, f"{where}.{name}"))
    if "items" in schema:
        errors.extend(check_schema(schema["items"], where + "[]"))
    return errors


def validate(instance, schema, where: str = "$") -> list[str]:
    errors: list[str] = []
    if "type" in schema:
        expected = schema["type"]
        options = expected if isinstance(expected, list) else [expected]
        if not any(_type_ok(instance, opt) for opt in options):
            got = type(instance).__name__
            return [f"{where}: expected type {expected!r}, got {got}"]
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{where}: {instance!r} is not one of {schema['enum']!r}")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{where}: shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{where}: longer than maxLength {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(
                f"{where}: {instance!r} does not match pattern {schema['pattern']!r}"
            )
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{where}: fewer than minItems {schema['minItems']}")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{where}: more than maxItems {schema['maxItems']}")
        if "items" in schema:
            for index, item in enumerate(instance):
                errors.extend(validate(item, schema["items"], f"{where}[{index}]"))
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{where}: missing required property {key!r}")
        for key, sub in schema.get("properties", {}).items():
            if key in instance:
                errors.extend(validate(instance[key], sub, f"{where}.{key}"))
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in schema.get("properties", {}):
                    errors.append(f"{where}: unexpected property {key!r}")
    return errors


def load_instance(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        import yaml

        return yaml.safe_load(text)
    return json.loads(text)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: schema_validator.py SCHEMA INSTANCE", file=sys.stderr)
        return _common.USAGE
    schema_path, instance_path = Path(argv[1]), Path(argv[2])
    try:
        schema = load_instance(schema_path)
        instance = load_instance(instance_path)
    except (OSError, ValueError) as exc:
        print(f"FAIL unable to load: {exc}", file=sys.stderr)
        return _common.USAGE
    problems = check_schema(schema)
    errors = validate(instance, schema) if not problems else []
    for problem in problems:
        print(f"FAIL schema {schema_path}: {problem}")
    for error in errors:
        print(f"FAIL {instance_path}: {error}")
    if problems or errors:
        print(f"{instance_path}: {len(problems) + len(errors)} problem(s)")
        return _common.FINDINGS
    print(f"{instance_path}: ok")
    return _common.OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
