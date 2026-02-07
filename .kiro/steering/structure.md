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
├── components/        # 再利用可能なUIコンポーネント
├── pages/             # ページコンポーネント
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

---
_Document patterns, not file trees. New files following patterns shouldn't require updates_
