import { Cpu } from 'lucide-react'

export default function Hero({ targetCompany }) {
  return (
    <section className="hero">
      <div className="hero-badge">
        <Cpu size={14} />
        Autonomous Pipeline
      </div>
      <h1 className="hero-title">Due Diligence Analysis</h1>
      <p className="hero-subtitle">
        Agentic multi-hop conflict detection for the proposed acquisition of{' '}
        <strong>{targetCompany}</strong> by <strong>Horizon Private Equity</strong>.
      </p>
    </section>
  )
}
