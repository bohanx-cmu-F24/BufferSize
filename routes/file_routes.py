import flask
from flask import request, jsonify
import os
from werkzeug.utils import secure_filename
from controller.file_service import mark_files_updated
from controller.schedule_service import get_user_courses, add_user_course

# Blueprint for file routes
file_bp = flask.Blueprint('file', __name__)

# Constants
UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'pdf'}
TYPE_OF_FILES = {"syllabus", "calendar"}

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@file_bp.route('/upload_file', methods=['POST'])
async def upload_pdf():
    try:
        # Get user information from headers
        token = request.headers.get('x-application-token')
        user_id = request.headers.get('x-application-uid')
        username = request.headers.get('x-application-username')
        
        # Get course_id from request body or query parameters
        data = request.form.to_dict()
        course_id = data.get('course_id') or request.args.get('course_id')
        
        print(f"POST /upload_file - username: {username}, course_id: {course_id}, files: {list(request.files.keys())}")
        
        # Check for required parameters
        if not course_id:
            return jsonify({"error": "Course ID is required"}), 400
        
        # If username is not provided, use a default or anonymous user
        if not username:
            username = "anonymous"
            print(f"No username provided, using '{username}' as default")
        
        # Check if the course exists for the user (skip for anonymous users)
        if username != "anonymous":
            user_courses = get_user_courses(username)
            if not any(course.get("course_id") == course_id for course in user_courses):
                print(f"Course {course_id} not found for user {username}")
                # Instead of returning error, we'll create the course automatically
                add_user_course(username, course_id, f"Course {course_id}")
                print(f"Created course {course_id} for user {username}")
        
        # Check if any files were uploaded
        if not request.files:
            return jsonify({"error": "No files were uploaded"}), 400
        
        for item in request.files:
            if item not in TYPE_OF_FILES:
                print(f"Skipping unknown file type: {item}")
                continue
                
            file = request.files[item]
            if file and allowed_file(file.filename):
                # Create user and course specific filename
                filename = secure_filename(f"{item}_{username}_{course_id}.pdf")
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                
                print(f"Saved file: {filename}")
                
                # Mark files as updated in chat_service with username and course_id
                mark_files_updated(username, course_id, file_type=item)
                print(f"Marked {item} as updated for user {username} and course {course_id}")
            else:
                return jsonify({"error": f"Invalid file type for {item}"}), 400
        
        return jsonify({"message": "File uploaded successfully"}), 200
    except Exception as e:
        print(f"Error saving file: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to save file: {str(e)}"}), 500

@file_bp.route("/upload_file", methods=["GET"])
def get_upload_file():
    # Get user information from headers
    token = request.headers.get('x-application-token')
    user_id = request.headers.get('x-application-uid')
    username = request.headers.get('x-application-username')
    course_id = request.args.get('course_id')
    
    print(f"GET /upload_file - username: {username}, course_id: {course_id}")

    if not username:
        return jsonify({"error": "Username is required"}), 400
    
    # MongoDB Connection
    from pymongo import MongoClient
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # MongoDB Connection
    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    db = client.buffer_size_db
    users_collection = db.users
    courses_collection = db.courses
    
    # If course_id is provided, check files for that specific course
    if course_id:
        # Query based on username and course_id
        query = {"username": username, "course_id": course_id}
        user_data = users_collection.find_one(query)
        
        if user_data:
            syllabus_exist = user_data.get("syllabus_updated", False)
            calendar_exist = user_data.get("calendar_updated", False)
            return jsonify({
                "syllabus": syllabus_exist,
                "calendar": calendar_exist,
                "course_id": course_id
            }), 200
        else:
            return jsonify({
                "syllabus": False,
                "calendar": False,
                "course_id": course_id
            }), 200
    else:
        # If no course_id provided, get all courses for the user and their file status
        user_courses = get_user_courses(username)
        course_files = []
        
        for course in user_courses:
            course_id = course.get("course_id")
            query = {"username": username, "course_id": course_id}
            user_data = users_collection.find_one(query)
            
            if user_data:
                course_files.append({
                    "course_id": course_id,
                    "course_name": course.get("course_name"),
                    "syllabus": user_data.get("syllabus_updated", False),
                    "calendar": user_data.get("calendar_updated", False)
                })
            else:
                course_files.append({
                    "course_id": course_id,
                    "course_name": course.get("course_name"),
                    "syllabus": False,
                    "calendar": False
                })
        
        return jsonify({"courses": course_files}), 200

# Add OPTIONS method handler for CORS preflight requests
@file_bp.route("/upload_file", methods=["OPTIONS"])
def handle_options():
    return "", 204
