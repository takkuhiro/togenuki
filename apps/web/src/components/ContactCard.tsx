/**
 * Contact card component for displaying individual contact items.
 * Requirements: 2.2, 2.3, 2.4, 3.1, 5.3
 */

import type { Contact } from '../types/contact';

interface ContactCardProps {
  contact: Contact;
  onDelete: (contactId: string) => void;
  onRetry?: (contactId: string) => void;
}

/**
 * Get learning status label based on contact state.
 */
function getLearningStatus(contact: Contact): {
  label: string;
  className: string;
} {
  if (contact.learningFailedAt) {
    return { label: '学習失敗', className: 'status--failed' };
  }
  if (contact.isLearningComplete) {
    return { label: '学習完了', className: 'status--complete' };
  }
  return { label: '学習中', className: 'status--learning' };
}

/**
 * Contact card component that displays contact information.
 *
 * Features:
 * - Displays contact name, email, and learning status
 * - Shows delete button
 * - Shows retry button for failed contacts
 */
export function ContactCard({ contact, onDelete, onRetry }: ContactCardProps) {
  const status = getLearningStatus(contact);
  const displayName = contact.contactName || contact.contactEmail;

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="contact-card" data-testid="contact-card">
      <div className="contact-card-main">
        <div className="contact-card-info">
          <span className="contact-name">{displayName}</span>
          {contact.contactName && <span className="contact-email">{contact.contactEmail}</span>}
        </div>
        <div className="contact-card-meta">
          <span className={`contact-status ${status.className}`}>
            {status.label === '学習中' && <span className="learning-spinner" aria-hidden="true" />}
            {status.label}
          </span>
          <span className="contact-date">{formatDate(contact.createdAt)}</span>
        </div>
      </div>
      <div className="contact-card-actions">
        {contact.learningFailedAt && onRetry && (
          <button
            type="button"
            className="retry-button"
            data-testid="retry-button"
            onClick={() => onRetry(contact.id)}
          >
            再試行
          </button>
        )}
        <button
          type="button"
          className="delete-button"
          onClick={() => onDelete(contact.id)}
          aria-label={`${displayName}を削除`}
        >
          削除
        </button>
      </div>
    </div>
  );
}
