# Research & Design Decisions: character-selection

## Summary
- **Feature**: `character-selection`
- **Discovery Scope**: Extension（既存システムの拡張）
- **Key Findings**:
  - Google Cloud TTS Chirp3-HDは日本語で8音声（男性4・女性4）を提供。キャラクターごとに異なる音声を割り当て可能
  - 既存の`convert_to_gyaru()`は`system_prompt`パラメータを外部から受け取る汎用メソッドにリファクタリング可能
  - キャラクター定義はコード内定数（dataclass）で管理し、DB不要

## Research Log

### TTS音声選定
- **Context**: 3キャラクターに適した日本語TTS音声を選定する必要がある
- **Sources Consulted**: [Google Cloud TTS Chirp3-HD ドキュメント](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd), [Supported voices](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types), [Chirp3 HD Japanese usage blog](https://calvincchan.com/blog/250531-google-tts-with-chirp3-hd-in-japanese)
- **Findings**:
  - Chirp3-HD 日本語音声（8種）: Male（Puck, Charon, Fenrir, Orus）、Female（Aoede, Kore, Leda, Zephyr）
  - 現在のギャルは `ja-JP-Chirp3-HD-Callirrhoe` を使用（標準8音声外の拡張音声の可能性あり）
  - 音声の特性は名前からは判断できず、実際に聴いて確認が必要
- **Implications**:
  - 暫定的な音声割り当て:
    - 全肯定ギャル: `ja-JP-Chirp3-HD-Callirrhoe`（現行、変更なし）
    - 優しい先輩: `ja-JP-Chirp3-HD-Aoede`（女性・暫定）
    - 冷静な執事: `ja-JP-Chirp3-HD-Charon`（男性・暫定）
  - 実装時に実際の音声を聴いて最終確認が必要

### GeminiServiceリファクタリング方針
- **Context**: 現在の`convert_to_gyaru()`をキャラクター対応に汎用化する方法
- **Sources Consulted**: 既存の `gemini_service.py` コード分析
- **Findings**:
  - `convert_to_gyaru()` のコアロジックは: システムプロンプト + ユーザープロンプト → Gemini API呼び出し
  - `system_prompt` を引数化するだけで汎用化可能
  - 既存テストは `convert_to_gyaru()` を名前でモックしているため、メソッド名変更時はテスト修正が必要
- **Implications**:
  - 新メソッド `convert_email(system_prompt, sender_name, original_body)` を追加
  - `convert_to_gyaru()` は `convert_email()` へのエイリアスとして一時的に残すか、完全に置き換える
  - 完全置き換えを推奨（呼び出し箇所が限定的: email_processor.py のみ）

### キャラクター定義の格納形式
- **Context**: キャラクター定義をどの形式で管理するか
- **Sources Consulted**: Pythonの`dataclass`パターン、既存コードの`@dataclass`使用箇所（`email_processor.py`）
- **Findings**:
  - プロジェクト内で`@dataclass`は既に使用されている（`NotificationResult`, `MessageResult`等）
  - Enumはメソッド付きにできるが、属性が多いとコードが冗長
  - dictは型安全性が低い
- **Implications**: `@dataclass(frozen=True)` でimmutableなキャラクター定義を作成し、モジュールレベル定数として保持

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| Hybrid | 新規character_service + 既存サービスの汎用化 | 責任分離が明確、既存パターン準拠 | テスト修正が広範囲 | gap-analysis推奨 |

## Design Decisions

### Decision: GeminiServiceのリファクタリング
- **Context**: `convert_to_gyaru()` をキャラクター対応にする
- **Alternatives Considered**:
  1. 新メソッド追加 + 旧メソッド保持
  2. メソッド名変更 + 全呼び出し箇所更新
- **Selected Approach**: メソッド名変更（`convert_email()`）
- **Rationale**: 呼び出し箇所が`email_processor.py`のみで影響範囲が限定的。旧名を残すと二重管理になる
- **Trade-offs**: テスト修正が必要だが、機械的な変更のみ
- **Follow-up**: テスト全件パス確認

### Decision: キャラクター定義の格納形式
- **Context**: 3キャラクターの定義データの管理方法
- **Alternatives Considered**:
  1. dict
  2. dataclass
  3. Enum
- **Selected Approach**: `@dataclass(frozen=True)` + モジュールレベル定数
- **Rationale**: 型安全、immutable、既存パターンと一致
- **Trade-offs**: Enumより柔軟だが、IDの一意性は手動管理
- **Follow-up**: なし

### Decision: TTSServiceの音声切替方式
- **Context**: キャラクターごとに異なるTTS音声を使用する
- **Alternatives Considered**:
  1. TTSService初期化時にvoice_nameを設定
  2. メソッド呼び出し時にvoice_nameを引数で渡す
- **Selected Approach**: メソッド引数（`voice_name: str | None = None`、None時はSettings値をフォールバック）
- **Rationale**: TTSServiceはシングルトン的に使われるため、初期化時固定は不適切。引数渡しなら後方互換性も維持
- **Trade-offs**: 毎回voice_nameを渡す必要があるが、EmailProcessorからの呼び出しのみなので問題なし
- **Follow-up**: なし

## Risks & Mitigations
- **TTS音声の品質**: 暫定選定した音声がキャラクターに合わない可能性 → 実装時に聴き比べて調整
- **テスト修正の漏れ**: `convert_to_gyaru` の参照箇所が多い → grep で全箇所を網羅的に修正
- **既存ユーザーへの影響**: NULLの`selected_character_id`がデフォルトとして正しく動作するか → フォールバックロジックで保証

## References
- [Google Cloud TTS Chirp3-HD](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd) — 利用可能な音声モデルと言語
- [Supported voices and languages](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types) — 全音声リスト
- [Chirp3 HD Japanese blog](https://calvincchan.com/blog/250531-google-tts-with-chirp3-hd-in-japanese) — 日本語でのChirp3-HD使用例
