import { useState } from 'react'
import { ScrollText, ChevronRight, CheckCircle2, ChevronDown } from 'lucide-react'

export default function AgentEventsTab({ pipelineResult }) {
  if (!pipelineResult) {
    return (
      <div className="empty-state">
        <ScrollText size={48} className="empty-state-icon" />
        <div className="empty-state-text">Run the analysis to view agent execution traces.</div>
      </div>
    )
  }

  return (
    <div>
      <div className="section-header">
        <ScrollText size={20} className="section-icon" />
        <h3 className="section-title">Agentic Pipeline Event Log</h3>
      </div>
      <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
        Execution trace of the Google ADK SequentialAgent pipeline across all sub-agents.
      </p>

      {/* Pipeline Summary */}
      <div className="pipeline-log">
        <div className="section-header" style={{ marginBottom: '1rem', paddingBottom: '0.5rem' }}>
          <h4 className="section-title" style={{ fontSize: '1rem' }}>Execution Summary</h4>
        </div>
        
        <div className="pipeline-step">
          <CheckCircle2 size={16} style={{ color: 'var(--accent-emerald)' }} />
          <span><strong>Stage 1</strong>: CoC_Conflict_Detector – <code>analyze_change_of_control_graphrag</code></span>
        </div>
        <div className="pipeline-step">
          <CheckCircle2 size={16} style={{ color: 'var(--accent-emerald)' }} />
          <span><strong>Stage 2</strong>: Secondary_Risk_Analyzer – <code>analyze_secondary_and_antitrust_risks</code></span>
        </div>
        <div className="pipeline-step">
          <CheckCircle2 size={16} style={{ color: 'var(--accent-emerald)' }} />
          <span><strong>Stage 3</strong>: Risk_Scorer – <code>calculate_and_store_risk_factor</code></span>
        </div>
      </div>

      {/* JSON Expanders */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <JsonExpander
          title="Stage 1: Change-of-Control Results"
          data={pipelineResult.coc}
        />
        <JsonExpander
          title="Stage 2: Secondary Risk Results"
          data={pipelineResult.secondary}
        />
        <JsonExpander
          title="Stage 3: Risk Scoring Results"
          data={pipelineResult.scored}
        />
      </div>
    </div>
  )
}

function JsonExpander({ title, data }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="json-expander">
      <button className="json-expander-btn" onClick={() => setOpen(!open)}>
        {open ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
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
