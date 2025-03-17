import regex
import json

def json_extractor(response):
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        response = regex.sub(r'""', '"', response)
        code_blocks = regex.findall(r'```json\s*([\s\S]*?)\s*```', response)
        if code_blocks:
            try:
                return json.loads(code_blocks[0])
            except json.JSONDecodeError:
                pass

        # If all methods fail
        raise ValueError("Could not extract valid JSON from the response")


if __name__ == '__main__':
    pass