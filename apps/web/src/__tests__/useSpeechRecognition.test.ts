/**
 * @vitest-environment jsdom
 */

import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';

// SpeechRecognition mock
let mockRecognition: {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: ReturnType<typeof vi.fn>;
  stop: ReturnType<typeof vi.fn>;
  abort: ReturnType<typeof vi.fn>;
  onresult: ((event: unknown) => void) | null;
  onerror: ((event: unknown) => void) | null;
  onend: (() => void) | null;
};

function createMockRecognition() {
  mockRecognition = {
    lang: '',
    continuous: false,
    interimResults: false,
    start: vi.fn(),
    stop: vi.fn(),
    abort: vi.fn(),
    onresult: null,
    onerror: null,
    onend: null,
  };
  return mockRecognition;
}

function createSpeechEvent(results: Array<{ transcript: string; isFinal: boolean }>) {
  return {
    results: results.map((r) => {
      const item = [{ transcript: r.transcript }];
      Object.defineProperty(item, 'isFinal', { value: r.isFinal });
      return item;
    }),
    resultIndex: 0,
  };
}

describe('useSpeechRecognition', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: SpeechRecognition available
    vi.stubGlobal(
      'SpeechRecognition',
      vi.fn(() => createMockRecognition())
    );
    vi.stubGlobal('webkitSpeechRecognition', undefined);
  });

  describe('利用可能判定 (Requirement 5.1)', () => {
    it('SpeechRecognition API存在時はisAvailable=trueを返す', () => {
      const { result } = renderHook(() => useSpeechRecognition());
      expect(result.current.isAvailable).toBe(true);
    });

    it('webkitSpeechRecognition存在時もisAvailable=trueを返す', () => {
      vi.stubGlobal('SpeechRecognition', undefined);
      vi.stubGlobal(
        'webkitSpeechRecognition',
        vi.fn(() => createMockRecognition())
      );

      const { result } = renderHook(() => useSpeechRecognition());
      expect(result.current.isAvailable).toBe(true);
    });

    it('SpeechRecognition API非存在時はisAvailable=falseを返す', () => {
      vi.stubGlobal('SpeechRecognition', undefined);
      vi.stubGlobal('webkitSpeechRecognition', undefined);

      const { result } = renderHook(() => useSpeechRecognition());
      expect(result.current.isAvailable).toBe(false);
    });
  });

  describe('音声認識の開始と停止 (Requirement 1.3, 1.5)', () => {
    it('startListeningでisListening=trueになる', () => {
      const { result } = renderHook(() => useSpeechRecognition());

      act(() => {
        result.current.startListening();
      });

      expect(result.current.isListening).toBe(true);
      expect(mockRecognition.start).toHaveBeenCalled();
    });

    it('startListeningで日本語(ja-JP)とcontinuous/interimResultsが設定される', () => {
      const { result } = renderHook(() => useSpeechRecognition());

      act(() => {
        result.current.startListening();
      });

      expect(mockRecognition.lang).toBe('ja-JP');
      expect(mockRecognition.continuous).toBe(true);
      expect(mockRecognition.interimResults).toBe(true);
    });

    it('lang引数を指定した場合はその言語が設定される', () => {
      const { result } = renderHook(() => useSpeechRecognition('en-US'));

      act(() => {
        result.current.startListening();
      });

      expect(mockRecognition.lang).toBe('en-US');
    });

    it('stopListeningでrecognition.stopが呼ばれ、onend後にisListeningがfalseになる', () => {
      const { result } = renderHook(() => useSpeechRecognition());

      act(() => {
        result.current.startListening();
      });
      expect(result.current.isListening).toBe(true);

      act(() => {
        result.current.stopListening();
      });

      // stop()は呼ばれるが、isListeningはonendまでtrueのまま
      expect(mockRecognition.stop).toHaveBeenCalled();
      expect(result.current.isListening).toBe(true);

      // onend発火でisListeningがfalseになる
      act(() => {
        mockRecognition.onend?.();
      });
      expect(result.current.isListening).toBe(false);
    });
  });

  describe('中間結果と確定結果の状態遷移 (Requirement 1.4)', () => {
    it('onresultで中間結果がinterimTranscriptに反映される', () => {
      const { result } = renderHook(() => useSpeechRecognition());

      act(() => {
        result.current.startListening();
      });

      act(() => {
        mockRecognition.onresult?.(
          createSpeechEvent([{ transcript: 'こんにちは', isFinal: false }])
        );
      });

      expect(result.current.interimTranscript).toBe('こんにちは');
      expect(result.current.transcript).toBe('');
    });

    it('onresultで確定結果がtranscriptに反映される', () => {
      const { result } = renderHook(() => useSpeechRecognition());

      act(() => {
        result.current.startListening();
      });

      act(() => {
        mockRecognition.onresult?.(
          createSpeechEvent([{ transcript: 'お疲れ様です', isFinal: true }])
        );
      });

      expect(result.current.transcript).toBe('お疲れ様です');
      expect(result.current.interimTranscript).toBe('');
    });

    it('確定結果が複数回来た場合は累積される', () => {
      const { result } = renderHook(() => useSpeechRecognition());

      act(() => {
        result.current.startListening();
      });

      act(() => {
        mockRecognition.onresult?.(
          createSpeechEvent([{ transcript: 'お疲れ様です。', isFinal: true }])
        );
      });

      act(() => {
        mockRecognition.onresult?.(
          createSpeechEvent([
            { transcript: 'お疲れ様です。', isFinal: true },
            { transcript: '明日の会議は', isFinal: true },
          ])
        );
      });

      expect(result.current.transcript).toBe('お疲れ様です。明日の会議は');
    });
  });

  describe('エラーハンドリング (Requirement 5.2)', () => {
    it('onerrorイベントでエラーメッセージが設定される', () => {
      const { result } = renderHook(() => useSpeechRecognition());

      act(() => {
        result.current.startListening();
      });

      act(() => {
        mockRecognition.onerror?.({ error: 'no-speech' });
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.isListening).toBe(false);
    });

    it('network errorでエラーメッセージが設定される', () => {
      const { result } = renderHook(() => useSpeechRecognition());

      act(() => {
        result.current.startListening();
      });

      act(() => {
        mockRecognition.onerror?.({ error: 'network' });
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.isListening).toBe(false);
    });

    it('not-allowed errorでエラーメッセージが設定される', () => {
      const { result } = renderHook(() => useSpeechRecognition());

      act(() => {
        result.current.startListening();
      });

      act(() => {
        mockRecognition.onerror?.({ error: 'not-allowed' });
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.isListening).toBe(false);
    });
  });

  describe('API非対応時のフォールバック動作 (Requirement 5.1)', () => {
    it('API非対応時にstartListeningがno-opになる', () => {
      vi.stubGlobal('SpeechRecognition', undefined);
      vi.stubGlobal('webkitSpeechRecognition', undefined);

      const { result } = renderHook(() => useSpeechRecognition());

      act(() => {
        result.current.startListening();
      });

      expect(result.current.isListening).toBe(false);
      expect(result.current.isAvailable).toBe(false);
    });
  });

  describe('リセット機能', () => {
    it('resetTranscriptでtranscriptとinterimTranscriptとerrorがクリアされる', () => {
      const { result } = renderHook(() => useSpeechRecognition());

      act(() => {
        result.current.startListening();
      });

      act(() => {
        mockRecognition.onresult?.(createSpeechEvent([{ transcript: 'テスト', isFinal: true }]));
      });

      expect(result.current.transcript).toBe('テスト');

      act(() => {
        result.current.resetTranscript();
      });

      expect(result.current.transcript).toBe('');
      expect(result.current.interimTranscript).toBe('');
      expect(result.current.error).toBeNull();
    });
  });

  describe('onendイベント', () => {
    it('onendイベントでisListeningがfalseになる', () => {
      const { result } = renderHook(() => useSpeechRecognition());

      act(() => {
        result.current.startListening();
      });

      expect(result.current.isListening).toBe(true);

      act(() => {
        mockRecognition.onend?.();
      });

      expect(result.current.isListening).toBe(false);
    });
  });

  describe('再開時の古いインスタンスのクリーンアップ', () => {
    it('startListeningを再度呼んだ後、古いrecognitionのonendが発火してもisListeningがfalseにならない', () => {
      const { result } = renderHook(() => useSpeechRecognition());

      // 1回目の録音開始
      act(() => {
        result.current.startListening();
      });
      const oldRecognition = mockRecognition;

      // 1回目の録音停止
      act(() => {
        result.current.stopListening();
      });
      // stopListeningではisListeningはまだtrue（onendを待つ）
      expect(result.current.isListening).toBe(true);

      // onend発火でisListeningがfalseになる
      act(() => {
        oldRecognition.onend?.();
      });
      expect(result.current.isListening).toBe(false);

      // 2回目の録音開始
      act(() => {
        result.current.resetTranscript();
        result.current.startListening();
      });
      expect(result.current.isListening).toBe(true);

      // 古いrecognitionのonendが遅延発火（callbackはnull化済み）
      act(() => {
        oldRecognition.onend?.();
      });

      // 新しい録音のisListeningはtrueのまま
      expect(result.current.isListening).toBe(true);
    });
  });
});
