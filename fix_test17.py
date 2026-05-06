import re

with open("backend/tests/test_vnext_core_endpoints.py", "r") as f:
    content = f.read()

import_mock = "from unittest.mock import patch, MagicMock, AsyncMock\n\n"

# Remove from beginning and insert after future imports
if "from __future__ import annotations" in content:
    content = content.replace("from __future__ import annotations", "from __future__ import annotations\n" + import_mock)
    content = content.replace(import_mock, "", 1) # remove the one added at the beginning

with open("backend/tests/test_vnext_core_endpoints.py", "w") as f:
    f.write(content)
