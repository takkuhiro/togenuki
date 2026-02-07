# Gmail Push通知設定と処理フロー

このドキュメントでは、Gmail APIのpush通知設定から、通知を受け取った後の処理フローまでを詳細に説明します。

## 目次

1. [概要](#概要)
2. [インフラ構成](#インフラ構成)
3. [Gmail OAuth認証フロー](#gmail-oauth認証フロー)
4. [Gmail Watch設定](#gmail-watch設定)
5. [Push通知受信フロー](#push通知受信フロー)
6. [メール処理フロー](#メール処理フロー)
7. [データモデル](#データモデル)
8. [エラーハンドリング](#エラーハンドリング)
9. [設定値と定数](#設定値と定数)

---

## 概要

togenukiでは、Gmail APIのpush通知機能を利用して、ユーザーのメール受信をリアルタイムで検知します。

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│   Gmail     │────>│  Cloud       │────>│  Cloud Run    │────>│  Database    │
│   Server    │     │  Pub/Sub     │     │  (FastAPI)    │     │  (Cloud SQL) │
└─────────────┘     └──────────────┘     └───────────────┘     └──────────────┘
```

**主要コンポーネント:**
- **Gmail API**: メール監視（Watch API）とメール取得
- **Cloud Pub/Sub**: Gmail通知の受信基盤
- **Cloud Run**: Webhookエンドポイント（FastAPI）
- **Cloud SQL**: メールデータの永続化

---

## インフラ構成

### Pub/Sub設定（Terraform）

**ファイル**: `infrastructures/main.tf`

```hcl
# Pub/Sub Topic
resource "google_pubsub_topic" "gmail_notifications" {
  name = "gmail-notifications"
}

# Pub/Sub Subscription
resource "google_pubsub_subscription" "gmail_push" {
  name  = "gmail-push"
  topic = google_pubsub_topic.gmail_notifications.id

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.api.uri}/api/webhook/gmail"
  }

  ack_deadline_seconds = 20

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}
```

**設定ポイント:**
- Push Endpoint: Cloud Run のURL + `/api/webhook/gmail`
- Acknowledgement Deadline: 20秒
- Retry Policy: 10秒～600秒の指数バックオフ

### Gmail APIサービスアカウント権限

Gmail APIがPub/Subにメッセージをpublishするため、以下の権限が必要です:

```hcl
# Gmail APIサービスアカウントへのPublish権限付与
resource "google_pubsub_topic_iam_binding" "gmail_publish" {
  topic   = google_pubsub_topic.gmail_notifications.id
  role    = "roles/pubsub.publisher"
  members = ["serviceAccount:gmail-api-push@system.gserviceaccount.com"]
}
```

---

## Gmail OAuth認証フロー

### 1. 認可URL取得

**エンドポイント**: `POST /api/auth/gmail/url`

**ファイル**: `apps/api/src/auth/gmail_oauth.py`

```python
def get_authorization_url() -> str:
    """OAuth 2.0認可URLを生成"""
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send",
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"
```

**スコープ:**
- `gmail.readonly`: メール読み取り
- `gmail.send`: メール送信（返信機能用）

### 2. コールバック処理

**エンドポイント**: `POST /api/auth/gmail/callback`

```
認可コード → Access Token + Refresh Token 交換 → DBに保存
```

**ファイル**: `apps/api/src/auth/gmail_oauth.py`

```python
async def exchange_code_for_tokens(code: str) -> dict:
    """認可コードをトークンに交換"""
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(GOOGLE_TOKEN_ENDPOINT, data=data)
    return response.json()
```

**レスポンス例:**
```json
{
  "access_token": "ya29.xxx...",
  "refresh_token": "1//xxx...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

### 3. トークン自動更新

**ファイル**: `apps/api/src/auth/gmail_oauth.py`

```python
async def ensure_valid_access_token(user: User) -> str | None:
    """有効なAccess Tokenを取得（期限切れなら自動更新）"""
    if user.gmail_token_expires_at and user.gmail_token_expires_at > datetime.now(UTC):
        return user.gmail_access_token

    # 期限切れ → Refresh Tokenで更新
    return await refresh_access_token(user.gmail_refresh_token)
```

---

## Gmail Watch設定

### Watch APIの仕組み

Gmail Watch APIは、指定したメールボックスの変更をPub/Subトピックにpushします。

**有効期限**: 7日間（自動更新が必要）

### Watch設定エンドポイント

**エンドポイント**: `POST /api/gmail/watch`

**ファイル**: `apps/api/src/routers/gmail_watch.py`

```python
@router.post("/watch")
async def setup_gmail_watch(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    # 1. OAuthトークン確認
    access_token = await ensure_valid_access_token(current_user, db)

    # 2. Gmail Watch API呼び出し
    result = await gmail_watch_service.setup_watch(access_token)

    # 3. historyIdをDBに保存
    current_user.gmail_history_id = result["historyId"]
    await db.commit()

    return {"message": "Watch setup successful", "historyId": result["historyId"]}
```

### GmailWatchService

**ファイル**: `apps/api/src/services/gmail_watch.py`

```python
async def setup_watch(self, access_token: str) -> dict:
    """Gmail Watch APIを呼び出してPub/Sub通知を設定"""
    headers = {"Authorization": f"Bearer {access_token}"}
    body = {
        "topicName": f"projects/{settings.project_id}/topics/gmail-notifications",
        "labelIds": ["INBOX"],
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/watch",
            headers=headers,
            json=body,
        )

    return response.json()
```

**レスポンス例:**
```json
{
  "historyId": "12345678",
  "expiration": "1706140800000"
}
```

---

## Push通知受信フロー

### Webhookエンドポイント

**エンドポイント**: `POST /api/webhook/gmail`

**ファイル**: `apps/api/src/routers/webhook.py`

### 受信メッセージ形式

Pub/Subからのpushメッセージ:

```json
{
  "message": {
    "data": "eyJlbWFpbEFkZHJlc3MiOiJ1c2VyQGV4YW1wbGUuY29tIiwiaGlzdG9yeUlkIjoiMTIzNDU2Nzg5In0=",
    "messageId": "123456789",
    "publishTime": "2024-01-25T12:00:00.000Z"
  },
  "subscription": "projects/project-id/subscriptions/gmail-push"
}
```

**デコード後のdata:**
```json
{
  "emailAddress": "user@example.com",
  "historyId": "123456789"
}
```

### 処理フロー

```python
@router.post("/webhook/gmail")
async def gmail_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
):
    # 1. メッセージデコード
    body = await request.json()
    data = json.loads(base64.b64decode(body["message"]["data"]))
    email = data["emailAddress"]
    history_id = data["historyId"]

    # 2. 重複チェック（同じhistoryIdは処理済みとしてスキップ）
    if is_duplicate_notification(email, history_id):
        logger.info(f"Duplicate notification skipped: {email}:{history_id}")
        return Response(status_code=200)

    # 3. 即座に200 OKを返却（Pub/Sub requirement）
    # 4. バックグラウンドタスクとして非同期処理をスケジュール
    background_tasks.add_task(process_gmail_notification, email, history_id)

    return Response(status_code=200)
```

### 重複検出メカニズム

```python
# In-memory cache（本番ではRedis/DB推奨）
_processed_history_ids: set[str] = set()

def is_duplicate_notification(email: str, history_id: str) -> bool:
    """同一historyIdの重複通知を検出"""
    cache_key = f"{email}:{history_id}"
    if cache_key in _processed_history_ids:
        return True
    _processed_history_ids.add(cache_key)
    return False
```

**注意**: Cloud Runのインスタンスは複数起動される可能性があるため、本番環境ではRedisやデータベースでの永続化が推奨されます。

---

## メール処理フロー

### バックグラウンド処理

**ファイル**: `apps/api/src/services/email_processor.py`

```python
async def process_notification(self, email_address: str, history_id: str):
    """Gmail通知を処理"""

    # 1. ユーザー検索
    user = await self._get_user_by_email(email_address)
    if not user:
        logger.warning(f"User not found: {email_address}")
        return

    # 2. OAuth状態確認
    if not user.gmail_refresh_token:
        logger.warning(f"Gmail not connected for user: {user.id}")
        return

    # 3. historyId比較（新規メールがあるか確認）
    if user.gmail_history_id and int(history_id) <= int(user.gmail_history_id):
        logger.info(f"No new emails (historyId not advanced)")
        return

    # 4. Access Token取得（必要なら自動更新）
    access_token = await self._get_valid_access_token(user)

    # 5. Gmail履歴取得
    await self._fetch_and_process_messages(user, access_token, history_id)
```

### Gmail履歴取得

**ファイル**: `apps/api/src/services/gmail_service.py`

```python
async def fetch_email_history(
    self,
    access_token: str,
    start_history_id: str
) -> dict:
    """historyId以降の変更履歴を取得"""
    params = {
        "startHistoryId": start_history_id,
        "labelId": "INBOX",
        "historyTypes": "messageAdded",
    }

    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/history",
            headers=headers,
            params=params,
        )

    return response.json()
```

**レスポンス例:**
```json
{
  "history": [
    {
      "id": "123456790",
      "messagesAdded": [
        {
          "message": {
            "id": "abc123",
            "threadId": "thread123",
            "labelIds": ["INBOX", "UNREAD"]
          }
        }
      ]
    }
  ],
  "historyId": "123456795"
}
```

### 個別メッセージ処理

```python
async def _process_single_message(self, user_id: UUID, gmail_message: dict):
    """個別のGmailメッセージを処理"""

    # 1. メッセージ詳細をパース
    parsed = parse_gmail_message(gmail_message)
    # parsed = {
    #   "sender_email": "sender@example.com",
    #   "sender_name": "Sender Name",
    #   "subject": "Email Subject",
    #   "body": "Email body text...",
    #   "received_at": datetime(2024, 1, 25, 12, 0, 0)
    # }

    # 2. Contactに登録されているか確認
    contact = await get_contact_for_email(self.db, user_id, parsed["sender_email"])
    if not contact:
        logger.info(f"Sender not in contacts, skipping: {parsed['sender_email']}")
        return

    # 3. 重複チェック（google_message_id）
    if await email_exists(self.db, gmail_message["id"]):
        logger.info(f"Email already exists: {gmail_message['id']}")
        return

    # 4. Emailレコード作成
    email = Email(
        user_id=user_id,
        contact_id=contact.id,
        google_message_id=gmail_message["id"],
        sender_email=parsed["sender_email"],
        sender_name=parsed["sender_name"],
        subject=parsed["subject"],
        original_body=parsed["body"],
        received_at=parsed["received_at"],
        is_processed=False,  # Phase 4でTrueに更新
    )
    self.db.add(email)
    await self.db.commit()

    # 5. TODO: Phase 4 - AI処理
    # - Gemini: ギャル語変換
    # - Google Cloud TTS: 音声生成
    # - Cloud Storage: 音声ファイルアップロード
```

### メール本文抽出

```python
def extract_email_body(payload: dict) -> str:
    """GmailメッセージのPayloadから本文を抽出"""

    mime_type = payload.get("mimeType", "")

    # 1. text/plain 直接取得
    if mime_type == "text/plain" and "body" in payload:
        data = payload["body"].get("data", "")
        return base64.urlsafe_b64decode(data).decode("utf-8")

    # 2. multipart の場合は再帰的に探索
    if "parts" in payload:
        for part in payload["parts"]:
            # text/plain を優先
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8")

        # text/html をフォールバック
        for part in payload["parts"]:
            if part.get("mimeType") == "text/html":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8")

        # 再帰的に探索
        for part in payload["parts"]:
            result = extract_email_body(part)
            if result:
                return result

    return ""
```

---

## データモデル

### User テーブル

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    firebase_uid: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str]

    # Gmail OAuth
    gmail_refresh_token: Mapped[str | None]
    gmail_access_token: Mapped[str | None]
    gmail_token_expires_at: Mapped[datetime | None]
    gmail_history_id: Mapped[str | None]  # 最後に処理したhistoryId

    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
```

### Contact テーブル

```python
class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    contact_email: Mapped[str]
    contact_name: Mapped[str | None]
    gmail_query: Mapped[str | None]  # Gmail検索クエリ
    is_learning_complete: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
```

### Email テーブル

```python
class Email(Base):
    __tablename__ = "emails"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    contact_id: Mapped[UUID | None] = mapped_column(ForeignKey("contacts.id"))

    google_message_id: Mapped[str] = mapped_column(unique=True)  # 重複防止キー
    sender_email: Mapped[str]
    sender_name: Mapped[str | None]
    subject: Mapped[str | None]
    original_body: Mapped[str | None]

    # Phase 4で更新
    converted_body: Mapped[str | None]  # ギャル語変換後
    audio_url: Mapped[str | None]       # GCS URL

    received_at: Mapped[datetime | None]
    is_processed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
```

---

## エラーハンドリング

### 重複通知への対応

1. **historyIdベースの重複検出**: 同じhistoryIdの通知は処理済みとしてスキップ
2. **google_message_idの一意制約**: DBレベルで同一メールの重複保存を防止
3. **In-memory cache**: インスタンス内での短期的な重複検出

### トークン期限切れへの対応

```python
async def _get_valid_access_token(self, user: User) -> str | None:
    """有効なAccess Tokenを取得（期限切れなら自動更新）"""
    token = await ensure_valid_access_token(user)

    if token != user.gmail_access_token:
        # トークンが更新された場合はDBを更新
        user.gmail_access_token = token
        user.gmail_token_expires_at = datetime.now(UTC) + timedelta(hours=1)
        await self.db.commit()

    return token
```

### Pub/Sub再試行への対応

- Webhookは常に200 OKを即座に返却（10秒以内）
- 200以外を返すとPub/Subが指数バックオフで再試行
- 処理はバックグラウンドタスクで非同期実行

---

## 設定値と定数

### 環境変数

**ファイル**: `.env` / Cloud Run環境変数

```
# Google OAuth
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_REDIRECT_URI=https://api.example.com/api/auth/gmail/callback

# Project
PROJECT_ID=your-gcp-project-id

# Firebase
FIREBASE_CREDENTIALS_PATH=secrets/firebase-service-account.json
```

### 定数

```python
# Gmail API Scopes
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# Pub/Sub Topic
PUBSUB_TOPIC = "projects/{project_id}/topics/gmail-notifications"

# Gmail Watch
WATCH_LABEL_IDS = ["INBOX"]  # INBOXのみ監視
WATCH_EXPIRATION_DAYS = 7    # 7日で期限切れ

# Token
TOKEN_EXPIRY_BUFFER_MINUTES = 5  # 5分前に更新開始
```

---

## 全体フロー図

```
┌────────────────────────────────────────────────────────────────────────────┐
│ 初期設定フロー                                                              │
└────────────────────────────────────────────────────────────────────────────┘

  User                Frontend              API                    Google
   │                     │                   │                       │
   ├──「Gmail連携」───────>│                   │                       │
   │                     ├──POST /auth/gmail/url──>│                  │
   │                     │<─────認可URL─────────────│                  │
   │<─────認可画面へリダイレクト───│                   │                  │
   ├────────────────────────────認可画面────────────────────────────────>│
   │<───────────────────────認可コード（callback）──────────────────────│
   │                     ├──POST /auth/gmail/callback (code)─>│       │
   │                     │                   ├──Token交換────────────>│
   │                     │                   │<─Access/Refresh Token─│
   │                     │<───────Success────│                       │
   │                     │                   │                       │
   ├──「通知ON」──────────>│                   │                       │
   │                     ├──POST /gmail/watch───>│                   │
   │                     │                   ├──users.watch API────>│
   │                     │                   │<───historyId─────────│
   │                     │<───────Success────│                       │


┌────────────────────────────────────────────────────────────────────────────┐
│ 通知受信フロー                                                              │
└────────────────────────────────────────────────────────────────────────────┘

  Gmail          Pub/Sub          Cloud Run            DB            GCS
    │               │                 │                 │              │
    ├──新着メール──>│                 │                 │              │
    │               ├──Push通知────────>│                │              │
    │               │                 ├─デコード        │              │
    │               │                 ├─重複チェック    │              │
    │               │<─────200 OK──────│                 │              │
    │               │                 │                 │              │
    │               │          [Background Task]        │              │
    │               │                 ├─ユーザー検索────>│              │
    │               │                 │<────User────────│              │
    │               │                 ├─OAuth検証       │              │
    │<─────────────────履歴取得API─────│                 │              │
    ├──────────────────履歴データ────>│                 │              │
    │               │                 │                 │              │
    │               │            [各メッセージ処理]     │              │
    │               │                 ├─Contact確認────>│              │
    │               │                 │<────Contact─────│              │
    │               │                 ├─重複確認───────>│              │
    │               │                 ├─Email保存──────>│              │
    │               │                 │                 │              │
    │               │            [TODO: Phase 4]        │              │
    │               │                 ├─Gemini変換      │              │
    │               │                 ├─TTS音声生成     │              │
    │               │                 ├─────────────────────>音声保存─>│
    │               │                 ├─URL更新─────────>│              │
```

---

## 関連ドキュメント

- [ARCHITECTURE.md](./ARCHITECTURE.md) - システム全体のアーキテクチャ
- [SECRETS.md](./SECRETS.md) - シークレット管理
