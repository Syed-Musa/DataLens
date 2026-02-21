import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useConnection } from '../context/ConnectionContext'
import SchemaExplorer from './SchemaExplorer'
import styles from './Layout.module.css'

export default function Layout({ children }: { children: ReactNode }) {
  const loc = useLocation()
  const { connected } = useConnection()
  const showSidebar = loc.pathname !== '/'

  return (
    <div className={styles.layout}>
      {showSidebar && (
        <aside className={styles.sidebar}>
          <header className={styles.sidebarHeader}>
            <Link to="/" className={styles.brand}>
              DataLens
            </Link>
            <div className={styles.status}>
              <span className={connected ? styles.statusOk : styles.statusOff} />
              {connected === true ? (
                'Connected'
              ) : connected === false ? (
                <Link to="/" className={styles.statusLink}>Not connected — reconnect</Link>
              ) : (
                '…'
              )}
            </div>
            <nav className={styles.nav}>
              <Link
                to="/chat"
                className={loc.pathname === '/chat' ? styles.navActive : ''}
              >
                Chat
              </Link>
              <Link
                to="/lineage"
                className={loc.pathname === '/lineage' ? styles.navActive : ''}
              >
                Lineage
              </Link>
            </nav>
          </header>
          <SchemaExplorer />
        </aside>
      )}
      <main className={styles.main}>{children}</main>
    </div>
  )
}
