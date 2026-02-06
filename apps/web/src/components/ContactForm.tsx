/**
 * Contact form component for creating new contacts.
 * Requirements: 1.5
 */

import { useCallback, useState } from 'react';
import { createContact } from '../api/contacts';
import { useAuth } from '../contexts/AuthContext';

interface ContactFormProps {
  onSuccess: () => void;
}

/**
 * Validate email format.
 */
function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Contact form component for registering new contacts.
 *
 * Features:
 * - Email input (required)
 * - Name input (optional)
 * - Gmail search query input (optional)
 * - Email format validation
 * - Loading state while submitting
 * - Error display
 */
export function ContactForm({ onSuccess }: ContactFormProps) {
  const { idToken } = useAuth();
  const [contactEmail, setContactEmail] = useState('');
  const [contactName, setContactName] = useState('');
  const [gmailQuery, setGmailQuery] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const validateForm = useCallback((): boolean => {
    if (!contactEmail.trim()) {
      setValidationError('メールアドレスは必須です');
      return false;
    }
    if (!isValidEmail(contactEmail.trim())) {
      setValidationError('有効なメールアドレスを入力してください');
      return false;
    }
    setValidationError(null);
    return true;
  }, [contactEmail]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!validateForm()) {
        return;
      }

      if (!idToken) {
        setError('認証されていません');
        return;
      }

      setIsSubmitting(true);
      setError(null);

      try {
        await createContact(idToken, {
          contactEmail: contactEmail.trim(),
          contactName: contactName.trim() || undefined,
          gmailQuery: gmailQuery.trim() || undefined,
        });

        // Clear form on success
        setContactEmail('');
        setContactName('');
        setGmailQuery('');
        onSuccess();
      } catch (err) {
        setError(err instanceof Error ? err.message : '登録に失敗しました');
      } finally {
        setIsSubmitting(false);
      }
    },
    [idToken, contactEmail, contactName, gmailQuery, validateForm, onSuccess]
  );

  return (
    <form className="contact-form" onSubmit={handleSubmit}>
      <div className="form-field">
        <label htmlFor="contactEmail">
          メールアドレス <span className="required">*</span>
        </label>
        <input
          type="text"
          id="contactEmail"
          value={contactEmail}
          onChange={(e) => setContactEmail(e.target.value)}
          placeholder="example@company.com"
          aria-required="true"
          disabled={isSubmitting}
        />
      </div>

      <div className="form-field">
        <label htmlFor="contactName">名前</label>
        <input
          type="text"
          id="contactName"
          value={contactName}
          onChange={(e) => setContactName(e.target.value)}
          placeholder="田中部長"
          disabled={isSubmitting}
        />
      </div>

      <div className="form-field">
        <label htmlFor="gmailQuery">
          Gmail検索クエリ
          <span className="tooltip-wrapper">
            <span className="tooltip-icon" aria-hidden="true">
              ?
            </span>
            <span className="tooltip-text" role="tooltip">
              学習対象とするメールを絞り込むためのGmail検索クエリ（省略可）
            </span>
          </span>
        </label>
        <input
          type="text"
          id="gmailQuery"
          value={gmailQuery}
          onChange={(e) => setGmailQuery(e.target.value)}
          placeholder="from:example@company.com"
          disabled={isSubmitting}
        />
      </div>

      {validationError && (
        <div className="form-error" role="alert">
          {validationError}
        </div>
      )}

      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}

      <button type="submit" className="submit-button" disabled={isSubmitting}>
        {isSubmitting ? '登録中...' : '登録'}
      </button>
    </form>
  );
}
