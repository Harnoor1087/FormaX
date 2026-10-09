import { useState } from 'react';
import { OUTPUT_TYPES } from './options';

const labelOf = (id) => OUTPUT_TYPES.find((o) => o.id === id)?.label ?? id;

function toText(o) {
  const points = (o.key_points || []).filter(Boolean).map((p) => `• ${p}`);
  return [o.title, '', o.summary, '', ...points, '', o.body].join('\n').trim();
}

function download(name, content) {
  const url = URL.createObjectURL(new Blob([content], { type: 'text/plain;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function Card({ initial }) {
  const [o, setO] = useState(initial);
  const [editing, setEditing] = useState(false);
  const [approved, setApproved] = useState(false);
  const set = (k, v) => { setO({ ...o, [k]: v }); setApproved(false); }; // any edit needs re-approval

  return (
    <article className="out">
      <header>
        <h3>{labelOf(o.output_type)}</h3>
        <span className={`tag${approved ? ' ok' : ''}`}>{approved ? 'Approved' : 'Draft'}</span>
      </header>

      {editing ? (
        <div className="edit">
          <label className="field">Title<input value={o.title || ''} onChange={(e) => set('title', e.target.value)} /></label>
          <label className="field">Summary<textarea rows={3} value={o.summary || ''} onChange={(e) => set('summary', e.target.value)} /></label>
          <label className="field">Key points (one per line)
            <textarea rows={4} value={(o.key_points || []).join('\n')} onChange={(e) => set('key_points', e.target.value.split('\n'))} />
          </label>
          <label className="field">Body<textarea rows={8} value={o.body || ''} onChange={(e) => set('body', e.target.value)} /></label>
        </div>
      ) : (
        <div className="read">
          <h4>{o.title}</h4>
          {o.summary && <p className="lead">{o.summary}</p>}
          {o.key_points?.some(Boolean) && <ul>{o.key_points.filter(Boolean).map((p, i) => <li key={i}>{p}</li>)}</ul>}
          <p className="body">{o.body}</p>
        </div>
      )}

      <footer>
        <button className="ghost" onClick={() => setEditing(!editing)}>{editing ? 'Done editing' : 'Edit'}</button>
        <button className="ghost" disabled={editing || approved} onClick={() => setApproved(true)}>Approve</button>
        <button disabled={!approved} title={approved ? '' : 'Approve the draft before exporting'} onClick={() => download(`${o.output_type}.txt`, toText(o))}>Export</button>
      </footer>
    </article>
  );
}

export default function Results({ outputs }) {
  return (
    <section className="results" aria-labelledby="res-h">
      <h2 id="res-h">Review drafts</h2>
      <p className="note">Nothing is published automatically. Edit, approve, then export each draft.</p>
      <div className="outs">{outputs.map((o, i) => <Card key={`${o.output_type}-${i}`} initial={o} />)}</div>
    </section>
  );
}
