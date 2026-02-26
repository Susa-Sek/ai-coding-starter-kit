/**
 * E2E User Journey Step Definitions
 *
 * This file defines user journeys for interactive E2E testing with Playwright MCP.
 * Each journey represents a complete user flow through the application.
 */

export interface JourneyStep {
  id: string;
  name: string;
  action: 'navigate' | 'click' | 'type' | 'select' | 'verify' | 'wait' | 'fill_form' | 'screenshot' | 'evaluate';
  target?: string;
  value?: string;
  expected?: string;
  screenshot?: boolean;
  timeout?: number;
}

export interface Journey {
  id: string;
  name: string;
  description: string;
  category: 'smoke' | 'critical' | 'extended' | 'security' | 'accessibility';
  steps: JourneyStep[];
}

/**
 * Built-in Journey Definitions
 */
export const journeys: Journey[] = [
  // ============================================
  // UJ-1: Homepage & Navigation
  // ============================================
  {
    id: 'UJ-1',
    name: 'Homepage & Navigation',
    description: 'Basic page loading and navigation verification',
    category: 'smoke',
    steps: [
      {
        id: 'UJ-1.1',
        name: 'Navigate to homepage',
        action: 'navigate',
        target: '/',
        screenshot: true
      },
      {
        id: 'UJ-1.2',
        name: 'Verify page title',
        action: 'verify',
        target: 'title',
        expected: 'not empty',
        screenshot: false
      },
      {
        id: 'UJ-1.3',
        name: 'Check logo visibility',
        action: 'verify',
        target: 'img[alt*="logo"], img[alt*="Logo"], [data-testid="logo"]',
        expected: 'visible',
        screenshot: true
      },
      {
        id: 'UJ-1.4',
        name: 'Check navigation links',
        action: 'verify',
        target: 'nav a, nav button',
        expected: 'visible',
        screenshot: false
      },
      {
        id: 'UJ-1.5',
        name: 'Check console errors',
        action: 'evaluate',
        target: 'console',
        value: 'errors',
        screenshot: false
      },
      {
        id: 'UJ-1.6',
        name: 'Final homepage screenshot',
        action: 'screenshot',
        screenshot: true
      }
    ]
  },

  // ============================================
  // UJ-2: Link Navigation
  // ============================================
  {
    id: 'UJ-2',
    name: 'Link Navigation',
    description: 'External link security and functionality verification',
    category: 'smoke',
    steps: [
      {
        id: 'UJ-2.1',
        name: 'Navigate to homepage',
        action: 'navigate',
        target: '/',
        screenshot: true
      },
      {
        id: 'UJ-2.2',
        name: 'Find external links',
        action: 'evaluate',
        target: 'links',
        value: 'external',
        screenshot: false
      },
      {
        id: 'UJ-2.3',
        name: 'Verify external link security',
        action: 'verify',
        target: 'a[target="_blank"]',
        expected: 'has-rel-noopener-noreferrer',
        screenshot: false
      },
      {
        id: 'UJ-2.4',
        name: 'Check footer links',
        action: 'verify',
        target: 'footer a',
        expected: 'visible',
        screenshot: true
      }
    ]
  },

  // ============================================
  // UJ-3: Responsive Design
  // ============================================
  {
    id: 'UJ-3',
    name: 'Responsive Design',
    description: 'Layout adaptation across different viewport sizes',
    category: 'extended',
    steps: [
      {
        id: 'UJ-3.1',
        name: 'Navigate to homepage',
        action: 'navigate',
        target: '/',
        screenshot: true
      },
      {
        id: 'UJ-3.2',
        name: 'Test Mobile S (320px)',
        action: 'evaluate',
        target: 'viewport',
        value: '320x568',
        screenshot: true
      },
      {
        id: 'UJ-3.3',
        name: 'Test Mobile M (375px)',
        action: 'evaluate',
        target: 'viewport',
        value: '375x667',
        screenshot: true
      },
      {
        id: 'UJ-3.4',
        name: 'Test Mobile L (414px)',
        action: 'evaluate',
        target: 'viewport',
        value: '414x896',
        screenshot: true
      },
      {
        id: 'UJ-3.5',
        name: 'Test Tablet (768px)',
        action: 'evaluate',
        target: 'viewport',
        value: '768x1024',
        screenshot: true
      },
      {
        id: 'UJ-3.6',
        name: 'Test Laptop (1024px)',
        action: 'evaluate',
        target: 'viewport',
        value: '1024x768',
        screenshot: true
      },
      {
        id: 'UJ-3.7',
        name: 'Test Desktop (1440px)',
        action: 'evaluate',
        target: 'viewport',
        value: '1440x900',
        screenshot: true
      },
      {
        id: 'UJ-3.8',
        name: 'Test Large (1920px)',
        action: 'evaluate',
        target: 'viewport',
        value: '1920x1080',
        screenshot: true
      },
      {
        id: 'UJ-3.9',
        name: 'Check horizontal scroll',
        action: 'evaluate',
        target: 'layout',
        value: 'no-horizontal-scroll',
        screenshot: false
      },
      {
        id: 'UJ-3.10',
        name: 'Check touch targets',
        action: 'evaluate',
        target: 'touch-targets',
        value: 'min-44x44',
        screenshot: false
      }
    ]
  },

  // ============================================
  // UJ-4: Performance Check
  // ============================================
  {
    id: 'UJ-4',
    name: 'Performance Check',
    description: 'Page load performance metrics verification',
    category: 'smoke',
    steps: [
      {
        id: 'UJ-4.1',
        name: 'Navigate to homepage',
        action: 'navigate',
        target: '/',
        screenshot: true
      },
      {
        id: 'UJ-4.2',
        name: 'Measure TTFB',
        action: 'evaluate',
        target: 'performance',
        value: 'ttfb',
        expected: '<2000ms',
        screenshot: false
      },
      {
        id: 'UJ-4.3',
        name: 'Measure FCP',
        action: 'evaluate',
        target: 'performance',
        value: 'fcp',
        expected: '<2000ms',
        screenshot: false
      },
      {
        id: 'UJ-4.4',
        name: 'Measure LCP',
        action: 'evaluate',
        target: 'performance',
        value: 'lcp',
        expected: '<4000ms',
        screenshot: false
      },
      {
        id: 'UJ-4.5',
        name: 'Measure CLS',
        action: 'evaluate',
        target: 'performance',
        value: 'cls',
        expected: '<0.1',
        screenshot: false
      }
    ]
  },

  // ============================================
  // UJ-5: Accessibility Scan
  // ============================================
  {
    id: 'UJ-5',
    name: 'Accessibility Scan',
    description: 'Basic accessibility verification',
    category: 'accessibility',
    steps: [
      {
        id: 'UJ-5.1',
        name: 'Navigate to homepage',
        action: 'navigate',
        target: '/',
        screenshot: true
      },
      {
        id: 'UJ-5.2',
        name: 'Check image alt text',
        action: 'evaluate',
        target: 'accessibility',
        value: 'image-alt-text',
        screenshot: false
      },
      {
        id: 'UJ-5.3',
        name: 'Check color contrast',
        action: 'evaluate',
        target: 'accessibility',
        value: 'color-contrast',
        screenshot: false
      },
      {
        id: 'UJ-5.4',
        name: 'Verify focus states',
        action: 'evaluate',
        target: 'accessibility',
        value: 'focus-states',
        screenshot: true
      },
      {
        id: 'UJ-5.5',
        name: 'Test keyboard navigation',
        action: 'evaluate',
        target: 'accessibility',
        value: 'keyboard-nav',
        screenshot: false
      },
      {
        id: 'UJ-5.6',
        name: 'Check ARIA labels',
        action: 'evaluate',
        target: 'accessibility',
        value: 'aria-labels',
        screenshot: false
      }
    ]
  },

  // ============================================
  // UJ-6: Security Check
  // ============================================
  {
    id: 'UJ-6',
    name: 'Security Check',
    description: 'Basic security audit',
    category: 'security',
    steps: [
      {
        id: 'UJ-6.1',
        name: 'Navigate to homepage',
        action: 'navigate',
        target: '/',
        screenshot: true
      },
      {
        id: 'UJ-6.2',
        name: 'Check for exposed secrets',
        action: 'evaluate',
        target: 'security',
        value: 'exposed-secrets',
        screenshot: false
      },
      {
        id: 'UJ-6.3',
        name: 'Check localStorage',
        action: 'evaluate',
        target: 'security',
        value: 'localstorage-sensitive',
        screenshot: false
      },
      {
        id: 'UJ-4.4',
        name: 'Test XSS prevention',
        action: 'evaluate',
        target: 'security',
        value: 'xss-prevention',
        screenshot: false
      },
      {
        id: 'UJ-6.5',
        name: 'Check security headers',
        action: 'evaluate',
        target: 'security',
        value: 'headers',
        screenshot: false
      },
      {
        id: 'UJ-6.6',
        name: 'Verify HTTPS',
        action: 'evaluate',
        target: 'security',
        value: 'https',
        screenshot: false
      }
    ]
  }
];

