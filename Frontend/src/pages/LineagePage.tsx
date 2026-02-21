import { useState, useEffect } from 'react'
import { api } from '../api/client'
import LineageGraph from '../components/LineageGraph'
import styles from './LineagePage.module.css'

export default function LineagePage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.lineage>> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .lineage()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className={styles.page}><p className={styles.loading}>Loading lineage…</p></div>
  if (error) return <div className={styles.page}><p className={styles.error}>{error}</p></div>

  const nodes = data?.nodes ?? []
  const edges = data?.edges ?? []

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Schema Lineage</h1>
      <p className={styles.hint}>Tables and foreign key relationships. Click a table to view details.</p>
      {nodes.length > 0 ? (
        <section className={styles.graphSection}>
          <LineageGraph nodes={nodes} edges={edges} />
        </section>
      ) : (
        <p className={styles.empty}>No tables or relationships found.</p>
      )}
      {edges.length > 0 && (
        <section className={styles.edgeList}>
          <h3>Relationships</h3>
          {edges.map((e, i) => (
            <div key={i} className={styles.edge}>
              <span>{e.source}</span>
              <span className={styles.arrow}>→</span>
              <span>{e.target}</span>
              <span className={styles.edgeCols}>
                {e.columns.join(', ')} → {e.referred_columns.join(', ')}
              </span>
            </div>
          ))}
        </section>
      )}
    </div>
  )
}
