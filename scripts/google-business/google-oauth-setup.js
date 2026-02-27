import { google } from 'googleapis';
import http from 'http';
import { config } from 'dotenv';
import { writeFileSync, readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { exec } from 'child_process';

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
  console.log('\n🔑 Google OAuth Setup für SE Handwerk\n');
  console.log('='.repeat(50));

  if (!CLIENT_ID || !CLIENT_SECRET) {
    console.error('❌ Error: GOOGLE_CLIENT_ID und GOOGLE_CLIENT_SECRET müssen in .env gesetzt sein');
    process.exit(1);
  }

  const oauth2Client = new OAuth2(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI);

  // Generate authorization URL
  const authUrl = oauth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES,
    prompt: 'consent' // Force consent screen to get refresh token
  });

  console.log('\n📱 Schritt 1: Browser öffnet sich zur Autorisierung...\n');
  console.log('Falls der Browser sich nicht automatisch öffnet, besuchen Sie:');
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
        res.end(`<h1>❌ Autorisierung fehlgeschlagen: ${error}</h1>`);
        server.close();
        process.exit(1);
      }

      // Exchange code for tokens
      const { tokens } = await oauth2Client.getToken(code);

      // Save refresh token to .env
      const envPath = join(__dirname, '.env');
      let envContent = readFileSync(envPath, 'utf-8');

      if (tokens.refresh_token) {
        envContent = envContent.replace(
          /GOOGLE_REFRESH_TOKEN=.*/,
          `GOOGLE_REFRESH_TOKEN=${tokens.refresh_token}`
        );
        writeFileSync(envPath, envContent);
        console.log('\n✅ Refresh Token gespeichert in .env\n');
      }

      // Success response
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(`
        <html>
        <head><title>Erfolgreich</title></head>
        <body style="font-family: Arial; padding: 50px; text-align: center; background: #f5f5f5;">
          <div style="background: white; padding: 40px; border-radius: 10px; max-width: 500px; margin: 0 auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h1 style="color: #4CAF50;">✅ Autorisierung erfolgreich!</h1>
            <p>Sie können dieses Fenster jetzt schließen.</p>
            <hr>
            <p><strong>Nächster Schritt:</strong></p>
            <code style="background: #f0f0f0; padding: 10px; display: block; border-radius: 5px;">npm run create</code>
          </div>
        </body>
        </html>
      `);

      console.log('✅ OAuth Flow erfolgreich abgeschlossen!');
      console.log('\nNächster Schritt: Führen Sie "npm run create" aus um das Unternehmensprofil zu erstellen.\n');

      server.close();
      process.exit(0);

    } catch (error) {
      console.error('Error:', error);
      res.writeHead(500, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(`<h1>❌ Fehler: ${error.message}</h1>`);
      server.close();
      process.exit(1);
    }
  });

  server.listen(3000, () => {
    console.log('🌐 Server läuft auf http://localhost:3000/oauth/callback');
    console.log('Warte auf Autorisierung...\n');

    // Try to open browser
    const start = process.platform === 'darwin' ? 'open' : process.platform === 'win32' ? 'start' : 'xdg-open';
    exec(`${start} "${authUrl}"`, (err) => {
      if (err) {
        console.log('⚠️  Bitte öffnen Sie die URL manuell im Browser.');
      }
    });
  });
}

runOAuthFlow().catch(console.error);