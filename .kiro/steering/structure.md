# Project Structure

## Organization Philosophy

モノレポ構成で、`apps/` 配下にフロントエンド・バックエンド等のアプリケーションを配置。各アプリは独立してビルド・デプロイ可能。

## Directory Patterns

### Applications
**Location**: `apps/`
**Purpose**: 独立したアプリケーションを配置
**Example**: `apps/web/` (React SPA), `apps/api/` (FastAPI - 計画中)

### Frontend Application
**Location**: `apps/web/`
**Purpose**: React + TypeScript フロントエンド
**Pattern**: Create React App標準構成

```
apps/web/
├── src/
│   ├── App.tsx          # ルートコンポーネント
│   ├── index.tsx        # エントリーポイント
│   ├── [Feature].tsx    # 機能コンポーネント
│   └── *.css            # スタイル
└── package.json
```

### Documentation
**Location**: `docs/`
**Purpose**: プロジェクトドキュメント（アーキテクチャ、設計書等）
**Example**: `docs/ARCHITECTURE.md`

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
