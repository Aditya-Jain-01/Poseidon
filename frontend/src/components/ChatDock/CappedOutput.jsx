import React, { useState } from 'react';
import { headTailCap } from './headTailCap';

export function CappedOutput({ value }) {
  const [expanded, setExpanded] = useState(false);
  const text = JSON.stringify(value, null, 2) ?? 'null';
  const { head, hidden, tail, hiddenCount } = headTailCap(text);

  if (!hiddenCount) return <pre className="receipt-json-code">{text}</pre>;

  return (
    <div className="receipt-json-code receipt-capped-output">
      <pre>{head}</pre>
      <button type="button" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded}>
        {expanded ? 'Hide' : 'Show'} {hiddenCount} middle lines
      </button>
      {expanded && <pre>{hidden}</pre>}
      <pre>{tail}</pre>
    </div>
  );
}
