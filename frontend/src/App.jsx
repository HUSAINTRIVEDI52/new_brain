import { useState, useEffect } from 'react';
import { authService } from './api/auth';
import Layout from './components/Layout';
import MemoryFeed from './components/MemoryFeed';
import Chronology from './components/Chronology';
import Oracle from './components/Oracle';
import Studio from './components/Studio';
import './App.css';

function App() {
  const [isLogin, setIsLogin] = useState(true);
  const [view, setView] = useState('feed'); // 'feed' or 'timeline'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [user, setUser] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (authService.isAuthenticated()) {
      setUser({ email: authService.getUserEmail() });
    }
  }, []);

  const handleAuth = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let data;
      if (isLogin) {
        data = await authService.login(email, password);
      } else {
        data = await authService.register(email, password, name);
      }
      setUser({ email: data.email });
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Authentication failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    authService.logout();
    setUser(null);
    setEmail('');
    setPassword('');
    setName('');
    setView('feed'); // Reset view on logout
  };

  if (user) {
    return (
      <Layout onLogout={handleLogout} userEmail={user.email}>
        <div className="manuscript-entry">
          <Studio onEntrySaved={() => setRefreshKey(prev => prev + 1)} />
          <hr className="faint-hr" style={{ margin: '4rem 0' }} />

          <Oracle />

          <header className="entry-head">
            <div className="view-selector">
              <button
                className={`button-minimal ${view === 'feed' ? 'active' : ''}`}
                onClick={() => setView('feed')}
              >
                The Nexus
              </button>
              <span className="dot-sep">·</span>
              <button
                className={`button-minimal ${view === 'timeline' ? 'active' : ''}`}
                onClick={() => setView('timeline')}
              >
                The Chronology
              </button>
            </div>
            <p className="entry-date">{view === 'feed' ? 'CURRENT ARCHIVE' : 'HISTORICAL RECORD'}</p>
            <h2 className="entry-title">{view === 'feed' ? 'The Nexus' : 'The Chronology'}</h2>
          </header>

          {view === 'feed' ? (
            <MemoryFeed key={refreshKey} />
          ) : (
            <Chronology key={refreshKey} />
          )}
        </div>
      </Layout>
    );
  }

  return (
    <div className="auth-canvas">
      <div className="auth-box fade-in">
        <header className="auth-header">
          <h1 className="logo">Second Brain</h1>
          <p className="subtitle sienna-italic">
            {isLogin ? "Resuming the manuscript." : "Beginning an archive."}
          </p>
        </header>

        <form onSubmit={handleAuth} className="auth-form">
          <div className="form-fields">
            {!isLogin && (
              <div className="form-group">
                <label className="mono-label">Full Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter your name..."
                  autoComplete="name"
                  required
                />
              </div>
            )}

            <div className="form-group">
              <label className="mono-label">Email Address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@archive.ai"
                autoComplete="email"
                required
              />
            </div>

            <div className="form-group">
              <label className="mono-label">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete={isLogin ? "current-password" : "new-password"}
                required
              />
            </div>
          </div>

          {error && <p className="error-text">{"[!WARN] " + error}</p>}

          <div className="auth-actions">
            <div className="action-divider">
              <span className="dot-sep">...</span>
            </div>

            <button type="submit" className="button-primary" disabled={loading}>
              {loading ? 'Consulting the Oracle...' : (isLogin ? 'Consult the Oracle →' : 'Bind the Manuscript')}
            </button>

            <nav className="auth-nav">
              <p className="toggle-auth">
                {isLogin ? "New here? " : "Already an author? "}
                <span onClick={() => setIsLogin(!isLogin)} className="toggle-link">
                  {isLogin ? 'Begin your journey' : 'Resume writing'}
                </span>
              </p>
              {!isLogin && (
                <p className="legal-note">
                  Your thoughts are kept in a private vault. By beginning, you agree to our terms of ink and paper.
                </p>
              )}
            </nav>
          </div>
        </form>
      </div>
    </div>
  );
}

export default App;
