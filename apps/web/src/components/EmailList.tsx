/**
 * Email list component for displaying all emails.
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
 */

import { useState, useEffect, useCallback } from "react";
import type { Email } from "../types/email";
import { fetchEmails } from "../api/emails";
import { useAuth } from "../contexts/AuthContext";
import { EmailCard } from "./EmailCard";

/**
 * Email list component that fetches and displays all emails for the user.
 *
 * Features:
 * - Fetches emails using Firebase ID Token
 * - Displays emails sorted by received date (newest first)
 * - Shows loading state while fetching
 * - Shows empty state when no emails
 * - Shows error state on fetch failure
 */
export function EmailList() {
  const { idToken } = useAuth();
  const [emails, setEmails] = useState<Email[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadEmails = useCallback(async () => {
    if (!idToken) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetchEmails(idToken);
      setEmails(response.emails);
    } catch (err) {
      setError(err instanceof Error ? err.message : "エラーが発生しました");
    } finally {
      setIsLoading(false);
    }
  }, [idToken]);

  useEffect(() => {
    loadEmails();
  }, [loadEmails]);

  if (isLoading) {
    return (
      <div className="email-list-loading">
        <span className="loading-spinner" aria-hidden="true" />
        <p>読み込み中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="email-list-error" role="alert">
        <p>エラー: {error}</p>
        <button onClick={loadEmails} className="retry-button">
          再読み込み
        </button>
      </div>
    );
  }

  if (emails.length === 0) {
    return (
      <div className="email-list-empty">
        <p>メールがありません</p>
      </div>
    );
  }

  return (
    <div className="email-list">
      {emails.map((email) => (
        <EmailCard key={email.id} email={email} />
      ))}
    </div>
  );
}
