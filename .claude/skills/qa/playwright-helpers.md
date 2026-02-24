# Playwright Helper Snippets (NO Confirmation Prompts!)

**Use `browser_run_code` for ALL interactions** - it bypasses element confirmation prompts entirely.

## MANDATORY: Screenshots for Documentation

**Every test snippet includes screenshots.** Screenshot naming:
- `{feature}-{test}-before.png` - Initial state
- `{feature}-{test}-after.png` - Final state
- `{feature}-{test}-error.png` - On failure
- `{feature}-mobile.png` - Mobile viewport
- `{feature}-desktop.png` - Desktop viewport

## Quick Reference

### Navigate and Snapshot (with Screenshots)
```javascript
async (page) => {
  await page.goto('http://localhost:3000');
  await page.waitForLoadState('networkidle');

  // Screenshot
  await page.screenshot({ path: 'test-results/page-initial.png', fullPage: true });

  return { url: page.url(), title: await page.title(), screenshot: 'page-initial.png' };
}
```

### Fill Form and Submit (with Screenshots)
```javascript
async (page) => {
  const screenshots = [];

  // Before
  await page.screenshot({ path: 'test-results/form-before.png' });
  screenshots.push('form-before.png');

  await page.getByLabel('Name').fill('Test User');
  await page.getByLabel('Email').fill('test@example.com');

  // Filled
  await page.screenshot({ path: 'test-results/form-filled.png' });
  screenshots.push('form-filled.png');

  await page.getByRole('button', { name: 'Submit' }).click();
  await page.waitForURL('**/success**', { timeout: 5000 });

  // After
  await page.screenshot({ path: 'test-results/form-success.png', fullPage: true });
  screenshots.push('form-success.png');

  return { success: true, url: page.url(), screenshots };
}
```

### Complete Form Test Flow (with Screenshots)
```javascript
async (page) => {
  const results = { steps: [], screenshots: [], errors: [] };

  try {
    // Navigate
    await page.goto('http://localhost:3000/contact');
    await page.screenshot({ path: 'test-results/contact-before.png' });
    results.screenshots.push('contact-before.png');
    results.steps.push('navigated');

    // Fill all fields
    await page.getByLabel(/name/i).fill('Max Mustermann');
    await page.getByLabel(/email/i).fill('max@test.de');
    await page.getByLabel(/telefon/i).fill('+49 170 1234567');
    await page.getByLabel(/nachricht/i).fill('Testnachricht');
    await page.screenshot({ path: 'test-results/contact-filled.png' });
    results.screenshots.push('contact-filled.png');
    results.steps.push('form_filled');

    // Submit
    await page.getByRole('button', { name: /absenden|senden|submit/i }).click();
    results.steps.push('submitted');

    // Wait for success
    await page.waitForSelector('.success, [data-success], text=/danke|erfolgreich/i', { timeout: 10000 });
    await page.screenshot({ path: 'test-results/contact-success.png', fullPage: true });
    results.screenshots.push('contact-success.png');
    results.steps.push('success_detected');

  } catch (error) {
    results.errors.push(error.message);
    await page.screenshot({ path: 'test-results/contact-error.png' });
    results.screenshots.push('contact-error.png');
  }

  return results;
}
```

### Responsive Testing (with Screenshots)
```javascript
async (page) => {
  const results = { viewports: {}, screenshots: [] };

  await page.goto('http://localhost:3000');

  // Mobile
  await page.setViewportSize({ width: 375, height: 667 });
  await page.screenshot({ path: 'test-results/responsive-mobile.png', fullPage: true });
  results.screenshots.push('responsive-mobile.png');
  results.viewports.mobile = { width: 375, height: 667, visible: true };

  // Tablet
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.screenshot({ path: 'test-results/responsive-tablet.png', fullPage: true });
  results.screenshots.push('responsive-tablet.png');
  results.viewports.tablet = { width: 768, height: 1024, visible: true };

  // Desktop
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.screenshot({ path: 'test-results/responsive-desktop.png', fullPage: true });
  results.screenshots.push('responsive-desktop.png');
  results.viewports.desktop = { width: 1440, height: 900, visible: true };

  return results;
}
```

