import time
from http.client import responses
import os
import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

import boundary.llms.moonshot
from agent.syllabus_agent import syllabus_agent
from model.agent import Agent
from boundary.llms.moonshot import moonshotChatReceiver
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

# Load environment variables
load_dotenv()

# MongoDB Connection
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client.buffer_size_db
analysis_collection = db.analysis
calendar_collection = db.calendars
users_collection = db.users

# Abort message, used in agent termination
ABORT_MESSAGE = "$ABORT"

# Retrieves the syllabus from the uploaded PDF
# TODO: Handle Syllabus from remote URL
async def retrieve_syllabus(username=None, course_id="14194"):
    """Retrieve the syllabus PDF content for a specific user and course
    
    Args:
        username (str, optional): Username to retrieve syllabus for
        course_id (str, optional): Course ID to retrieve syllabus for
        
    Returns:
        str: JSON string of the syllabus content or error message
    """
    # Only use the type_username_course format
    if not username or not course_id:
        return json.dumps({"error": "Both username and course ID are required to retrieve syllabus."})
        
    filename = f"syllabus_{username}_{course_id}.pdf"
    file_path = os.path.join("uploads", filename)
    
    # Check if the file exists
    if not os.path.exists(file_path):
        return json.dumps({"error": f"No syllabus file found for user '{username}' and course '{course_id}'. Please upload a syllabus first."})
    
    pdf_text = file_parser.extract_text_from_pdf(file_path)
    if pdf_text == {}:
        return json.dumps({"error": "Failed to extract text from syllabus file."})
    return json.dumps(pdf_text)

# Retrieves the calendar from the uploaded PDF
# TODO: Handle Calendar from remote URL
async def retrieve_calendar(username=None, course_id=None):
    """Retrieve the calendar PDF content for a specific user and course
    
    Args:
        username (str, optional): Username to retrieve calendar for
        course_id (str, optional): Course ID to retrieve calendar for
        
    Returns:
        str: JSON string of the calendar content or error message
    """
    # Only use the type_username_course format
    if not username or not course_id:
        return json.dumps({"error": "Both username and course ID are required to retrieve calendar."})
        
    filename = f"calendar_{username}_{course_id}.pdf"
    file_path = os.path.join("uploads", filename)
    
    # Check if the file exists
    if not os.path.exists(file_path):
        return json.dumps({"error": f"No calendar file found for user '{username}' and course '{course_id}'. Please upload a calendar first."})
    
    pdf_text = file_parser.extract_text_from_pdf(file_path)
    if pdf_text == {}:
        return json.dumps({"error": "Failed to extract text from calendar file."})
    return json.dumps(pdf_text)

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

