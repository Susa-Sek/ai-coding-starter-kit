# Google Business Profile API - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create SE Handwerk Google Business Profile via official API, bypassing bot detection, with SEO optimization for high ranking.

**Architecture:** Node.js script using Google OAuth 2.0 and Business Profile API. One-time setup with refresh token for future updates. Photos from Google Drive, supplemented by website assets.

**Tech Stack:** Node.js, googleapis npm package, OAuth 2.0, Business Profile API v1

---

## Prerequisites (User Action Required)

User must complete these in Google Cloud Console:

1. Create project at https://console.cloud.google.com/
2. Enable "Business Profile API"
3. Create OAuth 2.0 Web Application credentials
4. Add redirect URI: `http://localhost:3000/oauth/callback`
5. Provide: Client ID and Client Secret

---

## Photo Sources

**Primary:** Google Drive
- Folder: https://drive.google.com/drive/folders/19OOOcKG9olwTQbCdi5_rJQyaGDRNWH4_

**Supplemental (if needed):**
- Logo: https://sehandwerk.de/assets/logo-white.png
- Cover: https://sehandwerk.de/assets/bodenarbeiten.jpg
- Work photos: https://sehandwerk.de/assets/wohnungsuebergabe.jpg, https://sehandwerk.de/assets/montage.jpg

---

### Task 1: Setup Project Dependencies

**Files:**
- Create: `scripts/google-business/package.json`

**Step 1: Create package.json**

```json
{
  "name": "google-business-setup",
  "version": "1.0.0",
  "description": "SE Handwerk Google Business Profile API Setup",
  "type": "module",
  "scripts": {
    "oauth": "node google-oauth-setup.js",
    "create": "node google-business-api.js"
  },
  "dependencies": {
    "googleapis": "^140.0.0",
    "dotenv": "^16.4.0",
    "open": "^10.1.0"
  }
}
```

**Step 2: Install dependencies**

Run: `cd scripts/google-business && npm install`
Expected: Dependencies installed successfully

**Step 3: Commit**

```bash
git add scripts/google-business/package.json scripts/google-business/package-lock.json
git commit -m "feat(PROJ-10): Add Google Business API package setup"
```

---

### Task 2: Create Environment Configuration

**Files:**
- Create: `scripts/google-business/.env.example`
- Create: `scripts/google-business/.env` (gitignored, user fills in)

**Step 1: Create .env.example**

```bash
# Google OAuth Credentials
GOOGLE_CLIENT_ID=your-client-id-here
GOOGLE_CLIENT_SECRET=your-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:3000/oauth/callback

# Tokens (auto-generated after OAuth flow)
GOOGLE_REFRESH_TOKEN=
```

**Step 2: Create .gitignore for scripts**

```
.env
node_modules/
tokens/
```

**Step 3: Commit**

```bash
git add scripts/google-business/.env.example scripts/google-business/.gitignore
git commit -m "feat(PROJ-10): Add environment configuration template"
```

---

### Task 3: Create OAuth Setup Script

**Files:**
- Create: `scripts/google-business/google-oauth-setup.js`

**Step 1: Write OAuth setup script**

