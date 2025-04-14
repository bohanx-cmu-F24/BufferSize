import asyncio

from model.agent import Agent
from boundary.llms.deepseek import DeepseekChatReceiver
from prompts import system_prompt

def make_new_plan_review_agent():
    # Create a DeepseekChatReceiver instance with the deepseek-reasoner model
    m_chat = DeepseekChatReceiver(
        model="deepseek-reasoner",
        system_prompt=system_prompt.PLAN_REVIEW_PROMPT,
        use_json=True
    )
    return Agent(m_chat, name="plan_review_agent")

if __name__ == '__main__':
    pass
