import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ConnectPage from './pages/ConnectPage'
import ChatPage from './pages/ChatPage'
import TablePage from './pages/TablePage'
import LineagePage from './pages/LineagePage'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<ConnectPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/table/:tableName" element={<TablePage />} />
        <Route path="/lineage" element={<LineagePage />} />
      </Routes>
    </Layout>
  )
}

export default App
