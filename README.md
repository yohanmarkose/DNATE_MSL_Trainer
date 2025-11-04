# DNATE MSL Practice Gym

An AI-powered training application designed to enhance Medical Science Liaison (MSL) education through realistic physician interactions and intelligent feedback.

## 🎯 Overview

The DNATE MSL Practice Gym helps medical professionals practice communicating with different physician personas (oncologists, cardiologists, neurologists) across various medical scenarios. The system uses OpenAI GPT-4o-mini to provide AI-powered evaluation feedback, dynamic scenario generation, and comprehensive model answers with persona-specific responses.

## ✨ Key Features

### 🎭 **Practice Module**
- Select from 3 distinct physician personas with detailed backgrounds
- Filter questions by difficulty (low/medium/high) and category
- AI-generated realistic scenarios for each question
- Real-time response evaluation with semantic analysis
- Personalized feedback based on physician priorities and communication style

### 📊 **Track Dashboard**
- Gamified progress tracking with levels and XP
- Practice streak monitoring
- Performance analytics with interactive charts
- Category and persona-specific breakdowns
- Achievement badges and milestones
- Practice calendar heatmap

### 📚 **Learn Module**
- Model answers for all questions
- Generic and persona-specific responses
- Strategic reasoning and key talking points
- Difficulty ratings and estimated response times

### 💬 **Sessions History**
- Complete practice session logs
- Review past responses and scores
- Track improvement over time

## 🛠️ Tech Stack

### Frontend
- **Streamlit** - Interactive web interface
- **Plotly** - Data visualizations and charts
- **Requests** - API communication

### Backend
- **FastAPI** - High-performance API framework
- **MongoDB** - Document database for user data and progress
- **OpenAI GPT-4o-mini** - AI evaluation and content generation
- **Python-dotenv** - Environment variable management
- **PyJWT** - Authentication token handling
- **Bcrypt** - Password hashing

### Infrastructure
- **AWS S3** - Cached content storage
- **MongoDB Atlas** - Cloud database (recommended)

## 📋 Prerequisites

- Python 3.12
- MongoDB instance (local or Atlas)
- OpenAI API key
- AWS credentials (for S3 features)

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/dnate-msl-practice-gym.git
cd dnate-msl-practice-gym
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables
Create a `.env` file in the root directory:
```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB_NAME=msl_practice_gym

# JWT Configuration
JWT_SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# AWS S3 (Optional - for cached content)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_S3_BUCKET=your_bucket_name
AWS_REGION=us-east-1
```

### 4. Initialize Database
Load the initial data into MongoDB:
```bash
python scripts/init_database.py
```

This will populate:
- Physician personas from `personas.json` from db
- Question bank from `questions.json` from db
- Category definitions

## 🏃 Running the Application

### Start the Backend (FastAPI)
```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### Start the Frontend (Streamlit)
In a separate terminal:
```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## 📁 Project Structure
```
dnate-msl-practice-gym/
├── app.py                      # Streamlit frontend
├── main.py                     # FastAPI backend
├── components/
│   └── track_dashboard.py     # Dashboard visualization components
│
├── services/
│   ├── database.py            # MongoDB connection and collections
│   ├── auth.py                # Authentication utilities
│   └── models.py              # Pydantic models
│
├── features/
│   ├── model_answer.py        # Model answer generation
│   └── gamification.py        # Progress tracking and achievements
│
├── scripts/
│   └── init_database.py       # Database initialization
│
└── requirements.txt           # Python dependencies
```

## 🔐 Authentication

The application uses JWT-based authentication:

1. **Sign Up**: Create a new account with email and password
2. **Login**: Authenticate and receive access token
3. **Session Management**: Tokens expire after 24 hours
4. **Logout**: Invalidate session tokens

All API endpoints (except login/signup) require authentication via Bearer token.

## 📊 Database Schema

### Collections

- **users** - User accounts and authentication
- **personas** - Physician persona definitions
- **questions** - Question bank with metadata
- **categories** - Question category definitions
- **sessions** - Practice session tracking with interactions
- **user_progress** - Aggregated user statistics and achievements

See `schema.sql` for detailed schema documentation.

## 🎮 Gamification Features

- **Levels & XP**: Progress through levels based on practice sessions
- **Streaks**: Daily practice streak tracking
- **Achievements**: Unlock milestones for various accomplishments
- **Goals**: Daily and weekly session targets
- **Analytics**: Performance trends and insights

## 🔧 Configuration

### API Base URL
Update in `app.py`:
```python
API_BASE_URL = "http://localhost:8000"
```

### MongoDB Connection
Configure in `.env` or `services/database.py`:
```python
MONGODB_URI = "mongodb://localhost:27017/"
MONGODB_DB_NAME = "msl_practice_gym"
```

### OpenAI Model Settings
Adjust in `main.py`:
```python
model="gpt-4o-mini"
temperature=0.3
max_tokens=200
```

## 🧪 Testing

### Backend API Tests
```bash
pytest tests/
```

### Manual Testing
Access API documentation at:
```
http://localhost:8000/docs
```

## 📈 Performance Optimization

The application implements caching strategies:

1. **Model Answers**: Pre-generated and cached in JSON/S3
2. **Scenarios**: Cached per question-persona combination
3. **Progress Data**: Aggregated in MongoDB for fast retrieval

## 🐛 Troubleshooting

### MongoDB Connection Issues
- Ensure MongoDB is running: `sudo systemctl status mongod`
- Check connection string in `.env`
- Verify network access for MongoDB Atlas

### OpenAI API Errors
- Verify API key is valid
- Check rate limits and quotas
- Ensure proper error handling in code

### Authentication Problems
- Clear browser cookies/localStorage
- Check JWT secret key configuration
- Verify token expiration settings