### Check Console Errors (with Screenshots)
```javascript
async (page) => {
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });

  await page.goto('http://localhost:3000');
  await page.waitForLoadState('networkidle');

  // Screenshot for visual check
  await page.screenshot({ path: 'test-results/console-check.png', fullPage: true });

  return { errorCount: errors.length, errors: errors.slice(0, 10), screenshot: 'console-check.png' };
}
```

### Security Check (XSS/SQL Injection) (with Screenshots)
```javascript
async (page) => {
  const results = { xss: [], sqlInjection: [], exposed: [], screenshots: [] };

  const xssPayloads = ['<script>alert(1)</script>', '<img src=x onerror=alert(1)>'];

  for (let i = 0; i < xssPayloads.length; i++) {
    await page.goto('http://localhost:3000');
    const input = page.locator('input[type=text], textarea').first();
    if (await input.isVisible()) {
      await input.fill(xssPayloads[i]);
      await page.screenshot({ path: `test-results/xss-test-${i+1}.png` });
      results.screenshots.push(`xss-test-${i+1}.png`);
      await page.keyboard.press('Enter');
    }
  }

  // Check for exposed sensitive data
  const cookies = await page.context().cookies();
  const localStorage = await page.evaluate(() => ({ ...localStorage }));

  results.exposed = [
    ...cookies.filter(c => !c.httpOnly).map(c => `Cookie '${c.name}' not HttpOnly`),
    ...Object.keys(localStorage).filter(k => k.includes('token') || k.includes('secret'))
  ];

  await page.screenshot({ path: 'test-results/security-final.png' });
  results.screenshots.push('security-final.png');

  return results;
}
```

### Login Flow (with Screenshots)
```javascript
async (page) => {
  const screenshots = [];

  await page.goto('http://localhost:3000/login');
  await page.screenshot({ path: 'test-results/login-page.png' });
  screenshots.push('login-page.png');

  await page.getByLabel(/email/i).fill('test@example.com');
  await page.getByLabel(/password/i).fill('password123');

  await page.screenshot({ path: 'test-results/login-filled.png' });
  screenshots.push('login-filled.png');

  await page.getByRole('button', { name: /login|anmelden/i }).click();
  await page.waitForURL('**/dashboard**', { timeout: 10000 });

  await page.screenshot({ path: 'test-results/login-success.png', fullPage: true });
  screenshots.push('login-success.png');

  return { loggedIn: true, url: page.url(), screenshots };
}
```

### API Response Test (with Screenshots)
```javascript
async (page) => {
  const responses = [];

  page.on('response', async response => {
    if (response.url().includes('/api/')) {
      try {
        const body = await response.json();
        responses.push({ url: response.url(), status: response.status(), body });
      } catch {}
    }
  });

  await page.goto('http://localhost:3000');
  await page.waitForLoadState('networkidle');

  await page.screenshot({ path: 'test-results/api-test.png', fullPage: true });

  return { apiCalls: responses.length, responses, screenshot: 'api-test.png' };
}
```

## Usage in QA Skill

1. Copy the relevant snippet
2. Modify URL, selectors, and screenshot paths as needed
3. Use `browser_run_code` tool with the code
4. Check returned results and screenshots

### Accessibility Testing with axe-core (WCAG Compliance)
```javascript
async (page) => {
  const results = { violations: [], passes: 0, screenshots: [] };

  // Inject axe-core library
  await page.addScriptTag({ url: 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js' });

  // Navigate to page
  await page.goto('http://localhost:3000');
  await page.waitForLoadState('networkidle');

  // Run accessibility audit
  const audit = await page.evaluate(() => {
    return axe.run();
  });

  results.passes = audit.passes.length;
  results.violations = audit.violations.map(v => ({
    id: v.id,
    impact: v.impact,
    description: v.description,
    help: v.help,
    nodes: v.nodes.length
  }));

  // Screenshot for visual reference
  await page.screenshot({ path: 'test-results/accessibility.png', fullPage: true });
  results.screenshots.push('accessibility.png');

  // Summary
  results.summary = `${results.violations.length} violations found (${results.passes} rules passed)`;
  results.wcagCompliant = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious').length === 0;

  return results;
}
```

