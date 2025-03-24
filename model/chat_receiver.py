from abc import ABC, abstractmethod
import requests
from openai import OpenAI
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import UserMessage

class ChatReceiver(ABC):

    def __init__(self,api_key,base_url,
                 model,
                 system_prompt,
                 temperature = 0.6,
                 use_vision=False,
                 use_function_call=True,
                 use_json=False
                 ):

        self.set_up_client(api_key, base_url,
                           model_name = model,
                           use_vision = use_vision,
                           use_function_call = use_function_call,
                           use_json = use_json)
        self.system_prompt = system_prompt
        self.temperature = temperature


    def set_up_client(self, api_key: str, base_url: str,
                      model_name: str,
                      use_vision = False,
                      use_function_call = True,
                      use_json = False,
                        ):

        self.client = OpenAIChatCompletionClient(
            model=model_name,
            api_key= api_key,
            base_url= base_url,
            model_capabilities={
                "vision": use_vision,
                "function_calling": use_function_call,
                "json_output": use_json,
            },
            max_tokens=8192
        )

    # def get_model_param(self,key):
    #     return self.model_params[key]
    # def set_model_param(self,key, value):
    #     self.model_params[key] = value
    # def __setitem__(self, key, value):
    #     self.set_model_param(key,value)
    # def __getitem__(self, key):
    #     return self.get_model_param(key)

    def set_system_prompt(self,message: str):
        self.system_prompt = message


    @abstractmethod
    def make_message(self, message: str) -> dict:
        pass

    @abstractmethod
    def send_message(self, message: str) -> str:
        pass

    @abstractmethod
    def handle_message(self, response: dict) -> str:
        pass


    def get_history(self) -> list:
        pass