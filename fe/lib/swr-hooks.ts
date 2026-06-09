import useSWR from "swr"

const API = process.env.NEXT_PUBLIC_API_URL

const fetcher = (url: string) =>
  fetch(url).then((r) => {
    if (!r.ok) throw new Error(`${r.status}`)
    return r.json()
  })

export function useUser() {
  return useSWR(`${API}/user/me`, fetcher)
}

export function useUsageQuota() {
  return useSWR(`${API}/user/quota`, fetcher)
}

export function useHistory(sessionId?: string) {
  return useSWR(
    sessionId ? `${API}/history?session=${sessionId}` : null,
    fetcher
  )
}

export interface ConversationSummary {
  id: string
  created_at: string
  preview: string
}

export function useConversations() {
  return useSWR<ConversationSummary[]>(`${API}/history/list`, fetcher, {
    refreshInterval: 5000,
  })
}
