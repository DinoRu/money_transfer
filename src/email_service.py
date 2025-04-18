import resend

resend.api_key = "re_BWn9sKQm_LRoyRaTHoFYWEpZcD6RPziFD"


def send_email(to_email: str, subject: str, html_content: str):
    return resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": [to_email],
        "subject": subject,
        "html": html_content,
    })