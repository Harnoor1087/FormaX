import { useState } from 'react';
import { login } from './api';

const MOCK = import.meta.env.VITE_USE_MOCK === 'true';

export default function Login({ onSuccess, onBack }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(e) {
    e.preventDefault();
    setError('');
    if (!/^\S+@\S+\.\S+$/.test(email)) return setError('Enter a valid email address.');
    if (!password) return setError('Enter your password.');
    setBusy(true);
    try {
      onSuccess(await login(email.trim(), password));
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
          <p className="muted">Use your operator account to open the workspace.</p>

          <label className="field" htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@organisation.gov.in" />
          <label className="field" htmlFor="pw">Password</label>
          <input id="pw" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />

          {error && <p className="err" role="alert">{error}</p>}
          <button className="primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
          {MOCK && <p className="muted small">Demo mode: any valid email and password will work.</p>}
        </form>
      </main>
    </div>
  );
}
