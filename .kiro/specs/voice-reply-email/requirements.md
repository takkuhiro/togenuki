# Requirements Document

## Introduction
本仕様は、TogeNuki（トゲヌキ）の中核機能である「音声入力による返信メール生成・送信」機能の要件を定義する。ユーザーが口語的に音声で返信内容を伝えると、AIがビジネスメールに清書し、Gmail経由で送信する。これにより、ビジネスメール作成の心理的負担と作業コストを大幅に軽減する。

## Requirements

### Requirement 1: 音声入力による返信文の口述
**Objective:** ユーザーとして、メールへの返信内容を音声で口述したい。キーボードでビジネスメールを作成する負担を軽減するため。

#### Acceptance Criteria
1. When メールカードが展開され処理済みの場合, the EmailCard shall 「とげぬき再生」ボタン（AudioPlayer）の隣に音声入力ボタンを表示する
2. When ユーザーが音声入力ボタンを押下した場合, the EmailCard shall 同一カード内に音声入力エリアを展開表示する
3. When ユーザーが録音開始ボタンを押下した場合, the Voice Reply UI shall Web Speech API を使用してブラウザ上で音声認識を開始する
4. While 音声認識が実行中の場合, the Voice Reply UI shall リアルタイムで認識テキストをプレビュー表示する
5. When ユーザーが録音停止ボタンを押下した場合, the Voice Reply UI shall 音声認識を停止し、最終的な認識テキストを確定する
6. When 音声認識が完了した場合, the Voice Reply UI shall 認識されたテキストを編集可能なテキストエリアに表示する
7. The Voice Reply UI shall 認識テキストの手動編集を許可する

### Requirement 2: AIによるビジネスメール清書
**Objective:** ユーザーとして、口語的な音声入力がビジネスメールとして自動的に清書されてほしい。相手に適切な文体で返信するため。

#### Acceptance Criteria
1. When ユーザーが認識テキストの清書を要求した場合, the Reply Service shall 口語テキストをGemini APIに送信してビジネスメール文体に変換する
2. When 清書リクエストを処理する場合, the Reply Service shall 元のメールの内容をコンテキストとしてAIに提供する
3. Where 相手との過去のやり取りパターン（contact_context）が存在する場合, the Reply Service shall 過去パターンを考慮して清書のトーンと文体を調整する
4. When 清書が完了した場合, the Voice Reply UI shall 生成されたビジネスメール文をプレビュー表示する
5. The Voice Reply UI shall 清書されたメール本文の手動編集を許可する
6. When ユーザーが清書結果に満足しない場合, the Voice Reply UI shall 再清書を要求できるボタンを提供する

### Requirement 3: メール送信
**Objective:** ユーザーとして、清書された返信メールをそのまま送信したい。スムーズにメール返信を完了するため。

#### Acceptance Criteria
1. When ユーザーが送信ボタンを押下した場合, the Reply Service shall Gmail API を使用して返信メールを送信する
2. When メールを送信する場合, the Reply Service shall 元のメールへの返信（In-Reply-To / References ヘッダー）として送信する
3. When メール送信が成功した場合, the Voice Reply UI shall 送信完了のフィードバックを表示する
4. When メール送信が成功した場合, the Reply Service shall 送信済みメールをデータベースに記録する
5. If メール送信が失敗した場合, the Reply Service shall エラー内容をユーザーに通知し、再送信を可能にする

### Requirement 4: 送信前確認（確認・送信の2段階）
**Objective:** ユーザーとして、メール送信前に宛先・件名・本文を最終確認したい。誤送信を防止するため。

#### Acceptance Criteria
1. When メール下書き（清書結果）が完成した場合, the Voice Reply UI shall 「確認」ボタンと「送信」ボタンを分けて表示する
2. The Voice Reply UI shall 「送信」ボタンを常に有効状態で表示し、プレビュー確認なしでも即座に送信できるようにする
3. When ユーザーが「確認」ボタンを押下した場合, the Voice Reply UI shall 宛先（To）、件名（Subject）、本文を含む送信プレビューを表示する
4. The Voice Reply UI shall 件名を元のメールの件名に「Re: 」を付与した形で自動設定する
5. When 送信プレビュー表示中にユーザーが「戻る」を選択した場合, the Voice Reply UI shall 編集画面に戻る
6. When ユーザーが「送信」ボタンを押下した場合, the Voice Reply UI shall メール送信処理を開始する

### Requirement 5: エラーハンドリングとフォールバック
**Objective:** ユーザーとして、音声認識やAI処理が失敗した場合でも返信作業を継続したい。作業の中断を防ぐため。

#### Acceptance Criteria
1. If Web Speech API が利用不可の場合, the Voice Reply UI shall テキスト入力のみのフォールバックモードを提供する
2. If 音声認識中にエラーが発生した場合, the Voice Reply UI shall エラーメッセージを表示し、再試行ボタンを表示する
3. If AI清書リクエストがタイムアウトまたは失敗した場合, the Reply Service shall エラーメッセージを返却し、ユーザーが手動でメール本文を編集できる状態を維持する
4. If Gmail OAuth トークンが期限切れの場合, the Reply Service shall トークンのリフレッシュを試行し、失敗時は再認証を促す
