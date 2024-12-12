from . import server
import asyncio
import argparse


def main():
    """Main entry point for the package."""
    parser = argparse.ArgumentParser(description="Data Visualization MCP Server")
    # parser.add_argument(
    #     "--language", default="vegalite", choices=["vegalite"], help="The visualization language/grammar/framework to use"
    # )
    parser.add_argument("--output-type", default="png", choices=["text", "png"], help="Format of the output")

    args = parser.parse_args()
    asyncio.run(server.main(output_type=args.output_type))


# Optionally expose other important items at package level
__all__ = ["main", "server"]
