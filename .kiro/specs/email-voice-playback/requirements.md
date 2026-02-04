# Requirements Document

## Introduction

本仕様は「TogeNuki」のコア機能である「メール受信→ギャル語変換→音声読み上げ」機能の要件を定義する。登録済み連絡先からのメールをGmail APIで取得し、Gemini 2.5 Flashで「全肯定ギャル」口調に変換後、Google Cloud TTSで音声化してダッシュボードで再生する。冷淡・威圧的なメールの心象を和らげ、リモートワークでのメールストレスを軽減することが目的。

## Requirements

### Requirement 1: メール受信・通知処理

**Objective:** As a システム, I want 登録済み連絡先からの新着メールをリアルタイムで検知・取得したい, so that ユーザーがダッシュボードで最新のメールを確認できる

#### Acceptance Criteria
1. When Gmailに新着メールが届いた時, the Backend Service shall Cloud Pub/Sub経由でWebhook通知を受信する
2. When Webhook通知を受信した時, the Backend Service shall 即座に200 OKを返却し、BackgroundTasksでメイン処理を開始する
3. When メール処理を開始した時, the Backend Service shall Gmail API (`users.messages.get`) で本文を取得する
4. If 送信者が登録済み連絡先でない場合, then the Backend Service shall そのメールの処理をスキップする
5. When メールの取得に成功した時, the Backend Service shall `emails`テーブルに`is_processed=false`でレコードを作成する

### Requirement 2: ギャル語変換処理

**Objective:** As a ユーザー, I want 冷淡・威圧的なメールを「全肯定ギャル」口調に変換してほしい, so that メールの心象が和らぎ、ストレスなく内容を確認できる

#### Acceptance Criteria
1. When メール本文の取得が完了した時, the Backend Service shall Gemini 2.5 Flashにギャル語変換リクエストを送信する
2. The Backend Service shall 以下のルールでギャル語変換を行う：一人称は「ウチ」、相手は「〇〇さん」、ユーザーは「先輩」と呼ぶ
3. The Backend Service shall 語尾に「〜だし！」「〜じゃね？」「〜なんだけどｗ」「草」などを自然に使用する
4. The Backend Service shall 怒られている内容でもポジティブに解釈して変換する
5. The Backend Service shall 絵文字を適度に使用する（💖, ✨, 🥺, 🎉, 🔥）
6. When 変換が完了した時, the Backend Service shall `emails.converted_body`に変換後テキストを保存する
7. If Gemini APIがエラーを返した場合, then the Backend Service shall エラーをログに記録し、リトライ処理を行う

### Requirement 3: 音声合成処理

**Objective:** As a ユーザー, I want 変換されたギャル語テキストを音声で聴きたい, so that メールを読まずに内容を把握でき、より親密感のある体験ができる

#### Acceptance Criteria
1. When ギャル語変換が完了した時, the Backend Service shall Google Cloud TTSに音声合成リクエストを送信する
2. The Backend Service shall 日本語の女性音声を使用する（候補: `ja-JP-Wavenet-B`, `ja-JP-Neural2-B`, `ja-JP-Journeys-1`）
3. When 音声合成が完了した時, the Backend Service shall MP3形式でGCSバケットにアップロードする
4. When GCSアップロードが完了した時, the Backend Service shall `emails.audio_url`に公開URLを保存する
5. When 全処理が完了した時, the Backend Service shall `emails.is_processed=true`に更新する
6. If TTS APIがエラーを返した場合, then the Backend Service shall エラーをログに記録し、リトライ処理を行う

### Requirement 4: ダッシュボード表示

**Objective:** As a ユーザー, I want 変換済みメールの一覧をダッシュボードで確認したい, so that 登録済み連絡先からのメールを一箇所で管理できる

#### Acceptance Criteria
1. When ユーザーがダッシュボードを開いた時, the Frontend App shall `GET /api/emails`でメール一覧を取得する
2. The Frontend App shall Firebase ID Tokenを`Authorization: Bearer`ヘッダーに含めてリクエストする
3. When メール一覧を受信した時, the Frontend App shall 受信日時の降順で表示する
4. The Frontend App shall 各メールの送信者名、件名、変換後テキストをカード形式で表示する
5. The Frontend App shall 処理中のメール（`is_processed=false`）にはローディング表示を行う

### Requirement 5: 音声再生機能

**Objective:** As a ユーザー, I want メールカードの再生ボタンを押して音声を聴きたい, so that 視覚的にメールを読まずに内容を確認できる

#### Acceptance Criteria
1. When ユーザーが再生ボタンをクリックした時, the Frontend App shall `audio_url`から音声ファイルを読み込み再生する
2. While 音声が再生中, the Frontend App shall 再生ボタンを停止ボタンに切り替える
3. When ユーザーが停止ボタンをクリックした時, the Frontend App shall 音声再生を停止する
4. When 音声再生が完了した時, the Frontend App shall 停止ボタンを再生ボタンに戻す
5. If 音声ファイルの読み込みに失敗した場合, then the Frontend App shall エラーメッセージを表示する

### Requirement 6: 認証・認可

**Objective:** As a システム, I want ユーザー認証を行い、本人のメールのみアクセス可能にしたい, so that セキュリティが確保される

#### Acceptance Criteria
1. The Frontend App shall Firebase Authentication (Google Sign-In) でログイン機能を提供する
2. When ユーザーがログインした時, the Frontend App shall Firebase ID Tokenを取得・保持する
3. When APIリクエストを送信する時, the Backend Service shall Firebase ID Tokenを検証する
4. If トークンが無効または期限切れの場合, then the Backend Service shall 401 Unauthorizedを返す
5. The Backend Service shall ユーザーは自分の`user_id`に紐づくメールのみ取得可能とする

