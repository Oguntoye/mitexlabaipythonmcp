from fastmcp import FastMCP
import importlib

server = FastMCP("mailer_mcp")


def mailer_mcp_main_server():
    """
    Main entry point
    """

    # Import tool modules to register them with the MCP server via decorators
    tool_imports = {
        'auth': lambda: importlib.import_module('..tools.auth', package=__name__),
        'getmails': lambda: importlib.import_module('..tools.getmails', package=__name__),
        'sendmails': lambda: importlib.import_module('..tools.sendmails', package=__name__),
       
       
    }
    tools_to_import = tool_imports.keys()

    for tool in tools_to_import:
        tool_imports[tool]()
        print(f"{tool.title()} - mailer {tool.title()} API integration")
    
    return server