import { Shield, Layers, Database, Activity, Target } from 'lucide-react'

export default function Sidebar({ targetCompany, setTargetCompany, graphStats, neo4jStatus }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <Shield size={24} />
        </div>
        <div className="sidebar-brand-text">
          <div className="sidebar-brand-name">DealShield</div>
          <div className="sidebar-brand-sub">M&A Due Diligence</div>
        </div>
      </div>

      <div className="sidebar-input-group">
        <label>Target Company</label>
        <div style={{ position: 'relative' }}>
          <Target size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            className="sidebar-input"
            style={{ paddingLeft: '2rem' }}
            value={targetCompany}
            onChange={(e) => setTargetCompany(e.target.value)}
            placeholder="e.g. TargetTech Inc."
          />
        </div>
      </div>

      <div className="sidebar-divider" />

      <div className="sidebar-section-label">
        <Layers size={14} /> Stack Components
      </div>
      {[
        { label: 'Google ADK Agents' },
        { label: 'Neo4j Aura Graph' },
        { label: 'GraphRAG Engine' },
        { label: 'Agent Memory' },
        { label: 'Gemini LLM' },
      ].map(({ label }) => (
        <div key={label} className="sidebar-stack-item">
          <Activity size={14} className="sidebar-stack-icon" />
          {label}
        </div>
      ))}

      <div className="sidebar-divider" />

      <div className="sidebar-section-label">
        <Database size={14} /> Knowledge Graph
      </div>
      {graphStats ? (
        <>
          <div className="sidebar-stats">
            <div className="sidebar-stat">
              <div className="sidebar-stat-value">{graphStats.companies ?? 0}</div>
              <div className="sidebar-stat-label">Companies</div>
            </div>
            <div className="sidebar-stat">
              <div className="sidebar-stat-value">{graphStats.executives ?? 0}</div>
              <div className="sidebar-stat-label">Executives</div>
            </div>
            <div className="sidebar-stat">
              <div className="sidebar-stat-value">{graphStats.clauses ?? 0}</div>
              <div className="sidebar-stat-label">Clauses</div>
            </div>
            <div className="sidebar-stat">
              <div className="sidebar-stat-value">{graphStats.doc_chunks ?? 0}</div>
              <div className="sidebar-stat-label">Documents</div>
            </div>
          </div>
          <div className="sidebar-status">
            <span className={`status-dot ${neo4jStatus === 'connected' ? 'connected' : 'error'}`} />
            <span style={{ color: neo4jStatus === 'connected' ? 'var(--text-secondary)' : 'var(--accent-red)' }}>
              {neo4jStatus === 'connected' ? 'Connected to Aura' : 'Connection Error'}
            </span>
          </div>
        </>
      ) : (
        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          {neo4jStatus === 'checking' ? 'Connecting to DB...' : 'Failed to load stats'}
        </div>
      )}
    </aside>
  )
}