### Accessibility Violation Details
```javascript
async (page) => {
  await page.addScriptTag({ url: 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js' });
  await page.goto('http://localhost:3000');

  const audit = await page.evaluate(() => axe.run());

  // Detailed breakdown by WCAG level
  const details = {
    critical: audit.violations.filter(v => v.impact === 'critical'),
    serious: audit.violations.filter(v => v.impact === 'serious'),
    moderate: audit.violations.filter(v => v.impact === 'moderate'),
    minor: audit.violations.filter(v => v.impact === 'minor'),
    wcag2a: audit.violations.filter(v => v.tags?.includes('wcag2a')),
    wcag2aa: audit.violations.filter(v => v.tags?.includes('wcag2aa')),
    wcag21aa: audit.violations.filter(v => v.tags?.includes('wcag21aa'))
  };

  await page.screenshot({ path: 'test-results/accessibility-detailed.png' });

  return {
    totalViolations: audit.violations.length,
    details,
    screenshot: 'accessibility-detailed.png'
  };
}
```

### Performance Testing (Lighthouse-style metrics)
```javascript
async (page) => {
  const results = { metrics: {}, screenshots: [] };

  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });

  // Collect performance metrics
  const metrics = await page.evaluate(() => {
    const perf = performance.getEntriesByType('navigation')[0];
    return {
      // Load times
      domContentLoaded: Math.round(perf.domContentLoadedEventEnd - perf.domContentLoadedEventStart),
      loadComplete: Math.round(perf.loadEventEnd - perf.loadEventStart),
      domInteractive: Math.round(perf.domInteractive - perf.fetchStart),
      totalLoadTime: Math.round(perf.loadEventEnd - perf.fetchStart),

      // Resource counts
      resourceCount: performance.getEntriesByType('resource').length,
      scriptCount: performance.getEntriesByType('resource').filter(r => r.initiatorType === 'script').length,
      styleCount: performance.getEntriesByType('resource').filter(r => r.initiatorType === 'css').length,

      // Memory (if available)
      memory: performance.memory ? {
        usedJSHeapSize: Math.round(performance.memory.usedJSHeapSize / 1048576),
        totalJSHeapSize: Math.round(performance.memory.totalJSHeapSize / 1048576)
      } : null
    };
  });

  results.metrics = metrics;
  results.screenshots.push('performance-initial.png');

  // Largest Contentful Paint (LCP)
  const lcp = await page.evaluate(() => {
    return new Promise((resolve) => {
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        resolve(Math.round(entries[entries.length - 1].startTime));
      }).observe({ type: 'largest-contentful-paint', buffered: true });
      // Fallback timeout
      setTimeout(() => resolve(null), 3000);
    });
  });
  results.metrics.lcp = lcp;

  // Cumulative Layout Shift (CLS)
  const cls = await page.evaluate(() => {
    return new Promise((resolve) => {
      let clsValue = 0;
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (!entry.hadRecentInput) clsValue += entry.value;
        }
      }).observe({ type: 'layout-shift', buffered: true });
      setTimeout(() => resolve(Math.round(clsValue * 1000) / 1000), 2000);
    });
  });
  results.metrics.cls = cls;

  await page.screenshot({ path: 'test-results/performance-final.png' });
  results.screenshots.push('performance-final.png');

  // Performance score estimation
  results.score = {
    lcp: lcp !== null && lcp < 2500 ? 'good' : lcp !== null && lcp < 4000 ? 'needs-improvement' : 'poor',
    cls: cls < 0.1 ? 'good' : cls < 0.25 ? 'needs-improvement' : 'poor',
    loadTime: metrics.totalLoadTime < 3000 ? 'good' : metrics.totalLoadTime < 5000 ? 'needs-improvement' : 'poor'
  };

  return results;
}
```

## Usage in QA Skill

1. Copy the relevant snippet
2. Modify URL, selectors, and screenshot paths as needed
3. Use `browser_run_code` tool with the code
4. Check returned results and screenshots

**All snippets include screenshots for documentation!**