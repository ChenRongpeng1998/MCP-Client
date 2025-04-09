# MCP-Client
一个基于python编写的使用系统提示词实现与LLM交互的客户端。

# 安装
## 1. 安装node.js和npm
## 2. 安装uv
## 3. 使用uv命令同步客户端配置文件
```bash
uv sync
```
# 用法
## 1. 配置你的客户端设置文件
通过修改`client_setting.json`文件来配置你的客户端设置。`mcpClient`设置客户端相关设置，`mcpServer`设置相连接的mcp服务。参考如下：
```json
{
    "mcpClient":
    {
        "LLMApi": "your_api_key",
        "ApiProvider":"OpenRouter",
        "LLMModel": "deepseek/deepseek-chat-v3-0324:free",
        "SystemPromptTemplatePath": "system_prompt_temp.txt",
    },
    "mcpServer":
    {
        "mysql_reader": {
            "command": "uv",
            "args": [
                "--directory",
                "D:\\Project\\MySQLReader",
                "run",
                "mysql_reader.py"
            ],
            "env": {"PATH": "D:\\Project\\MySQLReader\\.venv\\Scripts"}
    },
    "filesystem": {
      "command": "cmd",
      "args": [
        "/c",
        "npx",
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "D:\\Std\\MCP"
      ]
    },
    "time": {
      "command": "python",
      "args": [
        "-m",
        "mcp_server_time",
        "--local-timezone=Asia/Shanghai"
      ]
    }
    }
}
```
# 特别说明
- __目前仅支持OpenRouter作为API提供商。__




