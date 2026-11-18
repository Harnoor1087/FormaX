import { useState } from 'react';
import { login } from './api';

const DEMO = import.meta.env.VITE_MOCK_AUTH === 'true';

export default function Login({ onSuccess, onBack }) {
  const [token, setToken] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(e) {
    e.preventDefault();
    setError('');
    if (!DEMO && !token.trim()) return setError('Enter your access token.');
    setBusy(true);
    try {
      onSuccess(await login(token.trim()));
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <aside className="auth-side">
        <div className="brand"><span className="logo" aria-hidden="true">↻</span>
          <div><div className="name">formax<span>AI</span></div><div className="mono tiny">Operational workspace</div></div>
        </div>
        <div>
          <h2>Every claim stays traceable.</h2>
          <p>Sign in to turn a single source into reviewed, consistent communication drafts.</p>
        </div>
        <div className="mono tiny">Human-reviewed · Audit-logged</div>
      </aside>

      <main className="auth-main">
        <form className="auth-card" onSubmit={submit} noValidate>
          <button type="button" className="link" onClick={onBack}>← Back to home</button>
          <h1>Sign in</h1>
          <p className="muted">Enter your access token to open the workspace.</p>

          <label className="field" htmlFor="tok">Access token</label>
          <input id="tok" type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} />

          {error && <p className="err" role="alert">{error}</p>}
          <button className="primary" disabled={busy}>{busy ? 'Checking…' : 'Sign in'}</button>
          {DEMO && <p className="muted small">Demo mode: any value works.</p>}
        </form>
      </main>
    </div>
  );
}