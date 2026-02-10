/**
 * @vitest-environment jsdom
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ContactCard } from '../components/ContactCard';
import type { Contact } from '../types/contact';

const baseContact: Contact = {
  id: '1',
  contactEmail: 'tanaka@example.com',
  contactName: '田中部長',
  gmailQuery: 'from:tanaka@example.com',
  isLearningComplete: true,
  learningFailedAt: null,
  createdAt: '2024-01-15T10:30:00+00:00',
  status: 'learning_complete',
};

describe('ContactCard - 再学習ボタン', () => {
  describe('再学習ボタンの表示条件 (Requirement 1.1, 1.2, 1.3)', () => {
    it('should show relearn button when status is learning_complete', () => {
      const onRelearn = vi.fn();
      render(
        <ContactCard
          contact={{
            ...baseContact,
            status: 'learning_complete',
            isLearningComplete: true,
            learningFailedAt: null,
          }}
          onDelete={vi.fn()}
          onRelearn={onRelearn}
        />
      );

      expect(screen.getByTestId('relearn-button')).toBeInTheDocument();
      expect(screen.getByTestId('relearn-button')).toHaveTextContent('再学習');
    });

    it('should not show relearn button when status is learning_started', () => {
      render(
        <ContactCard
          contact={{
            ...baseContact,
            status: 'learning_started',
            isLearningComplete: false,
            learningFailedAt: null,
          }}
          onDelete={vi.fn()}
          onRelearn={vi.fn()}
        />
      );

      expect(screen.queryByTestId('relearn-button')).not.toBeInTheDocument();
    });

    it('should not show relearn button when status is learning_failed', () => {
      render(
        <ContactCard
          contact={{
            ...baseContact,
            status: 'learning_failed',
            isLearningComplete: false,
            learningFailedAt: '2024-01-13T12:00:00+00:00',
          }}
          onDelete={vi.fn()}
          onRetry={vi.fn()}
          onRelearn={vi.fn()}
        />
      );

      expect(screen.queryByTestId('relearn-button')).not.toBeInTheDocument();
    });
  });

  describe('再学習ボタンのクリック (Requirement 3.1, 3.3)', () => {
    it('should call onRelearn with contact id when clicked', async () => {
      const onRelearn = vi.fn();
      const user = userEvent.setup();

      render(
        <ContactCard
          contact={{ ...baseContact, status: 'learning_complete', isLearningComplete: true }}
          onDelete={vi.fn()}
          onRelearn={onRelearn}
        />
      );

      await user.click(screen.getByTestId('relearn-button'));
      expect(onRelearn).toHaveBeenCalledWith('1');
    });

    it('should not show relearn button when onRelearn callback is not provided', () => {
      render(
        <ContactCard
          contact={{ ...baseContact, status: 'learning_complete', isLearningComplete: true }}
          onDelete={vi.fn()}
        />
      );

      expect(screen.queryByTestId('relearn-button')).not.toBeInTheDocument();
    });
  });
});
