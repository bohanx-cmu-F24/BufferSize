import os
import json
import datetime
import asyncio
import agent.study_review_agent as study_review_agent
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client.buffer_size_db

# Dictionary to store active sessions
sessions = {}

# Constants for session management
MAX_EXPLANATIONS = 3  # Maximum number of user explanations before terminating
SESSION_TIMEOUT = 10 * 60  # 10 minutes in seconds

def get_review_topics(username: str, course_id: str):
    """Get the available review topics for a course"""
    # Get topics from database
    topics_doc = db.analysis.find_one({"username": username, "course_id": course_id})
        
    # If no topics found in database, return empty list
    if not topics_doc:
        return []
    
    # Check for topics in the analysis.topic array (based on actual document structure)
    if "analysis" in topics_doc and isinstance(topics_doc["analysis"], dict):
        if "topic" in topics_doc["analysis"] and isinstance(topics_doc["analysis"]["topic"], list):
            # Format topics to match the expected TopicItem interface (id and name)
            formatted_topics = []
            for i, topic_name in enumerate(topics_doc["analysis"]["topic"]):
                if isinstance(topic_name, str):
                    formatted_topics.append({
                        "id": f"topic{i+1}",  # Generate an ID based on index
                        "name": topic_name
                    })
            
            # Return the formatted topics
            return formatted_topics
    
    # If we couldn't find or extract topics, return empty list
    return []

async def start_session(username: str, course_id: str, topic: str):
    """Start a new review session with a mock classmate"""
    session_id = f"{username}_{course_id}_{topic}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    
    # Create a new session object
    sessions[session_id] = {
        "username": username,
        "course_id": course_id,
        "topic": topic,
        "review_agent": study_review_agent.make_new_study_review_agent(topic),
        "question_agent": study_review_agent.make_new_study_question_agent(topic),
        "explanation_count": 0,
        "last_activity": datetime.datetime.now(),
        "is_active": True
    }
    
    # Schedule session cleanup after timeout
    asyncio.create_task(monitor_session_timeout(session_id))
    
    return session_id

async def monitor_session_timeout(session_id: str):
    """Monitor session for timeout and clean up if inactive"""
    while session_id in sessions and sessions[session_id]["is_active"]:
        # Check if session has been inactive for too long
        time_since_activity = (datetime.datetime.now() - sessions[session_id]["last_activity"]).total_seconds()
        
        if time_since_activity > SESSION_TIMEOUT:
            await stop_session(session_id, reason="timeout")
            break
            
        # Check every 30 seconds
        await asyncio.sleep(30)

async def save_session_history(session_id: str):
    """Save the session conversation history to the database"""
    if session_id not in sessions:
        return
        
    # Get the agent's conversation history
    agent = sessions[session_id]["review_agent"]
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
        
        # Insert the history entries into the database
        db.review_history.insert_many(history_entries)

async def stop_session(session_id: str, reason="user_request"):
    """Stop the review session and clean up resources"""
    if session_id not in sessions:
        return {"status": "error", "message": "Session not found"}
    
    # Save session history to database before removing
    await save_session_history(session_id)
    
    # Record session termination reason
    termination_info = {
        "session_id": session_id,
        "username": sessions[session_id]["username"],
        "course_id": sessions[session_id]["course_id"],
        "topic": sessions[session_id]["topic"],
        "explanation_count": sessions[session_id]["explanation_count"],
        "termination_reason": reason,
        "timestamp": datetime.datetime.now()
    }
    
    # Save termination info to database
    db.review_sessions.insert_one(termination_info)
    
    # Remove the session
    sessions[session_id]["is_active"] = False
    sessions.pop(session_id, None)
    
    return {"status": "success", "message": f"Session terminated: {reason}"}

async def get_session(session_id: str):
    """Get the current session information"""
    if session_id not in sessions:
        return None
        
    # Update last activity timestamp
    sessions[session_id]["last_activity"] = datetime.datetime.now()
    
    return sessions[session_id]

async def generate_initial_question(session_id: str):
    """Generate the initial question to start the review session"""
    if session_id not in sessions:
        return {"status": "error", "message": "Session not found"}
    
    # Update last activity timestamp
    sessions[session_id]["last_activity"] = datetime.datetime.now()
    
    # Get the topic from the session
    topic = sessions[session_id]["topic"]
    
    # Use the question agent to generate an initial question
    question_agent = sessions[session_id]["question_agent"]
    response = await question_agent.send_message(f"Please generate a question about the topic {topic}")
    
    # Store this as the first message in the review agent's history
    review_agent = sessions[session_id]["review_agent"]
    await review_agent.send_message(f"I'm having trouble understanding {topic}. {response}")
    
    return {
        "status": "success", 
        "question": response,
        "message": f"I'm having trouble understanding {topic}. {response}"
    }

async def review_user_explanation(session_id: str, user_explanation: str):
    """Process the user's explanation and provide feedback or follow-up questions"""
    if session_id not in sessions:
        return {"status": "error", "message": "Session not found"}
    
    # Update last activity timestamp
    sessions[session_id]["last_activity"] = datetime.datetime.now()
    
    # Increment explanation count
    sessions[session_id]["explanation_count"] += 1
    
    # Send the explanation to the agent
    agent = sessions[session_id]["review_agent"]
    response = await agent.send_message(user_explanation)
    
    # Parse the JSON response from the agent
    try:
        parsed_response = json.loads(response)
        
        # Check if we should continue the conversation
        continue_conversation = parsed_response.get("continue_conversation", True)
        
        # Check if we've reached the maximum number of explanations
        if sessions[session_id]["explanation_count"] >= MAX_EXPLANATIONS:
            await stop_session(session_id, reason="max_explanations_reached")
            return {
                "status": "success",
                "message": parsed_response.get("response", "Thank you for your explanations! I think I understand now."),
                "evaluation": parsed_response.get("evaluation", "Good"),
                "session_ended": True,
                "reason": "Maximum number of explanations reached"
            }
        
        # Check if the agent wants to end the conversation
        if not continue_conversation:
            await stop_session(session_id, reason="agent_ended")
            return {
                "status": "success",
                "message": parsed_response.get("response", "Thank you for your explanation!"),
                "evaluation": parsed_response.get("evaluation", "Good"),
                "session_ended": True,
                "reason": "Agent ended conversation"
            }
        
        # Continue the conversation
        return {
            "status": "success",
            "message": parsed_response.get("response", "Thank you for your explanation!"),
            "evaluation": parsed_response.get("evaluation", "Needs Improvement"),
            "session_ended": False
        }
        
    except json.JSONDecodeError:
        # If the response is not valid JSON, return it as is
        return {
            "status": "success",
            "message": response,
            "session_ended": False
        }

async def get_session_status(session_id: str):
    """Get the current status of a session"""
    if session_id not in sessions:
        return {"status": "error", "message": "Session not found or expired"}
    
    session = sessions[session_id]
    
    return {
        "status": "success",
        "is_active": session["is_active"],
        "explanation_count": session["explanation_count"],
        "topic": session["topic"],
        "last_activity": session["last_activity"].isoformat(),
        "time_remaining": SESSION_TIMEOUT - (datetime.datetime.now() - session["last_activity"]).total_seconds()
    }
