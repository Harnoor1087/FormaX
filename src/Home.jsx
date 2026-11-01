import { OUTPUT_TYPES } from './options';

const FEATURES = [
  ['Structured controls, not prompts', 'Choose audience, tone, language, detail and objective from simple dropdowns. No prompt-writing skill needed.'],
  ['One source, many outputs', 'Produce an advisory, social posts, summaries and more from the same source in one run, so facts and tone stay consistent.'],
  ['Human in the loop', 'Every output is a draft. Operators edit and approve it before anything can be exported.'],
];
const STEPS = [
  ['Add your source', 'Upload a PDF, DOCX or TXT file, or paste text.'],
  ['Choose outputs', 'Select one or more formats and set the parameters.'],
  ['Generate drafts', 'All outputs are created from the same source in a single operation.'],
  ['Review and export', 'Edit, approve and export each draft.'],
];
const SECURITY = [
  ['Prompt-injection guardrails', 'Uploaded content is treated as untrusted data and filtered before it reaches the model.'],
  ['Sensitive-data screening', 'Outputs are checked so personal or classified details do not leak into a draft.'],
  ['Rate limiting and access control', 'Per-user limits and input caps protect availability and cost.'],
  ['Audit trail', 'Every stage is logged, recording which source produced which output.'],
];

export default function Home({ onSignIn }) {
  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="brand home-brand"><span className="logo" aria-hidden="true">↻</span><div className="name dark">formax<span>AI</span></div></div>
        <nav aria-label="Page sections" className="lp-links">
          <a href="#about">About</a><a href="#how">How it works</a><a href="#security">Security</a>
        </nav>
        <button onClick={onSignIn}>Sign in</button>
      </header>

      <section className="lp-hero">
        <div>
          <p className="mono eyebrow">Gen AI content transformation</p>
          <h1>One source. Every format. Reviewed before it ships.</h1>
          <p className="lead">FormaX AI turns a single report, article or prompt into advisories, social posts, summaries, decks and video packages, consistent across every channel and approved by a person.</p>
          <div className="cta">
            <button className="big" onClick={onSignIn}>Sign in to workspace</button>
            <a className="btn-ghost" href="#how">See how it works</a>
          </div>
        </div>
        <div className="flow" aria-hidden="true">
          <div className="flow-src"><span className="mono tiny">Source</span><strong>Threat intelligence report.pdf</strong></div>
          <div className="flow-arrow">↓</div>
          {['Advisory for field staff', 'Executive summary', 'LinkedIn post'].map((t) => (
            <div key={t} className="flow-out"><i className="dot" />{t}<span className="mono tiny">Draft</span></div>
          ))}
        </div>
      </section>

      <section id="about" className="lp-sec">
        <h2>What is FormaX AI?</h2>
        <p className="sub">Organisations often need to convert one body of information into several communication artefacts. Doing it by hand is slow and inconsistent. FormaX AI is a governed platform that does it in one step.</p>
        <div className="cards">
          {FEATURES.map(([t, d]) => <div key={t} className="lp-card"><h3>{t}</h3><p>{d}</p></div>)}
        </div>
        <p className="mono tiny formats">Supported outputs</p>
        <div className="chips">{OUTPUT_TYPES.map((o) => <span key={o.id} className="chip static">{o.label}</span>)}</div>
      </section>

      <section id="how" className="lp-sec alt">
        <h2>How it works</h2>
        <ol className="steps">
          {STEPS.map(([t, d], i) => <li key={t}><span className="mono num">0{i + 1}</span><h3>{t}</h3><p>{d}</p></li>)}
        </ol>
      </section>

      <section id="security" className="lp-sec">
        <h2>Security built into the pipeline</h2>
        <p className="sub">AI-specific risks are treated as a design concern, following the OWASP Top 10 for LLM Applications.</p>
        <div className="cards four">
          {SECURITY.map(([t, d]) => <div key={t} className="lp-card"><h3>{t}</h3><p>{d}</p></div>)}
        </div>
      </section>

      <footer className="lp-foot">
  <div className="foot-brand">
    <strong>formaxAI</strong>
    <span>Gen AI platform for automated content transformation.</span>
  </div>
  <nav aria-label="Footer" className="foot-links">
    <a href="#about">About       </a>
    <a href="#how">How it works       </a>
    <a href="#security">Security</a>
  </nav>
  <div className="foot-copy">© 2026 FormaX AI. All rights reserved.</div>
</footer>
    </div>
  );
}
