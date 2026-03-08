import logging
from typing import Any, Literal, Callable, Awaitable
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware  
from fastmcp.server.dependencies import get_http_request
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from src.env import settings
from mitexlab_googlemcp import google_mcp_main_server, oauth2_callback
from mitexlab_instagrammcp import instagram_mcp_main_server  # type: ignore
from mitexlab_whatsappmcp import whatsapp_mcp_main_server 
from mitex_mailer_mcp import mailer_mcp_main_server  # type: ignore

logging.captureWarnings(True)

class AuthenticationMiddleware(Middleware):
    def __init__(self, api_key: str) -> None:
        super().__init__()
        self.api_key = api_key

    async def on_request(self, context: Any, call_next: Callable[[Any], Awaitable[Any]]) -> Any:
        request: Request = get_http_request()
        print(f"{request.headers}")
        
        if not request or not hasattr(request, "headers"):
            raise ValueError("No authorization context available")
        
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise ValueError("Missing or invalid authorization header")
        
        token = auth_header.replace("Bearer ", "").strip()
        if token != self.api_key:
            raise ValueError("Invalid API key")
        
        return await call_next(context)


def create_main_server() -> FastMCP[Any]:
    """Create the main aggregated MCP server"""
    main_server = FastMCP(name="Mitexlab AI Core Server", include_fastmcp_meta=True)

    @main_server.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> Response:
        return JSONResponse({"status": "healthy", "version": "1.0.11"})
  
    # Create individual servers
    googlemcp_server = google_mcp_main_server()
    instagrammcp_server = instagram_mcp_main_server()
    whatsapp_server = whatsapp_mcp_main_server()
    mailermcp_server = mailer_mcp_main_server()
    
    
    # Mount servers with prefixes (server first, then prefix)
    main_server.mount(googlemcp_server, "googlemcp")
    main_server.mount(instagrammcp_server, "instagrammcp")
    main_server.mount(whatsapp_server, "whatsappmcp")
    main_server.mount(mailermcp_server, "mailermcp")
    
    
    return main_server

async def run_server() -> None:
    """Run the aggregated MCP server"""
    server = create_main_server()
    await server.run_async(transport='streamable-http', host='0.0.0.0', port=settings.MCPPORT)