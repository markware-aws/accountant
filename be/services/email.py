import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@yourdomain.com")


def send_magic_link(to_email: str, magic_link: str) -> None:
    resend.Emails.send({
        "from": EMAIL_FROM,
        "to": to_email,
        "subject": "Σύνδεση στο AccountantAI",
        "html": f"""
            <p>Κάντε κλικ στον παρακάτω σύνδεσμο για να συνδεθείτε:</p>
            <p><a href="{magic_link}">Σύνδεση στο AccountantAI</a></p>
            <p>Ο σύνδεσμος λήγει σε 1 ώρα.</p>
        """,
    })


def send_welcome(to_email: str) -> None:
    resend.Emails.send({
        "from": EMAIL_FROM,
        "to": to_email,
        "subject": "Καλωσήρθατε στο AccountantAI",
        "html": "<p>Ο λογαριασμός σας ενεργοποιήθηκε με επιτυχία.</p>",
    })
