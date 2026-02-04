# Research & Design Decisions

## Summary
- **Feature**: `email-voice-playback`
- **Discovery Scope**: New Feature（グリーンフィールド開発）
- **Key Findings**:
  - Gmail Push通知はPub/Sub経由で受信し、7日ごとにwatchを更新する必要がある
  - Gemini 2.5 FlashはGoogle Gen AI SDK (`google-genai`) を使用し、非同期処理に対応
  - Cloud TTSはChirp 3 HD/Gemini 2.5 TTS Flash等の最新音声エンジンが利用可能

## Research Log

### Gmail API Push Notifications
- **Context**: メール受信のリアルタイム検知方法を調査
- **Sources Consulted**:
  - [Gmail API Push Notifications Guide](https://developers.google.com/workspace/gmail/api/guides/push)
  - [Cloud Pub/Sub Push subscriptions](https://cloud.google.com/pubsub/docs/push)
- **Findings**:
  - `gmail-api-push@system.gserviceaccount.com` にPub/Sub Publisherロールを付与
  - `users.watch` APIでメールボックスの監視を開始
  - Push通知にはhistoryIdのみ含まれ、実際のメッセージは別途取得が必要
  - watchは7日で期限切れ、毎日の更新を推奨
  - 通知を受けたら即座に200 OKを返却し、BackgroundTasksで処理
- **Implications**:
  - watchの自動更新機能（Cloud Schedulerなど）が将来的に必要
  - Webhook受信後は非同期処理でメイン処理を実行

### Gemini 2.5 Flash SDK
- **Context**: ギャル語変換のLLM APIを調査
- **Sources Consulted**:
  - [Google Gen AI Python SDK](https://github.com/googleapis/python-genai)
  - [Gemini 2.5 Flash Documentation](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash)
- **Findings**:
  - `google-genai` パッケージを使用（旧`google-generativeai`は非推奨）
  - モデルID: `gemini-2.5-flash`
  - Vertex AI APIまたはGemini Developer APIのどちらでも利用可能
  - ストリーミングレスポンス対応
  - Gemini 2.0 Flashは2026年3月3日に廃止予定
- **Implications**:
  - Vertex AI経由で利用する場合はGCPプロジェクトIDとリージョン設定が必要
  - プロンプトはシステムプロンプトとして定義し、メール本文をユーザーメッセージとして渡す

### Google Cloud Text-to-Speech
- **Context**: 日本語音声合成のオプションを調査
- **Sources Consulted**:
  - [Cloud TTS Supported voices](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types)
  - [Chirp 3: HD voices](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd)
- **Findings**:
  - 日本語（ja-JP）対応ボイス: WaveNet, Neural2, Chirp 3 HD
  - Gemini 2.5 TTS Flash/Proも利用可能（30種類のスピーカー、80以上のロケール）
  - Chirp 3 HDは8スピーカー、31ロケールでGA
  - `client.list_voices(language_code="ja-JP")`で利用可能な音声を取得
- **Implications**:
  - 初期実装ではWaveNet-Bまたは Neural2-Bを使用、後からChirp 3 HDへアップグレード可能
  - 音声ファイルはMP3形式でGCSに保存

### FastAPI BackgroundTasks
- **Context**: 非同期処理のベストプラクティスを調査
- **Sources Consulted**:
  - [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
  - [Managing Background Tasks in FastAPI](https://leapcell.io/blog/managing-background-tasks-and-long-running-operations-in-fastapi)
- **Findings**:
  - `async def`または通常の`def`関数を登録可能
  - タスクは追加順に実行される
  - 同一プロセスで実行されるため、プロセス停止時にタスクも停止
  - CPU負荷の高いタスクはメインイベントループに影響
  - ミッションクリティカルなタスクにはCelery/ARQを推奨
- **Implications**:
  - 初期実装はBackgroundTasksで十分（メール処理は短時間）
  - エラーハンドリングとログ記録を必須とする
  - 将来的にはARQへの移行を検討

### Gmail API Server-Side OAuth
- **Context**: サーバーサイドでGmail APIのOAuth管理を行う方法を調査
- **Sources Consulted**:
  - [Google OAuth 2.0 for Server-side Web Apps](https://developers.google.com/identity/protocols/oauth2/web-server)
  - [Using OAuth 2.0 to Access Google APIs](https://developers.google.com/identity/protocols/oauth2)
- **Findings**:
  - サーバーサイドOAuthでは `authorization_code` フローを使用
  - `access_type=offline` を指定してRefresh Tokenを取得
  - Refresh Tokenは一度のみ発行（prompt=consent で再取得可能）
  - Access Tokenは1時間で期限切れ、Refresh Tokenで更新
  - Refresh Tokenは取り消されるまで有効
  - Client ID/Secretはサーバー側で安全に管理
- **Implications**:
  - usersテーブルにrefresh_token, access_token, token_expires_atカラムを追加
  - GmailOAuthServiceでトークン管理を実装
  - 本番環境ではRefresh Tokenを暗号化して保存
  - トークン更新失敗時はユーザーに再認証を促す

### Firebase Authentication Token Verification
- **Context**: バックエンドでのトークン検証方法を調査
- **Sources Consulted**:
  - [Firebase Verify ID Tokens](https://firebase.google.com/docs/auth/admin/verify-id-tokens)
  - [fastapi-cloudauth](https://github.com/tokusumi/fastapi-cloudauth)
- **Findings**:
  - `firebase-admin` SDKの`auth.verify_id_token()`を使用
  - サービスアカウントJSON（`GOOGLE_APPLICATION_CREDENTIALS`）が必要
  - Cloud Run環境では自動的に認証情報が設定される
  - fastapi-cloudauthライブラリで簡略化可能
- **Implications**:
  - FastAPIのDependencyとして認証ミドルウェアを実装
  - 401 Unauthorizedを返す際は`WWW-Authenticate: Bearer`ヘッダーを含める

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| Layered Architecture | Controller → Service → Repository | シンプル、理解しやすい | 大規模化時に肥大化 | 初期実装に適切 |
| Event-Driven | Pub/Sub駆動の非同期処理 | スケーラブル、疎結合 | 複雑性増加 | Gmail通知で部分採用 |
| Hexagonal | ポート&アダプター | テスタビリティ高 | 過度な抽象化リスク | 将来の拡張に向けて意識 |

**選択**: Layered Architecture + Event-Driven（Gmail通知部分のみ）

## Design Decisions

### Decision: バックエンド処理のアーキテクチャ
- **Context**: Pub/Sub Webhook受信後のメール処理フロー
- **Alternatives Considered**:
  1. 同期処理 — Webhook内で全処理を完了
  2. BackgroundTasks — レスポンス返却後に非同期処理
  3. Cloud Tasks — 別サービスに処理を委譲
- **Selected Approach**: BackgroundTasks
- **Rationale**:
  - Pub/Subは10秒以内の応答を期待
  - 処理時間は通常数秒（Gemini API + TTS + GCSアップロード）
  - 初期MVPとして複雑性を抑える
- **Trade-offs**: プロセス停止時に処理が失われる可能性
- **Follow-up**: 本番環境ではCloud Tasksへの移行を検討

### Decision: 音声合成エンジンの選択
- **Context**: 日本語女性ボイスの選定
- **Alternatives Considered**:
  1. ja-JP-Wavenet-B — 安定、低コスト
  2. ja-JP-Neural2-B — より自然な音声
  3. Chirp 3 HD — 最新、高品質
  4. Gemini 2.5 TTS Flash — 最新、感情表現豊か
- **Selected Approach**: ja-JP-Wavenet-B（初期）、将来Chirp 3 HDへ移行
- **Rationale**:
  - WaveNetは無料枠あり（月100万文字）
  - 十分な品質でMVP検証可能
- **Trade-offs**: 最新の音声技術は後回し
- **Follow-up**: ユーザーフィードバックに基づき音声品質を改善

### Decision: Gmail API OAuth方式
- **Context**: Gmail APIアクセスに必要なOAuthトークンの管理方式
- **Alternatives Considered**:
  1. クライアントサイドOAuth — FrontendでaccessTokenを保持
  2. サーバーサイドOAuth — BackendでRefresh Tokenを管理
- **Selected Approach**: サーバーサイドOAuth
- **Rationale**:
  - Refresh Tokenをサーバーで安全に管理
  - Webhook処理時にユーザー操作なしでトークン更新可能
  - クライアント側にセンシティブなトークンを露出しない
- **Trade-offs**: 実装複雑性増加、初回OAuth認証フローが必要
- **Follow-up**: トークン暗号化、トークン失効時の再認証UX設計

### Decision: フロントエンド状態管理
- **Context**: メール一覧と音声再生状態の管理
- **Alternatives Considered**:
  1. useState/useReducer — ローカル状態のみ
  2. Context API — 軽量なグローバル状態
  3. Redux/Zustand — 本格的な状態管理
- **Selected Approach**: useState + Context API
- **Rationale**:
  - 小規模アプリケーションで過度な複雑性は不要
  - 認証状態とメール一覧のみがグローバル状態
- **Trade-offs**: 状態が複雑化した場合のリファクタリングコスト
- **Follow-up**: 機能拡張時にZustandへの移行を検討

## Risks & Mitigations
- **Gmail Watch期限切れ** — Cloud Schedulerで毎日watchを更新
- **Gemini APIレート制限** — 指数バックオフでリトライ、キューイング
- **TTS処理時間** — 長文メールは分割処理を検討
- **GCSストレージコスト** — 古い音声ファイルの自動削除ポリシー
- **Firebase Token漏洩** — HTTPSのみ、トークンの短期有効期限

## References
- [Gmail API Push Notifications](https://developers.google.com/workspace/gmail/api/guides/push)
- [Google Gen AI Python SDK](https://github.com/googleapis/python-genai)
- [Cloud TTS Supported voices](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Firebase Verify ID Tokens](https://firebase.google.com/docs/auth/admin/verify-id-tokens)
