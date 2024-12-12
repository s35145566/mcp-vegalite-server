import logging
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from pydantic import AnyUrl
from typing import Any
import vl_convert as vlc
import base64

logging.basicConfig(
    level=logging.INFO,  # Set the log level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/mcp_datavis_server.log"),  # Log file path
        logging.StreamHandler(),  # Optional: still output to the console
    ],
)

logger = logging.getLogger("mcp_datavis_server")
logger.info("Starting MCP Data Visualization Server")

saved_data = {
    "sample_data": [
        {"name": "Alice", "age": 25, "city": "New York"},
        {"name": "Bob", "age": 30, "city": "San Francisco"},
        {"name": "Charlie", "age": 35, "city": "Los Angeles"},
    ]
}

SAVE_DATA_TOOL_DESCRIPTION = """
A tool which allows you to save data to a named table for later use in visualizations.
When to use this tool:
- Use this tool when you have data that you want to visualize later.
How to use this tool:
- Provide the name of the table to save the data to (for later reference) and the data itself.
""".strip()

VISUALIZE_DATA_TOOL_DESCRIPTION = """
A tool which allows you to produce a data visualization using the Vega-Lite grammar.
When to use this tool:
- At times, it will be advantageous to provide the user with a visual representation of some data, rather than just a textual representation.
- This tool is particularly useful when the data is complex or has many dimensions, making it difficult to understand in a tabular format. It is not useful for singular data points.
How to use this tool:
- Prior to visualization, data must be saved to a named table using the save_data tool.
- After saving the data, use this tool to visualize the data by providing the name of the table with the saved data and a Vega-Lite specification.
""".strip()


async def main(output_type: str):
    logger.info("Starting Data Visualization MCP Server")

    server = Server("datavis-manager")

    # Register handlers
    logger.debug("Registering handlers")

    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        logger.debug("Handling list_resources request")
        return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> str:
        logger.debug(f"Handling read_resource request for URI: {uri}")
        path = str(uri).replace("memo://", "")
        raise ValueError(f"Unknown resource path: {path}")

    @server.list_prompts()
    async def handle_list_prompts() -> list[types.Prompt]:
        logger.debug("Handling list_prompts request")
        return []

    @server.get_prompt()
    async def handle_get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
        logger.debug(f"Handling get_prompt request for {name} with args {arguments}")
        raise ValueError(f"Unknown prompt: {name}")

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available tools"""
        return [
            types.Tool(
                name="save_data",
                description=SAVE_DATA_TOOL_DESCRIPTION,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "The name of the table to save the data to"},
                        "data": {
                            "type": "array",
                            "items": {"type": "object", "description": "Row of the table as a dictionary/object"},
                            "description": "The data to save",
                        },
                    },
                    "required": ["name", "data"],
                },
            ),
            types.Tool(
                name="visualize_data",
                description=VISUALIZE_DATA_TOOL_DESCRIPTION,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "data_name": {
                            "type": "string",
                            "description": "The name of the data table to visualize",
                        },
                        "vegalite_specification": {
                            "type": "string",
                            "description": "The vegalite v5 specification for the visualization. Do not include the data field, as this will be added automatically.",
                        },
                    },
                    "required": ["data_name", "vegalite_specification"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool execution requests"""
        logger.info(f"Handling tool execution request for {name} with args {arguments}")
        try:
            if name == "save_data":
                save_name = arguments["name"]
                saved_data[save_name] = arguments["data"]
                return [types.TextContent(type="text", text=f"Data saved successfully to table {save_name}")]
            elif name == "visualize_data":
                data_name = arguments["data_name"]
                vegalite_specification = eval(arguments["vegalite_specification"])
                data = saved_data[data_name]
                vegalite_specification["data"] = {"values": data}

                if output_type == "png":
                    png = vlc.vegalite_to_png(vl_spec=vegalite_specification, scale=2)
                    png = base64.b64encode(png).decode("utf-8")
                    return [types.ImageContent(type="image", data=png, mimeType="image/png")]
                else:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Visualized data from table {data_name} with provided spec.",
                            artifact=vegalite_specification,
                        )
                    ]
            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running with stdio transport")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="datavis",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
