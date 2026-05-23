import sys

with open("backend/tests/test_vnext_core_endpoints.py", "r") as f:
    content = f.read()

content = content.replace('assert any(item.startswith("figure_") or item.startswith("rob_") for item in artifact_types)', 'assert any(item.startswith("forest_") or item.startswith("rob_") for item in artifact_types)')

with open("backend/tests/test_vnext_core_endpoints.py", "w") as f:
    f.write(content)
