from model.agent import Agent
from boundary.llms.moonshot import MoonshotChatReceiver
from prompts.system_prompt import JSON_FIX_PROMPT


json_chat = MoonshotChatReceiver(
    system_prompt=JSON_FIX_PROMPT,
    use_json=True
)

json_agent = Agent(json_chat, name="json_agent")
