import './App.css';
import { EmailList } from './components/EmailList';
import { useAuth } from './contexts/AuthContext';
import { ContactsPage } from './pages/ContactsPage';
import { GmailCallback } from './pages/GmailCallback';

function App() {
  const {
    user,
    isLoading,
    error,
    isGmailConnected,
    signInWithGoogle,
    signOut,
    connectGmail,
    checkGmailStatus,
  } = useAuth();

  // Simple routing: check if we're on the Gmail callback page
  const path = window.location.pathname;
  if (path === '/auth/gmail/callback') {
    return <GmailCallback />;
  }

  // Route to contacts management page
  if (path === '/contacts') {
    if (!user || !isGmailConnected) {
      // Redirect to home if not authenticated
      window.location.href = '/';
      return null;
    }
    return (
      <div className="app">
        <header className="app-header">
          <div className="header-content">
            <div className="header-title">
              <span className="header-icon">💖</span>
              <h1>TogeNuki</h1>
            </div>
            <div className="header-actions">
              <span className="user-email">{user.email}</span>
              <button type="button" onClick={signOut} className="logout-button-small">
                ログアウト
              </button>
            </div>
          </div>
        </header>
        <main className="main-content">
          <ContactsPage />
        </main>
      </div>
    );
  }

  const handleCheckGmailStatus = async () => {
    const connected = await checkGmailStatus();
    alert(`Gmail連携状態: ${connected ? '連携済み' : '未連携'}`);
  };

  if (isLoading) {
    return (
      <div className="app">
        <div className="loading-container">
          <h1>TogeNuki</h1>
          <p>読み込み中...</p>
        </div>
      </div>
    );
  }

  // Not logged in
  if (!user) {
    return (
      <div className="app">
        <div className="login-container">
          <h1>TogeNuki</h1>
          <p className="app-description">メールストレス軽減AIツール</p>
          {error && <p className="error-message">エラー: {error}</p>}
          <button type="button" onClick={signInWithGoogle} className="login-button">
            Googleでログイン
          </button>
        </div>
      </div>
    );
  }

  // Logged in but Gmail not connected
  if (!isGmailConnected) {
    return (
      <div className="app">
        <header className="app-header">
          <div className="header-content">
            <h1>TogeNuki</h1>
            <div className="header-actions">
              <button type="button" onClick={signOut} className="logout-button">
                ログアウト
              </button>
            </div>
          </div>
        </header>
        <main className="main-content">
          <div className="setup-container">
            <h2>Gmail連携が必要です</h2>
            <p>メールを読み込むためにGmail連携を行ってください。</p>
            <button type="button" onClick={connectGmail} className="gmail-button">
              Gmail連携
            </button>
            <button type="button" onClick={handleCheckGmailStatus} className="check-button">
              Gmail状態確認
            </button>
          </div>
        </main>
      </div>
    );
  }

  // Logged in and Gmail connected - show dashboard
  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="header-title">
            <span className="header-icon">💖</span>
            <h1>TogeNuki</h1>
          </div>
          <div className="header-actions">
            <a href="/contacts" className="nav-link">
              連絡先管理
            </a>
            <span className="user-email">{user.email}</span>
            <button type="button" onClick={signOut} className="logout-button-small">
              ログアウト
            </button>
          </div>
        </div>
      </header>

      <main className="main-content">
        <EmailList />
      </main>
    </div>
  );
}

export default App;
