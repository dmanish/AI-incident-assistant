import React, { useRef, useState } from 'react'
import { chat } from '../api'
import type { Session } from '../types'
import MessageInput from './MessageInput'

type Msg = { role: 'user' | 'assistant'; content: string }

export default function ChatPane({
  session,
  onLogout
}: {
  session: Session
  onLogout: () => void
}) {
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: 'assistant',
      content:
        'Ask about policies or run tools.\nExample: “Show me today’s failed login attempts for username jdoe”.'
    }
  ])
  const listRef = useRef<HTMLDivElement>(null)

  async function send(text: string) {
    if (!text.trim()) return
    setMessages(prev => [...prev, { role: 'user', content: text }])
    try {
      const res = await chat(session.token, text)
      const pretty = res.reply || '(no reply)'
      setMessages(prev => [...prev, { role: 'assistant', content: pretty }])
      queueMicrotask(() => {
        const el = listRef.current
        if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
      })
    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error: ' + (e?.message ?? 'unknown') }])
    }
  }

  return (
    <div className="chat-layout">
      <div className="toolbar">
        <div>Signed in as <b>{session.email}</b> ({session.role})</div>
        <button onClick={onLogout}>Log out</button>
      </div>

      <div className="chat-list" ref={listRef}>
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <pre>{m.content}</pre>
          </div>
        ))}
      </div>

      <MessageInput onSend={send} />
    </div>
  )
}

