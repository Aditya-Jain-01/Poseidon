function label(value, limit = 28) {
  return value.length > limit ? `${value.slice(0, limit - 1)}…` : value;
}

export default function BrainGraph({ graph, selectedId, onSelect }) {
  const { sources, topics, edges } = graph;
  const height = Math.max(300, Math.max(sources.length, topics.length) * 64 + 80);
  const position = (index, count) => 50 + (index + 1) * (height - 100) / (count + 1);
  const sourceY = new Map(sources.map((source, index) => [source.id, position(index, sources.length)]));
  const topicY = new Map(topics.map((topic, index) => [topic.id, position(index, topics.length)]));

  if (!edges.length) {
    return <p className="brain-graph-empty">No connections yet. Add a note to <code>raw</code> and scan it to build the graph.</p>;
  }

  return (
    <div className="brain-graph-scroll">
      <svg className="brain-graph-svg" viewBox={`0 0 900 ${height}`} role="img" aria-label={`${sources.length} source notes connected to ${topics.length} topics`}>
        <text className="brain-graph-column" x="54" y="36">SOURCE NOTES</text>
        <text className="brain-graph-column" x="578" y="36">TOPICS</text>
        {edges.map((edge) => {
          const from = sourceY.get(edge.source_id);
          const to = topicY.get(edge.node_id);
          if (from == null || to == null) return null;
          return <path className={`brain-graph-edge ${selectedId === edge.node_id ? 'active' : ''}`} key={`${edge.source_id}-${edge.node_id}`} d={`M 320 ${from} C 455 ${from}, 455 ${to}, 580 ${to}`} />;
        })}
        {sources.map((source) => <g key={source.id} transform={`translate(54 ${sourceY.get(source.id)})`}>
          <circle className="brain-graph-source-dot" r="7" />
          <text className="brain-graph-source-label" x="18" y="5"><title>{source.path}</title>{label(source.path)}</text>
        </g>)}
        {topics.map((topic) => <g
          className={`brain-graph-topic ${selectedId === topic.id ? 'active' : ''}`}
          key={topic.id}
          transform={`translate(580 ${topicY.get(topic.id)})`}
          role="button"
          tabIndex={0}
          aria-label={`Open topic ${topic.title}`}
          onClick={() => onSelect(topic.id)}
          onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(topic.id); } }}
        >
          <rect x="-14" y="-23" width="292" height="46" rx="10" />
          <circle r="6" />
          <text x="20" y="5"><title>{topic.title}</title>{label(topic.title, 29)}</text>
        </g>)}
      </svg>
    </div>
  );
}
