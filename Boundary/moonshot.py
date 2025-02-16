from autogen_core.models import UserMessage
from sympy import content

from Boundary.chatReceiver import ChatReceiver
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()


# completion = client.chat.completions.create(
#     model="moonshot-v1-8k",
#     messages=[
#         {"role": "system",
#          "content": "你是专业的健身教练，擅长为用户制定合理的健身计划，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。"
#                     "同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。"
#                     ""},
#         {"role": "user", "content": "你好，我叫小徐，我想减肥。"}
#     ],
#     temperature=0.6,
# )

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
                         temperature= temperature)

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
        print(response)
        return response.content

KimiStaticTesting = moonshotChatReceiver(system_prompt="你是一个职业的摇滚明星，你不能有绯闻。你会耍酷。你会扮演自己")

if __name__ == '__main__':
    print(asyncio.run(KimiStaticTesting.send_message("我喜欢你！")))
