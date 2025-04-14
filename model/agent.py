import asyncio
import os
from typing import Sequence

from autogen_agentchat.base import Response
from autogen_agentchat.messages import ChatMessage

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent, BaseChatAgent
from dotenv import load_dotenv

from model.chat_receiver import ChatReceiver
from boundary.llms.moonshot import KimiStaticTesting

from autogen_core import CancellationToken


load_dotenv()

class Agent:
    def __init__(self, chatReceiver: ChatReceiver, name = "",
                 tools = []):
        self.chatReceiver = chatReceiver
        self.agent = AssistantAgent(
                    name=name,
                    model_client=self.chatReceiver.client,
                    tools=tools,
                    system_message=self.chatReceiver.system_prompt,
                )
        self.messages = []  # Store message history

    async def send_message(self, message, is_debug = False):
        print("Loading...")
        response = await self.agent.run(
            task=message,
            cancellation_token=CancellationToken(),
        )
        if is_debug:
            print(response.messages[-1].models_usage)
            print(response.stop_reason)

        # Store all messages from the response
        self.messages.extend(response.messages)

        return response.messages[-1].content


if __name__ == '__main__':
    myAgent = Agent(KimiStaticTesting)
    while True:
        userInput = input()
        asyncio.run(myAgent.send_message(userInput,is_debug=False))