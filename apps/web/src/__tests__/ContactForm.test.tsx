/**
 * @vitest-environment jsdom
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as contactApi from '../api/contacts';
import { ContactForm } from '../components/ContactForm';

// Mock the contacts API
vi.mock('../api/contacts', () => ({
  createContact: vi.fn(),
}));

// Mock AuthContext
vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(() => ({
    idToken: 'mock-token',
    user: { uid: 'test-uid', email: 'test@example.com' },
    isLoading: false,
  })),
}));

describe('ContactForm', () => {
  const mockOnSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('フォーム表示 (Requirement 1.5)', () => {
    it('should render email input field (required)', () => {
      render(<ContactForm onSuccess={mockOnSuccess} />);

      const emailInput = screen.getByLabelText(/メールアドレス/);
      expect(emailInput).toBeInTheDocument();
      expect(emailInput).toHaveAttribute('aria-required', 'true');
    });

    it('should render name input field (optional)', () => {
      render(<ContactForm onSuccess={mockOnSuccess} />);

      const nameInput = screen.getByLabelText(/名前/);
      expect(nameInput).toBeInTheDocument();
      expect(nameInput).not.toHaveAttribute('aria-required');
    });

    it('should render gmail query input field (optional)', () => {
      render(<ContactForm onSuccess={mockOnSuccess} />);

      const queryInput = screen.getByLabelText(/Gmail検索クエリ/);
      expect(queryInput).toBeInTheDocument();
      expect(queryInput).not.toHaveAttribute('aria-required');
    });

    it('should render submit button', () => {
      render(<ContactForm onSuccess={mockOnSuccess} />);

      expect(screen.getByRole('button', { name: /登録/ })).toBeInTheDocument();
    });
  });

  describe('バリデーション', () => {
    it('should show error for invalid email format', async () => {
      const user = userEvent.setup();
      render(<ContactForm onSuccess={mockOnSuccess} />);

      const emailInput = screen.getByLabelText(/メールアドレス/);
      await user.type(emailInput, 'invalid-email');

      const submitButton = screen.getByRole('button', { name: /登録/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/有効なメールアドレスを入力してください/)).toBeInTheDocument();
      });
    });

    it('should show error for empty email', async () => {
      const user = userEvent.setup();
      render(<ContactForm onSuccess={mockOnSuccess} />);

      const submitButton = screen.getByRole('button', { name: /登録/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/メールアドレスは必須です/)).toBeInTheDocument();
      });
    });

    it('should accept valid email format', async () => {
      vi.mocked(contactApi.createContact).mockResolvedValue({
        id: '1',
        contactEmail: 'test@example.com',
        contactName: null,
        gmailQuery: null,
        isLearningComplete: false,
        learningFailedAt: null,
        createdAt: '2024-01-15T10:30:00+00:00',
        status: 'learning_started',
      });

      const user = userEvent.setup();
      render(<ContactForm onSuccess={mockOnSuccess} />);

      const emailInput = screen.getByLabelText(/メールアドレス/);
      await user.type(emailInput, 'test@example.com');

      const submitButton = screen.getByRole('button', { name: /登録/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(contactApi.createContact).toHaveBeenCalled();
      });
    });
  });

  describe('フォーム送信', () => {
    it('should call createContact API with form data', async () => {
      vi.mocked(contactApi.createContact).mockResolvedValue({
        id: '1',
        contactEmail: 'boss@example.com',
        contactName: '上司',
        gmailQuery: 'from:boss@example.com',
        isLearningComplete: false,
        learningFailedAt: null,
        createdAt: '2024-01-15T10:30:00+00:00',
        status: 'learning_started',
      });

      const user = userEvent.setup();
      render(<ContactForm onSuccess={mockOnSuccess} />);

      await user.type(screen.getByLabelText(/メールアドレス/), 'boss@example.com');
      await user.type(screen.getByLabelText(/名前/), '上司');
      await user.type(screen.getByLabelText(/Gmail検索クエリ/), 'from:boss@example.com');

      await user.click(screen.getByRole('button', { name: /登録/ }));

      await waitFor(() => {
        expect(contactApi.createContact).toHaveBeenCalledWith('mock-token', {
          contactEmail: 'boss@example.com',
          contactName: '上司',
          gmailQuery: 'from:boss@example.com',
        });
      });
    });

    it('should call onSuccess callback after successful creation', async () => {
      vi.mocked(contactApi.createContact).mockResolvedValue({
        id: '1',
        contactEmail: 'test@example.com',
        contactName: null,
        gmailQuery: null,
        isLearningComplete: false,
        learningFailedAt: null,
        createdAt: '2024-01-15T10:30:00+00:00',
        status: 'learning_started',
      });

      const user = userEvent.setup();
      render(<ContactForm onSuccess={mockOnSuccess} />);

      await user.type(screen.getByLabelText(/メールアドレス/), 'test@example.com');
      await user.click(screen.getByRole('button', { name: /登録/ }));

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });

    it('should clear form after successful creation', async () => {
      vi.mocked(contactApi.createContact).mockResolvedValue({
        id: '1',
        contactEmail: 'test@example.com',
        contactName: 'テスト',
        gmailQuery: null,
        isLearningComplete: false,
        learningFailedAt: null,
        createdAt: '2024-01-15T10:30:00+00:00',
        status: 'learning_started',
      });

      const user = userEvent.setup();
      render(<ContactForm onSuccess={mockOnSuccess} />);

      await user.type(screen.getByLabelText(/メールアドレス/), 'test@example.com');
      await user.type(screen.getByLabelText(/名前/), 'テスト');
      await user.click(screen.getByRole('button', { name: /登録/ }));

      await waitFor(() => {
        expect(screen.getByLabelText(/メールアドレス/)).toHaveValue('');
        expect(screen.getByLabelText(/名前/)).toHaveValue('');
      });
    });
  });

  describe('エラーハンドリング', () => {
    it('should display error message on duplicate contact (409)', async () => {
      vi.mocked(contactApi.createContact).mockRejectedValue(
        new Error('この連絡先は既に登録されています')
      );

      const user = userEvent.setup();
      render(<ContactForm onSuccess={mockOnSuccess} />);

      await user.type(screen.getByLabelText(/メールアドレス/), 'test@example.com');
      await user.click(screen.getByRole('button', { name: /登録/ }));

      await waitFor(() => {
        expect(screen.getByText('この連絡先は既に登録されています')).toBeInTheDocument();
      });
    });

    it('should display generic error message on API failure', async () => {
      vi.mocked(contactApi.createContact).mockRejectedValue(new Error('Network error'));

      const user = userEvent.setup();
      render(<ContactForm onSuccess={mockOnSuccess} />);

      await user.type(screen.getByLabelText(/メールアドレス/), 'test@example.com');
      await user.click(screen.getByRole('button', { name: /登録/ }));

      await waitFor(() => {
        expect(screen.getByText(/Network error/)).toBeInTheDocument();
      });
    });
  });

  describe('送信中の状態', () => {
    it('should disable submit button while submitting', async () => {
      vi.mocked(contactApi.createContact).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const user = userEvent.setup();
      render(<ContactForm onSuccess={mockOnSuccess} />);

      await user.type(screen.getByLabelText(/メールアドレス/), 'test@example.com');
      await user.click(screen.getByRole('button', { name: /登録/ }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /登録/ })).toBeDisabled();
      });
    });

    it('should show loading indicator while submitting', async () => {
      vi.mocked(contactApi.createContact).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const user = userEvent.setup();
      render(<ContactForm onSuccess={mockOnSuccess} />);

      await user.type(screen.getByLabelText(/メールアドレス/), 'test@example.com');
      await user.click(screen.getByRole('button', { name: /登録/ }));

      await waitFor(() => {
        expect(screen.getByText(/登録中/)).toBeInTheDocument();
      });
    });
  });
});
