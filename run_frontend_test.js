const { execSync } = require('child_process');
try {
  execSync('pnpm test SettingsPage', { cwd: 'frontend', stdio: 'inherit' });
} catch (e) {
  process.exit(1);
}
