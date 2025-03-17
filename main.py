import asyncio
import os
import flask
from flask import request, jsonify
from werkzeug.utils import secure_filename
from flask_cors import CORS
import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId
import bcrypt
from dotenv import load_dotenv
from boundary.llms.moonshot import moonshotChatReceiver
from controller.chat_service import run_schedule_analysis, mark_files_updated
from util.text_extractor import json_extractor
import datetime
import json

# Load environment variables
load_dotenv()

app = flask.Flask(__name__)
CORS(app)

# MongoDB Connection
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client.buffer_size_db
users_collection = db.users
courses_collection = db.courses

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'pdf'}
TYPE_OF_FILES = {"syllabus", "calendar"}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_user_courses(username):
    user_courses = courses_collection.find_one({"username": username})
    if user_courses:
        return user_courses.get("courses", [])
    else:
        return []


def add_user_course(username, course_id, course_name):
    user_courses = get_user_courses(username)
    if course_id in [course.get("course_id") for course in user_courses]:
        return {"success": False, "error": "Course already exists"}
    else:
        user_courses.append({"course_id": course_id, "course_name": course_name})
        courses_collection.update_one({"username": username}, {"$set": {"courses": user_courses}}, upsert=True)
        return {"success": True, "message": "Course added successfully"}


def delete_user_course(username, course_name):
    user_courses = get_user_courses(username)
    course_to_delete = next((course for course in user_courses if course.get("course_name") == course_name), None)
    if course_to_delete:
        user_courses.remove(course_to_delete)
        courses_collection.update_one({"username": username}, {"$set": {"courses": user_courses}})
        return {"success": True, "message": "Course deleted successfully"}
    else:
        return {"success": False, "error": "Course not found"}


@app.route('/upload_file', methods=['POST'])
async def upload_pdf():
    try:
        # Get user information from headers
        token = request.headers.get('x-application-token')
        user_id = request.headers.get('x-application-uid')
        username = request.headers.get('x-application-username')
        
        # Get course_id from request body
        data = request.form.to_dict()
        course_id = data.get('course_id')
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
            
        if not course_id:
            return jsonify({"error": "Course ID is required"}), 400
        
        for item in request.files:
            if item not in TYPE_OF_FILES:
                continue
            print(item)
            file = request.files[item]
            if file and allowed_file(file.filename):
                # Create user and course specific filename
                filename = secure_filename(f"{item}_{username}_{course_id}.pdf")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Mark files as updated in chat_service with username and course_id
                mark_files_updated(username, course_id)
            else:
                return jsonify({"error": "Invalid file type"}), 400
        return jsonify({"message": "File uploaded successfully"}), 200
    except Exception as e:
        print(f"Error saving file: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to save file: {str(e)}"}), 500

@app.route("/upload_file", methods=["GET"])
def get_upload_file():
    syllabus_exist = os.path.exists("uploads/syllabus.pdf")
    calendar_exist = os.path.exists("uploads/calendar.pdf")
    return jsonify({"syllabus": syllabus_exist, "calendar": calendar_exist}), 200


@app.route("/schedule", methods=["GET"])
async def get_schedule():
    try:
        # Get user information from headers
        token = request.headers.get('x-application-token')
        user_id = request.headers.get('x-application-uid')
        username = request.headers.get('x-application-username')
        
        # Get parameters
        makeCalendar = request.args.get('make_calendar', 'false').lower() == 'true'
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        course_id = request.args.get('course_id')
        
        if not username:
            return jsonify({
                "success": False,
                "message": "Username is required"
            }), 400
            
        if not course_id:
           course_id = "undefined"
        
        # Call schedule analysis with course_id
        if makeCalendar:
            result = await run_schedule_analysis(makeCalendar, username, force_refresh, course_id)
        else:
            result = await run_schedule_analysis(make_schedule=False, username=username, force_refresh=force_refresh, course_id=course_id)
        
        # Check if result contains an error message
        try:
            result_json = json.loads(result)
            if isinstance(result_json, dict) and "error" in result_json:
                return jsonify({
                    "success": False,
                    "message": result_json["error"]
                }), 400
        except (json.JSONDecodeError, TypeError):
            # Not a JSON with error, continue processing
            pass
        
        # Check if result is already JSON or needs to be extracted
        try:
            # Try to parse as JSON first (in case it's already a JSON string)
            parsed_result = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            # If not valid JSON, extract it
            parsed_result = json_extractor(result)
            
        print(parsed_result)

        # Return the results
        return jsonify({
            "success": True,
            "message": "Study schedule generated successfully",
            "data": parsed_result
        }), 200

    except Exception as e:
        print(f"Error generating schedule: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Failed to generate schedule: {str(e)}"
        }), 500


