from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime
import uuid
from dotenv import load_dotenv
import os
from openai import OpenAI

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
def get_categories(persona_id: Optional[str] = None):
    """Get categories, optionally filtered by persona"""
    
    if not persona_id:
        return questions_data["categories"]
    
    persona_questions = [
        q for q in questions_data["questions"] 
        if persona_id in q.get("persona", [])
    ]

    available_categories = set(q["category"] for q in persona_questions)
    
    # Filter the categories dict to only include available ones
    filtered_categories = {
        cat_name: cat_info 
        for cat_name, cat_info in questions_data["categories"].items()
        if cat_name in available_categories
    }
    
    for cat_name in filtered_categories:
        count = sum(1 for q in persona_questions if q["category"] == cat_name)
        filtered_categories[cat_name]["question_count"] = count
    
    return filtered_categories

@app.get("/scenario/{question_id}/{persona_id}")
def get_scenario(question_id: int, persona_id: str):
    question = next((q for q in questions_data["questions"] if q["id"] == question_id), None)
    persona = next((p for p in personas_data["personas"] if p["id"] == persona_id), None)
    
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
def evaluate_response(session: SessionRequest):
    question = next((q for q in questions_data["questions"] if q["id"] == session.question_id), None)
    persona = next((p for p in personas_data["personas"] if p["id"] == session.persona_id), None)
    
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
        session_id = str(uuid.uuid4())
        sessions_store[session_id] = {
            "id": session_id,
            "question_id": session.question_id,
            "persona_id": session.persona_id,
            "user_response": session.user_response,
            "score": result["score"],
            "timestamp": datetime.now().isoformat(),
            "category": question["category"]
        }
        
        # Update progress
        update_progress(question["category"], session.persona_id, result["score"])
        
        return EvaluationResponse(
            score=result["score"],
            feedback=result["feedback"],
            priorities_covered=result.get("priorities_covered", []),
            engagement_points_covered=result.get("engagement_points_covered", []),
            missing_points=result.get("missing_points", [])
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@app.get("/model-answer/{question_id}")
def get_model_answer(question_id: int, persona_id: Optional[str] = None):
    question = next((q for q in questions_data["questions"] if q["id"] == question_id), None)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Get persona if provided
    persona = None
    if persona_id:
        persona = next((p for p in personas_data["personas"] if p["id"] == persona_id), None)
    
    model_prompt = f"""Create a model answer for an MSL responding to this physician question.

Question: {question['question']}
Category: {question['category']}
Context: {question['context']}
Key Themes to Cover: {', '.join(question.get('key_themes', []))}
"""

    if persona:
        model_prompt += f"""
Physician Persona:
- {persona['name']}, {persona['specialty']}
- Priorities: {', '.join(persona['priorities'][:3])}
- Communication Style: {persona['communication_style']['tone']}
- Engagement Tips: {', '.join(persona['engagement_tips'][:3])}
"""

    model_prompt += """
Create a strong MSL response (200-250 words) that:
1. Directly addresses the question
2. Covers the key themes
3. Uses appropriate communication style for this persona (if provided)
4. Is evidence-based and professional

Also provide:
- 4-5 key points that should be covered
- Brief reasoning for the approach"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert MSL trainer creating model answers."},
                {"role": "user", "content": model_prompt}
            ],
            temperature=0.5,
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        
        return {
            "question_id": question_id,
            "question": question["question"],
            "category": question["category"],
            "model_answer": content,
            "key_points": question.get('key_themes', []),
            "persona_tailored": persona_id is not None
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model answer generation failed: {str(e)}")

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