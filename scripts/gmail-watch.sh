#!/bin/bash
# Gmail Watch Setup Script
# Usage: ./gmail-watch.sh <access_token>
#
# This script sets up Gmail push notifications using the Gmail API.
# You need a valid OAuth access token with gmail.readonly scope.
#
# To get an access token:
# 1. Use the application's Gmail OAuth flow
# 2. Or use Google OAuth Playground: https://developers.google.com/oauthplayground/

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-your-gcp-project-id}"
TOPIC_NAME="projects/${PROJECT_ID}/topics/gmail-notifications"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check for access token
ACCESS_TOKEN="${1:-$GMAIL_ACCESS_TOKEN}"

if [ -z "${ACCESS_TOKEN}" ]; then
    echo -e "${RED}Error: Access token required${NC}"
    echo ""
    echo "Usage: ./gmail-watch.sh <access_token>"
    echo "   or: GMAIL_ACCESS_TOKEN=<token> ./gmail-watch.sh"
    echo ""
    echo "To get an access token:"
    echo "1. Complete Gmail OAuth in the application"
    echo "2. Or use Google OAuth Playground:"
    echo "   https://developers.google.com/oauthplayground/"
    echo "   - Select 'Gmail API v1' > 'gmail.readonly'"
    echo "   - Authorize and get access token"
    exit 1
fi

echo -e "${GREEN}=== Gmail Watch Setup ===${NC}"
echo "Topic: ${TOPIC_NAME}"
echo ""

# Call Gmail API users.watch
echo -e "${YELLOW}Setting up Gmail watch...${NC}"

RESPONSE=$(curl -s -X POST \
    "https://gmail.googleapis.com/gmail/v1/users/me/watch" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"topicName\": \"${TOPIC_NAME}\",
        \"labelIds\": [\"INBOX\"]
    }")

# Check response
if echo "${RESPONSE}" | grep -q "historyId"; then
    echo -e "${GREEN}✓ Gmail watch setup successful!${NC}"
    echo ""
    echo "Response:"
    echo "${RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${RESPONSE}"
    echo ""
    echo -e "${YELLOW}Note: Gmail watch expires after 7 days.${NC}"
    echo "You'll need to renew it periodically."
else
    echo -e "${RED}✗ Gmail watch setup failed${NC}"
    echo ""
    echo "Response:"
    echo "${RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${RESPONSE}"
    exit 1
fi
