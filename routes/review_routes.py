import flask
from flask import request, jsonify
import controller.review_service as review_service

# Blueprint for review routes
review_bp = flask.Blueprint('review', __name__)

@review_bp.route("/review/topics", methods=["GET"])
async def get_review_topics():
    """Get available review topics for a course
    
    Query parameters:
        course_id (str): Course ID for specific course data
        
    Returns:
        JSON response with the available review topics
    """
    try:
        # Get user information from headers
        token = request.headers.get('x-application-token')
        user_id = request.headers.get('x-application-uid')
        username = request.headers.get('x-application-username')
        
        # Get query parameters
        course_id = request.args.get('course_id')
        
        if not course_id:
            return jsonify({"error": "Missing course_id parameter"}), 400
        
        print(f"GET /review/topics - username: {username}, course_id: {course_id}")
        
        # Get review topics from the service
        topics = review_service.get_review_topics(username, course_id)
        
        # Log for debugging
        print(f"Returning topics for user: {username}, course: {course_id}")
            
        return jsonify({"topics": topics}), 200
    except Exception as e:
        print(f"Error getting review topics: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to get review topics: {str(e)}"}), 500

@review_bp.route("/review/session/start", methods=["POST"])
async def start_review_session():
    """Start a new review session
    
    Request body should contain:
    - course_id: ID of the course
    - topic: Topic to review
    
    Returns:
        JSON response with session ID and initial question
    """
    try:
        # Get user information from headers
        token = request.headers.get('x-application-token')
        user_id = request.headers.get('x-application-uid')
        username = request.headers.get('x-application-username')
        
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Missing request body"}), 400
            
        course_id = data.get('course_id')
        topic = data.get('topic')
        
        if not course_id or not topic:
            return jsonify({"error": "Missing required parameters: course_id and topic"}), 400
        
        print(f"POST /review/session/start - username: {username}, course_id: {course_id}, topic: {topic}")
        
        # Start a new review session
        session_id = await review_service.start_session(username, course_id, topic)
        
        # Generate the initial question
        question_response = await review_service.generate_initial_question(session_id)
        
        return jsonify({
            "session_id": session_id,
            "topic": topic,
            "initial_question": question_response
        }), 200
    except Exception as e:
        print(f"Error starting review session: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to start review session: {str(e)}"}), 500

@review_bp.route("/review/session/<session_id>/explain", methods=["POST"])
async def submit_explanation(session_id):
    """Submit a user explanation to the review session
    
    Path parameters:
        session_id (str): ID of the active review session
    
    Request body should contain:
    - explanation: User's explanation of the topic
    
    Returns:
        JSON response with feedback and next question
    """
    try:
        # Get user information from headers
        token = request.headers.get('x-application-token')
        user_id = request.headers.get('x-application-uid')
        username = request.headers.get('x-application-username')
        
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Missing request body"}), 400
            
        explanation = data.get('explanation')
        
        if not explanation:
            return jsonify({"error": "Missing required parameter: explanation"}), 400
        
        print(f"POST /review/session/{session_id}/explain - username: {username}")
        
        # Process the user's explanation
        response = await review_service.review_user_explanation(session_id, explanation)
        
        return jsonify(response), 200
    except Exception as e:
        print(f"Error processing explanation: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to process explanation: {str(e)}"}), 500

@review_bp.route("/review/session/<session_id>/status", methods=["GET"])
async def get_session_status(session_id):
    """Get the status of a review session
    
    Path parameters:
        session_id (str): ID of the review session
        
    Returns:
        JSON response with session status information
    """
    try:
        # Get user information from headers
        token = request.headers.get('x-application-token')
        user_id = request.headers.get('x-application-uid')
        username = request.headers.get('x-application-username')
        
        print(f"GET /review/session/{session_id}/status - username: {username}")
        
        # Get session status
        status = await review_service.get_session_status(session_id)
        
        return jsonify(status), 200
    except Exception as e:
        print(f"Error getting session status: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to get session status: {str(e)}"}), 500

@review_bp.route("/review/session/<session_id>/end", methods=["POST"])
async def end_review_session(session_id):
    """End a review session
    
    Path parameters:
        session_id (str): ID of the review session to end
        
    Returns:
        JSON response with result of the operation
    """
    try:
        # Get user information from headers
        token = request.headers.get('x-application-token')
        user_id = request.headers.get('x-application-uid')
        username = request.headers.get('x-application-username')
        
        print(f"POST /review/session/{session_id}/end - username: {username}")
        
        # End the session
        result = await review_service.stop_session(session_id, reason="user_ended")
        
        return jsonify(result), 200
    except Exception as e:
        print(f"Error ending review session: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to end review session: {str(e)}"}), 500

# Add OPTIONS method handlers for CORS preflight requests
@review_bp.route("/review/topics", methods=["OPTIONS"])
@review_bp.route("/review/session/start", methods=["OPTIONS"])
@review_bp.route("/review/session/<session_id>/explain", methods=["OPTIONS"])
@review_bp.route("/review/session/<session_id>/status", methods=["OPTIONS"])
@review_bp.route("/review/session/<session_id>/end", methods=["OPTIONS"])
def handle_options():
    return "", 204
