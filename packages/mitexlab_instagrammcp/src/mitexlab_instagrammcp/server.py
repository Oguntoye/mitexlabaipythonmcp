from fastmcp import FastMCP
import importlib

server = FastMCP("instagram_mcp")


def instagram_mcp_main_server():
    """
    Main entry point
    """

    # Import tool modules to register them with the MCP server via decorators
    tool_imports = {
        'auth': lambda: importlib.import_module('..tools.auth', package=__name__),
        'comments': lambda: importlib.import_module('..tools.comments', package=__name__),
        'media': lambda: importlib.import_module('..tools.media', package=__name__),
        'messages': lambda: importlib.import_module('..tools.messages', package=__name__),
        'profile': lambda: importlib.import_module('..tools.profile', package=__name__),
       
    }
    tools_to_import = tool_imports.keys()

    for tool in tools_to_import:
        tool_imports[tool]()
        print(f"{tool.title()} - Instagram {tool.title()} API integration")
    
    return server