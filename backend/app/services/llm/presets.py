from __future__ import annotations

from typing import Any


PIPELINE_PRESETS: dict[str, dict[str, Any]] = {
    "ultrafast": {
        "name": "Ultra Rápido",
        "description": "~2 min, calidad 88+, ideal para consulta rápida",
        "tier_required": "free",
        "free_only": True,
        "min_quality": 80,
        "prefer_speed": True,
        "max_tokens_content": 4096,
        "skip_validation_if_fast": True,
        "estimated_time_minutes": 2,
        "estimated_quality": 88,
    },
    "premium_free": {
        "name": "Premium Gratis",
        "description": "~5 min, calidad 95+, pipeline completo con validación",
        "tier_required": "free",
        "free_only": True,
        "min_quality": 88,
        "prefer_speed": False,
        "max_tokens_content": 8192,
        "skip_validation_if_fast": False,
        "estimated_time_minutes": 5,
        "estimated_quality": 95,
    },
    "pro": {
        "name": "Pro",
        "description": "Modelos premium para contenido + validación, calidad 97+",
        "tier_required": "pro",
        "free_only": False,
        "min_quality": 92,
        "prefer_speed": False,
        "max_tokens_content": 16384,
        "skip_validation_if_fast": False,
        "model_overrides": {
            "content": "anthropic/claude-sonnet-4-5",
            "validate": "anthropic/claude-sonnet-4-5",
        },
        "estimated_time_minutes": 8,
        "estimated_quality": 97,
        "cost_per_sheet_usd": 0.50,
    },
    "enterprise": {
        "name": "Enterprise",
        "description": "Máximo detalle; modelos premium en todo, calidad 99",
        "tier_required": "enterprise",
        "free_only": False,
        "min_quality": 95,
        "prefer_speed": False,
        "max_tokens_content": 32768,
        "skip_validation_if_fast": False,
        "model_overrides": {
            "extract": "anthropic/claude-sonnet-4-5",
            "content": "anthropic/claude-opus-4-5",
            "validate": "anthropic/claude-opus-4-5",
            "polish": "anthropic/claude-sonnet-4-5",
        },
        "estimated_time_minutes": 12,
        "estimated_quality": 99,
        "cost_per_sheet_usd": 2.00,
    },
}


USER_TIERS: dict[str, dict[str, Any]] = {
    "free": {
        "name": "Free",
        "sheets_per_month": 10,
        "presets_available": ["ultrafast", "premium_free"],
        "max_sources_per_sheet": 20,
        "export_formats": ["pdf", "json"],
        "features": ["basic_sheets", "mermaid", "tables", "export_pdf"],
        "price_usd_monthly": 0,
    },
    "pro": {
        "name": "Pro",
        "sheets_per_month": 100,
        "presets_available": ["ultrafast", "premium_free", "pro"],
        "max_sources_per_sheet": 50,
        "export_formats": ["pdf", "json", "pptx", "docx"],
        "features": [
            "basic_sheets",
            "mermaid",
            "tables",
            "export_pdf",
            "export_pptx",
            "export_docx",
            "batch_generation",
            "custom_templates",
            "priority_queue",
            "api_access",
            "collaboration",
            "version_history",
        ],
        "price_usd_monthly": 29,
    },
    "enterprise": {
        "name": "Enterprise",
        "sheets_per_month": -1,
        "presets_available": ["ultrafast", "premium_free", "pro", "enterprise"],
        "max_sources_per_sheet": 200,
        "export_formats": ["pdf", "json", "pptx", "docx", "latex"],
        "features": [
            "basic_sheets",
            "mermaid",
            "tables",
            "export_pdf",
            "export_pptx",
            "export_docx",
            "batch_generation",
            "custom_templates",
            "priority_queue",
            "api_access",
            "collaboration",
            "version_history",
            "white_label",
            "sso",
            "audit_log",
            "dedicated_support",
            "custom_models",
            "on_premise",
            "hipaa_compliance",
        ],
        "price_usd_monthly": 199,
    },
}


def get_preset(preset: str) -> dict[str, Any]:
    if preset not in PIPELINE_PRESETS:
        raise KeyError(f"Unknown preset: {preset}")
    return PIPELINE_PRESETS[preset]


def get_tier(tier: str) -> dict[str, Any]:
    if tier not in USER_TIERS:
        raise KeyError(f"Unknown tier: {tier}")
    return USER_TIERS[tier]
