import { fmtUsd, severityColor } from '../utils'

const SEVERITY_ICONS = { CRITICAL: '🔴', HIGH: '🟠', MEDIUM: '🔵', LOW: '🟢' }

export default function RiskAnalysisTab({
  targetCompany, pipelineRunning, pipelineResult, pipelineError, stageStatus, onRun,
}) {
  const hasResult = !!pipelineResult

  return (
    <div>
      {/* Run bar */}
      <div className="run-bar">
        <div className="run-bar-text">
          Execute the 3-stage agentic pipeline on <code>{targetCompany}</code>
        </div>
        <button
          className={`btn-primary ${pipelineRunning ? 'loading' : ''}`}
          onClick={onRun}
          disabled={pipelineRunning}
        >
          {pipelineRunning ? (
            <><span className="spinner">⟳</span> Running...</>
          ) : (
            <>🚀 Run Full Analysis</>
          )}
        </button>
      </div>

      {/* Stage tracker */}
      {(pipelineRunning || hasResult || pipelineError) && (
        <div className="stage-tracker">
          <StageItem
            label="Stage 1: Change-of-Control Conflict Detection"
            status={stageStatus.coc}
            detail={hasResult ? `${pipelineResult.coc?.total_conflicts_detected ?? 0} conflicts` : ''}
          />
          <StageItem
            label="Stage 2: Secondary & Antitrust Risk Scan"
            status={stageStatus.secondary}
            detail={hasResult ? `${pipelineResult.secondary?.risks_found ?? 0} risks` : ''}
          />
          <StageItem
            label="Stage 3: Risk Scoring & Neo4j Write-back"
            status={stageStatus.scoring}
            detail={hasResult ? `${pipelineResult.scored?.length ?? 0} factors stored` : ''}
          />
        </div>
      )}

      {pipelineError && (
        <div style={{
          background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)',
          borderRadius: 'var(--radius-md)', padding: '1rem', marginBottom: '1rem',
          color: '#fca5a5', fontSize: '0.85rem',
        }}>
          ❌ Pipeline error: {pipelineError}
        </div>
      )}

      {/* Results */}
      {hasResult && <ResultsDashboard data={pipelineResult} />}

      {!hasResult && !pipelineRunning && !pipelineError && (
        <div className="empty-state">
          <div className="empty-state-icon">🛡️</div>
          <div className="empty-state-text">Run the analysis to see results</div>
        </div>
      )}
    </div>
  )
}

function StageItem({ label, status, detail }) {
  const icons = { pending: '○', running: '◉', complete: '✓', error: '✕' }
  return (
    <div className={`stage-item ${status}`}>
      <div className={`stage-icon ${status}`}>
        {status === 'running' ? <span className="spinner">⟳</span> : icons[status]}
      </div>
      <span className="stage-label">{label}</span>
      {detail && <span className="stage-detail">{detail}</span>}
    </div>
  )
}

function ResultsDashboard({ data }) {
  const { coc, secondary, scored } = data
  const totalExposure = scored.reduce((sum, r) => sum + r.calculation.total_exposure_usd, 0)
  const criticalCount = scored.filter((r) => r.calculation.severity === 'CRITICAL').length
  const highCount = scored.filter((r) => r.calculation.severity === 'HIGH').length
  const conflictsCount = coc?.total_conflicts_detected ?? 0

  return (
    <>
      {/* KPI Cards */}
      <h3 className="section-title">📊 Deal Risk Dashboard</h3>
      <div className="kpi-grid">
        <div className="kpi-card critical">
          <div className="kpi-label">Total Deal Exposure</div>
          <div className="kpi-value">{fmtUsd(totalExposure)}</div>
          <div className="kpi-sub">Combined risk deductions</div>
        </div>
        <div className="kpi-card critical">
          <div className="kpi-label">Critical Risks</div>
          <div className="kpi-value">{criticalCount}</div>
          <div className="kpi-sub">Score ≥ 80</div>
        </div>
        <div className="kpi-card high">
          <div className="kpi-label">High Risks</div>
          <div className="kpi-value">{highCount}</div>
          <div className="kpi-sub">Score ≥ 60</div>
        </div>
        <div className="kpi-card info">
          <div className="kpi-label">Conflict Rings</div>
          <div className="kpi-value">{conflictsCount}</div>
          <div className="kpi-sub">Related-party chains</div>
        </div>
      </div>

      {/* Scored Risk Cards */}
      <h3 className="section-title">🎯 Calculated Risk Factors</h3>
      {scored.map((risk) => (
        <RiskCard key={risk.risk_id} risk={risk} />
      ))}

      {/* Conflict Chains */}
      <h3 className="section-title" style={{ marginTop: '1.5rem' }}>🕵️ Change-of-Control Conflict Chains</h3>
      {(coc?.related_party_conflicts || []).length > 0 ? (
        coc.related_party_conflicts.map((conflict, i) => (
          <ConflictPanel key={i} conflict={conflict} index={i} />
        ))
      ) : (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '1rem' }}>
          No related-party conflict rings detected.
        </div>
      )}

      {/* Secondary Risks */}
      <h3 className="section-title" style={{ marginTop: '1.5rem' }}>📋 Secondary & Antitrust Risks</h3>
      {(secondary?.risk_details || []).slice(0, 10).map((detail, i) => (
        <SecondaryRiskRow key={i} detail={detail} />
      ))}
      {(secondary?.risk_details?.length ?? 0) > 10 && (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textAlign: 'center', padding: '0.5rem' }}>
          + {secondary.risk_details.length - 10} more clauses
        </div>
      )}

      {/* Deal Summary */}
      <div className="deal-summary">
        <h3 className="section-title" style={{ color: '#fca5a5' }}>⚖️ Deal Impact Summary</h3>
        <div className="deal-summary-grid">
          <div>
            <div className="kpi-label">Total Deal Deduction</div>
            <div className="deal-total-value">{fmtUsd(totalExposure)}</div>
            <div className="deal-total-sub">Sum of all calculated risk factor exposures</div>
          </div>
          <div>
            <div className="kpi-label">Risk Breakdown</div>
            <div className="deal-breakdown">
              🔴 CRITICAL: {criticalCount} risk(s)<br />
              🟠 HIGH: {highCount} risk(s)<br />
              📊 Total Factors Stored: {scored.length}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

