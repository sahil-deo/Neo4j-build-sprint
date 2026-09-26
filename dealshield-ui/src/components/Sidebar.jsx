export default function Sidebar({ targetCompany, setTargetCompany, graphStats, neo4jStatus }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">🛡️</div>
        <div className="sidebar-brand-name">DealShield</div>
        <div className="sidebar-brand-sub">M&A Due Diligence AI</div>
      </div>

      <div className="sidebar-divider" />

      <div className="sidebar-input-group">
        <label>🎯 Target Company</label>
        <input
          className="sidebar-input"
          value={targetCompany}
          onChange={(e) => setTargetCompany(e.target.value)}
          placeholder="e.g. TargetTech Inc."
        />
      </div>

      <div className="sidebar-divider" />

      <div className="sidebar-section-label">⚡ Tech Stack</div>
      {[
        { dot: '#6366f1', label: 'Google ADK SequentialAgent' },
        { dot: '#3b82f6', label: 'Neo4j Aura Cloud Graph' },
        { dot: '#06b6d4', label: 'GraphRAG Multi-hop Cypher' },
        { dot: '#8b5cf6', label: 'Neo4j Agent Memory' },
        { dot: '#10b981', label: 'Gemini 2.5 Flash' },
      ].map(({ dot, label }) => (
        <div key={label} className="sidebar-stack-item">
          <span className="sidebar-stack-dot" style={{ background: dot }} />
          {label}
        </div>
      ))}

      <div className="sidebar-divider" />

      <div className="sidebar-section-label">📊 Graph Stats</div>
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
              <div className="sidebar-stat-label">Doc Chunks</div>
            </div>
          </div>
          <div className="sidebar-status">
            <span className={`status-dot ${neo4jStatus === 'connected' ? 'connected' : 'error'}`} />
            <span style={{ color: neo4jStatus === 'connected' ? '#10b981' : '#ef4444', fontSize: '0.75rem' }}>
              {neo4jStatus === 'connected' ? 'Neo4j Connected' : 'Connection Error'}
            </span>
          </div>
        </>
      ) : (
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center', padding: '0.5rem' }}>
          {neo4jStatus === 'checking' ? 'Connecting...' : 'Failed to load stats'}
        </div>
      )}
    </aside>
  )
}
