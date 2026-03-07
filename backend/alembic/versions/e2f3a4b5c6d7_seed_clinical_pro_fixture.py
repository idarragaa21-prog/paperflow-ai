"""seed clinical pro fixture

Revision ID: e2f3a4b5c6d7
Revises: c7f8a9b0d1e2
Create Date: 2026-03-06

"""

from __future__ import annotations

from alembic import op


revision = "e2f3a4b5c6d7"
down_revision = "c7f8a9b0d1e2"
branch_labels = None
depends_on = None


USER_ID = "00000000-0000-0000-0000-000000000111"
SHEET_ID = "1b8cb0e2-35ab-4ace-89fe-be07f7e01849"


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        f"""
        INSERT INTO users (id, email, password_hash, full_name, is_active)
        VALUES ('{USER_ID}', 'paperflow-fixture@example.com', 'fixture', 'PaperFlow Fixture', true)
        ON CONFLICT (email) DO NOTHING;
        """
    )
    statement = """
        INSERT INTO clinical_sheets (
            id,
            project_id,
            user_id,
            topic,
            input_params,
            content_markdown,
            content_json,
            format_version,
            references_json,
            sources_used,
            version,
            is_current,
            llm_model,
            llm_usage
        )
        VALUES (
            '__SHEET_ID__',
            NULL,
            '__USER_ID__',
            'Clinical PRO fixture for validation',
            '{"source":"alembic_seed","scope":"legacy_validation"}'::jsonb,
            'Fixture content for validation.',
            $${
              "title": "Clinical PRO Validation Fixture",
              "sections": [
                {
                  "id": "intro",
                  "title": "Introduction",
                  "content_markdown": "Overview of the evidence base. Fuentes: PMID:12345678 DOI:10.1000/example1"
                },
                {
                  "id": "methods",
                  "title": "Methods",
                  "content_markdown": "Evidence synthesis approach and eligibility framing. Fuentes: PMID:23456789 DOI:10.1000/example2"
                },
                {
                  "id": "gaps",
                  "title": "Evidence Gaps",
                  "content_markdown": "Insufficient evidence for long-term comparative effectiveness in this fixture."
                }
              ],
              "mermaid": [
                {
                  "title": "Evidence flow",
                  "code": "flowchart TD; Search-->Screen; Screen-->Include;"
                }
              ],
              "tables": [
                {
                  "title": "Study characteristics",
                  "columns": ["Study", "Design", "Population"],
                  "rows": [["Alpha 2024", "Cohort", "Adults"], ["Beta 2023", "RCT", "Mixed"]]
                },
                {
                  "title": "Primary outcomes",
                  "columns": ["Outcome", "Direction", "Certainty"],
                  "rows": [["Pain", "Improved", "Moderate"], ["Function", "Improved", "Low"]]
                },
                {
                  "title": "Limitations",
                  "columns": ["Study", "Issue"],
                  "rows": [["Alpha 2024", "Short follow-up"], ["Beta 2023", "Small sample"]]
                }
              ],
              "references_vancouver": [
                "1. Alpha Study. J Clin Res. 2024;10(1):1-10. PMID:12345678.",
                "2. Beta Trial. Evid Med. 2023;9(4):44-52. DOI:10.1000/example2."
              ],
              "evidence_map": [
                {"section_id": "intro", "supports": ["1", "2"]}
              ]
            }$$::jsonb,
            'clinical_pro_v1',
            $$[
              {"pmid":"12345678","doi":"10.1000/example1"},
              {"pmid":"23456789","doi":"10.1000/example2"}
            ]$$::jsonb,
            '{"seeded":true}'::jsonb,
            1,
            true,
            'fixture-model',
            '{"tokens":0}'::jsonb
        )
        ON CONFLICT (id) DO NOTHING;
        """
    bind.exec_driver_sql(statement.replace("__SHEET_ID__", SHEET_ID).replace("__USER_ID__", USER_ID))


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(f"DELETE FROM clinical_sheets WHERE id = '{SHEET_ID}';")
    bind.exec_driver_sql(f"DELETE FROM users WHERE id = '{USER_ID}';")
