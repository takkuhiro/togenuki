import './App.css';
import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom';
import { EmailList } from './components/EmailList';
import { useAuth } from './contexts/AuthContext';
import { ContactsPage } from './pages/ContactsPage';
import { GmailCallback } from './pages/GmailCallback';

/**
 * Layout with shared header for authenticated pages.
 */
function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, signOut } = useAuth();

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="header-title">
            <span className="header-icon">💖</span>
            <h1>TogeNuki</h1>
          </div>
          <div className="header-actions">
            <Link to="/contacts" className="nav-link">
              連絡先管理
            </Link>
            <span className="user-email">{user?.email}</span>
            <button type="button" onClick={signOut} className="logout-button-small">
              ログアウト
            </button>
          </div>
        </div>
      </header>
      <main className="main-content">{children}</main>
    </div>
  );
}

/**
 * Guard that requires authentication and Gmail connection.
 * Redirects to landing page if not authenticated or Gmail not connected.
 */
function RequireGmail({ children }: { children: React.ReactNode }) {
  const { user, isGmailConnected, isLoading } = useAuth();

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

  if (!user || !isGmailConnected) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

/**
 * Landing page: login / Gmail connection flow.
 * Redirects to /emails if already fully connected.
 */
function LandingPage() {
  const { user, isLoading, error, isGmailConnected, signInWithGoogle, signOut, connectGmail, checkGmailStatus } =
    useAuth();

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

  // Already fully connected -> redirect to emails
  if (user && isGmailConnected) {
    return <Navigate to="/emails" replace />;
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
  const handleCheckGmailStatus = async () => {
    const connected = await checkGmailStatus();
    alert(`Gmail連携状態: ${connected ? '連携済み' : '未連携'}`);
  };

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

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route
          path="/emails"
          element={
            <RequireGmail>
              <AppLayout>
                <EmailList />
              </AppLayout>
            </RequireGmail>
          }
        />
        <Route
          path="/contacts"
          element={
            <RequireGmail>
              <AppLayout>
                <ContactsPage />
              </AppLayout>
            </RequireGmail>
          }
        />
        <Route path="/auth/gmail/callback" element={<GmailCallback />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
