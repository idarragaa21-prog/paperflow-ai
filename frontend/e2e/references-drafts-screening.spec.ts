import { expect, test } from '@playwright/test';
import { loadFixture } from './fixture';
import { dismissTourIfPresent } from './helpers';

test('references, drafts and screening workflows stay usable in the seeded fixture', async ({ page }) => {
  const fixture = loadFixture();
  const draftTitle = `E2E Draft ${Date.now()}`;

  await page.goto(`/projects/${fixture.project.id}/references`);
  await dismissTourIfPresent(page);
  await page.getByTestId('references-format-select').selectOption('bibtex');
  await page.getByTestId('references-content-input').fill(
    '@article{fixture2026,title={Internal RC Imported Study},author={Fixture, Team},year={2026},journal={PaperFlow Bench},doi={10.4242/paperflow.imported}}',
  );
  await page.getByTestId('references-import-button').click();
  await expect(page.locator('.rc-soft-card').filter({ hasText: 'Internal RC Imported Study' }).first()).toBeVisible();

  await page.goto(`/projects/${fixture.project.id}/drafts`);
  await dismissTourIfPresent(page);
  await page.getByTestId('draft-title-input').fill(draftTitle);
  await page.getByTestId('draft-create-button').click();
  await expect(page.getByTestId('draft-select')).toHaveValue(/.+/);
  await expect(page.locator('div[style*="font-weight: 800"]').filter({ hasText: draftTitle })).toBeVisible();
  const summaryHeadings = page.getByText('Summary', { exact: true });
  const summaryCountBefore = await summaryHeadings.count();
  await page.getByTestId('draft-heading-input').fill('Summary');
  await page.getByTestId('draft-generate-button').click();
  await expect.poll(async () => summaryHeadings.count()).toBeGreaterThan(summaryCountBefore);

  await page.goto(`/projects/${fixture.project.id}/screening`);
  await dismissTourIfPresent(page);
  await page.getByTestId('screening-comment-input').fill('Playwright screening note');
  await page.getByTestId('screening-add-comment').click();
  await expect(page.locator('.rc-help').filter({ hasText: 'Playwright screening note' }).first()).toBeVisible();
});
