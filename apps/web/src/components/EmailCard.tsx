/**
 * Email card component for displaying individual email items.
 * All voice reply functionality is integrated directly (no separate VoiceReplyPanel).
 * Requirements: 1.1, 1.2, 4.4, 4.5
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { composeReply, saveDraft, sendReply } from '../api/reply';
import { useAuth } from '../contexts/AuthContext';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import type { Email } from '../types/email';
import { AudioPlayer } from './AudioPlayer';
import { SplitActionButton } from './SplitActionButton';

type ReplyPhase =
  | 'idle'
  | 'recording'
  | 'composing'
  | 'composed'
  | 'confirming'
  | 'sending'
  | 'sent'
  | 'draft_saving'
  | 'error';

type ErrorType = 'compose' | 'send' | 'draft' | 'empty';

export interface EmailCardProps {
  email: Email;
  isExpanded: boolean;
  onToggle: () => void;
  onReplied?: (emailId: string) => void;
}

/**
 * Email card component that displays email information in a toggle format.
 *
 * Features:
 * - Header (sender, subject, date) is always visible
 * - Click to expand/collapse content
 * - Shows loading indicator for unprocessed emails (when expanded)
 * - Includes audio player and voice reply controls for processed emails (when expanded)
 */
export function EmailCard({ email, isExpanded, onToggle, onReplied }: EmailCardProps) {
  const { idToken } = useAuth();
  const speech = useSpeechRecognition();

  const [phase, setPhase] = useState<ReplyPhase>(
    email.composedBody && !email.repliedAt ? 'composed' : 'idle'
  );
  const [composedBody, setComposedBody] = useState(email.composedBody || '');
  const [composedSubject, setComposedSubject] = useState(email.composedSubject || '');
  const [hasDraft, setHasDraft] = useState(!!email.googleDraftId);
  const [error, setError] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<ErrorType>('compose');
  const wasListeningRef = useRef(false);
  const composeTriggeredRef = useRef(false);
  const [fallbackText, setFallbackText] = useState('');
  const [showSentReply, setShowSentReply] = useState(false);

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

  // Auto-compose when recording stops (isListening transitions from true to false)
  // biome-ignore lint/correctness/useExhaustiveDependencies: handleAutoCompose is stable via useCallback
  useEffect(() => {
    if (
      phase === 'recording' &&
      wasListeningRef.current &&
      !speech.isListening &&
      !composeTriggeredRef.current
    ) {
      composeTriggeredRef.current = true;
      const text = speech.transcript.trim() || speech.interimTranscript.trim();
      if (text) {
        handleAutoCompose(text);
      } else {
        setError('音声が検出されませんでした。もう一度お試しください。');
        setErrorType('empty');
        setPhase('error');
      }
    }
    wasListeningRef.current = speech.isListening;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speech.isListening, speech.transcript, phase]);

  const handleAutoCompose = useCallback(
    async (text: string) => {
      if (!idToken) return;

      setPhase('composing');
      setError(null);

      try {
        const result = await composeReply(idToken, email.id, { rawText: text });
        setComposedBody(result.composedBody);
        setComposedSubject(result.composedSubject);
        setPhase('composed');
      } catch (err) {
        setError(err instanceof Error ? err.message : '清書に失敗しました');
        setErrorType('compose');
        setPhase('error');
      }
    },
    [idToken, email.id]
  );

  const handleStartRecording = useCallback(() => {
    setComposedBody('');
    setComposedSubject('');
    setError(null);
    composeTriggeredRef.current = false;
    speech.resetTranscript();
    speech.startListening();
    setPhase('recording');
  }, [speech]);

  const handleStopRecording = useCallback(() => {
    speech.stopListening();
  }, [speech]);

  const handleRestartRecording = useCallback(() => {
    setComposedBody('');
    setComposedSubject('');
    setError(null);
    composeTriggeredRef.current = false;
    speech.resetTranscript();
    speech.startListening();
    setPhase('recording');
  }, [speech]);

  const handleConfirm = useCallback(() => {
    setPhase('confirming');
  }, []);

  const handleBack = useCallback(() => {
    setPhase('composed');
  }, []);

  const handleSend = useCallback(async () => {
    if (!idToken) return;

    setPhase('sending');
    setError(null);

    try {
      await sendReply(idToken, email.id, {
        composedBody,
        composedSubject,
      });
      setPhase('sent');
      onReplied?.(email.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : '送信に失敗しました');
      setErrorType('send');
      setPhase('error');
    }
  }, [idToken, email.id, composedBody, composedSubject, onReplied]);

  const handleRetrySend = useCallback(async () => {
    await handleSend();
  }, [handleSend]);

  const handleSaveDraft = useCallback(async () => {
    if (!idToken) return;

    setPhase('draft_saving');
    setError(null);

    try {
      await saveDraft(idToken, email.id, {
        composedBody,
        composedSubject,
      });
      setHasDraft(true);
      setPhase('composed');
    } catch (err) {
      setError(err instanceof Error ? err.message : '下書き保存に失敗しました');
      setErrorType('draft');
      setPhase('error');
    }
  }, [idToken, email.id, composedBody, composedSubject]);

  const handleFallbackCompose = useCallback(async () => {
    if (!idToken) return;
    if (!fallbackText.trim()) return;

    setPhase('composing');
    setError(null);

    try {
      const result = await composeReply(idToken, email.id, { rawText: fallbackText });
      setComposedBody(result.composedBody);
      setComposedSubject(result.composedSubject);
      setPhase('composed');
    } catch (err) {
      setError(err instanceof Error ? err.message : '清書に失敗しました');
      setErrorType('compose');
      setPhase('error');
    }
  }, [idToken, email.id, fallbackText]);

  const displaySubject = composedSubject || `Re: ${email.subject || ''}`;

  const renderReplyUI = () => {
    // Fallback for non-speech environments
    if (!speech.isAvailable) {
      return renderFallbackUI();
    }

    switch (phase) {
      case 'idle':
        return (
          <button type="button" className="audio-player-button" onClick={handleStartRecording}>
            <MicIcon />
            音声入力
          </button>
        );

      case 'recording':
        return (
          <>
            {speech.isListening && (
              <button type="button" className="audio-player-button" onClick={handleStopRecording}>
                <StopIcon />
                録音停止
              </button>
            )}
          </>
        );

      case 'composing':
        return (
          <button type="button" className="audio-player-button" disabled>
            <span className="processing-spinner" aria-hidden="true" />
            音声入力
          </button>
        );

      case 'composed':
        return (
          <div className="voice-reply-actions">
            <button type="button" className="audio-player-button" onClick={handleRestartRecording}>
              <MicIcon />
              音声入力
            </button>
            <button type="button" className="audio-player-button" onClick={handleConfirm}>
              <CheckIcon />
              確認
            </button>
            <SplitActionButton
              actions={[
                { key: 'send', label: '送信', icon: <SendIcon />, onClick: handleSend },
                { key: 'draft', label: '下書き', icon: <DraftIcon />, onClick: handleSaveDraft },
              ]}
            />
          </div>
        );

      case 'confirming':
        return (
          // biome-ignore lint/a11y/useKeyWithClickEvents: overlay dismiss is supplementary to the 戻る button
          // biome-ignore lint/a11y/noStaticElementInteractions: overlay backdrop click to dismiss
          <div className="dialog-overlay" onClick={handleBack}>
            {/* biome-ignore lint/a11y/useKeyWithClickEvents: stopPropagation prevents overlay dismiss */}
            <div
              role="dialog"
              aria-label="送信確認"
              className="dialog voice-reply-confirm-dialog"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="voice-reply-preview-field">
                <span className="voice-reply-preview-label">宛先:</span>
                <span>{email.senderEmail}</span>
              </div>
              <div className="voice-reply-preview-field">
                <span className="voice-reply-preview-label">件名:</span>
                <span>{displaySubject}</span>
              </div>
              <div className="voice-reply-preview-field">
                <span className="voice-reply-preview-label">本文:</span>
                <p>{composedBody}</p>
              </div>
              <div className="dialog-actions">
                <button type="button" className="audio-player-button" onClick={handleBack}>
                  <BackIcon />
                  戻る
                </button>
                <SplitActionButton
                  actions={[
                    { key: 'send', label: '送信', icon: <SendIcon />, onClick: handleSend },
                    { key: 'draft', label: '下書き', icon: <DraftIcon />, onClick: handleSaveDraft },
                  ]}
                />
              </div>
            </div>
          </div>
        );

      case 'sending':
        return (
          <button type="button" className="audio-player-button" disabled>
            <span className="processing-spinner" aria-hidden="true" />
            送信
          </button>
        );

      case 'draft_saving':
        return (
          <button type="button" className="audio-player-button" disabled>
            <span className="processing-spinner" aria-hidden="true" />
            下書き
          </button>
        );

      case 'sent':
        return (
          <button type="button" className="audio-player-button" disabled>
            <SendIcon />
            送信済み
          </button>
        );

      case 'error':
        return (
          <>
            <p className="voice-reply-error" role="alert">
              {error}
            </p>
            {errorType === 'send' ? (
              <button type="button" className="audio-player-button" onClick={handleRetrySend}>
                <SendIcon />
                再送信
              </button>
            ) : errorType === 'draft' ? (
              <button type="button" className="audio-player-button" onClick={handleSaveDraft}>
                <DraftIcon />
                下書き再試行
              </button>
            ) : (
              <button
                type="button"
                className="audio-player-button"
                onClick={handleRestartRecording}
              >
                <MicIcon />
                音声入力
              </button>
            )}
          </>
        );
    }
  };

  const renderFallbackUI = () => (
    <>
      <p className="voice-reply-fallback">
        音声入力は利用できません。テキスト入力をご利用ください。
      </p>
      <textarea
        className="voice-reply-textarea"
        value={fallbackText}
        onChange={(e) => setFallbackText(e.target.value)}
        placeholder="返信内容を入力してください..."
      />
      {fallbackText.trim() && (
        <button type="button" className="audio-player-button" onClick={handleFallbackCompose}>
          <SendIcon />
          清書
        </button>
      )}
    </>
  );

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
          {hasDraft && !email.repliedAt && (
            <span className="draft-saved-badge">下書き保存済み</span>
          )}
          {email.repliedAt && email.replySource && (
            <span className={`reply-source-badge reply-source-badge--${email.replySource}`}>
              {email.replySource === 'togenuki' ? 'TogeNukiより返信' : 'Gmailより返信'}
            </span>
          )}
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
                {!email.repliedAt && renderReplyUI()}
                {email.repliedAt && email.replyBody && (
                  <>
                    <button
                      type="button"
                      className="audio-player-button"
                      onClick={() => setShowSentReply(true)}
                    >
                      <CheckIcon />
                      確認
                    </button>
                    {showSentReply && (
                      // biome-ignore lint/a11y/useKeyWithClickEvents: overlay dismiss is supplementary
                      // biome-ignore lint/a11y/noStaticElementInteractions: overlay backdrop click to dismiss
                      <div className="dialog-overlay" onClick={() => setShowSentReply(false)}>
                        {/* biome-ignore lint/a11y/useKeyWithClickEvents: stopPropagation prevents overlay dismiss */}
                        <div
                          role="dialog"
                          aria-label="送信内容確認"
                          className="dialog voice-reply-confirm-dialog"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div className="voice-reply-preview-field">
                            <span className="voice-reply-preview-label">宛先:</span>
                            <span>{email.senderEmail}</span>
                          </div>
                          <div className="voice-reply-preview-field">
                            <span className="voice-reply-preview-label">件名:</span>
                            <span>{email.replySubject || ''}</span>
                          </div>
                          <div className="voice-reply-preview-field">
                            <span className="voice-reply-preview-label">本文:</span>
                            <p>{email.replyBody}</p>
                          </div>
                          <div className="dialog-actions">
                            <button
                              type="button"
                              className="audio-player-button"
                              onClick={() => setShowSentReply(false)}
                            >
                              <CloseIcon />
                              閉じる
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
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

function MicIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5z" />
      <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M6 6h12v12H6z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
    </svg>
  );
}

function BackIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z" />
    </svg>
  );
}

function DraftIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M21.99 8c0-.72-.37-1.35-.94-1.7L12 1 2.95 6.3C2.38 6.65 2 7.28 2 8v10c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2l-.01-10zM12 13L3.74 7.84 12 3l8.26 4.84L12 13z" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
    </svg>
  );
}
