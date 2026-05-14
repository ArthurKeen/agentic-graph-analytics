"""Unit tests for graph_analytics_ai.ai.schema.sensitivity (PRD v0.6 / FR-72)."""

from __future__ import annotations

from typing import Any, Dict

import pytest

from graph_analytics_ai.ai.schema.acquire import SchemaAcquisitionBundle
from graph_analytics_ai.ai.schema.sensitivity import (
    PropertySensitivity,
    SensitivityReport,
    classify_conceptual_schema,
    classify_property_sensitivity,
    classify_schema_sensitivity,
)

# ---------------------------------------------------------------------------
# classify_property_sensitivity
# ---------------------------------------------------------------------------


class TestClassifyPropertySensitivityHigh:
    """Direct-identifier matches must be tagged high with high confidence."""

    @pytest.mark.parametrize(
        "name",
        [
            "ssn",
            "SSN",
            "social_security_number",
            "ein",
            "credit_card",
            "creditCardNumber".lower(),
            "iban",
            "passport",
            "passport_number",
            "email",
            "phone",
            "date_of_birth",
            "national_id",
            "patient_id",
            "home_address",
        ],
    )
    def test_high_exact_dictionary(self, name: str) -> None:
        result = classify_property_sensitivity(name)
        assert result.level == "high"
        assert result.confidence >= 0.9
        assert result.rule == "high_exact"

    @pytest.mark.parametrize("name", ["password", "secret", "api_token", "auth_token"])
    def test_high_substring(self, name: str) -> None:
        result = classify_property_sensitivity(name)
        assert result.level == "high"
        assert result.rule in {"high_substring", "high_exact"}

    @pytest.mark.parametrize(
        "name",
        ["customer_ssn", "employee_tax_id", "user_passport_number"],
    )
    def test_high_regex(self, name: str) -> None:
        result = classify_property_sensitivity(name)
        assert result.level == "high"

    @pytest.mark.parametrize(
        "name", ["first_name", "lastName".lower(), "given_name", "surname"]
    )
    def test_name_fields(self, name: str) -> None:
        result = classify_property_sensitivity(name)
        assert result.level == "high"
        assert result.rule == "name_field"


class TestClassifyPropertySensitivityMedium:
    @pytest.mark.parametrize(
        "name", ["ip_address", "device_id", "salary", "postal_code", "zip_code"]
    )
    def test_medium_exact(self, name: str) -> None:
        result = classify_property_sensitivity(name)
        assert result.level == "medium"
        assert result.rule == "medium_exact"


class TestClassifyPropertySensitivityLow:
    @pytest.mark.parametrize("name", ["city", "country", "department", "role", "title"])
    def test_low_exact(self, name: str) -> None:
        result = classify_property_sensitivity(name)
        assert result.level == "low"
        assert result.rule == "low_exact"


class TestClassifyPropertySensitivityFallbacks:
    def test_unknown_property_is_safe(self) -> None:
        result = classify_property_sensitivity("project_health_score")
        assert result.level == "safe"
        assert result.rule == "default_safe"

    def test_empty_property_returns_unknown(self) -> None:
        result = classify_property_sensitivity("")
        assert result.level == "unknown"
        assert result.rule == "empty"

    def test_dash_normalization(self) -> None:
        # Dashes normalize to underscores so kebab-case keys are matched too.
        result = classify_property_sensitivity("first-name")
        assert result.level == "high"
        assert result.rule == "name_field"

    def test_carries_entity_context(self) -> None:
        result = classify_property_sensitivity("email", entity="Person")
        assert result.entity == "Person"


# ---------------------------------------------------------------------------
# classify_conceptual_schema / classify_schema_sensitivity
# ---------------------------------------------------------------------------


def _conceptual_schema() -> Dict[str, Any]:
    """Synthetic conceptual schema with a mix of sensitivities."""
    return {
        "entities": [
            {
                "name": "Person",
                "properties": [
                    {"name": "first_name"},
                    {"name": "last_name"},
                    {"name": "email"},
                    {"name": "city"},
                    {"name": "favorite_color"},
                ],
            },
            {
                "name": "Company",
                "properties": [
                    "name",
                    {"name": "ein"},
                    {"name": "country"},
                    {"name": "industry"},
                ],
            },
            {
                "name": "Device",
                "properties": [{"name": "ip_address"}, {"name": "model"}],
            },
        ],
        "relationships": [],
    }


