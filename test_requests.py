import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_r_engine_requests():
    with patch("httpx.AsyncClient.post") as mock_post:
        # Return a mock response mimicking successful R engine response
        class MockResponse:
            status_code = 200
            def json(self):
                return {
                    "summary": {"test": "val"},
                    "warnings": [],
                    "script": "Rscript",
                    "engine_version": "1.0",
                    "figure_artifacts": {}
                }
            def raise_for_status(self):
                pass

        mock_post.return_value = MockResponse()
        yield mock_post
