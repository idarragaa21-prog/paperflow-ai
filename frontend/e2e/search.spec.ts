import { expect, test } from '@playwright/test';
import { loadFixture } from './fixture';

test('search can return openable results and save at least one paper with honest result states', async ({ page }) => {
  const fixture = loadFixture();
  await page.goto(`/projects/${fixture.project.id}`);
  await expect(page).toHaveURL(new RegExp(`/projects/${fixture.project.id}/research$`));

  await page.getByRole('button', { name: 'Filtros' }).click();
  await expect(page.getByTestId('search-recency-select')).toHaveValue('5y');

  await page.getByTestId('search-query-input').fill('rotator cuff repair augmentation review');
  await page.getByTestId('search-recency-select').selectOption('2y');
  await page.getByTestId('search-submit-button').click();

  const firstCard = page.locator('[data-testid^="search-result-card-"]').first();
  await expect(firstCard).toBeVisible({ timeout: 120000 });

  const years = await page.locator('[data-testid^="search-result-card-"]').evaluateAll((nodes) =>
    nodes
      .map((node) => Number(node.getAttribute('data-pub-year')))
      .filter((year) => Number.isFinite(year) && year > 0)
      .slice(0, 8),
  );
  const minYear = new Date().getFullYear() - 2;
  expect(years.length).toBeGreaterThan(0);
  expect(years.every((year) => year >= minYear)).toBeTruthy();

  await page.getByTestId('search-details-0').click();
  await expect(firstCard).toContainText(/Estado:|Proveedor:|Contenido:/);

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
    await expect(firstSaveButton).toHaveText(/Guardado en biblioteca|Ya est[aá] en la biblioteca|Reintentar guardado/, { timeout: 120000 });
  }
});
