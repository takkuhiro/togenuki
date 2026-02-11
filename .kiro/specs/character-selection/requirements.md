# Requirements Document

## Introduction

現在TogeNukiでは、メール感情変換のキャラクターが「全肯定ギャル」にハードコードされている（`gemini_service.py`のシステムプロンプト、`config.py`のTTS音声設定）。本機能では、事前定義された3つのキャラクターからユーザーが選択できる汎用的な仕組みを導入する。

キャラクターは以下の要素で構成される:
- **ペルソナ定義**: LLMへのシステムプロンプト（口調、変換ルール、例文）
- **TTS音声**: Google Cloud TTS の音声名
- **表示情報**: キャラクター名、説明文

## Requirements

### Requirement 1: キャラクター定義

**Objective:** As a 開発者, I want 事前定義されたキャラクターをシステムに登録できる仕組み, so that 新しいキャラクターの追加・変更が容易に行える

#### Acceptance Criteria

1. The TogeNuki API shall 3つの事前定義キャラクターを提供する: 「全肯定ギャル」「優しい先輩」「冷静な執事」
2. The TogeNuki API shall 各キャラクターについて以下の属性を保持する: キャラクターID、表示名、説明文、LLMシステムプロンプト、TTS音声名
3. The TogeNuki API shall キャラクター定義をコード内の定数として管理する（DB管理は不要）

### Requirement 2: キャラクター一覧取得

**Objective:** As a ユーザー, I want 選択可能なキャラクターの一覧を確認したい, so that 自分の好みに合ったキャラクターを選べる

#### Acceptance Criteria

1. When フロントエンドがキャラクター一覧APIを呼び出した時, the TogeNuki API shall 利用可能な全キャラクターのID・表示名・説明文を返却する
2. The TogeNuki API shall キャラクター一覧を認証なしでアクセス可能にする（公開情報のため）

### Requirement 3: キャラクター選択・永続化

**Objective:** As a ユーザー, I want 好みのキャラクターを選択し保存したい, so that 次回ログイン時も同じキャラクターが使われる

#### Acceptance Criteria

1. When ユーザーがキャラクターを選択した時, the TogeNuki API shall ユーザーの選択をデータベースに保存する
2. When 新規ユーザーが初めてアクセスした時, the TogeNuki API shall デフォルトキャラクターとして「全肯定ギャル」を適用する
3. When ユーザーがキャラクターを変更した時, the TogeNuki API shall 以降の新規メール処理に新しいキャラクターを適用する
4. The TogeNuki API shall 既に処理済みのメールのconverted_bodyおよびaudio_urlは変更しない（再変換は行わない）

### Requirement 4: キャラクターに基づくメール変換

**Objective:** As a ユーザー, I want 選択したキャラクターの口調でメールが変換される, so that 自分が心地よいと感じるキャラクターでメールを読める

#### Acceptance Criteria

1. When メールが受信され処理される時, the Email Processor shall ユーザーが選択中のキャラクターに対応するシステムプロンプトを使用してGemini APIを呼び出す
2. When メールが受信され処理される時, the TTS Service shall ユーザーが選択中のキャラクターに対応するTTS音声で音声を合成する
3. If ユーザーの選択キャラクターIDが無効な場合, the TogeNuki API shall デフォルトキャラクター（全肯定ギャル）にフォールバックする

### Requirement 5: キャラクター選択UI

**Objective:** As a ユーザー, I want 画面上でキャラクターを選択・変更したい, so that 直感的にキャラクターを切り替えられる

#### Acceptance Criteria

1. The TogeNuki Web shall 設定画面（連絡先管理画面）にキャラクター選択セクションを表示する
2. When ユーザーがキャラクターカードをタップした時, the TogeNuki Web shall 選択中のキャラクターを視覚的にハイライトし、即座にAPIへ保存リクエストを送信する
3. The TogeNuki Web shall 各キャラクターカードにキャラクター名と説明文を表示する
4. While キャラクター保存中, the TogeNuki Web shall ローディング状態を表示し、保存完了後に確定表示を更新する
