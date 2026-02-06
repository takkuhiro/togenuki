# Research & Design Decisions

## Summary
- **Feature**: contact-management
- **Discovery Scope**: Extension（既存システムへの機能追加）
- **Key Findings**:
  - `Contact`モデルと`is_learning_complete`フラグが既に実装済み
  - `contact_context`テーブルは未実装、マイグレーション作成が必要
  - 既存の`GeminiService`と`GmailApiClient`パターンを拡張して学習機能を実装

## Research Log

### Gmail API メッセージ検索機能
- **Context**: 連絡先登録時に過去メール30件を取得する必要がある
- **Sources Consulted**: 既存コード (`apps/api/src/services/gmail_service.py`)
- **Findings**:
  - `GmailApiClient`に`list_recent_messages()`が既に存在
  - クエリ検索には`messages.list`の`q`パラメータを使用
  - 形式: `from:email@example.com after:2024/01/01`
- **Implications**: `GmailApiClient`に`search_messages(query, max_results)`メソッドを追加

### Gemini 学習分析プロンプト
- **Context**: 過去メールから相手の特徴とユーザーの返信パターンを抽出
- **Sources Consulted**: 既存コード (`apps/api/src/services/gemini_service.py`)、ARCHITECTURE.md
- **Findings**:
  - 既存の`convert_to_gyaru()`と同じ`Result`型パターンを使用
  - ARCHITECTURE.mdに`SYSTEM_PROMPT_LEARNING`のテンプレートあり
  - JSON形式で構造化された出力を要求可能
- **Implications**: `GeminiService`に`analyze_patterns()`メソッドを追加、JSONスキーマで出力を制御

### BackgroundTasks パターン
- **Context**: 連絡先登録後の学習処理を非同期実行
- **Sources Consulted**: 既存コード (`apps/api/src/routers/webhook.py`)
- **Findings**:
  - `BackgroundTasks.add_task()`で即座に200 OK返却後に処理
  - DBセッションは`async for session in get_db()`で新規作成
  - エラーハンドリングは`try/except`でログ記録
- **Implications**: 同じパターンを連絡先ルーターに適用

### 学習失敗時のステータス管理
- **Context**: 学習処理が失敗した場合のリトライ戦略
- **Sources Consulted**: 要件分析
- **Findings**:
  - 現在の`Contact`モデルには失敗ステータス用カラムがない
  - `is_learning_complete`はboolean（true/false）のみ
- **Implications**:
  - Option A: `learning_status` enumカラム追加（pending/in_progress/completed/failed）
  - Option B: `is_learning_complete`をそのまま使用し、failedは別途フラグ追加
  - **選択**: Option B - 最小限の変更で実装、`learning_failed_at`カラムを追加

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| ハイブリッド | 既存サービス拡張 + 新規ルーター/リポジトリ作成 | 既存パターン維持、テスト分離可能 | 作業量中程度 | 推奨 |
| 拡張のみ | 既存ファイルにすべて追加 | 新規ファイル最小 | ファイル肥大化、SRP違反 | 非推奨 |
| 新規のみ | すべて新規作成 | 完全分離 | 重複コード発生 | 過剰 |

## Design Decisions

### Decision: contact_context データ構造
- **Context**: 学習結果の保存形式を決定
- **Alternatives Considered**:
  1. JSON Text（`learned_patterns` TEXTカラム）— シンプル、スキーマ変更不要
  2. 正規化テーブル — 柔軟だが複雑
- **Selected Approach**: JSON Text
- **Rationale**: ハッカソン向けにシンプルさ優先、将来的に正規化可能
- **Trade-offs**: クエリ性能は劣るが、読み取り中心の用途なら問題なし
- **Follow-up**: JSON Schemaでバリデーション検討

### Decision: 学習完了通知方式
- **Context**: 学習処理完了をFrontendに通知する方法
- **Alternatives Considered**:
  1. ポーリング（30秒間隔）— シンプル
  2. WebSocket — リアルタイムだが実装コスト高
  3. Server-Sent Events — 中間的
- **Selected Approach**: ポーリング
- **Rationale**: ハッカソン向けに最小実装、学習処理は数分で完了するため許容範囲
- **Trade-offs**: リアルタイム性は劣るが実装コスト最小
- **Follow-up**: 将来的にWebSocket移行を検討

### Decision: 連絡先削除時のカスケード
- **Context**: 連絡先削除時の関連データ処理
- **Alternatives Considered**:
  1. カスケード削除（contact_context、関連emails）
  2. 論理削除（deleted_atフラグ）
  3. contact_contextのみ削除、emailsは保持
- **Selected Approach**: contact_contextのみ削除、emailsは`contact_id=NULL`に更新
- **Rationale**: メール履歴は保持したい、contact_contextは連絡先固有なので削除
- **Trade-offs**: emailsの孤児レコード発生、だがデータ保全優先

## Risks & Mitigations
- **Gmail API レートリミット** — 30件程度の取得なら問題なし、エラー時はログ記録と再試行ボタン提供
- **Gemini API 長文入力** — 30件のメール本文を連結すると大きくなる可能性、トークン制限に注意
- **学習プロンプト品質** — 実データでの検証が必要、イテレーション前提

## References
- [Gmail API messages.list](https://developers.google.com/gmail/api/reference/rest/v1/users.messages/list) — qパラメータで検索クエリ指定
- [Gemini API](https://ai.google.dev/docs) — google-genai SDK使用
- 既存実装: `apps/api/src/services/gemini_service.py`, `apps/api/src/services/gmail_service.py`
