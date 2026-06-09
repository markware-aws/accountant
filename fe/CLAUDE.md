# Frontend — Claude Code Guide

Next.js 16 frontend for accountantAI. Static export, Pages Router.

## Stack

- **Next.js 16**, React 19, TypeScript
- **Router**: Pages Router — no App Router
- **Build**: `output: "export"` (static files, no server)
- **UI**: shadcn-style components in `components/ui/` + Tailwind CSS
- **Data fetching**: SWR for REST/mutations, native `fetch` for SSE streaming
- **Auth**: Supabase JS client (client-side only)

## Running locally

```bash
# From fe/
cp .env.local.example .env.local   # fill in values
npm install
npm run dev                         # http://localhost:3000
```

## Critical rules

**No `/pages/api/` routes** — `output: "export"` removes all server-side code after build. API routes do not exist. Never add them.

**All API calls go directly to `NEXT_PUBLIC_API_URL`** — the FastAPI backend. There is no Next.js proxy layer.

**No dynamic route segments** — static export cannot generate `[id]` pages. Use query params instead: `/chat?session=xxx` not `/chat/[session]`.

**SWR is for REST only** — use it for user profile, quota, history. The chat stream uses `streamChat()` from `lib/api.ts` (native fetch + ReadableStream). Never wrap SSE in SWR.

## Key files

| File | Purpose |
|---|---|
| `pages/index.tsx` | Magic link login page + dev bypass link |
| `pages/chat.tsx` | Main chat UI — reads `?session=` query param |
| `pages/_app.tsx` | Global CSS import |
| `components/MessageBubble.tsx` | Renders user/assistant messages |
| `components/CitationPill.tsx` | Single source citation badge |
| `components/SourceTags.tsx` | Row of CitationPills attached to a message |
| `components/ui/button.tsx` | shadcn-style Button |
| `components/ui/input.tsx` | shadcn-style Input |
| `lib/api.ts` | `streamChat()` — SSE stream with onSources/onToken/onDone/onError callbacks |
| `lib/swr-hooks.ts` | `useUser()`, `useUsageQuota()`, `useHistory(sessionId)` |
| `lib/utils.ts` | `cn()` — clsx + tailwind-merge |
| `styles/globals.css` | Tailwind directives + CSS custom properties (design tokens) |
| `next.config.js` | `output: "export"`, `trailingSlash: true` |

## Adding shadcn components

Components live in `components/ui/`. Add new ones manually following the pattern in `button.tsx` and `input.tsx` — CVA for variants, `cn()` for class merging, `React.forwardRef`.

## Environment variables

All env vars must be prefixed `NEXT_PUBLIC_` to be available in the browser (static export has no server-side env).

```
NEXT_PUBLIC_API_URL            FastAPI backend URL
NEXT_PUBLIC_SUPABASE_URL       Supabase project URL
NEXT_PUBLIC_SUPABASE_ANON_KEY  Supabase anon key
```

## Build output

`npm run build` writes static files to `out/`. Deploy to S3 + CloudFront or any static host.
