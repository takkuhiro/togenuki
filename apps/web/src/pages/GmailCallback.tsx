/**
 * Gmail OAuth callback page.
 * Handles the OAuth callback and exchanges the code for tokens.
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

type CallbackStatus = 'processing' | 'success' | 'error';

export function GmailCallback() {
  const { idToken, checkGmailStatus } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState<CallbackStatus>('processing');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    const handleCallback = async () => {
      // Get the authorization code from URL
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      const error = urlParams.get('error');

      if (error) {
        setStatus('error');
        setErrorMessage(`Google認証エラー: ${error}`);
        return;
      }

      if (!code) {
        setStatus('error');
        setErrorMessage('認証コードが見つかりません');
        return;
      }

      if (!idToken) {
        setStatus('error');
        setErrorMessage('ログインが必要です');
        return;
      }

      try {
        // Step 1: Exchange the code for tokens
        const callbackResponse = await fetch('/api/auth/gmail/callback', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${idToken}`,
          },
          body: JSON.stringify({ code }),
        });

        if (!callbackResponse.ok) {
          const data = await callbackResponse.json();
          setStatus('error');
          setErrorMessage(data.detail?.error || 'トークン交換に失敗しました');
          return;
        }

        // Step 2: Setup Gmail Watch for push notifications
        const watchResponse = await fetch('/api/gmail/watch', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${idToken}`,
          },
        });

        if (!watchResponse.ok) {
          const data = await watchResponse.json();
          setStatus('error');
          setErrorMessage(data.detail || 'Gmail Watch設定に失敗しました');
          return;
        }

        const watchData = await watchResponse.json();
        if (!watchData.success) {
          setStatus('error');
          setErrorMessage(watchData.error || 'Gmail Watch設定に失敗しました');
          return;
        }

        // Step 3: Success - update status and redirect
        setStatus('success');
        await checkGmailStatus();
        setTimeout(() => {
          navigate('/emails', { replace: true });
        }, 2000);
      } catch (error) {
        setStatus('error');
        setErrorMessage('通信エラーが発生しました');
        console.error('Gmail callback error:', error);
      }
    };

    if (idToken) {
      handleCallback();
    }
  }, [idToken, checkGmailStatus, navigate]);

  return (
    <div className="callback-container">
      <h1>Gmail連携</h1>
      {status === 'processing' && (
        <div>
          <p>処理中...</p>
          <p style={{ fontSize: '0.9em', color: '#666' }}>
            Gmail連携とメール通知の設定を行っています
          </p>
        </div>
      )}
      {status === 'success' && (
        <div>
          <p style={{ color: 'green' }}>Gmail連携が完了しました！</p>
          <p>メール一覧に移動します...</p>
        </div>
      )}
      {status === 'error' && (
        <div>
          <p style={{ color: 'red' }}>エラー: {errorMessage}</p>
          <Link to="/">ホームに戻る</Link>
        </div>
      )}
    </div>
  );
}
