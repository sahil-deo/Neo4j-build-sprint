import { Play, Circle, CheckCircle2, AlertCircle, AlertTriangle, Info, FileText, ChevronRight, BarChart3, Scale, ShieldAlert, Users, LayoutList } from 'lucide-react'
import { fmtUsd, severityColor } from '../utils'

export default function RiskAnalysisTab({
  targetCompany, pipelineRunning, pipelineResult, pipelineError, stageStatus, onRun,
}) {
  const hasResult = !!pipelineResult

  return (
    <div>
      {/* Run bar */}
      <div className="run-bar">
        <div className="run-bar-text">
          Execute the agentic pipeline on <code>{targetCompany}</code>
        </div>
        <button
          className="btn-primary"
          onClick={onRun}
          disabled={pipelineRunning}
        >
          {pipelineRunning ? (
            <><span className="spinner" style={{ display: 'inline-block' }}>⟳</span> Running Analysis</>
          ) : (
            <><Play size={16} /> Run Analysis</>
          )}
        </button>
      </div>

      {/* Stage tracker */}
      {(pipelineRunning || hasResult || pipelineError) && (
        <div className="stage-tracker">
          <StageItem
            label="Stage 1: Change-of-Control Detection"
            status={stageStatus.coc}
            detail={hasResult ? `${pipelineResult.coc?.total_conflicts_detected ?? 0} conflicts` : ''}
          />
          <StageItem
            label="Stage 2: Secondary & Antitrust Scan"
            status={stageStatus.secondary}
            detail={hasResult ? `${pipelineResult.secondary?.risks_found ?? 0} risks` : ''}
          />
          <StageItem
            label="Stage 3: Risk Scoring & DB Write-back"
            status={stageStatus.scoring}
            detail={hasResult ? `${pipelineResult.scored?.length ?? 0} factors stored` : ''}
          />
        </div>
      )}

      {pipelineError && (
        <div style={{
          background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: 'var(--radius-md)', padding: '1rem', marginBottom: '1.5rem',
          color: '#f87171', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '8px'
        }}>
          <AlertCircle size={16} /> Pipeline error: {pipelineError}
        </div>
      )}

      {/* Results */}
      {hasResult && <ResultsDashboard data={pipelineResult} />}

      {!hasResult && !pipelineRunning && !pipelineError && (
        <div className="empty-state">
          <div className="empty-state-icon"><BarChart3 size={48} /></div>
          <div className="empty-state-text">Ready to run analysis</div>
        </div>
      )}
    </div>
  )
}

function StageItem({ label, status, detail }) {
  const icons = {
    pending: <Circle size={18} />,
    running: <span className="spinner" style={{ display: 'inline-block', lineHeight: 0 }}><Circle size={18} /></span>,
    complete: <CheckCircle2 size={18} />,
    error: <AlertCircle size={18} />
  }
  return (
    <div className={`stage-item ${status}`}>
      <div className={`stage-icon ${status}`}>
        {icons[status]}
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
      <div className="section-header">
        <BarChart3 size={20} className="section-icon" />
        <h3 className="section-title">Risk Dashboard</h3>
      </div>
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-label">Total Exposure</div>
          </div>
          <div className="kpi-value">{fmtUsd(totalExposure)}</div>
          <div className="kpi-sub">Calculated risk deductions</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-label">Critical Risks</div>
          </div>
          <div className="kpi-value" style={{ color: 'var(--accent-red)' }}>{criticalCount}</div>
          <div className="kpi-sub">Score ≥ 80</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-label">High Risks</div>
          </div>
          <div className="kpi-value" style={{ color: 'var(--accent-amber)' }}>{highCount}</div>
          <div className="kpi-sub">Score ≥ 60</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-header">
            <div className="kpi-label">Conflict Rings</div>
          </div>
          <div className="kpi-value" style={{ color: 'var(--accent-blue)' }}>{conflictsCount}</div>
          <div className="kpi-sub">Related-party chains</div>
        </div>
      </div>

      <div className="section-header" style={{ marginTop: '2.5rem' }}>
        <TargetIcon size={20} className="section-icon" />
        <h3 className="section-title">Risk Factors</h3>
      </div>
      {scored.map((risk) => (
        <RiskCard key={risk.risk_id} risk={risk} />
      ))}

      <div className="section-header" style={{ marginTop: '2.5rem' }}>
        <Users size={20} className="section-icon" />
        <h3 className="section-title">Conflict Chains</h3>
      </div>
      {(coc?.related_party_conflicts || []).length > 0 ? (
        coc.related_party_conflicts.map((conflict, i) => (
          <ConflictPanel key={i} conflict={conflict} index={i} />
        ))
      ) : (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', padding: '1rem', background: 'var(--bg-card)', borderRadius: 'var(--radius-md)' }}>
          No related-party conflicts detected.
        </div>
      )}

      <div className="section-header" style={{ marginTop: '2.5rem' }}>
        <LayoutList size={20} className="section-icon" />
        <h3 className="section-title">Secondary Risks</h3>
      </div>
      {(secondary?.risk_details || []).slice(0, 10).map((detail, i) => (
        <SecondaryRiskRow key={i} detail={detail} />
      ))}
      {(secondary?.risk_details?.length ?? 0) > 10 && (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '1rem' }}>
          + {secondary.risk_details.length - 10} more clauses
        </div>
      )}

      <div className="deal-summary">
        <div className="deal-summary-header">
          <Scale size={20} style={{ color: 'var(--accent-red)' }} />
          Deal Impact
        </div>
        <div style={{ display: 'flex', gap: '3rem', flexWrap: 'wrap' }}>
          <div>
            <div className="kpi-label">Total Deduction</div>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.25rem' }}>{fmtUsd(totalExposure)}</div>
          </div>
          <div>
            <div className="kpi-label">Summary</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem', lineHeight: 1.6 }}>
              {criticalCount} Critical • {highCount} High <br/>
              Total Factors: {scored.length}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

