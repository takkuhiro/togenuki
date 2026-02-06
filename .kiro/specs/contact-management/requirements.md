# Requirements Document

## Introduction

本仕様は「TogeNuki」の連絡先管理機能の要件を定義する。監視対象の連絡先（上司・取引先など）を登録・管理し、過去のメールやり取りを分析して相手の特徴とユーザーの返信パターンを学習する。この学習データは、将来の音声返信機能でビジネスメールを清書する際にパーソナライズされた返信を生成するために使用される。

## Requirements

### Requirement 1: 連絡先登録

**Objective:** As a ユーザー, I want 監視対象の連絡先を登録したい, so that その連絡先からのメールのみがギャル語変換・音声読み上げの対象となる

#### Acceptance Criteria
1. When ユーザーが連絡先登録フォームを送信した時, the Backend Service shall `contacts`テーブルに新しいレコードを作成する（`is_learning_complete=false`）
2. When 連絡先登録リクエストを受信した時, the Backend Service shall 即座に200 OKと`contact_id`、`status: "learning_started"`を返却する
3. The Backend Service shall 連絡先登録時に以下の情報を保存する：メールアドレス（必須）、名前（任意）、Gmail検索クエリ（任意）
4. If 同一ユーザーが同じメールアドレスの連絡先を重複登録しようとした場合, then the Backend Service shall 409 Conflictエラーを返却する
5. The Frontend App shall Firebase ID Tokenを`Authorization: Bearer`ヘッダーに含めて連絡先登録リクエストを送信する

### Requirement 2: 連絡先一覧表示

**Objective:** As a ユーザー, I want 登録済みの連絡先一覧を確認したい, so that 監視対象を把握・管理できる

#### Acceptance Criteria
1. When ユーザーが連絡先一覧画面を開いた時, the Frontend App shall `GET /api/contacts`で連絡先一覧を取得する
2. The Frontend App shall 各連絡先のメールアドレス、名前、学習状態を表示する
3. While 連絡先の学習処理が進行中（`is_learning_complete=false`）, the Frontend App shall ローディング表示または「学習中」ラベルを表示する
4. When 学習が完了した連絡先, the Frontend App shall 「学習完了」ステータスを表示する
5. The Backend Service shall 認証済みユーザーの自分の連絡先のみ返却する

### Requirement 3: 連絡先削除

**Objective:** As a ユーザー, I want 不要になった連絡先を削除したい, so that 監視対象を整理できる

#### Acceptance Criteria
1. When ユーザーが連絡先の削除ボタンをクリックした時, the Frontend App shall 削除確認ダイアログを表示する
2. When ユーザーが削除を確認した時, the Frontend App shall `DELETE /api/contacts/{id}`リクエストを送信する
3. When 削除リクエストを受信した時, the Backend Service shall 該当の連絡先と関連する`contact_context`を削除する
4. If 他ユーザーの連絡先を削除しようとした場合, then the Backend Service shall 403 Forbiddenエラーを返却する
5. If 存在しない連絡先を削除しようとした場合, then the Backend Service shall 404 Not Foundエラーを返却する

### Requirement 4: 過去メール取得・学習処理

**Objective:** As a システム, I want 連絡先登録時に過去のメールを分析して相手の特徴を学習したい, so that 将来の返信生成をパーソナライズできる

#### Acceptance Criteria
1. When 連絡先が登録された時, the Backend Service shall BackgroundTasksで学習処理を非同期実行する
2. When 学習処理を開始した時, the Backend Service shall Gmail APIで過去メール30件程度を取得する（`gmail_query`を使用）
3. When 過去メールの取得が完了した時, the Backend Service shall Gemini（Learning Analyzer）に分析リクエストを送信する
4. The Backend Service shall 以下の情報を分析・抽出する：相手のメール特徴（語調、よく使う表現、要求パターン）、ユーザーの返信パターン（よく使う表現、対応スタイル）
5. When 分析が完了した時, the Backend Service shall `contact_context`テーブルに`learned_patterns`を保存する
6. When 学習処理が完了した時, the Backend Service shall `contacts.is_learning_complete=true`に更新する
7. If Gmail APIがエラーを返した場合, then the Backend Service shall エラーをログに記録し、学習ステータスを「失敗」に設定する
8. If Gemini APIがエラーを返した場合, then the Backend Service shall エラーをログに記録し、リトライ処理を行う

### Requirement 5: 学習完了通知

**Objective:** As a ユーザー, I want 学習処理が完了したことを知りたい, so that 連絡先が利用可能になったことを把握できる

#### Acceptance Criteria
1. While 連絡先一覧画面を表示中, the Frontend App shall 定期的に学習状態をポーリングする（30秒間隔）
2. When 学習状態が`is_learning_complete=true`に変化した時, the Frontend App shall UI上の学習ステータスを更新する
3. If 学習処理が失敗した場合, then the Frontend App shall エラーメッセージと再試行ボタンを表示する

### Requirement 6: 認証・認可

**Objective:** As a システム, I want 連絡先APIへのアクセスを認証済みユーザーに限定したい, so that セキュリティが確保される

#### Acceptance Criteria
1. When 連絡先APIリクエストを受信した時, the Backend Service shall Firebase ID Tokenを検証する
2. If トークンが無効または期限切れの場合, then the Backend Service shall 401 Unauthorizedを返却する
3. The Backend Service shall ユーザーは自分の`user_id`に紐づく連絡先のみ操作可能とする
4. If 他ユーザーのリソースにアクセスしようとした場合, then the Backend Service shall 403 Forbiddenを返却する

