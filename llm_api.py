import requests
import time
from abc import ABC, abstractmethod
from config import Config, LLMConfig

class BaseLLMAPI(ABC):
    def __init__(self, api_base, api_key, model_name, stream=False, max_retries=3):
        self.config = LLMConfig(api_base, api_key, model_name, stream)
        self.max_retries = max_retries

    def _make_request(self, url, headers, data):
        retries = 0
        while retries < self.max_retries:
            try:
                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except (requests.exceptions.RequestException, KeyError) as e:
                retries += 1
                if retries == self.max_retries:
                    raise Exception(f"Request failed after {self.max_retries} retries: {str(e)}")
                print(f"Request failed, retrying in 30 seconds (attempt {retries}/{self.max_retries})")
                time.sleep(30)

    @abstractmethod
    def generate(self, prompt):
        pass

class GPTCallAPI(BaseLLMAPI):
    def generate(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.config.model_name,
            "messages": [{"role": "user", "content": prompt}]
        }
        return self._make_request(
            f"{self.config.api_base}/chat/completions",
            headers,
            data
        )

class ClaudeCallAPI(BaseLLMAPI):
    def generate(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.config.model_name,
            "messages": [{"role": "user", "content": prompt}]
        }
        return self._make_request(
            f"{self.config.api_base}/chat/completions",
            headers,
            data
        )

class DeepSeekCallAPI(BaseLLMAPI):
    def generate(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.config.model_name,
            "messages": [{"role": "user", "content": prompt}]
        }
        return self._make_request(
            f"{self.config.api_base}/chat/completions",
            headers,
            data
        ) 