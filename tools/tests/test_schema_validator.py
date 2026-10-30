"""The bundled schema validator."""

import unittest

import schema_validator

SCHEMA = {
    "type": "object",
    "required": ["name", "tags"],
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string", "pattern": "^[a-z]+$", "minLength": 2},
        "tags": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "active": {"type": "boolean"},
    },
}


class Validate(unittest.TestCase):
    def test_valid_instance(self):
        instance = {"name": "ab", "tags": ["x"]}
        self.assertEqual(schema_validator.validate(instance, SCHEMA), [])

    def test_missing_required(self):
        errors = schema_validator.validate({"name": "ab"}, SCHEMA)
        self.assertTrue(any("tags" in e for e in errors))

    def test_pattern_enforced(self):
        errors = schema_validator.validate({"name": "AB", "tags": ["x"]}, SCHEMA)
        self.assertTrue(any("pattern" in e for e in errors))

    def test_unexpected_property(self):
        instance = {"name": "ab", "tags": ["x"], "extra": 1}
        errors = schema_validator.validate(instance, SCHEMA)
        self.assertTrue(any("unexpected" in e for e in errors))

    def test_min_items_enforced(self):
        errors = schema_validator.validate({"name": "ab", "tags": []}, SCHEMA)
        self.assertTrue(any("minItems" in e for e in errors))

    def test_boolean_is_not_integer(self):
        schema = {"type": "integer"}
        self.assertNotEqual(schema_validator.validate(True, schema), [])
        self.assertEqual(schema_validator.validate(3, schema), [])

    def test_wrong_type_reports_expected(self):
        errors = schema_validator.validate({"name": "ab", "tags": "x"}, SCHEMA)
        self.assertTrue(any("expected type" in e for e in errors))


class CheckSchema(unittest.TestCase):
    def test_unsupported_keyword_rejected(self):
        self.assertNotEqual(schema_validator.check_schema({"minimum": 1}), [])

    def test_supported_schema_accepted(self):
        self.assertEqual(schema_validator.check_schema(SCHEMA), [])


if __name__ == "__main__":
    unittest.main()
