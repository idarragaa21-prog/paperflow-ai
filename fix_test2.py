import re

with open("backend/tests/test_vnext_core_endpoints.py", "r") as f:
    content = f.read()

# Memory: The backend test suite has a known, pre-existing assertion failure in `tests/test_vnext_core_endpoints.py::TestVNextCoreFlow::test_extraction_matrix_to_meta_run_pipeline`. Do not explicitly bypass this with `@pytest.mark.skip` if the test is unrelated to your current PR's scope, as code reviewers will reject it for masking failures out-of-scope.

# BUT wait, the instructions are explicitly asking to FIX the CI failure this time.
# "Your goal now is to analyze the provided check run details... and make a fix."
# If I don't fix it, CI will keep failing. However, the memory says "Do not explicitly bypass this with @pytest.mark.skip if the test is unrelated to your current PR's scope".
# Is there a real fix I can do instead of a skip?
# Let's inspect the R_ENGINE dummy or why the run_data status is "failed" instead of "completed".
