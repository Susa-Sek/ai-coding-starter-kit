#!/usr/bin/env python3
"""
Test IMAP Draft Saver - Speichert E-Mail-Entwürfe direkt im E-Mail-Konto.

Usage:
    python scripts/test_imap_drafts.py

Voraussetzungen:
    - IMAP-Zugangsdaten in .env konfiguriert
    - aioimaplib installiert: pip install aioimaplib
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.storage.imap_drafts import IMAPDraftSaver, IMAPConfig


async def test_connection(saver: IMAPDraftSaver):
    """Test IMAP connection."""
    print("=" * 60)
    print("Testing IMAP connection...")
    print("=" * 60)

    if await saver.connect():
        print("✅ Connected to IMAP server")
        await saver.disconnect()
        return True
    else:
        print("❌ Failed to connect to IMAP server")
        return False


async def test_save_draft(saver: IMAPDraftSaver):
    """Test saving a draft to IMAP folder."""
    print("\n" + "=" * 60)
    print("Testing draft save to IMAP...")
    print("=" * 60)

    # Sample HTML email
    html_body = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
</head>
<body style="font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; padding: 20px;">

  <p style="margin: 0 0 16px 0;">Sehr geehrte Frau Schmidt,</p>

  <p style="margin: 0 0 16px 0;">als ich auf Ihrer Webseite die Leistungen im Bereich Immobilienverwaltung gelesen habe, war ich beeindruckt von Ihrem Angebot.</p>

  <hr style="border: none; border-top: 1px solid #cccccc; margin: 16px 0;">

  <p style="margin: 0 0 8px 0;"><strong>Warum ich Sie anschreibe:</strong></p>

  <p style="margin: 0 0 16px 0;">Die Hausverwaltung wird immer anspruchsvoller. Steigende Energiekosten, neue gesetzliche Vorgaben und h&ouml;here Erwartungen der Eigent&uuml;mer.</p>

  <hr style="border: none; border-top: 1px solid #cccccc; margin: 16px 0;">

  <p style="margin: 0 0 8px 0;"><strong>Was wir bieten:</strong></p>

  <ul style="margin: 0 0 16px 0; padding-left: 20px;">
    <li style="margin-bottom: 8px;"><strong>Technisches Geb&auml;udemanagement</strong> – Instandhaltung und Reparaturen aus einer Hand</li>
    <li style="margin-bottom: 8px;"><strong>Mietnebenkostenabrechnung</strong> – Transparent, fristgerecht und rechtssicher</li>
    <li style="margin-bottom: 8px;"><strong>Objektbetreuung</strong> – Regelm&auml;&szlig;ige Kontrollg&auml;nge</li>
    <li style="margin-bottom: 0;"><strong>Notfallservice</strong> – 24/7 Erreichbarkeit</li>
  </ul>

  <hr style="border: none; border-top: 1px solid #cccccc; margin: 16px 0;">

  <p>Mit freundlichen Gr&uuml;&szlig;en<br>
  <strong>Max Mustermann</strong><br>
  SE Handwerk GbR</p>

</body>
</html>"""

    subject = "Test-Entwurf: Muster Hausverwaltung GmbH – Entlastung für Ihre Hausverwaltung"

    result = await saver.save_draft(
        to="test@example.com",  # Test-Empfänger
        subject=subject,
        body_html=html_body,
        from_name="SE Handwerk GbR",
        from_email=os.getenv('SMTP_USER', 'kontakt@sehandwerk.de')
    )

    if result:
        print(f"✅ Draft saved successfully!")
        print(f"   Subject: {subject}")
        print(f"   Check your email 'Drafts' folder")
        return True
    else:
        print("❌ Failed to save draft")
        return False


async def main():
    """Main test function."""
    # Load environment variables
    load_dotenv()

    print("=" * 60)
    print("IMAP Draft Saver Test")
    print("=" * 60)

    # Check configuration
    imap_host = os.getenv('IMAP_HOST')
    imap_user = os.getenv('IMAP_USER') or os.getenv('SMTP_USER')
    imap_password = os.getenv('IMAP_PASSWORD') or os.getenv('SMTP_PASSWORD')

    if not imap_host or not imap_user or not imap_password:
        print("❌ IMAP not configured!")
        print("\nPlease set in .env:")
        print("  IMAP_HOST=mail.privateemail.com")
        print("  IMAP_PORT=993")
        print("  IMAP_USER=your-email@domain.de")
        print("  IMAP_PASSWORD=your-password")
        print("\nOr use SMTP credentials:")
        print("  SMTP_USER and SMTP_PASSWORD")
        return False

    print(f"IMAP Host: {imap_host}")
    print(f"IMAP User: {imap_user}")
    print(f"IMAP Port: {os.getenv('IMAP_PORT', '993')}")

    # Create IMAP config
    config = IMAPConfig(
        host=imap_host,
        port=int(os.getenv('IMAP_PORT', '993')),
        user=imap_user,
        password=imap_password,
        use_ssl=os.getenv('IMAP_USE_SSL', 'true').lower() == 'true',
        drafts_folder=os.getenv('IMAP_DRAFTS_FOLDER', 'Drafts')
    )

    # Create saver
    saver = IMAPDraftSaver(config)

    # Test connection
    if not await test_connection(saver):
        return False

    # Test saving draft
    if not await test_save_draft(saver):
        return False

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print("\nCheck your email client's Drafts folder for the test draft.")

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)