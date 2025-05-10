# Frontend Integration Guide

## Overview

This document provides guidance on integrating the KnowLodge Review Service with the frontend application. It includes code examples and best practices for implementing the mock classmate review functionality.

## Required Libraries

Make sure you have the following dependencies in your frontend project:

- Material UI v6.4.7
- Axios (for API requests)
- React Router (for navigation)

## Component Structure

Here's a recommended component structure for implementing the review feature:

```
src/
├── components/
│   ├── review/
│   │   ├── ReviewTopicSelector.jsx
│   │   ├── ReviewSession.jsx
│   │   ├── ReviewChat.jsx
│   │   └── ReviewSummary.jsx
│   └── ...
├── services/
│   ├── reviewService.js
│   └── ...
└── ...
```

## API Service Implementation

Create a service to handle API calls to the review endpoints:

```javascript
// src/services/reviewService.js
import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000';

// Configure axios with default headers
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth headers to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  const userId = localStorage.getItem('userId');
  const username = localStorage.getItem('username');
  
  config.headers['x-application-token'] = token;
  config.headers['x-application-uid'] = userId;
  config.headers['x-application-username'] = username;
  
  return config;
});

const reviewService = {
  // Get available review topics for a course
  getReviewTopics: async (courseId) => {
    try {
      const response = await api.get(`/review/topics?course_id=${courseId}`);
      return response.data.topics;
    } catch (error) {
      console.error('Error fetching review topics:', error);
      throw error;
    }
  },
  
  // Start a new review session
  startReviewSession: async (courseId, topic) => {
    try {
      const response = await api.post('/review/session/start', {
        course_id: courseId,
        topic: topic
      });
      return response.data;
    } catch (error) {
      console.error('Error starting review session:', error);
      throw error;
    }
  },
  
  // Submit an explanation to the review session
  submitExplanation: async (sessionId, explanation) => {
    try {
      const response = await api.post(`/review/session/${sessionId}/explain`, {
        explanation: explanation
      });
      return response.data;
    } catch (error) {
      console.error('Error submitting explanation:', error);
      throw error;
    }
  },
  
  // Get the status of a review session
  getSessionStatus: async (sessionId) => {
    try {
      const response = await api.get(`/review/session/${sessionId}/status`);
      return response.data;
    } catch (error) {
      console.error('Error getting session status:', error);
      throw error;
    }
  },
  
  // End a review session
  endReviewSession: async (sessionId) => {
    try {
      const response = await api.post(`/review/session/${sessionId}/end`);
      return response.data;
    } catch (error) {
      console.error('Error ending review session:', error);
      throw error;
    }
  }
};

export default reviewService;
```

## Component Examples

### Topic Selector Component

```jsx
// src/components/review/ReviewTopicSelector.jsx
import React, { useState, useEffect } from 'react';
import Grid2 from '@mui/material/Grid2';
import { Typography, Card, CardContent, Button, CircularProgress } from '@mui/material';
import reviewService from '../../services/reviewService';

const ReviewTopicSelector = ({ courseId, onTopicSelected }) => {
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchTopics = async () => {
      try {
        setLoading(true);
        const topicsList = await reviewService.getReviewTopics(courseId);
        setTopics(topicsList);
        setError(null);
      } catch (err) {
        setError('Failed to load topics. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchTopics();
  }, [courseId]);

  const handleTopicSelect = (topic) => {
    onTopicSelected(topic);
  };

  if (loading) {
    return (
      <Grid2 container justifyContent="center" alignItems="center" style={{ minHeight: '200px' }}>
        <CircularProgress />
      </Grid2>
    );
  }

  if (error) {
    return (
      <Grid2 container justifyContent="center" alignItems="center">
        <Typography color="error">{error}</Typography>
        <Button variant="contained" onClick={() => window.location.reload()}>Retry</Button>
      </Grid2>
    );
  }

  return (
    <Grid2 container spacing={3}>
      <Grid2 size={{ xs: 12 }}>
        <Typography variant="h5" gutterBottom>Select a Topic to Review</Typography>
      </Grid2>
      
      {topics.map((topic) => (
        <Grid2 size={{ xs: 12, md: 6, lg: 4 }} key={topic}>
          <Card>
            <CardContent>
              <Typography variant="h6">{topic}</Typography>
              <Button 
                variant="contained" 
                color="primary" 
                onClick={() => handleTopicSelect(topic)}
                sx={{ mt: 2 }}
              >
                Start Review
              </Button>
            </CardContent>
          </Card>
        </Grid2>
      ))}
    </Grid2>
  );
};

export default ReviewTopicSelector;
```

