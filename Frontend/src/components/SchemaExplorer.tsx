import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useConnection } from '../context/ConnectionContext'
import styles from './SchemaExplorer.module.css'

interface TableSummary {
  schema: string
  name: string
  full_name: string
}

export default function SchemaExplorer() {
  const { connected } = useConnection()
  const [tables, setTables] = useState<TableSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (connected !== true) {
      setLoading(false)
      setTables([])
      setError(connected === false ? null : null)
      return
    }
    setLoading(true)
    setError(null)
    api
      .getTables()
      .then(setTables)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [connected])

  return (
    <div className={styles.explorer}>
      <h3 className={styles.title}>Tables</h3>
      {connected === null && <p className={styles.hint}>Checking…</p>}
      {connected === false && (
        <p className={styles.hint}>
          <Link to="/">Connect database</Link> to browse tables.
        </p>
      )}
      {connected === true && loading && <p className={styles.hint}>Loading…</p>}
      {connected === true && error && <p className={styles.error}>{error}</p>}
      {connected === true && !loading && !error && tables.length === 0 && (
        <p className={styles.hint}>No tables in this database.</p>
      )}
      {connected === true && (
      <ul className={styles.list}>
        {tables.map((t) => (
          <li key={t.full_name}>
            <Link to={`/table/${encodeURIComponent(t.full_name)}`} className={styles.item}>
              <span className={styles.tableName}>{t.name}</span>
              {t.schema !== 'public' && (
                <span className={styles.schema}>{t.schema}</span>
              )}
            </Link>
          </li>
        ))}
      </ul>
      )}
    </div>
  )
}
