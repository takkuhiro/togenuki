/**
 * Email card component for displaying individual email items.
 * Requirements: 4.4, 4.5
 */

import type { Email } from "../types/email";
import { AudioPlayer } from "./AudioPlayer";

interface EmailCardProps {
  email: Email;
}

/**
 * Email card component that displays email information in a card format.
 *
 * Features:
 * - Shows sender name, subject, and converted body
 * - Shows loading indicator for unprocessed emails
 * - Includes audio player for processed emails
 */
export function EmailCard({ email }: EmailCardProps) {
  const formatDate = (dateString: string | null) => {
    if (!dateString) return "";

    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return date.toLocaleTimeString("ja-JP", {
        hour: "2-digit",
        minute: "2-digit",
      });
    } else if (days === 1) {
      return "昨日";
    } else if (days < 7) {
      return `${days}日前`;
    } else {
      return date.toLocaleDateString("ja-JP", {
        month: "short",
        day: "numeric",
      });
    }
  };

  return (
    <article className="email-card">
      <div className="email-card-header">
        <div className="email-card-sender">
          <span className="sender-name">{email.senderName || "不明な送信者"}</span>
          <span className="sender-email">{email.senderEmail}</span>
        </div>
        <span className="email-card-date">{formatDate(email.receivedAt)}</span>
      </div>

      <h3 className="email-card-subject">{email.subject || "(件名なし)"}</h3>

      {email.isProcessed ? (
        <>
          {email.convertedBody && (
            <p className="email-card-body">{email.convertedBody}</p>
          )}
          <div className="email-card-actions">
            <AudioPlayer audioUrl={email.audioUrl} emailId={email.id} />
          </div>
        </>
      ) : (
        <div className="email-card-processing">
          <span className="processing-spinner" aria-hidden="true" />
          <span>処理中...</span>
        </div>
      )}
    </article>
  );
}
