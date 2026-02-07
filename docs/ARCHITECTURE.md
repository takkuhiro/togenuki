# リモートワークでの「メールが怖い」からおさらば！TogeNuki

## 1. 背景とコンセプト

### 背景：リモートワークでのメールストレス

チャットやメールなどのテキストコミュニケーションでは、相手の「表情」「声のトーン」「雰囲気」が分かりません。受け手は相手の感情をネガティブに深読みしてしまい、メール受信がストレスになります。

**リモートワークうつは「真面目で責任感が強い人」ほど陥りやすい傾向があります。** 姿が見えない分、自分を追い込み、上司からの怖いメールは社員が病んでしまう原因となっています。

### ソリューション

**「もう上司からのメールも怖くない！リモートワークでの「メールが怖い」からおわらば！TogeNuki」**

上司からの冷淡・威圧的なメールを、AIが「全肯定してくれるハイテンションなギャル」の口調と音声に変換して読み上げます。メールをユーザーに直接開かせず、怖い文体も親密感のあるAIの読み上げに変換することでユーザーの心象を和らげます。

返信はユーザーが口語で音声入力すると、AIが完璧なビジネスメールに清書して送信するため、ユーザーは最終的にちゃんとしたビジネスメール文体でメールを送ることができます。

### コア体験（User Journey）

1. **受信**: ユーザーがダッシュボードを開くと、事前に登録しておいた相手連絡先からのメールの一覧が表示される
2. **視聴**: 一覧から選択し、再生ボタンを押すと**「ねー先輩！部長からマジうける連絡きたんだけど〜！ｗ」**と読み上げられる。
3. **返信**: ユーザーが「あー、わかった。後でやっとくって言っといて」と音声入力する。
4. **送信**: AIが「承知いたしました。只今別件の対応中ですので、完了次第直ちに着手いたします。」と清書して送信。

## 2. システムアーキテクチャ

### 全体構成図

```mermaid
graph TD
    %% Email Ingestion
    Gmail[Gmail Server] -- "1. New Email" --> PubSub[Cloud Pub/Sub]
    PubSub -- "2. Push Notification" --> CR_Back[Cloud Run (FastAPI)]

    %% Backend Processing
    subgraph "Backend (Google Cloud)"
        CR_Back -- "3. Fetch Email Body" --> GmailAPI[Gmail API]
        CR_Back -- "4. Convert Text (Gal)" --> Gemini[Gemini 2.5 Flash]
        CR_Back -- "5. Generate Audio" --> TTS[Google Cloud TTS]
        CR_Back -- "6. Upload Audio" --> GCS[Cloud Storage]
        CR_Back -- "7. Save Metadata" --> SQL[(Cloud SQL)]
        CR_Back -- "8. Draft Reply" --> Gemini
        CR_Back -- "9. Send Email" --> GmailAPI

        %% Contact Learning Flow (Async)
        CR_Back -- "10. Fetch Past Emails (30件)" --> GmailAPI
        CR_Back -- "11. Learn Patterns" --> Gemini
        CR_Back -- "12. Save Context" --> SQL
    end

    %% Frontend Interaction
    subgraph "Frontend (React + Firebase)"
        User((User)) -- "Login" --> FireAuth[Firebase Auth]
        User -- "Voice Reply" --> ReactApp[React Client]
        User -- "Add Contact" --> ReactApp
        ReactApp -- "Poll New Emails" --> CR_Back
        ReactApp -- "Play Audio (GCS URL)" --> User
        ReactApp -- "Send Voice Blob" --> CR_Back
        ReactApp -- "POST /api/contacts" --> CR_Back
    end

```

`5. Generate Audio`での参考Pythonコード
```
def synthesize_text():
    """Synthesizes speech from the input string of text."""
    from google.cloud import texttospeech

    text = "Hello there."
    client = texttospeech.TextToSpeechClient()

    input_text = texttospeech.SynthesisInput(text=text)

    # Note: the voice can also be specified by name.
    # Names of voices can be retrieved with client.list_voices().
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Chirp3-HD-Charon",
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=input_text,
        voice=voice,
        audio_config=audio_config,
    )

    # The response's audio_content is binary.
    with open("output.mp3", "wb") as out:
        out.write(response.audio_content)
        print('Audio content written to file "output.mp3"')
```


### 技術スタック詳細

