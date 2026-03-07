import { expect, test } from '@playwright/test';
import { loadFixture } from './fixture';

test('references, drafts and screening workflows stay usable in the seeded fixture', async ({ page }) => {
  const fixture = loadFixture();

  await page.goto(`/projects/${fixture.project.id}/references`);
  await expect(page.getByText('References')).toBeVisible();
  await page.getByTestId('references-format-select').selectOption('bibtex');
  await page.getByTestId('references-content-input').fill(
    '@article{fixture2026,title={Internal RC Imported Study},author={Fixture, Team},year={2026},journal={PaperFlow Bench},doi={10.4242/paperflow.imported}}',
  );
  await page.getByTestId('references-import-button').click();
  await expect(page.getByText('Internal RC Imported Study')).toBeVisible();

  await page.goto(`/projects/${fixture.project.id}/drafts`);
  await expect(page.getByText('Writing Studio')).toBeVisible();
  await page.getByTestId('draft-title-input').fill(`E2E Draft ${Date.now()}`);
  await page.getByTestId('draft-create-button').click();
  await expect(page.getByText(/E2E Draft/)).toBeVisible();
  await page.getByTestId('draft-select').selectOption({ index: 1 });
  await page.getByTestId('draft-heading-input').fill('Summary');
  await page.getByTestId('draft-generate-button').click();
  await expect(page.getByText('Summary')).toBeVisible();

  await page.goto(`/projects/${fixture.project.id}/screening`);
  await expect(page.getByText('Screening')).toBeVisible();
  await page.getByTestId('screening-comment-input').fill('Playwright screening note');
  await page.getByTestId('screening-add-comment').click();
  await expect(page.getByText('Playwright screening note')).toBeVisible();
});
