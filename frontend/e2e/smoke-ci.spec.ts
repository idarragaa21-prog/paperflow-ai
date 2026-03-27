import { expect, test, type Page } from '@playwright/test';
import { loadFixture } from './fixture';

const currentYear = new Date().getFullYear();

const smokeSearchResponse = {
  count: 2,
  cached: false,
  sources: ['pubmed', 'europepmc'],
  results: [
    {
      title: 'Rotator cuff augmentation in revision repair',
      abstract: 'Mocked CI smoke result used to validate search rendering, save actions and traceability UI.',
      journal: 'Journal of Shoulder Surgery',
      pub_year: currentYear,
      doi: '10.5555/paperflow-smoke-1',
      pmid: '12345678',
      pmcid: 'PMC1234567',
      source: 'pubmed',
      oa_url: 'https://example.org/mock-paper-1.pdf',
      landing_url: 'https://example.org/mock-paper-1',
      is_open_access: true,
      relevance_score: 0.97,
    },
    {
      title: 'Bioinductive implant outcomes after cuff repair',
      abstract: 'Second mocked result to keep the list realistic without depending on external APIs.',
      journal: 'Arthroscopy',
      pub_year: currentYear - 1,
      doi: '10.5555/paperflow-smoke-2',
      pmid: '87654321',
      pmcid: 'PMC7654321',
      source: 'europepmc',
      oa_url: 'https://example.org/mock-paper-2.pdf',
      landing_url: 'https://example.org/mock-paper-2',
      is_open_access: true,
      relevance_score: 0.92,
    },
  ],
};

const smokeDownloadResponse = {
  duplicate: false,
  paper_id: 'paperflow-smoke-paper-1',
  source_provider: 'unpaywall',
  oa_url: 'https://example.org/mock-paper-1.pdf',
};

const smokeBatchJobId = 'paperflow-smoke-job';
const smokeBatchJob = {
  status: 'completed',
  progress_percent: 100,
  result: {
    output: {
      downloaded: [
        {
          title: 'Rotator cuff augmentation in revision repair',
          doi: '10.5555/paperflow-smoke-1',
          pmid: '12345678',
          pmcid: 'PMC1234567',
          paper_id: 'paperflow-smoke-paper-1',
          source_provider: 'unpaywall',
          oa_url: 'https://example.org/mock-paper-1.pdf',
          landing_url: 'https://example.org/mock-paper-1',
          resolved_url: 'https://example.org/mock-paper-1.pdf',
          used_fallback: false,
          final_status: 'downloaded',
          failure_reason: null,
        },
      ],
      already_exists: [],
      not_available: [],
      failed: [],
      items: [
        {
          title: 'Rotator cuff augmentation in revision repair',
          doi: '10.5555/paperflow-smoke-1',
          pmid: '12345678',
          pmcid: 'PMC1234567',
          paper_id: 'paperflow-smoke-paper-1',
          source_provider: 'unpaywall',
          oa_url: 'https://example.org/mock-paper-1.pdf',
          landing_url: 'https://example.org/mock-paper-1',
          resolved_url: 'https://example.org/mock-paper-1.pdf',
          used_fallback: false,
          final_status: 'downloaded',
          failure_reason: null,
        },
      ],
    },
  },
};

async function dismissTourIfPresent(page: Page) {
  const skipTour = page.getByRole('button', { name: /skip tour/i });
  if (await skipTour.count()) {
    await skipTour.click();
  }
}

test.beforeEach(async ({ page }) => {
  await page.route('**/search/federated', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(smokeSearchResponse) });
  });

  await page.route('**/papers/download', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(smokeDownloadResponse) });
  });

  await page.route('**/papers/batch-download', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ job_id: smokeBatchJobId }) });
  });

  await page.route(`**/jobs/${smokeBatchJobId}`, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(smokeBatchJob) });
  });
});

test('CI smoke keeps auth, search UI and single-save trace wired end-to-end', async ({ page }) => {
  const fixture = loadFixture();
  await page.goto(`/projects/${fixture.project.id}`);
  await expect(page).toHaveURL(new RegExp(`/projects/${fixture.project.id}/research$`));
  await dismissTourIfPresent(page);

  await page.getByTestId('search-filters-toggle').click();
  await page.getByTestId('search-query-input').fill('rotator cuff repair augmentation review');
  await page.getByTestId('search-year-from-input').fill(String(currentYear - 2));
  await page.getByTestId('search-submit-button').click();

  const firstCard = page.getByTestId('search-result-card-0');
  await expect(firstCard).toContainText('Rotator cuff augmentation in revision repair');
  await expect(firstCard).toContainText('PubMed');
  await expect(page.getByTestId('search-open-0')).toHaveAttribute('href', 'https://example.org/mock-paper-1.pdf');

  await page.getByTestId('search-save-0').click();
  await expect(page.getByTestId('search-download-trace-0')).toContainText(/Downloaded|Already in project/);
  await expect(page.getByTestId('search-download-trace-0')).toContainText('https://example.org/mock-paper-1.pdf');
});

test('CI smoke keeps batch traceability modal wired end-to-end', async ({ page }) => {
  const fixture = loadFixture();
  await page.goto(`/projects/${fixture.project.id}`);
  await expect(page).toHaveURL(new RegExp(`/projects/${fixture.project.id}/research$`));
  await dismissTourIfPresent(page);

  await page.getByTestId('search-query-input').fill('rotator cuff repair augmentation review');
  await page.getByTestId('search-submit-button').click();

  await page.getByTestId('search-select-0').check();
  await expect(page.getByTestId('batch-download-button')).toContainText('(1)');
  await page.getByTestId('batch-download-button').click();

  const batchModal = page.getByTestId('batch-trace-modal');
  await expect(batchModal).toBeVisible();
  await expect(batchModal.getByTestId('batch-trace-title')).toHaveText('Batch OA Download');

  const firstTraceRow = batchModal.getByTestId('batch-trace-row-0');
  await expect(firstTraceRow).toContainText('Proveedor: Unpaywall');
  await expect(firstTraceRow).toContainText('Resolved URL');
  await expect(firstTraceRow).toContainText('https://example.org/mock-paper-1.pdf');
});
