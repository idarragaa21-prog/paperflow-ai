const fs = require('fs');
const filepath = "frontend/src/test/SettingsPage.test.tsx";
let content = fs.readFileSync(filepath, "utf-8");

// Memory states: In frontend Vitest tests, avoid selecting form inputs using fragile index-based queries like screen.getAllByDisplayValue('')

content = content.replace(
    "const inputs = screen.getAllByDisplayValue('');\n    await userEvent.type(inputs[0], 'current-password');\n    await userEvent.type(inputs[1], 'new-password');\n    await userEvent.type(inputs[2], 'different-password');",
    "const inputs = document.querySelectorAll('input[type=\"password\"]');\n    await userEvent.type(inputs[0], 'current-password');\n    await userEvent.type(inputs[1], 'new-password');\n    await userEvent.type(inputs[2], 'different-password');"
);

fs.writeFileSync(filepath, content);
