import React, { useEffect, useRef, useState } from 'react'
import ScrollButton from './ScrollButton'

export default function MessageInput({ onSend }: { onSend: (text: string) => void }) {
  const [text, setText] = useState('')
  const taRef = useRef<HTMLTextAreaElement | null>(null)
  const [showScroll, setShowScroll] = useState(false)

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    const v = e.target.value
    setText(v)
    const ta = taRef.current
    if (!ta) return
    setShowScroll(ta.scrollHeight > ta.clientHeight + 2)
  }

  function scrollToBottom() {
    const ta = taRef.current
    if (!ta) return
    ta.scrollTo({ top: ta.scrollHeight, behavior: 'smooth' })
  }

  function submit() {
    onSend(text)
    setText('')
    setShowScroll(false)
  }

  useEffect(() => {
    const resizeObserver = new ResizeObserver(() => {
      const ta = taRef.current
      if (!ta) return
      setShowScroll(ta.scrollHeight > ta.clientHeight + 2)
    })
    if (taRef.current) resizeObserver.observe(taRef.current)
    return () => resizeObserver.disconnect()
  }, [])

  return (
    <div className="composer">
      <div className="input-wrap">
        <textarea
          ref={taRef}
          className="input"
          placeholder="Ask about policies or run tools, e.g. “Show me today’s failed login attempts for username jdoe”."
          value={text}
          onChange={handleInput}
          rows={4}
        />
        {showScroll && <ScrollButton onClick={scrollToBottom} />}
      </div>
      <div className="actions">
        <button onClick={submit}>Send</button>
      </div>
    </div>
  )
}

