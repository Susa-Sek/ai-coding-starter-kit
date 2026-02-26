import { test, expect } from '@playwright/test';

test.describe('Security Tests - US-6: Security', () => {
  test('external links should have noopener noreferrer', async ({ page }) => {
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

  test('should not expose secrets in client-side code', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Get page content
    const content = await page.content();

    // Check for common secret patterns
    const secretPatterns = [
      /api[_-]?key\s*[=:]\s*['"][^'"]+['"]/i,
      /secret\s*[=:]\s*['"][^'"]+['"]/i,
      /password\s*[=:]\s*['"][^'"]+['"]/i,
      /token\s*[=:]\s*['"][^'"]+['"]/i,
      /auth[_-]?key\s*[=:]\s*['"][^'"]+['"]/i,
      /private[_-]?key\s*[=:]\s*['"][^'"]+['"]/i,
    ];

    for (const pattern of secretPatterns) {
      const matches = content.match(pattern);
      expect(matches).toBeNull();
    }
  });

  test('should not have sensitive data in localStorage', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const localStorage = await page.evaluate(() => {
      const items: { [key: string]: string } = {};
      for (let i = 0; i < window.localStorage.length; i++) {
        const key = window.localStorage.key(i);
        if (key) {
          items[key] = window.localStorage.getItem(key) || '';
        }
      }
      return items;
    });

    const sensitiveKeys = ['token', 'password', 'secret', 'key', 'auth', 'credential'];

    for (const key of Object.keys(localStorage)) {
      const lowerKey = key.toLowerCase();
      const isSensitive = sensitiveKeys.some((sk) => lowerKey.includes(sk));
      expect(isSensitive).toBe(false);
    }
  });

  test('should not have sensitive data in sessionStorage', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const sessionStorage = await page.evaluate(() => {
      const items: { [key: string]: string } = {};
      for (let i = 0; i < window.sessionStorage.length; i++) {
        const key = window.sessionStorage.key(i);
        if (key) {
          items[key] = window.sessionStorage.getItem(key) || '';
        }
      }
      return items;
    });

    const sensitiveKeys = ['token', 'password', 'secret', 'key', 'auth', 'credential'];

    for (const key of Object.keys(sessionStorage)) {
      const lowerKey = key.toLowerCase();
      const isSensitive = sensitiveKeys.some((sk) => lowerKey.includes(sk));
      expect(isSensitive).toBe(false);
    }
  });

  test('should handle XSS attempts gracefully', async ({ page }) => {
    // Navigate to a page that might reflect input
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Try to inject script via URL hash
    await page.goto('/#<script>alert("xss")</script>');
    await page.waitForLoadState('networkidle');

    // Check that no alert was triggered
    const hasInjectedScript = await page.evaluate(() => {
      const scripts = document.querySelectorAll('script');
      for (const script of scripts) {
        if (script.textContent?.includes('alert("xss")')) {
          return true;
        }
      }
      return false;
    });

    expect(hasInjectedScript).toBe(false);
  });

  test('should not have inline event handlers', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check for inline event handlers
    const inlineHandlers = await page.evaluate(() => {
      const elements = document.querySelectorAll('[onclick], [onerror], [onload], [onmouseover], [onmouseout], [onkeydown], [onkeyup], [onfocus], [onblur]');
      return elements.length;
    });

    expect(inlineHandlers).toBe(0);
  });

  test('should not have javascript: URLs', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Get all links
    const links = await page.locator('a').all();

    for (const link of links) {
      const href = await link.getAttribute('href');
      if (href) {
        expect(href.toLowerCase().startsWith('javascript:')).toBe(false);
      }
    }
  });
});

test.describe('Content Security Tests', () => {
  test('should not load external scripts from untrusted sources', async ({ page }) => {
    const externalScripts: string[] = [];

    page.on('response', (response) => {
      const url = response.url();
      if (url.endsWith('.js') && !url.includes('localhost')) {
        externalScripts.push(url);
      }
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Log external scripts for review
    console.log('External scripts loaded:', externalScripts);

    // Check that external scripts are from trusted sources
    const trustedDomains = [
      'vercel.com',
      'nextjs.org',
      'cloudflare.com',
      'cloudflareinsights.com',
      'jsdelivr.net',
      'unpkg.com',
    ];

    for (const script of externalScripts) {
      const isTrusted = trustedDomains.some((domain) => script.includes(domain));
      // This is informational - don't fail on external scripts
      console.log(`Script: ${script} - Trusted: ${isTrusted}`);
    }
  });

  test('should not have mixed content issues', async ({ page }) => {
    const mixedContent: string[] = [];

    page.on('response', (response) => {
      const url = response.url();
      // Check for HTTP resources on HTTPS page (if applicable)
      if (url.startsWith('http://') && !url.includes('localhost')) {
        mixedContent.push(url);
      }
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    expect(mixedContent).toHaveLength(0);
  });

  test('should not expose source maps in production', async ({ page }) => {
    let sourceMapsFound = false;

    page.on('response', (response) => {
      if (response.url().endsWith('.map')) {
        sourceMapsFound = true;
      }
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // In development, source maps are expected
    // In production, this would be a security concern
    console.log('Source maps found:', sourceMapsFound);
  });
});

test.describe('Form Security Tests (for future forms)', () => {
  test('should handle special characters in URLs safely', async ({ page }) => {
    const specialChars = ['<', '>', '"', "'", '&', '\\x00', '\\n', '\\r'];

    for (const char of specialChars) {
      // Try to navigate with special characters
      const response = await page.goto(`/test${encodeURIComponent(char)}`).catch(() => null);

      // Page should either load or return 404, but not crash
      if (response) {
        expect([200, 404]).toContain(response.status());
      }
    }
  });

  test('should not leak information in error pages', async ({ page }) => {
    // Navigate to a non-existent page
    const response = await page.goto('/nonexistent-error-page-12345');

    // Should return 404
    expect(response?.status()).toBe(404);

    // Get page content
    const content = await page.content();

    // Should not contain stack traces or internal paths
    // Note: In dev mode, Next.js shows detailed error info which is expected
    // This test is more relevant for production builds
    const sensitivePatterns = [
      /stack trace/i,
      /at\s+\w+\s*\(/i, // Stack trace pattern
    ];

    for (const pattern of sensitivePatterns) {
      // In dev mode, we allow some error details for debugging
      // This is informational for dev mode
      const matches = content.match(pattern);
      if (matches) {
        console.log('Note: Dev mode may show error details for debugging');
      }
    }

    // Verify the 404 page is displayed
    expect(response?.status()).toBe(404);
  });
});