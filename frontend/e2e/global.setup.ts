import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { request } from '@playwright/test';

type Fixture = {
  owner: { id: string; email: string; password: string };
  reviewer: { id: string; email: string; password: string };
  project: { id: string; title: string };
  papers: { count: number; first_paper_id: string };
};

export default async function globalSetup() {
  const currentDir = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = path.resolve(currentDir, '..', '..');
  const authDir = path.resolve(currentDir, '.auth');
  const tmpDir = path.resolve(repoRoot, 'tmp');
  const fixturePath = process.env.PLAYWRIGHT_FIXTURE_PATH || path.resolve(tmpDir, 'internal_rc_fixture.json');
  const backendPython = process.env.BACKEND_PYTHON || path.resolve(repoRoot, 'backend/.venv/bin/python');
  const seedScript = path.resolve(repoRoot, 'backend/scripts/seed_internal_rc_fixture.py');
  const apiURL = process.env.PLAYWRIGHT_API_URL || 'http://127.0.0.1:8000';

  mkdirSync(authDir, { recursive: true });
  mkdirSync(tmpDir, { recursive: true });

  execFileSync(
    backendPython,
    [
      seedScript,
      '--output',
      fixturePath,
      '--owner-email',
      process.env.PLAYWRIGHT_E2E_EMAIL || 'rc-owner@paperflow.local',
      '--owner-password',
      process.env.PLAYWRIGHT_E2E_PASSWORD || 'paperflow-e2e-123',
      '--reviewer-email',
      process.env.PLAYWRIGHT_E2E_REVIEWER_EMAIL || 'rc-reviewer@paperflow.local',
      '--reviewer-password',
      process.env.PLAYWRIGHT_E2E_REVIEWER_PASSWORD || 'paperflow-e2e-123',
    ],
    {
      stdio: 'inherit',
      env: { ...process.env, PAPERFLOW_DISABLE_DOTENV: process.env.PAPERFLOW_DISABLE_DOTENV || '1' },
    },
  );

  const fixture = JSON.parse(readFileSync(fixturePath, 'utf-8')) as Fixture;
  const context = await request.newContext({ baseURL: apiURL });
  const response = await context.post('/auth/login', {
    data: { email: fixture.owner.email, password: fixture.owner.password },
  });
  if (!response.ok()) {
    throw new Error(`Playwright login failed: ${response.status()} ${await response.text()}`);
  }

  await context.storageState({ path: path.resolve(authDir, 'owner.json') });
  await context.dispose();
}
