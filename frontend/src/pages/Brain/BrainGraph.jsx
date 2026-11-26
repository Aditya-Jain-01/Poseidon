import { useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Maximize2, Minus, Plus, Search } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

const nodeId = (type, id) => `${type}:${id}`;
const short = (value, max = 28) => value.length > max ? `${value.slice(0, max - 1)}…` : value;
const sourceName = (path) => path.split('/').pop().replace(/\.(md|txt)$/i, '');
const idOf = (endpoint) => typeof endpoint === 'object' ? endpoint.id : endpoint;

function makeData(graph, showSources) {
  const sourceEdges = graph.edges || [];
  const bySource = new Map();
  sourceEdges.forEach(({ source_id, node_id }) => {
    if (!bySource.has(source_id)) bySource.set(source_id, []);
    bySource.get(source_id).push(node_id);
  });
  const pairs = new Set();
  bySource.forEach((ids) => ids.forEach((first, index) => ids.slice(index + 1)
    .forEach((second) => pairs.add([first, second].sort().join('|')))));
  const links = [
    ...[...pairs].map((pair) => {
      const [first, second] = pair.split('|');
      return { source: nodeId('topic', first), target: nodeId('topic', second), kind: 'related' };
    }),
    ...(showSources ? sourceEdges.map(({ source_id, node_id }) => ({
      source: nodeId('source', source_id), target: nodeId('topic', node_id), kind: 'evidence',
    })) : []),
  ];
  const nodes = [
    ...(graph.topics || []).map((topic) => ({ id: nodeId('topic', topic.id), rawId: topic.id, label: topic.title, kind: 'topic' })),
    ...(showSources ? (graph.sources || []).map((source) => ({ id: nodeId('source', source.id), rawId: source.id,
      label: sourceName(source.path), fullLabel: source.path, kind: 'source' })) : []),
  ];
  const degree = new Map(nodes.map((node) => [node.id, 0]));
  const neighbors = new Map(nodes.map((node) => [node.id, new Set()]));
  links.forEach(({ source, target }) => {
    degree.set(source, (degree.get(source) || 0) + 1);
    degree.set(target, (degree.get(target) || 0) + 1);
    neighbors.get(source)?.add(target);
    neighbors.get(target)?.add(source);
  });
  nodes.forEach((node) => { node.degree = degree.get(node.id) || 0; });
  return { nodes, links, neighbors };
}