@app.route('/login', methods=['POST'])
def login():
    """Login a user or create a new account if the user doesn't exist"""
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Username and password are required"}), 400
            
        username = data['username']
        password = data['password']
        
        # Check if user exists
        user = users_collection.find_one({"username": username})
        
        if user:
            # User exists, verify password
            if bcrypt.checkpw(password.encode('utf-8'), user['password']):
                # Password matches
                return jsonify({
                    "message": "Login successful",
                    "user_id": str(user["_id"]),
                    "username": user["username"]
                }), 200
            else:
                # Password doesn't match
                return jsonify({"error": "Invalid password"}), 401
        else:
            # User doesn't exist, create a new account
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            new_user = {
                "username": username,
                "password": hashed_password,
                "created_at": datetime.datetime.utcnow()
            }
            
            result = users_collection.insert_one(new_user)
            
            return jsonify({
                "message": "New account created successfully",
                "user_id": str(result.inserted_id),
                "username": username
            }), 201
            
    except Exception as e:
        print(f"Error logging in: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Username and password are required"}), 400
            
        username = data['username']
        password = data['password']
        
        # Check if username already exists
        existing_user = users_collection.find_one({"username": username})
        if existing_user:
            return jsonify({"error": "Username already exists"}), 409
        
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create new user
        new_user = {
            "username": username,
            "password": hashed_password,
            "created_at": datetime.datetime.utcnow()
        }
        
        result = users_collection.insert_one(new_user)
        
        return jsonify({
            "message": "User registered successfully",
            "user_id": str(result.inserted_id),
            "username": username
        }), 201
        
    except Exception as e:
        print(f"Error registering user: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/courses", methods=["GET"])
def get_courses():
    """Get all courses for the authenticated user
    
    Returns:
        JSON response with list of courses
    """
    try:
        # Get user information from headers
        token = request.headers.get('x-application-token')
        user_id = request.headers.get('x-application-uid')
        username = request.headers.get('x-application-username')
        
        # Fallback to query parameters if username is not in headers
        if not username and 'username' in request.args:
            username = request.args.get('username')
        
        if not username:
            response = jsonify({
                "success": False,
                "message": "Username is required in either headers or query parameters"
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        # Get courses for the user
        courses = get_user_courses(username)
        
        response = jsonify({
            "success": True,
            "message": "Courses retrieved successfully",
            "data": courses
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
        
    except Exception as e:
        print(f"Error getting courses: {str(e)}")
        import traceback
        traceback.print_exc()
        response = jsonify({
            "success": False,
            "message": f"Failed to get courses: {str(e)}"
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route("/courses", methods=["POST"])
def add_course():
    """Add a new course for the authenticated user
    
    Request body should contain:
    - course_id: ID of the course
    - course_name: Name of the course
    
    Returns:
        JSON response with result of the operation
    """
    try:
        # Get user information from headers
        token = request.headers.get('x-application-token')
        user_id = request.headers.get('x-application-uid')
        username = request.headers.get('x-application-username')
        
        # Fallback to query parameters if username is not in headers
        if not username and 'username' in request.args:
            username = request.args.get('username')
        
        if not username:
            response = jsonify({
                "success": False,
                "message": "Username is required in either headers or query parameters"
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        # Get course data from request body - handle both JSON and form data
        data = None
        
        # Try to get JSON data
        if request.is_json:
            data = request.get_json()
        # If not JSON, try to get form data
        elif request.form:
            data = request.form.to_dict()
        # If still no data, try to force parse JSON
        elif request.data:
            try:
                data = json.loads(request.data)
            except:
                pass
                
        if not data:
            response = jsonify({
                "success": False,
                "message": "Request body is required in either JSON or form format"
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        course_id = data.get('course_id')
        course_name = data.get('course_name')
        
        if not course_id or not course_name:
            response = jsonify({
                "success": False,
                "message": "Course ID and course name are required"
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        # Add the course
        result = add_user_course(username, course_id, course_name)
        
        if result.get("success"):
            response = jsonify({
                "success": True,
                "message": result.get("message")
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 201
        else:
            response = jsonify({
                "success": False,
                "message": result.get("error")
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
    except Exception as e:
        print(f"Error adding course: {str(e)}")
        import traceback
        traceback.print_exc()
        response = jsonify({
            "success": False,
            "message": f"Failed to add course: {str(e)}"
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route("/courses/<course_name>", methods=["DELETE"])
def delete_course(course_name):
    """Delete a course for the authenticated user
    
    Args:
        course_name: Name of the course to delete
    
    Returns:
        JSON response with result of the operation
    """
    try:
        # Get user information from headers
        token = request.headers.get('x-application-token')
        user_id = request.headers.get('x-application-uid')
        username = request.headers.get('x-application-username')
        
        # Fallback to query parameters if username is not in headers
        if not username and 'username' in request.args:
            username = request.args.get('username')
        
        if not username:
            response = jsonify({
                "success": False,
                "message": "Username is required in either headers or query parameters"
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        # Delete the course
        result = delete_user_course(username, course_name)
        
        if result.get("success"):
            response = jsonify({
                "success": True,
                "message": result.get("message")
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 200
        else:
            response = jsonify({
                "success": False,
                "message": result.get("error")
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 404
        
    except Exception as e:
        print(f"Error deleting course: {str(e)}")
        import traceback
        traceback.print_exc()
        response = jsonify({
            "success": False,
            "message": f"Failed to delete course: {str(e)}"
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500


# Add OPTIONS method handler for CORS preflight requests
@app.route("/courses", methods=["OPTIONS"])
@app.route("/courses/<course_name>", methods=["OPTIONS"])
def handle_options(course_name=None):
    response = jsonify({})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,x-application-token,x-application-uid,x-application-username')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,DELETE,OPTIONS')
    return response, 200

if __name__ == "__main__":
    app.run(port=2817)