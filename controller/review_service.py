import os
import json
import datetime
import agent.study_review_agent as study_review_agent
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client.buffer_size_db

session = {}

async def get_review_topics(username: str, course_id: str):
    # get the topics from the course
    topics = await db.analysis.find_one({"username": username, "course_id": course_id})
    return topics

async def start_session(username: str, course_id: str, topic: str):
    session_id = username + "_" + course_id + "_" + topic + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session[session_id] = {
        "username": username,
        "course_id": course_id,
        "topic": topic,
        "review_agent": study_review_agent.make_new_study_review_agent(topic)
    }
    return session_id

async def save_session_history(session_id: str):
    # Get the agent's conversation history
    agent = session[session_id]["review_agent"]
    history = agent.messages  # Access the agent's stored message history
    
    # Save the history to database
    if history:
        history_entries = [{
            "session_id": session_id,
            "timestamp": datetime.datetime.now(),
            "entry": {
                "role": msg.source,
                "content": msg.content
            }
        } for msg in history]
        # insert_many is synchronous, so we don't need to await it
        db.review_history.insert_many(history_entries)

async def stop_session(session_id: str):
    # Save session history to database before removing
    await save_session_history(session_id)
    session.pop(session_id, None)

async def get_session(session_id: str):
    return session[session_id]

async def generate_initial_question(session_id: str):
    agent = study_review_agent.make_new_study_question_agent(session[session_id]["topic"])
    response = await agent.send_message(f"Please generate a question about the topic {session[session_id]['topic']}")
    return response

async def review_user_explanation(session_id: str, user_explanation: str):
    agent = session[session_id]["review_agent"]
    # Send the explanation to the agent - it will maintain its own history
    response = await agent.send_message(user_explanation)
    return response



