import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync } from 'node:fs';
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
  const ownerAuthPath = path.resolve(authDir, 'owner.json');
  const reviewerAuthPath = path.resolve(authDir, 'reviewer.json');

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
      env: { ...process.env },
    },
  );

  const fixture = JSON.parse(readFileSync(fixturePath, 'utf-8')) as Fixture;

  async function authStateStillWorks(storagePath: string) {
    if (!existsSync(storagePath)) return false;
    const ctx = await request.newContext({ baseURL: apiURL, storageState: storagePath });
    try {
      const response = await ctx.get('/auth/me');
      return response.ok();
    } finally {
      await ctx.dispose();
    }
  }

  async function loginAndPersist(storagePath: string, email: string, password: string, label: string) {
    const ctx = await request.newContext({ baseURL: apiURL });
    try {
      const response = await ctx.post('/auth/login', {
        data: { email, password },
      });
      if (!response.ok()) {
        throw new Error(`Playwright ${label} login failed: ${response.status()} ${await response.text()}`);
      }
      await ctx.storageState({ path: storagePath });
    } finally {
      await ctx.dispose();
    }
  }

  if (!(await authStateStillWorks(ownerAuthPath))) {
    await loginAndPersist(ownerAuthPath, fixture.owner.email, fixture.owner.password, 'owner');
  }

  if (!(await authStateStillWorks(reviewerAuthPath))) {
    await loginAndPersist(reviewerAuthPath, fixture.reviewer.email, fixture.reviewer.password, 'reviewer');
  }
}
