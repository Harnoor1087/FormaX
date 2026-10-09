import { useState } from 'react';
import { OUTPUT_TYPES, PARAMS, DEFAULTS } from './options';
import { extractText } from './extract';
import { generate } from './api';
import Results from './Results.jsx';
import { Sidebar, TopBar } from './Shell.jsx';

const MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

const MAX_CHARS = 50000;

export default function App() {
  const [file, setFile] = useState(null);
  const [text, setText] = useState('');
  const [extracting, setExtracting] = useState(false);
  const [srcError, setSrcError] = useState('');
  const [drag, setDrag] = useState(false);
  const [types, setTypes] = useState(['advisory']);
  const [params, setParams] = useState(DEFAULTS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [outputs, setOutputs] = useState(null);

  async function handleFile(f) {
    if (!f) return;
    setSrcError('');
    setFile(f);
    setText('');
    setExtracting(true);
    try {
      setText(await extractText(f));
    } catch (e) {
      setSrcError(e.message);
      setFile(null);
    } finally {
      setExtracting(false);
    }
  }

  function clearSource() {
    setFile(null);
    setText('');
    setSrcError('');
  }

  const toggleType = (id) =>
    setTypes((t) => (t.includes(id) ? t.filter((x) => x !== id) : [...t, id]));

  const tooLong = text.length > MAX_CHARS;
  const canGenerate = text.trim() && types.length && !extracting && !loading && !tooLong;

  async function onGenerate() {
    setError('');
    setLoading(true);
    setOutputs(null);
    const payload = {
      source_text: text.trim(),
      source_type: file ? 'file' : 'text',
      source_filename: file ? file.name : null,
      output_types: types,
      ...params,
    };
    try {
      const data = await generate(payload);
      setOutputs(data.outputs);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="shell">
      <Sidebar />
      <div className="main">
        <TopBar mock={MOCK} />
        <div className="content">
      <header className="top">
        <h1>FormaX AI</h1>
        <p>Add a source, choose the outputs, then review every draft before it leaves the platform.</p>
      </header>

      <main className="grid">
        <section className="panel" aria-labelledby="src-h">
          <h2 id="src-h">Source content</h2>

          <label
            className={`drop${drag ? ' over' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); handleFile(e.dataTransfer.files[0]); }}
          >
            <input type="file" accept=".pdf,.docx,.txt" onChange={(e) => { handleFile(e.target.files[0]); e.target.value = ''; }} />
            {extracting ? <strong>Reading {file?.name}…</strong> : file ? <strong>{file.name}</strong> : <strong>Drop a PDF, DOCX or TXT file here</strong>}
            <span>{file && !extracting ? 'Drop another file to replace it' : 'or click to browse (max 10 MB)'}</span>
          </label>
          {srcError && <p className="err" role="alert">{srcError}</p>}

          <label className="field" htmlFor="src-text">
            {file ? 'Extracted text (you can edit it)' : 'Or paste your text'}
          </label>
          <textarea
            id="src-text" rows={14} value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste an article, report or incident description…"
          />
          <div className="meta">
            <span className={tooLong ? 'bad' : ''}>{text.length.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters</span>
            {(text || file) && <button type="button" className="link" onClick={clearSource}>Clear source</button>}
          </div>
          {tooLong && <p className="err">The text is too long. Shorten it to {MAX_CHARS.toLocaleString()} characters or fewer.</p>}
        </section>

        <section className="panel" aria-labelledby="set-h">
          <h2 id="set-h">What to create</h2>
          <div className="chips" role="group" aria-label="Output types">
            {OUTPUT_TYPES.map((o) => (
              <label key={o.id} className={`chip${types.includes(o.id) ? ' on' : ''}`}>
                <input type="checkbox" checked={types.includes(o.id)} onChange={() => toggleType(o.id)} />
                {o.label}
              </label>
            ))}
          </div>
          {!types.length && <p className="err">Select at least one output type.</p>}

          <h2 className="sub">Settings</h2>
          <div className="params">
            {PARAMS.map((p) => (
              <div key={p.key} className="param">
                <label htmlFor={p.key} className="field">{p.label}</label>
                <select id={p.key} value={params[p.key]} onChange={(e) => setParams({ ...params, [p.key]: e.target.value })}>
                  {p.options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
            ))}
          </div>

          <button className="primary" disabled={!canGenerate} onClick={onGenerate}>
            {loading ? 'Generating…' : `Generate ${types.length > 1 ? `${types.length} drafts` : 'draft'}`}
          </button>
          {error && <p className="err" role="alert">{error}</p>}
        </section>
      </main>

      {outputs && <Results outputs={outputs} />}
        </div>
      </div>
    </div>
  );
}