### Review Session Component

```jsx
// src/components/review/ReviewSession.jsx
import React, { useState, useEffect } from 'react';
import Grid2 from '@mui/material/Grid2';
import { Typography, Paper, TextField, Button, CircularProgress, Alert } from '@mui/material';
import reviewService from '../../services/reviewService';
import ReviewChat from './ReviewChat';

const ReviewSession = ({ courseId, topic, onSessionEnd }) => {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(null);

  // Start the session when the component mounts
  useEffect(() => {
    const startSession = async () => {
      try {
        setLoading(true);
        const response = await reviewService.startReviewSession(courseId, topic);
        setSessionId(response.session_id);
        
        // Add the initial question to messages
        setMessages([
          {
            sender: 'classmate',
            content: response.initial_question.message,
            timestamp: new Date().toISOString()
          }
        ]);
        
        setError(null);
      } catch (err) {
        setError('Failed to start review session. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    startSession();
    
    // Cleanup function to end the session when component unmounts
    return () => {
      if (sessionId && !sessionEnded) {
        reviewService.endReviewSession(sessionId).catch(console.error);
      }
    };
  }, [courseId, topic]);

  // Poll for session status to update time remaining
  useEffect(() => {
    if (!sessionId || sessionEnded) return;
    
    const statusInterval = setInterval(async () => {
      try {
        const status = await reviewService.getSessionStatus(sessionId);
        setTimeRemaining(Math.floor(status.time_remaining / 60)); // Convert to minutes
        
        if (!status.is_active) {
          setSessionEnded(true);
          clearInterval(statusInterval);
        }
      } catch (err) {
        console.error('Error checking session status:', err);
      }
    }, 30000); // Check every 30 seconds
    
    return () => clearInterval(statusInterval);
  }, [sessionId, sessionEnded]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!userInput.trim() || !sessionId || sessionEnded) return;
    
    const userMessage = {
      sender: 'user',
      content: userInput,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setUserInput('');
    
    try {
      setSubmitting(true);
      const response = await reviewService.submitExplanation(sessionId, userInput);
      
      const classmateMessage = {
        sender: 'classmate',
        content: response.message,
        timestamp: new Date().toISOString(),
        evaluation: response.evaluation
      };
      
      setMessages(prev => [...prev, classmateMessage]);
      
      if (response.session_ended) {
        setSessionEnded(true);
      }
    } catch (err) {
      setError('Failed to submit explanation. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEndSession = async () => {
    if (!sessionId || sessionEnded) return;
    
    try {
      await reviewService.endReviewSession(sessionId);
      setSessionEnded(true);
      if (onSessionEnd) onSessionEnd();
    } catch (err) {
      setError('Failed to end session. Please try again.');
    }
  };

  if (loading) {
    return (
      <Grid2 container justifyContent="center" alignItems="center" style={{ minHeight: '300px' }}>
        <CircularProgress />
      </Grid2>
    );
  }

  return (
    <Grid2 container spacing={3}>
      <Grid2 size={{ xs: 12 }}>
        <Typography variant="h5" gutterBottom>Review Session: {topic}</Typography>
        {timeRemaining !== null && !sessionEnded && (
          <Typography variant="subtitle2" color="text.secondary">
            Session will expire in {timeRemaining} minutes if inactive
          </Typography>
        )}
        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      </Grid2>
      
      <Grid2 size={{ xs: 12 }}>
        <Paper elevation={3} sx={{ p: 2, height: '400px', overflow: 'auto' }}>
          <ReviewChat messages={messages} />
        </Paper>
      </Grid2>
      
      <Grid2 size={{ xs: 12 }}>
        <form onSubmit={handleSubmit}>
          <Grid2 container spacing={2}>
            <Grid2 size={{ xs: 12 }}>
              <TextField
                fullWidth
                multiline
                rows={4}
                variant="outlined"
                placeholder="Type your explanation here..."
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                disabled={submitting || sessionEnded}
              />
            </Grid2>
            <Grid2 size={{ xs: 12 }} container justifyContent="space-between">
              <Button
                variant="outlined"
                color="secondary"
                onClick={handleEndSession}
                disabled={submitting || sessionEnded}
              >
                End Session
              </Button>
              <Button
                type="submit"
                variant="contained"
                color="primary"
                disabled={!userInput.trim() || submitting || sessionEnded}
              >
                {submitting ? <CircularProgress size={24} /> : 'Send Explanation'}
              </Button>
            </Grid2>
          </Grid2>
        </form>
      </Grid2>
      
      {sessionEnded && (
        <Grid2 size={{ xs: 12 }}>
          <Alert severity="info" sx={{ mt: 2 }}>
            This review session has ended. You can start a new session with another topic.
          </Alert>
          <Button 
            variant="contained" 
            color="primary" 
            onClick={onSessionEnd}
            sx={{ mt: 2 }}
          >
            Choose Another Topic
          </Button>
        </Grid2>
      )}
    </Grid2>
  );
};

export default ReviewSession;
```

