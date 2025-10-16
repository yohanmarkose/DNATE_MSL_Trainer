from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load JSON files
with open('questions.json', 'r') as f:
    questions_data = json.load(f)

with open('personas.json', 'r') as f:
    personas_data = json.load(f)

# In-memory storage (replace with database in production)
sessions_store = {}
user_progress = {
    "total_sessions": 0,
    "category_stats": {},
    "persona_stats": {},
    "average_score": 0.0,
    "scores_history": []
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

@app.get("/personas")
def get_personas():
    return personas_data["personas"]

@app.get("/personas/{persona_id}")
def get_persona(persona_id: str):
    persona = next((p for p in personas_data["personas"] if p["id"] == persona_id), None)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona

@app.get("/questions")
def get_questions(
    persona_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    category: Optional[str] = None
):
    questions = questions_data["questions"]
    
    if persona_id:
        questions = [q for q in questions if persona_id in q.get("persona", [])]
    
    if difficulty:
        questions = [q for q in questions if q.get("difficulty") == difficulty]
    
    if category:
        questions = [q for q in questions if q.get("category") == category]
    
    return questions

@app.get("/categories")
def get_categories():
    return questions_data["categories"]

@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate_response(session: SessionRequest):
    # Find question and persona
    question = next((q for q in questions_data["questions"] if q["id"] == session.question_id), None)
    persona = next((p for p in personas_data["personas"] if p["id"] == session.persona_id), None)
    
    if not question or not persona:
        raise HTTPException(status_code=404, detail="Question or Persona not found")
    
    # Evaluation logic
    user_response_lower = session.user_response.lower()
    
    # Check priorities covered
    priorities_covered = []
    for priority in persona["priorities"]:
        if any(keyword in user_response_lower for keyword in priority.lower().split()[:3]):
            priorities_covered.append(priority)
    
    # Check engagement tips covered
    engagement_covered = []
    for tip in persona["engagement_tips"]:
        if any(keyword in user_response_lower for keyword in tip.lower().split()[:3]):
            engagement_covered.append(tip)
    
    # Check key themes from question
    themes_covered = 0
    for theme in question.get("key_themes", []):
        if theme.lower() in user_response_lower:
            themes_covered += 1
    
    # Calculate score (0-100)
    priority_score = (len(priorities_covered) / len(persona["priorities"])) * 40
    engagement_score = (len(engagement_covered) / len(persona["engagement_tips"])) * 40
    theme_score = (themes_covered / len(question.get("key_themes", [1]))) * 20 if question.get("key_themes") else 20
    
    total_score = min(100, priority_score + engagement_score + theme_score)
    
    # Generate feedback
    feedback = f"You scored {total_score:.1f}/100. "
    if total_score >= 80:
        feedback += "Excellent response! "
    elif total_score >= 60:
        feedback += "Good response, but could be improved. "
    else:
        feedback += "Your response needs improvement. "
    
    missing_priorities = [p for p in persona["priorities"] if p not in priorities_covered]
    missing_engagement = [e for e in persona["engagement_tips"] if e not in engagement_covered]
    
    # Store session
    session_id = str(uuid.uuid4())
    sessions_store[session_id] = {
        "id": session_id,
        "question_id": session.question_id,
        "persona_id": session.persona_id,
        "user_response": session.user_response,
        "score": total_score,
        "timestamp": datetime.now().isoformat(),
        "category": question["category"]
    }
    
    # Update progress
    update_progress(question["category"], session.persona_id, total_score)
    
    return EvaluationResponse(
        score=total_score,
        feedback=feedback,
        priorities_covered=priorities_covered,
        engagement_points_covered=engagement_covered,
        missing_points=missing_priorities[:3] + missing_engagement[:3]
    )

@app.get("/model-answer/{question_id}")
def get_model_answer(question_id: int):
    question = next((q for q in questions_data["questions"] if q["id"] == question_id), None)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Generate model answer based on question themes
    model_answer = {
        "question_id": question_id,
        "question": question["question"],
        "category": question["category"],
        "model_answer": generate_model_answer(question),
        "key_points": question.get("key_themes", []),
        "reasoning": f"This answer addresses the {question['category']} concern by covering: {', '.join(question.get('key_themes', []))}."
    }
    
    return model_answer

@app.get("/progress")
def get_progress():
    return user_progress

@app.get("/sessions")
def get_sessions():
    return list(sessions_store.values())

def update_progress(category: str, persona_id: str, score: float):
    user_progress["total_sessions"] += 1
    
    # Update category stats
    if category not in user_progress["category_stats"]:
        user_progress["category_stats"][category] = {"count": 0, "avg_score": 0, "total_score": 0}
    
    cat_stats = user_progress["category_stats"][category]
    cat_stats["count"] += 1
    cat_stats["total_score"] += score
    cat_stats["avg_score"] = cat_stats["total_score"] / cat_stats["count"]
    
    # Update persona stats
    if persona_id not in user_progress["persona_stats"]:
        user_progress["persona_stats"][persona_id] = {"count": 0, "avg_score": 0, "total_score": 0}
    
    pers_stats = user_progress["persona_stats"][persona_id]
    pers_stats["count"] += 1
    pers_stats["total_score"] += score
    pers_stats["avg_score"] = pers_stats["total_score"] / pers_stats["count"]
    
    # Update overall average
    user_progress["scores_history"].append(score)
    user_progress["average_score"] = sum(user_progress["scores_history"]) / len(user_progress["scores_history"])

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