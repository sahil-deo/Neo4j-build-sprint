import { useState } from 'react'

export default function AgentEventsTab({ pipelineResult }) {
  if (!pipelineResult) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📋</div>
        <div className="empty-state-text">Run the analysis first to see agent events.</div>
      </div>
    )
  }

  return (
    <div>
      <h3 className="section-title">📋 Agentic Pipeline Event Log</h3>
      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Detailed trace of the SequentialAgent pipeline execution across all 3 sub-agents.
      </p>

      {/* Pipeline Summary */}
      <div className="pipeline-log">
        <h4 className="section-title" style={{ fontSize: '0.95rem' }}>🤖 Pipeline Execution Summary</h4>
        <div className="pipeline-step">
          <span className="status-dot connected" />
          <strong>Stage 1</strong>: CoC_Conflict_Detector –{' '}
          <code>analyze_change_of_control_graphrag</code>
        </div>
        <div className="pipeline-step">
          <span className="status-dot connected" />
          <strong>Stage 2</strong>: Secondary_Risk_Analyzer –{' '}
          <code>analyze_secondary_and_antitrust_risks</code>
        </div>
        <div className="pipeline-step">
          <span className="status-dot connected" />
          <strong>Stage 3</strong>: Risk_Scorer –{' '}
          <code>calculate_and_store_risk_factor</code> × 3 calls
        </div>
      </div>

      {/* JSON Expanders */}
      <JsonExpander
        title="🔍 Stage 1: Change-of-Control Results"
        data={pipelineResult.coc}
      />
      <JsonExpander
        title="🔍 Stage 2: Secondary Risk Results"
        data={pipelineResult.secondary}
      />
      <JsonExpander
        title="🔍 Stage 3: Risk Scoring Results"
        data={pipelineResult.scored}
      />
    </div>
  )
}

function JsonExpander({ title, data }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="json-expander">
      <button className="json-expander-btn" onClick={() => setOpen(!open)}>
        <span style={{ transition: 'transform 150ms', display: 'inline-block', transform: open ? 'rotate(90deg)' : 'rotate(0)' }}>
          ▶
        </span>
        {title}
      </button>
      {open && (
        <div className="json-expander-content">
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
