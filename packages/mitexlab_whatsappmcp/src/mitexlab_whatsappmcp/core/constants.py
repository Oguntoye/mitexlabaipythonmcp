from ..env import settings

REDIS_OAUTH_CRED_PREFIX = f"{settings.WHICHENV}_wa_oauth_cred:"

WA_GRAPH_API_URL = "https://graph.facebook.com"
WA_API_VERSION = "v23.0"

# Message types
MESSAGE_TYPE_TEXT = "text"
MESSAGE_TYPE_IMAGE = "image"
MESSAGE_TYPE_DOCUMENT = "document"
MESSAGE_TYPE_AUDIO = "audio"
MESSAGE_TYPE_VIDEO = "video"
MESSAGE_TYPE_LOCATION = "location"
MESSAGE_TYPE_CONTACTS = "contacts"
MESSAGE_TYPE_TEMPLATE = "template"
MESSAGE_TYPE_INTERACTIVE = "interactive"
MESSAGE_TYPE_STICKER = "sticker"

WHATSAPP_SUPPORTED_MESSAGE_TYPES = {
    MESSAGE_TYPE_TEXT,
    MESSAGE_TYPE_IMAGE,
    MESSAGE_TYPE_DOCUMENT,
    MESSAGE_TYPE_AUDIO,
    MESSAGE_TYPE_VIDEO,
    MESSAGE_TYPE_LOCATION,
    MESSAGE_TYPE_CONTACTS,
    MESSAGE_TYPE_TEMPLATE,
    MESSAGE_TYPE_INTERACTIVE,
    MESSAGE_TYPE_STICKER,
}

# Interactive message types
INTERACTIVE_TYPE_BUTTON = "button"
INTERACTIVE_TYPE_LIST = "list"

# Template types
TEMPLATE_CATEGORY_MARKETING = "MARKETING"
TEMPLATE_CATEGORY_UTILITY = "UTILITY"

# Media types
MEDIA_TYPE_IMAGE = "image"
MEDIA_TYPE_DOCUMENT = "document"
MEDIA_TYPE_AUDIO = "audio"
MEDIA_TYPE_VIDEO = "video"
MEDIA_TYPE_STICKER = "sticker"

WHATSAPP_SUPPORTED_MEDIA_TYPES = {
    MEDIA_TYPE_IMAGE,
    MEDIA_TYPE_DOCUMENT,
    MEDIA_TYPE_AUDIO,
    MEDIA_TYPE_VIDEO,
    MEDIA_TYPE_STICKER,
}

# Business profile fields
BUSINESS_PROFILE_FIELDS = [
    "id",
    "about",
    "address",
    "description",
    "email",
    "messaging_product",
    "name",
    "phone_number",
    "profile_picture_url",
    "websites",
    "vertical",
]

# Webhook event types
WEBHOOK_EVENT_MESSAGE = "messages"
WEBHOOK_EVENT_STATUS = "message_status"
WEBHOOK_EVENT_ACCOUNT_UPDATE = "account_update"
WEBHOOK_EVENT_BUSINESS_UPDATE = "business_update"
