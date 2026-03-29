import { expect, test } from '@playwright/test';
import { loadFixture } from './fixture';

test.describe('project invitations', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('a new invited user can sign up, sign in and open the shared project', async ({ page }) => {
    const fixture = loadFixture();
    const invitedPassword = 'paperflow-e2e-123';

    await page.goto(fixture.pending_invitation.accept_path);
    await expect(page.getByRole('heading', { name: /join a shared paperflow project/i })).toBeVisible();
    await page.getByTestId('invitation-create-account-link').click();

    await expect(page).toHaveURL(/\/signup\?/);
    await page.locator('input[autocomplete="name"]').fill('Invited Reviewer');
    await page.locator('input[type="email"]').fill(fixture.pending_invitation.email);
    const passwordInputs = page.locator('input[autocomplete="new-password"]');
    await passwordInputs.nth(0).fill(invitedPassword);
    await passwordInputs.nth(1).fill(invitedPassword);
    await page.locator('button[type="submit"]').click();

    await expect(page).toHaveURL(/\/login\?/);
    await expect(page.getByText(/account created\. sign in to open your shared project/i)).toBeVisible();
    await page.locator('input[type="password"]').fill(invitedPassword);
    await page.locator('button[type="submit"]').click();

    await expect(page).toHaveURL(new RegExp(`/projects/${fixture.project.id}/research$`), { timeout: 30000 });
    await expect(page.getByTestId('search-query-input')).toBeVisible();
  });
});
