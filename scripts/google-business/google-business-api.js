import { google } from 'googleapis';
import { config } from 'dotenv';

config();

const OAuth2 = google.auth.OAuth2;

const CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
const CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET;
const REDIRECT_URI = process.env.GOOGLE_REDIRECT_URI;
const REFRESH_TOKEN = process.env.GOOGLE_REFRESH_TOKEN;

// SE Handwerk Business Data - SEO optimized
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
  console.log('='.repeat(50));

  if (!REFRESH_TOKEN) {
    console.error('❌ Error: GOOGLE_REFRESH_TOKEN nicht in .env gefunden');
    console.log('Führen Sie zuerst "npm run oauth" aus um das Refresh Token zu erhalten.\n');
    process.exit(1);
  }

  // Setup OAuth2 client
  const oauth2Client = new OAuth2(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI);
  oauth2Client.setCredentials({ refresh_token: REFRESH_TOKEN });

  // Get access token
  console.log('🔑 Authentifizierung bei Google...');
  try {
    const { credentials } = await oauth2Client.refreshAccessToken();
    console.log('✅ Authentifiziert\n');
  } catch (error) {
    console.error('❌ Authentifizierung fehlgeschlagen:', error.message);
    console.log('\nMögliche Lösungen:');
    console.log('1. Führen Sie "npm run oauth" erneut aus');
    console.log('2. Prüfen Sie Client ID und Secret in .env\n');
    process.exit(1);
  }

  // Get account ID
  console.log('📋 Account-Informationen abrufen...');

  const mybusinessaccountmanagement = google.mybusinessaccountmanagement({
    version: 'v1',
    auth: oauth2Client
  });

  let account;
  try {
    const accounts = await mybusinessaccountmanagement.accounts.list();
    account = accounts.data.accounts?.[0];

    if (!account) {
      console.error('❌ Kein Google Business Account gefunden');
      console.log('\nLösung: Erstellen Sie zuerst ein Google Business Profil unter:');
      console.log('https://business.google.com\n');
      process.exit(1);
    }

    console.log(`✅ Account: ${account.accountName || account.name}`);
    console.log(`   Account ID: ${account.name.replace('accounts/', '')}\n`);

  } catch (error) {
    if (error.message.includes('not found') || error.message.includes('permission')) {
      console.error('❌ Business Profile API nicht verfügbar oder nicht aktiviert');
      console.log('\nStellen Sie sicher, dass:');
      console.log('1. Business Profile API in Google Cloud aktiviert ist');
      console.log('2. OAuth-Zustimmungsbildschirm konfiguriert ist');
      console.log('3. Sie sich als Testnutzer hinzugefügt haben\n');
    } else {
      console.error('❌ Fehler:', error.message);
    }
    process.exit(1);
  }

  // Create location using Business Information API
  console.log('📝 Unternehmensprofil wird erstellt...');
  console.log('');
  console.log('   Firma:', BUSINESS_DATA.title);
  console.log('   Adresse:', BUSINESS_DATA.storefrontAddress.addressLines[0],
    BUSINESS_DATA.storefrontAddress.postalCode,
    BUSINESS_DATA.storefrontAddress.locality);
  console.log('   Telefon:', BUSINESS_DATA.phoneNumbers.primaryPhone);
  console.log('   Website:', BUSINESS_DATA.websiteUri);
  console.log('');

  const mybusinessbusinessinformation = google.mybusinessbusinessinformation({
    version: 'v1',
    auth: oauth2Client
  });

  try {
    const location = await mybusinessbusinessinformation.accounts.locations.create({
      parent: account.name,
      requestBody: BUSINESS_DATA
    });

    console.log('\n' + '='.repeat(50));
    console.log('✅ UNTERNEHMENSPROFIL ERFOLGREICH ERSTELLT!\n');
    console.log('📍 Location Name:', location.data.title);
    console.log('🆔 Location ID:', location.data.name?.split('/').pop());
    console.log('');
    console.log('📱 Nächste Schritte:');
    console.log('   1. Besuchen Sie: https://business.google.com');
    console.log('   2. Bestätigen Sie Ihr Unternehmen (Postkarte oder Video)');
    console.log('   3. Laden Sie Fotos hoch aus:');
    console.log('      https://drive.google.com/drive/folders/19OOOcKG9olwTQbCdi5_rJQyaGDRNWH4_');
    console.log('   4. Reagieren Sie auf erste Bewertungen');
    console.log('');

    // Save location name for later use
    const fs = await import('fs');
    const path = await import('path');
    const { fileURLToPath } = await import('url');
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);

    fs.writeFileSync(
      path.join(__dirname, 'location-info.json'),
      JSON.stringify({
        locationName: location.data.name,
        locationId: location.data.name?.split('/').pop(),
        created: new Date().toISOString()
      }, null, 2)
    );

    return location.data;

  } catch (error) {
    const errorMessage = error.response?.data?.error?.message || error.message;

    console.error('\n❌ API Fehler:', errorMessage);

    // Handle specific errors
    if (errorMessage.includes('DUPLICATE') || errorMessage.includes('already exists')) {
      console.log('\n💡 Dieses Unternehmen existiert bereits auf Google.');
      console.log('   Prüfen Sie: https://business.google.com');
      console.log('   Sie können den bestehenden Eintrag beanspruchen.\n');
    } else if (errorMessage.includes('permission') || errorMessage.includes('access')) {
      console.log('\n💡 Berechtigungsproblem:');
      console.log('   1. Prüfen Sie den OAuth-Zustimmungsbildschirm');
      console.log('   2. Fügen Sie sich als Testnutzer hinzu\n');
    }

    process.exit(1);
  }
}

// Run if executed directly
createBusinessProfile().catch(console.error);