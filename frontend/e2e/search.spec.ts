import { expect, test, type Page } from '@playwright/test';
import { loadFixture } from './fixture';

async function dismissTourIfPresent(page: Page) {
  const skipTour = page.getByRole('button', { name: /skip tour/i });
  if (await skipTour.count()) {
    await skipTour.click();
  }
}

test('search can return openable results and save at least one paper with honest result states', async ({ page }) => {
  const fixture = loadFixture();
  const minYear = new Date().getFullYear() - 2;
  await page.goto(`/projects/${fixture.project.id}`);
  await expect(page).toHaveURL(new RegExp(`/projects/${fixture.project.id}/research$`));
  await dismissTourIfPresent(page);

  await page.getByTestId('search-filters-toggle').click();
  await page.getByTestId('search-query-input').fill('rotator cuff repair augmentation review');
  await page.getByTestId('search-year-from-input').fill(String(minYear));
  await page.getByTestId('search-submit-button').click();

  const firstCard = page.locator('[data-testid^="search-result-card-"]').first();
  await expect(firstCard).toBeVisible({ timeout: 120000 });

  const years = await page.locator('[data-testid^="search-result-card-"]').evaluateAll((nodes) =>
    nodes
      .map((node) => Number(node.getAttribute('data-pub-year')))
      .filter((year) => Number.isFinite(year) && year > 0)
      .slice(0, 8),
  );
  expect(years.length).toBeGreaterThan(0);
  expect(years.every((year) => year >= minYear)).toBeTruthy();

  await expect(firstCard).toContainText(/PubMed|Europe PMC|DOAJ/);
  await expect(firstCard).toContainText(/OA|Closed/);

  const firstOpenButton = page.locator('a[data-testid^="search-open-"]').first();
  await expect(firstOpenButton).toBeVisible({ timeout: 120000 });

  const href = await firstOpenButton.getAttribute('href');
  expect(href).toMatch(/^https?:\/\//);

  const externalPage = await page.context().newPage();
  await externalPage.goto(String(href), { waitUntil: 'domcontentloaded', timeout: 120000 });
  expect(externalPage.url()).toMatch(/^https?:\/\//);
  await externalPage.close();

  const firstSaveButton = page.locator('[data-testid^="search-save-"]').first();
  if (await firstSaveButton.count()) {
    await firstSaveButton.click();
    const firstTrace = page.locator('[data-testid^="search-download-trace-"]').first();
    await expect(firstTrace).toContainText(/Downloaded|Already in project|Failed/, { timeout: 120000 });
  }
});

test('batch download shows per-paper traceability in the modal', async ({ page }) => {
  const fixture = loadFixture();
  const minYear = new Date().getFullYear() - 2;
  await page.goto(`/projects/${fixture.project.id}`);
  await expect(page).toHaveURL(new RegExp(`/projects/${fixture.project.id}/research$`));
  await dismissTourIfPresent(page);

  await page.getByTestId('search-filters-toggle').click();
  await page.getByTestId('search-query-input').fill('rotator cuff repair augmentation review');
  await page.getByTestId('search-year-from-input').fill(String(minYear));
  await page.getByTestId('search-submit-button').click();

  const selectableRows = page.locator('[data-testid^="search-select-"]');
  await expect(selectableRows.first()).toBeVisible({ timeout: 120000 });
  await selectableRows.first().check();

  const batchButton = page.getByTestId('batch-download-button');
  await expect(batchButton).toContainText('(1)');
  await batchButton.click();

  const batchModal = page.getByTestId('batch-trace-modal');
  await expect(batchModal).toBeVisible({ timeout: 120000 });
  await expect(batchModal.getByTestId('batch-trace-title')).toHaveText('Batch OA Download');

  const firstTraceRow = batchModal.getByTestId('batch-trace-row-0');
  await expect(firstTraceRow).toBeVisible({ timeout: 120000 });
  await expect(firstTraceRow).toContainText(/Proveedor:|Proveedor no resuelto/);
  await expect(firstTraceRow).toContainText(/OA URL|Landing URL|Resolved URL|Resultado:/);
});
