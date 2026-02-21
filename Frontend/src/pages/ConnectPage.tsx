import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useConnection } from '../context/ConnectionContext'
import styles from './ConnectPage.module.css'

export default function ConnectPage() {
  const [url, setUrl] = useState(
    () => localStorage.getItem('datalens_db_url') ?? 'postgresql://postgres:tiger@localhost:5432/business_data'
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const navigate = useNavigate()
  const { refresh } = useConnection()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setLoading(true)
    try {
      // Basic validation for common placeholders
      if (url.includes('user:password')) {
        throw new Error('Please replace "user:password" with your actual database credentials.')
      }
      
      const res = await api.connectDb(url)
      if (res.success) {
        localStorage.setItem('datalens_db_url', url)
        setSuccess(res.message + (res.tables_count != null ? ` (${res.tables_count} tables)` : ''))
        refresh()
        setTimeout(() => navigate('/chat'), 800)
      } else {
        setError(res.message)
      }
    } catch (err) {
      if (err instanceof Error && err.message.includes('user:password')) {
         setError(err.message)
      } else {
         setError(err instanceof Error ? err.message : 'Connection failed')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>DataLens</h1>
        <p className={styles.subtitle}>Intelligent Data Dictionary Agent</p>
        <form onSubmit={handleSubmit} className={styles.form}>
          <label htmlFor="url" className={styles.label}>
            PostgreSQL connection string
          </label>
          <input
            id="url"
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="postgresql://user:pass@host:5432/dbname"
            className={styles.input}
            disabled={loading}
          />
          <div className={styles.hint}>
            Try: <code>postgresql://postgres:tiger@localhost:5432/business_data</code> or <code>postgresql://postgres:postgres@localhost:5432/postgres</code>
          </div>
          <button type="submit" className={styles.button} disabled={loading}>
            {loading ? 'Connecting…' : 'Connect'}
          </button>
        </form>
        {error && <p className={styles.error}>{error}</p>}
        {success && <p className={styles.success}>{success}</p>}
      </div>
    </div>
  )
}
