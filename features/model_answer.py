from dotenv import load_dotenv
import os
from openai import OpenAI
import json
from typing import Optional
from datetime import datetime


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL_ANSWERS_FILE = "model_answers.json"

# Load JSON files
with open('questions.json', 'r') as f:
    questions_data = json.load(f)

with open('personas.json', 'r') as f:
    personas_data = json.load(f)

# Load or initialize model answers
def load_model_answers():
    if os.path.exists(MODEL_ANSWERS_FILE):
        with open(MODEL_ANSWERS_FILE, 'r') as f:
            return json.load(f)
    return {"answers": {}}

def save_model_answers(data):
    with open(MODEL_ANSWERS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

model_answers_data = load_model_answers()

# Helper to create cache key
def get_answer_key(question_id: int, persona_id: Optional[str] = None):
    """Create a unique key for caching"""
    if persona_id:
        return f"q{question_id}_{persona_id}"
    return f"q{question_id}_generic"

# FUNCTION: Generate all model answers
def generate_all_model_answers():
    """
    Run this function once to generate all model answers.
    Call it from Python directly, not as an API endpoint.
    """
    print("Starting model answer generation...")
    
    generated_answers = {}
    questions = questions_data["questions"]
    personas = personas_data["personas"]
    
    for question in questions:
        question_id = question["id"]
        
        # Generate generic answer
        print(f"Generating generic answer for Q{question_id}...")
        answer_key = get_answer_key(question_id)
        
        model_prompt = f"""Create a model answer for an MSL responding to this physician question.

Question: {question['question']}
Category: {question['category']}
Context: {question['context']}
Key Themes to Cover: {', '.join(question.get('key_themes', []))}

Create a strong MSL response (200-250 words) that:
1. Directly addresses the question
2. Covers the key themes
3. Is evidence-based and professional

Provide your response in this format:
MODEL ANSWER:
[Your detailed response here]

KEY POINTS:
- Point 1
- Point 2
- Point 3
- Point 4

REASONING:
[Brief explanation of the approach]"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert MSL trainer creating model answers."},
                    {"role": "user", "content": model_prompt}
                ],
                temperature=0.5,
                max_tokens=600
            )
            
            content = response.choices[0].message.content
            
            # Parse the response
            sections = content.split("KEY POINTS:")
            model_answer = ""
            key_points = []
            reasoning = ""
            
            if len(sections) > 1:
                model_answer = sections[0].replace("MODEL ANSWER:", "").strip()
                remaining = sections[1].split("REASONING:")
                if len(remaining) > 1:
                    key_points_text = remaining[0].strip()
                    key_points = [line.strip('- ').strip() for line in key_points_text.split('\n') if line.strip().startswith('-')]
                    reasoning = remaining[1].strip()
            else:
                model_answer = content
                key_points = question.get('key_themes', [])
            
            generated_answers[answer_key] = {
                "question_id": question_id,
                "persona_id": None,
                "question": question["question"],
                "category": question["category"],
                "model_answer": model_answer,
                "key_points": key_points if key_points else question.get('key_themes', []),
                "reasoning": reasoning,
                "persona_tailored": False,
                "generated_at": datetime.now().isoformat()
            }
            
            print(f"✓ Generated generic answer for Q{question_id}")
            
        except Exception as e:
            print(f"✗ Error generating generic answer for Q{question_id}: {str(e)}")
        
        # Generate persona-specific answers
        for persona in personas:
            persona_id = persona["id"]
            
            # Only generate if this persona is relevant for this question
            if persona_id in question.get("persona", []):
                print(f"Generating answer for Q{question_id} + {persona_id}...")
                answer_key = get_answer_key(question_id, persona_id)
                
                persona_prompt = f"""Create a model answer for an MSL responding to this physician question.

Question: {question['question']}
Category: {question['category']}
Context: {question['context']}
Key Themes to Cover: {', '.join(question.get('key_themes', []))}

Physician Persona:
- {persona['name']}, {persona['specialty']}
- Practice Setting: {persona['practice_setting']['type']}
- Priorities: {', '.join(persona['priorities'][:3])}
- Communication Style: {persona['communication_style']['tone']}
- Engagement Tips: {', '.join(persona['engagement_tips'][:3])}

Create a strong MSL response (200-250 words) that:
1. Directly addresses the question
2. Covers the key themes
3. Uses appropriate communication style for this specific persona
4. Addresses their specific priorities
5. Is evidence-based and professional

Provide your response in this format:
MODEL ANSWER:
[Your detailed response here]

KEY POINTS:
- Point 1
- Point 2
- Point 3
- Point 4

REASONING:
[Brief explanation of why this approach works for this persona]"""

                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are an expert MSL trainer creating persona-tailored model answers."},
                            {"role": "user", "content": persona_prompt}
                        ],
                        temperature=0.5,
                        max_tokens=600
                    )
                    
                    content = response.choices[0].message.content
                    
                    # Parse the response
                    sections = content.split("KEY POINTS:")
                    model_answer = ""
                    key_points = []
                    reasoning = ""
                    
                    if len(sections) > 1:
                        model_answer = sections[0].replace("MODEL ANSWER:", "").strip()
                        remaining = sections[1].split("REASONING:")
                        if len(remaining) > 1:
                            key_points_text = remaining[0].strip()
                            key_points = [line.strip('- ').strip() for line in key_points_text.split('\n') if line.strip().startswith('-')]
                            reasoning = remaining[1].strip()
                    else:
                        model_answer = content
                        key_points = question.get('key_themes', [])
                    
                    generated_answers[answer_key] = {
                        "question_id": question_id,
                        "persona_id": persona_id,
                        "persona_name": persona['name'],
                        "question": question["question"],
                        "category": question["category"],
                        "model_answer": model_answer,
                        "key_points": key_points if key_points else question.get('key_themes', []),
                        "reasoning": reasoning,
                        "persona_tailored": True,
                        "generated_at": datetime.now().isoformat()
                    }
                    
                    print(f"✓ Generated answer for Q{question_id} + {persona_id}")
                    
                except Exception as e:
                    print(f"✗ Error generating answer for Q{question_id} + {persona_id}: {str(e)}")
    
    # Save all answers to file
    save_data = {
        "answers": generated_answers,
        "metadata": {
            "total_answers": len(generated_answers),
            "generated_at": datetime.now().isoformat()
        }
    }
    
    save_model_answers(save_data)
    print(f"\n✅ Complete! Generated {len(generated_answers)} model answers")
    print(f"Saved to {MODEL_ANSWERS_FILE}")
    
    return generated_answers

if __name__ == "__main__":
    generate_all_model_answers()