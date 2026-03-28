import { expect, test } from '@playwright/test';
import { loadFixture } from './fixture';
import { dismissTourIfPresent } from './helpers';

test('analysis workspace can create a dataset, queue a run and export html', async ({ page }) => {
  const fixture = loadFixture();
  const datasetName = `e2e_dataset_${Date.now()}`;
  const runTitle = `E2E run ${Date.now()}`;
  await page.goto(`/projects/${fixture.project.id}/analysis`);
  await dismissTourIfPresent(page);

  await page.getByTestId('dataset-title-input').fill(datasetName);
  await page.getByTestId('dataset-rows-input').fill(
    '[{"group":"A","value":12},{"group":"A","value":10},{"group":"B","value":18},{"group":"B","value":15}]',
  );
  await page.getByTestId('dataset-create-button').click();
  await expect(page.getByTestId('analysis-dataset-select')).toContainText(datasetName);

  await page.getByTestId('analysis-title-input').fill(runTitle);
  await page.getByTestId('analysis-type-select').selectOption('group_comparison');
  await page.getByTestId('analysis-run-button').click();

  const runCard = page.locator('[data-testid^="analysis-run-"]').filter({ hasText: runTitle }).first();
  await expect(runCard).toContainText(/queued|running|completed/);
  await expect(runCard).toContainText('completed', { timeout: 180000 });

  const exportResponsePromise = page.waitForResponse((response) => {
    return (
      response.request().method() === 'POST' &&
      response.url().includes('/analysis-runs/') &&
      response.url().includes('format=html') &&
      response.status() === 200
    );
  });
  await runCard.locator('button[data-testid*="-html"]').click();
  const exportResponse = await exportResponsePromise;
  expect(exportResponse.headers()['content-type'] || '').toContain('text/html');
});
