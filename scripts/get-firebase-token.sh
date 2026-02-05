#!/bin/bash
# Get Firebase ID Token Script
# Usage: ./get-firebase-token.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check for required environment variables or arguments
FIREBASE_API_KEY="${FIREBASE_API_KEY:-}"
EMAIL="${1:-$FIREBASE_EMAIL}"
PASSWORD="${2:-$FIREBASE_PASSWORD}"

if [ -z "${FIREBASE_API_KEY}" ]; then
    echo -e "${RED}Error: FIREBASE_API_KEY is required${NC}"
    echo ""
    echo "Set it via environment variable:"
    echo "  export FIREBASE_API_KEY=<your-web-api-key>"
    echo ""
    echo "Find it in Firebase Console > Project Settings > General > Web API Key"
    exit 1
fi

if [ -z "${EMAIL}" ] || [ -z "${PASSWORD}" ]; then
    echo -e "${RED}Error: Email and password are required${NC}"
    echo ""
    echo "Usage: ./get-firebase-token.sh <email> <password>"
    echo "   or: FIREBASE_EMAIL=<email> FIREBASE_PASSWORD=<password> ./get-firebase-token.sh"
    exit 1
fi

echo -e "${GREEN}=== Firebase ID Token Generator ===${NC}"
echo ""

# Sign in with email/password
RESPONSE=$(curl -s -X POST \
    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${FIREBASE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"${EMAIL}\",
        \"password\": \"${PASSWORD}\",
        \"returnSecureToken\": true
    }")

# Check for error
if echo "${RESPONSE}" | grep -q '"error"'; then
    echo -e "${RED}Authentication failed${NC}"
    echo "${RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${RESPONSE}"
    exit 1
fi

# Extract ID token
ID_TOKEN=$(echo "${RESPONSE}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('idToken', ''))" 2>/dev/null)

if [ -z "${ID_TOKEN}" ]; then
    echo -e "${RED}Failed to extract ID token${NC}"
    echo "${RESPONSE}"
    exit 1
fi

echo -e "${GREEN}Successfully authenticated!${NC}"
echo ""
echo -e "${YELLOW}Firebase ID Token:${NC}"
echo "${ID_TOKEN}"
echo ""
echo -e "${YELLOW}Token expires in 1 hour.${NC}"
echo ""
echo -e "Test Gmail Watch API:"
echo "curl -X POST https://togenuki-api-bkndgb2cpa-an.a.run.app/api/gmail/watch \\"
echo "  -H \"Authorization: Bearer ${ID_TOKEN}\""
