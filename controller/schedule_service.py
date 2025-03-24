import time
from http.client import responses
import os
import datetime
from datetime import timezone
from pymongo import MongoClient
from dotenv import load_dotenv

import boundary.llms.moonshot
from agent.syllabus_agent import syllabus_agent
from model.agent import Agent
from boundary.llms.moonshot import MoonshotChatReceiver
import asyncio
from autogen_agentchat.agents import UserProxyAgent, AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from boundary import googleCalendar
import json
from prompts import system_prompt
from agent.plan_agent import planAgent
import util.file_parser as file_parser
from util.text_extractor import json_extractor
from util.json_fixer import fix_json
from controller.file_service import retrieve_syllabus, retrieve_calendar, mark_files_updated

# Load environment variables
load_dotenv()

# MongoDB Connection
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client.buffer_size_db
analysis_collection = db.analysis
calendar_collection = db.calendars
users_collection = db.users
courses_collection = db.courses

# Abort message, used in agent termination
ABORT_MESSAGE = "$ABORT"

async def get_schedule(username=None, course_id=None):
    """Get the schedule text for a specific user and course
    
    Args:
        username (str, optional): Username to get schedule for
        course_id (str, optional): Course ID to get schedule for
        
    Returns:
        str: The schedule text
    """
    schedule_text = await retrieve_calendar(username, course_id)
    return schedule_text

def get_user_update_flags(username, course_id=None):
    """Get user-specific update flags from the database
    
    Args:
        username (str): Username to get flags for
        course_id (str, optional): Course ID to get flags for
        
    Returns:
        tuple: (syllabus_updated, calendar_updated) flags for the user
    """
    if not username:
        return False, False
    
    # Query based on username and course_id if provided
    query = {"username": username}
    if course_id:
        query["course_id"] = course_id
        
    user_data = users_collection.find_one(query)
    if user_data:
        return (
            user_data.get("syllabus_updated", False),
            user_data.get("calendar_updated", False)
        )
    
    return False, False

