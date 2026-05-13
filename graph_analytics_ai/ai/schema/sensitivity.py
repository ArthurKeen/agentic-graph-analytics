"""Sensitivity / PII classifier for conceptual schemas (PRD v0.6 / FR-72).

Given a :class:`~graph_analytics_ai.ai.schema.acquire.SchemaAcquisitionBundle`
(or any conceptual_schema dict that follows the same shape), this
module tags every property with a sensitivity level so downstream
consumers — the report generator's masking pass, the audit-log
preview, the sensitivity overlay in Graph Explorer — can treat the
data correctly without each one re-implementing PII detection.

Levels (closed set, ordered by mask priority):

- ``high`` — direct identifiers and regulated identifiers.
  Examples: SSN, EIN, tax ID, credit card, bank account, passport,
  email, phone, date of birth, exact GPS, full name (firstName +
  lastName combined). MUST be masked in shared reports by default.
- ``medium`` — quasi-identifiers and sensitive operational data.
  Examples: IP address, device ID, employee ID, salary, performance
  rating, postal code, timezone, employer-issued URLs. Masking is
  workspace-policy dependent.
- ``low`` — non-sensitive but worth flagging for audit.
  Examples: city, country, role, department name. Usually safe but
  surfaced in the Graph Explorer overlay so the user can confirm.
- ``safe`` — clearly non-sensitive, free for unmasked use.
  Default classification when no rule matches.
- ``unknown`` — analyzer / heuristic could not classify confidently.
  Surfaced in the workbench so the user can resolve manually.

Classification is deterministic (regex + keyword), runs on the
bundle alone (no DB calls, no LLM), and is cheap enough to call
inside :meth:`ProductService.discover_graph_profile`. Each tagged
property carries:

- ``level`` — the closed-set tag above.
- ``confidence`` — float in [0, 1]. Direct-name hits score 0.95;
  fuzzy substring hits score 0.65.
- ``reason`` — short string the UI can show in a tooltip
  ("name matched ssn-style identifier").
- ``rule`` — the rule name that fired (for downstream audit /
  dashboard filtering).

The bundle's analyzer_metadata is *not* mutated by the classifier
(we keep `classify_property_sensitivity` pure). Callers that want
to persist the result merge it back themselves.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, FrozenSet, List, Literal, Optional, Tuple

if TYPE_CHECKING:
    from .acquire import SchemaAcquisitionBundle

logger = logging.getLogger(__name__)

SensitivityLevel = Literal["high", "medium", "low", "safe", "unknown"]


# ---------------------------------------------------------------------------
# Pattern dictionaries
# ---------------------------------------------------------------------------


# Exact-name matches (case-insensitive). Highest-confidence rule.
_HIGH_EXACT: FrozenSet[str] = frozenset(
    {
        "ssn",
        "social_security_number",
        "socialsecuritynumber",
        "ein",
        "tax_id",
        "taxid",
        "vat_number",
        "vatnumber",
        "passport",
        "passport_number",
        "drivers_license",
        "driverslicense",
        "credit_card",
        "creditcard",
        "credit_card_number",
        "creditcardnumber",
        "card_number",
        "cardnumber",
        "iban",
        "swift",
        "bank_account",
        "bankaccount",
        "account_number",
        "routing_number",
        "email",
        "email_address",
        "emailaddress",
        "phone",
        "phone_number",
        "mobile",
        "mobile_number",
        "fax",
        "dob",
        "date_of_birth",
        "dateofbirth",
        "birthdate",
        "birthday",
        "national_id",
        "nationalid",
        "personal_id",
        "medical_record_number",
        "mrn",
        "patient_id",
        "patientid",
        "hipaa_id",
        "gps_lat",
        "gps_lon",
        "latitude",
        "longitude",
        "home_address",
        "homeaddress",
        "street_address",
        "streetaddress",
        "address_line",
        "addressline",
    }
)

# Substring patterns (case-insensitive). Medium confidence.
_HIGH_SUBSTRING: Tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "private_key",
    "privatekey",
    "api_key",
    "apikey",
    "api_token",
    "apitoken",
    "auth_token",
    "authtoken",
    "session_token",
    "sessiontoken",
    "credit",
    "ssn",
    "biometric",
    "fingerprint",
    "iris",
)

_MEDIUM_EXACT: FrozenSet[str] = frozenset(
    {
        "ip",
        "ip_address",
        "ipaddress",
        "device_id",
        "deviceid",
        "user_agent",
        "useragent",
        "fingerprint_id",
        "employee_id",
        "employeeid",
        "user_id",
        "userid",
        "salary",
        "compensation",
        "performance_rating",
        "performancerating",
        "review_score",
        "postal_code",
        "postalcode",
        "zip",
        "zipcode",
        "zip_code",
        "timezone",
        "session_id",
        "sessionid",
        "cookie",
    }
)

_LOW_EXACT: FrozenSet[str] = frozenset(
    {
        "city",
        "state",
        "country",
        "region",
        "department",
        "team",
        "role",
        "title",
        "manager",
    }
)

# Direct name parts (firstName, lastName). When BOTH appear in the
# same entity we promote the entity-level rating to high (joint name
# is a stronger PII signal than any single field), but each field
# individually scores high too because most reporting / masking
# pipelines treat them as PII regardless of the join.
_NAME_FIELDS: FrozenSet[str] = frozenset(
    {
        "first_name",
        "firstname",
        "given_name",
        "givenname",
        "last_name",
        "lastname",
        "family_name",
        "familyname",
        "surname",
        "full_name",
        "fullname",
        "middle_name",
        "middlename",
    }
)

# Compiled regex matchers for "looks like a SSN / EIN / phone / email
# field name". Keeps the substring fallback bounded.
_HIGH_REGEX: Tuple[re.Pattern[str], ...] = (
    re.compile(r"^.*ssn.*$", re.IGNORECASE),
    re.compile(r"^.*tax.?id.*$", re.IGNORECASE),
    re.compile(r"^.*credit.?card.*$", re.IGNORECASE),
    re.compile(r"^.*passport.*$", re.IGNORECASE),
)


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PropertySensitivity:
    """Per-property classification result."""

    entity: str
    property: str
    level: SensitivityLevel
    confidence: float
    reason: str
    rule: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "entity": self.entity,
            "property": self.property,
            "level": self.level,
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
            "rule": self.rule,
        }


@dataclass(frozen=True)
class SensitivityReport:
    """Output of :func:`classify_schema_sensitivity`.

    ``properties`` is the per-(entity, property) tag list.
    ``entity_levels`` is the rolled-up per-entity max level so the UI
    can colour the entity card directly. ``counts`` summarizes how
    many properties landed in each level for the dashboard summary.
    """

    properties: List[PropertySensitivity] = field(default_factory=list)
    entity_levels: Dict[str, SensitivityLevel] = field(default_factory=dict)
    counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "properties": [p.to_dict() for p in self.properties],
            "entity_levels": dict(self.entity_levels),
            "counts": dict(self.counts),
        }


# Internal: ordering used to compute the entity-level rollup.
_LEVEL_ORDER: Dict[SensitivityLevel, int] = {
    "safe": 0,
    "low": 1,
    "unknown": 1,  # treated like low for rollup; surfaces a flag in UI
    "medium": 2,
    "high": 3,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_property_sensitivity(
    name: str, *, entity: str = ""
) -> PropertySensitivity:
    """Classify a single property name. Pure function — no I/O.

    Useful by itself when the caller wants to tag a property surfaced
    outside a conceptual schema (e.g. a BRD field, a report column).
    """

    norm = (name or "").strip().lower().replace("-", "_")

    if not norm:
        return PropertySensitivity(
            entity=entity,
            property=name or "",
            level="unknown",
            confidence=0.0,
            reason="empty property name",
            rule="empty",
        )

    if norm in _HIGH_EXACT:
        return PropertySensitivity(
            entity=entity,
            property=name,
            level="high",
            confidence=0.95,
            reason=f"name '{norm}' matches a regulated-identifier dictionary",
            rule="high_exact",
        )

    if norm in _NAME_FIELDS:
        return PropertySensitivity(
            entity=entity,
            property=name,
            level="high",
            confidence=0.85,
            reason=f"name '{norm}' is a direct-name field",
            rule="name_field",
        )

    for pattern in _HIGH_REGEX:
        if pattern.match(norm):
            return PropertySensitivity(
                entity=entity,
                property=name,
                level="high",
                confidence=0.80,
                reason=f"name '{norm}' matches PII regex {pattern.pattern!r}",
                rule="high_regex",
            )

    for substring in _HIGH_SUBSTRING:
        if substring in norm:
            return PropertySensitivity(
                entity=entity,
                property=name,
                level="high",
                confidence=0.65,
                reason=f"name '{norm}' contains sensitive substring '{substring}'",
                rule="high_substring",
            )

    if norm in _MEDIUM_EXACT:
        return PropertySensitivity(
            entity=entity,
            property=name,
            level="medium",
            confidence=0.85,
            reason=f"name '{norm}' is a quasi-identifier",
            rule="medium_exact",
        )

    if norm in _LOW_EXACT:
        return PropertySensitivity(
            entity=entity,
            property=name,
            level="low",
            confidence=0.70,
            reason=f"name '{norm}' is a low-sensitivity dimension",
            rule="low_exact",
        )

    return PropertySensitivity(
        entity=entity,
        property=name,
        level="safe",
        confidence=0.50,
        reason="no sensitivity rule matched",
        rule="default_safe",
    )


def classify_schema_sensitivity(
    bundle: "SchemaAcquisitionBundle",
) -> SensitivityReport:
    """Classify every property in the bundle's conceptual schema."""

    return _classify_conceptual_schema(bundle.conceptual_schema)


