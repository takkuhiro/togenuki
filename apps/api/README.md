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
| **AI (TTS)** | Gemini 2.5 Flash TTS (google-genai) |
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
│   ├── characters.py      # キャラクター選択
│   ├── contacts.py        # 連絡先管理
│   ├── cron.py            # スケジュールタスク
│   ├── emails.py          # メール一覧
│   ├── gmail_oauth.py     # Gmail OAuth 認証
│   ├── gmail_watch.py     # Gmail Push通知設定
│   ├── reply.py           # 返信清書・送信・下書き
│   └── webhook.py         # Gmail Pub/Sub Webhook
├── services/          # ビジネスロジック
│   ├── character_service.py   # キャラクター定義
│   ├── email_processor.py     # メール処理 (変換 + TTS)
│   ├── gemini_service.py      # Gemini LLM 統合
│   ├── gmail_service.py       # Gmail API クライアント
│   ├── gmail_watch.py         # Gmail Watch 設定
│   ├── instruction_service.py # ユーザー指示処理
│   ├── learning_service.py    # コンテキスト学習
│   ├── reply_service.py       # 返信オーケストレーション
│   ├── reply_sync_service.py  # Gmail直接返信検出
│   └── tts_service.py         # Gemini TTS 音声合成
├── repositories/      # データアクセス層
│   ├── email_repository.py
│   └── contact_repository.py
├── schemas/           # Pydantic リクエスト/レスポンスモデル
│   ├── character.py       # キャラクタースキーマ
│   ├── contact.py         # 連絡先スキーマ
│   ├── email.py           # メールスキーマ
│   └── reply.py           # 返信スキーマ
├── auth/              # 認証関連
│   ├── firebase_admin.py  # Firebase 初期化
│   ├── gmail_oauth.py     # Gmail OAuth ユーティリティ
│   ├── middleware.py      # 認証ミドルウェア
│   └── schemas.py         # 認証スキーマ
└── utils/             # ユーティリティ
    ├── gcs_signer.py      # GCS署名URL生成
    └── logging.py         # ログ設定

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

### キャラクター (`/api`)

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/characters` | キャラクター一覧取得 | 不要 |
| GET | `/api/users/character` | ユーザーの選択キャラクター取得 | 要 |
| PUT | `/api/users/character` | キャラクター変更 | 要 |

### メール (`/api`)

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/emails` | メール一覧取得 | 要 |

### 返信 (`/api`)

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| POST | `/api/emails/{email_id}/compose-reply` | 返信文の清書 (AI生成) | 要 |
| POST | `/api/emails/{email_id}/send-reply` | 返信メール送信 | 要 |
| POST | `/api/emails/{email_id}/save-draft` | 返信の下書き保存 | 要 |

### 連絡先 (`/api`)

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| POST | `/api/contacts` | 連絡先登録 (+ バックグラウンド学習開始) | 要 |
| GET | `/api/contacts` | 連絡先一覧取得 | 要 |
| DELETE | `/api/contacts/{contact_id}` | 連絡先削除 | 要 |
| POST | `/api/contacts/{contact_id}/relearn` | 学習済み連絡先の再学習 | 要 |
| POST | `/api/contacts/{contact_id}/instruct` | 連絡先への指示追加 | 要 |
| POST | `/api/contacts/{contact_id}/retry` | 学習リトライ | 要 |

### Webhook (`/api/webhook`)

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| POST | `/api/webhook/gmail` | Gmail Pub/Sub Webhook受信 | 不要 (Pub/Sub) |

### Gmail Watch (`/api/gmail`)

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| POST | `/api/gmail/watch` | Gmail Push通知の設定 | 要 |
| DELETE | `/api/gmail/watch` | Gmail Push通知の停止 | 要 |

### Cron (`/api/cron`)

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| POST | `/api/cron/renew-gmail-watches` | Gmail Watch の一括更新 | スケジューラシークレット |

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
