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

describe('ContactCard - 学習ボタン', () => {
  describe('学習ボタンの表示条件', () => {
    it('should show learn button when status is learning_complete', () => {
      const onLearn = vi.fn();
      render(
        <ContactCard
          contact={{
            ...baseContact,
            status: 'learning_complete',
            isLearningComplete: true,
            learningFailedAt: null,
          }}
          onDelete={vi.fn()}
          onLearn={onLearn}
        />
      );

      expect(screen.getByTestId('learn-button')).toBeInTheDocument();
      expect(screen.getByTestId('learn-button')).toHaveTextContent('学習');
    });

    it('should not show learn button when status is learning_started', () => {
      render(
        <ContactCard
          contact={{
            ...baseContact,
            status: 'learning_started',
            isLearningComplete: false,
            learningFailedAt: null,
          }}
          onDelete={vi.fn()}
          onLearn={vi.fn()}
        />
      );

      expect(screen.queryByTestId('learn-button')).not.toBeInTheDocument();
    });

    it('should not show learn button when status is learning_failed', () => {
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
          onLearn={vi.fn()}
        />
      );

      expect(screen.queryByTestId('learn-button')).not.toBeInTheDocument();
    });
  });

  describe('学習ボタンのクリック', () => {
    it('should call onLearn with contact id when clicked', async () => {
      const onLearn = vi.fn();
      const user = userEvent.setup();

      render(
        <ContactCard
          contact={{ ...baseContact, status: 'learning_complete', isLearningComplete: true }}
          onDelete={vi.fn()}
          onLearn={onLearn}
        />
      );

      await user.click(screen.getByTestId('learn-button'));
      expect(onLearn).toHaveBeenCalledWith('1');
    });

    it('should not show learn button when onLearn callback is not provided', () => {
      render(
        <ContactCard
          contact={{ ...baseContact, status: 'learning_complete', isLearningComplete: true }}
          onDelete={vi.fn()}
        />
      );

      expect(screen.queryByTestId('learn-button')).not.toBeInTheDocument();
    });
  });
});
