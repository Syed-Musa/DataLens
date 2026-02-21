import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ConnectionProvider } from './context/ConnectionContext'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ConnectionProvider>
        <App />
      </ConnectionProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
