#!/bin/bash
# Database migration script with automatic credential detection
# Usage: ./scripts/migrate.sh <migration-file.sql>

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🗄️ Database Migration Script${NC}\n"

# Check for migration file
if [ -z "$1" ]; then
    echo -e "${RED}Usage: ./scripts/migrate.sh <migration-file.sql>${NC}"
    exit 1
fi

MIGRATION_FILE="$1"

if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}❌ Migration file not found: $MIGRATION_FILE${NC}"
    exit 1
fi

# Database credentials (from chorechamp context)
DB_HOST="aws-0-eu-central-1.pooler.supabase.com"
DB_PORT="6543"
DB_NAME="postgres"
DB_USER="postgres.uyfogthmpmenivnyiioe"

# Check for password in environment or .env.local
DB_PASSWORD=""

if [ -n "$SUPABASE_DB_PASSWORD" ]; then
    DB_PASSWORD="$SUPABASE_DB_PASSWORD"
    echo -e "${GREEN}✅ Found DB password in environment${NC}"
elif [ -f .env.local ]; then
    DB_PASSWORD=$(grep "SUPABASE_DB_PASSWORD=" .env.local 2>/dev/null | cut -d'=' -f2)
    if [ -n "$DB_PASSWORD" ]; then
        echo -e "${GREEN}✅ Found DB password in .env.local${NC}"
    fi
fi

if [ -z "$DB_PASSWORD" ]; then
    echo -e "${YELLOW}⚠️ No DB password found. Please set SUPABASE_DB_PASSWORD or add to .env.local${NC}"
    echo -e "\nEnter password manually:"
    read -s DB_PASSWORD
fi

# Build connection string
export PGPASSWORD="$DB_PASSWORD"
CONNECTION_STRING="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"

echo -e "\n${YELLOW}Running migration: $MIGRATION_FILE${NC}\n"

# Run migration
psql "$CONNECTION_STRING" -f "$MIGRATION_FILE"

echo -e "\n${GREEN}✅ Migration complete!${NC}"

# Unset password
unset PGPASSWORD