| 領域 | 技術要素 | 詳細・備考 |
| --- | --- | --- |
| **Frontend** | React, TypeScript | Vite利用。UIはshadcn/ui。音声入力はWeb Speech API。 |
| **Auth** | **Firebase Authentication** | Google Sign-Inプロバイダを使用。 |
| **Backend** | FastAPI (Python 3.10+) | 非同期処理 (`async/await`) 必須。 |
| **Database** | **Cloud SQL (PostgreSQL)** | `SQLAlchemy` (ORM) で操作。 |
| **File Storage** | **Cloud Storage (GCS)** | 音声ファイル(.mp3)置き場。 |
| **Messaging** | Cloud Pub/Sub | GmailからのPush通知受信用。 |
| **AI (LLM)** | **Gemini 2.5 Flash** | 感情変換、メール清書用。 |
| **AI (Voice - TTS)** | **Google Cloud Text-to-Speech** | ギャル語テキストを音声化（日本語）。候補: `ja-JP-Wavenet-B`, `ja-JP-Neural2-B`, `ja-JP-Journeys-1` など。最終選定は実装時に決定。 |
| **Infra** | Terraform, Cloud Run | Dockerコンテナデプロイ。 |

## 3. 認証・セキュリティ仕様 (重要)

ハッカソン向けに「実装コスト」と「動作の確実性」を最適化した設定です。

### A. Google Cloud Console 設定 (OAuth)

* **User Type**: **External (外部)**
* **Publishing Status**: **Testing (テスト)**
* **Test Users**: 開発メンバーとデモ用アカウント（上司役、自分役）のGmailアドレスを必ず登録する。
* **Scopes**:
* `https://www.googleapis.com/auth/gmail.readonly` (受信・本文取得)
* `https://www.googleapis.com/auth/gmail.send` (メール送信)
* `userinfo.email`, `userinfo.profile` (ログイン用)



### B. Firebase Authentication 設定

1. Firebase Consoleでプロジェクト作成（Google Cloudプロジェクトと紐付け）。
2. Authentication > Sign-in method で **Google** を有効化。
3. React側: `firebase/auth` の `signInWithPopup` を使用。

### C. Gmail API OAuth (サーバーサイド)

Gmail APIアクセス用のOAuthはBackend側でRefresh Tokenを管理する方式を採用。

1. ユーザーがGmail連携ボタンをクリック → Backend が認証URLを生成
2. Google OAuth画面で権限付与 → 認証コードがBackendに返却
3. Backend が認証コードをRefresh Token/Access Tokenに交換し、`users`テーブルに保存
4. メール取得時はBackendがAccess Tokenを使用（期限切れ時は自動更新）

**メリット**: Refresh Tokenをサーバーで安全に管理、Webhook処理時もトークン更新可能



## 4. データモデル (Cloud SQL Schema)

**Table: `users`**
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | SERIAL (PK) | 一意のID |
| `firebase_uid` | VARCHAR (UNIQUE) | Firebase Authentication UID |
| `email` | VARCHAR | ユーザーメールアドレス |
| `gmail_refresh_token` | TEXT | Gmail API用Refresh Token |
| `gmail_access_token` | TEXT | Gmail API用Access Token |
| `gmail_token_expires_at` | TIMESTAMP | Access Token有効期限 |
| `created_at` | TIMESTAMP | 作成日時 |

**Table: `contacts`**
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | SERIAL (PK) | 一意のID |
| `user_id` | INTEGER (FK) | ユーザーID |
| `contact_email` | VARCHAR | 相手のメールアドレス |
| `contact_name` | VARCHAR | 相手の名前（例: "鬼瓦部長"） |
| `gmail_query` | VARCHAR | Gmail API クエリ（期間指定など） |
| `is_learning_complete` | BOOLEAN | 学習完了フラグ |
| `created_at` | TIMESTAMP | 作成日時 |

**Table: `contact_context`**
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | SERIAL (PK) | 一意のID |
| `contact_id` | INTEGER (FK) | 相手連絡先ID |
| `learned_patterns` | TEXT | 学習した相手のメール特徴とユーザーの返信パターン |
| `updated_at` | TIMESTAMP | 更新日時 |

**Table: `emails`**
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | SERIAL (PK) | 一意のID |
| `user_id` | INTEGER (FK) | ユーザーID |
| `contact_id` | INTEGER (FK) | 相手連絡先ID |
| `google_message_id` | VARCHAR | GmailのMessage ID（重複処理防止用） |
| `sender_email` | VARCHAR | 送信者メール |
| `sender_name` | VARCHAR | 送信者名（例: "鬼瓦部長"） |
| `subject` | VARCHAR | 件名 |
| `original_body` | TEXT | 原文（袋とじの中身） |
| `converted_body` | TEXT | ギャル語変換後のテキスト |
| `audio_url` | VARCHAR | GCSの公開URL (Signed URLでも可) |
| `received_at` | TIMESTAMP | 受信日時 |
| `is_processed` | BOOLEAN | AI処理完了フラグ |