def _bundle(conceptual: Dict[str, Any]) -> SchemaAcquisitionBundle:
    return SchemaAcquisitionBundle(
        schema_kind="lpg",
        conceptual_schema=conceptual,
        physical_mapping={"entities": [], "relationships": []},
        analyzer_metadata={"source": "heuristic"},
        shape_fingerprint="shape",
        full_fingerprint="full",
        database="db",
        graph_name="g",
    )


class TestClassifyConceptualSchema:
    def test_returns_property_tags_for_every_named_property(self) -> None:
        report = classify_conceptual_schema(_conceptual_schema())
        # 5 (Person) + 4 (Company) + 2 (Device) = 11
        assert len(report.properties) == 11

    def test_entity_levels_rolled_up_to_max(self) -> None:
        report = classify_conceptual_schema(_conceptual_schema())
        assert report.entity_levels["Person"] == "high"
        assert report.entity_levels["Company"] == "high"  # ein
        assert report.entity_levels["Device"] == "medium"  # ip_address

    def test_first_last_name_combo_promotes_entity_to_high(self) -> None:
        # Each name field is high already — the combo rule keeps it
        # high even when other properties are added that aren't.
        report = classify_conceptual_schema(_conceptual_schema())
        assert report.entity_levels["Person"] == "high"

    def test_counts_are_summed(self) -> None:
        report = classify_conceptual_schema(_conceptual_schema())
        # high: first_name, last_name, email, ein
        # medium: ip_address
        # low: city, country
        # safe: favorite_color, name, industry, model
        assert report.counts["high"] == 4
        assert report.counts["medium"] == 1
        assert report.counts["low"] == 2
        assert report.counts["safe"] == 4

    def test_to_dict_round_trip(self) -> None:
        report = classify_conceptual_schema(_conceptual_schema())
        as_dict = report.to_dict()
        assert set(as_dict.keys()) == {"properties", "entity_levels", "counts"}
        assert isinstance(as_dict["properties"], list)
        assert isinstance(as_dict["entity_levels"], dict)
        assert isinstance(as_dict["counts"], dict)
        # property entries are JSON-friendly
        first = as_dict["properties"][0]
        for key in ("entity", "property", "level", "confidence", "reason", "rule"):
            assert key in first

    def test_empty_or_malformed_schema_returns_empty_report(self) -> None:
        assert classify_conceptual_schema({}).properties == []
        assert classify_conceptual_schema({"entities": "nope"}).properties == []
        assert (
            classify_conceptual_schema({"entities": [{"name": "X"}]}).properties == []
        )

    def test_handles_missing_property_name(self) -> None:
        schema = {
            "entities": [
                {
                    "name": "Person",
                    "properties": [
                        {"description": "no name field"},
                        42,
                        {"name": "email"},
                    ],
                }
            ],
            "relationships": [],
        }
        report = classify_conceptual_schema(schema)
        assert len(report.properties) == 1
        assert report.properties[0].property == "email"

    def test_classify_schema_sensitivity_alias(self) -> None:
        bundle = _bundle(_conceptual_schema())
        from_alias = classify_schema_sensitivity(bundle)
        from_direct = classify_conceptual_schema(bundle.conceptual_schema)
        assert from_alias.to_dict() == from_direct.to_dict()


class TestPropertySensitivityModel:
    def test_to_dict_rounds_confidence(self) -> None:
        sensitivity = PropertySensitivity(
            entity="Person",
            property="email",
            level="high",
            confidence=0.954321,
            reason="r",
            rule="high_exact",
        )
        assert sensitivity.to_dict()["confidence"] == 0.954

    def test_report_to_dict_returns_copies(self) -> None:
        report = SensitivityReport(
            properties=[],
            entity_levels={"Person": "high"},
            counts={"high": 1, "safe": 0},
        )
        as_dict = report.to_dict()
        as_dict["entity_levels"]["Person"] = "safe"
        assert report.entity_levels["Person"] == "high"
