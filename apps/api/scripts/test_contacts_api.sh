#!/bin/bash
# Contact Management API テストスクリプト
# Phase 3: APIエンドポイントの動作確認用
#
# 使用方法:
#   1. TOKEN と BASE_URL を環境変数で設定するか、下記の値を直接編集
#   2. chmod +x test_contacts_api.sh
#   3. ./test_contacts_api.sh

# ===========================================
# 設定 (環境変数が未設定の場合はデフォルト値を使用)
# ===========================================
BASE_URL="${BASE_URL:-https://YOUR_API_URL_HERE}"
TOKEN="${TOKEN:-YOUR_FIREBASE_ID_TOKEN_HERE}"

# テスト用メールアドレス
TEST_EMAIL="test-$(date +%s)@example.com"
EXISTING_EMAIL="boss@company.com"

echo "========================================"
echo "Contact Management API テスト"
echo "========================================"
echo "BASE_URL: ${BASE_URL}"
echo "TEST_EMAIL: ${TEST_EMAIL}"
echo ""

# ===========================================
# テスト1: 認証なしでのアクセス (401確認)
# ===========================================
echo "=== テスト1: 認証なしでPOST (401確認) ==="
curl -s -X POST "${BASE_URL}/api/contacts" \
  -H "Content-Type: application/json" \
  -d '{"contactEmail": "test@example.com"}' \
  -w "\nHTTP Status: %{http_code}\n"
echo ""

echo "=== テスト2: 認証なしでGET (401確認) ==="
curl -s -X GET "${BASE_URL}/api/contacts" \
  -w "\nHTTP Status: %{http_code}\n"
echo ""

echo "=== テスト3: 認証なしでDELETE (401確認) ==="
curl -s -X DELETE "${BASE_URL}/api/contacts/00000000-0000-0000-0000-000000000000" \
  -w "\nHTTP Status: %{http_code}\n"
echo ""

# ===========================================
# テスト4: 無効なメールアドレス形式 (422確認)
# ===========================================
echo "=== テスト4: 無効なメールアドレス形式 (422確認) ==="
curl -s -X POST "${BASE_URL}/api/contacts" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"contactEmail": "invalid-email"}' \
  -w "\nHTTP Status: %{http_code}\n"
echo ""

# ===========================================
# テスト5: 連絡先一覧取得 (GET /api/contacts)
# ===========================================
echo "=== テスト5: 連絡先一覧取得 (200確認) ==="
curl -s -X GET "${BASE_URL}/api/contacts" \
  -H "Authorization: Bearer ${TOKEN}" \
  -w "\nHTTP Status: %{http_code}\n"
echo ""

# ===========================================
# テスト6: 存在しないIDの削除 (404確認)
# ===========================================
echo "=== テスト6: 存在しないIDの削除 (404確認) ==="
curl -s -X DELETE "${BASE_URL}/api/contacts/00000000-0000-0000-0000-000000000000" \
  -H "Authorization: Bearer ${TOKEN}" \
  -w "\nHTTP Status: %{http_code}\n"
echo ""

# ===========================================
# テスト7: 新規連絡先登録 (POST /api/contacts)
# ===========================================
echo "=== テスト7: 新規連絡先登録 (201確認) ==="
RESPONSE=$(curl -s -X POST "${BASE_URL}/api/contacts" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"contactEmail\": \"${TEST_EMAIL}\", \"contactName\": \"テスト連絡先\"}" \
  -w "\nHTTP_STATUS:%{http_code}")

BODY=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:.*//')
STATUS=$(echo "$RESPONSE" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
echo "$BODY"
echo "HTTP Status: $STATUS"

# 新規作成した連絡先のIDを抽出
NEW_CONTACT_ID=$(echo "$BODY" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "Created Contact ID: $NEW_CONTACT_ID"
echo ""

# ===========================================
# テスト8: 登録確認 (GET /api/contacts)
# ===========================================
echo "=== テスト8: 登録確認 (GET) ==="
curl -s -X GET "${BASE_URL}/api/contacts" \
  -H "Authorization: Bearer ${TOKEN}" \
  -w "\nHTTP Status: %{http_code}\n"
echo ""

# ===========================================
# テスト9: 重複登録 (409確認)
# ===========================================
echo "=== テスト9: 重複登録 (409確認) ==="
curl -s -X POST "${BASE_URL}/api/contacts" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"contactEmail\": \"${TEST_EMAIL}\"}" \
  -w "\nHTTP Status: %{http_code}\n"
echo ""

# ===========================================
# テスト10: 連絡先削除 (DELETE /api/contacts/{id})
# ===========================================
if [ -n "$NEW_CONTACT_ID" ] && [ "$NEW_CONTACT_ID" != "null" ]; then
  echo "=== テスト10: 連絡先削除 (204確認) ==="
  curl -s -X DELETE "${BASE_URL}/api/contacts/${NEW_CONTACT_ID}" \
    -H "Authorization: Bearer ${TOKEN}" \
    -w "\nHTTP Status: %{http_code}\n"
  echo ""

  echo "=== テスト11: 削除確認 (GET) ==="
  curl -s -X GET "${BASE_URL}/api/contacts" \
    -H "Authorization: Bearer ${TOKEN}" \
    -w "\nHTTP Status: %{http_code}\n"
  echo ""
else
  echo "=== テスト10: スキップ (連絡先IDが取得できませんでした) ==="
  echo ""
fi

echo "========================================"
echo "テスト完了"
echo "========================================"

# ===========================================
# 個別テスト用コマンド (コピペ用)
# ===========================================
: <<'INDIVIDUAL_COMMANDS'

# --- 連絡先登録 ---
curl -s -X POST "${BASE_URL}/api/contacts" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"contactEmail": "example@example.com", "contactName": "名前", "gmailQuery": "from:example@example.com"}' \
  -w "\nHTTP Status: %{http_code}\n"

# --- 連絡先一覧取得 ---
curl -s -X GET "${BASE_URL}/api/contacts" \
  -H "Authorization: Bearer ${TOKEN}" \
  -w "\nHTTP Status: %{http_code}\n"

# --- 連絡先削除 ---
curl -s -X DELETE "${BASE_URL}/api/contacts/{CONTACT_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -w "\nHTTP Status: %{http_code}\n"

INDIVIDUAL_COMMANDS
