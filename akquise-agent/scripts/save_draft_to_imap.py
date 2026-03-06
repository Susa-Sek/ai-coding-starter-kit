#!/usr/bin/env python3
"""
Save Email Draft to IMAP - Speichert HTML-E-Mail direkt im E-Mail-Entwürfe-Ordner.

Usage:
    python scripts/save_draft_to_imap.py --to empfaenger@firma.de --subject "Betreff" --template initial_contact

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


async def save_draft_to_imap(
    to: str,
    subject: str,
    body_html: str,
    body_text: str = None,
    from_name: str = "SE Handwerk GbR",
    from_email: str = None
) -> bool:
    """
    Save a draft email directly to IMAP Drafts folder.

    Args:
        to: Recipient email address
        subject: Email subject
        body_html: HTML body content
        body_text: Plain text body (auto-generated from HTML if not provided)
        from_name: Sender name
        from_email: Sender email

    Returns:
        True if draft saved successfully
    """
    # Load environment variables
    load_dotenv()

    # Get IMAP credentials
    imap_host = os.getenv('IMAP_HOST') or os.getenv('SMTP_HOST', 'mail.privateemail.com')
    imap_user = os.getenv('IMAP_USER') or os.getenv('SMTP_USER', '')
    imap_password = os.getenv('IMAP_PASSWORD') or os.getenv('SMTP_PASSWORD', '')
    imap_port = int(os.getenv('IMAP_PORT', '993'))

    if not imap_user or not imap_password:
        print("❌ IMAP/SMTP credentials not configured!")
        print("\nSet in .env:")
        print("  SMTP_USER=your-email@domain.de")
        print("  SMTP_PASSWORD=your-password")
        return False

    # Create IMAP config
    config = IMAPConfig(
        host=imap_host,
        port=imap_port,
        user=imap_user,
        password=imap_password,
        use_ssl=True,
        drafts_folder=os.getenv('IMAP_DRAFTS_FOLDER', 'Drafts')
    )

    # Create saver and connect
    saver = IMAPDraftSaver(config)

    print(f"Connecting to {imap_host}:{imap_port}...")

    if not await saver.connect():
        print("❌ Failed to connect to IMAP server")
        return False

    print(f"Saving draft to '{config.drafts_folder}' folder...")

    # Save draft
    from_email = from_email or imap_user
    result = await saver.save_draft(
        to=to,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        from_name=from_name,
        from_email=from_email
    )

    await saver.disconnect()

    if result:
        print(f"✅ Draft saved successfully!")
        print(f"   To: {to}")
        print(f"   Subject: {subject}")
        print(f"\n   Check your email client's 'Drafts' folder.")
    else:
        print("❌ Failed to save draft")

    return result


async def main():
    """Demo: Save a test draft."""
    load_dotenv()

    # Sample HTML email (from templates)
    html_body = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
</head>
<body style="font-family: Arial, Helvetica, sans-serif; font-size: 14px; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; padding: 20px;">

  <p style="margin: 0 0 16px 0;">Sehr geehrte Damen und Herren,</p>

  <p style="margin: 0 0 16px 0;">als regionaler Partner aus <strong>Heilbronn und Umgebung</strong> habe ich Ihr Unternehmen mit Interesse zur Kenntnis genommen.</p>

  <hr style="border: none; border-top: 1px solid #cccccc; margin: 16px 0;">

  <p style="margin: 0 0 8px 0;"><strong>Warum ich Sie anschreibe:</strong></p>

  <p style="margin: 0 0 16px 0;">Die Hausverwaltung wird immer anspruchsvoller. Steigende Energiekosten, neue gesetzliche Vorgaben und h&ouml;here Erwartungen der Eigent&uuml;mer – das kennen Sie aus dem Alltag.</p>

  <hr style="border: none; border-top: 1px solid #cccccc; margin: 16px 0;">

  <p style="margin: 0 0 8px 0;"><strong>Was wir bieten:</strong></p>

  <p style="margin: 0 0 12px 0;">Die <strong>SE Handwerk GbR</strong> aus Heilbronn und Umgebung unterst&uuml;tzt Hausverwaltungen bei:</p>

  <ul style="margin: 0 0 16px 0; padding-left: 20px;">
    <li style="margin-bottom: 8px;"><strong>Technisches Geb&auml;udemanagement</strong> – Instandhaltung und Reparaturen aus einer Hand</li>
    <li style="margin-bottom: 8px;"><strong>Mietnebenkostenabrechnung</strong> – Transparent, fristgerecht und rechtssicher</li>
    <li style="margin-bottom: 8px;"><strong>Objektbetreuung</strong> – Regelm&auml;&szlig;ige Kontrollg&auml;nge mit l&uuml;ckenloser Dokumentation</li>
    <li style="margin-bottom: 0;"><strong>Notfallservice</strong> – 24/7 Erreichbarkeit f&uuml;r Ihre Mieter bei dringenden F&auml;llen</li>
  </ul>

  <hr style="border: none; border-top: 1px solid #cccccc; margin: 16px 0;">

  <p style="margin: 0 0 8px 0;"><strong>Das Angebot:</strong></p>

  <p style="margin: 0 0 16px 0;">Ein unverbindliches, kurzes Telefonat. Mehr nicht.</p>

  <p style="margin: 0 0 16px 0;">Ich zeige Ihnen konkrete Beispiele, wie wir andere Hausverwaltungen in Heilbronn und Umgebung entlasten. Danach entscheiden Sie, ob eine Zusammenarbeit f&uuml;r Sie interessant ist.</p>

  <p style="margin: 0 0 8px 0;"><strong>Wann passt es Ihnen?</strong></p>

  <ul style="margin: 0 0 16px 0; padding-left: 20px;">
    <li style="margin-bottom: 4px;">Vormittag (9-12 Uhr)</li>
    <li style="margin-bottom: 4px;">Nachmittag (14-17 Uhr)</li>
    <li style="margin-bottom: 0;">Nach Vereinbarung</li>
  </ul>

  <p style="margin: 0 0 16px 0;">Antworten Sie einfach auf diese E-Mail oder nennen Sie mir telefonisch Ihren Wunschtermin.</p>

  <hr style="border: none; border-top: 1px solid #cccccc; margin: 16px 0;">

  <p>Mit freundlichen Gr&uuml;&szlig;en<br>
  <strong>Max Mustermann</strong><br>
  SE Handwerk GbR<br>
  +49 7131 XXXXXXX<br>
  kontakt@se-handwerk.de</p>

  <p style="font-size: 13px; color: #666666; margin-top: 16px;"><em>PS: Referenzen aus Heilbronn und Umgebung sende ich gerne auf Anfrage.</em></p>

</body>
</html>"""

    # Get recipient from command line or use default
    to = sys.argv[1] if len(sys.argv) > 1 else "test@example.com"
    subject = "Test: Entlastung für Ihre Hausverwaltung aus der Region"

    await save_draft_to_imap(
        to=to,
        subject=subject,
        body_html=html_body
    )


if __name__ == "__main__":
    asyncio.run(main())