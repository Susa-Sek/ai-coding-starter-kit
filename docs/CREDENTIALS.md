# Credentials & Tokens

> Automatische Token-Erkennung für Deployments und lokale Entwicklung.

## Übersicht

| Service | Speicherort | Automatisch erkannt |
|---------|-------------|---------------------|
| Vercel | `~/.vercel/auth.json` | ✅ Ja |
| Supabase | `.env.local` | ✅ Ja |
| Database (Supabase) | `.env.local` | ✅ Ja |

---

## Vercel Token

### Speicherort
```bash
~/.vercel/auth.json
```

### Token auslesen
```bash
cat ~/.vercel/auth.json | jq -r '.token'
# Oder ohne jq:
cat ~/.vercel/auth.json | grep -o '"token":"[^"]*"' | cut -d'"' -f4
```

### Deployment mit Token
```bash
# Automatisch (empfohlen)
./scripts/deploy.sh --prod

# Manuell
vercel --prod --token "$(cat ~/.vercel/auth.json | jq -r '.token')"
```

### Token erneuern
```bash
vercel login
```

---

## Supabase Credentials

### Speicherort
```bash
# Projekt-spezifisch
chorechamp/.env.local

# Variablen
NEXT_PUBLIC_SUPABASE_URL=https://uyfogthmpmenivnyiioe.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Database Connection String
```
# Transaction Pooler (Port 6543) - für Migrationen
postgresql://postgres.uyfogthmpmenivnyiioe:[PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres

# Session Pooler (Port 5432) - für langlaufende Verbindungen
postgresql://postgres.uyfogthmpmenivnyiioe:[PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:5432/postgres

# Direct Connection - für Admin-Operationen
postgresql://postgres:[PASSWORD]@db.uyfogthmpmenivnyiioe.supabase.co:5432/postgres
```

---

## Skills & Agents

### Deploy Skill
Der Deploy-Skill sucht automatisch in dieser Reihenfolge:
1. `~/.vercel/auth.json` (Vercel CLI Login)
2. `VERCEL_TOKEN` Environment Variable
3. `.env.local` (VERCEL_TOKEN=...)

### Backend Skill
Der Backend-Skill nutzt automatisch:
- `.env.local` für Supabase URL und Keys
- `DATABASE_URL` für direkte Datenbankverbindungen

---

## Vercel Dashboard

### Projekt-Info
- **Project Name:** chorechamp
- **Project ID:** `prj_e3z4uWR6CiUEUmdUWikgA6FQiUSR`
- **Org ID:** `team_aQ1cp1oCw7xI20IPCbUzj7ye`
- **Production URL:** https://chorechamp-phi.vercel.app

### Environment Variables (im Vercel Dashboard setzen)
```
NEXT_PUBLIC_SUPABASE_URL=https://uyfogthmpmenivnyiioe.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Sicherheit

### NICHT committen
- `.env.local`
- `~/.vercel/auth.json`
- Database Passwörter
- API Keys

### Bereits in .gitignore
```
.env.local
.env.*.local
.vercel/
```

---

## Troubleshooting

### "Token not valid"
```bash
vercel login
```

### "Environment variables not available"
Im Vercel Dashboard: Settings → Environment Variables

### "Database connection failed"
- Supabase Projekt aktiv? (Free tier pausiert nach Inaktivität)
- RLS Policies korrekt?
- Connection String richtig?