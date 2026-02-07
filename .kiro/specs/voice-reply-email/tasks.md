# Implementation Plan

- [x] 1. データモデル拡張とDBマイグレーション
- [x] 1.1 Emailモデルに返信関連カラムを追加しマイグレーションを作成する
  - Emailモデルに`reply_body`（Text, nullable）、`reply_subject`（Text, nullable）、`replied_at`（DateTime, nullable）、`reply_google_message_id`（String, nullable）カラムを追加する
  - Alembicマイグレーションファイルを生成し、既存データに影響がないことを確認する
  - マイグレーションの適用と、テスト用のロールバックを検証する
  - _Requirements: 3.4_
  - **ユーザー確認**: マイグレーションファイル生成後、開発者にTerraformやCloud SQL環境へのマイグレーション適用を依頼する。ローカル環境でのマイグレーション適用結果（`alembic upgrade head`）の成功を確認してもらう

- [x] 2. GeminiService にビジネスメール清書メソッドを追加する
- [x] 2.1 (P) 口語テキストをビジネスメール文体に変換するメソッドを実装する
  - 口語テキスト、元メール本文、送信者名、contact_context（任意）を受け取り、ビジネスメールを生成する
  - 清書用のシステムプロンプトを作成する（元メールの文脈を考慮、敬語・定型表現の適切な使用）
  - contact_contextが提供された場合は、過去のやり取りパターンを踏まえたトーン調整を行う
  - 既存のResult型パターン（Ok/Err）でエラーハンドリングする
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 2.2 (P) 清書メソッドのユニットテストを作成する
  - 正常系：口語テキストがビジネスメール文体に変換されること
  - contact_contextありの場合にプロンプトに含まれること
  - 空テキストでINVALID_INPUTエラーが返ること
  - APIタイムアウト・レートリミットのエラーケース
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 3. GmailApiClient にメール送信メソッドを追加する
- [x] 3.1 (P) MIMEメッセージを構築しGmail API経由で返信メールを送信するメソッドを実装する
  - 宛先、件名、本文、threadId、In-Reply-To、Referencesを受け取る
  - MIMEメッセージをbase64urlエンコードし、threadIdと共にGmail API messages.sendに送信する
  - 元メールのMessage-IDヘッダーを取得するために、既存のfetch_messageメソッドのパース結果からMessage-IDを抽出するユーティリティを追加する
  - 既存のhttpx.AsyncClientパターンとGmailApiErrorを使用したエラーハンドリング
  - _Requirements: 3.1, 3.2_

- [x] 3.2 (P) メール送信メソッドのユニットテストを作成する
  - 正常系：MIMEメッセージの構築が正しいこと（ヘッダー、エンコード）
  - Gmail API呼び出しのリクエスト形式が正しいこと
  - APIエラー時にGmailApiErrorが発生すること
  - _Requirements: 3.1, 3.2_
  - **ユーザー確認**: タスク2・3の完了後、Gmail APIの`gmail.send`スコープがOAuth同意画面に追加されているか確認を依頼する。必要であればGoogle Cloud Consoleでスコープの追加設定を行ってもらう

- [x] 4. ReplyService（清書・送信オーケストレーション）を実装する
- [x] 4.1 清書オーケストレーションメソッドを実装する
  - メールIDからEmailとContactContext（存在すれば）を取得する
  - ユーザーの所有権を検証する
  - GeminiServiceのビジネスメール清書メソッドを呼び出す
  - 件名を元メールの件名に「Re: 」を付与して自動生成する
  - 結果をResult型で返却する
  - _Requirements: 2.1, 2.2, 2.3, 4.4, 5.4_

- [x] 4.2 送信オーケストレーションメソッドを実装する
  - OAuthトークンの有効性を確認し、期限切れ時は自動リフレッシュする
  - GmailApiClientのメール送信メソッドを呼び出す
  - 送信成功時、Emailモデルのreply_body、reply_subject、replied_at、reply_google_message_idを更新する
  - 結果をResult型で返却する
  - _Requirements: 3.1, 3.2, 3.4, 5.4_

