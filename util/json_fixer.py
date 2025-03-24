import json
import re
from agent.json_agent import json_agent
from util.text_extractor import json_extractor


async def fix_json(json_str):
    """
    Attempts to fix invalid JSON by:
    1. First trying to parse it directly
    2. If that fails, trying to use json_extractor to extract JSON from code blocks or text
    3. If that fails, trying to extract JSON using regex
    4. If that fails, sending it to the json_agent for repair
    
    Args:
        json_str (str): The potentially invalid JSON string
        
    Returns:
        dict or list: The parsed JSON object
    """
    # If it's already a dict or list, return it directly
    if isinstance(json_str, (dict, list)):
        return json_str
    
    # First try to parse directly
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        # Try to extract JSON using json_extractor
        try:
            return json_extractor(json_str)
        except ValueError:
            # Try to extract JSON using regex
            try:
                json_pattern = r'(\[.*\]|\{.*\})'
                match = re.search(json_pattern, json_str, re.DOTALL)
                if match:
                    extracted_json = match.group(0)
                    return json.loads(extracted_json)
            except (json.JSONDecodeError, AttributeError, TypeError):
                pass
            
            # If all else fails, use the json_agent to fix it
            try:
                fixed_json_str = await json_agent.send_message(json_str)
                return json.loads(fixed_json_str)
            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                # If even the json_agent can't fix it, raise the error
                raise ValueError(f"Could not parse or fix JSON: {str(e)}")
