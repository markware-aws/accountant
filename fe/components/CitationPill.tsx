import { cn } from "@/lib/utils"
import type { Source } from "@/lib/api"

interface CitationPillProps {
  source: Source
  index: number
}

export default function CitationPill({ source, index }: CitationPillProps) {
  const label = [source.law, source.article].filter(Boolean).join(" ")

  return (
    <span
      title={source.source}
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5",
        "text-xs font-medium text-muted-foreground bg-muted",
        "cursor-default select-none"
      )}
    >
      <span className="text-primary font-semibold">[{index + 1}]</span>
      {label || source.source}
    </span>
  )
}
