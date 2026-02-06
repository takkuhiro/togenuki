# Research & Design Decisions

## Summary
- **Feature**: `voice-reply-email`
- **Discovery Scope**: Extension（既存システムへの機能追加）
- **Key Findings**:
  - Web Speech API（SpeechRecognition）はブラウザ側STTとして利用可能。既存のAudioPlayerと同じEmailCard内に配置可能
  - Gmail API でのメール返信には `threadId`、`In-Reply-To`、`References` ヘッダーの設定が必要。既存の `GmailApiClient` に `send_message` メソッドを追加する形で拡張可能
  - GeminiService に清書メソッドを追加し、既存の `analyze_patterns` / `convert_to_gyaru` と同じパターンで実装可能

## Research Log

### Web Speech API（SpeechRecognition）のブラウザサポート
- **Context**: 音声入力をブラウザ側で処理するため、Web Speech API の利用可能性を調査
- **Sources Consulted**: MDN Web Docs、steering/tech.md（既にWeb Speech API for音声入力を記載）
- **Findings**:
  - `SpeechRecognition` はChrome/Edgeで安定サポート。Firefox/Safariは限定的
  - `webkitSpeechRecognition` プレフィックスがChromiumブラウザで必要
  - `continuous: true` と `interimResults: true` でリアルタイムプレビューが実現可能
  - 日本語（`lang: 'ja-JP'`）サポートあり
- **Implications**: フォールバック（テキスト手動入力）が必須。`window.SpeechRecognition || window.webkitSpeechRecognition` での存在チェックパターン

### Gmail API メール送信（返信スレッド）
- **Context**: 返信メールを正しいスレッドに紐づけて送信するためのAPI仕様調査
- **Sources Consulted**: Gmail API公式ドキュメント、RFC 2822
- **Findings**:
  - `messages.send` エンドポイント（`POST /gmail/v1/users/me/messages/send`）を使用
  - リクエストボディに `raw`（base64url エンコードされたMIMEメッセージ）と `threadId` を含める
  - MIMEメッセージに `In-Reply-To: <original-message-id>` と `References: <original-message-id>` ヘッダーを設定
  - `Subject: Re: <original-subject>` でスレッド表示を維持
  - 既存の `GmailApiClient` は read 系メソッドのみ → `send_message` メソッドを追加
- **Implications**: Emailモデルの `google_message_id` はGmail内部ID。MIMEヘッダー用の `Message-ID`（`<xxx@mail.gmail.com>` 形式）を元メールから取得する必要がある

### Gemini API 清書プロンプト設計
- **Context**: 口語テキストをビジネスメールに清書するためのプロンプト戦略
- **Sources Consulted**: 既存の `GeminiService.convert_to_gyaru` パターン
- **Findings**:
  - 既存パターン: system_instruction + user_prompt + GenerateContentConfig
  - 清書用には `temperature: 0.3`（正確性重視）が適切
  - コンテキスト（元メール、contact_context）をプロンプトに含める
  - `max_output_tokens: 2048` で十分なビジネスメール長をカバー
- **Implications**: `GeminiService` に `compose_business_reply` メソッドを追加。既存の `analyze_patterns` と同じ Result パターン

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| EmailCard内拡張 | EmailCardコンポーネント内に音声入力UIを段階的に展開 | 既存UIフローに自然に統合。ページ遷移不要 | EmailCard の責務が増大 | ユーザーフィードバックに合致。カード内完結型 |
| 別ページ遷移 | 返信用の専用ページに遷移 | 責務分離が明確 | コンテキストの受け渡しが複雑。UX的にメール一覧から離れる | プロダクトコンセプト（メールが怖い人向け）と不一致 |

**選択**: EmailCard内拡張。ユーザーが使い慣れたメール一覧画面内で全フローを完結させる。

## Design Decisions

### Decision: 音声入力UIの配置
- **Context**: 音声入力ボタンの配置場所をユーザーフィードバックに基づき決定
- **Alternatives Considered**:
  1. EmailCard の `email-card-actions` 内、AudioPlayer の隣に配置
  2. メール一覧の上部にグローバル返信ボタン
- **Selected Approach**: Option 1 — AudioPlayerの隣に音声入力ボタンを配置
- **Rationale**: ユーザーの明示的な要望。「とげぬき再生」で内容を聴いた直後に返信できる自然なフロー
- **Trade-offs**: EmailCard の props が増えるが、VoiceReplyPanel コンポーネントとして切り出すことで管理可能

### Decision: 清書→確認→送信フロー
- **Context**: メール送信のUXフロー設計
- **Selected Approach**: 清書完了後に「確認」と「送信」ボタンを分離表示。「送信」は常に有効
- **Rationale**: メールが怖いユーザーは中身を見ずに送信したい場合がある。確認は任意操作
- **Trade-offs**: 誤送信リスクは若干上がるが、TogeNukiの心理的安全性コンセプトを優先

### Decision: バックエンドの送信API設計
- **Context**: メール送信エンドポイントの設計方針
- **Alternatives Considered**:
  1. 清書と送信を1つのエンドポイントで同期的に処理
  2. 清書エンドポイントと送信エンドポイントを分離
- **Selected Approach**: Option 2 — 清書（`POST /api/emails/{id}/compose-reply`）と送信（`POST /api/emails/{id}/send-reply`）を分離
- **Rationale**: 清書結果の確認・編集フェーズが間に入るため分離が自然。再清書も容易
- **Follow-up**: 清書結果はフロントエンドのステートで保持し、送信時にリクエストボディに含める

## Risks & Mitigations
- Web Speech API のブラウザ非対応 → テキスト手動入力フォールバックを必須実装
- Gmail OAuth トークン期限切れ → 既存の `ensure_valid_access_token` パターンを再利用
- Gemini API レート制限 → 既存のリトライパターン（MAX_RETRIES）を再利用
- 誤送信 → 送信完了後のフィードバック表示で対応（取り消し機能はスコープ外）

## References
- [Gmail API messages.send](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send)
- [Web Speech API - MDN](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition)
- [RFC 2822 - In-Reply-To / References headers](https://www.rfc-editor.org/rfc/rfc2822#section-3.6.4)