```javascript
import { google } from 'googleapis';
import { open } from 'open';
import http from 'http';
import { config } from 'dotenv';
import { writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const OAuth2 = google.auth.OAuth2;

const CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
const CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET;
const REDIRECT_URI = process.env.GOOGLE_REDIRECT_URI || 'http://localhost:3000/oauth/callback';

// Scopes needed for Business Profile API
const SCOPES = [
  'https://www.googleapis.com/auth/business.manage',
  'https://www.googleapis.com/auth/userinfo.profile',
  'https://www.googleapis.com/auth/userinfo.email'
];

async function runOAuthFlow() {
  console.log('\n🔑 Google OAuth Setup for SE Handwerk\n');
  console.log('=' .repeat(50));

  if (!CLIENT_ID || !CLIENT_SECRET) {
    console.error('❌ Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env');
    process.exit(1);
  }

  const oauth2Client = new OAuth2(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI);

  // Generate authorization URL
  const authUrl = oauth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES,
    prompt: 'consent' // Force consent screen to get refresh token
  });

  console.log('\n📱 Step 1: Opening browser for authorization...\n');
  console.log('If browser does not open automatically, visit this URL:');
  console.log('\n' + authUrl + '\n');

  // Start local server to receive callback
  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, REDIRECT_URI);

      if (url.pathname !== '/oauth/callback') {
        res.writeHead(404);
        res.end('Not found');
        return;
      }

      const code = url.searchParams.get('code');

      if (!code) {
        const error = url.searchParams.get('error');
        res.writeHead(400, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(`<h1>❌ Authorization failed: ${error}</h1>`);
        server.close();
        process.exit(1);
      }

      // Exchange code for tokens
      const { tokens } = await oauth2Client.getToken(code);

      // Save refresh token to .env
      const envPath = join(__dirname, '.env');
      let envContent = require('fs').readFileSync(envPath, 'utf-8');

      if (tokens.refresh_token) {
        envContent = envContent.replace(
          /GOOGLE_REFRESH_TOKEN=.*/,
          `GOOGLE_REFRESH_TOKEN=${tokens.refresh_token}`
        );
        writeFileSync(envPath, envContent);
        console.log('\n✅ Refresh token saved to .env\n');
      }

      // Success response
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(`
        <html>
        <head><title>Erfolgreich</title></head>
        <body style="font-family: Arial; padding: 50px; text-align: center;">
          <h1>✅ Autorisierung erfolgreich!</h1>
          <p>Sie können dieses Fenster schließen.</p>
          <p>Führen Sie nun aus: <code>npm run create</code></p>
        </body>
        </html>
      `);

      console.log('✅ OAuth flow completed successfully!');
      console.log('\nNext step: Run "npm run create" to create the business profile.\n');

      server.close();
      process.exit(0);

    } catch (error) {
      console.error('Error:', error);
      res.writeHead(500, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(`<h1>❌ Error: ${error.message}</h1>`);
      server.close();
      process.exit(1);
    }
  });

  server.listen(3000, () => {
    console.log('🌐 Listening on http://localhost:3000/oauth/callback');
    console.log('Waiting for authorization callback...\n');

    // Open browser
    open(authUrl).catch(() => {
      console.log('Please open the URL manually in your browser.');
    });
  });
}

runOAuthFlow().catch(console.error);
```

**Step 2: Test script runs without errors**

Run: `cd scripts/google-business && node google-oauth-setup.js`
Expected: Shows auth URL and starts server (will wait for browser callback)

**Step 3: Commit**

```bash
git add scripts/google-business/google-oauth-setup.js
git commit -m "feat(PROJ-10): Add OAuth setup script for Google Business API"
```

---

### Task 4: Create Business Profile API Script

**Files:**
- Create: `scripts/google-business/google-business-api.js`

**Step 1: Write main API script**

```javascript
import { google } from 'googleapis';
import { config } from 'dotenv';
import { createRequire } from 'module';

config();

const require = createRequire(import.meta.url);

const OAuth2 = google.auth.OAuth2;

const CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
const CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET;
const REDIRECT_URI = process.env.GOOGLE_REDIRECT_URI;
const REFRESH_TOKEN = process.env.GOOGLE_REFRESH_TOKEN;

// SE Handwerk Business Data
const BUSINESS_DATA = {
  title: 'SE Handwerk',
  languageCode: 'de',
  storefrontAddress: {
    addressLines: ['Steinsfeldstr. 21'],
    locality: 'Bretzfeld',
    postalCode: '74626',
    administrativeArea: 'Baden-Württemberg',
    regionCode: 'DE'
  },
  phoneNumbers: {
    primaryPhone: '+491734536225'
  },
  websiteUri: 'https://sehandwerk.de',
  categories: {
    primaryCategory: {
      name: 'gcid:flooring_contractor'
    },
    additionalCategories: [
      { name: 'gcid:general_contractor' },
      { name: 'gcid:carpenter' }
    ]
  },
  regularHours: {
    periods: [
      { openDay: 'MONDAY', openTime: '08:00', closeDay: 'MONDAY', closeTime: '18:00' },
      { openDay: 'TUESDAY', openTime: '08:00', closeDay: 'TUESDAY', closeTime: '18:00' },
      { openDay: 'WEDNESDAY', openTime: '08:00', closeDay: 'WEDNESDAY', closeTime: '18:00' },
      { openDay: 'THURSDAY', openTime: '08:00', closeDay: 'THURSDAY', closeTime: '18:00' },
      { openDay: 'FRIDAY', openTime: '08:00', closeDay: 'FRIDAY', closeTime: '18:00' }
    ]
  },
  serviceArea: {
    places: [
      { placeId: 'ChIJV2JCr8jRmUcRrhhV-zv_QE4' }, // Heilbronn
      { placeId: 'ChIJJzIMI_NmpEcRUrI6T5cLrZQ' }, // Stuttgart
      { placeId: 'ChIJe4xJbNM_mUcRYGq9X5f9pRk' }, // Mannheim
      { placeId: 'ChIJ41Hw0tINmUcR5E8Hf8xLmKQ' }  // Bretzfeld area
    ]
  },
  // SEO-optimized description (max 750 chars)
  advertiserProvidedDescription: `Zuverlässiger Handwerksbetrieb im Raum Heilbronn und Stuttgart.

