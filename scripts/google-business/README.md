# SE Handwerk - Google Business Profile Setup

Automatisierte Erstellung des Google Unternehmensprofils via offizieller API.

## Schnellstart

```bash
cd scripts/google-business
npm install
npm run oauth    # Einmalig: Google autorisieren
npm run create   # Unternehmensprofil erstellen
```

## Google Drive Fotos

Nach der Erstellung Fotos hochladen aus:
https://drive.google.com/drive/folders/19OOOcKG9olwTQbCdi5_rJQyaGDRNWH4_

## SEO Ranking Faktoren

✅ Vollständige NAP-Daten (Name, Adresse, Telefon)
✅ Unternehmenskategorien (primär + sekundär)
✅ Einsatzgebiet definiert
✅ SEO-optimierte Beschreibung mit Keywords
✅ Öffnungszeiten
✅ Website verlinkt
📋 Fotos (manuell nach Verifizierung)
📋 Bewertungen (Kunden bitten)
📋 Regelmäßige Beiträge (über Dashboard)

## Troubleshooting

### "Access Denied"
- OAuth-Zustimmungsbildschirm prüfen
- Sich selbst als Testnutzer hinzufügen

### "Duplicate Location"
- Unternehmen existiert bereits
- Bestehenden Eintrag beanspruchen

### "API not enabled"
- Business Profile API in Cloud Console aktivieren