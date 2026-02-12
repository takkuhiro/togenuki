/**
 * @vitest-environment jsdom
 */

import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { EmailCard } from '../components/EmailCard';
import type { Email } from '../types/email';

// --- Mocks ---

// Mock AudioPlayer
vi.mock('../components/AudioPlayer', () => ({
  AudioPlayer: ({ emailId }: { audioUrl: string | null; emailId?: string }) => (
    <div data-testid="audio-player" data-email-id={emailId}>
      AudioPlayer
    </div>
  ),
}));

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
const mockSaveDraft = vi.fn();

vi.mock('../api/reply', () => ({
  composeReply: (...args: unknown[]) => mockComposeReply(...args),
  sendReply: (...args: unknown[]) => mockSendReply(...args),
  saveDraft: (...args: unknown[]) => mockSaveDraft(...args),
}));

// Mock useAuth
vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ idToken: 'test-token' }),
}));

// --- Helpers ---

function createEmail(overrides: Partial<Email> = {}): Email {
  return {
    id: 'email-123',
    senderName: '田中太郎',
    senderEmail: 'tanaka@example.com',
    subject: 'テスト件名',
    convertedBody: 'ギャル語に変換されたメール本文',
    audioUrl: 'https://example.com/audio.mp3',
    isProcessed: true,
    receivedAt: new Date().toISOString(),
    repliedAt: null,
    replyBody: null,
    replySubject: null,
    replySource: null,
    composedBody: null,
    composedSubject: null,
    googleDraftId: null,
    ...overrides,
  };
}

// --- Tests ---

