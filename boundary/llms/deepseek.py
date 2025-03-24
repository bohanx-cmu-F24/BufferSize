from autogen_core.models import UserMessage

from model.chat_receiver import ChatReceiver
from dotenv import load_dotenv
import os
import asyncio
import json
import re

load_dotenv()


class DeepseekChatReceiver(ChatReceiver):
    def __init__(self, api_key=None, base_url=None,
                 model="deepseek-chat",
                 system_prompt="",
                 temperature=0.6,
                 use_vision=False,
                 use_function_call=True,
                 use_json=False):
        if api_key is None:
            api_key = os.getenv("DEEPSEEK_API_KEY")
        if base_url is None:
            base_url = os.getenv("DEEPSEEK_URL")
            
        # Store use_json flag for later use
        self.use_json_mode = use_json
        
        super().__init__(api_key, base_url, model,
                         system_prompt=system_prompt,
                         temperature=temperature,
                         use_json=use_json,
                         use_vision=use_vision,
                         use_function_call=use_function_call)

    def make_message(self, message: str) -> list:
        new_message = [
            UserMessage(content=self.system_prompt, source="system"),
            UserMessage(content=message, source="user")
        ]
        return new_message

    async def send_message(self, message: str) -> str:
        used_message = self.make_message(message)
        completion = await self.client.create(used_message)
        return self.handle_message(completion)

    def handle_message(self, response):
        # Extract the content from the response
        content = response.content
        
        # If we're in JSON mode, validate the response is proper JSON
        if self.use_json_mode:
            try:
                # Try to parse the content as JSON to validate it
                json_content = json.loads(content)
                # Return the original string (not the parsed object)
                # to maintain consistency with the expected return type
                return content
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from the text
                # Look for content between curly braces or square brackets
                json_pattern = r'(\[.*\]|\{.*\})'
                match = re.search(json_pattern, content, re.DOTALL)
                if match:
                    try:
                        extracted_json = match.group(0)
                        # Validate it's proper JSON
                        json.loads(extracted_json)
                        return extracted_json
                    except json.JSONDecodeError:
                        pass
                # If all attempts fail, return the original content
                return content
        return content


# Create a default instance with system prompt from the project
from prompts.system_prompt import STUDY_PLAN_PROMPT
DeepseekDefault = DeepseekChatReceiver(system_prompt=STUDY_PLAN_PROMPT)


if __name__ == '__main__':
    # Example usage
    import asyncio
    
    async def test_chat():
        deepseek = DeepseekChatReceiver()
        response = await deepseek.send_message("Hello, how are you today?")
        print(response)
    
    asyncio.run(test_chat())
