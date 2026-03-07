import { expect, test } from '@playwright/test';
import { loadFixture } from './fixture';

test('analysis workspace can create a dataset, queue a run and export html', async ({ page }) => {
  const fixture = loadFixture();
  await page.goto(`/projects/${fixture.project.id}/analysis`);

  await expect(page.getByText('Analysis')).toBeVisible();
  await page.getByTestId('dataset-title-input').fill(`e2e_dataset_${Date.now()}`);
  await page.getByTestId('dataset-rows-input').fill(
    '[{"group":"A","value":12},{"group":"A","value":10},{"group":"B","value":18},{"group":"B","value":15}]',
  );
  await page.getByTestId('dataset-create-button').click();
  await expect(page.getByText(/e2e_dataset_/)).toBeVisible();

  await page.getByTestId('analysis-title-input').fill(`E2E run ${Date.now()}`);
  await page.getByTestId('analysis-type-select').selectOption('group_comparison');
  await page.getByTestId('analysis-run-button').click();

  const runCard = page.locator('[data-testid^="analysis-run-"]').first();
  await expect(runCard).toContainText(/queued|running|completed/);
  await expect(runCard).toContainText(/Job:/);
  await expect(runCard).toContainText('completed', { timeout: 180000 });

  const downloadPromise = page.waitForEvent('download');
  await runCard.locator('button:has-text("HTML")').click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.html$/);
});