function TargetIcon({ className, size }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  )
}

function RiskCard({ risk }) {
  const { calculation: calc } = risk
  const sev = calc.severity
  
  const SevIcon = sev === 'CRITICAL' ? AlertTriangle : sev === 'HIGH' ? ShieldAlert : Info

  return (
    <div className="risk-card">
      <div className="risk-card-header">
        <div className="risk-card-title-group">
          <span className="risk-card-title">{risk.category}</span>
          <span className="risk-card-id">{risk.risk_id} • {risk.clause_id}</span>
        </div>
        <span className={`severity-badge severity-${sev.toLowerCase()}`}>
          <SevIcon size={14} /> {sev}
        </span>
      </div>
      <div className="risk-card-grid">
        <div>
          <div className="risk-metric-label">Score</div>
          <div className="risk-metric-value">{calc.risk_score}</div>
        </div>
        <div>
          <div className="risk-metric-label">Base Penalty</div>
          <div className="risk-metric-value">{fmtUsd(calc.base_penalty_usd)}</div>
        </div>
        <div>
          <div className="risk-metric-label">Annual Value</div>
          <div className="risk-metric-value">{fmtUsd(calc.annual_contract_usd)}</div>
        </div>
        <div>
          <div className="risk-metric-label">Exposure</div>
          <div className="risk-metric-value" style={{ color: severityColor(sev) }}>
            {fmtUsd(calc.total_exposure_usd)}
          </div>
        </div>
      </div>
      <div className="risk-card-footer">
        <span>{calc.is_related_party_conflict ? 'Related-party' : 'Regulatory'}</span>
        <span>Hops: {calc.holding_hops}</span>
        <span style={{ color: 'var(--text-muted)' }}>Status: {risk.write_status}</span>
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
      <div className="conflict-header">
        <AlertTriangle size={18} style={{ color: 'var(--accent-amber)' }} />
        Conflict Chain {index + 1}: {director.name ?? 'Unknown'} & {related.name ?? 'Unknown'}
      </div>

      <div className="kpi-label" style={{ marginBottom: '0.5rem' }}>Ownership Flow</div>
      <div className="conflict-chain">
        {chain.map((step, i) => (
          <span key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className={`chain-node ${i === 0 || i === chain.length - 1 ? 'highlight' : ''}`}>
              {step.entity || step.name || '?'}
            </span>
            {i < chain.length - 1 && <ChevronRight size={16} className="chain-arrow" />}
          </span>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginBottom: '1.5rem' }}>
        <div>
          <div className="risk-metric-label">Director</div>
          <div style={{ color: 'var(--text-primary)', fontWeight: 500, fontSize: '0.95rem' }}>{director.name ?? '?'}</div>
        </div>
        <div>
          <div className="risk-metric-label">Supplier Value</div>
          <div style={{ color: 'var(--accent-amber)', fontWeight: 600, fontSize: '1rem' }}>
            {fmtUsd(conflict.annual_supplier_value_usd)}
          </div>
        </div>
        <div>
          <div className="risk-metric-label">CoC Penalty</div>
          <div style={{ color: 'var(--accent-red)', fontWeight: 600, fontSize: '1rem' }}>
            {fmtUsd(conflict.coc_termination_penalty_usd)}
          </div>
        </div>
      </div>

      {citations.filter((d) => d && d.id).map((doc, i) => (
        <div key={i} className="evidence-card">
          <div className="evidence-source">
            <FileText size={14} /> {doc.source_doc ?? 'Doc'} • Page {doc.page ?? '?'}
          </div>
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
        <span>Type: {clause.clause_type ?? 'N/A'}</span>
        <span className="meta-divider">•</span>
        <span>Source: {detail.source ?? 'unknown'}</span>
      </div>
    </div>
  )
}
