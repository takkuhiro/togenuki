/**
 * @vitest-environment jsdom
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
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

// Mock VoiceReplyPanel
vi.mock('../components/VoiceReplyPanel', () => ({
  VoiceReplyPanel: ({
    emailId,
    senderEmail,
    senderName,
    subject,
  }: {
    emailId: string;
    senderEmail: string;
    senderName: string | null;
    subject: string | null;
  }) => (
    <div
      data-testid="voice-reply-panel"
      data-email-id={emailId}
      data-sender-email={senderEmail}
      data-sender-name={senderName || ''}
      data-subject={subject || ''}
    >
      VoiceReplyPanel
    </div>
  ),
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
    ...overrides,
  };
}

// --- Tests ---

describe('EmailCard - 音声入力ボタン統合', () => {
  const onToggle = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('処理済みメールカード展開時 (Requirement 1.1)', () => {
    it('処理済みメールカード展開時にAudioPlayerの隣に音声入力ボタンが表示される', () => {
      const email = createEmail({ isProcessed: true });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      // AudioPlayerが表示される
      expect(screen.getByTestId('audio-player')).toBeInTheDocument();
      // 音声入力ボタンが表示される
      expect(screen.getByRole('button', { name: /音声入力|返信/ })).toBeInTheDocument();
    });

    it('音声入力ボタンとAudioPlayerが同じアクションエリア内にある', () => {
      const email = createEmail({ isProcessed: true });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      const actionsArea = screen.getByTestId('audio-player').closest('.email-card-actions');
      expect(actionsArea).toBeInTheDocument();

      // 音声入力ボタンもアクションエリア内
      const voiceBtn = screen.getByRole('button', { name: /音声入力|返信/ });
      expect(actionsArea?.contains(voiceBtn)).toBe(true);
    });
  });

  describe('未処理メールカード (Requirement 1.1)', () => {
    it('未処理メールカードには音声入力ボタンが表示されない', () => {
      const email = createEmail({ isProcessed: false });
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      expect(screen.queryByRole('button', { name: /音声入力|返信/ })).not.toBeInTheDocument();
    });
  });

  describe('カード折りたたみ時', () => {
    it('カード折りたたみ時には音声入力ボタンが表示されない', () => {
      const email = createEmail({ isProcessed: true });
      render(<EmailCard email={email} isExpanded={false} onToggle={onToggle} />);

      expect(screen.queryByRole('button', { name: /音声入力|返信/ })).not.toBeInTheDocument();
    });
  });

  describe('VoiceReplyPanel展開 (Requirement 1.2)', () => {
    it('音声入力ボタン押下でVoiceReplyPanelが展開表示される', async () => {
      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      // 初期状態ではVoiceReplyPanelは非表示
      expect(screen.queryByTestId('voice-reply-panel')).not.toBeInTheDocument();

      // 音声入力ボタン押下
      const voiceBtn = screen.getByRole('button', { name: /音声入力|返信/ });
      await user.click(voiceBtn);

      // VoiceReplyPanelが表示される
      expect(screen.getByTestId('voice-reply-panel')).toBeInTheDocument();
    });

    it('VoiceReplyPanelにメール情報がpropsとして渡される', async () => {
      const email = createEmail({
        id: 'email-456',
        senderEmail: 'test@example.com',
        senderName: '山田花子',
        subject: '重要な件名',
      });
      const user = userEvent.setup();
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      // 音声入力ボタン押下
      const voiceBtn = screen.getByRole('button', { name: /音声入力|返信/ });
      await user.click(voiceBtn);

      const panel = screen.getByTestId('voice-reply-panel');
      expect(panel).toHaveAttribute('data-email-id', 'email-456');
      expect(panel).toHaveAttribute('data-sender-email', 'test@example.com');
      expect(panel).toHaveAttribute('data-sender-name', '山田花子');
      expect(panel).toHaveAttribute('data-subject', '重要な件名');
    });

    it('音声入力ボタンを再度押下するとVoiceReplyPanelが閉じる', async () => {
      const email = createEmail({ isProcessed: true });
      const user = userEvent.setup();
      render(<EmailCard email={email} isExpanded={true} onToggle={onToggle} />);

      const voiceBtn = screen.getByRole('button', { name: /音声入力|返信/ });

      // 開く
      await user.click(voiceBtn);
      expect(screen.getByTestId('voice-reply-panel')).toBeInTheDocument();

      // 閉じる
      await user.click(screen.getByRole('button', { name: /音声入力|返信|閉じる/ }));
      expect(screen.queryByTestId('voice-reply-panel')).not.toBeInTheDocument();
    });
  });
});
