export default function Hero({ targetCompany }) {
  return (
    <section className="hero">
      <div className="hero-badge">🛡️ ENTERPRISE M&A DUE DILIGENCE</div>
      <h1 className="hero-title">DealShield AI Analysis</h1>
      <p className="hero-subtitle">
        Agentic multi-hop GraphRAG conflict detection for the proposed acquisition of{' '}
        <strong>{targetCompany}</strong> by <strong>Horizon Private Equity</strong>.
        Powered by Google ADK, Neo4j Aura, and Gemini 2.5 Flash.
      </p>
    </section>
  )
}
