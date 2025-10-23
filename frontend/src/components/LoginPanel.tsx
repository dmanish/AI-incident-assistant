import React, { useState } from 'react'
import { login } from '../api'
import type { Session } from '../types'

export default function LoginPanel({
  onAuthenticated
}: {
  onAuthenticated: (s: Session) => void
}) {
  const [email, setEmail] = useState('alice@company')
  const [password, setPassword] = useState('pass1')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await login(email, password)
      onAuthenticated({ token: res.token, email: res.email, role: res.role })
    } catch (err: any) {
      setError(err?.message ?? 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <h2>Sign in</h2>
      <form onSubmit={onSubmit} className="form">
        <label>Email</label>
        <input value={email} onChange={e => setEmail(e.target.value)} />
        <label>Password</label>
        <input type="password" value={password} onChange={e => setPassword(e.target.value)} />
        <button disabled={loading}>{loading ? 'Signing in…' : 'Sign in'}</button>
        {error && <div className="error">{error}</div>}
      </form>
      <div className="hint">
        Try <code>alice@company / pass1</code>, <code>bob@company / pass2</code>, <code>sam@company / pass3</code>
      </div>
    </div>
  )
}

