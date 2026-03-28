import { expect, test } from '@playwright/test';
import { dismissTourIfPresent } from './helpers';

test('deep research, knowledge, settings, clinical and jobs load without fatal UI gaps', async ({ page }) => {
  await page.goto('/deep-research');
  await dismissTourIfPresent(page);
  await expect(page.getByRole('heading', { name: /deep research|investigación profunda/i })).toBeVisible();
  await page.getByRole('button', { name: /my project library|mi biblioteca del proyecto/i }).click();
  await expect(page.getByRole('combobox').first()).toBeVisible();

  await page.goto('/knowledge');
  await expect(page.getByRole('heading', { name: /private knowledge sources/i })).toBeVisible();

  await page.goto('/settings');
  await expect(page.getByRole('heading', { name: /settings|configuración/i })).toBeVisible();
  await page.getByRole('button', { name: /uso & facturación/i }).click();
  await expect(page.getByText(/quota|tokens|No monthly usage history yet/i).first()).toBeVisible();
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
