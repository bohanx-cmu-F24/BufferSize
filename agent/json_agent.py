from model.agent import Agent
from boundary.llms.moonshot import MoonshotChatReceiver
from prompts.system_prompt import JSON_FIX_PROMPT



def make_new_json_agent():
    m_chat = MoonshotChatReceiver(
        system_prompt=JSON_FIX_PROMPT,
        use_json=True
    )
    return Agent(m_chat, name="json_agent")

if __name__ == '__main__':
    pass