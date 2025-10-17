from fastapi import FastAPI, HTTPException, Depends, Header, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime
import uuid
from bson import ObjectId
from dotenv import load_dotenv
import os
from copy import deepcopy
from openai import OpenAI
from services.database import (
    users_collection, 
    sessions_collection,
    personas_collections,
    questions_collections,
    category_collections,
    user_progress_collections
)
from services.models import UserSignup, UserLogin, TokenResponse
from services.auth import hash_password, verify_password, create_access_token, decode_access_token, generate_session_id
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


from features.model_answer import (
    load_model_answers,
    get_answer_key
)

from features.gamification import (
    calculate_level,
    xp_progress_to_next_level,
    calculate_streak,
    check_and_award_milestones,
    get_all_milestones_with_status,
    get_sessions_today,
    get_sessions_this_week,
    calculate_improvement_rate,
    calculate_goal_progress,
    MILESTONES
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load JSON files
# with open('questions.json', 'r') as f:
#     questions_data = json.load(f)

# with open('personas.json', 'r') as f:
#     personas_data = json.load(f)

# In-memory storage (replace with database in production)
sessions_store = {}

user_progress = {
    "total_sessions": 0,
    "category_stats": {},
    "persona_stats": {},
    "average_score": 0.0,
    "scores_history": [],
    "score_timestamps": [],  # NEW
    
    # Gamification fields
    "total_practice_time_minutes": 0,
    "current_streak_days": 0,
    "longest_streak_days": 0,
    "last_practice_date": None,
    "practice_dates": [],
    
    # Achievements
    "milestones_achieved": [],
    "level": 1,
    "experience_points": 0,
    "badges": [],
    
    # Goals
    "daily_goal": 3,
    "weekly_goal": 15,
}

class SessionRequest(BaseModel):
    question_id: int
    persona_id: str
    user_response: str

class EvaluationResponse(BaseModel):
    score: float
    feedback: str
    priorities_covered: List[str]
    engagement_points_covered: List[str]
    missing_points: List[str]


def convert_objectid(obj):
    """
    Recursively converts ObjectId in dict or list to string
    """
    if isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    elif isinstance(obj, ObjectId):
        return str(obj)
    else:
        return obj
    
# Function to convert list of objs to dict
def format_category(category):
    merged_dict = {k: v for d in category for k, v in d.items()}
    return merged_dict

# ------------------------------------------------
# SIGNUP ENDPOINT
# ------------------------------------------------
@app.post("/signup", response_model=TokenResponse)
async def signup(user: UserSignup):
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_pw = hash_password(user.password)
    new_user = {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "password_hash": hashed_pw,
        "created_at": datetime.utcnow(),
        "last_login": None,
        
    }
    result = await users_collection.insert_one(new_user)
    user_id = str(result.inserted_id)

    progress_doc = deepcopy(user_progress)
    progress_doc.update({
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    await user_progress_collections.insert_one(progress_doc)

    # Create session
    session_id = generate_session_id()
    await sessions_collection.insert_one({
        "user_id": user_id,
        "session_id": session_id,
        "login_time": datetime.utcnow(),
        "active": True
    })

    token = create_access_token({"user_id": user_id, "session_id": session_id})
    return {"access_token": token}

# ------------------------------------------------
# LOGIN ENDPOINT
# ------------------------------------------------
@app.post("/login", response_model=TokenResponse)
async def login(user: UserLogin):
    existing_user = await users_collection.find_one({"email": user.email})
    if not existing_user or not verify_password(user.password, existing_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session_id = generate_session_id()
    await sessions_collection.insert_one({
        "user_id": str(existing_user["_id"]),
        "session_id": session_id,
        "login_time": datetime.utcnow(),
        "active": True
    })

    await users_collection.update_one(
        {"_id": existing_user["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )

    token = create_access_token({"user_id": str(existing_user["_id"]), "session_id": session_id})
    return {"access_token": token}

# ------------------------------------------------
# LOGOUT ENDPOINT
# ------------------------------------------------
@app.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Security(security),
):
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    session_id = payload.get("session_id")
    print(f"session id : {session_id}")

    if session_id:
        await sessions_collection.update_one(
            {"session_id": session_id},
            {"$set": {"active": False, "logout_time": datetime.utcnow()}}
        )

    return {"message": "Logged out successfully"}

@app.get("/personas")
async def get_personas():
    personas = await personas_collections.find({}).to_list(length=None)
    personas = convert_objectid(personas)
    return personas

@app.get("/personas/{persona_id}")
async def get_persona(persona_id: str):
    personas = await personas_collections.find({}).to_list(length=None)
    personas = convert_objectid(personas)
    persona = next((p for p in personas if p["id"] == persona_id), None)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona

@app.get("/questions")
async def get_questions(
    persona_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    category: Optional[str] = None
):
    # questions = questions_data["questions"]
    questions = await questions_collections.find({}).to_list(length=None)
    questions = convert_objectid(questions)

    if persona_id:
        questions = [q for q in questions if persona_id in q.get("persona", [])]
    
    if difficulty:
        questions = [q for q in questions if q.get("difficulty") == difficulty]
    
    if category:
        questions = [q for q in questions if q.get("category") == category]
    return questions

@app.get("/categories")
async def get_categories(persona_id: Optional[str] = None):
    """Get categories, optionally filtered by persona"""
    questions = await questions_collections.find({}).to_list(length=None)
    questions = convert_objectid(questions)

    category = await category_collections.find({}).to_list(length=None)
    category = convert_objectid(category)
    
    if not persona_id:
        return category
    
    persona_questions = [
        q for q in questions 
        if persona_id in q.get("persona", [])
    ]

    available_categories = set(q["category"] for q in persona_questions)
    
    # Filter the categories dict to only include available ones
    category = format_category(category)
    filtered_categories = {
        cat_name: cat_info 
        for cat_name, cat_info in category.items()
        if cat_name in available_categories
    }
    
    for cat_name in filtered_categories:
        count = sum(1 for q in persona_questions if q["category"] == cat_name)
        filtered_categories[cat_name]["question_count"] = count
    
    return filtered_categories

@app.get("/scenario/{question_id}/{persona_id}")
async def get_scenario(question_id: int, persona_id: str):
    questions = await questions_collections.find({}).to_list(length=None)
    questions = convert_objectid(questions)

    personas = await personas_collections.find({}).to_list(length=None)
    personas = convert_objectid(personas)

    question = next((q for q in questions if q["id"] == question_id), None)
    persona = next((p for p in personas if p["id"] == persona_id), None)
    
    if not question or not persona:
        raise HTTPException(status_code=404, detail="Question or Persona not found")
    
    scenario_prompt = f"""Create a realistic, engaging scenario for an MSL practice session.

Physician Persona:
- {persona['name']}, {persona['title']}
- {persona['specialty']} at {persona['practice_setting']['type']}
- Communication Style: {persona['communication_style']['tone']}
- Common Challenges: {', '.join(persona['common_challenges'][:2])}

Question Context: {question['context']}
Question Category: {question['category']}

Create a brief (3-4 sentence) scenario that sets up WHY this physician is asking this question. Include:
- The specific situation or patient case prompting the question
- The physician's mindset/concern
- Any relevant practice context

Make it realistic and immersive."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are creating realistic medical scenarios for MSL training."},
                {"role": "user", "content": scenario_prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        return {
            "question_id": question_id,
            "persona_id": persona_id,
            "scenario": response.choices[0].message.content,
            "question": question['question']
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scenario generation failed: {str(e)}")

@app.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_response(session: SessionRequest, credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload["user_id"]
    session_id = payload["session_id"]

    print(f"payload: {payload}")

    questions = await questions_collections.find({}).to_list(length=None)
    questions = convert_objectid(questions)

    personas = await personas_collections.find({}).to_list(length=None)
    personas = convert_objectid(personas)

    question = next((q for q in questions if q["id"] == session.question_id), None)
    persona = next((p for p in personas if p["id"] == session.persona_id), None)
    
    if not question or not persona:
        raise HTTPException(status_code=404, detail="Question or Persona not found")
    
    # Use OpenAI for evaluation
    evaluation_prompt = f"""You are evaluating an MSL's response to a physician question. 

Physician Persona:
- Name: {persona['name']}
- Specialty: {persona['specialty']}
- Practice Setting: {persona['practice_setting']['type']}
- Key Priorities: {', '.join(persona['priorities'][:3])}
- Communication Style: {persona['communication_style']['tone']}
- Engagement Tips: {', '.join(persona['engagement_tips'])}

Question Asked: {question['question']}
Category: {question['category']}
Key Themes to Address: {', '.join(question.get('key_themes', []))}

MSL's Response:
{session.user_response}

Evaluate this response on a 0-100 scale using these criteria:
1. Addressing Physician Priorities (40 points): How well does the response align with this persona's priorities?
2. Engagement Techniques (30 points): Does it use appropriate communication style and engagement approaches for this persona?
3. Key Themes Coverage (20 points): Does it cover the key themes for this question?
4. Professionalism (10 points): Tone, clarity, and structure.

Respond in this JSON format:
{{
  "score": <number 0-100>,
  "feedback": "<2-3 sentence overall feedback>",
  "priorities_covered": ["<priority 1>", "<priority 2>"],
  "engagement_points_covered": ["<engagement point 1>", "<engagement point 2>"],
  "missing_points": ["<what could be improved 1>", "<what could be improved 2>"],
  "detailed_breakdown": {{
    "priorities_score": <0-40>,
    "engagement_score": <0-30>,
    "themes_score": <0-20>,
    "professionalism_score": <0-10>
  }}
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert MSL trainer evaluating responses. Provide structured, actionable feedback."},
                {"role": "user", "content": evaluation_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Store session
        # session_id = str(uuid.uuid4())
        # sessions_store[session_id] = {
        #     "id": session_id,
        #     "question_id": session.question_id,
        #     "persona_id": session.persona_id,
        #     "user_response": session.user_response,
        #     "score": result["score"],
        #     "timestamp": datetime.now().isoformat(),
        #     "category": question["category"]
        # }

        interaction = {
            "question_id": session.question_id,
            "persona_id": session.persona_id,
            "user_response": session.user_response,
            "score": result["score"],
            "timestamp": datetime.utcnow().isoformat(),
            "category": question["category"]
        }

        update_response = await sessions_collection.update_one(
            {"session_id": session_id},          # Find the correct session
            {"$push": {"interactions": interaction}}  # Append interaction
        )

        if update_response.matched_count == 0:
            # Optional: handle session not found
            raise Exception(f"Session {session_id} not found.")

        
        # Update progress
        await update_progress(user_id, question["category"], session.persona_id, result["score"])

        # update user_progress in db
        
        return EvaluationResponse(
            score=result["score"],
            feedback=result["feedback"],
            priorities_covered=result.get("priorities_covered", []),
            engagement_points_covered=result.get("engagement_points_covered", []),
            missing_points=result.get("missing_points", [])
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@app.get("/model-answers")
def get_model_answers(
    persona_id: Optional[str] = None,
    category: Optional[str] = None
):
    """
    Get all model answers with optional filtering.
    Returns list of answers that can be filtered by persona and/or category.
    """
    model_answers_data = load_model_answers()

    all_answers = list(model_answers_data.get("answers", {}).values())
    
    # Filter by persona_id if provided
    if persona_id:
        # Get both persona-specific and generic answers for this persona
        all_answers = [a for a in all_answers if a.get("persona_id") == persona_id or a.get("persona_id") is None]
    
    # Filter by category if provided
    if category:
        all_answers = [a for a in all_answers if a.get("category") == category]
    
    return {
        "total": len(all_answers),
        "answers": all_answers
    }

@app.get("/progress")
async def get_progress(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload["user_id"]

    user_progress_data = await user_progress_collections.find_one({"user_id": user_id})
    if not user_progress_data:
        raise HTTPException(status_code=404, detail="User progress not found")
    print(user_progress_data)
    user_progress_data = convert_objectid(user_progress_data)
    return user_progress_data

# Work in progress
@app.get("/sessions")
async def get_sessions(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload["user_id"]
    user_sessions = await sessions_collection.find({"user_id": user_id}).to_list(length=None)
    if not user_sessions:
        return {"message": "No sessions found for this user."}

    user_sessions = convert_objectid(user_sessions)
    # return list(sessions_store.values())
    return user_sessions


@app.get("/progress/detailed")
async def get_detailed_progress(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get comprehensive progress data for Track dashboard"""
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload["user_id"]
    user_sessions = await sessions_collection.find({"user_id": user_id}).to_list(length=None)
    if not user_sessions:
        return {"message": "No sessions found for this user."}

    user_sessions = convert_objectid(user_sessions)
    # sessions_list = list(sessions_store.values())
    user_progress_data = await user_progress_collections.find_one({"user_id": user_id})
    if not user_progress_data:
        raise HTTPException(status_code=404, detail="User progress not found")
    user_progress_data = convert_objectid(user_progress_data)

    xp_info = xp_progress_to_next_level(user_progress_data["experience_points"])
    
    improvement = calculate_improvement_rate(user_progress_data["scores_history"])
    
    daily_progress = calculate_goal_progress(
        get_sessions_today(user_sessions),
        user_progress_data["daily_goal"]
    )
    
    weekly_progress = calculate_goal_progress(
        get_sessions_this_week(user_sessions),
        user_progress_data["weekly_goal"]
    )
    
    return {
        **user_progress_data,
        **xp_info,
        "sessions_today": daily_progress["current"],
        "sessions_this_week": weekly_progress["current"],
        "improvement_rate": improvement,
        "daily_goal_progress": daily_progress,
        "weekly_goal_progress": weekly_progress
    }


@app.get("/progress/milestones")
async def get_milestones(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get all milestones with achievement status"""
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload["user_id"]

    user_progress_data = await user_progress_collections.find_one({"user_id": user_id})
    if not user_progress_data:
        raise HTTPException(status_code=404, detail="User progress not found")

    user_progress_data = convert_objectid(user_progress_data)
    milestones_list = get_all_milestones_with_status(user_progress_data["milestones_achieved"])

    return {
        "milestones": milestones_list,
        "total_achieved": len(user_progress_data["milestones_achieved"]),
        "total_available": len(MILESTONES)
    }


@app.get("/progress/timeline")
async def get_progress_timeline(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get score history for charts"""
    timeline = []

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload["user_id"]

    user_progress_data = await user_progress_collections.find_one({"user_id": user_id})
    if not user_progress_data:
        raise HTTPException(status_code=404, detail="User progress not found")

    user_progress_data = convert_objectid(user_progress_data)
    
    for i, (score, timestamp) in enumerate(zip(user_progress_data["scores_history"], user_progress_data["score_timestamps"])):
        timeline.append({
            "session_number": i + 1,
            "score": score,
            "timestamp": timestamp,
            "date": datetime.fromisoformat(timestamp).strftime("%Y-%m-%d")
        })
    
    return timeline


@app.get("/progress/heatmap")
async def get_practice_heatmap(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get practice frequency data for heatmap"""
    date_counts = {}

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload["user_id"]

    user_progress_data = await user_progress_collections.find_one({"user_id": user_id})
    if not user_progress_data:
        raise HTTPException(status_code=404, detail="User progress not found")

    user_progress_data = convert_objectid(user_progress_data)
    
    for date_str in user_progress_data["practice_dates"]:
        date_counts[date_str] = date_counts.get(date_str, 0) + 1
    
    heatmap_data = [
        {"date": date, "count": count}
        for date, count in date_counts.items()
    ]
    
    return heatmap_data

# def update_progress(category: str, persona_id: str, score: float, response_time_seconds: int = 90):
#     """Enhanced progress update with gamification"""
#     user_progress["total_sessions"] += 1
    
#     # Update category stats
#     if category not in user_progress["category_stats"]:
#         user_progress["category_stats"][category] = {"count": 0, "avg_score": 0, "total_score": 0}
    
#     cat_stats = user_progress["category_stats"][category]
#     cat_stats["count"] += 1
#     cat_stats["total_score"] += score
#     cat_stats["avg_score"] = cat_stats["total_score"] / cat_stats["count"]
    
#     # Update persona stats
#     if persona_id not in user_progress["persona_stats"]:
#         user_progress["persona_stats"][persona_id] = {"count": 0, "avg_score": 0, "total_score": 0}
    
#     pers_stats = user_progress["persona_stats"][persona_id]
#     pers_stats["count"] += 1
#     pers_stats["total_score"] += score
#     pers_stats["avg_score"] = pers_stats["total_score"] / pers_stats["count"]
    
#     # Update overall average
#     user_progress["scores_history"].append(score)
#     user_progress["score_timestamps"].append(datetime.now().isoformat())
#     user_progress["average_score"] = sum(user_progress["scores_history"]) / len(user_progress["scores_history"])
    
#     # NEW: Track practice dates
#     today = datetime.now().date().isoformat()
#     if today not in user_progress["practice_dates"]:
#         user_progress["practice_dates"].append(today)
    
#     # NEW: Update practice time
#     user_progress["total_practice_time_minutes"] += response_time_seconds / 60
    
#     # NEW: Calculate streaks
#     current_streak, longest_streak = calculate_streak(user_progress["practice_dates"])
#     user_progress["current_streak_days"] = current_streak
#     user_progress["longest_streak_days"] = max(longest_streak, user_progress["longest_streak_days"])
#     user_progress["last_practice_date"] = datetime.now().isoformat()
    
#     # NEW: Check and award milestones
#     newly_achieved = check_and_award_milestones(user_progress)
    
#     return newly_achieved

async def update_progress(user_id: str, category: str, persona_id: str, score: float, response_time_seconds: int = 90):
    """Update user progress in MongoDB with gamification features."""
    
    # Fetch user progress from DB
    user_progress_data = await user_progress_collections.find_one({"user_id": user_id})

    if not user_progress_data:
        raise HTTPException(status_code=404, detail="User progress not found")

    # Make a modifiable copy
    user_progress_data = deepcopy(user_progress_data)

    # Update total sessions
    user_progress_data["total_sessions"] = user_progress_data.get("total_sessions", 0) + 1

    # Update category stats
    category_stats = user_progress_data.get("category_stats", {})
    if category not in category_stats:
        category_stats[category] = {"count": 0, "avg_score": 0, "total_score": 0}
    cat_stats = category_stats[category]
    cat_stats["count"] += 1
    cat_stats["total_score"] += score
    cat_stats["avg_score"] = cat_stats["total_score"] / cat_stats["count"]
    user_progress_data["category_stats"] = category_stats

    # Update persona stats
    persona_stats = user_progress_data.get("persona_stats", {})
    if persona_id not in persona_stats:
        persona_stats[persona_id] = {"count": 0, "avg_score": 0, "total_score": 0}
    pers_stats = persona_stats[persona_id]
    pers_stats["count"] += 1
    pers_stats["total_score"] += score
    pers_stats["avg_score"] = pers_stats["total_score"] / pers_stats["count"]
    user_progress_data["persona_stats"] = persona_stats

    # Update score history and average
    user_progress_data.setdefault("scores_history", []).append(score)
    user_progress_data.setdefault("score_timestamps", []).append(datetime.utcnow().isoformat())
    user_progress_data["average_score"] = sum(user_progress_data["scores_history"]) / len(user_progress_data["scores_history"])

    # Update practice dates and total time
    today = datetime.utcnow().date().isoformat()
    practice_dates = set(user_progress_data.get("practice_dates", []))
    practice_dates.add(today)
    user_progress_data["practice_dates"] = list(practice_dates)
    user_progress_data["total_practice_time_minutes"] = user_progress_data.get("total_practice_time_minutes", 0) + (response_time_seconds / 60)

    # Calculate streaks
    current_streak, longest_streak = calculate_streak(user_progress_data["practice_dates"])
    user_progress_data["current_streak_days"] = current_streak
    user_progress_data["longest_streak_days"] = max(longest_streak, user_progress_data.get("longest_streak_days", 0))
    user_progress_data["last_practice_date"] = datetime.utcnow().isoformat()

    # Award milestones and achievements
    newly_achieved = check_and_award_milestones(user_progress_data)
    if newly_achieved:
        user_progress_data["milestones_achieved"].extend(newly_achieved)

    # Update last modified timestamp
    user_progress_data["updated_at"] = datetime.utcnow()

    print(f"user prgress : {user_progress_data}")

    # Save back to DB
    await user_progress_collections.update_one(
        {"user_id": user_id},
        {"$set": user_progress_data},
        upsert=True
    )

    return newly_achieved


def generate_model_answer(question):
    # Template for model answers based on category
    templates = {
        "Cost & Value": "I understand the cost concern. Let me address the value proposition by highlighting...",
        "Clinical Data & Evidence": "That's an excellent question about the data. Let me walk you through...",
        "Patient Acceptance & Treatment Burden": "Patient experience is crucial. Here's what we're seeing...",
        "Clinical Decision-Making & Time Constraints": "I appreciate your time constraints. Let me provide the key information...",
        "Data Validity & Study Design": "Let me explain the study methodology...",
        "Treatment Practicality": "That's a practical consideration. Here's how it works...",
        "Skepticism & Pushback": "I appreciate your skepticism. Let me address that directly..."
    }
    
    base = templates.get(question["category"], "Let me address your question...")
    themes = " I'll cover " + ", ".join(question.get("key_themes", [])) + "."
    
    return base + themes