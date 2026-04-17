import re

with open("tests/test_vnext_core_endpoints.py", "r") as f:
    content = f.read()

new_content = content.replace(
    'assert run_data["status"] == "completed"',
    'print(run_data)\n        assert run_data["status"] == "completed"'
)

with open("tests/test_vnext_core_endpoints.py", "w") as f:
    f.write(new_content)