export default function BrainGraph({ graph, selectedId, onSelect }) {
  const { theme } = useTheme();
  const containerRef = useRef(null);
  const graphRef = useRef(null);
  const [width, setWidth] = useState(900);
  const [query, setQuery] = useState('');
  const [showSources, setShowSources] = useState(true);
  const [hoveredId, setHoveredId] = useState(null);
  const [zoom, setZoom] = useState(1);
  const data = useMemo(() => makeData(graph, showSources), [graph, showSources]);
  const search = query.trim().toLowerCase();
  const focusId = hoveredId || (selectedId ? nodeId('topic', selectedId) : null);
  const palette = theme === 'dark'
    ? { bg: '#252626', topic: '#8eaee0', source: '#d3d3cc', text: '#f1f1ed', edge: '#777a80' }
    : { bg: '#fbfaf7', topic: '#2860a4', source: '#767775', text: '#242525', edge: '#a4a6a2' };

  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(300, Math.floor(entry.contentRect.width))));
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    const instance = graphRef.current;
    if (!instance) return;
    instance.d3Force('charge')?.strength(-190);
    instance.d3Force('link')?.distance((link) => link.kind === 'related' ? 105 : 78);
    instance.d3Force('center')?.strength?.(.08);
    instance.d3ReheatSimulation();
  }, [data]);

  if (!(graph.edges || []).length) return <p className="brain-graph-empty">No connections yet. Add a note to <code>raw</code> and scan it to build the graph.</p>;

  const active = (node) => focusId === node.id || (search && node.label.toLowerCase().includes(search));
  const dimmed = (node) => (focusId && !active(node) && !data.neighbors.get(focusId)?.has(node.id)) || (search && !active(node) && !focusId);
  const drawNode = (node, ctx, scale) => {
    const radius = (node.kind === 'topic' ? 5 : 3.5) + Math.min(9, Math.sqrt(node.degree) * 2.2);
    ctx.beginPath(); ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
    ctx.fillStyle = node.kind === 'topic' ? palette.topic : palette.source;
    ctx.globalAlpha = dimmed(node) ? .16 : 1;
    ctx.fill();
    if (active(node)) { ctx.lineWidth = 2 / scale; ctx.strokeStyle = palette.text; ctx.stroke(); }
    const showLabel = scale > 1.25 || active(node) || data.nodes.length <= 12;
    if (showLabel) {
      const fontSize = 12 / Math.max(.75, Math.min(scale, 1.7));
      ctx.font = `${node.kind === 'topic' ? '600' : '400'} ${fontSize}px Segoe UI, sans-serif`;
      ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      ctx.lineWidth = 3 / scale; ctx.strokeStyle = palette.bg;
      ctx.strokeText(short(node.label), node.x, node.y + radius + 6);
      ctx.fillStyle = palette.text; ctx.fillText(short(node.label), node.x, node.y + radius + 6);
    }
    ctx.globalAlpha = 1;
  };

  return <div className="brain-network" ref={containerRef}>
    <div className="brain-network-toolbar">
      <label className="brain-network-search"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a note or topic" aria-label="Find a note or topic" /></label>
      <button type="button" className={showSources ? 'is-on' : ''} aria-pressed={showSources} onClick={() => setShowSources((value) => !value)}>Sources</button>
      <div className="brain-network-tools" aria-label="Graph controls">
        <button type="button" onClick={() => graphRef.current?.zoom(Math.max(.4, graphRef.current.zoom() / 1.3), 250)} aria-label="Zoom out"><Minus size={16} /></button>
        <button type="button" onClick={() => graphRef.current?.zoomToFit(400, 90)} aria-label="Fit graph to view"><Maximize2 size={16} /></button>
        <button type="button" onClick={() => graphRef.current?.zoom(Math.min(5, graphRef.current.zoom() * 1.3), 250)} aria-label="Zoom in"><Plus size={16} /></button>
      </div>
    </div>
    <ForceGraph2D ref={graphRef} graphData={data} width={width} height={Math.min(620, Math.max(420, width * .62))}
      backgroundColor={palette.bg} nodeCanvasObject={drawNode} nodePointerAreaPaint={(node, color, ctx) => { ctx.fillStyle = color; ctx.beginPath(); ctx.arc(node.x, node.y, 14, 0, Math.PI * 2); ctx.fill(); }}
      linkColor={(link) => focusId && idOf(link.source) !== focusId && idOf(link.target) !== focusId ? `${palette.edge}26` : palette.edge}
      linkWidth={(link) => focusId && (idOf(link.source) === focusId || idOf(link.target) === focusId) ? 2 : 1}
      linkLineDash={(link) => link.kind === 'related' ? [3, 4] : null}
      onNodeHover={(node) => setHoveredId(node?.id || null)}
      onNodeClick={(node) => { if (node.kind === 'topic') onSelect(node.rawId); else setHoveredId(node.id); }}
      nodeLabel={(node) => node.fullLabel || node.label}
      onZoom={({ k }) => setZoom(k)}
      onEngineStop={() => graphRef.current?.zoomToFit(350, 90)}
      cooldownTicks={120} />
    <div className="brain-network-legend"><span><i className="topic" />Topic</span><span><i className="source" />Source</span><span>{data.nodes.length} nodes · {zoom.toFixed(1)}× · drag nodes to explore</span></div>
  </div>;
}
