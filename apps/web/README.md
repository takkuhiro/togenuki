<p align="center">
  <img src="../../assets/icon_square_transparent.png" alt="TogeNuki" width="120" />
</p>

# TogeNuki Web

TogeNuki のフロントエンドアプリケーションです。React + TypeScript で構築された SPA で、メールダッシュボード・音声再生・音声入力返信・連絡先管理の機能を提供します。

## 技術スタック

| 項目 | 技術 |
|------|------|
| **フレームワーク** | React 19 |
| **言語** | TypeScript 5.7 |
| **ビルドツール** | Vite 6 |
| **ルーティング** | React Router v7 |
| **認証** | Firebase Authentication (Google Sign-In) |
| **Linter / Formatter** | Biome |
| **テスト** | Vitest + Testing Library |
| **音声入力** | Web Speech API (ブラウザネイティブ) |

## ディレクトリ構成

```
src/
├── main.tsx           # エントリーポイント
├── App.tsx            # ルートコンポーネント・ルーティング
├── components/        # UIコンポーネント
│   ├── AudioPlayer.tsx      # 音声再生プレーヤー
│   ├── CharacterSelector.tsx # キャラクター選択
│   ├── EmailCard.tsx        # メールカード表示
│   ├── EmailList.tsx        # メール一覧 (ダッシュボード)
│   ├── ContactCard.tsx      # 連絡先カード表示
│   ├── ContactForm.tsx      # 連絡先登録フォーム
│   ├── ContactList.tsx      # 連絡先一覧
│   └── SplitActionButton.tsx # 送信/下書き切替ボタン
├── pages/             # ページコンポーネント
│   ├── ContactsPage.tsx     # 連絡先管理ページ
│   └── GmailCallback.tsx    # Gmail OAuth コールバック
├── contexts/          # React Context
│   └── AuthContext.tsx       # 認証状態管理
├── api/               # API呼び出しモジュール
│   ├── characters.ts        # キャラクターAPI
│   ├── contacts.ts          # 連絡先API
│   ├── emails.ts            # メール取得API
│   └── reply.ts             # 返信API
├── hooks/             # カスタムフック
│   └── useSpeechRecognition.ts  # Web Speech API ラッパー
├── types/             # 型定義
├── firebase/          # Firebase 設定
└── __tests/           # テストファイル
```

## セットアップ

### 前提条件

- Node.js 18+

### インストール

```bash
npm install
```

### 環境変数

`.env` ファイルを作成し、以下の値を設定してください。

```env
VITE_API_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=your-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
VITE_FIREBASE_APP_ID=your-app-id
```

## 開発

```bash
# 開発サーバー起動 (http://localhost:5173)
npm run dev

# プロダクションビルド
npm run build

# ビルドプレビュー
npm run preview
```

## テスト

```bash
# ウォッチモード
npm run test

# 単発実行
npm run test:run
```

## コード品質

```bash
# lint + format チェック
npm run check

# lint + format 自動修正
npm run check:fix

# lint のみ
npm run lint

# format のみ
npm run format
```

## ページ構成

| パス | コンポーネント | 説明 |
|------|---------------|------|
| `/` | LandingPage | ログイン・Gmail連携フロー |
| `/emails` | EmailList | メールダッシュボード (認証必須) |
| `/contacts` | ContactsPage | 連絡先管理 (認証必須) |
| `/auth/gmail/callback` | GmailCallback | Gmail OAuth コールバック |

## デザインカラー

| 役割 | カラーコード | 説明 |
|------|-------------|------|
| 背景 | `#F2F0EB` | 和紙のような温かみのある白 |
| プライマリ | `#4A6C74` | 深い青緑（知性と落ち着き） |
| アクセント | `#D6A884` | 落ち着いたオレンジベージュ |
| カード背景 | `#FFFFFF` | ピュアホワイト |
| 本文テキスト | `#464646` | ソフトチャコール |
| 補足テキスト | `#8C8C8C` | ストーングレー |
