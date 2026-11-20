import { useState, useEffect } from 'react';

export default function TokenManager({ accessToken }) {
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [newToken, setNewToken] = useState(null);

  // Form state
  const [tokenName, setTokenName] = useState('');
  const [role, setRole] = useState('operator');
  const [expires, setExpires] = useState('');

  useEffect(() => {
    loadTokens();
  }, []);

  async function loadTokens() {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/v1/tokens', {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!res.ok) throw new Error('Failed to load tokens');
      const data = await res.json();
      setTokens(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function createToken(e) {
    e.preventDefault();
    setError('');
    setNewToken(null);

    if (!tokenName.trim()) {
      setError('Token name is required');
      return;
    }

    setCreating(true);
    try {
      const body = {
        token_name: tokenName.trim(),
        role,
      };

      if (expires) {
        body.expires_in_days = parseInt(expires);
      }

      const res = await fetch('/api/v1/tokens', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to create token');
      }

      const data = await res.json();
      setNewToken(data);
      setTokenName('');
      setRole('operator');
      setExpires('');
      loadTokens();
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  }

  async function revokeToken(tokenId, tokenName) {
    if (!confirm(`Revoke token "${tokenName}"? This cannot be undone.`)) {
      return;
    }

    try {
      const res = await fetch(`/api/v1/tokens/${tokenId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      if (!res.ok) throw new Error('Failed to revoke token');
      loadTokens();
    } catch (err) {
      setError(err.message);
    }
  }

  function copyToken() {
    navigator.clipboard.writeText(newToken.token_value);
    alert('Token copied to clipboard!');
  }

  if (loading) return <div className="panel"><p>Loading tokens...</p></div>;

  return (
    <div className="token-manager">
      <header className="top">
        <h1>Token Management</h1>
        <p>Create and manage API tokens for operators and reviewers.</p>
      </header>

      {error && <div className="err" role="alert">{error}</div>}

      {newToken && (
        <div className="panel" style={{ background: '#f0fdf4', border: '2px solid #22c55e' }}>
          <h2>✅ Token Created Successfully</h2>
          <p className="muted">Save this token securely. It will not be shown again.</p>
          
          <div className="field-group">
            <label className="field">Token Value</label>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="text"
                value={newToken.token_value}
                readOnly
                style={{ flex: 1, fontFamily: 'monospace', fontSize: '0.9rem' }}
              />
              <button type="button" onClick={copyToken} className="secondary">
                Copy
              </button>
            </div>
          </div>

          <div className="meta">
            <span><strong>Name:</strong> {newToken.token_name}</span>
            <span><strong>Role:</strong> {newToken.role}</span>
            {newToken.expires_at && <span><strong>Expires:</strong> {new Date(newToken.expires_at).toLocaleDateString()}</span>}
          </div>

          <button type="button" onClick={() => setNewToken(null)} className="link">
            Close
          </button>
        </div>
      )}

      <div className="grid">
        <section className="panel">
          <h2>Create New Token</h2>
          <form onSubmit={createToken}>
            <label className="field" htmlFor="token-name">Token Name</label>
            <input
              id="token-name"
              type="text"
              value={tokenName}
              onChange={(e) => setTokenName(e.target.value)}
              placeholder="e.g., Production Operator Token"
              required
            />

            <label className="field" htmlFor="token-role">Role</label>
            <select
              id="token-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="operator">Operator (generate only)</option>
              <option value="reviewer">Reviewer (full access)</option>
            </select>

            <label className="field" htmlFor="token-expires">Expires In (days, optional)</label>
            <input
              id="token-expires"
              type="number"
              min="1"
              max="365"
              value={expires}
              onChange={(e) => setExpires(e.target.value)}
              placeholder="Leave empty for no expiration"
            />

            <button type="submit" className="primary" disabled={creating}>
              {creating ? 'Creating...' : 'Create Token'}
            </button>
          </form>
        </section>

        <section className="panel">
          <h2>Active Tokens ({tokens.filter(t => t.is_active).length})</h2>
          {tokens.length === 0 ? (
            <p className="muted">No tokens created yet.</p>
          ) : (
            <div className="token-list">
              {tokens.map((token) => (
                <div key={token.token_id} className={`token-card ${!token.is_active ? 'revoked' : ''}`}>
                  <div className="token-header">
                    <strong>{token.token_name}</strong>
                    <span className={`badge ${token.role}`}>{token.role}</span>
                  </div>
                  
                  <div className="token-meta">
                    <span className="mono tiny">ID: {token.token_id.slice(0, 8)}...</span>
                    <span className="tiny">
                      Created: {new Date(token.created_at).toLocaleDateString()}
                    </span>
                    {token.last_used_at && (
                      <span className="tiny">
                        Last used: {new Date(token.last_used_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>

                  {token.expires_at && (
                    <div className="tiny muted">
                      Expires: {new Date(token.expires_at).toLocaleDateString()}
                    </div>
                  )}

                  {token.is_active && (
                    <button
                      type="button"
                      className="link danger"
                      onClick={() => revokeToken(token.token_id, token.token_name)}
                    >
                      Revoke
                    </button>
                  )}

                  {!token.is_active && (
                    <span className="tiny muted">❌ Revoked</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