def classify_conceptual_schema(
    conceptual_schema: Dict[str, object],
) -> SensitivityReport:
    """Standalone entrypoint used when the caller has just a dict.

    Same logic as :func:`classify_schema_sensitivity`. Useful for the
    PATCH endpoint that re-runs sensitivity scoring after the user
    edits a conceptual schema by hand.
    """

    return _classify_conceptual_schema(conceptual_schema)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _classify_conceptual_schema(
    conceptual_schema: Dict[str, object],
) -> SensitivityReport:
    properties: List[PropertySensitivity] = []
    entity_levels: Dict[str, SensitivityLevel] = {}
    counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0, "safe": 0, "unknown": 0}

    entities = conceptual_schema.get("entities") or []
    if not isinstance(entities, list):
        return SensitivityReport()

    for entity in entities:
        if not isinstance(entity, dict):
            continue
        entity_name = entity.get("name") or "Unnamed"
        entity_props = entity.get("properties") or []
        if not isinstance(entity_props, list):
            continue

        for prop in entity_props:
            prop_name = _extract_property_name(prop)
            if not prop_name:
                continue
            tag = classify_property_sensitivity(prop_name, entity=entity_name)
            properties.append(tag)
            counts[tag.level] = counts.get(tag.level, 0) + 1

            current = entity_levels.get(entity_name, "safe")
            if _LEVEL_ORDER[tag.level] > _LEVEL_ORDER[current]:
                entity_levels[entity_name] = tag.level

        # Joint-name promotion: when both first_name + last_name appear
        # on the same entity we elevate the entity-level rollup to high
        # even if they were already there. Cheap idempotent boost.
        prop_names_norm = {
            _extract_property_name(p, normalize=True) or "" for p in entity_props
        }
        if {"first_name", "firstname", "given_name", "givenname"}.intersection(
            prop_names_norm
        ) and {"last_name", "lastname", "family_name", "familyname", "surname"}.intersection(
            prop_names_norm
        ):
            entity_levels[entity_name] = "high"

    return SensitivityReport(
        properties=properties,
        entity_levels=entity_levels,
        counts=counts,
    )


def _extract_property_name(prop: object, *, normalize: bool = False) -> Optional[str]:
    """Pull the property name from a conceptual-schema entry.

    Schemas in the wild use either bare strings or
    ``{"name": "...", ...}`` dicts. Be permissive.
    """
    if isinstance(prop, str):
        name = prop
    elif isinstance(prop, dict):
        candidate = prop.get("name")
        if not isinstance(candidate, str):
            return None
        name = candidate
    else:
        return None

    if normalize:
        return (name or "").strip().lower().replace("-", "_") or None
    return name or None


__all__ = [
    "PropertySensitivity",
    "SensitivityLevel",
    "SensitivityReport",
    "classify_conceptual_schema",
    "classify_property_sensitivity",
    "classify_schema_sensitivity",
]
