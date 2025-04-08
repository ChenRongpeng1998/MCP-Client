# MCP-Client
This is a MCP Client.The client is made by python.This client can only connect to one service.
# Installation

```bash
uv sync
```
# Usages
## 1. Start the client
Pass your own LLM API when instantiating the class.OpenRouter's API is supported by default.
```python
 client = MCPClientBase('your_api',
                           "deepseek/deepseek-chat-v3-0324:free")
```
## 2. Connect to a server
After instantiating the client class, use the `connect_to_server ` method to connect to a server.`connect_to_server` has two parameters that need to be entered, `name` and `info`.The `name` is a string, which is the name of your service,`info` is a dictionary of necessary parameters for client to connect to the service.The `info` can be filled out by referring to the json for Claude desktop connection to the MCP.Here is a simple example.
```python
await client.connect_to_server('time',{
      "command": "python",
      "args": [
        "-m",
        "mcp_server_time",
        "--local-timezone=Asia/Shanghai"
      ]})
```