def mark_files_updated(username=None, course_id=None, file_type=None):
    """Mark that syllabus and calendar files have been updated for a specific user and course
    
    Args:
        username (str, optional): Username to mark update flags for
        course_id (str, optional): Course ID to mark update flags for
        file_type (str, optional): Type of file that was updated (syllabus or calendar)
    """
    if username:
        # Create query based on username and course_id if provided
        query = {"username": username}
        if course_id:
            query["course_id"] = course_id
            
        # Create update document based on file_type
        update_doc = {"$set": {"flags_updated_at": datetime.datetime.utcnow()}}
        
        if file_type == "syllabus" or file_type is None:
            update_doc["$set"]["syllabus_updated"] = True
            
        if file_type == "calendar" or file_type is None:
            update_doc["$set"]["calendar_updated"] = True
            
        users_collection.update_one(
            query,
            update_doc,
            upsert=True
        )

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
                schedule_str = json.dumps(schedule_data) if not isinstance(schedule_data, str) else schedule_data
                make_google_calendar(schedule_str, username, course_id)
            
            # Return the schedule directly
            return json.dumps(schedule_data) if not isinstance(schedule_data, str) else schedule_data
    
    # Step 2: Do the generation
    # Step 2a: Check if syllabus has been analyzed and hasn't been updated
    analysis_response = None
    if username and not force_refresh and not user_syllabus_updated:
        # Create query based on username and course_id if provided
        query = {"username": username}
        if course_id:
            query["course_id"] = course_id
            
        cached_analysis = analysis_collection.find_one(query)
        if cached_analysis:
            print(f"Using cached analysis for user: {username}, course: {course_id}")
            analysis_response = cached_analysis["analysis"]
    
    # Step 2b: If no cached analysis or syllabus updated, generate new analysis
    if analysis_response is None:
        # Take Syllabus
        syllabus_text = await retrieve_syllabus(username, course_id)
        if "error" in json.loads(syllabus_text):
            return syllabus_text

        # Extract tasks from syllabus
        response = await syllabus_agent.send_message(syllabus_text)
        print(response)
        response_parsed = json.dumps(extract_tasks(response))
        print(response_parsed)
        
        analysis_response = response
        
        # Save analysis to database if username is provided
        if username:
            analysis_data = {
                "username": username,
                "analysis": analysis_response,
                "created_at": datetime.datetime.utcnow()
            }
            # Add course_id if provided
            if course_id:
                analysis_data["course_id"] = course_id
                
            # Create query based on username and course_id if provided
            query = {"username": username}
            if course_id:
                query["course_id"] = course_id
                
            analysis_collection.update_one(
                query,
                {"$set": analysis_data},
                upsert=True
            )
    
    # Step 2c: Generate schedule from analysis
    # Get calendar/schedule
    schedule_text = await retrieve_calendar(username, course_id)
    if "error" in json.loads(schedule_text):
        return schedule_text
    
    # Generate study schedule from tasks and calendar
    intro = """Here is the course tasks analysis.\n"""
    bring_in = """Here is the schedule.\n"""
    
    # Extract tasks from the analysis response
    response_parsed = json.dumps(extract_tasks(analysis_response))

    time.sleep(2)
    # Generate the schedule
    schedule_response = await planAgent.send_message(intro + response_parsed + bring_in + schedule_text)
    print(schedule_response)
    
    # Save schedule to database if username is provided
    if username:
        schedule_data = json_extractor(schedule_response)
        calendar_data = {
            "username": username,
            "schedule": schedule_data,
            "created_at": datetime.datetime.utcnow()
        }
        # Add course_id if provided
        if course_id:
            calendar_data["course_id"] = course_id
            
        # Create query based on username and course_id if provided
        query = {"username": username}
        if course_id:
            query["course_id"] = course_id
            
        calendar_collection.update_one(
            query,
            {"$set": calendar_data},
            upsert=True
        )
    
    # Step 3: If asked to create Google Calendar API, create it
    if make_schedule:
        make_google_calendar(schedule_response, username, course_id)
    
    # Reset update flags after processing
    if username:
        # Create query based on username and course_id if provided
        query = {"username": username}
        if course_id:
            query["course_id"] = course_id
            
        users_collection.update_one(
            query,
            {"$set": {
                "syllabus_updated": False,
                "calendar_updated": False,
                "flags_updated_at": datetime.datetime.utcnow()
            }},
            upsert=True
        )
    
    return schedule_response

def make_google_calendar(plan: str, username=None, course_id=None):
    """Create Google Calendar events from a study plan
    
    Args:
        plan (str): The study plan to create events from
        username (str, optional): Username to associate events with
        course_id (str, optional): Course ID to associate events with
    """
    plan = json_extractor(plan)
    generate_google = True
    if generate_google:
        service = boundary.googleCalendar.get_calendar_service()
        for i in plan[:5]:
            times, timee = boundary.googleCalendar.convert_md_to_datetime_range(i["date"])
            for item in i["dues"]:
                print(i, item)
                # Add course information to event description if available
                description = f"Course: {course_id}" if course_id else ""
                boundary.googleCalendar.create_event(
                    service=service,
                    summary=item,
                    location="",
                    description=description,
                    start_time=times,
                    end_time=timee
                )

def extract_tasks(text):
    txt = json_extractor(text)
    return txt["tasks"]

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
    
    # Find all documents for this user in users_collection
    user_courses = list(users_collection.find({"username": username}, {"_id": 0, "course_id": 1, "course_name": 1}))
    
    # Filter out documents without course_id
    user_courses = [course for course in user_courses if "course_id" in course]
    
    # Print debug info
    print(f"Found {len(user_courses)} courses for user {username}")
    
    return user_courses

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
    
    # Check if course already exists
    existing_course = users_collection.find_one({"username": username, "course_id": course_id})
    if existing_course:
        return {"success": False, "error": f"Course with ID {course_id} already exists for user {username}"}
    
    # Add the course
    result = users_collection.insert_one({
        "username": username,
        "course_id": course_id,
        "course_name": course_name,
        "created_at": datetime.datetime.utcnow(),
        "syllabus_updated": False,
        "calendar_updated": False
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
    
    # Find the course to get its ID
    course = users_collection.find_one({"username": username, "course_name": course_name})
    if not course:
        return {"success": False, "error": f"Course {course_name} not found for user {username}"}
    
    course_id = course.get("course_id")
    
    # Delete the course from users_collection
    result = users_collection.delete_one({"username": username, "course_name": course_name})
    
    # Also delete any related files
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
    
    if result.deleted_count > 0:
        return {"success": True, "message": f"Course {course_name} deleted successfully"}
    else:
        return {"success": False, "error": f"Failed to delete course {course_name}"}

if __name__ == '__main__':
    print(asyncio.run(run_schedule_analysis()))
