# Review Service API Documentation

This document describes the API endpoints for the KnowLodge Review Service, which implements a mock classmate functionality for interactive learning.

## Base URL

All API endpoints are relative to the base URL of your server, typically:

```
http://localhost:5000
```

## Authentication

All requests require the following headers for authentication:

```
x-application-token: <token>
x-application-uid: <user_id>
x-application-username: <username>
```

## Endpoints

### 1. Get Review Topics

Retrieve available topics for review in a specific course.

- **URL**: `/review/topics`
- **Method**: `GET`
- **Query Parameters**:
  - `course_id` (required): The ID of the course

#### Success Response

- **Code**: 200 OK
- **Content Example**:

```json
{
  "topics": ["Time in Distributed Systems", "Consensus Algorithms", "CAP Theorem"]
}
```

#### Error Response

- **Code**: 400 Bad Request
  - **Content**: `{"error": "Missing course_id parameter"}`

- **Code**: 404 Not Found
  - **Content**: `{"message": "No topics found for this course"}`

- **Code**: 500 Internal Server Error
  - **Content**: `{"error": "Failed to get review topics: <error_message>"}`

### 2. Start Review Session

Start a new review session with a mock classmate for a specific topic.

- **URL**: `/review/session/start`
- **Method**: `POST`
- **Request Body**:

```json
{
  "course_id": "cs101",
  "topic": "Time in Distributed Systems"
}
```

#### Success Response

- **Code**: 200 OK
- **Content Example**:

```json
{
  "session_id": "username_cs101_Time in Distributed Systems_2025-04-14_13-15-35",
  "topic": "Time in Distributed Systems",
  "initial_question": {
    "status": "success",
    "question": "Can you explain how time synchronization works in distributed systems?",
    "message": "I'm having trouble understanding Time in Distributed Systems. Can you explain how time synchronization works in distributed systems?"
  }
}
```

#### Error Response

- **Code**: 400 Bad Request
  - **Content**: `{"error": "Missing required parameters: course_id and topic"}`

- **Code**: 500 Internal Server Error
  - **Content**: `{"error": "Failed to start review session: <error_message>"}`

### 3. Submit Explanation

Submit a user explanation to the mock classmate and receive feedback.

- **URL**: `/review/session/{session_id}/explain`
- **Method**: `POST`
- **URL Parameters**:
  - `session_id` (required): The ID of the active review session
- **Request Body**:

```json
{
  "explanation": "Time in distributed systems is challenging because different computers may have different clock times. Physical clocks can drift, so we use logical clocks like Lamport clocks to establish event ordering."
}
```

#### Success Response

- **Code**: 200 OK
- **Content Example** (Continuing Conversation):

```json
{
  "status": "success",
  "message": "That's a good start! Could you tell me more about vector clocks and how they differ from Lamport clocks in distributed systems?",
  "evaluation": "Needs Improvement",
  "session_ended": false
}
```

- **Content Example** (Session Ended):

```json
{
  "status": "success",
  "message": "Thank you for your detailed explanation! You've covered the key aspects of time synchronization in distributed systems very well.",
  "evaluation": "Good",
  "session_ended": true,
  "reason": "Maximum number of explanations reached"
}
```

#### Error Response

- **Code**: 400 Bad Request
  - **Content**: `{"error": "Missing required parameter: explanation"}`

- **Code**: 500 Internal Server Error
  - **Content**: `{"error": "Failed to process explanation: <error_message>"}`

### 4. Get Session Status

Check the status of an active review session.

- **URL**: `/review/session/{session_id}/status`
- **Method**: `GET`
- **URL Parameters**:
  - `session_id` (required): The ID of the review session

#### Success Response

- **Code**: 200 OK
- **Content Example**:

```json
{
  "status": "success",
  "is_active": true,
  "explanation_count": 2,
  "topic": "Time in Distributed Systems",
  "last_activity": "2025-04-14T13:20:35.123456",
  "time_remaining": 450.5
}
```

#### Error Response

- **Code**: 500 Internal Server Error
  - **Content**: `{"error": "Failed to get session status: <error_message>"}`

### 5. End Review Session

Manually end an active review session.

- **URL**: `/review/session/{session_id}/end`
- **Method**: `POST`
- **URL Parameters**:
  - `session_id` (required): The ID of the review session to end

#### Success Response

- **Code**: 200 OK
- **Content Example**:

```json
{
  "status": "success",
  "message": "Session terminated: user_ended"
}
```

#### Error Response

- **Code**: 500 Internal Server Error
  - **Content**: `{"error": "Failed to end review session: <error_message>"}`

## Session Termination

A review session can be terminated in the following ways:

1. **User manually ends the session** - By calling the end session endpoint
2. **Maximum explanations reached** - After the user provides 3 explanations
3. **Timeout** - After 10 minutes of inactivity
4. **Agent ends the conversation** - When the agent determines the user has demonstrated sufficient understanding

## Frontend Integration

When integrating with the KnowLodgeClient frontend, remember to follow the Material UI v6.4.7 patterns with Grid2 component:

```jsx
import Grid2 from '@mui/material/Grid2';

// For container
<Grid2 container spacing={3}>
  {/* Grid items */}
  <Grid2 size={{ xs: 12, md: 6 }} key={id}>
    {/* Content */}
  </Grid2>
</Grid2>
```

The frontend should handle the response structure as follows:

```javascript
// Extract study plan data from response
const studyPlanData = response.plan.study_plan;

// Extract review data from response
const reviewData = response.review;
```
