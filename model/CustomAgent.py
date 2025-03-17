from autogen.agentchat import ConversableAgent


def CustomAgent(name, **kwargs):
    return ConversableAgent(name, **kwargs)