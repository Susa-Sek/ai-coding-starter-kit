#!/usr/bin/env python3
"""
Standalone IMAP Draft Test - ohne Import-Probleme.
"""

import asyncio
import email
import os
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from dataclasses import dataclass
from pathlib import Path

# Load .env
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ.setdefault(key, value)

import aioimaplib


@dataclass
class IMAPConfig:
    host: str = "mail.privateemail.com"
    port: int = 993
    user: str = ""
    password: str = ""
    use_ssl: bool = True
    drafts_folder: str = "Drafts"


async def test_imap():
    """Test IMAP connection and save draft."""

    # Get config from env
    config = IMAPConfig(
        host=os.getenv('IMAP_HOST', 'mail.privateemail.com'),
        port=int(os.getenv('IMAP_PORT', '993')),
        user=os.getenv('SMTP_USER', ''),
        password=os.getenv('SMTP_PASSWORD', ''),
        use_ssl=True,
        drafts_folder=os.getenv('IMAP_DRAFTS_FOLDER', 'Drafts')
    )

    print("=" * 60)
    print("IMAP Draft Test")
    print("=" * 60)
    print(f"Host: {config.host}:{config.port}")
    print(f"User: {config.user}")
    print(f"Password: {'*' * len(config.password)}")
    print()

    if not config.user or not config.password:
        print("❌ Keine SMTP_USER/SMTP_PASSWORD in .env")
        return False

    # Connect
    print("Verbinde zu IMAP Server...")
    try:
        client = aioimaplib.IMAP4_SSL(host=config.host, port=config.port)
        await client.wait_hello_from_server()

        result = await client.login(config.user, config.password)
        if result.result != 'OK':
            print(f"❌ Login fehlgeschlagen: {result}")
            return False

        print("✅ Verbunden und eingeloggt!")

        # List folders
        print("\nOrdner auflisten...")
        result, data = await client.list('', '*')
        if result == 'OK':
            for line in data[:10]:  # Show first 10 folders
                if isinstance(line, bytes):
                    line = line.decode('utf-8', errors='ignore')
                print(f"   {line}")

        # Find drafts folder
        drafts_folder = None
        for line in data:
            if isinstance(line, bytes):
                line = line.decode('utf-8', errors='ignore')
            line_lower = line.lower()
            for name in ['drafts', 'entwürfe', 'draft']:
                if name in line_lower:
                    parts = line.split('"')
                    if len(parts) >= 3:
                        drafts_folder = parts[-2] or parts[-1]
                        drafts_folder = drafts_folder.strip().strip('"')
                        break
            if drafts_folder:
                break

        if not drafts_folder:
            drafts_folder = "Drafts"

        print(f"\nVerwende Entwürfe-Ordner: {drafts_folder}")

        # Create test email
        html_body = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; font-size: 14px; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <p>Sehr geehrte Damen und Herren,</p>
  <p> dies ist ein <strong>Test-Entwurf</strong> vom Akquise-Agenten.</p>
  <hr style="border: none; border-top: 1px solid #ccc;">
  <p><strong>Was wir bieten:</strong></p>
  <ul>
    <li>Technisches Geb&auml;udemanagement</li>
    <li>Mietnebenkostenabrechnung</li>
    <li>Objektbetreuung</li>
    <li>Notfallservice 24/7</li>
  </ul>
  <p>Mit freundlichen Gr&uuml;&szlig;en<br><strong>SE Handwerk GbR</strong></p>
</body>
</html>"""

        msg = MIMEMultipart('alternative')
        msg['From'] = f"SE Handwerk GbR <{config.user}>"
        msg['To'] = "test@example.com"
        msg['Subject'] = "Test-Entwurf: Entlastung für Ihre Hausverwaltung"
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain='sehandwerk.de')

        # Plain text version
        text_body = """Sehr geehrte Damen und Herren,

dies ist ein Test-Entwurf vom Akquise-Agenten.

Was wir bieten:
- Technisches Gebäudemanagement
- Mietnebenkostenabrechnung
- Objektbetreuung
- Notfallservice 24/7

Mit freundlichen Grüßen
SE Handwerk GbR"""

        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        # Save to drafts
        draft_content = msg.as_string()
        if isinstance(draft_content, str):
            draft_content = draft_content.encode('utf-8')

        print(f"\nSpeichere Entwurf...")

        # Try different folder names
        folder_names = [drafts_folder, 'Drafts', 'INBOX.Drafts', 'Draft', 'Entwürfe']

        saved = False
        for folder in folder_names:
            try:
                result = await client.append(
                    draft_content,
                    mailbox=folder,
                    flags='\\Draft',
                    date=None
                )
                if result.result == 'OK':
                    print(f"✅ Entwurf gespeichert in: {folder}")
                    saved = True
                    break
            except Exception as e:
                print(f"   {folder}: {e}")
                continue

        if not saved:
            print("❌ Konnte Entwurf nicht speichern")
            # Try INBOX as fallback
            try:
                result = await client.append(
                    draft_content,
                    mailbox='INBOX',
                    flags='\\Draft',
                    date=None
                )
                if result.result == 'OK':
                    print("✅ Entwurf in INBOX gespeichert")
                    saved = True
            except Exception as e:
                print(f"   INBOX: {e}")

        await client.logout()

        if saved:
            print("\n" + "=" * 60)
            print("✅ ERFOLG! Check deine E-Mail-App 'Entwürfe' Ordner")
            print("=" * 60)
            return True
        else:
            print("\n❌ Entwurf konnte nicht gespeichert werden")
            return False

    except Exception as e:
        print(f"❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_imap())
    sys.exit(0 if success else 1)