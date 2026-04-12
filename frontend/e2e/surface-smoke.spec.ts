import { expect, test } from '@playwright/test';
import { dismissTourIfPresent } from './helpers';
import { loadFixture } from './fixture';

test('vnext project workflow pages load without legacy surface', async ({ page }) => {
  const fixture = loadFixture();
  const base = `/projects/${fixture.project.id}`;

  await page.goto(`${base}/research`);
  await dismissTourIfPresent(page);
  await expect(page.getByRole('heading', { name: /research search/i })).toBeVisible();

  await page.goto(`${base}/library`);
  await expect(page.getByRole('heading', { name: /^library$/i })).toBeVisible();

  await page.goto(`${base}/reader`);
  await expect(page.getByRole('heading', { name: /read with ai/i })).toBeVisible();

  await page.goto(`${base}/extraction`);
  await expect(page.getByRole('heading', { name: /convert processed papers/i })).toBeVisible();

  await page.goto(`${base}/matrix`);
  await expect(page.getByRole('heading', { name: /master extraction matrix/i })).toBeVisible();

  await page.goto(`${base}/meta-runs`);
  await expect(page.getByRole('heading', { name: /meta runs/i })).toBeVisible();

  await page.goto(`${base}/artifacts`);
  await expect(page.getByRole('heading', { name: /^artifacts$/i })).toBeVisible();

  await page.goto(`${base}/writing`);
  await expect(page.getByRole('heading', { name: /writing assistant/i })).toBeVisible();

  await page.goto(`${base}/clinical-consults`);
  await expect(page.getByRole('heading', { name: /clinical consults/i })).toBeVisible();
});

test('clinical consults v2 create a grounded quick-answer record', async ({ page }) => {
  const fixture = loadFixture();
  let consults: any[] = [];

  await page.route('**/projects', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: fixture.project.id,
          title: fixture.project.title,
          clinical_area: fixture.project.clinical_area || null,
          archived: false,
        },
      ]),
    });
  });

  await page.route('**/clinical/consults*', async (route, request) => {
    if (request.method() !== 'GET') {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(consults),
    });
  });

  await page.route('**/clinical/consults', async (route, request) => {
    if (request.method() !== 'POST') {
      await route.continue();
      return;
    }
    const payload = request.postDataJSON() as Record<string, any>;
    const created = {
      id: 'consult-smoke-1',
      project_id: fixture.project.id,
      question: String(payload.question || ''),
      mode: payload.mode || 'standard',
      status: 'completed',
      answer_markdown: 'Use anticoagulation according to bleeding risk and guideline class.',
      uncertainty_text: 'Moderate certainty due to heterogeneity.',
      limitations_text: 'Small sample size in subgroup studies.',
      used_project_library: true,
      used_pubmed: true,
      created_at: new Date().toISOString(),
      sources: [
        {
          id: 'src-1',
          source_kind: 'project_paper',
          title: 'Example RCT',
          pmid: '12345678',
          doi: null,
          year: 2025,
          excerpt: 'Primary endpoint favored intervention.',
          confidence: 0.82,
        },
      ],
      claims: [
        {
          id: 'claim-1',
          claim_text: 'Intervention reduces recurrence risk.',
          confidence: 0.8,
          support_level: 'moderate',
        },
      ],
    };
    consults = [created];
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(created),
    });
  });

  await page.goto(`/projects/${fixture.project.id}/clinical-consults`);
  await dismissTourIfPresent(page);
  await expect(page.getByRole('heading', { name: /clinical consults/i })).toBeVisible();

  await page.getByPlaceholder(/should aspirin be used/i).fill('Should NOACs be preferred over warfarin in AF with high bleeding risk?');
  await page.getByRole('button', { name: /generate consult/i }).click();

  await expect(page.getByText(/moderate certainty due to heterogeneity/i)).toBeVisible();
  await expect(page.getByText(/intervention reduces recurrence risk/i)).toBeVisible();
});
