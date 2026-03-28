import { type Page } from '@playwright/test';

export async function dismissTourIfPresent(page: Page) {
  const skipTour = page.getByRole('button', { name: /skip tour|saltar tour|pular tour/i });
  await skipTour.waitFor({ state: 'visible', timeout: 1500 }).catch(() => undefined);
  const visible = await skipTour.isVisible().catch(() => false);
  if (visible) {
    await skipTour.click();
    await skipTour.waitFor({ state: 'hidden', timeout: 3000 }).catch(() => undefined);
  }
  await page.evaluate(() => window.localStorage.setItem('paperflow_onboarding_done', '1')).catch(() => undefined);
}
