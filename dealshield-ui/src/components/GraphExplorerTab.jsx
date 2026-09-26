import { useState, useEffect } from 'react'
import { Database, Play, AlertCircle, FileSearch } from 'lucide-react'
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
        // Clean up preset labels from emojis if any
        const cleaned = list.map(p => ({
          ...p,
          label: p.label.replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F1E6}-\u{1F1FF}\u{1F900}-\u{1F9FF}\u{1F018}-\u{1F270}\u{238C}\u{2B06}\u{2B05}\u{2B07}\u{2B00}-\u{2B04}\u{2934}\u{2935}\u{2194}-\u{2199}\u{21A9}\u{21AA}\u{25AA}\u{25AB}\u{25FB}-\u{25FE}\u{25B6}\u{25C0}\u{23E9}-\u{23F3}\u{23F8}-\u{23FA}\u{200D}]/gu, '').trim()
        }))
        setPresets(cleaned)
        if (cleaned.length > 0) {
          setSelectedPreset(cleaned[0].id)
          setQuery(cleaned[0].query)
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
      <div className="section-header">
        <Database size={20} className="section-icon" />
        <h3 className="section-title">Neo4j Graph Explorer</h3>
      </div>
      <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
        Run custom Cypher queries against the DealShield knowledge graph in Neo4j Aura.
      </p>

      <div className="explorer-controls">
        <select className="explorer-select" value={selectedPreset} onChange={handlePresetChange}>
          {presets.map((p) => (
            <option key={p.id} value={p.id}>{p.label}</option>
          ))}
        </select>
      </div>

      <textarea
        className="explorer-textarea"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        rows={5}
        spellCheck={false}
      />

      <button className="btn-secondary" onClick={execute} disabled={loading} style={{ marginBottom: '2rem' }}>
        {loading ? (
          <><span className="spinner" style={{ display: 'inline-block' }}><Database size={16} /></span> Executing</>
        ) : (
          <><Play size={16} /> Execute Query</>
        )}
      </button>

      {error && (
        <div style={{
          background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: 'var(--radius-md)', padding: '1rem', marginBottom: '1.5rem',
          color: '#f87171', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '8px'
        }}>
          <AlertCircle size={16} /> Cypher error: {error}
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
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.75rem', textAlign: 'right' }}>
            {results.count} record(s) returned
          </div>
        </>
      )}

      {results && results.count === 0 && (
        <div className="empty-state" style={{ padding: '3rem 2rem' }}>
          <FileSearch size={32} className="empty-state-icon" />
          <div className="empty-state-text">Query returned no results.</div>
        </div>
      )}
    </div>
  )
}
