const I = (d) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{d}</svg>
);
const WandIcon = () => I(<><path d="M15 4V2M15 16v-2M8 9h2M20 9h2M17.8 11.8 19 13M17.8 6.2 19 5M12.2 6.2 11 5M3 21l9-9" /></>);
const ClockIcon = () => I(<><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5M12 7v5l3 2" /></>);
const ShieldIcon = () => I(<><path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z" /><path d="m9 12 2 2 4-4" /></>);

export function Sidebar() {
  return (
    <aside className="side">
      <div className="brand">
        <span className="logo" aria-hidden="true">↻</span>
        <div>
          <div className="name">formax<span>AI</span></div>
          <div className="mono tiny">Operational workspace</div>
        </div>
      </div>

      <div className="ws mono"><i className="dot" /> Secure workspace</div>

      <nav aria-label="Main">
        <div className="mono tiny navhead">Workspace</div>
        <a className="nav active" href="#" aria-current="page"><WandIcon /> Transform</a>
        <span className="nav off" aria-disabled="true"><ClockIcon /> History <em className="mono">Soon</em></span>
      </nav>

      <div className="side-foot">
        <div className="ground">
          <ShieldIcon />
          <div><strong>Source-grounded</strong><span>Every claim stays traceable.</span></div>
        </div>
        <div className="user">
          <span className="avatar">AO</span>
          <div><strong>Analyst Operator</strong><span>Operations team</span></div>
        </div>
      </div>
    </aside>
  );
}

export function TopBar({ mock }) {
  const date = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  return (
    <div className="topbar mono">
      <span className="crumbs">FormaX / <b>Transform</b></span>
      <span className="status">
        <i className={`dot${mock ? ' warn' : ''}`} />
        {mock ? 'Demo mode · mock data' : 'Connected to backend'}
        <span className="sep" />
        <span className="date">{date}</span>
      </span>
    </div>
  );
}
