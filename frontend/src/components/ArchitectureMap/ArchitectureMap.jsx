import React from 'react';
import './ArchitectureMap.css';

export function ArchitectureMap({
  activeNodes = [],
  activePaths = [],
  modelName = '',
  agentName = 'poseidon',
  toolNames = [],
}) {
  const isPathActive = (path) => activePaths.includes(path);
  const displayModel = modelName ? modelName.slice(0, 34) : 'Configured model';
  const displayAgent = `${agentName.charAt(0).toUpperCase()}${agentName.slice(1)} Agent`;
  const displayTools = toolNames.length > 0
    ? toolNames.join(' · ').slice(0, 42)
    : 'No tool executed';

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
            <polygon points="0 1, 8 4, 0 7" fill="context-stroke" />
          </marker>

          <marker
            id="arrowhead-reply"
            markerWidth="8"
            markerHeight="8"
            refX="7"
            refY="4"
            orient="auto"
          >
            <polygon points="0 1, 8 4, 0 7" fill="context-stroke" />
          </marker>

          <marker
            id="arrowhead-bi"
            markerWidth="8"
            markerHeight="8"
            refX="7"
            refY="4"
            orient="auto"
          >
            <polygon points="0 1, 8 4, 0 7" fill="context-stroke" />
          </marker>

          <marker
            id="arrowhead-bi-start"
            markerWidth="8"
            markerHeight="8"
            refX="1"
            refY="4"
            orient="auto"
          >
            <polygon points="8 1, 0 4, 8 7" fill="context-stroke" />
          </marker>

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
            Channels → InboundEvent
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
            className={`arch-line line-event ${isPathActive('gateway-harness') ? 'active' : ''}`}
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
            className={`arch-line line-reply ${isPathActive('gateway-harness') ? 'active' : ''}`}
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
            HARNESS · WORKING MEMORY · AGENT RUN
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
              {displayAgent}
            </text>
            <text x="265" y="228" textAnchor="middle" className="arch-subtitle">
              {displayModel}
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
            className={`arch-line line-bidirectional ${isPathActive('agent-tools') ? 'active' : ''}`}
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
              {displayTools}
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
            className={`arch-line line-down ${isPathActive('harness-procedural') ? 'active' : ''}`}
            markerEnd="url(#arrowhead)"
          />
          <line
            x1="460"
            y1="316"
            x2="460"
            y2="356"
            className={`arch-line line-down ${isPathActive('harness-semantic') ? 'active' : ''}`}
            markerEnd="url(#arrowhead)"
          />
          <line
            x1="700"
            y1="316"
            x2="700"
            y2="356"
            className={`arch-line line-down ${isPathActive('harness-episodic') ? 'active' : ''}`}
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
            className={`arch-line line-down ${isPathActive('semantic-summarizer') ? 'active' : ''}`}
            markerEnd="url(#arrowhead)"
          />
          <path
            d="M 700 440 L 700 465 L 530 465 L 530 488"
            fill="none"
            className={`arch-line line-down ${isPathActive('episodic-summarizer') ? 'active' : ''}`}
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
            Policy &amp; Audit
          </text>
          <text x="220" y="544" textAnchor="middle" className="arch-subtitle">
            Trace · Risk · Approval
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
