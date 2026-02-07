/**
 * Voice reply panel component for voice input, AI compose, and email sending.
 * Requirements: 1.2-1.7, 2.4-2.6, 3.3, 3.5, 4.1-4.6, 5.1-5.3
 */

import { useCallback, useState } from 'react';
import { composeReply, sendReply } from '../api/reply';
import { useAuth } from '../contexts/AuthContext';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';

type ReplyPhase =
  | 'idle'
  | 'recording'
  | 'editing'
  | 'composing'
  | 'composed'
  | 'previewing'
  | 'sending'
  | 'sent'
  | 'error';

interface VoiceReplyPanelProps {
  emailId: string;
  senderEmail: string;
  senderName: string | null;
  subject: string | null;
}

export function VoiceReplyPanel({ emailId, senderEmail, subject }: VoiceReplyPanelProps) {
  const { idToken } = useAuth();
  const speech = useSpeechRecognition();

  const [phase, setPhase] = useState<ReplyPhase>('idle');
  const [rawText, setRawText] = useState('');
  const [composedBody, setComposedBody] = useState('');
  const [composedSubject, setComposedSubject] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleStartRecording = useCallback(() => {
    speech.startListening();
    setPhase('recording');
    setError(null);
  }, [speech]);

  const handleStopRecording = useCallback(() => {
    speech.stopListening();
    setPhase('editing');
  }, [speech]);

  const handleCompose = useCallback(async () => {
    if (!idToken) return;

    const textToCompose = rawText || speech.transcript;
    if (!textToCompose.trim()) return;

    setPhase('composing');
    setError(null);

    try {
      const result = await composeReply(idToken, emailId, { rawText: textToCompose });
      setComposedBody(result.composedBody);
      setComposedSubject(result.composedSubject);
      setPhase('composed');
    } catch (err) {
      setError(err instanceof Error ? err.message : '清書に失敗しました');
      setPhase('editing');
    }
  }, [idToken, emailId, rawText, speech.transcript]);

  const handleRecompose = useCallback(async () => {
    if (!idToken) return;

    const textToCompose = rawText || speech.transcript;
    if (!textToCompose.trim()) return;

    setPhase('composing');
    setError(null);

    try {
      const result = await composeReply(idToken, emailId, { rawText: textToCompose });
      setComposedBody(result.composedBody);
      setComposedSubject(result.composedSubject);
      setPhase('composed');
    } catch (err) {
      setError(err instanceof Error ? err.message : '清書に失敗しました');
      setPhase('composed');
    }
  }, [idToken, emailId, rawText, speech.transcript]);

  const handleConfirm = useCallback(() => {
    setPhase('previewing');
  }, []);

  const handleBack = useCallback(() => {
    setPhase('composed');
  }, []);

  const handleSend = useCallback(async () => {
    if (!idToken) return;

    setPhase('sending');
    setError(null);

    try {
      await sendReply(idToken, emailId, {
        composedBody,
        composedSubject,
      });
      setPhase('sent');
    } catch (err) {
      setError(err instanceof Error ? err.message : '送信に失敗しました');
      setPhase('error');
    }
  }, [idToken, emailId, composedBody, composedSubject]);

  const handleRetryRecording = useCallback(() => {
    speech.resetTranscript();
    setError(null);
    setPhase('idle');
  }, [speech]);

  const handleRetrySend = useCallback(async () => {
    await handleSend();
  }, [handleSend]);

  // Sync transcript from speech recognition to rawText
  const currentText = rawText || speech.transcript;

  const displaySubject = composedSubject || `Re: ${subject || ''}`;

  // --- Render ---

  // Sent phase
  if (phase === 'sent') {
    return (
      <div data-testid="voice-reply-panel" className="voice-reply-panel">
        <p className="voice-reply-success">送信完了しました</p>
      </div>
    );
  }

  // Previewing phase
  if (phase === 'previewing') {
    return (
      <div data-testid="voice-reply-panel" className="voice-reply-panel">
        <div className="voice-reply-preview">
          <div className="voice-reply-preview-field">
            <span className="voice-reply-preview-label">宛先:</span>
            <span>{senderEmail}</span>
          </div>
          <div className="voice-reply-preview-field">
            <span className="voice-reply-preview-label">件名:</span>
            <span>{displaySubject}</span>
          </div>
          <div className="voice-reply-preview-field">
            <span className="voice-reply-preview-label">本文:</span>
            <p>{composedBody}</p>
          </div>
        </div>
        <div className="voice-reply-actions">
          <button type="button" onClick={handleBack}>
            戻る
          </button>
          <button type="button" onClick={handleSend}>
            送信
          </button>
        </div>
      </div>
    );
  }

  // Sending phase
  if (phase === 'sending') {
    return (
      <div data-testid="voice-reply-panel" className="voice-reply-panel">
        <div className="voice-reply-loading">
          <span className="processing-spinner" aria-hidden="true" />
          <p>送信中...</p>
        </div>
      </div>
    );
  }

  // Error phase (send failure)
  if (phase === 'error') {
    return (
      <div data-testid="voice-reply-panel" className="voice-reply-panel">
        <p className="voice-reply-error" role="alert">
          {error}
        </p>
        <button type="button" onClick={handleRetrySend}>
          再送信
        </button>
      </div>
    );
  }

  // Composing phase (loading)
  if (phase === 'composing') {
    return (
      <div data-testid="voice-reply-panel" className="voice-reply-panel">
        <div className="voice-reply-loading">
          <span className="processing-spinner" aria-hidden="true" />
          <p>清書中...</p>
        </div>
      </div>
    );
  }

  // Composed phase
  if (phase === 'composed') {
    return (
      <div data-testid="voice-reply-panel" className="voice-reply-panel">
        <textarea
          className="voice-reply-composed-textarea"
          value={composedBody}
          onChange={(e) => setComposedBody(e.target.value)}
        />
        <div className="voice-reply-actions">
          <button type="button" onClick={handleRecompose}>
            再清書
          </button>
          <button type="button" onClick={handleConfirm}>
            確認
          </button>
          <button type="button" onClick={handleSend}>
            送信
          </button>
        </div>
      </div>
    );
  }

  // Idle / Recording / Editing phases
  return (
    <div data-testid="voice-reply-panel" className="voice-reply-panel">
      {!speech.isAvailable && (
        <p className="voice-reply-fallback">
          音声入力は利用できません。テキスト入力をご利用ください。
        </p>
      )}

      {speech.error && (
        <div className="voice-reply-speech-error">
          <p role="alert">{speech.error}</p>
          <button type="button" onClick={handleRetryRecording}>
            再試行
          </button>
        </div>
      )}

      {error && (
        <p className="voice-reply-error" role="alert">
          {error}
        </p>
      )}

      {speech.isAvailable && !speech.isListening && (
        <button type="button" onClick={handleStartRecording}>
          音声入力
        </button>
      )}

      {speech.isListening && (
        <>
          <button type="button" onClick={handleStopRecording}>
            録音停止
          </button>
          {speech.interimTranscript && (
            <p className="voice-reply-interim">{speech.interimTranscript}</p>
          )}
        </>
      )}

      <textarea
        className="voice-reply-textarea"
        value={currentText}
        onChange={(e) => setRawText(e.target.value)}
        placeholder="返信内容を入力してください..."
      />

      {currentText.trim() && (
        <button type="button" onClick={handleCompose}>
          清書
        </button>
      )}
    </div>
  );
}
