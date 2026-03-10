import { expect, test } from '@playwright/test';
import { loadFixture } from './fixture';

test('reader returns an evidence-based answer for the seeded fixture paper', async ({ page }) => {
  const fixture = loadFixture();
  await page.goto(`/projects/${fixture.project.id}/reader`);

  await page.getByTestId('reader-scope-select').selectOption(fixture.papers.first_paper_id);
  await page.getByTestId('reader-question-input').fill('What main effect is reported by the seeded monitoring study?');
  await page.getByTestId('reader-ask-button').click();

  const answerPanel = page.getByTestId('reader-answer-panel');
  await expect(answerPanel).toContainText(/con evidencia|sin evidencia suficiente|fallo de dependencia/, { timeout: 120000 });
  await expect(answerPanel).not.toContainText('Todavia no hay respuesta.');
});
