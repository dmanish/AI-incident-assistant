import React, { useEffect, useState } from 'react'
import { health } from './api'
import type { Session } from './types'
import LoginPanel from './components/LoginPanel'
import ChatPane from './components/ChatPane'

export default function App() {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null)
  const [session, setSession] = useState<Session | null>(null)

  useEffect(() => {
    health().then(setIsHealthy).catch(() => setIsHealthy(false))
  }, [])

  return (
    <div className="container">
      <header>
        <h1>AI Incident Assistant</h1>
        <div className={`pill ${isHealthy ? 'ok' : 'bad'}`}>
          API: {isHealthy === null ? 'checking…' : isHealthy ? 'healthy' : 'down'}
        </div>
      </header>

      {!session ? (
        <LoginPanel onAuthenticated={setSession} />
      ) : (
        <ChatPane session={session} onLogout={() => setSession(null)} />
      )}

      <footer>
        <small>Demo — RAG + log queries with RBAC & audit logging</small>
      </footer>
    </div>
  )
}

