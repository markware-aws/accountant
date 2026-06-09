from fastapi import APIRouter, HTTPException
from schemas import MagicLinkRequest
from services.email import send_magic_link

router = APIRouter()


@router.post("/magic-link")
async def request_magic_link(body: MagicLinkRequest):
    """
    Supabase Auth handles the actual magic link generation and token validation.
    This endpoint is a hook to send the email via Resend instead of Supabase's
    built-in email provider.

    Wire this up in the Supabase dashboard under:
    Authentication → Email Templates → Hook URL
    """
    # In production, Supabase calls this hook with the generated magic link.
    # For now this is a placeholder that accepts the email and link from the hook payload.
    raise HTTPException(status_code=501, detail="Configure Supabase auth hook to provide the magic link")


@router.post("/send-magic-link")
async def send_link(body: MagicLinkRequest, link: str):
    """Internal — called by the Supabase webhook with the generated link."""
    send_magic_link(body.email, link)
    return {"ok": True}
