from ..env import settings

REDIS_IMAP_AUTH_CRED_PREFIX = f"{settings.WHICHENV}_mailer_imap_auth_cred:"
REDIS_SMTP_AUTH_CRED_PREFIX = f"{settings.WHICHENV}_mailer_smtp_auth_cred:"

# REDIS_EMAIL_TEMPLATE_PREFIX = f"{settings.WHICHENV}_mailer_email_template:"
# REDIS_AUTO_REPLY_PREFIX = f"{settings.WHICHENV}_mailer_auto_reply:"
