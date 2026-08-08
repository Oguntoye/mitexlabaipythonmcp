import json
from typing import Any, Dict, List, Optional
import httpx


class InstagramAPI:
    """Instagram API client for Instagram Login"""

    def __init__(
        self,
        access_token: str,
        app_id: str = "nill",
        app_secret: str = "nill",
    ) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = access_token
        self.version = "v23.0"
        self.base_url = "https://graph.instagram.com/v23.0"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("HTTP client not initialized. Use 'async with InstagramAPI(...)'.")
        return self._client

    async def __aenter__(self):
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=httpx.Timeout(30.0))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
            self._client = None

    def _debug_request(self, url: str, data: Dict) -> None:
        print("\n====== INSTAGRAM API REQUEST ======")
        print(f"URL: {self.base_url}{url}")
        print(f"PAYLOAD: {json.dumps(data, indent=2)}")
        print("===================================\n")

    def _debug_response(self, response: httpx.Response) -> None:
        print("\n====== INSTAGRAM API RESPONSE ======")
        print(f"STATUS: {response.status_code}")
        print(f"BODY: {response.text}")
        print("====================================\n")

    # ---------------- Core methods ---------------- #
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        data = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
        response = await self.client.post("https://api.instagram.com/oauth/access_token", data=data)
        response.raise_for_status()
        return response.json()

    async def get_long_lived_token(self, short_lived_token: str) -> Dict[str, Any]:
        params = {
            "grant_type": "ig_exchange_token",
            "client_secret": self.app_secret,
            "access_token": short_lived_token,
        }
        response = await self.client.get("/access_token", params=params)
        response.raise_for_status()
        return response.json()

    async def refresh_token(self) -> Dict[str, Any]:
        params = {"grant_type": "ig_refresh_token", "access_token": self.access_token}
        response = await self.client.get("/refresh_access_token", params=params)
        response.raise_for_status()
        return response.json()

    async def test_connection(self) -> Dict[str, Any]:
        params = {"fields": "user_id,username", "access_token": self.access_token}
        response = await self.client.get("/me", params=params)
        response.raise_for_status()
        return response.json()

    async def get_user_profile(
        self,
        fields: str = "id,user_id,username,name,account_type,profile_picture_url,followers_count,follows_count,media_count",
    ) -> Dict[str, Any]:
        params = {"fields": fields, "access_token": self.access_token}
        response = await self.client.get("/me", params=params)
        response.raise_for_status()
        return response.json()

    async def get_user_media(
        self,
        fields: str = "id,media_type,media_url,caption,permalink,timestamp,thumbnail_url",
        limit: int = 25,
        before: str | None = None,
        after: str | None = None,
    ) -> Dict[str, Any]:
        params = {"fields": fields, "limit": limit, "access_token": self.access_token}
        if before:
            params["before"] = before
        if after:
            params["after"] = after
        response = await self.client.get("/me/media", params=params)
        response.raise_for_status()
        return response.json()

    async def get_media_details(
        self,
        media_id: str,
        fields: str = "id,media_type,media_url,caption,permalink,timestamp,thumbnail_url,children",
    ) -> Dict[str, Any]:
        params = {"fields": fields, "access_token": self.access_token}
        response = await self.client.get(f"/{media_id}", params=params)
        response.raise_for_status()
        return response.json()

    async def get_media_children(self, media_id: str, fields: str = "id,media_type,media_url,thumbnail_url") -> Dict[str, Any]:
        params = {"fields": fields, "access_token": self.access_token}
        response = await self.client.get(f"/{media_id}/children", params=params)
        response.raise_for_status()
        return response.json()

    async def create_media_container(
        self,
        image_url: str,
        caption: Optional[str] = None,
        location_id: Optional[str] = None,
        user_tags: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {"image_url": image_url, "access_token": self.access_token}
        if caption:
            data["caption"] = caption
        if location_id:
            data["location_id"] = location_id
        if user_tags:
            data["user_tags"] = json.dumps(user_tags)
        response = await self.client.post("/me/media", data=data)
        response.raise_for_status()
        return response.json()

    async def create_carousel_container(
        self,
        children_ids: List[str],
        caption: Optional[str] = None,
        location_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "access_token": self.access_token,
        }
        if caption:
            data["caption"] = caption
        if location_id:
            data["location_id"] = location_id
        response = await self.client.post("/me/media", data=data)
        response.raise_for_status()
        return response.json()

    async def create_video_container(
        self,
        video_url: str,
        thumbnail_url: Optional[str] = None,
        caption: Optional[str] = None,
        location_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {"media_type": "VIDEO", "video_url": video_url, "access_token": self.access_token}
        if thumbnail_url:
            data["thumbnail_url"] = thumbnail_url
        if caption:
            data["caption"] = caption
        if location_id:
            data["location_id"] = location_id
        response = await self.client.post("/me/media", data=data)
        response.raise_for_status()
        return response.json()

    async def create_reels_container(
        self,
        video_url: str,
        thumbnail_url: Optional[str] = None,
        caption: Optional[str] = None,
        location_id: Optional[str] = None,
        share_to_feed: bool = True,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "media_type": "REELS",
            "video_url": video_url,
            "share_to_feed": str(share_to_feed).lower(),
            "access_token": self.access_token,
        }
        if thumbnail_url:
            data["thumbnail_url"] = thumbnail_url
        if caption:
            data["caption"] = caption
        if location_id:
            data["location_id"] = location_id
        response = await self.client.post("/me/media", data=data)
        response.raise_for_status()
        return response.json()

    async def create_story_container(self, image_url: str) -> Dict[str, Any]:
        data = {"image_url": image_url, "media_type": "STORIES", "access_token": self.access_token}
        response = await self.client.post("/me/media", data=data)
        response.raise_for_status()
        return response.json()

    async def publish_media(self, creation_id: str) -> Dict[str, Any]:
        data = {"creation_id": creation_id, "access_token": self.access_token}
        response = await self.client.post("/me/media_publish", data=data)
        response.raise_for_status()
        return response.json()

    async def get_media_comments(
        self,
        media_id: str,
        fields: str = "id,text,timestamp,username,like_count,replies",
        limit: int = 25,
    ) -> Dict[str, Any]:
        params = {"fields": fields, "limit": limit, "access_token": self.access_token}
        response = await self.client.get(f"/{media_id}/comments", params=params)
        response.raise_for_status()
        return response.json()

    async def create_comment(self, media_id: str, message: str) -> Dict[str, Any]:
        data = {"message": message, "access_token": self.access_token}
        response = await self.client.post(f"/{media_id}/comments", data=data)
        response.raise_for_status()
        return response.json()

    async def reply_to_comment(self, comment_id: str, message: str) -> Dict[str, Any]:
        data = {"message": message, "access_token": self.access_token}
        response = await self.client.post(f"/{comment_id}/replies", data=data)
        response.raise_for_status()
        return response.json()

    async def delete_comment(self, comment_id: str) -> Dict[str, Any]:
        params = {"access_token": self.access_token}
        response = await self.client.delete(f"/{comment_id}", params=params)
        response.raise_for_status()
        return response.json()

    async def hide_comment(self, comment_id: str, hide: bool = True) -> Dict[str, Any]:
        data = {"hide": str(hide).lower(), "access_token": self.access_token}
        response = await self.client.post(f"/{comment_id}", data=data)
        response.raise_for_status()
        return response.json()

    async def get_media_insights(self, media_id: str, metrics: str = "impressions,reach,engagement") -> Dict[str, Any]:
        params = {"metric": metrics, "access_token": self.access_token}
        response = await self.client.get(f"/{media_id}/insights", params=params)
        response.raise_for_status()
        return response.json()

    async def get_user_insights(
        self,
        metrics: str = "follower_count,impressions,profile_views,reach",
        period: str = "day",
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"metric": metrics, "period": period, "access_token": self.access_token}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        response = await self.client.get("/me/insights", params=params)
        response.raise_for_status()
        return response.json()

    async def get_mentioned_media(
        self,
        fields: str = "id,media_type,media_url,caption,permalink,timestamp",
        limit: int = 25,
    ) -> Dict[str, Any]:
        params = {"fields": fields, "limit": limit, "access_token": self.access_token}
        response = await self.client.get("/me/mentioned_media", params=params)
        response.raise_for_status()
        return response.json()

    # ---------------- Messaging Methods ---------------- #
    # User have dm business before
    async def send_text_directmessage(self, recipient_id: str, text: str) -> Dict[str, Any]:
        """Send a plain text DM to a user via their IGSID."""
        data = {"recipient": {"id": recipient_id}, "message": {"text": text}}
        response = await self.client.post(
            "/me/messages",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json=data,
        )
        response.raise_for_status()
        return response.json()

    async def send_media_directmessage(self, recipient_id: str, media_type: str, url: str) -> Dict[str, Any]:
        """Send image/audio/video DM to a user via their IGSID."""
        if media_type not in {"image", "audio", "video"}:
            raise ValueError("media_type must be one of: image, audio, video")
        data = {
            "recipient": {"id": recipient_id},
            "message": {"attachment": {"type": media_type, "payload": {"url": url}}},
        }
        response = await self.client.post(
            "/me/messages",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json=data,
        )
        response.raise_for_status()
        return response.json()

    async def send_button_template(self, recipient_id: str, text: str, buttons: List[Dict]) -> Dict[str, Any]:
        """
        Send a button template DM to a user via their IGSID.
        - Use commenter's IGSID (fromuserid from webhook) as recipient_id
        - Comment on your post opens the 24hr window automatically
        - Max 3 buttons, types: 'postback' or 'web_url'
        """
        if len(buttons) > 3:
            raise ValueError("Button template supports max 3 buttons")
        data = {
            "recipient": {"id": recipient_id},
            "message": {
                "attachment": {
                    "type": "template",
                    "payload": {
                        "template_type": "button",
                        "text": text,
                        "buttons": buttons,
                    },
                }
            },
        }
        self._debug_request("/me/messages", data)
        response = await self.client.post(
            "/me/messages",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json=data,
        )
        self._debug_response(response)
        response.raise_for_status()
        return response.json()

    # ##from comment >>  user may have never dm business before
    async def send_private_reply(self, comment_id: str, text: str) -> Dict[str, Any]:
        """
        Send a plain text private reply to a commenter via comment_id.
        - Only plain text supported
        - Max one private reply per comment
        - Must be within 7 days of the comment
        """
        data = {
            "recipient": {"comment_id": comment_id},
            "message": {"text": text},
        }
        self._debug_request("/me/messages", data)
        response = await self.client.post(
            "/me/messages",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json=data,
        )
        self._debug_response(response)
        if response.status_code == 500:
            body = response.json()
            if body.get("error", {}).get("error_subcode") == 2534023:
                raise ValueError("Already replied to this comment privately. Instagram only allows one private reply per comment.")
        response.raise_for_status()
        return response.json()
    
    async def send_private_reply_with_buttons(self, comment_id: str, text: str, buttons: List[Dict]) -> Dict[str, Any]:
        """
        Send a button template as a private reply to a commenter via comment_id.
        - Max 3 buttons, types: 'postback' or 'web_url'
        - Only one private reply allowed per comment
        - Must be within 7 days of the comment
        - When user taps a button, the 24hr messaging window opens
        """
        if len(buttons) > 3:
            raise ValueError("Button template supports max 3 buttons")
        data = {
            "recipient": {"comment_id": comment_id},
            "message": {
                "attachment": {
                    "type": "template",
                    "payload": {
                        "template_type": "button",
                        "text": text,
                        "buttons": buttons,
                    },
                }
            },
        }
        self._debug_request("/me/messages", data)
        response = await self.client.post(
            "/me/messages",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json=data,
        )
        self._debug_response(response)
        if response.status_code == 500:
            body = response.json()
            if body.get("error", {}).get("error_subcode") == 2534023:
                raise ValueError("Already replied to this comment privately. Instagram only allows one private reply per comment.")
        response.raise_for_status()
        return response.json()

    # ---------------- All Comments Fetching Methods ---------------- #
    async def get_all_comments_from_media(self, media_ids: List[str]) -> Dict[str, Any]:
        all_comments = {}
        for media_id in media_ids:
            comments = await self.get_media_comments(media_id)
            all_comments[media_id] = comments
        return all_comments

    async def get_all_user_comments(self) -> Dict[str, Any]:
        media_response = await self.get_user_media(limit=100)
        media_ids = [item['id'] for item in media_response.get('data', [])]
        return await self.get_all_comments_from_media(media_ids)