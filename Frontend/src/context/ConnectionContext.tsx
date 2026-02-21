import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../api/client'

interface ConnectionContextValue {
  connected: boolean | null
  refresh: () => void
}

const ConnectionContext = createContext<ConnectionContextValue>({
  connected: null,
  refresh: () => {},
})

export function ConnectionProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState<boolean | null>(null)

  function refresh() {
    api.connectionStatus()
      .then((r) => setConnected(r.connected))
      .catch(() => setConnected(false))
  }

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 30000)
    return () => clearInterval(id)
  }, [])

  return (
    <ConnectionContext.Provider value={{ connected, refresh }}>
      {children}
    </ConnectionContext.Provider>
  )
}

export function useConnection() {
  return useContext(ConnectionContext)
}
