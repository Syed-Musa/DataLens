import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../api/client'
import styles from './ChatPage.module.css'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sql?: string
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [genLoading, setGenLoading] = useState(false)
  const [copiedId, setCopiedId] = useState<number | null>(null)
  const [artifacts, setArtifacts] = useState<string[]>([])
  const [showArtifacts, setShowArtifacts] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Load artifacts on mount
    api.listArtifacts?.().then(res => setArtifacts(res.artifacts || [])).catch(() => {})
  }, [])

  function copySql(sql: string, msgIndex: number) {
    navigator.clipboard.writeText(sql).then(() => {
      setCopiedId(msgIndex)
      setTimeout(() => setCopiedId(null), 2000)
    })
  }

  async function handleGenerateAllDocs() {
    setGenLoading(true)
    try {
      const res = await api.generateDocs()
      if (res.success) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `Documentation generated successfully for ${res.tables_processed} table(s). You can download the artifacts below.`
        }])
        // Refresh artifacts list
        const list = await api.listArtifacts?.()
        if (list?.artifacts) setArtifacts(list.artifacts)
        setShowArtifacts(true)
      } else {
        alert('Failed to generate docs: ' + res.message)
      }
    } catch (err: any) {
      alert('Error: ' + err.message)
    } finally {
      setGenLoading(false)
    }
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: text }])
    setLoading(true)
    try {
      const history = messages.map((h) => ({ role: h.role, content: h.content }))
      const res = await api.chat(text, history)
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: res.response, sql: res.sql_suggestion },
      ])
    } catch (err) {
      console.error(err)
      let content = "Something went wrong."
      if (err instanceof Error) content = err.message
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: content,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerTop}>
          <h1>Chat</h1>
          <div>
            <button
              onClick={() => setShowArtifacts(!showArtifacts)}
              className={styles.toggleBtn}
            >
               {showArtifacts ? 'Hide Files' : `Show Files (${artifacts.length})`}
            </button>
            <button
              onClick={handleGenerateAllDocs}
              className={styles.genBtn}
              style={{ marginLeft: '10px' }}
              disabled={genLoading}
              title="Generate AI docs for all tables (improves chat answers)"
            >
              {genLoading ? 'Generating…' : 'Generate docs (all tables)'}
            </button>
          </div>
        </div>
        
        {showArtifacts && artifacts.length > 0 && (
          <div className={styles.artifacts}>
             <h3>Generated Artifacts</h3>
             <ul>
               {artifacts.map(f => (
                 <li key={f}>
                   <a href={api.getArtifactUrl?.(f)} target="_blank" rel="noreferrer" download>{f}</a>
                 </li>
               ))}
             </ul>
          </div>
        )}
        
        <p className={styles.hint}>Ask about your schema, relationships, or request SQL suggestions.</p>
      </div>
      <div className={styles.messages}>
        {messages.length === 0 && (
          <div className={styles.empty}>
            <p>Ask a question about your database schema.</p>
            <p className={styles.example}>e.g. &quot;Which tables have order data?&quot; or &quot;Show me how to join orders and customers&quot;</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={msg.role === 'user' ? styles.msgUser : styles.msgAssistant}>
            <div className={styles.msgContent}>
              {msg.role === 'assistant' ? (
                <div className={styles.markdown}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                </div>
              ) : (
                msg.content
              )}
              {msg.sql && (
                <div className={styles.sqlBlock}>
                  <button
                    type="button"
                    className={styles.copyBtn}
                    onClick={() => copySql(msg.sql ?? '', i)}
                  >
                    {copiedId === i ? 'Copied!' : 'Copy'}
                  </button>
                  <pre className={styles.sql}>{msg.sql}</pre>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className={styles.msgAssistant}>
            <div className={styles.msgContent}>Thinking…</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <form onSubmit={handleSubmit} className={styles.form}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your data..."
          className={styles.input}
          disabled={loading}
        />
        <button type="submit" className={styles.button} disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}
