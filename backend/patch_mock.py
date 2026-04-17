import re

with open("tests/test_vnext_core_endpoints.py", "r") as f:
    content = f.read()

new_content = content.replace(
    '{"forest": {"svg_b64": "bW9jaw=="}}',
    '{"figure_forest": {"svg_b64": "bW9jaw=="}}'
)

with open("tests/test_vnext_core_endpoints.py", "w") as f:
    f.write(new_content)
