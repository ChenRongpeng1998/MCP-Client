import requests
import json


class OpenRouterAugmentedLLM:

    def __init__(self, api,model):
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api}'
        }
        self.model = model

    def augment(self, prompt):
        response = requests.post(self.url, data=json.dumps({"prompt": prompt}))
        return response.text

    def get_response_p(self, prompt,sys_prompt="You is a helpful assistant."):
        if sys_prompt:
            message = [{"role": "system", "content": sys_prompt},
                       {"role": "user", "content": prompt}]
        else:
            message =[ {"role": "user", "content": prompt}]
        data = {
            "model": self.model,
            "messages": message,
        }
        response = requests.post(self.url, headers=self.headers,
                                data=json.dumps(data))
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception("Error: {}".format(response.content))
    
    def get_respones_m(self, messages):
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "stream": False,
            "stream_options": {
                "include_usage": True
                            }
        }
        response = requests.post(self.url, headers=self.headers,
                                data=json.dumps(data))
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception("Error: {}".format(response.content))
    

if __name__ == "__main__":
    open_router = OpenRouterAugmentedLLM('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',
                                         "deepseek/deepseek-chat-v3-0324:free")
    print(open_router.get_response_p("Hello,who are you?"))