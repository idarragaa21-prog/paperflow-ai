sed -i "s/const inputs = screen.getAllByDisplayValue('');/const inputs = document.querySelectorAll('input[type=\"password\"]');/" frontend/src/test/SettingsPage.test.tsx