async def run_schedule_analysis(make_schedule=False, username=None, force_refresh=False, course_id=None):
    """Generate study schedule from academic calendar
    
    Logic flow:
    1. Check if a calendar/schedule has been generated and not updated
       - If so, use pre-generated schedule and skip generation
    2. Else, do the generation:
       - If syllabus has been analyzed and hasn't been updated, use pre-generated analysis
       - Else, generate a new analysis and save it
       - Pass the analysis to generate a schedule
    3. If asked to create Google Calendar API, create it (regardless of pre-gen or not)
    
    Args:
        make_schedule (bool): Whether to generate Google Calendar events
        username (str): Username for caching results
        force_refresh (bool): Force regeneration of analysis
        course_id (str): Course ID for specific course data
        
    Returns:
        str: The generated schedule analysis
    """
    # Get user-specific update flags
    user_syllabus_updated, user_calendar_updated = get_user_update_flags(username, course_id)
    
    # Step 1: Check if a calendar/schedule has been generated and not updated
    if username and not force_refresh and not user_syllabus_updated and not user_calendar_updated:
        # Create query based on username and course_id if provided
        query = {"username": username}
        if course_id:
            query["course_id"] = course_id
            
        cached_calendar = calendar_collection.find_one(query)
        if cached_calendar and "schedule" in cached_calendar:
            print(f"Using cached schedule for user: {username}, course: {course_id}")
            schedule_data = cached_calendar["schedule"]
            
            # If make_schedule is requested, create Google Calendar events
            if make_schedule:
                # Convert schedule_data to string if it's not already
                if not isinstance(schedule_data, str):
                    schedule_data = json.dumps(schedule_data)
                await make_google_calendar(schedule_data, username, course_id)
                
            # Return the cached schedule
            if isinstance(schedule_data, str):
                return schedule_data
            return json.dumps(schedule_data)
    
    # Step 2: Generate a new analysis and schedule
    # Check if syllabus has been analyzed and hasn't been updated
    syllabus_data = None
    if username and not force_refresh and not user_syllabus_updated:
        # Create query based on username and course_id if provided
        query = {"username": username}
        if course_id:
            query["course_id"] = course_id
            
        cached_analysis = analysis_collection.find_one(query)
        if cached_analysis and "analysis" in cached_analysis:
            print(f"Using cached syllabus analysis for user: {username}, course: {course_id}")
            syllabus_data = cached_analysis["analysis"]
    
    # If no cached syllabus analysis or it's been updated, generate a new one
    if syllabus_data is None:
        # Get syllabus text
        syllabus_text = await retrieve_syllabus(username, course_id)
        
        try:
            # Parse syllabus text as JSON
            syllabus_json = await fix_json(syllabus_text)
            
            # Generate syllabus analysis
            print(f"Generating new syllabus analysis for user: {username}, course: {course_id}")
            syllabus_analysis = await syllabus_agent.send_message(json.dumps(syllabus_json))
            
            # Try to parse the analysis as JSON
            try:
                syllabus_data = await fix_json(syllabus_analysis)
            except ValueError as e:
                print(f"Error parsing syllabus analysis: {e}")
                return json.dumps({"error": "Failed to parse syllabus analysis."})
            
            # Save the analysis to the database if username is provided
            if username:
                # Create query based on username and course_id if provided
                query = {"username": username}
                if course_id:
                    query["course_id"] = course_id
                    
                # Update or insert the analysis
                analysis_collection.update_one(
                    query,
                    {
                        "$set": {
                            "analysis": syllabus_data,
                            "updated_at": datetime.datetime.now(timezone.utc)
                        }
                    },
                    upsert=True
                )
                
                # Reset the syllabus_updated flag
                if user_syllabus_updated:
                    users_collection.update_one(
                        query,
                        {"$set": {"syllabus_updated": False}}
                    )
        except ValueError as e:
            print(f"Error parsing syllabus text: {e}")
            return json.dumps({"error": "Failed to parse syllabus text."})
    
    # Get schedule text
    schedule_text = await get_schedule(username, course_id)
    
    try:
        # Parse schedule text as JSON
        schedule_json = await fix_json(schedule_text)
        
        # Generate schedule
        print(f"Generating new schedule for user: {username}, course: {course_id}")
        schedule_prompt = f"Syllabus Analysis: {json.dumps(syllabus_data)}\n\nSchedule: {json.dumps(schedule_json)}"
        schedule_result = await planAgent.send_message(schedule_prompt)
        
        # Try to parse the schedule as JSON
        try:
            schedule_data = await fix_json(schedule_result)
        except ValueError as e:
            print(f"Error parsing schedule result: {e}")
            return json.dumps({"error": "Failed to parse schedule result."})
        
        # Save the schedule to the database if username is provided
        if username:
            # Create query based on username and course_id if provided
            query = {"username": username}
            if course_id:
                query["course_id"] = course_id
                
            # Update or insert the schedule
            calendar_collection.update_one(
                query,
                {
                    "$set": {
                        "schedule": schedule_data,
                        "updated_at": datetime.datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            
            # Reset the calendar_updated flag
            if user_calendar_updated:
                users_collection.update_one(
                    query,
                    {"$set": {"calendar_updated": False}}
                )
        
        # If make_schedule is requested, create Google Calendar events
        if make_schedule:
            await make_google_calendar(json.dumps(schedule_data), username, course_id)
        
        # Return the schedule
        if isinstance(schedule_data, str):
            return schedule_data
        return json.dumps(schedule_data)
    except ValueError as e:
        print(f"Error parsing schedule text: {e}")
        return json.dumps({"error": "Failed to parse schedule text."})

async def make_google_calendar(plan: str, username=None, course_id=None):
    """Create Google Calendar events from a study plan
    
    Args:
        plan (str): The study plan to create events from
        username (str, optional): Username to associate events with
        course_id (str, optional): Course ID to associate events with
        
    Returns:
        bool: True if events were created successfully, False otherwise
    """
    try:
        # Try to parse the plan as JSON
        plan_data = await fix_json(plan)
        
        # Extract events from the plan
        events = []
        if isinstance(plan_data, list):
            for day in plan_data:
                date_str = day.get("date", "")
                dues = day.get("dues", [])
                starts = day.get("start", [])
                
                # Add due events
                for due in dues:
                    events.append({
                        "summary": f"Due: {due}",
                        "description": f"Assignment due for {username or 'user'}'s course {course_id or 'unknown'}",
                        "start_date": date_str,
                        "end_date": date_str,
                        "location": ""
                    })
                    
                # Add start events
                for start in starts:
                    events.append({
                        "summary": f"Start: {start}",
                        "description": f"Start working on this for {username or 'user'}'s course {course_id or 'unknown'}",
                        "start_date": date_str,
                        "end_date": date_str,
                        "location": ""
                    })
        
        # Create Google Calendar events
        if events:
            # Pass the username to create_events to use the correct token
            googleCalendar.create_events(events, username=username)
            print(f"Created {len(events)} Google Calendar events for user {username or 'default'}")
        else:
            print("No events to create")
            
    except Exception as e:
        print(f"Error creating Google Calendar events: {e}")
        return False
    
    return True

def extract_tasks(text):
    """Extract tasks from text using the json_fixer
    
    Args:
        text (str): Text to extract tasks from
        
    Returns:
        dict or list: Extracted tasks
    """
    try:
        # Use the async fix_json function in a synchronous context
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(fix_json(text))
    except ValueError:
        # Fallback to the original json_extractor if fix_json fails
        return json_extractor(text)

def abort_func(_s):
    return ABORT_MESSAGE

def get_user_courses(username):
    """Get all courses for a specific user
    
    Args:
        username (str): Username to get courses for
        
    Returns:
        list: List of course objects with name and id
    """
    if not username:
        return []
    
    # Find the user document to get the list of course IDs
    user_doc = users_collection.find_one({"username": username})
    if not user_doc or "course_ids" not in user_doc or not user_doc["course_ids"]:
        return []
    
    # Get the course IDs from the user document
    course_ids = user_doc["course_ids"]
    
    # Fetch course details from the courses collection
    user_courses = list(courses_collection.find({"_id": {"$in": course_ids}}, {"_id": 1, "name": 1}))
    
    # Format the response
    formatted_courses = [
        {"course_id": str(course["_id"]), "course_name": course["name"]} 
        for course in user_courses
    ]
    
    # Print debug info
    print(f"Found {len(formatted_courses)} courses for user {username}")
    
    return formatted_courses

def add_user_course(username, course_id, course_name):
    """Add a course for a specific user
    
    Args:
        username (str): Username to add course for
        course_id (str): Course ID to add
        course_name (str): Course name to add
        
    Returns:
        dict: Result of the operation
    """
    if not username or not course_id or not course_name:
        return {"success": False, "error": "Username, course ID, and course name are all required"}
    
    # Check if course already exists in the courses collection
    existing_course = courses_collection.find_one({"_id": course_id})
    
    # If the course doesn't exist in the courses collection, add it
    if not existing_course:
        courses_collection.insert_one({
            "_id": course_id,
            "name": course_name,
            "created_at": datetime.datetime.now(timezone.utc)
            # Additional course attributes can be added here later
        })
    
    # Update the user document to include this course ID
    # First check if the user has this course already
    user_doc = users_collection.find_one({"username": username})
    
    if user_doc:
        # If user exists, check if they already have this course
        course_ids = user_doc.get("course_ids", [])
        
        if course_id in course_ids:
            return {"success": False, "error": f"Course with ID {course_id} already exists for user {username}"}
        
        # Add the course ID to the user's course_ids list
        users_collection.update_one(
            {"username": username},
            {"$push": {"course_ids": course_id}}
        )
    else:
        # If user doesn't exist, create a new user document
        users_collection.insert_one({
            "username": username,
            "course_ids": [course_id],
            "created_at": datetime.datetime.now(timezone.utc)
        })
    
    return {"success": True, "message": f"Course {course_name} added successfully"}

def delete_user_course(username, course_name):
    """Delete a course for a specific user by course name
    
    Args:
        username (str): Username to delete course for
        course_name (str): Course name to delete
        
    Returns:
        dict: Result of the operation
    """
    if not username or not course_name:
        return {"success": False, "error": "Username and course name are required"}
    
    # Find the course in the courses collection by name
    course = courses_collection.find_one({"name": course_name})
    if not course:
        return {"success": False, "error": f"Course {course_name} not found"}
    
    course_id = course["_id"]
    
    # Remove the course ID from the user's course_ids list
    result = users_collection.update_one(
        {"username": username},
        {"$pull": {"course_ids": course_id}}
    )
    
    if result.modified_count == 0:
        return {"success": False, "error": f"Course {course_name} not found for user {username}"}
    
    # Note: We're not deleting the course from the courses collection
    # as it might be used by other users. This is a design decision.
    # If you want to delete orphaned courses, you would need to implement
    # a cleanup process.
    
    # Delete any related files
    try:
        syllabus_path = os.path.join("uploads", f"syllabus_{username}_{course_id}.pdf")
        if os.path.exists(syllabus_path):
            os.remove(syllabus_path)
            
        calendar_path = os.path.join("uploads", f"calendar_{username}_{course_id}.pdf")
        if os.path.exists(calendar_path):
            os.remove(calendar_path)
    except Exception as e:
        print(f"Error deleting files: {str(e)}")
    
    # Delete any related data in other collections
    try:
        analysis_collection.delete_many({"username": username, "course_id": course_id})
        calendar_collection.delete_many({"username": username, "course_id": course_id})
    except Exception as e:
        print(f"Error deleting collection data: {str(e)}")
    
    return {"success": True, "message": f"Course {course_name} removed from user {username} successfully"}

if __name__ == '__main__':
    print(asyncio.run(run_schedule_analysis()))
