import { useState, useRef, useEffect, useCallback } from "react"
import { useRouter } from "next/router"
import MessageBubble, { type Message } from "@/components/MessageBubble"
import { streamChat } from "@/lib/api"
import { useHistory, useConversations } from "@/lib/swr-hooks"
import { cn } from "@/lib/utils"
import { PlusIcon, SendHorizontal, ScaleIcon } from "lucide-react"

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return "μόλις τώρα"
  if (m < 60) return `${m}λ`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}ω`
  const d = Math.floor(h / 24)
  if (d < 7) return `${d}μ`
  return new Date(iso).toLocaleDateString("el-GR", { day: "numeric", month: "short" })
}

export default function ChatPage() {
  const router = useRouter()
  const sessionId = router.query.session as string | undefined

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const { data: historyData } = useHistory(sessionId)
  const { data: conversations, mutate: mutateConversations } = useConversations()

  useEffect(() => {
    if (historyData?.messages) setMessages(historyData.messages)
  }, [historyData])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Auto-grow textarea fallback for browsers without field-sizing support
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 192)}px`
  }, [input])

  const send = useCallback(async () => {
    if (!input.trim() || loading) return
    const question = input.trim()
    setInput("")
    setLoading(true)
    setError(null)

    setMessages((prev) => [...prev, { role: "user", content: question }])
    let assistantMsg: Message = { role: "assistant", content: "", sources: [] }
    setMessages((prev) => [...prev, assistantMsg])

    await streamChat(
      question,
      messages.map((m) => ({ role: m.role, content: m.content })),
      sessionId,
      {
        onConversationId: (id) => {
          if (!sessionId) {
            router.replace({ query: { session: id } }, undefined, { shallow: true })
            mutateConversations()
          }
        },
        onSources: (sources) => {
          assistantMsg = { ...assistantMsg, sources }
          setMessages((prev) => [...prev.slice(0, -1), assistantMsg])
        },
        onToken: (token) => {
          assistantMsg = { ...assistantMsg, content: assistantMsg.content + token }
          setMessages((prev) => [...prev.slice(0, -1), assistantMsg])
        },
        onDone: () => {
          setLoading(false)
          mutateConversations()
        },
        onError: (err) => {
          setError(err.message)
          setLoading(false)
          setMessages((prev) => prev.slice(0, -1))
        },
      }
    )
  }, [input, loading, messages, sessionId, router, mutateConversations])

  function newChat() {
    setMessages([])
    setInput("")
    setError(null)
    router.push("/chat", undefined, { shallow: true })
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="flex h-screen overflow-hidden bg-white">

      {/* ── Sidebar ─────────────────────────────────────── */}
      <aside
        className="sidebar-scroll flex flex-col overflow-y-auto flex-shrink-0"
        style={{
          width: 272,
          background: "hsl(var(--sidebar-bg))",
          borderRight: "1px solid hsl(var(--sidebar-border))",
        }}
      >
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-4 py-5 border-b"
          style={{ borderColor: "hsl(var(--sidebar-border))" }}>
          <div className="flex items-center justify-center w-7 h-7 rounded-md"
            style={{ background: "hsl(var(--primary))" }}>
            <ScaleIcon className="w-4 h-4 text-white" />
          </div>
          <span className="text-sm font-semibold tracking-tight"
            style={{ color: "hsl(210 20% 92%)" }}>
            AccountantAI
          </span>
        </div>

        {/* New chat */}
        <div className="px-3 pt-3 pb-2">
          <button
            onClick={newChat}
            className="flex items-center gap-2 w-full px-3 py-2 rounded-md text-sm font-medium transition-colors"
            style={{
              color: "hsl(var(--sidebar-fg))",
              background: "hsl(var(--sidebar-hover))",
            }}
            onMouseEnter={e => (e.currentTarget.style.background = "hsl(220 16% 22%)")}
            onMouseLeave={e => (e.currentTarget.style.background = "hsl(var(--sidebar-hover))")}
          >
            <PlusIcon className="w-3.5 h-3.5" />
            Νέα συνομιλία
          </button>
        </div>

        {/* History label */}
        <p className="px-4 pt-2 pb-1 text-xs font-medium uppercase tracking-widest"
          style={{ color: "hsl(220 16% 35%)" }}>
          Ιστορικό
        </p>

        {/* Conversation list */}
        <nav className="flex-1 px-2 pb-4 space-y-0.5">
          {!conversations || conversations.length === 0 ? (
            <p className="px-3 py-2 text-xs" style={{ color: "hsl(220 16% 35%)" }}>
              Δεν υπάρχουν συνομιλίες
            </p>
          ) : (
            conversations.map((conv) => {
              const isActive = conv.id === sessionId
              return (
                <button
                  key={conv.id}
                  onClick={() => router.push(`/chat?session=${conv.id}`)}
                  className="group w-full text-left px-3 py-2.5 rounded-md transition-colors"
                  style={{
                    background: isActive
                      ? "hsl(var(--sidebar-active))"
                      : "transparent",
                    color: isActive
                      ? "hsl(var(--sidebar-active-fg))"
                      : "hsl(var(--sidebar-fg))",
                  }}
                  onMouseEnter={e => {
                    if (!isActive) e.currentTarget.style.background = "hsl(var(--sidebar-hover))"
                  }}
                  onMouseLeave={e => {
                    if (!isActive) e.currentTarget.style.background = "transparent"
                  }}
                >
                  <p className="text-xs leading-snug line-clamp-2 mb-1">
                    {conv.preview}
                  </p>
                  <p className="text-xs opacity-40">
                    {formatRelative(conv.created_at)}
                  </p>
                </button>
              )
            })
          )}
        </nav>
      </aside>

      {/* ── Main ────────────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0">

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-8">
          <div className="max-w-2xl mx-auto space-y-5">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-64 gap-3 text-center">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                  style={{ background: "hsl(158 40% 94%)" }}>
                  <ScaleIcon className="w-5 h-5" style={{ color: "hsl(var(--primary))" }} />
                </div>
                <p className="text-sm" style={{ color: "hsl(var(--muted-foreground))" }}>
                  Ρωτήστε οτιδήποτε σχετικά με<br />το ελληνικό φορολογικό δίκαιο.
                </p>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className="message-in">
                <MessageBubble message={msg} />
              </div>
            ))}

            {loading && messages[messages.length - 1]?.content === "" && (
              <div className="flex justify-start message-in">
                <div className="px-4 py-3 rounded-2xl rounded-bl-sm text-sm"
                  style={{ background: "hsl(var(--muted))" }}>
                  <span className="flex gap-1 items-center"
                    style={{ color: "hsl(var(--muted-foreground))" }}>
                    <span className="animate-bounce [animation-delay:0ms]">·</span>
                    <span className="animate-bounce [animation-delay:150ms]">·</span>
                    <span className="animate-bounce [animation-delay:300ms]">·</span>
                  </span>
                </div>
              </div>
            )}

            {error && (
              <p className="text-center text-xs text-red-400">{error}</p>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input */}
        <div className="px-6 pb-6 pt-2">
          <div className="max-w-2xl mx-auto">
            <div
              className="flex items-end gap-3 rounded-xl border px-4 py-3 shadow-sm"
              style={{
                borderColor: "hsl(var(--border))",
                background: "#fff",
                boxShadow: "0 1px 6px rgba(0,0,0,0.06)",
              }}
            >
              <textarea
                ref={textareaRef}
                className="auto-textarea flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground leading-relaxed"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ρωτήστε για φορολογικό θέμα… (Enter για αποστολή, Shift+Enter για νέα γραμμή)"
                disabled={loading}
                rows={2}
              />
              <button
                onClick={send}
                disabled={loading || !input.trim()}
                className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-lg transition-all"
                style={{
                  background: input.trim() && !loading
                    ? "hsl(var(--primary))"
                    : "hsl(var(--muted))",
                  color: input.trim() && !loading
                    ? "#fff"
                    : "hsl(var(--muted-foreground))",
                }}
              >
                <SendHorizontal className="w-4 h-4" />
              </button>
            </div>
            <p className="text-center text-xs mt-2" style={{ color: "hsl(var(--muted-foreground))" }}>
              Οι απαντήσεις βασίζονται αποκλειστικά στη νομοθεσία της βάσης δεδομένων.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
