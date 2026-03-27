import { expect, test } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { loadFixture } from './fixture';

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const reviewerStorageState = path.resolve(currentDir, '.auth', 'reviewer.json');

test('owner can open seeded project and review memberships', async ({ page }) => {
  const fixture = loadFixture();

  await page.goto('/projects');
  await expect(page.getByText(fixture.project.title, { exact: true })).toBeVisible();

  await page.goto(`/projects/${fixture.project.id}/collaboration`);
  await expect(page.getByTestId(`member-card-${fixture.owner.id}`)).toBeVisible();
  await expect(page.getByTestId(`member-card-${fixture.reviewer.id}`)).toBeVisible();
  await expect(page.getByTestId(`member-role-${fixture.reviewer.id}`)).toHaveValue('reviewer');
});

test.describe('reviewer permissions', () => {
  test.use({ storageState: reviewerStorageState });

  test('reviewer sees collaboration and screening controls constrained by role', async ({ page }) => {
    const fixture = loadFixture();

    await page.goto(`/projects/${fixture.project.id}/collaboration`);
    await expect(page.getByTestId('member-add-button')).toBeDisabled();
    await expect(page.getByTestId(`member-role-${fixture.owner.id}`)).toBeDisabled();

    await page.goto(`/projects/${fixture.project.id}/screening`);
    await expect(page.getByTestId('screening-create-batch')).toBeDisabled();
    await expect(page.getByTestId('screening-add-comment')).toBeEnabled();
    await expect(page.getByTestId('screening-queue-review-action')).toBeEnabled();
  });
});
