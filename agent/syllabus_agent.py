import asyncio
from typing import Sequence

from autogen_agentchat.agents import BaseChatAgent, AssistantAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import AgentEvent, ChatMessage, TextMessage
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken

from boundary.llms.moonshot import MoonshotChatReceiver
from boundary.llms.chatgpt import ChatGPTReceiver
from model.agent import Agent
from prompts import system_prompt
from util.text_extractor import json_extractor

m_chat = ChatGPTReceiver(
    system_prompt=system_prompt.SYLLABUS_ANALYSIS_PROMPT,
    use_json=True
)

syllabus_agent = Agent(
    m_chat, name="syllabus_agent")



if __name__ == '__main__':
    pass