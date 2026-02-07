/**
 * @vitest-environment jsdom
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { VoiceReplyPanel } from '../components/VoiceReplyPanel';

// --- Mocks ---

// Mock useSpeechRecognition hook
const mockStartListening = vi.fn();
const mockStopListening = vi.fn();
const mockResetTranscript = vi.fn();
let mockSpeechReturn = {
  isAvailable: true,
  isListening: false,
  transcript: '',
  interimTranscript: '',
  error: null as string | null,
  startListening: mockStartListening,
  stopListening: mockStopListening,
  resetTranscript: mockResetTranscript,
};

vi.mock('../hooks/useSpeechRecognition', () => ({
  useSpeechRecognition: () => mockSpeechReturn,
}));

// Mock reply API
const mockComposeReply = vi.fn();
const mockSendReply = vi.fn();

vi.mock('../api/reply', () => ({
  composeReply: (...args: unknown[]) => mockComposeReply(...args),
  sendReply: (...args: unknown[]) => mockSendReply(...args),
}));

// Mock useAuth
vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ idToken: 'test-token' }),
}));

// --- Helpers ---

const defaultProps = {
  emailId: 'email-123',
  senderEmail: 'sender@example.com',
  senderName: '田中太郎',
  subject: 'テスト件名',
};

function renderPanel(props = defaultProps) {
  return render(<VoiceReplyPanel {...props} />);
}

// --- Tests ---

describe('VoiceReplyPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSpeechReturn = {
      isAvailable: true,
      isListening: false,
      transcript: '',
      interimTranscript: '',
      error: null,
      startListening: mockStartListening,
      stopListening: mockStopListening,
      resetTranscript: mockResetTranscript,
    };
    mockComposeReply.mockReset();
    mockSendReply.mockReset();
  });

  describe('初期表示とフォールバック (Requirement 1.2, 5.1)', () => {
    it('音声認識が利用可能な場合、録音開始ボタンを表示する', () => {
      renderPanel();
      expect(screen.getByRole('button', { name: /録音開始|音声入力/ })).toBeInTheDocument();
    });

    it('テキスト入力エリアを表示する', () => {
      renderPanel();
      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    it('Web Speech API非対応時はテキスト入力のみのフォールバックUIを表示する', () => {
      mockSpeechReturn = { ...mockSpeechReturn, isAvailable: false };
      renderPanel();

      // 録音ボタンが表示されない
      expect(screen.queryByRole('button', { name: /録音開始/ })).not.toBeInTheDocument();
      // テキスト入力は表示される
      expect(screen.getByRole('textbox')).toBeInTheDocument();
      // フォールバックメッセージ
      expect(screen.getByText(/音声入力.*利用できません|テキスト入力/)).toBeInTheDocument();
    });
  });

  describe('音声認識フェーズ (Requirement 1.3, 1.4, 1.5, 1.6, 1.7)', () => {
    it('録音開始ボタン押下でstartListeningが呼ばれる', async () => {
      const user = userEvent.setup();
      renderPanel();

      const startBtn = screen.getByRole('button', { name: /録音開始|音声入力/ });
      await user.click(startBtn);

      expect(mockStartListening).toHaveBeenCalled();
    });

    it('録音中は停止ボタンが表示される', () => {
      mockSpeechReturn = { ...mockSpeechReturn, isListening: true };
      renderPanel();

      expect(screen.getByRole('button', { name: /録音停止|停止/ })).toBeInTheDocument();
    });

    it('録音中に中間テキストがリアルタイムプレビュー表示される', () => {
      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: true,
        interimTranscript: '明日の会議は',
      };
      renderPanel();

      expect(screen.getByText('明日の会議は')).toBeInTheDocument();
    });

    it('録音停止ボタン押下でstopListeningが呼ばれる', async () => {
      mockSpeechReturn = { ...mockSpeechReturn, isListening: true };
      const user = userEvent.setup();
      renderPanel();

      const stopBtn = screen.getByRole('button', { name: /録音停止|停止/ });
      await user.click(stopBtn);

      expect(mockStopListening).toHaveBeenCalled();
    });

    it('確定テキストが編集可能なテキストエリアに表示される', () => {
      mockSpeechReturn = {
        ...mockSpeechReturn,
        transcript: 'お疲れ様です。明日の会議よろしくお願いします。',
      };
      renderPanel();

      const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
      expect(textarea.value).toBe('お疲れ様です。明日の会議よろしくお願いします。');
    });

    it('認識テキストを手動で編集できる', async () => {
      mockSpeechReturn = {
        ...mockSpeechReturn,
        transcript: '元のテキスト',
      };
      const user = userEvent.setup();
      renderPanel();

      const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
      // ユーザーが末尾に追記する操作をシミュレート
      await user.type(textarea, '追記テキスト');

      expect(textarea.value).toBe('元のテキスト追記テキスト');
    });
  });

  describe('清書フェーズ (Requirement 2.4, 2.5, 2.6)', () => {
    it('テキスト入力後に清書ボタンが表示される', () => {
      mockSpeechReturn = { ...mockSpeechReturn, transcript: 'テスト' };
      renderPanel();

      expect(screen.getByRole('button', { name: /清書/ })).toBeInTheDocument();
    });

    it('清書ボタン押下でcomposeReply APIが呼ばれる', async () => {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });

      mockSpeechReturn = { ...mockSpeechReturn, transcript: 'お疲れ様' };
      const user = userEvent.setup();
      renderPanel();

      const composeBtn = screen.getByRole('button', { name: /清書/ });
      await user.click(composeBtn);

      expect(mockComposeReply).toHaveBeenCalledWith('test-token', 'email-123', {
        rawText: 'お疲れ様',
      });
    });

    it('清書中はローディング表示される', async () => {
      let resolveCompose: ((value: unknown) => void) | undefined;
      mockComposeReply.mockReturnValueOnce(
        new Promise((resolve) => {
          resolveCompose = resolve;
        })
      );

      mockSpeechReturn = { ...mockSpeechReturn, transcript: 'テスト' };
      const user = userEvent.setup();
      renderPanel();

      const composeBtn = screen.getByRole('button', { name: /清書/ });
      await user.click(composeBtn);

      expect(screen.getByText(/清書中/)).toBeInTheDocument();
      // スピナーが表示される
      expect(document.querySelector('.processing-spinner')).toBeInTheDocument();

      // Resolve to clean up
      resolveCompose?.({
        composedBody: '清書結果',
        composedSubject: 'Re: テスト件名',
      });
    });

    it('清書結果がプレビュー表示される', async () => {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '拝啓\n\n明日の会議について承知いたしました。\n\n敬具',
        composedSubject: 'Re: テスト件名',
      });

      mockSpeechReturn = { ...mockSpeechReturn, transcript: 'テスト' };
      const user = userEvent.setup();
      renderPanel();

      await user.click(screen.getByRole('button', { name: /清書/ }));

      await waitFor(() => {
        expect(screen.getByDisplayValue(/拝啓/)).toBeInTheDocument();
      });
    });

    it('清書されたメール本文を手動編集できる', async () => {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書本文',
        composedSubject: 'Re: テスト件名',
      });

      mockSpeechReturn = { ...mockSpeechReturn, transcript: 'テスト' };
      const user = userEvent.setup();
      renderPanel();

      await user.click(screen.getByRole('button', { name: /清書/ }));

      await waitFor(() => {
        expect(screen.getByDisplayValue('清書本文')).toBeInTheDocument();
      });

      const composedTextarea = screen.getByDisplayValue('清書本文') as HTMLTextAreaElement;
      await user.clear(composedTextarea);
      await user.type(composedTextarea, '手動編集した本文');

      expect(composedTextarea.value).toBe('手動編集した本文');
    });

    it('再清書ボタンで再度API呼び出しが行われる', async () => {
      mockComposeReply
        .mockResolvedValueOnce({
          composedBody: '清書本文1',
          composedSubject: 'Re: テスト件名',
        })
        .mockResolvedValueOnce({
          composedBody: '清書本文2',
          composedSubject: 'Re: テスト件名',
        });

      mockSpeechReturn = { ...mockSpeechReturn, transcript: 'テスト' };
      const user = userEvent.setup();
      renderPanel();

      await user.click(screen.getByRole('button', { name: /清書/ }));

      await waitFor(() => {
        expect(screen.getByDisplayValue('清書本文1')).toBeInTheDocument();
      });

      const recomposeBtn = screen.getByRole('button', { name: /再清書/ });
      await user.click(recomposeBtn);

      await waitFor(() => {
        expect(screen.getByDisplayValue('清書本文2')).toBeInTheDocument();
      });

      expect(mockComposeReply).toHaveBeenCalledTimes(2);
    });
  });

  describe('確認・送信ボタンの分離表示 (Requirement 4.1, 4.2, 4.3, 4.5)', () => {
    async function renderComposedState() {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });

      mockSpeechReturn = { ...mockSpeechReturn, transcript: 'テスト' };
      const user = userEvent.setup();
      renderPanel();

      await user.click(screen.getByRole('button', { name: /清書/ }));

      await waitFor(() => {
        expect(screen.getByDisplayValue('清書されたメール本文')).toBeInTheDocument();
      });

      return user;
    }

    it('清書完了後に「確認」と「送信」ボタンが両方表示される', async () => {
      await renderComposedState();

      expect(screen.getByRole('button', { name: /確認/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /送信/ })).toBeInTheDocument();
    });

    it('「送信」ボタンが常に有効状態である', async () => {
      await renderComposedState();

      const sendBtn = screen.getByRole('button', { name: /送信/ });
      expect(sendBtn).not.toBeDisabled();
    });

    it('「確認」ボタンで送信プレビュー（To, Subject, Body）が表示される', async () => {
      const user = await renderComposedState();

      const confirmBtn = screen.getByRole('button', { name: /確認/ });
      await user.click(confirmBtn);

      // 宛先
      expect(screen.getByText(/sender@example.com/)).toBeInTheDocument();
      // 件名
      expect(screen.getByText(/Re: テスト件名/)).toBeInTheDocument();
      // 本文
      expect(screen.getByText('清書されたメール本文')).toBeInTheDocument();
    });

    it('送信プレビュー表示中に「戻る」ボタンで編集画面に戻る', async () => {
      const user = await renderComposedState();

      // プレビュー表示
      await user.click(screen.getByRole('button', { name: /確認/ }));
      expect(screen.getByText(/sender@example.com/)).toBeInTheDocument();

      // 戻る
      const backBtn = screen.getByRole('button', { name: /戻る/ });
      await user.click(backBtn);

      // 編集画面に戻る（テキストエリアが表示される）
      expect(screen.getByDisplayValue('清書されたメール本文')).toBeInTheDocument();
    });
  });

  describe('メール送信と完了フェーズ (Requirement 3.3, 3.5, 4.6)', () => {
    async function renderAndSend() {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書本文',
        composedSubject: 'Re: テスト件名',
      });
      mockSendReply.mockResolvedValueOnce({
        success: true,
        googleMessageId: 'msg-456',
      });

      mockSpeechReturn = { ...mockSpeechReturn, transcript: 'テスト' };
      const user = userEvent.setup();
      renderPanel();

      // 清書
      await user.click(screen.getByRole('button', { name: /清書/ }));
      await waitFor(() => {
        expect(screen.getByDisplayValue('清書本文')).toBeInTheDocument();
      });

      return user;
    }

    it('送信中はスピナーとテキストが表示される', async () => {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書本文',
        composedSubject: 'Re: テスト件名',
      });
      let resolveSend: ((value: unknown) => void) | undefined;
      mockSendReply.mockReturnValueOnce(
        new Promise((resolve) => {
          resolveSend = resolve;
        })
      );

      mockSpeechReturn = { ...mockSpeechReturn, transcript: 'テスト' };
      const user = userEvent.setup();
      renderPanel();

      await user.click(screen.getByRole('button', { name: /清書/ }));
      await waitFor(() => {
        expect(screen.getByDisplayValue('清書本文')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /送信/ }));

      expect(screen.getByText(/送信中/)).toBeInTheDocument();
      expect(document.querySelector('.processing-spinner')).toBeInTheDocument();

      // Resolve to clean up
      resolveSend?.({ success: true, googleMessageId: 'msg-456' });
    });

    it('送信ボタン押下でsendReply APIが呼ばれる', async () => {
      const user = await renderAndSend();

      const sendBtn = screen.getByRole('button', { name: /送信/ });
      await user.click(sendBtn);

      expect(mockSendReply).toHaveBeenCalledWith('test-token', 'email-123', {
        composedBody: '清書本文',
        composedSubject: 'Re: テスト件名',
      });
    });

    it('送信完了後にフィードバックが表示される', async () => {
      const user = await renderAndSend();

      await user.click(screen.getByRole('button', { name: /送信/ }));

      await waitFor(() => {
        expect(screen.getByText(/送信完了|送信しました/)).toBeInTheDocument();
      });
    });

    it('送信失敗時にエラーメッセージと再送信ボタンが表示される', async () => {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書本文',
        composedSubject: 'Re: テスト件名',
      });
      mockSendReply.mockRejectedValueOnce(new Error('送信に失敗しました'));

      mockSpeechReturn = { ...mockSpeechReturn, transcript: 'テスト' };
      const user = userEvent.setup();
      renderPanel();

      await user.click(screen.getByRole('button', { name: /清書/ }));
      await waitFor(() => {
        expect(screen.getByDisplayValue('清書本文')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /送信/ }));

      await waitFor(() => {
        expect(screen.getByText(/送信に失敗/)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /再送信|再試行/ })).toBeInTheDocument();
      });
    });
  });

  describe('清書失敗時のエラーハンドリング (Requirement 5.3)', () => {
    it('清書失敗時にエラー表示されテキストエリアが編集可能な状態を維持する', async () => {
      mockComposeReply.mockRejectedValueOnce(new Error('清書に失敗しました'));

      mockSpeechReturn = { ...mockSpeechReturn, transcript: 'テスト入力' };
      const user = userEvent.setup();
      renderPanel();

      await user.click(screen.getByRole('button', { name: /清書/ }));

      await waitFor(() => {
        expect(screen.getByText(/清書に失敗/)).toBeInTheDocument();
      });

      // テキストエリアが編集可能
      const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
      expect(textarea).not.toBeDisabled();
      expect(textarea.value).toBe('テスト入力');
    });
  });

  describe('音声認識エラー時の再試行 (Requirement 5.2)', () => {
    it('音声認識エラー時にエラーメッセージと再試行ボタンが表示される', () => {
      mockSpeechReturn = {
        ...mockSpeechReturn,
        error: '音声が検出されませんでした。もう一度お試しください。',
      };
      renderPanel();

      expect(screen.getByText(/音声が検出されませんでした/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /再試行|もう一度/ })).toBeInTheDocument();
    });
  });
});
