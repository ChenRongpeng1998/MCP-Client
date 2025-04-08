import asyncio
import re
import json
from typing import Optional,Dict
from contextlib import AsyncExitStack

from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client

from dotenv import load_dotenv

from openrouter import OpenRouterAugmentedLLM

load_dotenv() # 加载环境变量

class MCPClientBase():
    def __init__(self,api:str,model:str,*,sys_prompt_template_filepath:Optional[str]='./system_prompt_temp.txt'):
        # 初始化 session 属性为 None，类型为 Optional[ClientSession]
        self.session: Optional[ClientSession] = None
        # 初始化 exit_stack 属性为 AsyncExitStack 对象
        self.exit_stack = AsyncExitStack()
        self.llm = None
        self.api = api
        self.model = model
        self.sys_prompt_temp = get_sys_prompt_from_file(sys_prompt_template_filepath)

    async def initialize(self):
        self.llm = OpenRouterAugmentedLLM(self.api,self.model)
        
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
        else:
            raise ValueError("Command and arguments are required")

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

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

class MCPClient(MCPClientBase):
    def __init__(self,api:str,model:str,*,sys_prompt_template_filepath:Optional[str]='./system_prompt_temp.txt'):
        super().__init__(api,model,sys_prompt_template_filepath=sys_prompt_template_filepath)
        self.sessions:Dict[str,ClientSession] = {}
        self.tools_by_session:Dict[str,list] = {}
        self.all_tools = []
    
    def connect_to_servers(self, servers:dict):
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
            session = self.connect_to_server(name, info)
            self.sessions[name] = session
            self.tools_by_session[name] = []
            


async def main():
    print("start test...")
    client = MCPClientBase('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',
                           "deepseek/deepseek-chat-v3-0324:free")
    try:
        await client.initialize()
        await client.connect_to_server('time',{
      "command": "python",
      "args": [
        "-m",
        "mcp_server_time",
        "--local-timezone=Asia/Shanghai"
      ]})
        await client.chat_loop()
    finally:
        await client.cleanup()

flag2tool_fun = {
    r'<use_mcp_tool>(.*?)</use_mcp_tool>(.*)':use_mcp_tool,
}

if __name__ == "__main__":
    asyncio.run(main())


    