/**
 * Get journey by ID
 */
export function getJourney(id: string): Journey | undefined {
  return journeys.find(j => j.id === id);
}

/**
 * Get all journeys
 */
export function getAllJourneys(): Journey[] {
  return journeys;
}

/**
 * Get journeys by category
 */
export function getJourneysByCategory(category: Journey['category']): Journey[] {
  return journeys.filter(j => j.category === category);
}

/**
 * Journey execution result
 */
export interface JourneyResult {
  journeyId: string;
  journeyName: string;
  startTime: string;
  endTime: string;
  duration: string;
  totalSteps: number;
  passed: number;
  failed: number;
  skipped: number;
  steps: StepResult[];
  screenshots: string[];
  consoleErrors: string[];
}

export interface StepResult {
  stepId: string;
  stepName: string;
  action: string;
  status: 'passed' | 'failed' | 'skipped';
  screenshot?: string;
  error?: string;
  duration: number;
}

/**
 * Helper to create custom journey
 */
export function createCustomJourney(
  id: string,
  name: string,
  description: string,
  category: Journey['category'],
  steps: JourneyStep[]
): Journey {
  return { id, name, description, category, steps };
}

/**
 * Example: User Registration Flow
 * Uncomment and customize for your application
 */
/*
export const userRegistrationJourney = createCustomJourney(
  'UJ-7',
  'User Registration Flow',
  'Complete user registration process',
  'critical',
  [
    { id: 'UJ-7.1', name: 'Navigate to register', action: 'navigate', target: '/register', screenshot: true },
    { id: 'UJ-7.2', name: 'Enter name', action: 'type', target: 'Name', value: 'Test User', screenshot: false },
    { id: 'UJ-7.3', name: 'Enter email', action: 'type', target: 'Email', value: 'test@example.com', screenshot: false },
    { id: 'UJ-7.4', name: 'Enter password', action: 'type', target: 'Password', value: 'Test1234!', screenshot: false },
    { id: 'UJ-7.5', name: 'Confirm password', action: 'type', target: 'Confirm Password', value: 'Test1234!', screenshot: false },
    { id: 'UJ-7.6', name: 'Submit form', action: 'click', target: 'Register', screenshot: true },
    { id: 'UJ-7.7', name: 'Verify redirect', action: 'verify', expected: '/dashboard', screenshot: false },
  ]
);
*/