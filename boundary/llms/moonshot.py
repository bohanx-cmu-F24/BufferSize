from autogen_core.models import UserMessage
from sympy import content

from model.chat_receiver import ChatReceiver
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()


class moonshotChatReceiver(ChatReceiver):
    def __init__(self, api_key = None, base_url = None,
                 system_prompt = "",
                 temperature = 0.6,
                 use_vision = False,
                 use_function_call = True,
                 use_json = False):
        if api_key is None:
            api_key = os.getenv("MOONSHOT_API_KEY")
        if base_url is None:
            base_url = os.getenv("MOONSHOT_URL")
        super().__init__(api_key,base_url, "moonshot-v1-8k",
                         system_prompt=system_prompt,
                         temperature= temperature,use_json=use_json,use_vision=use_vision,use_function_call=use_function_call)

    def make_message(self, message: str) -> list:
        new_message = [
            UserMessage(content=self.system_prompt,source="system"),
            UserMessage(content=message,source="Your_boss")
        ]
        return new_message

    async def send_message(self, message: str) -> str:
        used_message = self.make_message(message)
        completion = await self.client.create(used_message)
        return self.handle_message(completion)

    def handle_message(self, response):
        # print(response)
        return response.content

from prompts.system_prompt import STUDY_PLAN_PROMPT
KimiStaticTesting = moonshotChatReceiver(system_prompt=STUDY_PLAN_PROMPT)

if __name__ == '__main__':
    pass