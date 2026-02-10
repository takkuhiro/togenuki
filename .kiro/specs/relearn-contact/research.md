# Research & Design Decisions

## Summary
- **Feature**: relearn-contact
- **Discovery Scope**: Extension（既存の学習・再試行機能を拡張）
- **Key Findings**:
  - 既存の retry エンドポイントは `learning_failed_at` が設定されている場合のみ実行可能（失敗復旧専用）
  - relearn は `is_learning_complete == True` の連絡先が対象であり、retry とは前提条件が異なる
  - バックグラウンド処理（`LearningService.process_learning`）は retry と relearn で完全に再利用可能

## Research Log

### retry と relearn の前提条件の違い
- **Context**: 既存の retry は失敗状態のみ受付。relearn は完了状態のみ受付。同時実行防止が必要。
- **Sources Consulted**: `apps/api/src/routers/contacts.py` L232-305
- **Findings**:
  - retry: `contact.learning_failed_at is None` → 409（失敗していなければ拒否）
  - relearn: `contact.is_learning_complete == False` → 409（学習中または未完了なら拒否）
  - 両者は排他的な前提条件を持つ
- **Implications**: relearn エンドポイントでは `is_learning_complete` をチェックし、False の場合に 409 を返す

### 既存 LearningService の再利用性
- **Context**: relearn のバックグラウンド処理は新規実装が必要か
- **Sources Consulted**: `apps/api/src/services/learning_service.py`
- **Findings**:
  - `process_learning(contact_id, user_id)` は連絡先IDとユーザーIDのみを引数に取る
  - 内部でGmail API取得 → Gemini分析 → ContactContext保存の全フローを実行
  - retry エンドポイントでも同メソッドをそのまま呼び出している
- **Implications**: relearn でも `process_learning` をそのまま再利用可能。新サービス追加は不要

### フロントエンドのパターン
- **Context**: 再学習ボタンの追加方法と状態管理
- **Sources Consulted**: `ContactCard.tsx`, `ContactList.tsx`, `contacts.ts`
- **Findings**:
  - ContactCard は `onRetry` コールバックを optional props として受け取る既存パターン
  - ContactList でハンドラを定義し、API呼び出し→state更新→ポーリング開始の流れ
  - retry ボタンは `learningFailedAt && onRetry` で条件表示
- **Implications**: `onRelearn` コールバックを同じパターンで追加。表示条件は `status === 'learning_complete'`

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| 既存パターン踏襲 | retry と同じ Router → BackgroundTask → LearningService パターン | 実装コスト最小、一貫性維持 | 特になし | 採用 |

## Design Decisions

### Decision: 専用エンドポイント vs retry の拡張
- **Context**: relearn を retry エンドポイントの拡張（クエリパラメータ等）として実装するか、専用エンドポイントとするか
- **Alternatives Considered**:
  1. `/retry?force=true` — retry エンドポイントにオプション追加
  2. `/relearn` — 専用エンドポイント新設
- **Selected Approach**: `/relearn` 専用エンドポイント
- **Rationale**: retry と relearn は前提条件が異なり（失敗状態 vs 完了状態）、責務が異なる。エンドポイントを分けることでバリデーションロジックが明確になる
- **Trade-offs**: エンドポイント数は増えるが、Router内の条件分岐が単純になる
- **Follow-up**: なし

### Decision: レスポンスステータスコード
- **Context**: relearn 成功時のHTTPステータス
- **Alternatives Considered**:
  1. 200 OK — 処理完了を示す
  2. 202 Accepted — 非同期処理の受付を示す
- **Selected Approach**: 202 Accepted
- **Rationale**: バックグラウンドで処理が実行されるため、リクエスト受付を示す 202 が意味的に正確
- **Trade-offs**: retry は 200 を返しているが、relearn は 202 で統一性がやや異なる。ただし意味的正確性を優先
- **Follow-up**: なし

## Risks & Mitigations
- 学習中に再学習リクエストが来た場合の重複実行 → 409 Conflict で拒否
- 再学習中のデータ不整合 → 既存の process_learning が原子的にステータス更新するため問題なし

## References
- 既存実装: `apps/api/src/routers/contacts.py` (retry エンドポイント)
- 既存実装: `apps/api/src/services/learning_service.py` (LearningService)
