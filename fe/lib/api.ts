const API = process.env.NEXT_PUBLIC_API_URL

export interface Source {
  source: string
  law: string
  article: string
}

export interface StreamCallbacks {
  onConversationId: (id: string) => void
  onSources: (sources: Source[]) => void
  onToken: (token: string) => void
  onDone: () => void
  onError: (err: Error) => void
}

export async function streamChat(
  question: string,
  history: { role: string; content: string }[],
  conversationId: string | undefined,
  callbacks: StreamCallbacks
) {
  let response: Response

  try {
    response = await fetch(`${API}/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history, conversation_id: conversationId ?? null }),
    })
  } catch (err) {
    callbacks.onError(err instanceof Error ? err : new Error("Network error"))
    return
  }

  if (!response.ok) {
    callbacks.onError(new Error(`API error ${response.status}`))
    return
  }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const lines = decoder.decode(value, { stream: true }).split("\n")
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue
        if (line === "data: [DONE]") {
          callbacks.onDone()
          continue
        }
        const data = JSON.parse(line.slice(6))
        if (data.type === "conversation_id") callbacks.onConversationId(data.id)
        else if (data.type === "sources") callbacks.onSources(data.sources)
        else if (data.type === "token") callbacks.onToken(data.content)
      }
    }
  } catch (err) {
    callbacks.onError(err instanceof Error ? err : new Error("Stream error"))
  }
}
