export interface Session {
  token: string
  email: string
  role: string
}

export interface ChatResponse {
  reply?: string
  retrieved?: Array<{
    text: string
    metadata: Record<string, unknown>
    score?: number
  }>
  tool_calls?: Array<Record<string, unknown>>
}

