# Gap Analysis: character-selection

## 1. 現在の状態調査

### キャラクター関連のハードコード箇所

| # | ファイル | 箇所 | 内容 |
|---|---------|------|------|
| 1 | `apps/api/src/services/gemini_service.py:23-51` | `GYARU_SYSTEM_PROMPT` | ギャル変換用の固定システムプロンプト（口調ルール、変換例） |
| 2 | `apps/api/src/services/gemini_service.py:98-152` | `convert_to_gyaru()` | ギャル専用の変換メソッド（メソッド名・プロンプト参照がハードコード） |
| 3 | `apps/api/src/services/email_processor.py:224` | `_process_ai_conversion()` | `self.gemini_service.convert_to_gyaru()` を直接呼び出し |
| 4 | `apps/api/src/services/tts_service.py:43-45` | `TTSService.__init__()` | `settings.tts_voice_name` をインスタンス変数に格納（ユーザー単位の切替不可） |
| 5 | `apps/api/src/config.py:38` | `tts_voice_name` | `"ja-JP-Chirp3-HD-Callirrhoe"` がデフォルト値として固定 |
| 6 | `apps/api/src/models.py` | `User` モデル | `character_id` フィールドが存在しない |

### テストへの影響箇所

| ファイル | 影響範囲 |
|---------|---------|
| `tests/test_gemini_service.py` | `GYARU_SYSTEM_PROMPT` 参照テスト、`convert_to_gyaru()` テスト |
| `tests/test_email_processor.py` | `convert_to_gyaru()` 呼び出しのモックテスト |
| `tests/test_integration.py` | E2Eフロー内での `convert_to_gyaru` モック |
| `tests/test_tts_service.py` | `"ja-JP-Chirp3-HD-Callirrhoe"` を固定で参照 |

### 既存パターン（再利用可能）

- **Router-Service-Schema パターン**: `contacts.py` → `contact_repository.py` → `schemas/contact.py` と同じ構造を踏襲
- **BackgroundTasks パターン**: `email_processor.py` の非同期処理パターン
- **Result型パターン**: `GeminiService` が `Result[str, GeminiError]` を返却
- **Alembic マイグレーション**: 既存のカラム追加パターン（`d4e5f6a7b8c9_add_reply_fields_to_emails.py`）
- **フロントAPI パターン**: `api/contacts.ts` → `components/ContactList.tsx` → `pages/ContactsPage.tsx`

## 2. 要件ごとのギャップマップ

### Requirement 1: キャラクター定義

| 技術要素 | 現状 | ギャップ |
|---------|------|---------|
| キャラクター定義構造 | `GYARU_SYSTEM_PROMPT` のみ（単一定数） | **Missing**: 3キャラクターの定義構造（ID、名前、説明、プロンプト、TTS音声名） |
| 2つ目・3つ目のキャラクター | 存在しない | **Missing**: 「優しい先輩」「冷静な執事」のシステムプロンプトとTTS音声名 |
| TTS音声の選定 | `ja-JP-Chirp3-HD-Callirrhoe` のみ | **Research Needed**: キャラクターに合う日本語TTS音声の選定 |

### Requirement 2: キャラクター一覧取得API

| 技術要素 | 現状 | ギャップ |
|---------|------|---------|
| APIエンドポイント | 存在しない | **Missing**: `GET /api/characters` |
| Pydanticスキーマ | 存在しない | **Missing**: `CharacterResponse`, `CharactersListResponse` |

### Requirement 3: キャラクター選択・永続化

| 技術要素 | 現状 | ギャップ |
|---------|------|---------|
| DBカラム | `User` に `character_id` なし | **Missing**: `users.selected_character_id` カラム + Alembicマイグレーション |
| 更新API | 存在しない | **Missing**: `PUT /api/users/character` |
| デフォルト値 | N/A | **Constraint**: 既存ユーザーのNULL値はデフォルト（ギャル）として扱う |

### Requirement 4: キャラクターに基づくメール変換

| 技術要素 | 現状 | ギャップ |
|---------|------|---------|
| GeminiService | `convert_to_gyaru()` がプロンプトをハードコード | **Missing**: キャラクターIDに基づくプロンプト切替 |
| TTSService | `voice_name` がインスタンス固定 | **Missing**: 呼び出し時に音声名を指定する仕組み |
| EmailProcessor | `convert_to_gyaru()` を直接呼び出し | **Missing**: ユーザーのキャラクター取得 → 対応プロンプト/音声で処理 |

