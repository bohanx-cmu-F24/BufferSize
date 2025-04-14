import model.agent as agent
from boundary.llms.chatgpt import ChatGPTReceiver


def make_new_study_review_agent(topic: str):
    example_output = {
        "thought": "The user explained the eigenvalues and eigenvectors of a matrix. They fully understand the concept by articulating the purpose of eigenvalues and eigenvectors, and how they are used in linear algebra. They listed their properties and corresponding formulas. I believe they have a good understanding of the topic.",
        "evaluation": "Good",
        "next_steps": "The user can improve their understanding of the eigenvalues and eigenvectors of a matrix by practicing more problems.",
        "continue_conversation": True,
        "response": "Thank you for your explanation. You are such a smart cookie. Can you then give me an example of how to use the eigenvalues and eigenvectors of a matrix?"
    }
    
    base_prompt = f""" You are a study review agent of {topic}. You are nice, friendly, and helpful.
    You need to ask the user to explain the topic in their own words, you then need to evaluate their understanding of the topic.
    Give a score between ["Good", "Needs Improvement", "Off Topic"] based on the user's understanding of the topic. And provide a response to the user based on their understanding of the topic.
    # Example Output
    {str(example_output)}
    """

    # Create a new ChatGPTReceiver instance with the system prompt
    base_client = ChatGPTReceiver(system_prompt=base_prompt, use_json=True)

    return agent.Agent(
        chatReceiver=base_client,
        name=f"study_review_agent_{topic.replace(' ', '_')}"
    )

def make_new_study_question_agent(topic: str):
    base_prompt = f""" You are a study review agent of {topic}. You are nice, friendly, and helpful.
    Pretend that you don't understand the topic. Generate a question that will help you understand the topic.
    DIRECTLY RESPOND WITH THE QUESTION.
    """

    # Create a new ChatGPTReceiver instance with the system prompt
    base_client = ChatGPTReceiver(system_prompt=base_prompt, use_json=True)

    return agent.Agent(
        chatReceiver=base_client,
        name=f"study_question_agent_{topic.replace(' ', '_')}"
    )




