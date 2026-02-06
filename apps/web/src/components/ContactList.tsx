/**
 * Contact list component for displaying all contacts.
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 5.1, 5.2, 5.3
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { deleteContact, fetchContacts, retryLearning } from '../api/contacts';
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
          />
        ))}
      </div>
      <DeleteConfirmDialog
        contact={deleteTarget}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
      />
    </>
  );
}
