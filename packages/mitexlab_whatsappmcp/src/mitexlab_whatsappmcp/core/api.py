import asyncio
from typing import Any, Dict, List, Optional
import httpx
from .constants import WA_API_VERSION, WA_GRAPH_API_URL

import re


class WhatsAppAPI:
    """WhatsApp Cloud API client for business messaging"""

    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        business_account_id: str,
    ) -> None:
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.business_account_id = business_account_id
        self.base_url = f"{WA_GRAPH_API_URL}/{WA_API_VERSION}"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "HTTP client not initialized. Use 'async with WhatsAppAPI(...)'."
            )
        return self._client

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(30.0),
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
            self._client = None

    def _sanitize_flow_json(self, flow_json: Dict[str, Any]) -> Dict[str, Any]:
        flow_json["version"] = "7.3"

        # Build ID mapping first
        id_map = {}
        for screen in flow_json.get("screens", []):
            old_id = screen["id"]
            new_id = re.sub(r'[^A-Za-z_]', '_', old_id).upper()
            id_map[old_id] = new_id

        # Apply fixes to screens
        for screen in flow_json.get("screens", []):
            screen["id"] = id_map[screen["id"]]

            if not screen.get("terminal", False):
                screen.pop("success", None)

            # Replace all old IDs anywhere inside the screen layout
            screen["layout"] = self._replace_ids_in_dict(screen["layout"], id_map)

        # Fix routing_model
        if "routing_model" in flow_json:
            new_routing = {}
            for key, targets in flow_json["routing_model"].items():
                new_key = id_map.get(key, key)
                new_targets = [id_map.get(t, t) for t in targets]
                new_routing[new_key] = new_targets
            flow_json["routing_model"] = new_routing

        return flow_json

    def _replace_ids_in_dict(self, obj: Any, id_map: Dict[str, str]) -> Any:
        if isinstance(obj, dict):
            return {k: self._replace_ids_in_dict(v, id_map) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_ids_in_dict(i, id_map) for i in obj]
        elif isinstance(obj, str):
            return id_map.get(obj, obj)
        return obj

    # ---------------- Private helper methods ---------------- #
    def _check_business_account_id(self):
        if not self.business_account_id or len(self.business_account_id.strip()) == 0:
            raise ValueError("Business account ID is required for this operation")

    # ---------------- Core messaging methods ---------------- #

    async def send_text_message(
        self, to: str, text: str, preview_url: bool = False, context_message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a text message."""
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": preview_url, "body": text},
        }
        
        if context_message_id:
            data["context"] = {"message_id": context_message_id}
        
        response = await self.client.post(
            f"/{self.phone_number_id}/messages", json=data
        )
        
        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")
        
        return response.json()

    async def send_media_message(
        self,
        to: str,
        media_type: str,
        media_url: str = "",
        caption: str = "",
        filename: str = "",
        media_id: Optional[str] = None,
        context_message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a media message (image, document, audio, video, sticker)."""
        if not media_id and not media_url:
            raise ValueError("Either media_id or media_url must be provided")

        media_data = {}
        if media_id:
            media_data["id"] = media_id
        elif media_url:
            media_data["link"] = media_url

        if caption and media_type in ["image", "video", "document"]:
            media_data["caption"] = caption

        if filename and media_type == "document":
            media_data["filename"] = filename

        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": media_type,
            media_type: media_data,
        }
        
        if context_message_id:
            data["context"] = {"message_id": context_message_id}

        response = await self.client.post(
            f"/{self.phone_number_id}/messages", json=data
        )
        
        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")
        
        return response.json()

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "en_US",
        components: Optional[List[Dict[str, Any]]] = None,
        context_message_id: Optional[str] = None,
        biz_opaque_callback_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a template message."""
        template_data = {"name": template_name, "language": {"code": language_code}}

        if components:
            template_data["components"] = components

        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": template_data,
        }
        
        if context_message_id:
            data["context"] = {"message_id": context_message_id}

        if biz_opaque_callback_data: 
            data["biz_opaque_callback_data"] = biz_opaque_callback_data[:512]  # enforce limit


        response = await self.client.post(
            f"/{self.phone_number_id}/messages", json=data
        )
        
        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")
        
        return response.json()

    async def send_interactive_message(
        self,
        to: str,
        interactive_type: str,
        body_text: str,
        header: Optional[Dict[str, Any]] = None,
        footer_text: str = "",
        action: Optional[Dict[str, Any]] = None,
        context_message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an interactive message (buttons or list)."""
        interactive_data = {"type": interactive_type, "body": {"text": body_text}}

        if header:
            interactive_data["header"] = header

        if footer_text:
            interactive_data["footer"] = {"text": footer_text}

        if action:
            interactive_data["action"] = action

        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive_data,
        }
        
        if context_message_id:
            data["context"] = {"message_id": context_message_id}

        response = await self.client.post(
            f"/{self.phone_number_id}/messages", json=data
        )
        
        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")
        
        return response.json()

    # ---------------- Message management methods ---------------- #

    async def mark_message_as_read(self, message_id: str) -> Dict[str, Any]:
        """Mark a message as read."""
        data = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
            "typing_indicator": {
                "type": "text"
            }
        }

        response = await self.client.post(
            f"/{self.phone_number_id}/messages", json=data
        )
        response.raise_for_status()
        return response.json()

    # ---------------- Business profile methods ---------------- #
    async def get_business_profile(
        self,
        phone_number_id: str,
        fields: str = "id,about,address,description,email,messaging_product,name,phone_number,profile_picture_url,websites,vertical",
    ) -> Dict[str, Any]:
        """Get business profile information."""
        params = {"fields": fields}
        response = await self.client.get(
            f"/{phone_number_id}/whatsapp_business_profile",
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def update_business_profile(
        self,
        about: str = "",
        address: str = "",
        description: str = "",
        email: str = "",
        profile_picture_handle: str = "",
        websites: List[str] = [],
        vertical: str = "",
    ) -> Dict[str, Any]:
        """Update business profile information."""
        data: Dict[str, Any] = {"messaging_product": "whatsapp"}

        if about:
            data["about"] = about
        if address:
            data["address"] = address
        if description:
            data["description"] = description
        if email:
            data["email"] = email
        if profile_picture_handle:
            data["profile_picture_handle"] = profile_picture_handle
        if websites:
            data["websites"] = websites
        if vertical:
            data["vertical"] = vertical

        response = await self.client.post(
            f"/{self.phone_number_id}/whatsapp_business_profile", json=data
        )
        response.raise_for_status()
        return response.json()

    # ---------------- Phone number methods ---------------- #

    async def get_phone_numbers(self) -> Dict[str, Any]:
        """Get phone numbers associated with the business account."""
        if not self.business_account_id:
            raise ValueError("Business account ID is required")

        response = await self.client.get(f"/{self.business_account_id}/phone_numbers")
        response.raise_for_status()
        return response.json()

    async def register_phone_number(
        self, 
        pin: str, 
        phone_number_id: str,
        data_localization_region: str = "US"
    ) -> Dict[str, Any]:
        """Register a phone number."""
        data = {
            "messaging_product": "whatsapp",
            "pin": pin,
        }

        response = await self.client.post(
            f"/{phone_number_id}/register", json=data
        )
        response.raise_for_status()
        return response.json()

    # ---------------- Template methods ---------------- #

    async def get_filtered_message_templates(
        self,
        templatename: Optional[str] = None
    ) -> Dict[str, Any]:
        params = {}
        
        # Build URL with optional name parameter
        url = f"/{self.business_account_id}/message_templates"
        if templatename:
            url += f"?name={templatename}"
        
        response = await self.client.get(url, params=params)
        
        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")
        
        return response.json()

    async def create_message_template(
        self,
        name: str,
        language: str,
        category: str,
        components: List[Dict[str, Any]],
        allow_category_change: bool = False,
    ) -> Dict[str, Any]:
        """Create a new message template."""
        self._check_business_account_id()

        data = {
            "name": name,
            "language": language,
            "category": category,
            "components": components,
            "allow_category_change": allow_category_change,
        }

        response = await self.client.post(
            f"/{self.business_account_id}/message_templates", json=data
        )

        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")
        
        return response.json()

    async def delete_message_template(
        self, 
        template_name: str, 
        hsm_id: str | None = None
    ) -> Dict[str, Any]:
        """Delete a message template."""
        self._check_business_account_id()

        data = {"name": template_name}
        if hsm_id:
            data["hsm_id"] = hsm_id

        response = await self.client.delete(
            f"/{self.business_account_id}/message_templates", params=data
        )

        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")
        
        return response.json()

    # ---------------- Token Management ---------------- #
    async def check_token_expiry(self, app_id: str, app_secret: str) -> Dict[str, Any]:
        """Check when the access token expires.
        
        Args:
            app_id: Your Facebook App ID
            app_secret: Your Facebook App Secret
            
        Returns:
            Dict containing token info including expiration timestamp
        """
        app_access_token = f"{app_id}|{app_secret}"
        
        response = await self.client.get(
            "/debug_token",
            params={
                "input_token": self.access_token,
                "access_token": app_access_token,
            },
        )
        
        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")
        
        return response.json()

    async def refresh_long_lived_token(
        self, 
        app_id: str, 
        app_secret: str
    ) -> Dict[str, Any]:
        """
        Exchange a short-lived token for a long-lived token (60 days).
        
        Args:
            app_id: Your Facebook App ID
            app_secret: Your Facebook App Secret
            
        Returns:
            Dict containing new access_token and expires_in
        """
        response = await self.client.get(
            "/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": self.access_token,
            },
        )
        
        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")
        
        return response.json()
    
    # ---------------- Flow Management methods ---------------- #
    async def create_flow(
        self,
        name: str,
        categories: List[str],
    ) -> Dict[str, Any]:
        """Create a new WhatsApp Flow."""
        self._check_business_account_id()

        data = {
            "name": name,
            "categories": categories,
        }

        response = await self.client.post(
            f"/{self.business_account_id}/flows", json=data
        )

        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")

        return response.json()  # { id: flow_id }



    async def upload_flow_json(
        self,
        flow_id: str,
        flow_json: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Upload or update the screen JSON for a flow."""
        import json

        flow_json["version"] = "7.3"
        # file_content = json.dumps(flow_json).encode("utf-8")
        flow_json = self._sanitize_flow_json(flow_json)
        file_content = json.dumps(flow_json).encode("utf-8")

        response = await self.client.post(
            f"/{flow_id}/assets",
            files={
                "file": ("flow.json", file_content, "application/json"),
                "name": (None, "flow.json"),
                "asset_type": (None, "FLOW_JSON"),
            },
        )

        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")

        return response.json()

    async def get_flow(
        self,
        flow_id: str,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get full details of a single flow."""
        params = {}
        if fields:
            params["fields"] = ",".join(fields)

        response = await self.client.get(f"/{flow_id}", params=params)

        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")

        return response.json()

    async def list_flows(
        self,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """List all flows for the WhatsApp Business Account."""
        self._check_business_account_id()

        params = {}
        if fields:
            params["fields"] = ",".join(fields)

        response = await self.client.get(
            f"/{self.business_account_id}/flows", params=params
        )

        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")

        return response.json()

    # async def submit_flow(self, flow_id: str) -> Dict[str, Any]:
    #     """Submit a DRAFT flow for Meta review."""
    #     response = await self.client.post(f"/{flow_id}/submit")

    #     if not response.is_success:
    #         error_data = response.json()
    #         raise ValueError(f"{error_data}")

    #     return response.json()


    async def submit_flow(self, flow_id: str) -> Dict[str, Any]:
        """For simple flows, publishing IS the submission."""
        response = await self.client.post(f"/{flow_id}/publish")

        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")

        return response.json()

    async def publish_flow(self, flow_id: str) -> Dict[str, Any]:
        """Publish an approved flow to make it live."""
        response = await self.client.post(f"/{flow_id}/publish")

        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")

        return response.json()

    async def deprecate_flow(self, flow_id: str) -> Dict[str, Any]:
        """Deprecate a published flow."""
        response = await self.client.post(f"/{flow_id}/deprecate")

        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")

        return response.json()

    async def delete_flow(self, flow_id: str) -> Dict[str, Any]:
        """Delete a DRAFT or DEPRECATED flow."""
        response = await self.client.delete(f"/{flow_id}")

        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")

        return response.json()
    
    async def get_flow_assets(self, flow_id: str) -> Dict[str, Any]:
        """Get the assets (flow.json content) for a flow."""
        response = await self.client.get(f"/{flow_id}/assets")

        if not response.is_success:
            error_data = response.json()
            raise ValueError(f"{error_data}")

        return response.json()
    
    async def download_flow_json(self, download_url: str) -> Dict[str, Any]:
        """Download the actual flow JSON content from the asset download URL."""
        response = await self.client.get(download_url)

        if not response.is_success:
            raise ValueError(f"{response.text}")

        return response.json()