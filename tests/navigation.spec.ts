import { test, expect } from '@playwright/test';

test.describe('Navigation Tests - US-2: Navigation Links', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should have "Deploy now" button with correct attributes', async ({ page }) => {
    const deployButton = page.getByRole('link', { name: 'Deploy now' });

    // Check visibility
    await expect(deployButton).toBeVisible();

    // Check href
    const href = await deployButton.getAttribute('href');
    expect(href).toContain('vercel.com');

    // Check opens in new tab
    const target = await deployButton.getAttribute('target');
    expect(target).toBe('_blank');

    // Check security attributes
    const rel = await deployButton.getAttribute('rel');
    expect(rel).toContain('noopener');
    expect(rel).toContain('noreferrer');
  });

  test('should have "Read our docs" link with correct attributes', async ({ page }) => {
    const docsLink = page.getByRole('link', { name: 'Read our docs' });

    // Check visibility
    await expect(docsLink).toBeVisible();

    // Check href
    const href = await docsLink.getAttribute('href');
    expect(href).toContain('nextjs.org/docs');

    // Check opens in new tab
    const target = await docsLink.getAttribute('target');
    expect(target).toBe('_blank');

    // Check security attributes
    const rel = await docsLink.getAttribute('rel');
    expect(rel).toContain('noopener');
    expect(rel).toContain('noreferrer');
  });

  test('should have "Learn" footer link with correct attributes', async ({ page }) => {
    const learnLink = page.getByRole('link', { name: 'Learn' });

    // Check visibility
    await expect(learnLink).toBeVisible();

    // Check href
    const href = await learnLink.getAttribute('href');
    expect(href).toContain('nextjs.org/learn');

    // Check opens in new tab
    const target = await learnLink.getAttribute('target');
    expect(target).toBe('_blank');

    // Check security attributes
    const rel = await learnLink.getAttribute('rel');
    expect(rel).toContain('noopener');
    expect(rel).toContain('noreferrer');
  });

  test('should have "Examples" footer link with correct attributes', async ({ page }) => {
    const examplesLink = page.getByRole('link', { name: 'Examples' });

    // Check visibility
    await expect(examplesLink).toBeVisible();

    // Check href
    const href = await examplesLink.getAttribute('href');
    expect(href).toContain('vercel.com/templates');

    // Check opens in new tab
    const target = await examplesLink.getAttribute('target');
    expect(target).toBe('_blank');

    // Check security attributes
    const rel = await examplesLink.getAttribute('rel');
    expect(rel).toContain('noopener');
    expect(rel).toContain('noreferrer');
  });

  test('should have "Go to nextjs.org" footer link with correct attributes', async ({ page }) => {
    const nextjsLink = page.getByRole('link', { name: /Go to nextjs.org/ });

    // Check visibility
    await expect(nextjsLink).toBeVisible();

    // Check href
    const href = await nextjsLink.getAttribute('href');
    expect(href).toContain('nextjs.org');

    // Check opens in new tab
    const target = await nextjsLink.getAttribute('target');
    expect(target).toBe('_blank');

    // Check security attributes
    const rel = await nextjsLink.getAttribute('rel');
    expect(rel).toContain('noopener');
    expect(rel).toContain('noreferrer');
  });
});

test.describe('Navigation Security Tests', () => {
  test('all external links should have noopener noreferrer', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Get all links that open in new tab
    const externalLinks = await page.locator('a[target="_blank"]').all();

    for (const link of externalLinks) {
      const rel = await link.getAttribute('rel');
      expect(rel).toContain('noopener');
      expect(rel).toContain('noreferrer');
    }
  });

  test('all links should have valid href attributes', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Get all links
    const links = await page.locator('a').all();

    for (const link of links) {
      const href = await link.getAttribute('href');
      expect(href).not.toBeNull();
      expect(href).not.toBe('javascript:void(0)');
      expect(href).not.toBe('#');
    }
  });
});

test.describe('Keyboard Navigation - US-5: Accessibility', () => {
  test('should be navigable via keyboard', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Get all focusable elements
    const focusableElements = await page.locator('a, button, input, [tabindex]:not([tabindex="-1"])').all();

    // Verify there are focusable elements
    expect(focusableElements.length).toBeGreaterThan(0);

    // Tab through elements
    for (let i = 0; i < Math.min(5, focusableElements.length); i++) {
      await page.keyboard.press('Tab');
      const focusedElement = page.locator(':focus');
      await expect(focusedElement).toBeVisible();
    }
  });

  test('should have visible focus states', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Tab to first link
    await page.keyboard.press('Tab');

    // Check that focused element is visible
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();

    // Check that focus indicator is visible (outline or ring)
    const outline = await focusedElement.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return {
        outlineWidth: styles.outlineWidth,
        outlineStyle: styles.outlineStyle,
        boxShadow: styles.boxShadow,
      };
    });

    // Either outline or box-shadow should indicate focus
    const hasFocusIndicator =
      (outline.outlineWidth !== '0px' && outline.outlineStyle !== 'none') ||
      outline.boxShadow !== 'none';

    expect(hasFocusIndicator).toBe(true);
  });
});