import importlib

from fastmcp import FastMCP

server = FastMCP("whatsapp_mcp")


def whatsapp_mcp_main_server():
    """
    Main entry point for WhatsApp MCP server
    """

    # Import tool modules to register them with the MCP server via decorators
    tool_imports = {
        'auth': lambda: importlib.import_module('..tools.auth', package=__name__),
        'business': lambda: importlib.import_module('..tools.business', package=__name__),
        'messages': lambda: importlib.import_module('..tools.messages', package=__name__),
        'templates': lambda: importlib.import_module('..tools.templates', package=__name__),
        'whatsappflow': lambda: importlib.import_module('..tools.whatsappflow', package=__name__),
       
    }
    tools_to_import = tool_imports.keys()

    for tool in tools_to_import:
        tool_imports[tool]()
        print(f"{tool.title()} - WhatsApp {tool.title()} API integration")

    return server
