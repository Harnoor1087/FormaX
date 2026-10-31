import { useEffect, useState } from 'react';
import { OUTPUT_TYPES } from './options';
import {
  approveOutput,
  exportPresentationPptx,
  fetchVideoDownload,
  getOutputVideoJob,
  getVideoJob,
  recordExport,
  startVideoGeneration,
  updateOutput,
} from './api';

const labelOf = (id) => OUTPUT_TYPES.find((o) => o.id === id)?.label ?? id;

function toText(o) {
  const points = (o.key_points || []).filter(Boolean).map((p) => `• ${p}`);
  return [o.title, '', o.summary, '', ...points, '', o.body].join('\n').trim();
}

function toMarkdown(o) {
  const points = (o.key_points || []).filter(Boolean).map((point) => `- ${point}`);
  return [
    `# ${o.title}`,
    '',
    o.summary,
    '',
    ...(points.length ? ['## Key points', ...points, ''] : []),
    '## Draft',
    '',
    o.body,
  ].join('\n').trim();
}

function download(name, content) {
  const url = URL.createObjectURL(new Blob([content], { type: 'text/plain;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function Card({ initial, accessToken, canReview }) {
  const [o, setO] = useState(initial);
  const [editing, setEditing] = useState(false);
  const [approved, setApproved] = useState(initial.review_status === 'approved');
  const [saving, setSaving] = useState(false);
  const [exportingPptx, setExportingPptx] = useState(false);
  const [error, setError] = useState('');
  const [videoJob, setVideoJob] = useState(null);
  const [videoError, setVideoError] = useState('');
  const [videoPollError, setVideoPollError] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const set = (k, v) => {
    setO({ ...o, [k]: v });
    setApproved(false);
    setVideoJob(null);
    setVideoError('');
    setVideoPollError('');
    setVideoUrl('');
  };

  useEffect(() => {
    if (o.output_type !== 'video_package' || !o.output_id || !approved || !canReview) return undefined;
    let active = true;
    getOutputVideoJob(o.output_id, accessToken)
      .then((job) => { if (active) setVideoJob(job); })
      .catch((err) => { if (active) setVideoError(err.message); });
    return () => { active = false; };
  }, [o.output_id, o.output_type, approved, canReview, accessToken]);

  useEffect(() => {
    if (!videoJob || !['processing', 'downloading'].includes(videoJob.status) || videoPollError) return undefined;
    let active = true;
    const timer = window.setTimeout(async () => {
      try {
        const updated = await getVideoJob(videoJob.video_job_id, accessToken);
        if (active) setVideoJob(updated);
      } catch (err) {
        if (active) setVideoPollError(err.message);
      }
    }, 5000);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [videoJob, accessToken, videoPollError]);

  useEffect(() => {
    if (!videoJob || videoJob.status !== 'completed' || !accessToken) return undefined;
    let active = true;
    let objectUrl = '';
    fetchVideoDownload(videoJob.video_job_id, accessToken)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setVideoUrl(objectUrl);
      })
      .catch((err) => { if (active) setVideoError(err.message); });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [videoJob, accessToken]);

  async function renderVideo() {
    setVideoError('');
    setVideoPollError('');
    setVideoUrl('');
    setVideoJob({ status: 'starting' });
    try {
      setVideoJob(await startVideoGeneration(o.output_id, accessToken));
    } catch (err) {
      setVideoJob(null);
      setVideoError(err.message);
    }
  }

  async function finishEditing() {
    if (o.output_id) {
      setSaving(true);
      setError('');
      try {
        const updated = await updateOutput(o.output_id, {
          title: o.title,
          summary: o.summary,
          key_points: o.key_points,
          body: o.body,
        }, accessToken);
        setO(updated);
      } catch (err) {
        setError(err.message);
        setSaving(false);
        return;
      }
      setSaving(false);
    }
    setEditing(false);
  }

  async function approve() {
    setError('');
    try {
      if (o.output_id) await approveOutput(o.output_id, accessToken);
      setApproved(true);
    } catch (err) {
      setError(err.message);
    }
  }

  async function exportDraft(format) {
    setError('');
    try {
      if (o.output_id) await recordExport(o.output_id, accessToken);
      const formats = {
        txt: toText(o),
        md: toMarkdown(o),
        json: JSON.stringify({
          output_type: o.output_type,
          title: o.title,
          summary: o.summary,
          key_points: o.key_points,
          body: o.body,
          validation: o.validation,
        }, null, 2),
      };
      download(`${o.output_type}.${format}`, formats[format]);
    } catch (err) {
      setError(err.message);
    }
  }

  async function exportPptx() {
    setError('');
    setExportingPptx(true);
    try {
      const { blob, filename } = await exportPresentationPptx(o.output_id, accessToken);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    } finally {
      setExportingPptx(false);
    }
  }

  return (
    <article className="out">
      <header>
        <h3>{labelOf(o.output_type)}</h3>
        <div className="out-tags">
          {o.generation_mode === 'template_fallback' && <span className="tag fallback">Template fallback</span>}
          <span className={`tag${approved ? ' ok' : ''}`}>{approved ? 'Approved' : 'Draft'}</span>
        </div>
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

      {o.validation && (
        <div className="validation" aria-label="Output validation">
          <span className={o.validation.schema_valid ? 'valid' : 'invalid'}>
            Schema {o.validation.schema_valid ? 'passed' : 'failed'}
          </span>
          <span className={o.validation.consistency_valid ? 'valid' : 'invalid'}>
            Source consistency {o.validation.consistency_valid ? 'passed' : 'failed'}
          </span>
          {!!o.validation.issues?.length && (
            <ul>{o.validation.issues.map((issue, i) => <li key={i}>{issue}</li>)}</ul>
          )}
        </div>
      )}
      {error && <p className="err" role="alert">{error}</p>}

      {o.output_type === 'video_package' && o.output_id && canReview && (
        <section className="video-render" aria-label="Video rendering">
          <div>
            <strong>Optional MP4 video</strong>
            <p className="note">
              This draft is a script and storyboard, not a video file. After approval, Veo can render
              one 8-second 720p landscape MP4 with audio. Rendering requires available Google Veo
              quota and may take a few minutes.
            </p>
          </div>
          <button
            className="ghost"
            disabled={!approved || ['starting', 'processing', 'downloading', 'completed'].includes(videoJob?.status)}
            onClick={renderVideo}
          >
            {videoJob?.status === 'completed'
              ? 'MP4 ready'
              : ['starting', 'processing', 'downloading'].includes(videoJob?.status)
                ? 'Rendering…'
                : videoJob?.status === 'stale' || videoJob?.status === 'failed'
                  ? 'Render MP4 again'
                  : 'Render 8-second MP4'}
          </button>
          {!approved && <p className="note">Approve this video brief before rendering.</p>}
          {videoJob?.status === 'processing' && <p role="status">Veo is rendering your clip…</p>}
          {videoJob?.status === 'downloading' && <p role="status">Saving the generated MP4…</p>}
          {videoJob?.status === 'failed' && <p className="err" role="alert">{videoJob.error}</p>}
          {videoJob?.status === 'stale' && <p className="note">The brief changed after this render. Approve the revised brief to generate a new clip.</p>}
          {videoError && <p className="err" role="alert">{videoError}</p>}
          {videoPollError && (
            <div>
              <p className="err" role="alert">{videoPollError}</p>
              <button className="ghost" onClick={() => setVideoPollError('')}>Retry status check</button>
            </div>
          )}
          {videoJob?.status === 'completed' && videoUrl && (
            <div className="video-preview">
              <video controls playsInline src={videoUrl}>Your browser does not support video playback.</video>
              <a className="button-link" href={videoUrl} download={`formax-${videoJob.video_job_id.slice(0, 8)}.mp4`}>
                Download MP4
              </a>
            </div>
          )}
        </section>
      )}

      <footer>
        <button className="ghost" disabled={saving || !canReview} onClick={() => (editing ? finishEditing() : setEditing(true))}>
          {saving ? 'Saving…' : editing ? 'Save changes' : 'Edit'}
        </button>
        <button className="ghost" disabled={!canReview || editing || approved} onClick={approve}>Approve</button>
        <div className="export-actions" aria-label="Export formats">
          {o.output_type === 'presentation' && (
            <button
              disabled={!canReview || !approved || exportingPptx}
              title={approved ? 'Download a PowerPoint presentation' : 'Approve the draft before exporting'}
              onClick={exportPptx}
            >
              {exportingPptx ? 'Creating PPTX…' : 'PPTX'}
            </button>
          )}
          <button disabled={!canReview || !approved} title={approved ? '' : 'Approve the draft before exporting'} onClick={() => exportDraft('txt')}>TXT</button>
          <button disabled={!canReview || !approved} title={approved ? '' : 'Approve the draft before exporting'} onClick={() => exportDraft('md')}>Markdown</button>
          <button disabled={!canReview || !approved} title={approved ? '' : 'Approve the draft before exporting'} onClick={() => exportDraft('json')}>JSON</button>
        </div>
      </footer>
    </article>
  );
}

export default function Results({ outputs, accessToken = '', canReview = true, generationMode = '' }) {
  return (
    <section className="results" aria-labelledby="res-h">
      <h2 id="res-h">Review drafts</h2>
      <p className="note">
        {generationMode === 'gemini'
          ? 'AI-assisted draft. Review all claims before approval; nothing is published automatically.'
          : generationMode === 'template_fallback'
              ? 'Gemini is temporarily busy. Template drafts are English and may only partially reflect tone, objective, or detail settings; review them before approval.'
          : generationMode === 'template'
              ? 'Template draft (Gemini is not configured). Templates are English and may only partially reflect tone, objective, or detail settings; review and edit before approval.'
            : generationMode === 'mixed'
                ? 'Some drafts use Gemini and others use English templates, which may only partially reflect tone, objective, or detail settings. Review all claims before approval.'
            : 'Demo data only. Nothing is published automatically.'}
      </p>
      <div className="outs">{outputs.map((o, i) => (
        <Card key={o.output_id || `${o.output_type}-${i}`} initial={o} accessToken={accessToken} canReview={canReview} />
      ))}</div>
    </section>
  );
}
