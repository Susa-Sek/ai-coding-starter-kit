#!/bin/bash
# Auto-deploy script with automatic token detection
# Usage: ./scripts/deploy.sh [--prod]

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Deploy Script${NC}\n"

# Detect Vercel token
VERCEL_TOKEN=""

# Method 1: Check ~/.vercel/auth.json
if [ -f ~/.vercel/auth.json ]; then
    VERCEL_TOKEN=$(cat ~/.vercel/auth.json | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
    echo -e "${GREEN}✅ Found Vercel token in ~/.vercel/auth.json${NC}"
fi

# Method 2: Check environment variable
if [ -z "$VERCEL_TOKEN" ] && [ -n "$VERCEL_TOKEN_ENV" ]; then
    VERCEL_TOKEN="$VERCEL_TOKEN_ENV"
    echo -e "${GREEN}✅ Found Vercel token in environment${NC}"
fi

# Method 3: Check .env.local
if [ -z "$VERCEL_TOKEN" ] && [ -f .env.local ]; then
    VERCEL_TOKEN=$(grep "VERCEL_TOKEN=" .env.local 2>/dev/null | cut -d'=' -f2)
    if [ -n "$VERCEL_TOKEN" ]; then
        echo -e "${GREEN}✅ Found Vercel token in .env.local${NC}"
    fi
fi

# Deploy
if [ -n "$VERCEL_TOKEN" ]; then
    echo -e "\n${YELLOW}Deploying to Vercel...${NC}\n"

    if [ "$1" == "--prod" ]; then
        vercel --prod --yes --token "$VERCEL_TOKEN"
    else
        vercel --yes --token "$VERCEL_TOKEN"
    fi
else
    echo -e "${RED}❌ No Vercel token found!${NC}"
    echo -e "\nPlease run: ${YELLOW}vercel login${NC}"
    echo -e "Or set: ${YELLOW}export VERCEL_TOKEN_ENV=your_token${NC}"
    exit 1
fi

echo -e "\n${GREEN}✅ Deployment complete!${NC}"