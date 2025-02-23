import asyncio
import os
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent

from dotenv import load_dotenv
from autogen_core.models import UserMessage

from Boundary.chatReceiver import ChatReceiver
from Boundary.moonshot import KimiStaticTesting

from autogen_agentchat.messages import TextMessage
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken


load_dotenv()

openai_model_client = OpenAIChatCompletionClient(
    model="moonshot-v1-8k",
    api_key=os.getenv("MOONSHOT_API_KEY"),
    base_url= os.getenv("MOONSHOT_URL"),
    model_capabilities={
        "vision": True,
        "function_calling": True,
        "json_output": False,
    },
)
class Agent:
    def __init__(self, chatReceiver: ChatReceiver):
        self.chatReceiver = chatReceiver
        self.agent = AssistantAgent(
                    name="assistant",
                    model_client=self.chatReceiver.client,
                    tools=[],
                    system_message=self.chatReceiver.system_prompt
                )

    async def send_message(self, message):
        print("Loading...")
        response = await self.agent.on_messages(
            [TextMessage(content=message, source="user")],
            cancellation_token=CancellationToken(),
        )
        print(response.chat_message.content)


if __name__ == '__main__':
    myAgent = Agent(KimiStaticTesting)
    while True:
        userInput = input()
        asyncio.run(myAgent.send_message(userInput))