function RiskCard({ risk }) {
  const { calculation: calc } = risk
  const sev = calc.severity
  return (
    <div className="risk-card">
      <div className="risk-card-header">
        <span className={`severity-badge severity-${sev.toLowerCase()}`}>
          {SEVERITY_ICONS[sev]} {sev}
        </span>
        <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.9rem' }}>
          {risk.risk_id} – {risk.clause_id}
        </span>
      </div>
      <div className="risk-card-grid">
        <div>
          <div className="risk-card-metric-label">Risk Score</div>
          <div className="risk-card-metric-value">{calc.risk_score}/100</div>
        </div>
        <div>
          <div className="risk-card-metric-label">Base Penalty</div>
          <div className="risk-card-metric-value">{fmtUsd(calc.base_penalty_usd)}</div>
        </div>
        <div>
          <div className="risk-card-metric-label">Annual Contract</div>
          <div className="risk-card-metric-value">{fmtUsd(calc.annual_contract_usd)}</div>
        </div>
        <div>
          <div className="risk-card-metric-label">Total Exposure</div>
          <div className="risk-card-metric-value" style={{ color: severityColor(sev) }}>
            {fmtUsd(calc.total_exposure_usd)}
          </div>
        </div>
      </div>
      <div className="risk-card-footer">
        <span>{calc.is_related_party_conflict ? '🔗 Related-party conflict' : '📋 Direct regulatory risk'}</span>
        <span>Holding hops: {calc.holding_hops}</span>
        <span style={{ color: '#10b981' }}>Write: {risk.write_status}</span>
      </div>
    </div>
  )
}

function ConflictPanel({ conflict, index }) {
  const director = conflict.director || {}
  const related = conflict.related_party || {}
  const chain = conflict.holding_chain || []
  const citations = conflict.document_citations || []

  return (
    <div className="conflict-panel">
      <h4 className="section-title" style={{ fontSize: '0.95rem' }}>
        ⚠️ Conflict Ring {index + 1}: {director.name ?? 'Unknown'} → {related.name ?? 'Unknown'}
      </h4>

      <div className="kpi-label">Ownership Chain</div>
      <div className="conflict-chain">
        {chain.map((step, i) => (
          <span key={i}>
            <span className="chain-node">{step.entity || step.name || '?'}</span>
            {i < chain.length - 1 && <span className="chain-arrow"> → </span>}
          </span>
        ))}
      </div>

      <div className="conflict-meta-grid">
        <div>
          <div className="risk-card-metric-label">Director</div>
          <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{director.name ?? '?'}</div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{director.title ?? ''}</div>
        </div>
        <div>
          <div className="risk-card-metric-label">Annual Supplier Value</div>
          <div style={{ color: '#f59e0b', fontWeight: 700, fontSize: '1.1rem' }}>
            {fmtUsd(conflict.annual_supplier_value_usd)}
          </div>
        </div>
        <div>
          <div className="risk-card-metric-label">CoC Penalty</div>
          <div style={{ color: '#ef4444', fontWeight: 700, fontSize: '1.1rem' }}>
            {fmtUsd(conflict.coc_termination_penalty_usd)}
          </div>
        </div>
      </div>

      {citations.filter((d) => d && d.id).map((doc, i) => (
        <div key={i} className="evidence-card">
          <div className="evidence-source">📄 {doc.source_doc ?? 'Unknown'} — Page {doc.page ?? '?'}</div>
          <div className="evidence-text">{doc.text ?? 'No text available'}</div>
        </div>
      ))}
    </div>
  )
}

function SecondaryRiskRow({ detail }) {
  const clause = detail.clause || {}
  return (
    <div className="secondary-risk-row">
      <div className="secondary-risk-header">
        <span className="secondary-risk-title">
          {clause.id ?? '?'} – {clause.title ?? 'Unknown'}
        </span>
        <span className="secondary-risk-exposure">
          {fmtUsd(clause.financial_exposure_usd)}
        </span>
      </div>
      <div className="secondary-risk-meta">
        Type: <strong>{clause.clause_type ?? 'N/A'}</strong>
        {' • '}Source: {detail.source ?? 'unknown'}
        {clause.summary && <> {' • '}{clause.summary}</>}
      </div>
    </div>
  )
}