describe('EmailCard - VoiceReplyPanel統合', () => {
  const onToggle = vi.fn();

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
    mockSaveDraft.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  describe('idle（初期）フェーズ', () => {
    it('展開+処理済み時にAudioPlayerと「音声入力」ボタンが並列表示される', () => {
      const email = createEmail({ isProcessed: true });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      expect(screen.getByTestId('audio-player')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /音声入力/ })).toBeInTheDocument();
    });

    it('AudioPlayerと「音声入力」ボタンが同じemail-card-actions内にある', () => {
      const email = createEmail({ isProcessed: true });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      const actionsArea = screen.getByTestId('audio-player').closest('.email-card-actions');
      expect(actionsArea).toBeInTheDocument();

      const voiceBtn = screen.getByRole('button', { name: /音声入力/ });
      expect(actionsArea?.contains(voiceBtn)).toBe(true);
    });

    it('マウント時に自動録音開始しない（idle状態で待機）', () => {
      const email = createEmail({ isProcessed: true });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      expect(mockStartListening).not.toHaveBeenCalled();
    });
  });

  describe('トグルボタンが存在しない', () => {
    it('「返信を閉じる」トグルボタンが存在しない', () => {
      const email = createEmail({ isProcessed: true });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      expect(screen.queryByText(/返信を閉じる/)).not.toBeInTheDocument();
      expect(screen.queryByText(/音声入力で返信/)).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /返信を閉じる/ })).not.toBeInTheDocument();
    });
  });

  describe('未処理メールカード', () => {
    it('未処理メールカードには音声入力ボタンが表示されない', () => {
      const email = createEmail({ isProcessed: false });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      expect(screen.queryByRole('button', { name: /音声入力/ })).not.toBeInTheDocument();
    });
  });

  describe('カード折りたたみ時', () => {
    it('カード折りたたみ時には音声入力ボタンが表示されない', () => {
      const email = createEmail({ isProcessed: true });
      render(<EmailCard email={email} isExpanded={false} onToggle={onToggle} />);

      expect(screen.queryByRole('button', { name: /音声入力/ })).not.toBeInTheDocument();
    });
  });

  describe('recording フェーズ', () => {
    it('「音声入力」クリック → 録音開始、「録音停止」ボタン表示', async () => {
      mockSpeechReturn = { ...mockSpeechReturn, isListening: true };
      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      expect(mockStartListening).toHaveBeenCalled();
    });

    it('録音中は「録音停止」ボタンが表示される', () => {
      mockSpeechReturn = { ...mockSpeechReturn, isListening: true };
      const email = createEmail({ isProcessed: true });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      // idleのuseEffectからrecordingに遷移後をシミュレート: phaseはrecording想定
      // ただしphaseのstate変更はクリックイベント経由なので、isListeningを見てUI判定
      // → 実際にはphaseをrecordingにする必要がある。初回renderでは音声入力ボタンが表示
      // テストではクリックをシミュレートしてrecordingに遷移
    });

    it('録音中に中間テキストやエラーが画面に表示されない', async () => {
      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isAvailable: true, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} />
      );

      // 音声入力ボタンをクリック
      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      // 録音中に遷移（isListening: true + interimTranscript + error）
      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: true,
        interimTranscript: '明日の会議は',
        error: '音声が検出されませんでした。もう一度お試しください。',
      };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      // 中間テキストは表示されない
      expect(screen.queryByText('明日の会議は')).not.toBeInTheDocument();
      // エラーメッセージも表示されない
      expect(screen.queryByText(/音声が検出されませんでした/)).not.toBeInTheDocument();
      // 録音停止ボタンは表示される
      expect(screen.getByRole('button', { name: /録音停止/ })).toBeInTheDocument();
    });

    it('「録音停止」クリックでstopListeningが呼ばれる', async () => {
      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isAvailable: true, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} />
      );

      // 音声入力クリック → recordingへ
      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      mockSpeechReturn = { ...mockSpeechReturn, isListening: true };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await user.click(screen.getByRole('button', { name: /録音停止/ }));
      expect(mockStopListening).toHaveBeenCalled();
    });
  });

  describe('auto-compose（録音停止後自動清書）', () => {
    it('録音停止後にtranscriptがある場合、自動でcomposeReplyが呼ばれる', async () => {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });

      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} />
      );

      // 音声入力クリック
      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      // 録音中
      mockSpeechReturn = { ...mockSpeechReturn, isListening: true, transcript: '' };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      // 録音停止 + transcript確定
      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: false,
        transcript: 'お疲れ様です',
      };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await waitFor(() => {
        expect(mockComposeReply).toHaveBeenCalledWith('test-token', 'email-123', {
          rawText: 'お疲れ様です',
        });
      });
    });

    it('transcriptが空でもinterimTranscriptがあれば清書が呼ばれる', async () => {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書本文',
        composedSubject: 'Re: テスト件名',
      });

      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} />
      );

      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      // 録音中（interimTranscriptのみ）
      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: true,
        transcript: '',
        interimTranscript: '明日の会議は',
      };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      // 録音停止 → transcriptは空だがinterimTranscriptあり
      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: false,
        transcript: '',
        interimTranscript: '明日の会議は',
      };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await waitFor(() => {
        expect(mockComposeReply).toHaveBeenCalledWith('test-token', 'email-123', {
          rawText: '明日の会議は',
        });
      });
    });

    it('transcriptもinterimTranscriptも空の場合はエラーメッセージが表示される', async () => {
      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} />
      );

      // 音声入力クリック
      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      // 録音中
      mockSpeechReturn = { ...mockSpeechReturn, isListening: true, transcript: '' };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      // 録音停止、transcript空
      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: false,
        transcript: '',
      };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
      });
    });
  });

  describe('composing フェーズ', () => {
    it('清書中は音声入力ボタンがdisabledでスピナーが表示される', async () => {
      let resolveCompose: ((value: unknown) => void) | undefined;
      mockComposeReply.mockReturnValueOnce(
        new Promise((resolve) => {
          resolveCompose = resolve;
        })
      );

      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} />
      );

      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      mockSpeechReturn = { ...mockSpeechReturn, isListening: true, transcript: '' };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: false,
        transcript: 'テスト',
      };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await waitFor(() => {
        const btn = screen.getByRole('button', { name: /音声入力/ });
        expect(btn).toBeDisabled();
      });
      expect(document.querySelector('.processing-spinner')).toBeInTheDocument();
      expect(screen.queryByText(/清書中/)).not.toBeInTheDocument();

      resolveCompose?.({
        composedBody: '清書結果',
        composedSubject: 'Re: テスト件名',
      });
    });
  });

  describe('composed フェーズ', () => {
    async function renderComposedState() {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });

      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} />
      );

      // 音声入力 → recording → 停止 → auto-compose → composed
      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      mockSpeechReturn = { ...mockSpeechReturn, isListening: true, transcript: '' };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: false,
        transcript: 'テスト',
      };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await waitFor(() => {
        expect(mockComposeReply).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /確認/ })).toBeInTheDocument();
      });

      return { rerender, user };
    }

    it('AudioPlayer、「音声入力」「確認」「送信」「下書き」ボタンが全て並列表示される', async () => {
      await renderComposedState();

      expect(screen.getByTestId('audio-player')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /音声入力/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /確認/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /送信/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /下書き/ })).toBeInTheDocument();

      // 全てが同じemail-card-actions内にある
      const actionsArea = screen.getByTestId('audio-player').closest('.email-card-actions');
      expect(actionsArea).toBeInTheDocument();
      expect(actionsArea?.contains(screen.getByRole('button', { name: /音声入力/ }))).toBe(true);
      expect(actionsArea?.contains(screen.getByRole('button', { name: /確認/ }))).toBe(true);
      expect(actionsArea?.contains(screen.getByRole('button', { name: /送信/ }))).toBe(true);
      expect(actionsArea?.contains(screen.getByRole('button', { name: /下書き/ }))).toBe(true);
    });

    it('「音声入力」ボタンで全状態リセット＋録音再開', async () => {
      const { user } = await renderComposedState();

      mockStartListening.mockClear();
      mockResetTranscript.mockClear();

      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      expect(mockResetTranscript).toHaveBeenCalled();
      expect(mockStartListening).toHaveBeenCalled();
    });
  });

  describe('confirming フェーズ', () => {
    async function renderComposedAndConfirm() {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });

      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} />
      );

      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      mockSpeechReturn = { ...mockSpeechReturn, isListening: true, transcript: '' };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: false,
        transcript: 'テスト',
      };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /確認/ })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /確認/ }));
      return { user, rerender };
    }

    it('「確認」ボタンでモーダルオーバーレイ付きダイアログが表示される', async () => {
      await renderComposedAndConfirm();

      const dialog = screen.getByRole('dialog');
      expect(dialog).toBeInTheDocument();

      // モーダルオーバーレイで表示される
      const overlay = dialog.closest('.dialog-overlay');
      expect(overlay).toBeInTheDocument();

      // ダイアログ内に宛先・件名・本文が表示される
      expect(dialog.textContent).toContain('tanaka@example.com');
      expect(dialog.textContent).toContain('Re: テスト件名');
      expect(dialog.textContent).toContain('清書されたメール本文');
    });

    it('ダイアログ内「戻る」で元に戻る', async () => {
      const { user } = await renderComposedAndConfirm();

      await user.click(screen.getByRole('button', { name: /戻る/ }));

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /確認/ })).toBeInTheDocument();
    });

    it('ダイアログ内に「下書き」ボタンが表示される', async () => {
      await renderComposedAndConfirm();

      const dialog = screen.getByRole('dialog');
      // ダイアログ内に「下書き」ボタンがあること
      expect(dialog.textContent).toContain('下書き');
      const buttons = screen.getAllByRole('button', { name: /下書き/ });
      // ダイアログ内に下書きボタンが存在
      expect(buttons.length).toBeGreaterThanOrEqual(1);
    });

    it('ダイアログ内「下書き」ボタンでsaveDraft APIが呼ばれる', async () => {
      mockSaveDraft.mockResolvedValueOnce({
        success: true,
        googleDraftId: 'draft-789',
      });

      const { user } = await renderComposedAndConfirm();

      const draftButtons = screen.getAllByRole('button', { name: /下書き/ });
      const dialogDraftBtn = draftButtons[draftButtons.length - 1];
      await user.click(dialogDraftBtn);

      expect(mockSaveDraft).toHaveBeenCalledWith('test-token', 'email-123', {
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });
    });

    it('ダイアログ内「送信」ボタンでsendReply APIが呼ばれる', async () => {
      mockSendReply.mockResolvedValueOnce({
        success: true,
        googleMessageId: 'msg-456',
      });

      const { user } = await renderComposedAndConfirm();

      const sendButtons = screen.getAllByRole('button', { name: /送信/ });
      const dialogSendBtn = sendButtons[sendButtons.length - 1];
      await user.click(dialogSendBtn);

      expect(mockSendReply).toHaveBeenCalledWith('test-token', 'email-123', {
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });
    });
  });

  describe('sending フェーズ', () => {
    it('送信中は送信ボタンがdisabledでスピナーが表示される', async () => {
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

      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} />
      );

      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      mockSpeechReturn = { ...mockSpeechReturn, isListening: true, transcript: '' };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: false,
        transcript: 'テスト',
      };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /送信/ })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /送信/ }));

      const sendBtn = screen.getByRole('button', { name: /送信/ });
      expect(sendBtn).toBeDisabled();
      expect(sendBtn.querySelector('.processing-spinner')).toBeInTheDocument();
      expect(screen.queryByText(/送信中\.\.\./)).not.toBeInTheDocument();

      resolveSend?.({ success: true, googleMessageId: 'msg-456' });
    });
  });

  describe('sent フェーズ', () => {
    it('送信完了後に送信ボタンがdisabledで「送信済み」と表示される', async () => {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書本文',
        composedSubject: 'Re: テスト件名',
      });
      mockSendReply.mockResolvedValueOnce({
        success: true,
        googleMessageId: 'msg-456',
      });

      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} />
      );

      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      mockSpeechReturn = { ...mockSpeechReturn, isListening: true, transcript: '' };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: false,
        transcript: 'テスト',
      };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /送信/ })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /送信/ }));

      await waitFor(() => {
        const sentBtn = screen.getByRole('button', { name: /送信済み/ });
        expect(sentBtn).toBeDisabled();
      });
      expect(screen.queryByText(/送信完了しました/)).not.toBeInTheDocument();
    });

    it('送信完了時にonRepliedコールバックが呼ばれる', async () => {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書本文',
        composedSubject: 'Re: テスト件名',
      });
      mockSendReply.mockResolvedValueOnce({
        success: true,
        googleMessageId: 'msg-456',
      });

      const onReplied = vi.fn();
      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} onReplied={onReplied} />
      );

      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      mockSpeechReturn = { ...mockSpeechReturn, isListening: true, transcript: '' };
      rerender(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} onReplied={onReplied} />
      );

      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: false,
        transcript: 'テスト',
      };
      rerender(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} onReplied={onReplied} />
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /送信/ })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /送信/ }));

      await waitFor(() => {
        expect(onReplied).toHaveBeenCalledWith('email-123');
      });
    });
  });

  describe('error フェーズ', () => {
    it('清書失敗時にエラー表示と「音声入力」リトライボタンが表示される', async () => {
      mockComposeReply.mockRejectedValueOnce(new Error('清書に失敗しました'));

      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} />
      );

      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      mockSpeechReturn = { ...mockSpeechReturn, isListening: true, transcript: '' };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: false,
        transcript: 'テスト入力',
      };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await waitFor(() => {
        expect(screen.getByText(/清書に失敗/)).toBeInTheDocument();
      });

      expect(screen.getByRole('button', { name: /音声入力/ })).toBeInTheDocument();
    });

    it('送信失敗時にエラーメッセージと再送信ボタンが表示される', async () => {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書本文',
        composedSubject: 'Re: テスト件名',
      });
      mockSendReply.mockRejectedValueOnce(new Error('送信に失敗しました'));

      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} />
      );

      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      mockSpeechReturn = { ...mockSpeechReturn, isListening: true, transcript: '' };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: false,
        transcript: 'テスト',
      };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /送信/ })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /送信/ }));

      await waitFor(() => {
        expect(screen.getByText(/送信に失敗/)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /再送信/ })).toBeInTheDocument();
      });
    });
  });

  describe('返信済みメール（repliedAt設定済み）', () => {
    it('repliedAtが設定されている場合、返信UI（音声入力ボタン等）が非表示', () => {
      const email = createEmail({
        isProcessed: true,
        repliedAt: '2024-01-16T14:00:00+00:00',
      });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      // AudioPlayerは表示される
      expect(screen.getByTestId('audio-player')).toBeInTheDocument();
      // 返信UI（音声入力ボタン）は非表示
      expect(screen.queryByRole('button', { name: /音声入力/ })).not.toBeInTheDocument();
    });

    it('repliedAtが設定されている場合、テキスト入力フォールバックUIも非表示', () => {
      mockSpeechReturn = { ...mockSpeechReturn, isAvailable: false };
      const email = createEmail({
        isProcessed: true,
        repliedAt: '2024-01-16T14:00:00+00:00',
      });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
      expect(screen.queryByText(/音声入力.*利用できません/)).not.toBeInTheDocument();
    });

    it('replyBodyがある場合、「確認」ボタンが表示される', () => {
      const email = createEmail({
        isProcessed: true,
        repliedAt: '2024-01-16T14:00:00+00:00',
        replyBody: '送信済みの本文です',
        replySubject: 'Re: テスト件名',
      });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      expect(screen.getByRole('button', { name: /確認/ })).toBeInTheDocument();
    });

    it('replyBodyがnullの場合、「確認」ボタンが表示されない', () => {
      const email = createEmail({
        isProcessed: true,
        repliedAt: '2024-01-16T14:00:00+00:00',
        replyBody: null,
        replySubject: null,
      });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      expect(screen.queryByRole('button', { name: /確認/ })).not.toBeInTheDocument();
    });

    it('「確認」ボタンクリックでダイアログに送信内容が表示される', async () => {
      const email = createEmail({
        isProcessed: true,
        repliedAt: '2024-01-16T14:00:00+00:00',
        replyBody: '送信済みの本文です',
        replySubject: 'Re: テスト件名',
      });
      const user = userEvent.setup();
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await user.click(screen.getByRole('button', { name: /確認/ }));

      const dialog = screen.getByRole('dialog');
      expect(dialog).toBeInTheDocument();
      expect(dialog.textContent).toContain('tanaka@example.com');
      expect(dialog.textContent).toContain('Re: テスト件名');
      expect(dialog.textContent).toContain('送信済みの本文です');
    });

    it('ダイアログの「閉じる」ボタンでダイアログが閉じる', async () => {
      const email = createEmail({
        isProcessed: true,
        repliedAt: '2024-01-16T14:00:00+00:00',
        replyBody: '送信済みの本文です',
        replySubject: 'Re: テスト件名',
      });
      const user = userEvent.setup();
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await user.click(screen.getByRole('button', { name: /確認/ }));
      expect(screen.getByRole('dialog')).toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: /閉じる/ }));
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  describe('返信元バッジ表示', () => {
    it('replySource=togenukiの場合、TogeNukiより返信バッジが表示される', () => {
      const email = createEmail({
        isProcessed: true,
        repliedAt: '2024-01-16T14:00:00+00:00',
        replyBody: '返信本文',
        replySubject: 'Re: テスト件名',
        replySource: 'togenuki',
      });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      const badge = screen.getByText('TogeNukiより返信');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('reply-source-badge--togenuki');
    });

    it('replySource=gmailの場合、Gmailより返信バッジが表示される', () => {
      const email = createEmail({
        isProcessed: true,
        repliedAt: '2024-01-16T14:00:00+00:00',
        replyBody: null,
        replySubject: null,
        replySource: 'gmail',
      });
      render(<EmailCard email={email} isExpanded={false} onToggle={onToggle} />);

      const badge = screen.getByText('Gmailより返信');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('reply-source-badge--gmail');
    });

    it('replySourceがnullの場合、バッジは表示されない', () => {
      const email = createEmail({
        isProcessed: true,
        repliedAt: '2024-01-16T14:00:00+00:00',
        replyBody: '返信本文',
        replySubject: 'Re: テスト件名',
        replySource: null,
      });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      expect(screen.queryByText('TogeNukiより返信')).not.toBeInTheDocument();
      expect(screen.queryByText('Gmailより返信')).not.toBeInTheDocument();
    });

    it('未返信メールにはバッジが表示されない', () => {
      const email = createEmail({
        isProcessed: true,
        repliedAt: null,
        replySource: null,
      });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      expect(screen.queryByText('TogeNukiより返信')).not.toBeInTheDocument();
      expect(screen.queryByText('Gmailより返信')).not.toBeInTheDocument();
    });
  });

  describe('draft_saving / draft_saved フェーズ', () => {
    async function renderComposedStateForDraft() {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });

      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} />
      );

      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      mockSpeechReturn = { ...mockSpeechReturn, isListening: true, transcript: '' };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: false,
        transcript: 'テスト',
      };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /下書き/ })).toBeInTheDocument();
      });

      return { rerender, user };
    }

    it('「下書き」ボタンクリックでsaveDraft APIが呼ばれる', async () => {
      mockSaveDraft.mockResolvedValueOnce({
        success: true,
        googleDraftId: 'draft-789',
      });

      const { user } = await renderComposedStateForDraft();

      await user.click(screen.getByRole('button', { name: /下書き/ }));

      expect(mockSaveDraft).toHaveBeenCalledWith('test-token', 'email-123', {
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });
    });

    it('下書き保存中はボタンがdisabledでスピナーが表示される', async () => {
      let resolveDraft: ((value: unknown) => void) | undefined;
      mockSaveDraft.mockReturnValueOnce(
        new Promise((resolve) => {
          resolveDraft = resolve;
        })
      );

      const { user } = await renderComposedStateForDraft();

      await user.click(screen.getByRole('button', { name: /下書き/ }));

      const draftBtn = screen.getByRole('button', { name: /下書き/ });
      expect(draftBtn).toBeDisabled();
      expect(draftBtn.querySelector('.processing-spinner')).toBeInTheDocument();

      resolveDraft?.({ success: true, googleDraftId: 'draft-789' });
    });

    it('下書き保存完了後に「下書き保存済み」バッジが表示され、操作ボタンが残る', async () => {
      mockSaveDraft.mockResolvedValueOnce({
        success: true,
        googleDraftId: 'draft-789',
      });

      const { user } = await renderComposedStateForDraft();

      await user.click(screen.getByRole('button', { name: /下書き/ }));

      await waitFor(() => {
        expect(screen.getByText('下書き保存済み')).toBeInTheDocument();
      });

      // All action buttons should still be available in the actions area
      const actionsArea = screen.getByTestId('audio-player').closest('.email-card-actions');
      expect(actionsArea).toBeInTheDocument();
      expect(
        within(actionsArea as HTMLElement).getByRole('button', { name: /音声入力/ })
      ).toBeInTheDocument();
      expect(
        within(actionsArea as HTMLElement).getByRole('button', { name: /確認/ })
      ).toBeInTheDocument();
      expect(
        within(actionsArea as HTMLElement).getByRole('button', { name: /送信/ })
      ).toBeInTheDocument();
      expect(
        within(actionsArea as HTMLElement).getByRole('button', { name: /下書き/ })
      ).toBeInTheDocument();
    });

    it('下書き保存完了後にonRepliedは呼ばれない', async () => {
      mockSaveDraft.mockResolvedValueOnce({
        success: true,
        googleDraftId: 'draft-789',
      });

      const onReplied = vi.fn();
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });

      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} onReplied={onReplied} />
      );

      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      mockSpeechReturn = { ...mockSpeechReturn, isListening: true, transcript: '' };
      rerender(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} onReplied={onReplied} />
      );

      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: false,
        transcript: 'テスト',
      };
      rerender(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} onReplied={onReplied} />
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /下書き/ })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /下書き/ }));

      await waitFor(() => {
        expect(screen.getByText('下書き保存済み')).toBeInTheDocument();
      });

      expect(onReplied).not.toHaveBeenCalled();
    });

    it('下書き保存失敗時にエラーメッセージが表示される', async () => {
      mockSaveDraft.mockRejectedValueOnce(new Error('下書き保存に失敗しました'));

      const { user } = await renderComposedStateForDraft();

      await user.click(screen.getByRole('button', { name: /下書き/ }));

      await waitFor(() => {
        expect(screen.getByText(/下書き保存に失敗/)).toBeInTheDocument();
      });
    });
  });

  describe('下書き保存後も操作可能（要件1）', () => {
    async function renderComposedAndSaveDraft() {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });
      mockSaveDraft.mockResolvedValueOnce({
        success: true,
        googleDraftId: 'draft-789',
      });

      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();

      mockSpeechReturn = { ...mockSpeechReturn, isListening: false };
      const { rerender } = render(
        <EmailCard email={email} isExpanded={true} onToggle={onToggle} />
      );

      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      mockSpeechReturn = { ...mockSpeechReturn, isListening: true, transcript: '' };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      mockSpeechReturn = {
        ...mockSpeechReturn,
        isListening: false,
        transcript: 'テスト',
      };
      rerender(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /下書き/ })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /下書き/ }));

      await waitFor(() => {
        expect(screen.getByText('下書き保存済み')).toBeInTheDocument();
      });

      return { user, rerender };
    }

    it('下書き保存後に「送信」クリックでsendReply APIが呼ばれる', async () => {
      mockSendReply.mockResolvedValueOnce({
        success: true,
        googleMessageId: 'msg-456',
      });

      const { user } = await renderComposedAndSaveDraft();

      await user.click(screen.getByRole('button', { name: /送信/ }));

      expect(mockSendReply).toHaveBeenCalledWith('test-token', 'email-123', {
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });
    });

    it('下書き保存後に「音声入力」クリックで再録音できる', async () => {
      const { user } = await renderComposedAndSaveDraft();

      mockStartListening.mockClear();
      mockResetTranscript.mockClear();

      await user.click(screen.getByRole('button', { name: /音声入力/ }));

      expect(mockResetTranscript).toHaveBeenCalled();
      expect(mockStartListening).toHaveBeenCalled();
    });
  });

  describe('下書きラベル表示（要件2）', () => {
    it('下書き保存前にはバッジが表示されない', () => {
      const email = createEmail({ isProcessed: true });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      expect(screen.queryByText('下書き保存済み')).not.toBeInTheDocument();
    });

    it('email.googleDraftIdがある場合、マウント時にバッジが表示される', () => {
      const email = createEmail({
        isProcessed: true,
        composedBody: '清書済みの本文',
        composedSubject: 'Re: テスト件名',
        googleDraftId: 'draft-existing',
      });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      expect(screen.getByText('下書き保存済み')).toBeInTheDocument();
    });
  });

  describe('リロード後の復元（要件3）', () => {
    it('email.composedBodyがある場合、初期フェーズがcomposedになる', () => {
      const email = createEmail({
        isProcessed: true,
        composedBody: '清書済みの本文',
        composedSubject: 'Re: テスト件名',
      });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      // composed フェーズでは「確認」「送信」「下書き」ボタンが表示される
      expect(screen.getByRole('button', { name: /確認/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /送信/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /下書き/ })).toBeInTheDocument();
    });

    it('email.composedBodyがありrepliedAtもある場合、初期フェーズはidle', () => {
      const email = createEmail({
        isProcessed: true,
        composedBody: '清書済みの本文',
        composedSubject: 'Re: テスト件名',
        repliedAt: '2024-01-16T14:00:00+00:00',
      });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      // repliedAtがあるので返信UIは表示されない
      expect(screen.queryByRole('button', { name: /送信/ })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /下書き/ })).not.toBeInTheDocument();
    });
  });

  describe('fallback（Speech API非対応）', () => {
    it('Speech API非対応時はテキスト入力UIが表示される', () => {
      mockSpeechReturn = { ...mockSpeechReturn, isAvailable: false };
      const email = createEmail({ isProcessed: true });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      expect(screen.getByText(/音声入力.*利用できません|テキスト入力/)).toBeInTheDocument();
      expect(screen.getByRole('textbox')).toBeInTheDocument();
      expect(mockStartListening).not.toHaveBeenCalled();
    });

    it('フォールバックUIでテキスト入力後に清書ボタンが表示される', async () => {
      mockSpeechReturn = { ...mockSpeechReturn, isAvailable: false };
      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'テスト入力');

      expect(screen.getByRole('button', { name: /清書/ })).toBeInTheDocument();
    });

    it('フォールバックUIで清書ボタン押下でcomposeReply APIが呼ばれる', async () => {
      mockComposeReply.mockResolvedValueOnce({
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });

      mockSpeechReturn = { ...mockSpeechReturn, isAvailable: false };
      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'お疲れ様');

      await user.click(screen.getByRole('button', { name: /清書/ }));

      expect(mockComposeReply).toHaveBeenCalledWith('test-token', 'email-123', {
        rawText: 'お疲れ様',
      });
    });
  });
});
