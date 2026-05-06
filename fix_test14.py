import re

with open("backend/tests/test_vnext_core_endpoints.py", "r") as f:
    content = f.read()

import_mock = "from unittest.mock import patch, MagicMock, AsyncMock\n\n"

# Only replace exactly the def block once and properly.
target = "    async def test_extraction_matrix_to_meta_run_pipeline(self, db_session: AsyncSession, authed_client: AsyncClient, test_user: User):"

patch_decorator = "    @patch('app.services.meta_runs_service.httpx.AsyncClient.post', new_callable=AsyncMock)\n    async def test_extraction_matrix_to_meta_run_pipeline(self, mock_post, db_session: AsyncSession, authed_client: AsyncClient, test_user: User):"

mock_config = """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "summary": {"test": "summary"},
            "warnings": [],
            "script": "print('hello')",
            "engine_version": "1.0",
        }
        mock_post.return_value = mock_response
"""

new_content = content.replace(target, patch_decorator + mock_config)

if "from unittest.mock" not in new_content:
    new_content = import_mock + new_content

with open("backend/tests/test_vnext_core_endpoints.py", "w") as f:
    f.write(new_content)