Unsere Leistungen:
✓ Bodenarbeiten – Laminat & Vinyl verlegen, Sockelleisten, Untergrundvorbereitung
✓ Wohnungsübergabe – Böden erneuern, Wände/Decken streichen, Kleinreparaturen
✓ Montage & Reparatur – Möbelmontage, Küchen, Sportgeräte-Aufbau

Warum SE Handwerk?
• Festpreis vor Arbeitsbeginn
• Rückmeldung innerhalb 24 Stunden
• Kostenlose Besichtigung bei Auftragserteilung
• Transparent, fair und termingerecht

Einsatzgebiet: Heilbronn, Stuttgart, Mannheim, Bretzfeld, Weinsberg, Sachsenheim, Freudenstadt & Umgebung.

Rufen Sie uns an oder schreiben Sie uns!`
};

async function createBusinessProfile() {
  console.log('\n🏢 SE Handwerk - Google Business Profile Creator\n');
  console.log('=' .repeat(50));

  if (!REFRESH_TOKEN) {
    console.error('❌ Error: GOOGLE_REFRESH_TOKEN not found in .env');
    console.log('Run "npm run oauth" first to get the refresh token.\n');
    process.exit(1);
  }

  // Setup OAuth2 client
  const oauth2Client = new OAuth2(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI);
  oauth2Client.setCredentials({ refresh_token: REFRESH_TOKEN });

  // Get access token
  console.log('🔑 Authenticating with Google...');
  const { credentials } = await oauth2Client.refreshAccessToken();
  console.log('✅ Authenticated successfully\n');

  // Get account ID
  console.log('📋 Fetching account information...');
  const mybusinessaccountmanagement = google.mybusinessaccountmanagement({
    version: 'v1',
    auth: oauth2Client
  });

  const accounts = await mybusinessaccountmanagement.accounts.list();
  const account = accounts.data.accounts?.[0];

  if (!account) {
    console.error('❌ No Google Business account found');
    process.exit(1);
  }

  console.log(`✅ Account: ${account.name}`);
  console.log(`   Account ID: ${account.name.replace('accounts/', '')}\n`);

  // Create location using Business Information API
  console.log('📝 Creating business profile...');

  const mybusinessbusinessinformation = google.mybusinessbusinessinformation({
    version: 'v1',
    auth: oauth2Client
  });

  try {
    const location = await mybusinessbusinessinformation.accounts.locations.create({
      parent: account.name,
      requestBody: BUSINESS_DATA
    });

    console.log('\n✅ Business profile created successfully!\n');
    console.log('📍 Location Name:', location.data.name);
    console.log('🆔 Location ID:', location.data.name?.split('/').pop());
    console.log('\n📱 Next steps:');
    console.log('1. Visit: https://business.google.com');
    console.log('2. Verify your business (postcard or video)');
    console.log('3. Add photos from Google Drive');
    console.log('4. Respond to first reviews to boost ranking\n');

    return location.data;

  } catch (error) {
    if (error.response?.data?.error?.message) {
      console.error('\n❌ API Error:', error.response.data.error.message);

      // Handle specific errors
      if (error.response.data.error.message.includes('DUPLICATE')) {
        console.log('\n💡 This business may already exist. Check: https://business.google.com');
      }
    } else {
      console.error('\n❌ Error:', error.message);
    }
    process.exit(1);
  }
}

// Also export for programmatic use
export { BUSINESS_DATA, createBusinessProfile };

// Run if executed directly
if (import.meta.url === `file://${process.argv[1].replace(/\\/g, '/')}`) {
  createBusinessProfile().catch(console.error);
}
```

**Step 2: Commit**

```bash
git add scripts/google-business/google-business-api.js
git commit -m "feat(PROJ-10): Add Business Profile API creation script with SEO data"
```

---

### Task 5: Create Photo Upload Helper

**Files:**
- Create: `scripts/google-business/upload-photos.js`

**Step 1: Write photo upload script**

```javascript
import { google } from 'googleapis';
import { config } from 'dotenv';
import { createReadStream } from 'fs';
import { basename } from 'path';

config();

const OAuth2 = google.auth.OAuth2;