**Table: `replies`**
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | SERIAL (PK) | 一意のID |
| `user_id` | INTEGER (FK) | ユーザーID |
| `email_id` | INTEGER (FK) | 返信元メールID |
| `user_voice_input` | TEXT | ユーザーの音声入力テキスト |
| `business_reply` | TEXT | AI清書後のビジネスメール |
| `is_sent` | BOOLEAN | 送信完了フラグ |
| `sent_at` | TIMESTAMP | 送信日時 |
| `created_at` | TIMESTAMP | 作成日時 |

## 5. 機能要件とAPI仕様

### ① メール受信 & バックグラウンド処理 (Backend)

**Trigger**: Pub/Sub Push Notification -> `POST /api/webhook/gmail`

* **処理フロー**:
1. Pub/Subからのデータを受け取り、即座に `200 OK` を返す。
2. `BackgroundTasks` でメイン処理を開始。
3. Gmail API (`users.messages.get`) で本文取得。
4. **Gemini (Character Convert)**: 原文をギャル語に変換。
5. **Google Cloud TTS**: ギャル語テキストを音声化。
6. **GCS Upload**: 音声ファイルをGCSバケット (`gs://your-project-audio/`) に保存。
7. **DB Insert**: `emails` テーブルにレコード作成。



### ② ダッシュボード表示 (Frontend)

**Endpoint**: `GET /api/emails`

* **Request**: `Authorization: Bearer <Firebase_ID_Token>`
* **Response**: `emails` テーブルのレコード一覧（降順）。
* **UI挙動**:
  * `converted_body` をチャットの吹き出しのように表示。
  * 再生ボタンで `audio_url` の音声を再生。



### ③ 音声返信 & 送信 (Frontend -> Backend)

**Endpoint**: `POST /api/reply`

* **Request**: `FormData` (テキスト：ユーザーの音声認識結果, 対象の `email_id`)
  * ※ 音声→テキスト変換は React の Web Speech API でブラウザ側で完了
* **処理フロー**:
1. ユーザーが入力したテキスト（例：「了解っす」）をバックエンドで受け取る。
2. **contact_context を参照**: 相手の過去パターンを取得。
3. **Gemini (Business Writer)**: テキストをビジネスメールに変換（例：「承知いたしました。」）。
4. **Gmail API (`users.messages.send`)**: 変換後のテキストで返信メールを送信。
5. **DB Insert**: `replies` テーブルにレコード作成。
6. **Response**: 送信完了ステータスと、実際に送った文面。



### ④ 相手連絡先追加 & 学習処理 (Frontend -> Backend, 非同期)

**Endpoint**: `POST /api/contacts`

* **Request**:
  ```json
  {
    "contact_email": "bucho@company.com",
    "contact_name": "鬼瓦部長",
    "gmail_query": "from:bucho@company.com after:2024/01/01"
  }
  ```
* **即座の Response**: `200 OK` + `{ "contact_id": 123, "status": "learning_started" }`
* **バックグラウンド処理フロー** (`BackgroundTasks` で非同期実行):
1. `contacts` テーブルに相手連絡先を作成（`is_learning_complete = false`）。
2. Gmail API で過去メール（30件程度）を取得（`gmail_query` を使用）。
3. **Gemini (Learning Analyzer)**: 過去メールを分析して「相手のメール特徴」と「ユーザーの返信パターン」を学習。
4. `contact_context` テーブルに `learned_patterns` を保存。
5. `contacts.is_learning_complete = true` に更新。
6. ※ 完了時はWebSocketやポーリングで Frontend に通知（実装時に決定）。



## 6. プロンプトエンジニアリング

Backendのコード内に定数として埋め込みます。

### ギャル変換プロンプト (Gemini)

