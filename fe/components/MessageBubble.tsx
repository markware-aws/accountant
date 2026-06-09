import { cn } from "@/lib/utils"
import SourceTags from "./SourceTags"
import type { Source } from "@/lib/api"

export interface Message {
  role: "user" | "assistant"
  content: string
  sources?: Source[]
}

interface MessageBubbleProps {
  message: Message
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user"

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-primary text-primary-foreground rounded-br-sm"
            : "bg-muted text-foreground rounded-bl-sm"
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {!isUser && message.sources && (
          <SourceTags sources={message.sources} />
        )}
      </div>
    </div>
  )
}