- [x] 4.3 ReplyServiceのユニットテストを作成する
  - 清書：メール取得→contact_context取得→Gemini呼び出し→件名生成の一連のフロー
  - 清書：存在しないメールIDでEMAIL_NOT_FOUNDが返ること
  - 清書：他ユーザーのメールでUNAUTHORIZEDが返ること
  - 送信：トークンリフレッシュ→Gmail送信→DB更新の一連のフロー
  - 送信：トークン期限切れでリフレッシュ失敗時のエラーハンドリング
  - 送信：Gmail API失敗時のエラーハンドリング
  - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.4, 5.3, 5.4_

- [x] 5. ReplyRouter（APIエンドポイント）とPydanticスキーマを実装する
- [x] 5.1 Pydanticスキーマを定義する
  - ComposeReplyRequest（rawText, min_length=1）
  - ComposeReplyResponse（composedBody, composedSubject）
  - SendReplyRequest（composedBody, composedSubject, min_length=1）
  - SendReplyResponse（success, googleMessageId）
  - camelCase変換のためのConfigDict設定
  - _Requirements: 2.1, 3.1_

- [x] 5.2 清書エンドポイント（POST /api/emails/{email_id}/compose-reply）を実装する
  - Firebase認証ミドルウェアによるユーザー検証
  - リクエストボディのバリデーション
  - ReplyServiceの清書メソッドを呼び出し、結果に応じたHTTPステータスを返却する（400, 404, 500, 503）
  - _Requirements: 2.1, 5.3_

- [x] 5.3 送信エンドポイント（POST /api/emails/{email_id}/send-reply）を実装する
  - Firebase認証ミドルウェアによるユーザー検証
  - リクエストボディのバリデーション
  - ReplyServiceの送信メソッドを呼び出し、結果に応じたHTTPステータスを返却する（400, 404, 409, 500, 503）
  - _Requirements: 3.1, 3.5, 5.4_

- [x] 5.4 ルーターをFastAPIアプリに登録する
  - main.pyにReplyRouterを/apiプレフィックスで登録する
  - _Requirements: 2.1, 3.1_

- [x] 5.5 エンドポイントの統合テストを作成する
  - 清書エンドポイント：認証成功→清書成功→200レスポンス
  - 清書エンドポイント：認証なし→401レスポンス
  - 清書エンドポイント：空テキスト→422レスポンス
  - 送信エンドポイント：認証成功→送信成功→200レスポンス
  - 送信エンドポイント：既に返信済み→409レスポンス
  - _Requirements: 2.1, 3.1, 3.5, 5.3, 5.4_
  - **ユーザー確認**: バックエンド実装（タスク1〜5）の完了後、ローカル環境でバックエンドサーバーを起動し、curlやHTTPクライアントで清書・送信エンドポイントの動作確認を依頼する。特にGemini API連携（清書結果の品質）とOAuthトークンのリフレッシュ動作を実際のAPIキーで確認してもらう

- [x] 6. useSpeechRecognition hookを実装する
- [x] 6.1 (P) Web Speech APIをラップするカスタムhookを実装する
  - SpeechRecognition / webkitSpeechRecognitionの存在をチェックし、利用可能フラグを提供する
  - 日本語（ja-JP）でcontinuousモードとinterimResultsを有効にした音声認識を管理する
  - 開始・停止・リセット関数と、確定テキスト・中間テキスト・エラー状態を返却する
  - ブラウザ非対応時はisAvailable=falseを返し、startListeningをno-opにする
  - onresultイベントで中間結果と確定結果を分離して管理する
  - onerrorイベントでエラーメッセージを日本語で設定する
  - _Requirements: 1.3, 1.4, 1.5, 5.1, 5.2_

- [x] 6.2 (P) useSpeechRecognition hookのユニットテストを作成する
  - SpeechRecognition APIのモックを使用
  - 利用可能判定：API存在時はtrue、非存在時はfalse
  - 開始→中間結果→確定結果の状態遷移
  - エラーハンドリング：onerrorイベント時のエラーメッセージ設定
  - API非対応時のフォールバック動作（startListeningがno-op）
  - _Requirements: 1.3, 1.4, 1.5, 5.1, 5.2_

