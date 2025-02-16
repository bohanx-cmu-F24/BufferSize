import asyncio
import os
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
from autogen_core.models import UserMessage

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



if __name__ == '__main__':
    async def trytry():
        result = await openai_model_client.create([UserMessage(content="What is the capital of France?", source="user")])
        print(result)
    asyncio.run(trytry())