async function uploadPhoto(locationName, photoPath, category = 'ADDITIONAL') {
  const CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
  const CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET;
  const REDIRECT_URI = process.env.GOOGLE_REDIRECT_URI;
  const REFRESH_TOKEN = process.env.GOOGLE_REFRESH_TOKEN;

  const oauth2Client = new OAuth2(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI);
  oauth2Client.setCredentials({ refresh_token: REFRESH_TOKEN });

  const mybusinessbusinessinformation = google.mybusinessbusinessinformation({
    version: 'v1',
    auth: oauth2Client
  });

  console.log(`📷 Uploading: ${basename(photoPath)}`);

  try {
    const result = await mybusinessbusinessinformation.media.create({
      parent: `${locationName}/media`,
      requestBody: {
        mediaFormat: 'PHOTO',
        locationAssociation: {
          category: category // LOGO, COVER, ADDITIONAL, INTERIOR, EXTERIOR, etc.
        }
      },
      media: {
        body: createReadStream(photoPath)
      }
    });

    console.log(`✅ Uploaded: ${result.data.name}`);
    return result.data;

  } catch (error) {
    console.error('❌ Upload failed:', error.message);
  }
}

// Usage: node upload-photos.js <location-name> <photo-path> [category]
if (process.argv.length >= 4) {
  const locationName = process.argv[2];
  const photoPath = process.argv[3];
  const category = process.argv[4] || 'ADDITIONAL';
  uploadPhoto(locationName, photoPath, category);
}

export { uploadPhoto };
```

**Step 2: Commit**

```bash
git add scripts/google-business/upload-photos.js
git commit -m "feat(PROJ-10): Add photo upload helper for Business Profile"
```

---

### Task 6: Create README with Instructions

**Files:**
- Create: `scripts/google-business/README.md`

**Step 1: Write comprehensive README**

```markdown
# SE Handwerk - Google Business Profile Setup

Automated creation of Google Business Profile via official API.

## Prerequisites

1. Google Cloud Console project with Business Profile API enabled
2. OAuth 2.0 credentials (Client ID & Secret)
3. Node.js 18+

## Setup

### 1. Google Cloud Console (one-time)

1. Go to https://console.cloud.google.com/
2. Create project: `se-handwerk-business`
3. Enable **Business Profile API**
4. Create OAuth 2.0 Web Application credentials
5. Add redirect URI: `http://localhost:3000/oauth/callback`
6. Copy Client ID and Client Secret

### 2. Configure Environment

```bash
cd scripts/google-business
npm install
cp .env.example .env
# Edit .env with your credentials
```

### 3. OAuth Authorization (one-time)

```bash
npm run oauth
```

This will:
- Open your browser
- Ask you to authorize with Google
- Save refresh token to .env

### 4. Create Business Profile

```bash
npm run create
```

## Photo Upload

After profile creation, upload photos:

```bash
# Logo
node upload-photos.js "accounts/XXX/locations/YYY" "./photos/logo.png" LOGO

# Cover photo
node upload-photos.js "accounts/XXX/locations/YYY" "./photos/cover.jpg" COVER

# Work photos
node upload-photos.js "accounts/XXX/locations/YYY" "./photos/work1.jpg" ADDITIONAL
```

## Business Data

All data is defined in `google-business-api.js`:
- Company: SE Handwerk
- Address: Steinsfeldstr. 21, 74626 Bretzfeld
- Phone: +49 173 4536225
- Website: https://sehandwerk.de
- Service Area: Heilbronn, Stuttgart, Mannheim & surroundings

## SEO Optimization

The profile includes:
- SEO-optimized description (keywords: Bodenarbeiten, Wohnungsübergabe, Montage)
- Service area coverage
- Business categories
- Opening hours

## Troubleshooting

### "Access Denied"
- Check OAuth consent screen
- Add yourself as test user

### "Duplicate Location"
- Business already exists on Google
- Claim existing profile instead

### "API not enabled"
- Enable Business Profile API in Cloud Console
```

**Step 2: Commit**

```bash
git add scripts/google-business/README.md
git commit -m "docs(PROJ-10): Add README with setup instructions"
```

---

### Task 7: Create Feature Spec

**Files:**
- Create: `features/PROJ-10-playwright-mcp-tool-coverage.md` (update existing)

**Step 1: Verify feature spec exists and update**

**Step 2: Update features/INDEX.md**

---

## Success Criteria

- [ ] OAuth flow completes successfully
- [ ] Business profile created via API
- [ ] Profile visible in Google Business dashboard
- [ ] Verification initiated
- [ ] Photos upload-ready

## SEO Ranking Factors Addressed

1. ✅ Complete NAP (Name, Address, Phone) data
2. ✅ Business categories (primary + secondary)
3. ✅ Service area defined
4. ✅ SEO-optimized description with keywords
5. ✅ Opening hours
6. ✅ Website linked
7. 📋 Photos (manual upload after verification)
8. 📋 Reviews (encourage customers)
9. 📋 Regular posts (manual via dashboard)