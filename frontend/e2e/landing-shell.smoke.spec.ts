import { expect, test } from '@playwright/test';
import { dismissTourIfPresent } from './helpers';
import { loadFixture } from './fixture';

test('landing keeps editorial structure across desktop and mobile', async ({ page }) => {
  await page.goto('/');

  const hero = page.getByTestId('landing-hero');
  await expect(hero).toBeVisible();
  await expect(
    page.getByRole('heading', { name: /research with ai|investiga con ia|pesquise com ia/i }),
  ).toBeVisible();
  await expect(hero.getByRole('link', { name: /create workspace|crear workspace|criar workspace/i })).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('link', { name: /start free|comenzar gratis|começar grátis/i }).first()).toBeVisible();
  await expect(page.getByRole('link', { name: /log in|entrar/i }).first()).toBeVisible();
});

test('authenticated shell keeps responsive navigation and project routing', async ({ page }) => {
  const fixture = loadFixture();
  await page.goto(`/projects/${fixture.project.id}`);
  await dismissTourIfPresent(page);

  await expect(page.getByTestId('app-shell')).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`/projects/${fixture.project.id}/research$`));
  await expect(page.getByRole('link', { name: /projects|proyectos|projetos/i }).first()).toBeVisible();

  await page.goto('/dashboard');
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('button', { name: 'Open menu' })).toBeVisible();
  await page.getByRole('button', { name: 'Open menu' }).click();
  await expect(page.getByRole('link', { name: /projects|proyectos|projetos/i }).first()).toBeVisible();
});
