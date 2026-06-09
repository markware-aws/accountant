import { useRouter } from "next/router"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useState } from "react"

export default function Home() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  async function requestMagicLink() {
    if (!email.trim()) return
    setLoading(true)
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/magic-link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      })
      setSent(true)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-sm space-y-6 px-4">
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">AccountantAI</h1>
          <p className="text-sm text-muted-foreground">
            Βοηθός ελληνικού φορολογικού δικαίου
          </p>
        </div>

        {sent ? (
          <p className="text-center text-sm text-muted-foreground">
            Στείλαμε σύνδεσμο στο <strong>{email}</strong>. Ελέγξτε τα email σας.
          </p>
        ) : (
          <div className="space-y-3">
            <Input
              type="email"
              placeholder="email@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && requestMagicLink()}
            />
            <Button
              className="w-full"
              onClick={requestMagicLink}
              disabled={loading}
            >
              {loading ? "Αποστολή..." : "Σύνδεση με magic link"}
            </Button>
          </div>
        )}

        {/* Dev shortcut — remove before production */}
        <div className="text-center">
          <button
            className="text-xs text-muted-foreground underline underline-offset-2"
            onClick={() => router.push("/chat")}
          >
            Είσοδος χωρίς σύνδεση (dev)
          </button>
        </div>
      </div>
    </main>
  )
}