- [x] 7. フロントエンドAPI関数を実装する
- [x] 7.1 (P) 清書・送信APIへのHTTPリクエスト関数を実装する
  - composeReply：idToken, emailId, rawTextを受け取り、POST /api/emails/{emailId}/compose-replyを呼び出す
  - sendReply：idToken, emailId, composedBody, composedSubjectを受け取り、POST /api/emails/{emailId}/send-replyを呼び出す
  - 既存のfetchEmails関数と同じパターン（Authorizationヘッダー、エラーハンドリング）を使用する
  - _Requirements: 2.1, 3.1_

- [x] 8. VoiceReplyPanelコンポーネントを実装する
- [x] 8.1 音声入力と認識テキスト編集フェーズを実装する
  - useSpeechRecognitionを使用して音声認識を管理する
  - 録音開始・停止ボタンとリアルタイムプレビュー表示
  - 認識完了後、テキストエリアに確定テキストを表示し手動編集を可能にする
  - Web Speech API非対応時はテキスト入力のみのフォールバックUIを表示する
  - 「清書」ボタンでAPI呼び出しフェーズに遷移する
  - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 5.1, 5.2_

- [x] 8.2 清書結果表示と確認・送信フェーズを実装する
  - 清書API呼び出し中のローディング表示
  - 清書結果のプレビュー表示と手動編集機能
  - 「再清書」ボタンで再度API呼び出し
  - 清書完了後に「確認」ボタンと「送信」ボタンを分離して表示
  - 「送信」ボタンは常に有効状態（プレビュー確認なしでも送信可能）
  - 「確認」ボタンで宛先・件名・本文の送信プレビュー表示
  - プレビュー表示中の「戻る」ボタンで編集画面に戻る
  - _Requirements: 2.4, 2.5, 2.6, 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 8.3 メール送信と完了フェーズを実装する
  - 送信API呼び出しと送信中ローディング表示
  - 送信完了フィードバックの表示
  - 送信失敗時のエラー表示と再送信ボタン
  - 清書失敗時のエラー表示と手動編集可能状態の維持
  - _Requirements: 3.3, 3.5, 4.6, 5.3_

- [x] 8.4 VoiceReplyPanelのユニットテストを作成する
  - フェーズ遷移：idle → recording → editing → composing → composed → previewing → sending → sent
  - 音声認識不可時のフォールバックUI表示
  - 清書完了後に「確認」と「送信」ボタンが両方表示されること
  - 「送信」ボタンが常に有効状態であること
  - 「確認」ボタンで送信プレビュー（To, Subject, Body）が表示されること
  - エラー時の再試行ボタン表示
  - _Requirements: 1.2, 1.3, 1.6, 2.4, 2.6, 3.3, 3.5, 4.1, 4.2, 4.3, 4.5, 5.1, 5.2, 5.3_
  - **ユーザー確認**: フロントエンド実装（タスク6〜8）の完了後、ブラウザで以下の動作確認を依頼する：（1）音声入力ボタンの表示と録音→テキスト認識の動作、（2）Web Speech API非対応ブラウザでのフォールバック表示、（3）清書ボタン押下後のビジネスメール生成結果の品質、（4）確認ボタンと送信ボタンの表示・動作

- [x] 9. EmailCardに音声入力ボタンを統合する
- [x] 9.1 EmailCardのアクションエリアに音声入力ボタンとVoiceReplyPanelを統合する
  - 処理済みメールカードの展開コンテンツ内で、AudioPlayer（とげぬき再生）の隣に音声入力ボタンを配置する
  - 音声入力ボタン押下時にVoiceReplyPanelを同一カード内に展開表示する
  - メールのid、senderEmail、senderName、subjectをVoiceReplyPanelにpropsとして渡す
  - _Requirements: 1.1, 1.2_

- [x] 9.2 EmailCard統合のユニットテストを作成する
  - 処理済みメールカード展開時に音声入力ボタンが表示されること
  - 未処理メールカードには音声入力ボタンが表示されないこと
  - 音声入力ボタン押下でVoiceReplyPanelが展開されること
  - _Requirements: 1.1, 1.2_
  - **ユーザー確認**: 全タスク完了後、E2Eでの通しテストを依頼する：メール一覧画面で処理済みメールカードを展開→音声入力ボタン押下→音声入力（または手動テキスト入力）→清書→確認→送信の一連のフローが正常に動作すること。実際のGmailアカウントへのテスト送信で、返信メールがスレッドに正しく紐づくことを確認してもらう
