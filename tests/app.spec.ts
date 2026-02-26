import { test, expect } from '@playwright/test';

test.describe('Homepage Tests - US-1: Homepage Loading', () => {
  test('should load homepage successfully', async ({ page }) => {
    await page.goto('/');

    // Verify page loaded
    await expect(page).toHaveTitle(/.*/);
  });

  test('should display Next.js logo', async ({ page }) => {
    await page.goto('/');

    // Check for Next.js logo image
    const nextLogo = page.getByAltText('Next.js logo');
    await expect(nextLogo).toBeVisible();
  });

  test('should display getting started section', async ({ page }) => {
    await page.goto('/');

    // Check for getting started text
    const gettingStarted = page.getByText('Get started by editing');
    await expect(gettingStarted).toBeVisible();
  });

  test('should display code example', async ({ page }) => {
    await page.goto('/');

    // Check for code element showing src/app/page.tsx
    const codeElement = page.locator('code:has-text("src/app/page.tsx")');
    await expect(codeElement).toBeVisible();
  });

  test('should have no console errors on load', async ({ page }) => {
    const errors: string[] = [];
    const warnings: string[] = [];

    page.on('pageerror', (error) => {
      errors.push(error.message);
    });

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        warnings.push(msg.text());
      }
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check for no page errors
    expect(errors).toHaveLength(0);

    // Filter out expected Next.js dev warnings
    const unexpectedWarnings = warnings.filter(
      (w) => !w.includes('Download the React DevTools') && !w.includes('[Fast Refresh]')
    );
    expect(unexpectedWarnings).toHaveLength(0);
  });

  test('should take screenshot of homepage', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Take screenshot for evidence
    await page.screenshot({ path: 'test-results/homepage-full.png', fullPage: true });
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have main content area', async ({ page }) => {
    await page.goto('/');

    // Check for main element
    const main = page.locator('main');
    await expect(main).toBeVisible();
  });

  test('should have footer section', async ({ page }) => {
    await page.goto('/');

    // Check for footer element
    const footer = page.locator('footer');
    await expect(footer).toBeVisible();
  });
});

test.describe('404 Page Handling - EC-4: Input Validation', () => {
  test('should handle invalid routes gracefully', async ({ page }) => {
    const response = await page.goto('/nonexistent-page-12345');

    // Should return 404
    expect(response?.status()).toBe(404);
  });

  test('should display 404 content for invalid routes', async ({ page }) => {
    await page.goto('/nonexistent-page-12345');

    // Check for 404 or not found text
    const content = await page.content();
    const has404 = content.includes('404') || content.includes('Not Found') || content.includes('not found');
    expect(has404).toBe(true);
  });
});

test.describe('Network Edge Cases - EC-2: Network Issues', () => {
  test('should handle slow network', async ({ page }) => {
    // Simulate slow network
    const client = await page.context().newCDPSession(page);
    await client.send('Network.emulateNetworkConditions', {
      offline: false,
      downloadThroughput: (500 * 1024) / 8,
      uploadThroughput: (500 * 1024) / 8,
      latency: 200,
    });

    await page.goto('/');
    await expect(page).toHaveTitle(/.*/);
  });

  test('should load resources correctly', async ({ page }) => {
    const failedRequests: string[] = [];

    page.on('requestfailed', (request) => {
      failedRequests.push(request.url());
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Filter out expected failures (like analytics)
    const unexpectedFailures = failedRequests.filter(
      (url) => !url.includes('analytics') && !url.includes('sentry')
    );

    expect(unexpectedFailures).toHaveLength(0);
  });
});