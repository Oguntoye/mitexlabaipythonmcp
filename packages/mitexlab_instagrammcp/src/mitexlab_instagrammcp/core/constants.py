# from datetime import datetime, timedelta
# import json
# from ..tools.auth import redis_client
from ..env import settings

REDIS_OAUTH_CRED_PREFIX = f"{settings.WHICHENV}_ig_oauth_cred:"

 # Instagram API URLs
# IG_OAUTH_URL = "https://api.instagram.com/oauth/authorize"
# IG_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
# IG_GRAPH_URL = "https://graph.instagram.com"