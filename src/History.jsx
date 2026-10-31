import { useEffect, useState } from 'react';
import { getGeneration, listGenerations } from './api';
import Results from './Results.jsx';

export default function History({ accessToken, role }) {
  const [generations, setGenerations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!accessToken) {
      setGenerations([]);
      setSelected(null);
      setError('');
      setLoading(false);
      return undefined;
    }
    let active = true;
    listGenerations(accessToken)
      .then((items) => { if (active) setGenerations(items); })
      .catch((err) => { if (active) setError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [accessToken]);

  async function openGeneration(generationId) {
    setSelected({ loading: true });
    setError('');
    try {
      setSelected(await getGeneration(generationId, accessToken));
    } catch (err) {
      setSelected(null);
      setError(err.message);
    }
  }

  return (
    <section className="history">
      <header className="top">
        <h1>Generation history</h1>
        <p>Review saved drafts, validation results, and approval status.</p>
      </header>
      {!accessToken && <p className="note">Connect with an operator or reviewer token to view saved generations.</p>}
      {loading && accessToken && <p>Loading saved generations…</p>}
      {error && <p className="err" role="alert">{error}</p>}
      {!loading && !error && accessToken && generations.length === 0 && (
        <p className="note">No saved generations yet. Generate drafts with the backend connected to see them here.</p>
      )}
      {accessToken && generations.length > 0 && (
        <div className="history-list">
          {generations.map((item) => (
            <button
              className="history-item"
              key={item.generation_id}
              onClick={() => openGeneration(item.generation_id)}
            >
              <span>
                <strong>{new Date(item.created_at).toLocaleString()}</strong>
                <small>{item.request_id} · {item.generation_mode} · {item.output_count} draft{item.output_count === 1 ? '' : 's'}</small>
              </span>
              <span className="mono">{item.approved_count}/{item.output_count} approved</span>
            </button>
          ))}
        </div>
      )}
      {selected?.loading && <p>Loading generation…</p>}
      {selected?.outputs && (
        <Results
          outputs={selected.outputs}
          accessToken={accessToken}
          canReview={role === 'reviewer'}
          generationMode={selected.generation_mode}
        />
      )}
      {selected?.events?.length > 0 && (
        <section className="audit-events">
          <h2>Review audit trail</h2>
          <ul>
            {selected.events.map((event, index) => (
              <li key={`${event.action}-${index}`}>
                <strong>{event.action}</strong>
                <span>{new Date(event.created_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  );
}
