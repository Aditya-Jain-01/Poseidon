import { useCallback, useEffect, useState } from 'react';
import { BrainCircuit, FileText, RefreshCw, Link2, Search, Stethoscope, Plus } from 'lucide-react';
import { fetchBrainStatus, fetchBrainNodes, fetchBrainGraph, fetchBrainNode, syncBrain, queryBrain, lintBrain, addBrainSource } from '../../api/brain';
import { lazy, Suspense } from 'react';
const BrainGraph = lazy(() => import('./BrainGraph'));
import './Brain.css';

export default function Brain() {
  const [status, setStatus] = useState(null);
  const [nodes, setNodes] = useState([]);
  const [graph, setGraph] = useState({ sources: [], topics: [], edges: [] });
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [health, setHealth] = useState(null);
  const [sourceTitle, setSourceTitle] = useState('');
  const [sourceText, setSourceText] = useState('');
  const [savedSource, setSavedSource] = useState('');

  const load = useCallback(async () => {
    const [nextStatus, nextNodes, nextGraph] = await Promise.all([fetchBrainStatus(), fetchBrainNodes(), fetchBrainGraph()]);
    setStatus(nextStatus);
    setNodes(nextNodes);
    setGraph(nextGraph);
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([fetchBrainStatus(), fetchBrainNodes(), fetchBrainGraph()])
      .then(([nextStatus, nextNodes, nextGraph]) => {
        if (active) { setStatus(nextStatus); setNodes(nextNodes); setGraph(nextGraph); }
      })
      .catch((err) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, []);

  const openNode = async (id) => {
    try {
      setError('');
      setSelected(await fetchBrainNode(id));
    } catch (err) {
      setError(err.message);
    }
  };

  const scan = async () => {
    setBusy(true);
    setError('');
    try {
      const nextResult = await syncBrain();
      setResult(nextResult);
      await load();
      if (selected) setSelected(await fetchBrainNode(selected.id));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const ask = async (event) => {
    event.preventDefault();
    if (question.trim().length < 3) return;
    setBusy(true);
    setError('');
    setAnswer(null);
    try {
      setAnswer(await queryBrain(question.trim()));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const checkHealth = async () => {
    setBusy(true);
    setError('');
    try {
      setHealth(await lintBrain());
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const addSource = async (event) => {
    event.preventDefault();
    if (!sourceTitle.trim() || !sourceText.trim()) return;
    setBusy(true);
    setError('');
    setSavedSource('');
    try {
      const saved = await addBrainSource(sourceTitle.trim(), sourceText.trim());
      setSavedSource(saved.path);
      setResult(saved.scan);
      setSourceTitle('');
      setSourceText('');
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="brain-page">
      <header className="brain-header">
        <div>
          <h1><BrainCircuit size={27} /> Brain</h1>
          <p>Ask your notes. Follow the evidence. Keep the original sources close.</p>
        </div>
        <button className="brain-scan" onClick={scan} disabled={busy || !status?.vault_exists}>
          <RefreshCw size={16} className={busy ? 'brain-spinning' : ''} /> {busy ? 'Scanning…' : 'Scan raw sources'}
        </button>
      </header>

      <div className="brain-vault">Local vault <code>{status?.vault_path || 'Loading…'}</code></div>
      {status && !status.vault_exists && <p className="brain-notice">Start the backend to create this vault, then open it in Obsidian.</p>}
      {error && <p className="brain-error" role="alert">{error}</p>}
      {result && <div className="brain-result" role="status">
        Processed {result.processed.length}, unchanged {result.unchanged.length}, failed {result.failed.length}.
        {result.failed.map((item) => <div key={item.path}><strong>{item.path}:</strong> {item.error}</div>)}
      </div>}
      {savedSource && <p className="brain-notice" role="status">Saved original note to <code>{savedSource}</code>.</p>}

      <details className="brain-add-source">
        <summary><span><Plus size={17} /> Add a source</span><small>Paste a note or excerpt into your local vault</small></summary>
        <form className="brain-source-form" onSubmit={addSource}>
          <input aria-label="Source title" placeholder="Source title" value={sourceTitle} onChange={(event) => setSourceTitle(event.target.value)} maxLength={100} />
          <textarea aria-label="Source text" placeholder="Paste the source text here" value={sourceText} onChange={(event) => setSourceText(event.target.value)} maxLength={23000} rows={4} />
          <button type="submit" disabled={busy || !sourceTitle.trim() || !sourceText.trim()}><Plus size={16} /> Add to Brain</button>
        </form>
      </details>

      <section className="brain-workflow" aria-label="Ask the brain">
        <div className="brain-workflow-heading">
          <div><h2>Ask your Brain</h2><p>Answers cite the source notes Poseidon used.</p></div>
          <button type="button" className="brain-scan" onClick={checkHealth} disabled={busy || !status?.vault_exists}>
            <Stethoscope size={16} /> Check health
          </button>
        </div>
        <form className="brain-question" onSubmit={ask}>
          <input aria-label="Question for the Brain" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What did we decide about the project?" maxLength={1000} />
          <button type="submit" disabled={busy || question.trim().length < 3 || nodes.length === 0}><Search size={16} /> Ask</button>
        </form>
        {answer && <div className="brain-answer" role="status">
          <p>{answer.answer}</p>
          {answer.sources.length > 0 && <div className="brain-citations"><strong>Sources</strong>
            {answer.sources.map((source) => <div key={source.chunk_id ?? `${source.path}-${source.title}`}><span>{source.path} · {source.title}{source.chunk_index != null ? ` · passage ${source.chunk_index + 1}` : ''}</span><blockquote>{source.evidence}</blockquote></div>)}
          </div>}
        </div>}
        {health && <div className="brain-health" role="status">
          <strong>Health check: {health.issues.length} issue{health.issues.length === 1 ? '' : 's'}</strong>
          <span>Checked {health.checked_sources} sources and {health.checked_topics} topics.</span>
          <span>Conflict check: {health.semantic_check}.</span>
          {health.issues.map((issue, index) => <div key={`${issue.kind}-${issue.path}-${index}`}>{issue.kind.replaceAll('_', ' ')}: {issue.path}{issue.reason ? ` — ${issue.reason}` : ''}</div>)}
        </div>}
      </section>

      <section className="brain-graph" aria-label="Brain graph">
        <div className="brain-graph-heading">
          <h2>Knowledge graph</h2>
          <span>{graph.sources.length} sources · {graph.topics.length} topics · {graph.edges.length} links</span>
        </div>
        <Suspense fallback={<p className="brain-graph-empty">Loading graph?</p>}><BrainGraph graph={graph} selectedId={selected?.id} onSelect={openNode} /></Suspense>
      </section>

      <div className="brain-body">
        <section className="brain-topics" aria-label="Brain topics">
          <h2>Topics <span>{nodes.length}</span></h2>
          {nodes.length === 0 && <p className="brain-empty">Add a note to <code>raw</code>, then scan to build your first topic.</p>}
          {nodes.map((node) => <button
            key={node.id}
            className={`brain-topic ${selected?.id === node.id ? 'selected' : ''}`}
            onClick={() => openNode(node.id)}
          >
            <span>{node.title}</span><small>{node.source_count} source{node.source_count === 1 ? '' : 's'}</small>
          </button>)}
        </section>

        <section className="brain-detail" aria-label="Topic details">
          {!selected ? <div className="brain-placeholder"><BrainCircuit size={35} /><p>Select a topic to inspect its sources and connections.</p></div> : <>
            <span className="brain-eyebrow">TOPIC</span>
            <h2>{selected.title}</h2>
            <p className="brain-file">Obsidian page: <code>wiki/{selected.file_name}</code></p>
            <h3>Source-backed notes</h3>
            {selected.sources.map((source) => <article className="brain-source" key={source.path}>
              <div className="brain-source-path"><FileText size={15} /> {source.path}</div>
              <p>{source.summary}</p>
              <blockquote>{source.evidence}</blockquote>
            </article>)}
            {selected.links.length > 0 && <><h3>Related topics</h3><div className="brain-links">
              {selected.links.map((link) => <button key={link.id} onClick={() => openNode(link.id)}><Link2 size={14} /> {link.title}</button>)}
            </div></>}
          </>}
        </section>
      </div>
    </div>
  );
}
