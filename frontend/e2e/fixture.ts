import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

export type E2EFixture = {
  owner: { id: string; email: string; password: string };
  reviewer: { id: string; email: string; password: string };
  project: { id: string; title: string };
  papers: { count: number; first_paper_id: string };
};

export function loadFixture(): E2EFixture {
  const currentDir = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = path.resolve(currentDir, '..', '..');
  const fixturePath = process.env.PLAYWRIGHT_FIXTURE_PATH || path.resolve(repoRoot, 'tmp', 'internal_rc_fixture.json');
  return JSON.parse(readFileSync(fixturePath, 'utf-8')) as E2EFixture;
}
