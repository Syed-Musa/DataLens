import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import styles from './TablePage.module.css'

export default function TablePage() {
  const { tableName } = useParams<{ tableName: string }>()
  const [schema, setSchema] = useState<Awaited<ReturnType<typeof api.getTable>> | null>(null)
  const [dq, setDq] = useState<Awaited<ReturnType<typeof api.getTableDq>> | null>(null)
  const [relationships, setRelationships] = useState<Awaited<ReturnType<typeof api.getTableRelationships>> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [genLoading, setGenLoading] = useState(false)
  const [dqRefresh, setDqRefresh] = useState(0)

  useEffect(() => {
    if (!tableName) return
    setLoading(true)
    setError(null)

    // Load schema first to display something quickly
    api.getTable(tableName)
      .then((s) => {
        setSchema(s)
        // Then load DQ and relationships (which might be slower or fail)
        Promise.all([
          api.getTableDq(tableName, dqRefresh > 0).catch(() => null),
          api.getTableRelationships(tableName).catch(() => null)
        ]).then(([d, r]) => {
            setDq(d)
            if (r) setRelationships(r)
        })
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))

  }, [tableName, dqRefresh])

  async function handleGenerateDocs() {
    if (!tableName || genLoading) return
    setGenLoading(true)
    try {
      await api.generateDocs([tableName])
      const s = await api.getTable(tableName)
      setSchema(s)
    } finally {
      setGenLoading(false)
    }
  }

  if (loading) {
    return (
      <div className={styles.page}>
        <p className={styles.loading}>Loading…</p>
      </div>
    )
  }

  if (error || !schema) {
    return (
      <div className={styles.page}>
        <p className={styles.error}>{error ?? 'Table not found'}</p>
        <Link to="/chat">Back to Chat</Link>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>{schema.full_name}</h1>
        <div className={styles.headerActions}>
          <button onClick={() => setDqRefresh((r) => r + 1)} className={styles.genBtn} title="Recompute DQ metrics">
            Refresh DQ
          </button>
          <button onClick={handleGenerateDocs} className={styles.genBtn} disabled={genLoading}>
            {genLoading ? 'Generating…' : 'Generate AI description'}
          </button>
        </div>
      </header>
      {schema.ai_description && (
        <section className={styles.section}>
          <h2>Description</h2>
          <p className={styles.description}>{schema.ai_description}</p>
        </section>
      )}
      <section className={styles.section}>
        <h2>Columns</h2>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Nullable</th>
              <th>Default</th>
            </tr>
          </thead>
          <tbody>
            {schema.columns.map((c) => (
              <tr key={c.name}>
                <td className={styles.mono}>
                  {c.name}
                  {schema.primary_keys.includes(c.name) && <span className={styles.badge}>PK</span>}
                </td>
                <td className={styles.mono}>{c.type}</td>
                <td>{c.nullable ? 'Yes' : 'No'}</td>
                <td className={styles.mono}>{c.default ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      {schema.foreign_keys.length > 0 && (
        <section className={styles.section}>
          <h2>Foreign Keys</h2>
          <ul className={styles.list}>
            {schema.foreign_keys.map((fk, i) => (
              <li key={i}>
                {fk.columns.join(', ')} → {fk.referred_table}({fk.referred_columns.join(', ')})
              </li>
            ))}
          </ul>
        </section>
      )}
      {dq && (
        <section className={styles.section}>
          <h2>Data Quality</h2>
          <p className={styles.rowCount}>
            {dq.row_count.toLocaleString()} rows
            {dq.pk_duplicate_pct != null && (
              <span> • PK duplicate: {dq.pk_duplicate_pct}%</span>
            )}
          </p>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Column</th>
                <th>Null %</th>
                <th>Distinct %</th>
                <th>Min</th>
                <th>Max</th>
                <th>Mean</th>
                <th>Duplicate %</th>
                <th>Freshness</th>
              </tr>
            </thead>
            <tbody>
              {dq.columns.map((c) => (
                <tr key={c.column}>
                  <td className={styles.mono}>{c.column}</td>
                  <td>{c.null_pct}%</td>
                  <td>{c.distinct_pct}%</td>
                  <td className={styles.mono}>{c.min != null ? String(c.min) : '—'}</td>
                  <td className={styles.mono}>{c.max != null ? String(c.max) : '—'}</td>
                  <td>{c.mean != null ? c.mean.toFixed(2) : '—'}</td>
                  <td>{c.duplicate_pct != null ? `${c.duplicate_pct}%` : '—'}</td>
                  <td className={styles.mono}>{c.freshness ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {relationships && !relationships.error && (relationships.outgoing_relationships?.length > 0 || relationships.incoming_relationships?.length > 0) && (
        <section className={styles.section}>
          <h2>Relationships (MCP Inspection)</h2>
          
          {relationships.outgoing_relationships?.length > 0 && (
            <div className={styles.relGroup}>
              <h3>Outgoing Relationships (Foreign Keys)</h3>
              <ul className={styles.relList}>
                {relationships.outgoing_relationships.map((rel: any, i: number) => (
                  <li key={i}>
                    <strong>{rel.related_table}</strong>: {rel.description}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {relationships.incoming_relationships?.length > 0 && (
            <div className={styles.relGroup}>
              <h3>Incoming References</h3>
              <ul className={styles.relList}>
                {relationships.incoming_relationships.map((rel: any, i: number) => (
                  <li key={i}>
                    <strong>{rel.related_table}</strong>: {rel.description}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </div>

  )
}
