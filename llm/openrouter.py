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
    
