/**
 * @vitest-environment jsdom
 */

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as emailApi from '../api/emails';
import { EmailList } from '../components/EmailList';

// Mock the email API
vi.mock('../api/emails', () => ({
  fetchEmails: vi.fn(),
}));

// Mock AuthContext
vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(() => ({
    idToken: 'mock-token',
    user: { uid: 'test-uid', email: 'test@example.com' },
    isLoading: false,
  })),
}));

const mockEmails = [
  {
    id: '1',
    senderName: '田中部長',
    senderEmail: 'tanaka@example.com',
    subject: '重要：プロジェクト進捗報告',
    convertedBody: '変換後テキスト1',
    audioUrl: 'https://example.com/audio1.mp3',
    isProcessed: true,
    receivedAt: '2024-01-15T10:30:00+00:00',
    repliedAt: null,
    replyBody: null,
    replySubject: null,
  },
  {
    id: '2',
    senderName: '佐藤課長',
    senderEmail: 'sato@example.com',
    subject: '週報提出のお願い',
    convertedBody: null,
    audioUrl: null,
    isProcessed: false,
    receivedAt: '2024-01-14T09:00:00+00:00',
    repliedAt: null,
    replyBody: null,
    replySubject: null,
  },
];

const mockEmailsWithReplied = [
  {
    id: '1',
    senderName: '田中部長',
    senderEmail: 'tanaka@example.com',
    subject: '重要：プロジェクト進捗報告',
    convertedBody: '変換後テキスト1',
    audioUrl: 'https://example.com/audio1.mp3',
    isProcessed: true,
    receivedAt: '2024-01-15T10:30:00+00:00',
    repliedAt: null,
    replyBody: null,
    replySubject: null,
  },
  {
    id: '2',
    senderName: '佐藤課長',
    senderEmail: 'sato@example.com',
    subject: '週報提出のお願い',
    convertedBody: '変換後テキスト2',
    audioUrl: 'https://example.com/audio2.mp3',
    isProcessed: true,
    receivedAt: '2024-01-14T09:00:00+00:00',
    repliedAt: '2024-01-15T12:00:00+00:00',
    replyBody: '返信本文2',
    replySubject: 'Re: 週報提出のお願い',
  },
  {
    id: '3',
    senderName: '鈴木係長',
    senderEmail: 'suzuki@example.com',
    subject: '会議室予約の件',
    convertedBody: '変換後テキスト3',
    audioUrl: 'https://example.com/audio3.mp3',
    isProcessed: true,
    receivedAt: '2024-01-13T08:00:00+00:00',
    repliedAt: '2024-01-14T10:00:00+00:00',
    replyBody: '返信本文3',
    replySubject: 'Re: 会議室予約の件',
  },
];

