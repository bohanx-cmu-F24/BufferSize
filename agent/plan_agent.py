import asyncio

from model.agent import Agent
from boundary.llms.deepseek import DeepseekChatReceiver
from prompts import system_prompt

def make_new_plan_agent():
    m_chat = DeepseekChatReceiver(
        system_prompt=system_prompt.STUDY_PLAN_PROMPT,
        use_json=True
    )
    return Agent(m_chat, name="your_study_planner")

if __name__ == '__main__':
    pass