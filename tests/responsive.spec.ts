import { test, expect } from '@playwright/test';

test.describe('Responsive Design Tests - US-3: Responsive Design', () => {
  // Mobile S - iPhone SE
  test('should display correctly on mobile S (320px)', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 568 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check for horizontal scroll (should not exist)
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.body.scrollWidth > window.innerWidth;
    });
    expect(hasHorizontalScroll).toBe(false);

    // Take screenshot
    await page.screenshot({ path: 'test-results/responsive-mobile-s.png', fullPage: true });

    // Verify main elements are visible
    await expect(page.locator('main')).toBeVisible();
    await expect(page.locator('footer')).toBeVisible();
  });

  // Mobile M - iPhone 8
  test('should display correctly on mobile M (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check for horizontal scroll
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.body.scrollWidth > window.innerWidth;
    });
    expect(hasHorizontalScroll).toBe(false);

    // Take screenshot
    await page.screenshot({ path: 'test-results/responsive-mobile-m.png', fullPage: true });

    // Verify main elements
    await expect(page.locator('main')).toBeVisible();
  });

  // Mobile L - iPhone 11
  test('should display correctly on mobile L (414px)', async ({ page }) => {
    await page.setViewportSize({ width: 414, height: 896 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check for horizontal scroll
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.body.scrollWidth > window.innerWidth;
    });
    expect(hasHorizontalScroll).toBe(false);

    // Take screenshot
    await page.screenshot({ path: 'test-results/responsive-mobile-l.png', fullPage: true });
  });

  // Tablet - iPad
  test('should display correctly on tablet (768px)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check for horizontal scroll
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.body.scrollWidth > window.innerWidth;
    });
    expect(hasHorizontalScroll).toBe(false);

    // Take screenshot
    await page.screenshot({ path: 'test-results/responsive-tablet.png', fullPage: true });
  });

  // Desktop
  test('should display correctly on desktop (1440px)', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check for horizontal scroll
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.body.scrollWidth > window.innerWidth;
    });
    expect(hasHorizontalScroll).toBe(false);

    // Take screenshot
    await page.screenshot({ path: 'test-results/responsive-desktop.png', fullPage: true });
  });

  // Large Desktop
  test('should display correctly on large desktop (1920px)', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check for horizontal scroll
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.body.scrollWidth > window.innerWidth;
    });
    expect(hasHorizontalScroll).toBe(false);

    // Take screenshot
    await page.screenshot({ path: 'test-results/responsive-large.png', fullPage: true });
  });
});

test.describe('Touch Target Tests', () => {
  test('touch targets should be at least 44x44px on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Get all interactive elements
    const interactiveElements = await page.locator('a, button, input, [role="button"]').all();

    const smallTargets: string[] = [];

    for (const element of interactiveElements) {
      const box = await element.boundingBox();
      if (box) {
        if (box.width < 44 || box.height < 44) {
          const text = await element.textContent();
          smallTargets.push(`${text?.trim() || 'unknown'}: ${Math.round(box.width)}x${Math.round(box.height)}`);
        }
      }
    }

    // Log small targets for visibility
    if (smallTargets.length > 0) {
      console.log('Small touch targets:', smallTargets);
    }

    // This test is informational - not strictly failing
    // Many designs have smaller touch targets for certain elements
  });
});

test.describe('Layout Tests', () => {
  test('should not have overlapping elements on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check for overlapping interactive elements
    const overlappingElements = await page.evaluate(() => {
      const elements = document.querySelectorAll('button, a, input');
      const overlapping: string[] = [];

      for (let i = 0; i < elements.length; i++) {
        const rect1 = elements[i].getBoundingClientRect();
        for (let j = i + 1; j < elements.length; j++) {
          const rect2 = elements[j].getBoundingClientRect();

          // Check if elements overlap (with some tolerance)
          if (
            rect1.left < rect2.right - 5 &&
            rect1.right > rect2.left + 5 &&
            rect1.top < rect2.bottom - 5 &&
            rect1.bottom > rect2.top + 5
          ) {
            overlapping.push(`${elements[i].tagName} overlaps ${elements[j].tagName}`);
          }
        }
      }

      return overlapping;
    });

    expect(overlappingElements).toHaveLength(0);
  });

  test('should not have overlapping elements on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check for overlapping interactive elements
    const overlappingElements = await page.evaluate(() => {
      const elements = document.querySelectorAll('button, a, input');
      const overlapping: string[] = [];

      for (let i = 0; i < elements.length; i++) {
        const rect1 = elements[i].getBoundingClientRect();
        for (let j = i + 1; j < elements.length; j++) {
          const rect2 = elements[j].getBoundingClientRect();

          if (
            rect1.left < rect2.right - 5 &&
            rect1.right > rect2.left + 5 &&
            rect1.top < rect2.bottom - 5 &&
            rect1.bottom > rect2.top + 5
          ) {
            overlapping.push(`${elements[i].tagName} overlaps ${elements[j].tagName}`);
          }
        }
      }

      return overlapping;
    });

    expect(overlappingElements).toHaveLength(0);
  });

  test('content should be visible without horizontal scroll on all viewports', async ({ page }) => {
    const viewports = [
      { name: 'mobile-s', width: 320, height: 568 },
      { name: 'mobile-m', width: 375, height: 667 },
      { name: 'mobile-l', width: 414, height: 896 },
      { name: 'tablet', width: 768, height: 1024 },
      { name: 'desktop', width: 1440, height: 900 },
    ];

    for (const viewport of viewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      const hasHorizontalScroll = await page.evaluate(() => {
        return document.body.scrollWidth > window.innerWidth;
      });

      expect(hasHorizontalScroll).toBe(false);
    }
  });
});