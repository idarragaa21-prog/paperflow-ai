import { expect, test } from '@playwright/test';
import { dismissTourIfPresent } from './helpers';
import { loadFixture } from './fixture';

test('deep research, knowledge, settings, clinical and jobs load without fatal UI gaps', async ({ page }) => {
  const fixture = loadFixture();
  await page.goto('/deep-research');
  await dismissTourIfPresent(page);
  await expect(page.getByRole('heading', { name: /deep research|investigación profunda/i })).toBeVisible();
  await page.getByTestId('deep-research-source-project').click();
  await expect(page.getByTestId('deep-research-generate-button')).toBeDisabled();
  await page.getByTestId('deep-research-project-select').selectOption(fixture.project.id);
  await page.getByTestId('deep-research-query-input').fill('rotator cuff augmentation');
  await expect(page.getByTestId('deep-research-generate-button')).toBeEnabled();

  await page.goto('/books');
  await expect(page).toHaveURL(/\/knowledge$/);
  await expect(page.getByRole('heading', { name: /private knowledge sources/i })).toBeVisible();

  await page.goto('/settings');
  await expect(page.getByRole('heading', { name: /settings|configuración/i })).toBeVisible();
  await page.getByRole('button', { name: /uso local & cuotas/i }).click();
  await expect(page.getByText(/usage and quotas only|quota|tokens|No tracked local AI usage yet/i).first()).toBeVisible();
  await page.getByRole('button', { name: /equipo/i }).click();
  await expect(page.getByText(/project members|miembros/i).first()).toBeVisible();

  await page.goto('/clinical');
  await expect(page.getByRole('heading', { name: /clinical sheets/i })).toBeVisible();
  const topicInput = page.getByPlaceholder(/fifth metatarsal stress fracture|acl reconstruction/i);
  await topicInput.fill('Rotator cuff patch augmentation');
  await expect(page.getByRole('button', { name: /generate clinical sheet/i })).toBeEnabled();

  await page.goto('/jobs');
  await expect(page.getByRole('heading', { name: /jobs/i })).toBeVisible();
});

test('meta exports and draft clinical enrichment stay wired through the project workspace', async ({ page }) => {
  const fixture = loadFixture();
  let exportReady = false;

  await page.route(`**/meta/batches?project_id=${fixture.project.id}`, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
  });
  await page.route(`**/meta/studies?project_id=${fixture.project.id}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'study-smoke-1',
          paper_id: fixture.papers.first_paper_id,
          project_id: fixture.project.id,
          batch_id: null,
          paper_title: 'Smoke extracted study',
          title: 'Smoke extracted study',
          authors: 'Fixture Team',
          journal: 'PaperFlow Bench',
          publication_year: 2025,
          extraction_status: 'completed',
          risk_of_bias: [],
          effect_sizes: [],
        },
      ]),
    });
  });
  await page.route(`**/meta/exports?project_id=${fixture.project.id}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(
        exportReady
          ? [
              {
                id: 'export-smoke-1',
                project_id: fixture.project.id,
                batch_id: null,
                filename: 'meta_export_csv_bundle.zip',
                format: 'csv_bundle',
                created_at: new Date().toISOString(),
              },
            ]
          : [],
      ),
    });
  });
  await page.route('**/meta/export', async (route) => {
    exportReady = true;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ job_id: 'meta-export-smoke-job' }),
    });
  });
  await page.route('**/jobs/meta-export-smoke-job', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'completed', progress_percent: 100, result: { output: {} } }),
    });
  });

  await page.route(`**/drafts?project_id=${fixture.project.id}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'draft-smoke-1',
          project_id: fixture.project.id,
          title: 'Smoke Draft',
          status: 'draft',
          version: 1,
          sections: [],
        },
      ]),
    });
  });
  await page.route(`**/evidence/tables?project_id=${fixture.project.id}`, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
  });
  await page.route('**/drafts/draft-smoke-1/enhance-with-clinical', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });

  await page.goto(`/projects/${fixture.project.id}/meta`);
  await dismissTourIfPresent(page);
  await expect(page.getByRole('heading', { name: /extraction workspace/i })).toBeVisible();
  await page.getByRole('button', { name: 'Export CSV bundle' }).click();
  await expect(page.getByText(/Export CSV bundle job enqueued/i)).toBeVisible();
  await expect(page.getByText('meta_export_csv_bundle.zip')).toBeVisible({ timeout: 15000 });

  await page.goto(`/projects/${fixture.project.id}/drafts`);
  await dismissTourIfPresent(page);
  await expect(page.getByRole('heading', { name: /writing studio/i })).toBeVisible();
  await expect(page.getByTestId('draft-select')).toHaveValue('draft-smoke-1');
  await page.getByTestId('draft-enhance-clinical-button').click();
  await expect(page.getByText(/Clinical evidence added/i)).toBeVisible();
});
