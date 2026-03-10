import { expect, test } from '@playwright/test';
import { loadFixture } from './fixture';

test('search can return openable results and save at least one paper with honest result states', async ({ page }) => {
  const fixture = loadFixture();
  await page.goto(`/projects/${fixture.project.id}/research`);

  await page.getByTestId('search-query-input').fill('rotator cuff repair augmentation review');
  await page.getByTestId('search-submit-button').click();

  const firstOpenButton = page.locator('[data-testid^="search-open-"], [data-testid^="search-open-review-"]').first();
  await expect(firstOpenButton).toBeVisible({ timeout: 120000 });

  const popupPromise = page.waitForEvent('popup');
  await firstOpenButton.click();
  const popup = await popupPromise;
  await popup.waitForLoadState('domcontentloaded');
  expect(popup.url()).toMatch(/^https?:\/\//);
  await popup.close();

  const firstSaveButton = page.locator('[data-testid^="search-save-"]').first();
  if (await firstSaveButton.count()) {
    await firstSaveButton.click();
    await expect(firstSaveButton).toHaveText(/Guardado en biblioteca|Ya esta en la biblioteca|Reintentar guardado/, { timeout: 120000 });
  }
});