describe('EmailList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('メール一覧表示 (Requirement 4.3, 4.4)', () => {
    it('should display email list with sender name, subject, and converted text', async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmails,
        total: 2,
      });

      render(<EmailList />);

      await waitFor(() => {
        expect(screen.getByText('田中部長')).toBeInTheDocument();
        expect(screen.getByText('重要：プロジェクト進捗報告')).toBeInTheDocument();
      });
    });

    it('should display emails in card format', async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmails,
        total: 2,
      });

      render(<EmailList />);

      await waitFor(() => {
        // Each email should be in a card
        const cards = screen.getAllByRole('article');
        expect(cards).toHaveLength(2);
      });
    });

    it('should show loading state while fetching', async () => {
      vi.mocked(emailApi.fetchEmails).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      render(<EmailList />);

      expect(screen.getByText('読み込み中...')).toBeInTheDocument();
    });
  });

  describe('処理中メールのローディング表示 (Requirement 4.5)', () => {
    it('should show loading indicator for unprocessed emails when expanded', async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmails,
        total: 2,
      });

      render(<EmailList />);

      await waitFor(() => {
        // Find the card for佐藤課長 (unprocessed)
        const unprocessedCard = screen.getByText('佐藤課長').closest('article');
        expect(unprocessedCard).toBeInTheDocument();
      });

      // Click to expand the unprocessed email card
      const unprocessedCard = screen.getByText('佐藤課長').closest('article');
      const header = unprocessedCard?.querySelector('.email-card-header');
      if (header) {
        fireEvent.click(header);
      }

      await waitFor(() => {
        if (unprocessedCard) {
          expect(within(unprocessedCard).getByText('処理中...')).toBeInTheDocument();
        }
      });
    });
  });

  describe('トグル形式', () => {
    it('should expand email card on header click', async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmails,
        total: 2,
      });

      render(<EmailList />);

      await waitFor(() => {
        expect(screen.getByText('田中部長')).toBeInTheDocument();
      });

      // Initially, converted body should not be visible
      expect(screen.queryByText('変換後テキスト1')).not.toBeInTheDocument();

      // Click to expand the first email card
      const processedCard = screen.getByText('田中部長').closest('article');
      const header = processedCard?.querySelector('.email-card-header');
      if (header) {
        fireEvent.click(header);
      }

      // After expansion, converted body should be visible
      await waitFor(() => {
        expect(screen.getByText('変換後テキスト1')).toBeInTheDocument();
      });
    });

    it('should collapse email card when clicking header again', async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmails,
        total: 2,
      });

      render(<EmailList />);

      await waitFor(() => {
        expect(screen.getByText('田中部長')).toBeInTheDocument();
      });

      const processedCard = screen.getByText('田中部長').closest('article');
      const header = processedCard?.querySelector('.email-card-header');

      // Click to expand
      if (header) {
        fireEvent.click(header);
      }

      await waitFor(() => {
        expect(screen.getByText('変換後テキスト1')).toBeInTheDocument();
      });

      // Click again to collapse
      if (header) {
        fireEvent.click(header);
      }

      await waitFor(() => {
        expect(screen.queryByText('変換後テキスト1')).not.toBeInTheDocument();
      });
    });
  });

  describe('空リスト', () => {
    it('should display empty state when no emails', async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: [],
        total: 0,
      });

      render(<EmailList />);

      await waitFor(() => {
        expect(screen.getByText('メールがありません')).toBeInTheDocument();
      });
    });
  });

  describe('エラーハンドリング', () => {
    it('should display error message on fetch failure', async () => {
      vi.mocked(emailApi.fetchEmails).mockRejectedValue(new Error('Network error'));

      render(<EmailList />);

      await waitFor(() => {
        expect(screen.getByText(/エラー/)).toBeInTheDocument();
      });
    });
  });

  describe('タブ切り替え（未返信/返信済み）', () => {
    it('タブが表示され、デフォルトで未返信タブが選択される', async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmailsWithReplied,
        total: 3,
      });

      render(<EmailList />);

      await waitFor(() => {
        const unrepliedTab = screen.getByRole('tab', { name: /未返信/ });
        const repliedTab = screen.getByRole('tab', { name: /返信済み/ });
        expect(unrepliedTab).toBeInTheDocument();
        expect(repliedTab).toBeInTheDocument();
        expect(unrepliedTab).toHaveAttribute('aria-selected', 'true');
        expect(repliedTab).toHaveAttribute('aria-selected', 'false');
      });
    });

    it('未返信タブ選択時は未返信メールのみ表示される', async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmailsWithReplied,
        total: 3,
      });

      render(<EmailList />);

      await waitFor(() => {
        expect(screen.getByText('田中部長')).toBeInTheDocument();
      });

      // 未返信メールが表示される
      expect(screen.getByText('田中部長')).toBeInTheDocument();
      // 返信済みメールは表示されない
      expect(screen.queryByText('佐藤課長')).not.toBeInTheDocument();
      expect(screen.queryByText('鈴木係長')).not.toBeInTheDocument();
    });

    it('返信済みタブをクリックすると返信済みメールのみ表示される', async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmailsWithReplied,
        total: 3,
      });

      render(<EmailList />);

      await waitFor(() => {
        expect(screen.getByText('田中部長')).toBeInTheDocument();
      });

      // 返信済みタブをクリック
      fireEvent.click(screen.getByRole('tab', { name: /返信済み/ }));

      // 返信済みメールが表示される
      expect(screen.getByText('佐藤課長')).toBeInTheDocument();
      expect(screen.getByText('鈴木係長')).toBeInTheDocument();
      // 未返信メールは表示されない
      expect(screen.queryByText('田中部長')).not.toBeInTheDocument();
    });

    it('タブに件数が表示される', async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmailsWithReplied,
        total: 3,
      });

      render(<EmailList />);

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /未返信.*1/ })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /返信済み.*2/ })).toBeInTheDocument();
      });
    });

    it('全て未返信の場合でも両方のタブが表示される', async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmails,
        total: 2,
      });

      render(<EmailList />);

      await waitFor(() => {
        expect(screen.getByText('田中部長')).toBeInTheDocument();
      });

      expect(screen.getByRole('tab', { name: /未返信/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /返信済み/ })).toBeInTheDocument();
    });

    it('全て返信済みの場合「すべて返信済みです」メッセージが未返信タブに表示される', async () => {
      const allReplied = mockEmailsWithReplied.filter((e) => e.repliedAt !== null);
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: allReplied,
        total: allReplied.length,
      });

      render(<EmailList />);

      await waitFor(() => {
        expect(screen.getByText('すべて返信済みです')).toBeInTheDocument();
      });
    });
  });
});
