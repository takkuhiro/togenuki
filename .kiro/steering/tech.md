# Technology Stack

## Architecture

Google Cloud を中心としたサーバーレスアーキテクチャ。フロントエンドはReact SPA、バックエンドはFastAPI on Cloud Run、リアルタイム連携はPub/Sub経由で実現。

## Core Technologies

### Frontend
- **Language**: TypeScript
- **Framework**: React 19 (Vite)
- **Runtime**: ブラウザ (Web Speech API for 音声入力)
- **Linter/Formatter**: Biome (ESLint + Prettierの代替)
- **Testing**: Vitest + Testing Library

### Backend
- **Language**: Python 3.10+
- **Framework**: FastAPI (async/await 必須)
- **Database**: Cloud SQL (PostgreSQL) + SQLAlchemy ORM
- **Storage**: Cloud Storage (GCS) - 音声ファイル保存

### AI/ML Services
- **LLM**: Gemini 2.5 Flash (感情変換・メール清書・学習分析)
- **TTS**: Google Cloud Text-to-Speech (日本語)

### Authentication
- Firebase Authentication (Google Sign-In)
- Gmail API OAuth scopes: `gmail.readonly`, `gmail.send`

### Infrastructure
- Cloud Run (コンテナデプロイ)
- Cloud Pub/Sub (Gmail Push通知受信)
- Terraform (IaC)

## Development Standards

### Type Safety
- TypeScript: 型定義を明示（Web Speech API等の型は手動定義）
- Python: 型ヒント推奨

### Code Quality
- Frontend: Biome（lint + format）
- Python: Ruff（lint）、mypy（型チェック）

### Testing
- Frontend: Vitest + Testing Library
- Backend: pytest + pytest-asyncio

## Development Environment

### Required Tools
- Node.js 18+
- Python 3.10+
- Docker (Cloud Run デプロイ用)
- gcloud CLI

### Common Commands
```bash
# Frontend (apps/web/)
npm run dev    # 開発サーバー起動 (Vite)
npm run build  # プロダクションビルド
npm run test   # テスト実行 (Vitest)
npm run check  # lint + format チェック (Biome)

# Backend (apps/api/)
uvicorn src.main:app --reload   # 開発サーバー起動
pytest                          # テスト実行
ruff check src/                 # lint
```

## Key Technical Decisions

- **非同期処理優先**: Pub/Sub Webhook受信後、即座に200 OK返却し、BackgroundTasksで処理
- **音声変換ローカル化**: Web Speech APIでブラウザ側STT処理（サーバー負荷軽減）
- **学習データ永続化**: contact_contextテーブルで相手パターンを保持
- **Result型パターン**: 外部API呼び出しは`result`ライブラリでエラーハンドリング
- **UUID v7採用**: 時系列ソート可能なUUIDをPKに使用

---
_Document standards and patterns, not every dependency_
