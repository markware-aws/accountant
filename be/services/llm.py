import os
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

_anthropic = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
_openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
Είσαι ειδικός βοηθός ελληνικού φορολογικού δικαίου για λογιστές.

Κανόνες:
- Απάντα ΜΟΝΟ βάσει των παρεχόμενων αποσπασμάτων νόμων
- Κάθε ισχυρισμός πρέπει να αναφέρει τη συγκεκριμένη πηγή [π.χ. άρθρο 58 ν.4172/2013]
- Αν δεν βρίσκεις σαφή απάντηση στα αποσπάσματα, πες το ξεκάθαρα
- Μη φτιάχνεις ποτέ νόμους ή παραπομπές
- Γράφε σε επαγγελματικά ελληνικά
""".strip()


async def stream_response(question: str, context: str, history: list[dict]):
    messages = [
        *history,
        {
            "role": "user",
            "content": f"Αποσπάσματα νόμων:\n{context}\n\nΕρώτηση: {question}",
        },
    ]

    if ENVIRONMENT == "prod":
        async with _anthropic.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text
    else:
        stream = await _openai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
            stream=True,
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
