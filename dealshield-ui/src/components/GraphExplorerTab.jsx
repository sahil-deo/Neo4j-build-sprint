import { useState, useEffect } from 'react'
import { api } from '../api'

export default function GraphExplorerTab() {
  const [presets, setPresets] = useState([])
  const [selectedPreset, setSelectedPreset] = useState('')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.graphPresets()
      .then((data) => {
        const list = data.presets || []
        setPresets(list)
        if (list.length > 0) {
          setSelectedPreset(list[0].id)
          setQuery(list[0].query)
        }
      })
      .catch(() => {})
  }, [])

  const handlePresetChange = (e) => {
    const id = e.target.value
    setSelectedPreset(id)
    const preset = presets.find((p) => p.id === id)
    if (preset) setQuery(preset.query)
  }

  const execute = async () => {
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const data = await api.graphQuery(query)
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const columns = results?.results?.length > 0 ? Object.keys(results.results[0]) : []

  return (
    <div>
      <h3 className="section-title">🕸️ Neo4j Graph Explorer</h3>
      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Run custom Cypher queries against the DealShield knowledge graph in Neo4j Aura.
      </p>

      <select className="explorer-select" value={selectedPreset} onChange={handlePresetChange}>
        {presets.map((p) => (
          <option key={p.id} value={p.id}>{p.label}</option>
        ))}
      </select>

      <textarea
        className="explorer-textarea"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        rows={4}
      />

      <button className="btn-execute" onClick={execute} disabled={loading}>
        {loading ? <><span className="spinner">⟳</span> Executing...</> : <>▶️ Execute Query</>}
      </button>

      {error && (
        <div style={{
          background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)',
          borderRadius: 'var(--radius-md)', padding: '0.75rem 1rem', marginBottom: '1rem',
          color: '#fca5a5', fontSize: '0.82rem',
        }}>
          Cypher error: {error}
        </div>
      )}

      {results && results.results && (
        <>
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  {columns.map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.results.map((row, i) => (
                  <tr key={i}>
                    {columns.map((col) => (
                      <td key={col} title={String(row[col] ?? '')}>
                        {typeof row[col] === 'object' ? JSON.stringify(row[col]) : String(row[col] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="table-count">{results.count} record(s) returned</div>
        </>
      )}

      {results && results.count === 0 && (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '1rem', textAlign: 'center' }}>
          Query returned no results.
        </div>
      )}
    </div>
  )
}