### Review Chat Component

```jsx
// src/components/review/ReviewChat.jsx
import React from 'react';
import Grid2 from '@mui/material/Grid2';
import { Typography, Box, Chip } from '@mui/material';

const ReviewChat = ({ messages }) => {
  return (
    <Box>
      {messages.map((message, index) => (
        <Box 
          key={index}
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: message.sender === 'user' ? 'flex-end' : 'flex-start',
            mb: 2
          }}
        >
          <Typography variant="caption" color="text.secondary">
            {message.sender === 'user' ? 'You' : 'Classmate'}
          </Typography>
          
          <Box
            sx={{
              bgcolor: message.sender === 'user' ? 'primary.light' : 'grey.100',
              color: message.sender === 'user' ? 'primary.contrastText' : 'text.primary',
              borderRadius: 2,
              p: 2,
              maxWidth: '80%'
            }}
          >
            <Typography variant="body1">{message.content}</Typography>
          </Box>
          
          {message.evaluation && (
            <Chip 
              label={message.evaluation} 
              color={message.evaluation === 'Good' ? 'success' : 'warning'}
              size="small"
              sx={{ mt: 1 }}
            />
          )}
        </Box>
      ))}
    </Box>
  );
};

export default ReviewChat;
```

## Main Review Page

```jsx
// src/pages/ReviewPage.jsx
import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import Grid2 from '@mui/material/Grid2';
import { Container, Typography, Paper } from '@mui/material';
import ReviewTopicSelector from '../components/review/ReviewTopicSelector';
import ReviewSession from '../components/review/ReviewSession';

const ReviewPage = () => {
  const { courseId } = useParams();
  const [selectedTopic, setSelectedTopic] = useState(null);

  const handleTopicSelected = (topic) => {
    setSelectedTopic(topic);
  };

  const handleSessionEnd = () => {
    setSelectedTopic(null);
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Paper elevation={2} sx={{ p: 3 }}>
        <Grid2 container spacing={3}>
          <Grid2 size={{ xs: 12 }}>
            <Typography variant="h4" gutterBottom>Review with a Classmate</Typography>
            <Typography variant="body1" paragraph>
              Practice explaining concepts to a virtual classmate to reinforce your understanding.
            </Typography>
          </Grid2>
          
          {!selectedTopic ? (
            <Grid2 size={{ xs: 12 }}>
              <ReviewTopicSelector 
                courseId={courseId} 
                onTopicSelected={handleTopicSelected} 
              />
            </Grid2>
          ) : (
            <Grid2 size={{ xs: 12 }}>
              <ReviewSession 
                courseId={courseId} 
                topic={selectedTopic} 
                onSessionEnd={handleSessionEnd} 
              />
            </Grid2>
          )}
        </Grid2>
      </Paper>
    </Container>
  );
};

export default ReviewPage;
```

## Response Handling

When working with the review service API, remember to handle the specific response structure:

```javascript
// Extract data from the response
const studyPlanData = response.plan.study_plan;
const reviewData = response.review;
```

## Session Management

The review session has the following lifecycle:

1. User selects a topic to review
2. Session starts with an initial question from the mock classmate
3. User provides explanations (up to 3 times)
4. Session ends when:
   - User manually ends it
   - Maximum explanations (3) are reached
   - 10 minutes of inactivity occurs
   - The agent decides the user has demonstrated sufficient understanding

Make sure to handle all these termination scenarios in your frontend code.
