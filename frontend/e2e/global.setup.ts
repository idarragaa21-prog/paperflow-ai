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
  const healthURL = `${apiURL.replace(/\/$/, '')}/health`;
  const devUpScript = path.resolve(repoRoot, 'scripts/dev_up.sh');

  mkdirSync(authDir, { recursive: true });
  mkdirSync(tmpDir, { recursive: true });

  async function isHealthy() {
    try {
      const response = await fetch(healthURL, { method: 'GET' });
      return response.ok;
    } catch {
      return false;
    }
  }

  if (!(await isHealthy())) {
    execFileSync('bash', [devUpScript], {
      cwd: repoRoot,
      stdio: 'inherit',
      env: {
        ...process.env,
        PAPERFLOW_DISABLE_DOTENV: process.env.PAPERFLOW_DISABLE_DOTENV || '1',
        PAPERFLOW_SKIP_GROBID_WAIT: process.env.PAPERFLOW_SKIP_GROBID_WAIT || '1',
      },
    });
  }

  if (!(await isHealthy())) {
    throw new Error(`Playwright setup failed: backend health endpoint is still unavailable at ${healthURL}`);
  }

  execFileSync(
    backendPython,
    [
      seedScript,
      '--output',
      fixturePath,
      '--owner-email',
      process.env.PLAYWRIGHT_E2E_EMAIL || 'rc-owner@paperflow.dev',
      '--owner-password',
      process.env.PLAYWRIGHT_E2E_PASSWORD || 'paperflow-e2e-123',
      '--reviewer-email',
      process.env.PLAYWRIGHT_E2E_REVIEWER_EMAIL || 'rc-reviewer@paperflow.dev',
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

  const reviewerContext = await request.newContext({ baseURL: apiURL });
  const reviewerResponse = await reviewerContext.post('/auth/login', {
    data: { email: fixture.reviewer.email, password: fixture.reviewer.password },
  });
  if (!reviewerResponse.ok()) {
    throw new Error(`Playwright reviewer login failed: ${reviewerResponse.status()} ${await reviewerResponse.text()}`);
  }

  await reviewerContext.storageState({ path: path.resolve(authDir, 'reviewer.json') });
  await reviewerContext.dispose();
}
