"""
Industry vertical JSON schema for custom verticals.

This schema defines the structure for auto-generated custom industry verticals
that are stored in client projects.
"""

INDUSTRY_VERTICAL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Custom Industry Vertical",
    "description": "Schema for custom industry-specific analysis configurations",
    "type": "object",
    "required": ["metadata", "domain_context", "analysis_prompt"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["name", "display_name", "version", "generated_at"],
            "properties": {
                "name": {
                    "type": "string",
                    "pattern": "^[a-z][a-z0-9_]*$",
                    "description": "Machine-readable identifier (snake_case)",
                    "examples": ["supply_chain", "healthcare", "cybersecurity"],
                },
                "display_name": {
                    "type": "string",
                    "description": "Human-readable name",
                    "examples": ["Supply Chain & Logistics", "Healthcare Networks"],
                },
                "version": {
                    "type": "string",
                    "pattern": "^\\d+\\.\\d+$",
                    "description": "Version number (major.minor)",
                    "examples": ["1.0", "2.1"],
                },
                "generated_at": {
                    "type": "string",
                    "format": "date-time",
                    "description": "ISO 8601 timestamp of generation",
                },
                "generated_by": {
                    "type": "string",
                    "description": "Agent or tool that generated this vertical",
                    "default": "IndustryVerticalAgent",
                },
                "source_documents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Paths to source documents used for generation",
                    "examples": [
                        ["docs/business_requirements.md", "docs/domain_description.md"]
                    ],
                },
            },
        },
        "domain_context": {
            "type": "object",
            "required": ["industry", "business_focus", "key_entities"],
            "properties": {
                "industry": {
                    "type": "string",
                    "description": "Industry or domain name",
                },
                "business_focus": {
                    "type": "string",
                    "description": "Primary business goal or focus area",
                },
                "key_entities": {
                    "type": "object",
                    "required": ["nodes", "edges"],
                    "properties": {
                        "nodes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Node types with descriptions",
                        },
                        "edges": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Edge types with descriptions",
                        },
                    },
                },
                "key_metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Important metrics for this domain",
                },
                "terminology": {
                    "type": "object",
                    "properties": {
                        "currency": {
                            "type": "string",
                            "description": "Primary currency",
                            "examples": ["USD", "EUR", "₹ Crores"],
                        },
                        "units": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Common measurement units",
                        },
                        "regulations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Relevant regulations and compliance",
                        },
                        "thresholds": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Domain-specific thresholds",
                        },
                    },
                },
            },
        },
        "analysis_prompt": {
            "type": "string",
            "minLength": 100,
            "maxLength": 50000,
            "description": "LLM prompt for industry-specific analysis",
        },
        "pattern_definitions": {
            "type": "object",
            "description": "Pattern templates for graph algorithms",
            "properties": {
                "wcc": {"type": "array", "items": {"$ref": "#/definitions/pattern"}},
                "pagerank": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/pattern"},
                },
                "cycles": {"type": "array", "items": {"$ref": "#/definitions/pattern"}},
            },
        },
        "user_validated": {
            "type": "boolean",
            "description": "Whether user has reviewed and approved this vertical",
            "default": False,
        },
        "user_notes": {"type": "string", "description": "User's notes and refinements"},
    },
    "definitions": {
        "pattern": {
            "type": "object",
            "required": ["name", "description", "risk_level"],
            "properties": {
                "name": {"type": "string", "description": "Pattern identifier"},
                "description": {
                    "type": "string",
                    "description": "What this pattern indicates",
                },
                "indicators": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Signals that indicate this pattern",
                },
                "risk_level": {
                    "type": "string",
                    "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
                    "description": "Severity of this pattern",
                },
                "example": {
                    "type": "string",
                    "description": "Example of how this pattern manifests",
                },
                "business_impact": {
                    "type": "string",
                    "description": "What actions to take when detected",
                },
            },
        }
    },
}


def validate_vertical_schema(vertical_data: dict) -> tuple[bool, list[str]]:
    """
    Validate a custom vertical against the schema.

    Args:
        vertical_data: Dictionary containing the vertical configuration

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    try:
        import jsonschema

        jsonschema.validate(instance=vertical_data, schema=INDUSTRY_VERTICAL_SCHEMA)
        return True, []
    except jsonschema.ValidationError as e:
        return False, [str(e)]
    except jsonschema.SchemaError as e:
        return False, [f"Schema error: {str(e)}"]
    except Exception as e:
        return False, [f"Validation error: {str(e)}"]


def get_example_vertical() -> dict:
    """Return an example custom vertical for reference."""
    return {
        "metadata": {
            "name": "supply_chain",
            "display_name": "Supply Chain & Logistics",
            "version": "1.0",
            "generated_at": "2026-02-10T10:30:00Z",
            "generated_by": "IndustryVerticalAgent",
            "source_documents": [
                "docs/business_requirements.md",
                "docs/domain_description.md",
            ],
        },
        "domain_context": {
            "industry": "Supply Chain & Logistics",
            "business_focus": "Optimize supply chain resilience, detect bottlenecks, predict disruptions",
            "key_entities": {
                "nodes": [
                    "Supplier: Manufacturing suppliers and vendors",
                    "Warehouse: Distribution centers and storage facilities",
                    "Product: SKUs and inventory items",
                    "ShipmentRoute: Transportation corridors",
                    "Port: Import/export facilities",
                ],
                "edges": [
                    "suppliesTo: Supply relationships between entities",
                    "shipsVia: Transportation routes",
                    "stores: Inventory storage relationships",
                    "dependsOn: Supply dependencies",
                ],
            },
            "key_metrics": [
                "Lead time variance",
                "Inventory turnover",
                "Supply chain resilience score",
                "Bottleneck detection",
                "Geographic concentration risk",
            ],
            "terminology": {
                "currency": "USD",
                "units": ["units", "pallets", "containers", "days"],
                "regulations": ["Import/Export regulations", "Customs compliance"],
                "thresholds": {
                    "critical_inventory": "< 7 days",
                    "single_supplier_risk": "> 30% of volume",
                },
            },
        },
        "analysis_prompt": "You are analyzing a supply chain and logistics graph for optimization and risk detection.\n\n## Domain Context\n\n**Nodes:** Supplier (vendors), Warehouse (distribution centers), Product (SKUs), ShipmentRoute (corridors), Port (import/export)\n\n**Edges:** suppliesTo (supply relationships), shipsVia (routes), stores (inventory), dependsOn (dependencies)\n\n## Key Metrics\n\n1. Lead time variance (delivery time consistency)\n2. Inventory turnover (efficiency)\n3. Geographic concentration (risk exposure)\n4. Single points of failure (critical dependencies)\n\nGenerate insights focused on supply chain resilience, bottleneck detection, and risk mitigation.",
        "pattern_definitions": {
            "wcc": [
                {
                    "name": "single_point_of_failure",
                    "description": "Critical supplier with no alternatives",
                    "indicators": [
                        "Single supplier for key component",
                        "No backup in same region",
                    ],
                    "risk_level": "CRITICAL",
                    "example": "Supplier S-123 is sole provider of Component X (40% of product line)",
                    "business_impact": "IMMEDIATE: Identify backup suppliers. Add to risk register.",
                }
            ]
        },
        "user_validated": False,
        "user_notes": "",
    }
