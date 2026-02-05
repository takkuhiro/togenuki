ID_TOKEN="${1:-$ID_TOKEN}"
PUBLIC_API_URL="https://xxxx.app"
curl -X POST ${PUBLIC_API_URL}/api/gmail/watch \
  -H "Authorization: Bearer ${ID_TOKEN}"
