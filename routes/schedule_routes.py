import flask
from flask import request, jsonify
import asyncio
import json
from controller.schedule_service import run_schedule_analysis, get_user_courses, add_user_course, delete_user_course

# Blueprint for schedule routes
schedule_bp = flask.Blueprint('schedule', __name__)

@schedule_bp.route("/schedule", methods=["GET"])
async def get_schedule():
    """Get the study schedule for a course
    
    Query parameters:
        make_schedule (bool): Whether to generate Google Calendar events
        force_refresh (bool): Force regeneration of analysis
        course_id (str): Course ID for specific course data
        
    Returns:
        JSON response with the generated schedule
    """
    try:
        # Get user information from headers
        token = request.headers.get('x-application-token')
        user_id = request.headers.get('x-application-uid')
        username = request.headers.get('x-application-username')
        
        # Get query parameters
        make_schedule = request.args.get('make_schedule', 'false').lower() == 'true'
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        course_id = request.args.get('course_id')
        
        print(f"GET /schedule - username: {username}, course_id: {course_id}, make_schedule: {make_schedule}, force_refresh: {force_refresh}")
        
        # Run schedule analysis
        schedule_data = await run_schedule_analysis(
            make_schedule=make_schedule,
            username=username,
            force_refresh=force_refresh,
            course_id=course_id
        )
        
        # Try to parse schedule_data as JSON
        try:
            schedule_json = json.loads(schedule_data)
            return jsonify(schedule_json), 200
        except json.JSONDecodeError:
            return jsonify({"schedule": schedule_data}), 200
    except Exception as e:
        print(f"Error generating schedule: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate schedule: {str(e)}"}), 500

@schedule_bp.route("/courses", methods=["GET"])
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
        
        print(f"GET /courses - username: {username}")
        
        # Check for required parameters
        if not username:
            return jsonify({"error": "Username is required"}), 400
        
        # Get courses for the user
        user_courses = get_user_courses(username)
        
        return jsonify({"courses": user_courses}), 200
    except Exception as e:
        print(f"Error getting courses: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to get courses: {str(e)}"}), 500

@schedule_bp.route("/courses", methods=["POST"])
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
        
        # Get request data
        data = request.get_json()
        
        print(f"POST /courses - username: {username}, data: {data}")
        
        # Check for required parameters
        if not username:
            return jsonify({"error": "Username is required"}), 400
        
        if not data or not data.get("course_id") or not data.get("course_name"):
            return jsonify({"error": "Course ID and course name are required"}), 400
        
        # Add course for the user
        result = add_user_course(username, data["course_id"], data["course_name"])
        
        if result.get("success"):
            return jsonify({"message": result.get("message")}), 200
        else:
            return jsonify({"error": result.get("error")}), 400
    except Exception as e:
        print(f"Error adding course: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to add course: {str(e)}"}), 500

@schedule_bp.route("/courses/<course_name>", methods=["DELETE"])
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
        
        print(f"DELETE /courses/{course_name} - username: {username}")
        
        # Check for required parameters
        if not username:
            return jsonify({"error": "Username is required"}), 400
        
        # Delete course for the user
        result = delete_user_course(username, course_name)
        
        if result.get("success"):
            return jsonify({"message": result.get("message")}), 200
        else:
            return jsonify({"error": result.get("error")}), 400
    except Exception as e:
        print(f"Error deleting course: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to delete course: {str(e)}"}), 500

# Add OPTIONS method handler for CORS preflight requests
@schedule_bp.route("/courses", methods=["OPTIONS"])
@schedule_bp.route("/courses/<course_name>", methods=["OPTIONS"])
@schedule_bp.route("/schedule", methods=["OPTIONS"])
def handle_options(course_name=None):
    return "", 204
