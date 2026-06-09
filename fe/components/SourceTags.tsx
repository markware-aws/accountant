import CitationPill from "./CitationPill"
import type { Source } from "@/lib/api"

interface SourceTagsProps {
  sources: Source[]
}

export default function SourceTags({ sources }: SourceTagsProps) {
  if (!sources.length) return null

  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {sources.map((s, i) => (
        <CitationPill key={i} source={s} index={i} />
      ))}
    </div>
  )
}
