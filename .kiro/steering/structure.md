# Project Structure

## Organization Philosophy

モノレポ構成で、`apps/` 配下にフロントエンド・バックエンド等のアプリケーションを配置。各アプリは独立してビルド・デプロイ可能。

## Directory Patterns

### Applications
**Location**: `apps/`
**Purpose**: 独立したアプリケーションを配置
**Example**: `apps/web/` (React SPA), `apps/api/` (FastAPI)

### Frontend Application
**Location**: `apps/web/`
**Purpose**: React + TypeScript フロントエンド
**Pattern**: Vite + 機能別ディレクトリ構成

```
apps/web/src/
├── main.tsx           # エントリーポイント
├── App.tsx            # ルートコンポーネント
├── assets/            # 画像等の静的アセット
├── components/        # 再利用可能なUIコンポーネント
├── pages/             # ページコンポーネント（ルート単位）
├── contexts/          # React Context (認証等)
├── api/               # API呼び出しモジュール
├── hooks/             # カスタムReact Hooks
├── types/             # 型定義
├── firebase/          # Firebase設定
└── __tests__/         # テストファイル
```

### Backend Application
**Location**: `apps/api/`
**Purpose**: FastAPI バックエンド
**Pattern**: レイヤードアーキテクチャ（Router → Service → Repository）

```
apps/api/src/
├── main.py            # FastAPIアプリケーション
├── config.py          # 設定管理
├── database.py        # DB接続設定
├── models.py          # SQLAlchemy ORMモデル
├── routers/           # APIエンドポイント
├── services/          # ビジネスロジック
├── repositories/      # データアクセス層
├── schemas/           # Pydanticスキーマ
├── auth/              # 認証関連（Firebase、OAuth）
└── utils/             # ユーティリティ
```

### Documentation
**Location**: `docs/`
**Purpose**: プロジェクトドキュメント（アーキテクチャ、設計書等）
**Example**: `docs/ARCHITECTURE.md`

### Infrastructure
**Location**: `infrastructures/`
**Purpose**: Terraform によるGoogle Cloudリソースのプロビジョニング
**Pattern**: ルートモジュール構成（`main.tf`, `variables.tf`, `outputs.tf`）
**管理リソース**: Cloud SQL, Cloud Run, Pub/Sub, Artifact Registry, GCS等

### Database Migrations
**Location**: `apps/api/alembic/`
**Purpose**: Alembicによるデータベーススキーマ管理
**Pattern**: `alembic revision --autogenerate -m "description"` でマイグレーション生成、`alembic upgrade head` で適用

### Scripts
**Location**: `scripts/`
**Purpose**: 開発・運用ユーティリティスクリプト
**Example**: Firebase トークン取得、Gmail Watch設定等

### Specifications
**Location**: `.kiro/specs/`
**Purpose**: 機能仕様書（requirements, design, tasks）
**Pattern**: 機能ごとにサブディレクトリ

## Naming Conventions

- **Files (TypeScript)**: PascalCase for components (`VoiceInput.tsx`), camelCase for utilities
- **Files (Python)**: snake_case (`main.py`, `email_service.py`)
- **Components**: PascalCase (`VoiceInput`, `EmailDashboard`)
- **Functions**: camelCase (TS), snake_case (Python)

## Import Organization

```typescript
// External dependencies first
import React from 'react';
import { useState, useRef } from 'react';

// Internal modules
import './App.css';
```

**Path Aliases**: 現時点では未設定（相対パス使用）

## Code Organization Principles

- **コンポーネント**: 1ファイル1コンポーネントを基本とし、型定義はファイル内に記述
- **型定義**: ブラウザAPI等の型は利用ファイル内でinterface定義
- **状態管理**: React hooks (useState, useRef) をローカルで使用
- **副作用**: useRef等でインスタンスを保持し、クリーンアップを確実に行う
- **カスタムフック**: ブラウザAPI統合（Web Speech API等）は`hooks/`に専用フックとして切り出し、可用性チェック・フォールバックを内包
- **UIフェーズ管理**: 複雑なUI操作フロー（例: 録音→清書→確認→送信）はフェーズ型（`type Phase = 'idle' | 'recording' | ...`）で状態遷移を管理
- **APIモジュール**: `api/`配下は機能単位で1ファイル（例: `reply.ts`, `characters.ts`）。リクエスト/レスポンス型とfetch関数をセットでエクスポート
- **SVGアイコン**: 小さなアイコンはコンポーネントファイル内にインラインSVG関数コンポーネントとして定義。外部アイコンライブラリ（`react-icons`）はヘッダー等の共通UIで使用

### Backend Module Pattern

機能追加時は以下の3ファイルをセットで作成:
- `routers/<feature>.py` - エンドポイント定義 + エラーマッピング
- `services/<feature>_service.py` - ビジネスロジック（`Result[T]`返却）
- `schemas/<feature>.py` - Pydantic リクエスト/レスポンスモデル

複数サービスを横断する場合は、オーケストレーションサービスとして独立（例: `reply_service.py` が `gemini_service` + `gmail_service` を調整）

DB不要のドメイン（例: キャラクター定義）は、Repositoryを省略しServiceのみで完結可能（インメモリdataclass定義）

非同期同期サービス（例: `reply_sync_service.py`）: 外部APIからの状態同期を行う独立サービス。`asyncio.gather`でバッチ処理

---
_Document patterns, not file trees. New files following patterns shouldn't require updates_
