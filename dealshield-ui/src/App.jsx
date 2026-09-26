import { useState, useEffect } from 'react'
import { Activity, Network, ScrollText } from 'lucide-react'
import { api } from './api'
import Sidebar from './components/Sidebar'
import Hero from './components/Hero'
import RiskAnalysisTab from './components/RiskAnalysisTab'
import GraphExplorerTab from './components/GraphExplorerTab'
import AgentEventsTab from './components/AgentEventsTab'

const TABS = [
  { id: 'analysis', label: 'Risk Analysis', icon: Activity },
  { id: 'graph', label: 'Graph Explorer', icon: Network },
  { id: 'events', label: 'Agent Events', icon: ScrollText },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('analysis')
  const [targetCompany, setTargetCompany] = useState('TargetTech Inc.')
  const [graphStats, setGraphStats] = useState(null)
  const [neo4jStatus, setNeo4jStatus] = useState('checking')

  const [pipelineRunning, setPipelineRunning] = useState(false)
  const [pipelineResult, setPipelineResult] = useState(null)
  const [pipelineError, setPipelineError] = useState(null)
  const [stageStatus, setStageStatus] = useState({
    coc: 'pending', secondary: 'pending', scoring: 'pending',
  })

  useEffect(() => {
    api.graphStats()
      .then((data) => {
        setGraphStats(data)
        setNeo4jStatus('connected')
      })
      .catch(() => setNeo4jStatus('error'))
  }, [])

  const runPipeline = async () => {
    setPipelineRunning(true)
    setPipelineError(null)
    setPipelineResult(null)
    setStageStatus({ coc: 'running', secondary: 'pending', scoring: 'pending' })

    try {
      const cocResult = await api.analyzeCoc(targetCompany)
      setStageStatus((s) => ({ ...s, coc: 'complete', secondary: 'running' }))

      const secResult = await api.analyzeSecondary(targetCompany)
      setStageStatus((s) => ({ ...s, secondary: 'complete', scoring: 'running' }))

      const risksToScore = [
        {
          company_id: 'COMP-002', clause_id: 'CL-402', risk_id: 'RISK-CALC-001',
          category: 'Undisclosed Related-Party + Change-of-Control',
          base_penalty_usd: 15000000, annual_contract_usd: 18500000,
          is_related_party_conflict: true, holding_hops: 2,
          rationale: "Director Marcus Vance's spouse Elena Rostova-Vance holds 42% of Vanguard Pacific Holdings, which owns 65% of sole-source supplier Apex MicroSystems LLC. The $18.5M annual supply contract combined with the $15M CoC poison-pill penalty creates $33.5M total exposure.",
          source_chunk_id: 'DOC-CHUNK-101',
        },
        {
          company_id: 'COMP-002', clause_id: 'CL-819', risk_id: 'RISK-CALC-002',
          category: 'Anti-Trust / Regulatory – DoD Contract Revocation',
          base_penalty_usd: 45000000, annual_contract_usd: 0,
          is_related_party_conflict: false, holding_hops: 0,
          rationale: "Acquirer Horizon Private Equity's existing defense portfolio creates >25% market share overlap, triggering immediate revocation of TargetTech's $45M DoD contract per Clause 9.4.",
          source_chunk_id: 'DOC-CHUNK-103',
        },
        {
          company_id: 'COMP-002', clause_id: 'CL-205', risk_id: 'RISK-CALC-003',
          category: 'Governance / Fraud – Director Attestation Failure',
          base_penalty_usd: 18500000, annual_contract_usd: 0,
          is_related_party_conflict: true, holding_hops: 2,
          rationale: "Marcus Vance failed to disclose spousal beneficial ownership in sole-source vendor Apex MicroSystems via Vanguard Pacific Holdings in annual director conflict attestation.",
          source_chunk_id: 'DOC-CHUNK-102',
        },
      ]

      const scoredRisks = []
      for (const risk of risksToScore) {
        const result = await api.scoreRisk(risk)
        scoredRisks.push(result)
      }

      setStageStatus({ coc: 'complete', secondary: 'complete', scoring: 'complete' })
      setPipelineResult({ coc: cocResult, secondary: secResult, scored: scoredRisks })
    } catch (err) {
      setPipelineError(err.message)
      setStageStatus((prev) => {
        const updated = { ...prev }
        for (const key of Object.keys(updated)) {
          if (updated[key] === 'running') updated[key] = 'error'
        }
        return updated
      })
    } finally {
      setPipelineRunning(false)
    }
  }

  return (
    <div className="app-layout">
      <Sidebar
        targetCompany={targetCompany}
        setTargetCompany={setTargetCompany}
        graphStats={graphStats}
        neo4jStatus={neo4jStatus}
      />
      <main className="main-content">
        <Hero targetCompany={targetCompany} />

        <div className="tabs-nav">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <tab.icon size={16} />
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'analysis' && (
          <RiskAnalysisTab
            targetCompany={targetCompany}
            pipelineRunning={pipelineRunning}
            pipelineResult={pipelineResult}
            pipelineError={pipelineError}
            stageStatus={stageStatus}
            onRun={runPipeline}
          />
        )}
        {activeTab === 'graph' && <GraphExplorerTab />}
        {activeTab === 'events' && <AgentEventsTab pipelineResult={pipelineResult} />}
      </main>
    </div>
  )
}