### Requirement 5: キャラクター選択UI

| 技術要素 | 現状 | ギャップ |
|---------|------|---------|
| 選択コンポーネント | 存在しない | **Missing**: `CharacterSelector.tsx` |
| API呼び出し | 存在しない | **Missing**: `api/characters.ts` |
| ページ統合 | `ContactsPage.tsx` にセクション追加可能 | **Constraint**: 既存レイアウトとの調和 |

## 3. 実装アプローチ

### Option A: 既存コンポーネント拡張

- `gemini_service.py` にキャラクター定義dictと汎用 `convert_email(character_id, ...)` を追加
- `tts_service.py` の `synthesize_and_upload()` に `voice_name` パラメータ追加
- `email_processor.py` にキャラクター取得→切替ロジック追加
- `ContactsPage.tsx` に直接セレクター埋め込み

**Trade-offs**:
- ✅ 新規ファイル最小限、既存パターン活用
- ❌ `gemini_service.py` が肥大化（プロンプト3つ分 + 定義dict）
- ❌ 責任の混在（変換ロジック + キャラクター管理）

### Option B: 新規キャラクターモジュール作成

新規ファイル:
- `services/character_service.py` - キャラクター定義管理
- `routers/characters.py` - API
- `schemas/character.py` - スキーマ
- `components/CharacterSelector.tsx` - UI
- `api/characters.ts` - フロントAPI
- `types/character.ts` - 型定義

**Trade-offs**:
- ✅ 責任分離が明確、テストしやすい
- ✅ 将来のキャラクター拡張が容易
- ❌ ファイル数増加
- ❌ 既存サービスとの接続インターフェース設計が必要

### Option C: ハイブリッド（推奨）

**新規作成**:
- `services/character_service.py` - キャラクター定義（定数）+ 取得ロジック
- `routers/characters.py` + `schemas/character.py` - APIレイヤー
- `components/CharacterSelector.tsx` + `api/characters.ts` - フロントUI

**既存拡張**:
- `GeminiService.convert_to_gyaru()` → `convert_email(system_prompt, sender_name, body)` にリファクタリング（汎用化）
- `TTSService.synthesize_and_upload()` に `voice_name` 引数追加（デフォルト値で後方互換）
- `EmailProcessorService._process_ai_conversion()` でユーザーのキャラクター設定を参照
- `User` モデルに `selected_character_id` カラム追加
- `ContactsPage.tsx` にキャラクター選択セクション追加

**Trade-offs**:
- ✅ キャラクター定義は独立管理、変換ロジックは既存の汎用化
- ✅ 既存テストへの影響が最小限（メソッド名変更 + パラメータ追加のみ）
- ✅ Backend Module Pattern（router/service/schema）に準拠

## 4. 実装規模・リスク

**Effort: M（3-7日）**
- 新規パターンは少なく、既存パターンの拡張が中心
- DBマイグレーション1件、API 2-3本、フロントコンポーネント1-2個
- テストの修正が広範囲だが機械的

**Risk: Low**
- 使用技術は全て既知（FastAPI, React, Alembic）
- キャラクター定義はコード内定数のため外部依存なし
- 既存の `convert_to_gyaru()` のリファクタリングは後方互換性を保ちやすい

## 5. Research Needed（設計フェーズへ持ち越し）

1. **TTS音声選定**: 「優しい先輩」「冷静な執事」に適する日本語TTS音声名の調査（Google Cloud TTS の利用可能な日本語音声一覧から選定）
2. **キャラクタープロンプト設計**: 2つの新キャラクターのシステムプロンプト詳細設計

## 6. 設計フェーズへの推奨事項

- **推奨アプローチ**: Option C（ハイブリッド）
- **キーとなる設計判断**:
  1. `GeminiService` のリファクタリング方針（メソッド名変更 vs 新メソッド追加）
  2. キャラクター定義の格納形式（dict vs dataclass vs Enum）
  3. TTS音声のキャラクターごとの選定
  4. ContactsPage のUI配置（キャラクター選択をどこに配置するか）
