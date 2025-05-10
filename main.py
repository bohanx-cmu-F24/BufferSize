import os
import flask
import json
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import bcrypt

# Custom JSON encoder for MongoDB ObjectId
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super(MongoJSONEncoder, self).default(obj)

# Import route blueprints
from routes.schedule_routes import schedule_bp
from routes.file_routes import file_bp
from routes.review_routes import review_bp

# Load environment variables
load_dotenv()

# Setup secrets directory
SECRETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'secrets')
# Ensure the secrets directory exists
if not os.path.exists(SECRETS_DIR):
    os.makedirs(SECRETS_DIR)
    print(f"Created secrets directory at {SECRETS_DIR}")

# Make the secrets directory path available to other modules
os.environ['SECRETS_DIR'] = SECRETS_DIR

app = flask.Flask(__name__)
CORS(app)

# Configure app to use custom JSON encoder
app.json_encoder = MongoJSONEncoder

# MongoDB Connection
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client.buffer_size_db
users_collection = db.users
courses_collection = db.courses

# Configure app settings
UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Register blueprints
app.register_blueprint(schedule_bp)
app.register_blueprint(file_bp)
app.register_blueprint(review_bp)

# Course routes
@app.route("/courses", methods=["GET"])
def get_courses():
    """Get all courses for the current user
    
    Returns:
        JSON response with courses list
    """
    try:
        # Get user information from headers
        user_id = flask.request.headers.get('x-application-uid')
        
        # If no user ID provided, return empty list
        if not user_id:
            return flask.jsonify({"courses": []}), 200
        
        # Find courses for this user
        user_courses = courses_collection.find({"user_id": user_id})
        
        # Format the response
        courses_list = []
        for course in user_courses:
            courses_list.append({
                "course_id": course["course_id"],
                "course_name": course["course_name"]
            })
        
        return flask.jsonify({"courses": courses_list}), 200
    except Exception as e:
        print(f"Error getting courses: {str(e)}")
        import traceback
        traceback.print_exc()
        return flask.jsonify({"error": f"Failed to get courses: {str(e)}"}), 500

@app.route("/courses", methods=["POST"])
def add_course():
    """Add a new course
    
    Request body should contain:
    - course_id: Course ID
    - course_name: Course name
    
    Returns:
        JSON response with success message
    """
    try:
        data = flask.request.get_json()
        
        # Validate request data
        if not data or not data.get("course_id") or not data.get("course_name"):
            return flask.jsonify({"error": "Course ID and name are required"}), 400
        
        # Get user information from headers
        user_id = flask.request.headers.get('x-application-uid')
        username = flask.request.headers.get('x-application-username')
        
        # If no user ID provided, return error
        if not user_id:
            return flask.jsonify({"error": "Authentication required"}), 401
        
        course_id = data["course_id"]
        course_name = data["course_name"]
        
        # Check if course already exists for this user
        existing_course = courses_collection.find_one({
            "user_id": user_id,
            "course_id": course_id
        })
        
        if existing_course:
            return flask.jsonify({"error": "Course already exists"}), 409
        
        # Create new course
        new_course = {
            "user_id": user_id,
            "username": username,
            "course_id": course_id,
            "course_name": course_name
        }
        
        result = courses_collection.insert_one(new_course)
        
        return flask.jsonify({"message": "Course added successfully"}), 201
    except Exception as e:
        print(f"Error adding course: {str(e)}")
        import traceback
        traceback.print_exc()
        return flask.jsonify({"error": f"Failed to add course: {str(e)}"}), 500

@app.route("/courses/<course_name>", methods=["DELETE"])
def delete_course(course_name):
    """Delete a course by name
    
    Returns:
        JSON response with success message
    """
    try:
        # Get user information from headers
        user_id = flask.request.headers.get('x-application-uid')
        
        # If no user ID provided, return error
        if not user_id:
            return flask.jsonify({"error": "Authentication required"}), 401
        
        # Delete the course
        result = courses_collection.delete_one({
            "user_id": user_id,
            "course_name": course_name
        })
        
        if result.deleted_count == 0:
            return flask.jsonify({"error": "Course not found"}), 404
        
        return flask.jsonify({"message": "Course deleted successfully"}), 200
    except Exception as e:
        print(f"Error deleting course: {str(e)}")
        import traceback
        traceback.print_exc()
        return flask.jsonify({"error": f"Failed to delete course: {str(e)}"}), 500

# Authentication routes
@app.route("/login", methods=["POST"])
def login():
    """Login a user or create a new account if the user doesn't exist
    
    Request body should contain:
    - username: Username for login
    - password: Password for login
    
    Returns:
        JSON response with user information and token
    """
    try:
        data = flask.request.get_json()
        
        if not data or not data.get("username") or not data.get("password"):
            return flask.jsonify({"error": "Username and password are required"}), 400
        
        username = data["username"]
        password = data["password"]
        
        # Check if user exists
        user = users_collection.find_one({"username": username})
        
        if user:
            # Verify password
            if bcrypt.checkpw(password.encode('utf-8'), user["password"]):
                return flask.jsonify({
                    "message": "Login successful",
                    "user": {
                        "id": str(user["_id"]),
                        "username": user["username"]
                    },
                    "token": "dummy-token"
                }), 200
            else:
                return flask.jsonify({"error": "Invalid password"}), 401
        else:
            # Create new user
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            new_user = {
                "username": username,
                "password": hashed_password
            }
            result = users_collection.insert_one(new_user)
            
            return flask.jsonify({
                "message": "User created and logged in",
                "user": {
                    "id": str(result.inserted_id),
                    "username": username
                },
                "token": "dummy-token"
            }), 201
    except Exception as e:
        print(f"Error during login: {str(e)}")
        import traceback
        traceback.print_exc()
        return flask.jsonify({"error": f"Login failed: {str(e)}"}), 500

@app.route("/register", methods=["POST"])
def register():
    """Register a new user
    
    Request body should contain:
    - username: Username for registration
    - password: Password for registration
    
    Returns:
        JSON response with user information and token
    """
    try:
        data = flask.request.get_json()
        
        if not data or not data.get("username") or not data.get("password"):
            return flask.jsonify({"error": "Username and password are required"}), 400
        
        username = data["username"]
        password = data["password"]
        
        # Check if user already exists
        existing_user = users_collection.find_one({"username": username})
        if existing_user:
            return flask.jsonify({"error": "Username already exists"}), 409
        
        # Create new user
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        new_user = {
            "username": username,
            "password": hashed_password
        }
        result = users_collection.insert_one(new_user)
        
        return flask.jsonify({
            "message": "User registered successfully",
            "user": {
                "id": str(result.inserted_id),
                "username": username
            },
            "token": "dummy-token"
        }), 201
    except Exception as e:
        print(f"Error during registration: {str(e)}")
        import traceback
        traceback.print_exc()
        return flask.jsonify({"error": f"Registration failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(port=2817)