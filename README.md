# KnowLodge Server

![KnowLodge Logo](https://via.placeholder.com/200x100?text=KnowLodge)

## Overview

KnowLodge Server is the backend component of the KnowLodge platform, an intelligent study assistant designed to help students organize their coursework, create personalized study plans, and improve their academic performance. The server handles data processing, AI-powered analysis, and provides RESTful API endpoints for the client application.

## Key Features

- **User Authentication**: Secure login and registration system
- **Course Management**: Store and retrieve course information
- **Study Plan Generation**: AI-powered analysis of course materials to create optimized study schedules
- **AI Review System**: Process and analyze user explanations of topics
- **Assignment Feedback**: Provide AI-powered feedback on assignments
- **MongoDB Integration**: Persistent storage of user data and course materials

## Technical Stack

- **Language**: Python 3.8+
- **Framework**: Flask
- **Database**: MongoDB (PyMongo)
- **AI Integration**: OpenAI, DeepSeek, and Moonshot APIs
- **Authentication**: Custom token-based authentication
- **CORS Handling**: Flask-CORS

## Project Structure

```
KnowLodgeServer/
├── agent/            # AI agent implementations
├── boundary/         # External service integrations
├── controller/       # Business logic
│   └── review_service.py  # Review functionality
├── models/           # Data models
├── routes/           # API route handlers
│   └── review_routes.py   # Review endpoints
├── util/             # Utility functions
├── main.py           # Application entry point
└── requirements.txt  # Dependencies
```

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration

### Courses
- `GET /courses` - Get all courses for a user
- `POST /courses` - Create a new course
- `GET /courses/{id}` - Get course details
- `PUT /courses/{id}` - Update course
- `DELETE /courses/{id}` - Delete course

### Study Plans
- `POST /plan/generate` - Generate study plan from course materials
- `GET /plan/{id}` - Get study plan details

### Review
- `GET /review/topics` - Get available review topics
- `POST /review/session/start` - Start a review session
- `POST /review/session/{id}/explain` - Submit explanation and get feedback
- `GET /review/session/{id}/status` - Get session status
- `POST /review/session/{id}/end` - End review session

## Installation and Setup

### Prerequisites
- Python 3.8+
- MongoDB (local instance or Atlas connection)
- API keys for LLM services (OpenAI, DeepSeek, Moonshot)

### Setup Instructions

```bash
# Clone the repository
git clone https://github.com/yourusername/KnowlodgePacket.git
cd KnowlodgePacket/KnowLodgeServer

# Create and activate a virtual environment
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
# Create a .env file with the following variables:
# MONGO_URI=your_mongodb_connection_string
# OPENAI_API_KEY=your_openai_api_key
# DEEPSEEK_API_KEY=your_deepseek_api_key
# MOONSHOT_API_KEY=your_moonshot_api_key

# Start the server
python main.py
```

## Required LLM API Keys

You MUST provide API keys for the LLMs used by the system:
- **OPENAI_API_KEY**: For OpenAI models
- **DEEPSEEK_API_KEY**: For DeepSeek models
- **MOONSHOT_API_KEY**: For Moonshot models

Without these API keys, the AI features will not function properly. However, technically all LLM providers with OpenAI completion API compatibility should work.

## Data Flow

1. **Course Creation**: User creates a course and uploads materials
2. **Material Analysis**: Server analyzes uploaded PDFs to extract key information
3. **Plan Generation**: AI generates optimized study plans based on extracted data
4. **Review Process**: User selects topics to review and explains them to the AI
5. **Feedback Generation**: AI evaluates explanations and provides feedback

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[MIT License](../LICENSE)
