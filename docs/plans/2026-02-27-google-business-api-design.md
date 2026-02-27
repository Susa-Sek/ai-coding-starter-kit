# Google Business Profile API - Design Document

**Date:** 2026-02-27
**Status:** Approved
**Target:** SE Handwerk Google Unternehmensprofil

## Overview

Ein Node.js-Setup-Skript zur Erstellung des Google Unternehmensprofils für SE Handwerk über die offizielle Google Business Profile API - ohne Bot-Erkennungsprobleme.

## Business Data

| Field | Value |
|-------|-------|
| Firma | SE Handwerk |
| Adresse | Steinsfeldstr. 21, 74626 Bretzfeld |
| Telefon | +49 173 4536225 |
| E-Mail | kontakt@sehandwerk.de |
| Website | https://sehandwerk.de |
| Kategorie | Handwerksbetrieb / Bodenleger |

## Architecture

```
Setup Process
=============
1. Google Cloud Console (manual, one-time)
   - Create project
   - Enable Business Profile API
   - Create OAuth 2.0 credentials

2. OAuth Flow (one-time in browser)
   - Open authorization URL
   - Login with Google
   - Receive refresh token

3. API Script (automated)
   - Create business profile
   - Insert all data from KURZKARTE.md
   - Trigger verification
```

## Components

### Files to Create
- `scripts/google-business-api.js` - Main API script
- `scripts/google-oauth-setup.js` - OAuth flow for initial token
- `.env.local` - Credentials and tokens (gitignored)

### API Endpoints Used
1. Google OAuth 2.0 - Authentication
2. `accounts.locations.create` - Create profile
3. `accounts.locations.verify` - Start verification

## Data Flow

```javascript
// Business profile payload
const businessData = {
  title: "SE Handwerk",
  languageCode: "de",
  storefrontAddress: {
    addressLines: ["Steinsfeldstr. 21"],
    locality: "Bretzfeld",
    postalCode: "74626",
    regionCode: "DE"
  },
  phoneNumbers: {
    primaryPhone: "+491734536225"
  },
  websiteUri: "https://sehandwerk.de",
  categories: {
    primaryCategory: {
      name: "gcid:flooring_contractor"
    }
  },
  regularHours: {
    periods: []  // Nach Vereinbarung
  },
  serviceArea: {
    places: [
      { placeId: "Heilbronn" },
      { placeId: "Stuttgart" },
      { placeId: "Mannheim" }
    ]
  }
};
```

## User Interaction Required

1. **Google Cloud Console Setup** (one-time, ~5 min)
2. **OAuth Authorization** (browser click, one-time)
3. **Business Verification** (postcard or video)

## Security

- OAuth credentials stored in `.env.local` (gitignored)
- Refresh token for long-term access
- No hardcoded secrets in source code

## Success Criteria

- [ ] OAuth flow completed
- [ ] Business profile created via API
- [ ] Verification initiated
- [ ] Profile visible in Google Business dashboard

## References

- [Google Business Profile API](https://developers.google.com/my-business)
- [accounts.locations.create](https://developers.google.com/my-business/reference/businessinformation/rest/v1/accounts.locations/create)
- KURZKARTE.md in features/sehandwerk-google-profile/