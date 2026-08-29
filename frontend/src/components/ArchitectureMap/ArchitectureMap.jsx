import React from 'react';
import './ArchitectureMap.css';

export function ArchitectureMap({ activeNodes = [] }) {
  return (
    <div className="architecture-map-container">
      <svg
        viewBox="0 0 920 600"
        className="architecture-map-svg"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          {/* Arrow markers */}
          <marker
            id="arrowhead"
            markerWidth="8"
            markerHeight="8"
            refX="7"
            refY="4"
            orient="auto"
          >
            <polygon points="0 1, 8 4, 0 7" fill="var(--accent)" />
          </marker>

          <marker
            id="arrowhead-reply"
            markerWidth="8"
            markerHeight="8"
            refX="7"
            refY="4"
            orient="auto"
          >
            <polygon points="0 1, 8 4, 0 7" fill="var(--teal)" />
          </marker>

          <marker
            id="arrowhead-bi"
            markerWidth="8"
            markerHeight="8"
            refX="7"
            refY="4"
            orient="auto"
          >
            <polygon points="0 1, 8 4, 0 7" fill="var(--muted-dim)" />
          </marker>

          <marker
            id="arrowhead-bi-start"
            markerWidth="8"
            markerHeight="8"
            refX="1"
            refY="4"
            orient="auto"
          >
            <polygon points="8 1, 0 4, 8 7" fill="var(--muted-dim)" />
          </marker>

          {/* Gradients */}
          <linearGradient id="gatewayGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#111a30" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#0d1526" stopOpacity="0.9" />
          </linearGradient>

          <linearGradient id="harnessGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#131e38" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#0a0f1e" stopOpacity="0.7" />
          </linearGradient>
        </defs>

        {/* 1. GATEWAY BOX */}
        <g className={`arch-node arch-box arch-box-gateway ${activeNodes.includes('gateway') ? 'active' : ''}`}>
          <rect
            x="170"
            y="20"
            width="580"
            height="64"
            rx="10"
            className="arch-rect node-gateway"
          />
          <text x="460" y="46" textAnchor="middle" className="arch-title node-title-gateway">
            GATEWAY
          </text>
          <text x="460" y="66" textAnchor="middle" className="arch-subtitle">
            Web / CLI Channels → InboundEvent
          </text>
        </g>

        {/* Connections: Gateway <-> Harness */}
        <g className="arch-connector">
          {/* Inbound Event Arrow */}
          <line
            x1="380"
            y1="84"
            x2="380"
            y2="128"
            className="arch-line line-event"
            markerEnd="url(#arrowhead)"
          />
          <text x="368" y="110" textAnchor="end" className="arch-edge-label accent">
            event
          </text>

          {/* Outbound Reply Arrow */}
          <line
            x1="540"
            y1="128"
            x2="540"
            y2="88"
            className="arch-line line-reply"
            markerEnd="url(#arrowhead-reply)"
          />
          <text x="552" y="110" textAnchor="start" className="arch-edge-label teal">
            reply
          </text>
        </g>

        {/* 2. HARNESS (OUTER BOX) */}
        <g className={`arch-node arch-box arch-box-harness ${activeNodes.includes('harness') ? 'active' : ''}`}>
          <rect
            x="120"
            y="130"
            width="680"
            height="186"
            rx="12"
            className="arch-rect node-harness"
          />
          <text x="144" y="156" className="arch-group-title">
            HARNESS · EPHEMERAL AGENT RUN
          </text>

          {/* 2a. LLM Q&A Agent */}
          <g className={`arch-node arch-box arch-box-agent ${activeNodes.includes('agent') ? 'active' : ''}`}>
            <rect
              x="150"
              y="172"
              width="230"
              height="94"
              rx="8"
              className="arch-rect node-inner node-agent"
            />
            <text x="265" y="206" textAnchor="middle" className="arch-title">
              LLM Q&amp;A Agent
            </text>
            <text x="265" y="228" textAnchor="middle" className="arch-subtitle">
              Single-turn Q&amp;A (Gemma)
            </text>
            <text x="265" y="246" textAnchor="middle" className="arch-badge">
              Active Agent
            </text>
          </g>

          {/* Bidirectional Arrow Agent <-> Tools */}
          <line
            x1="384"
            y1="219"
            x2="476"
            y2="219"
            className="arch-line line-bidirectional"
            markerEnd="url(#arrowhead-bi)"
            markerStart="url(#arrowhead-bi-start)"
          />

          {/* 2b. Agentic Tools */}
          <g className={`arch-node arch-box arch-box-tools ${activeNodes.includes('tools') ? 'active' : ''}`}>
            <rect
              x="480"
              y="172"
              width="290"
              height="94"
              rx="8"
              className="arch-rect node-inner node-tools"
            />
            <text x="625" y="198" textAnchor="middle" className="arch-title">
              Agentic Tools
            </text>
            <text x="625" y="222" textAnchor="middle" className="arch-subtitle">
              calendar · notes · CRM
            </text>
            <g className="not-registered-group">
              <text x="625" y="244" textAnchor="middle" className="arch-tool-denied">
                terminal — NOT REG.
              </text>
              <line x1="540" y1="240" x2="710" y2="240" className="arch-strikethrough" />
            </g>
          </g>

          {/* Guardrails footer */}
          <text x="460" y="296" textAnchor="middle" className="arch-guardrail-text">
            Guardrails: max iterations · max tool calls · execution timeout
          </text>
        </g>

        {/* 3. ARROWS TO MEMORY TIERS */}
        <g className="arch-connector">
          <line
            x1="220"
            y1="316"
            x2="220"
            y2="356"
            className="arch-line line-down"
            markerEnd="url(#arrowhead)"
          />
          <line
            x1="460"
            y1="316"
            x2="460"
            y2="356"
            className="arch-line line-down"
            markerEnd="url(#arrowhead)"
          />
          <line
            x1="700"
            y1="316"
            x2="700"
            y2="356"
            className="arch-line line-down"
            markerEnd="url(#arrowhead)"
          />
        </g>

        {/* 4. MEMORY TIERS */}
        {/* Procedural Memory */}
        <g className={`arch-node arch-box arch-box-procedural ${activeNodes.includes('procedural') ? 'active' : ''}`}>
          <rect
            x="120"
            y="360"
            width="200"
            height="80"
            rx="8"
            className="arch-rect node-memory"
          />
          <text x="220" y="394" textAnchor="middle" className="arch-title">
            Procedural Memory
          </text>
          <text x="220" y="416" textAnchor="middle" className="arch-subtitle">
            Rules · Workflows
          </text>
        </g>

        {/* Semantic Memory */}
        <g className={`arch-node arch-box arch-box-semantic ${activeNodes.includes('semantic') ? 'active' : ''}`}>
          <rect
            x="360"
            y="360"
            width="200"
            height="80"
            rx="8"
            className="arch-rect node-memory"
          />
          <text x="460" y="394" textAnchor="middle" className="arch-title">
            Semantic Memory
          </text>
          <text x="460" y="416" textAnchor="middle" className="arch-subtitle">
            Knowledge · Vectors
          </text>
        </g>

        {/* Episodic Memory */}
        <g className={`arch-node arch-box arch-box-episodic ${activeNodes.includes('episodic') ? 'active' : ''}`}>
          <rect
            x="600"
            y="360"
            width="200"
            height="80"
            rx="8"
            className="arch-rect node-memory"
          />
          <text x="700" y="394" textAnchor="middle" className="arch-title">
            Episodic Memory
          </text>
          <text x="700" y="416" textAnchor="middle" className="arch-subtitle">
            Logs · Experiences
          </text>
        </g>

        {/* 5. CONNECTORS TO SUMMARIZER AGENT */}
        <g className="arch-connector">
          <line
            x1="460"
            y1="440"
            x2="460"
            y2="488"
            className="arch-line line-down"
            markerEnd="url(#arrowhead)"
          />
          <path
            d="M 700 440 L 700 465 L 530 465 L 530 488"
            fill="none"
            className="arch-line line-down"
            markerEnd="url(#arrowhead)"
          />
        </g>

        {/* 6. BOTTOM ROW: LLM OPS & SUMMARIZER AGENT */}
        {/* LLM OPS */}
        <g className={`arch-node arch-box arch-box-llmops ${activeNodes.includes('llmops') ? 'active' : ''}`}>
          <rect
            x="120"
            y="492"
            width="200"
            height="76"
            rx="8"
            className="arch-rect node-ops"
          />
          <text x="220" y="522" textAnchor="middle" className="arch-title">
            LLM OPS
          </text>
          <text x="220" y="544" textAnchor="middle" className="arch-subtitle">
            Trace → Eval → Gate
          </text>
        </g>

        {/* Summarizer Agent */}
        <g className={`arch-node arch-box arch-box-summarizer ${activeNodes.includes('summarizer') ? 'active' : ''}`}>
          <rect
            x="360"
            y="492"
            width="240"
            height="76"
            rx="8"
            className="arch-rect node-summarizer"
          />
          <text x="480" y="522" textAnchor="middle" className="arch-title">
            Summarizer Agent
          </text>
          <text x="480" y="544" textAnchor="middle" className="arch-subtitle">
            Memory Synthesis Loop
          </text>
        </g>
      </svg>
    </div>
  );
}

export default ArchitectureMap;
