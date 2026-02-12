/**
 * Contact list component for displaying all contacts.
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 5.1, 5.2, 5.3
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  deleteContact,
  fetchContacts,
  instructContact,
  relearnContact,
  retryLearning,
} from '../api/contacts';
import { useAuth } from '../contexts/AuthContext';
import type { Contact } from '../types/contact';
import { ContactCard } from './ContactCard';

/**
 * Polling interval for learning status updates (30 seconds).
 */
const POLLING_INTERVAL_MS = 30000;

interface DeleteConfirmDialogProps {
  contact: Contact | null;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Confirmation dialog for contact deletion.
 */
function DeleteConfirmDialog({ contact, onConfirm, onCancel }: DeleteConfirmDialogProps) {
  if (!contact) return null;

  const displayName = contact.contactName || contact.contactEmail;

  return (
    <div className="dialog-overlay" role="dialog" aria-modal="true">
      <div className="dialog">
        <p>「{displayName}」を削除しますか？</p>
        <p className="dialog-warning">
          この操作は取り消せません。関連する学習データも削除されます。
        </p>
        <div className="dialog-actions">
          <button type="button" className="dialog-cancel" onClick={onCancel}>
            キャンセル
          </button>
          <button type="button" className="dialog-confirm" onClick={onConfirm}>
            確認
          </button>
        </div>
      </div>
    </div>
  );
}

interface RelearnConfirmDialogProps {
  contact: Contact | null;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Confirmation dialog for contact relearning.
 */
function RelearnConfirmDialog({ contact, onConfirm, onCancel }: RelearnConfirmDialogProps) {
  if (!contact) return null;

  const displayName = contact.contactName || contact.contactEmail;

  return (
    <div className="dialog-overlay" role="dialog" aria-modal="true">
      <div className="dialog">
        <p>「{displayName}」を再学習しますか？</p>
        <p className="dialog-warning">現在の学習データを削除し、最新のメール履歴で再学習します。</p>
        <div className="dialog-actions">
          <button type="button" className="dialog-cancel" onClick={onCancel}>
            キャンセル
          </button>
          <button type="button" className="dialog-confirm" onClick={onConfirm}>
            確認
          </button>
        </div>
      </div>
    </div>
  );
}

interface InstructDialogProps {
  contact: Contact | null;
  instructionText: string;
  onTextChange: (text: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
}

/**
 * Dialog for entering user instructions for a contact.
 */
function InstructDialog({
  contact,
  instructionText,
  onTextChange,
  onSubmit,
  onCancel,
}: InstructDialogProps) {
  if (!contact) return null;

  const displayName = contact.contactName || contact.contactEmail;

  return (
    <div className="dialog-overlay" role="dialog" aria-modal="true" data-testid="instruct-dialog">
      <div className="dialog instruct-dialog">
        <p>「{displayName}」さんが宛先の場合の指示</p>
        <p className="dialog-warning">メール作成時に適用するルールを入力してください。</p>
        <textarea
          className="instruct-textarea"
          data-testid="instruct-textarea"
          value={instructionText}
          onChange={(e) => onTextChange(e.target.value)}
          placeholder="例: 文章の最後には「田中より」と追加して"
          rows={3}
          maxLength={1000}
        />
        <div className="dialog-actions">
          <button type="button" className="dialog-cancel" onClick={onCancel}>
            キャンセル
          </button>
          <button
            type="button"
            className="instruct-submit"
            data-testid="instruct-submit"
            onClick={onSubmit}
            disabled={!instructionText.trim()}
          >
            送信
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Contact list component that fetches and displays all contacts for the user.
 *
 * Features:
 * - Fetches contacts using Firebase ID Token
 * - Shows loading state while fetching
 * - Shows empty state when no contacts
 * - Shows error state on fetch failure
 * - Polls for learning status updates every 30 seconds
 * - Delete with confirmation dialog
 */
export function ContactList() {
  const { idToken } = useAuth();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Contact | null>(null);
  const [, setIsDeleting] = useState(false);
  const [relearnTarget, setRelearnTarget] = useState<Contact | null>(null);
  const [instructTarget, setInstructTarget] = useState<Contact | null>(null);
  const [instructionText, setInstructionText] = useState('');
  const pollingRef = useRef<number | null>(null);

  const loadContacts = useCallback(async () => {
    if (!idToken) {
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetchContacts(idToken);
      setContacts(response.contacts);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'エラーが発生しました');
    } finally {
      setIsLoading(false);
    }
  }, [idToken]);

  // Initial load
  useEffect(() => {
    loadContacts();
  }, [loadContacts]);

  // Polling for learning status updates
  useEffect(() => {
    // Only poll if there are contacts that are still learning
    const hasLearningContacts = contacts.some((c) => !c.isLearningComplete && !c.learningFailedAt);

    if (hasLearningContacts && idToken) {
      pollingRef.current = window.setInterval(() => {
        loadContacts();
      }, POLLING_INTERVAL_MS);
    }

    return () => {
      if (pollingRef.current) {
        window.clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [contacts, idToken, loadContacts]);

  const handleDeleteClick = useCallback(
    (contactId: string) => {
      const contact = contacts.find((c) => c.id === contactId);
      if (contact) {
        setDeleteTarget(contact);
      }
    },
    [contacts]
  );

  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteTarget || !idToken) return;

    setIsDeleting(true);
    try {
      await deleteContact(idToken, deleteTarget.id);
      setContacts((prev) => prev.filter((c) => c.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '削除に失敗しました');
    } finally {
      setIsDeleting(false);
    }
  }, [deleteTarget, idToken]);

  const handleDeleteCancel = useCallback(() => {
    setDeleteTarget(null);
  }, []);

  const handleRetry = useCallback(
    async (contactId: string) => {
      if (!idToken) return;

      try {
        const updated = await retryLearning(idToken, contactId);
        setContacts((prev) => prev.map((c) => (c.id === contactId ? updated : c)));
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : '再試行に失敗しました');
      }
    },
    [idToken]
  );

  const handleRelearnClick = useCallback(
    (contactId: string) => {
      const contact = contacts.find((c) => c.id === contactId);
      if (contact) {
        setRelearnTarget(contact);
      }
    },
    [contacts]
  );

  const handleRelearnConfirm = useCallback(async () => {
    if (!relearnTarget || !idToken) return;

    try {
      const updated = await relearnContact(idToken, relearnTarget.id);
      setContacts((prev) => prev.map((c) => (c.id === relearnTarget.id ? updated : c)));
      setRelearnTarget(null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '再学習に失敗しました');
      setRelearnTarget(null);
    }
  }, [relearnTarget, idToken]);

  const handleRelearnCancel = useCallback(() => {
    setRelearnTarget(null);
  }, []);

  const handleInstructClick = useCallback(
    (contactId: string) => {
      const contact = contacts.find((c) => c.id === contactId);
      if (contact) {
        setInstructTarget(contact);
        setInstructionText('');
      }
    },
    [contacts]
  );

  const handleInstructSubmit = useCallback(async () => {
    if (!instructTarget || !idToken || !instructionText.trim()) return;

    try {
      await instructContact(idToken, instructTarget.id, instructionText.trim());
      setInstructTarget(null);
      setInstructionText('');
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '指示の送信に失敗しました');
      setInstructTarget(null);
      setInstructionText('');
    }
  }, [instructTarget, idToken, instructionText]);

  const handleInstructCancel = useCallback(() => {
    setInstructTarget(null);
    setInstructionText('');
  }, []);

  if (isLoading) {
    return (
      <div className="contact-list-loading">
        <span className="loading-spinner" aria-hidden="true" />
        <p>読み込み中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="contact-list-error" role="alert">
        <p>エラー: {error}</p>
        <button type="button" onClick={loadContacts} className="retry-button">
          再読み込み
        </button>
      </div>
    );
  }

  if (contacts.length === 0) {
    return (
      <div className="contact-list-empty">
        <p>連絡先がありません</p>
      </div>
    );
  }

  return (
    <>
      <div className="contact-list">
        {contacts.map((contact) => (
          <ContactCard
            key={contact.id}
            contact={contact}
            onDelete={handleDeleteClick}
            onRetry={handleRetry}
            onRelearn={handleRelearnClick}
            onInstruct={handleInstructClick}
          />
        ))}
      </div>
      <DeleteConfirmDialog
        contact={deleteTarget}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
      />
      <RelearnConfirmDialog
        contact={relearnTarget}
        onConfirm={handleRelearnConfirm}
        onCancel={handleRelearnCancel}
      />
      <InstructDialog
        contact={instructTarget}
        instructionText={instructionText}
        onTextChange={setInstructionText}
        onSubmit={handleInstructSubmit}
        onCancel={handleInstructCancel}
      />
    </>
  );
}
