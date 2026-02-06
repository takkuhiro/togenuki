/**
 * @vitest-environment jsdom
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as contactApi from '../api/contacts';
import { ContactList } from '../components/ContactList';

// Mock the contacts API
vi.mock('../api/contacts', () => ({
  fetchContacts: vi.fn(),
  deleteContact: vi.fn(),
  retryLearning: vi.fn(),
}));

// Mock AuthContext
vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(() => ({
    idToken: 'mock-token',
    user: { uid: 'test-uid', email: 'test@example.com' },
    isLoading: false,
  })),
}));

const mockContacts = [
  {
    id: '1',
    contactEmail: 'tanaka@example.com',
    contactName: '田中部長',
    gmailQuery: 'from:tanaka@example.com',
    isLearningComplete: true,
    learningFailedAt: null,
    createdAt: '2024-01-15T10:30:00+00:00',
    status: 'learning_complete' as const,
  },
  {
    id: '2',
    contactEmail: 'sato@example.com',
    contactName: '佐藤課長',
    gmailQuery: null,
    isLearningComplete: false,
    learningFailedAt: null,
    createdAt: '2024-01-14T09:00:00+00:00',
    status: 'learning_started' as const,
  },
  {
    id: '3',
    contactEmail: 'suzuki@example.com',
    contactName: null,
    gmailQuery: null,
    isLearningComplete: false,
    learningFailedAt: '2024-01-13T12:00:00+00:00',
    createdAt: '2024-01-13T09:00:00+00:00',
    status: 'learning_failed' as const,
  },
];

describe('ContactList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('連絡先一覧表示 (Requirement 2.1, 2.2)', () => {
    it('should display contact list with email and name', async () => {
      vi.mocked(contactApi.fetchContacts).mockResolvedValue({
        contacts: mockContacts,
        total: 3,
      });

      render(<ContactList />);

      await waitFor(() => {
        expect(screen.getByText('田中部長')).toBeInTheDocument();
        expect(screen.getByText('tanaka@example.com')).toBeInTheDocument();
        expect(screen.getByText('佐藤課長')).toBeInTheDocument();
        expect(screen.getByText('sato@example.com')).toBeInTheDocument();
      });
    });

    it('should display email as name when contactName is null', async () => {
      vi.mocked(contactApi.fetchContacts).mockResolvedValue({
        contacts: mockContacts,
        total: 3,
      });

      render(<ContactList />);

      await waitFor(() => {
        // suzuki@example.com has no name, so email should be displayed
        expect(screen.getByText('suzuki@example.com')).toBeInTheDocument();
      });
    });
  });

  describe('学習状態表示 (Requirement 2.3, 2.4)', () => {
    it('should show "学習中" label for contacts with isLearningComplete=false', async () => {
      vi.mocked(contactApi.fetchContacts).mockResolvedValue({
        contacts: mockContacts,
        total: 3,
      });

      render(<ContactList />);

      await waitFor(() => {
        // 佐藤課長 is learning (isLearningComplete=false, learningFailedAt=null)
        const satoCard = screen.getByText('佐藤課長').closest('[data-testid="contact-card"]');
        expect(satoCard).toHaveTextContent('学習中');
      });
    });

    it('should show "学習完了" label for contacts with isLearningComplete=true', async () => {
      vi.mocked(contactApi.fetchContacts).mockResolvedValue({
        contacts: mockContacts,
        total: 3,
      });

      render(<ContactList />);

      await waitFor(() => {
        // 田中部長 has completed learning
        const tanakaCard = screen.getByText('田中部長').closest('[data-testid="contact-card"]');
        expect(tanakaCard).toHaveTextContent('学習完了');
      });
    });

    it('should show "学習失敗" label for contacts with learningFailedAt set', async () => {
      vi.mocked(contactApi.fetchContacts).mockResolvedValue({
        contacts: mockContacts,
        total: 3,
      });

      render(<ContactList />);

      await waitFor(() => {
        // suzuki has failed learning
        const suzukiCard = screen
          .getByText('suzuki@example.com')
          .closest('[data-testid="contact-card"]');
        expect(suzukiCard).toHaveTextContent('学習失敗');
      });
    });
  });

  describe('ローディング表示', () => {
    it('should show loading state while fetching', async () => {
      vi.mocked(contactApi.fetchContacts).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      render(<ContactList />);

      expect(screen.getByText('読み込み中...')).toBeInTheDocument();
    });
  });

  describe('空リスト', () => {
    it('should display empty state when no contacts', async () => {
      vi.mocked(contactApi.fetchContacts).mockResolvedValue({
        contacts: [],
        total: 0,
      });

      render(<ContactList />);

      await waitFor(() => {
        expect(screen.getByText('連絡先がありません')).toBeInTheDocument();
      });
    });
  });

  describe('エラーハンドリング', () => {
    it('should display error message on fetch failure', async () => {
      vi.mocked(contactApi.fetchContacts).mockRejectedValue(new Error('Network error'));

      render(<ContactList />);

      await waitFor(() => {
        expect(screen.getByText(/エラー/)).toBeInTheDocument();
      });
    });

    it('should have retry button on error', async () => {
      vi.mocked(contactApi.fetchContacts).mockRejectedValue(new Error('Network error'));

      render(<ContactList />);

      await waitFor(() => {
        expect(screen.getByText('再読み込み')).toBeInTheDocument();
      });
    });
  });

  describe('削除機能 (Requirement 3.1, 3.2)', () => {
    it('should show delete button for each contact', async () => {
      vi.mocked(contactApi.fetchContacts).mockResolvedValue({
        contacts: mockContacts,
        total: 3,
      });

      render(<ContactList />);

      await waitFor(() => {
        const deleteButtons = screen.getAllByRole('button', { name: /削除/ });
        expect(deleteButtons).toHaveLength(3);
      });
    });

    it('should show confirmation dialog when delete button clicked', async () => {
      vi.mocked(contactApi.fetchContacts).mockResolvedValue({
        contacts: mockContacts,
        total: 3,
      });

      const user = userEvent.setup();
      render(<ContactList />);

      await waitFor(() => {
        expect(screen.getByText('田中部長')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByRole('button', { name: /削除/ });
      await user.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/削除しますか/)).toBeInTheDocument();
      });
    });

    it('should call deleteContact API when confirmed', async () => {
      vi.mocked(contactApi.fetchContacts).mockResolvedValue({
        contacts: mockContacts,
        total: 3,
      });
      vi.mocked(contactApi.deleteContact).mockResolvedValue(undefined);

      const user = userEvent.setup();
      render(<ContactList />);

      await waitFor(() => {
        expect(screen.getByText('田中部長')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByRole('button', { name: /削除/ });
      await user.click(deleteButtons[0]);

      // Confirm deletion
      const confirmButton = await screen.findByRole('button', {
        name: /確認|OK|はい/,
      });
      await user.click(confirmButton);

      await waitFor(() => {
        expect(contactApi.deleteContact).toHaveBeenCalledWith('mock-token', '1');
      });
    });

    it('should not call deleteContact when cancelled', async () => {
      vi.mocked(contactApi.fetchContacts).mockResolvedValue({
        contacts: mockContacts,
        total: 3,
      });

      const user = userEvent.setup();
      render(<ContactList />);

      await waitFor(() => {
        expect(screen.getByText('田中部長')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByRole('button', { name: /削除/ });
      await user.click(deleteButtons[0]);

      // Cancel deletion
      const cancelButton = await screen.findByRole('button', {
        name: /キャンセル|いいえ/,
      });
      await user.click(cancelButton);

      expect(contactApi.deleteContact).not.toHaveBeenCalled();
    });
  });

  describe('学習失敗時の再試行 (Requirement 5.3)', () => {
    it('should show retry button for failed contacts', async () => {
      vi.mocked(contactApi.fetchContacts).mockResolvedValue({
        contacts: mockContacts,
        total: 3,
      });

      render(<ContactList />);

      await waitFor(() => {
        // suzuki has failed learning
        const suzukiCard = screen
          .getByText('suzuki@example.com')
          .closest('[data-testid="contact-card"]');
        expect(suzukiCard?.querySelector('[data-testid="retry-button"]')).toBeInTheDocument();
      });
    });

    it('should call retryLearning API when retry button clicked', async () => {
      vi.mocked(contactApi.fetchContacts).mockResolvedValue({
        contacts: mockContacts,
        total: 3,
      });
      vi.mocked(contactApi.retryLearning).mockResolvedValue({
        id: '3',
        contactEmail: 'suzuki@example.com',
        contactName: null,
        gmailQuery: null,
        isLearningComplete: false,
        learningFailedAt: null,
        createdAt: '2024-01-13T09:00:00+00:00',
        status: 'learning_started' as const,
      });

      const user = userEvent.setup();
      render(<ContactList />);

      await waitFor(() => {
        expect(screen.getByText('suzuki@example.com')).toBeInTheDocument();
      });

      const retryButton = screen.getByTestId('retry-button');
      await user.click(retryButton);

      await waitFor(() => {
        expect(contactApi.retryLearning).toHaveBeenCalledWith('mock-token', '3');
      });
    });

    it('should update contact status to learning after retry', async () => {
      vi.mocked(contactApi.fetchContacts).mockResolvedValue({
        contacts: mockContacts,
        total: 3,
      });
      vi.mocked(contactApi.retryLearning).mockResolvedValue({
        id: '3',
        contactEmail: 'suzuki@example.com',
        contactName: null,
        gmailQuery: null,
        isLearningComplete: false,
        learningFailedAt: null,
        createdAt: '2024-01-13T09:00:00+00:00',
        status: 'learning_started' as const,
      });

      const user = userEvent.setup();
      render(<ContactList />);

      await waitFor(() => {
        expect(screen.getByText('suzuki@example.com')).toBeInTheDocument();
      });

      const retryButton = screen.getByTestId('retry-button');
      await user.click(retryButton);

      await waitFor(() => {
        const suzukiCard = screen
          .getByText('suzuki@example.com')
          .closest('[data-testid="contact-card"]');
        expect(suzukiCard).toHaveTextContent('学習中');
      });
    });

    it('should show error when retry fails', async () => {
      vi.mocked(contactApi.fetchContacts).mockResolvedValue({
        contacts: mockContacts,
        total: 3,
      });
      vi.mocked(contactApi.retryLearning).mockRejectedValue(
        new Error('再試行に失敗しました')
      );

      const user = userEvent.setup();
      render(<ContactList />);

      await waitFor(() => {
        expect(screen.getByText('suzuki@example.com')).toBeInTheDocument();
      });

      const retryButton = screen.getByTestId('retry-button');
      await user.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText(/エラー/)).toBeInTheDocument();
      });
    });
  });
});
