import logging
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.auth import StaticTokenVerifier
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.env import settings
from mitexlab_googlemcp import google_mcp_main_server
from mitexlab_instagrammcp import instagram_mcp_main_server  # type: ignore
from mitexlab_whatsappmcp import whatsapp_mcp_main_server
from mitex_mailer_mcp import mailer_mcp_main_server  # type: ignore

logger = logging.getLogger(__name__)
logging.captureWarnings(True)


def _mcp_auth() -> StaticTokenVerifier:
    return StaticTokenVerifier(
        tokens={
            settings.MCPKEY: {
                "client_id": "mitex-mcp",
                "scopes": [],
            }
        }
    )


def create_main_server() -> FastMCP[Any]:
    """Create the main aggregated MCP server."""
    main_server = FastMCP(
        name="Mitexlab AI Core Server",
        include_fastmcp_meta=True,
        auth=_mcp_auth(),
    )

    @main_server.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> Response:
        return JSONResponse({"status": "healthy", "version": "1.0.11"})

    googlemcp_server = google_mcp_main_server()
    instagrammcp_server = instagram_mcp_main_server()
    whatsapp_server = whatsapp_mcp_main_server()
    mailermcp_server = mailer_mcp_main_server()

    main_server.mount(googlemcp_server, "googlemcp")
    main_server.mount(instagrammcp_server, "instagrammcp")
    main_server.mount(whatsapp_server, "whatsappmcp")
    main_server.mount(mailermcp_server, "mailermcp")

    return main_server


async def run_server() -> None:
    """Run the aggregated MCP server."""
    server = create_main_server()
    await server.run_async(
        transport="streamable-http",
        host="0.0.0.0",
        port=settings.MCPPORT,
    )
