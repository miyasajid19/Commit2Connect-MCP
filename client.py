import asyncio
import collections
from fastmcp import Client
from rich import print

client = Client("http://localhost:8000/mcp")

async def main():
    async with client:
        available_prompts = await client.list_prompts()
        available_tools = await client.list_tools()
        available_resources = await client.list_resources()
        available_templates = await client.list_resource_templates()

        while True:
            choice = input(
                "Enter 'p' for prompt, 't' for tool, 'r' for resource, "
                "'rt' for resource template, or 'exit' to quit: "
            ).strip().lower()
            if choice == "exit":
                return
            print("="*40)

            if choice == "p":
                names = [p.name for p in available_prompts]
                print("Available prompts:", names)
                x = input(f"enter index 0 - {len(names)-1}: ")
                prompt = available_prompts[int(x) % len(names)]
                print(prompt)
                print("="*40)
                args = {}
                if prompt.arguments:
                    for arg in prompt.arguments:
                        args[arg.name] = input(f"enter value for '{arg.name}': ")
                result = await client.get_prompt(prompt.name, args)
                print(result)

            elif choice == "t":
                names = [t.name for t in available_tools]
                print("Available tools:", names)
                x = input(f"enter index 0 - {len(names)-1}: ")
                tool = available_tools[int(x) % len(names)]
                print(tool)
                print("="*40)
                args = {}
                schema = tool.inputSchema or {}
                for prop in schema.get("properties", {}):
                    args[prop] = input(f"enter value for '{prop}': ")
                result = await client.call_tool(tool.name, args)
                print(result)

            elif choice == "r":
                uris = [r.uri for r in available_resources]
                print("Available resources:", uris)
                x = input(f"enter index 0 - {len(uris)-1} or -1 for a custom uri: ")
                if int(x) == -1:
                    uri = input("enter resource uri to read: ")
                else:
                    uri = uris[int(x) % len(uris)]
                contents = await client.read_resource(uri)
                if isinstance(contents, collections.abc.Iterable):
                    contents = list(contents)
                for content in contents:
                    if hasattr(content, "text"):
                        print(content.text)
                    elif hasattr(content, "blob"):
                        print(f"Binary data: {len(content.blob)} bytes")
                        print(f"First 100 bytes: {content.blob[:100]}")

            elif choice == "rt":
                uri_templates = [t.uriTemplate for t in available_templates]
                print("Available resource templates:", uri_templates)
                x = input(f"enter index 0 - {len(uri_templates)-1}: ")
                template = available_templates[int(x) % len(uri_templates)]
                print(template)
                print("="*40)
                uri = input(
                    f"template is '{template.uriTemplate}' - "
                    "enter a concrete uri (fill in the {params}): "
                )
                contents = await client.read_resource(uri)
                if isinstance(contents, collections.abc.Iterable):
                    contents = list(contents)
                for content in contents:
                    if hasattr(content, "text"):
                        print(content.text)
                    elif hasattr(content, "blob"):
                        print(f"Binary data: {len(content.blob)} bytes")
                        print(f"First 100 bytes: {content.blob[:100]}")

            print("\n" + "="*40 + "\n")

asyncio.run(main())