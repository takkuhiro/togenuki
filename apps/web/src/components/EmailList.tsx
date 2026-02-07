/**
 * Email list component for displaying all emails.
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
 */

import { useCallback, useEffect, useState } from 'react';
import { fetchEmails } from '../api/emails';
import { useAuth } from '../contexts/AuthContext';
import type { Email } from '../types/email';
import { EmailCard } from './EmailCard';

/**
 * Email list component that fetches and displays all emails for the user.
 *
 * Features:
 * - Fetches emails using Firebase ID Token
 * - Displays emails sorted by received date (newest first)
 * - Shows loading state while fetching
 * - Shows empty state when no emails
 * - Shows error state on fetch failure
 * - Toggle expansion for individual email cards
 */
export function EmailList() {
  const { idToken } = useAuth();
  const [emails, setEmails] = useState<Email[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedEmailId, setExpandedEmailId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'unreplied' | 'replied'>('unreplied');

  const handleToggle = useCallback((emailId: string) => {
    setExpandedEmailId((prevId) => (prevId === emailId ? null : emailId));
  }, []);

  const handleReplied = useCallback((emailId: string) => {
    setEmails((prev) =>
      prev.map((email) =>
        email.id === emailId ? { ...email, repliedAt: new Date().toISOString() } : email
      )
    );
  }, []);

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
      setError(err instanceof Error ? err.message : 'エラーが発生しました');
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
        <button type="button" onClick={loadEmails} className="retry-button">
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

  const unrepliedEmails = emails.filter((email) => !email.repliedAt);
  const repliedEmails = emails.filter((email) => email.repliedAt);
  const displayedEmails = activeTab === 'unreplied' ? unrepliedEmails : repliedEmails;

  return (
    <div className="email-list">
      <div className="email-list-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'unreplied'}
          className={`email-list-tab ${activeTab === 'unreplied' ? 'email-list-tab--active' : ''}`}
          onClick={() => setActiveTab('unreplied')}
        >
          未返信（{unrepliedEmails.length}件）
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'replied'}
          className={`email-list-tab ${activeTab === 'replied' ? 'email-list-tab--active' : ''}`}
          onClick={() => setActiveTab('replied')}
        >
          返信済み（{repliedEmails.length}件）
        </button>
      </div>
      <div role="tabpanel">
        {activeTab === 'unreplied' && unrepliedEmails.length === 0 ? (
          <p className="email-list-section-title">すべて返信済みです</p>
        ) : (
          displayedEmails.map((email) => (
            <EmailCard
              key={email.id}
              email={email}
              isExpanded={expandedEmailId === email.id}
              onToggle={() => handleToggle(email.id)}
              onReplied={handleReplied}
            />
          ))
        )}
      </div>
    </div>
  );
}
