import re

with open("backend/tests/test_vnext_core_endpoints.py", "r") as f:
    content = f.read()

import_mock = "from unittest.mock import patch, MagicMock, AsyncMock\n\n"

# Check exact target string we want to replace
target = "    async def test_extraction_matrix_to_meta_run_pipeline(self, db_session: AsyncSession, authed_client: AsyncClient, test_user: User):"

patch_decorator = "    @patch('app.api.meta_runs.run_meta_analysis', new_callable=AsyncMock)\n    async def test_extraction_matrix_to_meta_run_pipeline(self, mock_run, db_session: AsyncSession, authed_client: AsyncClient, test_user: User):"

mock_config = """
        mock_run.return_value = MagicMock(
            status="completed",
            artifacts=[{"id": "a-123", "artifact_type": "effect_table_csv"}, {"id": "b-456", "artifact_type": "script_r"}]
        )
        mock_run.return_value.id = "run-id-789"
"""

# BUT WAIT
# The test expects a run_data with "artifacts" in it and "status": "completed".
# Look at `app.api.meta_runs.run_meta_analysis` ? No, `MetaRun` is serialized in the route.
# Let's see the route.
