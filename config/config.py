import json

class Config:
    data = None
    def __init__(self, json_file,schema_file="./schema_default.json"):
        self.data = json.load(open(json_file))
        if not self.validate_json(self.data,schema_file):
            raise TypeError("设置文件格式与schema所述不匹配！")


    def validate_json(self,data:dict,schema_file:str):
        # 假定有一个格式审查函数
        return True

    @property
    def mcpClient(self):
        return self.data.get("mcpClient")

    @property
    def mcpServer(self):
        return self.data.get("mcpServer")
    
    @property
    def LLMApi(self):
        if self.mcpClient is None:
            return None
        else:
            return self.mcpClient.get("LLMApi")
    
    @property
    def ApiProvider(self):
        if self.mcpClient is None:
            return None
        else:
            return  self.mcpClient.get("ApiProvider")

    @property
    def LLMModel(self):
        if self.mcpClient is None:
            return None
        else:
            return  self.mcpClient.get("LLMModel")
    @property
    def SystemPromptTemplatePath(self):
        if self.mcpClient is None:
            return None
        else:
            return self.mcpClient.get("SystemPromptTemplatePath")
        

    
        