```python
SYSTEM_PROMPT_GYARU = """
あなたは「ハイテンションで超ポジティブなギャル」です。
ユーザー（先輩）のメンタルを守るため、送られてきたメールを以下のルールで「ギャル語」に超訳してください。

【ルール】
1. 一人称は「ウチ」、相手は「〇〇さん」、ユーザーは「先輩」と呼ぶ。
2. 語尾は「〜だし！」「〜じゃね？」「〜なんだけどｗ」「草」などを自然に使う。
3. 文脈に関わらず、とにかく明るく、先輩を全肯定するスタンスで。
4. 怒られている内容でも「〇〇さん、ガチ焦っててウケるｗ 先輩のこと頼りにしてる証拠じゃん？」のようにポジティブに解釈する。
5. 絵文字を大量に使うこと (💖, ✨, 🥺, 🎉, 🔥)。

【入力メール】
{original_mail_body}

【出力】
ギャル語の翻訳テキストのみを出力してください。
"""

```

### ビジネス清書プロンプト (Gemini)

```python
SYSTEM_PROMPT_BUSINESS = """
あなたは「超一流の秘書」です。
ユーザーの口語（ラフな音声入力）を元に、上司に対する非常に丁寧で洗練されたビジネスメールの返信文を作成してください。

【相手の特徴と過去パターン】
{learned_patterns}

【入力テキスト】
{user_voice_text}

【出力】
件名: (Re: 元の件名)
本文: (適切な挨拶、本文、結び)
  ※ 相手の特徴とユーザーの過去パターンを踏まえた、自然な返信を作成してください。
"""

```

### 学習分析プロンプト (Gemini)

```python
SYSTEM_PROMPT_LEARNING = """
あなたは「メールコミュニケーション分析スペシャリスト」です。
以下の過去メールのやり取り（相手からのメール + ユーザーの返信）を分析して、以下を出力してください：

【分析項目】
1. 相手のメール特徴（語調、よく使う表現、要求パターンなど）
2. ユーザーの返信パターン（よく使う表現、対応スタイルなど）

【過去メール履歴】
{email_history}

【出力】
相手のメール特徴:
- （相手のメール特徴を簡潔に記述）

ユーザーの返信パターン:
- （ユーザーの返信パターンを簡潔に記述）
"""

```

## 7. 開発・デプロイ手順書（ハッカソン当日用）

### Step 1: インフラ準備 (Terraform & GCloud)

1. GCPプロジェクト作成。
2. API有効化: `Gmail API`, `Cloud Pub/Sub API`, `Cloud Run API`, `Cloud SQL Admin API`.
3. `gcloud auth application-default login`
4. Terraform apply (Cloud SQL, Pub/Sub, Cloud Run, GCS)。

### Step 2: Backend実装 (FastAPI)

1. `/api/webhook/gmail` の実装（ログ出力だけでいいので疎通確認）。
2. Cloud Runへデプロイ。
3. **Gmail Watch設定**: ローカルまたはワンショットスクリプトを実行し、`users.watch` APIを叩いて、Gmailの通知先をCloud Pub/Subトピックに紐付ける。

### Step 3: Frontend実装 & 結合

1. Firebase Authのログイン画面作成。
2. メール一覧取得の結合。
3. 「再生ボタン」の実装。

### Step 4: デモ準備

1. **シナリオ**: 上司役のアカウントから「至急！！」というメールを送る。
2. **確認**: PC画面にメールが通知されて、ギャルが読み上げ、返信する流れをリハーサル。


### ページの色味
色の役割,Hex Code,色の名前,説明
Main Background,#F2F0EB,Warm Washi,真っ白ではなく、少し黄みがかった和紙のような白。目の疲れを軽減します。
Primary (Brand),#4A6C74,Deep Calm Teal,深い青緑。知性と落ち着きを表します。アイコンの「暗い部分」とリンクさせます。
Secondary (Accent),#D6A884,Muted Apricot,落ち着いたオレンジベージュ。アイコンの「とげが抜けた光」や「肌のぬくもり」を表現。
Surface (Card),#FFFFFF,Pure White,メール本文などを表示するカード部分。清潔感を保ちます。
Text (Body),#464646,Soft Charcoal,真っ黒（#000）ではなく、柔らかいチャコールグレー。
Text (Muted),#8C8C8C,Stone Gray,補足情報や、読みたくない「原文」の表示などに使用。


### その他

* [ ] **GCSバケットの権限**: ハッカソン中は、生成された音声ファイルのURLに誰でもアクセスできるように、バケット設定を `allUsers` に `Storage Object Viewer` を付与しておくと、Frontendでの再生エラー（CORSや認証など）を防げて楽です。
* [ ] **APIキー管理**: Gemini API Key は、Cloud Runの環境変数 (`SECRET`) に安全に格納してください。
