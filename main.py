import os
import flask
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import bcrypt

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