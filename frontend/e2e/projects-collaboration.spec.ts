import { expect, test } from '@playwright/test';
import { loadFixture } from './fixture';

test('owner can open seeded project and review memberships', async ({ page }) => {
  const fixture = loadFixture();

  await page.goto('/projects');
  await expect(page.getByText('Projects')).toBeVisible();
  await expect(page.getByText(fixture.project.title)).toBeVisible();

  await page.goto(`/projects/${fixture.project.id}/collaboration`);
  await expect(page.getByText('Collaboration')).toBeVisible();
  await expect(page.getByTestId(`member-card-${fixture.owner.id}`)).toBeVisible();
  await expect(page.getByTestId(`member-card-${fixture.reviewer.id}`)).toBeVisible();
  await expect(page.getByTestId(`member-role-${fixture.reviewer.id}`)).toHaveValue('reviewer');
});
