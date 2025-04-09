import asyncio

import re
import json
from typing import Optional,Dict

from contextlib import AsyncExitStack
from config import Config
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client

from dotenv import load_dotenv

from llm import OpenRouterAugmentedLLM


load_dotenv() # 加载环境变量

class MCPClient():
    def __init__(self,*,config_file_path:str="client_setting.json"):
        # 初始化 exit_stack 属性为 AsyncExitStack 对象
        self.exit_stack = AsyncExitStack()
        self.api = ""
        self.model = ""
        self.config_file_path = config_file_path
        self.llm: Optional[OpenRouterAugmentedLLM] = None
        self.cfg = None
        self.sys_prompt_temp = None
        self.sessions = None
        self.tools_by_session = None
        self.all_tools = None

    async def initialize(self):
        """
        初始化函数。
        """
        self.cfg = Config(self.config_file_path) # 读取配置
        self.api = self.cfg.LLMApi
        self.model = self.cfg.LLMModel
        self.llm = OpenRouterAugmentedLLM(self.api,self.model) # 实例化MCP使用的LLM对象
        self.sys_prompt_temp = get_sys_prompt_from_file(self.cfg.SystemPromptTemplatePath) # 从配置文件中获取系统提示模板
        self.sessions: Dict[str, ClientSession] = {} # 会话列表
        self.tools_by_session:Dict[str, list] = {} # 工具列表，每个工具对应一个会话
        self.all_tools = [] # 所有工具列表
        await self.connect_to_servers(self.cfg.mcpServer)

    async def connect_to_servers(self, servers:dict):
        """
        同时启动多个服务器并获取工具。
        Args:
            servers: 一个字典，包含需要连接的服务器信息。
            如：{"weather": {
                    "command": "uv",
                    "args": [
                        "--directory",
                        "D:\\Project\\weather",
                        "run",
                        "weather_server.py",
                    ]}, 
                "rag": {
                    "command":"python",
                    "args":["rag_server.py"]}}
        """
        for name, info in servers.items():
            session,tools = await self.connect_to_server(name, info)
            self.sessions[name] = session
            self.tools_by_session[name] = tools
            self.all_tools.extend(tools)
        print("\n✅ 已连接到下列服务:")
        for name in self.sessions.keys():
            print(f"- {name}")
            for tool in self.tools_by_session[name]:
                print(f" # {tool.name}")
        
    async def connect_to_server(self,name,info:dict):
        """
        Connect to an MCP server
        """
        command = info.get('command')
        args = info.get('args')
        env = info.get('env')
        if command and args:
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

            await self.session.initialize()

            # List available tools
            response = await self.session.list_tools()
            tools = response.tools
            print(f"\nConnected to {name}:")
            for tool in tools:
                print(f"-Tool name: {tool.name}\nDescription: {tool.description}\nInput schema: {tool.inputSchema}")
            return self.session,tools
        else:
            raise ValueError("Command and arguments are required")

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in self.all_tools]

        sys_prompt = self.sys_prompt_temp.replace("{available_tools}",json.dumps(available_tools))

        messages = [{
            "role": "system",
            "content": sys_prompt
        },
            {
                "role": "user",
                "content": query
            }
        ]
        response = self.llm.get_respones_m(messages)

        # Process response and handle tool calls
        final_text = []

        assistant_message_content = []
        _,fun = tools_filter(think_separation(response)[-1],flag2tool_fun=flag2tool_fun)
        if _:
            if fun.get('type') == 'tool_use':
                tool_name = fun.get('tool_name')
                tool_args = json.loads(fun.get('arguments'))

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                assistant_message_content.append(think_separation(response)[-1])
                messages.append({
                    "role": "assistant",
                    "content": assistant_message_content[0]
                })
                messages.append({
                    "role": "user",
                    "content":f"[use_mcp_tool for '{tool_name}'] Result:"+result.content[0].text
                })
                # Get next response
                response = self.llm.get_respones_m(messages)
                assistant_message_content.append(response)
                final_text.append(response)
            else:
                final_text.append(response)
        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == "quit":
                    print("正在退出chat_loop请稍后.")
                    break
                response = await self.process_query(query)
                print("\n" + response)
            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()        


def get_sys_prompt_from_file(filename: str,encoding="utf-8") -> str:
    with open(filename, 'r',encoding=encoding) as f:
        return f.read()

def think_separation(text):
    pattern = r'<thinking>(.*?)</thinking>(.*)'
    matches = re.match(pattern, text.strip(), re.DOTALL)
    if matches:
        return matches.group(1).strip(),matches.group(2).strip()
    else:
        #raise ValueError("No <think>...</think> found in the given text.")
        return "",text

def tools_filter(text,flag2tool_fun:dict):
    for k,v in flag2tool_fun.items():
        _,result = tool_filter(text,k,v)
        if _:
            return True,result
    return False,None

def tool_filter(text,pattern,fun:callable):
    matches = re.match(pattern, text.strip(), re.DOTALL)
    if matches:
        return True,fun(matches.group(1).strip())
    return False,None

def use_mcp_tool(text):
    patternes = [r'<server_name>(.*?)</server_name>',
               r'<tool_name>(.*?)</tool_name>',
               r'<arguments>(.*?)</arguments>']
    arg = []
    for pattern in patternes:
        matches = re.findall(pattern, text.strip(), re.DOTALL)
        if matches:
            arg.append(matches[0].strip())
        else:
            arg.append("")
    return{
        "server_name":arg[0],
        "tool_name":arg[1],
        "arguments":arg[2],
        "type":"tool_use",
    } 



async def main():
    print("start test...")
    client = MCPClient()
    try:
        await client.initialize()
        await client.chat_loop()
    finally:
        await client.cleanup()
        del client

flag2tool_fun = {
    r'<use_mcp_tool>(.*?)</use_mcp_tool>(.*)':use_mcp_tool,
}

if __name__ == "__main__":
    asyncio.run(main())


    

