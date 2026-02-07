/**
 * Email card component for displaying individual email items.
 * Requirements: 1.1, 1.2, 4.4, 4.5
 */

import { useState } from 'react';
import type { Email } from '../types/email';
import { AudioPlayer } from './AudioPlayer';
import { VoiceReplyPanel } from './VoiceReplyPanel';

interface EmailCardProps {
  email: Email;
  isExpanded: boolean;
  onToggle: () => void;
}

/**
 * Email card component that displays email information in a toggle format.
 *
 * Features:
 * - Header (sender, subject, date) is always visible
 * - Click to expand/collapse content
 * - Shows loading indicator for unprocessed emails (when expanded)
 * - Includes audio player for processed emails (when expanded)
 */
export function EmailCard({ email, isExpanded, onToggle }: EmailCardProps) {
  const [showVoiceReply, setShowVoiceReply] = useState(false);
  const formatDate = (dateString: string | null) => {
    if (!dateString) return '';

    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return date.toLocaleTimeString('ja-JP', {
        hour: '2-digit',
        minute: '2-digit',
      });
    } else if (days === 1) {
      return '昨日';
    } else if (days < 7) {
      return `${days}日前`;
    } else {
      return date.toLocaleDateString('ja-JP', {
        month: 'short',
        day: 'numeric',
      });
    }
  };

  return (
    <article className={`email-card ${isExpanded ? 'email-card--expanded' : ''}`}>
      {/* Header - Always visible, clickable to toggle */}
      <button type="button" className="email-card-header" onClick={onToggle}>
        <div className="email-card-header-main">
          <div className="email-card-sender">
            <span className="sender-name">{email.senderName || '不明な送信者'}</span>
            <span className="sender-email">{email.senderEmail}</span>
          </div>
          <h3 className="email-card-subject">{email.subject || '(件名なし)'}</h3>
        </div>
        <div className="email-card-header-meta">
          <span className="email-card-date">{formatDate(email.receivedAt)}</span>
          <span className={`email-card-chevron ${isExpanded ? 'email-card-chevron--up' : ''}`}>
            ▼
          </span>
        </div>
      </button>

      {/* Content - Only visible when expanded */}
      {isExpanded && (
        <div className="email-card-content">
          {email.isProcessed ? (
            <>
              {email.convertedBody && <p className="email-card-body">{email.convertedBody}</p>}
              <div className="email-card-actions">
                <AudioPlayer audioUrl={email.audioUrl} emailId={email.id} />
                <button
                  type="button"
                  className="voice-reply-toggle-button"
                  onClick={() => setShowVoiceReply((prev) => !prev)}
                >
                  {showVoiceReply ? '返信を閉じる' : '音声入力で返信'}
                </button>
              </div>
              {showVoiceReply && (
                <VoiceReplyPanel
                  emailId={email.id}
                  senderEmail={email.senderEmail}
                  senderName={email.senderName}
                  subject={email.subject}
                />
              )}
            </>
          ) : (
            <div className="email-card-processing">
              <span className="processing-spinner" aria-hidden="true" />
              <span>処理中...</span>
            </div>
          )}
        </div>
      )}
    </article>
  );
}
