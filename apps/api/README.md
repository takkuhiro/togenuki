<p align="center">
  <img src="../../assets/icon_square_transparent.png" alt="TogeNuki" width="120" />
</p>

# TogeNuki API

TogeNuki のバックエンド API サービスです。FastAPI + SQLAlchemy で構築され、メール処理・AI変換・音声合成・返信送信などの機能を提供します。

## 技術スタック

| 項目 | 技術 |
|------|------|
| **フレームワーク** | FastAPI |
| **言語** | Python 3.10+ |
| **ORM** | SQLAlchemy (async) |
| **DB** | PostgreSQL (Cloud SQL) |
| **マイグレーション** | Alembic |
| **AI (LLM)** | Gemini 2.5 Flash (google-genai) |
| **AI (TTS)** | Google Cloud Text-to-Speech |
| **ストレージ** | Google Cloud Storage |
| **認証** | Firebase Admin SDK |
| **テスト** | pytest + pytest-asyncio |
| **Linter** | Ruff |

## ディレクトリ構成

```
src/
├── main.py            # FastAPI アプリケーションエントリーポイント
├── config.py          # 設定管理 (pydantic-settings)
├── database.py        # DB接続設定
├── models.py          # SQLAlchemy ORM モデル
├── routers/           # API エンドポイント
│   ├── emails.py          # メール一覧
│   ├── reply.py           # 返信清書・送信
│   ├── contacts.py        # 連絡先管理
│   ├── webhook.py         # Gmail Pub/Sub Webhook
│   ├── gmail_oauth.py     # Gmail OAuth 認証
│   └── gmail_watch.py     # Gmail Push通知設定
├── services/          # ビジネスロジック
│   ├── email_processor.py # メール処理 (ギャル変換 + TTS)
│   ├── tts_service.py     # 音声合成サービス
│   └── learning_service.py # コンテキスト学習サービス
├── repositories/      # データアクセス層
│   ├── email_repository.py
│   └── contact_repository.py
├── schemas/           # Pydantic リクエスト/レスポンスモデル
├── auth/              # 認証関連
│   ├── firebase_admin.py  # Firebase 初期化
│   ├── gmail_oauth.py     # Gmail OAuth ユーティリティ
│   └── middleware.py      # 認証ミドルウェア
└── utils/             # ユーティリティ

alembic/               # データベースマイグレーション
tests/                 # テストファイル
```

## セットアップ

### 前提条件

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (パッケージマネージャー)
- Firebase サービスアカウント JSON (`secrets/firebase-service-account.json`)
- Google Cloud OAuth クレデンシャル

### インストール

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 環境変数

`.env` ファイルを作成し、以下の値を設定してください。

```env
# Firebase
GOOGLE_APPLICATION_CREDENTIALS=secrets/firebase-service-account.json

# Gmail OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5173/auth/gmail/callback

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/togenuki

# Google Cloud
GCS_BUCKET_NAME=your-bucket-name
GOOGLE_CLOUD_PROJECT=your-project-id

# Pub/Sub
PUBSUB_TOPIC=projects/your-project/topics/gmail-notifications

# App
APP_NAME=TogeNuki API
DEBUG=true
```

## 開発

```bash
# 開発サーバー起動 (http://localhost:8000)
uvicorn src.main:app --reload

# APIドキュメント
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

## テスト

```bash
pytest
```

## コード品質

```bash
# lint
ruff check src/

# lint 自動修正
ruff check --fix src/

# 型チェック
mypy src/
```

## データベースマイグレーション

```bash
# マイグレーション生成
alembic revision --autogenerate -m "description"

# マイグレーション適用
alembic upgrade head

# マイグレーション状態確認
alembic current
```

## API エンドポイント

### 一般

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/` | アプリケーション情報 |
| GET | `/health` | ヘルスチェック |

### Gmail OAuth (`/api/auth/gmail`)

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/auth/gmail/url` | OAuth認証URL取得 | 要 |
| POST | `/api/auth/gmail/callback` | OAuthコールバック処理 | 要 |
| GET | `/api/auth/gmail/status` | Gmail連携状態確認 | 要 |

### メール (`/api`)

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/emails` | メール一覧取得 | 要 |

### 返信 (`/api`)

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| POST | `/api/emails/{email_id}/compose-reply` | 返信文の清書 (AI生成) | 要 |
| POST | `/api/emails/{email_id}/send-reply` | 返信メール送信 | 要 |

### 連絡先 (`/api`)

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| POST | `/api/contacts` | 連絡先登録 (+ バックグラウンド学習開始) | 要 |
| GET | `/api/contacts` | 連絡先一覧取得 | 要 |
| DELETE | `/api/contacts/{contact_id}` | 連絡先削除 | 要 |
| POST | `/api/contacts/{contact_id}/retry` | 学習リトライ | 要 |

### Webhook

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| POST | `/gmail` | Gmail Pub/Sub Webhook受信 | 不要 (Pub/Sub) |

### Gmail Watch

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| POST | `/watch` | Gmail Push通知の設定 | 要 |
| DELETE | `/watch` | Gmail Push通知の停止 | 要 |

## デプロイ (Cloud Run)

### deploy.sh を使用

```bash
export PROJECT_ID="your-project-id"
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_REDIRECT_URI="https://your-frontend-url/auth/gmail/callback"
export DATABASE_URL="postgresql+asyncpg://user:password@/togenuki?host=/cloudsql/PROJECT:REGION:INSTANCE"

./deploy.sh
```

### 手動デプロイ

```bash
# イメージのビルドとプッシュ
gcloud builds submit --tag gcr.io/$PROJECT_ID/togenuki-api

# Cloud Run へデプロイ
gcloud run deploy togenuki-api \
    --image gcr.io/$PROJECT_ID/togenuki-api \
    --platform managed \
    --region asia-northeast1 \
    --allow-unauthenticated \
    --set-env-vars "DATABASE_URL=..." \
    --set-env-vars "GOOGLE_CLIENT_ID=..." \
    --set-env-vars "GOOGLE_CLIENT_SECRET=..." \
    --set-env-vars "GOOGLE_REDIRECT_URI=..."
```

## アーキテクチャパターン

- **レイヤードアーキテクチャ**: Router → Service → Repository の3層構成
- **非同期処理優先**: Webhook受信後は即座に200 OKを返し、`BackgroundTasks`で処理
- **Result型パターン**: サービス層の外部API呼び出しは `Result[T]` 型で返却
- **UUID v7**: 時系列ソート可能なUUIDをプライマリキーに使用
- **サービスオーケストレーション**: 複数サービスを横断する処理は専用オーケストレーションサービスで調整
