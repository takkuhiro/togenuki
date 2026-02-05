/**
 * Gmail OAuth callback page.
 * Handles the OAuth callback and exchanges the code for tokens.
 */
import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";

type CallbackStatus = "processing" | "success" | "error";

export function GmailCallback() {
  const { idToken, checkGmailStatus } = useAuth();
  const [status, setStatus] = useState<CallbackStatus>("processing");
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    const handleCallback = async () => {
      // Get the authorization code from URL
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get("code");
      const error = urlParams.get("error");

      if (error) {
        setStatus("error");
        setErrorMessage(`Google認証エラー: ${error}`);
        return;
      }

      if (!code) {
        setStatus("error");
        setErrorMessage("認証コードが見つかりません");
        return;
      }

      if (!idToken) {
        setStatus("error");
        setErrorMessage("ログインが必要です");
        return;
      }

      try {
        // Exchange the code for tokens
        const response = await fetch("/api/auth/gmail/callback", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${idToken}`,
          },
          body: JSON.stringify({ code }),
        });

        if (response.ok) {
          setStatus("success");
          // Update Gmail connection status
          await checkGmailStatus();
          // Redirect to home after 2 seconds
          setTimeout(() => {
            window.location.href = "/";
          }, 2000);
        } else {
          const data = await response.json();
          setStatus("error");
          setErrorMessage(data.detail?.error || "トークン交換に失敗しました");
        }
      } catch (err) {
        setStatus("error");
        setErrorMessage("通信エラーが発生しました");
      }
    };

    if (idToken) {
      handleCallback();
    }
  }, [idToken, checkGmailStatus]);

  return (
    <div className="callback-container">
      <h1>Gmail連携</h1>
      {status === "processing" && <p>処理中...</p>}
      {status === "success" && (
        <div>
          <p style={{ color: "green" }}>Gmail連携が完了しました！</p>
          <p>ホーム画面に戻ります...</p>
        </div>
      )}
      {status === "error" && (
        <div>
          <p style={{ color: "red" }}>エラー: {errorMessage}</p>
          <a href="/">ホームに戻る</a>
        </div>
      )}
    </div>
  );
}
