import os
import json
import datetime
from datetime import timezone
from pymongo import MongoClient
from dotenv import load_dotenv
import util.file_parser as file_parser

# Load environment variables
load_dotenv()

# MongoDB Connection
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client.buffer_size_db
users_collection = db.users

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
        update_doc = {"$set": {"flags_updated_at": datetime.datetime.now(timezone.utc)}}
        
        if file_type == "syllabus" or file_type is None:
            update_doc["$set"]["syllabus_updated"] = True
            
        if file_type == "calendar" or file_type is None:
            update_doc["$set"]["calendar_updated"] = True
            
        users_collection.update_one(
            query,
            update_doc,
            upsert=True
        )